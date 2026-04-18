use dioxus::prelude::*;
use crate::api::Story;

#[derive(Props, Clone, PartialEq)]
pub struct ReaderViewProps {
    pub story: Story,
    pub font_size: f32,
    pub on_back: EventHandler<()>,
}

#[component]
pub fn ReaderView(props: ReaderViewProps) -> Element {
    let story = props.story;
    let font_size = props.font_size;

    rsx! {
        article { class: "animate-in fade-in slide-in-from-bottom-10 duration-1000",
            button { 
                class: "mb-8 text-slate-500 hover:text-blue-400 font-bold flex items-center gap-2 transition-colors group",
                onclick: move |_| props.on_back.call(()),
                span { class: "group-hover:-translate-x-1 transition-transform", "←" }
                "Library"
            }
            
            header { class: "text-center mb-12",
                h1 { class: "text-4xl md:text-5xl font-black mb-4 leading-[1.1] tracking-tight", "{story.title}" }
                div { class: "h-1.5 w-32 bg-blue-500 mx-auto rounded-full shadow-lg shadow-blue-500/20" }
            }

            div { 
                class: "story-content space-y-8 leading-[1.8] text-slate-300 selection:bg-blue-500/30",
                style: "font-size: {font_size}rem; font-family: 'Inter', system-ui, sans-serif;",
                for (i, p) in story.paragraphs.iter().enumerate() {
                    p { key: "{i}", class: "hover:text-slate-100 transition-colors", "{p}" }
                }
            }

            footer { class: "mt-16 pt-10 border-t border-slate-800/50 flex flex-col items-center gap-6",
                p { class: "text-slate-500 italic", "You've reached the end of the story." }
                button { 
                    class: "bg-slate-800 hover:bg-slate-700 px-8 py-3 rounded-2xl font-bold transition-all flex items-center gap-3 shadow-lg hover:shadow-slate-900/50 active:scale-95",
                    onclick: move |_| {
                        props.on_back.call(());
                    },
                    span { "✨" }
                    "Back to Library"
                }
            }
        }
    }
}
