"""
多层级特征提取 — 从 PocketTTS 模型中提取 level 1-7 的声音特征。

Level 1: Raw Audio (24kHz) — 原始波形
Level 2: SEANet Features — 卷积提取的声学特征 [B, 512, T/120] 200Hz
Level 3: Encoder Attn — self-attention 增强 [B, T/120, 512] 200Hz
Level 4: MiMi Latent — codec 压缩指纹 [B, 32, T/1920] 12.5Hz
Level 5: Transpose — 格式转换 [B, T_latent, 32]
Level 6: Speaker Proj — 线性投射 [B, T_latent, 1024]
Level 7: FlowLM KV Cache — 完整的 model_state dict
"""

from __future__ import annotations

import torch
import numpy as np
from pathlib import Path
from typing import Optional

from persona import Persona


class LevelExtractor:
    """从 TTSModel 提取不同层级的声音特征"""

    def __init__(self, model):
        self.model = model
        self._hooks = []
        self._captured: dict[int, torch.Tensor] = {}

    def extract_all_levels(
        self,
        audio_path: str,
        copy_state: bool = False,
    ) -> dict[int, torch.Tensor]:
        """
        提取所有 7 个 level 的特征。
        返回 {level: tensor} dict。
        """
        self._captured = {}

        # 注册 hooks（在 _encode_audio 调用前）
        self._register_hooks()

        try:
            # 调用 get_state_for_audio_prompt 触发完整的编码流程
            state = self.model.get_state_for_audio_prompt(
                audio_path, truncate=True, copy_state=copy_state)

            # Level 7: 完整的 KV Cache state
            if state:
                self._captured[7] = self._pack_state(state)

            return dict(self._captured)
        finally:
            self._remove_hooks()

    def extract_single_level(
        self,
        audio_path: str,
        level: int,
        copy_state: bool = False,
    ) -> Optional[torch.Tensor]:
        """提取单个 level 的特征"""
        all_levels = self.extract_all_levels(audio_path, copy_state)
        return all_levels.get(level)

    def _register_hooks(self):
        """注册 forward hooks 捕获中间特征"""
        mimi = self.model.mimi

        # Level 2: SEANet encoder output [B, 512, T/120]
        def hook_seanet(module, input, output):
            self._captured[2] = output.detach().cpu()

        self._hooks.append(
            mimi.encoder.register_forward_hook(hook_seanet))

        # Level 3: Encoder transformer output [B, T/120, 512]
        # encoder_transformer is a ProjectedTransformer, wraps StreamingTransformer
        # Its forward returns a tuple: (output_tensor,)
        def hook_enc_transformer(module, input, output):
            # output is (tensor,) from ProjectedTransformer
            if isinstance(output, tuple) and len(output) > 0:
                self._captured[3] = output[0].detach().cpu()
            else:
                self._captured[3] = output.detach().cpu()

        self._hooks.append(
            mimi.encoder_transformer.transformer.register_forward_hook(
                hook_enc_transformer))

        # Level 4: Downsample (ConvDownsample1d) output [B, 32, T/1920]
        def hook_downsample(module, input, output):
            self._captured[4] = output.detach().cpu()

        self._hooks.append(
            mimi.downsample.register_forward_hook(hook_downsample))

        # Level 5 & 6: 需要拦截 TTSModel._encode_audio 内部的 transpose 和 projection
        # 通过 monkey-patch _encode_audio 来捕获
        self._patch_encode_audio()

    def _patch_encode_audio(self):
        """Monkey-patch _encode_audio 来捕获 level 5 和 6"""
        original_encode = self.model._encode_audio

        def patched_encode(audio_prompt, model_state=None, copy_state=False):
            result = original_encode(audio_prompt, model_state, copy_state)
            # result 是 encoded tensor, 在 _encode_audio 内部经过了 transpose 和 projection
            # Level 5 (transpose): [B, 32, T] -> [B, T, 32]
            # Level 6 (speaker proj): [B, T, 32] -> [B, T, 1024]
            # encoded 最终是 [B, T_latent, 1024] (level 6 output)
            self._captured[6] = result.detach().cpu()
            # Level 5 需要重新计算 transpose 之前的状态
            # encoded 的来源: transpose([B, 32, T]) -> [B, T, 32] -> proj -> [B, T, 1024]
            # 所以 level 5 = result[:, :, :32] 不对，需要从 level 4 反推
            # level 4 是 [B, 32, T_latent], level 5 = transpose = [B, T_latent, 32]
            if 4 in self._captured:
                self._captured[5] = self._captured[4].transpose(-1, -2).cpu()
            return result

        self.model._encode_audio = patched_encode
        self._original_encode = original_encode

    def _remove_hooks(self):
        """移除所有 hooks 和 patches"""
        for hook in self._hooks:
            hook.remove()
        self._hooks.clear()
        if hasattr(self, '_original_encode'):
            self.model._encode_audio = self._original_encode

    def _pack_state(self, state: dict) -> torch.Tensor:
        """
        将完整的 model_state (level 7) 打包为一个 tensor 用于存储。
        保存所有 cache 为一个 stack tensor。
        """
        caches = []
        for module_name in sorted(state.keys()):
            module_state = state[module_name]
            if "cache" in module_state:
                caches.append(module_state["cache"].detach().cpu().float())

        if not caches:
            return torch.tensor([])
        return torch.stack(caches, dim=0)  # [num_modules, 2, B, T, H, D]


def save_level_features(
    features: dict[int, torch.Tensor],
    persona: Persona,
):
    """将各 level 特征保存为 numpy 文件"""
    for level, tensor in features.items():
        if tensor is None or (hasattr(tensor, 'nelement') and tensor.nelement() == 0):
            continue
        path = persona.get_derived_path(level)
        arr = tensor.numpy() if isinstance(tensor, torch.Tensor) else tensor
        np.save(str(path), arr)


def load_level_features(
    persona: Persona,
    level: int,
) -> Optional[np.ndarray]:
    """加载指定 level 的特征"""
    path = persona.get_derived_path(level)
    if not path.exists():
        return None
    return np.load(str(path))


def get_level_info(level: int) -> dict:
    """获取 level 的描述信息"""
    info = {
        1: {"name": "Raw Audio", "desc": "原始波形 24kHz", "shape": "[B, 1, T]"},
        2: {"name": "SEANet Features", "desc": "卷积声学特征 512维 200Hz", "shape": "[B, 512, T/120]"},
        3: {"name": "Encoder Attn", "desc": "self-attention 增强 512维 200Hz", "shape": "[B, T/120, 512]"},
        4: {"name": "MiMi Latent", "desc": "codec 压缩指纹 32维 12.5Hz", "shape": "[B, 32, T/1920]"},
        5: {"name": "Transpose", "desc": "格式转换", "shape": "[B, T_latent, 32]"},
        6: {"name": "Speaker Proj", "desc": "线性投射到 LM 空间 1024维", "shape": "[B, T_latent, 1024]"},
        7: {"name": "FlowLM KV Cache", "desc": "语言模型处理后的记忆", "shape": "[N, 2, B, T, H, D]"},
    }
    return info.get(level, {"name": f"Level {level}", "desc": "", "shape": ""})
