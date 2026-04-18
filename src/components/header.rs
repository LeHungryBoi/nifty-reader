use dioxus::prelude::*;
use crate::api::Story;

#[derive(Props, Clone, PartialEq)]
pub struct HeaderProps {
    pub theme: Signal<String>,
    pub font_size: Signal<f32>,
    pub current_story: Signal<Option<Story>>,
}

#[component]
pub fn Header(props: HeaderProps) -> Element {
    let mut theme = props.theme;
    let mut font_size = props.font_size;
    let mut current_story = props.current_story;

    let toggle_theme = move |_| {
        if *theme.read() == "dark" {
            theme.set("light".to_string());
        } else {
            theme.set("dark".to_string());
        }
    };

    rsx! {
        header { class: "sticky top-0 z-10 backdrop-blur-md bg-opacity-80 border-b border-slate-700/30 px-6 py-4 flex justify-between items-center",
            div { 
                class: "flex items-center gap-3 text-2xl font-black tracking-tight cursor-pointer hover:opacity-80 transition-opacity",
                onclick: move |_| current_story.set(None),
                span { class: "text-blue-500", "📚" }
                span { "NiftyReader" }
            }
            div { class: "flex items-center gap-4",
                if current_story.read().is_some() {
                    div { class: "flex items-center bg-slate-800/50 rounded-lg p-1 border border-slate-700/30",
                        button { 
                            class: "px-3 py-1 hover:bg-slate-700 rounded transition-colors text-sm font-bold",
                            onclick: move |_| {
                                let current = *font_size.read();
                                font_size.set((current - 0.1).max(0.8));
                            },
                            "A-"
                        }
                        div { class: "w-px h-4 bg-slate-700 mx-1" }
                        button { 
                            class: "px-3 py-1 hover:bg-slate-700 rounded transition-colors text-sm font-bold",
                            onclick: move |_| {
                                let current = *font_size.read();
                                font_size.set((current + 0.1).min(2.5));
                            },
                            "A+"
                        }
                    }
                }
                button { 
                    class: "p-2.5 rounded-xl bg-slate-800/50 hover:bg-slate-700/50 border border-slate-700/30 transition-all text-xl shadow-inner",
                    onclick: toggle_theme,
                    if *theme.read() == "dark" { "☀️" } else { "🌙" }
                }
            }
        }
    }
}
