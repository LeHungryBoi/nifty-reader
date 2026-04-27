# architecture.md — 代码库结构

> **这是什么：** 代码库的地图。告诉你有哪些文件、每个包的作用、使用的库、以及组件之间的数据流。需要在理解某样东西在哪里或各部分如何连接时阅读此文件。
>
> **边界：** 此文件必须始终反映代码的当前状态。添加/删除文件、添加/删除依赖、或改变包的功能时必须更新。不要添加愿景内容——只描述当前存在的东西。

## 项目结构

```
nifty-reader/
├── main.go                 ← Fyne 应用入口
├── pkg/
│   ├── nifty-ui/
│   │   └── ui.go           ← 所有 UI 逻辑 (Fyne widgets, views)
│   ├── nifty-core/
│   │   └── pkg/api/
│   │       └── search.go   ← HTTP 客户端、故事获取、搜索
│   ├── tts/
│   │   └── *.go            ← 语音合成引擎 (sherpa-onnx)
│   └── core/
│       └── state.go        ← 应用状态持久化 (JSON)
└── go.mod
```

## 包职责

### `nifty-reader` (根)

- **用途：** Fyne 桌面 GUI 应用
- **入口：** `main.go` → `fyne.NewApp()`

### `pkg/nifty-ui`

- **用途：** 所有 UI 组件和视图逻辑
- **关键库：** `fyne.io/fyne/v2` — 纯 Go GUI 框架
- **文件：** `ui.go` — 包含 `NiftyApp` 结构体和所有视图函数

### `pkg/nifty-core/pkg/api`

- **用途：** niftyarchives.org 的 HTTP 客户端、HTML 解析
- **关键库：**
  - `net/http` — HTTP 客户端
  - `github.com/PuerkitoBio/goquery` — HTML 解析

### `pkg/tts`

- **用途：** 通过 sherpa-onnx 实现语音合成
- **关键库：**
  - `github.com/k2-fsa/sherpa-onnx-go` — TTS 推理
  - `github.com/ebitengine/oto` — 音频播放

### `pkg/core`

- **用途：** 应用状态持久化 (JSON 写入磁盘)
- **关键库：** `encoding/json`, `github.com/adrg/xdg`

## UI 视图

| 视图 | 函数 | 描述 |
|------|------|------|
| **Browse** | `showBrowse()` | 故事/章节列表，搜索结果 |
| **Story Page** | `readStory()` | 完整章节文本，含 TTS 按钮 |
| **History** | `showHistory()` | 阅读历史列表 |
| **Settings** | `showSettings()` | 代理设置 |

### Fyne 组件

- `widget.NewEntry()` — 文本输入（搜索框）
- `widget.NewLabel()` — 纯文本显示
- `widget.NewRichTextFromMarkdown()` — Markdown 文本
- `widget.NewList()` — 虚拟滚动列表
- `container.NewVScroll()` — 可滚动容器
- `container.NewPadded()` — 内边距包装器

## 数据流

```
用户点击故事
  → showBrowse() → List.OnSelected
  → readStory(url)
  → api.FetchStory(url)
  → goquery 解析 HTML
  → RichText 显示段落
```

```
用户点击"朗读"
  → readStory() → ttsBtn 回调
  → tts.GetEngine().Speak(text)
  → sherpa-onnx 生成音频
  → oto 播放音频
```

## 构建和运行

```bash
go mod tidy                              # 安装依赖
go run main.go                           # 开发运行
CGO_ENABLED=1 go build -o nifty-reader.exe main.go  # 构建
```

## 关键约束

- Fyne 和 sherpa-onnx 需要 CGO（Windows 需要 MinGW-w64）
- `pkg/nifty-ui` 依赖 `pkg/nifty-core`（UI → 网络）
- `pkg/nifty-core` 不得导入 UI 包（保持逻辑纯粹）
