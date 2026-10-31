import time

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from core.model.entities import CloudEntity, ScalarField
from ui.main_window import MainWindow


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
    assert not window.isVisible()


def test_clip_excludes_hidden_points_from_pick_and_selection(win, app):
    cloud = CloudEntity("test", xyz=np.array([[-1, 0, 0], [1, 0, 0]], dtype=np.float32))
    win._add_entity(cloud)
    app.processEvents()
    vp = win.viewport
    vp.set_clip_box([0, -1, -1], [2, 1, 1])
    sx, sy, valid = vp._screen_coords(cloud.xyz)
    assert valid.tolist() == [False, True]
    vp._on_point_click(float(sx[1]), float(sy[1]))
    assert vp._selected_point == (cloud, 1)
    assert vp._pick_point(float(sx[1]), float(sy[1]))[2] == 1
    assert vp._pick_point(-10000, -10000) is None


def test_removing_selected_cloud_clears_point_info(win):
    cloud = CloudEntity("test", xyz=np.array([[-1, 0, 0], [1, 0, 0]], dtype=np.float32))
    win._add_entity(cloud)
    sx, sy, _ = win.viewport._screen_coords(cloud.xyz)
    win.viewport._on_point_click(float(sx[0]), float(sy[0]))
    assert win.viewport._selection_marker is not None
    win._remove_entity(cloud)
    assert win.viewport._selected_point is None
    assert win.viewport._selection_marker is None
    assert not win.viewport.selection_label.isVisible()
    assert not win.entities


def test_full_load_preserves_history_entity_identity(win):
    old = CloudEntity("preview", path="test.bin", xyz=np.zeros((10, 3), dtype=np.float32), loaded=.1)
    win._add_entity(old)
    win._remove_entity(old)
    win._undo()
    fresh = CloudEntity("full", path="test.bin", xyz=np.ones((20, 3), dtype=np.float32))
    win._on_full_loaded("test.bin", fresh)
    assert win.entities[0] is old and old.point_count == 20
    win._redo()
    assert not win.entities


def test_close_waits_for_filter_without_adding_result(win, app):
    def worker(progress):
        time.sleep(.2)
        return CloudEntity("result", xyz=np.zeros((10, 3), dtype=np.float32))

    win._run_filter("test", worker)
    win.close()
    assert win.isVisible()
    deadline = time.monotonic() + 5
    while win.isVisible() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(.01)
    assert not win.isVisible()
    assert not win.entities


def test_reload_and_visibility_undo(win):
    cloud = CloudEntity("source", xyz=np.zeros((10, 3), dtype=np.float32))
    win._add_entity(cloud)
    win.scene_panel.set_visible(cloud, False)
    win._undo()
    assert cloud.visible
    win._redo()
    assert not cloud.visible
    fresh = CloudEntity("fresh", xyz=np.ones((20, 3), dtype=np.float32))
    win._apply_reload(cloud, fresh)
    assert win.scene_panel.card_summary(0)["points"] == "20 点"
    win._undo()
    assert cloud.point_count == 10
    win._redo()
    assert cloud.point_count == 20


def test_project_relative_paths_and_existing_display(win, tmp_path):
    import json

    cloud_path = tmp_path / "source.npy"
    np.save(cloud_path, np.ones((10, 3), dtype=np.float32))
    project = tmp_path / "scene.pls"
    project.write_text(json.dumps({"files": [{"path": "source.npy", "visible": False,
                                             "color_mode": "height", "point_size": 4}]}))
    win.open_paths([str(cloud_path)])
    assert win.open_project(str(project))
    assert len(win.entities) == 1
    assert not win.entities[0].visible
    assert win.entities[0].point_size == 4
    assert not win._pending_display


def test_script_refreshes_display_and_preserves_output_on_error(win):
    from ui.widgets.script_dialog import ScriptDialog

    cloud = CloudEntity("source", xyz=np.zeros((10, 3), dtype=np.float32))
    win._add_entity(cloud)
    dialog = ScriptDialog(win, win)
    dialog.editor.setPlainText("entities[0].visible = False\nprint('before-error')\nraise ValueError('test')")
    dialog._run()
    assert not win.viewport._points_objs
    assert "before-error" in win.log_view.toPlainText()
    dialog.close()


