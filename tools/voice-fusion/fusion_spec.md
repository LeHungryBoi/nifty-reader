# Voice Fusion Spec

改动代码后用py_compile检查错误

## 1. 融合层级

用户可选择在 Mimi encoder 内部的不同层级进行融合：

语音特征编码 All 7 Level（数据处理顺序 1→7）：

```
mimi encoder 内部:
  1. Raw Audio — 原始波形 24kHz
  2. SEANet Features — 卷积提取的声学特征 512维 200Hz
  3. Encoder Attn — self-attention 上下文增强 512维 200Hz
  4. MiMi Latent — codec 压缩的声音指纹 32维 12.5Hz
  5. (transpose，纯格式转换，不命名)
mimi 外部:
  6. Speaker Proj — 线性投射到 LM 空间 1024维
  7. FlowLM KV Cache — 语言模型处理后的记忆
```

## 2. 数据流

```
编码（参考音频 → voice state）：
  Raw Audio [B,1,T] 24kHz
    → SEANet Features [B,512,T/120] 200Hz
    → Encoder Attn [B,512,T/120]
    → MiMi Latent [B,32,T/1200] 12.5Hz
    → transpose [B,T/1200,32]
    → Speaker Proj [B,T/1200,1024]
    → FlowLM KV Cache (每层 cache: [2,1,seq_len,heads,dim])
```

## 3. 音频预处理

pocketTTS 克隆音源预处理需求：单声道、24kHz。

### 3.1 全局预处理选项（工具栏）

在工具栏提供全局开关，影响所有新导入的 Persona 的预处理流程：

| 选项 | 默认 | 说明 |
|---|---|---|
| **Normalize** | 开 | 音量归一化（loudnorm -3dB） |
| **Denoise** | 开 | 降噪（afftdn，可调强度 0.1-1.0） |

预处理管线（ffmpeg）：mono → 24kHz resample → [denoise] → [normalize] → PCM16 WAV 缓存。

### 3.2 Clip 级 Effect（per-clip，应用到 WAV 音频）

每个 Track 上的 Clip 可独立启用/禁用以下效果，**覆盖全局预处理设置**。
所有 effect 均直接应用到 **预处理后的 WAV 音频**上，生成带 effect 的衍生 WAV 缓存，
再从该缓存进行特征提取。

完整处理管线：

```
原始音频 → [全局预处理: mono → 24kHz → denoise → normalize] → processed.wav
                                                                    ↓
                                                       [Clip Effect: pitch_shift 等]
                                                                    ↓
                                                          {name}.effect_{hash}.wav
                                                                    ↓
                                                          特征提取 (level 1-7)
```

| 效果 | 类型 | 范围 | 默认 | 说明 |
|---|---|---|---|---|
| **normalize** | bool | on/off | 跟随全局 | 音量归一化 |
| **denoise** | bool | on/off | 跟随全局 | 降噪 |
| **denoise_strength** | float | 0.1 - 1.0 | 0.3 | 降噪强度 |
| **pitch_shift** | float | -12.0 ~ +12.0 | 0.0 | 半音（semitones）偏移 |

不同的 effect 组合会生成不同的衍生缓存文件（以 effect 参数 hash 作为文件名的一部分），避免重复处理。

**Pitch Shift 实现**（ffmpeg）：

```
rubberband=pitch=(2^(semitones/12))  # 或 asetrate + atempo 组合
```

- 正值 = 音调升高，负值 = 音调降低
- 0.0 = 不变（跳过处理，无额外开销）

## 4. Voice Library（语音库）

### 4.1 Persona 定义

- 每个 **Persona** 以 `assets/voices/`（及子文件夹）下的一个 wav 原始音频文件为身份标识。
- Persona 名称 = 音频文件名（不含扩展名），子文件夹路径作为命名空间（如 `v2/bad_coolhat`）。

### 4.2 自动文件管理

系统为每个 Persona 自动管理以下衍生文件，与原始音频存放于同一目录下：

