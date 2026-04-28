package tts

import (
	"encoding/binary"
	"fmt"
	"io"
	"log"
	"math"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"
	"sync/atomic"

	"github.com/ebitengine/oto/v3"
	"github.com/lehungryboi/nifty-reader/pkg/core/storage"
	sherpa "github.com/k2-fsa/sherpa-onnx-go/sherpa_onnx"
)

// Data Structures

type VoiceKind string

const (
	Predefined VoiceKind = "Predefined"
	Cached     VoiceKind = "Cached"
	Custom     VoiceKind = "Custom"
)

type VoiceInfo struct {
	Name string    `json:"name"`
	Kind VoiceKind `json:"kind"`
}

type SpeakOptions struct {
	ReferenceAudioPath string  // 用于 voice fusion 的参考音频路径
	ReferenceText      string  // 参考音频对应的文本（用于提升效果）
	Speed              float32 // 语速，默认 1.0
}

// PCM Buffer for streaming playback
type pcmBuffer struct {
	mu       sync.Mutex
	queue    [][]byte
	finished bool
	started  chan struct{} // closed on first callback
	once     sync.Once
}

func newPCMBuffer() *pcmBuffer {
	return &pcmBuffer{
		started: make(chan struct{}),
	}
}

func (b *pcmBuffer) Push(p []byte) {
	b.once.Do(func() {
		close(b.started)
	})

	b.mu.Lock()
	b.queue = append(b.queue, p)
	b.mu.Unlock()
}

func (b *pcmBuffer) Finish() {
	b.once.Do(func() {
		close(b.started)
	})

	b.mu.Lock()
	b.finished = true
	b.mu.Unlock()
}

type pcmReader struct {
	buf  *pcmBuffer
	done chan struct{}
	once sync.Once
}

func (r *pcmReader) Read(p []byte) (int, error) {
	<-r.buf.started

	r.buf.mu.Lock()
	defer r.buf.mu.Unlock()

	if len(r.buf.queue) > 0 {
		chunk := r.buf.queue[0]
		n := copy(p, chunk)

		if n == len(chunk) {
			r.buf.queue = r.buf.queue[1:]
		} else {
			r.buf.queue[0] = chunk[n:]
		}
		return n, nil
	}

	if r.buf.finished {
		r.once.Do(func() { close(r.done) })
		return 0, io.EOF
	}

	for i := range p {
		p[i] = 0
	}
	return len(p), nil
}

// Engine

var (
	engine     *Engine
	engineOnce sync.Once
)

type Engine struct {
	tts         *sherpa.OfflineTts
	otoCtx      *oto.Context
	stopFlag    atomic.Bool
	currentSink *oto.Player
	mu          sync.Mutex
}

func GetEngine() *Engine {
	engineOnce.Do(func() {
		engine = NewEngine()
	})
	return engine
}

const pocketTTSModelDir = "sherpa-onnx-pocket-tts-int8-2026-01-26"

func NewEngine() *Engine {
	// PocketTTS 模型配置
	modelDir := getModelPath(pocketTTSModelDir)
	config := sherpa.OfflineTtsConfig{
		Model: sherpa.OfflineTtsModelConfig{
			Pocket: sherpa.OfflineTtsPocketModelConfig{
				LmFlow:            filepath.Join(modelDir, "lm_flow.int8.onnx"),
				LmMain:            filepath.Join(modelDir, "lm_main.int8.onnx"),
				Encoder:           filepath.Join(modelDir, "encoder.onnx"),
				Decoder:           filepath.Join(modelDir, "decoder.int8.onnx"),
				TextConditioner:   filepath.Join(modelDir, "text_conditioner.onnx"),
				VocabJson:         filepath.Join(modelDir, "vocab.json"),
				TokenScoresJson:   filepath.Join(modelDir, "token_scores.json"),
				VoiceEmbeddingCacheCapacity: 50,
			},
			NumThreads: 2,
			Debug:      0,
			Provider:   "cpu",
		},
	}

	tts := sherpa.NewOfflineTts(&config)
	if tts == nil {
		log.Println("Warning: Failed to create sherpa-onnx TTS engine (models might be missing)")
		return &Engine{}
	}

	// Initialize Oto using the sample rate from the model
	otoCtx, ready, err := oto.NewContext(&oto.NewContextOptions{
		SampleRate:   tts.SampleRate(),
		ChannelCount: 1,
		Format:       oto.FormatSignedInt16LE,
	})
	if err != nil {
		log.Printf("Failed to create Oto context: %v", err)
		return &Engine{tts: tts}
	}
	<-ready

	return &Engine{
		tts:    tts,
		otoCtx: otoCtx,
	}
}

func getModelPath(parts ...string) string {
	return storage.ModelPath(parts...)
}

func getAssetPath(parts ...string) string {
	return storage.AssetPath(parts...)
}

// Public API

func (e *Engine) Speak(text string, voiceName string) error {
	return e.SpeakWithOptions(text, SpeakOptions{Speed: 1.0})
}

