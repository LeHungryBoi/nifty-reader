//! TTS Controls component for playback control
//!
//! Provides play/pause/stop buttons, speed control, and seek functionality.

use dioxus::prelude::*;

#[derive(Props, PartialEq, Clone)]
pub struct TTSControlsProps {
    pub is_playing: bool,
    pub playback_speed: f32,
    pub on_play: EventHandler<()>,
    pub on_pause: EventHandler<()>,
    pub on_stop: EventHandler<()>,
    pub on_speed_change: EventHandler<f32>,
    pub on_seek: EventHandler<f32>,
}

#[component]
pub fn TTSControls(props: TTSControlsProps) -> Element {
    let play_pause_icon = if props.is_playing { "⏸️" } else { "▶️" };
    let play_pause_handler = if props.is_playing { props.on_pause } else { props.on_play };

    rsx! {
        div { class: "flex items-center gap-3 p-3 bg-slate-800/50 rounded-lg border border-slate-700/50",
            // Play/Pause button (toggles icon)
            button {
                class: "flex items-center justify-center w-10 h-10 bg-blue-600 hover:bg-blue-700 text-white rounded-full transition-colors duration-200",
                onclick: move |_| play_pause_handler.call(()),
                span { class: "text-lg", "{play_pause_icon}" }
            }

            // Stop button
            button {
                class: "flex items-center justify-center w-8 h-8 bg-slate-600 hover:bg-slate-700 text-white rounded transition-colors duration-200",
                onclick: move |_| props.on_stop.call(()),
                span { class: "text-sm", "⏹️" }
            }

            // Speed control
            div { class: "flex items-center gap-2",
                span { class: "text-sm text-slate-300", "Speed:" }
                select {
                    class: "bg-slate-700 text-white px-2 py-1 rounded text-sm border border-slate-600",
                    value: "{props.playback_speed}",
                    onchange: move |evt| {
                        if let Ok(speed) = evt.value().parse::<f32>() {
                            props.on_speed_change.call(speed);
                        }
                    },
                    option { value: "0.5", "0.5x" }
                    option { value: "1.0", "1x" }
                    option { value: "1.5", "1.5x" }
                    option { value: "2.0", "2x" }
                }
            }

            // Seek slider (placeholder for now)
            div { class: "flex items-center gap-2 flex-1 max-w-xs",
                span { class: "text-sm text-slate-300", "Seek:" }
                input {
                    r#type: "range",
                    min: "0",
                    max: "100",
                    step: "1",
                    class: "flex-1 h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer slider",
                    oninput: move |evt| {
                        if let Ok(value) = evt.value().parse::<f32>() {
                            props.on_seek.call(value / 100.0);
                        }
                    }
                }
            }
        }
    }
}
