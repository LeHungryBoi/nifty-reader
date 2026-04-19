use regex::Regex;
use reqwest;
use scraper::{Html, Selector};
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize, Clone, PartialEq)]
pub struct Story {
  pub title: String,
  pub paragraphs: Vec<String>,
  pub original_url: String,
}

#[derive(Clone, Serialize, Deserialize, Debug, Default, PartialEq)]
pub struct HistoryItem {
  pub title: String,
  pub url: String,
  pub timestamp: u64,
}

#[derive(Debug, Serialize, Deserialize, Clone, PartialEq)]
pub struct StorySummary {
  pub title: String,
  pub url: String,
  pub categories: Vec<String>,
  pub subcategories: Vec<String>,
  pub date_added: String,
  pub chapters: Vec<(String, String)>, // (chapter_title, chapter_url)
  pub snippet: Option<String>,         // HTML snippet with <em class="highlight">
}

fn get_client(proxy_url: Option<&str>) -> Result<reqwest::Client, Box<dyn std::error::Error>> {
  let mut builder = reqwest::Client::builder();
  if let Some(url) = proxy_url {
    if !url.is_empty() {
      builder = builder.proxy(reqwest::Proxy::all(url)?);
    }
  }
  Ok(builder.build()?)
}

/// Guess a human-readable title from the URL path.
fn guess_title_from_url(url: &str) -> String {
  let url_parts: Vec<&str> = url.split('/').collect();
  let last_part = url_parts.last().cloned().unwrap_or("unknown-story");
  let title = last_part
    .replace(".html", "")
    .replace(".htm", "")
    .replace("-", " ")
    .replace("_", " ");
  if title.is_empty() {
    return "Unknown Story".to_string();
  }
  title
    .split_whitespace()
    .map(|word| {
      let mut chars = word.chars();
      match chars.next() {
        None => String::new(),
        Some(first) => first.to_uppercase().collect::<String>() + chars.as_str(),
      }
    })
    .collect::<Vec<_>>()
    .join(" ")
}

/// Apply userscript-style text cleanup to raw story text.
/// 1. Collapse faux word-wrap newlines (single \n between non-whitespace → space)
/// 2. Collapse multiple spaces
/// 3. Remove noise headers (Date:, From:, Subject:, support plea)
/// 4. Split on double-newlines to form paragraphs
fn parse_plain_text_story(text: &str) -> Vec<String> {
  // Step 1: collapse word-wrap — single newline between non-whitespace becomes a space
  let re_word_wrap = Regex::new(r"(\S)\n(\S)").unwrap();
  let cleaned = re_word_wrap.replace_all(text, "$1 $2").to_string();

  // Step 2: collapse multiple spaces
  let re_spaces = Regex::new(r" {2,}").unwrap();
  let cleaned = re_spaces.replace_all(&cleaned, " ").to_string();

  // Step 3: strip noise
  let re_support = Regex::new(r"(?i)please support the nifty archive[^\n]*").unwrap();
  let re_date = Regex::new(r"(?im)^Date:.*$").unwrap();
  let re_from = Regex::new(r"(?im)^From:.*$").unwrap();
  let re_subject = Regex::new(r"(?im)^Subject:.*$").unwrap();
  let cleaned = re_support.replace_all(&cleaned, "").to_string();
  let cleaned = re_date.replace_all(&cleaned, "").to_string();
  let cleaned = re_from.replace_all(&cleaned, "").to_string();
  let cleaned = re_subject.replace_all(&cleaned, "").to_string();

  // Step 4: split on 2+ newlines → paragraphs; normalize remaining single newlines
  let re_para_break = Regex::new(r"\n{2,}").unwrap();
  re_para_break
    .split(&cleaned)
    .map(|block| block.replace('\n', " ").trim().to_string())
    .filter(|p| !p.is_empty() && p.len() > 2)
    .collect()
}

pub async fn fetch_nifty_story(
  url: &str,
  proxy_url: Option<&str>,
) -> Result<Story, Box<dyn std::error::Error>> {
  let client = get_client(proxy_url)?;
  let response = client.get(url).send().await?;
  if !response.status().is_success() {
    return Err(format!("Failed to fetch story: {}", response.status()).into());
  }

  // Detect content type from headers
  let content_type = response
    .headers()
    .get("content-type")
    .and_then(|v| v.to_str().ok())
    .unwrap_or("")
    .to_lowercase();
  let is_plain_text = content_type.contains("text/plain");

  let body = response.text().await?;

  let paragraphs = if is_plain_text {
    // Raw plain text — apply userscript-style parsing directly
    parse_plain_text_story(&body)
  } else {
    // HTML — look for <pre> tag (Nifty plain-text stories wrapped in <pre> by browser/server)
    let document = Html::parse_document(&body);
    let pre_selector = Selector::parse("pre").unwrap();
    let has_tables = document
      .select(&Selector::parse("table").unwrap())
      .next()
      .is_some();

    if let Some(pre_element) = document.select(&pre_selector).next() {
      // Has <pre> and no tables → treat as plain-text story
      if !has_tables {
        let raw = pre_element.text().collect::<Vec<_>>().join("");
        parse_plain_text_story(&raw)
      } else {
        // <pre> with tables — unusual, just extract text
        let raw = pre_element.text().collect::<Vec<_>>().join("");
        parse_plain_text_story(&raw)
      }
    } else {
      // True HTML story — extract body paragraphs
      let body_text = document.root_element().text().collect::<Vec<_>>().join(" ");
      parse_plain_text_story(&body_text)
    }
  };

  let title = guess_title_from_url(url);

  Ok(Story {
    title,
    paragraphs,
    original_url: url.to_string(),
  })
}

