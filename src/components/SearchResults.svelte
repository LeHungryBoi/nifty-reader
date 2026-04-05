<script lang="ts">
  import { createEventDispatcher } from "svelte";
  import type { ArchiveItem } from "../services/nifty";
  import StoryResultList from "./StoryResultList.svelte";

  export let results: ArchiveItem[] = [];
  export let loading = false;
  export let currentPage = 1;
  export let totalPages = 1;
  export let pageNumbers: number[] = [];
  export let totalResults = 0;
  export let resultStart = 0;
  export let resultEnd = 0;

  const dispatch = createEventDispatcher<{
    open: ArchiveItem;
    page: number;
  }>();
</script>

<main class="results">
  <div class="results-list">
    <StoryResultList {results} {loading} on:open={(event) => dispatch("open", event.detail)} />
  </div>

  {#if results.length > 0}
    <div class="results-footer" aria-label="Search results pages">
      <span class="results-footer-meta">Results {resultStart} - {resultEnd} of {totalResults}</span>

      <div class="pagination-bar">
        <button
          class="pagination-button"
          on:click={() => dispatch("page", Math.max(1, currentPage - 1))}
          disabled={loading || currentPage <= 1}
        >
          &laquo;
        </button>

        {#each pageNumbers as page}
          <button
            class:active={page === currentPage}
            class="pagination-button"
            on:click={() => dispatch("page", page)}
            disabled={loading}
          >
            {page}
          </button>
        {/each}

        {#if totalPages > 1 && (!pageNumbers.includes(totalPages) || totalPages > (pageNumbers[pageNumbers.length - 1] ?? 0))}
          <button
            class="pagination-button"
            on:click={() => dispatch("page", totalPages)}
            disabled={loading || currentPage >= totalPages}
          >
            Last
          </button>
        {/if}

        <button
          class="pagination-button"
          on:click={() => dispatch("page", Math.min(totalPages, currentPage + 1))}
          disabled={loading || currentPage >= totalPages}
        >
          &raquo;
        </button>
      </div>

      <span class="results-footer-page">Page {currentPage} of {totalPages}</span>
    </div>
  {/if}
</main>
