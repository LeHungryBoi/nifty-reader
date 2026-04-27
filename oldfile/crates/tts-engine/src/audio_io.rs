use anyhow::{Context, Result};
use std::fs;
use std::io::Read;
use std::path::Path;

/// Validate that a file is a proper WAV file.
pub fn validate_wav(path: &Path) -> Result<()> {
    let metadata = fs::metadata(path).context("Cannot read file metadata")?;
    let file_size = metadata.len();

    if file_size < 1000 {
        anyhow::bail!("File too small to be valid audio");
    }

    if file_size > 100_000_000 {
        anyhow::bail!("File too large (>100MB). Please use shorter audio samples");
    }

    // Check WAV header
    let mut file = fs::File::open(path)?;
    let mut header = [0u8; 12];
    file.read_exact(&mut header)?;

    if &header[0..4] != b"RIFF" {
        anyhow::bail!("Not a valid WAV file (missing RIFF header)");
    }

    if &header[8..12] != b"WAVE" {
        anyhow::bail!("Not a valid WAV file (missing WAVE marker)");
    }

    Ok(())
}
