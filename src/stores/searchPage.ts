import { writable } from "svelte/store";
import type { ArchiveItem, SearchPagination, SearchSort } from "../services/nifty";

export interface SearchPageState {
  query: string;
  filters: {
    category: string;
    subcategory: string;
    sort: SearchSort;
  };
  results: ArchiveItem[];
  pagination: SearchPagination;
  loading: boolean;
  initialized: boolean;
}

const createDefaultPagination = (): SearchPagination => ({
  currentPage: 1,
  totalPages: 1,
  pageNumbers: [],
  totalResults: 0,
  resultStart: 0,
  resultEnd: 0
});

export const createDefaultSearchPageState = (): SearchPageState => ({
  query: "",
  filters: {
    category: "gay",
    subcategory: "",
    sort: "Relevance"
  },
  results: [],
  pagination: createDefaultPagination(),
  loading: false,
  initialized: false
});

export const cloneSearchPageState = (state: SearchPageState): SearchPageState => ({
  query: state.query,
  filters: {
    category: state.filters.category,
    subcategory: state.filters.subcategory,
    sort: state.filters.sort
  },
  results: [...state.results],
  pagination: {
    currentPage: state.pagination.currentPage,
    totalPages: state.pagination.totalPages,
    pageNumbers: [...state.pagination.pageNumbers],
    totalResults: state.pagination.totalResults,
    resultStart: state.pagination.resultStart,
    resultEnd: state.pagination.resultEnd
  },
  loading: state.loading,
  initialized: state.initialized
});

export const searchPageState = writable<SearchPageState>(createDefaultSearchPageState());
