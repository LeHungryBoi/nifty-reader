"""Voice Fusion Tool — 颜色主题。

所有 UI 颜色集中在此文件，方便管理和切换配色方案。
每个配色方案是一个 dict，键名统一使用 THEME_KEYS 中定义的语义名称。

使用方式:
    from theme import THEME, apply_theme
    bg = THEME.track_bg
    apply_theme(my_ttk_style)  # 配置 ttk.Style
"""


# ── 主题键名定义（语义化） ───────────────────────────────────────────

THEME_KEYS = [
    # 整体
    "app_bg",
    # Track Editor (Canvas)
    "track_editor_bg",
    "track_even_bg",
    "track_odd_bg",
    "track_border",
    "track_selected_border",
    "track_label_fg",
    "ruler_bg",
    "ruler_major_fg",
    "ruler_minor_fg",
    "ruler_text_fg",
    "playhead_fg",
    "add_track_fg",
    # Clip
    "clip_name_fg",
    "clip_info_fg",
    "clip_selected_outline",
    "clip_default_outline",
    "clip_handle_fill",
    "clip_weight_bar_darken",
    "clip_weight_bar_darken_sel",
    # Clip Effect 指示
    "clip_effect_normal_on",
    "clip_effect_normal_off",
    "clip_effect_pitch_up",
    "clip_effect_pitch_down",
    # Persona Pool
    "pool_card_bg",
    "pool_card_border",
    "pool_name_fg",
    "pool_name_stale_fg",
    "pool_status_fg",
    # Log
    "log_bg",
    "log_fg",
    "log_cursor",
    # Playhead indicator accent
    "accent",
    "error_fg",
    # Clip palette (固定，不随主题变 — 用于区分不同 persona clip)
    "clip_palette",
]


# ── Zesty 主题（默认） ──────────────────────────────────────────────────
# 活力柑橘风 — 深色底 + 亮橙/柠绿强调

ZESTY_THEME = {
    "app_bg":                 "#1a1a2e",
    "track_editor_bg":        "#1a1a2e",
    "track_even_bg":          "#22223a",
    "track_odd_bg":           "#2a2a42",
    "track_border":           "#3a3a52",
    "track_selected_border":  "#6a6aaa",
    "track_label_fg":         "#8a8a9e",
    "ruler_bg":               "#252540",
    "ruler_major_fg":         "#8a8a9e",
    "ruler_minor_fg":         "#555570",
    "ruler_text_fg":          "#b0b0c4",
    "playhead_fg":            "#ff6b35",
    "add_track_fg":           "#c8e64a",
    "clip_name_fg":           "#fff",
    "clip_info_fg":           "#ccc",
    "clip_selected_outline":  "#ff6b35",
    "clip_default_outline":   "#555570",
    "clip_handle_fill":       "#e0e0e0",
    "clip_weight_bar_darken": 0.35,
    "clip_weight_bar_darken_sel": 0.20,
    "clip_effect_normal_on":  "#c8e64a",
    "clip_effect_normal_off": "#555570",
    "clip_effect_pitch_up":   "#00e5ff",
    "clip_effect_pitch_down": "#ff6b35",
    "pool_card_bg":           "#2a2a42",
    "pool_card_border":       "#3a3a52",
    "pool_name_fg":           "#e8e8e8",
    "pool_name_stale_fg":     "#ff8a65",
    "pool_status_fg":         "#8a8a9e",
    "log_bg":                 "#16162a",
    "log_fg":                 "#d0d0e4",
    "log_cursor":             "#c8e64a",
    "accent":                 "#ff6b35",
    "error_fg":               "#ff5252",
    "clip_palette": [
        "#ff6b35", "#c8e64a", "#00e5ff", "#ffab40",
        "#b2ff59", "#ff80ab", "#ffd740", "#7c4dff",
        "#18ffff", "#ff6e40",
    ],
}


# ── 暗色主题（备用） ──────────────────────────────────────────────────

DARK_THEME = {
    "app_bg":                 "#1e1e2e",
    "track_editor_bg":        "#1e1e2e",
    "track_even_bg":          "#252535",
    "track_odd_bg":           "#282840",
    "track_border":           "#333",
    "track_selected_border":  "#6a6a9a",
    "track_label_fg":         "#888",
    "ruler_bg":               "#2d2d3d",
    "ruler_major_fg":         "#888",
    "ruler_minor_fg":         "#555",
    "ruler_text_fg":          "#aaa",
    "playhead_fg":            "#ff4444",
    "add_track_fg":           "#666",
    "clip_name_fg":           "#000",
    "clip_info_fg":           "#333",
    "clip_selected_outline":  "#fff",
    "clip_default_outline":   "#000",
    "clip_handle_fill":       "#cccccc",
    "clip_weight_bar_darken": 0.30,
    "clip_weight_bar_darken_sel": 0.20,
    "clip_effect_normal_on":  "#000",
    "clip_effect_normal_off": "#666",
    "clip_effect_pitch_up":   "#0000cc",
    "clip_effect_pitch_down": "#cc0000",
    "pool_card_bg":           "#F5F5F5",
    "pool_card_border":       "#E0E0E0",
    "pool_name_fg":           "#333333",
    "pool_name_stale_fg":     "#E57373",
    "pool_status_fg":         "#888888",
    "log_bg":                 "#1e1e1e",
    "log_fg":                 "#d4d4d4",
    "log_cursor":             "white",
    "accent":                 "#ff4444",
    "error_fg":               "#ff4444",
    "clip_palette": [
        "#4FC3F7", "#81C784", "#FFB74D", "#E57373",
        "#BA68C8", "#4DD0E1", "#FFD54F", "#A1887F",
        "#90A4AE", "#F06292",
    ],
}


