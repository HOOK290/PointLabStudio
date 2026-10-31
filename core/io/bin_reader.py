""".bin 维度启发式自动识别（迁移自 vis_point_cloud.py）。

.bin 没有文件头，自动识别无法保证 100% 正确；
UI 层在低置信度时会弹确认框（见 ui/main_window.py）。
"""

from __future__ import annotations

import os
from typing import Optional, Tuple

import numpy as np


def parse_bin_dim(value: str) -> Optional[int]:
    value = str(value).strip().lower()
    return None if value in {"auto", "none", ""} else int(value)


def path_dim_hint(path: str) -> Optional[int]:
    path_lower = path.replace("\\", "/").lower()
    name = os.path.basename(path_lower)

    if "lidar_top" in path_lower or name.endswith(".pcd.bin") or ("nuscenes" in path_lower and "samples" in path_lower):
        return 5
    if "velodyne" in path_lower or "kitti" in path_lower or "gt_database" in path_lower or "database" in path_lower:
        return 4
    return None


def score_bin_dim(points: np.ndarray, dim: int) -> float:
    """启发式评分：越像合理点云得分越高。"""
    xyz = points[: min(len(points), 200000), :3]
    finite = np.all(np.isfinite(xyz), axis=1)
    if finite.size == 0 or finite.mean() < 0.98:
        return -1e6

    xyz = xyz[finite]
    q1, q99 = np.percentile(xyz, [1, 99], axis=0)
    extent = q99 - q1
    abs99 = np.percentile(np.abs(xyz), 99, axis=0)

    xy_extent = max(float(extent[0]), float(extent[1]))
    z_extent = float(extent[2])
    max_abs = float(np.max(abs99))

    score = 100.0
    if max_abs > 1e5:
        score -= 250
    elif max_abs > 1e4:
        score -= 80
    if xy_extent < 0.05:
        score -= 50
    if z_extent > max(80.0, xy_extent * 3.0):
        score -= 80

    if dim == 5 and points.shape[1] >= 5:
        ring = points[: min(len(points), 200000), 4]
        ring = ring[np.isfinite(ring)]
        if ring.size:
            integer_like = np.mean(np.abs(ring - np.round(ring)) < 1e-3)
            if np.percentile(ring, 1) >= -1e-3 and np.percentile(ring, 99) <= 255 and integer_like > 0.8:
                score += 18

    score += {4: 4, 5: 3, 3: 1}.get(dim, 0)
    return float(score)


def infer_bin_dim(path: str, array: np.ndarray, user_dim: Optional[int],
                  total_values: Optional[int] = None) -> Tuple[int, str]:
    if user_dim is not None:
        if user_dim < 3 or array.size % user_dim != 0:
            raise ValueError(f"无法按 bin_dim={user_dim} reshape，float 数量={array.size}")
        return user_dim, f"dim={user_dim}"

    total_values = array.size if total_values is None else total_values
    candidates = [d for d in [3, 4, 5, 6, 7, 8]
                  if array.size >= d and array.size % d == 0 and total_values % d == 0]
    if not candidates:
        raise ValueError(f"无法自动识别 .bin 维度，float 数量={array.size}，请指定 bin_dim")

    scores = {d: score_bin_dim(array.reshape(-1, d), d) for d in candidates}
    hint = path_dim_hint(path)
    if hint in scores:
        scores[hint] += 60

    dim = max(scores, key=scores.get)
    debug = "auto_dim={}, hint={}, scores={}".format(
        dim, hint, ",".join(f"{k}:{v:.1f}" for k, v in sorted(scores.items()))
    )
    return dim, debug


def bin_dim_confidence(scores: dict, chosen: int) -> float:
    """维度识别置信度（0..1），用于决定是否弹确认框。"""
    if not scores:
        return 0.0
    values = sorted(scores.values(), reverse=True)
    if len(values) < 2:
        return 1.0
    gap = values[0] - values[1]
    return float(np.clip(gap / 60.0, 0.0, 1.0))
