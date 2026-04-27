> **Note:** This file was moved from `docs/roadmap.md` to `spec/roadmap.md`. Update links accordingly.

# roadmap.md — Feature Status and Migration Plan

> **What this file is:** The current state of feature implementation. It tracks what’s done, what’s in progress, what’s not started, and what technical debt exists. It also contains the active migration plan for the sherpa-onnx TTS switch.
>
> **Boundary:** Update this file whenever you complete, start, or abandon a feature. It should always reflect reality. Do not leave ❌ for something you just implemented.

This document tracks implementation status against specs and serves as the migration plan log.

**Last Updated:** April 24, 2026

---

## ✅ Completed Migration: TTS Backend → sherpa-onnx

**Status:** Implementation complete (April 25, 2026)

**What changed:**
- Replaced `pocket-tts` + `candle-core` with `sherpa-onnx` in `crates/tts-engine/Cargo.toml`
- Rewrote `model.rs` to use `OfflineTts::create()` singleton
- Rewrote `playback.rs` to generate full audio then play via rodio
- Rewrote `voice.rs` to use WAV reference audio for voice cloning instead of safetensors embeddings
- Updated `download_models.rs` to download `.onnx` model files
- Updated CLI tools to use `SHERPA_ONNX_*` environment variables
- Removed `build.rs` env var setup (no longer needed)

**Benefits:**
- Reduced transitive dependencies from ~700 crates to minimal set (`serde` + `serde_json`)
- Faster compile times and smaller binary size
- Better portability via ONNX Runtime C++ FFI
- Same zero-shot voice cloning capability via reference WAV files

**Trade-offs:**
- No true streaming (sherpa-onnx generates full audio before playback starts)
- Progress callback exists but playback begins after generation completes
- Acceptable for story reading use case

**Why:** `babybirdprd/pocket-tts` (current) pulls in ~700 transitive deps including `intel-mkl-src`, `ocipkg`, and the full HuggingFace `tokenizers` stack — all unconditionally, regardless of feature flags. `sherpa-onnx` uses a prebuilt C++ ONNX Runtime binary with a thin Rust FFI wrapper, reducing runtime Rust deps to just `serde` + `serde_json`.

**Trade-off:** No true streaming (sherpa-onnx generates full audio then plays). Progress callback exists but playback starts after generation. Acceptable for story reading use case.

**Migration plan:**
1. Replace `pocket-tts` + `candle-core` in `crates/tts-engine/Cargo.toml` with `sherpa-onnx`
2. Rewrite `crates/tts-engine/src/model.rs` — `OfflineTts::create()` instead of `TTSModel::load()`
3. Rewrite `crates/tts-engine/src/playback.rs` — generate full audio, then play via rodio
4. Rewrite `crates/tts-engine/src/voice.rs` — voice cloning via `GenerationConfig.reference_audio`
5. Update `src/cli/download_models.rs` — download `.onnx` model files instead of `.safetensors`
6. Remove `build.rs` env var setup (no longer needed)
7. Update `spec/pocket-tts.md` to reflect new API
8. Update `spec/roadmap.md` (this file) status table

**New model files needed** (replace current `src/assets/models/`):
- `lm_flow.int8.onnx`
- `lm_main.int8.onnx`
- `encoder.onnx`
- `decoder.int8.onnx`
- `text_conditioner.onnx`
- `vocab.json`
- `token_scores.json`

See [sherpa-onnx.md](./com_spec/sherpa-onnx.md) for the sherpa-onnx API details.

---

## Feature Implementation Status

### Core TTS Integration

| Feature | Status | Notes |
|---------|--------|-------|
| Model loading singleton | ✅ | `OnceLock` in `model.rs` |
| Audio playback | ✅ | sherpa-onnx generate + rodio (full generation then play) |
| Stop functionality | ✅ | `StopFlag` atomic bool |
| Blocking task for TTS | ✅ | `spawn_blocking` in reader UI |
| Voice selection (hardcoded "alba") | ⚠️ | Only alba; no UI |
| **sherpa-onnx migration** | ✅ | Completed April 25, 2026 |

### Voice Management

| Feature | Status | Notes |
|---------|--------|-------|
| Predefined voices (8 voices) | ⚠️ | API supports all, only alba used |
| Custom voice from WAV | ✅ | `voice.rs` train_voice() |
| Custom voice from embeddings | ✅ | `get_voice_state_from_prompt_file()` |
| Voice selection UI | ❌ | Not started |
| Voice download (predefined) | ✅ | `voice.rs` download_voice() |

### UI / Reader

| Feature | Status | Notes |
|---------|--------|-------|
| Story browse/search | ✅ | `browse.rs` |
| Story reading view | ✅ | `reader.rs` |
| Read Aloud button | ✅ | Toggles play/stop |
| Reading history | ✅ | `history.rs` + storage |
| Settings page | ✅ | `settings.rs` |
| Voice selection UI | ❌ | Not started |
| Loading indicator (model init) | ❌ | No feedback on first TTS load |
| User-friendly TTS error display | ❌ | Errors go to stderr only |

### Build & Tooling

| Feature | Status | Notes |
|---------|--------|-------|
| `download-models` binary | ✅ | `src/cli/download_models.rs` |
| `voice-cli` binary | ✅ | `src/cli/voice_cli.rs` |
| CLI works without GUI deps | ✅ | `--no-default-features` |
| int8 quantization | ✅ | sherpa-onnx uses pre-quantized `.int8.onnx` models |

---

## Known Deviations from Spec

1. **Voice hardcoded to "alba"** — spec requires configurable voice selection
2. **No pause syntax** — `[pause:Xms]` not implemented
3. **No audio export** — TTS output not saveable to WAV
4. **Errors to stderr only** — no UI error feedback

---

## Technical Debt

1. `voice.rs` uses `reqwest::blocking` for voice downloads — blocks the thread, should be async or moved to CLI only
2. Voice reference audio loaded on every TTS request — could cache GenerationConfig per voice name
3. ~~`candle_core` imported directly in `voice.rs` for embedding math~~ — **RESOLVED** by sherpa-onnx migration
