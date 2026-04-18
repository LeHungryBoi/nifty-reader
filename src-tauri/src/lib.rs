use chrono::Utc;
use rfd::FileDialog;
use rusqlite::{params, Connection, OptionalExtension};
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::{Path, PathBuf};
use tauri::Manager;

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
struct ArchiveItemPayload {
    id: String,
    title: String,
    author: String,
    date: String,
    description: String,
    url: String,
    categories: Vec<String>,
    subcategories: Vec<String>,
    parts: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
struct StoryChapterPayload {
    title: String,
    url: String,
    html: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
struct StoryDocumentPayload {
    title: String,
    chapters: Vec<StoryChapterPayload>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
struct DownloadRecord {
    story_id: String,
    title: String,
    local_path: String,
    is_favorite: bool,
    downloaded_at: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
struct HistoryRecord {
    story_id: String,
    title: String,
    author: String,
    story_url: String,
    opened_at: String,
    open_count: i64,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
struct AppSettings {
    theme: String,
    download_directory: Option<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
struct LibrarySnapshot {
    settings: AppSettings,
    downloads: Vec<DownloadRecord>,
    history: Vec<HistoryRecord>,
}

fn app_data_root<R: tauri::Runtime>(app: &tauri::AppHandle<R>) -> Result<PathBuf, String> {
    let dir = app
        .path()
        .app_data_dir()
        .map_err(|error| format!("Unable to resolve app data directory: {error}"))?;
    fs::create_dir_all(&dir)
        .map_err(|error| format!("Unable to create app data directory: {error}"))?;
    Ok(dir)
}

fn database_path<R: tauri::Runtime>(app: &tauri::AppHandle<R>) -> Result<PathBuf, String> {
    Ok(app_data_root(app)?.join("library.sqlite3"))
}

fn open_database<R: tauri::Runtime>(app: &tauri::AppHandle<R>) -> Result<Connection, String> {
    let path = database_path(app)?;
    let connection =
        Connection::open(path).map_err(|error| format!("Unable to open database: {error}"))?;
    initialize_database(&connection)?;
    Ok(connection)
}

fn initialize_database(connection: &Connection) -> Result<(), String> {
    connection
        .execute_batch(
            "
            CREATE TABLE IF NOT EXISTS settings (
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS downloads (
              story_id TEXT PRIMARY KEY,
              title TEXT NOT NULL,
              local_path TEXT NOT NULL,
              is_favorite INTEGER NOT NULL DEFAULT 0,
              downloaded_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS history (
              story_id TEXT PRIMARY KEY,
              title TEXT NOT NULL,
              author TEXT NOT NULL,
              story_url TEXT NOT NULL,
              opened_at TEXT NOT NULL,
              open_count INTEGER NOT NULL DEFAULT 1
            );
            ",
        )
        .map_err(|error| format!("Unable to initialize database: {error}"))?;

    connection
        .execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES ('theme', 'dark')",
            [],
        )
        .map_err(|error| format!("Unable to seed settings: {error}"))?;

    Ok(())
}

fn get_setting(connection: &Connection, key: &str) -> Result<Option<String>, String> {
    connection
        .query_row("SELECT value FROM settings WHERE key = ?1", [key], |row| {
            row.get(0)
        })
        .optional()
        .map_err(|error| format!("Unable to read setting {key}: {error}"))
}

fn set_setting(connection: &Connection, key: &str, value: Option<&str>) -> Result<(), String> {
    match value {
        Some(inner) => connection
            .execute(
                "INSERT INTO settings (key, value) VALUES (?1, ?2)
                 ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                params![key, inner],
            )
            .map(|_| ())
            .map_err(|error| format!("Unable to save setting {key}: {error}")),
        None => connection
            .execute("DELETE FROM settings WHERE key = ?1", [key])
            .map(|_| ())
            .map_err(|error| format!("Unable to clear setting {key}: {error}")),
    }
}

fn normalize_filename(value: &str) -> String {
    let mut sanitized = value
        .chars()
        .map(|character| match character {
            'a'..='z' | 'A'..='Z' | '0'..='9' => character,
            _ => '-',
        })
        .collect::<String>()
        .split('-')
        .filter(|part| !part.is_empty())
        .collect::<Vec<_>>()
        .join("-");

    if sanitized.is_empty() {
        sanitized = "story".to_string();
    }

    sanitized
}

fn ensure_parent_directory(path: &Path) -> Result<(), String> {
    let Some(parent) = path.parent() else {
        return Err("Download path is missing a parent directory".to_string());
    };

    fs::create_dir_all(parent)
        .map_err(|error| format!("Unable to create download directory: {error}"))
}

fn snapshot_from_connection(connection: &Connection) -> Result<LibrarySnapshot, String> {
    let theme = get_setting(connection, "theme")?.unwrap_or_else(|| "dark".to_string());
    let download_directory = get_setting(connection, "download_directory")?;

    let mut downloads_statement = connection
        .prepare(
            "
            SELECT story_id, title, local_path, is_favorite, downloaded_at
            FROM downloads
            ORDER BY downloaded_at DESC
            ",
        )
        .map_err(|error| format!("Unable to prepare downloads query: {error}"))?;

    let downloads = downloads_statement
        .query_map([], |row| {
            Ok(DownloadRecord {
                story_id: row.get(0)?,
                title: row.get(1)?,
                local_path: row.get(2)?,
                is_favorite: row.get::<_, i64>(3)? != 0,
                downloaded_at: row.get(4)?,
            })
        })
        .map_err(|error| format!("Unable to query downloads: {error}"))?
        .collect::<Result<Vec<_>, _>>()
        .map_err(|error| format!("Unable to read downloads: {error}"))?;

    let mut history_statement = connection
        .prepare(
            "
            SELECT story_id, title, author, story_url, opened_at, open_count
            FROM history
            ORDER BY opened_at DESC
            LIMIT 25
            ",
        )
        .map_err(|error| format!("Unable to prepare history query: {error}"))?;

    let history = history_statement
        .query_map([], |row| {
            Ok(HistoryRecord {
                story_id: row.get(0)?,
                title: row.get(1)?,
                author: row.get(2)?,
                story_url: row.get(3)?,
                opened_at: row.get(4)?,
                open_count: row.get(5)?,
            })
        })
        .map_err(|error| format!("Unable to query history: {error}"))?
        .collect::<Result<Vec<_>, _>>()
        .map_err(|error| format!("Unable to read history: {error}"))?;

    Ok(LibrarySnapshot {
        settings: AppSettings {
            theme,
            download_directory,
        },
        downloads,
        history,
    })
}

#[tauri::command]
fn load_library_snapshot(app: tauri::AppHandle) -> Result<LibrarySnapshot, String> {
    let connection = open_database(&app)?;
    snapshot_from_connection(&connection)
}

#[tauri::command]
fn pick_download_directory() -> Option<String> {
    FileDialog::new()
        .pick_folder()
        .map(|path| path.display().to_string())
}

#[tauri::command]
fn set_download_directory(
    app: tauri::AppHandle,
    path: Option<String>,
) -> Result<AppSettings, String> {
    let connection = open_database(&app)?;
    set_setting(&connection, "download_directory", path.as_deref())?;

    Ok(AppSettings {
        theme: get_setting(&connection, "theme")?.unwrap_or_else(|| "dark".to_string()),
        download_directory: get_setting(&connection, "download_directory")?,
    })
}

#[tauri::command]
fn set_theme(app: tauri::AppHandle, theme: String) -> Result<AppSettings, String> {
    let normalized = if theme == "light" { "light" } else { "dark" };
    let connection = open_database(&app)?;
    set_setting(&connection, "theme", Some(normalized))?;

    Ok(AppSettings {
        theme: normalized.to_string(),
        download_directory: get_setting(&connection, "download_directory")?,
    })
}

#[tauri::command]
fn record_history(
    app: tauri::AppHandle,
    item: ArchiveItemPayload,
) -> Result<Vec<HistoryRecord>, String> {
    let connection = open_database(&app)?;
    let now = Utc::now().to_rfc3339();

    connection
        .execute(
            "
            INSERT INTO history (story_id, title, author, story_url, opened_at, open_count)
            VALUES (?1, ?2, ?3, ?4, ?5, 1)
            ON CONFLICT(story_id) DO UPDATE SET
              title = excluded.title,
              author = excluded.author,
              story_url = excluded.story_url,
              opened_at = excluded.opened_at,
              open_count = history.open_count + 1
            ",
            params![item.id, item.title, item.author, item.url, now],
        )
        .map_err(|error| format!("Unable to record history: {error}"))?;

    Ok(snapshot_from_connection(&connection)?.history)
}

#[tauri::command]
fn save_story_download(
    app: tauri::AppHandle,
    item: ArchiveItemPayload,
    document: StoryDocumentPayload,
) -> Result<DownloadRecord, String> {
    let connection = open_database(&app)?;
    let download_directory = get_setting(&connection, "download_directory")?
        .ok_or_else(|| "Download directory is not configured".to_string())?;

    let filename = format!(
        "{}-{}.json",
        normalize_filename(&item.title),
        normalize_filename(&item.id)
    );
    let target_path = PathBuf::from(download_directory).join(filename);
    ensure_parent_directory(&target_path)?;

    let serialized = serde_json::to_string_pretty(&document)
        .map_err(|error| format!("Unable to serialize downloaded story: {error}"))?;
    fs::write(&target_path, serialized)
        .map_err(|error| format!("Unable to write downloaded story: {error}"))?;

    let downloaded_at = Utc::now().to_rfc3339();
    connection
        .execute(
            "
            INSERT INTO downloads (story_id, title, local_path, is_favorite, downloaded_at)
            VALUES (?1, ?2, ?3, 1, ?4)
            ON CONFLICT(story_id) DO UPDATE SET
              title = excluded.title,
              local_path = excluded.local_path,
              is_favorite = 1,
              downloaded_at = excluded.downloaded_at
            ",
            params![
                item.id,
                item.title,
                target_path.display().to_string(),
                downloaded_at
            ],
        )
        .map_err(|error| format!("Unable to save download record: {error}"))?;

    Ok(DownloadRecord {
        story_id: item.id,
        title: item.title,
        local_path: target_path.display().to_string(),
        is_favorite: true,
        downloaded_at,
    })
}

#[tauri::command]
fn set_story_favorite(
    app: tauri::AppHandle,
    story_id: String,
    favorite: bool,
) -> Result<Option<DownloadRecord>, String> {
    let connection = open_database(&app)?;

    let updated = if favorite {
        connection
            .query_row(
                "
                UPDATE downloads
                SET is_favorite = 1
                WHERE story_id = ?1
                RETURNING story_id, title, local_path, is_favorite, downloaded_at
                ",
                [story_id.clone()],
                |row| {
                    Ok(DownloadRecord {
                        story_id: row.get(0)?,
                        title: row.get(1)?,
                        local_path: row.get(2)?,
                        is_favorite: row.get::<_, i64>(3)? != 0,
                        downloaded_at: row.get(4)?,
                    })
                },
            )
            .optional()
            .map_err(|error| format!("Unable to update favorite: {error}"))?
    } else {
        connection
            .execute(
                "UPDATE downloads SET is_favorite = 0 WHERE story_id = ?1",
                [story_id.clone()],
            )
            .map_err(|error| format!("Unable to clear favorite: {error}"))?;

        connection
            .query_row(
                "
                SELECT story_id, title, local_path, is_favorite, downloaded_at
                FROM downloads
                WHERE story_id = ?1
                ",
                [story_id],
                |row| {
                    Ok(DownloadRecord {
                        story_id: row.get(0)?,
                        title: row.get(1)?,
                        local_path: row.get(2)?,
                        is_favorite: row.get::<_, i64>(3)? != 0,
                        downloaded_at: row.get(4)?,
                    })
                },
            )
            .optional()
            .map_err(|error| format!("Unable to read favorite: {error}"))?
    };

    Ok(updated)
}

#[tauri::command]
fn load_downloaded_story(
    app: tauri::AppHandle,
    story_id: String,
) -> Result<Option<StoryDocumentPayload>, String> {
    let connection = open_database(&app)?;
    let local_path: Option<String> = connection
        .query_row(
            "SELECT local_path FROM downloads WHERE story_id = ?1",
            [story_id],
            |row| row.get(0),
        )
        .optional()
        .map_err(|error| format!("Unable to look up downloaded story: {error}"))?;

    let Some(path) = local_path else {
        return Ok(None);
    };

    let content = match fs::read_to_string(&path) {
        Ok(content) => content,
        Err(_) => return Ok(None),
    };

    let document = serde_json::from_str::<StoryDocumentPayload>(&content)
        .map_err(|error| format!("Unable to parse downloaded story: {error}"))?;
    Ok(Some(document))
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_http::init())
        .invoke_handler(tauri::generate_handler![
            load_library_snapshot,
            pick_download_directory,
            set_download_directory,
            set_theme,
            record_history,
            save_story_download,
            set_story_favorite,
            load_downloaded_story
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
