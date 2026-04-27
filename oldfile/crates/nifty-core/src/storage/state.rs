use crate::network::api::HistoryItem;
use directories::ProjectDirs;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;

#[derive(Clone, Serialize, Deserialize, Debug)]
pub struct Settings {
  pub theme: String,
  pub font_size: f32,
  pub proxy_url: Option<String>,
}

impl Default for Settings {
  fn default() -> Self {
    Self {
      theme: "dark".to_string(),
      font_size: 1.0,
      proxy_url: None,
    }
  }
}

#[derive(Clone, Serialize, Deserialize, Debug, Default)]
pub struct AppState {
  pub settings: Settings,
  pub history: Vec<HistoryItem>,
}

fn get_storage_path() -> PathBuf {
  if let Some(proj_dirs) = ProjectDirs::from("com", "lehungryboi", "niftyreader") {
    let config_dir = proj_dirs.config_dir();
    if !config_dir.exists() {
      let _ = fs::create_dir_all(config_dir);
    }
    return config_dir.join("state.json");
  }
  PathBuf::from("state.json")
}

pub fn load_state() -> AppState {
  let path = get_storage_path();
  if let Ok(content) = fs::read_to_string(path) {
    if let Ok(state) = serde_json::from_str(&content) {
      return state;
    }
  }
  AppState::default()
}

pub fn save_state(state: &AppState) {
  let path = get_storage_path();
  if let Ok(content) = serde_json::to_string(state) {
    let _ = fs::write(path, content);
  }
}
