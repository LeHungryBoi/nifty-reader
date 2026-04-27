# nifty-core-go 规范

> **What this file is:** Go 后端 core 的详细规范。基于现有 Rust `nifty-core` 重构，保留相同功能但使用 Go 实现。
>
> **Boundary:** 描述 Go core 的目标结构、数据模型和 API 设计。实现代码放在 `nifty-core-go/` 目录。

---

## 项目结构

```
nifty-core-go/
├── go.mod
├── README.md
├── internal/
│   ├── models/          # 数据模型 (对应 Rust struct)
│   │   ├── story.go     # Story, StorySummary, HistoryItem
│   │   └── state.go     # AppState, Settings
│   ├── scraper/         # HTML 解析逻辑
│   │   └── nifty.go     # 抓取 search.niftyarchives.org
│   ├── storage/         # 状态持久化
│   │   └── state.go     # JSON 文件读写
│   └── utils/           # 工具函数
│       └── url.go       # URL encoding, title guessing
├── pkg/
│   └── api/             # 公开 API
│       ├── client.go    # HTTP client 配置
│       ├── story.go     # 故事相关接口
│       └── search.go    # 搜索相关接口
└── cmd/
    └── server/          # (可选) HTTP server 入口
        └── main.go
```

---

## 数据模型

### Story - 故事内容

对应 Rust `crates/nifty-core/src/network/api.rs` 中的 `Story` struct。

```go
package models

// Story 表示一个完整的故事内容
type Story struct {
    Title        string   `json:"title"`
    Paragraphs   []string `json:"paragraphs"`
    OriginalURL  string   `json:"original_url"`
}
```

### StorySummary - 搜索结果摘要

对应 Rust `StorySummary` struct。

```go
package models

// StorySummary 表示搜索结果中的故事摘要
type StorySummary struct {
    Title          string            `json:"title"`
    URL            string            `json:"url"`
    Categories     []string          `json:"categories"`
    Subcategories  []string          `json:"subcategories"`
    DateAdded      string            `json:"date_added"`
    Chapters       []Chapter         `json:"chapters"`  // (title, url) tuple
    Snippet        *string           `json:"snippet,omitempty"`  // HTML snippet
}

// Chapter 表示故事的章节
type Chapter struct {
    Title string `json:"title"`
    URL   string `json:"url"`
}
```

### HistoryItem - 阅读历史

对应 Rust `HistoryItem` struct。

```go
package models

// HistoryItem 表示一条阅读历史记录
type HistoryItem struct {
    Title     string `json:"title"`
    URL       string `json:"url"`
    Timestamp uint64 `json:"timestamp"`
}
```

### AppState + Settings - 应用状态

对应 Rust `AppState` 和 `Settings` struct。

```go
package models

// Settings 表示应用设置
type Settings struct {
    Theme    string  `json:"theme"`     // default: "dark"
    FontSize float32 `json:"font_size"` // default: 1.0
    ProxyURL *string `json:"proxy_url,omitempty"`
}

// AppState 表示完整的应用状态
type AppState struct {
    Settings Settings       `json:"settings"`
    History  []HistoryItem  `json:"history"`
}

// DefaultSettings 返回默认设置
func DefaultSettings() Settings {
    return Settings{
        Theme:    "dark",
        FontSize: 1.0,
        ProxyURL: nil,
    }
}

// DefaultAppState 返回默认应用状态
func DefaultAppState() AppState {
    return AppState{
        Settings: DefaultSettings(),
        History:  []HistoryItem{},
    }
}
```

---

## API 设计

### HTTP Client 配置

对应 Rust `ureq::Agent` 配置。

```go
package api

import (
    "net/http"
    "net/url"
    "time"
)

// Client 封装 HTTP 客户端配置
type Client struct {
    httpClient *http.Client
    proxyURL   string
}

// NewClient 创建新的 API 客户端
// proxyURL: 可选的代理地址，如 "http://127.0.0.1:7890"
func NewClient(proxyURL string) *Client {
    transport := &http.Transport{}
    
    if proxyURL != "" {
        if proxy, err := url.Parse(proxyURL); err == nil {
            transport.Proxy = http.ProxyURL(proxy)
        }
    }
    
    return &Client{
        httpClient: &http.Client{
            Transport: transport,
            Timeout:   30 * time.Second,
        },
        proxyURL: proxyURL,
    }
}

// WithTimeout 设置自定义超时
func (c *Client) WithTimeout(timeout time.Duration) *Client {
    c.httpClient.Timeout = timeout
    return c
}
```

