package main

import (
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
)

// This script downloads the necessary DLLs for sherpa-onnx on Windows.
// DLLs are saved to the lib/ directory.

const (
	baseURL = "https://github.com/k2-fsa/sherpa-onnx-go-windows/raw/master/lib/x86_64-pc-windows-gnu/"
)

var dlls = []string{
	"onnxruntime.dll",
	"sherpa-onnx-c-api.dll",
	"sherpa-onnx-cxx-api.dll",
}

func main() {
	// Create lib directory if it doesn't exist
	libDir := "lib"
	if err := os.MkdirAll(libDir, 0755); err != nil {
		fmt.Printf("Error creating lib directory: %v\n", err)
		os.Exit(1)
	}

	fmt.Println("Downloading sherpa-onnx DLLs for Windows...")

	for _, dll := range dlls {
		url := baseURL + dll
		destPath := filepath.Join(libDir, dll)
		fmt.Printf("Downloading %s...\n", dll)
		if err := downloadFile(destPath, url); err != nil {
			fmt.Printf("Error downloading %s: %v\n", dll, err)
			continue
		}
		fmt.Printf("Successfully downloaded %s to %s\n", dll, destPath)
	}

	fmt.Println("\nSetup complete! DLLs are in the lib/ directory.")
	fmt.Println("Run 'build.bat' to compile the app (DLLs will be copied to build/win/).")
}

func downloadFile(filepath string, url string) error {
	resp, err := http.Get(url)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("bad status: %s", resp.Status)
	}

	out, err := os.Create(filepath)
	if err != nil {
		return err
	}
	defer out.Close()

	_, err = io.Copy(out, resp.Body)
	return err
}
