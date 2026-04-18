#![allow(non_snake_case)]
mod api;
mod components;

use dioxus::prelude::*;
use dioxus::desktop::{Config, WindowBuilder};
use serde::{Deserialize, Serialize};
use tracing::info;
use std::fs;
use std::path::PathBuf;
use directories::ProjectDirs;

use crate::api::{fetch_nifty_story, fetch_latest_stories, Story, StorySummary, HistoryItem};
use crate::components::*;


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
    
    let theme = use_signal(|| state.read().settings.theme.clone());
    let font_size = use_signal(|| state.read().settings.font_size);
    let mut history = use_signal(|| state.read().history.clone());
    
    let mut current_story = use_signal(|| None::<Story>);
    let mut loading = use_signal(|| false);
    let mut error = use_signal(|| String::new());
    let mut input_url = use_signal(|| String::new());
    let mut browse_list = use_signal(Vec::<StorySummary>::new);

    // Initial fetch of browse list
    use_effect(move || {
        spawn(async move {
            if browse_list.read().is_empty() {
                if let Ok(list) = fetch_latest_stories().await {
                    browse_list.set(list);
                }
            }
        });
    });

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


    let container_class = if *theme.read() == "dark" { "bg-slate-900 text-slate-100" } else { "bg-slate-50 text-slate-900" };

    rsx! {
        div { class: "min-h-screen font-sans transition-colors duration-300 {container_class}",
            Header { 
                theme, 
                font_size, 
                current_story 
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
                    div { class: "space-y-16",
                        BrowseView {
                            input_url,
                            browse_list,
                            on_read: move |url| handle_read(url)
                        }
                        HistoryView {
                            history,
                            on_clear: clear_history,
                            on_read: move |url| handle_read(Some(url))
                        }
                    }
                } else if let Some(story) = current_story.read().clone() {
                    ReaderView {
                        story,
                        font_size: *font_size.read(),
                        on_back: move |_| current_story.set(None)
                    }
                }
            }
        }
    }
}
