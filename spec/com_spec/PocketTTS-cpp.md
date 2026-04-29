# PocketTTS.cpp — CGO 集成与 Voice Fusion 技术规范

> **Source:** [VolgaGerm/PocketTTS.cpp](https://github.com/VolgaGerm/PocketTTS.cpp)
> **替代 sherpa-onnx** 作为 TTS 推理引擎，通过 CGO FFI 从 Go 调用。

## 1. 概述

PocketTTS.cpp 是 PocketTTS 的纯 C++ ONNX 实现，提供：
- 独立的 Mimi encoder ONNX 模型
- 原生音频加载 (WAV/MP3/FLAC via dr_libs)，内部 resample + mono + normalize
- 两级磁盘缓存：`.emb` (encoder 输出) 和 `.kv` (transformer KV cache)
- **流式 C API** + HTTP server
- 单文件 `pocket_tts.cpp`，零框架依赖，仅依赖 ONNX Runtime + SentencePiece
- 9.2x 实时速度 (RTFx)，INT8 默认精度

## 2. ONNX 模型文件

INT8 模式 (默认) 需要 7 个文件：

| 文件 | 用途 |
|---|---|
| `mimi_encoder.onnx` | Mimi VAE encoder — 音频 → latent trajectory (FP32，无 int8 变体) |
| `flow_lm_main_int8.onnx` | FlowLM main transformer — voice + text conditioning (INT8) |
| `flow_lm_flow_int8.onnx` | FlowLM flow transformer — 自回归音频生成 (INT8) |
| `mimi_decoder_int8.onnx` | Mimi VAE decoder — latent → PCM 音频 (INT8) |
| `text_conditioner.onnx` | Text token conditioning (FP32，无 int8 变体) |
| `tokenizer.model` | SentencePiece tokenizer |

FP32 模式使用 `_int8` 后缀替换为非后缀版本 (如 `flow_lm_main.onnx`)。

## 3. `.emb` 文件格式 (Mimi Encoder Output)

`.emb` 存储 Mimi encoder 的原始输出，即 voice 的 **continuous latent trajectory**。

```
二进制布局:
[4B magic "EMB1"] [4B ndims=3] [3×8B shape: {1, C, T}] [N×4B float32 data]

其中:
- magic = 0x31424D45 (小端序 "EMB1")
- C = seanet channel dim (e.g. 8)
- T = time frames (12.5 Hz 帧率, 10s 音频 ≈ 125 帧)
- N = 1 × C × T
```

**这是 voice fusion 操作的目标数据**。融合在 `.emb` 级别进行 (KV cache 之前)，因为：
- 格式简单 (3D tensor)
- 是 transformer 处理前的原始 latent 数据
- 融合后的 tensor 直接传给 generate pipeline

**注意：C API 不暴露 `encode_voice`。** Voice 编码在 C++ 内部完成，Go 层通过读写 `.emb` 文件操作 embedding。

## 4. `.kv` 文件格式 (Transformer KV Cache)

`.kv` 存储 transformer 处理 `.emb` 后的 KV cache，用于**加速推理**（跳过 voice conditioning forward pass）。

```
[4B magic "KVC1"] [8B blob_size] [blob data]

blob 内部格式:
[4B current_buf] [4B num_states] 然后每个 state:
[4B ndims] [ndims×8B shape] [4B type_code] [8B data_bytes] [data]
```

Voice fusion **不需要**操作 `.kv`，只融合 `.emb`，然后删除对应的 `.kv` 让引擎重新生成。

## 5. Voice Fusion Protocol

### 5.1 定义

Voice State (`.emb`) 的本质是 **Continuous Latent Trajectory** — 一组在潜空间中随时间变化的坐标序列。

### 5.2 核心挑战: 维度对齐

Voice A 长度为 T_a，Voice B 长度为 T_b。矩阵形状不一致，无法直接加权求和。

### 5.3 实现逻辑 (Go 层)

```
步骤 1: 读取 .emb 文件
  二进制解析 → emb_A: [1, C, T_a], emb_B: [1, C, T_b]

步骤 2: 时间轴重采样 (Temporal Resampling)
  target_T = max(T_a, T_b)
  对最后一个维度 (T 轴) 做线性插值拉伸:
  - Aligned_A = resample_linear(emb_A, T_a → target_T)  // [1, C, target_T]
  - Aligned_B = resample_linear(emb_B, T_b → target_T)  // [1, C, target_T]

步骤 3: 向量插值 (Vector Mixing)
  Fused[i][j] = alpha * Aligned_A[i][j] + (1 - alpha) * Aligned_B[i][j]
  - alpha ∈ [0.0, 1.0]: 混合比例

步骤 4: 写入融合后 .emb 文件
  二进制序列化 → fused.emb

步骤 5: 删除对应的 .kv 缓存文件（如有）
  让引擎在下一次使用时重新计算 KV cache
```

### 5.4 为什么选择潜空间融合

- **避免波形干扰**: 不会像 PCM 混合那样产生双重人声叠加的物理波形干扰
- **平滑音色**: CALM 模型擅长处理连续向量，混合后的坐标代表两个音色特征的中间点
- **鲁棒性**: 模型训练时的噪声注入机制保证合成出来的"中间坐标"也能生成清晰人声

## 6. 实际 C API

### 6.1 函数签名

```c
// 创建实例
void* ptt_create(const char* models_dir, const char* voices_dir,
                 const char* tokenizer_path, const char* precision,
                 float temperature, int lsd_steps, int num_threads);
// 返回 handle，失败返回 nullptr

// 预热（生成一个短句子触发模型加载）
double ptt_warmup(void* handle);
// 返回耗时（秒），失败返回 -1

// 释放音频 buffer（由 ptt_stream_read 分配的）
void ptt_free_audio(float* samples);

// 销毁实例
void ptt_destroy(void* handle);

// ── 流式 API ────────────────────────────────────────────

// 启动流式生成（后台线程）
void* ptt_stream_start(void* handle, const char* text, const char* voice);
// voice: voices_dir 下的文件名 或 绝对路径 (WAV/MP3/FLAC)
// 返回 stream context，失败返回 nullptr

// 读取一个 chunk（阻塞直到有数据或流结束）
// 返回 1=有数据, 0=流结束, -1=错误
// *out_samples 需要调用方用 ptt_free_audio 释放
int ptt_stream_read(void* stream_ctx, float** out_samples, int* out_len);

// 结束流（等待后台线程退出，释放资源）
void ptt_stream_end(void* stream_ctx);
```

### 6.2 与 Spec 旧版的差异

| 旧版 Spec | 实际 |
|---|---|
| `ptt_create(config_json)` | `ptt_create(models_dir, voices_dir, tokenizer_path, precision, temperature, lsd_steps, num_threads)` |
| `ptt_encode_voice(handle, pcm, len, sr, &out_len)` | **不存在** — 内部自动编码，结果缓存在 `.emb` 文件 |
| `ptt_generate(handle, text, emb, emb_len, ...)` | **不存在** — 改用流式 API |
| 无流式 API | `ptt_stream_start/read/end` |
| 无 warmup | `ptt_warmup(handle)` |
| 无音频释放 | `ptt_free_audio(float*)` |

### 6.3 Go binding 设计

```go
// pkg/cgo/pocket_tts.go

package cgo

/*
#cgo CFLAGS: -I${SRCDIR}/../../lib/pocket_tts/include
#cgo windows LDFLAGS: -L${SRCDIR}/../../lib/pocket_tts -lpocket_tts
#cgo !windows LDFLAGS: -L${SRCDIR}/../../lib/pocket_tts -lpocket_tts -lstdc++ -lm
#include <stdlib.h>
#include "pocket_tts.h"
*/
import "C"
import "unsafe"

type Handle struct {
    h C.void  // 实际是 void*
}

type CreateConfig struct {
    ModelsDir     string
    VoicesDir     string
    TokenizerPath string
    Precision     string // "int8" 或 "fp32"
    Temperature   float32
    LSDSteps      int
    NumThreads    int
}

func Create(cfg CreateConfig) (*Handle, error) { ... }
func (h *Handle) Warmup() (float64, error) { ... }
func (h *Handle) StreamStart(text, voice string) (*StreamCtx, error) { ... }
func (h *Handle) Destroy() { ... }

type StreamCtx struct {
    ctx C.void  // 实际是 void*
}

func (s *StreamCtx) Read() ([]float32, error) { ... }
func (s *StreamCtx) End() { ... }
```

## 7. CGO 集成方案

### 7.1 构建

```batch
# 1. 编译 PocketTTS.cpp 共享库
git clone https://github.com/VolgaGerm/PocketTTS.cpp lib/pocket_tts/src
cd lib/pocket_tts/src
cmake -B build -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIB=ON
cmake --build build --config Release
# 产出: pocket_tts.dll + onnxruntime.dll

# 2. 复制到项目 lib 目录
copy build\Release\pocket_tts.dll ..\pocket_tts.dll
copy build\Release\onnxruntime.dll ..\onnxruntime.dll
copy pocket_tts.cpp ..\include\pocket_tts.h  (需从源码提取 C API 头文件)

# 3. 编译 Go 应用
cd ..\..\..
set CGO_ENABLED=1
go build -o nifty-reader.exe .
```

### 7.2 Windows 运行时依赖

`pocket_tts.dll` 依赖 `onnxruntime.dll`，两者必须与 exe 在同一目录或 PATH 中。

## 8. 数据流全景

```
录音/文件加载
    │
    ▼
( PocketTTS.cpp 内部: dr_libs 加载 → mono → resample 24kHz → normalize )
    │
    ▼
mimi_encoder.onnx ──► .emb (latent trajectory [1, C, T])  ← Go 层可读写
    │                        │
    │                   [Voice Fusion: Go 层对 .emb 做线性插值]
    │                        │
    ▼                        ▼
lm_main.onnx ◄──────── fused .emb (通过 voice 文件路径传入)
    │  (voice conditioning → KV cache 更新)
    ▼
text_conditioner.onnx ──► text embedding
    │
    ▼
lm_main.onnx ──► text conditioning pass
    │
    ▼
lm_flow.onnx ──► 自回归生成 audio latent tokens (流式)
    │
    ▼
mimi_decoder.onnx ──► PCM float32 chunks (流式)
    │
    ▼
Go 层接收 float32 PCM → int16 转换 → oto v3 播放
```

## 9. Voice Fusion 的 Go 层实现方案

由于 C API 不暴露 `encode_voice`，Voice Fusion 在 Go 层通过 `.emb` 文件操作完成：

### 9.1 `.emb` 文件读写 (`pkg/tts/embfile.go`)

```go
// EmbFile 表示一个 .emb 文件
type EmbFile struct {
    Shape []int64    // [1, C, T]
    Data  []float32  // C × T 个 float32
}

func ReadEmb(path string) (*EmbFile, error)
func WriteEmb(path string, emb *EmbFile) error
```

### 9.2 线性插值融合 (`pkg/tts/fusion.go`)

```go
// FuseEmbeddings 对两个 .emb 在时间轴上对齐后做线性插值
func FuseEmbeddings(a, b *EmbFile, alpha float32) (*EmbFile, error)
// 1. target_T = max(a.T, b.T)
// 2. 对 T 轴做线性插值重采样
// 3. 加权混合: result = alpha*a + (1-alpha)*b
```

### 9.3 使用流程

1. 用户选择 Voice A + Voice B + alpha
2. Go 层读取两个 `.emb` 文件
3. 执行 `FuseEmbeddings()`
4. 写入融合后的 `.emb` 到 `voices/` 目录
5. 删除对应的 `.kv` 缓存
6. 调用 `ptt_stream_start(handle, text, "fused_voice.wav")` 生成语音
   - **问题：** voice 参数期望的是音频文件路径，不是 `.emb` 文件
   - **解决方案：** 需要创建一个占位 WAV 文件指向 `.emb`，或者修改 C++ 源码支持 `.emb` 输入

### 9.4 Voice Fusion 的两种路径

**路径 A (推荐): 修改 C++ 源码**
- 在 `ptt_stream_start` 中增加对 `.emb` 文件的直接支持
- 当 voice 文件扩展名为 `.emb` 时，直接加载而非调用 encoder
- 修改量小，约 10 行代码

**路径 B (纯 Go): 占位文件**
- 融合后 `.emb` 写入 `voices/` 目录
- 创建同名 `.wav` 占位文件（空/极短）
- PocketTTS 内部会编码这个 WAV，但我们替换其 `.emb` 缓存
- 依赖缓存机制的时序，不够可靠

## 10. 参考规范

- PocketTTS.cpp 仓库：https://github.com/VolgaGerm/PocketTTS.cpp
- PocketTTS 官方 Python 实现：`spec/com_spec/pocket-tts/`
- 旧引擎参考（已弃用）：`spec/com_spec/sherpa-onnx/`
- CALM / PocketTTS 论文笔记：`spec/com_spec/CALM-PocketTTS-论文参考.md`
