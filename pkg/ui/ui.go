package niftyui

import (
	"fmt"
	"time"

	"fyne.io/fyne/v2"
	"fyne.io/fyne/v2/canvas"
	"fyne.io/fyne/v2/container"
	"fyne.io/fyne/v2/layout"
	"fyne.io/fyne/v2/theme"
	"fyne.io/fyne/v2/widget"

	"github.com/lehungryboi/nifty-reader/pkg/core"
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

	searchBox := container.NewGridWrap(fyne.NewSize(250, 35), searchEntry)

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

func (na *NiftyApp) showError(err error) {
	fyne.Do(func() {
		label := widget.NewLabel(fmt.Sprintf("Error: %v", err))
		label.Wrapping = fyne.TextWrapWord
		na.content.Objects = []fyne.CanvasObject{
			container.NewPadded(label),
		}
		na.content.Refresh()
	})
}

func (na *NiftyApp) addToHistory(title, url string) {
	for i, item := range na.state.History {
		if item.URL == url {
			na.state.History = append(na.state.History[:i], na.state.History[i+1:]...)
			break
		}
	}

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
