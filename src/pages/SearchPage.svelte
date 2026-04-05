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
  <SearchControls
    bind:searchQuery={state.query}
    loading={state.loading}
    theme={$libraryState.settings.theme}
    downloadDirectory={$libraryState.settings.downloadDirectory}
    on:search={handleSearchSubmit}
    on:toggleTheme={handleToggleTheme}
    on:configureDownloads={handleConfigureDownloads}
  />
  <ReadingHistory entries={$libraryState.history} on:open={handleOpen} />
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
