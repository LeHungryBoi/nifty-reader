"""
Fusion Studio — PocketTTS voice state fusion GUI.

布局:
  - 顶部: 工具栏 (模型加载、预处理、Preset/FuseSona)
  - 左侧: Persona Pool (媒体池，所有已扫描 persona)
  - 右侧: Track 编辑器 + TTS 对比播放
  - 底部: Log
"""

import os
import sys
import time
import threading
import traceback
import warnings
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from pathlib import Path
from typing import Optional

from gui_base import (
    _sounddevice_available, _get_np, _get_torch,
    RUNNING_DIR, AUTO_IMPORT_DIR, COLORS,
    _apply_proxy,
    load_settings, save_settings, Settings,
    Persona, scan_voices_dir, get_stale_personas,
    TrackEditor, Track, Clip, ClipEffect,
    level_display_str, parse_level_from_str, LEVEL_SHORT_NAMES,
)
from theme import THEME, apply_theme, load_theme, get_theme_name, THEMES

# Mixin imports
from gui_toolbar import ToolbarMixin
from gui_pool import PoolMixin
from gui_effect_panel import EffectPanelMixin
from gui_tts_compare import TtsCompareMixin
from gui_fusion import FusionMixin


class VoiceFusionApp(ToolbarMixin, PoolMixin, EffectPanelMixin, TtsCompareMixin, FusionMixin):

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Fusion Studio")
        self.root.geometry("1400x850")
        self.root.minsize(1000, 600)
        self.root.configure(bg=THEME["app_bg"])
        self._set_icon()

        # State
        self.model = None
        self.model_int8 = None
        self.personas: list[Persona] = []
        self._color_idx = 0
        self._generating = False
        self._generating_int8 = False
        self._save_settings_fn = save_settings
        self._play_stream = None
        self._play_audio_data = None
        self._play_sr = 0
        self._play_pos = 0
        self._play_paused = False
        self._play_source_key = None
        self._last_f32_audio = None
        self._last_int8_audio = None
        self._fused_state_cache: Optional[dict] = None
        self._fused_state_key: str = ""

        def _invalidate_fused_cache():
            self._fused_state_cache = None
            self._fused_state_key = ""

        self._invalidate_fused_cache = _invalidate_fused_cache
        self._rescan_running = False
        self._last_active_track_idx: int = 0
        self._persona_level_runtime: dict[str, dict[int, str]] = {}
        self._auto_extract_running = False

        # Preset tabs state
        self._preset_tabs: list[dict] = []  # [{"name": ..., "data": PresetData}, ...]
        self._active_preset_idx: int = 0
        self._preset_tab_buttons: list[ttk.Button] = []

        # Effect panel state
        self._effect_normalize = tk.BooleanVar()
        self._effect_denoise = tk.BooleanVar()
        self._effect_denoise_strength = tk.DoubleVar(value=0.3)
        self._effect_pitch_shift = tk.DoubleVar(value=0.0)

        # Settings
        saved = load_settings(RUNNING_DIR)
        self._saved_settings = saved
        self.test_text = tk.StringVar(value=saved.test_text)
        self._last_generated_text = ""
        self.method = tk.StringVar(value="align")
        self.device = tk.StringVar(value=saved.device)
        self.language = tk.StringVar(value=saved.language)
        self.proxy = tk.StringVar(value=saved.proxy)
        self.proxy_enabled = tk.BooleanVar(value=saved.proxy_enabled)
        self.last_audio_dir = saved.last_audio_dir
        self.preprocess_normalize = tk.BooleanVar(value=saved.preprocess_normalize)
        self.preprocess_denoise = tk.BooleanVar(value=saved.preprocess_denoise)
        self.preprocess_denoise_strength = tk.DoubleVar(value=saved.preprocess_denoise_strength)

        # Restore saved theme (before _build_ui so it applies correctly)
        saved_theme = getattr(saved, "theme", "Zesty")
        if saved_theme and saved_theme in THEMES:
            load_theme(saved_theme)
            self._current_theme_name = saved_theme

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Load restored active tab's data into TrackEditor
        if self._preset_tabs and self._active_preset_idx < len(self._preset_tabs):
            tab = self._preset_tabs[self._active_preset_idx]
            if tab.get("data") is not None and tab["data"].tracks_config:
                self._track_editor.load_from_dict(tab["data"].tracks_config)
            elif getattr(self._saved_settings, "tracks", None):
                # Fallback: legacy single-track restoration
                self._track_editor.load_from_dict(self._saved_settings.tracks)

        # Shortcut manager (replaces all root.bind calls)
        from hotkey import ShortcutManager
        self._hotkey = ShortcutManager(self.root)

        # Global shortcuts
        self._hotkey.bind_global("<space>", self._on_key_space)
        self._hotkey.bind_global("<Shift-space>", self._on_key_shift_space)
        for i in range(12):
            self._hotkey.bind_global(f"<F{i+1}>", lambda e, idx=i: self._switch_preset_tab(idx))

        # Track-editor page shortcuts
        self._hotkey.bind_page("track", "s", lambda e: self._split_at_playhead())
        self._hotkey.bind_page("track", "t", lambda e: self._trim_clip())
        self._hotkey.set_active_page("track")

        # Load model async
        self.root.after(100, self._load_model)

    # ── UI 构建 ──────────────────────────────────────────────────────────

    def _build_ui(self):
        style = ttk.Style()
        apply_theme(style)

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)
        self.root.rowconfigure(5, weight=1)

        # Row 0 — Toolbar
        self._build_toolbar()
        # Row 1 — Main content (split)
        self._build_main_content()
        # Row 5 — Bottom row: left (TTS Compare + Log) | right (Audio Effect)
        self._build_bottom_row()

    def _build_main_content(self):
        pw = ttk.PanedWindow(self.root, orient="horizontal")
        pw.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)

        # Left: Persona Pool
        self._build_pool(pw)

        # Right: Track Editor
        right = ttk.LabelFrame(pw, text="Track Editor", padding=4)
        pw.add(right, weight=1)

        # Preset tabs bar (above track editor)
        self._build_preset_tabs(right, getattr(self._saved_settings, "preset_tabs", None))

        # Track editor toolbar
        te_tb = ttk.Frame(right)
        te_tb.pack(fill="x", pady=(0, 4))
        ttk.Button(te_tb, text="+ Track", command=self._add_track).pack(side="left", padx=2)
        ttk.Button(te_tb, text="- Track", command=self._remove_track).pack(side="left", padx=2)
        ttk.Separator(te_tb, orient="vertical").pack(side="left", fill="y", padx=6)

        self._clip_info_label = ttk.Label(te_tb, text="No clip selected", style="Status.TLabel")
        self._clip_info_label.pack(side="left", padx=4)

        ttk.Separator(te_tb, orient="vertical").pack(side="left", fill="y", padx=6)

        ttk.Label(te_tb, text="Weight:").pack(side="left")
        self._clip_weight_var = tk.DoubleVar(value=1.0)
        self._clip_weight_scale = ttk.Scale(te_tb, from_=0.1, to=3.0,
            variable=self._clip_weight_var, orient="horizontal", length=80,
            command=self._on_clip_weight_change)
        self._clip_weight_scale.pack(side="left", padx=2)

        ttk.Label(te_tb, text="Preset Level:").pack(side="left", padx=(8, 2))
        self._clip_level_var = tk.StringVar(value=level_display_str(4))
        level_values = [level_display_str(i) for i in range(1, 8)]
        level_combo = ttk.Combobox(te_tb, textvariable=self._clip_level_var,
            width=10, state="readonly", values=level_values)
        level_combo.pack(side="left")
        level_combo.bind("<<ComboboxSelected>>", self._on_clip_level_change)

        # Track editor canvas
        self._track_editor = TrackEditor(right)
        self._track_editor.pack(fill="both", expand=True)
        self._track_editor.on_clip_double_click = self._on_clip_double_click
        self._track_editor.on_clip_right_click = self._on_clip_right_click
        self._track_editor.on_track_selected = self._on_track_selected
        self._track_editor.set_preset_level(self._get_active_preset_level())

        # Action bar
        action_row = ttk.Frame(right)
        action_row.pack(fill="x", pady=(4, 0))
        ttk.Button(action_row, text="Generate Fused", command=self._generate_fused,
                   style="Accent.TButton").pack(side="right", padx=4)
        ttk.Button(action_row, text="Split at Playhead", command=self._split_at_playhead).pack(side="right", padx=4)
        ttk.Button(action_row, text="Trim", command=self._trim_clip).pack(side="right", padx=4)

    def _build_log(self, parent: tk.Widget = None):
        if parent is None:
            parent = self.root
        f = ttk.LabelFrame(parent, text="Log", padding=4)
        f.pack(side="top", fill="both", expand=True)
        self.log_text = tk.Text(f, height=5, wrap="word", state="disabled",
                                 font=("Consolas", 9),
                                 bg=THEME["log_bg"], fg=THEME["log_fg"],
                                 insertbackground=THEME["log_cursor"])
        sb = ttk.Scrollbar(f, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.log_text.pack(fill="both", expand=True)
        self.log_text.bind("<Button-3>", self._log_context_menu)

    def _build_bottom_row(self):
        """Build bottom row: left (TTS Compare + Log) | right (Audio Effect)"""
        bottom_pw = ttk.PanedWindow(self.root, orient="horizontal")
        bottom_pw.grid(row=5, column=0, sticky="nsew", padx=8, pady=(0, 8))

        # Left pane: TTS Compare + Log stacked
        left_pane = ttk.Frame(bottom_pw)
        bottom_pw.add(left_pane, weight=1)

        self._build_tts_compare(left_pane)
        self._build_log(left_pane)

        # Right pane: Audio Effect
        right_pane = ttk.Frame(bottom_pw)
        bottom_pw.add(right_pane)
        self._build_effect_panel(right_pane)

    # ── Preset Tabs ──

    def _build_preset_tabs(self, parent, saved_tabs=None):
        """构建预设选项卡栏，显示在轨道编辑器上方"""
        tab_bar = ttk.Frame(parent)
        tab_bar.pack(fill="x", pady=(0, 4))
        self._preset_tab_bar = tab_bar

        # "+" button to add new preset tab
        ttk.Button(tab_bar, text="+", width=2,
                   command=self._add_preset_tab).pack(side="left", padx=(0, 8))

        # Tab buttons container (scrollable)
        tab_container = ttk.Frame(tab_bar)
        tab_container.pack(side="left", fill="x", expand=True)

        self._tab_button_container = tab_container

        # Export button on right side
        ttk.Button(tab_bar, text="Export FuseSona", command=self._export_fusesona).pack(side="right", padx=2)

        # Restore saved tabs or create default
        if saved_tabs and len(saved_tabs) > 0:
            from preset import PresetData, ClipData
            self._preset_tabs = []
            for st in saved_tabs:
                pd = None
                if st.get("clips") or st.get("tracks_config"):
                    clips = [ClipData(**c) for c in st.get("clips", []) if isinstance(c, dict)]
                    pd = PresetData(
                        name=st.get("name", "Preset"),
                        clips=clips,
                        tracks_config=st.get("tracks_config", []),
                    )
                tab_dict = {"name": st.get("name", f"Preset {len(self._preset_tabs)+1}"), "data": pd}
                # Restore saved level, or infer from first clip
                if "fusion_level" in st:
                    tab_dict["fusion_level"] = st["fusion_level"]
                elif pd and pd.clips:
                    tab_dict["fusion_level"] = pd.clips[0].fusion_level if hasattr(pd.clips[0], 'fusion_level') else 4
                else:
                    tab_dict["fusion_level"] = 4
                if pd and pd.clips:
                    for c in pd.clips:
                        c.fusion_level = tab_dict["fusion_level"]
                if pd and pd.tracks_config:
                    self._normalize_tracks_config_level(pd.tracks_config, tab_dict["fusion_level"])
                self._preset_tabs.append(tab_dict)
            self._active_preset_idx = min(getattr(self._saved_settings, "active_preset_idx", 0), len(self._preset_tabs) - 1)
        else:
            self._preset_tabs = [{"name": "Preset 1", "data": None, "fusion_level": 4}]
        self._refresh_preset_tab_buttons()

    def _refresh_preset_tab_buttons(self):
        """重建预设选项卡按钮"""
        for w in self._tab_button_container.winfo_children():
            w.destroy()
        self._preset_tab_buttons = []

        for i, tab in enumerate(self._preset_tabs):
            lvl = tab.get("fusion_level", 4)
            level_tag = LEVEL_SHORT_NAMES.get(lvl, f"L{lvl}")
            btn = ttk.Button(
                self._tab_button_container,
                text=f"F{i+1}: {tab['name']} [{level_tag}]",
                width=14,
                command=lambda idx=i: self._switch_preset_tab(idx),
            )
            btn.pack(side="left", padx=1)
            if i == self._active_preset_idx:
                btn.configure(style="Accent.TButton")
            btn.bind("<Button-3>", lambda e, idx=i: self._preset_tab_context_menu(e, idx))
            self._preset_tab_buttons.append(btn)

    def _add_preset_tab(self):
        """添加新的预设选项卡"""
        idx = len(self._preset_tabs) + 1
        current_level = parse_level_from_str(self._clip_level_var.get())
        self._preset_tabs.append({"name": f"Preset {idx}", "data": None, "fusion_level": current_level})
        self._switch_preset_tab(len(self._preset_tabs) - 1)

    def _remove_preset_tab(self, idx: int = None):
        """移除指定预设选项卡（至少保留一个）"""
        if len(self._preset_tabs) <= 1:
            return
        if idx is None:
            idx = self._active_preset_idx
        self._preset_tabs.pop(idx)
        if self._active_preset_idx >= len(self._preset_tabs):
            self._active_preset_idx = len(self._preset_tabs) - 1
        self._refresh_preset_tab_buttons()
        self._auto_save()
        tab = self._preset_tabs[self._active_preset_idx]
        if tab["data"] is not None:
            self._track_editor.load_from_dict(tab["data"].tracks_config)

    def _preset_tab_context_menu(self, event, idx: int):
        """右键预设选项卡菜单"""
        menu = tk.Menu(self.root, tearoff=0)
        tab = self._preset_tabs[idx]
        menu.add_command(label=f"Rename '{tab['name']}'",
                         command=lambda: self._rename_preset_tab(idx))
        if len(self._preset_tabs) > 1:
            menu.add_command(label="Delete",
                             command=lambda: self._remove_preset_tab(idx))
        menu.post(event.x_root, event.y_root)

    def _rename_preset_tab(self, idx: int):
        """重命名预设选项卡"""
        from tkinter import simpledialog
        tab = self._preset_tabs[idx]
        new_name = simpledialog.askstring("Rename Preset", "New name:",
                                           parent=self.root, initialvalue=tab["name"])
        if new_name and new_name.strip():
            tab["name"] = new_name.strip()
            self._refresh_preset_tab_buttons()
            self._auto_save()

    def _switch_preset_tab(self, idx: int):
        """切换到指定预设选项卡，保存当前状态到旧选项卡"""
        if idx < 0 or idx >= len(self._preset_tabs):
            return

        # Save current state (including level) to current tab
        if self._active_preset_idx < len(self._preset_tabs):
            self._save_current_state_to_tab(self._active_preset_idx)

        self._active_preset_idx = idx
        self._refresh_preset_tab_buttons()
        self._auto_save()

        # Load new tab's data
        tab = self._preset_tabs[idx]
        # Restore the level stored in this tab
        stored_level = tab.get("fusion_level", 4)
        self._clip_level_var.set(level_display_str(stored_level))
        self._track_editor.set_preset_level(stored_level)

        if tab["data"] is not None:
            self._normalize_tracks_config_level(tab["data"].tracks_config, stored_level)
            self._track_editor.load_from_dict(tab["data"].tracks_config)
            self._normalize_live_clips_level(stored_level)
            self._log(f"[Preset] Switched to: {tab['name']} (L{stored_level})")
        else:
            # Fresh tab — clear tracks
            self._track_editor.tracks = [Track(index=0, name="T1")]
            self._track_editor._selected_clip = None
            self._track_editor._redraw()

    def _save_current_state_to_tab(self, idx: int):
        """将当前轨道编辑器状态保存到指定选项卡"""
        if idx < 0 or idx >= len(self._preset_tabs):
            return
        tab = self._preset_tabs[idx]
        preset_level = int(tab.get("fusion_level", 4))
        self._normalize_live_clips_level(preset_level)
        clips_data = []
        for track_idx, clip in self._track_editor.get_all_clips():
            clips_data.append(clip.to_clip_data(track_idx))
        from preset import PresetData
        tab["data"] = PresetData(
            name=tab["name"],
            clips=clips_data,
            tracks_config=self._track_editor.to_dict(),
        )
        tab["fusion_level"] = preset_level

    def _normalize_live_clips_level(self, level: int):
        """将当前编辑器中所有 clip 的 level 统一为 preset level。"""
        for _, clip in self._track_editor.get_all_clips():
            clip.fusion_level = level

    @staticmethod
    def _normalize_tracks_config_level(tracks_config: list, level: int):
        """兼容旧数据：将 tracks_config 内所有 clip level 规范为 tab level。"""
        for track in tracks_config or []:
            clips = track.get("clips", []) if isinstance(track, dict) else []
            for clip in clips:
                if isinstance(clip, dict):
                    clip["fusion_level"] = level

    def _get_active_preset_level(self) -> int:
        if 0 <= self._active_preset_idx < len(self._preset_tabs):
            return int(self._preset_tabs[self._active_preset_idx].get("fusion_level", 4))
        return 4


    # ── Theme ──

    def _on_theme_change(self, event=None):
        """切换主题并刷新所有 UI"""
        name = self._theme_var.get()
        if name == self._current_theme_name:
            return
        load_theme(name)
        self._current_theme_name = name
        # Re-apply ttk styles
        style = ttk.Style()
        apply_theme(style)
        # Refresh root bg
        self.root.configure(bg=THEME["app_bg"])
        # Refresh themed widgets
        self.log_text.configure(
            bg=THEME["log_bg"], fg=THEME["log_fg"],
            insertbackground=THEME["log_cursor"])
        self._track_editor.configure(bg=THEME["track_editor_bg"])
        self._track_editor._redraw()
        # Refresh pool canvas
        if hasattr(self, "_pool_canvas"):
            self._pool_canvas.configure(bg=THEME["app_bg"])
        if self.personas:
            self._rebuild_pool()
        self._log(f"[Theme] Switched to: {name}")

    # ── Key Bindings ──

    def _on_key_space(self, event):
        """Space = generate and play f32"""
        self.root.focus_set()
        self._play_f32()

    def _on_key_shift_space(self, event):
        """Shift+Space = play int8"""
        self.root.focus_set()
        if self._last_int8_audio is not None or self._last_f32_audio is not None:
            self._play_int8()

    # ── Settings Dialog ──

    def _show_settings_dialog(self):
        """打开设置对话框（包含代理设置）"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Settings")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg=THEME["app_bg"])

        nb = ttk.Notebook(dialog)
        nb.pack(fill="both", expand=True, padx=8, pady=8)

        # Proxy tab
        proxy_frame = ttk.Frame(nb, padding=12)
        nb.add(proxy_frame, text="Proxy")

        ttk.Checkbutton(proxy_frame, text="Enable Proxy",
                        variable=self.proxy_enabled).pack(anchor="w", pady=(0, 8))
        ttk.Label(proxy_frame, text="Proxy Address:").pack(anchor="w")
        ttk.Entry(proxy_frame, textvariable=self.proxy, width=40).pack(fill="x", pady=(0, 8))
        ttk.Label(proxy_frame, text="Format: http://host:port or socks5://host:port",
                  style="Status.TLabel").pack(anchor="w")

        # Apply/Close
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(btn_frame, text="Close", command=dialog.destroy).pack(side="right", padx=2)

    # ── Voice Scanning ──

    def _rescan_voices(self, preprocess_stale: bool = True):
        if self._rescan_running:
            self._log("[Scan] Already running")
            return

        self._rescan_running = True
        self.model_status.configure(text="Scanning voices...")

        normalize = self.preprocess_normalize.get()
        denoise = self.preprocess_denoise.get()
        denoise_strength = self.preprocess_denoise_strength.get()

        def task():
            try:
                AUTO_IMPORT_DIR.mkdir(parents=True, exist_ok=True)
                personas = scan_voices_dir(AUTO_IMPORT_DIR)
                stale = get_stale_personas(personas)

                def on_scanned():
                    self.personas = personas
                    self._persona_level_runtime = {
                        p.original_path: self._get_persona_level_states(p)
                        for p in personas
                    }
                    self._log(f"[Scan] Found {len(personas)} persona(s) in {AUTO_IMPORT_DIR}")
                    if stale:
                        self._log(f"[Scan] {len(stale)} persona(s) need re-processing")
                    self._rebuild_pool()
                    if self.model is not None:
                        self.model_status.configure(text=f"Ready ({self.device.get()})")
                        self._start_auto_extract_personas()
                    else:
                        self.model_status.configure(text="Not loaded")

                self.root.after(0, on_scanned)

                if preprocess_stale and stale:
                    for p in stale:
                        self._preprocess_persona(
                            p,
                            normalize=normalize,
                            denoise=denoise,
                            denoise_strength=denoise_strength,
                        )
            except Exception as e:
                self.root.after(0, lambda: self._log(f"[Error] Scan failed: {e}"))
            finally:
                self._rescan_running = False

        threading.Thread(target=task, daemon=True).start()

    def _get_persona_level_states(self, persona: Persona) -> dict[int, str]:
        """返回 persona 各 level 的缓存状态。"""
        base = {}
        for level in range(1, 8):
            base[level] = "ready" if persona.get_derived_path(level).exists() else "missing"
        runtime = self._persona_level_runtime.get(persona.original_path, {})
        for level, state in runtime.items():
            if state in ("extracting", "error", "queued"):
                base[level] = state
            elif state == "ready":
                base[level] = "ready"
        return base

    def _set_persona_level_status(self, persona: Persona, level: int, status: str):
        states = self._persona_level_runtime.setdefault(persona.original_path, {})
        states[level] = status

    def _refresh_pool_async(self):
        try:
            self.root.after(0, self._rebuild_pool)
        except Exception:
            pass

    def _start_auto_extract_personas(self):
        if self.model is None or self._auto_extract_running or not self.personas:
            return
        self._auto_extract_running = True

        def task():
            try:
                for persona in self.personas:
                    current = self._get_persona_level_states(persona)
                    missing = [l for l in range(2, 8) if current.get(l) != "ready"]
                    if not missing:
                        continue
                    for level in missing:
                        self._set_persona_level_status(persona, level, "extracting")
                    self._refresh_pool_async()
                    features = self._extract_persona_levels(persona) or {}
                    if features:
                        for level in range(2, 8):
                            exists = persona.get_derived_path(level).exists()
                            self._set_persona_level_status(persona, level, "ready" if exists else "missing")
                        if persona.get_derived_path(1).exists():
                            self._set_persona_level_status(persona, 1, "ready")
                    else:
                        for level in missing:
                            self._set_persona_level_status(persona, level, "error")
                    self._refresh_pool_async()
                self._log("[Extract] auto precompute finished")
            finally:
                self._auto_extract_running = False

        threading.Thread(target=task, daemon=True).start()

    # ── Model Loading ──

    def _load_model(self):
        if self.model is not None:
            return
        proxy = self.proxy.get().strip() if self.proxy_enabled.get() else None
        if proxy:
            _apply_proxy(proxy)
        else:
            for var in ("HTTP_PROXY", "http_proxy", "HTTPS_PROXY",
                        "https_proxy", "ALL_PROXY", "all_proxy"):
                os.environ.pop(var, None)

        self.load_btn.configure(state="disabled")
        self.model_status.configure(text="Loading...")

        def task():
            try:
                from pocket_tts import TTSModel
                self.root.after(0, lambda: self.model_status.configure(text="Loading model..."))
                model = TTSModel.load_model(language=self.language.get() or None)
                model = model.to(self.device.get())
                self.model = model
                self.root.after(0, self._on_model_loaded)
                # 加载 int8 量化模型
                self.root.after(0, lambda: self.model_status.configure(text="Loading int8 model..."))
                try:
                    model_int8 = TTSModel.load_model(language=self.language.get() or None)
                    model_int8 = model_int8.to("cpu")  # int8 模型用 CPU 节省显存
                    self.model_int8 = model_int8
                    self._log("[Model] Int8 model loaded (CPU)")
                except Exception as e:
                    self._log(f"[Model] Int8 model load failed: {e}")
                    self.model_int8 = None
            except Exception as e:
                err = traceback.format_exc()
                self.root.after(0, lambda _e=e, _err=err:
                    self._on_error(f"Model load failed:\n{_err}", exc=_e))

        threading.Thread(target=task, daemon=True).start()

    def _on_model_loaded(self):
        sr = self.model.sample_rate if hasattr(self.model, "sample_rate") else self.model.config.mimi.sample_rate
        self.model_status.configure(text=f"Ready ({self.device.get()}, {sr}Hz)")
        self._log(f"Model loaded on {self.device.get()}, {sr}Hz")
        self._rescan_voices(preprocess_stale=False)

    # ── Track Operations ──

    def _on_track_selected(self, track_idx: int):
        self._last_active_track_idx = track_idx

    def _add_track(self):
        self._track_editor.add_track()
        self._auto_save()
        self._invalidate_fused_cache()


    def _remove_track(self):
        sel = self._track_editor.get_selected_clip()
        if sel:
            self._track_editor.remove_track(sel[0])
        else:
            self._track_editor.remove_track(len(self._track_editor.tracks) - 1)
        self._auto_save()
        self._invalidate_fused_cache()

    def _add_persona_to_track(self, persona: Persona, new_track: bool = True):
        if not new_track:
            # Right-click: use selected clip's track; if none selected, fall back to new track
            sel = self._track_editor.get_selected_clip()
            if sel:
                track_idx = sel[0]
            else:
                new_track = True

        if new_track:
            # Find first empty track (from index 0)
            track_idx = None
            for i, t in enumerate(self._track_editor.tracks):
                if not t.clips:
                    track_idx = i
                    break
            if track_idx is None:
                # All tracks have clips, create a new one
                track = self._track_editor.add_track()
                track_idx = track.index

        color = COLORS[self._color_idx % len(COLORS)]
        self._color_idx += 1

        level = self._get_active_preset_level()
        latent_frames = self._get_persona_latent_frames(persona, level=level)

        clip = Clip(
            persona_name=persona.name,
            persona_original_path=persona.original_path,
            start_frame=0,
            length_frames=latent_frames,
            original_length_frames=latent_frames,
            weight=1.0,
            fusion_level=level,
            color=color,
        )
        track = self._track_editor.tracks[track_idx]
        if track.clips:
            clip.start_frame = max(c.end_frame for c in track.clips)

        self._track_editor.add_clip(track_idx, clip)
        self._last_active_track_idx = track_idx
        self._log(f"[Track] Added '{persona.display_name}' to T{track_idx + 1}")
        self._auto_save()
        self._invalidate_fused_cache()


    @staticmethod
    def _get_persona_latent_frames(persona: Persona, level: int = 4) -> int:
        """
        Get the latent time dimension for a persona at a given level.
        Tries to read the extracted feature .npy file; falls back to audio duration.
        """
        try:
            import numpy as np
            derived_path = persona.get_derived_path(level)
            if derived_path.exists():
                arr = np.load(str(derived_path))
                # Level 7 shape: [N, 2, B, T, H, D] → time dim is index 3
                # Level 2 shape: [B, 512, T] → time dim is last
                # Level 4 shape: [B, 32, T] → time dim is last
                # Level 5 shape: [B, T, 32] → time dim is 1
                # Level 6 shape: [B, T, 1024] → time dim is 1
                if level == 7 and arr.ndim >= 4:
                    return max(int(arr.shape[3]), 20)
                elif level in (5, 6) and arr.ndim >= 2:
                    return max(int(arr.shape[1]), 20)
                elif arr.ndim >= 1:
                    return max(int(arr.shape[-1]), 20)
        except Exception:
            pass
        # Fallback: estimate from audio duration
        return VoiceFusionApp._get_audio_duration_frames(persona.original_path)

    @staticmethod
    def _get_audio_duration_frames(audio_path: str) -> int:
        """Read audio file duration and return visual frame count (1 frame = 10ms)."""
        try:
            import soundfile as sf
            info = sf.info(audio_path)
            return max(int(info.duration * 100), 20)  # 20 frames minimum
        except Exception:
            return 100

    def _split_at_playhead(self):
        sel = self._track_editor.get_selected_clip()
        if not sel:
            messagebox.showinfo("Split", "Select a clip first")
            return
        track_idx, clip = sel
        frame = int(self._track_editor.playhead_frame)
        self._track_editor.split_clip_at(track_idx, clip, frame)
        self._log(f"[Track] Split clip '{clip.persona_name}' at frame {frame}")
        self._auto_save()
        self._invalidate_fused_cache()


    def _trim_clip(self):
        trimmed = self._track_editor.trim_clip_at_playhead()
        if not trimmed:
            sel = self._track_editor.get_selected_clip()
            if not sel:
                messagebox.showinfo("Trim", "Select a clip first, then position playhead inside it")
            else:
                messagebox.showinfo("Trim", "Position playhead inside the clip to trim")
            return
        _, clip = self._track_editor.get_selected_clip()
        self._log(f"[Track] Trimmed '{clip.persona_name}' → [{clip.start_frame}-{clip.end_frame}]")
        self._auto_save()
        self._invalidate_fused_cache()


    def _on_clip_double_click(self, track_idx, clip):
        self._clip_info_label.configure(
            text=f"Selected: {clip.persona_name} | Track {track_idx + 1} | "
                 f"[{clip.start_frame}-{clip.end_frame}]")
        self._clip_weight_var.set(clip.weight)
        self._clip_level_var.set(level_display_str(self._get_active_preset_level()))
        self._show_effect_panel(clip)

    def _on_clip_right_click(self, event, track_idx, clip):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label=f"Delete '{clip.persona_name}'",
                         command=lambda: self._delete_clip(track_idx, clip))
        menu.add_command(label="Split at Playhead",
                         command=lambda: (self._track_editor.split_clip_at(
                             track_idx, clip, int(self._track_editor.playhead_frame)),
                             self._invalidate_fused_cache()))
        menu.add_command(label=f"Reset Length ({clip.original_length_frames} frames)",
                         command=lambda: (self._track_editor.reset_clip_length(clip),
                             self._invalidate_fused_cache()))
        menu.add_separator()
        eff = clip.effect
        has_eff = eff.has_custom_effects()
        pitch_str = f"pitch={eff.pitch_shift:+.1f}st" if eff.pitch_shift != 0 else ""
        eff_str = " (custom effects)" if has_eff else ""
        menu.add_command(label=f"Weight: {clip.weight:.1f} | Level: {clip.fusion_level}{eff_str} {pitch_str}",
                         state="disabled")
        menu.add_command(label="Edit Effects",
                         command=lambda: self._show_effect_panel(clip))
        menu.post(event.x_root, event.y_root)

    def _delete_clip(self, track_idx, clip):
        self._track_editor.remove_clip(track_idx, clip)
        self._hide_effect_panel()
        self._auto_save()
        self._invalidate_fused_cache()


    def _on_clip_weight_change(self, val):
        sel = self._track_editor.get_selected_clip()
        if sel:
            sel[1].weight = float(val)
            self._track_editor._redraw()
            self._auto_save()
            self._invalidate_fused_cache()


    def _on_clip_level_change(self, event=None):
        new_level = parse_level_from_str(self._clip_level_var.get())
        # Update current preset tab's level
        if self._active_preset_idx < len(self._preset_tabs):
            self._preset_tabs[self._active_preset_idx]["fusion_level"] = new_level
            self._normalize_live_clips_level(new_level)
            self._track_editor.set_preset_level(new_level)
            self._refresh_preset_tab_buttons()
            self._auto_save()
            self._invalidate_fused_cache()

        self._track_editor._redraw()

    # ── Preview ──

    def _preview_audio(self, persona, mode: str = "raw"):
        if not _sounddevice_available:
            messagebox.showwarning("Warning", "Install sounddevice for playback")
            return

        if mode == "raw":
            path = persona.original_path
        else:
            path = str(persona.get_derived_path(1))
            if not Path(path).exists():
                self._log(f"[Preview] No processed audio for {persona.display_name}, using raw")
                path = persona.original_path

        p = Path(path)
        if not p.exists():
            messagebox.showwarning("Warning", f"File not found: {p}")
            return

        try:
            import soundfile as sf
            data, sr = sf.read(p)
            if data.ndim > 1:
                data = data[:, 0]
            import numpy as np
            audio = data.astype(np.float32)
            self._log(f"[Preview] {mode}: {persona.display_name}")
            import sounddevice as sd
            from audio_duck import AudioDuck
            AudioDuck().duck_for_playback()
            sd.play(audio, sr)
        except Exception as e:
            self._on_error(f"Preview failed: {e}")

    def _preview_audio_path(self, path: Path, label: str = ""):
        if not _sounddevice_available:
            messagebox.showwarning("Warning", "Install sounddevice for playback")
            return
        p = Path(path)
        if not p.exists():
            return
        try:
            import soundfile as sf
            import numpy as np
            import sounddevice as sd
            data, sr = sf.read(p)
            if data.ndim > 1:
                data = data[:, 0]
            audio = data.astype(np.float32)
            self._log(f"[Preview] {label}: {p.name}")
            from audio_duck import AudioDuck
            AudioDuck().duck_for_playback()
            sd.play(audio, sr)
        except Exception as e:
            self._on_error(f"Preview failed: {e}")

    # ── Settings ──

    def _auto_save(self):
        """Auto-save current state to settings file (debounced)."""
        if hasattr(self, "_auto_save_pending"):
            return
        self._auto_save_pending = True
        self.root.after(500, self._do_auto_save)

    def _do_auto_save(self):
        self._auto_save_pending = False
        try:
            settings = self._collect_settings()
            self._save_settings_fn(settings, RUNNING_DIR)
        except Exception:
            pass

    def _collect_settings(self):
        # Save current state to active tab before collecting
        self._save_current_state_to_tab(self._active_preset_idx)
        # Serialize preset tabs for persistence
        saved_tabs = []
        for tab in self._preset_tabs:
            tab_dict = {"name": tab["name"], "fusion_level": tab.get("fusion_level", 4)}
            if tab["data"] is not None:
                self._normalize_tracks_config_level(tab["data"].tracks_config, tab_dict["fusion_level"])
                tab_dict["clips"] = [c.__dict__ if hasattr(c, "__dict__") else c for c in tab["data"].clips]
                tab_dict["tracks_config"] = tab["data"].tracks_config
            else:
                tab_dict["clips"] = []
                tab_dict["tracks_config"] = []
            saved_tabs.append(tab_dict)
        return Settings(
            language=self.language.get(),
            device=self.device.get(),
            proxy_enabled=self.proxy_enabled.get(),
            proxy=self.proxy.get(),
            test_text=self.test_text.get(),
            alpha=0.5,
            method=self.method.get(),
            last_audio_dir=self.last_audio_dir,
            preprocess_normalize=self.preprocess_normalize.get(),
            preprocess_denoise=self.preprocess_denoise.get(),
            preprocess_denoise_strength=self.preprocess_denoise_strength.get(),
            voice_library=[p.to_dict() for p in self.personas],
            tracks=self._track_editor.to_dict(),
            theme=self._current_theme_name,
            preset_tabs=saved_tabs,
            active_preset_idx=self._active_preset_idx,
        )

    def _on_close(self):
        try:
            import sounddevice as sd
            sd.stop()
        except Exception:
            pass
        self._save_settings_fn(self._collect_settings(), RUNNING_DIR)
        self.root.destroy()

    # ── Log / Error ──

    def _set_icon(self):
        """Set window icon (title bar + taskbar) from pre-generated ICO file"""
        ico_path = Path(__file__).parent / "fusion-icon.ico"
        png_path = Path(__file__).parent / "fusion-icon.png"
        try:
            self.root.iconbitmap(str(ico_path)) if ico_path.exists() else None
        except Exception:
            pass
        if not png_path.exists():
            return
        try:
            from PIL import Image, ImageTk
            img = Image.open(png_path)
            self._icon_photo = ImageTk.PhotoImage(img)
            self.root.iconphoto(True, self._icon_photo)
        except Exception:
            pass

    def _log_context_menu(self, event):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Copy All", command=self._copy_log)
        menu.add_command(label="Clear Log", command=self._clear_log)
        menu.post(event.x_root, event.y_root)

    def _copy_log(self):
        content = self.log_text.get("1.0", "end").strip()
        if content:
            self.root.clipboard_clear()
            self.root.clipboard_append(content)

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _log(self, msg: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _on_error(self, msg: str, exc: Exception | None = None):
        self.load_btn.configure(state="normal")
        self.model_status.configure(text="Error")
        self._log(f"ERROR: {msg}")
        if exc:
            traceback.print_exception(type(exc), exc, exc.__traceback__, file=sys.stderr)
        messagebox.showerror("Error", msg)


def main():
    root = tk.Tk()
    app = VoiceFusionApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
