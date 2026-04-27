# pocket-tts.md — Legacy TTS System Specification

> **What this file is:** The spec for the legacy `pocket-tts` text-to-speech system. 
>
> **Status:** ⚠️ **LEGACY** — This engine is currently being replaced by [sherpa-onnx](./sherpa-onnx.md).
>
> **Boundary:** Use this file for maintaining the existing `pocket-tts` implementation. For all new development and the migration plan, see [sherpa-onnx.md](./sherpa-onnx.md).

## Overview

Pocket-TTS is a pure Rust, CPU-only text-to-speech system using Candle (HuggingFace tensor framework). It implements Kyutai's Pocket TTS architecture to generate WAV audio from text using neural TTS models. Models are downloaded from HuggingFace and cached locally.

**Source Repository:** https://github.com/babybirdprd/pocket-tts

## Project Configuration

### Cargo.toml Dependencies

```toml
pocket-tts = { version = "0.6", features = ["quantized"] }
```

- The `"quantized"` feature enables int8 quantization for faster CPU inference
- `candle-core` is pulled in automatically for tensor operations
- `rodio` is used separately for audio playback

### Build System

**Important:** Model downloads are separated from the build process to avoid compilation blocking.

#### Model Download Workflow

Models are downloaded using a dedicated binary, NOT during compilation:

```bash
# Download models before first use
cargo run --release --bin download-models

# Optional: Set HF_TOKEN for private repositories
$env:HF_TOKEN="hf_your_token_here"  # PowerShell
export HF_TOKEN=hf_your_token_here   # bash
```

The download script fetches three files to the `models/` directory:
- **model.safetensors**: Main model weights (~hundreds of MB)
- **tokenizer.model**: SentencePiece tokenizer
- **english.yaml**: Model configuration with architecture parameters

Models are cached locally and reused on subsequent runs. The build script (`build.rs`) only sets environment variables and checks if models exist - it does NOT download anything.

#### Environment Variables

- `HF_TOKEN` (optional): HuggingFace authentication token for gated repositories
- `POCKET_TTS_MODEL_PATH`: Automatically set by build.rs to point to the models directory
- `POCKET_TTS_CACHE_DIR` (optional): Override default cache location for download-models binary

## Public API

```rust
use pocket_tts::TTSModel;
use pocket_tts::audio;          // WAV I/O + resampling
use pocket_tts::ModelState;     // type alias: HashMap<String, HashMap<String, Tensor>>
```

## Core Usage Pattern

```rust
use pocket_tts::TTSModel;

// 1. Load model (downloads weights from HuggingFace on first run, cached after)
let model = TTSModel::load("b6369a24")?;           // default variant
// OR with custom params:
let model = TTSModel::load_with_params(
    "b6369a24",  // variant
    0.7,         // temperature (0.0 = deterministic, 0.7 = natural variation)
    1,           // lsd_decode_steps (1 = fast, 5 = high quality)
    -4.0,        // eos_threshold (more negative = longer audio)
)?;

// 2. Get voice state (voice cloning from a reference WAV)
let voice_state = model.get_voice_state("reference.wav")?;
// OR from pre-computed embeddings:
let voice_state = model.get_voice_state_from_prompt_file("embeddings.safetensors")?;

// 3a. Generate full audio at once
let audio = model.generate("Hello, world!", &voice_state)?;
// audio is a Tensor of shape [1, samples]

// 3b. Stream audio chunks (better for long text / low latency)
for chunk in model.generate_stream("Long text...", &voice_state) {
    let chunk = chunk?; // Tensor [1, 1, samples_per_frame]
}

// 3c. Long text with automatic segmentation
for chunk in model.generate_stream_long("Very long text...", &voice_state) {
    let audio = chunk?;
}

// 4. Save to WAV
pocket_tts::audio::write_wav("output.wav", &audio, model.sample_rate as u32)?;
// sample_rate is always 24000
```

## Audio Utilities

```rust
// Read WAV → Tensor [channels, samples]
let (audio, sample_rate) = pocket_tts::audio::read_wav("input.wav")?;

// Write WAV
pocket_tts::audio::write_wav("output.wav", &audio, 24000)?;

// Resample
let resampled = pocket_tts::audio::resample(&audio, 48000, 24000)?;
```

## Predefined Voices

Eight built-in voices available without additional files:
- `alba`, `marius`, `javert`, `jean`, `fantine`, `cosette`, `eponine`, `azelma`

These are built-in voice embeddings — pass the name string to `get_voice_state` or CLI `--voice`.

## Pause Syntax

Supports `[pause:500ms]` inline in text for natural pauses.

```rust
use pocket_tts::{parse_text_with_pauses, ParsedText, PauseMarker};
```

## Nifty Reader Implementation

### Model Loading (Singleton Pattern)

**Location:** `src/tts.rs`

```rust
static MODEL: OnceLock<TTSModel> = OnceLock::new();

fn get_model() -> Result<&'static TTSModel> {
    if MODEL.get().is_none() {
        let model_path = env::var("POCKET_TTS_MODEL_PATH")
            .unwrap_or_else(|_| "english".to_string());
        let m = TTSModel::load(&model_path)?;
        let _ = MODEL.set(m);
    }
    Ok(MODEL.get().unwrap())
}
```

