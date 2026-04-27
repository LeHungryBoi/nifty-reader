use anyhow::Result;
use rodio::{OutputStream, Sink, buffer::SamplesBuffer};
use sherpa_onnx::{GenerationConfig, OfflineTts};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;

/// Global stop flag for simple stop() calls (backward compatible with old tts.rs API).
static GLOBAL_STOP: AtomicBool = AtomicBool::new(false);

/// A shared stop flag for controlling playback.
#[derive(Clone)]
pub struct StopFlag {
    inner: Arc<AtomicBool>,
}

impl StopFlag {
    pub fn new() -> Self {
        Self {
            inner: Arc::new(AtomicBool::new(false)),
        }
    }

    pub fn set(&self) {
        self.inner.store(true, Ordering::SeqCst);
    }

    pub fn clear(&self) {
        self.inner.store(false, Ordering::SeqCst);
    }

    pub fn is_set(&self) -> bool {
        self.inner.load(Ordering::SeqCst)
    }
}

/// Set the global stop flag.
pub fn global_stop() {
    GLOBAL_STOP.store(true, Ordering::SeqCst);
}

/// Clear the global stop flag.
fn global_clear() {
    GLOBAL_STOP.store(false, Ordering::SeqCst);
}

/// Generate full audio and play it through the speakers.
/// sherpa-onnx generates the complete audio first, then we play it via rodio.
/// Respects both the per-call stop flag and the global stop flag.
pub fn play_stream(
    model: &OfflineTts,
    gen_config: &GenerationConfig,
    text: &str,
    stop_flag: &StopFlag,
) -> Result<()> {
    global_clear();

    // Generate full audio (sherpa-onnx doesn't support true streaming, no progress callback)
    let audio: sherpa_onnx::GeneratedAudio = model.generate_with_config::<fn(&[f32], f32) -> bool>(text, gen_config, None)
        .ok_or_else(|| anyhow::anyhow!("TTS generation failed"))?;

    if stop_flag.is_set() || GLOBAL_STOP.load(Ordering::SeqCst) {
        return Ok(());
    }

    // Play the generated audio via rodio
    let (_stream, stream_handle) = OutputStream::try_default()?;
    let sink = Sink::try_new(&stream_handle)?;

    let samples = audio.samples().to_vec();
    let sample_rate = audio.sample_rate() as u32;
    let source = SamplesBuffer::new(1, sample_rate, samples);
    sink.append(source);
    sink.sleep_until_end();

    Ok(())
}
