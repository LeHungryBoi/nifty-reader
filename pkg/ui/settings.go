package niftyui

import (
	"fyne.io/fyne/v2"
	"fyne.io/fyne/v2/container"
	"fyne.io/fyne/v2/layout"
	"fyne.io/fyne/v2/theme"
	"fyne.io/fyne/v2/widget"

	"github.com/lehungryboi/nifty-reader/pkg/core"
	"github.com/lehungryboi/nifty-reader/pkg/tts"
)

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
				fyne.Do(func() {
					progressBar.SetValue(p)
					statusLabel.SetText(msg)
				})
			})

			fyne.Do(func() {
				downloadBtn.Enable()
				if err != nil {
					statusLabel.SetText("❌ " + err.Error())
				} else {
					statusLabel.SetText("✅ 下载完成")
					progressBar.Hide()
					updateModelStatus()
				}
			})
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