### 故事获取

对应 Rust `fetch_nifty_story()` 函数。

```go
package api

import (
    "fmt"
    "io"
    "net/http"
    "strings"
    
    "github.com/PuerkitoBio/goquery"
    "nifty-core-go/internal/models"
    "nifty-core-go/internal/utils"
)

// FetchStory 从指定 URL 获取故事内容
func (c *Client) FetchStory(storyURL string) (*models.Story, error) {
    req, err := http.NewRequest("GET", storyURL, nil)
    if err != nil {
        return nil, err
    }
    
    resp, err := c.httpClient.Do(req)
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()
    
    if resp.StatusCode != http.StatusOK {
        return nil, fmt.Errorf("failed to fetch story: %d", resp.StatusCode)
    }
    
    body, err := io.ReadAll(resp.Body)
    if err != nil {
        return nil, err
    }
    
    contentType := resp.Header.Get("Content-Type")
    isPlainText := strings.Contains(strings.ToLower(contentType), "text/plain")
    
    var paragraphs []string
    if isPlainText {
        paragraphs = utils.ParsePlainTextStory(string(body))
    } else {
        paragraphs = parseHTMLStory(string(body))
    }
    
    title := utils.GuessTitleFromURL(storyURL)
    
    return &models.Story{
        Title:       title,
        Paragraphs:  paragraphs,
        OriginalURL: storyURL,
    }, nil
}

func parseHTMLStory(html string) []string {
    doc, err := goquery.NewDocumentFromReader(strings.NewReader(html))
    if err != nil {
        return []string{}
    }
    
    // 尝试从 <pre> 标签获取内容
    if pre := doc.Find("pre").First(); pre.Length() > 0 {
        text := pre.Text()
        return utils.ParsePlainTextStory(text)
    }
    
    // 回退：获取 body 全部文本
    text := doc.Find("body").Text()
    return utils.ParsePlainTextStory(text)
}
```

### 搜索/浏览

对应 Rust `fetch_latest_stories()` 函数。

```go
package api

import (
    "fmt"
    "io"
    "net/http"
    "net/url"
    "strings"
    
    "github.com/PuerkitoBio/goquery"
    "nifty-core-go/internal/models"
)

// SearchOptions 搜索选项
type SearchOptions struct {
    Page         int
    Category     string  // "All" 或空表示全部
    Subcategory  string  // "All" 或空表示全部
    SearchQuery  string
}

// SearchStories 搜索故事
func (c *Client) SearchStories(opts SearchOptions) ([]models.StorySummary, error) {
    params := url.Values{}
    
    if opts.Page > 1 {
        params.Set("page", fmt.Sprintf("%d", opts.Page))
    }
    if opts.Category != "" && opts.Category != "All" {
        params.Add("categories[]", opts.Category)
    }
    if opts.Subcategory != "" && opts.Subcategory != "All" {
        params.Add("subcategories[]", opts.Subcategory)
    }
    if opts.SearchQuery != "" {
        params.Set("keywords", utils.URLEncode(opts.SearchQuery))
    }
    
    baseURL := "https://search.niftyarchives.org/"
    if len(params) > 0 {
        baseURL = baseURL + "?" + params.Encode()
    }
    
    resp, err := c.httpClient.Get(baseURL)
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()
    
    body, err := io.ReadAll(resp.Body)
    if err != nil {
        return nil, err
    }
    
    return parseSearchResults(string(body)), nil
}

func parseSearchResults(html string) []models.StorySummary {
    doc, err := goquery.NewDocumentFromReader(strings.NewReader(html))
    if err != nil {
        return []models.StorySummary{}
    }
    
    var summaries []models.StorySummary
    var current *models.StorySummary
    
    doc.Find("table.results tbody tr").Each(func(i int, s *goquery.Selection) {
        // 检查是否是章节/摘要行 (colspan=2)
        if td := s.Find("td[colspan='2']").First(); td.Length() > 0 {
            if current == nil {
                return
            }
            
            // 尝试提取章节链接
            hasChapters := false
            td.Find("a").Each(func(j int, a *goquery.Selection) {
                chapterTitle := strings.TrimSpace(a.Text())
                chapterURL, _ := a.Attr("href")
                
                if chapterTitle != "" && chapterURL != "" {
                    fullURL := chapterURL
                    if !strings.HasPrefix(chapterURL, "http") {
                        fullURL = "https://search.niftyarchives.org/" + strings.TrimPrefix(chapterURL, "/")
                    }
                    current.Chapters = append(current.Chapters, models.Chapter{
                        Title: chapterTitle,
                        URL:   fullURL,
                    })
                    hasChapters = true
                }
            })
            
            // 如果没有章节，保存为 snippet
            if !hasChapters {
                html, _ := td.Html()
                current.Snippet = &html
            }
        } else {
            // 新故事行
            if current != nil {
                summaries = append(summaries, *current)
            }
            
            link := s.Find("a[style*='font-weight: bold']").First()
            if link.Length() == 0 {
                current = nil
                return
            }
            
            title := strings.TrimSpace(link.Text())
            storyURL, _ := link.Attr("href")
            
            var categories []string
            s.Find("span.label-success").Each(func(i int, span *goquery.Selection) {
                categories = append(categories, strings.TrimSpace(span.Text()))
            })
            
            var subcategories []string
            s.Find("span.label-info").Each(func(i int, span *goquery.Selection) {
                subcategories = append(subcategories, strings.TrimSpace(span.Text()))
            })
            
            dateAdded := strings.TrimSpace(s.Find("td[style*='text-align:right']").First().Text())
            
            fullURL := storyURL
            if !strings.HasPrefix(storyURL, "http") {
                fullURL = "https://search.niftyarchives.org/" + strings.TrimPrefix(storyURL, "/")
            }
            
            current = &models.StorySummary{
                Title:         title,
                URL:           fullURL,
                Categories:    categories,
                Subcategories: subcategories,
                DateAdded:     dateAdded,
                Chapters:      []models.Chapter{},
            }
        }
    })
    
    if current != nil {
        summaries = append(summaries, *current)
    }
    
    return summaries
}
```

