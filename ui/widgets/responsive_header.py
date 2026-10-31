"""宽度不足时将视图工具换到第二行，保留控件的正常尺寸。"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLayout, QSizePolicy, QVBoxLayout, QWidget


class ResponsiveHeader(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("appHeader")
        self.setAttribute(Qt.WA_StyledBackground, True)
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 8, 12, 8)
        root.setSpacing(6)
        self.primary = QWidget()
        self.primary.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.row = QHBoxLayout(self.primary)
        self.row.setContentsMargins(0, 0, 0, 0)
        self.row.setSpacing(6)
        self.row.setSizeConstraint(QLayout.SetNoConstraint)
        root.addWidget(self.primary)
        self.secondary = QWidget()
        self.tools_row = QHBoxLayout(self.secondary)
        self.tools_row.setContentsMargins(0, 0, 0, 0)
        self.tools_row.addStretch(1)
        root.addWidget(self.secondary)
        self.secondary.hide()
        self._tools = None
        self._compact = False

    def set_tools(self, tools, separator):
        self._tools = tools
        self._separator = separator
        self._tools_index = self.row.indexOf(tools)
        self.ensurePolished()
        tools.setFixedSize(tools.sizeHint())
        self._wide_width = self.row.sizeHint().width() + 28
        self._adapt()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._adapt()

    def _adapt(self):
        if self._tools is None:
            return
        compact = self.width() < self._wide_width
        if compact == self._compact:
            return
        self._compact = compact
        if compact:
            self.row.removeWidget(self._tools)
            self.tools_row.addWidget(self._tools)
        else:
            self.tools_row.removeWidget(self._tools)
            self.row.insertWidget(self._tools_index, self._tools)
        self._separator.setVisible(not compact)
        self.secondary.setVisible(compact)
        self._tools.show()
        self.updateGeometry()
