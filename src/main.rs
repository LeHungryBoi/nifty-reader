#![allow(non_snake_case)]
mod api;

use dioxus::prelude::*;
use dioxus::desktop::{Config, WindowBuilder};
use serde::{Deserialize, Serialize};
use tracing::info;
use std::fs;
use std::path::PathBuf;
use directories::ProjectDirs;

use crate::api::{fetch_nifty_story, Story};

#[derive(Clone, Serialize, Deserialize, Debug, Default)]
struct HistoryItem {
    title: String,
    url: String,
    timestamp: u64,
}

#[derive(Clone, Serialize, Deserialize, Debug)]
struct Settings {
    theme: String,
    font_size: f32,
}

impl Default for Settings {
    fn default() -> Self {
        Self {
            theme: "dark".to_string(),
            font_size: 1.125,
        }
    }
}

#[derive(Clone, Serialize, Deserialize, Debug, Default)]
struct AppState {
    settings: Settings,
    history: Vec<HistoryItem>,
}

fn get_storage_path() -> PathBuf {
    if let Some(proj_dirs) = ProjectDirs::from("com", "lehungryboi", "niftyreader") {
        let config_dir = proj_dirs.config_dir();
        if !config_dir.exists() {
            let _ = fs::create_dir_all(config_dir);
        }
        return config_dir.join("state.json");
    }
    PathBuf::from("state.json")
}

fn load_state() -> AppState {
    let path = get_storage_path();
    if let Ok(content) = fs::read_to_string(path) {
        if let Ok(state) = serde_json::from_str(&content) {
            return state;
        }
    }
    AppState::default()
}

fn save_state(state: &AppState) {
    let path = get_storage_path();
    if let Ok(content) = serde_json::to_string(state) {
        let _ = fs::write(path, content);
    }
}

