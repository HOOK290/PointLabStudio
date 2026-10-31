"""E24：八叉树式 LOD —— 按视距与预算选择渲染采样级别。

点云本身仍保留全分辨率（导出/测量/选择都用全量），只有渲染缓冲使用
采样索引；缩放到近处时预算提高，远离时降低。
"""

from __future__ import annotations

import numpy as np

# 渲染预算（按由近到远）
LOD_BUDGETS = (1_500_000, 600_000, 150_000)


def lod_budget(point_count: int, extent: float, distance: float) -> int:
    """根据点数、包围盒对角线与相机距离决定渲染预算。"""
    if point_count <= LOD_BUDGETS[-1]:
        return int(point_count)
    ratio = float(distance) / max(float(extent), 1e-9)
    if ratio > 20.0:
        return LOD_BUDGETS[-1]
    if ratio > 6.0:
        return LOD_BUDGETS[1]
    return LOD_BUDGETS[0]


def select_lod_indices(point_count: int, budget: int,
                       seed: int = 0) -> np.ndarray | None:
    """返回均匀分层的采样索引；预算覆盖全量时返回 None。

    用等步长 + 固定抖动，保证视角变化时采样稳定、不闪烁。
    """
    point_count = int(point_count)
    budget = int(budget)
    if budget >= point_count:
        return None
    if budget <= 0:
        return np.zeros(0, dtype=np.int64)
    step = point_count / budget
    offset = 0.5 * step
    idx = np.floor(np.arange(budget, dtype=np.float64) * step + offset).astype(np.int64)
    return np.clip(idx, 0, point_count - 1)


def level_name(point_count: int, budget: int) -> str:
    """给状态栏/日志用的可读级别描述。"""
    if budget >= point_count:
        return "全量"
    return f"LOD {budget / max(point_count, 1) * 100:.1f}%"
