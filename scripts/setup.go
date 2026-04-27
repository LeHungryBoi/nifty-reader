package main

import (
	"fmt"
	"io"
	"net/http"
	"os"
)

// This script downloads the necessary DLLs for sherpa-onnx on Windows.
// It mimics the behavior of the Rust build.rs.

const (
	baseURL = "https://github.com/k2-fsa/sherpa-onnx-go-windows/raw/master/lib/x86_64-pc-windows-gnu/"
)

var dlls = []string{
	"onnxruntime.dll",
	"sherpa-onnx-c-api.dll",
}

func main() {
	fmt.Println("Downloading sherpa-onnx DLLs for Windows...")

	for _, dll := range dlls {
		url := baseURL + dll
		fmt.Printf("Downloading %s...\n", dll)
		if err := downloadFile(dll, url); err != nil {
			fmt.Printf("Error downloading %s: %v\n", dll, err)
			continue
		}
		fmt.Printf("Successfully downloaded %s\n", dll)
	}

	fmt.Println("\nSetup complete! You can now run the app with 'go run main.go'.")
	fmt.Println("Make sure CGO_ENABLED=1 is set in your environment.")
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
