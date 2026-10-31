"""原生格式读写与字段保真测试（P0 数据正确性）。"""

from __future__ import annotations

import numpy as np

from core.io.exporters import export_entity
from core.io.native_io import read_pcd, read_ply, read_text
from core.io.readers import read_cloud
from core.io.readers import ReadOptions
from core.model.entities import CloudEntity, ScalarField


def _entity(n=100, seed=0) -> CloudEntity:
    rng = np.random.default_rng(seed)
    xyz = rng.uniform(-2, 2, (n, 3)).astype(np.float32)
    color = rng.uniform(0, 1, (n, 3)).astype(np.float32)
    return CloudEntity(
        name="t",
        xyz=xyz,
        fields={
            "intensity": ScalarField("intensity", rng.uniform(0, 1, n).astype(np.float32)),
            "labels": ScalarField("labels", np.arange(n).astype(np.float32)),
            "rgb": ScalarField("rgb", color, kind="color"),
        },
    )


def test_ply_roundtrip_keeps_scalar_fields(tmp_path):
    entity = _entity()
    path = tmp_path / "a.ply"
    export_entity(entity, str(path))
    loaded = read_ply(str(path))

    np.testing.assert_allclose(loaded.xyz, entity.xyz, atol=1e-5)
    np.testing.assert_allclose(loaded.fields["intensity"].data, entity.fields["intensity"].data, atol=1e-6)
    np.testing.assert_allclose(loaded.fields["labels"].data, entity.fields["labels"].data, atol=1e-6)
    np.testing.assert_allclose(loaded.fields["rgb"].data, entity.fields["rgb"].data, atol=2 / 255)


def test_pcd_binary_roundtrip_keeps_scalar_fields(tmp_path):
    entity = _entity()
    path = tmp_path / "a.pcd"
    export_entity(entity, str(path))
    loaded = read_pcd(str(path))

    np.testing.assert_allclose(loaded.xyz, entity.xyz, atol=1e-5)
    np.testing.assert_allclose(loaded.fields["intensity"].data, entity.fields["intensity"].data, atol=1e-6)
    np.testing.assert_allclose(loaded.fields["labels"].data, entity.fields["labels"].data, atol=1e-6)
    assert loaded.fields["rgb"].data.max() <= 1.0


def test_pcd_ascii_reader(tmp_path):
    path = tmp_path / "b.pcd"
    path.write_text(
        "# .PCD v0.7\nVERSION 0.7\nFIELDS x y z intensity\nSIZE 4 4 4 4\n"
        "TYPE F F F F\nCOUNT 1 1 1 1\nWIDTH 2\nHEIGHT 1\n"
        "VIEWPOINT 0 0 0 1 0 0 0\nPOINTS 2\nDATA ascii\n"
        "0 0 0 0.5\n1 2 3 0.75\n",
        encoding="utf-8",
    )
    loaded = read_pcd(str(path))
    assert loaded.point_count == 2
    np.testing.assert_allclose(loaded.fields["intensity"].data, [0.5, 0.75], atol=1e-6)


def test_text_roundtrip_and_header_columns(tmp_path):
    entity = _entity(20)
    path = tmp_path / "a.xyz"
    export_entity(entity, str(path))
    loaded = read_text(str(path), ".xyz")

    np.testing.assert_allclose(loaded.xyz, entity.xyz, atol=1e-4)
    np.testing.assert_allclose(loaded.fields["intensity"].data, entity.fields["intensity"].data, atol=1e-4)
    np.testing.assert_allclose(loaded.fields["labels"].data, entity.fields["labels"].data, atol=1e-4)


def test_pts_roundtrip(tmp_path):
    entity = _entity(30)
    path = tmp_path / "a.pts"
    export_entity(entity, str(path))
    loaded = read_text(str(path), ".pts")
    assert loaded.point_count == 30
    np.testing.assert_allclose(loaded.fields["intensity"].data, entity.fields["intensity"].data, atol=1e-4)


def test_export_does_not_bake_display_colors(tmp_path):
    """高度着色只是显示状态，导出不应产生 rgb 字段。"""
    entity = CloudEntity(name="h", xyz=_entity().xyz, color_mode="height")
    path = tmp_path / "c.ply"
    export_entity(entity, str(path))
    loaded = read_ply(str(path))
    assert "rgb" not in loaded.fields


def test_read_cloud_pcd_preserves_intensity(tmp_path):
    entity = _entity(50)
    path = tmp_path / "d.pcd"
    export_entity(entity, str(path))
    loaded = read_cloud(str(path), ReadOptions())
    assert "intensity" in loaded.fields
    assert "labels" in loaded.fields
