"""工程文件 v2：相对路径、相机/裁剪恢复、派生点云内嵌。"""

from __future__ import annotations

import json
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


def _close(window: MainWindow, app):
    window.close()
    deadline = time.monotonic() + 5
    while window.isVisible() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)


def test_project_v2_saves_relative_path_camera_clip_and_derived(win, app, tmp_path):
    source = tmp_path / "source.npy"
    np.save(source, np.array([[0, 0, 0], [1, 1, 1], [2, 2, 2]], dtype=np.float32))
    win.open_paths([str(source)])
    app.processEvents()

    derived = CloudEntity(
        "去噪结果",
        xyz=np.array([[0, 0, 0], [1, 1, 1]], dtype=np.float32),
        fields={"intensity": ScalarField("intensity", np.array([0.25, 0.5], dtype=np.float32))},
    )
    win._add_entity(derived)
    derived.color_mode = "field"
    derived.color_field = "intensity"
    derived.color_range = (0.1, 0.9)
    win.entities[0].color_range = (0.0, 5.0)
    win.viewport.orbit_camera(120, -400)
    win.viewport.zoom_camera(2)
    win.viewport._settle_zoom()
    win.viewport.set_clip_box([0, 0, 0], [1, 1, 1])
    win.clip_popup.set_enabled(True)
    camera = win.viewport.camera_state()

    project_dir = tmp_path / "proj"
    project_dir.mkdir()
    project = project_dir / "scene.pls"
    assert win.save_project(str(project))

    data = json.loads(project.read_text(encoding="utf-8"))
    assert data["version"] == 2
    assert data["files"][0]["path"] == "../source.npy"
    assert data["camera"]["position"] == camera["position"]
    assert data["clip"]["enabled"] is True
    assert (project_dir / "scene.assets").is_dir()
    assert data["derived"] and data["derived"][0]["asset"].endswith(".npz")

    viewer = MainWindow()
    try:
        assert viewer.open_project(str(project))
        app.processEvents()
        restored = [e for e in viewer.entities if e.path and e.path.endswith("source.npy")]
        assert len(restored) == 1
        assert restored[0].color_range == (0.0, 5.0)
        embedded = [e for e in viewer.entities if not e.path]
        assert len(embedded) == 1
        assert embedded[0].name == "去噪结果"
        assert embedded[0].color_field == "intensity"
        assert embedded[0].color_range == (0.1, 0.9)
        np.testing.assert_allclose(
            embedded[0].fields["intensity"].data, [0.25, 0.5], atol=1e-6
        )
        assert viewer.viewport._clip_box is not None
        assert np.allclose(viewer.viewport.camera.local.position, camera["position"], atol=1e-4)
        viewer.viewport.orbit_camera(0, 0)
        np.testing.assert_allclose(viewer.viewport.camera.local.rotation, camera["rotation"], atol=1e-6)
    finally:
        _close(viewer, app)


def test_legacy_v1_project_with_absolute_path_still_opens(win, tmp_path):
    source = tmp_path / "legacy.npy"
    np.save(source, np.array([[0, 0, 0], [1, 2, 3]], dtype=np.float32))
    project = tmp_path / "legacy.pls"
    project.write_text(
        json.dumps({"files": [{"path": str(source), "visible": True, "color_mode": "auto",
                               "colormap": "default", "point_size": 2.0}]}),
        encoding="utf-8",
    )
    assert win.open_project(str(project))


def test_derived_from_preview_keeps_preview_flag(win):
    """派生结果来自采样预览时必须继续标记为预览，不能伪装成满分辨率结果。"""
    source = CloudEntity("big", xyz=np.zeros((10, 3), dtype=np.float32))
    source.loaded = 0.1
    source.tier = "M"
    result = win._make_result(source, "voxel", source.xyz, {}, "voxel=0.5")
    assert result.is_preview
    assert result.loaded == pytest.approx(0.1)
    assert result.tier == "M"
    assert "基于 10% 预览" in result.info


def test_load_queue_starts_next_only_when_a_slot_frees(win, tmp_path):
    started = []

    class Dummy:
        def deleteLater(self):
            pass

        def requestInterruption(self):
            pass

        def isRunning(self):
            return False

    b = str(tmp_path / "b.bin")
    c = str(tmp_path / "c.bin")
    for path in (b, c):
        open(path, "wb").close()

    def fake_start(path):
        started.append(path)
        win._threads[path] = Dummy()

    win._start_full_load = fake_start
    win._threads = {"a": Dummy(), "x": Dummy()}
    win._load_queue = [b, c]
    try:
        win._on_thread_finished("a")
        assert started == [b]
        assert win._load_queue == [c]
    finally:
        win._threads.clear()
        win._load_queue.clear()
