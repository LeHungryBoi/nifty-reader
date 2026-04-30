# Agent 上下文

你正在开发 **Nifty Reader**，一个基于 Go 的桌面应用程序。

## 规范

**所有 spec 文件必须用中文书写。** 包括 `spec/` 目录下的所有 `.md` 文件。这是为了确保所有 AI 代理都能理解项目规范。
新增或删除文件时要检查architecture.md是否需要更新
ascii art is heavily discouraged, unless there's no other way.

## 核心原则
1. **纯 Go**：使用 Fyne 构建 UI，不使用 Node/npm/Rust。
2. **逻辑分离**：
   - `main.go` 负责 UI 和导航。
   - `pkg/core/` 负责"业务逻辑"（网络、存储）。
   - `pkg/tts/` 负责音频和模型推理。

## 主要依赖
- `fyne.io/fyne/v2`：GUI 框架。
- `github.com/k2-fsa/sherpa-onnx-go/sherpa_onnx`：TTS 引擎。
- `github.com/ebitengine/oto/v3`：音频播放。
- `github.com/PuerkitoBio/goquery`：HTML 解析。

## 常见任务
- **添加视图**：在 `main.go` 中为 `NiftyApp` 添加新方法，并更新 `na.content.Objects`。
- **修改爬取逻辑**：更新 `pkg/core/core.go`。
- **TTS 调整**：更新 `pkg/tts/tts.go`。

## 构建与运行
- `build.bat` — 编译（release 模式，无控制台窗口）
- `build.bat debug` — 编译（debug 模式，保留控制台）
- `build.bat run` — 编译并立即运行（debug 模式）
