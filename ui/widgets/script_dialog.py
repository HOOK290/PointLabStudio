"""内嵌 Python 脚本控制台：用脚本直接操作场景（批量化/自动化的起点）。

可用对象：win（主窗口）、entities（场景点云列表）、np、log()、read_cloud、ReadOptions。
执行结果与 print 输出写入主窗口日志。
"""

from __future__ import annotations

import contextlib
import io

import numpy as np
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout,
)

from core.io.readers import ReadOptions, read_cloud

TEMPLATE = """# 可用对象：win（主窗口）、entities（场景点云列表）、np、log()、read_cloud、ReadOptions
log(f"场景中有 {len(entities)} 片点云")
for e in entities:
    log(f"  {e.name}: {e.point_count:,} 点")
"""


class ScriptDialog(QDialog):
    def __init__(self, parent, win):
        super().__init__(parent)
        self.setWindowTitle("脚本控制台")
        self.setMinimumSize(560, 420)
        self._win = win

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 12)
        root.setSpacing(10)

        hint = QLabel("脚本与界面共用同一内核：可直接访问场景点云、调用处理算法。"
                      "print 输出与异常会写入主窗口日志。")
        hint.setObjectName("dim")
        hint.setWordWrap(True)
        root.addWidget(hint)

        self.editor = QPlainTextEdit()
        self.editor.setObjectName("scriptEditor")
        self.editor.setPlainText(TEMPLATE)
        root.addWidget(self.editor, 1)

        buttons = QHBoxLayout()
        self.btn_run = QPushButton("运行")
        self.btn_run.setObjectName("primary")
        self.btn_run.clicked.connect(self._run)
        buttons.addWidget(self.btn_run)
        buttons.addStretch(1)
        close_box = QDialogButtonBox(QDialogButtonBox.Close)
        close_box.button(QDialogButtonBox.Close).setText("关闭")
        close_box.rejected.connect(self.reject)
        buttons.addWidget(close_box)
        root.addLayout(buttons)

    def _run(self):
        code = self.editor.toPlainText()
        env = {
            "win": self._win,
            "entities": list(self._win.entities),
            "np": np,
            "log": self._win.log,
            "read_cloud": read_cloud,
            "ReadOptions": ReadOptions,
            "__name__": "__console__",
        }
        buffer = io.StringIO()
        try:
            with contextlib.redirect_stdout(buffer):
                exec(compile(code, "<console>", "exec"), env, env)
        except Exception as exc:  # noqa: BLE001
            self._win.log(f"[脚本错误] {type(exc).__name__}: {exc}")
        finally:
            self._win._refresh_scene()
            self._win._show_entity(self._win.scene_panel.current_entity())
        output = buffer.getvalue().strip()
        if output:
            self._win.log("[脚本输出]\n" + output)
        self._win.log("[脚本] 执行结束")
