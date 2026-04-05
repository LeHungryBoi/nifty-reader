<script lang="ts">
  import { onMount } from "svelte";
  import "./App.css";
  import type { ArchiveItem } from "./services/nifty";
  import SearchPage from "./pages/SearchPage.svelte";
  import StoryPage from "./pages/StoryPage.svelte";
  import { hydrateLibrary } from "./stores/library";

  let selectedItem: ArchiveItem | null = null;

  onMount(() => {
    void hydrateLibrary();
  });
</script>

<div class="app">
  {#if !selectedItem}
    <SearchPage on:open={(event) => (selectedItem = event.detail)} />
  {:else}
    <StoryPage item={selectedItem} on:close={() => (selectedItem = null)} />
  {/if}
</div>
