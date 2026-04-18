use reqwest;
use scraper::{Html, Selector};
use serde::{Deserialize, Serialize};
use regex::Regex;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct Story {
    pub title: String,
    pub paragraphs: Vec<String>,
    pub original_url: String,
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
