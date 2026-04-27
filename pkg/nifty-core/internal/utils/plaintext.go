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
	reDate    = regexp.MustCompile(`(?im)^Date:.*$`)
	reFrom    = regexp.MustCompile(`(?im)^From:.*$`)
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
		if len(p) > 2 {
			paragraphs = append(paragraphs, p)
		}
	}
	return paragraphs
}
