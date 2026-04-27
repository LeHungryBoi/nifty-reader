use sherpa_onnx::{OfflineTts, OfflineTtsConfig, OfflineTtsPocketModelConfig, OfflineTtsModelConfig};
use std::env;
use std::sync::OnceLock;

static MODEL: OnceLock<OfflineTts> = OnceLock::new();

/// Default model variant directory name.
const DEFAULT_VARIANT: &str = "sherpa-onnx-pocket-tts";

/// Get or lazily load the TTS model singleton.
pub fn get_model() -> &'static OfflineTts {
    MODEL.get_or_init(|| {
        let model_dir = env::var("SHERPA_ONNX_MODEL_PATH")
            .unwrap_or_else(|_| DEFAULT_VARIANT.to_string());

        let config = build_config(&model_dir);
        OfflineTts::create(&config)
            .unwrap_or_else(|| panic!("Failed to load sherpa-onnx TTS model from '{}'", model_dir))
    })
}

/// Build sherpa-onnx configuration from model directory.
fn build_config(model_dir: &str) -> OfflineTtsConfig {
    let model_path = std::path::Path::new(model_dir);

    OfflineTtsConfig {
        model: OfflineTtsModelConfig {
            pocket: OfflineTtsPocketModelConfig {
                lm_flow: Some(model_path.join("lm_flow.int8.onnx").to_string_lossy().into_owned()),
                lm_main: Some(model_path.join("lm_main.int8.onnx").to_string_lossy().into_owned()),
                encoder: Some(model_path.join("encoder.onnx").to_string_lossy().into_owned()),
                decoder: Some(model_path.join("decoder.int8.onnx").to_string_lossy().into_owned()),
                text_conditioner: Some(model_path.join("text_conditioner.onnx").to_string_lossy().into_owned()),
                vocab_json: Some(model_path.join("vocab.json").to_string_lossy().into_owned()),
                token_scores_json: Some(model_path.join("token_scores.json").to_string_lossy().into_owned()),
                voice_embedding_cache_capacity: 50,
            },
            num_threads: 2,
            debug: false,
            ..Default::default()
        },
        ..Default::default()
    }
}
