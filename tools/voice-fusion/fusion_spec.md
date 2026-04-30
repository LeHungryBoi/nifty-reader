# Voice Fusion Spec

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

pocketTTS 克隆音源预处理需求：单声道、24kHz、音量 Normalization、Denoise。

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

### 5.4 Clip 属性

- 每个 clip 可独立设置 **weight**（融合权重），默认 1.0。
- 可选择融合的 **level**（对应 7 个融合层级之一）。
- clip 上显示 Persona 名称和波形缩略图。

## 6. TTS 对比播放

### 6.1 双模型对比

- 提供 **side-by-side** 对比播放功能。
- 两个播放按钮，分别标记为 **f32**（原版 float32 模型）和 **int8**（quantized int8 模型）。
- 声音特征编码统一使用原版 f32 模型，int8 模型仅用于 TTS 合成播放。

### 6.2 输入

- 文本输入框，输入要合成的测试文本。
- 可加载保存的 preset（见 §7）。

## 7. Preset / FuseSona 保存

### 7.1 Preset

- 保存/加载当前轨道编辑器的完整状态（所有 clip 位置、权重、level、Persona 配置）。
- 文件格式：JSON。
- 存储路径：`assets/fused/presets/`。

### 7.2 FuseSona

- 将当前融合结果导出为一个独立的 "FuseSona" 配置。
- FuseSona 包含：融合后的 voice state（指定 level 的特征数据）、元信息（创建时间、源 Persona 列表、权重比例）。
- 可作为 Persona 在未来会话中直接使用。
- 存储路径：`assets/fused/fusesonas/`。

## 8. 整体布局

```
┌─────────────────────────────────────────────────────┐
│                     工具栏                            │
│  [加载Preset] [保存Preset] [导出FuseSona] [设置]       │
├──────────────┬──────────────────────────────────────┤
│              │                                      │
│  Persona     │         Track 编辑器                  │
│  Pool        │                                      │
│  (左侧)      │    ┌─────────────────────────┐       │
│              │    │  时间轴 / playhead        │       │
│  [搜索/筛选]  │    ├─────────────────────────┤       │
│              │    │  Track 1: ═══PersonaA═══ │       │
│  ☐ alba      │    │  Track 2: ══PersonaB══  │       │
│    ▶ raw     │    │  Track 3: ═PersonaC═══  │       │
│    ▶ proc    │    └─────────────────────────┘       │
│  ☐ bad       │                                      │
│  ☑ omni      ├──────────────────────────────────────┤
│  ☑ hq        │       TTS 对比播放                    │
│  ...         │  [测试文本输入框]                       │
│              │  [▶ f32 播放]  [▶ int8 播放]            │
│              │  [波形可视化 / 进度条]                   │
├──────────────┴──────────────────────────────────────┤
│                     状态栏                            │
└─────────────────────────────────────────────────────┘
```
