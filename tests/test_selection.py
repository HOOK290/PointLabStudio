"""E18：框选/套索的屏幕空间命中逻辑与主窗口选择操作（不启动 GPU 视口）。"""

import time

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow
from ui.viewport.viewport import PointCloudViewport, _points_in_polygon


class _FakeEntity:
    def __init__(self, xyz, visible=True):
        self.xyz = np.asarray(xyz, dtype=np.float32)
        self.visible = visible


class _FakeViewport:
    """只带 _finish_selection 依赖的属性与投影函数。"""

    def __init__(self, project):
        self._sel_mode = None
        self._sel_start = None
        self._sel_points = []
        self.entities = []
        self._project = project

    def _project_points(self, xyz):
        return self._project


def _project(xy, ok=None):
    xy = np.asarray(xy, dtype=np.float32)
    sx, sy = xy[:, 0], xy[:, 1]
    if ok is None:
        ok = np.ones(len(xy), dtype=bool)
    depth = np.full(len(xy), 0.5, dtype=np.float32)
    return sx, sy, depth, ok


def test_polygon_contains_center_only():
    sx = np.array([5.0, 1.0, 9.0, np.inf], dtype=np.float32)
    sy = np.array([5.0, 1.0, 9.0, 5.0], dtype=np.float32)
    poly = np.array([(2.0, 2.0), (8.0, 2.0), (8.0, 8.0), (2.0, 8.0)])
    hit = _points_in_polygon(sx, sy, poly)
    assert hit.tolist() == [True, False, False, False]


def test_polygon_degenerate_returns_empty():
    hit = _points_in_polygon(np.array([1.0]), np.array([1.0]), np.array([(0, 0)]))
    assert not hit.any()


def test_box_selection_uses_screen_rect_and_ok():
    vp = _FakeViewport(_project([(1, 1), (5, 5), (20, 20), (5, 5)],
                                ok=np.array([True, True, False, True])))
    vp.entities = [_FakeEntity(np.zeros((4, 3)))]
    vp._sel_mode = "box"
    vp._sel_start = (0.0, 0.0)
    got = PointCloudViewport._finish_selection(vp, 10.0, 10.0)
    assert len(got) == 1
    entity, idx = got[0]
    assert idx.tolist() == [0, 1, 3]


def test_box_selection_skips_hidden_entities():
    vp = _FakeViewport(_project([(1, 1)]))
    vp.entities = [_FakeEntity(np.zeros((1, 3)), visible=False)]
    vp._sel_mode = "box"
    vp._sel_start = (0.0, 0.0)
    assert PointCloudViewport._finish_selection(vp, 10.0, 10.0) == []


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


def _open_four_points(win, app, tmp_path):
    path = tmp_path / "four.npy"
    np.save(path, np.array([[0, 0, 0], [1, 0, 0], [2, 0, 0], [3, 0, 0]],
                           dtype=np.float32))
    win.open_paths([str(path)])
    app.processEvents()
    assert win.entities
    return win.entities[0]


def test_extract_selection_creates_subset_entity(win, app, tmp_path):
    entity = _open_four_points(win, app, tmp_path)
    win._on_viewport_selection([(entity, np.array([0, 2]))])
    assert win.act_extract_selection.isEnabled()

    win._extract_selection()
    app.processEvents()

    assert len(win.entities) == 2
    result = win.entities[-1]
    assert result.point_count == 2
    assert np.allclose(result.xyz, entity.xyz[[0, 2]])
    assert not win.act_extract_selection.isEnabled()  # 选择已被清空


def test_delete_selection_keeps_complement(win, app, tmp_path):
    entity = _open_four_points(win, app, tmp_path)
    win._on_viewport_selection([(entity, np.array([1, 3]))])

    win._delete_selection()
    app.processEvents()

    assert len(win.entities) == 2
    result = win.entities[-1]
    assert result.point_count == 2
    assert np.allclose(result.xyz, entity.xyz[[0, 2]])


def test_selection_cleared_when_leaving_tool(win):
    win._on_viewport_selection([(_FakeEntity(np.zeros((2, 3))), np.array([0, 1]))])
    assert win.act_extract_selection.isEnabled()
    win._on_mode_changed("")
    assert not win.act_extract_selection.isEnabled()

