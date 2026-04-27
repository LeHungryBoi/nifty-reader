package core

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"regexp"
	"strings"

	"github.com/PuerkitoBio/goquery"
)

// Data Structures

type Story struct {
	Title       string   `json:"title"`
	Paragraphs  []string `json:"paragraphs"`
	OriginalURL string   `json:"original_url"`
}

type HistoryItem struct {
	Title     string `json:"title"`
	URL       string `json:"url"`
	Timestamp uint64 `json:"timestamp"`
}

type StorySummary struct {
	Title         string      `json:"title"`
	URL           string      `json:"url"`
	Categories    []string    `json:"categories"`
	Subcategories []string    `json:"subcategories"`
	DateAdded     string      `json:"date_added"`
	Chapters      [][2]string `json:"chapters"` // [title, url]
	Snippet       *string     `json:"snippet,omitempty"`
}

type Settings struct {
	Theme    string  `json:"theme"`
	FontSize float32 `json:"font_size"`
	ProxyURL *string `json:"proxy_url"`
}

type AppState struct {
	Settings Settings      `json:"settings"`
	History  []HistoryItem `json:"history"`
}

// Helpers

func getClient(proxyURL *string) (*http.Client, error) {
	if proxyURL == nil || *proxyURL == "" {
		return &http.Client{}, nil
	}

	proxy, err := url.Parse(*proxyURL)
	if err != nil {
		return nil, err
	}

	transport := &http.Transport{
		Proxy: http.ProxyURL(proxy),
	}

	return &http.Client{
		Transport: transport,
	}, nil
}

func guessTitleFromURL(storyURL string) string {
	u, err := url.Parse(storyURL)
	if err != nil {
		return "Unknown Story"
	}

	parts := strings.Split(u.Path, "/")
	lastPart := parts[len(parts)-1]
	if lastPart == "" && len(parts) > 1 {
		lastPart = parts[len(parts)-2]
	}

	title := strings.ReplaceAll(lastPart, ".html", "")
	title = strings.ReplaceAll(title, ".htm", "")
	title = strings.ReplaceAll(title, "-", " ")
	title = strings.ReplaceAll(title, "_", " ")

	if title == "" {
		return "Unknown Story"
	}

	words := strings.Fields(title)
	for i, word := range words {
		if len(word) > 0 {
			words[i] = strings.ToUpper(word[:1]) + word[1:]
		}
	}
	return strings.Join(words, " ")
}

func parsePlainTextStory(text string) []string {
	// Step 1: collapse word-wrap
	reWordWrap := regexp.MustCompile(`(\S)\n(\S)`)
	cleaned := reWordWrap.ReplaceAllString(text, "$1 $2")

	// Step 2: collapse multiple spaces
	reSpaces := regexp.MustCompile(` {2,}`)
	cleaned = reSpaces.ReplaceAllString(cleaned, " ")

	// Step 3: strip noise
	reSupport := regexp.MustCompile(`(?i)please support the nifty archive[^\n]*`)
	reDate := regexp.MustCompile(`(?im)^Date:.*$`)
	reFrom := regexp.MustCompile(`(?im)^From:.*$`)
	reSubject := regexp.MustCompile(`(?im)^Subject:.*$`)

	cleaned = reSupport.ReplaceAllString(cleaned, "")
	cleaned = reDate.ReplaceAllString(cleaned, "")
	cleaned = reFrom.ReplaceAllString(cleaned, "")
	cleaned = reSubject.ReplaceAllString(cleaned, "")

	// Step 4: split on 2+ newlines
	reParaBreak := regexp.MustCompile(`\n{2,}`)
	blocks := reParaBreak.Split(cleaned, -1)

	var paragraphs []string
	for _, block := range blocks {
		p := strings.TrimSpace(strings.ReplaceAll(block, "\n", " "))
		if len(p) > 2 {
			paragraphs = append(paragraphs, p)
		}
	}
	return paragraphs
}

func GetStoragePath() string {
	configDir, err := os.UserConfigDir()
	if err != nil {
		return "state.json"
	}
	path := filepath.Join(configDir, "lehungryboi", "niftyreader")
	_ = os.MkdirAll(path, 0755)
	return filepath.Join(path, "state.json")
}

// Logic Functions

