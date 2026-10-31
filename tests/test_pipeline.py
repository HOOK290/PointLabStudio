"""P5：处理链与 CLI 测试。"""

from __future__ import annotations

import numpy as np

from core.model.entities import CloudEntity, ScalarField
from core.pipeline import parse_stage, run_pipeline


def _make_cloud(n: int = 8000, seed: int = 0) -> CloudEntity:
    rng = np.random.default_rng(seed)
    xyz = rng.uniform(-5, 5, (n, 3)).astype(np.float32)
    intensity = rng.uniform(0, 1, n).astype(np.float32)
    return CloudEntity(name="test", xyz=xyz,
                       fields={"intensity": ScalarField("intensity", intensity)})


def test_parse_stage():
    assert parse_stage("voxel:0.5") == {"op": "voxel", "params": {"voxel": 0.5}}
    assert parse_stage("sor:20,2.0")["params"] == {"k": 20, "std": 2.0}
    crop = parse_stage("crop:-1,1,-2,2,-3,3")
    assert crop["op"] == "crop"
    assert crop["params"]["xmin"] == -1.0 and crop["params"]["zmax"] == 3.0


def test_pipeline_chain_reduces_and_keeps_fields():
    source = _make_cloud()
    steps = [
        {"op": "voxel", "params": {"voxel": 1.0}},
        {"op": "sor", "params": {"k": 10, "std": 1.0}},
        {"op": "crop", "params": {"xmin": -4, "xmax": 4, "ymin": -4, "ymax": 4,
                                  "zmin": -4, "zmax": 4}},
    ]
    result = run_pipeline(source, steps)
    assert 0 < result.point_count < source.point_count
    assert result.field("intensity") is not None
    assert result.field("intensity").shape[0] == result.point_count
    assert "体素" in result.info and "盒裁切" in result.info


def test_pipeline_dbscan_labels():
    source = _make_cloud()
    result = run_pipeline(source, [{"op": "dbscan", "params": {"eps": 0.8, "min_pts": 5}}])
    assert result.field("labels") is not None
    assert result.color_mode == "label"


def test_pipeline_progress():
    source = _make_cloud(3000)
    seen = []
    run_pipeline(source, [{"op": "voxel", "params": {"voxel": 0.5}}],
                 progress=lambda f: seen.append(f))
    assert seen and seen[-1] == 1.0
