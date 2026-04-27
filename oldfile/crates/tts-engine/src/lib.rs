pub mod audio_io;
pub mod model;
pub mod playback;
pub mod voice;

use anyhow::Result;
use std::sync::mpsc;

/// Commands sent to the TTS engine thread
#[derive(Debug)]
pub enum TtsCommand {
    Speak { text: String, voice: String },
    Stop,
    SetVoice { name: String },
}

/// Events emitted by the TTS engine thread
#[derive(Debug)]
pub enum TtsEvent {
    Playing,
    Stopped,
    Error(String),
}

/// The TTS engine that runs in its own thread and processes commands via channels.
pub struct TtsEngine {
    model: &'static sherpa_onnx::OfflineTts,
}

impl TtsEngine {
    /// Create a new TTS engine, loading the model lazily.
    pub fn new() -> Self {
        let model = model::get_model();
        Self { model }
    }

    /// Run the engine loop on the current thread, processing commands from `rx`
    /// and sending events back via `tx`.
    pub fn run(self, rx: mpsc::Receiver<TtsCommand>, tx: mpsc::Sender<TtsEvent>) {
        let stop_flag = playback::StopFlag::new();

        while let Ok(cmd) = rx.recv() {
            match cmd {
                TtsCommand::Speak { text, voice } => {
                    stop_flag.clear();
                    let _ = tx.send(TtsEvent::Playing);

                    if let Err(e) = self.speak_internal(&text, &voice, &stop_flag) {
                        let _ = tx.send(TtsEvent::Error(e.to_string()));
                    }
                    let _ = tx.send(TtsEvent::Stopped);
                }
                TtsCommand::Stop => {
                    stop_flag.set();
                }
                TtsCommand::SetVoice { .. } => {
                    // Voice is resolved per-speak command, nothing to do here
                }
            }
        }
    }

    /// Generate speech and save to WAV file (blocking call, for CLI use).
    pub fn generate_to_file(&self, text: &str, voice: &str, output: &std::path::Path) -> Result<()> {
        let voice_path = voice::get_voice_path(voice)?;
        let gen_config = voice::build_generation_config(&voice_path)?;

        // Generate full audio (no progress callback)
        let audio: sherpa_onnx::GeneratedAudio = self.model.generate_with_config::<fn(&[f32], f32) -> bool>(text, &gen_config, None)
            .ok_or_else(|| anyhow::anyhow!("TTS generation failed"))?;

        // Save to WAV
        if !audio.save(output.to_str().unwrap()) {
            anyhow::bail!("Failed to save audio to {:?}", output);
        }

        Ok(())
    }

    /// Speak text with the given voice (blocking call, for CLI use).
    pub fn speak(&self, text: &str, voice: &str) -> Result<()> {
        let stop_flag = playback::StopFlag::new();
        self.speak_internal(text, voice, &stop_flag)
    }

    /// Stop any ongoing playback (sets a global stop flag).
    pub fn stop() {
        playback::global_stop();
    }

    fn speak_internal(
        &self,
        text: &str,
        voice_name: &str,
        stop_flag: &playback::StopFlag,
    ) -> Result<()> {
        let voice_path = voice::get_voice_path(voice_name)?;
        let gen_config = voice::build_generation_config(&voice_path)?;

        playback::play_stream(self.model, &gen_config, text, stop_flag)
    }

    /// Train a voice embedding from a WAV file and save to output path.
    pub fn train_voice(input: &std::path::Path, output: &std::path::Path) -> Result<()> {
        voice::train_voice(input, output)
    }

    /// List all available voices (predefined, cached, custom).
    pub fn list_voices() -> Vec<VoiceInfo> {
        voice::list_voices()
    }

    /// Download a predefined voice from HuggingFace.
    pub fn download_voice(name: &str) -> Result<std::path::PathBuf> {
        voice::download_voice(name)
    }
}

/// Information about a voice.
#[derive(Debug, Clone)]
pub struct VoiceInfo {
    pub name: String,
    pub kind: VoiceKind,
}

#[derive(Debug, Clone, PartialEq)]
pub enum VoiceKind {
    Predefined,
    Cached,
    Custom,
}
