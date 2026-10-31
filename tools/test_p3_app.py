r"""P3 应用级验证：地面提取、DBSCAN 聚类、ICP 配准 + 截图。"""

import os
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from core.algorithms import registration, segmentation
from core.model.entities import CloudEntity, ScalarField
from ui.main_window import MainWindow

SMALL = os.path.join(ROOT, "data", "scene_small.bin")
OUT = os.path.join(ROOT, ".tmp")


class Test:
    def __init__(self, app, win):
        self.app, self.win = app, win
        self.deadline = time.time() + 60
        QTimer.singleShot(300, self.start)

    def start(self):
        self.win.open_paths([SMALL])
        QTimer.singleShot(300, self.poll)

    def poll(self):
        pending = [e for e in self.win.entities if e.is_preview] or list(self.win._threads)
        if pending and time.time() < self.deadline:
            QTimer.singleShot(300, self.poll)
            return
        self.run_ground()

    def pump(self, seconds):
        end = time.time() + seconds
        while time.time() < end:
            self.app.processEvents()
            time.sleep(0.01)

    def run_ground(self):
        win = self.win
        source = win.entities[0]
        t0 = time.time()
        (normal, d), mask = segmentation.extract_ground(source.xyz, distance=0.3)
        print(f"[地面] {int(mask.sum()):,}/{source.point_count:,} 点 · {time.time()-t0:.2f}s · "
              f"n=({normal[0]:.2f},{normal[1]:.2f},{normal[2]:.2f})", flush=True)
        entity = win._make_result(source, "地面", source.xyz[mask],
                                  win._subset_fields(source, mask), "地面提取（测试）")
        win._on_filter_done("地面提取", entity)
        self.pump(1.5)
        win.grab().save(os.path.join(OUT, "p3_ground.png"))
        print("   截图: .tmp/p3_ground.png", flush=True)
        self.run_dbscan()

    def run_dbscan(self):
        win = self.win
        source = win.entities[0]
        t0 = time.time()
        labels = segmentation.dbscan(source.xyz, eps=1.2, min_samples=6)
        clusters = int(labels.max()) if (labels >= 0).any() else 0
        print(f"[DBSCAN] {clusters} 簇 · 噪声 {int((labels < 0).sum()):,} · "
              f"{time.time()-t0:.2f}s", flush=True)
        fields = win._copy_fields(source)
        fields["labels"] = ScalarField("labels", labels.astype(np.float32))
        entity = win._make_result(source, f"聚类{clusters}", source.xyz, fields,
                                  f"DBSCAN eps=1.2 min=6｜{clusters} 簇")
        entity.color_mode = "label"
        win._on_filter_done("DBSCAN 聚类", entity)
        self.pump(1.5)
        win.grab().save(os.path.join(OUT, "p3_dbscan.png"))
        print("   截图: .tmp/p3_dbscan.png", flush=True)
        self.run_icp()

    def run_icp(self):
        win = self.win
        # 合成一个三维分布良好的点云（平面场景绕法向旋转不可观测，属算法固有退化）
        rng = np.random.default_rng(7)
        angle = np.deg2rad(6.0)
        rot = np.array([[1, 0, 0],
                        [0, np.cos(angle), -np.sin(angle)],
                        [0, np.sin(angle), np.cos(angle)]])
        T_true = np.eye(4)
        T_true[:3, :3] = rot
        T_true[:3, 3] = [2.0, -1.5, 0.4]
        base = rng.uniform(-5, 5, (30000, 3)).astype(np.float32)
        target_xyz = registration.apply_transform(base, T_true)
        source = CloudEntity(name="ICP 源（合成）", path=None, xyz=base, fields={})
        target = CloudEntity(name="ICP 目标（合成）", path=None, xyz=target_xyz, fields={})
        win._add_entity(source)
        win._add_entity(target)
        win.scene_panel.select_entity(source)

        t0 = time.time()
        T, rmse = registration.icp(base, target_xyz, max_iterations=60)
        err = float(np.mean(np.linalg.norm(
            registration.apply_transform(base, T) - target_xyz, axis=1)))
        print(f"[ICP] rmse={rmse:.4f} err={err:.4f} · {time.time()-t0:.2f}s", flush=True)
        entity = win._make_result(source, "ICP配准",
                                  registration.apply_transform(base, T),
                                  {}, f"ICP 测试 RMSE={rmse:.4f}")
        win._on_filter_done("ICP 配准", entity)
        self.pump(1.5)
        win.grab().save(os.path.join(OUT, "p3_icp.png"))
        print("   截图: .tmp/p3_icp.png", flush=True)
        print("P3 校验:", "OK" if err < 0.05 else "FAIL", flush=True)
        self.app.quit()


def main():
    app = QApplication(sys.argv[:1])
    win = MainWindow(theme="dark")
    win.show()
    test = Test(app, win)
    app._test = test
    os.makedirs(OUT, exist_ok=True)
    QTimer.singleShot(120_000, app.quit)
    app.exec()
    print("P3 TEST DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