```
voices/
├── alba.wav                          # 原始音频（用户面向的标记）
├── alba.processed.wav                # 预处理后的 wav
├── alba.level1.npy                   # SEANet Features
├── alba.level2.npy                   # Encoder Attn
├── alba.level3.npy                   # MiMi Latent
├── alba.level4.npy                   # transpose
├── alba.level5.npy                   # Speaker Proj
└── v2/                               # 子文件夹同理
    └── bad_coolhat.wav
        ├── bad_coolhat.processed.wav
        ├── bad_coolhat.level1.npy
        └── ...
```

### 4.3 版本管理

- 以原始音频文件的 **modify time** 作为版本标识。
- 当原始音频的 modify time 发生变化时，所有衍生文件标记为过期，下次使用时自动重新生成。
- 扫描 `assets/voices/` 时自动发现新增/删除的 Persona。

### 4.4 Persona Pool（左侧面板）

- Media pool 形式展示所有已扫描到的 Persona。
- 每个 Persona 卡片显示：名称、原始波形缩略图、时长。
- **Preview 按钮**：
  - 播放原始音频（raw）
  - 播放预处理后的音频（processed）
- 支持搜索/筛选。

## 5. Track 编辑器（右侧面板）

视频编辑软件风格的轨道视图，用于可视化和操控 Persona 的融合。

### 5.1 轨道结构

- 多条水平轨道，每条轨道可放置一个或多个 Persona 片段（clip）。
- 每个 clip 代表一个 Persona 的某段声音特征区间。
- clip 之间可重叠，重叠区域表示多个 Persona 的特征将按权重融合。

### 5.2 基本操作

| 操作 | 说明 |
|---|---|
| **拖放** | 从左侧 Persona Pool 拖入轨道创建 clip |
| **移动** | 拖动 clip 改变时间位置 |
| **调整长度** | 拖动 clip 边缘伸缩（通过插值调整特征长度） |
| **分割** | 将 clip 分割为两段 |
| **删除** | 移除 clip |

### 5.3 时间轴

- 顶部时间标尺，可缩放（zoom in/out）。
- 播放指针（playhead），可拖动定位。
- 时间单位为帧（frame），对应 MiMi Latent 的 12.5Hz 帧率。

### 5.4 Clip 视觉表示

每个 clip 在轨道上显示以下信息：

```
┌─────────────────────────────────────┐
│ PersonaA          W:1.0  4-MiMi    │  ← 名称 + 权重 + 融合层级名
│ ▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░ │  ← 权重条形图（长度 ∝ weight）
│ N ✓  D ═══●═══ 0.3    ▲ +3.0     │  ← Effect 指示行（仅自定义时显示）
└─────────────────────────────────────┘
```

**第一行（标题行）**：
- Persona 名称
- `W:` 权重值
- 融合层级名称（如 `4-MiMi`、`7-KVCache`），对应 §1 中的 7 个层级

**第二行（权重条形图）**：
- 填充条长度与 weight 成正比（weight 0.1~3.0 映射到 30%~100% 宽度）
- 颜色为 clip 背景色的加深版本

**第三行（Effect 指示行）**：
- `N ✓` — Normalize 开启时显示 ✓（关闭时灰色 ○）
- `D ═══●═══ 0.3` — Denoise 开启时显示小进度条 + 数值（强度 0.1-1.0）；关闭时灰色 `D ○`
- `▲ +3.0` / `▼ -2.0` — Pitch Shift 值：正值显示上箭头（音调升高），负值显示下箭头（音调降低），0.0 时不显示
- Effect 指示行**仅在有非默认 effect 时显示**，无自定义 effect 时隐藏以保持 clip 简洁

### 5.4.1 Clip 属性

- 每个 clip 可独立设置 **weight**（融合权重），默认 1.0。
- 可选择融合的 **level**（对应 7 个融合层级之一）。
- Effect 指示行实时反映 clip 当前的 effect 设置（见 §3.2）。

### 5.5 Clip Effect 面板

