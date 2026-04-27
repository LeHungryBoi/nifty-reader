package tts

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
)

// makeCacheDirectory returns the path to ~/.cache/pocket_tts
func makeCacheDirectory() (string, error) {
	home, err := os.UserHomeDir()
	if err != nil {
		return "", err
	}
	cacheDir := filepath.Join(home, ".cache", "pocket_tts")
	if err := os.MkdirAll(cacheDir, 0755); err != nil {
		return "", err
	}
	return cacheDir, nil
}

// DownloadIfNecessary mimics the Python download_if_necessary function.
// It supports HTTP/HTTPS URLs (caching by SHA256 of URL) and hf:// schemas.
func DownloadIfNecessary(filePath string) (string, error) {
	if strings.HasPrefix(filePath, "http://") || strings.HasPrefix(filePath, "https://") {
		cacheDir, err := makeCacheDirectory()
		if err != nil {
			return "", err
		}

		hash := sha256.Sum256([]byte(filePath))
		hashStr := hex.EncodeToString(hash[:])

		ext := filepath.Ext(filePath)
		if ext == "" {
			parts := strings.Split(filePath, ".")
			if len(parts) > 1 {
				ext = "." + parts[len(parts)-1]
			}
		}

		cachedFile := filepath.Join(cacheDir, hashStr+ext)

		if _, err := os.Stat(cachedFile); os.IsNotExist(err) {
			if err := downloadToFile(filePath, cachedFile); err != nil {
				return "", err
			}
		}
		return cachedFile, nil

	} else if strings.HasPrefix(filePath, "hf://") {
		// Example: hf://kyutai/pocket-tts-without-voice-cloning/languages/english/embeddings/alba.safetensors@d29db7978e464fb90cb3359ee0c69a273b9142cc
		trimmed := strings.TrimPrefix(filePath, "hf://")
		parts := strings.Split(trimmed, "/")
		if len(parts) < 3 {
			return "", fmt.Errorf("invalid hf:// URL format: %s", filePath)
		}

		repoID := parts[0] + "/" + parts[1]
		filename := strings.Join(parts[2:], "/")

		revision := "main"
		if strings.Contains(filename, "@") {
			fParts := strings.SplitN(filename, "@", 2)
			filename = fParts[0]
			revision = fParts[1]
		}

		return hfHubDownload(repoID, filename, revision)
	}

	return filePath, nil
}

func hfHubDownload(repoID, filename, revision string) (string, error) {
	cacheDir, err := makeCacheDirectory()
	if err != nil {
		return "", err
	}

	// Hugging Face resolve API
	url := fmt.Sprintf("https://huggingface.co/%s/resolve/%s/%s", repoID, revision, filename)

	hash := sha256.Sum256([]byte(url))
	hashStr := hex.EncodeToString(hash[:])
	ext := filepath.Ext(filename)
	cachedFile := filepath.Join(cacheDir, hashStr+ext)

	if _, err := os.Stat(cachedFile); os.IsNotExist(err) {
		if err := downloadToFile(url, cachedFile); err != nil {
			return "", err
		}
	}

	return cachedFile, nil
}

func downloadToFile(url, dest string) error {
	resp, err := http.Get(url)
	if err != nil {
		return fmt.Errorf("failed to GET %s: %v", url, err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("bad status: %s for %s", resp.Status, url)
	}

	tmpFile := dest + ".tmp"
	out, err := os.Create(tmpFile)
	if err != nil {
		return err
	}
	defer out.Close()

	if _, err := io.Copy(out, resp.Body); err != nil {
		os.Remove(tmpFile) // clean up on error
		return err
	}

	// Close before rename
	out.Close()
	return os.Rename(tmpFile, dest)
}
