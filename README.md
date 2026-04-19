# Nifty Reader

Desktop reader application for https://search.niftyarchives.org/
Built with Dioxus (Rust)

## 🚀 Setup Instructions

### Prerequisites
1. Install Rust: https://www.rust-lang.org/tools/install
2. Install Dioxus CLI:
```bash
cargo install dioxus-cli
```

### Development
```bash
# Run development server
dx serve
```

### Build
```bash
# Build desktop package
dx build --release
```

### TTS model assets
```bash
# Download Pocket TTS + wav2vec2 model files into ./models
bash scripts/fetch_tts_models.sh
# (uses the Rust hf-hub crate under the hood)
```


## Recommended IDE Setup
- [VS Code](https://code.visualstudio.com/)
- [rust-analyzer](https://marketplace.visualstudio.com/items?itemName=rust-lang.rust-analyzer)
