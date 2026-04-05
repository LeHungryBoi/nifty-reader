import { invoke } from "@tauri-apps/api/core";
import { get, writable } from "svelte/store";
import type { ArchiveItem, StoryDocument } from "../services/nifty";

export type AppTheme = "dark" | "light";

export interface AppSettings {
  theme: AppTheme;
  downloadDirectory: string | null;
}

export interface DownloadRecord {
  storyId: string;
  title: string;
  localPath: string;
  isFavorite: boolean;
  downloadedAt: string;
}

export interface HistoryRecord {
  storyId: string;
  title: string;
  author: string;
  storyUrl: string;
  openedAt: string;
  openCount: number;
}

export interface LibrarySnapshot {
  settings: AppSettings;
  downloads: DownloadRecord[];
  history: HistoryRecord[];
}

export interface LibraryState extends LibrarySnapshot {
  loaded: boolean;
  loading: boolean;
}

const FALLBACK_SNAPSHOT_KEY = "nifty_library_snapshot";
const FALLBACK_DOCUMENTS_KEY = "nifty_library_documents";

const defaultSnapshot: LibrarySnapshot = {
  settings: {
    theme: "dark",
    downloadDirectory: null
  },
  downloads: [],
  history: []
};

const defaultState: LibraryState = {
  ...defaultSnapshot,
  loaded: false,
  loading: false
};

const isTauriRuntime = () => typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;

const normalizeItemPayload = (item: ArchiveItem) => ({
  ...item,
  parts: item.parts ?? []
});

const parseFallbackSnapshot = (): LibrarySnapshot => {
  if (typeof localStorage === "undefined") {
    return defaultSnapshot;
  }

  const raw = localStorage.getItem(FALLBACK_SNAPSHOT_KEY);
  if (!raw) {
    return defaultSnapshot;
  }

  try {
    const parsed = JSON.parse(raw) as LibrarySnapshot;
    return {
      settings: {
        theme: parsed.settings?.theme === "light" ? "light" : "dark",
        downloadDirectory: parsed.settings?.downloadDirectory ?? null
      },
      downloads: parsed.downloads ?? [],
      history: parsed.history ?? []
    };
  } catch {
    return defaultSnapshot;
  }
};

const saveFallbackSnapshot = (snapshot: LibrarySnapshot) => {
  if (typeof localStorage === "undefined") {
    return;
  }

  localStorage.setItem(FALLBACK_SNAPSHOT_KEY, JSON.stringify(snapshot));
};

const readFallbackDocuments = (): Record<string, StoryDocument> => {
  if (typeof localStorage === "undefined") {
    return {};
  }

  const raw = localStorage.getItem(FALLBACK_DOCUMENTS_KEY);
  if (!raw) {
    return {};
  }

  try {
    return JSON.parse(raw) as Record<string, StoryDocument>;
  } catch {
    return {};
  }
};

const saveFallbackDocuments = (documents: Record<string, StoryDocument>) => {
  if (typeof localStorage === "undefined") {
    return;
  }

  localStorage.setItem(FALLBACK_DOCUMENTS_KEY, JSON.stringify(documents));
};

const applyThemeToDocument = (theme: AppTheme) => {
  if (typeof document === "undefined") {
    return;
  }

  document.body.dataset.theme = theme;
  document.documentElement.dataset.theme = theme;
};

const normalizeSnapshot = (snapshot: LibrarySnapshot): LibrarySnapshot => ({
  settings: {
    theme: snapshot.settings.theme === "light" ? "light" : "dark",
    downloadDirectory: snapshot.settings.downloadDirectory ?? null
  },
  downloads: snapshot.downloads ?? [],
  history: snapshot.history ?? []
});

export const libraryState = writable<LibraryState>(defaultState);

function mergeSnapshot(snapshot: LibrarySnapshot) {
  const normalized = normalizeSnapshot(snapshot);
  applyThemeToDocument(normalized.settings.theme);
  libraryState.update((state) => ({
    ...state,
    ...normalized,
    loaded: true,
    loading: false
  }));
  if (!isTauriRuntime()) {
    saveFallbackSnapshot(normalized);
  }
}

