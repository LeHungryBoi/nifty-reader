# Nifty Reader

Desktop reader application for https://search.niftyarchives.org/
Built with Tauri 2 + React 19 + TypeScript + Vite

## 🚀 Setup Instructions

### Prerequisites
1. Install Bun (package manager):
```bash
npm install -g bun
```

2. Install Tauri dependencies for your OS:
https://tauri.app/start/prerequisites/

### Development
```bash
# Install dependencies
bun install

# Run development server (native window)
bun run tauri dev

# Run web only
bun run dev
```

### Build
```bash
# Build native desktop package
bun run tauri build
```

## Recommended IDE Setup
- [VS Code](https://code.visualstudio.com/)
- [Tauri Extension](https://marketplace.visualstudio.com/items?itemName=tauri-apps.tauri-vscode)
- [rust-analyzer](https://marketplace.visualstudio.com/items?itemName=rust-lang.rust-analyzer)