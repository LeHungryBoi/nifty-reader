"""Persona Pool 面板 mixin"""

import tkinter as tk
from tkinter import ttk
from typing import Optional

from gui_base import COLORS
from persona import Persona, get_stale_personas
from theme import THEME


class PoolMixin:
    """VoiceFusionApp Persona Pool 面板"""

    def _build_pool(self, pw):
        """构建左侧 Persona Pool 面板"""
        left = ttk.LabelFrame(pw, text="Persona Pool", padding=4)
        pw.add(left, weight=0)

        # Search
        search_frame = ttk.Frame(left)
        search_frame.pack(fill="x", pady=(0, 4))
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._filter_personas())
        search_entry = ttk.Entry(search_frame, textvariable=self._search_var)
        search_entry.pack(side="left", fill="x", expand=True)
        search_entry.insert(0, "Search...")
        search_entry.config(foreground="gray")
        search_entry.bind("<FocusIn>", lambda e: (
            search_entry.delete(0, "end"), search_entry.config(foreground=THEME["log_fg"])
        ) if search_entry.get() == "Search..." else None)
        search_entry.bind("<FocusOut>", lambda e: (
            search_entry.insert(0, "Search..."), search_entry.config(foreground="gray")
        ) if not search_entry.get() else None)

        # Scrollable persona list
        container = ttk.Frame(left)
        container.pack(fill="both", expand=True)

        self._pool_canvas = tk.Canvas(container, bg=THEME["app_bg"], highlightthickness=0)
        sb = ttk.Scrollbar(container, orient="vertical", command=self._pool_canvas.yview)
        self._pool_inner = ttk.Frame(self._pool_canvas)

        self._pool_inner.bind("<Configure>",
            lambda e: self._pool_canvas.configure(scrollregion=self._pool_canvas.bbox("all")))
        self._pool_window_id = self._pool_canvas.create_window((0, 0), window=self._pool_inner, anchor="nw")
        self._pool_canvas.configure(yscrollcommand=sb.set)

        # Keep inner frame width in sync with canvas width
        self._pool_canvas.bind("<Configure>", self._on_pool_canvas_resize)

        sb.pack(side="right", fill="y")
        self._pool_canvas.pack(side="left", fill="both", expand=True)

        self._pool_canvas.bind("<Enter>", self._bind_pool_wheel)
        self._pool_canvas.bind("<Leave>", self._unbind_pool_wheel)

        return left

    def _bind_pool_wheel(self, event):
        self._pool_canvas.bind_all("<MouseWheel>", self._on_pool_wheel)
        self._pool_canvas.bind_all("<Button-4>", self._on_pool_wheel)
        self._pool_canvas.bind_all("<Button-5>", self._on_pool_wheel)

    def _unbind_pool_wheel(self, event):
        self._pool_canvas.unbind_all("<MouseWheel>")
        self._pool_canvas.unbind_all("<Button-4>")
        self._pool_canvas.unbind_all("<Button-5>")

    def _on_pool_wheel(self, event):
        if event.num == 4:
            self._pool_canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self._pool_canvas.yview_scroll(1, "units")
        else:
            self._pool_canvas.yview_scroll(-int(event.delta / 120), "units")

    def _on_pool_canvas_resize(self, event):
        """Keep inner frame width synced with canvas width so cards are never clipped"""
        self._pool_canvas.itemconfig(self._pool_window_id, width=event.width)

    def _rebuild_pool(self, personas: Optional[list[Persona]] = None):
        if not hasattr(self, "_pool_inner"):
            return
        for w in self._pool_inner.winfo_children():
            w.destroy()

        display = personas or self.personas
        for idx, persona in enumerate(display):
            self._build_persona_card(self._pool_inner, persona, idx)

        stale = get_stale_personas(display)
        self._pool_status = f"{len(display)} persona(s)"
        if stale:
            self._pool_status += f", {len(stale)} stale"

    def _build_persona_card(self, parent, persona: Persona, idx: int):
        color = COLORS[idx % len(COLORS)]
        is_stale = not persona.is_derived_valid()

        card_outer = tk.Frame(parent, bg=THEME["pool_card_border"], padx=1, pady=1)
        card_outer.pack(fill="x", pady=3, padx=2)
        card = tk.Frame(card_outer, bg=THEME["pool_card_bg"])
        card.pack(fill="x")

        # Color bar
        bar = tk.Frame(card, bg=color, width=4)
        bar.pack(side="left", fill="y")

        # Buttons (left of name)
        btn_frame = tk.Frame(card, bg=THEME["pool_card_bg"])
        btn_frame.pack(side="left", padx=2, pady=2)

        # Preview raw
        ttk.Button(btn_frame, text="▶R", width=3,
                   command=lambda p=persona: self._preview_audio(p, "raw")).pack(side="left", padx=1)
        # Preview processed
        ttk.Button(btn_frame, text="▶P", width=3,
                   command=lambda p=persona: self._preview_audio(p, "processed")).pack(side="left", padx=1)
        # Add to track (left=click: new track, right-click: last active track)
        add_btn = ttk.Button(btn_frame, text="+T", width=3,
                             command=lambda p=persona: self._add_persona_to_track(p, new_track=True))
        add_btn.pack(side="left", padx=1)
        add_btn.bind("<Button-3>", lambda e, p=persona: self._add_persona_to_track(p, new_track=False))

        # Info
        info = tk.Frame(card, bg=THEME["pool_card_bg"])
        info.pack(side="left", fill="x", expand=True, padx=4)

        display_name = persona.display_name
        if is_stale:
            name_lbl = tk.Label(info, text=f"{display_name}  (stale)", font=("", 9, "bold"),
                                bg=THEME["pool_card_bg"], fg=THEME["pool_name_stale_fg"], anchor="w")
        else:
            name_lbl = tk.Label(info, text=display_name, font=("", 9, "bold"),
                                bg=THEME["pool_card_bg"], fg=THEME["pool_name_fg"], anchor="w")
        name_lbl.pack(fill="x")

        self._build_level_cache_bar(info, persona, top=False)

    def _build_level_cache_bar(self, parent, persona: Persona, top: bool):
        """绘制 7 个独立 level 状态灯（VST 风格发光点）。"""
        bar = tk.Canvas(parent, height=14, bg=THEME["pool_card_bg"], highlightthickness=0, bd=0)
        pad = (0, 1) if top else (2, 0)
        bar.pack(fill="x", pady=pad)

        states = self._get_persona_level_states(persona) if hasattr(self, "_get_persona_level_states") else {}
        level_palette = THEME.get("pool_level_palette") or THEME.get("level_palette", {})
        bg = THEME["pool_card_bg"]

        def draw(_e=None):
            bar.delete("all")
            width = max(int(bar.winfo_width()), 56)
            height = max(int(bar.winfo_height()), 12)
            seg = width / 7.0
            inner_r = max(3, min(5, height // 3))
            glow_r = inner_r + 3
            y = height // 2
            for i in range(7):
                lvl = i + 1
                x = int((i + 0.5) * seg)
                base = level_palette.get(lvl, "#4f6b8a")
                state = states.get(lvl, "missing")
                fill, glow, outline = self._level_dot_style(base, state, bg)

                if glow:
                    bar.create_oval(
                        x - glow_r, y - glow_r, x + glow_r, y + glow_r,
                        fill=glow, outline=""
                    )
                bar.create_oval(
                    x - inner_r, y - inner_r, x + inner_r, y + inner_r,
                    fill=fill, outline=outline, width=1
                )

        bar.bind("<Configure>", draw)
        draw()

    @staticmethod
    def _level_dot_style(base: str, state: str, bg: str) -> tuple[str, str, str]:
        if state == "ready":
            fill = base
            glow = PoolMixin._mix_hex(fill, bg, 0.72)
            outline = PoolMixin._mix_hex(fill, "#ffffff", 0.15)
            return fill, glow, outline
        if state == "extracting":
            fill = PoolMixin._mix_hex(base, "#f1c40f", 0.55)
            glow = PoolMixin._mix_hex("#f1c40f", bg, 0.70)
            outline = "#f1c40f"
            return fill, glow, outline
        if state == "error":
            fill = PoolMixin._mix_hex(base, "#ff4d4f", 0.65)
            glow = PoolMixin._mix_hex("#ff4d4f", bg, 0.72)
            outline = "#ff7875"
            return fill, glow, outline
        fill = PoolMixin._mix_hex(base, bg, 0.78)
        glow = ""
        outline = PoolMixin._mix_hex(fill, bg, 0.45)
        return fill, glow, outline

    @staticmethod
    def _level_status_color(base: str, state: str) -> str:
        if state == "ready":
            return base
        if state == "extracting":
            return PoolMixin._mix_hex(base, "#f1c40f", 0.55)
        if state == "error":
            return PoolMixin._mix_hex(base, "#ff4d4f", 0.65)
        return PoolMixin._mix_hex(base, "#20232a", 0.65)

    @staticmethod
    def _mix_hex(c1: str, c2: str, ratio: float) -> str:
        c1 = c1.lstrip("#")
        c2 = c2.lstrip("#")
        r1, g1, b1 = [int(c1[i:i + 2], 16) for i in (0, 2, 4)]
        r2, g2, b2 = [int(c2[i:i + 2], 16) for i in (0, 2, 4)]
        r = int(r1 * (1 - ratio) + r2 * ratio)
        g = int(g1 * (1 - ratio) + g2 * ratio)
        b = int(b1 * (1 - ratio) + b2 * ratio)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _filter_personas(self):
        if not hasattr(self, "_pool_inner"):
            return
        query = self._search_var.get().lower()
        if not query:
            self._rebuild_pool(self.personas)
        else:
            filtered = [p for p in self.personas if query in p.name.lower() or query in p.display_name.lower()]
            self._rebuild_pool(filtered)
