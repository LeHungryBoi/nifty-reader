# CALM / Pocket TTS 论文参考

> **论文标题:** Continuous Audio Language Models
> **作者:** Simon Rouard, Manu Orsini, Axel Roebel, Neil Zeghidour, Alexandre Défossez (Kyutai / IRCAM-CNRS Sorbonne Univ.)
> **arXiv:** https://arxiv.org/abs/2509.06926v3
> **代码:** https://github.com/kyutai-labs/pocket-tts
> **样本页:** iclr-continuous-audio-language-models.github.io

---

## 1. 核心思想

传统音频语言模型（ALM）使用 **RVQ 离散 token** 表示音频，需要在 **码本深度**（质量）和 **计算成本** 之间做取舍。

CALM（Continuous Audio Language Model）改用 **VAE 连续潜空间** 直接建模，避免有损量化：
- 仅需 **1 步一致性模型（Consistency Model）** 即可生成高质量音频
- 在相同计算预算下，质量优于离散 token 模型
- 采样头推理速度比 RQ-Transformer 快 **×12（语音）/ ×20（音乐）**

---

## 2. 整体架构

CALM 由三个核心组件构成：

```
输入序列 (x^1, ..., x^S) ─ VAE 编码器 ─→ 连续潜变量序列

┌─────────────────────────────┐
│  1. Causal Backbone Transformer │  ← 长期依赖，带噪声注入
│     T_long: 产生 z_long^s        │
├─────────────────────────────┤
│  2. Short-Context Transformer   │  ← 近期精细上下文（干净潜变量）
│     T_short: 产生 z_short^s      │
├─────────────────────────────┤
│  3. Consistency Model Head     │  ← MLP，1步生成
│     f_φ: 输入噪声 → 输出 x^s    │
└─────────────────────────────┘
```

### 2.1 Causal Backbone Transformer（长期上下文 + 噪声注入）

- 输入潜变量在训练时加入噪声：`x̃^s = √(k_s) · ε + √(1-k_s) · x^s`，其中 `k_s ~ U(0,1)`, `ε ~ N(0,I)`
- **目的**：使模型对推理时的误差累积具有鲁棒性
- 推理时不注入噪声

### 2.2 Short-Context Transformer（短期上下文）

- 轻量因果 Transformer，关注最近 **K=10 个干净潜变量**（约 0.4s 音乐）
- 提供噪声注入后可能丢失的局部精细信息
- 消融实验证明这是 **关键组件**（去除后 FAD 从 0.93 暴增到 4.03）

### 2.3 Consistency Model Head（一致性模型头）

- 输入条件：`Z^s = z_long^s + z_short^s`
- 推理时 1 步采样：`ε ~ N(0,I), t=1, x̂^s = f_φ(x^s_1=ε, t=1, Z^s)`
- 基于 Lu & Song (2025) 的连续时间一致性损失函数训练

---

## 3. 关键创新

| 创新 | 说明 | 效果 |
|------|------|------|
| **噪声 + 短期上下文组合** | 长期上下文加噪防误差累积，短期上下文保留局部细节 | 音乐生成质量大幅提升 |
| **Diffusion → Consistency** | 用一致性模型替换扩散模型头 | 推理加速 ×12~×20 |
| **Gaussian Temperature Sampling** | 将标准差乘以 `√τ` 来控制温度 | 与离散模型的温度采样效果类似 |
| **Head Batch Multiplier** | 每个 backbone 输出复用 N 次训练（不同噪声级别） | 加速收敛、更好性能 |
| **Latent CFG** | Classifier Free Guidance 应用在潜变量 `Z^s` 上 | 提升有条件生成质量 |
| **Latent Distillation** | 将 CFG 教师模型的 backbone 蒸馏到更小的学生模型 | Pocket TTS: 24层→6层 |

---

## 4. VAE-GAN 编码器

基于 Mimi codec 架构，用 VAE 瓶颈替换 RVQ：
- **语音 VAE**: 32 维潜变量，12.5 Hz 帧率，WavLM 语义蒸馏
- **音乐 VAE**: 128 维潜变量，25 Hz 帧率，无语义蒸馏

| 模型 | 维度/层级 | 帧率 | MOSNet | ABX | PESQ |
|------|-----------|------|--------|-----|------|
| VQ-VAE (Mimi) | 8 RVQ | 12.5 Hz | 3.11 | 9.4% | 2.13 |
| **VAE (ours)** | **32 dims** | **12.5 Hz** | **3.15** | **8.1%** | **2.42** |

---

## 5. Pocket TTS 具体细节

### 5.1 模型规格

