import { fetch } from '@tauri-apps/plugin-http';

/**
 * Nifty Archive Service
 * Handles fetching, parsing, caching, and cleaning story content.
 */

export interface ArchiveItem {
  id: string;
  title: string;
  author: string;
  date: string;
  description: string;
  url: string;
  categories: string[];
  subcategories: string[];
  parts?: string[]; // Multiple chapters if any
}

export interface StoryChapter {
  title: string;
  url: string;
  html: string;
}

export interface StoryDocument {
  title: string;
  chapters: StoryChapter[];
}

export interface SearchFilters {
  category?: string;
  subcategory?: string;
  sort?: SearchSort;
  page?: number;
}

export type SearchSort = "Relevance" | "Newest" | "Oldest";

export interface SearchPagination {
  currentPage: number;
  totalPages: number;
  pageNumbers: number[];
  totalResults: number;
  resultStart: number;
  resultEnd: number;
}

export interface SearchResultsPage {
  results: ArchiveItem[];
  pagination: SearchPagination;
}

// Cache only cleaned story bodies. Search results should always be fresh.
const STORY_CACHE_KEY = "nifty_story_cache_";
const CACHE_TTL = 1000 * 60 * 60 * 24 * 7; // 1 week

const getCached = <T>(key: string): T | null => {
  const cached = localStorage.getItem(STORY_CACHE_KEY + key);
  if (!cached) return null;
  const { data, timestamp } = JSON.parse(cached);
  if (Date.now() - timestamp > CACHE_TTL) {
    localStorage.removeItem(STORY_CACHE_KEY + key);
    return null;
  }
  return data;
};

const setCached = <T>(key: string, data: T) => {
  localStorage.setItem(STORY_CACHE_KEY + key, JSON.stringify({ data, timestamp: Date.now() }));
};

const normalizeTitle = (value: string) =>
  value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();

const sanitizeStructuredHtml = (html: string) => {
  const decoder = document.createElement("textarea");
  decoder.innerHTML = html;
  const decodedHtml = decoder.value;
  const parser = new DOMParser();
  const doc = parser.parseFromString(decodedHtml, "text/html");
  doc.querySelectorAll("script, style, iframe, object, embed").forEach((node) => node.remove());

  const preferredRoot =
    doc.body.querySelector("#story-content, article, main, pre, .story-content") ??
    doc.body;

  return preferredRoot.innerHTML.trim();
};

const extractChapterHtml = (rawText: string) => {
  if (/<\/?[a-z][\s\S]*>/i.test(rawText) || /&lt;\/?[a-z]/i.test(rawText)) {
    const structuredHtml = sanitizeStructuredHtml(rawText);
    if (structuredHtml.length > 0) {
      return structuredHtml;
    }
  }

  const paragraphs = extractStoryBody(rawText);
  if (paragraphs.length === 0) {
    return "";
  }

  return paragraphs
    .filter((block) => block.trim().length > 0)
    .map((block) => `<p>${block.trim()}</p>`)
    .join("");
};

const extractChapterTitle = (rawText: string, fallbackTitle: string) => {
  const subjectMatch = rawText.match(/^Subject:\s*(.+)$/im);
  if (subjectMatch?.[1]?.trim()) {
    return subjectMatch[1].trim();
  }

  const bodyText = rawText.replace(/^[\s\S]*?\n\s*\n/, "").trim();
  const firstBodyLine = bodyText.split(/\n+/).find((line) => line.trim().length > 0)?.trim();
  return firstBodyLine || fallbackTitle;
};

const extractStoryBody = (rawText: string): string[] => {
  const bodyText = rawText.replace(/^[\s\S]*?\n\s*\n/, "").trim();
  if (!bodyText) return [];

  const lines = bodyText.split("\n");
  const paragraphs = lines
    .join("\n")
    .replace(/\r/g, "")
    .split(/\n{2,}/)
    .map((block) =>
      block
        .replace(/(\S)\n(\S)/g, "$1 $2")
        .replace(/ +/g, " ")
        .trim()
    )
    .filter(Boolean);

  if (paragraphs.length === 0) {
    return [];
  }

  return paragraphs;
};