**Key Implementation Details:**
- Model path is read from `POCKET_TTS_MODEL_PATH` environment variable (set by build.rs)
- Falls back to "english" string if not set
- Model loads lazily on first TTS request
- Uses `TTSModel::load()` which expects a directory containing model.safetensors, tokenizer.model, and config YAML

### Audio Playback

Audio is streamed using `rodio` for real-time playback:

```rust
pub fn speak(text: String) {
    STOP.store(false, Ordering::SeqCst);

    let model = get_model()?;
    let voice_state = model.get_voice_state("alba")?;
    let sample_rate = model.sample_rate as u32;

    let (_stream, stream_handle) = OutputStream::try_default()?;
    let sink = Sink::try_new(&stream_handle)?;

    for chunk in model.generate_stream_long(&text, &voice_state) {
        if STOP.load(Ordering::SeqCst) { break; }
        match chunk.and_then(|t| tensor_to_samples(t)) {
            Ok(samples) => {
                let source = SamplesBuffer::new(1, sample_rate, samples);
                sink.append(source);
            }
            Err(e) => { eprintln!("TTS chunk error: {e}"); break; }
        }
    }

    sink.sleep_until_end();
}
```

**UI Integration:** Located in `src/components/reader.rs`
- Users click "🔊 Read Aloud" button on story paragraphs
- Spawns blocking task to avoid UI thread blocking
- Toggle between "Read Aloud" and "⏹ Stop" states
- Joins all paragraphs into single text before TTS generation

## Model Hash Verification

Model hashes are used to identify specific model variants:

1. **Hash Storage**: Known model hashes stored in `.codebuddy/skills/huggingface-model-hash/references/known-models.md`
2. **Current Variant**: `a0ac5076` (English model from `english_2026-04`)
3. **Finding New Hashes**: Use the huggingface-model-hash skill to extract variant hashes from HuggingFace

**How to Find Model Hash:**
1. Navigate to HuggingFace model page
2. Click "Raw pointer file" button for model.safetensors
3. Extract first 8 characters of the hash value
4. Update configuration if needed

See [Model Hash Finder](./huggingface-model-hash.md) for detailed workflow.

## Custom Voice Generation

### Predefined Voices

Eight built-in voices available without additional files:
`alba`, `marius`, `javert`, `jean`, `fantine`, `cosette`, `eponine`, `azelma`

Currently hardcoded to use "alba" voice in `src/tts.rs`.

### Generating Custom Voice Embeddings

Custom voices require creating `.safetensors` embedding files. The official `pocket-tts` CLI tool is needed for this process.

**Method 1: Voice Cloning from Reference WAV**
```rust
// Clone voice from audio sample
let voice_state = model.get_voice_state("reference.wav")?;
```

**Method 2: Using Pre-computed Embeddings**
```rust
// Load pre-generated embeddings
let voice_state = model.get_voice_state_from_prompt_file("custom_voice.safetensors")?;
```

**Steps to Generate Custom Embeddings:**

1. **Install pocket-tts CLI:**
   ```bash
   cargo install pocket-tts --features cli
   ```

2. **Prepare reference audio:**
   - Format: WAV file
   - Sample rate: 24000 Hz (recommended)
   - Duration: 5-30 seconds of clear speech
   - Mono channel

3. **Generate embeddings:**
   ```bash
   pocket-tts extract-voice \
     --input reference.wav \
     --output custom_voice.safetensors
   ```

4. **Use in Nifty Reader:**
   - Place `.safetensors` file in project's `voices/` directory
   - Modify `src/tts.rs` to load custom voice:
     ```rust
     fn get_voice_state(model: &TTSModel) -> Result<ModelState> {
         model.get_voice_state_from_prompt_file("voices/custom_voice.safetensors")
     }
     ```

**Future Enhancement Ideas:**
- Add UI for voice selection from predefined voices
- Implement voice upload/cloning interface
- Support multiple saved voice profiles
- Add pause syntax support: `[pause:500ms]`

## What Pocket-TTS Is NOT

- NOT a wrapper around Windows SAPI / macOS AVSpeechSynthesizer
- NOT the `tts` crate (which IS a system TTS wrapper)
- Does NOT have a `TTS::default()` or `tts.speak(text, bool)` API

## Troubleshooting

### Model Download Issues
- **Download fails**: Run `cargo run --release --bin download-models` manually
- **Authentication errors (401)**: Set `HF_TOKEN` environment variable before downloading
- **Disk space**: Ensure sufficient space for model (~hundreds of MB)
- **Timeout**: The download script has 600 second timeout; retry if network is slow

### Compilation
- **Build hangs**: Models are NOT downloaded during build anymore - this should not happen
- **Missing models warning**: This is expected on first build; run download-models binary
- **cargo check works**: Should complete without network access or HF_TOKEN

### Runtime Issues
- **Model not found**: Check `POCKET_TTS_MODEL_PATH` points to correct directory
- **Slow first run**: Model loading is blocking; subsequent calls are instant
- **Audio playback issues**: Verify rodio dependencies and system audio drivers

### Performance Optimization
- int8 quantization is enabled via `"quantized"` feature flag
- Dev builds use `opt-level = 1` for reasonable TTS performance
- Release builds use `opt-level = 3` with LTO for maximum performance
- Consider enabling `"metal"` feature on macOS for GPU acceleration
- Use streaming (`generate_stream_long`) for long texts to reduce latency
