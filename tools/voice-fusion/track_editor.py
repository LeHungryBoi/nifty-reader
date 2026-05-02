"""
Track Editor — 视频编辑风格的轨道编辑器。

功能：
  - 多轨道显示，每条轨道放置 persona clip
  - 拖放 clip 从 persona pool 到轨道
  - 移动、伸缩（插值调整长度）、分割、删除 clip
  - 时间轴 + playhead + 缩放
  - clip 权重和 fusion level 设置
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from dataclasses import dataclass, field, asdict
from typing import Optional, Callable
from copy import deepcopy

from preset import ClipData
from theme import THEME


# 常量
FRAME_RATE = 12.5  # MiMi Latent 帧率
PIXELS_PER_FRAME_DEFAULT = 3.0
TRACK_HEIGHT = 32
CLIP_MIN_WIDTH = 20
RULER_HEIGHT = 24
TRACK_LABEL_WIDTH = 36  # 左侧固定轨道标签栏宽度
HANDLE_WIDTH = 6  # clip 边缘拖拽热区宽度

COLORS = [
    "#4FC3F7", "#81C784", "#FFB74D", "#E57373",
    "#BA68C8", "#4DD0E1", "#FFD54F", "#A1887F",
    "#90A4AE", "#F06292",
]

# Latent space level 短名称（用于 clip 和 UI 显示）
LEVEL_SHORT_NAMES = {
    1: "Raw",
    2: "SEANet",
    3: "EncAttn",
    4: "MiMi",
    5: "Trans",
    6: "SpkProj",
    7: "KVCache",
}

# 每个 level 的时间分辨率相对于 MiMi frame (12.5Hz) 的比率
# 值越大 = 1 个 track frame 里包含越多该 level 的单元
# arrow key 每次移动 = 1 个该 level 单元 = 1/ratio 个 track frame
_LEVEL_FRAME_RATIOS = {
    1: 1920,   # 24kHz raw samples per MiMi frame
    2: 16,     # 200Hz SEANet frames per MiMi frame
    3: 16,     # 200Hz encoder attn frames per MiMi frame
    4: 1,      # 12.5Hz MiMi latent — base unit
    5: 1,      # same as MiMi
    6: 1,      # same as MiMi
    7: 1,      # same as MiMi
}


def level_display_str(level: int) -> str:
    """生成用于 UI 下拉框的显示字符串，如 '4-MiMi'"""
    name = LEVEL_SHORT_NAMES.get(level, f"L{level}")
    return f"{level}-{name}"


def parse_level_from_str(s: str) -> int:
    """从 UI 下拉框字符串解析出 level 数字"""
    try:
        return int(s.split("-")[0])
    except (ValueError, IndexError):
        return 7


@dataclass
class ClipEffect:
    """Clip 级音频效果设置，覆盖全局预处理"""
    normalize: Optional[bool] = None     # None = 跟随全局
    denoise: Optional[bool] = None       # None = 跟随全局
    denoise_strength: Optional[float] = None  # None = 跟随全局
    pitch_shift: float = 0.0             # 半音偏移，0.0 = 不变

    def has_custom_effects(self) -> bool:
        """是否有任何非默认 effect"""
        return (
            self.normalize is not None
            or self.denoise is not None
            or self.denoise_strength is not None
            or self.pitch_shift != 0.0
        )

    def to_dict(self) -> dict:
        return {
            "normalize": self.normalize,
            "denoise": self.denoise,
            "denoise_strength": self.denoise_strength,
            "pitch_shift": self.pitch_shift,
        }

    @classmethod
    def from_dict(cls, d: dict) -> ClipEffect:
        return cls(
            normalize=d.get("normalize"),
            denoise=d.get("denoise"),
            denoise_strength=d.get("denoise_strength"),
            pitch_shift=d.get("pitch_shift", 0.0),
        )


@dataclass
class Clip:
    """轨道上的一个片段"""
    persona_name: str = ""
    persona_original_path: str = ""
    start_frame: int = 0
    length_frames: int = 100
    original_length_frames: int = 100
    weight: float = 1.0
    fusion_level: int = 4
    color: str = "#4FC3F7"
    effect: ClipEffect = field(default_factory=ClipEffect)

    @property
    def end_frame(self) -> int:
        return self.start_frame + self.length_frames

    def contains_frame(self, frame: int) -> bool:
        return self.start_frame <= frame < self.end_frame

    def overlaps(self, other: Clip) -> bool:
        return self.start_frame < other.end_frame and other.start_frame < self.end_frame

    def to_clip_data(self, track_index: int = 0) -> ClipData:
        return ClipData(
            persona_name=self.persona_name,
            persona_original_path=self.persona_original_path,
            track_index=track_index,
            start_frame=self.start_frame,
            length_frames=self.length_frames,
            original_length_frames=self.original_length_frames,
            weight=self.weight,
            fusion_level=self.fusion_level,
            effect=self.effect.to_dict(),
        )

    @classmethod
    def from_clip_data(cls, cd: ClipData, color: str = "#4FC3F7") -> Clip:
        effect = ClipEffect.from_dict(cd.effect) if cd.effect else ClipEffect()
        return cls(
            persona_name=cd.persona_name,
            persona_original_path=cd.persona_original_path,
            start_frame=cd.start_frame,
            length_frames=cd.length_frames,
            original_length_frames=cd.original_length_frames or cd.length_frames,
            weight=cd.weight,
            fusion_level=cd.fusion_level,
            color=color,
            effect=effect,
        )


@dataclass
class Track:
    """一条轨道"""
    index: int = 0
    clips: list[Clip] = field(default_factory=list)
    name: str = "T1"


class TrackEditor(tk.Canvas):
    """视频编辑风格的多轨道编辑器"""

    def __init__(self, parent, **kwargs):
        self.tracks: list[Track] = [Track(index=0, name="T1")]
        self._preset_level: int = 4
        self.pixels_per_frame = PIXELS_PER_FRAME_DEFAULT
        self.playhead_frame: float = 0
        self._max_frame = 500
        self._color_index = 0
        self._resize_redraw_after_id: str | None = None
        self._scroll_y: int = 0  # vertical scroll offset for tracks

        # 拖拽状态
        self._dragging: Optional[dict] = None  # {type: "move"|"resize_l"|"resize_r", clip, track_idx, offset_x, orig_start, orig_length}
        self._selected_clip: Optional[tuple[int, Clip]] = None  # (track_idx, clip)
        self.selected_track_idx: int = 0

        # 回调
        self.on_clip_double_click: Optional[Callable] = None
        self.on_clip_right_click: Optional[Callable] = None
        self.on_track_selected: Optional[Callable] = None  # (track_idx,)

        super().__init__(parent, bg=THEME["track_editor_bg"], highlightthickness=0, **kwargs)
        self.bind("<Button-1>", self._on_click)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Double-Button-1>", self._on_double_click)
        self.bind("<Button-3>", self._on_right_click)
        self.bind("<MouseWheel>", self._on_scroll)
        self.bind("<Button-4>", self._on_scroll)
        self.bind("<Button-5>", self._on_scroll)
        self.bind("<Left>", self._on_key_left)
        self.bind("<Right>", self._on_key_right)
        self.bind("<Delete>", self._on_key_delete)

        self.bind("<Configure>", self._on_configure)

        self.focus_set()
        self.bind("<Configure>", self._on_configure)

    # ── 公共 API ──

    def add_track(self) -> Track:
        idx = len(self.tracks)
        track = Track(index=idx, name=f"T{idx + 1}")
        self.tracks.append(track)
        self._redraw()
        return track

    def set_preset_level(self, level: int):
        """设置当前 preset level（用于背景着色）。"""
        try:
            level = int(level)
        except Exception:
            level = 4
        self._preset_level = min(7, max(1, level))
        self._redraw()

    def remove_track(self, index: int):
        if 0 <= index < len(self.tracks) and len(self.tracks) > 1:
            self.tracks.pop(index)
            for i, t in enumerate(self.tracks):
                t.index = i
                t.name = f"T{i + 1}"
            self._selected_clip = None
            self._redraw()

    def add_clip(self, track_index: int, clip: Clip):
        if 0 <= track_index < len(self.tracks):
            self.tracks[track_index].clips.append(clip)
            self._next_color()
            self._update_max_frame()
            self._redraw()

    def remove_clip(self, track_index: int, clip: Clip):
        if 0 <= track_index < len(self.tracks):
            self.tracks[track_index].clips = [
                c for c in self.tracks[track_index].clips if c is not clip]
            self._selected_clip = None
            self._update_max_frame()
            self._redraw()

    def reset_clip_length(self, clip: Clip):
        """Reset clip length to its original value."""
        clip.length_frames = clip.original_length_frames
        self._update_max_frame()
        self._redraw()

    def trim_clip_at_playhead(self) -> bool:
        """
        Trim the selected clip at the playhead position.
        If playhead is in the first half of clip → trim from start (keep right side).
        If playhead is in the second half → trim from end (keep left side).
        Returns True if trimmed, False if no selection or no-op.
        """
        if not self._selected_clip:
            return False
        _, clip = self._selected_clip
        ph = int(self.playhead_frame)

        # Playhead must be inside the clip
        if ph <= clip.start_frame or ph >= clip.end_frame:
            return False

        left_len = ph - clip.start_frame
        right_len = clip.end_frame - ph

        if left_len < 5 and right_len < 5:
            return False

        # Trim the shorter side — keep more content
        if left_len <= right_len:
            # Trim from start
            if right_len >= 5:
                clip.start_frame = ph
                clip.length_frames = right_len
        else:
            # Trim from end
            if left_len >= 5:
                clip.length_frames = left_len

        self._update_max_frame()
        self._redraw()
        return True

    def _select_track(self, idx: int):
        """Select a track and notify callback."""
        self.selected_track_idx = idx
        if self.on_track_selected:
            self.on_track_selected(idx)

    def split_clip_at(self, track_index: int, clip: Clip, frame: int):
        if not clip.contains_frame(frame):
            return
        if 0 <= track_index < len(self.tracks):
            new_length = frame - clip.start_frame
            if new_length < 5:
                return
            new_clip = Clip(
                persona_name=clip.persona_name,
                persona_original_path=clip.persona_original_path,
                start_frame=frame,
                length_frames=clip.length_frames - new_length,
                original_length_frames=clip.original_length_frames,
                weight=clip.weight,
                fusion_level=clip.fusion_level,
                color=self._next_color(),
                effect=ClipEffect(**clip.effect.to_dict()),
            )
            clip.length_frames = new_length
            idx = self.tracks[track_index].clips.index(clip)
            self.tracks[track_index].clips.insert(idx + 1, new_clip)
            self._redraw()

    def get_selected_clip(self) -> Optional[tuple[int, Clip]]:
        return self._selected_clip

    def set_playhead(self, frame: float):
        self.playhead_frame = max(0, frame)
        self._redraw()

    def get_total_duration_frames(self) -> int:
        max_frame = 0
        for track in self.tracks:
            for clip in track.clips:
                max_frame = max(max_frame, clip.end_frame)
        return max_frame

    def frame_to_x(self, frame: float) -> float:
        return TRACK_LABEL_WIDTH + RULER_HEIGHT + frame * self.pixels_per_frame

    def x_to_frame(self, x: float) -> float:
        return max(0, (x - TRACK_LABEL_WIDTH - RULER_HEIGHT) / self.pixels_per_frame)

    def get_all_clips(self) -> list[tuple[int, Clip]]:
        """返回所有 (track_index, clip) 对"""
        result = []
        for track in self.tracks:
            for clip in track.clips:
                result.append((track.index, clip))
        return result

    def to_dict(self) -> list:
        """序列化轨道状态"""
        result = []
        for track in self.tracks:
            track_data = {
                "index": track.index,
                "name": track.name,
                "clips": [],
            }
            for clip in track.clips:
                track_data["clips"].append(clip.to_clip_data(track.index).__dict__)
            result.append(track_data)
        return result

    def load_from_dict(self, data: list):
        """从字典恢复轨道状态"""
        self.tracks.clear()
        for td in data:
            track = Track(index=td.get("index", 0), name=td.get("name", "T1"))
            for cd in td.get("clips", []):
                clip_data = ClipData(**cd)
                color = self._next_color()
                track.clips.append(Clip.from_clip_data(clip_data, color))
            self.tracks.append(track)
        if not self.tracks:
            self.tracks = [Track(index=0, name="T1")]
        self._update_max_frame()
        self._redraw()

    # ── 绘制 ──

    def _redraw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w <= 1 or h <= 1:
            return

        self._draw_ruler(w)
        self._draw_tracks(w, h)
        self._draw_playhead(h)

    def _draw_ruler(self, w: int):
        """绘制顶部时间标尺"""
        self.create_rectangle(TRACK_LABEL_WIDTH, 0, w, RULER_HEIGHT, fill=THEME["ruler_bg"], outline="")

        total_frames = self._max_frame
        step = self._calc_ruler_step()

        frame = 0
        while frame <= total_frames:
            x = self._frame_to_x_safe(frame)
            if x > w:
                break
            is_major = (frame % (step * 5) == 0)
            tick_h = RULER_HEIGHT - 4 if is_major else RULER_HEIGHT - 8
            self.create_line(x, RULER_HEIGHT - tick_h, x, RULER_HEIGHT,
                             fill=THEME["ruler_major_fg"] if is_major else THEME["ruler_minor_fg"], width=1)
            if is_major:
                sec = frame / FRAME_RATE
                self.create_text(x, 4, text=f"{sec:.2f}s",
                                 fill=THEME["ruler_text_fg"], font=("Consolas", 7), anchor="nw")
            frame += step

    def _draw_playhead(self, h: int):
        """绘制播放指针"""
        x = self._frame_to_x_safe(self.playhead_frame)
        self.create_polygon(
            x - 5, 0, x + 5, 0, x, 8,
            fill=THEME["playhead_fg"], outline="")
        self.create_line(x, RULER_HEIGHT, x, h, fill=THEME["playhead_fg"], width=1, dash=(3, 3))

    def _draw_tracks(self, w: int, h: int):
        """绘制所有轨道和 clip"""
        y = RULER_HEIGHT - self._scroll_y

        # 左侧固定标签栏背景
        self.create_rectangle(0, RULER_HEIGHT, TRACK_LABEL_WIDTH, h,
                              fill=THEME["ruler_bg"], outline="")

        for track in self.tracks:
            if y + TRACK_HEIGHT < RULER_HEIGHT:
                # Track is above visible area, skip drawing but advance y
                y += TRACK_HEIGHT
                continue
            if y > h:
                break

            # ── 左侧轨道标签 ──
            is_track_selected = (self.selected_track_idx == track.index)
            label_color = THEME["track_selected_fg"] if is_track_selected else THEME["track_label_fg"]
            label_bg = THEME["track_selected_bg"] if is_track_selected else THEME["ruler_bg"]
            
            # Draw track label background with highlight if selected
            self.create_rectangle(0, y, TRACK_LABEL_WIDTH, y + TRACK_HEIGHT,
                                  fill=label_bg, outline="")
            self.create_text(TRACK_LABEL_WIDTH // 2, y + TRACK_HEIGHT // 2,
                             text=f"T{track.index + 1}", fill=label_color,
                             font=("", 8, "bold"), anchor="center")

            # ── 轨道区域（clip 区域）──
            track_bg = self._get_track_bg(track.index)
            # Highlight track area if selected
            if is_track_selected:
                track_bg = self._lighten(track_bg, 0.15)
            # Fix: Limit track background to canvas width, not extending beyond
            bg_end_x = min(w, TRACK_LABEL_WIDTH + RULER_HEIGHT + self._max_frame * self.pixels_per_frame + 50)
            self.create_rectangle(TRACK_LABEL_WIDTH, y, bg_end_x, y + TRACK_HEIGHT,
                                  fill=track_bg, outline=THEME["track_border"], width=1)

            for clip in track.clips:
                self._draw_clip(clip, track.index, y)

            y += TRACK_HEIGHT

        if y + 20 < h:
            self.create_text((TRACK_LABEL_WIDTH + w) // 2, y + 10, text="+ Add Track",
                             fill=THEME["add_track_fg"], font=("", 8), tags="add_track")

    def _draw_clip(self, clip: Clip, track_idx: int, track_y: int):
        """绘制单个 clip（名称 + level 标签 + effect 指示）"""
        x1 = self._frame_to_x_safe(clip.start_frame)
        x2 = self._frame_to_x_safe(clip.end_frame)

        if x2 - x1 < CLIP_MIN_WIDTH:
            x2 = x1 + CLIP_MIN_WIDTH

        y1 = track_y + 2
        y2 = track_y + TRACK_HEIGHT - 2

        is_selected = (self._selected_clip == (track_idx, clip))

        # clip 背景
        fill = clip.color if not is_selected else self._lighten(clip.color)
        outline = THEME["clip_selected_outline"] if is_selected else THEME["clip_default_outline"]
        outline_w = 2 if is_selected else 1

        self.create_rectangle(x1, y1, x2, y2,
                              fill=fill, outline=outline, width=outline_w,
                              tags=("clip", f"clip_{track_idx}_{id(clip)}"))

        has_effects = clip.effect.has_custom_effects()

        # ── 名称（左）+ 时长（右）──
        mid_y = (y1 + y2) // 2
        dur_sec = clip.length_frames / FRAME_RATE
        name_text = clip.persona_name[:10]
        label_text = f"{name_text} {dur_sec:.1f}s"
        text_fg = self._contrast_text(fill)
        self.create_text(x1 + 6, mid_y, text=label_text,
                         fill=text_fg, font=("", 9, "bold"), anchor="w")
        info_text = f"W:{clip.weight:.1f}"
        # Info text slightly dimmer than name
        info_fg = self._contrast_text(self._darken(fill, 0.15) if not is_selected else fill)
        self.create_text(x2 - 4, mid_y, text=info_text,
                         fill=info_fg, font=("Consolas", 8, "bold"), anchor="e")

        # ── Effect 指示（仅在有自定义 effect 时显示，作为小标记）──
        if has_effects:
            indicators = []
            norm = clip.effect.normalize
            if norm is not None:
                indicators.append(("N", "\u2713" if norm else "\u25CB",
                                   THEME["clip_effect_normal_on"] if norm else THEME["clip_effect_normal_off"]))
            dns = clip.effect.denoise
            if dns is not None:
                sym = "\u2713" if dns else "\u25CB"
                indicators.append(("D", sym,
                                   THEME["clip_effect_normal_on"] if dns else THEME["clip_effect_normal_off"]))

            pitch = clip.effect.pitch_shift
            if pitch != 0.0:
                arrow = "\u25B2" if pitch > 0 else "\u25BC"
                indicators.append((f"{arrow}{pitch:+.1f}", None,
                                   THEME["clip_effect_pitch_up"] if pitch > 0 else THEME["clip_effect_pitch_down"]))

            ex = x1 + 6
            ey = y2 - 6
            for label, sym, color in indicators:
                text = f"{label} {sym}" if sym else label
                self.create_text(ex, ey, text=text,
                                 fill=color, font=("Consolas", 7), anchor="w")
                ex += len(text) * 4 + 3

        # 左右拖拽手柄（仅选中时显示）
        if is_selected:
            self.create_rectangle(x1, y1, x1 + HANDLE_WIDTH, y2,
                                  fill=THEME["clip_handle_fill"], outline="",
                                  tags="handle_left")
            self.create_rectangle(x2 - HANDLE_WIDTH, y1, x2, y2,
                                  fill=THEME["clip_handle_fill"], outline="",
                                  tags="handle_right")

    # ── 事件处理 ──

    def _on_click(self, event):
        self.focus_set()
        x, y = event.x, event.y

        # 检查是否点击在左侧标签栏区域 → 选择轨道
        if TRACK_LABEL_WIDTH <= x < TRACK_LABEL_WIDTH + RULER_HEIGHT and y >= RULER_HEIGHT:
            adjusted_y = y + self._scroll_y
            track_idx = int((adjusted_y - RULER_HEIGHT) / TRACK_HEIGHT)
            if 0 <= track_idx < len(self.tracks):
                self._selected_clip = None
                self._select_track(track_idx)
                self._redraw()
            return

        # 检查是否点击在 ruler 区域（设置 playhead / 开始拖拽 playhead）
        if y < RULER_HEIGHT and x >= TRACK_LABEL_WIDTH:
            frame = self.x_to_frame(x)
            self.playhead_frame = frame
            self._dragging = {"type": "playhead"}
            self._redraw()
            return

        # 检查是否点击 add track
        if self.find_closest(x, y) and self.gettags(self.find_closest(x, y)):
            tags = self.gettags(self.find_closest(x, y))
            if "add_track" in tags:
                self.add_track()
                return

        # 检查是否点击了 clip 或 handle
        track_idx, clip, hit_type = self._hit_test(x, y)

        if clip:
            self._selected_clip = (track_idx, clip)
            self._select_track(track_idx)

            if hit_type == "handle_left":
                self._dragging = {
                    "type": "resize_l",
                    "clip": clip,
                    "track_idx": track_idx,
                    "orig_start": clip.start_frame,
                    "orig_length": clip.length_frames,
                }
            elif hit_type == "handle_right":
                self._dragging = {
                    "type": "resize_r",
                    "clip": clip,
                    "track_idx": track_idx,
                    "orig_start": clip.start_frame,
                    "orig_length": clip.length_frames,
                }
            else:
                frame_at_x = self.x_to_frame(x)
                self._dragging = {
                    "type": "move",
                    "clip": clip,
                    "track_idx": track_idx,
                    "offset_frame": frame_at_x - clip.start_frame,
                }
        else:
            self._selected_clip = None
            # Click on empty track area → select that track
            if 0 <= track_idx < len(self.tracks):
                self._select_track(track_idx)

        self._redraw()

    def _on_drag(self, event):
        if not self._dragging:
            return

        x = event.x
        d = self._dragging

        if d["type"] == "playhead":
            if event.x >= TRACK_LABEL_WIDTH:
                self.playhead_frame = max(0, self.x_to_frame(event.x))
            self._redraw()
            return

        clip = d["clip"]

        if d["type"] == "move":
            frame = self.x_to_frame(x)
            new_start = max(0, int(frame - d["offset_frame"]))

            # 检测是否拖到了不同轨道
            y = event.y
            adjusted_y = y + self._scroll_y
            new_track_idx = max(0, (adjusted_y - RULER_HEIGHT) // TRACK_HEIGHT)
            new_track_idx = min(new_track_idx, len(self.tracks) - 1)
            old_track_idx = d["track_idx"]

            if new_track_idx != old_track_idx:
                # 从旧轨道移除，加入新轨道
                old_track = self.tracks[old_track_idx]
                if clip in old_track.clips:
                    old_track.clips.remove(clip)
                new_track = self.tracks[new_track_idx]
                new_track.clips.append(clip)
                d["track_idx"] = new_track_idx
                self._selected_clip = (new_track_idx, clip)
                self._select_track(new_track_idx)

            clip.start_frame = new_start

        elif d["type"] == "resize_l":
            frame = self.x_to_frame(x)
            new_start = max(0, int(frame))
            new_length = d["orig_start"] + d["orig_length"] - new_start
            if new_length >= 5:
                clip.start_frame = new_start
                clip.length_frames = new_length

        elif d["type"] == "resize_r":
            frame = self.x_to_frame(x)
            new_end = max(clip.start_frame + 5, int(frame))
            clip.length_frames = new_end - clip.start_frame

        self._update_max_frame()
        self._redraw()

    def _on_release(self, event):
        # Snap to original length if close
        if self._dragging and self._selected_clip:
            _, clip = self._selected_clip
            d = self._dragging
            if d["type"] in ("resize_l", "resize_r"):
                orig_pixels = clip.original_length_frames * self.pixels_per_frame
                cur_pixels = clip.length_frames * self.pixels_per_frame
                if abs(orig_pixels - cur_pixels) < 8:
                    clip.length_frames = clip.original_length_frames
                    if d["type"] == "resize_l":
                        clip.start_frame = d["orig_start"] + d["orig_length"] - clip.original_length_frames
                    self._redraw()
        self._dragging = None

    def _get_arrow_step(self) -> float:
        """根据当前选中 clip 的 fusion level 计算箭头步进（帧数）"""
        step = 1.0  # 默认 1 MiMi frame
        if self._selected_clip:
            _, clip = self._selected_clip
            ratio = _LEVEL_FRAME_RATIOS.get(clip.fusion_level, 1)
            step = 1.0 / ratio  # 1 个该 level 单元 = 1/ratio track frames
        return step

    def _on_key_left(self, event):
        step = self._get_arrow_step()
        self.playhead_frame = max(0, self.playhead_frame - step)
        self._redraw()

    def _on_key_right(self, event):
        step = self._get_arrow_step()
        self.playhead_frame = min(self._max_frame, self.playhead_frame + step)
        self._redraw()

    def _on_key_delete(self, event):
        """Delete key: delete selected clip or selected track"""
        # If a clip is selected, delete the clip
        if self._selected_clip:
            track_idx, clip = self._selected_clip
            self.remove_clip(track_idx, clip)
            return
        
        # If no clip but a track is selected, delete the track
        if self.selected_track_idx is not None and len(self.tracks) > 1:
            self.remove_track(self.selected_track_idx)

    def _on_double_click(self, event):
        track_idx, clip, _ = self._hit_test(event.x, event.y)
        if clip and self.on_clip_double_click:
            self.on_clip_double_click(track_idx, clip)

    def _on_right_click(self, event):
        track_idx, clip, _ = self._hit_test(event.x, event.y)
        if clip and self.on_clip_right_click:
            self.on_clip_right_click(event, track_idx, clip)

    def _on_scroll(self, event):
        """滚轮：ruler区域=缩放，其他=垂直滚动看更多轨道"""
        if event.y < RULER_HEIGHT and event.x >= TRACK_LABEL_WIDTH:
            # Hover over ruler → zoom
            if event.num == 4 or (hasattr(event, 'delta') and event.delta > 0):
                self.pixels_per_frame = min(20, self.pixels_per_frame * 1.15)
            elif event.num == 5 or (hasattr(event, 'delta') and event.delta < 0):
                self.pixels_per_frame = max(0.5, self.pixels_per_frame / 1.15)
            self._redraw()
        else:
            # Vertical scroll
            total_h = RULER_HEIGHT + len(self.tracks) * TRACK_HEIGHT + 40
            canvas_h = self.winfo_height()
            max_scroll = max(0, total_h - canvas_h)
            if event.num == 4 or (hasattr(event, 'delta') and event.delta > 0):
                self._scroll_y = max(0, self._scroll_y - 30)
            elif event.num == 5 or (hasattr(event, 'delta') and event.delta < 0):
                self._scroll_y = min(max_scroll, self._scroll_y + 30)
            self._redraw()

    def _on_configure(self, _event):
        # Debounce frequent resize events to reduce repaint churn.
        if self._resize_redraw_after_id is not None:
            try:
                self.after_cancel(self._resize_redraw_after_id)
            except tk.TclError:
                pass
        self._resize_redraw_after_id = self.after(16, self._redraw_after_resize)

    def _redraw_after_resize(self):
        self._resize_redraw_after_id = None
        self._redraw()

    # ── 辅助 ──

    def _hit_test(self, x: float, y: float) -> tuple[int, Optional[Clip], str]:
        """
        测试点击命中的 clip。
        返回 (track_index, clip_or_None, hit_type)
        hit_type: "clip" | "handle_left" | "handle_right"
        """
        if y < RULER_HEIGHT or x < TRACK_LABEL_WIDTH:
            return -1, None, ""

        # Adjust y by scroll offset
        adjusted_y = y + self._scroll_y
        track_idx = int((adjusted_y - RULER_HEIGHT) / TRACK_HEIGHT)
        if track_idx < 0 or track_idx >= len(self.tracks):
            return -1, None, ""

        track = self.tracks[track_idx]
        frame_at_x = self.x_to_frame(x)

        for clip in track.clips:
            cx1 = self._frame_to_x_safe(clip.start_frame)
            cx2 = self._frame_to_x_safe(clip.end_frame)
            if cx2 - cx1 < CLIP_MIN_WIDTH:
                cx2 = cx1 + CLIP_MIN_WIDTH

            if cx1 <= x <= cx2:
                if self._selected_clip == (track_idx, clip):
                    if x - cx1 <= HANDLE_WIDTH:
                        return track_idx, clip, "handle_left"
                    if cx2 - x <= HANDLE_WIDTH:
                        return track_idx, clip, "handle_right"
                return track_idx, clip, "clip"

        return track_idx, None, ""

    def _frame_to_x_safe(self, frame: float) -> float:
        return TRACK_LABEL_WIDTH + RULER_HEIGHT + frame * self.pixels_per_frame

    def _get_track_bg(self, track_idx: int) -> str:
        """基于当前 preset level 返回轨道背景色，奇偶轨道做轻微明暗区分。"""
        palette = THEME.get("track_level_palette") or THEME.get("level_palette", {})
        base = palette.get(self._preset_level, THEME["track_even_bg"])
        return self._lighten(base, 0.04) if track_idx % 2 == 0 else self._darken(base, 0.06)

    def _update_max_frame(self):
        self._max_frame = max(500, self.get_total_duration_frames() + 100)

    def _calc_ruler_step(self) -> int:
        """根据缩放级别计算合适的刻度间隔"""
        pixels_per_step = 60
        step = max(1, int(pixels_per_step / self.pixels_per_frame))
        # Round to nice numbers
        for nice in [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]:
            if nice >= step:
                return nice
        return step

    def _next_color(self) -> str:
        color = COLORS[self._color_index % len(COLORS)]
        self._color_index += 1
        return color

    @staticmethod
    def _lighten(hex_color: str, factor: float = 0.3) -> str:
        """提亮颜色"""
        hex_color = hex_color.lstrip("#")
        r, g, b = [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]
        r = min(255, int(r + (255 - r) * factor))
        g = min(255, int(g + (255 - g) * factor))
        b = min(255, int(b + (255 - b) * factor))
        return f"#{r:02x}{g:02x}{b:02x}"

    @staticmethod
    def _darken(hex_color: str, factor: float = 0.3) -> str:
        """加深颜色"""
        hex_color = hex_color.lstrip("#")
        r, g, b = [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]
        r = max(0, int(r * (1 - factor)))
        g = max(0, int(g * (1 - factor)))
        b = max(0, int(b * (1 - factor)))
        return f"#{r:02x}{g:02x}{b:02x}"

    @staticmethod
    def _contrast_text(hex_color: str) -> str:
        """Return black or white text color depending on bg luminance."""
        hex_color = hex_color.lstrip("#")
        r, g, b = [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]
        # Perceived luminance (relative)
        lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return "#111111" if lum > 0.55 else "#ffffff"
