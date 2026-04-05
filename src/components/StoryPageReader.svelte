<script lang="ts">
  import { createEventDispatcher, onDestroy } from "svelte";
  import type { ArchiveItem, StoryDocument } from "../services/nifty";
  import {
    createStoryPageTtsController,
    type StoryPageTtsState
  } from "../pages/StoryPageTts";

  export let selectedItem: ArchiveItem;
  export let loading = false;
  export let story: StoryDocument | null = null;
  export let sourceLabel = "Online";
  export let isFavorite = false;
  export let isDownloaded = false;
  export let currentTheme: "dark" | "light" = "dark";
  export let downloadDirectory: string | null = null;
  export let favoriteBusy = false;

  let activeChapterIndex = 0;
  let activeChapter: StoryDocument["chapters"][number] | null = null;
  let chapterNavExpanded = false;
  let readerContentElement: HTMLDivElement | null = null;
  let renderedChapterHtml = "";
  let cleanupReaderEvents: (() => void) | null = null;
  let ttsState: StoryPageTtsState = {
    activeSentenceIndex: -1,
    sentenceCount: 0,
    status: "idle",
    isSupported: false
  };

  const ttsController = createStoryPageTtsController((nextState) => {
    ttsState = nextState;
  });

  const dispatch = createEventDispatcher<{
    close: void;
    toggleFavorite: void;
    toggleTheme: void;
    configureDownloads: void;
  }>();

  $: activeChapter = story?.chapters[activeChapterIndex] ?? null;
  $: if (story && activeChapterIndex >= story.chapters.length) {
    activeChapterIndex = 0;
  }

  $: if (activeChapter) {
    renderedChapterHtml = ttsController.prepareChapter(activeChapter.html).html;
  } else {
    renderedChapterHtml = "";
    ttsController.stop();
  }

  $: ttsController.bindReader(readerContentElement);
  $: ttsController.syncHighlight();
  $: {
    cleanupReaderEvents?.();
    cleanupReaderEvents = null;

    if (readerContentElement) {
      const element = readerContentElement;
      const clickHandler = (event: MouseEvent) => handleSentenceClick(event);
      const keyDownHandler = (event: KeyboardEvent) => handleSentenceKeyDown(event);

      element.addEventListener("click", clickHandler);
      element.addEventListener("keydown", keyDownHandler);

      cleanupReaderEvents = () => {
        element.removeEventListener("click", clickHandler);
        element.removeEventListener("keydown", keyDownHandler);
      };
    }
  }

  function handleSentenceClick(event: MouseEvent) {
    ttsController.activateFromTarget(event.target);
  }

  function handleSentenceKeyDown(event: KeyboardEvent) {
    if (event.key !== "Enter" && event.key !== " ") {
      return;
    }

    ttsController.activateFromTarget(event.target);
    event.preventDefault();
  }

  onDestroy(() => {
    cleanupReaderEvents?.();
    ttsController.destroy();
  });
</script>

<div class="reader">
  <div class="reader-header">
    <button on:click={() => dispatch("close")} class="back-button">Back</button>

    <div class="reader-header-copy">
      <h2>{selectedItem.title}</h2>
      <div class="reader-status-row">
        <span class="status-pill">{sourceLabel}</span>
        {#if isDownloaded}
          <span class="status-pill is-downloaded">Downloaded</span>
        {/if}
        {#if isFavorite}
          <span class="status-pill is-favorite">Hearted</span>
        {/if}
      </div>
    </div>

    <div class="reader-actions">
      <button
        class:is-active={isFavorite}
        class="pagination-button icon-button"
        on:click={() => dispatch("toggleFavorite")}
        disabled={loading || favoriteBusy || !story}
        aria-pressed={isFavorite}
      >
        {favoriteBusy ? "Saving..." : isFavorite ? "Unheart" : "Heart & Download"}
      </button>
      <button class="pagination-button" on:click={() => dispatch("configureDownloads")}>
        {downloadDirectory ? "Download Folder" : "Set Download Folder"}
      </button>
      <button class="pagination-button" on:click={() => dispatch("toggleTheme")}>
        {currentTheme === "dark" ? "Light Theme" : "Dark Theme"}
      </button>
    </div>

    <div class="tts-controls">
      <button
        class="pagination-button"
        on:click={() => ttsController.play()}
        disabled={!ttsState.isSupported || !ttsState.sentenceCount}
      >
        {ttsState.status === "paused" ? "Resume" : "Read Aloud"}
      </button>
      <button
        class="pagination-button"
        on:click={() => ttsController.pause()}
        disabled={ttsState.status !== "playing"}
      >
        Pause
      </button>
      <button
        class="pagination-button"
        on:click={() => ttsController.stop()}
        disabled={ttsState.status === "idle"}
      >
        Stop
      </button>
    </div>
  </div>

  {#if loading}
    <div class="loading">Loading document...</div>
  {:else}
    {#if story && story.chapters.length > 1}
      <div class="chapter-panel">
        <button
          class="chapter-toggle"
          on:click={() => (chapterNavExpanded = !chapterNavExpanded)}
          aria-expanded={chapterNavExpanded}
          aria-controls="chapter-nav"
        >
          Chapters ({story.chapters.length}) {chapterNavExpanded ? "Hide" : "Show"}
        </button>

        {#if chapterNavExpanded}
          <div id="chapter-nav" class="chapter-nav" role="tablist" aria-label="Story chapters">
            {#each story.chapters as chapter, index}
              <button
                class:active={index === activeChapterIndex}
                class="chapter-button"
                role="tab"
                aria-selected={index === activeChapterIndex}
                on:click={() => {
                  activeChapterIndex = index;
                  chapterNavExpanded = false;
                }}
              >
                {chapter.title}
              </button>
            {/each}
          </div>
        {/if}
      </div>
    {/if}

    <div
      class="reader-content"
      bind:this={readerContentElement}
      role="region"
      aria-label="Story content"
    >
      {#if activeChapter}
        <div class="chapter-heading">
          <h3>{activeChapter.title}</h3>
        </div>
        {@html renderedChapterHtml}
      {/if}
    </div>
  {/if}
</div>
