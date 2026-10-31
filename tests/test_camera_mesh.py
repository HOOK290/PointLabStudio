"""v0.8：转盘相机（CloudCompare 风格）与网格实体渲染的回归测试。"""

from __future__ import annotations

import time

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from core.model.entities import CloudEntity, MeshEntity
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


def _open_cloud(win, app):
    cloud = CloudEntity("cloud", xyz=np.array([[0, 0, 0], [10, 0, 0], [0, 10, 0]],
                                              dtype=np.float32))
    win._add_entity(cloud)
    app.processEvents()
    return cloud


def test_orbit_keeps_pivot_and_distance(win, app):
    _open_cloud(win, app)
    vp = win.viewport
    vp._pivot = np.array([5.0, 5.0, 0.0])
    vp._apply_camera()
    before = np.array(vp.camera.local.position, copy=True)
    yaw = vp._yaw
    vp.orbit_camera(120.0, 0.0)
    assert vp._yaw != yaw
    assert np.allclose(vp._pivot, [5.0, 5.0, 0.0])
    np.testing.assert_allclose(np.linalg.norm(np.asarray(vp.camera.local.position) - vp._pivot),
                               vp._distance, rtol=1e-6)
    assert not np.allclose(np.asarray(vp.camera.local.position), np.asarray(before))


def test_pan_moves_pivot(win, app):
    _open_cloud(win, app)
    vp = win.viewport
    vp._pivot = np.zeros(3)
    vp._apply_camera()
    before = vp._pivot.copy()
    vp._pan_pixels(100.0, 0.0)
    assert not np.allclose(vp._pivot, before)


def test_zoom_changes_distance(win, app):
    _open_cloud(win, app)
    vp = win.viewport
    distance = vp._distance
    vp.zoom_camera(3.0)
    assert vp._zoom_target < distance
    vp._settle_zoom()
    assert vp._distance < distance
    vp.zoom_camera(-3.0)
    vp._settle_zoom()
    np.testing.assert_allclose(vp._distance, distance, rtol=1e-6)


def test_zoom_is_damped_not_jumpy(win, app):
    _open_cloud(win, app)
    vp = win.viewport
    start = vp._distance
    vp.zoom_camera(1.0)
    # 滚轮只改目标，第一帧不应直接跳到终点
    assert vp._distance == pytest.approx(start)
    vp._step_zoom_animation(1 / 60)
    assert start > vp._distance > vp._zoom_target
    for _ in range(120):
        vp._step_zoom_animation(1 / 60)
    assert vp._distance == pytest.approx(vp._zoom_target, rel=1e-3)


def test_orbit_horizontal_only_turns_around_z(win, app):
    _open_cloud(win, app)
    vp = win.viewport
    pitch = vp._pitch
    yaw = vp._yaw
    vp.orbit_camera(200.0, 0.0)
    assert vp._pitch == pytest.approx(pitch)
    assert vp._yaw != pytest.approx(yaw)


@pytest.mark.parametrize("axis", ["horizontal", "vertical"])
def test_orbit_full_circle_is_continuous(win, app, axis):
    from ui.viewport.viewport import ORBIT_SPEED
    _open_cloud(win, app)
    vp = win.viewport
    initial = np.array(vp.camera.world.matrix, copy=True)
    previous = initial[:3, :3]
    step = 2 * np.pi / (360 * ORBIT_SPEED)
    for _ in range(360):
        vp.orbit_camera(step if axis == "horizontal" else 0,
                        step if axis == "vertical" else 0)
        matrix = np.asarray(vp.camera.world.matrix)
        assert np.isfinite(matrix).all()
        assert np.linalg.norm(matrix[:3, :3] - previous) < 0.03
        np.testing.assert_allclose(np.linalg.norm(matrix[:3, 3] - vp._pivot),
                                   vp._distance, rtol=1e-6)
        previous = matrix[:3, :3].copy()
    np.testing.assert_allclose(vp.camera.world.matrix, initial, atol=1e-6)


