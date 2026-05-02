"""Clip Effect 面板 mixin"""

import tkinter as tk
from tkinter import ttk

from track_editor import Clip, ClipEffect
from theme import THEME


class EffectPanelMixin:
    """VoiceFusionApp Clip Effect 面板"""

    def _build_effect_panel(self, parent: tk.Widget = None):
        if parent is None:
            parent = self.root
        self._effect_frame = ttk.LabelFrame(parent, text="Clip Effects", padding=6)
        self._effect_frame.pack(side="right", fill="both", expand=True, padx=(4, 0), pady=0)

        # Row 1: Weight + Normalize, Denoise, Strength
        row1 = ttk.Frame(self._effect_frame)
        row1.pack(fill="x")

        # Weight control with precise numeric display
        weight_frame = ttk.Frame(row1)
        weight_frame.pack(side="left", padx=(0, 8))
        
        ttk.Label(weight_frame, text="Weight:").pack(side="left")
        self._weight_value_label = ttk.Label(weight_frame, text="1.0", width=5, font=("Consolas", 9))
        self._weight_value_label.pack(side="left", padx=2)
        ttk.Scale(weight_frame, from_=0.0, to=2.0, variable=self._clip_weight_var,
                  orient="horizontal", length=100,
                  command=self._on_weight_change).pack(side="left", padx=2)

        ttk.Checkbutton(row1, text="Normalize",
                        variable=self._effect_normalize).pack(side="left", padx=2)
        ttk.Checkbutton(row1, text="Denoise",
                        variable=self._effect_denoise).pack(side="left", padx=2)
        ttk.Label(row1, text="D.Str:").pack(side="left", padx=(4, 0))
        ttk.Scale(row1, from_=0.1, to=1.0, variable=self._effect_denoise_strength,
                  orient="horizontal", length=80).pack(side="left", padx=2)
        self._dns_str_label = ttk.Label(row1, text="0.3", width=4)
        self._dns_str_label.pack(side="left")
        self._effect_denoise_strength.trace_add("write",
            lambda *_: self._dns_str_label.configure(
                text=f"{self._effect_denoise_strength.get():.1f}"))

        # Row 2: Pitch Shift + Buttons
        row2 = ttk.Frame(self._effect_frame)
        row2.pack(fill="x", pady=(4, 0))

        ttk.Label(row2, text="Pitch Shift:").pack(side="left")
        self._pitch_label = ttk.Label(row2, text="0.0 st", width=6)
        self._pitch_label.pack(side="left", padx=4)
        ttk.Scale(row2, from_=-12.0, to=12.0, variable=self._effect_pitch_shift,
                  orient="horizontal", length=200,
                  command=self._on_pitch_change).pack(side="left", padx=2)

        self._effect_pitch_shift.trace_add("write", self._update_pitch_label)

        # Buttons
        ttk.Separator(row2, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Button(row2, text="▶ Preview", command=self._preview_effect).pack(side="left", padx=2)
        ttk.Button(row2, text="Apply", command=self._apply_effect).pack(side="left", padx=2)
        ttk.Button(row2, text="Reset to Global",
                   command=self._reset_effect_to_global).pack(side="left", padx=2)

        # Hidden by default
        self._effect_frame.grid_remove()

    def _update_pitch_label(self, *_):
        val = self._effect_pitch_shift.get()
        if val > 0.01:
            arrow = "\u25B2"
            color = THEME["clip_effect_pitch_up"]
        elif val < -0.01:
            arrow = "\u25BC"
            color = THEME["clip_effect_pitch_down"]
        else:
            arrow = ""
            color = THEME["pool_status_fg"]
        text = f"{arrow}{val:+.1f} st" if arrow else "0.0 st"
        try:
            self._pitch_label.configure(text=text, foreground=color)
        except tk.TclError:
            pass

    def _on_pitch_change(self, val):
        self._update_pitch_label()
        sel = self._track_editor.get_selected_clip()
        if sel:
            sel[1].effect.pitch_shift = round(float(val), 1)
            self._track_editor._redraw()

    def _on_weight_change(self, val):
        """Update weight value display and sync to clip"""
        weight_val = round(float(val), 2)
        try:
            self._weight_value_label.configure(text=f"{weight_val:.2f}")
        except (AttributeError, tk.TclError):
            pass
        
        sel = self._track_editor.get_selected_clip()
        if sel:
            sel[1].weight = weight_val
            self._track_editor._redraw()
            self._auto_save()
            self._invalidate_fused_cache()

    def _show_effect_panel(self, clip: Clip):
        self._effect_frame.pack(side="right", fill="both", expand=True, padx=(4, 0), pady=0)
        eff = clip.effect
        
        # Update weight display
        self._clip_weight_var.set(clip.weight)
        try:
            self._weight_value_label.configure(text=f"{clip.weight:.2f}")
        except (AttributeError, tk.TclError):
            pass

        if eff.normalize is None:
            self._effect_normalize.set(self.preprocess_normalize.get())
            self._effect_normalize.configure(state="normal")
        else:
            self._effect_normalize.set(eff.normalize)

        if eff.denoise is None:
            self._effect_denoise.set(self.preprocess_denoise.get())
        else:
            self._effect_denoise.set(eff.denoise)

        if eff.denoise_strength is None:
            self._effect_denoise_strength.set(self.preprocess_denoise_strength.get())
        else:
            self._effect_denoise_strength.set(eff.denoise_strength)

        self._effect_pitch_shift.set(eff.pitch_shift)

        self._effect_normalize.trace_add("write", self._sync_effect_to_clip)
        self._effect_denoise.trace_add("write", self._sync_effect_to_clip)
        self._effect_denoise_strength.trace_add("write", self._sync_effect_to_clip)

    def _hide_effect_panel(self):
        self._effect_frame.pack_forget()
        try:
            self._effect_normalize.trace_remove("write", self._sync_effect_to_clip)
            self._effect_denoise.trace_remove("write", self._sync_effect_to_clip)
            self._effect_denoise_strength.trace_remove("write", self._sync_effect_to_clip)
        except (tk.TclError, ValueError):
            pass

    def _sync_effect_to_clip(self, *_):
        sel = self._track_editor.get_selected_clip()
        if not sel:
            return
        clip = sel[1]
        eff = clip.effect

        norm_panel = self._effect_normalize.get()
        norm_global = self.preprocess_normalize.get()
        eff.normalize = norm_panel if norm_panel != norm_global else None

        dns_panel = self._effect_denoise.get()
        dns_global = self.preprocess_denoise.get()
        eff.denoise = dns_panel if dns_panel != dns_global else None

        str_panel = round(self._effect_denoise_strength.get(), 1)
        str_global = round(self.preprocess_denoise_strength.get(), 1)
        eff.denoise_strength = str_panel if str_panel != str_global else None

        eff.pitch_shift = round(self._effect_pitch_shift.get(), 1)

        self._track_editor._redraw()
        self._auto_save()
        self._invalidate_fused_cache()

    def _apply_effect(self):
        sel = self._track_editor.get_selected_clip()
        if not sel:
            return
        track_idx, clip = sel
        persona = self._find_persona_by_path(clip.persona_original_path)
        if not persona:
            self._log("[Effect] Persona not found")
            return

        processed_path = persona.get_derived_path(1)
        if not processed_path.exists():
            self._preprocess_persona(persona)

        effect_dict = clip.effect.to_dict()
        try:
            from preprocess import apply_clip_effects, effect_cache_key
            effect_path, actions = apply_clip_effects(
                processed_path, effect_dict, persona.get_effect_cache_dir())
            if actions:
                self._log(f"[Effect] {persona.display_name}: {', '.join(actions)}")

            if self.model and effect_path != processed_path:
                from level_extractor import LevelExtractor, save_level_features
                extractor = LevelExtractor(self.model)
                features = extractor.extract_all_levels(str(effect_path), copy_state=False)
                save_level_features(features, persona)
                self._log(f"[Effect] Re-extracted features for {persona.display_name}")

            self._track_editor._redraw()
        except Exception as e:
            self._log(f"[Error] Apply effect: {e}")

    def _preview_effect(self):
        sel = self._track_editor.get_selected_clip()
        if not sel:
            return
        _, clip = sel
        persona = self._find_persona_by_path(clip.persona_original_path)
        if not persona:
            return

        processed_path = persona.get_derived_path(1)
        if not processed_path.exists():
            return

        effect_dict = clip.effect.to_dict()
        if not clip.effect.has_custom_effects():
            self._preview_audio(persona, "processed")
            return

        try:
            from preprocess import apply_clip_effects
            effect_path, actions = apply_clip_effects(
                processed_path, effect_dict, persona.get_effect_cache_dir())
            if effect_path.exists():
                self._preview_audio_path(effect_path, f"effect({', '.join(actions)})")
        except Exception as e:
            self._log(f"[Error] Preview effect: {e}")

    def _reset_effect_to_global(self):
        sel = self._track_editor.get_selected_clip()
        if not sel:
            return
        clip = sel[1]
        clip.effect = ClipEffect()
        self._show_effect_panel(clip)
        self._log(f"[Effect] Reset '{clip.persona_name}' to global")