选中 clip 时，在轨道编辑器下方展开 Effect 面板：

```
┌─ Clip Effects: bad_coolhat ─────────────────────────────┐
│  [✓] Normalize    [✓] Denoise    Strength: ═══●═══ 0.3 │
│  Pitch Shift: ◄══════════●═════════► +3.0 st            │
│                                                         │
│  [Apply]  [Reset to Global]                              │
└─────────────────────────────────────────────────────────┘
```

- **Apply**: 使用当前 effect 设置重新处理 WAV 音频（生成带 effect 的衍生缓存）并重新提取特征
- **Reset to Global**: 恢复为全局预处理设置，清空所有 clip 级覆盖
- Effect 值变化时实时预览（播放按钮播放带 effect 的音频）
- clip 上的 effect 指示行（见 §5.4）实时同步更新

## 6. TTS 对比播放

### 6.1 双模型对比

- 提供 **side-by-side** 对比播放功能。
- 两个播放按钮，分别标记为 **f32**（原版 float32 模型）和 **int8**（quantized int8 模型）。
- 声音特征编码统一使用原版 f32 模型，int8 模型仅用于 TTS 合成播放。

### 6.2 输入

- 文本输入框，输入要合成的测试文本。
- 可加载保存的 preset（见 §7）。

## 7. Preset 选项卡 / FuseSona

### 7.1 选项卡设计

轨道编辑器上方提供**多选项卡**界面，每个选项卡对应一组独立的轨道状态：

```
[+][-] [F1: Preset 1] [F2: Preset 2] [F3: Preset 3]    [Save] [Load] [Export FuseSona]
```

- `+` / `-` 按钮：添加/移除选项卡（至少保留 1 个）。
- 切换选项卡时自动保存当前轨道状态到旧选项卡、加载新选项卡状态。
- 选项卡按钮上显示对应的 Fn 快捷键（F1-F12，最多 12 个选项卡）。

### 7.2 Fn 快捷键

| 快捷键 | 功能 |
|---|---|
| **F1** ~ **F12** | 切换到对应编号的选项卡 |
| **Space** | 播放 int8 音频 |
| **Shift + Space** | 播放 f32 音频 |

Space 和 Shift+Space 为全局快捷键，无需焦点在特定控件上即可触发。

### 7.3 Preset 保存/加载

- **Save**: 将当前选项卡的轨道状态保存为 JSON 文件（`assets/fused/presets/`）。
- **Load**: 从文件加载预设到当前选项卡。
- 保存内容：所有 clip 位置、权重、level、effect 设置、Persona 配置。

### 7.4 FuseSona 导出

- 将当前融合结果导出为独立的 "FuseSona" 配置。
- FuseSona 包含：融合后的 voice state（指定 level 的特征数据）、元信息（创建时间、源 Persona 列表、权重比例、effect 设置）。
- 可作为 Persona 在未来会话中直接使用。
- 存储路径：`assets/fused/fusesonas/`。

## 8. 整体布局

```
┌──────────────────────────────────────────────────────────┐
│ 工具栏                                    [Theme: Dark v] │
│ [语言][设备][模型] │ [✓Norm] [✓Denoise] [Str] [Rescan]   │
│                   │ [Settings]                            │
├──────────────┬───────────────────────────────────────────┤
│              │ [+][-] [F1:Preset1] [F2:Preset2] [Save].. │
│  Persona     ├───────────────────────────────────────────┤
│  Pool        │          Track 编辑器                      │
│  (左侧)      │   ┌───────────────────────────┐           │
│              │   │  时间轴 / playhead          │           │
│  [搜索/筛选]  │   ├───────────────────────────┤           │
│              │   │  Track 1: ══PersonaA════   │           │
│  ☐ alba      │   │  Track 2: ═PersonaB══     │           │
│    ▶ raw     │   │  Track 3: ═══PersonaC═══  │           │
│    ▶ proc    │   └───────────────────────────┘           │
│  ☐ bad       │                                           │
│  ☑ omni      ├───────────────────────────────────────────┤
│  ☑ hq        │   Clip Effect Panel (选中 clip 时展开)      │
│  ...         │   [✓Norm] [✓Denoise] Str:___ Pitch:+3.0st  │
│              │   [Apply] [Reset to Global]                 │
│              ├───────────────────────────────────────────┤
│              │          TTS 对比播放                       │
│              │   [测试文本输入框]                            │
│              │   [▶ f32 播放]  [▶ int8 播放]                │
│              │   [波形可视化 / 进度条]                       │
├──────────────┴───────────────────────────────────────────┤
│                        状态栏                             │
└──────────────────────────────────────────────────────────┘
```