func (e *Engine) SpeakWithOptions(text string, opts SpeakOptions) error {
	if e.tts == nil {
		return fmt.Errorf("TTS engine not initialized")
	}
	e.Stop()
	e.stopFlag.Store(false)

	var refAudio []float32
	var refSampleRate int

	// Voice fusion: 加载参考音频
	if opts.ReferenceAudioPath != "" {
		wave := sherpa.ReadWave(opts.ReferenceAudioPath)
		refAudio = wave.Samples
		refSampleRate = int(wave.SampleRate)
	}

	speed := opts.Speed
	if speed <= 0 {
		speed = 1.0
	}

	cfg := sherpa.GenerationConfig{
		Speed:               speed,
		ReferenceAudio:      refAudio,
		ReferenceSampleRate: refSampleRate,
	}

	pcmBuf := newPCMBuffer()
	reader := &pcmReader{
		buf:  pcmBuf,
		done: make(chan struct{}),
	}

	e.mu.Lock()
	player := e.otoCtx.NewPlayer(reader)
	e.currentSink = player
	e.mu.Unlock()

	player.Play()

	go func() {
		defer func() {
			pcmBuf.Finish()
		}()

		// The callback will be invoked during TTS generation.
		e.tts.GenerateWithConfig(
			text,
			&cfg,
			func(samples []float32, progress float32) bool {
				if e.stopFlag.Load() {
					return false // abort generation
				}

				buf := make([]byte, len(samples)*2)
				for i, s := range samples {
					if s > 1 {
						s = 1
					} else if s < -1 {
						s = -1
					}
					v := int16(math.Round(float64(s * 32767)))
					binary.LittleEndian.PutUint16(buf[i*2:], uint16(v))
				}

				pcmBuf.Push(buf)
				return true
			},
		)
	}()

	return nil
}

func (e *Engine) Stop() {
	e.stopFlag.Store(true)
	e.mu.Lock()
	if e.currentSink != nil {
		e.currentSink.Close()
		e.currentSink = nil
	}
	e.mu.Unlock()
}

func (e *Engine) IsSpeaking() bool {
	e.mu.Lock()
	defer e.mu.Unlock()
	return e.currentSink != nil && e.currentSink.IsPlaying()
}

// Helpers

func resolveVoicePath(name string) (string, error) {
	customPath := getAssetPath("voices", name+".wav")
	if _, err := os.Stat(customPath); err == nil {
		return customPath, nil
	}
	return "", fmt.Errorf("voice %s not found", name)
}

func ListVoices() []VoiceInfo {
	var voices []VoiceInfo
	voices = append(voices, VoiceInfo{Name: "default", Kind: Predefined})
	files, _ := os.ReadDir(getAssetPath("voices"))
	for _, f := range files {
		if !f.IsDir() && strings.HasSuffix(f.Name(), ".wav") {
			voices = append(voices, VoiceInfo{
				Name: strings.TrimSuffix(f.Name(), ".wav"),
				Kind: Custom,
			})
		}
	}
	return voices
}

func DownloadVoice(name string) error {
	url := fmt.Sprintf("https://huggingface.co/k2-fsa/sherpa-onnx-tts-models/resolve/main/%s.onnx", name)
	outPath := getModelPath("voices", name+".onnx")

	cached, err := DownloadIfNecessary(url)
	if err != nil {
		return err
	}

	_ = os.MkdirAll(filepath.Dir(outPath), 0755)
	return copyFile(cached, outPath)
}

// IsModelReady 检查 PocketTTS 模型是否已下载
func IsModelReady() bool {
	modelDir := getModelPath(pocketTTSModelDir)
	required := []string{
		"lm_flow.int8.onnx",
		"lm_main.int8.onnx",
		"encoder.onnx",
		"decoder.int8.onnx",
		"text_conditioner.onnx",
		"vocab.json",
		"token_scores.json",
	}
	for _, f := range required {
		if _, err := os.Stat(filepath.Join(modelDir, f)); err != nil {
			return false
		}
	}
	return true
}

// DownloadModel 下载 PocketTTS 模型（tar.bz2）
func DownloadModel(progress func(float64, string)) error {
	modelURL := "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/sherpa-onnx-pocket-tts-int8-2026-01-26.tar.bz2"
	destDir := filepath.Dir(getModelPath(""))

	if progress != nil {
		progress(0, "正在下载模型...")
	}

	cached, err := DownloadIfNecessary(modelURL)
	if err != nil {
		return fmt.Errorf("下载失败: %w", err)
	}

	if progress != nil {
		progress(0.8, "正在解压...")
	}

	// 解压 tar.bz2
	extractPath := filepath.Join(destDir, "model")
	cmd := exec.Command("tar", "-xjf", cached, "-C", extractPath)
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("解压失败: %w", err)
	}

	if progress != nil {
		progress(1.0, "完成")
	}
	return nil
}

func copyFile(src, dst string) error {
	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()

	out, err := os.Create(dst)
	if err != nil {
		return err
	}
	defer out.Close()

	_, err = io.Copy(out, in)
	return err
}