export async function hydrateLibrary() {
  libraryState.update((state) => ({ ...state, loading: true }));

  if (!isTauriRuntime()) {
    mergeSnapshot(parseFallbackSnapshot());
    return;
  }

  try {
    const snapshot = await invoke<LibrarySnapshot>("load_library_snapshot");
    mergeSnapshot(snapshot);
  } catch (error) {
    console.error("Failed to load library snapshot:", error);
    mergeSnapshot(parseFallbackSnapshot());
  }
}

export async function chooseDownloadDirectory() {
  if (!isTauriRuntime()) {
    return get(libraryState).settings.downloadDirectory;
  }

  const selected = await invoke<string | null>("pick_download_directory");
  if (!selected) {
    return null;
  }

  return setDownloadDirectory(selected);
}

export async function setDownloadDirectory(path: string | null) {
  if (!isTauriRuntime()) {
    const snapshot = normalizeSnapshot({
      ...get(libraryState),
      settings: {
        ...get(libraryState).settings,
        downloadDirectory: path
      }
    });
    mergeSnapshot(snapshot);
    return path;
  }

  const settings = await invoke<AppSettings>("set_download_directory", { path });
  mergeSnapshot({
    ...get(libraryState),
    settings
  });
  return settings.downloadDirectory;
}

export async function updateTheme(theme: AppTheme) {
  if (!isTauriRuntime()) {
    const snapshot = normalizeSnapshot({
      ...get(libraryState),
      settings: {
        ...get(libraryState).settings,
        theme
      }
    });
    mergeSnapshot(snapshot);
    return;
  }

  const settings = await invoke<AppSettings>("set_theme", { theme });
  mergeSnapshot({
    ...get(libraryState),
    settings
  });
}

export async function recordStoryOpen(item: ArchiveItem) {
  if (!isTauriRuntime()) {
    const state = get(libraryState);
    const now = new Date().toISOString();
    const existing = state.history.find((entry) => entry.storyId === item.id);
    const nextHistory = [
      {
        storyId: item.id,
        title: item.title,
        author: item.author,
        storyUrl: item.url,
        openedAt: now,
        openCount: existing ? existing.openCount + 1 : 1
      },
      ...state.history.filter((entry) => entry.storyId !== item.id)
    ].slice(0, 25);

    mergeSnapshot({
      ...state,
      history: nextHistory
    });
    return;
  }

  const history = await invoke<HistoryRecord[]>("record_history", {
    item: normalizeItemPayload(item)
  });

  mergeSnapshot({
    ...get(libraryState),
    history
  });
}

export async function saveFavoriteDownload(item: ArchiveItem, document: StoryDocument) {
  if (!isTauriRuntime()) {
    const documents = readFallbackDocuments();
    documents[item.id] = document;
    saveFallbackDocuments(documents);

    const now = new Date().toISOString();
    const state = get(libraryState);
    const nextDownloads = [
      {
        storyId: item.id,
        title: item.title,
        localPath: `local-storage:${item.id}`,
        isFavorite: true,
        downloadedAt: now
      },
      ...state.downloads.filter((entry) => entry.storyId !== item.id)
    ];

    mergeSnapshot({
      ...state,
      downloads: nextDownloads
    });
    return nextDownloads[0];
  }

  const record = await invoke<DownloadRecord>("save_story_download", {
    item: normalizeItemPayload(item),
    document
  });

  const state = get(libraryState);
  mergeSnapshot({
    ...state,
    downloads: [record, ...state.downloads.filter((entry) => entry.storyId !== record.storyId)]
  });
  return record;
}

export async function setStoryFavorite(storyId: string, favorite: boolean) {
  if (!isTauriRuntime()) {
    const state = get(libraryState);
    const nextDownloads = state.downloads.map((entry) =>
      entry.storyId === storyId ? { ...entry, isFavorite: favorite } : entry
    );

    mergeSnapshot({
      ...state,
      downloads: nextDownloads
    });
    return;
  }

  const record = await invoke<DownloadRecord | null>("set_story_favorite", { storyId, favorite });
  const state = get(libraryState);
  mergeSnapshot({
    ...state,
    downloads: state.downloads.map((entry) => (entry.storyId === storyId ? record ?? entry : entry))
  });
}

export async function getDownloadedStory(storyId: string) {
  if (!isTauriRuntime()) {
    return readFallbackDocuments()[storyId] ?? null;
  }

  return invoke<StoryDocument | null>("load_downloaded_story", { storyId });
}
