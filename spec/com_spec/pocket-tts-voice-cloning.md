# Pocket-TTS Voice Cloning Technical Specification

This document details the technical implementation of voice cloning and voice state management in Kyutai Labs' `pocket-tts`.

## 1. Overview: The `.safetensors` Voice State

In `pocket-tts`, cloned voices are saved as `.safetensors` files. These files do not contain model weights, but rather the **Voice State** (or `model_state`) extracted from a reference audio prompt.

### What is a Voice State?
The voice state is a snapshot of the model's internal **KV (Key-Value) Cache** and **Offset** after it has processed a reference audio clip (encoded via the Mimi codec).
- **KV Cache**: The attention context that conditions the Transformer (FlowLM) to generate speech in the target voice.
- **Offset/Current End**: A pointer indicating the length of the prompt sequence in the cache.

### Benefits
- **Zero-Shot Cloning**: Allows cloning any voice from a short sample without fine-tuning weights.
- **Instant Loading**: Loading a `.safetensors` file is significantly faster than re-processing a `.wav` file, as it skips the Mimi encoding and initial Transformer forward pass.

## 2. File Structure

The `.safetensors` file stores a flat dictionary where keys represent the module hierarchy and tensor types.

### Internal Key Mapping
Keys are stored in the format: `{module_name}/{tensor_key}`.

| Storage Key | Internal Key | Description |
| :--- | :--- | :--- |
| `module/cache` | `cache` | The actual KV cache tensor. Shape: `[2, batch, length, heads, dim_head]`. |
| `module/current_end` | `offset` | The sequence length of the prompt. |

## 3. Implementation Details (Python)

### Exporting a Voice
The `export_model_state` function flattens the nested dictionary structure into a single level for `safetensors` compatibility.

```python
def export_model_state(model_state: dict[str, dict[str, torch.Tensor]], dest: str | Path):
    dict_to_store = {}
    for module_name, module_state in model_state.items():
        for key, tensor_value in module_state.items():
            dict_to_store[f"{module_name}/{key}"] = tensor_value
    safetensors.torch.save_file(dict_to_store, dest)
```

### Importing a Voice
The import process reconstructs the nested dictionary and handles the `current_end` to `offset` mapping.

```python
def _import_model_state(source: str | Path, device: torch.device):
    result = {}
    with safetensors.safe_open(source, framework="pt") as f:
        for key in f.keys():
            module_name, tensor_key = key.split("/")
            result.setdefault(module_name, {})
            if tensor_key == "current_end":
                tensor = f.get_tensor(key)
                result[module_name]["offset"] = torch.full(
                    (1,), fill_value=tensor.shape[0], dtype=torch.long, device=device
                )
            else:
                result[module_name][tensor_key] = f.get_tensor(key).to(device)
    return result
```

## 4. Voice Fusion Strategies

To combine multiple recordings or different voices into a single "fused" state:

### Method A: Audio Concatenation (Recommended)
Concatenate raw `.wav` samples into a single file (10s–30s total) and extract the state once. This ensures the model captures the full variance of the speaker.

### Method B: Tensor Averaging (Mathematical Fusion)
Average the KV cache tensors from multiple `.safetensors` files.
- **Limitation**: Requires all reference audios to have the **exact same length** so that the `sequence_length` dimension matches.
- **Formula**: $FusedCache = \frac{1}{N} \sum_{i=1}^{N} Cache_i$

## 5. Usage in Pocket-TTS

```python
from pocket_tts import TTSModel

model = TTSModel.load_model()
# Fast load from safetensors
voice_state = model.get_state_for_audio_prompt("path/to/voice.safetensors")
# Generate
audio = model.generate_audio(voice_state, "Hello, world!")
```
