import numpy as np
import pytest

from core.algorithms import filters, registration, segmentation
from core.cancellation import OperationCancelled, check_cancel
from core.io.readers import ReadOptions, _read_bin_chunked
from core.pipeline import parse_stage, run_pipeline
from core.model.entities import CloudEntity


def _cloud(n=2000, seed=0):
    rng = np.random.default_rng(seed)
    xyz = rng.normal(size=(n, 3)).astype(np.float32)
    return CloudEntity("pts", xyz=xyz)


def test_check_cancel_raises_only_when_requested():
    check_cancel(None)
    check_cancel(lambda: False)
    with pytest.raises(OperationCancelled):
        check_cancel(lambda: True)


@pytest.mark.parametrize("fn", ["plane_ransac", "extract_ground", "dbscan"])
def test_segmentation_honours_cancel(fn):
    with pytest.raises(OperationCancelled):
        getattr(segmentation, fn)(_cloud().xyz, cancel=lambda: True)


def test_filters_honour_cancel():
    entity = _cloud()
    with pytest.raises(OperationCancelled):
        filters.voxel_downsample(entity.xyz, voxel=0.2, cancel=lambda: True)
    with pytest.raises(OperationCancelled):
        filters.statistical_outlier_removal(entity.xyz, cancel=lambda: True)
    with pytest.raises(OperationCancelled):
        filters.radius_outlier_removal(entity.xyz, cancel=lambda: True)
    with pytest.raises(OperationCancelled):
        filters.crop_box(entity.xyz, [-1, -1, -1], [1, 1, 1], cancel=lambda: True)


def test_icp_honours_cancel():
    entity = _cloud()
    with pytest.raises(OperationCancelled):
        registration.icp(entity.xyz, entity.xyz, cancel=lambda: True)


def test_pipeline_honours_cancel():
    entity = _cloud()
    steps = [parse_stage("voxel:0.5"), parse_stage("sor:10,2.0")]
    with pytest.raises(OperationCancelled):
        run_pipeline(entity, steps, cancel=lambda: True)


def test_bin_reader_honours_cancel(tmp_path):
    path = tmp_path / "cloud.bin"
    np.arange(3000, dtype=np.float32).tofile(path)
    with pytest.raises(OperationCancelled):
        _read_bin_chunked(str(path), 3, "float32", cancel=lambda: True)
