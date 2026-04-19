//! TTS Engine implementation using pocket-tts
//!
//! Manages model loading, synthesis, and sentence-level synchronization.

use pocket_tts::{ModelState, TTSModel, voice_state::init_states};
use regex::Regex;
use std::collections::HashMap;

const POCKET_TTS_VARIANT: &str = "b6369a24";
const FALLBACK_SAMPLE_RATE: usize = 24_000;

#[derive(Clone)]
pub struct VoiceState {
  pub id: String,
  pub model_state: ModelState,
}

#[derive(Clone)]
pub struct TTSEngine {
  model: Option<TTSModel>,
  sentence_splitter: Regex,
  cache: HashMap<String, AudioChunkWithSync>,
}

impl TTSEngine {
  pub fn new() -> Self {
    Self {
      model: None,
      sentence_splitter: Regex::new(r"[^.!?]+[.!?]?").expect("sentence regex"),
      cache: HashMap::new(),
    }
  }

  pub async fn ensure_model_loaded(&mut self) -> Result<(), String> {
    if self.model.is_some() {
      return Ok(());
    }

    let model = TTSModel::load(POCKET_TTS_VARIANT)
      .map_err(|e| format!("Failed to load pocket-tts model '{POCKET_TTS_VARIANT}': {e}"))?;
    self.model = Some(model);
    Ok(())
  }

  pub fn default_voice_state(&self) -> VoiceState {
    VoiceState {
      id: "default".to_string(),
      model_state: init_states(1, 1000),
    }
  }

  pub fn synthesize_with_sync(
    &mut self,
    text: &str,
    voice_state: &VoiceState,
    speed: f32,
  ) -> Result<StreamingAudioWithSync, String> {
    let model = self
      .model
      .as_ref()
      .ok_or_else(|| "TTS model is not loaded".to_string())?;

    let safe_speed = speed.max(0.5);
    let sample_rate = model.sample_rate.max(FALLBACK_SAMPLE_RATE);

    let sentences = segment_sentences(&self.sentence_splitter, text);
    let mut chunks = Vec::with_capacity(sentences.len());
    let mut timestamp = 0.0f32;

    for sentence in sentences {
      let key = cache_key(&sentence.text, voice_state, safe_speed);

      let mut chunk = if let Some(cached) = self.cache.get(&key) {
        cached.clone()
      } else {
        let audio_data = synthesize_sentence_audio(model, &sentence.text, voice_state)?;
        AudioChunkWithSync {
          audio_data,
          word_indices: sentence.word_indices.clone(),
          timestamp: 0.0,
        }
      };

      chunk.word_indices = sentence.word_indices;
      let sentence_secs = chunk.audio_data.len() as f32 / sample_rate as f32 / safe_speed;
      timestamp += sentence_secs.max(0.05);
      chunk.timestamp = timestamp;

      self.cache.insert(key, chunk.clone());
      chunks.push(chunk);
    }

    Ok(StreamingAudioWithSync {
      chunks,
      current_index: 0,
    })
  }

  pub fn get_voice_state(&mut self, voice_path: &str) -> Result<VoiceState, String> {
    let model = self
      .model
      .as_ref()
      .ok_or_else(|| "TTS model is not loaded".to_string())?;

    let state = model
      .get_voice_state(voice_path)
      .map_err(|e| format!("Failed to load voice state from '{voice_path}': {e}"))?;

    Ok(VoiceState {
      id: format!("file:{voice_path}"),
      model_state: state,
    })
  }
}

fn synthesize_sentence_audio(
  model: &TTSModel,
  sentence: &str,
  voice_state: &VoiceState,
) -> Result<Vec<f32>, String> {
  let audio_tensor = model
    .generate(sentence, &voice_state.model_state)
    .map_err(|e| format!("Pocket-TTS generation failed: {e}"))?;

  audio_tensor
    .flatten_all()
    .map_err(|e| format!("Failed to flatten audio tensor: {e}"))?
    .to_vec1::<f32>()
    .map_err(|e| format!("Failed to decode audio samples: {e}"))
}

fn cache_key(text: &str, voice_state: &VoiceState, speed: f32) -> String {
  format!("{}|{}|{speed:.2}", voice_state.id, text)
}

#[derive(Clone)]
struct SentenceSegment {
  text: String,
  word_indices: Vec<usize>,
}

fn segment_sentences(splitter: &Regex, text: &str) -> Vec<SentenceSegment> {
  let mut segments = Vec::new();
  let mut global_word_index = 0usize;

  for mat in splitter.find_iter(text) {
    let sentence = mat.as_str().trim();
    if sentence.is_empty() {
      continue;
    }

    let words = sentence.split_whitespace().count();
    if words == 0 {
      continue;
    }

    let word_indices = (global_word_index..global_word_index + words).collect();
    global_word_index += words;

    segments.push(SentenceSegment {
      text: sentence.to_string(),
      word_indices,
    });
  }

  segments
}

pub struct StreamingAudioWithSync {
  chunks: Vec<AudioChunkWithSync>,
  current_index: usize,
}

impl Iterator for StreamingAudioWithSync {
  type Item = Result<AudioChunkWithSync, String>;

  fn next(&mut self) -> Option<Self::Item> {
    if self.current_index >= self.chunks.len() {
      return None;
    }

    let chunk = self.chunks[self.current_index].clone();
    self.current_index += 1;
    Some(Ok(chunk))
  }
}

#[derive(Clone)]
pub struct AudioChunkWithSync {
  pub audio_data: Vec<f32>,
  pub word_indices: Vec<usize>,
  pub timestamp: f32,
}
