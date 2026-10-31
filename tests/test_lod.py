"""E24：LOD 预算与渲染采样。"""

from __future__ import annotations

import time

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from core.geometry import lod
from core.model.entities import CloudEntity
from ui.main_window import MainWindow


def test_lod_budget_by_distance():
    assert lod.lod_budget(1000, 10.0, 1e9) == 1000
    assert lod.lod_budget(2_000_000, 100.0, 100.0) == lod.LOD_BUDGETS[0]
    assert lod.lod_budget(2_000_000, 100.0, 1000.0) == lod.LOD_BUDGETS[1]
    assert lod.lod_budget(2_000_000, 100.0, 3000.0) == lod.LOD_BUDGETS[2]


def test_select_lod_indices_is_stable_and_bounded():
    idx = lod.select_lod_indices(1_000_000, 100_000)
    assert idx is not None
    assert len(idx) == 100_000
    assert idx.min() >= 0 and idx.max() < 1_000_000
    assert np.all(np.diff(idx) > 0)
    again = lod.select_lod_indices(1_000_000, 100_000)
    assert np.array_equal(idx, again)
    assert lod.select_lod_indices(500, 5000) is None


def test_level_name():
    assert lod.level_name(1000, 1000) == "全量"
    assert "LOD" in lod.level_name(1000, 250)


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def win(app):
    window = MainWindow()
    window.show()
    app.processEvents()
    yield window
    window.close()
    deadline = time.monotonic() + 5
    while window.isVisible() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)


def test_viewport_down_samples_large_cloud(win, app, monkeypatch):
    monkeypatch.setattr(lod, "LOD_BUDGETS", (50_000, 20_000, 10_000))
    rng = np.random.default_rng(0)
    cloud = CloudEntity("big", xyz=rng.uniform(-10, 10, (400_000, 3)).astype(np.float32))
    win._add_entity(cloud)
    app.processEvents()

    vp = win.viewport
    rendered = vp._lod_counts[id(cloud)]
    assert rendered <= 50_000
    assert cloud.point_count == 400_000


def test_lod_uses_camera_distance_without_rescanning_or_clearing_selection(win, monkeypatch):
    monkeypatch.setattr(lod, "LOD_BUDGETS", (100, 50, 10))
    cloud = CloudEntity("lod", xyz=np.random.default_rng(2).uniform(-1, 1, (200, 3)).astype(np.float32))
    win._add_entity(cloud)
    vp = win.viewport
    extent = cloud.extent()
    vp._pivot = cloud.center()
    vp._distance = extent
    vp._apply_camera()
    vp._update_lod()
    assert vp._lod_counts[id(cloud)] == 100
    vp._apply_selection_highlight([(cloud, np.array([0, 1]))])
    highlight = vp._sel_highlight
    def unexpected_scan():
        pytest.fail("Camera-only LOD updates must reuse scene bounds")
    monkeypatch.setattr(cloud, "bounds", unexpected_scan)
    vp._distance = extent * 25
    vp._apply_camera()
    vp._update_lod()
    assert vp._lod_counts[id(cloud)] == 10
    assert vp._sel_highlight is highlight
    assert cloud.point_count == 200
