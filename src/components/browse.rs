use crate::api::StorySummary;
use dioxus::prelude::*;

#[derive(Props, Clone, PartialEq)]
pub struct BrowseViewProps {
  pub browse_list: Signal<Vec<StorySummary>>,
  pub selected_category: Signal<String>,
  pub selected_subcategory: Signal<String>,
  pub current_page: u32,
  pub on_change_page: EventHandler<u32>,
  pub on_read: EventHandler<Option<String>>,
}

#[component]
pub fn BrowseView(props: BrowseViewProps) -> Element {
  let browse_list = props.browse_list;
  let mut selected_category = props.selected_category;
  let mut selected_subcategory = props.selected_subcategory;

  let stories = browse_list.read();

  // Extract unique categories and subcategories
  let mut categories = vec!["All".to_string()];
  let mut subcategories = vec!["All".to_string()];

  for story in stories.iter() {
    for cat in &story.categories {
      if !categories.contains(cat) {
        categories.push(cat.clone());
      }
    }
  }

  // Filter stories by category first to determine available subcategories
  let stories_in_cat: Vec<_> = stories
    .iter()
    .filter(|s| {
      *selected_category.read() == "All" || s.categories.contains(&*selected_category.read())
    })
    .collect();

  for story in stories_in_cat.iter() {
    for sub in &story.subcategories {
      if !subcategories.contains(sub) {
        subcategories.push(sub.clone());
      }
    }
  }

  // Sort categories (keep "All" at the beginning)
  if categories.len() > 1 {
    let mut rest = categories.split_off(1);
    rest.sort();
    categories.extend(rest);
  }
  if subcategories.len() > 1 {
    let mut rest = subcategories.split_off(1);
    rest.sort();
    subcategories.extend(rest);
  }

  let filtered_stories: Vec<_> = stories
    .iter()
    .filter(|s| {
      let cat_match =
        *selected_category.read() == "All" || s.categories.contains(&*selected_category.read());
      let sub_match = *selected_subcategory.read() == "All"
        || s.subcategories.contains(&*selected_subcategory.read());
      cat_match && sub_match
    })
    .collect();

  rsx! {
      div { class: "space-y-12 animate-in fade-in slide-in-from-bottom-6 duration-700",
          section {
              class: "relative overflow-hidden bg-gradient-to-br from-slate-800/80 to-slate-900/80 p-8 rounded-3xl border border-slate-700/50 shadow-2xl backdrop-blur-xl",
              div { class: "relative z-10",
                  h2 { class: "text-2xl font-bold mb-2 tracking-tight", "Browse Latest Stories" }
                  p { class: "text-slate-400 mb-6 max-w-2xl text-base", "Discover something new or paste a specific link to start reading." }



                  // Filter UI
                  if !stories.is_empty() {
                      div { class: "space-y-6 mb-10 pb-8 border-b border-slate-700/30",
                          div { class: "space-y-3",
                              h4 { class: "text-xs font-black uppercase tracking-widest text-slate-500", "Categories" }
                              div { class: "flex flex-wrap gap-2",
                                  for cat in categories {
                                      button {
                                          class: if *selected_category.read() == cat {
                                              "px-4 py-1.5 rounded-full text-xs font-bold bg-green-500 text-slate-950 transition-all shadow-lg shadow-green-900/20"
                                          } else {
                                              "px-4 py-1.5 rounded-full text-xs font-bold bg-slate-800 text-slate-400 hover:bg-slate-700 transition-all border border-slate-700/50"
                                          },
                                          onclick: {
                                              let cat = cat.clone();
                                              move |_| {
                                                  selected_category.set(cat.clone());
                                                  // Reset subcategory when category changes
                                                  selected_subcategory.set("All".to_string());
                                              }
                                          },
                                          "{cat}"
                                      }
                                  }
                              }
                          }

                          div { class: "space-y-3",
                              h4 { class: "text-xs font-black uppercase tracking-widest text-slate-500", "Subcategories" }
                              div { class: "flex flex-wrap gap-2",
                                  for sub in subcategories {
                                      button {
                                          class: if *selected_subcategory.read() == sub {
                                              "px-4 py-1.5 rounded-full text-xs font-bold bg-blue-500 text-slate-950 transition-all shadow-lg shadow-blue-900/20"
                                          } else {
                                              "px-4 py-1.5 rounded-full text-xs font-bold bg-slate-800 text-slate-400 hover:bg-slate-700 transition-all border border-slate-700/50"
                                          },
                                          onclick: {
                                              let sub = sub.clone();
                                              move |_| {
                                                  selected_subcategory.set(sub.clone());
                                              }
                                          },
                                          "{sub}"
                                      }
                                  }
                              }
                          }
                      }
                  }

                  if stories.is_empty() {
                      div { class: "flex justify-center py-10",
                          div { class: "w-8 h-8 border-4 border-blue-500/20 border-t-blue-500 rounded-full animate-spin" }
                      }
                  } else if filtered_stories.is_empty() {
                      div { class: "py-20 text-center space-y-4",
                          div { class: "text-4xl", "🔍" }
                          p { class: "text-slate-400 text-lg", "No stories match your selected filters." }
                          button {
                              class: "text-blue-400 hover:text-blue-300 font-bold",
                              onclick: move |_| {
                                  selected_category.set("All".to_string());
                                  selected_subcategory.set("All".to_string());
                              },
                              "Reset all filters"
                          }
                      }
                  } else {
                      div { class: "grid grid-cols-1 gap-6",
                          for summary in filtered_stories {
                              div {
                                  class: "group bg-slate-900/40 hover:bg-slate-900/60 p-5 rounded-2xl border border-slate-700/30 hover:border-blue-500/30 transition-all duration-300",
                                  div { class: "flex flex-col md:flex-row justify-between items-start md:items-center gap-4",
                                      div { class: "flex-1",
                                          h3 { class: "text-lg font-bold group-hover:text-blue-400 transition-colors mb-2", "{summary.title}" }
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

                      // Pagination UI
                      div { class: "flex justify-center items-center gap-6 mt-12",
                          button {
                              class: if props.current_page > 1 {
                                  "px-6 py-2.5 rounded-xl font-bold bg-slate-800 text-slate-300 hover:bg-slate-700 hover:text-white transition-all border border-slate-700/50 shadow-lg"
                              } else {
                                  "px-6 py-2.5 rounded-xl font-bold bg-slate-900/50 text-slate-600 cursor-not-allowed border border-slate-800/50"
                              },
                              disabled: props.current_page <= 1,
                              onclick: move |_| {
                                  if props.current_page > 1 {
                                      props.on_change_page.call(props.current_page - 1);
                                  }
                              },
                              "← Previous Page"
                          }
                          div { class: "flex items-center gap-2 font-bold text-slate-400 bg-slate-900/40 px-4 py-2 rounded-xl border border-slate-800",
                              span { "Page" }
                              span { class: "text-blue-400", "{props.current_page}" }
                          }
                          button {
                              class: "px-6 py-2.5 rounded-xl font-bold bg-blue-600 text-white hover:bg-blue-500 transition-all border border-blue-500 shadow-lg shadow-blue-900/20 active:scale-95",
                              onclick: move |_| props.on_change_page.call(props.current_page + 1),
                              "Next Page →"
                          }
                      }
                  }
              }
              div { class: "absolute top-0 right-0 -mr-16 -mt-16 w-64 h-64 bg-blue-500/10 rounded-full blur-3xl" }
          }
      }
  }
}
