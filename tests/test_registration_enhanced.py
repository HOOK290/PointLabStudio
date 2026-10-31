"""E21：点到面 ICP、FPFH+RANSAC 全局配准、变换矩阵编辑器。"""

from __future__ import annotations

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from core.algorithms.registration import (
    apply_transform, estimate_normals, global_registration, icp_point_to_plane,
)
from ui.widgets.transform_dialog import TransformDialog


def _bumpy(n=4000, seed=2):
    rng = np.random.default_rng(seed)
    x = rng.uniform(-2, 2, n)
    y = rng.uniform(-2, 2, n)
    return x, y, 0.3 * np.sin(2 * x) + 0.2 * np.cos(3 * y)


def test_estimate_normals_on_plane():
    rng = np.random.default_rng(0)
    xyz = np.c_[rng.uniform(-1, 1, 300), rng.uniform(-1, 1, 300), np.zeros(300)]
    normals = estimate_normals(xyz, k=12)
    assert normals.shape == (300, 3)
    assert np.allclose(np.abs(normals[:, 2]), 1.0, atol=1e-3)


def test_point_to_plane_recovers_small_rotation_and_translation():
    x, y, z = _bumpy()
    target = np.c_[x, y, z]
    a = np.deg2rad(5.0)
    rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    b = np.deg2rad(3.0)
    rx = np.array([[1, 0, 0], [0, np.cos(b), -np.sin(b)], [0, np.sin(b), np.cos(b)]])
    source = target @ (rx @ rz).T + np.array([0.15, -0.1, 0.08])

    transform, rmse = icp_point_to_plane(source, target, max_iterations=60)
    moved = apply_transform(source, transform)
    assert np.abs(moved - target).mean() < 1e-3
    assert rmse < 1e-3
    assert transform.shape == (4, 4)


def test_global_registration_finds_translation():
    x, y, z = _bumpy(1200, seed=3)
    target = np.c_[x, y, z]
    source = target + np.array([0.05, -0.04, 0.03])
    transform, fitness, inlier_rmse = global_registration(
        source, target, voxel_size=0.08, max_iterations=50_000)
    assert fitness > 0.5
    assert inlier_rmse < 0.05
    assert np.abs(apply_transform(source, transform) - target).mean() < 0.01


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_transform_dialog_roundtrip(app):
    dlg = TransformDialog()
    m = np.eye(4)
    m[:3, 3] = [1.5, -2.0, 0.25]
    dlg.set_matrix(m)
    assert np.allclose(dlg.matrix(), m)

    dlg.invert_rotation()
    rotated = dlg.matrix()
    assert np.allclose(rotated[:3, :3], np.eye(3))
    assert np.allclose(rotated[:3, 3], m[:3, 3])

    dlg.reset_identity()
    assert np.allclose(dlg.matrix(), np.eye(4))
