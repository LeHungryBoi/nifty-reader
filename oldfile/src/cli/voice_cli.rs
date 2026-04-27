//! Voice Management CLI for Nifty Reader
//!
//! A unified CLI tool for voice training and generation operations.
//!
//! ## Commands
//!
//! - `train <input.wav> [output.safetensors>` - Train voice from WAV clip
//! - `generate [--phrase TEXT] [--voice NAME] [-o OUTPUT]` - Generate voice clip
//! - `list-voices` - List available predefined voices
//! - `download-voice <name>` - Download predefined voice
//!
//! ## Usage
//!
//! ```bash
//! # Train voice from WAV file
//! cargo run --release --bin voice-cli -- train my_voice.wav
//! cargo run --release --bin voice-cli -- train reference.wav src/assets/voices/custom.safetensors
//!
//! # Generate speech with default phrase
//! cargo run --release --bin voice-cli -- generate
//!
//! # Generate speech with custom phrase
//! cargo run --release --bin voice-cli -- generate --phrase "Hello world"
//!
//! # Generate with specific voice
//! cargo run --release --bin voice-cli -- generate --voice alba --phrase "Custom text"
//!
//! # Generate and save to file
//! cargo run --release --bin voice-cli -- generate -o output.wav
//!
//! # List available voices
//! cargo run --release --bin voice-cli -- list-voices
//!
//! # Download a voice
//! cargo run --release --bin voice-cli -- download-voice alba
//! ```
//!
//! ## Environment Variables
//!
//! - `HF_TOKEN` - HuggingFace authentication token (required for some operations)
//! - `SHERPA_ONNX_MODEL_PATH` - Path to sherpa-onnx model directory (default: "sherpa-onnx-pocket-tts")

use anyhow::Result;
use std::env;
use std::path::PathBuf;
use std::process::exit;
use tts_engine::{TtsEngine, VoiceKind};

/// Default phrases used when no custom phrase is provided
const DEFAULT_PHRASES: &[&str] = &[
    "Hello! This is a test of the text to speech system.",
    "The quick brown fox jumps over the lazy dog.",
    "Text to speech technology has come a long way.",
];

fn cmd_train(args: &[String]) -> Result<()> {
    if args.is_empty() {
        eprintln!("Error: Input WAV file required");
        eprintln!();
        eprintln!("Usage: voice-cli train <input.wav> [output.safetensors]");
        exit(1);
    }

    let input_path = PathBuf::from(&args[0]);
    let output_path = if args.len() >= 2 {
        PathBuf::from(&args[1])
    } else {
        let stem = input_path
            .file_stem()
            .and_then(|s| s.to_str())
            .unwrap_or("voice");
        let voices_dir = tts_engine::voice::get_voices_dir();
        std::fs::create_dir_all(&voices_dir)?;
        voices_dir.join(format!("{}.safetensors", stem))
    };

    println!("Input audio: {:?}", input_path);
    println!("Output embedding: {:?}", output_path);

    TtsEngine::train_voice(&input_path, &output_path)?;
    println!("Voice embedding saved successfully!");
    Ok(())
}

fn cmd_generate(args: &[String]) -> Result<()> {
    let mut phrase: Option<String> = None;
    let mut voice_name = "alba".to_string();
    let mut output_path: Option<PathBuf> = None;

    // Parse arguments
    let mut i = 0;
    while i < args.len() {
        match args[i].as_str() {
            "--phrase" | "-p" => {
                i += 1;
                if i < args.len() {
                    phrase = Some(args[i].clone());
                }
            }
            "--voice" | "-v" => {
                i += 1;
                if i < args.len() {
                    voice_name = args[i].clone();
                }
            }
            "--output" | "-o" => {
                i += 1;
                if i < args.len() {
                    output_path = Some(PathBuf::from(&args[i]));
                }
            }
            "--help" | "-h" => {
                print_help();
                return Ok(());
            }
            _ => {
                if phrase.is_none() {
                    phrase = Some(args[i].clone());
                }
            }
        }
        i += 1;
    }

    let text = phrase.unwrap_or_else(|| DEFAULT_PHRASES[0].to_string());
    println!("Text: \"{}\"", text);
    println!("Voice: {}", voice_name);

    let engine = TtsEngine::new();

    if let Some(output_file) = output_path {
        println!("Output: {:?}", output_file);
        engine.generate_to_file(&text, &voice_name, &output_file)?;
        println!("Audio saved to: {:?}", output_file);
    } else {
        engine.speak(&text, &voice_name)?;
        println!("Playback complete.");
    }

    Ok(())
}

