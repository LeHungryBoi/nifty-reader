package api

import (
	"fmt"
	"io"
	"net/http"
	"strings"

	"github.com/PuerkitoBio/goquery"
	"github.com/lehungryboi/nifty-reader/pkg/nifty-core/internal/models"
	"github.com/lehungryboi/nifty-reader/pkg/nifty-core/internal/utils"
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
	// 移除 footer：分割于 "please support" 并取前部分
	lowerText := strings.ToLower(text)
	if idx := strings.Index(lowerText, "please support"); idx != -1 {
		text = text[:idx]
	}
	return utils.ParsePlainTextStory(text)
}
