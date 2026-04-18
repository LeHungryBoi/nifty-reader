use dioxus::prelude::*;
use crate::api::StorySummary;

#[derive(Props, Clone, PartialEq)]
pub struct BrowseViewProps {
    pub input_url: Signal<String>,
    pub browse_list: Signal<Vec<StorySummary>>,
    pub on_read: EventHandler<Option<String>>,
}

#[component]
pub fn BrowseView(props: BrowseViewProps) -> Element {
    let mut input_url = props.input_url;
    let browse_list = props.browse_list;

    rsx! {
        div { class: "space-y-16 animate-in fade-in slide-in-from-bottom-6 duration-700",
            section { 
                class: "relative overflow-hidden bg-gradient-to-br from-slate-800/80 to-slate-900/80 p-10 rounded-[2rem] border border-slate-700/50 shadow-2xl backdrop-blur-xl",
                div { class: "relative z-10",
                    h2 { class: "text-3xl font-bold mb-3 tracking-tight", "Browse Latest Stories" }
                    p { class: "text-slate-400 mb-8 max-w-2xl text-lg", "Discover something new or paste a specific link to start reading." }
                    div { class: "flex flex-col md:flex-row gap-4 mb-10",
                        input {
                            class: "flex-1 bg-slate-950/50 border border-slate-700/50 rounded-2xl px-6 py-4 text-lg focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all placeholder:text-slate-600",
                            r#type: "url",
                            placeholder: "https://www.nifty.org/nifty/...",
                            value: "{input_url}",
                            oninput: move |evt| input_url.set(evt.value()),
                            onkeydown: move |evt| if evt.key() == Key::Enter { props.on_read.call(None) }
                        }
                        button {
                            class: "bg-blue-600 hover:bg-blue-500 text-white font-bold px-10 py-4 rounded-2xl transition-all flex items-center justify-center gap-3 shadow-lg shadow-blue-900/20 active:scale-95",
                            onclick: move |_| props.on_read.call(None),
                            "Read URL"
                        }
                    }

                    if browse_list.read().is_empty() {
                        div { class: "flex justify-center py-10",
                            div { class: "w-8 h-8 border-4 border-blue-500/20 border-t-blue-500 rounded-full animate-spin" }
                        }
                    } else {
                        div { class: "grid grid-cols-1 gap-6",
                            for summary in browse_list.read().iter() {
                                div { 
                                    class: "group bg-slate-900/40 hover:bg-slate-900/60 p-6 rounded-2xl border border-slate-700/30 hover:border-blue-500/30 transition-all duration-300",
                                    div { class: "flex flex-col md:flex-row justify-between items-start md:items-center gap-4",
                                        div { class: "flex-1",
                                            h3 { class: "text-xl font-bold group-hover:text-blue-400 transition-colors mb-2", "{summary.title}" }
                                            div { class: "flex flex-wrap gap-2",
                                                for cat in &summary.categories {
                                                    span { class: "text-[10px] uppercase font-black px-2 py-0.5 rounded bg-green-500/10 text-green-500 border border-green-500/20", "{cat}" }
                                                }
                                                for sub in &summary.subcategories {
                                                    span { class: "text-[10px] uppercase font-black px-2 py-0.5 rounded bg-blue-500/10 text-blue-500 border border-blue-500/20", "{sub}" }
                                                }
                                            }
                                        }
                                        div { class: "flex flex-wrap gap-2 justify-end",
                                            if summary.chapters.is_empty() {
                                                button { 
                                                    class: "bg-blue-600/10 hover:bg-blue-600 text-blue-400 hover:text-white px-4 py-2 rounded-xl text-sm font-bold transition-all border border-blue-500/20",
                                                    onclick: {
                                                        let url = summary.url.clone();
                                                        move |_| props.on_read.call(Some(url.clone()))
                                                    },
                                                    "Read Now"
                                                }
                                            } else {
                                                for (_idx, (chapter_title, chapter_url)) in summary.chapters.iter().enumerate() {
                                                    button { 
                                                        class: "bg-slate-700/30 hover:bg-blue-600 text-slate-300 hover:text-white px-3 py-1.5 rounded-lg text-xs font-bold transition-all border border-slate-700/50 hover:border-blue-500/50",
                                                        onclick: {
                                                            let url = chapter_url.clone();
                                                            move |_| props.on_read.call(Some(url.clone()))
                                                        },
                                                        "{chapter_title}"
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                div { class: "absolute top-0 right-0 -mr-16 -mt-16 w-64 h-64 bg-blue-500/10 rounded-full blur-3xl" }
            }
        }
    }
}
