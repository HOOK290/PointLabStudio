"""E20：任意标量场着色、显式颜色范围与颜色条控件。"""

from __future__ import annotations

import time

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from core.color.colormaps import compute_colors, sample_colormap
from core.model.entities import CloudEntity, ScalarField
from ui.main_window import MainWindow
from ui.widgets.colorbar import field_values, robust_minmax


def _cloud():
    xyz = np.array([[0, 0, 0], [0, 0, 1], [0, 0, 2]], dtype=np.float32)
    fields = {
        "temperature": ScalarField("temperature", np.array([0, 5, 10], np.float32)),
        "strength": ScalarField("strength", np.array([10, 0, 0], np.float32)),
    }
    return CloudEntity("c", xyz=xyz, fields=fields)


def test_field_mode_uses_selected_field():
    entity = _cloud()
    entity.color_mode = "field"
    entity.color_field = "strength"
    rgb = compute_colors(entity)
    assert rgb.shape == (3, 3)
    assert not np.allclose(rgb[0, :3], rgb[1, :3])
    assert rgb[0, 0] > rgb[1, 0]


def test_field_mode_auto_picks_first_scalar_field():
    entity = _cloud()
    entity.color_mode = "field"
    entity.color_field = ""
    compute_colors(entity)
    assert entity.color_field == "temperature"


def test_explicit_range_maps_to_colormap_ends():
    entity = _cloud()
    entity.color_mode = "field"
    entity.color_field = "temperature"
    entity.color_range = (0.0, 10.0)
    rgb = compute_colors(entity)
    ends = sample_colormap(entity.colormap, np.array([0.0, 1.0]))
    assert np.allclose(rgb[0, :3], ends[0], atol=1e-5)
    assert np.allclose(rgb[2, :3], ends[1], atol=1e-5)

    entity.color_range = (0.0, 5.0)
    clamped = compute_colors(entity)
    assert np.allclose(clamped[2, :3], ends[1], atol=1e-5)


def test_robust_minmax_percentiles_and_degenerate():
    lo, hi = robust_minmax(np.arange(101, dtype=float))
    assert lo == pytest.approx(2.0)
    assert hi == pytest.approx(98.0)
    lo, hi = robust_minmax(np.array([3.0, 3.0, 3.0]))
    assert hi > lo


def test_field_values_height_and_field():
    entity = _cloud()
    assert field_values(entity, "height")[2] == pytest.approx(2.0)
    assert field_values(entity, "strength")[0] == pytest.approx(10.0)
    assert field_values(entity, "missing") is None


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


def test_colorbar_switch_updates_entity_and_refreshes(win, app):
    cloud = _cloud()
    win._add_entity(cloud)
    app.processEvents()

    win._on_colorbar_field("strength")
    assert cloud.color_mode == "field"
    assert cloud.color_field == "strength"

    win._on_colorbar_range(1.0, 9.0)
    assert cloud.color_range == (1.0, 9.0)

    win._on_colorbar_reset()
    assert cloud.color_range is None

    win._on_colorbar_field("height")
    assert cloud.color_mode == "height"
    assert cloud.color_field == ""


def test_colorbar_field_and_range_update_gpu_colors(win):
    cloud = _cloud()
    win._add_entity(cloud)
    win._on_colorbar_field("temperature")
    before = win.viewport._points_objs[0].geometry.colors.data.copy()
    win._on_colorbar_field("strength")
    after = win.viewport._points_objs[0].geometry.colors.data.copy()
    assert not np.allclose(before, after)
    np.testing.assert_allclose(after[:, :3], compute_colors(cloud))
    win._on_colorbar_range(0, 20)
    ranged = win.viewport._points_objs[0].geometry.colors.data.copy()
    assert not np.allclose(after, ranged)
    np.testing.assert_allclose(ranged[:, :3], compute_colors(cloud))
    win._on_colorbar_reset()
    np.testing.assert_allclose(win.viewport._points_objs[0].geometry.colors.data, after)
