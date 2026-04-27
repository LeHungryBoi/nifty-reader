package main

import (
	"image/color"
	"os"

	"fyne.io/fyne/v2"
	"fyne.io/fyne/v2/app"
	"fyne.io/fyne/v2/theme"
	niftyui "github.com/lehungryboi/nifty-reader/pkg/nifty-ui"
)

// customTheme 包装默认主题，覆盖字体以支持中文
type customTheme struct {
	defaultTheme fyne.Theme
	font         fyne.Resource
}

func (t *customTheme) Color(name fyne.ThemeColorName, variant fyne.ThemeVariant) color.Color {
	return t.defaultTheme.Color(name, variant)
}

func (t *customTheme) Font(style fyne.TextStyle) fyne.Resource {
	if t.font != nil {
		return t.font
	}
	return t.defaultTheme.Font(style)
}

func (t *customTheme) Icon(name fyne.ThemeIconName) fyne.Resource {
	return t.defaultTheme.Icon(name)
}

func (t *customTheme) Size(name fyne.ThemeSizeName) float32 {
	return t.defaultTheme.Size(name)
}

// loadChineseFont 从系统加载支持中文的字体
func loadChineseFont() fyne.Resource {
	fontPaths := []string{
		`C:\Windows\Fonts\msyh.ttc`,
		`C:\Windows\Fonts\simhei.ttf`,
		`C:\Windows\Fonts\simsun.ttc`,
		`C:\Windows\Fonts\msyhl.ttc`,
	}
	for _, path := range fontPaths {
		data, err := os.ReadFile(path)
		if err == nil {
			return fyne.NewStaticResource("chinese-font", data)
		}
	}
	return nil
}

func main() {
	a := app.NewWithID("com.lehungryboi.niftyreader")

	// 设置中文字体
	if font := loadChineseFont(); font != nil {
		a.Settings().SetTheme(&customTheme{
			defaultTheme: theme.DefaultTheme(),
			font:         font,
		})
	}

	w := a.NewWindow("Nifty Reader")
	w.Resize(fyne.NewSize(900, 700))

	na := niftyui.NewNiftyApp(w)
	na.InitUI()
	w.ShowAndRun()
}
