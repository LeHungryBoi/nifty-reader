"""
Voice Fusion Core — PocketTTS voice state fusion logic.

Voice state 是 pocket-tts 内部的嵌套 dict 格式:
  {module_name: {"cache": Tensor[2,1,seq_len,heads,dim], "offset": Tensor[1]}}

融合直接在 torch tensor 上操作, 无需 numpy 转换。
"""

from __future__ import annotations

from pathlib import Path
from copy import deepcopy

import torch


# ---------------------------------------------------------------------------
# Voice State 信息
# ---------------------------------------------------------------------------

def get_state_info(state: dict) -> dict:
    """获取 voice state 的摘要信息。"""
    info = {
        "num_modules": len(state),
        "seq_lengths": set(),
        "details": [],
    }
    for module_name, module_state in state.items():
        if "cache" in module_state:
            cache = module_state["cache"]
            info["seq_lengths"].add(cache.shape[2])
            info["details"].append({
                "module": module_name,
                "cache_shape": list(cache.shape),
                "dtype": str(cache.dtype),
            })
    info["seq_lengths"] = sorted(info["seq_lengths"])
    info["all_same_seq_len"] = len(info["seq_lengths"]) == 1
    return info


def format_info(info: dict) -> str:
    """格式化 state info 为可读字符串。"""
    lines = [f"modules={info['num_modules']}, seq_len={info['seq_lengths']}"]
    if info["details"]:
        d = info["details"][0]
        lines.append(f"shape=[{d['cache_shape']}], dtype={d['dtype']}")
    if not info["all_same_seq_len"]:
        lines.append("WARNING: inconsistent seq_len across modules")
    return " | ".join(lines)


# ---------------------------------------------------------------------------
# 融合逻辑
# ---------------------------------------------------------------------------

def fuse_voice_states(
    state_a: dict,
    state_b: dict,
    alpha: float = 0.5,
    method: str = "align",
) -> dict:
    """
    融合两个 voice state (嵌套 dict 格式)。

    Args:
        state_a: voice state A (from model.get_state_for_audio_prompt)
        state_b: voice state B
        alpha: A 的权重, B 的权重为 (1 - alpha)
        method:
            "align"   — 时间轴对齐后加权插值 (推荐, 处理不同时长)
            "average" — 简单加权平均, 要求 seq_len 完全一致

    Returns:
        融合后的 voice state (新的 dict, 不修改输入)
    """
    beta = 1.0 - alpha
    modules_a = set(state_a.keys())
    modules_b = set(state_b.keys())
    if modules_a != modules_b:
        raise ValueError(
            f"Module mismatch: A has {modules_a - modules_b}, "
            f"B has {modules_b - modules_a}"
        )

    fused = {}
    for module_name in state_a:
        fused[module_name] = {}

        cache_a = state_a[module_name].get("cache")
        cache_b = state_b[module_name].get("cache")
        offset_a = state_a[module_name].get("offset")
        offset_b = state_b[module_name].get("offset")

        if cache_a is not None and cache_b is not None:
            if method == "align":
                fused[module_name]["cache"] = _fuse_cache_align(cache_a, cache_b, alpha, beta)
            elif method == "average":
                fused[module_name]["cache"] = _fuse_cache_average(cache_a, cache_b, alpha, beta)
            else:
                raise ValueError(f"Unknown method: {method}")

        if offset_a is not None and offset_b is not None:
            # offset 取较大值 (使用最长的序列位置)
            fused[module_name]["offset"] = torch.maximum(offset_a, offset_b)

        # 保留其他可能的 key
        for key in state_a[module_name]:
            if key not in ("cache", "offset") and key in state_b[module_name]:
                fused[module_name][key] = alpha * state_a[module_name][key] + beta * state_b[module_name][key]

    return fused


def fuse_voice_states_multi(
    states: list[dict],
    weights: list[float],
    method: str = "align",
) -> dict:
    """
    融合 N 个 voice state, 避免逐对融合导致的二次重采样。

    Args:
        states:  voice state 列表
        weights: 对应权重 (会自动归一化)
        method:  "align" 或 "average"

    Returns:
        融合后的 voice state
    """
    n = len(states)
    if n == 0:
        raise ValueError("No states to fuse")
    if n != len(weights):
        raise ValueError(f"states({n}) and weights({len(weights)}) length mismatch")

    if n == 1:
        return deepcopy(states[0])

    # 归一化权重
    total = sum(weights)
    if total <= 0:
        raise ValueError("Sum of weights must be positive")
    norm_weights = [w / total for w in weights]

    # 检查模块一致性
    modules = set(states[0].keys())
    for i, s in enumerate(states[1:], 1):
        if set(s.keys()) != modules:
            diff = set(s.keys()) ^ modules
            raise ValueError(f"State {i} module mismatch: {diff}")

    fused = {}
    for module_name in modules:
        fused[module_name] = {}

        caches = [s[module_name].get("cache") for s in states]
        offsets = [s[module_name].get("offset") for s in states]
        valid_cache = [(c, w) for c, w in zip(caches, norm_weights) if c is not None]
        valid_offset = [o for o in offsets if o is not None]

        if valid_cache:
            if method == "align":
                target_len = max(c.shape[2] for c, _ in valid_cache)
                aligned = []
                for c, w in valid_cache:
                    if c.shape[2] != target_len:
                        aligned.append((w, _resample_axis(c, dim=2, target_len=target_len)))
                    else:
                        aligned.append((w, c))
                fused[module_name]["cache"] = sum(w * a for w, a in aligned)
            elif method == "average":
                shapes = {c.shape for c, _ in valid_cache}
                if len(shapes) > 1:
                    seq_lens = [c.shape[2] for c, _ in valid_cache]
                    raise ValueError(
                        f"Shape mismatch: seq_lens={seq_lens}. Use method='align'."
                    )
                fused[module_name]["cache"] = sum(w * c for w, c in valid_cache)
            else:
                raise ValueError(f"Unknown method: {method}")

        if valid_offset:
            fused[module_name]["offset"] = max(valid_offset)

        # 保留其他 key (加权平均)
        for key in states[0][module_name]:
            if key in ("cache", "offset"):
                continue
            vals = [s[module_name].get(key) for s in states]
            if all(v is not None for v in vals):
                fused[module_name][key] = sum(w * v for w, v in zip(norm_weights, vals))

    return fused


