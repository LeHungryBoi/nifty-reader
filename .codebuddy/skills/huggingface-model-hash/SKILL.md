---
name: huggingface-model-hash
description: This skill should be used when user needs to find the variant hash for pocket-tts models on HuggingFace. The hash (first 8 characters) is used as the variant identifier in config files.
---

# HuggingFace Model Hash Finder

## Purpose

Find the variant hash for pocket-tts models from HuggingFace. The hash is computed from the model weights and is used as the `variant` identifier in the config YAML file.

## Workflow

1. **Open the HuggingFace model page**
   
   Model file URL format:
   ```
   https://huggingface.co/kyutai/pocket-tts/blob/main/languages/{LANG}_{DATE}/model.safetensors
   ```
   
   Example: `https://huggingface.co/kyutai/pocket-tts/blob/main/languages/english_2026-04/model.safetensors`

2. **Find the "Raw pointer file" button**
   
   On the model file page, locate the "Raw pointer file" button (raw pointer 文件).

3. **Get the hash**
   
   Click the button to open the raw pointer file URL:
   ```
   https://huggingface.co/kyutai/pocket-tts/raw/main/languages/{LANG}_{DATE}/model.safetensors
   ```
   
   The file content contains the model's hash value. The **first 8 characters** of this hash is the variant used in the config file.

4. **Update the config**
   
   In `english.yaml`, update the `variant` field with the new 8-character hash:
   ```yaml
   variant: a0ac5076  # update this to the new hash
   ```

## Example

- Model page: `https://huggingface.co/kyutai/pocket-tts/blob/main/languages/english_2026-04/model.safetensors`
- Raw pointer: `https://huggingface.co/kyutai/pocket-tts/raw/main/languages/english_2026-04/model.safetensors`
- Hash (first 8 chars): `a0ac5076`

## When to Use

Use this skill when:
- User asks to update the TTS model
- User wants to know the latest model hash
- Build errors indicate variant mismatch
- Config file needs updating with new model version
