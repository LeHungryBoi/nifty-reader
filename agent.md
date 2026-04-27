# Agent Context

You are working on **Nifty Reader**, a Go-based desktop application.

## Specs

**所有 spec 文件必须用中文书写。** 包括 `spec/` 目录下的所有 `.md` 文件。这是为了确保所有 AI 代理都能理解项目规范。

## Core Principles
1. **Pure Go**: We use Fyne for the UI and avoid Node/npm/Rust.
2. **Logic Separation**: 
   - `main.go` handles the UI and navigation.
   - `pkg/core/` handles the "business logic" (network, storage).
   - `pkg/tts/` handles the audio and model inference.

## Key Dependencies
- `fyne.io/fyne/v2`: GUI framework.
- `github.com/k2-fsa/sherpa-onnx-go/sherpa_onnx`: TTS engine.
- `github.com/ebitengine/oto/v3`: Audio playback.
- `github.com/PuerkitoBio/goquery`: HTML parsing.

## Common Tasks
- **Adding a View**: Add a new method to `NiftyApp` in `main.go` and update `na.content.Objects`.
- **Modifying Scraping**: Update `pkg/core/core.go`.
- **TTS Adjustments**: Update `pkg/tts/tts.go`.

## Development Commands
```bash
go mod tidy
go run scripts/setup.go  # Download DLLs (Windows only)
go run main.go           # Run app
```