def _fuse_cache_average(cache_a: torch.Tensor, cache_b: torch.Tensor, alpha: float, beta: float) -> torch.Tensor:
    """简单加权平均。要求 shape 完全一致。"""
    if cache_a.shape != cache_b.shape:
        seq_a, seq_b = cache_a.shape[2], cache_b.shape[2]
        raise ValueError(
            f"Shape mismatch: A has seq_len={seq_a}, B has seq_len={seq_b}. "
            f"Use method='align' for different-length voices."
        )
    return alpha * cache_a + beta * cache_b


def _fuse_cache_align(cache_a: torch.Tensor, cache_b: torch.Tensor, alpha: float, beta: float) -> torch.Tensor:
    """
    时间轴对齐后加权插值。
    对 dim=2 (seq_len) 做线性插值重采样, 对齐到 max(seq_len_a, seq_len_b)。
    """
    seq_a, seq_b = cache_a.shape[2], cache_b.shape[2]

    if seq_a == seq_b:
        return alpha * cache_a + beta * cache_b

    target_len = max(seq_a, seq_b)

    if seq_a != target_len:
        cache_a = _resample_axis(cache_a, dim=2, target_len=target_len)
    if seq_b != target_len:
        cache_b = _resample_axis(cache_b, dim=2, target_len=target_len)

    return alpha * cache_a + beta * cache_b


def _resample_axis(data: torch.Tensor, dim: int, target_len: int) -> torch.Tensor:
    """沿指定维度做线性插值重采样。"""
    src_len = data.shape[dim]
    if src_len == target_len:
        return data

    # 构建目标索引 (float)
    src_indices = torch.linspace(0, src_len - 1, target_len, device=data.device, dtype=data.dtype)

    floor_idx = torch.floor(src_indices).long()
    ceil_idx = torch.minimum(floor_idx + 1, torch.tensor(src_len - 1))
    frac = src_indices - floor_idx.float()  # [target_len]

    # 使用 index_select 在 dim 上采样
    floor_vals = torch.index_select(data, dim, floor_idx)
    ceil_vals = torch.index_select(data, dim, ceil_idx)

    # frac 需要 broadcast 到和 floor_vals 相同的 shape: 只在 dim 维度有值, 其余为 1
    frac_shape = [1] * data.ndim
    frac_shape[dim] = target_len
    frac = frac.reshape(frac_shape)

    return floor_vals * (1.0 - frac) + ceil_vals * frac


# ---------------------------------------------------------------------------
# Voice State 文件 I/O (safetensors flat ↔ nested dict)
# ---------------------------------------------------------------------------

def state_to_flat(state: dict) -> dict[str, torch.Tensor]:
    """嵌套 dict → flat dict (safetensors 格式)。"""
    flat = {}
    for module_name, module_state in state.items():
        for key, tensor in module_state.items():
            flat[f"{module_name}/{key}"] = tensor.cpu()
    return flat


def flat_to_state(flat: dict[str, torch.Tensor]) -> dict:
    """flat dict (safetensors 格式) → 嵌套 dict。"""
    state = {}
    for key, tensor in flat.items():
        module_name, tensor_key = key.split("/")
        state.setdefault(module_name, {})[tensor_key] = tensor
    return state


def save_state(state: dict, path: str | Path) -> None:
    """保存 voice state 到 .safetensors 文件。"""
    import safetensors.torch
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    safetensors.torch.save_file(state_to_flat(state), str(path))


def load_state(path: str | Path) -> dict:
    """从 .safetensors 文件加载 voice state (嵌套 dict 格式)。"""
    import safetensors
    path = Path(path)
    flat = {}
    with safetensors.safe_open(str(path), framework="pt") as f:
        for key in f.keys():
            flat[key] = f.get_tensor(key)
    return flat_to_state(flat)
