<script lang="ts">
  import { createEventDispatcher, onDestroy } from "svelte";
  import { get } from "svelte/store";
  import StoryPageReader from "../components/StoryPageReader.svelte";
  import { fetchStoryDocument, type ArchiveItem, type StoryDocument } from "../services/nifty";
  import {
    chooseDownloadDirectory,
    getDownloadedStory,
    libraryState,
    recordStoryOpen,
    saveFavoriteDownload,
    setStoryFavorite,
    updateTheme
  } from "../stores/library";

  export let item: ArchiveItem;

  const dispatch = createEventDispatcher<{
    close: void;
  }>();

  let loading = false;
  let favoriteBusy = false;
  let storyDocument: StoryDocument | null = null;
  let loadingForId = "";
  let sourceLabel = "Online";
  let mounted = true;
  let library = get(libraryState);

  $: library = $libraryState;
  $: downloadRecord = library.downloads.find((entry) => entry.storyId === item.id) ?? null;
  $: isDownloaded = Boolean(downloadRecord);
  $: isFavorite = downloadRecord?.isFavorite ?? false;

  function close() {
    dispatch("close");
  }

  async function loadStory(target: ArchiveItem) {
    loadingForId = target.id;
    loading = true;
    storyDocument = null;
    sourceLabel = "Loading...";

    try {
      const downloadedDocument = await getDownloadedStory(target.id);
      if (loadingForId !== target.id || !mounted) {
        return;
      }

      if (downloadedDocument) {
        storyDocument = downloadedDocument;
        sourceLabel = "Downloaded Copy";
        return;
      }

      const document = await fetchStoryDocument(target);
      if (loadingForId === target.id && mounted) {
        storyDocument = document;
        sourceLabel = "Online";
      }
    } catch (error) {
      console.error("Failed to load story:", error);
      if (loadingForId === target.id && mounted) {
        storyDocument = {
          title: target.title,
          chapters: [
            {
              title: "Could not load story",
              url: target.url,
              html: `
                <div class="error">
                  <h2>Could not load story</h2>
                  <p>Visit the story directly at: <a href="${target.url}" target="_blank" rel="noreferrer">${target.url}</a></p>
                </div>
              `
            }
          ]
        };
        sourceLabel = "Unavailable";
      }
    } finally {
      if (loadingForId === target.id && mounted) {
        loading = false;
      }
    }
  }

  async function toggleFavorite() {
    if (!storyDocument || favoriteBusy) {
      return;
    }

    favoriteBusy = true;
    try {
      if (isFavorite) {
        await setStoryFavorite(item.id, false);
        return;
      }

      if (!get(libraryState).settings.downloadDirectory) {
        const selected = await chooseDownloadDirectory();
        if (!selected) {
          return;
        }
      }

      await saveFavoriteDownload(item, storyDocument);
      const downloadedDocument = await getDownloadedStory(item.id);
      if (downloadedDocument && mounted && loadingForId === item.id) {
        storyDocument = downloadedDocument;
        sourceLabel = "Downloaded Copy";
      }
    } catch (error) {
      console.error("Failed to update favorite/download:", error);
    } finally {
      favoriteBusy = false;
    }
  }

  async function configureDownloads() {
    try {
      await chooseDownloadDirectory();
    } catch (error) {
      console.error("Failed to choose download directory:", error);
    }
  }

  async function toggleTheme() {
    try {
      await updateTheme(library.settings.theme === "dark" ? "light" : "dark");
    } catch (error) {
      console.error("Failed to update theme:", error);
    }
  }

  function handleKeyDown(event: KeyboardEvent) {
    if (event.key === "Escape") {
      close();
    }
  }

  $: if (item?.id && item.id !== loadingForId) {
    void loadStory(item);
    void recordStoryOpen(item);
  }

  onDestroy(() => {
    mounted = false;
  });
</script>

<svelte:window on:keydown={handleKeyDown} />

{#key item.id}
  <StoryPageReader
    selectedItem={item}
    {loading}
    story={storyDocument}
    {sourceLabel}
    {isFavorite}
    {isDownloaded}
    currentTheme={library.settings.theme}
    downloadDirectory={library.settings.downloadDirectory}
    {favoriteBusy}
    on:close={close}
    on:toggleFavorite={toggleFavorite}
    on:toggleTheme={toggleTheme}
    on:configureDownloads={configureDownloads}
  />
{/key}