def test_zoom_damping_is_frame_rate_independent(win, app):
    _open_cloud(win, app)
    vp = win.viewport
    start = vp._distance
    distances = []
    for fps in (30, 60, 120):
        vp._distance = start
        vp._sync_zoom()
        vp.zoom_camera(3)
        for _ in range(fps // 10):
            vp._step_zoom_animation(1 / fps)
        distances.append(vp._distance)
    np.testing.assert_allclose(distances, distances[0], rtol=1e-8)


@pytest.mark.parametrize("pitch", [np.pi / 2, -np.pi / 2])
def test_orbit_crosses_exact_pole_without_flip(win, app, pitch):
    _open_cloud(win, app)
    vp = win.viewport
    rotations = []
    for delta in (-1e-5, 0, 1e-5):
        vp._pitch = pitch + delta
        vp._apply_camera()
        rotations.append(np.array(vp.camera.world.matrix[:3, :3], copy=True))
    for rotation in rotations:
        assert np.isfinite(rotation).all()
        np.testing.assert_allclose(rotation.T @ rotation, np.eye(3), atol=1e-6)
    assert np.linalg.norm(rotations[2] - rotations[0]) < 1e-4


def test_pixel_only_wheel_zoom(win, app):
    from PySide6.QtCore import QPoint, QPointF, Qt
    from PySide6.QtGui import QWheelEvent

    _open_cloud(win, app)
    vp = win.viewport
    start = vp._distance
    event = QWheelEvent(QPointF(100, 100), QPointF(100, 100),
                        QPoint(0, 25), QPoint(0, 0), Qt.NoButton,
                        Qt.NoModifier, Qt.ScrollUpdate, False)
    vp.wheelEvent(event)
    assert vp._zoom_target < start
    assert vp._distance == start
    assert event.isAccepted()


def test_zoom_lod_uses_final_camera_position(win, app, monkeypatch):
    _open_cloud(win, app)
    vp = win.viewport
    positions = []
    monkeypatch.setattr(vp, "_update_lod", lambda: positions.append(
        np.linalg.norm(np.asarray(vp.camera.local.position) - vp._pivot)))
    vp.zoom_camera(2)
    for _ in range(120):
        vp._step_zoom_animation(1 / 60)
    assert positions == pytest.approx([vp._zoom_target])


def test_wheel_retarget_preserves_velocity_and_limits_backlog(win, app):
    _open_cloud(win, app)
    vp = win.viewport
    vp.zoom_camera(1)
    vp._step_zoom_animation(1 / 60)
    velocity = vp._zoom_velocity
    distance = vp._distance
    assert velocity < 0
    vp.zoom_camera(1)
    assert vp._zoom_velocity == velocity
    assert vp._distance == distance
    vp.zoom_camera(10000)
    assert vp._zoom_target >= distance / 4 - 1e-9
    vp._sync_zoom()
    assert vp._zoom_velocity == 0


@pytest.mark.parametrize("pitch", [0.3, 2.2])
def test_changing_pivot_preserves_camera_position(win, app, pitch):
    _open_cloud(win, app)
    vp = win.viewport
    vp._pitch = pitch
    vp._apply_camera()
    before = np.array(vp.camera.local.position, copy=True)
    vp._set_pivot([2.0, 3.0, 1.0])
    np.testing.assert_allclose(vp.camera.local.position, before, atol=1e-6)
    vp.orbit_camera(0, 0)
    np.testing.assert_allclose(vp.camera.local.position, before, atol=1e-6)


def test_camera_state_round_trip_with_pivot(win, app):
    _open_cloud(win, app)
    vp = win.viewport
    vp._pivot = np.array([3.0, -2.0, 1.0])
    vp._yaw = 0.4
    vp._pitch = 2.2
    vp._distance = 12.0
    vp._apply_camera()
    state = vp.camera_state()
    assert "pivot" in state

    vp._pivot = np.zeros(3)
    vp._apply_camera()
    assert vp.set_camera_state(state)
    np.testing.assert_allclose(vp._pivot, [3.0, -2.0, 1.0], atol=1e-5)
    np.testing.assert_allclose(vp._distance, 12.0, rtol=1e-5)
    vp.orbit_camera(0, 0)
    np.testing.assert_allclose(vp.camera.local.position, state["position"], atol=1e-5)
    np.testing.assert_allclose(vp.camera.local.rotation, state["rotation"], atol=1e-5)


def test_mesh_entity_add_and_remove(win, app):
    vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=np.float32)
    triangles = np.array([[0, 1, 2]], dtype=np.int32)
    mesh = MeshEntity("triangle", vertices=vertices, triangles=triangles)
    win.viewport.add_mesh_entity(mesh)
    assert win.viewport.mesh_entities == [mesh]
    assert len(win.viewport._mesh_objs) == 1

    win.viewport.remove_mesh_entity(mesh)
    assert win.viewport.mesh_entities == []
    assert win.viewport._mesh_objs == []


def test_poisson_mesh_can_be_rendered(win, app):
    from core.geometry import mesh as mesh_ops

    grid = np.stack(np.meshgrid(np.linspace(-1, 1, 12), np.linspace(-1, 1, 12),
                                indexing="ij"), axis=-1)
    xyz = np.column_stack([grid.reshape(-1, 2), np.zeros(grid.reshape(-1, 2).shape[0])])
    verts, tris = mesh_ops.poisson_mesh(xyz, depth=6)
    mesh = MeshEntity("recon", vertices=verts, triangles=tris)
    win.viewport.add_mesh_entity(mesh)
    assert len(win.viewport._mesh_objs) == 1
    assert win.viewport.reset_view() is None
