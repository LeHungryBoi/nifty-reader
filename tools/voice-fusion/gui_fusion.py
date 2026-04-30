"""融合/生成逻辑 mixin"""

import hashlib
import threading
import time
import traceback
from pathlib import Path
from typing import Optional

from tkinter import messagebox, simpledialog

from theme import THEME
import tkinter as tk
from tkinter import ttk

from persona import Persona
from track_editor import Clip
from level_extractor import LevelExtractor, save_level_features
from fusion import fuse_voice_states_multi, save_state, load_state, get_state_info, format_info
from preset import save_preset, load_preset, list_presets, save_fusesona, PresetData, FuseSonaMeta, ClipData
from gui_base import RUNNING_DIR, _get_np, PREPROCESS_CACHE_DIR


class FusionMixin:
    """VoiceFusionApp 融合/生成逻辑"""

    def _generate_fused(self):
        if self.model is None:
            messagebox.showwarning("Warning", "Load model first")
            return
        if self._generating:
            return

        text = self.test_text.get().strip()
        if not text:
            messagebox.showwarning("Warning", "Enter test text")
            return

        clips = self._track_editor.get_all_clips()
        if not clips:
            messagebox.showwarning("Warning", "Add clips to tracks first")
            return

        self._generating = True
        self._log(f"Generating fused audio (f32): \"{text[:50]}\"")

        def task():
            try:
                state = self._get_fused_state()
                audio = self.model.generate_audio(
                    model_state=state, text_to_generate=text, copy_state=True)
                self._last_f32_audio = audio
                self.root.after(0, lambda: self._on_generated(audio, "f32"))
            except Exception as e:
                err = traceback.format_exc()
                self.root.after(0, lambda _e=e, _err=err:
                    self._on_error(f"Generation failed:\n{_err}", exc=_e))
            finally:
                self.root.after(0, lambda: setattr(self, "_generating", False))

        threading.Thread(target=task, daemon=True).start()

    def _on_generated(self, audio, variant: str = "f32"):
        import numpy as np
        sr = self._get_sample_rate()
        duration = audio.shape[-1] / sr
        self._log(f"Generated ({variant}): {duration:.1f}s, {sr}Hz")
        self._tts_status.configure(text=f"{variant}: {duration:.1f}s")
        if variant == "f32":
            self._play_f32()
        elif variant == "int8":
            self._play_int8()

    def _get_fused_state(self) -> dict:
        all_clips = self._track_editor.get_all_clips()
        if not all_clips:
            raise ValueError("No clips on tracks")

        states = []
        weights = []

        for track_idx, clip in all_clips:
            persona = self._find_persona_by_path(clip.persona_original_path)

            if persona and clip.effect.has_custom_effects():
                processed_path = persona.get_derived_path(1)
                if processed_path.exists():
                    try:
                        from preprocess import apply_clip_effects
                        effect_path, actions = apply_clip_effects(
                            processed_path, clip.effect.to_dict(),
                            persona.get_effect_cache_dir())
                        if actions:
                            self._log(f"[Effect] {persona.display_name}: {', '.join(actions)}")
                    except Exception:
                        effect_path = processed_path
                else:
                    effect_path = processed_path
                state = self._load_persona_state_from_audio(effect_path, clip.fusion_level)
                if state is None and self.model:
                    try:
                        self._extract_from_audio_with_model(effect_path)
                        state = self._load_persona_state_from_audio(effect_path, clip.fusion_level)
                    except Exception:
                        pass
            else:
                state = self._load_persona_state(clip.persona_original_path, clip.fusion_level)
                if state is None:
                    if persona and self.model:
                        try:
                            self._extract_persona_levels(persona)
                            state = self._load_persona_state(clip.persona_original_path, clip.fusion_level)
                        except Exception:
                            pass

            if state is not None:
                states.append(state)
                weights.append(clip.weight)

        if not states:
            raise ValueError("No valid voice states. Ensure personas are extracted.")

        return fuse_voice_states_multi(
            states=states, weights=weights, method=self.method.get())

    def _load_persona_state(self, original_path: str, level: int) -> Optional[dict]:
        persona = self._find_persona_by_path(original_path)
        if persona is None:
            return None

        if level == 7:
            try:
                processed_path = persona.get_derived_path(1)
                if not processed_path.exists():
                    return None
                h = hashlib.sha256()
                with open(processed_path, "rb") as f:
                    for chunk in iter(lambda: f.read(1 << 20), b""):
                        h.update(chunk)
                cache_key = h.hexdigest()[:16]
                cache_dir = RUNNING_DIR / ".cache" / "voice_states"
                cache_path = cache_dir / f"{cache_key}.safetensors"
                if cache_path.exists():
                    return load_state(cache_path)
            except Exception:
                pass
        return None

    def _load_persona_state_from_audio(self, audio_path, level: int) -> Optional[dict]:
        if level != 7:
            return None
        try:
            h = hashlib.sha256()
            with open(audio_path, "rb") as f:
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    h.update(chunk)
            cache_key = h.hexdigest()[:16]
            cache_dir = RUNNING_DIR / ".cache" / "voice_states"
            cache_path = cache_dir / f"{cache_key}.safetensors"
            if cache_path.exists():
                return load_state(cache_path)
        except Exception:
            pass
        return None

    def _extract_from_audio_with_model(self, audio_path: Path):
        if self.model is None or not audio_path.exists():
            return
        extractor = LevelExtractor(self.model)
        features = extractor.extract_all_levels(str(audio_path), copy_state=False)
        if features:
            h = hashlib.sha256()
            with open(audio_path, "rb") as f:
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    h.update(chunk)
            cache_key = h.hexdigest()[:16]
            cache_dir = RUNNING_DIR / ".cache" / "voice_states"
            cache_dir.mkdir(parents=True, exist_ok=True)
            for level, tensor in features.items():
                if tensor is None or (hasattr(tensor, 'nelement') and tensor.nelement() == 0):
                    continue
                _get_np().save(str(cache_dir / f"{cache_key}.level{level}.npy"), tensor.numpy())

    def _find_persona_by_path(self, original_path: str) -> Optional[Persona]:
        for p in self.personas:
            if p.original_path == original_path:
                return p
        return None

    def _extract_persona_levels(self, persona: Persona):
        if self.model is None:
            return
        try:
            processed_path = persona.get_derived_path(1)
            if not processed_path.exists():
                self._preprocess_persona(persona)

            extractor = LevelExtractor(self.model)
            features = extractor.extract_all_levels(str(processed_path), copy_state=False)
            save_level_features(features, persona)
            self._log(f"[Extract] {persona.display_name}: {len(features)} level(s)")
        except Exception as e:
            self._log(f"[Error] Extract {persona.display_name}: {e}")

    def _preprocess_persona(self, persona: Persona,
                            normalize=None, denoise=None, denoise_strength=None):
        try:
            from preprocess import preprocess_audio
            pp_path, report = preprocess_audio(
                input_path=persona.original_path,
                cache_dir=PREPROCESS_CACHE_DIR,
                normalize=self.preprocess_normalize.get() if normalize is None else normalize,
                denoise=self.preprocess_denoise.get() if denoise is None else denoise,
                denoise_strength=self.preprocess_denoise_strength.get() if denoise_strength is None else denoise_strength,
            )
            actions = report.get("actions", [])
            if actions:
                self._log(f"[Preprocess] {persona.display_name}: {' -> '.join(actions)}")
            import shutil
            derived_path = persona.get_derived_path(1)
            shutil.copy2(str(pp_path), str(derived_path))
            persona.save_version()
        except Exception as e:
            self._log(f"[Error] Preprocess {persona.display_name}: {e}")

    def _save_preset_dialog(self, name_hint: str = ""):
        default = name_hint or f"preset_{int(time.time())}"
        name = simpledialog.askstring("Save Preset", "Preset name:", parent=self.root,
                                       initialvalue=default)
        if not name:
            name = default

        clips_data = []
        for track_idx, clip in self._track_editor.get_all_clips():
            clips_data.append(ClipData(**clip.to_clip_data(track_idx).__dict__))

        preset = PresetData(
            name=name,
            clips=clips_data,
            tracks_config=self._track_editor.to_dict(),
        )
        path = save_preset(preset, RUNNING_DIR)
        self._log(f"[Preset] Saved: {path}")

    def _load_preset_dialog(self):
        presets = list_presets(RUNNING_DIR)
        if not presets:
            messagebox.showinfo("Presets", "No presets found")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Load Preset")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.configure(bg=THEME["app_bg"])

        lb = tk.Listbox(dialog, bg=THEME["track_even_bg"], fg=THEME["log_fg"],
                        selectbackground=THEME["accent"], selectforeground="#fff",
                        borderwidth=0, highlightthickness=0)
        lb.pack(fill="both", expand=True, padx=8, pady=8)
        for p in presets:
            lb.insert("end", f"{p['name']} ({p.get('clip_count', 0)} clips)")

        def on_load():
            sel = lb.curselection()
            if not sel:
                return
            preset_path = Path(presets[sel[0]]["path"])
            preset = load_preset(preset_path)
            self._track_editor.load_from_dict(preset.tracks_config)
            self._log(f"[Preset] Loaded: {preset.name}")
            dialog.destroy()

        ttk.Button(dialog, text="Load", command=on_load).pack(pady=4)

    def _export_fusesona(self):
        clips = self._track_editor.get_all_clips()
        if not clips:
            messagebox.showwarning("Warning", "No clips on tracks")
            return

        try:
            state = self._get_fused_state()
            source_personas = [{"name": c.persona_name, "weight": c.weight, "effect": c.effect.to_dict()} for _, c in clips]
            meta = FuseSonaMeta(
                name=f"fusesona_{len(clips)}voices",
                source_personas=source_personas,
                fusion_level=7,
                fusion_method=self.method.get(),
            )
            state_path, meta_path = save_fusesona(state, meta, RUNNING_DIR)
            self._log(f"[FuseSona] Exported: {state_path}")
        except Exception as e:
            self._on_error(f"Export failed:\n{traceback.format_exc()}", exc=e)

    def _save_fused_state(self):
        clips = self._track_editor.get_all_clips()
        if not clips:
            messagebox.showwarning("Warning", "No clips on tracks")
            return
        path = filedialog.asksaveasfilename(
            title="Save fused state", defaultextension=".safetensors",
            initialfile="fused_state.safetensors",
            filetypes=[("Safetensors", "*.safetensors")])
        if not path:
            return
        try:
            state = self._get_fused_state()
            save_state(state, path)
            info = get_state_info(state)
            self._log(f"State saved: {path} — {format_info(info)}")
        except Exception as e:
            self._on_error(f"Save failed:\n{traceback.format_exc()}", exc=e)
