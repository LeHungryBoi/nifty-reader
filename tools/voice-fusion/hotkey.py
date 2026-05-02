"""Keyboard shortcut manager with priority levels.

Priority (high → low):
  1. Text entry widgets (Entry / Text) — plain keys always pass through
  2. Page-level shortcuts — active page wins when multiple pages bind the same key
  3. Global shortcuts — always available fallback

Usage:
  km = ShortcutManager(root)

  # Register global shortcuts
  km.bind_global("<space>", callback)
  km.bind_global("s", callback)

  # Register page shortcuts
  km.bind_page("track", "<space>", callback_page_space)

  # When switching pages:
  km.set_active_page("track")

  # Plain letter keys in Entry/Text are auto-suppressed (no handler fires).
"""

import tkinter as tk
from typing import Callable, Optional


class ShortcutManager:
    def __init__(self, root: tk.Tk):
        self.root = root
        self._global_map: dict[str, Callable] = {}
        self._page_map: dict[str, dict[str, Callable]] = {}
        self._active_page: Optional[str] = None

        # Bind a single dispatcher for each key event class.
        # We intercept at the root level and dispatch based on priority.
        self.root.bind("<Key>", self._dispatch)

        # For non-printable keys that tkinter sends as virtual events
        # (e.g. <space>, <Return>), we also bind common ones via event names
        # so the dispatcher catches them.  <Key> alone misses these on some
        # platforms.  We register lightweight stubs that call _dispatch.
        self._virtual_keys = [
            "<space>", "<Return>", "<Escape>", "<Tab>", "<BackSpace>",
            "<Delete>", "<Left>", "<Right>", "<Up>", "<Down>",
            "<Home>", "<End>", "<Prior>", "<Next>",
            "<F1>", "<F2>", "<F3>", "<F4>", "<F5>",
            "<F6>", "<F7>", "<F8>", "<F9>", "<F10>",
            "<F11>", "<F12>",
        ]
        for vk in self._virtual_keys:
            self.root.bind(vk, self._dispatch)
        # Shift combos
        for vk in ["<Shift-space>"]:
            self.root.bind(vk, self._dispatch)

    # ── registration ────────────────────────────────────────────────────

    def bind_global(self, key: str, callback: Callable) -> None:
        """Register a global (lowest priority) shortcut."""
        self._global_map[key] = callback

    def bind_page(self, page: str, key: str, callback: Callable) -> None:
        """Register a page-scoped shortcut for *page*."""
        self._page_map.setdefault(page, {})[key] = callback

    def set_active_page(self, page: Optional[str]) -> None:
        """Set the currently active page (None = no page active)."""
        self._active_page = page

    # ── dispatch ────────────────────────────────────────────────────────

    def _dispatch(self, event) -> str | None:
        """Central dispatcher. Returns 'break' to stop propagation."""
        focused = event.widget

        # Rule 1: if focus is on a text-entry widget, let plain keys through
        # (but still allow explicit bindings like <Return>, <Escape> if registered)
        if isinstance(focused, (tk.Entry, tk.Text)):
            # For plain printable single-char keys, always pass through
            key = event.keysym
            if len(key) == 1 and key.isprintable() and not event.state & 0x1:
                # Plain letter / digit / punctuation → typing, suppress shortcuts
                return None

            # Non-printable keys (Return, Escape, etc.) can still trigger shortcuts
            # if explicitly bound. Build the event string.
            event_str = self._event_to_str(event)

        else:
            event_str = self._event_to_str(event)

        # Rule 2: page-level (higher priority)
        if self._active_page:
            page_bindings = self._page_map.get(self._active_page, {})
            cb = page_bindings.get(event_str)
            if cb:
                cb(event)
                return "break"

        # Rule 3: global fallback
        cb = self._global_map.get(event_str)
        if cb:
            cb(event)
            return "break"

        return None

    @staticmethod
    def _event_to_str(event) -> str:
        """Convert a tk Event to a binding string like '<space>' or '<Control-s>'."""
        parts = []
        state = event.state

        # Tk state flags
        if state & 0x4:    # Control
            parts.append("Control")
        if state & 0x1:    # Shift
            parts.append("Shift")
        if state & 0x8:    # Alt
            parts.append("Alt")

        keysym = event.keysym
        # Single printable char
        if len(keysym) == 1 and keysym.isprintable():
            mod_str = "-".join(parts)
            return f"<{mod_str}-{keysym}>" if mod_str else keysym
        else:
            mod_str = "-".join(parts)
            return f"<{mod_str}-{keysym}>" if mod_str else f"<{keysym}>"

    def unbind_global(self, key: str) -> None:
        self._global_map.pop(key, None)

    def unbind_page(self, page: str, key: str) -> None:
        mapping = self._page_map.get(page)
        if mapping:
            mapping.pop(key, None)
