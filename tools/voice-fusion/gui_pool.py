"""Persona Pool 面板 mixin"""

import tkinter as tk
from tkinter import ttk
from typing import Optional

from gui_base import COLORS
from persona import Persona, get_stale_personas


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
            search_entry.delete(0, "end"), search_entry.config(foreground="black")
        ) if search_entry.get() == "Search..." else None)
        search_entry.bind("<FocusOut>", lambda e: (
            search_entry.insert(0, "Search..."), search_entry.config(foreground="gray")
        ) if not search_entry.get() else None)

        # Scrollable persona list
        container = ttk.Frame(left)
        container.pack(fill="both", expand=True)

        self._pool_canvas = tk.Canvas(container, highlightthickness=0)
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

        card_outer = tk.Frame(parent, bg="#E0E0E0", padx=1, pady=1)
        card_outer.pack(fill="x", pady=3, padx=2)
        card = tk.Frame(card_outer, bg="#F5F5F5")
        card.pack(fill="x")

        # Color bar
        bar = tk.Frame(card, bg=color, width=4)
        bar.pack(side="left", fill="y")

        # Buttons (left of name)
        btn_frame = tk.Frame(card, bg="#F5F5F5")
        btn_frame.pack(side="left", padx=2, pady=2)

        # Preview raw
        ttk.Button(btn_frame, text="▶R", width=3,
                   command=lambda p=persona: self._preview_audio(p, "raw")).pack(side="left", padx=1)
        # Preview processed
        ttk.Button(btn_frame, text="▶P", width=3,
                   command=lambda p=persona: self._preview_audio(p, "processed")).pack(side="left", padx=1)
        # Add to track
        ttk.Button(btn_frame, text="+T", width=3,
                   command=lambda p=persona: self._add_persona_to_track(p)).pack(side="left", padx=1)

        # Info
        info = tk.Frame(card, bg="#F5F5F5")
        info.pack(side="left", fill="x", expand=True, padx=4)

        display_name = persona.display_name
        if is_stale:
            name_lbl = tk.Label(info, text=f"{display_name}  (stale)", font=("", 9, "bold"),
                                bg="#F5F5F5", fg="#E57373", anchor="w")
        else:
            name_lbl = tk.Label(info, text=f"{display_name}  ✓", font=("", 9, "bold"),
                                bg="#F5F5F5", fg="#333333", anchor="w")
        name_lbl.pack(fill="x")

    def _filter_personas(self):
        if not hasattr(self, "_pool_inner"):
            return
        query = self._search_var.get().lower()
        if not query:
            self._rebuild_pool(self.personas)
        else:
            filtered = [p for p in self.personas if query in p.name.lower() or query in p.display_name.lower()]
            self._rebuild_pool(filtered)
