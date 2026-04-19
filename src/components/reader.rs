use crate::api::Story;
use dioxus::prelude::*;
use regex::Regex;

#[derive(Props, Clone, PartialEq)]
pub struct ReaderViewProps {
  pub story: Story,
  pub font_size: f32,
  pub search_query: String,
  pub on_back: EventHandler<()>,
  // TTS props
  pub available_voices: Vec<crate::tts::VoiceInfo>,
  pub selected_voice: String,
  pub current_word_index: Option<usize>,
  pub on_voice_change: EventHandler<String>,
}

#[component]
fn HighlightedParagraph(text: String, query: String, current_word_index: Option<usize>) -> Element {
  // Split text into words for TTS highlighting
  let words: Vec<&str> = text.split_whitespace().collect();
  let total_words = words.len();

  if query.is_empty() && current_word_index.is_none() {
    return rsx! { p { class: "hover:text-slate-100 transition-colors", "{text}" } };
  }

  // If we have a current word index, highlight that word
  if let Some(word_idx) = current_word_index {
    if word_idx < total_words {
      // Reconstruct text with current word highlighted
      let mut result = Vec::new();

      for (i, word) in words.iter().enumerate() {
        if i == word_idx {
          // Highlight current word
          result.push(rsx! {
            span {
              class: "bg-yellow-300 text-slate-900 font-bold px-0.5 rounded transition-all duration-200",
              "{word}"
            }
          });
        } else {
          result.push(rsx! { "{word}" });
        }

        // Add space after word (except last)
        if i < total_words - 1 {
          result.push(rsx! { " " });
        }
      }

      return rsx! {
        p { class: "hover:text-slate-100 transition-colors",
          for segment in result {
            {segment}
          }
        }
      };
    }
  }

  // Fall back to search highlighting if no TTS highlighting
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
  let current_word_index = props.current_word_index;

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

      // Voice Selector
      crate::components::VoiceSelector {
        available_voices: props.available_voices.clone(),
        selected_voice: props.selected_voice.clone(),
        on_voice_change: move |voice| props.on_voice_change.call(voice),
      }

      div {
        class: "story-content space-y-8 leading-[1.8] text-slate-300 selection:bg-blue-500/30",
        style: "font-size: {font_size}rem; font-family: 'Inter', system-ui, sans-serif;",
        for (i, p) in story.paragraphs.iter().enumerate() {
          HighlightedParagraph {
            key: "{i}",
            text: p.clone(),
            query: search_query.clone(),
            current_word_index: current_word_index
          }
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