## 9. 设置对话框

通过工具栏 **Settings** 按钮打开，以 Notebook 选项卡形式组织：

### 9.1 Proxy 设置

| 选项 | 说明 |
|---|---|
| Enable Proxy | 是否启用 HTTP/SOCKS 代理 |
| Proxy Address | 代理地址，格式 `http://host:port` 或 `socks5://host:port` |

代理设置在模型加载时生效，影响 PocketTTS 模型下载。

## 10. 主题系统

### 10.1 设计

所有 UI 颜色集中在 `theme.py` 中管理，使用语义化键名（如 `track_editor_bg`、`clip_name_fg`）。
各模块通过 `from theme import THEME` 引用颜色值，不直接硬编码色值。

换主题 = 替换一个 dict，零耦合。

### 10.2 主题切换 UI

- 工具栏**右上角**提供 Theme 下拉框，列出所有已注册主题。
- 切换主题时实时刷新所有 UI 元素（Canvas、Log、Pool 卡片等）。
- 主题选择自动保存到 settings，下次启动时恢复。

### 10.3 主题注册

```python
from theme import register_theme, THEMES

# 注册新主题
register_theme("Light", LIGHT_THEME_DICT)

# THEMES 字典自动更新，UI 下拉框下次打开时可见
```

### 10.4 文件结构

```
tools/voice-fusion/
├── theme.py          # 所有颜色定义、主题注册表、加载、ttk.Style 配置
├── gui_base.py       # re-export THEME 和 COLORS
├── gui_pool.py       # 引用 THEME
├── gui.py            # 引用 THEME，调用 apply_theme()，主题切换逻辑
├── track_editor.py   # 引用 THEME
├── gui_effect_panel.py  # 引用 THEME
└── gui_tts_compare.py   # 无硬编码颜色（纯 ttk）
```

### 10.5 使用方式

```python
from theme import THEME, load_theme, apply_theme, get_theme_name, register_theme

# 加载主题
load_theme("Dark")
apply_theme(style)

# 获取当前主题名
name = get_theme_name()  # "Dark"

# 引用颜色
bg = THEME["track_editor_bg"]
```

### 10.6 主题键名参考

| 键名 | 用途 |
|------|------|
| `app_bg` | 整体应用背景 |
| `track_editor_bg` | Track Editor canvas 背景 |
| `track_even_bg` / `track_odd_bg` | 轨道交替背景色 |
| `track_border` / `track_label_fg` | 轨道边框和标签 |
| `ruler_bg` / `ruler_major_fg` / `ruler_minor_fg` / `ruler_text_fg` | 时间标尺 |
| `playhead_fg` | 播放指针颜色 |
| `clip_name_fg` / `clip_info_fg` | clip 内文字颜色 |
| `clip_selected_outline` / `clip_default_outline` | clip 边框 |
| `clip_handle_fill` | clip 拖拽手柄 |
| `clip_effect_pitch_up` / `clip_effect_pitch_down` | pitch 指示颜色 |
| `pool_card_bg` / `pool_card_border` | Persona 卡片 |
| `pool_name_fg` / `pool_name_stale_fg` | Persona 名称颜色 |
| `log_bg` / `log_fg` / `log_cursor` | 日志面板 |
| `clip_palette` | clip 调色板（固定 10 色，不随主题变） |
