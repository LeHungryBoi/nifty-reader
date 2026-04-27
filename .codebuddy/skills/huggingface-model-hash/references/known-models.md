# Known Pocket-TTS Models

## English Models

| Folder Name | Raw URL | Known Hash |
|-------------|---------|------------|
| `english_2026-04` | `/languages/english_2026-04/model.safetensors` | `a0ac5076` |

## How to Check for Updates

1. Visit https://huggingface.co/kyutai/pocket-tts/tree/main/languages
2. Look for folders matching `english_*` pattern
3. For each folder, click on `model.safetensors`
4. Click "Raw pointer file" button
5. Get first 8 characters of hash for the `variant` field

## Config File Format (english.yaml)

```yaml
flow_lm:
  type: flowmatching
  variant: a0ac5076  # First 8 chars of model hash
  dim: 1024
  num_heads: 16
  num_layers: 24
  time_scale: 256
```
