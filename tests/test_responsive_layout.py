import time

import numpy as np
import pytest
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from core.model.entities import CloudEntity
from ui.main_window import MainWindow


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def win(app):
    window = MainWindow()
    window.showNormal()
    window._add_entity(CloudEntity("layout", xyz=np.array([[0, 0, 0], [1, 1, 1]], np.float32)))
    app.processEvents()
    yield window
    window.clip_popup.hide()
    window.close()
    deadline = time.monotonic() + 5
    while window.isVisible() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(.01)


def _rect_in(widget, parent):
    return QRect(widget.mapTo(parent, QPoint()), widget.size())


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_header_reflows_without_compressing_or_overlapping_controls(win, app, theme):
    win._set_theme(theme)
    header = win.centralWidget().layout().itemAt(0).widget()
    buttons = [win.btn_open, win.btn_project, win.btn_process, win.btn_view,
               win.btn_undo, win.btn_redo, win.btn_measure, win.btn_select,
               win.btn_box_select, win.btn_clip, win.btn_reset, win.btn_theme]
    controls = buttons + [win.cmb_color, win.sld_size, win.lbl_size]
    wide = min(1400, win.screen().availableGeometry().width() - 16)
    for width in (wide, 1280, 1024, 980, wide):
        win.resize(width, 740)
        QTest.qWait(80)
        assert win.width() == width
        rects = [_rect_in(widget, header) for widget in controls]
        for widget, rect in zip(controls, rects):
            assert widget.isVisible()
            assert header.rect().contains(rect), (width, widget.objectName(), rect)
        for i, rect in enumerate(rects):
            assert all(not rect.intersects(other) for other in rects[i + 1:]), width
        for button in buttons:
            assert button.width() >= 36 and button.height() >= 32
            assert button.iconSize().width() == 18
        assert win.sld_size.width() == 80
        assert header._compact == (width < header._wide_width)
        win.sld_size.setValue(20)
        app.processEvents()
        assert win.entities[0].point_size == 10
        QTest.mouseClick(win.btn_select, Qt.LeftButton)
        assert win.viewport._mode == "select"
        QTest.mouseClick(win.btn_select, Qt.LeftButton)


@pytest.mark.parametrize("fullscreen", [False, True])
def test_clip_popup_and_inputs_stay_inside_screen(win, app, fullscreen):
    if fullscreen:
        win.showFullScreen()
    else:
        win.resize(980, 680)
    QTest.qWait(100)
    win._show_clip_popup()
    QTest.qWait(100)
    popup = win.clip_popup
    bounds = win.screen().availableGeometry()
    assert bounds.contains(popup.frameGeometry())
    for spin in popup._spins.values():
        assert popup.rect().contains(_rect_in(spin, popup))
        assert spin.width() >= spin.minimumSizeHint().width()
    popup.set_values([-123456.78] * 3, [123456.78] * 3)
    popup.set_enabled(True)
    popup._spins["X min"].setValue(200000)
    popup._emit_values()
    app.processEvents()
    assert popup.lbl_warning.isVisible()
    assert bounds.contains(popup.frameGeometry())
