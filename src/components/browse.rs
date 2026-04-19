use crate::api::StorySummary;
use dioxus::prelude::*;

// ── Static filter lists from search.niftyarchives.org ────────────────────────

const CATEGORIES: &[(&str, &str)] = &[
  ("All", "All"),
  ("Gay Male", "gay"),
  ("Bisexual", "bisexual"),
  ("Lesbian", "lesbian"),
  ("Transgender", "transgender"),
  ("Bestiality", "bestiality"),
];

const SUBCATEGORIES: &[&str] = &[
  "All",
  "adult-friends",
  "adult-youth",
  "athletics",
  "authoritarian",
  "battle",
  "beginnings",
  "bondage",
  "camping",
  "celebrity",
  "college",
  "encounters",
  "highschool",
  "historical",
  "hookers",
  "incest",
  "interracial",
  "masturbation",
  "military",
  "misc",
  "no-sex",
  "non-english",
  "relationships",
  "rural",
  "romance",
  "sf-fantasy",
  "urination",
  "young-friends",
  "by_authors",
  "chemical",
  "control",
  "Joe_Bates_Saga",
  "Magic-ScFi",
  "mind-control",
  "Non-TG-Stories",
  "she-male",
  "surgery",
  "teen",
  "tv",
];

// ─────────────────────────────────────────────────────────────────────────────

#[derive(Props, Clone, PartialEq)]
pub struct BrowseViewProps {
  pub browse_list: Signal<Vec<StorySummary>>,
  pub selected_category: Signal<String>,
  pub selected_subcategory: Signal<String>,
  pub search_query: Signal<String>,
  pub current_page: u32,
  pub on_change_page: EventHandler<u32>,
  pub on_change_category: EventHandler<String>,
  pub on_change_subcategory: EventHandler<String>,
  pub on_search: EventHandler<String>,
  pub on_read: EventHandler<Option<String>>,
}

/// Renders snippet HTML from Nifty server, highlighting <em class="highlight"> terms.
#[component]
fn SnippetView(html: String) -> Element {
  // Simple parser for <em class="highlight">...</em>
  let mut segments = Vec::new();
  let mut current = html.as_str();

  while let Some(start_idx) = current.find("<em class=\"highlight\">") {
    // Text before the highlight
    if start_idx > 0 {
      segments.push(rsx! { "{&current[..start_idx]}" });
    }
    current = &current[start_idx + 22..]; // Skip <em class="highlight">

    if let Some(end_idx) = current.find("</em>") {
      let highlight_text = &current[..end_idx];
      segments.push(rsx! {
        span { class: "bg-blue-500/30 text-blue-200 font-bold px-1 rounded mx-0.5 border border-blue-500/20 shadow-sm",
          "{highlight_text}"
        }
      });
      current = &current[end_idx + 5..]; // Skip </em>
    }
  }

  // Remaining text
  if !current.is_empty() {
    segments.push(rsx! { "{current}" });
  }

  rsx! {
    div { class: "text-xs text-slate-400 leading-relaxed italic bg-slate-950/40 p-3 rounded-xl border border-slate-800/50 mb-3",
      for seg in segments {
        {seg}
      }
    }
  }
}

