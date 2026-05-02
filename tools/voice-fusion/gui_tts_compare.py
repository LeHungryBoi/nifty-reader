"""TTS 对比播放区域 mixin"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import traceback

from gui_base import _sounddevice_available


class TtsCompareMixin:
    """VoiceFusionApp TTS 对比播放"""

    def _build_tts_compare(self, parent: tk.Widget = None):
        if parent is None:
            parent = self.root
        self._tts_compare_frame = ttk.LabelFrame(parent, text="TTS Compare (f32 vs int8)", padding=6)
        self._tts_compare_frame.pack(side="top", fill="both", expand=True)

        # Text input — click to edit, Enter to confirm, Esc to cancel
        text_row = ttk.Frame(self._tts_compare_frame)
        text_row.pack(fill="x")
        ttk.Label(text_row, text="Text:").pack(side="left")

        self._text_entry = ttk.Entry(text_row, textvariable=self.test_text)
        self._text_entry.pack(side="left", fill="x", expand=True, padx=(4, 0))
        self._text_entry_hint = ttk.Label(text_row, text="  [Enter=confirm, Esc=cancel]",
                                          style="Status.TLabel")
        self._text_entry_hint.pack(side="left")

        self._text_editing = False
        self._text_entry.bind("<FocusIn>", self._on_text_focus_in)
        self._text_entry.bind("<FocusOut>", self._on_text_focus_out)
        self._text_entry.bind("<Return>", self._on_text_confirm)
        self._text_entry.bind("<Escape>", self._on_text_cancel)

        # Buttons
        btn_row = ttk.Frame(self._tts_compare_frame)
        btn_row.pack(fill="x", pady=(4, 0))

        ttk.Label(btn_row, text="f32:", font=("", 9, "bold")).pack(side="left")
        ttk.Button(btn_row, text="▶ Play f32 (Space)", command=self._play_f32).pack(side="left", padx=2)

        ttk.Separator(btn_row, orient="vertical").pack(side="left", fill="y", padx=8)

        ttk.Label(btn_row, text="int8:", font=("", 9, "bold")).pack(side="left")
        ttk.Button(btn_row, text="▶ Play int8 (Shift+Space)", command=self._play_int8).pack(side="left", padx=2)

        ttk.Separator(btn_row, orient="vertical").pack(side="left", fill="y", padx=8)

        ttk.Button(btn_row, text="Export FuseSona", command=self._export_fusesona).pack(side="left", padx=2)

        self._tts_status = ttk.Label(btn_row, text="", style="Status.TLabel")
        self._tts_status.pack(side="right", padx=4)

    def _on_text_focus_in(self, event=None):
        """进入编辑模式：保存当前文本作为备份"""
        self._text_editing = True
        self._text_backup = self.test_text.get()

    def _on_text_focus_out(self, event=None):
        """离开编辑模式：隐藏提示"""
        self._text_editing = False
        self._text_entry_hint.configure(text="")

    def _on_text_confirm(self, event=None):
        """Enter — 确认文本，退出编辑"""
        self.root.focus_set()

    def _on_text_cancel(self, event=None):
        """Esc — 还原文本，退出编辑"""
        self.test_text.set(self._text_backup)
        self.root.focus_set()

    def _get_sample_rate(self):
        if hasattr(self.model, "sample_rate"):
            return self.model.sample_rate
        return self.model.config.mimi.sample_rate

    def _play_f32(self):
        self._generate_fused()

    def _play_int8(self):
        self._generate_int8()

    def _generate_int8(self):
        if getattr(self, 'model_int8', None) is None:
            self._log("[int8] 量化模型未加载，直接使用 f32 结果")
            self._last_int8_audio = self._last_f32_audio
            return
        if self._generating_int8:
            return
        text = self.test_text.get().strip()
        if not text:
            return

        self._generating_int8 = True
        self._log(f"Generating int8: \"{text[:50]}\"")

        def task():
            try:
                state = self._get_fused_state()
                audio = self.model_int8.generate_audio(
                    model_state=state, text_to_generate=text, copy_state=True)
                self._last_int8_audio = audio
                self.root.after(0, lambda: self._on_generated(audio, "int8"))
            except Exception as e:
                err = traceback.format_exc()
                self.root.after(0, lambda _e=e, _err=err:
                    self._on_error(f"Int8 generation failed:\n{_err}", exc=_e))
            finally:
                self.root.after(0, lambda: setattr(self, "_generating_int8", False))

        import threading
        threading.Thread(target=task, daemon=True).start()

    def _save_audio_file(self, audio, default_name: str):
        if audio is None:
            messagebox.showwarning("Warning", "No audio to save")
            return
        path = filedialog.asksaveasfilename(
            title="Save audio", defaultextension=".wav",
            initialfile=default_name,
            filetypes=[("WAV", "*.wav")])
        if not path:
            return
        try:
            sr = self._get_sample_rate()
            from pocket_tts.data.audio import stream_audio_chunks
            audio_tensor = audio.squeeze()
            stream_audio_chunks(path, (audio_tensor,), sr)
            self._log(f"Saved: {path}")
        except Exception as e:
            self._on_error(f"Save failed: {traceback.format_exc()}", exc=e)
