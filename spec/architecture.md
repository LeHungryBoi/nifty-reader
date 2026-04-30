# architecture.md — 代码库结构

> 简洁的目录结构和依赖库说明。

## 项目结构

````
nifty-reader/
├── main.go              # Fyne 应用入口
├── pkg/
│   ├── core/            # 核心业务逻辑
│   │   ├── storage/     # 路径管理 + 状态持久化 (exe 同目录便携式部署)
│   │   ├── api/         # 网络请求、HTML 解析、搜索摘要解析
│   │   └── models/      # 数据结构定义
│   ├── ui/              # UI 组件 (Fyne)
│   └── tts/             # 语音合成 (sherpa-onnx)
├── lib/                 # 第三方 DLL (onnxruntime, sherpa-onnx-c-api)
├── scripts/             # 构建脚本
├── assets/              # 静态资源
└── tools/voice-fusion/  # Python 声音融合工具
    ├── gui.py           # 主界面入口 (mixin 组合)
    ├── gui_base.py      # 共享常量、路径、代理、lazy imports
    ├── gui_toolbar.py   # 工具栏构建 mixin
    ├── gui_pool.py      # Persona Pool 面板 mixin
    ├── gui_effect_panel.py # Clip Effect 面板 mixin
    ├── gui_tts_compare.py  # TTS 对比播放 mixin
    ├── gui_fusion.py    # 融合/生成/预设逻辑 mixin
    ├── theme.py         # 颜色主题定义、注册表、加载与切换
    ├── fusion.py        # 融合算法 (align/average)
    ├── settings.py      # 设置持久化 (JSON)
    ├── persona.py       # Voice Library / Persona 管理
    ├── track_editor.py  # 视频编辑风格轨道编辑器 (Canvas)
    ├── preset.py        # Preset / FuseSona 保存加载
    ├── level_extractor.py # 多层级特征提取 (level 1-7)
    ├── preprocess.py    # 音频预处理 (ffmpeg)
    └── assets/voices/   # 用户音频源文件
````

## 核心依赖库

| 包 | 用途 | 库 |
|---|---|---|
| `core` | 路径管理 + 状态管理 | `encoding/json`, `os`, `path/filepath` |
| `core/api` | 网络 + 解析 + 摘要高亮 | `net/http`, `github.com/PuerkitoBio/goquery`, `regexp` |
| `core/models` | 数据结构 | — |
| `ui` | GUI | `fyne.io/fyne/v2` |
| `tts` | 语音合成 | `github.com/k2-fsa/sherpa-onnx-go`, `github.com/ebitengine/oto/v3` |

## 官方参考

| 库 / 资料 | 路径 / 链接 | 说明 |
|---|---|---|
| PocketTTS (官方 Python) | `spec/com_spec/pocket-tts/` | `kyutai-labs/pocket-tts` 官方仓库浅克隆，供 TTS 开发参考 |
| sherpa-onnx (TTS 推理引擎) | `spec/com_spec/sherpa-onnx/` | `k2-fsa/sherpa-onnx` 官方仓库浅克隆，供 TTS 推理引擎开发参考 |
| CALM / Pocket TTS 论文 | `spec/com_spec/ContinuousAudioLanguageModel-arXiv-2509.06926v3/` | arXiv:2509.06926v3 — Continuous Audio Language Models 论文参考 |
