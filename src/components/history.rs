use dioxus::prelude::*;
use crate::api::HistoryItem;

#[derive(Props, Clone, PartialEq)]
pub struct HistoryViewProps {
    pub history: Signal<Vec<HistoryItem>>,
    pub on_clear: EventHandler<()>,
    pub on_read: EventHandler<String>,
}

#[component]
pub fn HistoryView(props: HistoryViewProps) -> Element {
    let history = props.history;

    rsx! {
        if !history.read().is_empty() {
            section { class: "space-y-6",
                div { class: "flex justify-between items-end px-2",
                    h3 { class: "text-xl font-bold flex items-center gap-3", 
                        span { class: "text-slate-500", "🕒" }
                        "Recent Readings" 
                    }
                    button { 
                        class: "text-sm font-semibold text-slate-500 hover:text-red-400 transition-colors uppercase tracking-wider",
                        onclick: move |_| props.on_clear.call(()),
                        "Clear All"
                    }
                }
                div { class: "grid grid-cols-1 md:grid-cols-2 gap-4",
                    for item in history.read().iter() {
                        div { 
                            class: "group bg-slate-800/20 hover:bg-slate-800/50 p-4 rounded-2xl border border-slate-800 hover:border-slate-700 cursor-pointer transition-all duration-300 hover:-translate-y-1 shadow-sm hover:shadow-xl",
                            onclick: {
                                let url = item.url.clone();
                                move |_| props.on_read.call(url.clone())
                            },
                            h4 { class: "text-base font-bold group-hover:text-blue-400 transition-colors line-clamp-1 mb-1", "{item.title}" }
                            p { class: "text-sm text-slate-500 truncate font-mono", "{item.url}" }
                        }
                    }
                }
            }
        }
    }
}
