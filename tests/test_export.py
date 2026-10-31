"""导出与 DBSCAN eps 估计测试。"""

from __future__ import annotations

import numpy as np

from core.algorithms.segmentation import suggest_eps
from core.io.exporters import export_entity
from core.model.entities import CloudEntity, ScalarField


def _cloud(points: int = 2000, scale: float = 1.0, seed: int = 0) -> CloudEntity:
    rng = np.random.default_rng(seed)
    xyz = (rng.uniform(-0.5, 0.5, (points, 3)) * scale).astype(np.float32)
    return CloudEntity(name="t", xyz=xyz, fields={})


def test_suggest_eps_scales_with_density():
    dense = suggest_eps(_cloud(2000, scale=1.0).xyz, min_samples=10)
    sparse = suggest_eps(_cloud(2000, scale=50.0).xyz, min_samples=10)
    assert dense > 0 and sparse > 0
    assert dense < sparse


def test_export_entity_writes_ply(tmp_path):
    entity = _cloud(500)
    entity.fields["intensity"] = ScalarField("intensity", np.linspace(0, 1, 500).astype(np.float32))
    path = tmp_path / "out.ply"
    export_entity(entity, str(path))
    assert path.exists() and path.stat().st_size > 500
