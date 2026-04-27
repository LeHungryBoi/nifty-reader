package storage

import (
	"encoding/json"
	"os"
	"path/filepath"

	"github.com/adrg/xdg"
	"github.com/lehungryboi/nifty-reader/pkg/nifty-core/internal/models"
)

// StateManager 管理应用状态持久化
type StateManager struct {
	statePath string
}

// NewStateManager 创建状态管理器
func NewStateManager() *StateManager {
	configDir := filepath.Join(xdg.ConfigHome, "niftyreader")
	// 确保目录存在
	os.MkdirAll(configDir, 0755)
	return &StateManager{
		statePath: filepath.Join(configDir, "state.json"),
	}
}

// LoadState 加载应用状态
func (sm *StateManager) LoadState() models.AppState {
	data, err := os.ReadFile(sm.statePath)
	if err != nil {
		return models.DefaultAppState()
	}
	var state models.AppState
	if err := json.Unmarshal(data, &state); err != nil {
		return models.DefaultAppState()
	}
	return state
}

// SaveState 保存应用状态
func (sm *StateManager) SaveState(state *models.AppState) error {
	data, err := json.Marshal(state)
	if err != nil {
		return err
	}
	return os.WriteFile(sm.statePath, data, 0644)
}