fn cmd_list_voices() -> Result<()> {
    let voices = TtsEngine::list_voices();

    let predefined: Vec<_> = voices.iter().filter(|v| v.kind == VoiceKind::Predefined).collect();
    let cached: Vec<_> = voices.iter().filter(|v| v.kind == VoiceKind::Cached).collect();
    let custom: Vec<_> = voices.iter().filter(|v| v.kind == VoiceKind::Custom).collect();

    println!("Predefined voices:");
    for v in &predefined {
        println!("  - {}", v.name);
    }
    println!();

    if !cached.is_empty() {
        println!("Cached voices:");
        for v in &cached {
            println!("  - {}", v.name);
        }
        println!();
    }

    if !custom.is_empty() {
        println!("Custom voices:");
        for v in &custom {
            println!("  - {}", v.name);
        }
        println!();
    }

    println!("Voice cache directory: {:?}", tts_engine::voice::get_voice_cache_dir());
    println!("Custom voices directory: {:?}", tts_engine::voice::get_voices_dir());

    Ok(())
}

fn cmd_download_voice(voice_name: &str) -> Result<()> {
    let path = TtsEngine::download_voice(voice_name)?;
    println!("Downloaded voice '{}' to: {:?}", voice_name, path);
    Ok(())
}

fn print_help() {
    println!("Voice Management CLI for Nifty Reader");
    println!();
    println!("Usage: voice-cli <command> [options]");
    println!();
    println!("Commands:");
    println!("  train <input.wav> [output.wav]          Train voice from WAV clip");
    println!("  generate [options]                       Generate voice clip");
    println!("  list-voices                              List available voices");
    println!("  download-voice <name>                    Download predefined voice");
    println!();
    println!("Generate Options:");
    println!("  -p, --phrase <TEXT>   Custom phrase to speak");
    println!("  -v, --voice <NAME>    Voice to use (default: alba)");
    println!("  -o, --output <FILE>   Output WAV file (default: play audio)");
    println!();
    println!("Examples:");
    println!("  voice-cli train my_voice.wav");
    println!("  voice-cli train ref.wav src/assets/voices/custom.wav");
    println!("  voice-cli generate");
    println!("  voice-cli generate --phrase \"Hello world\"");
    println!("  voice-cli generate -p \"Custom text\" -v alba -o output.wav");
    println!("  voice-cli list-voices");
    println!("  voice-cli download-voice alba");
    println!();
    println!("Environment Variables:");
    println!("  HF_TOKEN                 HuggingFace token (for voice/model downloads)");
    println!("  SHERPA_ONNX_MODEL_PATH   Path to sherpa-onnx model directory");
}

fn main() -> Result<()> {
    let args: Vec<String> = env::args().collect();

    if args.len() < 2 {
        print_help();
        exit(1);
    }

    let command = &args[1];

    match command.as_str() {
        "train" => {
            cmd_train(&args[2..])?;
        }
        "generate" => {
            cmd_generate(&args[2..])?;
        }
        "list-voices" => {
            cmd_list_voices()?;
        }
        "download-voice" => {
            if args.len() < 3 {
                eprintln!("Error: Voice name required");
                eprintln!("Usage: voice-cli download-voice <name>");
                exit(1);
            }
            cmd_download_voice(&args[2])?;
        }
        "--help" | "-h" | "help" => {
            print_help();
        }
        _ => {
            eprintln!("Error: Unknown command '{}'", command);
            eprintln!();
            print_help();
            exit(1);
        }
    }

    Ok(())
}
