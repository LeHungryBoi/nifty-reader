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
	niftyui "github.com/lehungryboi/nifty-reader/pkg/nifty-ui"
	"golang.org/x/image/font/opentype"
)

// customTheme 包装默认主题，覆盖字体以支持中文
type customTheme struct {
	defaultTheme fyne.Theme
	font         fyne.Resource
}

func (t *customTheme) Color(name fyne.ThemeColorName, variant fyne.ThemeVariant) color.Color {
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
