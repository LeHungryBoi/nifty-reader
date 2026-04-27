#![allow(non_snake_case)]
mod ui;

use nifty_core::load_state;
use std::sync::mpsc;
use tracing::info;
use tts_engine::{TtsCommand, TtsEngine, TtsEvent};

/// Global TTS command sender, set once in main() and read from UI components.
static TTS_CMD_TX: std::sync::OnceLock<mpsc::Sender<TtsCommand>> = std::sync::OnceLock::new();

/// Get a reference to the global TTS command sender.
pub fn tts_cmd_tx() -> &'static mpsc::Sender<TtsCommand> {
    TTS_CMD_TX.get().expect("TTS command sender not initialized")
}

fn main() {
    info!("Starting NiftyReader Desktop...");

    // 1. Load application state
    let app_state = load_state();

    // 2. Initialize TTS engine and channel communication
    let (cmd_tx, cmd_rx) = mpsc::channel::<TtsCommand>();
    let (event_tx, _event_rx) = mpsc::channel::<TtsEvent>();
    let engine = TtsEngine::new();

    // 3. Store sender in global static
    TTS_CMD_TX.set(cmd_tx).expect("TTS command sender already set");

    // 4. Start TTS thread
    std::thread::spawn(move || {
        engine.run(cmd_rx, event_tx);
    });

    // 5. Launch Slint UI
    let app = ui::App::new(app_state);
    app.run();
}