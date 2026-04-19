#![allow(non_snake_case)]
mod api;
mod components;
mod tts;

use dioxus::desktop::{Config, WindowBuilder};
use dioxus::prelude::*;
use directories::ProjectDirs;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;
use std::time::Duration;
use tracing::info;

use crate::api::{HistoryItem, Story, StorySummary, fetch_latest_stories, fetch_nifty_story};
use crate::components::*;

#[derive(Clone, Debug)]
struct TTSState {
  is_playing: bool,
  current_word_index: Option<usize>,
  playback_speed: f32,
  selected_voice: String,
  available_voices: Vec<crate::tts::VoiceInfo>,
  playback_session: u64,
}

#[derive(Clone, Serialize, Deserialize, Debug)]
struct Settings {
  theme: String,
  font_size: f32,
  proxy_url: Option<String>,
}

impl Default for Settings {
  fn default() -> Self {
    Self {
      theme: "dark".to_string(),
      font_size: 1.0,
      proxy_url: None,
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
    .with_window(
      WindowBuilder::new()
        .with_title("NiftyReader")
        .with_inner_size(dioxus::desktop::tao::dpi::LogicalSize::new(1000.0, 800.0)),
    )
    .with_disable_context_menu(true)
    .with_custom_head(r#"<link rel="icon" href="data:,">"#.to_string());

  LaunchBuilder::desktop().with_cfg(config).launch(App);
}

fn App() -> Element {
  let mut state = use_signal(load_state);

  let theme = use_signal(|| state.read().settings.theme.clone());
  let font_size = use_signal(|| state.read().settings.font_size);
  let mut history = use_signal(|| state.read().history.clone());

  let mut current_story = use_signal(|| None::<Story>);
  let mut loading = use_signal(|| false);
  let mut error = use_signal(|| String::new());
  let mut input_url = use_signal(|| String::new());
  let mut browse_list = use_signal(Vec::<StorySummary>::new);
  let mut show_settings = use_signal(|| false);
  let mut show_history = use_signal(|| false);
  let mut show_voice_manager = use_signal(|| false);
  let mut selected_category = use_signal(|| "All".to_string());
  let mut selected_subcategory = use_signal(|| "All".to_string());
  let mut search_query = use_signal(|| String::new());
  let mut current_page = use_signal(|| 1u32);
  let proxy_url = use_signal(|| state.read().settings.proxy_url.clone());

  // TTS state - single signal for all TTS state
  let mut tts_state = use_signal(|| TTSState {
    is_playing: false,
    current_word_index: None,
    playback_speed: 1.0,
    selected_voice: "Default".to_string(),
    available_voices: vec![],
    playback_session: 0,
  });

  // TTS engine and voice manager (internal, not exposed to UI)
  let mut tts_engine = use_signal(|| None::<crate::tts::TTSEngine>);
  let mut voice_manager = use_signal(|| None::<crate::tts::VoiceManager>);

  let handle_refresh = move |_| {
    loading.set(true);
    let proxy = proxy_url.read().clone();
    let page = *current_page.read();
    let cat = selected_category.read().clone();
    let sub = selected_subcategory.read().clone();
    let q = search_query.read().clone();
    spawn(async move {
      if let Ok(list) =
        fetch_latest_stories(proxy.as_deref(), page, Some(&cat), Some(&sub), Some(&q)).await
      {
        browse_list.set(list);
      }
      loading.set(false);
    });
  };

  // Initial fetch of browse list
  use_effect(move || {
    spawn(async move {
      if browse_list.read().is_empty() {
        let proxy = proxy_url.read().clone();
        if let Ok(list) = fetch_latest_stories(proxy.as_deref(), 1, None, None, None).await {
          browse_list.set(list);
        }
      }
    });
  });

  // Initialize TTS components
  use_effect(move || {
    spawn(async move {
      // Initialize TTS engine
      let mut engine = crate::tts::TTSEngine::new();
      if let Err(e) = engine.ensure_model_loaded().await {
        tracing::error!("Failed to initialize TTS engine: {}", e);
        return;
      }
      tts_engine.set(Some(engine));

      // Initialize voice manager
      match crate::tts::VoiceManager::new() {
        Ok(vm) => {
          let voices = vm.get_available_voices();
          let mut state = tts_state.read().clone();
          state.available_voices = voices;
          if !state
            .available_voices
            .iter()
            .any(|voice| voice.name == state.selected_voice)
          {
            state.selected_voice = state
              .available_voices
              .iter()
              .find(|voice| voice.is_default)
              .map(|voice| voice.name.clone())
              .unwrap_or_else(|| "Default".to_string());
          }
          voice_manager.set(Some(vm));
          tts_state.set(state);
        }
        Err(e) => {
          tracing::error!("Failed to initialize voice manager: {}", e);
        }
      }
    });
  });

  use_effect(move || {
    let _story = current_story.read().clone();
    let mut state = tts_state.read().clone();
    state.is_playing = false;
    state.current_word_index = None;
    state.playback_session = state.playback_session.wrapping_add(1);
    tts_state.set(state);
  });

  // Fetch when page changes
  let on_change_page = move |new_page: u32| {
    current_page.set(new_page);
    loading.set(true);
    let proxy = proxy_url.read().clone();
    let cat = selected_category.read().clone();
    let sub = selected_subcategory.read().clone();
    let q = search_query.read().clone();
    spawn(async move {
      if let Ok(list) =
        fetch_latest_stories(proxy.as_deref(), new_page, Some(&cat), Some(&sub), Some(&q)).await
      {
        browse_list.set(list);
      }
      loading.set(false);
    });
  };

  // Fetch when category changes — resets subcategory + page + search
  let on_change_category = move |new_cat: String| {
    selected_category.set(new_cat.clone());
    selected_subcategory.set("All".to_string());
    current_page.set(1);
    loading.set(true);
    let proxy = proxy_url.read().clone();
    let q = search_query.read().clone();
    spawn(async move {
      if let Ok(list) =
        fetch_latest_stories(proxy.as_deref(), 1, Some(&new_cat), None, Some(&q)).await
      {
        browse_list.set(list);
      }
      loading.set(false);
    });
  };

  // Fetch when subcategory changes
  let on_change_subcategory = move |new_sub: String| {
    selected_subcategory.set(new_sub.clone());
    current_page.set(1);
    loading.set(true);
    let proxy = proxy_url.read().clone();
    let cat = selected_category.read().clone();
    let q = search_query.read().clone();
    spawn(async move {
      if let Ok(list) =
        fetch_latest_stories(proxy.as_deref(), 1, Some(&cat), Some(&new_sub), Some(&q)).await
      {
        browse_list.set(list);
      }
      loading.set(false);
    });
  };

  // Fetch when search query changes
  let on_search = move |new_query: String| {
    search_query.set(new_query.clone());
    current_page.set(1);
    loading.set(true);
    let proxy = proxy_url.read().clone();
    let cat = selected_category.read().clone();
    let sub = selected_subcategory.read().clone();
    spawn(async move {
      if let Ok(list) = fetch_latest_stories(
        proxy.as_deref(),
        1,
        Some(&cat),
        Some(&sub),
        Some(&new_query),
      )
      .await
      {
        browse_list.set(list);
      }
      loading.set(false);
    });
  };

  // Sync settings to file
  use_effect(move || {
    let new_state = AppState {
      settings: Settings {
        theme: theme.read().clone(),
        font_size: *font_size.read(),
        proxy_url: proxy_url.read().clone(),
      },
      history: history.read().clone(),
    };
    save_state(&new_state);
    state.set(new_state);
  });

  let mut handle_read = move |url_override: Option<String>| {
    let url = url_override.unwrap_or_else(|| input_url.read().clone());
    if url.is_empty() {
      return;
    }

    loading.set(true);
    error.set(String::new());
    show_history.set(false); // close history page when reading

    let proxy = proxy_url.read().clone();

    spawn(async move {
      match fetch_nifty_story(&url, proxy.as_deref()).await {
        Ok(story) => {
          let mut new_history = history.read().clone();
          new_history.retain(|item| item.url != url);
          new_history.insert(
            0,
            HistoryItem {
              title: story.title.clone(),
              url: url.clone(),
              timestamp: chrono::Utc::now().timestamp() as u64,
            },
          );
          new_history.truncate(20);
          history.set(new_history);

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

  let container_class = if *theme.read() == "dark" {
    "bg-slate-900 text-slate-100"
  } else {
    "bg-slate-50 text-slate-900"
  };

  rsx! {
    style { {include_str!("../assets/main.css")} }
    div { class: "min-h-screen font-sans transition-colors duration-300 {container_class}",
      Header {
        theme,
        font_size,
        current_story,
        on_open_settings: move |_| show_settings.set(true),
        on_open_history: move |_| {
          show_history.set(true);
          current_story.set(None);
        },
        on_refresh: handle_refresh,
        // TTS props
        tts_is_playing: tts_state.read().is_playing,
        tts_playback_speed: tts_state.read().playback_speed,
        on_tts_play: move |_| {
          if let Some(story) = current_story.read().clone() {
            let mut engine = match tts_engine.read().clone() {
              Some(engine) => engine,
              None => {
                tracing::error!("TTS engine not initialized");
                return;
              }
            };

            let mut vm = match voice_manager.read().clone() {
              Some(vm) => vm,
              None => {
                tracing::error!("Voice manager not initialized");
                return;
              }
            };

            let mut state = tts_state.read().clone();
            state.is_playing = true;
            state.playback_session = state.playback_session.wrapping_add(1);
            let session = state.playback_session;
            let speed = state.playback_speed.max(0.5);
            let selected_voice = state.selected_voice.clone();
            tts_state.set(state);

            spawn(async move {
              let text = story.paragraphs.join("\n");
              if text.trim().is_empty() {
                let mut current = tts_state.read().clone();
                current.is_playing = false;
                current.current_word_index = None;
                tts_state.set(current);
                return;
              }

              let voice_state = match vm.get_voice_state(&selected_voice, &mut engine) {
                Ok(voice_state) => voice_state,
                Err(err) => {
                  tracing::error!("Unable to load voice state: {}", err);
                  let mut current = tts_state.read().clone();
                  current.is_playing = false;
                  tts_state.set(current);
                  return;
                }
              };

              let stream = match engine.synthesize_with_sync(&text, &voice_state, speed) {
                Ok(stream) => stream,
                Err(err) => {
                  tracing::error!("TTS synthesis failed: {}", err);
                  let mut current = tts_state.read().clone();
                  current.is_playing = false;
                  tts_state.set(current);
                  return;
                }
              };

              let mut previous_timestamp = 0.0f32;
              for chunk in stream {
                let state = tts_state.read().clone();
                if !state.is_playing || state.playback_session != session {
                  break;
                }

                let chunk = match chunk {
                  Ok(chunk) => chunk,
                  Err(err) => {
                    tracing::error!("Failed to read synthesized chunk: {}", err);
                    break;
                  }
                };

                if let Some(last_word_index) = chunk.word_indices.last().copied() {
                  tts_state.set(TTSState {
                    current_word_index: Some(last_word_index),
                    ..state
                  });
                }

                let chunk_delay = (chunk.timestamp - previous_timestamp).max(0.05);
                previous_timestamp = chunk.timestamp;
                tokio::time::sleep(Duration::from_secs_f32(chunk_delay)).await;
              }

              tts_engine.set(Some(engine));
              voice_manager.set(Some(vm));

              let state = tts_state.read().clone();
              if state.playback_session == session {
                tts_state.set(TTSState {
                  is_playing: false,
                  current_word_index: None,
                  ..state
                });
              }
            });
          }
        },
        on_tts_pause: move |_| {
          let mut state = tts_state.read().clone();
          state.is_playing = false;
          tts_state.set(state);
        },
        on_tts_stop: move |_| {
          let mut state = tts_state.read().clone();
          state.is_playing = false;
          state.current_word_index = None;
          state.playback_session = state.playback_session.wrapping_add(1);
          tts_state.set(state);
        },
        on_tts_speed_change: move |speed| {
          let mut state = tts_state.read().clone();
          state.playback_speed = speed;
          tts_state.set(state);
        },
        on_tts_seek: move |_| {
          // TODO: Implement seek logic
        },
        on_open_voice_manager: move |_| {
          show_voice_manager.set(true);
        }
      }

      if *show_settings.read() {
        SettingsView {
          proxy_url,
          on_close: move |_| show_settings.set(false)
        }
      }

      if *show_voice_manager.read() {
        crate::components::VoiceManager {
          available_voices: tts_state.read().available_voices.clone(),
          on_add_voice: move |_| {
            // TODO: Implement voice file upload
          },
          on_remove_voice: move |voice_name| {
            // TODO: Implement voice removal
            tracing::info!("Remove voice: {}", voice_name);
          },
          on_close: move |_| show_voice_manager.set(false)
        }
      }

      main { class: "max-w-4xl mx-auto px-6 py-8",
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

        // Routing: history page > reader > browse
        if *show_history.read() {
          HistoryView {
            history,
            on_clear: clear_history,
            on_read: move |url| handle_read(Some(url)),
            on_back: move |_| show_history.set(false)
          }
        } else if let Some(story) = current_story.read().clone() {
          ReaderView {
            story,
            font_size: *font_size.read(),
            search_query: search_query.read().clone(),
            on_back: move |_| current_story.set(None),
            // TTS props
            available_voices: tts_state.read().available_voices.clone(),
            selected_voice: tts_state.read().selected_voice.clone(),
            current_word_index: tts_state.read().current_word_index,
            on_voice_change: move |voice| {
              let mut state = tts_state.read().clone();
              state.selected_voice = voice;
              tts_state.set(state);
            }
          }
        } else if !*loading.read() {
          BrowseView {
            browse_list,
            selected_category,
            selected_subcategory,
            search_query,
            current_page: *current_page.read(),
            on_change_page,
            on_change_category,
            on_change_subcategory,
            on_search,
            on_read: move |url| handle_read(url)
          }
        }
      }
    }
  }
}
