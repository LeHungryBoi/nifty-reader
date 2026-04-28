# architecture.md — 代码库结构

> 简洁的目录结构和依赖库说明。

## 项目结构

```
nifty-reader/
├── main.go              # Fyne 应用入口
├── pkg/
│   ├── core/            # 核心业务逻辑
│   │   ├── state.go     # 状态持久化 (导出 models 类型别名)
│   │   ├── api/         # 网络请求、HTML 解析
│   │   ├── models/      # 数据结构定义
│   │   └── snippet/     # 搜索结果摘要解析
│   ├── ui/              # UI 组件 (Fyne)
│   └── tts/             # 语音合成 (sherpa-onnx)
├── scripts/             # 构建脚本
└── assets/              # 静态资源
```

## 核心依赖库

| 包 | 用途 | 库 |
|---|---|---|
| `core` | 状态管理 | `encoding/json`, `github.com/adrg/xdg` |
| `core/api` | 网络 + 解析 | `net/http`, `github.com/PuerkitoBio/goquery` |
| `core/models` | 数据结构 | — |
| `core/snippet` | 摘要高亮 | `regexp` |
| `ui` | GUI | `fyne.io/fyne/v2` |
| `tts` | 语音合成 | `github.com/k2-fsa/sherpa-onnx-go`, `github.com/ebitengine/oto/v3` |

## 官方参考

| 库 | 路径 | 说明 |
|---|---|---|
| PocketTTS (官方 Python) | `spec/com_spec/pocket-tts/` | `kyutai-labs/pocket-tts` 官方仓库浅克隆，供 TTS 开发参考 |
