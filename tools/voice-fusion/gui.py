"""
Voice Fusion Tool — PocketTTS voice state fusion GUI.

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
    level_display_str, parse_level_from_str,
)

# Mixin imports
from gui_toolbar import ToolbarMixin
from gui_pool import PoolMixin
from gui_effect_panel import EffectPanelMixin
from gui_tts_compare import TtsCompareMixin
from gui_fusion import FusionMixin


class VoiceFusionApp(ToolbarMixin, PoolMixin, EffectPanelMixin, TtsCompareMixin, FusionMixin):

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Voice Fusion Tool")
        self.root.geometry("1400x850")
        self.root.minsize(1000, 600)

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
        self._rescan_running = False

        # Effect panel state
        self._effect_normalize = tk.BooleanVar()
        self._effect_denoise = tk.BooleanVar()
        self._effect_denoise_strength = tk.DoubleVar(value=0.3)
        self._effect_pitch_shift = tk.DoubleVar(value=0.0)

        # Settings
        saved = load_settings(RUNNING_DIR)
        self.test_text = tk.StringVar(value=saved.test_text)
        self.method = tk.StringVar(value=saved.method)
        self.device = tk.StringVar(value=saved.device)
        self.language = tk.StringVar(value=saved.language)
        self.proxy = tk.StringVar(value=saved.proxy)
        self.proxy_enabled = tk.BooleanVar(value=saved.proxy_enabled)
        self.last_audio_dir = saved.last_audio_dir
        self.preprocess_normalize = tk.BooleanVar(value=saved.preprocess_normalize)
        self.preprocess_denoise = tk.BooleanVar(value=saved.preprocess_denoise)
        self.preprocess_denoise_strength = tk.DoubleVar(value=saved.preprocess_denoise_strength)

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Load model async
        self.root.after(100, self._load_model)

    # ── UI 构建 ──────────────────────────────────────────────────────────

    def _build_ui(self):
        style = ttk.Style()
        style.configure("Header.TLabel", font=("", 10, "bold"))
        style.configure("Status.TLabel", foreground="gray")
        style.configure("Accent.TButton", font=("", 9, "bold"))
        style.configure("Dark.TFrame", background="#1e1e2e")
        style.configure("Dark.TLabel", background="#1e1e2e", foreground="#ccc")
        style.configure("Dark.TLabelframe", background="#1e1e2e", foreground="#ccc")
        style.configure("Dark.TLabelframe.Label", background="#1e1e2e", foreground="#aaa")

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        # Row 0 — Toolbar
        self._build_toolbar()
        # Row 1 — Main content (split)
        self._build_main_content()
        # Row 2 — Clip Effect Panel
        self._build_effect_panel()
        # Row 3 — TTS Compare
        self._build_tts_compare()
        # Row 4 — Log
        self._build_log()

    def _build_main_content(self):
        pw = ttk.PanedWindow(self.root, orient="horizontal")
        pw.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)

        # Left: Persona Pool
        self._build_pool(pw)

        # Right: Track Editor
        right = ttk.LabelFrame(pw, text="Track Editor", padding=4)
        pw.add(right, weight=1)

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

        ttk.Label(te_tb, text="Level:").pack(side="left", padx=(8, 2))
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

        # Fusion method
        fuse_row = ttk.Frame(right)
        fuse_row.pack(fill="x", pady=(4, 0))
        ttk.Label(fuse_row, text="Fusion:").pack(side="left")
        ttk.Radiobutton(fuse_row, text="Align", variable=self.method, value="align").pack(side="left", padx=4)
        ttk.Radiobutton(fuse_row, text="Average", variable=self.method, value="average").pack(side="left", padx=4)
        ttk.Button(fuse_row, text="Generate Fused", command=self._generate_fused,
                   style="Accent.TButton").pack(side="right", padx=4)
        ttk.Button(fuse_row, text="Split at Playhead", command=self._split_at_playhead).pack(side="right", padx=4)

    def _build_log(self):
        f = ttk.LabelFrame(self.root, text="Log", padding=4)
        f.grid(row=4, column=0, sticky="ew", padx=8, pady=(4, 8))
        self.log_text = tk.Text(f, height=5, wrap="word", state="disabled",
                                 font=("Consolas", 9), bg="#1e1e1e", fg="#d4d4d4",
                                 insertbackground="white")
        sb = ttk.Scrollbar(f, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.log_text.pack(fill="both", expand=True)

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
                    self._log(f"[Scan] Found {len(personas)} persona(s) in {AUTO_IMPORT_DIR}")
                    if stale:
                        self._log(f"[Scan] {len(stale)} persona(s) need re-processing")
                    self._rebuild_pool()
                    if self.model is not None:
                        self.model_status.configure(text=f"Ready ({self.device.get()})")
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

    def _add_track(self):
        self._track_editor.add_track()

    def _remove_track(self):
        sel = self._track_editor.get_selected_clip()
        if sel:
            self._track_editor.remove_track(sel[0])
        else:
            self._track_editor.remove_track(len(self._track_editor.tracks) - 1)

    def _add_persona_to_track(self, persona: Persona):
        sel = self._track_editor.get_selected_clip()
        track_idx = sel[0] if sel else 0
        if track_idx >= len(self._track_editor.tracks):
            track_idx = 0

        color = COLORS[self._color_idx % len(COLORS)]
        self._color_idx += 1

        clip = Clip(
            persona_name=persona.name,
            persona_original_path=persona.original_path,
            start_frame=0,
            length_frames=100,
            weight=1.0,
            fusion_level=4,
            color=color,
        )
        track = self._track_editor.tracks[track_idx]
        if track.clips:
            clip.start_frame = max(c.end_frame for c in track.clips)

        self._track_editor.add_clip(track_idx, clip)
        self._log(f"[Track] Added '{persona.display_name}' to Track {track_idx + 1}")

    def _split_at_playhead(self):
        sel = self._track_editor.get_selected_clip()
        if not sel:
            messagebox.showinfo("Split", "Select a clip first")
            return
        track_idx, clip = sel
        frame = int(self._track_editor.playhead_frame)
        self._track_editor.split_clip_at(track_idx, clip, frame)
        self._log(f"[Track] Split clip '{clip.persona_name}' at frame {frame}")

    def _on_clip_double_click(self, track_idx, clip):
        self._clip_info_label.configure(
            text=f"Selected: {clip.persona_name} | Track {track_idx + 1} | "
                 f"[{clip.start_frame}-{clip.end_frame}]")
        self._clip_weight_var.set(clip.weight)
        self._clip_level_var.set(level_display_str(clip.fusion_level))
        self._show_effect_panel(clip)

    def _on_clip_right_click(self, event, track_idx, clip):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label=f"Delete '{clip.persona_name}'",
                         command=lambda: self._delete_clip(track_idx, clip))
        menu.add_command(label="Split at Playhead",
                         command=lambda: self._track_editor.split_clip_at(
                             track_idx, clip, int(self._track_editor.playhead_frame)))
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

    def _on_clip_weight_change(self, val):
        sel = self._track_editor.get_selected_clip()
        if sel:
            sel[1].weight = float(val)
            self._track_editor._redraw()

    def _on_clip_level_change(self, event=None):
        sel = self._track_editor.get_selected_clip()
        if sel:
            sel[1].fusion_level = parse_level_from_str(self._clip_level_var.get())
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
            sd.play(audio, sr)
        except Exception as e:
            self._on_error(f"Preview failed: {e}")

    # ── Settings ──

    def _collect_settings(self):
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
