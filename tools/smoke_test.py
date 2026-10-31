r"""P1 冒烟测试：启动真实主窗口，加载 S/M 数据，验证 Auto-Ingest 与渲染，截图。

用法：
    .venv\Scripts\python.exe tools/smoke_test.py
"""

from __future__ import annotations

import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow

SMALL = os.path.join(ROOT, "data", "scene_small.bin")
MEDIUM = os.path.join(ROOT, "data", "scene_medium.bin")
OUT = os.path.join(ROOT, ".tmp")


class Smoke:
    def __init__(self, app, win):
        self.app = app
        self.win = win
        self.fps = []
        self.win.viewport.fps_updated.connect(self.fps.append)
        self.start_time = time.time()
        os.makedirs(OUT, exist_ok=True)
        QTimer.singleShot(100, self.phase_empty)

    # ---------- 工具 ----------
    def sample(self, seconds: float, then):
        self.fps.clear()
        QTimer.singleShot(int(seconds * 1000), lambda: then([round(x) for x in self.fps]))

    def grab(self, name: str):
        os.makedirs(OUT, exist_ok=True)
        path = os.path.join(OUT, name)
        self.win.grab().save(path)
        print(f"   截图: {path}")

    def pump(self, seconds: float):
        end = time.time() + seconds
        while time.time() < end:
            self.app.processEvents()
            time.sleep(0.01)

    # ---------- 阶段 ----------
    def phase_empty(self):
        print(f"[1] 主窗口创建耗时 {time.time() - self.start_time:.2f}s")
        self.sample(1.5, self.after_empty)

    def after_empty(self, fps):
        print(f"[2] 空场景 FPS {fps}")
        t0 = time.time()
        self.win.open_paths([SMALL])
        e = self.win.entities[0]
        print(f"[3] S 级加载耗时 {time.time() - t0:.2f}s · {e.point_count:,} 点 · tier={e.tier}")
        self.sample(2.0, self.after_s)

    def after_s(self, fps):
        print(f"[4] S 级 FPS {fps}")
        t0 = time.time()
        self.win.open_paths([MEDIUM])
        print(f"[5] M 级预览就绪耗时 {time.time() - t0:.2f}s")
        if len(self.win.entities) > 1:
            e = self.win.entities[1]
            print(f"    预览: {e.point_count:,} 点 · loaded={e.loaded:.2f} · tier={e.tier}")
        self.deadline = time.time() + 25
        QTimer.singleShot(200, self.poll_full)

    def poll_full(self):
        e = next((x for x in self.win.entities if "medium" in (x.path or "")), None)
        if e is not None and e.loaded >= 1.0:
            print(f"[6] M 级全量加载: {e.point_count:,} 点 · tier={e.tier}")
            self.sample(2.0, self.after_m)
        elif time.time() > self.deadline:
            print("[6] !! M 级全量加载超时")
            self.after_m([])
        else:
            QTimer.singleShot(150, self.poll_full)

    def after_m(self, fps):
        print(f"[7] M 级 FPS {fps}")
        self.run_checks()
        # 展示裁剪范围线框，便于截图验证
        self.win._clip_fill_from_scene()
        self.pump(0.4)
        self.grab("studio_dark.png")
        self.win._clip_clear()
        self.win._set_theme("light")
        QTimer.singleShot(800, self.after_theme)

    def after_theme(self):
        self.grab("studio_light.png")
        print(f"[8] 状态: {self.win.status_points.text()} | {self.win.status_mem.text()} | "
              f"{self.win.status_fps.text()}")
        self.win.viewport.stop()
        self.app.quit()

    # ---------- 校验 ----------
    def run_checks(self):
        win = self.win
        results = []

        def check(name, fn):
            try:
                ok = bool(fn())
                results.append((name, "OK" if ok else "FAIL"))
            except Exception as exc:  # noqa: BLE001
                results.append((name, f"ERROR: {exc}"))

        def check_card_updated():
            summary = win.scene_panel.card_summary(1)
            return summary.get("points") == "5,000,000 点"

        def check_color():
            e = win.scene_panel.current_entity() or win.entities[0]
            before = e.color_mode
            win.viewport.key_cycle_color.emit()
            return e.color_mode != before

        def check_point_size():
            before = win.entities[0].point_size
            win.viewport.key_point_size.emit(0.5)
            return win.entities[0].point_size != before

        def check_clip():
            win._clip_fill_from_scene()  # 按包围盒填充并启用
            self.pump(0.4)
            applied = win.viewport._clip_box is not None
            win._clip_clear()
            self.pump(0.3)
            return applied and win.viewport._clip_box is None

        def check_visibility():
            entity = win.entities[0]
            before = entity.visible
            win.scene_panel.set_visible(entity, not before)
            changed = entity.visible != before
            win.scene_panel.set_visible(entity, before)
            return changed

        def check_project_save():
            p = os.path.join(OUT, "test.pls")
            if not win.save_project(p):
                return False
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
            return len(data.get("files", [])) == 2

        def check_voxel_undo():
            from core.algorithms import filters
            source = win.entities[0]
            voxel = max(source.extent() / 100.0, 1e-3)
            xyz, _c, _i = filters.voxel_downsample(source.xyz, voxel=voxel)
            entity = win._make_result(source, "体素测试", xyz, {}, "test")
            before = len(win.entities)
            win._on_filter_done("体素降采样", entity)
            added = len(win.entities) == before + 1
            win._undo()
            reverted = len(win.entities) == before
            win._redo()
            redone = len(win.entities) == before + 1
            win._undo()
            return added and reverted and redone

        def check_measure():
            import numpy as np
            vp = win.viewport
            vp.set_interaction_mode("measure")
            ok = False
            try:
                entity = win.entities[0]
                sx, sy, valid = vp._screen_coords(entity.xyz)
                idx = np.where(valid)[0]
                if len(idx) > 10:
                    i, j = int(idx[0]), int(idx[len(idx) // 2])
                    vp._on_measure_click(float(sx[i]), float(sy[i]))
                    vp._on_measure_click(float(sx[j]), float(sy[j]))
                    ok = vp.measure_label.isVisible() and "m" in vp.measure_label.text()
            finally:
                vp.set_interaction_mode(None)
            return ok

        def check_point_info():
            import numpy as np

            vp = win.viewport
            vp.set_interaction_mode("select")
            sx, sy, valid = vp._screen_coords(win.entities[0].xyz)
            idx = int(np.flatnonzero(valid)[0])
            vp._on_point_click(float(sx[idx]), float(sy[idx]))
            selected = vp._selected_point is not None and "X:" in vp.selection_label.text()
            vp.set_interaction_mode(None)
            return selected and vp._selected_point is None

        def check_pipeline():
            from core.pipeline import run_pipeline
            source = win.entities[0]
            steps = [{"op": "voxel", "params": {"voxel": max(source.extent() / 100.0, 1e-3)}}]
            before = len(win.entities)
            result = run_pipeline(source, steps)
            result.name = f"{source.name} · 处理链"
            win._on_filter_done("处理链", result)
            added = len(win.entities) == before + 1
            win._undo()
            self.pump(0.3)
            return added and len(win.entities) == before

        check("场景卡片点数更新", check_card_updated)
        check("颜色模式循环 (C)", check_color)
        check("点大小 +/-", check_point_size)
        check("裁剪范围开关 (B)", check_clip)
        check("可见性切换", check_visibility)
        check("工程保存 .pls", check_project_save)
        check("体素降采样 + 撤销/重做", check_voxel_undo)
        check("两点测距", check_measure)
        check("单点信息 + 退出清除", check_point_info)
        check("处理链 + 撤销", check_pipeline)

        print("[检查] 交互功能:")
        for name, status in results:
            print(f"   {status:>4}  {name}")


def main():
    app = QApplication(sys.argv)
    win = MainWindow(theme="dark")
    win.show()
    smoke = Smoke(app, win)
    app._smoke = smoke  # 保持引用，防止 Smoke 被垃圾回收导致定时器回调失效
    QTimer.singleShot(90_000, app.quit)  # 全局兜底超时
    app.exec()
    print("SMOKE OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
