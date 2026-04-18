<script lang="ts">
  import { categoryOptions, subcategoryOptions } from "../lib/niftyCategories";
  import type { SearchSort } from "../services/nifty";
  import "../styles/search-form.css";

  export let selectedCategory = "gay";
  export let selectedSubcategory = "";
  export let selectedSort: SearchSort = "Relevance";
</script>

<div class="search-bar search-bar--filters">
  <div class="search-field">
    <label for="search-category">Category</label>
    <select id="search-category" bind:value={selectedCategory} class="search-select">
      {#each categoryOptions as option}
        <option value={option.value}>{option.label}</option>
      {/each}
    </select>
  </div>

  <div class="search-field">
    <label for="search-subcategory">Subcategory</label>
    <select id="search-subcategory" bind:value={selectedSubcategory} class="search-select">
      <option value="">Any</option>
      {#each subcategoryOptions as option}
        <option value={option.value}>{option.label}</option>
      {/each}
    </select>
  </div>

  <div class="search-field">
    <label for="search-sort">Sort</label>
    <select id="search-sort" bind:value={selectedSort} class="search-select">
      <option value="Relevance">Relevance</option>
      <option value="Newest">Newest</option>
      <option value="Oldest">Oldest</option>
    </select>
  </div>
</div>
