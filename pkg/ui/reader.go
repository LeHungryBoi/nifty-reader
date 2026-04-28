package niftyui

import (
	"strings"

	"fyne.io/fyne/v2"
	"fyne.io/fyne/v2/container"
	"fyne.io/fyne/v2/theme"
	"fyne.io/fyne/v2/widget"

	"github.com/lehungryboi/nifty-reader/pkg/core/api"
	"github.com/lehungryboi/nifty-reader/pkg/tts"
)

func (na *NiftyApp) readStory(url string) {
	loading := widget.NewProgressBarInfinite()
	na.content.Objects = []fyne.CanvasObject{container.NewCenter(loading)}
	na.content.Refresh()

	go func() {
		client := api.NewClient("")
		if na.state.Settings.ProxyURL != nil {
			client = api.NewClient(*na.state.Settings.ProxyURL)
		}
		story, err := client.FetchStory(url)
		if err != nil {
			na.showError(err)
			return
		}

		title := widget.NewLabelWithStyle(story.Title, fyne.TextAlignCenter, fyne.TextStyle{Bold: true})

		var b strings.Builder
		for _, p := range story.Paragraphs {
			b.WriteString(p)
			b.WriteString("\n\n")
		}

		rich := widget.NewRichTextFromMarkdown(b.String())
		rich.Wrapping = fyne.TextWrapWord
		scroll := container.NewVScroll(rich)

		var ttsBtn *widget.Button
		ttsBtn = widget.NewButtonWithIcon("朗读", theme.MediaPlayIcon(), func() {
			engine := tts.GetEngine()
			if engine.IsSpeaking() {
				engine.Stop()
				ttsBtn.SetText("朗读")
				ttsBtn.Refresh()
			} else {
				ttsBtn.SetText("停止")
				go func() {
					engine.Speak(strings.Join(story.Paragraphs, " "), "default")
					fyne.Do(func() {
						ttsBtn.SetText("朗读")
						ttsBtn.Refresh()
					})
				}()
			}
		})

		na.addToHistory(story.Title, url)

		backBtn := widget.NewButtonWithIcon("返回", theme.NavigateBackIcon(), func() {
			na.showBrowse()
		})

		buttonBar := container.NewHBox(backBtn, ttsBtn)
		titleContainer := container.NewPadded(title)

		bottomBtn := widget.NewButtonWithIcon("返回书库", theme.HomeIcon(), func() {
			na.showBrowse()
		})
		bottomContainer := container.NewCenter(bottomBtn)
		paddedScroll := container.NewPadded(scroll)

		fyne.Do(func() {
			na.content.Objects = []fyne.CanvasObject{
				container.NewBorder(
					container.NewVBox(buttonBar, titleContainer),
					bottomContainer, nil, nil,
					paddedScroll,
				),
			}
			na.content.Refresh()
		})
	}()
}