| 组件 | 参数 |
|------|------|
| 总参数量 | ~100M（含 VAE 解码器 20M） |
| Backbone Transformer | 6 层（从 24 层教师蒸馏） |
| 模型维度 | 1024 |
| MLP 维度 | 4096 |
| 注意力头数 | 16 |
| 采样头（MLP） | 6 层, SiLU 门控, 512 维 |
| 文本分词 | SentencePiece，4k 词表 |
| CFG 系数 | α = 1.5（仅对文本） |
| 训练数据 | 88k 小时语音（多数据集混合） |

### 5.2 性能对比（LibriSpeech test-clean）

| 模型 | 参数量 | WER | 音质 (ELO) | 说话人相似度 (ELO) | CPU 实时 |
|------|--------|-----|-----------|-------------------|----------|
| F5-TTS | 336M | 2.21 | 1949 | 1946 | ✗ |
| DSM | 750M | 1.84 | 1959 | 2037 | ✗ |
| Chatterbox Turbo | 350M | 3.24 | 2055 | 2012 | ✗ |
| Kokoro | 82M | 1.93 | — | — | ✓（无声音克隆）|
| **Pocket TTS** | **100M** | **1.84** | **2016** | **1898** | **✓** |

### 5.3 训练配置

| 参数 | 值 |
|------|------|
| 训练 GPU | 8×H100 |
| 训练步数 | 400K |
| 学习率 | 1e-4（cosine schedule） |
| 批大小 | 128 |
| 音频长度 | 60s |
| Head Batch Multiplier | 8 |
| 优化器 | AdamW (β₁=0.9, β₂=0.95) |
| 采样温度 | 0.7（`τ·N(0,I)`）|

### 5.4 推理流程

```
文本输入 → SentencePiece 分词 → 前缀拼接
                                      ↓
                              Backbone Transformer (6层)
                                      ↓
                              z_long^s（长期上下文）
                                      ↓
                        Z^s = z_long^s (无 short-context)
                                      ↓
                        Latent CFG: Z_CFG = Z_∅ + 1.5·(Z_C - Z_∅)
                                      ↓
                        Consistency Head (MLP, 1步)
                                      ↓
                            连续潜变量 x̂^s
                                      ↓
                            VAE Decoder → 音频波形
```

> 注：Pocket TTS 的学生模型在推理时 **不需要 short-context transformer**，因为教师模型的 CFG 效果已经被蒸馏到 backbone 中。

---

## 6. 与 Nifty Reader 项目的关联

### 6.1 当前实现路径
Nifty Reader 使用 **sherpa-onnx** 的 Pocket TTS ONNX 导出模型进行推理，模型文件为：
- `lm_flow.int8.onnx` — 一致性模型头（对应论文 Consistency Head MLP）
- `lm_main.int8.onnx` — Backbone Transformer（对应论文 6 层学生模型）
- `encoder.onnx` — 文本编码器
- `decoder.int8.onnx` — VAE 解码器（对应论文 VAE-GAN Decoder）
- `text_conditioner.onnx` — 文本条件化模块

### 6.2 声音克隆对应关系
| 论文概念 | sherpa-onnx 实现 |
|----------|-----------------|
| Audio Prompt → Mimi VAE Encoder → Backbone → KV Cache | `reference_audio` → `encoder.onnx` → `lm_main.int8.onnx` |
| Voice State (KV Cache + Offset) | `voice_embedding_cache_capacity` 缓存机制 |
| Latent CFG | 内置于 int8 量化模型 |
| 1-step Consistency Sampling | `lm_flow.int8.onnx` 单步推理 |

### 6.3 关键工程参数
- **参考音频预处理**: 单声道、24kHz、音量归一、去静音噪声
- **Voice State 格式**: sherpa-onnx 内部缓存，不再需要手动导出 safetensors
- **量化**: 训练模型为 fp32，推理使用 int8 量化模型

---

## 7. 参考文献

| 引用 | 说明 |
|------|------|
| Li et al. (2024) MAR | 连续自回归建模基础框架 |
| Lu & Song (2025) | 连续时间一致性模型 |
| Boffi et al. (2025) LSD | Lagrangian Self-Distillation，1步流匹配 |
| Défossez et al. (2024b) Mimi | 基础 codec 架构 |
| Pasini et al. (2024b) | 噪声增强防止误差累积 |
| Ho & Salimans (2022) | Classifier Free Guidance |
| SoundReactor (Saito et al. 2025) | Latent CFG 概念来源 |

---

*文档生成于 2026-04-29，基于 arxiv:2509.06926v3 论文内容整理。*
