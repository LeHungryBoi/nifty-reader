/// Sherpa-ONNX Model Downloader
///
/// This utility downloads and caches Sherpa-ONNX TTS models for use with Nifty Reader.
/// Run this once before using TTS features to avoid runtime delays.
///
/// Usage:
///   cargo run --release --bin download-models
///
/// Environment Variables:
///   HF_TOKEN                  - HuggingFace authentication token (optional, required for private repos)
///   SHERPA_ONNX_CACHE_DIR     - Custom cache directory (optional, defaults to src/assets/models/sherpa-onnx-pocket-tts/)
///
/// Models Downloaded:
///   - lm_flow.int8.onnx       - Language model flow network
///   - lm_main.int8.onnx       - Main language model
///   - encoder.onnx            - Audio encoder
///   - decoder.int8.onnx       - Audio decoder
///   - text_conditioner.onnx   - Text conditioning network
///   - vocab.json              - Vocabulary file
///   - token_scores.json       - Token scoring data
///
/// The models are cached locally and reused on subsequent runs.

use std::env;
use std::fs;
use std::path::{Path, PathBuf};

// Model files to download
const MODEL_FILES: &[(&str, &str)] = &[
    ("lm_flow.int8.onnx", "https://huggingface.co/k2-fsa/sherpa-onnx-pocket-tts/resolve/main/lm_flow.int8.onnx"),
    ("lm_main.int8.onnx", "https://huggingface.co/k2-fsa/sherpa-onnx-pocket-tts/resolve/main/lm_main.int8.onnx"),
    ("encoder.onnx", "https://huggingface.co/k2-fsa/sherpa-onnx-pocket-tts/resolve/main/encoder.onnx"),
    ("decoder.int8.onnx", "https://huggingface.co/k2-fsa/sherpa-onnx-pocket-tts/resolve/main/decoder.int8.onnx"),
    ("text_conditioner.onnx", "https://huggingface.co/k2-fsa/sherpa-onnx-pocket-tts/resolve/main/text_conditioner.onnx"),
    ("vocab.json", "https://huggingface.co/k2-fsa/sherpa-onnx-pocket-tts/resolve/main/vocab.json"),
    ("token_scores.json", "https://huggingface.co/k2-fsa/sherpa-onnx-pocket-tts/resolve/main/token_scores.json"),
];

fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("Sherpa-ONNX Model Downloader");
    println!("=============================\n");

    let cache_dir = get_cache_dir();
    println!("Cache directory: {:?}", cache_dir);
    println!();

    // Ensure cache directory exists
    fs::create_dir_all(&cache_dir)?;

    // Check which files need downloading
    let mut needs_download = false;
    let mut files_to_download = Vec::new();

    for (filename, _url) in MODEL_FILES {
        let file_path = cache_dir.join(filename);
        if !file_path.exists() {
            needs_download = true;
            files_to_download.push(*filename);
        } else {
            println!("  ✓ {} already cached", filename);
        }
    }

    if !needs_download {
        println!();
        println!("All models are up to date!");
        println!("Location: {:?}", cache_dir);
        println!();
        println!("You can now run: cargo run --release");
        return Ok(());
    }

    println!();
    println!("Downloading {} model file(s)...", files_to_download.len());
    println!("This may take several minutes depending on your connection.\n");

    // Check for HF_TOKEN
    let has_token = env::var("HF_TOKEN").is_ok();
    if !has_token {
        println!("Note: HF_TOKEN not set. If the repository is private, downloads will fail.");
        println!("Set it with: $env:HF_TOKEN=\"hf_xxx\" (PowerShell)");
        println!("            export HF_TOKEN=hf_xxx (bash)\n");
    }

    // Download each file
    for (i, filename) in files_to_download.iter().enumerate() {
        let url = MODEL_FILES.iter()
            .find(|(name, _)| name == filename)
            .map(|(_, url)| *url)
            .unwrap();

        let dest = cache_dir.join(filename);
        println!("[{}/{}] Downloading {}...", i + 1, files_to_download.len(), filename);

        if let Err(e) = download_file(url, &dest) {
            eprintln!("Failed to download {}: {}", filename, e);
            eprintln!("Hint: You may need to set HF_TOKEN environment variable");
            // Clean up partial download
            fs::remove_file(&dest).ok();
            std::process::exit(1);
        }

        println!("      Saved: {:?}\n", dest);
    }

    println!();
    println!("Download complete!");
    println!("Models location: {:?}", cache_dir);
    println!();
    println!("You can now run: cargo run --release");
    println!("The application will automatically use these cached models.");

    Ok(())
}

fn get_cache_dir() -> PathBuf {
    // Use custom cache dir if specified, otherwise use project's default folder
    if let Ok(cache) = env::var("SHERPA_ONNX_CACHE_DIR") {
        PathBuf::from(cache)
    } else {
        PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap_or_else(|_| ".".to_string()))
            .join("src")
            .join("assets")
            .join("models")
            .join("sherpa-onnx-pocket-tts")
    }
}

fn download_file(url: &str, dest: &Path) -> Result<(), Box<dyn std::error::Error>> {
    if let Some(parent) = dest.parent() {
        fs::create_dir_all(parent)?;
    }

    let mut request = ureq::get(url)
        .timeout(std::time::Duration::from_secs(600));

    // Add authentication if available
    if let Ok(token) = env::var("HF_TOKEN") {
        request = request.header("Authorization", &format!("Bearer {}", token));
    }

    let response = request.call()?;

    if response.status() != 200 {
        return Err(format!("HTTP error: {}", response.status()).into());
    }

    use std::io::Read;
    let mut bytes = Vec::new();
    response.into_reader().read_to_end(&mut bytes)?;
    fs::write(dest, &bytes)?;

    Ok(())
}
