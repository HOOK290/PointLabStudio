"""八叉树流式采样：预算、确定性、空间覆盖与实体标记。"""

from __future__ import annotations

import numpy as np
import pytest

from core.io.octree import build_octree, estimate_stream_points
from core.io.readers import ReadOptions, read_stream_bin


def _write_bin(path, n=200_000, seed=0):
    rng = np.random.default_rng(seed)
    xyz = rng.uniform([-20, -20, 0], [20, 20, 8], (n, 3)).astype(np.float32)
    inten = rng.random((n, 1)).astype(np.float32)
    np.hstack([xyz, inten]).astype(np.float32).tofile(path)
    return xyz


def test_octree_budget_and_bounds(tmp_path):
    path = tmp_path / "a.bin"
    xyz = _write_bin(path, 200_000)
    index = build_octree(str(path), dim=4, depth=4, per_cell=200)
    assert index.total == 200_000
    assert index.cell_count > 0

    sample = index.sample(50_000)
    assert 0 < len(sample) <= 50_000
    assert sample.dtype == np.float32
    assert sample[:, 0].min() >= -20.001 and sample[:, 0].max() <= 20.001
    assert sample[:, 2].min() >= -0.001 and sample[:, 2].max() <= 8.001


def test_octree_sample_is_deterministic(tmp_path):
    path = tmp_path / "b.bin"
    _write_bin(path, 60_000, seed=2)
    index = build_octree(str(path), dim=4, depth=3, per_cell=100)
    first = index.sample(10_000)
    second = index.sample(10_000)
    np.testing.assert_array_equal(first, second)


def test_read_stream_bin_marks_preview(tmp_path):
    path = tmp_path / "c.bin"
    _write_bin(path, 120_000, seed=3)
    entity = read_stream_bin(str(path), ReadOptions(bin_dim=4), budget=30_000)
    assert entity.point_count <= 30_000
    assert entity.tier == "L"
    assert 0 < entity.loaded <= 1
    assert "八叉树流式" in entity.info
    assert "octree" in str(entity.debug)


def test_stream_budget_estimate():
    assert estimate_stream_points(1_000) == 1_000
    assert estimate_stream_points(100_000_000) >= 1
    assert estimate_stream_points(100_000_000) <= 100_000_000


def test_octree_rejects_empty_or_short_file(tmp_path):
    path = tmp_path / "empty.bin"
    path.write_bytes(b"")
    with pytest.raises(ValueError):
        build_octree(str(path), dim=3)
