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
    div { class: "fixed inset-0 z-50 flex items-center justify-center p-4 bg-base-300/80 backdrop-blur-sm",
      div { class: "modal modal-open",
        div { class: "modal-box w-full max-w-md bg-base-100",
          div { class: "flex justify-between items-center mb-6",
            h3 { class: "font-bold text-lg", "Settings" }
            button {
              class: "btn btn-sm btn-circle btn-ghost",
              onclick: move |_| props.on_close.call(()),
              "✕"
            }
          }

          div { class: "space-y-6",
            div {
              label { class: "label",
                span { class: "label-text font-bold uppercase tracking-wider", "Network Proxy" }
              }
              input {
                class: "input input-bordered w-full",
                r#type: "text",
                placeholder: "e.g. http://127.0.0.1:7890",
                value: "{temp_proxy}",
                oninput: move |evt| temp_proxy.set(evt.value()),
              }
              p { class: "mt-2 text-sm text-base-content/60",
                "Supports HTTP, HTTPS, and SOCKS5. Leave empty for direct connection."
              }
            }

            div { class: "modal-action",
              button {
                class: "btn btn-primary flex-1",
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
                class: "btn btn-ghost flex-1",
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
