<script lang="ts">
  import { createEventDispatcher } from "svelte";
  import "../styles/search-form.css";
  import "../styles/shared-controls.css";
  export let searchQuery = "";
  export let loading = false;

  const dispatch = createEventDispatcher<{ search: void }>();
</script>

<form
  class="top-nav w-full max-w-5xl mx-auto"
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
</form>
