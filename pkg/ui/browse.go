package niftyui

import (
	"fmt"
	"strings"

	"fyne.io/fyne/v2"
	"fyne.io/fyne/v2/container"
	"fyne.io/fyne/v2/widget"

	"github.com/lehungryboi/nifty-reader/pkg/core/api"
	"github.com/lehungryboi/nifty-reader/pkg/core/snippet"
)

func (na *NiftyApp) showBrowse() {
	na.showBrowseWithQuery("")
}

func (na *NiftyApp) showBrowseWithQuery(query string) {
	loading := widget.NewProgressBarInfinite()
	na.content.Objects = []fyne.CanvasObject{container.NewCenter(loading)}
	na.content.Refresh()

	go func() {
		client := api.NewClient("")
		if na.state.Settings.ProxyURL != nil {
			client = api.NewClient(*na.state.Settings.ProxyURL)
		}
		stories, err := client.SearchStories(api.SearchOptions{
			Page:        1,
			SearchQuery: query,
		})
		if err != nil {
			na.showError(err)
			return
		}

		type browseItem struct {
			title   string
			url     string
			meta    string
			snippet *string
		}
		var items []browseItem
		for _, s := range stories {
			meta := fmt.Sprintf("%s | %v", s.DateAdded, s.Categories)
			if len(s.Chapters) > 0 {
				for _, ch := range s.Chapters {
					items = append(items, browseItem{
						title:   ch.Title,
						url:     ch.URL,
						meta:    meta,
						snippet: s.Snippet,
					})
				}
			} else {
				items = append(items, browseItem{
					title:   s.Title,
					url:     s.URL,
					meta:    meta,
					snippet: s.Snippet,
				})
			}
		}

		list := widget.NewList(
			func() int { return len(items) },
			func() fyne.CanvasObject {
				title := widget.NewLabelWithStyle("", fyne.TextAlignLeading, fyne.TextStyle{Bold: true})
				meta := widget.NewLabelWithStyle("", fyne.TextAlignLeading, fyne.TextStyle{Italic: true})
				snippet := widget.NewLabel("")
				snippet.Wrapping = fyne.TextWrapWord

				inner := container.NewVBox(title, meta, snippet)
				padded := container.NewPadded(inner)
				return padded
			},
			func(id widget.ListItemID, item fyne.CanvasObject) {
				it := items[id]
				padded := item.(*fyne.Container)
				inner := padded.Objects[0].(*fyne.Container)

				inner.Objects[0].(*widget.Label).SetText(it.title)
				inner.Objects[1].(*widget.Label).SetText(it.meta)

				snippetLabel := inner.Objects[2].(*widget.Label)
				if it.snippet != nil && *it.snippet != "" {
					segments := snippet.ParseSnippetHTML(*it.snippet)
					var displayText strings.Builder
					for _, seg := range segments {
						if seg.IsHighlight {
							displayText.WriteString("**")
							displayText.WriteString(seg.Text)
							displayText.WriteString("**")
						} else {
							displayText.WriteString(seg.Text)
						}
					}
					snippetLabel.SetText(displayText.String())
				} else {
					snippetLabel.SetText("")
				}
			},
		)

		list.OnSelected = func(id widget.ListItemID) {
			na.readStory(items[id].url)
			list.Unselect(id)
		}

		fyne.Do(func() {
			na.content.Objects = []fyne.CanvasObject{list}
			na.content.Refresh()
		})
	}()
}
