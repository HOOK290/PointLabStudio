"""E23：LAS 原生读写（intensity/classification/RGB）。"""

from __future__ import annotations

import numpy as np
import pytest

from core.io.las_io import read_las, write_las
from core.io.readers import ReadOptions, read_cloud
from core.model.entities import CloudEntity, ScalarField


def _cloud(n=800, rgb=False, seed=0):
    rng = np.random.default_rng(seed)
    xyz = rng.uniform(-50, 50, (n, 3)).astype(np.float32)
    fields = {
        "intensity": ScalarField("intensity", rng.integers(0, 60000, n).astype(np.float32)),
        "classification": ScalarField("classification", rng.integers(0, 8, n).astype(np.float32),
                                      kind="label"),
    }
    if rgb:
        fields["rgb"] = ScalarField("rgb", rng.random((n, 3)).astype(np.float32), kind="color")
    return CloudEntity("t", xyz=xyz, fields=fields)


def test_las_roundtrip_positions_intensity_classification(tmp_path):
    cloud = _cloud()
    path = tmp_path / "cloud.las"
    write_las(cloud, str(path))

    loaded = read_las(str(path))
    assert loaded.point_count == cloud.point_count
    assert np.abs(loaded.xyz - cloud.xyz).max() < 0.001
    assert np.array_equal(loaded.fields["intensity"].data,
                          cloud.fields["intensity"].data)
    assert np.array_equal(loaded.fields["classification"].data,
                          cloud.fields["classification"].data)
    assert "rgb" not in loaded.fields


def test_las_roundtrip_rgb(tmp_path):
    cloud = _cloud(rgb=True)
    path = tmp_path / "rgb.las"
    write_las(cloud, str(path))
    loaded = read_las(str(path))
    assert "rgb" in loaded.fields
    assert np.abs(loaded.fields["rgb"].data - cloud.fields["rgb"].data).max() < 0.001


def test_las_header_is_valid_1_2(tmp_path):
    cloud = _cloud(50)
    path = tmp_path / "h.las"
    write_las(cloud, str(path))
    raw = path.read_bytes()
    assert raw[:4] == b"LASF"
    assert raw[24] == 1 and raw[25] == 2
    assert int(np.frombuffer(raw, dtype="<u4", count=1, offset=107)[0]) == 50


def test_read_cloud_dispatches_las(tmp_path):
    cloud = _cloud(120)
    path = tmp_path / "d.las"
    write_las(cloud, str(path))
    loaded = read_cloud(str(path), ReadOptions())
    assert loaded.point_count == 120


def test_laz_roundtrip_with_laspy(tmp_path):
    laspy = pytest.importorskip("laspy")
    pytest.importorskip("lazrs")
    rng = np.random.default_rng(3)
    xyz = rng.uniform(-10, 10, (400, 3))
    header = laspy.LasHeader(point_format=2, version="1.2")
    las = laspy.LasData(header)
    las.x, las.y, las.z = xyz[:, 0], xyz[:, 1], xyz[:, 2]
    las.intensity = rng.integers(0, 65535, 400).astype(np.uint16)
    las.red = rng.integers(0, 65535, 400).astype(np.uint16)
    las.green = rng.integers(0, 65535, 400).astype(np.uint16)
    las.blue = rng.integers(0, 65535, 400).astype(np.uint16)
    path = tmp_path / "c.laz"
    las.write(str(path))

    from core.io.las_io import read_laz

    loaded = read_laz(str(path))
    assert loaded.point_count == 400
    assert np.abs(loaded.xyz - xyz).max() < 0.01
    assert "intensity" in loaded.fields and "rgb" in loaded.fields
    assert loaded.fields["rgb"].data.max() <= 1.0


def test_e57_roundtrip_with_pye57(tmp_path):
    pye57 = pytest.importorskip("pye57")
    rng = np.random.default_rng(4)
    pts = rng.uniform(-3, 3, (300, 3))
    color = rng.integers(0, 255, (300, 3)).astype(np.uint16) * 257
    data = {
        "cartesianX": pts[:, 0], "cartesianY": pts[:, 1], "cartesianZ": pts[:, 2],
        "intensity": rng.random(300).astype(np.float32),
        "colorRed": color[:, 0], "colorGreen": color[:, 1], "colorBlue": color[:, 2],
    }
    path = tmp_path / "c.e57"
    writer = pye57.E57(str(path), mode="w")
    writer.write_scan_raw(data)
    writer.close()

    from core.io.las_io import read_e57

    loaded = read_e57(str(path))
    assert loaded.point_count == 300
    assert "intensity" in loaded.fields and "rgb" in loaded.fields
    assert loaded.fields["rgb"].data.max() <= 1.0


def test_missing_optional_dependency_message():
    from core.io import las_io

    with pytest.raises(ValueError, match="nonexistent_pointlab_mod"):
        las_io._require("nonexistent_pointlab_mod", "测试")


def test_read_missing_laz_raises_oserror(tmp_path):
    pytest.importorskip("laspy")
    from core.io.las_io import read_laz

    with pytest.raises(OSError):
        read_laz(str(tmp_path / "missing.laz"))
