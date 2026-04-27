use nifty_core::Story;
use dioxus::prelude::*;

#[derive(Props, Clone, PartialEq)]
pub struct HeaderProps {
  pub theme: Signal<String>,
  pub font_size: Signal<f32>,
  pub current_story: Signal<Option<Story>>,
  pub on_open_settings: EventHandler<()>,
  pub on_open_history: EventHandler<()>,
  pub on_refresh: EventHandler<()>,
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
    header { class: "navbar bg-base-100 sticky top-0 z-10 border-b border-base-300",
      div { class: "navbar-start",
        a {
          class: "btn btn-ghost text-xl font-bold gap-2",
          onclick: move |_| current_story.set(None),
          span { "📚" }
          "NiftyReader"
        }
      }
      div { class: "navbar-end gap-2",
        if current_story.read().is_some() {
          div { class: "join",
            button {
              class: "btn btn-sm join-item",
              onclick: move |_| {
                let current = *font_size.read();
                font_size.set((current - 0.1).max(0.8));
              },
              "A-"
            }
            button {
              class: "btn btn-sm join-item",
              onclick: move |_| {
                let current = *font_size.read();
                font_size.set((current + 0.1).min(2.5));
              },
              "A+"
            }
          }
        }
        button {
          class: "btn btn-ghost btn-sm",
          onclick: move |_| props.on_refresh.call(()),
          "🔄"
        }
        button {
          class: "btn btn-ghost btn-sm",
          onclick: move |_| props.on_open_history.call(()),
          "🕒"
        }
        button {
          class: "btn btn-ghost btn-sm",
          onclick: toggle_theme,
          if *theme.read() == "dark" { "☀️" } else { "🌙" }
        }
        button {
          class: "btn btn-ghost btn-sm",
          onclick: move |_| props.on_open_settings.call(()),
          "⚙️"
        }
      }
    }
  }
}
