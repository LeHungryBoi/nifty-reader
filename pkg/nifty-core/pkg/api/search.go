package api

import (
	"fmt"
	"io"
	"net/url"
	"strings"

	"github.com/PuerkitoBio/goquery"
	"github.com/lehungryboi/nifty-reader/pkg/nifty-core/internal/models"
	"github.com/lehungryboi/nifty-reader/pkg/nifty-core/internal/utils"
)

// SearchOptions 搜索选项
type SearchOptions struct {
	Page        int
	Category    string // "All" 或空表示全部
	Subcategory string // "All" 或空表示全部
	SearchQuery string
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
		td := s.Find("td[colspan='2']")
		if td.Length() > 0 {
			if current == nil {
				return
			}
			// 尝试提取章节链接
			td.Find("a").Each(func(j int, a *goquery.Selection) {
				// 获取链接文本（可能包含 span 等子元素）
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
				}
			})
				// 检查是否真的有链接（有章节链接才是章节行，否则是摘要行）
			hasLinks := td.Find("a").Length() > 0
			if !hasLinks {
				html, _ := td.Html()
				current.Snippet = &html
			}
		} else {
			// 新故事行 - 保存前一个故事
			if current != nil {
				summaries = append(summaries, *current)
			}
			link := s.Find("td").First().Find("a[style*='font-weight: bold']").First()
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
			dateAdded := strings.TrimSpace(s.Find("td").Last().Text())
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
