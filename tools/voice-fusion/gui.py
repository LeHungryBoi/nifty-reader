"""
Voice Fusion Tool — PocketTTS voice state fusion GUI.

Features:
  1. 加载模型
  2. 导入音频到语音库 (Media Bucket)
  3. 选择 2+ 个语音进行融合 (每语音独立权重)
  4. 可视化对齐与重叠 (波形 + seq_len 对齐图)
  5. 生成测试语音 + 播放 / 导出
"""

import os
import sys
import threading
import traceback
import warnings
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from dataclasses import dataclass
from pathlib import Path

# 静默 sounddevice 在 Python 3.14 上的 cffi callback 警告
warnings.filterwarnings("ignore", message=".*cffi callback.*")
warnings.filterwarnings("ignore", message=".*finished_callback_wrapper.*")

import numpy as np
import torch

# ---------------------------------------------------------------------------
# 可选依赖
# ---------------------------------------------------------------------------

try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    _matplotlib_available = True
except ImportError:
    _matplotlib_available = False

try:
    import sounddevice as sd
    _sounddevice_available = True
except ImportError:
    _sounddevice_available = False

# ---------------------------------------------------------------------------
# 路径
# ---------------------------------------------------------------------------

RUNNING_DIR = Path(os.getcwd())
CACHE_DIR = RUNNING_DIR / ".cache" / "pocket_tts"
PREPROCESS_CACHE_DIR = RUNNING_DIR / ".cache" / "preprocessed"
STATE_CACHE_DIR = RUNNING_DIR / ".cache" / "voice_states"  # voice state 缓存
AUTO_IMPORT_DIR = RUNNING_DIR / "assets" / "voices"  # 默认自动导入路径


# ---------------------------------------------------------------------------
# 代理 / 缓存
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
        utils.make_cache_directory = lambda: CACHE_DIR
    except ImportError:
        pass


_patch_cache_dir()


def _import_pocket_tts():
    from pocket_tts import TTSModel, export_model_state
    from pocket_tts.data.audio import stream_audio_chunks
    return TTSModel, export_model_state, stream_audio_chunks


# ---------------------------------------------------------------------------
# Voice Entry
# ---------------------------------------------------------------------------

@dataclass
class VoiceEntry:
    """语音库中的一个条目"""
    voice_id: int
    name: str
    audio_path: str  # 当前用于提取/预览的路径（可能指向缓存）
    original_audio_path: str = ""  # 原始文件路径（不会被 Clear Cache 清除）
    state: dict | None = None
    info: dict | None = None
    selected: bool = False
    weight: float = 1.0
    extracting: bool = False
    wave_data: np.ndarray | None = None
    wave_sr: int = 0

    def get_preview_path(self) -> str:
        """获取预览用的路径：优先原始文件，其次当前路径"""
        if self.original_audio_path and Path(self.original_audio_path).exists():
            return self.original_audio_path
        return self.audio_path


# ---------------------------------------------------------------------------
# 主窗口
# ---------------------------------------------------------------------------

