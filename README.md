# Nifty Reader (Go Edition)

A desktop application for browsing and reading stories from Nifty Archives, with built-in TTS and search capabilities.

## Tech Stack
- **GUI**: [Fyne](https://fyne.io/) (Pure Go)
- **TTS**: [Sherpa-ONNX](https://github.com/k2-fsa/sherpa-onnx) (Go API)
- **Audio**: [Oto](https://github.com/ebitengine/oto)
- **Parsing**: [Goquery](https://github.com/PuerkitoBio/goquery)

## Project Structure
- `main.go`: Application entry point and UI logic.
- `pkg/core/`: Network scraping and local state storage.
- `pkg/tts/`: Text-to-speech engine and audio playback.

## How to Build
1. Install [Go](https://go.dev/dl/).
2. Run `go mod tidy` to resolve dependencies.
3. **Setup DLLs (Windows)**: Run `go run scripts/setup.go` to download required `sherpa-onnx` binaries.
4. Run `go run main.go` or `go build -o nifty-reader.exe main.go`.

## Important Note (Windows)
This app requires **CGO** to be enabled for Fyne and Sherpa-ONNX.
Ensure you have a C compiler (like MinGW-w64) installed and `CGO_ENABLED=1` set.

## Features
- Browse and Search stories from search.niftyarchives.org.
- Read stories with adjustable font size and theme.
- Offline TTS with voice cloning support.
- Reading history and proxy settings.