---

## 工具函数

### URL 编码

对应 Rust `url_encode()` 函数。

```go
package utils

import (
    "fmt"
    "strings"
)

// URLEncode 对字符串进行 URL 编码 (application/x-www-form-urlencoded)
func URLEncode(s string) string {
    var out strings.Builder
    for _, c := range s {
        switch {
        case (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') ||
             (c >= '0' && c <= '9') || c == '-' || c == '_' ||
             c == '.' || c == '~':
            out.WriteRune(c)
        case c == ' ':
            out.WriteByte('+')
        default:
            for _, b := range []byte(string(c)) {
                out.WriteString(fmt.Sprintf("%%%02X", b))
            }
        }
    }
    return out.String()
}
```

### 从 URL 猜测标题

对应 Rust `guess_title_from_url()` 函数。

```go
package utils

import (
    "strings"
)

// GuessTitleFromURL 从 URL 路径猜测可读标题
func GuessTitleFromURL(url string) string {
    parts := strings.Split(url, "/")
    if len(parts) == 0 {
        return "Unknown Story"
    }
    
    lastPart := parts[len(parts)-1]
    if lastPart == "" && len(parts) > 1 {
        lastPart = parts[len(parts)-2]
    }
    
    title := strings.ReplaceAll(lastPart, ".html", "")
    title = strings.ReplaceAll(title, ".htm", "")
    title = strings.ReplaceAll(title, "-", " ")
    title = strings.ReplaceAll(title, "_", " ")
    
    title = strings.TrimSpace(title)
    if title == "" {
        return "Unknown Story"
    }
    
    // 首字母大写
    words := strings.Fields(title)
    for i, word := range words {
        if len(word) > 0 {
            words[i] = strings.ToUpper(word[:1]) + strings.ToLower(word[1:])
        }
    }
    return strings.Join(words, " ")
}
```

### 纯文本故事解析

对应 Rust `parse_plain_text_story()` 函数。

