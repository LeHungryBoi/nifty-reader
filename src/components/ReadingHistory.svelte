<script lang="ts">
  import { createEventDispatcher } from "svelte";
  import type { ArchiveItem } from "../services/nifty";
  import type { HistoryRecord } from "../stores/library";

  export let entries: HistoryRecord[] = [];

  const dispatch = createEventDispatcher<{
    open: ArchiveItem;
  }>();

  const formatOpenedAt = (value: string) => {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return "Recently";
    }

    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short"
    }).format(date);
  };

  const toArchiveItem = (entry: HistoryRecord): ArchiveItem => ({
    id: entry.storyId,
    title: entry.title,
    author: entry.author,
    date: "",
    description: "Open from reading history.",
    url: entry.storyUrl,
    categories: [],
    subcategories: []
  });
</script>

{#if entries.length > 0}
  <section class="history-panel" aria-label="Reading history">
    <div class="history-panel-header">
      <h3>Reading History</h3>
      <span>{entries.length} recent stories</span>
    </div>

    <div class="history-list">
      {#each entries as entry (entry.storyId)}
        <button class="history-card" on:click={() => dispatch("open", toArchiveItem(entry))}>
          <span class="history-title">{entry.title}</span>
          <span class="history-meta">{entry.author || "Unknown author"}</span>
          <span class="history-meta">Opened {entry.openCount} time{entry.openCount === 1 ? "" : "s"}</span>
          <span class="history-meta">{formatOpenedAt(entry.openedAt)}</span>
        </button>
      {/each}
    </div>
  </section>
{/if}
