<script lang="ts">
  import { createEventDispatcher } from "svelte";
  import { getCategoryBarStyle } from "../lib/niftyCategories";
  import type { ArchiveItem } from "../services/nifty";
  import { libraryState } from "../stores/library";

  export let results: ArchiveItem[] = [];
  export let loading = false;

  const dispatch = createEventDispatcher<{
    open: ArchiveItem;
  }>();

  function handleResultKeyDown(e: KeyboardEvent, item: ArchiveItem) {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      dispatch("open", item);
    }
  }
</script>

{#if results.length > 0}
  <h3>Found {results.length} results</h3>
{/if}

{#each results as item (item.id)}
  {@const primaryCategory = item.categories[0]}
  {@const downloadRecord = $libraryState.downloads.find((entry) => entry.storyId === item.id)}
  {@const historyRecord = $libraryState.history.find((entry) => entry.storyId === item.id)}
  <div
    class="result-block"
    on:click={() => dispatch("open", item)}
    on:keydown={(e) => handleResultKeyDown(e, item)}
    role="button"
    tabindex="0"
  >
    <div class="result-header" style={primaryCategory ? getCategoryBarStyle(primaryCategory) : ""}>
      <a class="result-title" href={item.url} target="_blank" rel="noreferrer" on:click|stopPropagation>
        {item.title}
      </a>
      {#if item.categories.length > 0}
        <span class="tag">{primaryCategory}</span>
      {/if}
    </div>

    <div class="result-meta">
      <span>Published: {item.date || "Unknown"}</span>
      <span>Author: {item.author || "Unknown"}</span>
      {#if downloadRecord}
        <span>{downloadRecord.isFavorite ? "Hearted" : "Downloaded"}</span>
      {/if}
      {#if historyRecord}
        <span>Opened {historyRecord.openCount} time{historyRecord.openCount === 1 ? "" : "s"}</span>
      {/if}
    </div>

    <div class="result-body">
      <div class="labels">
        {#if downloadRecord?.isFavorite}
          <span class="label status-label favorite">Hearted</span>
        {/if}
        {#if downloadRecord}
          <span class="label status-label downloaded">Downloaded</span>
        {/if}
        {#each item.subcategories as sub}
          <span class="label subcategory">{sub}</span>
        {/each}
      </div>
      <p>{item.description}</p>
    </div>
  </div>
{/each}

{#if results.length === 0 && !loading}
  <div class="empty-state">
    <h3>Welcome to Nifty Reader</h3>
    <p>Search for documents in the Nifty Archives database</p>
  </div>
{/if}
