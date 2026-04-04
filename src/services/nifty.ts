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
  parts?: string[]; // Multiple chapters if any
}

// Caching logic using local localStorage for simplicity
const CACHE_KEY = "nifty_cache_";
const CACHE_TTL = 1000 * 60 * 60 * 24 * 7; // 1 week

const getCached = <T>(key: string): T | null => {
  const cached = localStorage.getItem(CACHE_KEY + key);
  if (!cached) return null;
  const { data, timestamp } = JSON.parse(cached);
  if (Date.now() - timestamp > CACHE_TTL) {
    localStorage.removeItem(CACHE_KEY + key);
    return null;
  }
  return data;
};

const setCached = <T>(key: string, data: T) => {
  localStorage.setItem(CACHE_KEY + key, JSON.stringify({ data, timestamp: Date.now() }));
};

/**
 * Parses Nifty Search HTML for story links
 * Based on search.niftyarchives.org structure
 */
export const parseSearchResults = (html: string): ArchiveItem[] => {
  const parser = new DOMParser();
  const doc = parser.parseFromString(html, "text/html");
  const results: ArchiveItem[] = [];

  const rows = doc.querySelectorAll("table.results tbody tr");
  let currentItem: ArchiveItem | null = null;

  rows.forEach((row) => {
    // Check if it's a main story title row or a parts row
    const mainLink = row.querySelector('a[style*="font-size: 1.5em"]');
    if (mainLink) {
      const url = (mainLink as HTMLAnchorElement).href;
      const title = mainLink.textContent?.trim() || "Untitled";
      const meta = row.querySelector(".meta") || row.querySelector("td:nth-child(2)");
      const author = row.querySelector(".label-success")?.textContent?.trim() || "Unknown";
      const date = meta?.textContent?.trim() || "";
      
      currentItem = {
        id: url,
        title,
        author,
        date,
        description: "",
        url,
        parts: []
      };
      results.push(currentItem);
    } else {
      // It might be a parts row
      const parts = row.querySelectorAll("a[href*='/nifty/']");
      if (currentItem && parts.length > 0) {
        parts.forEach(p => {
          currentItem?.parts?.push((p as HTMLAnchorElement).href);
        });
      }
    }
  });

  return results;
};

/**
 * Cleans the raw story text according to the user's script
 */
export const cleanStoryContent = (rawText: string): string => {
  let text = rawText;
  // Based on nifty-clean-up.js logic
  text = text.replace(/(\S)\n(\S)/g, '$1 $2'); // Fix line breaks
  text = text.replace(/ +/g, ' '); // Compact spaces

  const paragraphBlocks = text.split(/\n{2,}/);
  const articleHtml = paragraphBlocks
    .filter(block => block.trim().length > 0)
    .map(block => `<p>${block.trim()}</p>`)
    .join("");

  return articleHtml;
};

/**
 * Fetches search results (via Tauri HTTP plugin to bypass CORS)
 */
export const fetchSearchResults = async (query: string): Promise<ArchiveItem[]> => {
  const cacheKey = `search_${query}`;
  const cached = getCached<ArchiveItem[]>(cacheKey);
  if (cached) return cached;

  const url = `https://search.niftyarchives.org/?keywords=${encodeURIComponent(query)}`;
  
  try {
    // Tauri's fetch bypasses CORS
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'User-Agent': 'Mozilla/5.0 (NiftyReader/0.1.0)'
      }
    });
    
    if (!response.ok) throw new Error(`Search failed: ${response.status}`);
    
    const html = await response.text();
    const results = parseSearchResults(html);
    
    setCached(cacheKey, results);
    return results;
  } catch (error) {
    console.warn("Tauri fetch failed, trying standard fetch (might fail due to CORS):", error);
    const response = await window.fetch(url);
    const html = await response.text();
    const results = parseSearchResults(html);
    setCached(cacheKey, results);
    return results;
  }
};

/**
 * Fetches and cleans a story
 */
export const fetchAndCleanStory = async (url: string): Promise<string> => {
  const cacheKey = `story_${url}`;
  const cached = getCached<string>(cacheKey);
  if (cached) return cached;

  try {
    const response = await fetch(url, {
      method: 'GET'
    });
    if (!response.ok) throw new Error(`Fetch failed: ${response.status}`);
    
    const rawText = await response.text();
    const cleanedHtml = cleanStoryContent(rawText);
    
    setCached(cacheKey, cleanedHtml);
    return cleanedHtml;
  } catch (error) {
    console.warn("Tauri fetch failed for story, trying standard fetch:", error);
    const response = await window.fetch(url);
    const rawText = await response.text();
    const cleanedHtml = cleanStoryContent(rawText);
    setCached(cacheKey, cleanedHtml);
    return cleanedHtml;
  }
};
