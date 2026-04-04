<script lang="ts">
  import { createEventDispatcher } from "svelte";
  export let searchQuery = "";
  export let loading = false;

  const dispatch = createEventDispatcher<{
    search: void;
  }>();
</script>

<header class="top-nav">
  <div class="search-bar">
    <input
      id="search-query"
      type="text"
      bind:value={searchQuery}
      placeholder="Search archives..."
      class="search-input"
    />
    <button on:click={() => dispatch("search")} disabled={loading} class="search-button">
      {loading ? "Searching..." : "Search"}
    </button>
  </div>
</header>
