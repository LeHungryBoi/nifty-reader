use nifty_core::Story;
use crate::tts_cmd_tx;
use dioxus::prelude::*;
use regex::Regex;
use tts_engine::TtsCommand;

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
    return rsx! { p { class: "hover:text-base-content transition-colors", "{text}" } };
  }

  // Case-insensitive highlighting
  let re = match Regex::new(&format!(r"(?i){}", regex::escape(&query))) {
    Ok(re) => re,
    Err(_) => return rsx! { p { class: "hover:text-base-content transition-colors", "{text}" } },
  };

  let mut segments = Vec::new();
  let mut last_idx = 0;
  for mat in re.find_iter(&text) {
    if mat.start() > last_idx {
      segments.push(rsx! { "{&text[last_idx..mat.start()]}" });
    }
    segments.push(rsx! {
      span { class: "font-bold text-primary underline decoration-2 underline-offset-2",
        "{&text[mat.start()..mat.end()]}"
      }
    });
    last_idx = mat.end();
  }
  if last_idx < text.len() {
    segments.push(rsx! { "{&text[last_idx..]}" });
  }

  rsx! {
    p { class: "hover:text-base-content transition-colors",
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
  let mut speaking = use_signal(|| false);

  rsx! {
    article { class: "container mx-auto px-4 py-6",
      div { class: "flex justify-between items-center mb-4",
        button {
          class: "btn btn-ghost btn-sm gap-2",
          onclick: move |_| props.on_back.call(()),
          span { "←" }
          "Library"
        }

        button {
          class: "btn btn-primary btn-sm gap-2",
          onclick: move |_| {
            if *speaking.read() {
              tts_cmd_tx().send(TtsCommand::Stop).ok();
              speaking.set(false);
            } else {
              let text = story.paragraphs.join(" ");
              tts_cmd_tx().send(TtsCommand::Speak { text, voice: "alba".into() }).ok();
              speaking.set(true);
            }
          },
          if *speaking.read() { "⏹ Stop" } else { "🔊 Read Aloud" }
        }
      }

      header { class: "text-center mb-8",
        h1 { class: "text-3xl md:text-4xl font-bold mb-3", "{story.title}" }
      }

      div {
        class: "prose prose-base max-w-none text-base-content",
        style: "font-size: {font_size}rem;",
        for (i, p) in story.paragraphs.iter().enumerate() {
          HighlightedParagraph { key: "{i}", text: p.clone(), query: search_query.clone() }
        }
      }

      div { class: "divider my-10" }

      footer { class: "text-center space-y-4",
        p { class: "text-base-content/60 italic", "You've reached the end of the story." }
        button {
          class: "btn btn-primary gap-2",
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
