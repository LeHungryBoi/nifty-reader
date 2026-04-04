<script lang="ts">
  import { onMount } from "svelte";
  import "./App.css";
  import {
    fetchSearchResults,
    fetchStoryDocument,
    type ArchiveItem,
    type SearchSort,
    type StoryDocument
  } from "./services/nifty";
  import SearchControls from "./components/SearchControls.svelte";
  import FilterPanel from "./components/FilterPanel.svelte";
  import SearchResults from "./components/SearchResults.svelte";
  import ReaderPanel from "./components/ReaderPanel.svelte";

  let searchQuery = "";
  let selectedCategory = "gay";
  let selectedSubcategory = "";
  let selectedSort: SearchSort = "Relevance";
  let results: ArchiveItem[] = [];
  let currentPage = 1;
  let totalPages = 1;
  let pageNumbers: number[] = [];
  let totalResults = 0;
  let resultStart = 0;
  let resultEnd = 0;
  let loading = false;
  let selectedItem: ArchiveItem | null = null;
  let storyDocument: StoryDocument | null = null;

  async function searchArchives(page = 1) {
    currentPage = page;
    loading = true;
    try {
      const response = await fetchSearchResults(searchQuery, {
        category: selectedCategory,
        subcategory: selectedSubcategory || undefined,
        sort: selectedSort,
        page: currentPage
      });
      results = response.results;
      currentPage = response.pagination.currentPage;
      totalPages = response.pagination.totalPages;
      pageNumbers = response.pagination.pageNumbers;
      totalResults = response.pagination.totalResults;
      resultStart = response.pagination.resultStart;
      resultEnd = response.pagination.resultEnd;
    } catch (error) {
      console.error("Search failed:", error);
      currentPage = 1;
      totalPages = 1;
      pageNumbers = [];
      totalResults = 0;
      resultStart = 0;
      resultEnd = 0;
      results = [
        {
          id: "1",
          title: "Demo Story (Search failed, see console)",
          author: "Self",
          date: "2025-01-15",
          description: "Search likely failed due to CORS.",
          url: "https://www.nifty.org/nifty/lesbian/hookers/linda-becomes-a-prostitute",
          categories: [],
          subcategories: []
        }
      ];
    } finally {
      loading = false;
    }
  }

  async function openReader(item: ArchiveItem) {
    selectedItem = item;
    loading = true;
    storyDocument = null;
    try {
      storyDocument = await fetchStoryDocument(item);
    } catch (error) {
      console.error("Failed to load story:", error);
      storyDocument = {
        title: item.title,
        chapters: [
          {
            title: "Could not load story",
            url: item.url,
            html: `
              <div class="error">
                <h2>Could not load story</h2>
                <p>Visit the story directly at: <a href="${item.url}" target="_blank" rel="noreferrer">${item.url}</a></p>
              </div>
            `
          }
        ]
      };
    } finally {
      loading = false;
    }
  }

  function closeReader() {
    selectedItem = null;
    storyDocument = null;
  }

  function handleKeyDown(e: KeyboardEvent) {
    if (e.key === "Escape") closeReader();
    if (e.key === "Enter" && !selectedItem) searchArchives(1);
  }

  onMount(() => {
    if (results.length === 0 && !loading) {
      searchArchives(1);
    }
  });
</script>

<svelte:window on:keydown={handleKeyDown} />

<div class="app">
  {#if !selectedItem}
    <SearchControls bind:searchQuery {loading} on:search={() => searchArchives(1)} />
    <FilterPanel
      bind:selectedCategory
      bind:selectedSubcategory
      bind:selectedSort
    />
    <SearchResults
      {results}
      {loading}
      {currentPage}
      {totalPages}
      {pageNumbers}
      {totalResults}
      {resultStart}
      {resultEnd}
      on:open={(event) => openReader(event.detail)}
      on:page={(event) => searchArchives(event.detail)}
    />
  {:else}
    <ReaderPanel
      selectedItem={selectedItem}
      {loading}
      story={storyDocument}
      on:close={closeReader}
    />
  {/if}

  <footer class="footer">
    <p>Nifty Reader - Built with Tauri + Svelte</p>
  </footer>
</div>
