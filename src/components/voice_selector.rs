//! Voice Selector component for choosing TTS voices
//!
//! Dropdown to select from available voices.

use dioxus::prelude::*;
use crate::tts::VoiceInfo;

#[derive(Props, PartialEq, Clone)]
pub struct VoiceSelectorProps {
    pub available_voices: Vec<VoiceInfo>,
    pub selected_voice: String,
    pub on_voice_change: EventHandler<String>,
}

#[component]
pub fn VoiceSelector(props: VoiceSelectorProps) -> Element {
    rsx! {
        div { class: "flex items-center gap-2 mb-4",
            span { class: "text-sm text-slate-300", "Voice:" }
            select {
                class: "bg-slate-700 text-white px-3 py-2 rounded border border-slate-600 min-w-32",
                value: "{props.selected_voice}",
                onchange: move |evt| {
                    props.on_voice_change.call(evt.value());
                },
                for voice in props.available_voices {
                    option {
                        value: "{voice.name}",
                        "{voice.name}"
                        if voice.is_default {
                            " (Default)"
                        }
                    }
                }
            }
        }
    }
}
