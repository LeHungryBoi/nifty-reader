use nifty_core::StorySummary;
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
        span { class: "font-bold text-primary mx-0.5",
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
    div { class: "text-xs text-base-content/60 leading-relaxed italic bg-base-200/50 p-3 rounded-lg border border-base-300 mb-3",
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
    div { class: "container mx-auto px-4 py-6 space-y-6",
      section { class: "card bg-base-100 shadow-xl",

        div { class: "card-body space-y-4",
          h2 { class: "card-title text-xl", "Browse Latest Stories" }
          p { class: "text-base-content/60 text-sm", "Filter by category, subcategory, or search by keywords." }

          div { class: "join",
            input {
              class: "input input-bordered input-sm join-item flex-1",
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
            button {
              class: "btn btn-primary btn-sm join-item",
              onclick: move |_| props.on_search.call(search_input.read().clone()),
              "🔍"
            }
            if !active_search.is_empty() {
              button {
                class: "btn btn-ghost btn-sm join-item",
                onclick: move |_| {
                  search_input.set(String::new());
                  props.on_search.call(String::new());
                },
                "✕ Clear"
              }
            }
          }

          if !active_search.is_empty() {
            div { class: "alert alert-info py-2",
              span { class: "text-xs font-semibold", "Showing results for:" }
              span { class: "badge badge-primary font-mono", "\"{active_search}\"" }
            }
          }
        }

        div { class: "divider my-0" }

        div { class: "px-6 py-4 space-y-4",
          div { class: "space-y-2",
            label { class: "label",
              span { class: "label-text-alt font-bold uppercase tracking-wider", "Category" }
            }
            div { class: "flex flex-wrap gap-2",
              for (label, value) in CATEGORIES.iter() {
                {
                  let value_str = value.to_string();
                  let is_active = sel_cat == *value;
                  rsx! {
                    button {
                      class: if is_active {
                        "badge badge-success cursor-pointer"
                      } else {
                        "badge badge-neutral cursor-pointer hover:badge-primary"
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
            label { class: "label",
              span { class: "label-text-alt font-bold uppercase tracking-wider", "Subcategory" }
            }
            div { class: "flex flex-wrap gap-2",
              for sub in SUBCATEGORIES.iter() {
                {
                  let sub_str = sub.to_string();
                  let is_active = sel_sub == *sub;
                  rsx! {
                    button {
                      class: if is_active {
                        "badge badge-primary cursor-pointer"
                      } else {
                        "badge badge-neutral cursor-pointer hover:badge-primary"
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

        div { class: "px-6 py-4",
          if stories.is_empty() {
            div { class: "flex flex-col items-center justify-center py-12 gap-3",
              span { class: "loading loading-spinner loading-md text-primary" }
              p { class: "text-base-content/60 text-sm animate-pulse", "Loading stories..." }
            }
          } else {
            div { class: "space-y-3",
              for summary in stories.iter() {
                div {
                  class: "card bg-base-200/50 hover:bg-base-200 transition-all border border-base-300 hover:border-primary/30",

                  div { class: "card-body p-4",
                    h3 {
                      class: "card-title text-base font-semibold group-hover:text-primary transition-colors",
                      "{summary.title}"
                    }
                    div { class: "flex flex-wrap items-center gap-1.5 mt-2",
                      for cat in &summary.categories {
                        span {
                          class: "badge badge-success badge-sm text-[10px]",
                          "{cat}"
                        }
                      }
                      for sub in &summary.subcategories {
                        span {
                          class: "badge badge-primary badge-sm text-[10px]",
                          "{sub}"
                        }
                      }
                      if !summary.date_added.is_empty() {
                        span { class: "text-xs text-base-content/50 font-mono ml-auto", "{summary.date_added}" }
                      }
                    }
                  }

                  if let Some(snippet) = &summary.snippet {
                    div { class: "px-4 pb-4",
                      SnippetView { html: snippet.clone() }
                    }
                  }

                  div { class: "card-actions justify-end p-4 pt-0",
                    div { class: "flex flex-wrap gap-2",
                      if summary.chapters.is_empty() {
                        button {
                          class: "btn btn-outline btn-primary btn-sm",
                          onclick: {
                            let url = summary.url.clone();
                            move |_| props.on_read.call(Some(url.clone()))
                          },
                          "▶ Read"
                        }
                      } else {
                        for (_idx, (chapter_title, chapter_url)) in summary.chapters.iter().enumerate() {
                          button {
                            class: "btn btn-ghost btn-sm",
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

            div { class: "divider my-6" }

            div { class: "flex justify-center items-center gap-4",
              button {
                class: "btn btn-sm",
                disabled: props.current_page <= 1,
                onclick: move |_| {
                  if props.current_page > 1 {
                    props.on_change_page.call(props.current_page - 1);
                  }
                },
                "← Prev"
              }
              div { class: "badge badge-lg font-bold", "Page {props.current_page}" }
              button {
                class: "btn btn-primary btn-sm",
                onclick: move |_| props.on_change_page.call(props.current_page + 1),
                "Next →"
              }
            }
          }
        }
      }
    }
  }
}
