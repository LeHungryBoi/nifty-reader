"""
Settings persistence — auto-save/load user preferences as JSON in running path.
"""

from __future__ import annotations

import json
from pathlib import Path
from dataclasses import dataclass, field, asdict


SETTINGS_FILE = "voice-fusion-settings.json"
PRESETS_DIR = "assets/fused/presets"
FUSESONAS_DIR = "assets/fused/fusesonas"


@dataclass
class Settings:
    language: str = "english"
    device: str = "cpu"
    proxy_enabled: bool = True
    proxy: str = "http://127.0.0.1:10808"
    test_text: str = "The quick brown fox jumps over the lazy dog."
    alpha: float = 0.5
    method: str = "align"
    last_audio_dir: str = ""
    preprocess_normalize: bool = True
    preprocess_denoise: bool = True
    preprocess_denoise_strength: float = 0.3
    voice_library: list = field(default_factory=list)
    # Track editor state (list of track dicts, each containing clips)
    tracks: list = field(default_factory=list)
    # Fusion level for encoding (1-7, corresponding to spec levels)
    fusion_level: int = 4
    # TTS compare last text
    tts_compare_text: str = ""
    # Theme name
    theme: str = "Zesty"


def load_settings(running_dir: Path) -> Settings:
    """Load settings from JSON, fall back to defaults for missing fields."""
    path = running_dir / SETTINGS_FILE
    if not path.exists():
        return Settings()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        defaults = asdict(Settings())
        defaults.update({k: v for k, v in data.items() if k in defaults})
        return Settings(**defaults)
    except Exception:
        return Settings()


def save_settings(settings: Settings, running_dir: Path) -> None:
    """Save settings to JSON."""
    path = running_dir / SETTINGS_FILE
    with open(path, "w", encoding="utf-8") as f:
        json.dump(asdict(settings), f, indent=2, ensure_ascii=False)