func FetchNiftyStory(storyURL string, proxyURL *string) (*Story, error) {
	client, err := getClient(proxyURL)
	if err != nil {
		return nil, err
	}

	resp, err := client.Get(storyURL)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("failed to fetch story: %s", resp.Status)
	}

	contentType := strings.ToLower(resp.Header.Get("Content-Type"))
	isPlainText := strings.Contains(contentType, "text/plain")

	bodyBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	body := string(bodyBytes)

	var paragraphs []string
	if isPlainText {
		paragraphs = parsePlainTextStory(body)
	} else {
		doc, err := goquery.NewDocumentFromReader(strings.NewReader(body))
		if err != nil {
			return nil, err
		}

		pre := doc.Find("pre")

		if pre.Length() > 0 {
			raw := pre.Text()
			paragraphs = parsePlainTextStory(raw)
		} else {
			// Fallback: extract all text
			raw := doc.Find("body").Text()
			if raw == "" {
				raw = doc.Text()
			}
			paragraphs = parsePlainTextStory(raw)
		}
	}

	return &Story{
		Title:       guessTitleFromURL(storyURL),
		Paragraphs:  paragraphs,
		OriginalURL: storyURL,
	}, nil
}

func FetchLatestStories(page uint32, category *string, subcategory *string, searchKeywords *string, proxyURL *string) ([]StorySummary, error) {
	params := url.Values{}
	if page > 1 {
		params.Add("page", fmt.Sprintf("%d", page))
	}
	if category != nil && *category != "All" && *category != "" {
		params.Add("categories[]", *category)
	}
	if subcategory != nil && *subcategory != "All" && *subcategory != "" {
		params.Add("subcategories[]", *subcategory)
	}
	if searchKeywords != nil && *searchKeywords != "" {
		params.Add("keywords", *searchKeywords)
	}

	targetURL := "https://search.niftyarchives.org/"
	if len(params) > 0 {
		targetURL += "?" + params.Encode()
	}

	client, err := getClient(proxyURL)
	if err != nil {
		return nil, err
	}

	resp, err := client.Get(targetURL)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	doc, err := goquery.NewDocumentFromReader(resp.Body)
	if err != nil {
		return nil, err
	}

	var summaries []StorySummary
	var current *StorySummary

	doc.Find("table.results tbody tr").Each(func(i int, s *goquery.Selection) {
		tdColspan2 := s.Find("td[colspan='2']")
		if tdColspan2.Length() > 0 {
			if current != nil {
				// Detail row (chapters or snippet)
				links := tdColspan2.Find("a")
				if links.Length() > 0 {
					links.Each(func(j int, l *goquery.Selection) {
						chapterTitle := strings.TrimSpace(l.Text())
						chapterURL, _ := l.Attr("href")
						if chapterTitle != "" && chapterURL != "" {
							if !strings.HasPrefix(chapterURL, "http") {
								chapterURL = "https://search.niftyarchives.org/" + strings.TrimPrefix(chapterURL, "/")
							}
							current.Chapters = append(current.Chapters, [2]string{chapterTitle, chapterURL})
						}
					})
				} else {
					html, _ := tdColspan2.Html()
					current.Snippet = &html
				}
			}
		} else {
			// Main row
			titleLink := s.Find("a[style*='font-weight: bold']")
			if titleLink.Length() > 0 {
				if current != nil {
					summaries = append(summaries, *current)
				}

				title := strings.TrimSpace(titleLink.Text())
				storyURL, _ := titleLink.Attr("href")
				if !strings.HasPrefix(storyURL, "http") {
					storyURL = "https://search.niftyarchives.org/" + strings.TrimPrefix(storyURL, "/")
				}

				var categories []string
				s.Find("span.label-success").Each(func(j int, c *goquery.Selection) {
					categories = append(categories, strings.TrimSpace(c.Text()))
				})

				var subcategories []string
				s.Find("span.label-info").Each(func(j int, c *goquery.Selection) {
					subcategories = append(subcategories, strings.TrimSpace(c.Text()))
				})

				dateAdded := ""
				s.Find("td[style*='text-align:right']").Each(func(j int, td *goquery.Selection) {
					dateAdded = strings.TrimSpace(td.Text())
				})

				current = &StorySummary{
					Title:         title,
					URL:           storyURL,
					Categories:    categories,
					Subcategories: subcategories,
					DateAdded:     dateAdded,
					Chapters:      [][2]string{},
				}
			}
		}
	})

	if current != nil {
		summaries = append(summaries, *current)
	}

	return summaries, nil
}

func LoadState() AppState {
	path := GetStoragePath()
	data, err := os.ReadFile(path)
	if err != nil {
		return AppState{
			Settings: Settings{
				Theme:    "dark",
				FontSize: 1.0,
			},
		}
	}

	var state AppState
	if err := json.Unmarshal(data, &state); err != nil {
		return AppState{
			Settings: Settings{
				Theme:    "dark",
				FontSize: 1.0,
			},
		}
	}
	return state
}

func SaveState(state AppState) error {
	data, err := json.Marshal(state)
	if err != nil {
		return err
	}
	return os.WriteFile(GetStoragePath(), data, 0644)
}
