"""融合/生成逻辑 mixin"""

import hashlib
import threading
import traceback
from pathlib import Path
from typing import Optional

from tkinter import messagebox

from theme import THEME
import tkinter as tk
from tkinter import ttk

from persona import Persona
from track_editor import Clip
from level_extractor import LevelExtractor, save_level_features
from fusion import fuse_voice_states_multi, save_state, load_state, get_state_info, format_info
from preset import save_fusesona, FuseSonaMeta, ClipData
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
                self._last_generated_text = text
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
        import sounddevice as sd
        sr = self._get_sample_rate()
        duration = audio.shape[-1] / sr
        self._log(f"Generated ({variant}): {duration:.1f}s, {sr}Hz")
        self._tts_status.configure(text=f"{variant}: {duration:.1f}s")
        if not _sounddevice_available:
            messagebox.showwarning("Warning", "Install sounddevice for playback")
            return
        audio_np = audio.squeeze().cpu().numpy().astype(np.float32)
        self._tts_status.configure(text="Playing...")
        try:
            from audio_duck import AudioDuck
            AudioDuck().duck_for_playback()
            sd.play(audio_np, sr)
        except Exception as e:
            self._on_error(f"Playback failed: {e}")

    def _get_fused_state(self) -> dict:
        all_clips = self._track_editor.get_all_clips()
        if not all_clips:
            raise ValueError("No clips on tracks")

        # 生成 cache key：如果 cache 存在且 key 未变，直接返回缓存的 fused state
        cache_key = self._compute_fused_state_key(all_clips)
        if (self._fused_state_cache is not None
                and cache_key == self._fused_state_key):
            self._log("[Fusion] Using cached fused state")
            return self._fused_state_cache

        preset_level = self._get_active_preset_level() if hasattr(self, "_get_active_preset_level") else 7
        self._log(f"[Fusion] preset type:L{preset_level}")
        states = []
        weights = []

        for track_idx, clip in all_clips:
            persona = self._find_persona_by_path(clip.persona_original_path)
            clip.fusion_level = preset_level

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
                state = self._load_persona_state_by_level_from_audio(effect_path, preset_level)
            else:
                state = self._load_persona_state_by_level(clip.persona_original_path, preset_level)
                if state is None:
                    if persona and self.model:
                        try:
                            self._extract_persona_levels(persona)
                            state = self._load_persona_state_by_level(clip.persona_original_path, preset_level)
                        except Exception:
                            pass

            if state is not None:
                states.append(state)
                weights.append(clip.weight)

        if not states:
            raise ValueError("No valid voice states. Ensure personas are extracted.")

        fused = fuse_voice_states_multi(
            states=states, weights=weights, method=self.method.get())

        # 缓存 fused state
        self._fused_state_cache = fused
        self._fused_state_key = cache_key
        self._log("[Fusion] Fused state cached")
        return fused

    def _compute_fused_state_key(self, clips: list) -> str:
        """根据 clip 配置生成唯一标识，用于判断缓存是否过期"""
        import hashlib
        parts = []
        preset_level = self._get_active_preset_level() if hasattr(self, "_get_active_preset_level") else 7
        parts.append(f"L{preset_level}")
        parts.append(self.method.get())
        for track_idx, clip in sorted(clips, key=lambda x: (x[0], x[1].persona_name)):
            parts.append(f"{clip.persona_original_path}:{clip.weight}:{clip.fusion_level}")
            eff = clip.effect
            if eff.has_custom_effects():
                parts.append(f"e{clip.effect.normalize}:{clip.effect.denoise}:{clip.effect.denoise_strength}:{clip.effect.pitch_shift}")
        key_str = "|".join(parts)
        return hashlib.md5(key_str.encode()).hexdigest()[:16]

    def _load_persona_state_by_level(self, original_path: str, level: int) -> Optional[dict]:
        persona = self._find_persona_by_path(original_path)
        if persona is None:
            return None
        if level == 7:
            state = self._load_cached_level7_state(persona.get_derived_path(1))
            if state is None:
                state = self._ensure_level_feature_and_state(persona.get_derived_path(1), level=7)
            if state is not None:
                self._log(f"[Fusion] L7 state loaded for {persona.display_name}")
            return state
        return self._load_non7_level_state(persona, level)

    def _load_persona_state_by_level_from_audio(self, audio_path, level: int) -> Optional[dict]:
        if level == 7:
            state = self._load_cached_level7_state(audio_path)
            if state is None:
                state = self._ensure_level_feature_and_state(audio_path, level=7)
            return state
        persona = self._find_persona_by_path(str(audio_path))
        if persona:
            return self._load_non7_level_state(persona, level, source_audio_path=audio_path)
        # effect 音频不一定对应 persona.original_path；直接走提取分支
        return self._ensure_level_feature_and_state(audio_path, level)

    def _load_non7_level_state(self, persona: Persona, level: int, source_audio_path: Optional[Path] = None) -> Optional[dict]:
        """非 L7: 先确保对应 level 特征存在，再回收为可生成的 L7 state。"""
        if level < 1 or level > 6:
            return None
        feature_path = persona.get_derived_path(level)
        if not feature_path.exists():
            self._extract_persona_levels(persona)
        if not feature_path.exists():
            self._log(f"[Fusion] Missing level feature L{level}: {persona.display_name}")
            return None
        source_path = source_audio_path or persona.get_derived_path(1)
        state = self._ensure_level_feature_and_state(source_path, level)
        if state is not None:
            self._log(f"[Fusion] L{level} feature loaded for {persona.display_name}")
        return state

    def _load_cached_level7_state(self, audio_path: Path) -> Optional[dict]:
        try:
            cache_path = self._state_cache_path(audio_path)
            if cache_path.exists():
                return load_state(cache_path)
        except Exception:
            pass
        return None

    def _state_cache_path(self, audio_path: Path) -> Path:
        h = hashlib.sha256()
        with open(audio_path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        cache_key = h.hexdigest()[:16]
        cache_dir = RUNNING_DIR / ".cache" / "voice_states"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / f"{cache_key}.safetensors"

    def _ensure_level_feature_and_state(self, audio_path: Path, level: int) -> Optional[dict]:
        """保证 level 特征已提取，并返回可用于生成的 L7 state。"""
        if self.model is None or not audio_path.exists():
            return None
        try:
            cache_path = self._state_cache_path(audio_path)
            if cache_path.exists():
                return load_state(cache_path)
            extractor = LevelExtractor(self.model)
            features = extractor.extract_all_levels(str(audio_path), copy_state=False)
            if level not in features:
                return None
            # 保存 level 特征缓存（用于后续诊断和复用）
            for lvl, tensor in features.items():
                if tensor is None or (hasattr(tensor, 'nelement') and tensor.nelement() == 0):
                    continue
                _get_np().save(str(cache_path.with_suffix(f".level{lvl}.npy")), tensor.numpy())
            # 最终可生成仍依赖 level7 state
            state = self.model.get_state_for_audio_prompt(str(audio_path), truncate=True)
            if state:
                save_state(state, cache_path)
                return state
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
            try:
                state = self.model.get_state_for_audio_prompt(str(audio_path), truncate=True)
                if state:
                    save_state(state, cache_dir / f"{cache_key}.safetensors")
            except Exception:
                pass

    def _find_persona_by_path(self, original_path: str) -> Optional[Persona]:
        for p in self.personas:
            if p.original_path == original_path:
                return p
        return None

    def _extract_persona_levels(self, persona: Persona):
        if self.model is None:
            return {}
        try:
            processed_path = persona.get_derived_path(1)
            if not processed_path.exists():
                self._preprocess_persona(persona)

            extractor = LevelExtractor(self.model)
            features = extractor.extract_all_levels(str(processed_path), copy_state=False)
            save_level_features(features, persona)
            levels = sorted(int(l) for l in features.keys())
            level_text = ",".join(f"L{l}" for l in levels)
            self._log(f"[Extract] {persona.display_name}: cached [{level_text}]")
            return features
        except Exception as e:
            self._log(f"[Error] Extract {persona.display_name}: {e}")
            return {}

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
                fusion_level=self._get_active_preset_level() if hasattr(self, "_get_active_preset_level") else 7,
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
