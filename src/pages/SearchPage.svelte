<script lang="ts">
  import { createEventDispatcher, onMount } from "svelte";
  import { get } from "svelte/store";
  import "./SearchPage.css";
  import ReadingHistory from "../components/ReadingHistory.svelte";
  import SearchControls from "../components/SearchControls.svelte";
  import FilterPanel from "../components/FilterPanel.svelte";
  import SearchResults from "../components/SearchResults.svelte";
  import { fetchSearchResults, type ArchiveItem } from "../services/nifty";
  import { chooseDownloadDirectory, libraryState, updateTheme } from "../stores/library";
  import {
    cloneSearchPageState,
    createDefaultSearchPageState,
    searchPageState,
    type SearchPageState
  } from "../stores/searchPage";

  const dispatch = createEventDispatcher<{
    open: ArchiveItem;
  }>();

  const fallbackResult: ArchiveItem = {
    id: "1",
    title: "Demo Story (Search failed, see console)",
    author: "Self",
    date: "2025-01-15",
    description: "Search likely failed due to CORS.",
    url: "https://www.nifty.org/nifty/lesbian/hookers/linda-becomes-a-prostitute",
    categories: [],
    subcategories: []
  };

  type TopTabKey = "search" | "history" | "downloads" | "theme";
  const topTabs: { key: TopTabKey; icon: string; label: string }[] = [
    { key: "search", icon: "🔍", label: "Search" },
    { key: "history", icon: "🕘", label: "History" },
    { key: "downloads", icon: "📁", label: "Downloads" },
    { key: "theme", icon: "🌤️", label: "Theme" }
  ];
  let activeTab: TopTabKey = "search";

  function handleTabClick(key: TopTabKey) {
    activeTab = key;
  }

  let state: SearchPageState = cloneSearchPageState(get(searchPageState));

  $: searchPageState.set(cloneSearchPageState(state));

  async function searchArchives(page = 1) {
    state = {
      ...state,
      loading: true,
      pagination: {
        ...state.pagination,
        currentPage: page
      }
    };

    try {
      const response = await fetchSearchResults(state.query, {
        category: state.filters.category,
        subcategory: state.filters.subcategory || undefined,
        sort: state.filters.sort,
        page
      });
      state = {
        ...state,
        results: response.results,
        pagination: response.pagination,
        initialized: true
      };
    } catch (error) {
      console.error("Search failed:", error);
      const fallbackState = createDefaultSearchPageState();
      state = {
        ...state,
        results: [fallbackResult],
        pagination: fallbackState.pagination,
        initialized: true
      };
    } finally {
      state = {
        ...state,
        loading: false
      };
    }
  }

  function handleSearchSubmit() {
    void searchArchives(1);
  }

  function handlePageChange(event: CustomEvent<number>) {
    void searchArchives(event.detail);
  }

  function handleOpen(event: CustomEvent<ArchiveItem>) {
    dispatch("open", event.detail);
  }

  async function handleToggleTheme() {
    try {
      await updateTheme($libraryState.settings.theme === "dark" ? "light" : "dark");
    } catch (error) {
      console.error("Failed to update theme:", error);
    }
  }

  async function handleConfigureDownloads() {
    try {
      await chooseDownloadDirectory();
    } catch (error) {
      console.error("Failed to choose download directory:", error);
    }
  }

  onMount(() => {
    if (!state.initialized && !state.loading) {
      void searchArchives(1);
    }
  });
</script>

<div class="search-page">
  <div class="top-tabs" role="tablist" aria-label="Primary actions">
    {#each topTabs as tab}
      <button
        type="button"
        class="top-tab"
        class:top-tab-active={activeTab === tab.key}
        on:click={() => handleTabClick(tab.key)}
        aria-pressed={activeTab === tab.key}
      >
        <span class="top-tab-icon" aria-hidden="true">{tab.icon}</span>
        <span class="top-tab-label">{tab.label}</span>
      </button>
    {/each}
  </div>

  <div class="tab-panel">
    {#if activeTab === "search"}
      <div class="search-panel">
        <SearchControls
          bind:searchQuery={state.query}
          loading={state.loading}
          on:search={handleSearchSubmit}
        />
        <FilterPanel
          bind:selectedCategory={state.filters.category}
          bind:selectedSubcategory={state.filters.subcategory}
          bind:selectedSort={state.filters.sort}
        />
        <SearchResults
          results={state.results}
          loading={state.loading}
          currentPage={state.pagination.currentPage}
          totalPages={state.pagination.totalPages}
          pageNumbers={state.pagination.pageNumbers}
          totalResults={state.pagination.totalResults}
          resultStart={state.pagination.resultStart}
          resultEnd={state.pagination.resultEnd}
          on:open={handleOpen}
          on:page={handlePageChange}
        />
      </div>
    {:else if activeTab === "history"}
      {#if $libraryState.history.length > 0}
        <ReadingHistory entries={$libraryState.history} on:open={handleOpen} />
      {:else}
        <section class="tab-card">
          <p>No stories opened yet. Once you read something, it will show up here.</p>
        </section>
      {/if}
    {:else if activeTab === "downloads"}
      <section class="tab-card">
        <h3>Download directory</h3>
        <p>
          {#if $libraryState.settings.downloadDirectory}
            Stories will land in <strong>{$libraryState.settings.downloadDirectory}</strong>.
          {:else}
            No folder selected yet.
          {/if}
        </p>
        <button type="button" class="tab-card-button" on:click={handleConfigureDownloads}>
          { $libraryState.settings.downloadDirectory ? "Change folder" : "Choose folder" }
        </button>
      </section>
    {:else}
      <section class="tab-card">
        <h3>Theme</h3>
        <p>The active palette is {$libraryState.settings.theme === "dark" ? "dark" : "light"}.</p>
        <button type="button" class="tab-card-button" on:click={handleToggleTheme}>
          Switch to {$libraryState.settings.theme === "dark" ? "Light" : "Dark"} Theme
        </button>
      </section>
    {/if}
  </div>
</div>
