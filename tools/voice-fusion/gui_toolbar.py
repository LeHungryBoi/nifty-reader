"""工具栏构建 mixin"""

import tkinter as tk
from tkinter import ttk


class ToolbarMixin:
    """VoiceFusionApp 工具栏构建"""

    def _build_toolbar(self):
        tb = ttk.Frame(self.root)
        tb.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))

        # Model controls
        ttk.Label(tb, text="Language:").pack(side="left")
        ttk.Combobox(tb, textvariable=self.language, width=10, state="readonly",
                      values=["english", "french_24l", "german_24l",
                              "portuguese", "italian", "spanish_24l"]
                      ).pack(side="left", padx=(2, 8))

        ttk.Label(tb, text="Device:").pack(side="left")
        ttk.Combobox(tb, textvariable=self.device, width=7, state="readonly",
                      values=["cpu", "cuda", "mps"]
                      ).pack(side="left", padx=(2, 8))

        ttk.Checkbutton(tb, text="Proxy", variable=self.proxy_enabled).pack(side="left")
        ttk.Entry(tb, textvariable=self.proxy, width=25).pack(side="left", padx=(2, 8))

        self.load_btn = ttk.Button(tb, text="Load Model", command=self._load_model)
        self.load_btn.pack(side="left", padx=2)
        self.model_status = ttk.Label(tb, text="Not loaded", style="Status.TLabel")
        self.model_status.pack(side="left", padx=8)

        ttk.Separator(tb, orient="vertical").pack(side="left", fill="y", padx=8)

        # Preprocessing
        ttk.Checkbutton(tb, text="Normalize", variable=self.preprocess_normalize).pack(side="left")
        ttk.Checkbutton(tb, text="Denoise", variable=self.preprocess_denoise).pack(side="left")
        ttk.Label(tb, text="Str:").pack(side="left")
        ttk.Scale(tb, from_=0.1, to=1.0, variable=self.preprocess_denoise_strength,
                  orient="horizontal", length=80).pack(side="left")
        ttk.Button(tb, text="Rescan", command=self._rescan_voices).pack(side="left", padx=4)

        ttk.Separator(tb, orient="vertical").pack(side="left", fill="y", padx=8)

        # Preset / FuseSona
        ttk.Button(tb, text="Save Preset", command=self._save_preset_dialog).pack(side="left", padx=2)
        ttk.Button(tb, text="Load Preset", command=self._load_preset_dialog).pack(side="left", padx=2)
        ttk.Button(tb, text="Export FuseSona", command=self._export_fusesona).pack(side="left", padx=2)
