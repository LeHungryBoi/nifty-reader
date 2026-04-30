package main

import (
	"flag"
	"image/color"
	"log"
	"os"
	"path/filepath"

	"fyne.io/fyne/v2"
	"fyne.io/fyne/v2/app"
	"fyne.io/fyne/v2/theme"
	niftyui "github.com/lehungryboi/nifty-reader/pkg/ui"
	"golang.org/x/image/font/opentype"
)

// customTheme 包装默认主题，覆盖字体以支持中文
type customTheme struct {
	defaultTheme fyne.Theme
	font         fyne.Resource
}

func (t *customTheme) Color(name fyne.ThemeColorName, variant fyne.ThemeVariant) color.Color {
	// Zesty color scheme — vibrant oranges, warm tones, energetic accents
	switch name {
	case theme.ColorNameBackground:
		return color.NRGBA{R: 30, G: 30, B: 30, A: 255}
	case theme.ColorNameForeground:
		return color.NRGBA{R: 255, G: 243, B: 230, A: 255}
	case theme.ColorNamePrimary:
		return color.NRGBA{R: 255, G: 107, B: 53, A: 255} // vivid orange
	case theme.ColorNameHover:
		return color.NRGBA{R: 255, G: 140, B: 66, A: 255}
	case theme.ColorNameFocus:
		return color.NRGBA{R: 255, G: 165, B: 0, A: 255} // golden
	case theme.ColorNameButton:
		return color.NRGBA{R: 255, G: 107, B: 53, A: 255}
	case theme.ColorNameDisabled:
		return color.NRGBA{R: 100, G: 90, B: 80, A: 180}
	case theme.ColorNameDisabledButton:
		return color.NRGBA{R: 80, G: 72, B: 65, A: 180}
	case theme.ColorNameInputBorder:
		return color.NRGBA{R: 255, G: 140, B: 66, A: 200}
	case theme.ColorNameInputBackground:
		return color.NRGBA{R: 45, G: 40, B: 38, A: 255}
	case theme.ColorNamePlaceHolder:
		return color.NRGBA{R: 180, G: 165, B: 150, A: 255}
	case theme.ColorNameSeparator:
		return color.NRGBA{R: 80, G: 70, B: 60, A: 255}
	case theme.ColorNameSuccess:
		return color.NRGBA{R: 124, G: 252, B: 0, A: 255} // chartreuse
	case theme.ColorNameWarning:
		return color.NRGBA{R: 255, G: 200, B: 0, A: 255} // bright yellow
	case theme.ColorNameError:
		return color.NRGBA{R: 255, G: 69, B: 58, A: 255} // coral red
	case theme.ColorNameScrollBar:
		return color.NRGBA{R: 255, G: 107, B: 53, A: 120}
	case theme.ColorNameShadow:
		return color.NRGBA{R: 0, G: 0, B: 0, A: 80}
	case theme.ColorNameHeaderBackground:
		return color.NRGBA{R: 40, G: 36, B: 34, A: 255}
	case theme.ColorNameHoverBackground:
		return color.NRGBA{R: 50, G: 45, B: 40, A: 255}
	case theme.ColorNameMenuBackground:
		return color.NRGBA{R: 40, G: 36, B: 34, A: 255}
	case theme.ColorNameOverlayBackground:
		return color.NRGBA{R: 20, G: 18, B: 16, A: 220}
	}
	if t.defaultTheme == nil {
		return theme.DefaultTheme().Color(name, variant)
	}
	return t.defaultTheme.Color(name, variant)
}

func (t *customTheme) Font(style fyne.TextStyle) fyne.Resource {
	if t.font != nil {
		return t.font
	}
	if t.defaultTheme == nil {
		return theme.DefaultTheme().Font(style)
	}
	return t.defaultTheme.Font(style)
}

func (t *customTheme) Icon(name fyne.ThemeIconName) fyne.Resource {
	if t.defaultTheme == nil {
		return theme.DefaultTheme().Icon(name)
	}
	return t.defaultTheme.Icon(name)
}

func (t *customTheme) Size(name fyne.ThemeSizeName) float32 {
	if t.defaultTheme == nil {
		return theme.DefaultTheme().Size(name)
	}
	return t.defaultTheme.Size(name)
}

// loadChineseFont 从系统加载支持中文的字体
func loadChineseFont() fyne.Resource {
	fontPaths := []string{
		`C:\Windows\Fonts\simhei.ttf`,
		`C:\Windows\Fonts\msyh.ttf`,
		`C:\Windows\Fonts\msyhl.ttc`,
		`C:\Windows\Fonts\arialuni.ttf`,
	}
	for _, path := range fontPaths {
		data, err := os.ReadFile(path)
		if err == nil && len(data) > 0 {
			// Skip files that are not valid single-face OpenType/TrueType fonts.
			// Some Windows TTC collections can trigger crashes in Fyne text measurement.
			if _, parseErr := opentype.Parse(data); parseErr != nil {
				continue
			}
			return fyne.NewStaticResource("chinese-font", data)
		}
	}
	return nil
}

func main() {
	// Parse command line flags
	debug := flag.Bool("debug", false, "Enable debug mode (logs to file)")
	flag.Parse()

	// Set up debug logging if requested
	if *debug {
		exePath, err := os.Executable()
		if err != nil {
			exePath = "."
		}
		logPath := filepath.Join(filepath.Dir(exePath), "debug.log")
		logFile, err := os.Create(logPath)
		if err == nil {
			log.SetOutput(logFile)
			log.SetFlags(log.LstdFlags | log.Lshortfile)
			log.Println("=== Debug mode enabled ===")
			defer logFile.Close()
		}
	}

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
