package core

import (
	"encoding/json"
	"os"
	"path/filepath"

	"github.com/adrg/xdg"
	"github.com/lehungryboi/nifty-reader/pkg/core/models"
)

// Type aliases for convenient access
type (
	AppState    = models.AppState
	Settings    = models.Settings
	HistoryItem = models.HistoryItem
)

func getStoragePath() string {
	configDir := filepath.Join(xdg.ConfigHome, "niftyreader")
	os.MkdirAll(configDir, 0755)
	return filepath.Join(configDir, "state.json")
}

// LoadState 加载应用状态，失败时返回默认值
func LoadState() AppState {
	data, err := os.ReadFile(getStoragePath())
	if err != nil {
		return models.DefaultAppState()
	}
	var state AppState
	if err := json.Unmarshal(data, &state); err != nil {
		return models.DefaultAppState()
	}
	return state
}

// SaveState 保存应用状态到磁盘
func SaveState(state AppState) error {
	data, err := json.Marshal(state)
	if err != nil {
		return err
	}
	return os.WriteFile(getStoragePath(), data, 0644)
}
