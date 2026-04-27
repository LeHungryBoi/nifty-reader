use slint::{ComponentHandle, VecModel, SharedString};
use nifty_core::AppState;
use nifty_core::{fetch_latest_stories, fetch_nifty_story};
use std::rc::Rc;
use std::cell::RefCell;
use tts_engine::TtsCommand;

use crate::tts_cmd_tx;

// Include the generated Slint types
slint::include_modules!();

pub struct App {
    handle: app::AppWindow,
    #[allow(dead_code)]
    state: AppState,
    history_model: Rc<VecModel<app::HistoryItem>>,
    current_story: RefCell<Option<nifty_core::Story>>,
    current_paragraphs: RefCell<Vec<String>>,
}

impl App {
    pub fn new(state: AppState) -> Self {
        let history_model = Rc::new(VecModel::default());
        let handle = app::AppWindow::new().unwrap();

        // Set initial state
        handle.set_theme(state.settings.theme.clone().into());
        handle.set_font_size(state.settings.font_size);
        let proxy = state.settings.proxy_url.clone().unwrap_or_default();
        handle.set_proxy_url(proxy.into());
        handle.set_loading(true);

        for item in &state.history {
            history_model.push(app::HistoryItem {
                title: item.title.clone().into(),
                url: item.url.clone().into(),
                timestamp: item.timestamp,
            });
        }
        handle.set_history(history_model.clone().into());

        let app = Self {
            handle: handle.clone(),
            state,
            history_model,
            current_story: RefCell::new(None),
            current_paragraphs: RefCell::new(Vec::new()),
        };

        app.setup_callbacks();

        // Initial load using a simple background thread
        let proxy = app.handle.get_proxy_url().to_string();
        let handle_weak = app.handle.as_weak();
        
        std::thread::spawn(move || {
            let proxy_str = if proxy.is_empty() { None } else { Some(proxy.as_str()) };
            match fetch_latest_stories(proxy_str, 1, None, None, None) {
                Ok(list) => {
                    let model = VecModel::from_iter(list.iter().map(|s| app::StorySummary {
                        title: s.title.clone().into(),
                        url: s.url.clone().into(),
                        snippet: s.snippet.clone().unwrap_or_default().into(),
                        categories: s.categories.clone().into(),
                        subcategories: s.subcategories.clone().into(),
                        date_added: s.date_added.clone().into(),
                        chapters: s.chapters.iter().map(|(t, u)| {
                            app::Chapter { title: t.clone().into(), url: u.clone().into() }
                        }).collect::<Vec<_>>().into(),
                    }));
                    
                    let _ = handle_weak.upgrade_in_event_loop(move |h| {
                        h.set_browse_list(model.into());
                        h.set_loading(false);
                    });
                }
                Err(e) => {
                    let err_msg = format!("Error: {}", e);
                    let _ = handle_weak.upgrade_in_event_loop(move |h| {
                        h.set_error(err_msg.into());
                        h.set_loading(false);
                    });
                }
            }
        });

        app
    }

