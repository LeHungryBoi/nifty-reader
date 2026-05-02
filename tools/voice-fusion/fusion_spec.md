# Fusion Studio Spec

改动代码后用 py_compile 检查错误。修改或增加依赖后自动pip安装.

## 架构

```
tools/voice-fusion/
├── gui.py               # 主入口，窗口布局、快捷键、音频闪避
├── gui_base.py          # 共享常量、懒加载、re-export
├── gui_pool.py          # Persona Pool 面板（左侧）
├── gui_toolbar.py       # 工具栏（顶部）
├── gui_fusion.py        # 融合生成逻辑
├── gui_effect_panel.py  # Clip Effect 面板
├── gui_tts_compare.py   # TTS 对比播放（f32 vs int8）
├── track_editor.py      # 多轨道时间线编辑器
├── hotkey.py            # 三级优先级快捷键管理器
├── audio_duck.py        # 播放时自动降低其他程序音量（pycaw）
├── theme.py             # 颜色主题系统
├── fusion.py            # voice state 融合算法
├── level_extractor.py   # 7 级特征提取
├── persona.py           # Persona 管理 + 衍生文件缓存
├── preprocess.py        # ffmpeg 音频预处理
├── preset.py            # Preset / FuseSona 保存加载
├── settings.py          # 设置持久化
└── run.py               # 开发用：文件变动自动重启
```

## 融合层级（Level 1-7）

```
mimi encoder 内部:
  1. Raw Audio — 原始波形 24kHz
  2. SEANet Features — 卷积声学特征 512维 200Hz
  3. Encoder Attn — self-attention 512维 200Hz
  4. MiMi Latent — codec 压缩 32维 12.5Hz
  5. (transpose，纯格式转换)
mimi 外部:
  6. Speaker Proj — 线性投射 1024维
  7. FlowLM KV Cache — LM 处理后记忆
```

## 音频预处理

全局（工具栏）→ clip 级可覆盖：

```
原始音频 → [mono → 24kHz → denoise → normalize] → processed.wav
                                                    ↓
                                        [clip effect: pitch_shift 等]
                                                    ↓
                                         {name}.effect_{hash}.wav
                                                    ↓
                                           特征提取 (level 1-7)
```

| Effect | 范围 | 默认 |
|---|---|---|
| normalize | on/off | 跟随全局 |
| denoise | on/off | 跟随全局 |
| denoise_strength | 0.1 - 1.0 | 0.3 |
| pitch_shift | -12.0 ~ +12.0 st | 0.0 |

## Persona / Voice Library

- Persona = `assets/voices/` 下的音频文件，名称 = 文件名，子目录 = namespace
- 衍生文件：`{name}.processed.wav`、`{name}.level{N}.npy` 等，与原始音频同目录
- 以原始音频 modify time 判断过期，过期自动重新生成

## Track 编辑器

视频编辑风格多轨道视图。Clip 操作：拖放、移动、伸缩、分割(s)、裁剪(t)。

Clip 显示：名称 + 权重 + level 标签 + effect 指示行（仅非默认时显示）。

## TTS 对比

f32（原版）vs int8（量化）并排对比播放，共用 f32 编码的 voice state。

## Preset 选项卡

最多 12 个（F1-F12 切换），每个独立保存轨道状态。支持 JSON 保存/加载、FuseSona 导出。

## 快捷键（hotkey.py）

优先级：文本框打字 > 当前页面 > 全局。文本框获焦时普通字母键穿透，不触发任何快捷键。

| 全局 | 功能 |
|---|---|
| F1-F12 | 切换 Preset 选项卡 |
| Space | 播放 f32 |
| Shift+Space | 播放 int8 |

| Track 页面 | 功能 |
|---|---|
| s | Split at playhead |
| t | Trim clip |

## 音频闪避（audio_duck.py）

播放前自动将其他程序音量降至 15%（`DUCK_FACTOR`），播放结束恢复。通过 pycaw 枚举 Windows audio session。不可用时静默降级。

## 主题系统（theme.py）

语义化键名 dict，换主题 = 换 dict。所有 UI 颜色集中管理，不硬编码。