# ── 主题注册表 ────────────────────────────────────────────────────────

THEMES: dict[str, dict] = {
    "Zesty": ZESTY_THEME,
    "Dark": DARK_THEME,
}


def register_theme(name: str, theme_dict: dict):
    """注册一个新主题到注册表。"""
    THEMES[name] = theme_dict


# ── 当前主题（运行时可替换） ─────────────────────────────────────────

THEME: dict = {}
_current_theme_name: str = "Zesty"


def load_theme(name: str | None = None) -> dict:
    """加载指定主题。name=None 时加载默认暗色主题。"""
    global THEME, _current_theme_name
    if name is None:
        name = _current_theme_name
    key = name if name in THEMES else "Zesty"
    THEME = dict(THEMES[key])
    _current_theme_name = key
    return THEME


def get_theme_name() -> str:
    """返回当前主题名称。"""
    return _current_theme_name


def apply_theme(style):
    """将当前 THEME 应用到 ttk.Style。覆盖默认样式使所有控件生效。"""
    style.theme_use("clam")

    bg = THEME["app_bg"]
    fg = THEME["log_fg"]
    border = THEME["track_border"]
    label_fg = THEME["ruler_text_fg"]
    status_fg = THEME["pool_status_fg"]
    field_bg = THEME["track_even_bg"]
    select_bg = THEME["accent"]

    style.configure(".", background=bg, foreground=fg, bordercolor=border,
                    troughcolor=THEME["track_odd_bg"], fieldbackground=field_bg)
    style.configure("TFrame", background=bg)
    style.configure("TLabel", background=bg, foreground=label_fg)
    style.configure("TLabelframe", background=bg, foreground=label_fg)
    style.configure("TLabelframe.Label", background=bg, foreground=status_fg)
    style.configure("TButton", background=field_bg, foreground=fg,
                    bordercolor=border, focuscolor=select_bg)
    style.map("TButton",
              background=[("active", THEME["track_odd_bg"])],
              foreground=[("active", select_bg)])
    style.configure("TCheckbutton", background=bg, foreground=label_fg)
    style.map("TCheckbutton", background=[("active", bg)])
    style.configure("TRadiobutton", background=bg, foreground=label_fg)
    style.map("TRadiobutton", background=[("active", bg)])
    style.configure("TScale", background=bg, troughcolor=THEME["track_odd_bg"])

    # Combobox — 关键: 用 map 覆盖 readonly 状态
    style.configure("TCombobox",
                    fieldbackground=field_bg, foreground=fg,
                    background=field_bg, bordercolor=border,
                    selectbackground=select_bg, selectforeground="#fff",
                    arrowcolor=label_fg)
    style.map("TCombobox",
              fieldbackground=[("readonly", field_bg)],
              foreground=[("readonly", fg)],
              selectbackground=[("readonly", select_bg)],
              selectforeground=[("readonly", "#fff")],
              arrowcolor=[("readonly", label_fg)])

    # Combobox 下拉列表框
    style.configure("TCombobox.Listbox",
                    background=field_bg, foreground=fg,
                    selectbackground=select_bg, selectforeground="#fff",
                    bordercolor=border)

    style.configure("TEntry", fieldbackground=field_bg, foreground=fg,
                    bordercolor=border, insertcolor=fg)
    style.configure("TSeparator", background=border)
    style.configure("TPanedwindow", background=bg)
    style.configure("TScrollbar", background=THEME["track_odd_bg"],
                    troughcolor=THEME["track_editor_bg"], bordercolor=border)
    style.configure("TNotebook", background=bg)
    style.configure("TNotebook.Tab", background=field_bg, foreground=label_fg,
                    padding=[8, 4])
    style.map("TNotebook.Tab",
              background=[("selected", bg)],
              foreground=[("selected", select_bg)])

    # Named styles
    style.configure("Header.TLabel", font=("", 10, "bold"))
    style.configure("Status.TLabel", background=bg, foreground=status_fg)
    style.configure("Accent.TButton", font=("", 9, "bold"),
                    background=select_bg, foreground="#fff")
    style.map("Accent.TButton",
              background=[("active", THEME["track_odd_bg"])],
              foreground=[("active", select_bg)])


# 初始化默认主题
load_theme()

# COLORS 兼容别名（供 gui_base 等模块 re-export 使用）
COLORS = THEME["clip_palette"]
