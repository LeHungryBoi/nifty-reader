package storage

import (
	"os"
	"path/filepath"
)

// ExeDir returns the directory containing the executable.
func ExeDir() string {
	exePath, err := os.Executable()
	if err != nil {
		return "."
	}
	return filepath.Dir(exePath)
}

// ModelPath returns a path under <exe_dir>/model/...
func ModelPath(parts ...string) string {
	p := append([]string{ExeDir(), "model"}, parts...)
	return filepath.Join(p...)
}

// AssetPath returns a path under <exe_dir>/assets/...
func AssetPath(parts ...string) string {
	p := append([]string{ExeDir(), "assets"}, parts...)
	return filepath.Join(p...)
}

// CachePath returns the cache directory <exe_dir>/cache, creating it if needed.
func CachePath() (string, error) {
	dir := filepath.Join(ExeDir(), "cache")
	if err := os.MkdirAll(dir, 0755); err != nil {
		return "", err
	}
	return dir, nil
}

// StoragePath returns the path to state.json in the exe directory.
func StoragePath() string {
	return filepath.Join(ExeDir(), "state.json")
}
