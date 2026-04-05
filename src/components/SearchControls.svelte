<script lang="ts">
  import { createEventDispatcher } from "svelte";
  export let searchQuery = "";
  export let loading = false;
  export let theme: "dark" | "light" = "dark";
  export let downloadDirectory: string | null = null;

  const dispatch = createEventDispatcher<{
    search: void;
    toggleTheme: void;
    configureDownloads: void;
  }>();
</script>

<form
  class="top-nav"
  on:submit|preventDefault={() => dispatch("search")}
>
  <div class="search-bar">
    <input
      id="search-query"
      type="text"
      bind:value={searchQuery}
      placeholder="Search archives..."
      class="search-input"
    />
    <button type="submit" disabled={loading} class="search-button">
      {loading ? "Searching..." : "Search"}
    </button>
  </div>

  <div class="search-toolbar">
    <button type="button" class="pagination-button" on:click={() => dispatch("toggleTheme")}>
      {theme === "dark" ? "Light Theme" : "Dark Theme"}
    </button>
    <button type="button" class="pagination-button" on:click={() => dispatch("configureDownloads")}>
      {downloadDirectory ? "Download Folder" : "Set Download Folder"}
    </button>
    <span class="settings-hint">
      {downloadDirectory ? `Downloads: ${downloadDirectory}` : "Choose where hearted stories are saved."}
    </span>
  </div>
</form>