fn main() {
    info!("Starting NiftyReader Desktop...");
    
    let config = Config::new()
        .with_window(WindowBuilder::new()
            .with_title("NiftyReader")
            .with_inner_size(dioxus::desktop::tao::dpi::LogicalSize::new(1000.0, 800.0)))
        .with_custom_head(r#"
            <script src="https://cdn.tailwindcss.com"></script>
            <style>
                body { background-color: #0f172a; margin: 0; padding: 0; }
                ::-webkit-scrollbar { width: 10px; }
                ::-webkit-scrollbar-track { background: #0f172a; }
                ::-webkit-scrollbar-thumb { background: #334155; border-radius: 5px; }
                ::-webkit-scrollbar-thumb:hover { background: #475569; }
            </style>
        "#.to_string());

    LaunchBuilder::desktop()
        .with_cfg(config)
        .launch(App);
}

fn App() -> Element {
    let state = use_signal(load_state);
    
    let mut theme = use_signal(|| state.read().settings.theme.clone());
    let mut font_size = use_signal(|| state.read().settings.font_size);
    let mut history = use_signal(|| state.read().history.clone());
    
    let mut current_story = use_signal(|| None::<Story>);
    let mut loading = use_signal(|| false);
    let mut error = use_signal(|| String::new());
    let mut input_url = use_signal(|| String::new());

    // Sync settings to file
    use_effect(move || {
        let new_state = AppState {
            settings: Settings {
                theme: theme.read().clone(),
                font_size: *font_size.read(),
            },
            history: history.read().clone(),
        };
        save_state(&new_state);
    });

    let handle_read = move |url_to_fetch: Option<String>| {
        spawn(async move {
            let url = url_to_fetch.unwrap_or_else(|| input_url.read().clone());
            if url.is_empty() { return; }

            loading.set(true);
            error.set(String::new());

            match fetch_nifty_story(&url).await {
                Ok(story) => {
                    // Update history
                    let mut current_history = history.read().clone();
                    current_history.retain(|item| item.url != url);
                    current_history.insert(0, HistoryItem {
                        title: story.title.clone(),
                        url: url.clone(),
                        timestamp: chrono::Utc::now().timestamp() as u64,
                    });
                    if current_history.len() > 50 {
                        current_history.pop();
                    }
                    history.set(current_history);

                    current_story.set(Some(story));
                    input_url.set(String::new());
                }
                Err(e) => {
                    error.set(format!("Error: {}", e));
                }
            }
            loading.set(false);
        });
    };

    let clear_history = move |_| {
        history.set(vec![]);
    };

    let toggle_theme = move |_| {
        if *theme.read() == "dark" {
            theme.set("light".to_string());
        } else {
            theme.set("dark".to_string());
        }
    };

    let container_class = if *theme.read() == "dark" { "bg-slate-900 text-slate-100" } else { "bg-slate-50 text-slate-900" };

    rsx! {
        div { class: "min-h-screen font-sans transition-colors duration-300 {container_class}",
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

            main { class: "max-w-5xl mx-auto px-6 py-10",
                if *loading.read() {
                    div { class: "flex flex-col items-center justify-center py-32 gap-6",
                        div { class: "relative w-16 h-16",
                            div { class: "absolute top-0 left-0 w-full h-full border-4 border-blue-500/20 rounded-full" }
                            div { class: "absolute top-0 left-0 w-full h-full border-4 border-blue-500 border-t-transparent rounded-full animate-spin" }
                        }
                        p { class: "text-slate-400 font-medium animate-pulse", "Preparing your story..." }
                    }
                } else if !error.read().is_empty() {
                    div { class: "bg-red-500/10 border border-red-500/30 text-red-400 p-6 rounded-2xl mb-8 flex items-center gap-4 shadow-lg",
                        span { class: "text-2xl", "⚠️" }
                        p { "{error.read()}" }
                    }
                }

                if current_story.read().is_none() && !*loading.read() {
                    div { class: "space-y-16 animate-in fade-in slide-in-from-bottom-6 duration-700",
                        section { 
                            class: "relative overflow-hidden bg-gradient-to-br from-slate-800/80 to-slate-900/80 p-10 rounded-[2rem] border border-slate-700/50 shadow-2xl backdrop-blur-xl",
                            div { class: "relative z-10",
                                h2 { class: "text-3xl font-bold mb-3 tracking-tight", "Dive into a New Story" }
                                p { class: "text-slate-400 mb-8 max-w-2xl text-lg", "Paste a link from the Nifty Archives to enjoy a distraction-free, premium reading experience." }
                                div { class: "flex flex-col md:flex-row gap-4",
                                    input {
                                        class: "flex-1 bg-slate-950/50 border border-slate-700/50 rounded-2xl px-6 py-4 text-lg focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all placeholder:text-slate-600",
                                        r#type: "url",
                                        placeholder: "https://www.nifty.org/nifty/...",
                                        value: "{input_url}",
                                        oninput: move |evt| input_url.set(evt.value()),
                                        onkeydown: move |evt| if evt.key() == Key::Enter { handle_read(None) }
                                    }
                                    button {
                                        class: "bg-blue-600 hover:bg-blue-500 text-white font-bold px-10 py-4 rounded-2xl transition-all flex items-center justify-center gap-3 shadow-lg shadow-blue-900/20 active:scale-95",
                                        onclick: move |_| handle_read(None),
                                        "Read Now"
                                        span { class: "text-xl", "→" }
                                    }
                                }
                            }
                            div { class: "absolute top-0 right-0 -mr-16 -mt-16 w-64 h-64 bg-blue-500/10 rounded-full blur-3xl" }
                        }

                        if !history.read().is_empty() {
                            section { class: "space-y-6",
                                div { class: "flex justify-between items-end px-2",
                                    h3 { class: "text-2xl font-bold flex items-center gap-3", 
                                        span { class: "text-slate-500", "🕒" }
                                        "Recent Readings" 
                                    }
                                    button { 
                                        class: "text-sm font-semibold text-slate-500 hover:text-red-400 transition-colors uppercase tracking-wider",
                                        onclick: clear_history,
                                        "Clear All"
                                    }
                                }
                                div { class: "grid grid-cols-1 md:grid-cols-2 gap-4",
                                    for item in history.read().iter() {
                                        div { 
                                            class: "group bg-slate-800/20 hover:bg-slate-800/50 p-6 rounded-[1.5rem] border border-slate-800 hover:border-slate-700 cursor-pointer transition-all duration-300 hover:-translate-y-1 shadow-sm hover:shadow-xl",
                                            onclick: {
                                                let url = item.url.clone();
                                                move |_| handle_read(Some(url.clone()))
                                            },
                                            h4 { class: "text-lg font-bold group-hover:text-blue-400 transition-colors line-clamp-1 mb-1", "{item.title}" }
                                            p { class: "text-sm text-slate-500 truncate font-mono", "{item.url}" }
                                        }
                                    }
                                }
                            }
                        }
                    }
                } else if let Some(story) = current_story.read().clone() {
                    article { class: "animate-in fade-in slide-in-from-bottom-10 duration-1000",
                        button { 
                            class: "mb-10 text-slate-500 hover:text-blue-400 font-bold flex items-center gap-2 transition-colors group",
                            onclick: move |_| current_story.set(None),
                            span { class: "group-hover:-translate-x-1 transition-transform", "←" }
                            "Library"
                        }
                        
                        header { class: "text-center mb-20",
                            h1 { class: "text-5xl md:text-6xl font-black mb-6 leading-[1.1] tracking-tight", "{story.title}" }
                            div { class: "h-1.5 w-32 bg-blue-500 mx-auto rounded-full shadow-lg shadow-blue-500/20" }
                        }

                        div { 
                            class: "story-content space-y-8 leading-[1.8] text-slate-300 selection:bg-blue-500/30",
                            style: "font-size: {font_size}rem; font-family: 'Inter', system-ui, sans-serif;",
                            for (i, p) in story.paragraphs.iter().enumerate() {
                                p { key: "{i}", class: "hover:text-slate-100 transition-colors", "{p}" }
                            }
                        }

                        footer { class: "mt-24 pt-12 border-t border-slate-800/50 flex flex-col items-center gap-6",
                            p { class: "text-slate-500 italic", "You've reached the end of the story." }
                            button { 
                                class: "bg-slate-800 hover:bg-slate-700 px-10 py-4 rounded-2xl font-bold transition-all flex items-center gap-3 shadow-lg hover:shadow-slate-900/50 active:scale-95",
                                onclick: move |_| {
                                    current_story.set(None);
                                },
                                span { "✨" }
                                "Back to Library"
                            }
                        }
                    }
                }
            }
        }
    }
}
