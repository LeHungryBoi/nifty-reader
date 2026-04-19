use crate::api::Story;
use dioxus::prelude::*;

#[derive(Props, Clone, PartialEq)]
pub struct HeaderProps {
  pub theme: Signal<String>,
  pub font_size: Signal<f32>,
  pub current_story: Signal<Option<Story>>,
  pub on_open_settings: EventHandler<()>,
  pub on_open_history: EventHandler<()>,
  pub on_refresh: EventHandler<()>,
  // TTS props
  pub tts_is_playing: bool,
  pub tts_playback_speed: f32,
  pub on_tts_play: EventHandler<()>,
  pub on_tts_pause: EventHandler<()>,
  pub on_tts_stop: EventHandler<()>,
  pub on_tts_speed_change: EventHandler<f32>,
  pub on_tts_seek: EventHandler<f32>,
  pub on_open_voice_manager: EventHandler<()>,
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
    header { class: "sticky top-0 z-10 backdrop-blur-md bg-opacity-80 border-b border-slate-700/30 px-6 py-3 flex justify-between items-center",
      div {
        class: "flex items-center gap-2 text-xl font-black tracking-tight cursor-pointer hover:opacity-80 transition-opacity",
        onclick: move |_| current_story.set(None),
        span { class: "text-blue-500", "📚" }
        span { "NiftyReader" }
      }
      div { class: "flex items-center gap-4",
        if current_story.read().is_some() {
          // TTS Controls
          crate::components::TTSControls {
            is_playing: props.tts_is_playing,
            playback_speed: props.tts_playback_speed,
            on_play: move |_| props.on_tts_play.call(()),
            on_pause: move |_| props.on_tts_pause.call(()),
            on_stop: move |_| props.on_tts_stop.call(()),
            on_speed_change: move |speed| props.on_tts_speed_change.call(speed),
            on_seek: move |position| props.on_tts_seek.call(position),
          }

          // Voice Manager Button
          button {
            class: "p-2 rounded-xl bg-slate-800/50 hover:bg-slate-700/50 border border-slate-700/30 transition-all text-lg shadow-inner",
            onclick: move |_| props.on_open_voice_manager.call(()),
            title: "Voice Manager",
            "🎤"
          }
        }
        if current_story.read().is_some() {
          div { class: "flex items-center bg-slate-800/50 rounded-lg p-1 border border-slate-700/30",
            button {
              class: "px-2 py-0.5 hover:bg-slate-700 rounded transition-colors text-sm font-bold",
              onclick: move |_| {
                let current = *font_size.read();
                font_size.set((current - 0.1).max(0.8));
              },
              "A-"
            }
            div { class: "w-px h-4 bg-slate-700 mx-1" }
            button {
              class: "px-2 py-0.5 hover:bg-slate-700 rounded transition-colors text-sm font-bold",
              onclick: move |_| {
                let current = *font_size.read();
                font_size.set((current + 0.1).min(2.5));
              },
              "A+"
            }
          }
        }
        button {
          class: "p-2 rounded-xl bg-slate-800/50 hover:bg-slate-700/50 border border-slate-700/30 transition-all text-lg shadow-inner",
          onclick: move |_| props.on_refresh.call(()),
          title: "Refresh",
          "🔄"
        }
        button {
          class: "p-2 rounded-xl bg-slate-800/50 hover:bg-slate-700/50 border border-slate-700/30 transition-all text-lg shadow-inner",
          onclick: move |_| props.on_open_history.call(()),
          title: "Reading History",
          "🕒"
        }
        button {
          class: "p-2 rounded-xl bg-slate-800/50 hover:bg-slate-700/50 border border-slate-700/30 transition-all text-lg shadow-inner",
          onclick: toggle_theme,
          if *theme.read() == "dark" { "☀️" } else { "🌙" }
        }
        button {
          class: "p-2 rounded-xl bg-slate-800/50 hover:bg-slate-700/50 border border-slate-700/30 transition-all text-lg shadow-inner",
          onclick: move |_| props.on_open_settings.call(()),
          "⚙️"
        }
      }
    }
  }
}
