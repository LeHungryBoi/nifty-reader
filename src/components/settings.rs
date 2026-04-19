use dioxus::prelude::*;

#[derive(Props, Clone, PartialEq)]
pub struct SettingsViewProps {
  pub proxy_url: Signal<Option<String>>,
  pub on_close: EventHandler<()>,
}

#[component]
pub fn SettingsView(props: SettingsViewProps) -> Element {
  let mut proxy_url = props.proxy_url;
  let mut temp_proxy = use_signal(|| proxy_url.read().clone().unwrap_or_default());

  rsx! {
      div { class: "fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-300",
          div { class: "bg-slate-900 w-full max-w-md rounded-3xl border border-slate-800 shadow-2xl overflow-hidden animate-in zoom-in-95 duration-300",
              div { class: "p-8",
                  div { class: "flex justify-between items-center mb-8",
                      h2 { class: "text-2xl font-black tracking-tight", "Settings" }
                      button {
                          class: "p-2 hover:bg-slate-800 rounded-xl transition-colors",
                          onclick: move |_| props.on_close.call(()),
                          "✕"
                      }
                  }

                  div { class: "space-y-8",
                      div {
                          label { class: "block text-sm font-bold text-slate-500 uppercase tracking-widest mb-3", "Network Proxy" }
                          input {
                              class: "w-full bg-slate-950 border border-slate-800 rounded-2xl px-5 py-3 text-base focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all placeholder:text-slate-700",
                              r#type: "text",
                              placeholder: "e.g. http://127.0.0.1:7890",
                              value: "{temp_proxy}",
                              oninput: move |evt| temp_proxy.set(evt.value()),
                          }
                          p { class: "mt-3 text-sm text-slate-500 leading-relaxed",
                              "Supports HTTP, HTTPS, and SOCKS5. Leave empty for direct connection."
                          }
                      }

                      div { class: "pt-6 flex gap-4",
                          button {
                              class: "flex-1 bg-blue-600 hover:bg-blue-500 text-white font-bold py-3 rounded-2xl transition-all shadow-lg shadow-blue-900/20 active:scale-95",
                              onclick: move |_| {
                                  let val = temp_proxy.read().clone();
                                  if val.trim().is_empty() {
                                      proxy_url.set(None);
                                  } else {
                                      proxy_url.set(Some(val.trim().to_string()));
                                  }
                                  props.on_close.call(());
                              },
                              "Save Changes"
                          }
                          button {
                              class: "flex-1 bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold py-3 rounded-2xl transition-all active:scale-95",
                              onclick: move |_| props.on_close.call(()),
                              "Cancel"
                          }
                      }
                  }
              }
          }
      }
  }
}
