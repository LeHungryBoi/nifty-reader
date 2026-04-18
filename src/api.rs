use reqwest;
use scraper::{Html, Selector};
use serde::{Deserialize, Serialize};
use regex::Regex;

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
}

pub async fn fetch_nifty_story(url: &str) -> Result<Story, Box<dyn std::error::Error>> {
    // Using the same CORS proxy as the original JS code for WASM compatibility
    let proxy_url = format!("https://corsproxy.io/?{}", urlencoding::encode(url));
    
    let response = reqwest::get(&proxy_url).await?;
    if !response.status().is_success() {
        return Err(format!("Failed to fetch story: {}", response.status()).into());
    }

    let html = response.text().await?;
    let document = Html::parse_document(&html);

    // Extract content
    let pre_selector = Selector::parse("pre").unwrap();
    let content_text = if let Some(pre_element) = document.select(&pre_selector).next() {
        pre_element.text().collect::<Vec<_>>().join("")
    } else {
        // Fallback to body text
        document.root_element().text().collect::<Vec<_>>().join(" ")
    };

    // Cleanup logic
    let re_support = Regex::new("(?i)Please Support the Nifty Archive").unwrap();
    let re_date = Regex::new("(?i)Date:.*?\n").unwrap();
    let re_from = Regex::new("(?i)From:.*?\n").unwrap();
    let re_subject = Regex::new("(?i)Subject:.*?\n").unwrap();

    let mut cleaned = re_support.replace_all(&content_text, "").to_string();
    cleaned = re_date.replace_all(&cleaned, "").to_string();
    cleaned = re_from.replace_all(&cleaned, "").to_string();
    cleaned = re_subject.replace_all(&cleaned, "").to_string();

    // Split into paragraphs (double blank lines)
    let raw_paragraphs: Vec<&str> = cleaned.split("\n\n").collect();
    let paragraphs: Vec<String> = raw_paragraphs
        .into_iter()
        .map(|p| p.trim().replace("\n", " "))
        .filter(|p| !p.is_empty())
        .collect();

    // Guess title from URL
    let url_parts: Vec<&str> = url.split('/').collect();
    let last_part = url_parts.last().cloned().unwrap_or("unknown-story");
    let mut title = last_part
        .replace(".html", "")
        .replace(".htm", "")
        .replace("-", " ")
        .replace("_", " ");
    
    if title.is_empty() {
        title = "Unknown Story".to_string();
    } else {
        // Capitalize words
        title = title.split_whitespace()
            .map(|word| {
                let mut chars = word.chars();
                match chars.next() {
                    None => String::new(),
                    Some(first) => first.to_uppercase().collect::<String>() + chars.as_str(),
                }
            })
            .collect::<Vec<_>>()
            .join(" ");
    }

    Ok(Story {
        title,
        paragraphs,
        original_url: url.to_string(),
    })
}

pub async fn fetch_latest_stories() -> Result<Vec<StorySummary>, Box<dyn std::error::Error>> {
    let url = "https://search.niftyarchives.org/";
    let proxy_url = format!("https://corsproxy.io/?{}", urlencoding::encode(url));
    
    let response = reqwest::get(&proxy_url).await?;
    let html = response.text().await?;
    let document = Html::parse_document(&html);
    
    let mut summaries = Vec::new();
    let table_selector = Selector::parse("table.results tbody tr").unwrap();
    let rows = document.select(&table_selector);
    
    let mut current_summary: Option<StorySummary> = None;
    
    for row in rows {
        // If the row has a colspan=2, it's the chapters row
        if let Some(td) = row.select(&Selector::parse("td[colspan='2']").unwrap()).next() {
            if let Some(mut summary) = current_summary.take() {
                let chapter_selector = Selector::parse("a").unwrap();
                for chapter_link in td.select(&chapter_selector) {
                    let chapter_title = chapter_link.text().collect::<String>().trim().to_string();
                    let chapter_url = chapter_link.value().attr("href").unwrap_or("").to_string();
                    
                    // Normalize relative URLs
                    let full_url = if chapter_url.starts_with("http") {
                        chapter_url
                    } else {
                        format!("https://search.niftyarchives.org/{}", chapter_url.trim_start_matches('/'))
                    };
                    
                    summary.chapters.push((chapter_title, full_url));
                }
                summaries.push(summary);
            }
        } else {
            // It's a main story row
            let title_link = row.select(&Selector::parse("a[style*='font-weight: bold']").unwrap()).next();
            if let Some(link) = title_link {
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
                
                let date_added = row.select(&Selector::parse("td[style*='text-align:right']").unwrap())
                    .next()
                    .map(|td| td.text().collect::<String>().trim().to_string())
                    .unwrap_or_default();
                
                current_summary = Some(StorySummary {
                    title,
                    url: if story_url.starts_with("http") { story_url } else { format!("https://search.niftyarchives.org/{}", story_url.trim_start_matches('/')) },
                    categories,
                    subcategories,
                    date_added,
                    chapters: Vec::new(),
                });
            } else if let Some(summary) = current_summary.take() {
                // If we have a summary but no chapters row followed it immediately, push it now
                summaries.push(summary);
            }
        }
    }
    
    // Catch the last one if it didn't have a chapters row
    if let Some(summary) = current_summary {
        summaries.push(summary);
    }

    Ok(summaries)
}
