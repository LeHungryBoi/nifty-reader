//! Voice management for TTS
//!
//! Handles voice cloning from audio files, storage, and selection.

use directories::ProjectDirs;
use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};
// use pocket_tts::VoiceState;  // TODO: Uncomment when pocket-tts is available
use crate::tts::engine::VoiceState;

/// Information about a voice
#[derive(Clone, Debug, PartialEq)]
pub struct VoiceInfo {
  pub name: String,
  pub path: PathBuf,
  pub is_default: bool,
}

/// Manages voice files and voice state caching
#[derive(Clone)]
pub struct VoiceManager {
  voices_dir: PathBuf,
  cached_states: HashMap<String, VoiceState>,
}

impl VoiceManager {
  /// Create a new voice manager
  pub fn new() -> Result<Self, String> {
    let proj_dirs = ProjectDirs::from("com", "niftyreader", "nifty-reader")
      .ok_or("Could not determine project directories")?;

    let voices_dir = proj_dirs.data_dir().join("voices");
    fs::create_dir_all(&voices_dir)
      .map_err(|e| format!("Failed to create voices directory: {}", e))?;

    Ok(Self {
      voices_dir,
      cached_states: HashMap::new(),
    })
  }

  /// Get all available voices (default + user-uploaded)
  pub fn get_available_voices(&self) -> Vec<VoiceInfo> {
    let mut voices = vec![VoiceInfo {
      name: "Default".to_string(),
      path: PathBuf::new(), // Special case - no file
      is_default: true,
    }];

    // Add user-uploaded voices
    if let Ok(entries) = fs::read_dir(&self.voices_dir) {
      for entry in entries.flatten() {
        if let Some(ext) = entry.path().extension() {
          if ext == "wav" {
            if let Some(name) = entry.path().file_stem() {
              voices.push(VoiceInfo {
                name: name.to_string_lossy().to_string(),
                path: entry.path(),
                is_default: false,
              });
            }
          }
        }
      }
    }

    voices
  }

  /// Add a new voice from a WAV file
  pub fn add_voice(&mut self, name: &str, wav_data: &[u8]) -> Result<(), String> {
    let filename = format!("{}.wav", name);
    let filepath = self.voices_dir.join(filename);

    fs::write(&filepath, wav_data).map_err(|e| format!("Failed to save voice file: {}", e))?;

    // Clear cached state if it exists
    self.cached_states.remove(name);

    Ok(())
  }

  /// Remove a voice
  pub fn remove_voice(&mut self, name: &str) -> Result<(), String> {
    let filename = format!("{}.wav", name);
    let filepath = self.voices_dir.join(filename);

    if filepath.exists() {
      fs::remove_file(&filepath).map_err(|e| format!("Failed to remove voice file: {}", e))?;
      self.cached_states.remove(name);
      Ok(())
    } else {
      Err("Voice file not found".to_string())
    }
  }

  /// Get voice state for a voice (with caching)
  pub fn get_voice_state(
    &mut self,
    voice_name: &str,
    engine: &mut crate::tts::TTSEngine,
  ) -> Result<VoiceState, String> {
    // Check cache first
    if let Some(state) = self.cached_states.get(voice_name) {
      return Ok(state.clone());
    }

    let state = if voice_name == "Default" {
      engine.default_voice_state()
    } else {
      // Load from file
      let filename = format!("{}.wav", voice_name);
      let filepath = self.voices_dir.join(filename);

      if !filepath.exists() {
        return Err(format!("Voice file not found: {}", filepath.display()));
      }

      engine.get_voice_state(filepath.to_str().unwrap())?
    };

    // Cache the state
    self
      .cached_states
      .insert(voice_name.to_string(), state.clone());

    Ok(state)
  }

  /// Validate a voice file (basic WAV check)
  pub fn validate_voice_file(data: &[u8]) -> bool {
    // Basic WAV header check
    data.len() >= 44 && &data[0..4] == b"RIFF" && &data[8..12] == b"WAVE"
  }
}
