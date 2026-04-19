//! Voice Manager modal for uploading and managing voices
//!
//! Allows users to upload voice prompt files and manage existing voices.

use dioxus::prelude::*;
use crate::tts::VoiceInfo;

#[derive(Props, PartialEq, Clone)]
pub struct VoiceManagerProps {
    pub available_voices: Vec<VoiceInfo>,
    pub on_add_voice: EventHandler<(String, Vec<u8>)>,
    pub on_remove_voice: EventHandler<String>,
    pub on_close: EventHandler<()>,
}

#[component]
pub fn VoiceManager(props: VoiceManagerProps) -> Element {
    let user_voices: Vec<_> = props.available_voices.iter().filter(|v| !v.is_default).cloned().collect();
    rsx! {
        // Modal overlay
        div {
            class: "fixed inset-0 bg-black/50 flex items-center justify-center z-50",
            onclick: move |_| props.on_close.call(()),

            // Modal content
            div {
                class: "bg-slate-800 border border-slate-700 rounded-lg p-6 max-w-md w-full mx-4",
                onclick: |evt| evt.stop_propagation(),

                // Header
                div { class: "flex items-center justify-between mb-4",
                    h2 { class: "text-xl font-semibold text-white", "Voice Manager" }
                    button {
                        class: "text-slate-400 hover:text-white",
                        onclick: move |_| props.on_close.call(()),
                        "✕"
                    }
                }

                // Voice list
                div { class: "space-y-2 mb-4",
                    for voice in user_voices {
                        div { class: "flex items-center justify-between p-2 bg-slate-700 rounded",
                            span { class: "text-white", "{voice.name}" }
                            button {
                                class: "text-red-400 hover:text-red-300 text-sm",
                                onclick: move |_| props.on_remove_voice.call(voice.name.clone()),
                                "Remove"
                            }
                        }
                    }
                }

                // Upload section
                div { class: "border-t border-slate-700 pt-4",
                    h3 { class: "text-lg font-medium text-white mb-2", "Add Voice" }
                    p { class: "text-sm text-slate-300 mb-3",
                        "Upload a WAV file containing a voice sample for cloning."
                    }

                    // File input will be added here - for now just a placeholder
                    div { class: "text-center p-4 border-2 border-dashed border-slate-600 rounded",
                        p { class: "text-slate-400", "Drop WAV file here or click to browse" }
                        p { class: "text-xs text-slate-500 mt-1", "File input implementation pending" }
                    }
                }
            }
        }
    }
}
