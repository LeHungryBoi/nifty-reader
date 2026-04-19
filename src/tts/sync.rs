//! Word boundary synchronization for TTS highlighting
//!
//! Maps audio timestamps to word indices for real-time text highlighting
//! during playback.

use regex::Regex;

/// Manages word boundary synchronization for TTS
#[derive(Clone)]
pub struct WordBoundarySync {
    word_splitter: Regex,
}

impl WordBoundarySync {
    /// Create a new word boundary sync
    pub fn new() -> Self {
        // Regex to split text into words, preserving punctuation
        let word_splitter = Regex::new(r"\b\w+\b").unwrap();

        Self { word_splitter }
    }

    /// Create synchronization data for a text
    ///
    /// Returns a vector of (word_index, estimated_timestamp) tuples
    pub fn create_sync_for_text(&self, text: &str) -> Vec<(usize, f32)> {
        let words: Vec<&str> = self.word_splitter.find_iter(text)
            .map(|m| m.as_str())
            .collect();

        let total_words = words.len();
        if total_words == 0 {
            return vec![];
        }

        // Estimate speaking time per word (rough approximation)
        // Average speaking rate is about 150 words per minute = 2.5 words per second
        let words_per_second = 2.5;
        let total_duration_seconds = total_words as f32 / words_per_second;

        // Create word boundaries with linear time distribution
        words.iter().enumerate().map(|(index, _word)| {
            let progress = index as f32 / total_words as f32;
            let timestamp = progress * total_duration_seconds;
            (index, timestamp)
        }).collect()
    }

    /// Find word index for a given timestamp
    pub fn get_word_index_at_time(&self, sync_data: &[(usize, f32)], timestamp: f32) -> Option<usize> {
        // Find the word that should be highlighted at this timestamp
        for (word_index, word_timestamp) in sync_data.iter().rev() {
            if timestamp >= *word_timestamp {
                return Some(*word_index);
            }
        }
        None
    }

    /// Get all word indices that should be highlighted in a time range
    pub fn get_word_indices_in_range(&self, sync_data: &[(usize, f32)], start_time: f32, end_time: f32) -> Vec<usize> {
        sync_data.iter()
            .filter(|(_, timestamp)| *timestamp >= start_time && *timestamp < end_time)
            .map(|(word_index, _)| *word_index)
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_word_boundary_sync() {
        let sync = WordBoundarySync::new();
        let text = "Hello world, this is a test.";
        let sync_data = sync.create_sync_for_text(text);

        // Should find some words
        assert!(!sync_data.is_empty());

        // Should have reasonable timestamps
        for (_, timestamp) in &sync_data {
            assert!(*timestamp >= 0.0);
        }

        // Test word index lookup
        let word_index = sync.get_word_index_at_time(&sync_data, 0.5);
        assert!(word_index.is_some());
    }
}