/// Simple percent-encode for query string values (spaces → +, special chars → %XX).
fn url_encode(s: &str) -> String {
  let mut out = String::with_capacity(s.len());
  for c in s.chars() {
    match c {
      'A'..='Z' | 'a'..='z' | '0'..='9' | '-' | '_' | '.' | '~' => out.push(c),
      ' ' => out.push('+'),
      c => {
        for byte in c.to_string().as_bytes() {
          out.push_str(&format!("%{:02X}", byte));
        }
      }
    }
  }
  out
}

pub async fn fetch_latest_stories(
  proxy_url: Option<&str>,
  page: u32,
  category: Option<&str>,
  subcategory: Option<&str>,
  search_query: Option<&str>,
) -> Result<Vec<StorySummary>, Box<dyn std::error::Error>> {
  let mut params = Vec::new();
  if page > 1 {
    params.push(format!("page={}", page));
  }
  if let Some(cat) = category {
    if cat != "All" && !cat.is_empty() {
      params.push(format!("categories[]={}", cat));
    }
  }
  if let Some(sub) = subcategory {
    if sub != "All" && !sub.is_empty() {
      params.push(format!("subcategories[]={}", sub));
    }
  }
  if let Some(q) = search_query {
    if !q.is_empty() {
      params.push(format!("keywords={}", url_encode(q)));
    }
  }

  let url = if params.is_empty() {
    "https://search.niftyarchives.org/".to_string()
  } else {
    format!("https://search.niftyarchives.org/?{}", params.join("&"))
  };

  let client = get_client(proxy_url)?;
  let response = client.get(&url).send().await?;
  let html = response.text().await?;
  let document = Html::parse_document(&html);

  let mut summaries = Vec::new();
  let table_selector = Selector::parse("table.results tbody tr").unwrap();
  let rows = document.select(&table_selector);

  let mut current_summary: Option<StorySummary> = None;

  for row in rows {
    // If the row has a colspan=2, it's a detail row (chapters or snippet)
    if let Some(td) = row
      .select(&Selector::parse("td[colspan='2']").unwrap())
      .next()
    {
      if let Some(ref mut summary) = current_summary {
        // Check for chapters
        let chapter_selector = Selector::parse("a").unwrap();
        let mut has_chapters = false;
        for chapter_link in td.select(&chapter_selector) {
          let chapter_title = chapter_link.text().collect::<String>().trim().to_string();
          let chapter_url = chapter_link.value().attr("href").unwrap_or("").to_string();

          if !chapter_title.is_empty() && !chapter_url.is_empty() {
            let full_url = if chapter_url.starts_with("http") {
              chapter_url
            } else {
              format!(
                "https://search.niftyarchives.org/{}",
                chapter_url.trim_start_matches('/')
              )
            };
            summary.chapters.push((chapter_title, full_url));
            has_chapters = true;
          }
        }

        // If it doesn't have chapters, it might be a snippet
        if !has_chapters {
          let html = td.inner_html();
          // Extract text inside td, preserving some formatting like <em class="highlight">
          // We'll keep it as raw HTML for the UI to handle highlighting
          summary.snippet = Some(html);
        }
      }
    } else {
      // It's a main story row
      let title_link = row
        .select(&Selector::parse("a[style*='font-weight: bold']").unwrap())
        .next();
      if let Some(link) = title_link {
        // Before starting a new story, push the previous one
        if let Some(prev) = current_summary.take() {
          summaries.push(prev);
        }

        let title = link.text().collect::<String>().trim().to_string();
        let story_url = link.value().attr("href").unwrap_or("").to_string();

        let mut categories = Vec::new();
        for cat in row.select(&Selector::parse("span.label-success").unwrap()) {
          categories.push(cat.text().collect::<String>().trim().to_string());
        }

        let mut subcategories = Vec::new();
        for sub in row.select(&Selector::parse("span.label-info").unwrap()) {
          subcategories.push(sub.text().collect::<String>().trim().to_string());
        }

        let date_added = row
          .select(&Selector::parse("td[style*='text-align:right']").unwrap())
          .next()
          .map(|td| td.text().collect::<String>().trim().to_string())
          .unwrap_or_default();

        current_summary = Some(StorySummary {
          title,
          url: if story_url.starts_with("http") {
            story_url
          } else {
            format!(
              "https://search.niftyarchives.org/{}",
              story_url.trim_start_matches('/')
            )
          },
          categories,
          subcategories,
          date_added,
          chapters: Vec::new(),
          snippet: None,
        });
      }
    }
  }

  // Catch the last one if it didn't have a chapters row
  if let Some(summary) = current_summary {
    summaries.push(summary);
  }

  Ok(summaries)
}
