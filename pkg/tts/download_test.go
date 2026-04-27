package tts

import (
	"os"
	"strings"
	"testing"
)

func TestDownloadIfNecessary_HF(t *testing.T) {
	// Test downloading a small file from Hugging Face hub
	hfURL := "hf://kyutai/pocket-tts-without-voice-cloning/README.md"
	
	cachedPath, err := DownloadIfNecessary(hfURL)
	if err != nil {
		t.Fatalf("DownloadIfNecessary failed: %v", err)
	}
	
	if _, err := os.Stat(cachedPath); os.IsNotExist(err) {
		t.Fatalf("File was not downloaded or cached at expected location: %s", cachedPath)
	}
	
	// Verify content
	content, err := os.ReadFile(cachedPath)
	if err != nil {
		t.Fatalf("Failed to read cached file: %v", err)
	}
	
	if !strings.Contains(string(content), "Pocket") {
		t.Errorf("Unexpected content in downloaded file: %s", string(content[:100]))
	}
}

func TestDownloadIfNecessary_HTTP(t *testing.T) {
	// Test standard HTTP download
	httpURL := "https://raw.githubusercontent.com/kyutai-labs/pocket-tts/main/README.md"
	
	cachedPath, err := DownloadIfNecessary(httpURL)
	if err != nil {
		t.Fatalf("DownloadIfNecessary failed for HTTP: %v", err)
	}
	
	if _, err := os.Stat(cachedPath); os.IsNotExist(err) {
		t.Fatalf("File was not downloaded or cached at expected location: %s", cachedPath)
	}
	
	// Verify content
	content, err := os.ReadFile(cachedPath)
	if err != nil {
		t.Fatalf("Failed to read cached file: %v", err)
	}
	
	if !strings.Contains(string(content), "Pocket") {
		t.Errorf("Unexpected content in downloaded file")
	}
}