const formatChapterHtml = (rawText: string, chapterTitle: string) => {
  const structuredHtml = extractChapterHtml(rawText);
  if (structuredHtml.length > 0) {
    return structuredHtml;
  }

  const paragraphs = extractStoryBody(rawText);
  if (paragraphs.length === 0) {
    return `<p>Unable to parse chapter content.</p>`;
  }

  const normalizedChapterTitle = normalizeTitle(chapterTitle);
  const normalizedStoryTitle = normalizeTitle(
    rawText.match(/^Subject:\s*(.+)$/im)?.[1]?.trim() ?? chapterTitle
  );

  const bodyParagraphs =
    paragraphs.length > 0 &&
    (normalizeTitle(paragraphs[0]) === normalizedChapterTitle ||
      normalizeTitle(paragraphs[0]) === normalizedStoryTitle)
      ? paragraphs.slice(1)
      : paragraphs;

  const html = bodyParagraphs
    .filter((block) => block.trim().length > 0)
    .map((block) => `<p>${block.trim()}</p>`)
    .join("");

  return html || `<p>Unable to parse chapter content.</p>`;
};

const fetchStoryText = async (url: string) => {
  try {
    const response = await fetch(url, {
      method: "GET"
    });
    if (!response.ok) throw new Error(`Fetch failed: ${response.status}`);
    return response.text();
  } catch (error) {
    console.warn("Tauri fetch failed for story, trying standard fetch:", error);
    const response = await window.fetch(url);
    if (!response.ok) throw new Error(`Fetch failed: ${response.status}`);
    return response.text();
  }
};

/**
 * Parses Nifty Search HTML for story links
 * Based on search.niftyarchives.org structure
 */
export const parseSearchResults = (html: string): SearchResultsPage => {
  const parser = new DOMParser();
  const doc = parser.parseFromString(html, "text/html");
  const results: ArchiveItem[] = [];

  const rows = doc.querySelectorAll("table.results tbody tr");
  let currentItem: ArchiveItem | null = null;

  const normalizeDescription = (text: string) =>
    text
      .replace(/\s+/g, " ")
      .replace(/\s*([,.!?;:])\s*/g, "$1 ")
      .trim();

  rows.forEach((row) => {
    // Check if it's a main story title row or a parts row
    const mainLink = row.querySelector('a[style*="font-size: 1.5em"]');
    if (mainLink) {
      const url = (mainLink as HTMLAnchorElement).href;
      const title = mainLink.textContent?.trim() || "Untitled";
      const meta = row.querySelector(".meta") || row.querySelector("td:nth-child(2)");
      const author = row.querySelector(".label-success")?.textContent?.trim() || "Unknown";
      const date = meta?.textContent?.trim() || "";
      
      // Extract categories and subcategories
      const categoryLabels = Array.from(row.querySelectorAll('.label-success')).map(el => el.textContent?.trim() || '');
      const subcategoryLabels = Array.from(row.querySelectorAll('.label-info')).map(el => el.textContent?.trim() || '');
      
      currentItem = {
        id: url,
        title,
        author,
        date,
        description: "",
        url,
        categories: categoryLabels,
        subcategories: subcategoryLabels,
        parts: []
      };
      results.push(currentItem);
    } else {
      // Description rows are plain text blocks after the title row.
      const descriptionCell = row.querySelector('td[colspan="2"]');
      const linkedParts = row.querySelectorAll("a[href*='/nifty/']");

      if (currentItem && descriptionCell && linkedParts.length === 0) {
        const description = normalizeDescription(descriptionCell.textContent || "");
        if (description) {
          currentItem.description = description;
        }
        return;
      }

      // It might be a parts row.
      if (currentItem && linkedParts.length > 0) {
        linkedParts.forEach(p => {
          currentItem?.parts?.push((p as HTMLAnchorElement).href);
        });
      }
    }
  });

  const paginationRoot = doc.querySelector("ul.pagination");
  const currentPage = Number(
    doc.querySelector("ul.pagination li.active a")?.textContent?.trim() || "1"
  );
  const resultSummaryText = doc.body?.textContent?.match(/Results\s+(\d+)\s*-\s*(\d+)\s+of\s+(\d+)/i);
  const resultStart = Number(resultSummaryText?.[1] ?? "1");
  const resultEnd = Number(resultSummaryText?.[2] ?? String(results.length));
  const totalResults = Number(resultSummaryText?.[3] ?? String(results.length));
  const pageNumbers = Array.from(
    paginationRoot?.querySelectorAll('a[href*="page="]') ?? []
  )
    .map((link) => {
      const label = link.textContent?.trim() || "";
      const page = Number(label);
      return Number.isNaN(page) ? null : page;
    })
    .filter((page): page is number => page !== null);
  const totalPages = Math.max(
    currentPage,
    ...Array.from(paginationRoot?.querySelectorAll('a[href*="page="]') ?? []).map((link) => {
      const match = link.getAttribute("href")?.match(/[?&]page=(\d+)/);
      return match ? Number(match[1]) : 1;
    })
  );

  return {
    results,
    pagination: {
      currentPage: Number.isNaN(currentPage) ? 1 : currentPage,
      totalPages: Number.isNaN(totalPages) ? 1 : totalPages,
      pageNumbers: Array.from(new Set(pageNumbers)),
      totalResults: Number.isNaN(totalResults) ? results.length : totalResults,
      resultStart: Number.isNaN(resultStart) ? 1 : resultStart,
      resultEnd: Number.isNaN(resultEnd) ? results.length : resultEnd,
    }
  };
};

