package niftyui

import (
	"fmt"
	"strings"
	"time"

	"fyne.io/fyne/v2"
	"fyne.io/fyne/v2/canvas"
	"fyne.io/fyne/v2/container"
	"fyne.io/fyne/v2/layout"
	"fyne.io/fyne/v2/theme"
	"fyne.io/fyne/v2/widget"

	"github.com/lehungryboi/nifty-reader/pkg/core"
	"github.com/lehungryboi/nifty-reader/pkg/nifty-core/pkg/utils"
	"github.com/lehungryboi/nifty-reader/pkg/nifty-core/pkg/api"
	"github.com/lehungryboi/nifty-reader/pkg/tts"
)

type NiftyApp struct {
	window  fyne.Window
	state   core.AppState
	content *fyne.Container
}

func NewNiftyApp(window fyne.Window) *NiftyApp {
	return &NiftyApp{
		window: window,
		state:  core.LoadState(),
	}
}

func (na *NiftyApp) InitUI() {
	na.content = container.NewStack()

	header := na.createHeader()

	na.showBrowse()

	mainLayout := container.NewBorder(header, nil, nil, nil, na.content)
	na.window.SetContent(mainLayout)
}

func (na *NiftyApp) createHeader() fyne.CanvasObject {
	title := widget.NewLabelWithStyle("Nifty Reader", fyne.TextAlignLeading, fyne.TextStyle{Bold: true})

	searchEntry := widget.NewEntry()
	searchEntry.SetPlaceHolder("Search stories...")
	searchEntry.OnSubmitted = func(q string) {
		na.showBrowseWithQuery(q)
	}
	searchEntry.ExtendBaseWidget(searchEntry)

	browseBtn := widget.NewButtonWithIcon("", theme.HomeIcon(), func() {
		na.showBrowse()
	})

	historyBtn := widget.NewButtonWithIcon("", theme.HistoryIcon(), func() {
		na.showHistory()
	})

	settingsBtn := widget.NewButtonWithIcon("", theme.SettingsIcon(), func() {
		na.showSettings()
	})

	// 限制搜索框宽度，用 Center 包裹让它不会无限拉伸
	searchBox := container.NewGridWrap(fyne.NewSize(250, 35), searchEntry)

	// 用 NewPadded 给标题加左边距，按钮之间用小型 spacer 分隔
	leftSpacer := canvas.NewRectangle(theme.BackgroundColor())
	leftSpacer.SetMinSize(fyne.NewSize(12, 0))
	btnSpacer := canvas.NewRectangle(theme.BackgroundColor())
	btnSpacer.SetMinSize(fyne.NewSize(6, 0))

	return container.NewHBox(
		leftSpacer,
		title,
		layout.NewSpacer(),
		searchBox,
		btnSpacer,
		browseBtn,
		btnSpacer,
		historyBtn,
		btnSpacer,
		settingsBtn,
		leftSpacer,
	)
}

// Views

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

		// Flatten stories: expand chapters into separate items
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

		// 创建列表，每个item是一个带padding的卡片样式容器
		list := widget.NewList(
			func() int { return len(items) },
			func() fyne.CanvasObject {
				title := widget.NewLabelWithStyle("", fyne.TextAlignLeading, fyne.TextStyle{Bold: true})
				meta := widget.NewLabelWithStyle("", fyne.TextAlignLeading, fyne.TextStyle{Italic: true})
				snippet := widget.NewLabel("")
				snippet.Wrapping = fyne.TextWrapWord

				inner := container.NewVBox(title, meta, snippet)
				// NewPadded 给内容加标准padding
				padded := container.NewPadded(inner)
				return padded
			},
			func(id widget.ListItemID, item fyne.CanvasObject) {
				it := items[id]
				padded := item.(*fyne.Container) // NewPadded 返回的容器
				// NewPadded 的内部结构：第一个子元素是内容
				inner := padded.Objects[0].(*fyne.Container)

				inner.Objects[0].(*widget.Label).SetText(it.title)
				inner.Objects[1].(*widget.Label).SetText(it.meta)

				snippetLabel := inner.Objects[2].(*widget.Label)
				if it.snippet != nil && *it.snippet != "" {
					segments := utils.ParseSnippetHTML(*it.snippet)
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

		na.content.Objects = []fyne.CanvasObject{list}
		na.content.Refresh()
	}()
}

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

		// 用 strings.Builder 替代 += 拼接
		var b strings.Builder
		for _, p := range story.Paragraphs {
			b.WriteString(p)
			b.WriteString("\n\n")
		}

		// 给正文加左右padding，阅读更舒适
		rich := widget.NewRichTextFromMarkdown(b.String())
		rich.Wrapping = fyne.TextWrapWord
		scroll := container.NewVScroll(rich)

		// 预先声明，让闭包可以捕获自身
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
					// Fyne v2 中 Refresh() 可安全在任意 goroutine 调用
					ttsBtn.SetText("朗读")
					ttsBtn.Refresh()
				}()
			}
		})

		na.addToHistory(story.Title, url)

		backBtn := widget.NewButtonWithIcon("返回", theme.NavigateBackIcon(), func() {
			na.showBrowse()
		})

		// 顶部按钮栏
		buttonBar := container.NewHBox(backBtn, ttsBtn)

		// 标题
		titleContainer := container.NewPadded(title)

		// 底部按钮
		bottomBtn := widget.NewButtonWithIcon("返回书库", theme.HomeIcon(), func() {
			na.showBrowse()
		})
		bottomContainer := container.NewCenter(bottomBtn)

		// 布局：顶部按钮 + 标题 + 滚动内容 + 底部按钮
		paddedScroll := container.NewPadded(scroll)

		na.content.Objects = []fyne.CanvasObject{
			container.NewBorder(
				container.NewVBox(buttonBar, titleContainer),
				bottomContainer, nil, nil,
				paddedScroll,
			),
		}
		na.content.Refresh()
	}()
}