def test_tools_receive_mouse_events_on_actual_render_widget(win, app):
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest

    cloud = CloudEntity("click-target", xyz=np.array([[-1, 0, 0], [1, 0, 0]], dtype=np.float32))
    cloud.fields = {
        "intensity": ScalarField("intensity", np.array([.25, .75])),
        "rgb": ScalarField("rgb", np.array([[1., 0, 0], [0, 1., 0]]), kind="color"),
        "labels": ScalarField("labels", np.array([3, 7])),
    }
    win._add_entity(cloud)
    app.processEvents()
    vp = win.viewport
    vp.camera.local.position = np.asarray(vp.camera.local.position) * 3
    sx, sy, valid = vp._screen_coords(cloud.xyz)
    assert valid.all()
    positions = [QPoint(round(float(x)), round(float(y))) for x, y in zip(sx, sy)]
    target = vp.childAt(positions[0])
    assert target is vp._subwidget
    distances = []
    vp.measured.connect(distances.append)
    QTest.mouseClick(win.btn_measure, Qt.LeftButton)
    for i, position in enumerate(positions):
        QTest.mouseClick(target, Qt.LeftButton, pos=target.mapFrom(vp, position))
        if i == 0:
            assert len(vp._measure_objs) == 1
    assert len(distances) == 2 and distances[-1] == pytest.approx(2.0)

    QTest.mouseClick(win.btn_select, Qt.LeftButton)
    camera_before = np.array(vp.camera.local.position)
    for i, position in enumerate(positions):
        QTest.mouseClick(target, Qt.LeftButton, pos=target.mapFrom(vp, position))
        assert vp._selected_point == (cloud, i)
        assert vp._selection_marker.material.size == 10
        text = vp.selection_label.text()
        assert f"点索引 {i}" in text
        assert f"X: {cloud.xyz[i, 0]:.6f}" in text
        assert "强度:" in text and "RGB:" in text and "聚类标签:" in text
    QTest.keyClick(target, Qt.Key_Delete)
    assert win.entities == [cloud] and cloud.point_count == 2
    QTest.mouseClick(target, Qt.LeftButton, pos=QPoint(target.width() - 5, target.height() - 5))
    assert vp._selected_point is None and vp._selection_marker is None
    np.testing.assert_array_equal(vp.camera.local.position, camera_before)
    QTest.keyClick(target, Qt.Key_Escape)
    assert vp._mode is None and vp._drag is None


@pytest.mark.parametrize("scale", [.001, 1., 1_000_000.])
def test_measurement_markers_use_fixed_screen_size(win, scale):
    import pygfx as gfx

    xyz = np.array([[-1, 0, 0], [1, 0, 0]], dtype=np.float32) * scale
    win._add_entity(CloudEntity("scale", xyz=xyz))
    vp = win.viewport
    vp._draw_measurement(*xyz)
    markers = vp._measure_objs[1:]
    assert len(markers) == 2
    for marker in markers:
        assert isinstance(marker, gfx.Points)
        assert marker.material.size_space == "screen"
        assert marker.material.size == 10
        assert not marker.material.depth_test
    vp.camera.local.position = np.asarray(vp.camera.local.position) * 2
    assert all(marker.material.size == 10 for marker in markers)


def test_pick_prefers_front_point_over_hidden(win, app):
    cloud = CloudEntity("two", xyz=np.array([[0, 0, 0], [0, 0, -10]], dtype=np.float32))
    win._add_entity(cloud)
    app.processEvents()
    vp = win.viewport
    vp.camera.local.position = (0, 0, 10)
    vp.camera.look_at((0, 0, 0))
    app.processEvents()
    sx, sy, ok = vp._screen_coords(cloud.xyz)
    assert ok[0] and ok[1]
    picked = vp._pick_point(float(sx[0]), float(sy[0]))
    assert picked is not None
    assert picked[2] == 0, "被遮挡的远点不应被拾取"


