"""「裁剪范围」弹出面板：启用开关 + 六向范围输入 + 按包围盒 / 清除。

作为顶栏按钮的下拉浮层使用（Qt.Popup），输入变化防抖后发出范围信号，
视口中会同步显示橙色线框，直观看到裁剪范围大小。
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox, QDoubleSpinBox, QGridLayout, QHBoxLayout, QLabel, QPushButton,
    QVBoxLayout, QWidget,
)


class ClipPopup(QWidget):
    enabled_changed = Signal(bool)
    values_changed = Signal(list, list)   # mn3, mx3（已防抖）
    fill_requested = Signal()
    clear_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Popup)
        self.setObjectName("clipPopup")
        self.setMinimumWidth(320)
        self._anchor = None

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(10)

        head = QHBoxLayout()
        title = QLabel("裁剪范围")
        title.setObjectName("sectionTitle")
        head.addWidget(title)
        head.addStretch(1)
        self.chk_enable = QCheckBox("启用")
        head.addWidget(self.chk_enable)
        root.addLayout(head)

        hint = QLabel("拖动橙色手柄调整范围，Esc 取消拖动。此处只改变显示；要保存框内点，请选择「工程 → 导出裁剪内点云」。")
        hint.setObjectName("dim")
        hint.setWordWrap(True)
        root.addWidget(hint)

        grid = QGridLayout()
        grid.setSpacing(6)
        self._spins = {}
        for row, axis in enumerate(("X", "Y", "Z")):
            for col, suffix in enumerate(("min", "max")):
                spin = QDoubleSpinBox()
                spin.setRange(-1e9, 1e9)
                spin.setDecimals(4)
                spin.setMinimumWidth(88)
                label = QLabel(f"{axis} {suffix}")
                label.setObjectName("dim")
                self._spins[f"{axis} {suffix}"] = spin
                grid.addWidget(label, row, col * 2)
                grid.addWidget(spin, row, col * 2 + 1)
        root.addLayout(grid)

        self.lbl_warning = QLabel("范围无效：每个轴的 min 必须小于 max，已忽略本次修改。")
        self.lbl_warning.setObjectName("warning")
        self.lbl_warning.setWordWrap(True)
        self.lbl_warning.hide()
        root.addWidget(self.lbl_warning)

        btns = QHBoxLayout()
        self.btn_fill = QPushButton("按包围盒")
        self.btn_clear = QPushButton("清除")
        btns.addWidget(self.btn_fill)
        btns.addWidget(self.btn_clear)
        root.addLayout(btns)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(200)
        self._timer.timeout.connect(self._emit_values)

        self.chk_enable.toggled.connect(self._on_enabled)
        for spin in self._spins.values():
            spin.valueChanged.connect(self._on_spin_changed)
        self.btn_fill.clicked.connect(self.fill_requested.emit)
        self.btn_clear.clicked.connect(self.clear_requested.emit)

    # ---------------- 接口 ----------------
    def show_for(self, anchor):
        self._anchor = anchor
        self.ensurePolished()
        self.adjustSize()
        self._position_at_anchor()
        self.show()
        self._position_at_anchor()

    def _position_at_anchor(self):
        if self._anchor is None:
            return
        anchor = self._anchor
        point = anchor.mapToGlobal(QPoint(0, anchor.height() + 6))
        screen = QGuiApplication.screenAt(anchor.mapToGlobal(anchor.rect().center()))
        screen = screen or anchor.screen()
        bounds = screen.availableGeometry().adjusted(6, 6, -6, -6)
        window = anchor.window()
        client = QRect(window.mapToGlobal(QPoint()), window.size()).intersected(bounds)
        if client.width() >= self.width() and client.height() >= self.height():
            bounds = client
        x = max(bounds.left(), min(point.x(), bounds.right() - self.width() + 1))
        y = point.y()
        if y + self.height() > bounds.bottom() + 1:
            y = anchor.mapToGlobal(QPoint()).y() - self.height() - 6
        y = max(bounds.top(), min(y, bounds.bottom() - self.height() + 1))
        self.move(x, y)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.isVisible():
            self._position_at_anchor()

    def is_enabled(self) -> bool:
        return self.chk_enable.isChecked()

    def set_enabled(self, enabled: bool):
        self.chk_enable.blockSignals(True)
        self.chk_enable.setChecked(bool(enabled))
        self.chk_enable.blockSignals(False)

    def values(self):
        mn = [self._spins[k].value() for k in ("X min", "Y min", "Z min")]
        mx = [self._spins[k].value() for k in ("X max", "Y max", "Z max")]
        return mn, mx

    def values_valid(self) -> bool:
        mn, mx = self.values()
        return all(lo < hi for lo, hi in zip(mn, mx))

    def set_values(self, mn, mx):
        self._timer.stop()
        self.lbl_warning.hide()
        values = {
            "X min": mn[0], "X max": mx[0],
            "Y min": mn[1], "Y max": mx[1],
            "Z min": mn[2], "Z max": mx[2],
        }
        for key, value in values.items():
            spin = self._spins[key]
            spin.blockSignals(True)
            spin.setValue(float(value))
            spin.blockSignals(False)

    # ---------------- 内部 ----------------
    def _on_enabled(self, checked: bool):
        self.enabled_changed.emit(bool(checked))
        if checked:
            self._timer.start()

    def _on_spin_changed(self, *_args):
        if not self.chk_enable.isChecked():
            return
        self._timer.start()

    def _emit_values(self):
        if not self.chk_enable.isChecked():
            return
        mn, mx = self.values()
        valid = all(lo < hi for lo, hi in zip(mn, mx))
        self.lbl_warning.setVisible(not valid)
        if not valid:
            return
        self.values_changed.emit(mn, mx)
