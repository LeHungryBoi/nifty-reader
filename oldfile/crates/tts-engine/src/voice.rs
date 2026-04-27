use anyhow::Result;
use sherpa_onnx::{GenerationConfig, Wave};
use std::collections::HashMap;
use std::env;
use std::fs;
use std::io::Read;
use std::path::{Path, PathBuf};

use crate::audio_io::validate_wav;
use crate::{VoiceInfo, VoiceKind};

/// Predefined voices available from HuggingFace (sherpa-onnx compatible).
const PREDEFINED_VOICES: &[&str] = &[
    "alba", "marius", "javert", "jean", "fantine", "cosette", "eponine", "azelma",
];

/// Get the directory for cached predefined voice reference audio (.wav files).
pub fn get_voice_cache_dir() -> PathBuf {
    if let Ok(cache) = env::var("SHERPA_ONNX_CACHE_DIR") {
        PathBuf::from(cache)
    } else {
        PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap_or_else(|_| ".".to_string()))
            .join("src")
            .join("assets")
            .join("models")
            .join("voices")
    }
}

/// Get the directory for custom trained voices (reference WAV files).
pub fn get_voices_dir() -> PathBuf {
    PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap_or_else(|_| ".".to_string()))
        .join("src")
        .join("assets")
        .join("voices")
}

/// Resolve voice file path (checks in order: custom wav, local file, cached embedding, downloadable).
/// Returns path to a WAV file for sherpa-onnx voice cloning.
pub fn get_voice_path(voice_name: &str) -> Result<PathBuf> {
    let voices_dir = get_voices_dir();
    let cache_dir = get_voice_cache_dir();

    // 1. Custom trained voice (.wav) FIRST - faster
    let voice_file = voices_dir.join(format!("{}.wav", voice_name));
    if voice_file.exists() {
        return Ok(voice_file);
    }

    // 2. Local file as-is (must be WAV)
    let local_path = PathBuf::from(voice_name);
    if local_path.exists() {
        return Ok(local_path);
    }

    // 3. Cached predefined voice reference audio
    let wav_path = cache_dir.join(format!("{}.wav", voice_name));
    if wav_path.exists() {
        return Ok(wav_path);
    }

    // 4. Download if predefined
    if PREDEFINED_VOICES.contains(&voice_name) {
        fs::create_dir_all(&cache_dir)?;
        download_voice_to(&voice_name, &wav_path)?;
        return Ok(wav_path);
    }

    anyhow::bail!(
        "Voice '{}' not found. Use 'list-voices' to see available voices.",
        voice_name
    )
}

/// Download a predefined voice reference audio from HuggingFace to a specific path.
fn download_voice_to(voice_name: &str, target: &Path) -> Result<()> {
    let url = format!(
        "https://huggingface.co/k2-fsa/sherpa-onnx-pocket-tts/resolve/main/voices/{}.wav",
        voice_name
    );

    let mut request = ureq::get(&url)
        .timeout(std::time::Duration::from_secs(300));

    if let Ok(token) = env::var("HF_TOKEN") {
        request = request.header("Authorization", &format!("Bearer {}", token));
    }

    let response = request.call()
        .map_err(|e| anyhow::anyhow!("Failed to download voice: {}", e))?;

    if response.status() != 200 {
        anyhow::bail!("Failed to download voice: HTTP {}", response.status());
    }

    let mut bytes = Vec::new();
    response.into_reader().read_to_end(&mut bytes)?;
    fs::write(target, &bytes)?;

    Ok(())
}

/// Train a voice by copying reference WAV to custom voices directory.
/// sherpa-onnx uses the WAV directly for voice cloning via reference_audio.
pub fn train_voice(input: &Path, output: &Path) -> Result<()> {
    if !input.exists() {
        anyhow::bail!("Input file not found: {:?}", input);
    }

    validate_wav(input)?;

    // Ensure parent directory exists
    if let Some(parent) = output.parent() {
        fs::create_dir_all(parent)?;
    }

    // Copy WAV file to output location
    fs::copy(input, output)?;

    Ok(())
}

/// List all available voices.
pub fn list_voices() -> Vec<VoiceInfo> {
    let mut voices = Vec::new();

    // Predefined voices
    for name in PREDEFINED_VOICES {
        voices.push(VoiceInfo {
            name: name.to_string(),
            kind: VoiceKind::Predefined,
        });
    }

    // Cached voices
    let cache_dir = get_voice_cache_dir();
    if let Ok(entries) = fs::read_dir(&cache_dir) {
        for entry in entries.flatten() {
            if let Some(name) = entry.file_name().to_str() {
                let voice_name = name.trim_end_matches(".wav").to_string();
                if !PREDEFINED_VOICES.contains(&voice_name.as_str()) && name.ends_with(".wav") {
                    voices.push(VoiceInfo {
                        name: voice_name,
                        kind: VoiceKind::Cached,
                    });
                }
            }
        }
    }

    // Custom voices
    let voices_dir = get_voices_dir();
    if voices_dir.exists() {
        if let Ok(entries) = fs::read_dir(&voices_dir) {
            for entry in entries.flatten() {
                if let Some(name) = entry.file_name().to_str() {
                    if name.ends_with(".wav") {
                        let voice_name = name.trim_end_matches(".wav").to_string();
                        voices.push(VoiceInfo {
                            name: voice_name,
                            kind: VoiceKind::Custom,
                        });
                    }
                }
            }
        }
    }

    voices
}

/// Download a predefined voice from HuggingFace.
pub fn download_voice(name: &str) -> Result<PathBuf> {
    if !PREDEFINED_VOICES.contains(&name) {
        anyhow::bail!(
            "Voice '{}' not found. Use 'list-voices' to see available voices.",
            name
        );
    }

    let cache_dir = get_voice_cache_dir();
    fs::create_dir_all(&cache_dir)?;

    let wav_path = cache_dir.join(format!("{}.wav", name));
    if wav_path.exists() {
        return Ok(wav_path);
    }

    download_voice_to(name, &wav_path)?;
    Ok(wav_path)
}

/// Build GenerationConfig for sherpa-onnx with optional voice cloning.
pub fn build_generation_config(voice_path: &Path) -> Result<GenerationConfig> {
    let mut extra = HashMap::new();
    extra.insert("seed".to_string(), serde_json::json!(42));

    // If voice is a WAV file, use it for zero-shot voice cloning
    let wave = Wave::read(voice_path.to_str().unwrap())
        .ok_or_else(|| anyhow::anyhow!("Failed to read WAV file: {:?}", voice_path))?;

    let gen_config = GenerationConfig {
        speed: 1.0,
        reference_audio: Some(wave.samples().to_vec()),
        reference_sample_rate: wave.sample_rate(),
        extra: Some(extra),
        ..Default::default()
    };

    Ok(gen_config)
}
