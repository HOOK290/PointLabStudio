"""E21：4×4 变换矩阵编辑器。"""

from __future__ import annotations

import numpy as np
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QDoubleSpinBox, QGridLayout, QLabel, QPushButton,
    QVBoxLayout, QWidget,
)


class TransformDialog(QDialog):
    """编辑 4×4 刚体变换：3×3 旋转 + 平移，实时显示组合结果。"""

    def __init__(self, parent=None, matrix=None, title="变换矩阵"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(430)

        root = QVBoxLayout(self)
        hint = QLabel("旋转（3×3）与平移（m）；点坐标按 p' = R·p + t 变换。")
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        root.addWidget(hint)

        grid = QWidget()
        lay = QGridLayout(grid)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setHorizontalSpacing(6)
        lay.setVerticalSpacing(6)
        self._spins = [[None] * 4 for _ in range(3)]
        for row in range(3):
            for col in range(4):
                spin = QDoubleSpinBox()
                spin.setDecimals(5)
                spin.setRange(-1e6, 1e6)
                spin.setSingleStep(0.01)
                spin.setMinimumWidth(76)
                lay.addWidget(spin, row, col)
                self._spins[row][col] = spin
        root.addWidget(grid)

        buttons = QWidget()
        row = QGridLayout(buttons)
        row.setContentsMargins(0, 0, 0, 0)
        self.btn_identity = QPushButton("单位矩阵")
        self.btn_identity.clicked.connect(self.reset_identity)
        self.btn_swap = QPushButton("反转旋转")
        self.btn_swap.clicked.connect(self.invert_rotation)
        row.addWidget(self.btn_identity, 0, 0)
        row.addWidget(self.btn_swap, 0, 1)
        root.addWidget(buttons)

        box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)
        root.addWidget(box)

        self.set_matrix(np.eye(4) if matrix is None else matrix)

    def set_matrix(self, matrix):
        m = np.asarray(matrix, dtype=np.float64)
        if m.shape != (4, 4):
            raise ValueError("需要 4×4 矩阵")
        for row in range(3):
            for col in range(4):
                self._spins[row][col].setValue(float(m[row, col]))

    def matrix(self) -> np.ndarray:
        m = np.eye(4, dtype=np.float64)
        for row in range(3):
            for col in range(4):
                m[row, col] = self._spins[row][col].value()
        return m

    def reset_identity(self):
        self.set_matrix(np.eye(4))

    def invert_rotation(self):
        """把旋转部分转置（正交矩阵的逆），平移保持不变。"""
        m = self.matrix()
        m[:3, :3] = m[:3, :3].T
        self.set_matrix(m)
