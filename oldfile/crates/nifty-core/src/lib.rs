/// Nifty Reader Core Library
/// 
/// This crate contains all backend logic for Nifty Reader, including:
/// - Network operations (API calls, web scraping)
/// - Storage management (state persistence, history)
/// 
/// It serves as the "backend" layer, completely separated from the UI.

pub mod network;
pub mod storage;

// Re-export commonly used types for convenience
pub use network::api::{Story, StorySummary, HistoryItem, fetch_latest_stories, fetch_nifty_story};
pub use storage::state::{AppState, Settings};
pub use storage::{load_state, save_state};
