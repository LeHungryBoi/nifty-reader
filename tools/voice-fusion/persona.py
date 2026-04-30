"""
Voice Library — Persona 管理。

每个 Persona 以 assets/voices/ 下的一个原始音频文件为身份标识。
系统自动管理衍生文件（预处理音频、各 level 特征），以原始音频的
modify time 作为版本标识来判断衍生文件是否过期。
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


VOICE_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}

# 衍生文件后缀映射 (level -> suffix for numpy cache)
# level 1-5 是 mimi encoder 内部, 6-7 是外部
LEVEL_SUFFIXES = {
    1: ".processed.wav",      # 预处理后的音频
    2: ".level2.npy",         # SEANet Features
    3: ".level3.npy",         # Encoder Attn
    4: ".level4.npy",         # MiMi Latent
    5: ".level5.npy",         # transpose
    6: ".level6.npy",         # Speaker Proj
    7: ".level7.npy",         # FlowLM KV Cache
}

# version 文件名，存储原始音频的 mtime
_VERSION_FILE = ".persona_version.json"


@dataclass
class PersonaVersion:
    """Persona 的版本信息（基于原始音频的 modify time）"""
    mtime: float = 0.0
    file_hash: str = ""


@dataclass
class Persona:
    """语音库中的一个 Persona 条目"""
    name: str
    original_path: str           # 原始音频文件绝对路径
    namespace: str = ""          # 子文件夹命名空间 (如 "v2")
    selected: bool = False
    weight: float = 1.0

    @property
    def original_path_obj(self) -> Path:
        return Path(self.original_path)

    @property
    def derived_dir(self) -> Path:
        """衍生文件所在目录（与原始音频同目录）"""
        return self.original_path_obj.parent

    @property
    def display_name(self) -> str:
        if self.namespace:
            return f"{self.namespace}/{self.name}"
        return self.name

    def get_derived_path(self, level: int) -> Path:
        """获取指定 level 的衍生文件路径"""
        suffix = LEVEL_SUFFIXES.get(level, f".level{level}.npy")
        return self.derived_dir / f"{self.name}{suffix}"

    def get_version_path(self) -> Path:
        """获取版本信息文件路径"""
        return self.derived_dir / f"{self.name}.persona_meta.json"

    def get_current_mtime(self) -> float:
        """获取原始音频的当前 modify time"""
        p = self.original_path_obj
        if p.exists():
            return p.stat().st_mtime
        return 0.0

    def is_derived_valid(self) -> bool:
        """检查衍生文件是否与原始音频版本一致"""
        meta_path = self.get_version_path()
        if not meta_path.exists():
            return False
        try:
            with open(meta_path, "r") as f:
                meta = json.load(f)
            return meta.get("mtime", 0) == self.get_current_mtime()
        except (json.JSONDecodeError, KeyError):
            return False

    def save_version(self) -> None:
        """保存当前原始音频的版本信息"""
        meta_path = self.get_version_path()
        meta = {
            "mtime": self.get_current_mtime(),
            "name": self.name,
            "original_path": self.original_path,
        }
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)

    def get_all_derived_files(self) -> list[Path]:
        """列出所有衍生文件"""
        files = []
        for level in LEVEL_SUFFIXES:
            p = self.get_derived_path(level)
            if p.exists():
                files.append(p)
        # 也列出 effect 缓存文件
        effect_cache_dir = self.derived_dir / ".effect_cache"
        if effect_cache_dir.exists():
            files.extend(effect_cache_dir.glob(f"{self.name}.effect_*.wav"))
        return files

    def get_effect_cache_dir(self) -> Path:
        """Effect 衍生缓存的目录"""
        return self.derived_dir / ".effect_cache"

    def get_effect_audio_path(self, effect_key: str) -> Path:
        """获取指定 effect key 的衍生 WAV 缓存路径"""
        cache_dir = self.get_effect_cache_dir()
        return cache_dir / f"{self.name}.effect_{effect_key}.wav"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "original_path": self.original_path,
            "namespace": self.namespace,
            "selected": self.selected,
            "weight": self.weight,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Persona:
        return cls(
            name=d.get("name", ""),
            original_path=d.get("original_path", ""),
            namespace=d.get("namespace", ""),
            selected=d.get("selected", False),
            weight=d.get("weight", 1.0),
        )


def scan_voices_dir(voices_dir: Path) -> list[Persona]:
    """递归扫描 voices 目录，发现所有 Persona"""
    personas = []
    if not voices_dir.exists():
        return personas

    for path in sorted(voices_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in VOICE_EXTENSIONS:
            continue
        # 跳过衍生文件
        if any(path.name.endswith(suffix) for suffix in LEVEL_SUFFIXES.values()):
            continue
        if path.name.endswith(".persona_meta.json"):
            continue
        # 跳过 effect 缓存目录下的文件
        if ".effect_cache" in path.parts:
            continue

        rel = path.relative_to(voices_dir)
        namespace = str(rel.parent) if str(rel.parent) != "." else ""

        personas.append(Persona(
            name=path.stem,
            original_path=str(path.resolve()),
            namespace=namespace,
        ))
    return personas


def get_stale_personas(personas: list[Persona]) -> list[Persona]:
    """获取衍生文件已过期的 Persona 列表"""
    return [p for p in personas if not p.is_derived_valid()]
