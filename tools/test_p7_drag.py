r"""可视化验证：单点信息与固定尺寸测量标记。"""

import os
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow

SMALL = os.path.join(ROOT, "data", "scene_small.bin")
OUT = os.path.join(ROOT, ".tmp")


def pump(app, seconds):
    end = time.time() + seconds
    while time.time() < end:
        app.processEvents()
        time.sleep(0.01)


def main():
    os.makedirs(OUT, exist_ok=True)
    app = QApplication(sys.argv[:1])
    win = MainWindow(theme="dark")
    win.resize(1280, 820)
    win.show()
    pump(app, 0.6)
    win.open_paths([SMALL])
    pump(app, 2.5)
    vp = win.viewport

    sx, sy, valid = vp._screen_coords(win.entities[0].xyz)
    valid &= (sx > 20) & (sx < vp.width() - 20) & (sy > 20) & (sy < vp.height() - 20)
    idx = np.flatnonzero(valid)
    i, j = int(idx[len(idx) // 3]), int(idx[2 * len(idx) // 3])
    win._set_tool("select")
    pump(app, 0.3)
    QTest.mouseClick(vp._subwidget, Qt.LeftButton, pos=QPoint(int(sx[i]), int(sy[i])))
    pump(app, 0.3)
    assert vp._selected_point is not None
    win.grab().save(os.path.join(OUT, "p7_point_info.png"))
    win._set_tool(None)
    pump(app, 0.2)

    # 测距结果
    win._set_tool("measure")
    pump(app, 0.3)
    QTest.mouseClick(vp._subwidget, Qt.LeftButton, pos=QPoint(int(sx[i]), int(sy[i])))
    pump(app, 0.2)
    QTest.mouseClick(vp._subwidget, Qt.LeftButton, pos=QPoint(int(sx[j]), int(sy[j])))
    pump(app, 0.3)
    win.grab().save(os.path.join(OUT, "p7_measure.png"))
    print("saved p7_measure.png |", vp.measure_label.text())
    win._set_tool(None)
    win.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