def test_projection_cache_hits_until_camera_moves(win, app):
    cloud = CloudEntity("cache", xyz=np.random.default_rng(0).normal(size=(1000, 3)).astype(np.float32))
    win._add_entity(cloud)
    app.processEvents()
    vp = win.viewport
    first = vp._project_points(cloud.xyz)
    second = vp._project_points(cloud.xyz)
    assert second[0] is first[0], "相机未变时应命中缓存"
    vp.camera.local.position = (5, 5, 5)
    vp._invalidate()
    third = vp._project_points(cloud.xyz)
    assert third[0] is not first[0], "相机变化后应重新投影"


def test_clip_popup_rejects_inverted_range(win, app):
    popup = win.clip_popup
    received = []
    popup.values_changed.connect(lambda mn, mx: received.append((mn, mx)))
    popup.set_enabled(True)
    popup.set_values([1, 0, 0], [0, 1, 1])
    popup._emit_values()
    assert received == []
    assert popup.lbl_warning.isVisible() or popup.lbl_warning.isHidden() is False
    popup.set_values([-1, -1, -1], [1, 1, 1])
    popup._emit_values()
    assert received == [([-1, -1, -1], [1, 1, 1])]


def test_viewport_ignores_invalid_clip_box(win, app):
    vp = win.viewport
    assert vp.set_clip_box([0, 0, 0], [1, 1, 1]) is True
    before = vp._clip_box
    assert vp.set_clip_box([2, 0, 0], [1, 1, 1]) is False
    assert vp._clip_box is before


def test_dbscan_eps_estimated_once_per_entity(win, app, monkeypatch):
    cloud = CloudEntity("db", xyz=np.random.default_rng(1).normal(size=(500, 3)).astype(np.float32))
    win._add_entity(cloud)
    from core.algorithms import segmentation
    calls = []
    monkeypatch.setattr(segmentation, "suggest_eps",
                        lambda xyz, min_samples=10, sample=4000, cancel=None: calls.append(1) or 0.42)
    opened = []
    monkeypatch.setattr(win, "_open_dbscan_dialog", lambda src, eps: opened.append(eps))
    win._process_dbscan()
    win._process_dbscan()
    assert len(calls) == 1, "同一实体重复打开应复用缓存的 eps"
    assert opened == [0.42, 0.42]


def test_pipeline_dialog_uses_command_specs(win, app):
    cloud = CloudEntity("pd", xyz=np.random.default_rng(2).normal(size=(800, 3)).astype(np.float32) * 10)
    win._add_entity(cloud)
    app.processEvents()
    from core.commands import get_spec
    from ui.widgets.pipeline_dialog import PipelineDialog

    dialog = PipelineDialog(win, cloud)
    fields, hint = dialog._fields_for("voxel")
    assert fields[0]["key"] == "voxel"
    assert abs(fields[0]["default"] - cloud.extent() / 300.0) < 1e-9
    assert hint == get_spec("voxel").hint
    eps_fields, _ = dialog._fields_for("dbscan")
    assert eps_fields[0]["default"] > 0


def test_pipeline_dialog_lists_params_and_roundtrips_commands(win, app):
    cloud = CloudEntity("pd2", xyz=np.random.default_rng(3).normal(size=(400, 3)).astype(np.float32))
    win._add_entity(cloud)
    app.processEvents()
    from core.commands import Command, commands_from_json, commands_to_json
    from ui.widgets.pipeline_dialog import PipelineDialog

    dialog = PipelineDialog(win, cloud)
    dialog._steps = [{"op": "voxel", "params": {"voxel": 0.5}},
                     {"op": "sor", "params": {"k": 12, "std": 1.5}}]
    dialog._refresh()
    assert "体素降采样" in dialog.list.item(0).text()
    assert "voxel=0.5" in dialog.list.item(0).text()
    text = commands_to_json([Command.from_step(s) for s in dialog.steps()])
    assert [c.op for c in commands_from_json(text)] == ["voxel", "sor"]
