"""P2 滤波算法与命令历史测试。"""

from __future__ import annotations

import numpy as np

from core.algorithms import filters
from core.commands import History


def test_voxel_downsample_reduces_and_centers():
    rng = np.random.default_rng(0)
    pts = (np.floor(rng.random((2000, 3)) * 10) * 0.5).astype(np.float32)
    xyz, colors, intensity = filters.voxel_downsample(pts, voxel=1.0)
    assert 0 < len(xyz) <= len(pts)
    assert colors is None and intensity is None
    keys = np.floor((pts - pts.min(axis=0)) / 1.0).astype(np.int64)
    assert len(xyz) == len(np.unique(keys, axis=0))


def test_voxel_downsample_averages_colors():
    pts = np.array([[0, 0, 0], [0.05, 0, 0], [5, 5, 5]], dtype=np.float32)
    cols = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=np.float32)
    xyz, out_colors, _ = filters.voxel_downsample(pts, colors=cols, voxel=1.0)
    assert len(xyz) == 2
    red_green = out_colors[np.argmin(np.linalg.norm(xyz, axis=1))]
    assert np.allclose(red_green, [0.5, 0.5, 0.0], atol=1e-5)


def test_statistical_outlier_removal():
    rng = np.random.default_rng(1)
    cluster = rng.normal(0, 1.0, (500, 3))
    outliers = rng.uniform(40, 60, (20, 3))
    pts = np.vstack([cluster, outliers]).astype(np.float32)
    keep = filters.statistical_outlier_removal(pts, k=10, std_ratio=2.0)
    assert keep[:500].mean() > 0.95
    assert keep[500:].mean() < 0.5


def test_radius_outlier_removal():
    rng = np.random.default_rng(2)
    cluster = rng.normal(0, 0.3, (300, 3))
    isolated = np.array([[30, 30, 30], [35, 35, 35], [40, 40, 40]], dtype=np.float32)
    pts = np.vstack([cluster, isolated]).astype(np.float32)
    keep = filters.radius_outlier_removal(pts, radius=1.5, min_neighbors=4)
    assert keep[:300].mean() > 0.95
    assert not keep[300:].any()


def test_crop_box():
    pts = np.array([[0, 0, 0], [1, 1, 1], [5, 5, 5]], dtype=np.float32)
    mask = filters.crop_box(pts, [0, 0, 0], [1, 1, 1])
    assert mask.tolist() == [True, True, False]


def test_history_undo_redo():
    log = []
    h = History()
    h.push("a", lambda: log.append("undo-a"), lambda: log.append("redo-a"))
    h.push("b", lambda: log.append("undo-b"), lambda: log.append("redo-b"))
    assert h.can_undo and not h.can_redo

    assert h.undo() == "b"
    assert log == ["undo-b"]
    assert h.can_redo

    assert h.redo() == "b"
    assert log == ["undo-b", "redo-b"]

    h.undo()
    h.push("c", lambda: log.append("undo-c"), lambda: log.append("redo-c"))
    assert not h.can_redo  # 新操作清空重做栈
