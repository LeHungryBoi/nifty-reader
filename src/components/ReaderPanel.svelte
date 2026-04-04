<script lang="ts">
  import { createEventDispatcher } from "svelte";
  import type { ArchiveItem, StoryDocument } from "../services/nifty";

  export let selectedItem: ArchiveItem;
  export let loading = false;
  export let story: StoryDocument | null = null;

  let activeChapterIndex = 0;
  let activeChapter: StoryDocument["chapters"][number] | null = null;

  $: if (story) {
    activeChapterIndex = 0;
  }

  $: activeChapter = story?.chapters[activeChapterIndex] ?? null;

  const dispatch = createEventDispatcher<{
    close: void;
  }>();
</script>

<div class="reader">
  <div class="reader-header">
    <button on:click={() => dispatch("close")} class="back-button">Back</button>
    <h2>{selectedItem.title}</h2>
  </div>

  {#if loading}
    <div class="loading">Loading document...</div>
  {:else}
    {#if story && story.chapters.length > 1}
      <div class="chapter-nav" role="tablist" aria-label="Story chapters">
        {#each story.chapters as chapter, index}
          <button
            class:active={index === activeChapterIndex}
            class="chapter-button"
            role="tab"
            aria-selected={index === activeChapterIndex}
            on:click={() => (activeChapterIndex = index)}
          >
            {chapter.title}
          </button>
        {/each}
      </div>
    {/if}

    <div class="reader-content">
      {#if activeChapter}
        <div class="chapter-heading">
          <h3>{activeChapter.title}</h3>
        </div>
        {@html activeChapter.html}
      {/if}
    </div>
  {/if}
</div>