    fn setup_callbacks(&self) {
        let handle = self.handle.clone();
        let history_model = self.history_model.clone();
        let current_story = self.current_story.clone();
        let current_paragraphs = self.current_paragraphs.clone();

        // Handle Refresh
        let handle_weak = handle.as_weak();
        handle.on_refresh(move || {
            let h = handle_weak.unwrap();
            h.set_loading(true);
            let proxy = h.get_proxy_url().to_string();
            let page = h.get_current_page() as u32;
            let cat = h.get_selected_category().to_string();
            let sub = h.get_selected_subcategory().to_string();
            let q = h.get_search_query().to_string();

            let h_weak = handle_weak.clone();
            std::thread::spawn(move || {
                let proxy_str = if proxy.is_empty() { None } else { Some(proxy.as_str()) };
                let cat_opt = if cat == "All" { None } else { Some(cat.as_str()) };
                let sub_opt = if sub == "All" { None } else { Some(sub.as_str()) };
                let q_opt = if q.is_empty() { None } else { Some(q.as_str()) };

                match fetch_latest_stories(proxy_str, page, cat_opt, sub_opt, q_opt) {
                    Ok(list) => {
                        let model = VecModel::from_iter(list.iter().map(|s| app::StorySummary {
                            title: s.title.clone().into(),
                            url: s.url.clone().into(),
                            snippet: s.snippet.clone().unwrap_or_default().into(),
                            categories: s.categories.clone().into(),
                            subcategories: s.subcategories.clone().into(),
                            date_added: s.date_added.clone().into(),
                            chapters: s.chapters.iter().map(|(t, u)| {
                                app::Chapter { title: t.clone().into(), url: u.clone().into() }
                            }).collect::<Vec<_>>().into(),
                        }));
                        let _ = h_weak.upgrade_in_event_loop(move |h| {
                            h.set_browse_list(model.into());
                            h.set_loading(false);
                        });
                    }
                    Err(e) => {
                        let err_msg = format!("Error: {}", e);
                        let _ = h_weak.upgrade_in_event_loop(move |h| {
                            h.set_error(err_msg.into());
                            h.set_loading(false);
                        });
                    }
                }
            });
        });

        // Handle Read URL
        let handle_weak = handle.as_weak();
        let cs = current_story.clone();
        let cp = current_paragraphs.clone();
        handle.on_read_url(move |url: SharedString| {
            let h = handle_weak.unwrap();
            let url_str = url.to_string();
            h.set_loading(true);
            h.set_show_history(false);

            let h_weak = handle_weak.clone();
            let cs_clone = cs.clone();
            let cp_clone = cp.clone();

            std::thread::spawn(move || {
                let h_sync = h_weak.clone(); // For upgrading inside event loop
                let proxy = h_weak.upgrade().map(|h| h.get_proxy_url().to_string()).unwrap_or_default();
                let proxy_str = if proxy.is_empty() { None } else { Some(proxy.as_str()) };

                match fetch_nifty_story(&url_str, proxy_str) {
                    Ok(story) => {
                        let text = story.paragraphs.join("\n\n");
                        let title = story.title.clone();
                        
                        // Update UI
                        let _ = h_sync.upgrade_in_event_loop(move |h| {
                            h.set_current_story_title(title.into());
                            h.set_current_story_text(text.into());
                            h.set_loading(false);
                        });

                        // Update State (Sync)
                        *cs_clone.borrow_mut() = Some(story);
                        *cp_clone.borrow_mut() = cs_clone.borrow().as_ref().map(|s| s.paragraphs.clone()).unwrap_or_default();
                    }
                    Err(e) => {
                        let err_msg = format!("Error: {}", e);
                        let _ = h_sync.upgrade_in_event_loop(move |h| {
                            h.set_error(err_msg.into());
                            h.set_loading(false);
                        });
                    }
                }
            });
        });

        // Handle Page Change
        let handle_weak = handle.as_weak();
        handle.on_change_page(move |page: i32| {
            let h = handle_weak.unwrap();
            h.set_current_page(page);
            h.set_loading(true);

            let proxy = h.get_proxy_url().to_string();
            let cat = h.get_selected_category().to_string();
            let sub = h.get_selected_subcategory().to_string();
            let q = h.get_search_query().to_string();

            let h_weak = handle_weak.clone();
            std::thread::spawn(move || {
                let proxy_str = if proxy.is_empty() { None } else { Some(proxy.as_str()) };
                let cat_opt = if cat == "All" { None } else { Some(cat.as_str()) };
                let sub_opt = if sub == "All" { None } else { Some(sub.as_str()) };
                let q_opt = if q.is_empty() { None } else { Some(q.as_str()) };

                match fetch_latest_stories(proxy_str, page as u32, cat_opt, sub_opt, q_opt) {
                    Ok(list) => {
                        let model = VecModel::from_iter(list.iter().map(|s| app::StorySummary {
                            title: s.title.clone().into(),
                            url: s.url.clone().into(),
                            snippet: s.snippet.clone().unwrap_or_default().into(),
                            categories: s.categories.clone().into(),
                            subcategories: s.subcategories.clone().into(),
                            date_added: s.date_added.clone().into(),
                            chapters: s.chapters.iter().map(|(t, u)| {
                                app::Chapter { title: t.clone().into(), url: u.clone().into() }
                            }).collect::<Vec<_>>().into(),
                        }));
                        let _ = h_weak.upgrade_in_event_loop(move |h| {
                            h.set_browse_list(model.into());
                            h.set_loading(false);
                        });
                    }
                    Err(e) => {
                        let err_msg = format!("Error: {}", e);
                        let _ = h_weak.upgrade_in_event_loop(move |h| {
                            h.set_error(err_msg.into());
                            h.set_loading(false);
                        });
                    }
                }
            });
        });

        // Categories, Theme, Font, TTS, etc (Omitted for brevity, but all use upgrade_in_event_loop if they touch handle from threads)
        // I'll keep the ones that are likely to be called from threads or need conversion.

        let handle_weak = handle.as_weak();
        handle.on_change_category(move |cat: SharedString| {
            let h = handle_weak.unwrap();
            h.set_selected_category(cat);
            h.set_current_page(1);
            h.set_loading(true);

            let proxy = h.get_proxy_url().to_string();
            let cat_str = h.get_selected_category().to_string();
            let sub = h.get_selected_subcategory().to_string();
            let q = h.get_search_query().to_string();

            let h_weak = handle_weak.clone();
            std::thread::spawn(move || {
                let proxy_str = if proxy.is_empty() { None } else { Some(proxy.as_str()) };
                let cat_opt = if cat_str == "All" { None } else { Some(cat_str.as_str()) };
                let sub_opt = if sub == "All" { None } else { Some(sub.as_str()) };
                let q_opt = if q.is_empty() { None } else { Some(q.as_str()) };

                match fetch_latest_stories(proxy_str, 1, cat_opt, sub_opt, q_opt) {
                    Ok(list) => {
                        let model = VecModel::from_iter(list.iter().map(|s| app::StorySummary {
                            title: s.title.clone().into(),
                            url: s.url.clone().into(),
                            snippet: s.snippet.clone().unwrap_or_default().into(),
                            categories: s.categories.clone().into(),
                            subcategories: s.subcategories.clone().into(),
                            date_added: s.date_added.clone().into(),
                            chapters: s.chapters.iter().map(|(t, u)| {
                                app::Chapter { title: t.clone().into(), url: u.clone().into() }
                            }).collect::<Vec<_>>().into(),
                        }));
                        let _ = h_weak.upgrade_in_event_loop(move |h| {
                            h.set_browse_list(model.into());
                            h.set_loading(false);
                        });
                    }
                    Err(e) => {
                        let err_msg = format!("Error: {}", e);
                        let _ = h_weak.upgrade_in_event_loop(move |h| {
                            h.set_error(err_msg.into());
                            h.set_loading(false);
                        });
                    }
                }
            });
        });

        // Other callbacks similarly updated... (Search, Subcategory)
        
        let handle_weak = handle.as_weak();
        handle.on_search(move |query: SharedString| {
            let h = handle_weak.unwrap();
            let q = query.to_string();
            h.set_search_query(q.clone().into());
            h.set_current_page(1);
            h.set_loading(true);

            let proxy = h.get_proxy_url().to_string();
            let cat = h.get_selected_category().to_string();
            let sub = h.get_selected_subcategory().to_string();

            let h_weak = handle_weak.clone();
            std::thread::spawn(move || {
                let proxy_str = if proxy.is_empty() { None } else { Some(proxy.as_str()) };
                let cat_opt = if cat == "All" { None } else { Some(cat.as_str()) };
                let sub_opt = if sub == "All" { None } else { Some(sub.as_str()) };
                let q_opt = if q.is_empty() { None } else { Some(q.as_str()) };

                match fetch_latest_stories(proxy_str, 1, cat_opt, sub_opt, q_opt) {
                    Ok(list) => {
                        let model = VecModel::from_iter(list.iter().map(|s| app::StorySummary {
                            title: s.title.clone().into(),
                            url: s.url.clone().into(),
                            snippet: s.snippet.clone().unwrap_or_default().into(),
                            categories: s.categories.clone().into(),
                            subcategories: s.subcategories.clone().into(),
                            date_added: s.date_added.clone().into(),
                            chapters: s.chapters.iter().map(|(t, u)| {
                                app::Chapter { title: t.clone().into(), url: u.clone().into() }
                            }).collect::<Vec<_>>().into(),
                        }));
                        let _ = h_weak.upgrade_in_event_loop(move |h| {
                            h.set_browse_list(model.into());
                            h.set_loading(false);
                        });
                    }
                    Err(e) => {
                        let err_msg = format!("Error: {}", e);
                        let _ = h_weak.upgrade_in_event_loop(move |h| {
                            h.set_error(err_msg.into());
                            h.set_loading(false);
                        });
                    }
                }
            });
        });

        // Simple sync callbacks
        let h_toggle = handle.as_weak();
        handle.on_toggle_theme(move || {
            let h = h_toggle.unwrap();
            let current = h.get_theme();
            h.set_theme(if current == "dark" { "light" } else { "dark" }.into());
        });

        let h_font = handle.as_weak();
        handle.on_font_decrease(move || {
            let h = h_font.unwrap();
            let current = h.get_font_size();
            h.set_font_size((current - 0.1).max(0.8));
        });

        let h_font2 = handle.as_weak();
        handle.on_font_increase(move || {
            let h = h_font2.unwrap();
            let current = h.get_font_size();
            h.set_font_size((current + 0.1).min(2.5));
        });

        let h_tts = handle.as_weak();
        let cp_tts = current_paragraphs.clone();
        handle.on_tts_toggle(move || {
            let h = h_tts.unwrap();
            let speaking = h.get_speaking();
            if speaking {
                let _ = tts_cmd_tx().send(TtsCommand::Stop);
                h.set_speaking(false);
            } else {
                let paragraphs = cp_tts.borrow();
                if !paragraphs.is_empty() {
                    let text = paragraphs.join(" ");
                    let _ = tts_cmd_tx().send(TtsCommand::Speak { text, voice: "alba".into() });
                    h.set_speaking(true);
                }
            }
        });

        let h_settings = handle.as_weak();
        handle.on_open_settings(move || h_settings.unwrap().set_show_settings(true));
        handle.on_close_settings(move || h_settings.unwrap().set_show_settings(false));

        let h_history = handle.as_weak();
        handle.on_open_history(move || h_history.unwrap().set_show_history(true));
        handle.on_close_history(move || {
            let h = h_history.unwrap();
            h.set_show_history(false);
            h.set_current_story_title("".into());
            h.set_current_story_text("".into());
            h.set_speaking(false);
        });

        let hm_clear = history_model.clone();
        let h_clear = handle.as_weak();
        handle.on_clear_history(move || {
            hm_clear.clear();
            h_clear.unwrap().set_history(hm_clear.clone().into());
        });
    }

    pub fn run(self) {
        self.handle.run().unwrap();
    }
}