"""core 层单元测试（无 UI 依赖），运行方式见 README。"""

from __future__ import annotations

import os
import tempfile

import numpy as np
import pytest

from core.color.colormaps import array_to_rgb, compute_colors, robust_norm, scalar_to_rgb
from core.geometry.ops import sanitize_cloud, subsample_indices
from core.io.auto_ingest import tier_by_points, tier_by_size
from core.io.bin_reader import infer_bin_dim
from core.io.readers import ReadOptions, read_bin, read_cloud
from core.io.scanner import collect_files, natural_key
from core.model.entities import CloudEntity


# ---------------- 色彩映射 ----------------
def test_robust_norm():
    v = np.array([0, 1, 2, 3, 4, 100], dtype=np.float32)
    t = robust_norm(v)
    assert t.shape == v.shape
    assert t.min() >= 0 and t.max() <= 1
    assert t.min() == 0 and t.max() == 1  # 极端值被 2–98 百分位截断到边界
    # 归一化后仍保持单调性
    assert np.all(np.diff(t[:5]) >= -1e-6)


def test_scalar_to_rgb():
    rgb = scalar_to_rgb(np.linspace(0, 1, 128).astype(np.float32), "turbo")
    assert rgb.shape == (128, 3)
    assert rgb.min() >= 0 and rgb.max() <= 1


def test_array_to_rgb_scales_0_255():
    rgb = array_to_rgb(np.array([[255, 0, 0]], dtype=np.float32))
    assert np.allclose(rgb, [[1, 0, 0]], atol=1e-5)


def test_compute_colors_modes():
    xyz = np.random.default_rng(0).random((50, 3)).astype(np.float32)
    e = CloudEntity("t", xyz=xyz)
    e.fields["intensity"] = np.random.default_rng(1).random(50).astype(np.float32)
    c_auto = compute_colors(e, "auto")
    assert c_auto.shape == (50, 3)
    c_height = compute_colors(e, "height")
    assert np.allclose(c_height, scalar_to_rgb(xyz[:, 2]))
    assert compute_colors(e, "none") is None


# ---------------- 几何 ----------------
def test_sanitize():
    xyz = np.array([[0, 0, 0], [1, 1, np.nan], [2, 2, 2]], dtype=np.float32)
    out, i, r = sanitize_cloud(xyz)
    assert out.shape == (2, 3)


def test_subsample():
    idx = subsample_indices(10_000, 1_000, seed=0)
    assert idx is not None and len(idx) == 1_000
    assert len(np.unique(idx)) == 1_000
    assert subsample_indices(500, 1_000) is None


# ---------------- .bin 维度识别 ----------------
def test_infer_bin_dim_kitti():
    rng = np.random.default_rng(0)
    pts = np.zeros((5000, 4), dtype=np.float32)
    pts[:, 0] = rng.uniform(-40, 40, 5000)
    pts[:, 1] = rng.uniform(-40, 40, 5000)
    pts[:, 2] = rng.uniform(-2, 3, 5000)
    pts[:, 3] = rng.uniform(0, 1, 5000)
    dim, debug = infer_bin_dim("D:/data/velodyne/000001.bin", pts.reshape(-1), None)
    assert dim == 4


def test_infer_bin_dim_user():
    arr = np.zeros(3000, dtype=np.float32)
    dim, _ = infer_bin_dim("x.bin", arr, 3)
    assert dim == 3


# ---------------- 读取器 ----------------
def test_read_bin_roundtrip(tmp_path):
    rng = np.random.default_rng(2)
    pts = np.zeros((2000, 4), dtype=np.float32)
    pts[:, :3] = rng.uniform(-5, 5, (2000, 3))
    pts[:, 3] = rng.uniform(0, 1, 2000)
    path = str(tmp_path / "cloud.bin")
    pts.tofile(path)

    entity = read_bin(path, ReadOptions(bin_dim="4"))
    assert entity.point_count == 2000
    assert entity.field("intensity") is not None
    assert entity.dim_hint == 4
    assert entity.tier == "S"


def test_read_cloud_xyz(tmp_path):
    path = str(tmp_path / "cloud.xyz")
    with open(path, "w") as f:
        for i in range(100):
            f.write(f"{i} {i*2} {i*3}\n")
    entity = read_cloud(path, ReadOptions())
    assert entity.point_count == 100


def test_collect_files(tmp_path):
    (tmp_path / "a2.pcd").write_bytes(b"")
    (tmp_path / "a10.pcd").write_bytes(b"")
    (tmp_path / "b.log").write_text("junk")  # 不支持的扩展名
    files = collect_files(str(tmp_path))
    names = [os.path.basename(f) for f in files]
    assert names == ["a2.pcd", "a10.pcd"]  # 自然排序


# ---------------- Auto-Ingest ----------------
def test_tier_thresholds():
    assert tier_by_points(500_000) == "S"
    assert tier_by_points(5_000_000) == "M"
    assert tier_by_points(150_000_000) == "L"
    assert tier_by_size(10 * 1024 * 1024) == "S"
    assert tier_by_size(500 * 1024 * 1024) == "M"
    assert tier_by_size(5 * 1024 * 1024 * 1024) == "L"
