"""
Audio preprocessing for PocketTTS voice cloning sources.

Pipeline (ffmpeg CLI):
- decode any supported input
- trim to max duration
- mono + resample 24kHz
- optional normalize / denoise filters
- write PCM16 WAV cache atomically
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

PREPROCESS_DIR_NAME = "preprocessed"
MAX_SAFE_DURATION_S = 180.0


def _file_hash(path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()[:16]


def _which_or_raise(name: str) -> str:
    p = shutil.which(name)
    if not p:
        raise RuntimeError(f"Missing required binary: {name}")
    return p


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def _ffprobe_stream_info(input_path: Path) -> dict:
    ffprobe = _which_or_raise("ffprobe")
    cmd = [
        ffprobe,
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_entries",
        "stream=channels,sample_rate,duration",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(input_path),
    ]
    cp = _run(cmd)
    if cp.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {cp.stderr.strip() or cp.stdout.strip()}")

    data = json.loads(cp.stdout or "{}")
    stream = (data.get("streams") or [{}])[0]
    fmt = data.get("format") or {}

    channels = int(stream.get("channels") or 1)
    sample_rate = int(float(stream.get("sample_rate") or 0))
    dur = stream.get("duration") or fmt.get("duration") or 0
    duration_s = float(dur) if dur else 0.0

    return {
        "channels": channels,
        "sample_rate": sample_rate,
        "duration_s": duration_s,
        "peak": 0.0,
        "peak_db": -120.0,
        "rms_db": -120.0,
        "needs_mono": channels > 1,
        "needs_resample": sample_rate != 24000 if sample_rate else True,
        "needs_normalize": False,
        "has_clipping": False,
    }


def format_detect(info: dict) -> str:
    parts = [f"{info['duration_s']:.1f}s"]
    if info["channels"] > 1:
        parts.append(f"{info['channels']}ch")
    parts.append(f"{info['sample_rate']}Hz")
    parts.append(f"peak={info['peak_db']:.1f}dB")
    parts.append(f"rms={info['rms_db']:.1f}dB")
    if info["has_clipping"]:
        parts.append("CLIPPING!")
    return ", ".join(parts)


def format_actions(actions: list[str]) -> str:
    if not actions:
        return "(no changes needed)"
    return " -> ".join(actions)


def _build_filters(normalize: bool, denoise: bool, denoise_strength: float) -> tuple[str, list[str]]:
    actions: list[str] = ["mono", "24kHz"]
    filters: list[str] = []

    # Always enforce output format for model conditioning.
    filters.append("aformat=channel_layouts=mono")
    filters.append("aresample=24000")

    if denoise:
        # afftdn strength mapped through noise floor/amount.
        nf = -20.0 - (denoise_strength * 25.0)
        amount = 0.2 + (denoise_strength * 0.8)
        filters.append(f"afftdn=nf={nf:.1f}:om=o:ad={amount:.2f}")
        actions.append(f"denoise({denoise_strength:.1f})")

    if normalize:
        # Lightweight loudness normalization + hard ceiling near -3 dBFS.
        filters.append("loudnorm=I=-19:LRA=7:TP=-3")
        actions.append("norm(-3dB-ish)")

    return ",".join(filters), actions


def preprocess_audio(
    input_path: str | Path,
    cache_dir: Path,
    target_sr: int = 24000,
    normalize: bool = True,
    denoise: bool = True,
    denoise_strength: float = 0.3,
) -> tuple[Path, dict]:
    input_path = Path(input_path)
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    if target_sr != 24000:
        raise ValueError("ffmpeg preprocessing currently expects target_sr=24000")

    detect = _ffprobe_stream_info(input_path)

    fh = _file_hash(input_path)
    key = f"ff_n{int(normalize)}d{int(denoise)}s{int(denoise_strength * 100):02d}_sr{target_sr}"
    cache_path = cache_dir / f"{fh}_{key}.wav"

    if cache_path.exists():
        return cache_path, {"cached": True, "actions": ["from cache"], "detect": detect}

    ffmpeg = _which_or_raise("ffmpeg")
    afilters, actions = _build_filters(normalize, denoise, denoise_strength)

    # Always bound duration before model extraction.
    actions.insert(0, f"trim(<= {MAX_SAFE_DURATION_S:.0f}s)")

    tmp_path = cache_path.with_suffix(".tmp.wav")
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(input_path),
        "-vn",
        "-t",
        str(int(MAX_SAFE_DURATION_S)),
        "-af",
        afilters,
        "-ac",
        "1",
        "-ar",
        "24000",
        "-f",
        "wav",
        "-c:a",
        "pcm_s16le",
        str(tmp_path),
    ]
    cp = _run(cmd)
    if cp.returncode != 0:
        tmp_path.unlink(missing_ok=True)
        raise RuntimeError(f"ffmpeg preprocess failed: {cp.stderr.strip() or cp.stdout.strip()}")

    if not tmp_path.exists() or tmp_path.stat().st_size <= 44:
        tmp_path.unlink(missing_ok=True)
        raise RuntimeError(f"ffmpeg produced invalid wav: {tmp_path}")

    os.replace(tmp_path, cache_path)

    report = {"cached": False, "actions": actions, "detect": detect}
    logger.info("Preprocessed (ffmpeg): %s -> %s | %s", input_path.name, cache_path.name, actions)
    return cache_path, report


def clear_cache(cache_dir: Path) -> int:
    cache_dir = Path(cache_dir)
    if not cache_dir.exists():
        return 0
    count = 0
    for f in cache_dir.iterdir():
        if f.suffix == ".wav":
            f.unlink()
            count += 1
    return count
