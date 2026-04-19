//! Text-to-Speech module for NiftyReader
//!
//! Provides AI-powered TTS synthesis with word-level synchronization
//! for real-time text highlighting during playback.

pub mod engine;
pub mod voice_manager;
pub mod sync;

pub use engine::TTSEngine;
pub use voice_manager::{VoiceManager, VoiceInfo};
pub use sync::WordBoundarySync;