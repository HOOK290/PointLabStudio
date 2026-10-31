import numpy as np
import pytest

from apps.cli import main
from core.algorithms.filters import statistical_outlier_removal
from core.color.colormaps import robust_norm
from core.io import auto_ingest
from core.io.readers import ReadOptions, read_cloud, read_bin_preview
from core.model.entities import CloudEntity
from core.pipeline import parse_stage


def test_small_bin_auto(tmp_path):
    path = tmp_path / "small.bin"
    points = np.arange(9, dtype=np.float32).reshape(3, 3)
    points.tofile(path)
    np.testing.assert_array_equal(read_cloud(str(path), ReadOptions()).xyz, points)


def test_probe_respects_full_file_divisibility(tmp_path):
    path = tmp_path / "cloud.bin"
    points = np.random.default_rng(2).normal(size=(66667, 3)).astype(np.float32)
    points.tofile(path)
    cloud = read_cloud(str(path), ReadOptions())
    assert cloud.dim_hint == 3
    np.testing.assert_array_equal(cloud.xyz, points)


def test_preview_explicit_nonstandard_dimension_and_coverage(tmp_path):
    path = tmp_path / "cloud.bin"
    points = np.arange(900, dtype=np.float32).reshape(100, 9)
    points.tofile(path)
    cloud, total = read_bin_preview(str(path), ReadOptions(bin_dim="9"), max_rows=10)
    assert total == 100 and cloud.point_count == 10
    np.testing.assert_array_equal(cloud.xyz[[0, -1]], points[[0, -1], :3])


@pytest.mark.parametrize("preview", [False, True])
def test_reject_truncated_bin(tmp_path, preview):
    path = tmp_path / "bad.bin"
    path.write_bytes(np.zeros((10, 4), dtype=np.float32).tobytes() + b"x")
    reader = read_bin_preview if preview else read_cloud
    with pytest.raises(ValueError):
        reader(str(path), ReadOptions(bin_dim="4"))


def test_missing_npz_key(tmp_path):
    path = tmp_path / "cloud.npz"
    np.savez(path, points=np.zeros((10, 3)))
    with pytest.raises(KeyError):
        read_cloud(str(path), ReadOptions(npy_key="missing"))


def test_memory_limit_also_applies_to_medium_tier(tmp_path, monkeypatch):
    path = tmp_path / "large.bin"
    path.touch()
    monkeypatch.setattr(auto_ingest, "SIZE_S", 0)
    preview = CloudEntity("preview", xyz=np.zeros((2, 3)))
    monkeypatch.setattr(auto_ingest, "read_preview", lambda *a: (preview, 60_000_000))
    plan = auto_ingest.plan_ingest(str(path), ReadOptions())
    assert plan.tier == "M" and not plan.needs_full


def test_sor_retains_identical_points():
    assert statistical_outlier_removal(np.zeros((30, 3)), k=5).all()


def test_nonfinite_scalar_colors():
    assert np.isfinite(robust_norm(np.array([0, 1, np.nan, np.inf]))).all()


@pytest.mark.parametrize("stage", ["voxel:1,2", "random:10,20"])
def test_extra_stage_arguments_rejected(stage):
    with pytest.raises(ValueError):
        parse_stage(stage)


def test_cli_reports_failure(tmp_path):
    path = tmp_path / "bad.npy"
    path.write_bytes(b"invalid")
    assert main([str(path), "--info"]) == 1


def test_cli_rejects_multi_file_single_export(tmp_path):
    for name in ("a.npy", "b.npy"):
        np.save(tmp_path / name, np.zeros((10, 3)))
    assert main([str(tmp_path), "--export", str(tmp_path / "out.ply")]) == 1


def test_batch_export_preserves_duplicate_names(tmp_path):
    source = tmp_path / "input"
    output = source / "output"
    for folder in ("a", "b"):
        (source / folder).mkdir(parents=True)
        np.save(source / folder / "cloud.npy", np.ones((10, 3)))
    np.savetxt(source / "a" / "cloud.txt", np.zeros((10, 3)))
    for _ in range(2):
        assert main([str(source), "--outdir", str(output)]) == 0
    assert len(list(output.rglob("*.ply"))) == 3
    assert (output / "a" / "cloud.npy.ply").exists()
    assert (output / "a" / "cloud.txt.ply").exists()
    assert (output / "b" / "cloud.ply").exists()


@pytest.mark.parametrize("extension", ["npy", "npz", "csv", "txt", "xyz", "pts", "ply", "pcd"])
def test_supported_formats(tmp_path, extension):
    import open3d as o3d

    points = np.random.default_rng(10).normal(size=(30, 3)).astype(np.float32)
    path = tmp_path / f"cloud.{extension}"
    if extension == "npy":
        np.save(path, points)
    elif extension == "npz":
        np.savez(path, points=points)
    elif extension in ("csv", "txt"):
        np.savetxt(path, points, delimiter="," if extension == "csv" else " ")
    else:
        cloud = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(points))
        assert o3d.io.write_point_cloud(str(path), cloud)
    loaded = read_cloud(str(path), ReadOptions())
    np.testing.assert_allclose(loaded.xyz, points, atol=1e-5)
