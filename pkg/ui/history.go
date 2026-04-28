package niftyui

import (
	"fyne.io/fyne/v2"
	"fyne.io/fyne/v2/container"
	"fyne.io/fyne/v2/widget"
)

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
