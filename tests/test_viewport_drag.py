"""Regression checks for mouse navigation using real Qt mouse events/cameras."""
import unittest
from unittest.mock import patch

import numpy as np
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent, QWheelEvent
from PySide6.QtWidgets import QApplication

from ui.viewport.viewport import PointCloudViewport


class ViewportDragTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.viewport = PointCloudViewport()

    def tearDown(self):
        self.viewport.close()

    def drag(self, dx, dy, button=Qt.LeftButton, platform="darwin"):
        start = QPointF(200, 200)
        finish = QPointF(200 + dx, 200 + dy)
        with patch("sys.platform", platform):
            self.viewport.mousePressEvent(QMouseEvent(
                QEvent.MouseButtonPress, start, start,
                button, button, Qt.NoModifier,
            ))
            self.viewport.mouseMoveEvent(QMouseEvent(
                QEvent.MouseMove, finish, finish,
                Qt.NoButton, button, Qt.NoModifier,
            ))
            self.viewport.mouseReleaseEvent(QMouseEvent(
                QEvent.MouseButtonRelease, finish, finish,
                button, Qt.NoButton, Qt.NoModifier,
            ))

    def test_mac_upward_left_drag_lowers_camera_elevation(self):
        before = np.array(self.viewport.camera.local.position)
        self.drag(0, -40)
        after = np.array(self.viewport.camera.local.position)
        self.assertLess(after[2], before[2])
        self.assertAlmostEqual(np.linalg.norm(after), np.linalg.norm(before))

    def test_mac_downward_left_drag_raises_camera_elevation(self):
        before = self.viewport.camera.local.position[2]
        self.drag(0, 40)
        self.assertGreater(self.viewport.camera.local.position[2], before)

    def test_horizontal_drag_keeps_original_direction_and_height(self):
        before = np.array(self.viewport.camera.local.position)
        self.drag(40, 0)
        after = np.array(self.viewport.camera.local.position)
        self.assertLess(after[0], before[0])
        self.assertAlmostEqual(after[2], before[2])

    def test_fixed_height_navigation_keeps_pitch_and_position(self):
        self.viewport.set_fixed_view(True)
        before = np.array(self.viewport.camera.local.position)
        self.drag(30, -40)
        np.testing.assert_allclose(self.viewport.camera.local.position, before, atol=1e-12)

    def test_windows_keeps_original_vertical_direction(self):
        before = self.viewport.camera.local.position[2]
        self.drag(0, -40, platform="win32")
        self.assertGreater(self.viewport.camera.local.position[2], before)

    def test_right_drag_pans_without_rotating_camera(self):
        before = np.array(self.viewport.camera.local.position) - self.viewport._pivot
        pivot = self.viewport._pivot.copy()
        self.drag(0, 40, button=Qt.RightButton)
        after = np.array(self.viewport.camera.local.position) - self.viewport._pivot
        np.testing.assert_allclose(after, before, atol=1e-12)
        self.assertGreater(np.linalg.norm(self.viewport._pivot - pivot), 0)

    def test_positive_wheel_delta_keeps_zoom_in_direction(self):
        before = self.viewport._distance
        event = QWheelEvent(
            QPointF(200, 200), QPointF(200, 200), QPoint(), QPoint(0, 120),
            Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False,
        )
        self.viewport.wheelEvent(event)
        self.assertLess(self.viewport._zoom_target, before)

    def wheel(self, angle=0, pixels=0, inverted=False):
        event = QWheelEvent(
            QPointF(200, 200), QPointF(200, 200), QPoint(0, pixels), QPoint(0, angle),
            Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, inverted,
        )
        self.viewport.wheelEvent(event)
        self.assertTrue(event.isAccepted())

    def test_physical_wheel_zoom_is_independent_of_natural_scrolling(self):
        for physical_direction in (-1, 1):
            with self.subTest(direction=physical_direction):
                self.viewport._sync_zoom()
                self.wheel(angle=physical_direction * 120)
                normal_target = self.viewport._zoom_target
                self.viewport._sync_zoom()
                self.wheel(angle=-physical_direction * 120, inverted=True)
                self.assertAlmostEqual(self.viewport._zoom_target, normal_target)

    def test_pixel_wheel_zoom_is_independent_of_natural_scrolling(self):
        for physical_direction in (-1, 1):
            with self.subTest(direction=physical_direction):
                self.viewport._sync_zoom()
                self.wheel(pixels=physical_direction * 50, angle=physical_direction * 120)
                normal_target = self.viewport._zoom_target
                self.viewport._sync_zoom()
                self.wheel(pixels=-physical_direction * 50,
                           angle=-physical_direction * 120, inverted=True)
                self.assertAlmostEqual(self.viewport._zoom_target, normal_target)

    def test_fixed_height_wheel_motion_is_independent_of_natural_scrolling(self):
        self.viewport.set_fixed_view(True)
        self.wheel(angle=120)
        normal_walk = self.viewport._walk_remaining
        self.viewport._sync_zoom()
        self.wheel(angle=-120, inverted=True)
        self.assertGreater(normal_walk, 0)
        self.assertAlmostEqual(self.viewport._walk_remaining, normal_walk, places=12)

    def test_zero_wheel_delta_does_not_start_zoom(self):
        before = self.viewport._distance
        self.wheel(inverted=True)
        self.assertEqual(self.viewport._zoom_target, before)
        self.assertFalse(self.viewport._zoom_animating)


if __name__ == "__main__":
    unittest.main()
