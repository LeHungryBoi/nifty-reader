"""TTS 对比播放区域 mixin"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import traceback


class TtsCompareMixin:
    """VoiceFusionApp TTS 对比播放"""

    def _build_tts_compare(self):
        f = ttk.LabelFrame(self.root, text="TTS Compare (f32 vs int8)", padding=6)
        f.grid(row=3, column=0, sticky="ew", padx=8, pady=4)

        # Text input — click to edit, Enter to confirm, Esc to cancel
        text_row = ttk.Frame(f)
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
        btn_row = ttk.Frame(f)
        btn_row.pack(fill="x", pady=(4, 0))

        ttk.Label(btn_row, text="f32:", font=("", 9, "bold")).pack(side="left")
        ttk.Button(btn_row, text="▶ Play f32", command=self._play_f32).pack(side="left", padx=2)
        ttk.Button(btn_row, text="Save f32", command=self._save_f32).pack(side="left", padx=2)

        ttk.Separator(btn_row, orient="vertical").pack(side="left", fill="y", padx=8)

        ttk.Label(btn_row, text="int8:", font=("", 9, "bold")).pack(side="left")
        ttk.Button(btn_row, text="▶ Play int8", command=self._play_int8).pack(side="left", padx=2)
        ttk.Button(btn_row, text="Save int8", command=self._save_int8).pack(side="left", padx=2)

        ttk.Separator(btn_row, orient="vertical").pack(side="left", fill="y", padx=8)

        ttk.Button(btn_row, text="Save State", command=self._save_fused_state).pack(side="left", padx=2)

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
        current_text = self.test_text.get().strip()
        if self._last_f32_audio is None or current_text != getattr(self, '_last_generated_text', ''):
            self._generate_fused()
            return
        if not _sounddevice_available:
            messagebox.showwarning("Warning", "Install sounddevice for playback")
            return
        import numpy as np
        import sounddevice as sd
        audio = self._last_f32_audio.squeeze().cpu().numpy().astype(np.float32)
        sr = self._get_sample_rate()
        self._tts_status.configure(text="Playing f32...")
        try:
            from audio_duck import AudioDuck
            AudioDuck().duck_for_playback()
            sd.play(audio, sr)
        except Exception as e:
            self._on_error(f"Playback failed: {e}")

    def _play_int8(self):
        if self._last_int8_audio is None:
            self._generate_int8()
            return
        if not _sounddevice_available:
            messagebox.showwarning("Warning", "Install sounddevice for playback")
            return
        import numpy as np
        import sounddevice as sd
        audio = self._last_int8_audio.squeeze().cpu().numpy().astype(np.float32)
        sr = self._get_sample_rate()
        self._tts_status.configure(text="Playing int8...")
        try:
            from audio_duck import AudioDuck
            AudioDuck().duck_for_playback()
            sd.play(audio, sr)
        except Exception as e:
            self._on_error(f"Playback failed: {e}")

    def _generate_int8(self):
        self._log("[int8] Quantized model not yet loaded. Using f32 model as fallback.")
        self._last_int8_audio = self._last_f32_audio
        self._play_int8()

    def _save_f32(self):
        self._save_audio_file(self._last_f32_audio, "fused_f32.wav")

    def _save_int8(self):
        self._save_audio_file(self._last_int8_audio, "fused_int8.wav")

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
            self._on_error(f"Save failed:\n{traceback.format_exc()}", exc=e)


# Late import to avoid circular
from gui_base import _sounddevice_available
