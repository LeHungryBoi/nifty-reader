use nifty_core::HistoryItem;
use dioxus::prelude::*;

#[derive(Props, Clone, PartialEq)]
pub struct HistoryViewProps {
  pub history: Signal<Vec<HistoryItem>>,
  pub on_clear: EventHandler<()>,
  pub on_read: EventHandler<String>,
  pub on_back: EventHandler<()>,
}

#[component]
pub fn HistoryView(props: HistoryViewProps) -> Element {
  let history = props.history;

  rsx! {
    div { class: "container mx-auto px-4 py-6",
      // Page header
      div { class: "flex items-center justify-between mb-6",
        button {
          class: "btn btn-ghost gap-2",
          onclick: move |_| props.on_back.call(()),
          span { "←" }
          "Back to Browse"
        }
        if !history.read().is_empty() {
          button {
            class: "btn btn-ghost btn-error btn-sm text-base",
            onclick: move |_| props.on_clear.call(()),
            "Clear All"
          }
        }
      }

      // Title
      div { class: "mb-8",
        h2 { class: "text-2xl font-bold flex items-center gap-3",
          span { "🕒" }
          "Reading History"
        }
        p { class: "text-base-content/60 mt-2", "Pick up where you left off." }
      }

      if history.read().is_empty() {
        div { class: "flex flex-col items-center justify-center py-20 gap-4 text-center",
          div { class: "text-5xl", "📭" }
          p { class: "text-base-content/60 text-lg font-medium", "No reading history yet." }
          p { class: "text-base-content/50 text-sm", "Stories you read will appear here." }
          button {
            class: "btn btn-primary",
            onclick: move |_| props.on_back.call(()),
            "Start Browsing"
          }
        }
      } else {
        div { class: "grid grid-cols-1 md:grid-cols-2 gap-3",
          for item in history.read().iter() {
            div {
              class: "card bg-base-200/50 hover:bg-base-200 transition-all border border-base-300 hover:border-primary/30 cursor-pointer hover:shadow-lg",
              onclick: {
                let url = item.url.clone();
                move |_| props.on_read.call(url.clone())
              },
              div { class: "card-body p-4",
                h4 { class: "card-title text-base font-semibold group-hover:text-primary transition-colors", "{item.title}" }
                p { class: "text-sm text-base-content/50 truncate font-mono", "{item.url}" }
              }
            }
          }
        }
      }
    }
  }
}
