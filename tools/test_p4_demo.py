r"""P4 可视化验证：两点测距 + 单点信息。"""

import os
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow

SMALL = os.path.join(ROOT, "data", "scene_small.bin")
OUT = os.path.join(ROOT, ".tmp")


class Demo:
    def __init__(self, app, win):
        self.app, self.win = app, win
        QTimer.singleShot(300, self.start)

    def pump(self, seconds):
        end = time.time() + seconds
        while time.time() < end:
            self.app.processEvents()
            time.sleep(0.01)

    def start(self):
        self.win.open_paths([SMALL])
        self.pump(3.0)
        self.measure()

    def measure(self):
        vp = self.win.viewport
        entity = self.win.entities[0]
        vp.set_interaction_mode("measure")
        sx, sy, ok = vp._screen_coords(entity.xyz)
        idx = np.where(ok)[0]
        i, j = int(idx[len(idx) // 3]), int(idx[2 * len(idx) // 3])
        vp._on_measure_click(float(sx[i]), float(sy[i]))
        vp._on_measure_click(float(sx[j]), float(sy[j]))
        self.pump(0.6)
        self.win.grab().save(os.path.join(OUT, "p4_measure.png"))
        print("saved p4_measure.png", flush=True)
        vp.set_interaction_mode(None)
        self.select()

    def select(self):
        vp = self.win.viewport
        vp.set_interaction_mode("select")
        sx, sy, valid = vp._screen_coords(self.win.entities[0].xyz)
        idx = int(np.flatnonzero(valid)[0])
        vp._on_point_click(float(sx[idx]), float(sy[idx]))
        self.pump(0.5)
        self.win.grab().save(os.path.join(OUT, "p4_select.png"))
        print("saved p4_select.png", flush=True)
        vp.set_interaction_mode(None)
        self.app.quit()


def main():
    os.makedirs(OUT, exist_ok=True)
    app = QApplication(sys.argv[:1])
    win = MainWindow(theme="dark")
    win.show()
    demo = Demo(app, win)
    app._demo = demo
    QTimer.singleShot(90_000, app.quit)
    app.exec()
    print("P4 DEMO DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
