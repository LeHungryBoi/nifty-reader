# HuggingFace Model Hash Finder Specification

## Purpose

Find the variant hash for pocket-tts models from HuggingFace. The hash is computed from the model weights and is used as the `variant` identifier in the config YAML file.

## Workflow

### Step 1: Open the HuggingFace Model Page

Model file URL format:
```
https://huggingface.co/kyutai/pocket-tts/blob/main/languages/{LANG}_{DATE}/model.safetensors
```

Example: `https://huggingface.co/kyutai/pocket-tts/blob/main/languages/english_2026-04/model.safetensors`

### Step 2: Find the "Raw Pointer File" Button

On the model file page, locate the "Raw pointer file" button (raw pointer 文件).

### Step 3: Get the Hash

Click the button to open the raw pointer file URL:
```
https://huggingface.co/kyutai/pocket-tts/raw/main/languages/{LANG}_{DATE}/model.safetensors
```

The file content contains the model's hash value. The **first 8 characters** of this hash is the variant used in the config file.

### Step 4: Update the Config

In `english.yaml`, update the `variant` field with the new 8-character hash:
```yaml
variant: a0ac5076  # update this to the new hash
```

## Example

- Model page: `https://huggingface.co/kyutai/pocket-tts/blob/main/languages/english_2026-04/model.safetensors`
- Raw pointer: `https://huggingface.co/kyutai/pocket-tts/raw/main/languages/english_2026-04/model.safetensors`
- Hash (first 8 chars): `a0ac5076`

## When to Use

Use this workflow when:
- User asks to update the TTS model
- User wants to know the latest model hash
- Build errors indicate variant mismatch
- Config file needs updating with new model version

## Current Model Variant

As of April 2026, the current English model variant is: `a0ac5076` (from `english_2026-04`)
