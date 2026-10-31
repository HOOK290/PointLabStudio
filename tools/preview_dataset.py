r"""预览指定数据集：打开目录、等待加载、截图（深色/浅色 + 不同颜色模式）。

用法：.venv\Scripts\python.exe tools/preview_dataset.py "D:\Desktop\lidar\1026mapping\li_init"
"""

from __future__ import annotations

import os
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from core.io.readers import ReadOptions, read_cloud
from ui.main_window import MainWindow

OUT = os.path.join(ROOT, ".tmp")


def analyze(path):
    e = read_cloud(path, ReadOptions())
    rgb = np.asarray(e.field("rgb"))
    mn, mx = e.bounds()
    print(f"\n{os.path.basename(path)}: {e.point_count:,} 点 · 包围盒 {np.round(mn,1)} ~ {np.round(mx,1)}")
    if rgb is not None:
        r = np.round(rgb[:, 0] * 255).astype(np.uint32)
        g = np.round(rgb[:, 1] * 255).astype(np.uint32)
        b = np.round(rgb[:, 2] * 255).astype(np.uint32)
        packed = (r << 16) | (g << 8) | b
        uniq = np.unique(packed)
        print(f"  唯一颜色数: {len(uniq)} · 前 6 种: {[hex(int(u)) for u in uniq[:6]]}")
        grayish = np.mean(np.abs(rgb[:, 0] - rgb[:, 2]) < 1e-6)
        print(f"  R==B 占比: {grayish:.3f} · 色彩标准差: {rgb.std(axis=0).round(4)}")
        # 与高度的相关性
        z = e.xyz[:, 2]
        for i, name in enumerate("RGB"):
            corr = np.corrcoef(z, rgb[:, i])[0, 1]
            print(f"  {name} 与高度 z 相关性: {corr:.3f}")


class Preview:
    def __init__(self, app, win, folder):
        self.app, self.win, self.folder = app, win, folder
        self.deadline = time.time() + 40
        QTimer.singleShot(200, self.start)

    def start(self):
        os.makedirs(OUT, exist_ok=True)
        t0 = time.time()
        self.win.open_paths([self.folder])
        print(f"[加载] 已发起，用时 {time.time() - t0:.1f}s，实体数 {len(self.win.entities)}")
        QTimer.singleShot(300, self.poll)

    def poll(self):
        pending = [e for e in self.win.entities if e.is_preview] or list(self.win._threads)
        if pending and time.time() < self.deadline:
            QTimer.singleShot(250, self.poll)
            return
        if time.time() >= self.deadline:
            print("[超时] 仍有未完成加载")
        print(f"[完成] 实体 {len(self.win.entities)} 个，累计 {sum(e.point_count for e in self.win.entities):,} 点")
        for e in self.win.entities:
            print(f"  - {e.name}: {e.point_count:,} 点 · tier={e.tier} · loaded={e.loaded:.2f}")
        QTimer.singleShot(2500, self.shots)  # 等待大点云 GPU 上传完成

    def grab(self, name):
        path = os.path.join(OUT, name)
        self.win.grab().save(path)
        print(f"   截图: {path}")

    def shots(self):
        # 1) 默认（auto → RGB）
        self.grab("data_auto.png")
        # 2) 高度着色
        for e in self.win.entities:
            e.color_mode = "height"
        self.win._refresh_scene()
        self.grab("data_height.png")
        # 3) 无颜色（灰）
        for e in self.win.entities:
            e.color_mode = "none"
        self.win._refresh_scene()
        self.grab("data_none.png")
        # 4) 恢复 auto
        for e in self.win.entities:
            e.color_mode = "auto"
        self.win._refresh_scene()
        print("[状态]", self.win.status_points.text(), "|", self.win.status_fps.text())
        self.win.viewport.stop()
        self.app.quit()


def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else r"D:\Desktop\lidar\1026mapping\li_init"
    files = sorted(f for f in os.listdir(folder) if f.lower().endswith(".pcd"))
    for f in files:
        analyze(os.path.join(folder, f))

    app = QApplication(sys.argv[:1])
    win = MainWindow(theme="dark")
    win.show()
    preview = Preview(app, win, folder)
    app._preview = preview
    QTimer.singleShot(120_000, app.quit)
    app.exec()
    print("PREVIEW OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