/**
 * Cleans the raw story text according to the user's script
 */
export const cleanStoryContent = (rawText: string): string => {
  const structuredHtml = extractChapterHtml(rawText);
  if (structuredHtml.length > 0) {
    return structuredHtml;
  }

  const paragraphs = extractStoryBody(rawText);
  return paragraphs.map((block) => `<p>${block}</p>`).join("");
};

/**
 * Fetches search results (via Tauri HTTP plugin to bypass CORS)
 */
export const fetchSearchResults = async (
  query: string,
  filters: SearchFilters = {}
): Promise<SearchResultsPage> => {
  const params = new URLSearchParams();
  params.set("keywords", query);
  params.set("search", "");
  if (filters.category) {
    params.append("categories[]", filters.category);
  }
  if (filters.subcategory) {
    params.append("subcategories[]", filters.subcategory);
  }
  if (filters.sort) {
    params.set("sort", filters.sort);
  }
  if (filters.page) {
    params.set("page", String(filters.page));
  }

  const url = `https://search.niftyarchives.org/?${params.toString()}`;
  
  try {
    // Tauri's fetch bypasses CORS
    const response = await fetch(url, {
      method: 'GET',
      cache: 'no-store',
      headers: {
        'User-Agent': 'Mozilla/5.0 (NiftyReader/0.1.0)'
      }
    });
    
    if (!response.ok) throw new Error(`Search failed: ${response.status}`);
    
    const html = await response.text();
    return parseSearchResults(html);
  } catch (error) {
    console.warn("Tauri fetch failed, trying standard fetch (might fail due to CORS):", error);
    const response = await window.fetch(url, { cache: "no-store" });
    const html = await response.text();
    return parseSearchResults(html);
  }
};

/**
 * Fetches and cleans a story
 */
export const fetchAndCleanStory = async (url: string): Promise<string> => {
  const cacheKey = `story_${url}`;
  const cached = getCached<string>(cacheKey);
  if (cached) return cached;

  const rawText = await fetchStoryText(url);
  const cleanedHtml = cleanStoryContent(rawText);
  setCached(cacheKey, cleanedHtml);
  return cleanedHtml;
};

/**
 * Fetches a story series or single chapter and returns chapter-aware HTML.
 */
export const fetchStoryDocument = async (item: ArchiveItem): Promise<StoryDocument> => {
  const chapterUrls = item.parts && item.parts.length > 0 ? item.parts : [item.url];
  const cacheKey = `document_${item.id}`;
  const cached = getCached<StoryDocument>(cacheKey);
  if (cached && cached.chapters.length === chapterUrls.length) {
    return cached;
  }

  const rawChapters = await Promise.all(chapterUrls.map((chapterUrl) => fetchStoryText(chapterUrl)));
  const chapters: StoryChapter[] = rawChapters.map((rawText, index) => {
    const fallbackTitle =
      chapterUrls.length > 1 ? `${item.title} - Chapter ${index + 1}` : item.title;
    const title = extractChapterTitle(rawText, fallbackTitle);
    return {
      title,
      url: chapterUrls[index],
      html: formatChapterHtml(rawText, title)
    };
  });

  const document: StoryDocument = {
    title: item.title,
    chapters
  };

  setCached(cacheKey, document);
  return document;
};
