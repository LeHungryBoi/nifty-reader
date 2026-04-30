"""
Preset 和 FuseSona — 保存/加载融合配置。

Preset: 保存轨道编辑器的完整状态（clips 位置、权重、level 等）。
FuseSona: 导出融合后的 voice state 为独立配置。
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

from settings import PRESETS_DIR, FUSESONAS_DIR


@dataclass
class ClipData:
    """轨道上的一个 Clip 的序列化数据"""
    persona_name: str = ""
    persona_original_path: str = ""
    track_index: int = 0
    start_frame: int = 0       # 起始帧 (12.5Hz)
    length_frames: int = 0     # 长度（帧数）
    weight: float = 1.0
    fusion_level: int = 4
    effect: dict = field(default_factory=dict)  # ClipEffect dict


@dataclass
class PresetData:
    """一个 Preset 的完整数据"""
    name: str = ""
    created_at: float = 0.0
    clips: list = field(default_factory=list)   # list[ClipData]
    tracks_config: list = field(default_factory=list)


def save_preset(preset: PresetData, running_dir: Path) -> Path:
    """保存 preset 到文件"""
    preset_dir = running_dir / PRESETS_DIR
    preset_dir.mkdir(parents=True, exist_ok=True)
    preset.created_at = time.time()

    filename = f"{preset.name or int(time.time())}.json"
    path = preset_dir / filename

    data = asdict(preset)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path


def load_preset(path: Path) -> PresetData:
    """从文件加载 preset"""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return PresetData(
        name=data.get("name", path.stem),
        created_at=data.get("created_at", 0),
        clips=[ClipData(**c) for c in data.get("clips", [])],
        tracks_config=data.get("tracks_config", []),
    )


def list_presets(running_dir: Path) -> list[dict]:
    """列出所有可用 preset"""
    preset_dir = running_dir / PRESETS_DIR
    if not preset_dir.exists():
        return []
    presets = []
    for p in sorted(preset_dir.glob("*.json")):
        try:
            with open(p, "r") as f:
                data = json.load(f)
            presets.append({
                "name": data.get("name", p.stem),
                "path": str(p),
                "created_at": data.get("created_at", 0),
                "clip_count": len(data.get("clips", [])),
            })
        except Exception:
            continue
    return presets


# ---------------------------------------------------------------------------
# FuseSona
# ---------------------------------------------------------------------------

@dataclass
class FuseSonaMeta:
    """FuseSona 的元信息"""
    name: str = ""
    created_at: float = 0.0
    source_personas: list = field(default_factory=list)  # [{"name": ..., "weight": ..., "effect": ...}]
    fusion_level: int = 4
    fusion_method: str = "align"


def save_fusesona(
    state: dict,
    meta: FuseSonaMeta,
    running_dir: Path,
) -> tuple[Path, Path]:
    """
    保存 FuseSona。
    返回 (state_path, meta_path)。

    state 保存为 .safetensors，meta 保存为 .json。
    """
    import torch

    fusesona_dir = running_dir / FUSESONAS_DIR
    fusesona_dir.mkdir(parents=True, exist_ok=True)
    meta.created_at = time.time()

    safe_name = "".join(c if c.isalnum() or c in "_- " else "_" for c in meta.name or "unnamed")

    state_path = fusesona_dir / f"{safe_name}.safetensors"
    meta_path = fusesona_dir / f"{safe_name}.json"

    # Save state using safetensors
    try:
        from fusion import save_state
        save_state(state, state_path)
    except ImportError:
        # Fallback: save as numpy
        import numpy as np
        flat = {}
        for module_name, module_state in state.items():
            for key, tensor in module_state.items():
                if isinstance(tensor, torch.Tensor):
                    arr = tensor.cpu().numpy()
                else:
                    arr = tensor
                flat[f"{module_name}/{key}"] = arr
        np.savez(state_path.with_suffix(".npz"), **flat)
        state_path = state_path.with_suffix(".npz")

    # Save meta
    meta_data = asdict(meta)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta_data, f, indent=2, ensure_ascii=False)

    return state_path, meta_path


def list_fusesonas(running_dir: Path) -> list[dict]:
    """列出所有可用 FuseSona"""
    fusesona_dir = running_dir / FUSESONAS_DIR
    if not fusesona_dir.exists():
        return []
    result = []
    for p in sorted(fusesona_dir.glob("*.json")):
        try:
            with open(p, "r") as f:
                meta = json.load(f)
            result.append({
                "name": meta.get("name", p.stem),
                "path": str(p),
                "meta_path": str(p),
                "created_at": meta.get("created_at", 0),
                "source_personas": meta.get("source_personas", []),
                "fusion_level": meta.get("fusion_level", 7),
            })
        except Exception:
            continue
    return result
