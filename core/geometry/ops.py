"""基础几何操作：清洗、采样（迁移自 vis_point_cloud.py）。"""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np


def sanitize_cloud(xyz, intensity=None, rgb=None):
    """校验形状、剔除非有限点，返回 (xyz, intensity, rgb)。"""
    xyz = np.asarray(xyz, dtype=np.float32)
    if xyz.ndim != 2 or xyz.shape[1] < 3:
        raise ValueError(f"点云不是 Nx3+: shape={xyz.shape}")

    xyz = xyz[:, :3]
    mask = np.all(np.isfinite(xyz), axis=1)

    xyz = xyz[mask]
    intensity = None if intensity is None else np.asarray(intensity)[mask]
    rgb = None if rgb is None else np.asarray(rgb, dtype=np.float32)[mask]
    return xyz, intensity, rgb


def subsample_indices(n: int, max_points: int, seed: int = 0) -> Optional[np.ndarray]:
    """均匀间隔 + 随机抖动混合采样，保证覆盖整体形状。"""
    if not max_points or max_points <= 0 or n <= max_points:
        return None
    rng = np.random.default_rng(seed)
    if max_points >= n // 2:
        index = rng.choice(n, size=max_points, replace=False)
    else:
        index = np.linspace(0, n - 1, num=max_points, dtype=np.int64)
        jitter = rng.integers(0, max(1, n // max_points), size=max_points)
        index = np.clip(index + jitter, 0, n - 1)
        index = np.unique(index)
        while len(index) < max_points:  # 补齐重复后缺的点（内存友好）
            add = rng.integers(0, n, size=max_points - len(index))
            index = np.unique(np.concatenate([index, add]))
    return np.sort(index)


def sample_cloud(xyz, max_points: int, seed: int = 0) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """返回 (采样后 xyz, 采样索引或 None)。"""
    index = subsample_indices(len(xyz), max_points, seed)
    if index is None:
        return xyz, None
    return xyz[index], index