func (na *NiftyApp) showHistory() {
	if len(na.state.History) == 0 {
		emptyLabel := widget.NewLabelWithStyle("暂无阅读历史", fyne.TextAlignCenter, fyne.TextStyle{Italic: true})
		na.content.Objects = []fyne.CanvasObject{container.NewCenter(emptyLabel)}
		na.content.Refresh()
		return
	}

	list := widget.NewList(
		func() int { return len(na.state.History) },
		func() fyne.CanvasObject {
			lbl := widget.NewLabelWithStyle("", fyne.TextAlignLeading, fyne.TextStyle{})
			return container.NewPadded(lbl)
		},
		func(id widget.ListItemID, item fyne.CanvasObject) {
			padded := item.(*fyne.Container)
			lbl := padded.Objects[0].(*widget.Label)
			lbl.SetText(na.state.History[id].Title)
		},
	)
	list.OnSelected = func(id widget.ListItemID) {
		na.readStory(na.state.History[id].URL)
	}

	na.content.Objects = []fyne.CanvasObject{list}
	na.content.Refresh()
}

func (na *NiftyApp) showSettings() {
	proxyEntry := widget.NewEntry()
	proxyEntry.SetPlaceHolder("如: socks5://127.0.0.1:7890")
	if na.state.Settings.ProxyURL != nil && *na.state.Settings.ProxyURL != "" {
		proxyEntry.SetText(*na.state.Settings.ProxyURL)
	}

	saveBtn := widget.NewButtonWithIcon("💾 保存", theme.ConfirmIcon(), func() {
		p := proxyEntry.Text
		na.state.Settings.ProxyURL = &p
		core.SaveState(na.state)
		fyne.CurrentApp().SendNotification(&fyne.Notification{
			Title:   "Nifty Reader",
			Content: "设置已保存",
		})
	})

	// 模型管理区域
	modelStatus := widget.NewLabel("")
	updateModelStatus := func() {
		if tts.IsModelReady() {
			modelStatus.SetText("✅ PocketTTS 模型已就绪")
		} else {
			modelStatus.SetText("❌ PocketTTS 模型未下载")
		}
	}
	updateModelStatus()

	progressBar := widget.NewProgressBar()
	progressBar.Hide()
	statusLabel := widget.NewLabel("")
	statusLabel.Hide()

	var downloadBtn *widget.Button
	downloadBtn = widget.NewButtonWithIcon("📥 下载模型", theme.DownloadIcon(), func() {
		downloadBtn.Disable()
		progressBar.Show()
		statusLabel.Show()

		go func() {
			err := tts.DownloadModel(func(p float64, msg string) {
				progressBar.SetValue(p)
				statusLabel.SetText(msg)
			})

			downloadBtn.Enable()
			if err != nil {
				statusLabel.SetText("❌ " + err.Error())
			} else {
				statusLabel.SetText("✅ 下载完成")
				progressBar.Hide()
				updateModelStatus()
			}
		}()
	})

	if tts.IsModelReady() {
		downloadBtn.Disable()
	}

	cancelBtn := widget.NewButtonWithIcon("🔙 返回", theme.NavigateBackIcon(), func() {
		na.showBrowse()
	})

	form := container.NewVBox(
		widget.NewLabelWithStyle("⚙️ 设置", fyne.TextAlignLeading, fyne.TextStyle{Bold: true}),
		widget.NewForm(
			widget.NewFormItem("代理地址", proxyEntry),
		),
		widget.NewSeparator(),
		widget.NewLabelWithStyle("🔊 TTS 模型", fyne.TextAlignLeading, fyne.TextStyle{Bold: true}),
		modelStatus,
		container.NewHBox(downloadBtn),
		progressBar,
		statusLabel,
		container.NewHBox(
			layout.NewSpacer(),
			cancelBtn,
			saveBtn,
		),
	)

	na.content.Objects = []fyne.CanvasObject{container.NewPadded(form)}
	na.content.Refresh()
}

func (na *NiftyApp) showError(err error) {
	label := widget.NewLabel(fmt.Sprintf("Error: %v", err))
	label.Wrapping = fyne.TextWrapWord
	na.content.Objects = []fyne.CanvasObject{
		container.NewPadded(label),
	}
	na.content.Refresh()
}

func (na *NiftyApp) addToHistory(title, url string) {
	// Remove if exists
	for i, item := range na.state.History {
		if item.URL == url {
			na.state.History = append(na.state.History[:i], na.state.History[i+1:]...)
			break
		}
	}

	// Add to front
	na.state.History = append([]core.HistoryItem{{
		Title:     title,
		URL:       url,
		Timestamp: uint64(time.Now().Unix()),
	}}, na.state.History...)

	if len(na.state.History) > 20 {
		na.state.History = na.state.History[:20]
	}

	core.SaveState(na.state)
}
