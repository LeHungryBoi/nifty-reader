use crate::api::Story;
use dioxus::prelude::*;
use regex::Regex;

#[derive(Props, Clone, PartialEq)]
pub struct ReaderViewProps {
  pub story: Story,
  pub font_size: f32,
  pub search_query: String,
  pub on_back: EventHandler<()>,
}

#[component]
fn HighlightedParagraph(text: String, query: String) -> Element {
  if query.is_empty() {
    return rsx! { p { class: "hover:text-slate-100 transition-colors", "{text}" } };
  }

  // Case-insensitive highlighting
  let re = match Regex::new(&format!(r"(?i){}", regex::escape(&query))) {
    Ok(re) => re,
    Err(_) => return rsx! { p { class: "hover:text-slate-100 transition-colors", "{text}" } },
  };

  let mut segments = Vec::new();
  let mut last_idx = 0;
  for mat in re.find_iter(&text) {
    if mat.start() > last_idx {
      segments.push(rsx! { "{&text[last_idx..mat.start()]}" });
    }
    segments.push(rsx! {
      span { class: "font-bold text-slate-100 underline decoration-blue-500/30 decoration-2 underline-offset-2",
        "{&text[mat.start()..mat.end()]}"
      }
    });
    last_idx = mat.end();
  }
  if last_idx < text.len() {
    segments.push(rsx! { "{&text[last_idx..]}" });
  }

  rsx! {
    p { class: "hover:text-slate-100 transition-colors",
      for seg in segments {
        {seg}
      }
    }
  }
}

#[component]
pub fn ReaderView(props: ReaderViewProps) -> Element {
  let story = props.story;
  let font_size = props.font_size;
  let search_query = props.search_query.clone();

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
          HighlightedParagraph { key: "{i}", text: p.clone(), query: search_query.clone() }
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
