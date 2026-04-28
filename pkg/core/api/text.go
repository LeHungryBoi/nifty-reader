package api

import (
	"fmt"
	"regexp"
	"strings"
)

var (
	reWordWrap  = regexp.MustCompile(`(\S)\n(\S)`)
	reSpaces    = regexp.MustCompile(` {2,}`)
	reSupport   = regexp.MustCompile(`(?i)please support the nifty archive[^\n]*`)
	reDate      = regexp.MustCompile(`(?im)^Date:.*$`)
	reFrom      = regexp.MustCompile(`(?im)^From:.*$`)
	reSubject   = regexp.MustCompile(`(?im)^Subject:.*$`)
	reParaBreak = regexp.MustCompile(`\n{2,}`)
)

// parsePlainTextStory 解析纯文本故事内容
func parsePlainTextStory(text string) []string {
	cleaned := reWordWrap.ReplaceAllString(text, "$1 $2")
	cleaned = reSpaces.ReplaceAllString(cleaned, " ")
	cleaned = reSupport.ReplaceAllString(cleaned, "")
	cleaned = reDate.ReplaceAllString(cleaned, "")
	cleaned = reFrom.ReplaceAllString(cleaned, "")
	cleaned = reSubject.ReplaceAllString(cleaned, "")
	blocks := reParaBreak.Split(cleaned, -1)
	var paragraphs []string
	for _, block := range blocks {
		p := strings.ReplaceAll(block, "\n", " ")
		p = strings.TrimSpace(p)
		if len(p) > 2 {
			paragraphs = append(paragraphs, p)
		}
	}
	return paragraphs
}

// urlEncode 对字符串进行 URL 编码 (application/x-www-form-urlencoded)
func urlEncode(s string) string {
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

// guessTitleFromURL 从 URL 路径猜测可读标题
func guessTitleFromURL(rawURL string) string {
	parts := strings.Split(rawURL, "/")
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
	words := strings.Fields(title)
	for i, word := range words {
		if len(word) > 0 {
			words[i] = strings.ToUpper(word[:1]) + strings.ToLower(word[1:])
		}
	}
	return strings.Join(words, " ")
}
