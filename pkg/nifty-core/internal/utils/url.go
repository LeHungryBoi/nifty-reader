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
