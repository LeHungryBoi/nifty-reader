package snippet

import (
	"regexp"
	"strings"
)

// SnippetSegment represents a segment of a snippet with styling info
type SnippetSegment struct {
	Text        string
	IsHighlight bool
}

// ParseSnippetHTML parses HTML snippet with <em class="highlight"> tags and returns styled segments
// Returns a slice of SnippetSegment that can be used to build rich text
func ParseSnippetHTML(html string) []SnippetSegment {
	if html == "" {
		return []SnippetSegment{}
	}

	// Find all <em class="highlight">...</em> tags
	var segments []SnippetSegment
	pattern := regexp.MustCompile(`<em\s+class="highlight">([^<]*)</em>`)

	lastIndex := 0
	matches := pattern.FindAllStringSubmatchIndex(html, -1)

	for _, match := range matches {
		// match[0] = start of <em>, match[1] = end of </em>
		// match[2] = start of captured text, match[3] = end of captured text

		// Add text before the highlight
		if match[0] > lastIndex {
			plainText := html[lastIndex:match[0]]
			plainText = cleanHTML(plainText)
			if plainText != "" {
				segments = append(segments, SnippetSegment{
					Text:        plainText,
					IsHighlight: false,
				})
			}
		}

		// Add highlighted text
		highlightedText := html[match[2]:match[3]]
		highlightedText = cleanHTML(highlightedText)
		if highlightedText != "" {
			segments = append(segments, SnippetSegment{
				Text:        highlightedText,
				IsHighlight: true,
			})
		}

		lastIndex = match[1]
	}

	// Add remaining text after last match
	if lastIndex < len(html) {
		plainText := html[lastIndex:]
		plainText = cleanHTML(plainText)
		if plainText != "" {
			segments = append(segments, SnippetSegment{
				Text:        plainText,
				IsHighlight: false,
			})
		}
	}

	return segments
}

// FormatSnippetAsText formats snippet segments as a display string
// Highlighted text is wrapped with asterisks for emphasis
func FormatSnippetAsText(segments []SnippetSegment) string {
	var result strings.Builder
	for i, seg := range segments {
		if i > 0 {
			result.WriteString(" ")
		}
		if seg.IsHighlight {
			result.WriteString("*" + seg.Text + "*")
		} else {
			result.WriteString(seg.Text)
		}
	}
	return result.String()
}

// cleanHTML removes HTML tags and decodes HTML entities
func cleanHTML(text string) string {
	// Remove common HTML tags (but keep em highlight tags for later processing)
	text = regexp.MustCompile(`<[^>]*>`).ReplaceAllString(text, "")

	// Decode common HTML entities
	text = strings.NewReplacer(
		"&nbsp;", " ",
		"&lt;", "<",
		"&gt;", ">",
		"&amp;", "&",
		"&quot;", "\"",
		"&#39;", "'",
		"&apos;", "'",
	).Replace(text)

	// Clean up excessive whitespace
	text = strings.TrimSpace(text)

	return text
}
