use crate::api::HistoryItem;
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
    div { class: "animate-in fade-in slide-in-from-bottom-6 duration-500",
      // Page header
      div { class: "flex items-center justify-between mb-8",
        button {
          class: "flex items-center gap-2 text-slate-400 hover:text-blue-400 font-bold transition-colors group",
          onclick: move |_| props.on_back.call(()),
          span { class: "group-hover:-translate-x-1 transition-transform", "←" }
          "Back to Browse"
        }
        if !history.read().is_empty() {
          button {
            class: "text-sm font-semibold text-slate-500 hover:text-red-400 transition-colors uppercase tracking-wider",
            onclick: move |_| props.on_clear.call(()),
            "Clear All"
          }
        }
      }

      // Title
      div { class: "mb-8",
        h2 { class: "text-3xl font-black tracking-tight flex items-center gap-3",
          span { class: "text-blue-500", "🕒" }
          "Reading History"
        }
        p { class: "text-slate-400 mt-2", "Pick up where you left off." }
      }

      if history.read().is_empty() {
        div { class: "flex flex-col items-center justify-center py-32 gap-4 text-center",
          div { class: "text-5xl", "📭" }
          p { class: "text-slate-400 text-lg font-medium", "No reading history yet." }
          p { class: "text-slate-500 text-sm", "Stories you read will appear here." }
          button {
            class: "mt-4 px-6 py-2.5 rounded-xl font-bold bg-blue-600 hover:bg-blue-500 text-white transition-all border border-blue-500 shadow-lg",
            onclick: move |_| props.on_back.call(()),
            "Start Browsing"
          }
        }
      } else {
        div { class: "grid grid-cols-1 md:grid-cols-2 gap-4",
          for item in history.read().iter() {
            div {
              class: "group bg-slate-800/30 hover:bg-slate-800/60 rounded-2xl border border-slate-700/30 hover:border-blue-500/30 cursor-pointer transition-all duration-300 hover:-translate-y-0.5 shadow-sm hover:shadow-xl overflow-hidden",
              onclick: {
                let url = item.url.clone();
                move |_| props.on_read.call(url.clone())
              },
              // Colored title bar
              div { class: "bg-gradient-to-r from-blue-900/50 to-slate-800/60 px-5 py-3 border-b border-slate-700/20",
                h4 { class: "text-base font-bold group-hover:text-blue-300 transition-colors line-clamp-1", "{item.title}" }
              }
              // URL + timestamp
              div { class: "px-5 py-3",
                p { class: "text-sm text-slate-500 truncate font-mono", "{item.url}" }
              }
            }
          }
        }
      }
    }
  }
}