class VoiceFusionApp:
    COLORS = [
        "#4FC3F7", "#81C784", "#FFB74D", "#E57373",
        "#BA68C8", "#4DD0E1", "#FFD54F", "#A1887F",
        "#90A4AE", "#F06292",
    ]

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("PocketTTS Voice Fusion Tool")
        self.root.geometry("900x700")
        self.root.minsize(640, 500)

        # State
        self.model = None
        self.voices: list[VoiceEntry] = []
        self._next_id = 0
        self.last_audio: torch.Tensor | None = None
        self._generating = False
        self._viz_timer = None
        self._play_stream = None
        self._play_audio_data = None
        self._play_sr = 0
        self._play_pos = 0
        self._play_paused = False
        self._play_source_key = None

        # Settings
        from settings import load_settings, save_settings, Settings
        self._settings_cls = Settings
        self._save_settings_fn = save_settings
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
        self.root.after(100, self._load_model)

        # Load voice library from settings
        self._load_voice_library(saved)

    # ── UI 构建 ──────────────────────────────────────────────────────────

    def _build_ui(self):
        style = ttk.Style()
        style.configure("Header.TLabel", font=("", 10, "bold"))
        style.configure("Status.TLabel", foreground="gray")
        style.configure("Accent.TButton", font=("", 10, "bold"))
        style.configure("Voice.TFrame", background="#f8f8f8")

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)

        # Row 0 — Model
        f_model = ttk.LabelFrame(self.root, text="Model", padding=8)
        f_model.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 4))
        self._build_model_panel(f_model)

        # Row 1 — Preprocessing
        f_pp = ttk.LabelFrame(self.root, text="Audio Preprocessing", padding=8)
        f_pp.grid(row=1, column=0, sticky="ew", padx=10, pady=4)
        self._build_preprocess_panel(f_pp)

        # Row 2 — Notebook: Library + Visualization (tabbed, saves space)
        nb = ttk.Notebook(self.root)
        nb.grid(row=2, column=0, sticky="nsew", padx=10, pady=4)

        tab_lib = ttk.Frame(nb)
        nb.add(tab_lib, text="Voice Library")
        self._build_library_panel(tab_lib)

        tab_viz = ttk.Frame(nb)
        nb.add(tab_viz, text="Visualization")
        self._build_viz_panel(tab_viz)

        # Row 3 — Fusion + Test (stacked vertically)
        f_ctrl = ttk.Frame(self.root)
        f_ctrl.grid(row=3, column=0, sticky="ew", padx=10, pady=4)
        self._build_fusion_panel(f_ctrl)

        # Row 4 — Log
        f_log = ttk.LabelFrame(self.root, text="Log", padding=4)
        f_log.grid(row=4, column=0, sticky="ew", padx=10, pady=(4, 10))
        self._build_log_panel(f_log)

    # ── Model ──

    def _build_model_panel(self, parent):
        row = ttk.Frame(parent)
        row.pack(fill="x")

        ttk.Label(row, text="Language:").pack(side="left")
        ttk.Combobox(row, textvariable=self.language, width=10, state="readonly",
                      values=["english", "french_24l", "german_24l",
                              "portuguese", "italian", "spanish_24l"]
                      ).pack(side="left", padx=(4, 12))

        ttk.Label(row, text="Device:").pack(side="left")
        ttk.Combobox(row, textvariable=self.device, width=8, state="readonly",
                      values=["cpu", "cuda", "mps"]
                      ).pack(side="left", padx=(4, 12))

        self.load_btn = ttk.Button(row, text="Load Model", command=self._load_model)
        self.load_btn.pack(side="left", padx=4)
        self.model_status = ttk.Label(row, text="Not loaded", style="Status.TLabel")
        self.model_status.pack(side="left", padx=8)

        proxy_row = ttk.Frame(parent)
        proxy_row.pack(fill="x", pady=(6, 0))
        ttk.Checkbutton(proxy_row, text="Proxy",
                         variable=self.proxy_enabled).pack(side="left")
        ttk.Entry(proxy_row, textvariable=self.proxy,
                   width=35).pack(side="left", padx=(4, 4))
        ttk.Label(proxy_row, text="(e.g. http://127.0.0.1:10808)",
                   style="Status.TLabel").pack(side="left")

    # ── Preprocessing ──

    def _build_preprocess_panel(self, parent):
        row = ttk.Frame(parent)
        row.pack(fill="x")
        ttk.Checkbutton(row, text="Normalize (-3dB peak)",
                         variable=self.preprocess_normalize).pack(side="left")
        ttk.Separator(row, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Checkbutton(row, text="Denoise",
                         variable=self.preprocess_denoise).pack(side="left")
        ttk.Label(row, text="Strength:").pack(side="left", padx=(8, 2))
        self.denoise_scale = ttk.Scale(
            row, from_=0.1, to=1.0, variable=self.preprocess_denoise_strength,
            orient="horizontal", length=120, command=self._on_denoise_change)
        self.denoise_scale.pack(side="left", padx=2)
        self.denoise_label = ttk.Label(row, text="0.30", width=4)
        self.denoise_label.pack(side="left")
        ttk.Separator(row, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Button(row, text="Refresh Cache",
                    command=self._refresh_pp_cache).pack(side="left", padx=2)
        self.pp_status = ttk.Label(parent, text="", style="Status.TLabel")
        self.pp_status.pack(anchor="w", pady=(4, 0))

    # ── Voice Library ──

    def _build_library_panel(self, parent):
        # Button row
        btn_row = ttk.Frame(parent)
        btn_row.pack(fill="x", pady=(0, 4))
        ttk.Button(btn_row, text="+ Add Audio...",
                    command=self._add_audio).pack(side="left", padx=2)
        ttk.Button(btn_row, text="+ Load .safetensors",
                    command=self._add_safetensors).pack(side="left", padx=2)
        self.lib_count_label = ttk.Label(btn_row, text="(empty)", style="Status.TLabel")
        self.lib_count_label.pack(side="right", padx=4)

        # Scrollable voice list — fill the tab
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        container = ttk.Frame(parent)
        container.pack(fill="both", expand=True)

        self._lib_canvas = tk.Canvas(container, highlightthickness=0, bg="#fafafa")
        self._lib_sb = ttk.Scrollbar(container, orient="vertical",
                                      command=self._lib_canvas.yview)
        self._lib_inner = ttk.Frame(self._lib_canvas)

        self._lib_inner.bind(
            "<Configure>",
            lambda e: self._lib_canvas.configure(
                scrollregion=self._lib_canvas.bbox("all")))
        self._lib_canvas.create_window((0, 0), window=self._lib_inner,
                                        anchor="nw")
        self._lib_canvas.configure(yscrollcommand=self._lib_sb.set)

        self._lib_sb.pack(side="right", fill="y")
        self._lib_canvas.pack(side="left", fill="both", expand=True)

        # Mouse wheel scrolling
        self._lib_canvas.bind("<Enter>", self._bind_mousewheel)
        self._lib_canvas.bind("<Leave>", self._unbind_mousewheel)

    def _bind_mousewheel(self, event):
        self._lib_canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self._lib_canvas.bind_all("<Button-4>", self._on_mousewheel)
        self._lib_canvas.bind_all("<Button-5>", self._on_mousewheel)

    def _unbind_mousewheel(self, event):
        self._lib_canvas.unbind_all("<MouseWheel>")
        self._lib_canvas.unbind_all("<Button-4>")
        self._lib_canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event):
        if event.num == 4:
            self._lib_canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self._lib_canvas.yview_scroll(1, "units")
        else:
            self._lib_canvas.yview_scroll(-int(event.delta / 120), "units")

    def _rebuild_library(self):
        """重建语音库列表 UI"""
        for w in self._lib_inner.winfo_children():
            w.destroy()

        for idx, entry in enumerate(self.voices):
            self._build_voice_row(self._lib_inner, entry, idx)

        selected = sum(1 for v in self.voices if v.selected)
        total = len(self.voices)
        self.lib_count_label.configure(
            text=f"{total} voice(s), {selected} selected")

    def _build_voice_row(self, parent, entry: VoiceEntry, idx: int):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=2, padx=2)

        # Color swatch
        color = self.COLORS[idx % len(self.COLORS)]
        swatch = tk.Label(row, text="  ", bg=color, width=2, relief="solid",
                           borderwidth=1)
        swatch.pack(side="left", padx=(0, 4))

        # Selection checkbox
        sel_var = tk.BooleanVar(value=entry.selected)
        ttk.Checkbutton(row, variable=sel_var,
                         command=lambda e=entry, v=sel_var: self._on_toggle(e, v)
                         ).pack(side="left")

        # Name + info
        info_frame = ttk.Frame(row)
        info_frame.pack(side="left", fill="x", expand=True, padx=6)

        name_lbl = ttk.Label(info_frame, text=entry.name,
                              font=("", 9, "bold"), anchor="w")
        name_lbl.pack(fill="x")

        if entry.extracting:
            info_text = "Extracting..."
        elif entry.state is not None and entry.info is not None:
            from fusion import format_info
            info_text = format_info(entry.info)
        elif entry.state is not None:
            info_text = "Loaded (no info)"
        else:
            info_text = "No state"
        info_lbl = ttk.Label(info_frame, text=info_text,
                              style="Status.TLabel", font=("", 8), anchor="w")
        info_lbl.pack(fill="x")

        # Weight slider
        w_frame = ttk.Frame(row)
        w_frame.pack(side="left", padx=6)
        ttk.Label(w_frame, text="w:", font=("", 8)).pack(side="left")
        w_var = tk.DoubleVar(value=entry.weight)
        w_scale = ttk.Scale(w_frame, from_=0.1, to=3.0, variable=w_var,
                             orient="horizontal", length=70,
                             command=lambda v, e=entry, vv=w_var:
                                 self._on_weight_change(e, float(v), vv))
        w_scale.pack(side="left")
        w_lbl = ttk.Label(w_frame, text=f"{entry.weight:.1f}", width=4,
                           font=("", 8))
        w_lbl.pack(side="left")

        # Remove button
        ttk.Button(row, text="x", width=3,
                    command=lambda e=entry: self._remove_voice(e)
                    ).pack(side="right", padx=2)

        # Preview button
        ttk.Button(row, text="▶", width=3,
                   command=lambda e=entry: self._preview_voice(e)
                   ).pack(side="right", padx=2)

    # ── Visualization ──

    def _build_viz_panel(self, parent):
        if _matplotlib_available:
            self._fig = Figure(figsize=(7, 6), dpi=100, facecolor="#fafafa")
            gs = self._fig.add_gridspec(
                3, 2, height_ratios=[0.8, 1.5, 0.8],
                hspace=0.50, wspace=0.30,
                left=0.08, right=0.95, top=0.95, bottom=0.06)
            self._ax_wave = self._fig.add_subplot(gs[0, :])
            self._ax_latent = self._fig.add_subplot(gs[1, 0])
            self._ax_weight = self._fig.add_subplot(gs[1, 1])
            self._ax_align = self._fig.add_subplot(gs[2, :])
            self._canvas_mpl = FigureCanvasTkAgg(self._fig, master=parent)
            self._canvas_mpl.get_tk_widget().pack(fill="both", expand=True)
            self._update_viz()
        else:
            self._viz_label = ttk.Label(
                parent,
                text="Install matplotlib for visualization:\n"
                     "pip install matplotlib",
                justify="center", style="Status.TLabel")
            self._viz_label.pack(fill="both", expand=True)

    # ── Fusion + Test ──

    def _build_fusion_panel(self, parent):
        # Fusion method (compact, single row)
        fuse_row = ttk.Frame(parent)
        fuse_row.pack(fill="x")
        ttk.Label(fuse_row, text="Fusion:", style="Header.TLabel").pack(side="left", padx=(0, 4))
        ttk.Radiobutton(fuse_row, text="Align (recommended)",
                         variable=self.method, value="align",
                         command=self._schedule_viz
                         ).pack(side="left", padx=4)
        ttk.Radiobutton(fuse_row, text="Average",
                         variable=self.method, value="average",
                         command=self._schedule_viz
                         ).pack(side="left", padx=4)
        self.fuse_info = ttk.Label(fuse_row, text="", style="Status.TLabel")
        self.fuse_info.pack(side="left", padx=8)

        # Test synthesis (compact, two rows)
        f_test = ttk.LabelFrame(parent, text="Test Synthesis", padding=6)
        f_test.pack(fill="x", pady=(4, 0))

        text_row = ttk.Frame(f_test)
        text_row.pack(fill="x")
        ttk.Label(text_row, text="Text:").pack(side="left")
        ttk.Entry(text_row, textvariable=self.test_text).pack(
            side="left", fill="x", expand=True, padx=(4, 0))

        btn_row = ttk.Frame(f_test)
        btn_row.pack(fill="x", pady=(4, 0))
        ttk.Button(btn_row, text="Generate Fused",
                    command=self._generate,
                    style="Accent.TButton").pack(side="left", padx=2)
        self.play_btn = ttk.Button(btn_row, text="Play",
                                   command=self._play_audio)
        self.play_btn.pack(side="left", padx=2)
        ttk.Button(btn_row, text="Save WAV...",
                    command=self._save_audio).pack(side="left", padx=2)
        ttk.Button(btn_row, text="Export State...",
                    command=self._save_fused_state).pack(side="left", padx=2)

    # ── Log ──

    def _build_log_panel(self, parent):
        self.log_text = tk.Text(parent, height=6, wrap="word", state="disabled",
                                 font=("Consolas", 9), bg="#1e1e1e", fg="#d4d4d4",
                                 insertbackground="white")
        sb = ttk.Scrollbar(parent, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.log_text.pack(fill="both", expand=True)

    # ── Settings ──

    def _collect_settings(self):
        # Serialize voice library (file path + metadata, NOT embedding state)
        voice_library = [{
            "name": v.name,
            "audio_path": v.audio_path,
            "original_audio_path": v.original_audio_path,
            "selected": v.selected,
            "weight": v.weight,
        } for v in self.voices]
        return self._settings_cls(
            language=self.language.get(),
            device=self.device.get(),
            proxy_enabled=self.proxy_enabled.get(),
            proxy=self.proxy.get(),
            voice_a_path="",
            voice_b_path="",
            test_text=self.test_text.get(),
            alpha=0.5,
            method=self.method.get(),
            last_audio_dir=self.last_audio_dir,
            preprocess_normalize=self.preprocess_normalize.get(),
            preprocess_denoise=self.preprocess_denoise.get(),
            preprocess_denoise_strength=self.preprocess_denoise_strength.get(),
            voice_library=voice_library,
        )

    def _on_close(self):
        self._stop_playback(reset_position=False, update_button=False)
        self._save_settings_fn(self._collect_settings(), RUNNING_DIR)
        self.root.destroy()

    # ── Log / Error ──

    def _log(self, msg: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
        self.root.update_idletasks()

    def _on_error(self, msg: str, exc: Exception | None = None):
        self.load_btn.configure(state="normal")
        self.model_status.configure(text="Error")
        self._log(f"ERROR: {msg}")
        print(f"[VoiceFusion ERROR] {msg}", file=sys.stderr)
        if exc is not None:
            traceback.print_exception(type(exc), exc, exc.__traceback__,
                                       file=sys.stderr)
        messagebox.showerror("Error", msg)

    # ── Model loading ──

    def _load_model(self):
        if self.model is not None:
            return
        proxy = self.proxy.get().strip() if self.proxy_enabled.get() else None
        if proxy:
            _apply_proxy(proxy)
            self._log(f"Proxy set: {proxy}")
        else:
            for var in ("HTTP_PROXY", "http_proxy", "HTTPS_PROXY",
                        "https_proxy", "ALL_PROXY", "all_proxy"):
                os.environ.pop(var, None)
            self._log("Proxy disabled")

        self.load_btn.configure(state="disabled")
        self.model_status.configure(
            text="Loading... (may download models on first run)")

        def task():
            try:
                TTSModel, _, _ = _import_pocket_tts()
                self.root.after(0, lambda: self.model_status.configure(
                    text="Loading model..."))
                model = TTSModel.load_model(language=self.language.get() or None)
                model = model.to(self.device.get())
                self.model = model
                self.root.after(0, self._on_model_loaded)
            except Exception as e:
                err = traceback.format_exc()
                self.root.after(0, lambda _e=e, _err=err:
                    self._on_error(f"Failed to load model:\n{_err}", exc=_e))

        threading.Thread(target=task, daemon=True).start()

    def _on_model_loaded(self):
        sr = (self.model.sample_rate
              if hasattr(self.model, "sample_rate")
              else self.model.config.mimi.sample_rate)
        self.model_status.configure(text=f"Ready ({self.device.get()}, {sr}Hz)")
        self.load_btn.configure(text="Loaded", state="disabled")
        self._log(f"Model loaded on {self.device.get()}, sample_rate={sr}Hz")

        # Re-extract states for entries that were loaded before model was ready
        pending = [v for v in self.voices if v.state is None and not v.extracting]
        for entry in pending:
            self._extract_for_entry(entry)

        # Auto-import new voices from assets/voices
        self._auto_import()

    # ── Library operations ──

    def _load_voice_library(self, saved):
        """Load voice library from settings. Entries are re-extracted if model is ready."""
        for entry_data in saved.voice_library:
            # 优先使用 original_audio_path（新格式），否则退化到 audio_path（旧格式）
            original_path = entry_data.get("original_audio_path", "")
            path = Path(original_path) if original_path else Path(entry_data.get("audio_path", ""))

            if not path.exists():
                self._log(f"[Skip] File not found: {path}")
                continue

            name = entry_data.get("name", path.stem)
            entry = VoiceEntry(
                voice_id=self._next_id,
                name=name,
                audio_path=str(path),  # 当前路径（指向缓存或原始文件）
                original_audio_path=str(path) if not original_path else original_path,  # 原始路径
                selected=entry_data.get("selected", False),
                weight=entry_data.get("weight", 1.0),
            )
            self._next_id += 1
            self.voices.append(entry)
            # Auto-extract if model is ready
            if self.model is not None:
                self._extract_for_entry(entry)
            else:
                self._log(f"[Library] '{name}' loaded (model not ready)")
        self._rebuild_library()

    def _add_audio(self):
        initialdir = (self.last_audio_dir
                      if self.last_audio_dir and Path(self.last_audio_dir).is_dir()
                      else str(RUNNING_DIR))
        path = filedialog.askopenfilename(
            title="Add audio to library",
            initialdir=initialdir,
            filetypes=[("Audio", "*.wav *.mp3 *.flac"), ("All", "*.*")],
        )
        if not path:
            return
        original_path = path  # 保存原始路径用于预览
        original_name = Path(path).stem
        self.last_audio_dir = str(Path(path).parent)
        try:
            # Auto-preprocess immediately after import so library entries are ready
            # even before model extraction starts.
            path = self._preprocess_for_extract(path, original_name)
        except Exception as e:
            self._on_error(
                f"Failed to preprocess {path}:\n{traceback.format_exc()}", exc=e)
            return
        entry = VoiceEntry(
            voice_id=self._next_id,
            name=original_name,
            audio_path=path,
            original_audio_path=original_path,
        )
        self._next_id += 1
        self.voices.append(entry)
        self._rebuild_library()

        # Auto-extract state
        if self.model is not None:
            self._extract_for_entry(entry)
        else:
            entry.extracting = False
            self._log(f"Added '{entry.name}' (model not loaded yet)")

    def _add_safetensors(self):
        initialdir = (self.last_audio_dir
                      if self.last_audio_dir and Path(self.last_audio_dir).is_dir()
                      else str(RUNNING_DIR))
        path = filedialog.askopenfilename(
            title="Load voice state",
            initialdir=initialdir,
            filetypes=[("Safetensors", "*.safetensors"), ("All", "*.*")],
        )
        if not path:
            return
        self.last_audio_dir = str(Path(path).parent)
        try:
            from fusion import load_state, get_state_info, format_info
            state = load_state(path)
            info = get_state_info(state)
            entry = VoiceEntry(
                voice_id=self._next_id,
                name=Path(path).stem,
                audio_path=path,
                state=state,
                info=info,
            )
            self._next_id += 1
            self.voices.append(entry)
            self._rebuild_library()
            self._schedule_viz()
            self._log(f"Loaded '{entry.name}' from .safetensors — {format_info(info)}")
        except Exception as e:
            self._on_error(
                f"Failed to load {path}:\n{traceback.format_exc()}", exc=e)

    def _auto_import(self):
        r"""自动从 assets/voices 及其子文件夹导入所有音频文件"""
        import glob

        # 自动创建目录（如果不存在）
        AUTO_IMPORT_DIR.mkdir(parents=True, exist_ok=True)

        # 收集所有音频文件（递归）
        audio_patterns = ["*.wav", "*.mp3", "*.flac"]
        audio_files = []
        for pattern in audio_patterns:
            audio_files.extend(AUTO_IMPORT_DIR.glob(f"**/{pattern}"))

        if not audio_files:
            messagebox.showinfo("Auto Import", f"No audio files found in:\n{AUTO_IMPORT_DIR}")
            return

        # 获取已存在的路径（用于去重）
        existing_paths = {v.original_audio_path for v in self.voices if v.original_audio_path}

        added = 0
        skipped = 0
        for path in sorted(audio_files):
            if str(path) in existing_paths:
                skipped += 1
                continue

            original_name = path.stem
            try:
                # 预处理（使用缓存）
                processed_path = self._preprocess_for_extract(str(path), original_name)
            except Exception as e:
                self._log(f"[Auto Import] {path.name}: preprocess failed — {e}")
                continue

            entry = VoiceEntry(
                voice_id=self._next_id,
                name=original_name,
                audio_path=processed_path,
                original_audio_path=str(path),
            )
            self._next_id += 1
            self.voices.append(entry)

            # 自动提取（如果模型已加载）
            if self.model is not None:
                self._extract_for_entry(entry)

            added += 1

        self._rebuild_library()
        self._log(f"[Auto Import] Added {added}, skipped {skipped} (from {AUTO_IMPORT_DIR})")
        if added > 0:
            self.pp_status.configure(text=f"Auto-imported {added} voice(s)")

    def _remove_voice(self, entry: VoiceEntry):
        self.voices = [v for v in self.voices if v.voice_id != entry.voice_id]
        self._rebuild_library()
        self._schedule_viz()

    def _on_toggle(self, entry: VoiceEntry, var: tk.BooleanVar):
        entry.selected = var.get()
        self._rebuild_library()
        self._schedule_viz()
        self._update_fuse_info()

    def _on_weight_change(self, entry: VoiceEntry, val: float, var: tk.DoubleVar):
        entry.weight = val
        # Update label in current row (find it by scanning children)
        for row in self._lib_inner.winfo_children():
            # Find the weight label in this row
            for child in row.winfo_children():
                if isinstance(child, ttk.Frame):
                    for sub in child.winfo_children():
                        if isinstance(sub, ttk.Label) and sub.cget("width") == "4":
                            sub.configure(text=f"{val:.1f}")
        self._schedule_viz()
        self._update_fuse_info()

    def _on_denoise_change(self, _=None):
        self.denoise_label.configure(
            text=f"{self.preprocess_denoise_strength.get():.2f}")

    def _clear_pp_cache(self):
        from preprocess import clear_cache
        count = clear_cache(PREPROCESS_CACHE_DIR)
        self._log(f"Preprocess cache cleared: {count} files removed")
        self.pp_status.configure(text=f"Cache cleared ({count} files)")

    def _refresh_pp_cache(self):
        """Clear cache, re-preprocess all entries, and check for new files in assets/voices."""
        from preprocess import clear_cache
        count = clear_cache(PREPROCESS_CACHE_DIR)
        self._log(f"Cache cleared ({count} files), re-processing...")

        # Re-preprocess all entries with original audio
        requeue = []
        for entry in self.voices:
            if entry.original_audio_path and Path(entry.original_audio_path).exists():
                requeue.append(entry)
            else:
                self._log(f"[Skip] {entry.name}: no original audio path")

        if not requeue:
            self.pp_status.configure(text="No entries to refresh")

        for entry in requeue:
            try:
                new_path = self._preprocess_for_extract(entry.original_audio_path, entry.name)
                entry.audio_path = new_path  # 更新为新的缓存路径
                entry.wave_data = None  # 清除波形缓存
                entry.wave_sr = 0
                # 重新提取 state
                entry.state = None
                entry.info = None
                if self.model is not None:
                    self._extract_for_entry(entry)
                else:
                    self._log(f"[Refresh] {entry.name} queued (model not ready)")
            except Exception as e:
                self._log(f"[Error] {entry.name}: {e}")

        # Also check for new files in assets/voices
        self._auto_import()

        self._rebuild_library()
        self.pp_status.configure(text=f"Refreshed {len(requeue)} entries")

    # ── Extract voice state ──

    def _state_cache_path(self, audio_path: str) -> Path:
        """计算 voice state 缓存文件路径（基于音频文件 hash）。"""
        from preprocess import _file_hash
        h = _file_hash(Path(audio_path))
        STATE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        return STATE_CACHE_DIR / f"{h}.safetensors"

    def _try_load_state_cache(self, entry: VoiceEntry) -> dict | None:
        """尝试从缓存加载 voice state，失败返回 None。"""
        cache_path = self._state_cache_path(entry.audio_path)
        if not cache_path.exists():
            return None
        try:
            from fusion import load_state, get_state_info
            state = load_state(cache_path)
            info = get_state_info(state)
            # 验证缓存完整性
            if not info["details"]:
                cache_path.unlink()
                return None
            self._log(f"[{entry.name}] State cache hit")
            return state
        except Exception:
            cache_path.unlink(missing_ok=True)
            return None

    def _save_state_cache(self, entry: VoiceEntry):
        """将 voice state 保存到缓存。"""
        if entry.state is None:
            return
        try:
            from fusion import save_state
            cache_path = self._state_cache_path(entry.audio_path)
            save_state(entry.state, cache_path)
        except Exception:
            pass

    def _extract_for_entry(self, entry: VoiceEntry):
        if self.model is None:
            messagebox.showwarning("Warning", "Please load model first")
            return
        entry.extracting = True
        self._rebuild_library()

        def task():
            try:
                actual_path = self._preprocess_for_extract(entry.audio_path, entry.name)
                ap = Path(actual_path)

                # 尝试从缓存加载
                cached_state = self._try_load_state_cache(entry)
                if cached_state is not None:
                    self.root.after(0, lambda: self._on_extracted(entry, cached_state))
                    return

                # 缓存未命中，执行提取
                if ap.stat().st_size == 0:
                    raise FileNotFoundError(f"Preprocessed file is empty: {ap}")
                try:
                    import wave
                    with wave.open(str(ap), "rb") as wf:
                        ch = wf.getnchannels()
                        rate = wf.getframerate()
                        frames = wf.getnframes()
                        self._log(f"[{entry.name}] WAV OK: {ch}ch, {rate}Hz, "
                                  f"{frames/rate:.1f}s")
                except EOFError:
                    raise EOFError(
                        f"Corrupt WAV: {ap} ({ap.stat().st_size} bytes)")

                state = self.model.get_state_for_audio_prompt(
                    str(ap), truncate=True)
                # 保存到缓存
                entry.state = state
                self._save_state_cache(entry)
                self.root.after(0, lambda: self._on_extracted(entry, state))
            except Exception as e:
                err = traceback.format_exc()
                self.root.after(0, lambda _e=e, _err=err:
                    self._on_error(f"Failed to extract '{entry.name}':\n{_err}",
                                   exc=_e))
                entry.extracting = False
                self.root.after(0, self._rebuild_library)

        threading.Thread(target=task, daemon=True).start()

    def _preprocess_for_extract(self, audio_path: str, tag: str) -> str:
        from preprocess import preprocess_audio, format_detect, format_actions
        pp_path, report = preprocess_audio(
            input_path=audio_path,
            cache_dir=PREPROCESS_CACHE_DIR,
            normalize=self.preprocess_normalize.get(),
            denoise=self.preprocess_denoise.get(),
            denoise_strength=self.preprocess_denoise_strength.get(),
        )
        detect = report["detect"]
        actions = report["actions"]
        det_str = format_detect(detect)
        act_str = format_actions(actions)

        if report["cached"]:
            self._log(f"[{tag}] Preprocess cache hit: {Path(pp_path).name}")
            self.pp_status.configure(text=f"{Path(audio_path).name} -> cache hit")
        elif not actions:
            self._log(f"[{tag}] Audio OK: {det_str}")
            self.pp_status.configure(
                text=f"{Path(audio_path).name}: {det_str}")
        else:
            self._log(f"[{tag}] Preprocessed: {det_str} -> {act_str}")
            self.pp_status.configure(
                text=f"{Path(audio_path).name}: {act_str}")
        return str(pp_path)

    def _on_extracted(self, entry: VoiceEntry, state: dict):
        from fusion import get_state_info, format_info
        entry.state = state
        entry.info = get_state_info(state)
        entry.extracting = False
        self._rebuild_library()
        self._schedule_viz()
        self._update_fuse_info()
        self._log(f"Extracted '{entry.name}' — {format_info(entry.info)}")

    # ── Visualization ──

    def _schedule_viz(self):
        if not _matplotlib_available:
            return
        if self._viz_timer is not None:
            self.root.after_cancel(self._viz_timer)
        self._viz_timer = self.root.after(150, self._update_viz)

    def _update_viz(self):
        self._viz_timer = None
        if not _matplotlib_available:
            return

        selected = [v for v in self.voices if v.selected and v.state is not None]

        self._ax_wave.clear()
        self._ax_latent.clear()
        self._ax_weight.clear()
        self._ax_align.clear()

        if len(selected) < 2:
            for ax, title in [
                (self._ax_wave, ""),
                (self._ax_latent, "Latent Space"),
                (self._ax_weight, ""),
                (self._ax_align, ""),
            ]:
                ax.set_xticks([])
                ax.set_yticks([])
            self._ax_latent.set_title(
                "Select 2+ voices with extracted states",
                fontsize=10, color="gray")
            self._canvas_mpl.draw_idle()
            return

        total_w = sum(v.weight for v in selected)
        norm_weights = [v.weight / total_w for v in selected]

        # ── Top: Waveforms ──
        self._ax_wave.set_title("Waveforms", fontsize=10, fontweight="bold")
        for i, v in enumerate(selected):
            self._load_waveform(v)
            color = self.COLORS[self.voices.index(v) % len(self.COLORS)]
            alpha = max(0.3, min(1.0, v.weight / total_w * len(selected) * 0.6))
            if v.wave_data is not None:
                self._ax_wave.plot(
                    v.wave_data, label=f"{v.name} (w={v.weight:.1f})",
                    color=color, alpha=alpha, linewidth=0.5)
            else:
                self._ax_wave.text(
                    0.5, 1 - (i + 0.5) / len(selected),
                    f"{v.name}: no waveform",
                    transform=self._ax_wave.transAxes, ha="center",
                    fontsize=8, color="gray")
        if any(v.wave_data is not None for v in selected):
            self._ax_wave.legend(fontsize=7, loc="upper right")

        # ── Middle-left: Latent Space Heatmap ──
        self._ax_latent.set_title("Latent Space (1st layer, mean K/V)",
                                   fontsize=10, fontweight="bold")
        # Extract latent summaries for each voice
        latents = []
        for v in selected:
            lat = self._extract_latent_summary(v.state, target_len=0)
            latents.append(lat)
        target_lat_len = max(
            lat.shape[0] for lat in latents if lat is not None) if any(latents) else 0

        # Resample all to target_lat_len and compute fused
        resampled = []
        for lat in latents:
            if lat is None:
                resampled.append(None)
                continue
            if lat.shape[0] != target_lat_len:
                x_old = np.linspace(0, 1, lat.shape[0])
                x_new = np.linspace(0, 1, target_lat_len)
                lat = np.interp(x_new, x_old, lat)
            resampled.append(lat)

        # Build heatmap data: rows = voices + fused result
        names_lat = [v.name for v in selected]
        colors_lat = [self.COLORS[self.voices.index(v) % len(self.COLORS)]
                      for v in selected]

        # Compute fused weighted result
        fused_lat = np.zeros(target_lat_len)
        for lat, nw in zip(resampled, norm_weights):
            if lat is not None:
                fused_lat += nw * lat

        all_rows = []
        all_labels = []
        all_colors = []
        for i, (lat, nm, cl, v) in enumerate(
                zip(resampled, names_lat, colors_lat, selected)):
            if lat is not None:
                all_rows.append(lat)
                all_labels.append(f"{nm} (w={v.weight:.1f})")
                all_colors.append(cl)
        all_rows.append(fused_lat)
        all_labels.append("FUSED")
        all_colors.append("#FF6B6B")

        if all_rows:
            heatmap_data = np.array(all_rows)
            im = self._ax_latent.imshow(
                heatmap_data, aspect="auto", cmap="RdBu_r",
                interpolation="nearest")
            self._ax_latent.set_yticks(range(len(all_labels)))
            self._ax_latent.set_yticklabels(all_labels, fontsize=7)
            self._ax_latent.set_xlabel("time step (resampled)", fontsize=8)

            # Add color indicators on the left
            for i, c in enumerate(all_colors):
                self._ax_latent.axhline(y=i, color=c, linewidth=3, alpha=0.7)

        # ── Middle-right: Weight Distribution ──
        self._ax_weight.set_title("Weight Distribution", fontsize=10,
                                   fontweight="bold")
        y_pos_w = list(range(len(selected) - 1, -1, -1))
        bars = self._ax_weight.barh(
            y_pos_w, [v.weight for v in selected],
            color=colors_lat, alpha=0.8, height=0.5)
        # Show normalized percentage
        for yp, nw, w in zip(y_pos_w, norm_weights, [v.weight for v in selected]):
            self._ax_weight.text(
                w + 0.05, yp, f" {nw:.0%}",
                va="center", fontsize=8)
        self._ax_weight.set_yticks(y_pos_w)
        self._ax_weight.set_yticklabels(names_lat, fontsize=7)
        self._ax_weight.set_xlabel("weight", fontsize=8)
        self._ax_weight.axvline(x=total_w / len(selected), color="gray",
                                 linestyle="--", linewidth=0.8, alpha=0.5)
        self._ax_weight.text(
            total_w / len(selected), len(selected) - 0.3,
            "avg", ha="center", fontsize=7, color="gray")

        # ── Bottom: Alignment bars ──
        self._ax_align.set_title("Seq Length Alignment", fontsize=10,
                                  fontweight="bold")

        seq_lens = []
        for v in selected:
            if v.info and v.info["seq_lengths"]:
                seq_lens.append(max(v.info["seq_lengths"]))
            else:
                seq_lens.append(0)
        target_len = max(seq_lens) if seq_lens else 0

        names = [v.name for v in selected]
        colors = [self.COLORS[self.voices.index(v) % len(self.COLORS)]
                  for v in selected]
        y_pos = list(range(len(names) - 1, -1, -1))

        # Raw bars
        bars = self._ax_align.barh(y_pos, seq_lens, color=colors,
                                    alpha=0.5, height=0.4, label="Original")
        for yp, sl, nm in zip(y_pos, seq_lens, names):
            self._ax_align.text(sl + 1, yp, f" {sl}", va="center",
                                fontsize=8)

        # Target bar (outline)
        self._ax_align.barh(
            [y - 0.4 for y in y_pos], [target_len] * len(names),
            color="none", edgecolor="gray", linewidth=1.5,
            linestyle="--", height=0.4, label=f"Target ({target_len})")

        self._ax_align.set_yticks([y - 0.2 for y in y_pos])
        self._ax_align.set_yticklabels(names, fontsize=8)
        self._ax_align.set_xlabel("seq_len", fontsize=8)
        self._ax_align.legend(fontsize=7, loc="lower right")

        self._canvas_mpl.draw_idle()

    def _load_waveform(self, entry: VoiceEntry):
        if entry.wave_data is not None:
            return
        try:
            import soundfile as sf
            data, sr = sf.read(entry.audio_path)
            if data.ndim > 1:
                data = data[:, 0]
            entry.wave_data = data.astype(np.float32)
            entry.wave_sr = sr
        except Exception:
            pass

    def _extract_latent_summary(self, state: dict, target_len: int = 0) -> np.ndarray | None:
        """从 voice state 的第一个 module 提取 latent 摘要。

        对 cache 取 mean(heads, dim) → [2, seq_len]（K/V 均值），
        再取 mean(K, V) → [seq_len]。
        可选 resample 到 target_len。
        """
        if not state:
            return None
        try:
            first_key = next(iter(state))
            cache = state[first_key]["cache"]  # [2, 1, seq_len, heads, dim]
            # mean across batch(1), heads(3), dim(4) → [2, seq_len]
            summary = cache.float().mean(dim=(1, 3, 4)).cpu().numpy()
            # average K and V → [seq_len]
            summary = summary.mean(axis=0)

            if target_len > 0 and summary.shape[0] != target_len:
                x_old = np.linspace(0, 1, summary.shape[0])
                x_new = np.linspace(0, 1, target_len)
                summary = np.interp(x_new, x_old, summary)
            return summary
        except Exception:
            return None

    # ── Fusion info ──

    def _update_fuse_info(self):
        selected = [v for v in self.voices if v.selected and v.state is not None]
        if len(selected) < 2:
            self.fuse_info.configure(text="")
            return

        all_lens = set()
        for v in selected:
            if v.info and v.info["seq_lengths"]:
                all_lens.update(v.info["seq_lengths"])

        total_w = sum(v.weight for v in selected)
        weights_str = ", ".join(f"{v.name}={v.weight:.1f}" for v in selected)

        if len(all_lens) > 1:
            self.fuse_info.configure(
                text=f"{len(selected)} voices, seq_len mismatch {sorted(all_lens)} "
                     f"— will align | {weights_str}",
                foreground="orange")
        else:
            self.fuse_info.configure(
                text=f"{len(selected)} voices, seq_len={sorted(all_lens)}, "
                     f"total_w={total_w:.1f} | {weights_str}",
                foreground="gray")

    # ── Fusion ──

    def _get_fused_state(self) -> dict:
        selected = [v for v in self.voices if v.selected and v.state is not None]
        if len(selected) < 2:
            raise ValueError(f"Need 2+ voices with state, got {len(selected)}")

        from fusion import fuse_voice_states_multi
        return fuse_voice_states_multi(
            states=[v.state for v in selected],
            weights=[v.weight for v in selected],
            method=self.method.get(),
        )

    # ── Generate ──

    def _generate(self):
        if self.model is None:
            messagebox.showwarning("Warning", "Please load model first")
            return
        selected = [v for v in self.voices if v.selected and v.state is not None]
        if len(selected) < 2:
            messagebox.showwarning("Warning",
                f"Select 2+ voices with extracted states (currently {len(selected)})")
            return
        if self._generating:
            return

        text = self.test_text.get().strip()
        if not text:
            messagebox.showwarning("Warning", "Please enter test text")
            return

        self._generating = True
        names = "+".join(v.name for v in selected)
        self._log(f"Generating (fused {names}): \"{text[:50]}\"")

        def task():
            try:
                state = self._get_fused_state()
                audio = self.model.generate_audio(
                    model_state=state,
                    text_to_generate=text,
                    copy_state=True,
                )
                self.last_audio = audio
                self.root.after(0, lambda: self._on_generated(audio))
            except Exception as e:
                err = traceback.format_exc()
                self.root.after(0, lambda _e=e, _err=err:
                    self._on_error(f"Generation failed:\n{_err}", exc=_e))
            finally:
                self.root.after(0, lambda: setattr(self, "_generating", False))

        threading.Thread(target=task, daemon=True).start()

    def _on_generated(self, audio: torch.Tensor):
        sr = (self.model.sample_rate
              if hasattr(self.model, "sample_rate")
              else self.model.config.mimi.sample_rate)
        duration = audio.shape[-1] / sr
        self._log(f"Generated: {duration:.1f}s, {sr}Hz")
        self._play_audio()

    # ── Playback ──

    def _play_audio(self):
        if self.last_audio is None:
            messagebox.showwarning("Warning", "No audio generated yet")
            return
        if not _sounddevice_available:
            messagebox.showwarning("Warning",
                "sounddevice not installed. Install with: pip install sounddevice\n"
                "Or use 'Save WAV' to save and play externally.")
            return
        audio = self.last_audio.squeeze().cpu().numpy().astype(np.float32)
        sr = (self.model.sample_rate
              if hasattr(self.model, "sample_rate")
              else self.model.config.mimi.sample_rate)
        try:
            self._toggle_playback(
                audio=audio,
                sr=sr,
                source_key=("generated",),
                pause_log="Playback paused",
            )
        except Exception as e:
            print(f"[VoiceFusion ERROR] Playback failed:\n"
                  f"{traceback.format_exc()}", file=sys.stderr)
            messagebox.showerror("Playback Error", str(e))

    def _toggle_playback(self, audio: np.ndarray, sr: int, source_key, pause_log: str):
        # If currently playing the same source, pause.
        if (
            self._play_stream is not None
            and self._play_stream.active
            and self._play_source_key == source_key
        ):
            self._play_paused = True
            self._stop_playback(reset_position=False, update_button=True)
            self._log(pause_log)
            return

        # If source changed, load new buffer from start.
        if self._play_source_key != source_key:
            self._play_audio_data = audio
            self._play_sr = sr
            self._play_pos = 0
            self._play_source_key = source_key
        else:
            # Same source but maybe resumed after stop; refresh on shape/sr mismatch.
            if (
                self._play_audio_data is None
                or self._play_sr != sr
                or len(self._play_audio_data) != len(audio)
            ):
                self._play_audio_data = audio
                self._play_sr = sr
                self._play_pos = 0

        self._start_or_resume_playback()

    def _start_or_resume_playback(self):
        if self._play_audio_data is None or self._play_sr <= 0:
            return
        if self._play_pos >= len(self._play_audio_data):
            self._play_pos = 0

        def callback(outdata, frames, _time, _status):
            if self._play_audio_data is None:
                outdata.fill(0)
                raise sd.CallbackStop
            end = min(self._play_pos + frames, len(self._play_audio_data))
            chunk = self._play_audio_data[self._play_pos:end]
            outdata[: len(chunk), 0] = chunk
            if len(chunk) < frames:
                outdata[len(chunk):, 0] = 0
            self._play_pos = end
            if self._play_pos >= len(self._play_audio_data):
                raise sd.CallbackStop

        self._stop_playback(reset_position=False, update_button=False)
        self._play_stream = sd.OutputStream(
            samplerate=self._play_sr,
            channels=1,
            dtype="float32",
            callback=callback,
            finished_callback=lambda: self.root.after(0, self._on_playback_finished),
        )
        self._play_stream.start()
        self._play_paused = False
        self.play_btn.configure(text="Pause")

    def _on_playback_finished(self):
        was_paused = self._play_paused
        self._stop_playback(reset_position=not was_paused, update_button=True)
        if not was_paused:
            self._play_pos = 0

    def _stop_playback(self, reset_position: bool, update_button: bool):
        stream = self._play_stream
        self._play_stream = None
        if stream is not None:
            try:
                stream.stop()
            except Exception:
                pass
            try:
                stream.close()
            except Exception:
                pass
        if reset_position:
            self._play_pos = 0
            self._play_paused = False
            self._play_source_key = None
        if update_button and hasattr(self, "play_btn"):
            self.play_btn.configure(text="Play")

    def _preview_voice(self, entry: VoiceEntry):
        """Preview the original audio file of a voice entry."""
        if not _sounddevice_available:
            messagebox.showwarning("Warning",
                "sounddevice not installed. Install with: pip install sounddevice\n"
                "Or use 'Save WAV' to save and play externally.")
            return
        path = Path(entry.get_preview_path())
        if not path.exists():
            messagebox.showwarning("Warning", f"File not found: {path}")
            return
        try:
            import soundfile as sf
            data, sr = sf.read(path)
            if data.ndim > 1:
                data = data[:, 0]
            audio = data.astype(np.float32)
            self._toggle_playback(
                audio=audio,
                sr=sr,
                source_key=("preview", entry.voice_id),
                pause_log=f"[Preview] paused: {entry.name}",
            )
            if not self._play_paused:
                self._log(f"[Preview] {entry.name}")
        except Exception as e:
            self._on_error(f"Failed to preview '{entry.name}':\n{traceback.format_exc()}", exc=e)

    # ── Save ──

    def _save_audio(self):
        if self.last_audio is None:
            messagebox.showwarning("Warning", "No audio generated yet")
            return
        path = filedialog.asksaveasfilename(
            title="Save audio",
            defaultextension=".wav",
            initialdir=str(RUNNING_DIR),
            initialfile="fused_voice_test.wav",
            filetypes=[("WAV", "*.wav")],
        )
        if not path:
            return
        try:
            sr = (self.model.sample_rate
                  if hasattr(self.model, "sample_rate")
                  else self.model.config.mimi.sample_rate)
            from pocket_tts.data.audio import stream_audio_chunks
            audio_tensor = self.last_audio.squeeze()

            def chunk_gen():
                yield audio_tensor
            stream_audio_chunks(path, chunk_gen(), sr)
            self._log(f"Audio saved: {path}")
        except Exception as e:
            self._on_error(f"Failed to save audio:\n{traceback.format_exc()}",
                           exc=e)

    def _save_fused_state(self):
        selected = [v for v in self.voices if v.selected and v.state is not None]
        if len(selected) < 2:
            messagebox.showwarning("Warning",
                "Select 2+ voices with extracted states")
            return

        path = filedialog.asksaveasfilename(
            title="Save fused voice state",
            defaultextension=".safetensors",
            initialdir=str(RUNNING_DIR),
            initialfile="fused_voice.safetensors",
            filetypes=[("Safetensors", "*.safetensors")],
        )
        if not path:
            return

        try:
            from fusion import save_state, get_state_info, format_info
            fused = self._get_fused_state()
            save_state(fused, path)
            info = get_state_info(fused)
            self._log(f"Fused state saved: {path} — {format_info(info)}")
        except Exception as e:
            self._on_error(f"Failed to save:\n{traceback.format_exc()}", exc=e)


def main():
    root = tk.Tk()
    app = VoiceFusionApp(root)

    root.update_idletasks()
    w = root.winfo_width()
    h = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (w // 2)
    y = (root.winfo_screenheight() // 2) - (h // 2)
    root.geometry(f"+{x}+{y}")

    root.mainloop()


if __name__ == "__main__":
    main()
