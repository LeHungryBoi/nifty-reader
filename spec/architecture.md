# architecture.md — 代码库结构

> 简洁的目录结构和依赖库说明。

## 项目结构

```
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
└── assets/              # 静态资源
```

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
| CALM / Pocket TTS 论文 | `spec/com_spec/CALM-PocketTTS-论文参考.md` | arXiv:2509.06926v3 — Continuous Audio Language Models 论文笔记 |