#[component]
pub fn BrowseView(props: BrowseViewProps) -> Element {
  let browse_list = props.browse_list;
  let selected_category = props.selected_category;
  let selected_subcategory = props.selected_subcategory;

  let mut search_input = use_signal(|| props.search_query.read().clone());
  let stories = browse_list.read();
  let active_search = props.search_query.read().clone();
  let sel_cat = selected_category.read().clone();
  let sel_sub = selected_subcategory.read().clone();

  rsx! {
    div { class: "space-y-8 animate-in fade-in slide-in-from-bottom-6 duration-700",
      section {
        class: "relative overflow-hidden bg-gradient-to-br from-slate-800/80 to-slate-900/80 rounded-3xl border border-slate-700/50 shadow-2xl backdrop-blur-xl",

        div { class: "px-8 pt-8 pb-6 border-b border-slate-700/30",
          h2 { class: "text-2xl font-bold tracking-tight", "Browse Latest Stories" }
          p { class: "text-slate-400 mt-1 text-sm", "Filter by category, subcategory, or search by keywords." }

          div { class: "flex gap-3 mt-5",
            div { class: "relative flex-1",
              span { class: "absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 text-sm pointer-events-none", "🔍" }
              input {
                class: "w-full bg-slate-900/70 border border-slate-700/50 rounded-xl pl-9 pr-4 py-2.5 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500/60 focus:ring-1 focus:ring-blue-500/30 transition-all",
                r#type: "text",
                placeholder: "Search keywords...",
                value: "{search_input.read()}",
                oninput: move |e| search_input.set(e.value()),
                onkeydown: move |e| {
                  if e.key() == Key::Enter {
                    props.on_search.call(search_input.read().clone());
                  }
                }
              }
            }
            button {
              class: "px-5 py-2.5 rounded-xl font-bold text-sm bg-blue-600 hover:bg-blue-500 text-white transition-all border border-blue-500 shadow-lg active:scale-95",
              onclick: move |_| props.on_search.call(search_input.read().clone()),
              "Search"
            }
            if !active_search.is_empty() {
              button {
                class: "px-4 py-2.5 rounded-xl font-bold text-sm bg-slate-700 hover:bg-slate-600 text-slate-300 transition-all border border-slate-600 active:scale-95",
                onclick: move |_| {
                  search_input.set(String::new());
                  props.on_search.call(String::new());
                },
                "✕ Clear"
              }
            }
          }

          if !active_search.is_empty() {
            div { class: "mt-3 flex items-center gap-2",
              span { class: "text-xs text-blue-400 font-semibold", "Showing results for:" }
              span { class: "text-xs bg-blue-500/20 text-blue-300 px-2 py-0.5 rounded-full border border-blue-500/30 font-mono", "\"{active_search}\"" }
            }
          }
        }

        div { class: "px-8 py-5 border-b border-slate-700/20 space-y-4",
          div { class: "space-y-2",
            h4 { class: "text-[10px] font-black uppercase tracking-widest text-slate-500", "Category" }
            div { class: "flex flex-wrap gap-2",
              for (label, value) in CATEGORIES.iter() {
                {
                  let value_str = value.to_string();
                  let is_active = sel_cat == *value;
                  rsx! {
                    button {
                      class: if is_active {
                        "px-3 py-1 rounded-full text-xs font-bold bg-green-500 text-slate-950 transition-all shadow-lg shadow-green-900/20"
                      } else {
                        "px-3 py-1 rounded-full text-xs font-bold bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200 transition-all border border-slate-700/50"
                      },
                      onclick: {
                        let v = value_str.clone();
                        move |_| props.on_change_category.call(v.clone())
                      },
                      "{label}"
                    }
                  }
                }
              }
            }
          }

          div { class: "space-y-2",
            h4 { class: "text-[10px] font-black uppercase tracking-widest text-slate-500", "Subcategory" }
            div { class: "flex flex-wrap gap-2",
              for sub in SUBCATEGORIES.iter() {
                {
                  let sub_str = sub.to_string();
                  let is_active = sel_sub == *sub;
                  rsx! {
                    button {
                      class: if is_active {
                        "px-3 py-1 rounded-full text-xs font-bold bg-blue-500 text-slate-950 transition-all shadow-lg shadow-blue-900/20"
                      } else {
                        "px-3 py-1 rounded-full text-xs font-bold bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200 transition-all border border-slate-700/50"
                      },
                      onclick: {
                        let s = sub_str.clone();
                        move |_| props.on_change_subcategory.call(s.clone())
                      },
                      "{sub}"
                    }
                  }
                }
              }
            }
          }
        }

        div { class: "px-8 py-6",
          if stories.is_empty() {
            div { class: "flex flex-col items-center justify-center py-20 gap-4",
              div { class: "w-8 h-8 border-4 border-blue-500/20 border-t-blue-500 rounded-full animate-spin" }
              p { class: "text-slate-500 text-sm animate-pulse", "Loading stories..." }
            }
          } else {
            div { class: "grid grid-cols-1 gap-4",
              for summary in stories.iter() {
                div {
                  class: "group bg-slate-900/50 rounded-2xl border border-slate-700/30 hover:border-blue-500/30 transition-all duration-300 overflow-hidden shadow-md hover:shadow-blue-900/20 hover:shadow-lg",

                  div { class: "bg-gradient-to-r from-blue-950/70 via-slate-800/60 to-slate-900/60 px-5 pt-4 pb-3 border-b border-slate-700/20",
                    h3 {
                      class: "text-base font-bold leading-snug group-hover:text-blue-300 transition-colors",
                      "{summary.title}"
                    }
                    div { class: "flex flex-wrap items-center gap-1.5 mt-2",
                      for cat in &summary.categories {
                        span {
                          class: "text-[10px] uppercase font-black px-2 py-0.5 rounded-full bg-green-500/15 text-green-400 border border-green-500/25",
                          "{cat}"
                        }
                      }
                      for sub in &summary.subcategories {
                        span {
                          class: "text-[10px] uppercase font-black px-2 py-0.5 rounded-full bg-blue-500/15 text-blue-400 border border-blue-500/25",
                          "{sub}"
                        }
                      }
                      if !summary.date_added.is_empty() {
                        span { class: "ml-auto text-[10px] text-slate-500 font-mono", "{summary.date_added}" }
                      }
                    }
                  }

                  div { class: "px-5 py-4",
                    // Display snippet if available
                    if let Some(snippet) = &summary.snippet {
                      SnippetView { html: snippet.clone() }
                    }

                    div { class: "flex flex-wrap gap-2",
                      if summary.chapters.is_empty() {
                        button {
                          class: "bg-blue-600/10 hover:bg-blue-600 text-blue-400 hover:text-white px-4 py-1.5 rounded-lg text-xs font-bold transition-all border border-blue-500/30 hover:border-blue-500 active:scale-95",
                          onclick: {
                            let url = summary.url.clone();
                            move |_| props.on_read.call(Some(url.clone()))
                          },
                          "▶ Read Now"
                        }
                      } else {
                        for (_idx, (chapter_title, chapter_url)) in summary.chapters.iter().enumerate() {
                          button {
                            class: "bg-slate-700/40 hover:bg-blue-600 text-slate-300 hover:text-white px-3 py-1.5 rounded-lg text-xs font-bold transition-all border border-slate-700/50 hover:border-blue-500/50 active:scale-95",
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

            div { class: "flex justify-center items-center gap-4 mt-10 pt-8 border-t border-slate-700/20",
              button {
                class: if props.current_page > 1 {
                  "px-6 py-2.5 rounded-xl font-bold text-sm bg-slate-800 text-slate-300 hover:bg-slate-700 hover:text-white transition-all border border-slate-700/50 shadow-lg active:scale-95"
                } else {
                  "px-6 py-2.5 rounded-xl font-bold text-sm bg-slate-900/50 text-slate-600 cursor-not-allowed border border-slate-800/50"
                },
                disabled: props.current_page <= 1,
                onclick: move |_| {
                  if props.current_page > 1 {
                    props.on_change_page.call(props.current_page - 1);
                  }
                },
                "← Prev"
              }
              div { class: "flex items-center gap-2 font-bold text-slate-400 bg-slate-900/60 px-5 py-2.5 rounded-xl border border-slate-800 text-sm",
                span { "Page" }
                span { class: "text-blue-400 font-black", "{props.current_page}" }
              }
              button {
                class: "px-6 py-2.5 rounded-xl font-bold text-sm bg-blue-600 text-white hover:bg-blue-500 transition-all border border-blue-500 shadow-lg shadow-blue-900/20 active:scale-95",
                onclick: move |_| props.on_change_page.call(props.current_page + 1),
                "Next →"
              }
            }
          }
        }

        div { class: "absolute top-0 right-0 -mr-20 -mt-20 w-72 h-72 bg-blue-500/5 rounded-full blur-3xl pointer-events-none" }
      }
    }
  }
}
