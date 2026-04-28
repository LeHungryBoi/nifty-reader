package models

// Settings 表示应用设置
type Settings struct {
	Theme    string  `json:"theme"`     // default: "dark"
	FontSize float32 `json:"font_size"` // default: 1.0
	ProxyURL *string `json:"proxy_url,omitempty"`
}

// AppState 表示完整的应用状态
type AppState struct {
	Settings Settings      `json:"settings"`
	History  []HistoryItem `json:"history"`
}

// DefaultSettings 返回默认设置
func DefaultSettings() Settings {
	return Settings{
		Theme:    "dark",
		FontSize: 1.0,
		ProxyURL: nil,
	}
}

// DefaultAppState 返回默认应用状态
func DefaultAppState() AppState {
	return AppState{
		Settings: DefaultSettings(),
		History:  []HistoryItem{},
	}
}
