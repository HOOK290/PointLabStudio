"""E19：测量折线/面积与 CSV 导出。"""

from __future__ import annotations

import csv
import time

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from core.io.measurements import measurements_to_csv, write_measurements_csv
from ui.main_window import MainWindow


def _summary(pts):
    vp = type("VP", (), {"_measure_pts": [np.asarray(p, dtype=float) for p in pts],
                         "measurement_summary": None})
    from ui.viewport.viewport import PointCloudViewport
    return PointCloudViewport.measurement_summary(vp)


def test_polyline_length_and_triangle_area():
    s = _summary([(0, 0, 0), (1, 0, 0), (0, 1, 0)])
    assert len(s["segments"]) == 2
    assert s["length"] == pytest.approx(1.0 + np.sqrt(2))
    assert s["area"] == pytest.approx(0.5)


def test_nonplanar_polygon_area_is_newell():
    s = _summary([(0, 0, 0), (2, 0, 0), (2, 2, 1), (0, 2, 1)])
    assert s["area"] == pytest.approx(0.5 * np.sqrt(80.0))
    assert s["length"] == pytest.approx(2 + np.sqrt(5) + 2)


def test_csv_contains_points_segments_and_summary():
    s = _summary([(0, 0, 0), (1, 0, 0), (0, 1, 0)])
    text = measurements_to_csv(s)
    rows = list(csv.reader(text.splitlines()))
    assert rows[0][0] == "kind"
    assert [r[0] for r in rows[1:]] == ["point", "point", "point",
                                        "segment", "segment", "summary"]
    assert float(rows[-1][8]) == pytest.approx(s["length"])
    assert float(rows[-1][9]) == pytest.approx(0.5)


def test_write_csv_roundtrip(tmp_path):
    s = _summary([(0, 0, 0), (3, 4, 0)])
    out = tmp_path / "m.csv"
    assert write_measurements_csv(s, str(out))
    text = out.read_text(encoding="utf-8-sig")
    assert "summary" in text and "5.000000" in text


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


def test_window_writes_measurement_csv(win, app, tmp_path):
    win.viewport._measure_pts = [np.array([0, 0, 0], np.float32),
                                 np.array([1, 0, 0], np.float32)]
    app.processEvents()
    out = tmp_path / "measured.csv"
    assert win._write_measurements(str(out))
    assert "segment" in out.read_text(encoding="utf-8-sig")
    win._clear_measurement()
    assert len(win.viewport.measurement_summary()["points"]) == 0


def test_triangle_area_draws_filled_mesh(win, app):
    """面积不仅在文字里，还应在图上以半透明面填充显示。"""
    import pygfx as gfx

    vp = win.viewport
    vp._measure_pts = [np.array(p, np.float32) for p in
                       [(0, 0, 0), (2, 0, 0), (0, 2, 0)]]
    vp._draw_measurement_polyline()
    app.processEvents()

    meshes = [o for o in vp._measure_objs if isinstance(o, gfx.Mesh)]
    assert len(meshes) == 1
    assert meshes[0].material.opacity == pytest.approx(0.22)
    assert meshes[0].material.side == "both"
