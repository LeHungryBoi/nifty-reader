# TTS Timestamp Migration Plan

## Current state (what to keep vs replace)

- Keep the **UI plumbing**:
  - `src/components/tts_controls.rs`
  - word highlight hooks in `src/components/reader.rs`
- Replace the current **simulated backend** in:
  - `src/tts/engine.rs`
  - `src/tts/sync.rs` (linear fake timing)
- Keep `VoiceManager` shape but wire to real Pocket TTS voice state handling.

## Target architecture

1. Split story text into sentence units (stable sentence IDs).
2. For each sentence:
   - Generate WAV chunk with `pocket-tts`.
   - Run alignment with `facebook/wav2vec2-base-960h` to produce sentence-level `(start_ms, end_ms)`.
3. Stitch playback schedule across sentences and expose timestamp events to UI.
4. Cache sentence artifacts (audio + timestamps) keyed by content/voice/speed.

## Data model

- `SentenceUnit`:
  - `id: u64`
  - `text: String`
  - `global_word_start: usize`
- `SentenceArtifact`:
  - `audio_path: PathBuf`
  - `start_ms: u64`
  - `end_ms: u64`
- `CacheKey` hash over:
  - sentence text
  - selected voice
  - playback speed
  - model revision

## Build-system model download plan

Use a deterministic fetch + cache flow during build image creation (not at runtime):

1. Add a Rust downloader (`src/bin/fetch_tts_models.rs`) using `hf-hub`, and keep `scripts/fetch_tts_models.sh` as a thin wrapper that runs it:
   - downloads Pocket TTS English model from:
     `https://huggingface.co/kyutai/pocket-tts/tree/main/languages/english_2026-04`
   - downloads wav2vec2 model assets for:
     `facebook/wav2vec2-base-960h`
   - verifies checksums if provided via lock file
   - stores under `models/`
2. Add a lock file `models/models.lock` containing:
   - source URL
   - revision/commit hash
   - sha256
3. In CI/build image:
   - run `bash scripts/fetch_tts_models.sh`
   - archive `models/` into build artifact layer
4. At app startup:
   - only read local `models/` paths
   - fail fast with clear error if model files missing

## Cargo dependencies

- Enable Pocket TTS crate in `Cargo.toml`:
  - `pocket-tts` from crates.io
- Add `hf-hub` in `Cargo.toml` for Hugging Face model downloads in the build step.
- Keep wav2vec2 execution isolated in a small adapter module (`src/tts/alignment.rs`).

## Implementation order

1. Add real sentence splitter and sentence IDs.
2. Replace fake sync with sentence timestamp outputs.
3. Add disk cache manager (`src/tts/cache.rs`).
4. Add alignment adapter with wav2vec2 pipeline (`src/tts/alignment.rs`).
5. Integrate playback session seek/jump against cached sentence boundaries.
6. Remove simulation fallback once real pipeline is stable.