```go
package utils

import (
    "regexp"
    "strings"
)

var (
    // 合并被换行分割的单词
    reWordWrap = regexp.MustCompile(`(\S)\n(\S)`)
    // 合并多个空格
    reSpaces = regexp.MustCompile(` {2,}`)
    // 移除支持信息
    reSupport = regexp.MustCompile(`(?i)please support the nifty archive[^\n]*`)
    // 移除邮件头
    reDate   = regexp.MustCompile(`(?im)^Date:.*$`)
    reFrom   = regexp.MustCompile(`(?im)^From:.*$`)
    reSubject = regexp.MustCompile(`(?im)^Subject:.*$`)
    // 段落分隔
    reParaBreak = regexp.MustCompile(`\n{2,}`)
)

// ParsePlainTextStory 解析纯文本故事内容
func ParsePlainTextStory(text string) []string {
    // 合并被换行分割的单词
    cleaned := reWordWrap.ReplaceAllString(text, "$1 $2")
    
    // 合并多个空格
    cleaned = reSpaces.ReplaceAllString(cleaned, " ")
    
    // 移除支持信息和邮件头
    cleaned = reSupport.ReplaceAllString(cleaned, "")
    cleaned = reDate.ReplaceAllString(cleaned, "")
    cleaned = reFrom.ReplaceAllString(cleaned, "")
    cleaned = reSubject.ReplaceAllString(cleaned, "")
    
    // 按段落分割
    blocks := reParaBreak.Split(cleaned, -1)
    
    var paragraphs []string
    for _, block := range blocks {
        // 将单个换行替换为空格
        p := strings.ReplaceAll(block, "\n", " ")
        p = strings.TrimSpace(p)
        // 过滤空段落和过短内容
        if len(p) > 2 {
            paragraphs = append(paragraphs, p)
        }
    }
    
    return paragraphs
}
```

---

## 状态存储

对应 Rust `storage/state.rs`。

```go
package storage

import (
    "encoding/json"
    "os"
    "path/filepath"
    
    "github.com/adrg/xdg"
    "nifty-core-go/internal/models"
)

// StateManager 管理应用状态持久化
type StateManager struct {
    statePath string
}

// NewStateManager 创建状态管理器
func NewStateManager() *StateManager {
    configDir := filepath.Join(xdg.ConfigHome, "niftyreader")
    
    // 确保目录存在
    os.MkdirAll(configDir, 0755)
    
    return &StateManager{
        statePath: filepath.Join(configDir, "state.json"),
    }
}

// LoadState 加载应用状态
func (sm *StateManager) LoadState() models.AppState {
    data, err := os.ReadFile(sm.statePath)
    if err != nil {
        return models.DefaultAppState()
    }
    
    var state models.AppState
    if err := json.Unmarshal(data, &state); err != nil {
        return models.DefaultAppState()
    }
    
    return state
}

// SaveState 保存应用状态
func (sm *StateManager) SaveState(state *models.AppState) error {
    data, err := json.Marshal(state)
    if err != nil {
        return err
    }
    
    return os.WriteFile(sm.statePath, data, 0644)
}
```

---

## 依赖

`go.mod`:

```go
module nifty-core-go

go 1.21

require (
    github.com/PuerkitoBio/goquery v1.8.1
    github.com/adrg/xdg v0.4.0
)
```

---

## 与 Rust Core 的对应关系

| Rust (crates/nifty-core) | Go (nifty-core-go) |
|--------------------------|-------------------|
| `network/api.rs` Story | `internal/models/story.go` Story |
| `network/api.rs` StorySummary | `internal/models/story.go` StorySummary |
| `network/api.rs` HistoryItem | `internal/models/story.go` HistoryItem |
| `storage/state.rs` AppState/Settings | `internal/models/state.go` AppState/Settings |
| `network/api.rs` fetch_nifty_story() | `pkg/api/story.go` FetchStory() |
| `network/api.rs` fetch_latest_stories() | `pkg/api/search.go` SearchStories() |
| `storage/state.rs` load/save_state() | `internal/storage/state.go` Load/SaveState() |
| `ureq::Agent` | `net/http.Client` |
| `scraper` (CSS selector) | `github.com/PuerkitoBio/goquery` |
| `regex::Regex` | `regexp` 标准库 |
| `serde_json` | `encoding/json` |
| `directories` | `github.com/adrg/xdg` |

---

## 迁移状态

| 组件 | 状态 | 备注 |
|------|------|------|
| 数据模型 | 已设计 | 对应 Rust struct |
| HTTP Client | 已设计 | 支持代理配置 |
| 故事获取 | 已设计 | HTML + 纯文本解析 |
| 搜索/浏览 | 已设计 | CSS selector 解析 |
| 状态存储 | 已设计 | JSON 文件持久化 |
| 工具函数 | 已设计 | URL 编码、标题猜测、文本解析 |
