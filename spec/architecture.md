# architecture.md — 代码库结构

> 简洁的目录结构和依赖库说明。

## 项目结构

```
nifty-reader/
├── main.go              # Fyne 应用入口
├── pkg/
│   ├── nifty-ui/        # UI 组件 (Fyne)
│   ├── nifty-core/      # 网络请求、HTML 解析
│   ├── tts/             # 语音合成 (sherpa-onnx)
│   └── core/            # 状态持久化
├── scripts/             # 构建脚本
└── assets/              # 静态资源
```

## 核心依赖库

| 包 | 用途 | 库 |
|---|---|---|
| `nifty-ui` | GUI | `fyne.io/fyne/v2` |
| `nifty-core` | 网络 + 解析 | `net/http`, `github.com/PuerkitoBio/goquery` |
| `tts` | 语音合成 | `github.com/k2-fsa/sherpa-onnx-go`, `github.com/ebitengine/oto/v3` |
| `core` | 持久化 | `encoding/json`, `github.com/adrg/xdg` |
