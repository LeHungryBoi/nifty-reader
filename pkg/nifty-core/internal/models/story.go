package models

// Story 表示一个完整的故事内容
type Story struct {
	Title       string    `json:"title"`
	Paragraphs  []string  `json:"paragraphs"`
	OriginalURL string    `json:"original_url"`
	Chapters    []Chapter `json:"chapters,omitempty"` // For multi-chapter stories
}

// StorySummary 表示搜索结果中的故事摘要
type StorySummary struct {
	Title         string    `json:"title"`
	URL           string    `json:"url"`
	Categories    []string  `json:"categories"`
	Subcategories []string  `json:"subcategories"`
	DateAdded     string    `json:"date_added"`
	Chapters      []Chapter `json:"chapters"`          // (title, url) tuple
	Snippet       *string   `json:"snippet,omitempty"` // HTML snippet
}

// Chapter 表示故事的章节
type Chapter struct {
	Title string `json:"title"`
	URL   string `json:"url"`
}

// HistoryItem 表示一条阅读历史记录
type HistoryItem struct {
	Title     string `json:"title"`
	URL       string `json:"url"`
	Timestamp uint64 `json:"timestamp"`
}
