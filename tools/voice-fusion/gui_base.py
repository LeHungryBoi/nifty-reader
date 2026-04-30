"""共享常量和工具函数"""

import os
import sys
import traceback
import warnings
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from pathlib import Path
from typing import Optional

warnings.filterwarnings("ignore", message=".*cffi callback.*")
warnings.filterwarnings("ignore", message=".*finished_callback_wrapper.*")

try:
    import sounddevice as sd
    _sounddevice_available = True
except ImportError:
    _sounddevice_available = False

# Lazy imports for faster startup
_np = None
_torch = None

def _get_np():
    global _np
    if _np is None:
        import numpy
        _np = numpy
    return _np

def _get_torch():
    global _torch
    if _torch is None:
        import torch
        _torch = torch
    return _torch

# ---------------------------------------------------------------------------
# 路径
# ---------------------------------------------------------------------------

RUNNING_DIR = Path(os.getcwd())
PREPROCESS_CACHE_DIR = RUNNING_DIR / ".cache" / "preprocessed"
AUTO_IMPORT_DIR = RUNNING_DIR / "assets" / "voices"

# ---------------------------------------------------------------------------
# 代理
# ---------------------------------------------------------------------------

def _apply_proxy(proxy: str | None):
    if not proxy:
        return
    for var in ("HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy",
                "ALL_PROXY", "all_proxy"):
        os.environ[var] = proxy

def _patch_cache_dir():
    try:
        from pocket_tts.utils import utils
        utils.make_cache_directory = lambda: RUNNING_DIR / ".cache" / "pocket_tts"
    except ImportError:
        pass

_patch_cache_dir()

# ---------------------------------------------------------------------------
# 导入本地模块
# ---------------------------------------------------------------------------

from settings import load_settings, save_settings, Settings, PRESETS_DIR, FUSESONAS_DIR
from persona import Persona, scan_voices_dir, get_stale_personas, LEVEL_SUFFIXES
from track_editor import TrackEditor, Track, Clip, ClipEffect, level_display_str, parse_level_from_str, LEVEL_SHORT_NAMES
from preset import (
    save_preset, load_preset, list_presets,
    save_fusesona, list_fusesonas, FuseSonaMeta, PresetData, ClipData,
)
from level_extractor import LevelExtractor, save_level_features, get_level_info
from fusion import fuse_voice_states_multi, get_state_info, format_info

# 颜色通过 theme.py 管理，COLORS 保留为兼容别名
from theme import THEME, COLORS, THEMES, get_theme_name
