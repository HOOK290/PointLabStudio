r"""全功能审计：用真实 UI 事件逐项走查每个入口，输出 PASS/FAIL 汇总。

不依赖 pytest；运行：
    .venv\Scripts\python.exe -u tools/audit_all.py
"""

import json
import os
import shutil
import subprocess
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog

import ui.main_window as mw
from core.model.entities import CloudEntity
from ui.main_window import MainWindow

SMALL = os.path.join(ROOT, "data", "scene_small.bin")
MEDIUM = os.path.join(ROOT, "data", "scene_medium.bin")
TMP = os.path.join(ROOT, ".tmp")
RESULTS = []


def wait_until(app, pred, timeout=25.0):
    end = time.time() + timeout
    while time.time() < end:
        app.processEvents()
        time.sleep(0.01)
        if pred():
            return True
    return False


def pump(app, seconds=0.25):
    end = time.time() + seconds
    while time.time() < end:
        app.processEvents()
        time.sleep(0.01)


def check(name, fn):
    try:
        ok = bool(fn())
        detail = ""
    except Exception as exc:  # noqa: BLE001
        ok = False
        detail = f"{type(exc).__name__}: {exc}"
    RESULTS.append((name, ok, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{('  — ' + detail) if detail else ''}", flush=True)
    return ok


def find_action(menu, text):
    for act in menu.actions():
        if act.text() == text:
            return act
        if act.menu() is not None:
            found = find_action(act.menu(), text)
            if found is not None:
                return found
    return None


def main():
    os.makedirs(TMP, exist_ok=True)
    app = QApplication(sys.argv[:1])
    win = MainWindow(theme="dark")
    win.show()
    pump(app, 0.4)

    # 自动接受所有参数对话框（用默认值），这样能走完整的菜单→对话框→线程链路
    mw.ParamDialog.exec = lambda self: QDialog.Accepted

    class AutoPipelineDialog(mw.PipelineDialog):
        def exec(self):
            self._steps = [{"op": "voxel", "params": {"voxel": 1.0}},
                           {"op": "sor", "params": {"k": 10, "std": 2.0}}]
            self._refresh()
            return QDialog.Accepted

    mw.PipelineDialog = AutoPipelineDialog

    print("=== 加载与场景 ===")
    win.open_paths([SMALL])
    check("打开文件（同步加载）", lambda: wait_until(app, lambda: len(win.entities) == 1)
          and win.entities[0].point_count == 200_000)
    if not win.entities:
        print("测试数据缺失：请先运行 tools/make_test_data.py --out data")
        return 2
    source = win.entities[0]
    check("场景卡片点数", lambda: win.scene_panel.card_summary(0)["points"] == "200,000 点")
    check("右侧概览名称/点数", lambda: win.overview.lbl_name.text() == source.name
          and win.overview.lbl_points.text() == "200,000")
    check("右侧概览单位 (m)", lambda: "m" in win.overview.v_x.text())

    card = win.scene_panel._rows[0][1]

    def toggle_visibility():
        QTest.mouseClick(card.dot, Qt.LeftButton, pos=card.dot.rect().center())
        pump(app, 0.4)
        hidden = not source.visible and len(win.viewport._points_objs) == 0
        QTest.mouseClick(card.dot, Qt.LeftButton, pos=card.dot.rect().center())
        pump(app, 0.4)
        return hidden and source.visible and len(win.viewport._points_objs) > 0

    check("场景勾选框切换显示", toggle_visibility)

    def select_card():
        QTest.mouseClick(card, Qt.LeftButton, pos=card.rect().center())
        pump(app, 0.2)
        return win.scene_panel.current_entity() is source

    check("点击卡片选中", select_card)

    print("=== 视图控制 ===")

    def color_combo():
        index = [win.cmb_color.itemData(i) for i in range(win.cmb_color.count())].index("rgb")
        win.cmb_color.setCurrentIndex(index)
        pump(app, 0.3)
        return source.color_mode == "rgb" and "RGB" in win.overview.v_colormode.text().upper()

    check("颜色模式下拉", color_combo)

    def cmap_action():
        act = next((a for a in win._cmap_group if a.text() == "turbo"), None)
        act.trigger()
        pump(app, 0.3)
        return source.colormap == "turbo" and win.overview.v_colormap.text() == "turbo"

    check("视图→色彩映射", cmap_action)

    def point_size():
        win.sld_size.setValue(12)
        pump(app, 0.2)
        return abs(source.point_size - 6.0) < 0.01 and win.lbl_size.text() == "6.0" \
            and win.overview.v_pointsize.text().startswith("6.0")

    check("点大小滑条", point_size)

    def key_color():
        before = source.color_mode
        QTest.keyClick(win.viewport, Qt.Key_C)
        pump(app, 0.2)
        return source.color_mode != before

    check("快捷键 C 循环颜色", key_color)

    def key_size():
        before = source.point_size
        QTest.keyClick(win.viewport, Qt.Key_Plus)
        pump(app, 0.2)
        return source.point_size > before

    check("快捷键 +/- 点大小", key_size)

    def clip_keys():
        QTest.keyClick(win.viewport, Qt.Key_B)
        pump(app, 0.3)
        on = win.viewport._clip_box is not None
        QTest.keyClick(win.viewport, Qt.Key_B)
        pump(app, 0.3)
        return on and win.viewport._clip_box is None

    check("快捷键 B 开关裁剪", clip_keys)

    def clip_fill():
        win._clip_fill_from_scene()
        pump(app, 0.3)
        on = win.viewport._clip_box is not None and win.clip_popup.is_enabled()
        win._clip_clear()
        pump(app, 0.2)
        return on and win.viewport._clip_box is None

    check("裁剪按包围盒填充/清除", clip_fill)

    def clip_undo():
        before = win._clip_state()
        win._toggle_clipbox()
        pump(app, 0.3)
        on = win.viewport._clip_box is not None
        win._undo()
        pump(app, 0.3)
        undone = win._clip_states_equal(win._clip_state(), before)
        win._redo()
        pump(app, 0.3)
        redone = win.viewport._clip_box is not None
        win._undo()
        pump(app, 0.2)
        return on and undone and redone

    check("裁剪可撤销/重做（B 键）", clip_undo)

    def clip_popup_undo():
        win._show_clip_popup()
        pump(app, 0.2)
        before = win._clip_state()
        win.clip_popup.set_values([-5.0, -5.0, -5.0], [5.0, 5.0, 5.0])
        # 真实点击「启用」复选框（set_enabled 会阻塞信号，不代表用户操作）
        QTest.mouseClick(win.clip_popup.chk_enable, Qt.LeftButton,
                         pos=win.clip_popup.chk_enable.rect().center())
        pump(app, 0.8)
        changed = win.viewport._clip_box is not None and win.history.can_undo
        win.clip_popup.hide()
        pump(app, 0.3)
        win._undo()
        pump(app, 0.3)
        restored = win._clip_states_equal(win._clip_state(), before)
        return changed and restored

    check("裁剪弹层修改可撤销", clip_popup_undo)

    def space_key():
        before = source.visible
        win.scene_panel.select_entity(source)
        QTest.keyClick(win.viewport, Qt.Key_Space)
        pump(app, 0.3)
        changed = source.visible != before
        QTest.keyClick(win.viewport, Qt.Key_Space)
        pump(app, 0.2)
        return changed

    check("快捷键 Space 显示/隐藏", space_key)

    def help_key():
        before = win.log_view.toPlainText()
        QTest.keyClick(win.viewport, Qt.Key_H)
        pump(app, 0.2)
        return "快捷键" in win.log_view.toPlainText()[len(before):]

    check("快捷键 H 帮助", help_key)

    def log_drawer():
        QTest.mouseClick(win.btn_log, Qt.LeftButton)
        pump(app, 0.3)
        shown = win.log_view.isVisible()
        QTest.mouseClick(win.btn_log, Qt.LeftButton)
        pump(app, 0.2)
        return shown and not win.log_view.isVisible()

    check("日志抽屉开关", log_drawer)

    print("=== 处理命令（菜单 → 对话框 → 线程）===")

    def run_op(name, expect_change=True):
        before = len(win.entities)
        act = find_action(win.btn_process.menu(), name)
        if act is None:
            raise RuntimeError(f"菜单项缺失: {name}")
        win.scene_panel.select_entity(source)
        act.trigger()
        ok = wait_until(app, lambda: len(win.entities) == before + 1, timeout=90)
        if not ok:
            return False
        result = win.entities[-1]
        changed = result.point_count != source.point_count if expect_change else True
        win._undo()
        pump(app, 0.3)
        return changed and len(win.entities) == before

    check("体素降采样", lambda: run_op("体素降采样…"))
    check("随机采样", lambda: run_op("随机采样…"))
    check("统计滤波 SOR", lambda: run_op("统计滤波 (SOR)…"))
    check("半径滤波 ROR", lambda: run_op("半径滤波 (ROR)…"))
    check("盒裁切", lambda: run_op("盒裁切…"))
    check("平面分割", lambda: run_op("平面分割…"))
    check("地面提取", lambda: run_op("地面提取…"))

    def dbscan_op():
        # 造一片带簇的点云，验证聚类入口（均匀随机云本来就没有簇）
        rng = np.random.default_rng(7)
        blobs = []
        for center in ((-20, -20, 5), (20, 20, 8), (0, 25, 3)):
            blobs.append(rng.normal(center, 1.2, (3000, 3)))
        xyz = np.concatenate(blobs).astype(np.float32)
        clustered = CloudEntity(name="clustered", xyz=xyz, fields={})
        win._add_entity(clustered)
        pump(app, 0.3)
        win.scene_panel.select_entity(clustered)
        before = len(win.entities)
        act = find_action(win.btn_process.menu(), "DBSCAN 聚类…")
        act.trigger()
        ok = wait_until(app, lambda: len(win.entities) == before + 1, timeout=60)
        if ok:
            result = win.entities[-1]
            ok = result.field("labels") is not None and result.point_count == len(xyz)
            win._undo()
            pump(app, 0.3)
        win._remove_entity(clustered)
        pump(app, 0.2)
        return ok

    check("DBSCAN 聚类（带簇数据）", dbscan_op)

    def icp_op():
        # 复制一片点云作为目标，避免读取大文件
        target = CloudEntity(name="icp_target", xyz=source.xyz.copy(),
                             fields={k: type(v)(k, v.data.copy(), kind=v.kind)
                                     for k, v in source.fields.items()})
        win._add_entity(target)
        pump(app, 0.3)
        before = len(win.entities)
        win.scene_panel.select_entity(source)
        act = find_action(win.btn_process.menu(), "ICP 配准（点到点）…")
        act.trigger()
        ok = wait_until(app, lambda: len(win.entities) == before + 1, timeout=120)
        if ok:
            win._undo()
            pump(app, 0.3)
        return ok

    check("ICP 配准", icp_op)

    print("=== 测量 / 选择 ===")

    def measure_flow():
        QTest.mouseClick(win.btn_measure, Qt.LeftButton)
        pump(app, 0.3)
        if win.viewport._mode != "measure":
            return False
        camera_before = np.array(win.viewport.camera.local.position, dtype=np.float64)
        sx, sy, valid = win.viewport._screen_coords(source.xyz)
        valid &= (sx > 20) & (sx < win.viewport.width() - 20) \
            & (sy > 20) & (sy < win.viewport.height() - 20)
        idx = np.where(valid)[0]
        i, j = int(idx[0]), int(idx[len(idx) // 2])
        QTest.mouseClick(win.viewport._subwidget, Qt.LeftButton, pos=QPoint(int(sx[i]), int(sy[i])))
        pump(app, 0.2)
        QTest.mouseClick(win.viewport._subwidget, Qt.LeftButton, pos=QPoint(int(sx[j]), int(sy[j])))
        pump(app, 0.3)
        camera_after = np.array(win.viewport.camera.local.position, dtype=np.float64)
        frozen = float(np.linalg.norm(camera_after - camera_before)) < 1e-9
        summary = win.viewport.measurement_summary()
        ok = len(summary["points"]) == 2 and summary["length"] > 0
        QTest.keyClick(win.viewport, Qt.Key_Escape)
        pump(app, 0.2)
        return ok and frozen and win.viewport._mode is None

    check("两点测距 + Esc（相机冻结）", measure_flow)

    def select_flow():
        QTest.mouseClick(win.btn_select, Qt.LeftButton)
        pump(app, 0.3)
        camera_before = np.array(win.viewport.camera.local.position, dtype=np.float64)
        vp = win.viewport
        sx, sy, valid = vp._screen_coords(win.entities[0].xyz)
        valid &= (sx > 20) & (sx < vp.width() - 20) & (sy > 20) & (sy < vp.height() - 20)
        i = int(np.flatnonzero(valid)[0])
        QTest.mouseClick(vp._subwidget, Qt.LeftButton, pos=QPoint(int(sx[i]), int(sy[i])))
        pump(app, 0.4)
        camera_after = np.array(win.viewport.camera.local.position, dtype=np.float64)
        frozen = float(np.linalg.norm(camera_after - camera_before)) < 1e-9
        selected = vp._selected_point is not None and "X:" in vp.selection_label.text()
        before = len(win.entities)
        QTest.keyClick(win.viewport._subwidget, Qt.Key_Delete)
        pump(app, 0.5)
        after = len(win.entities)
        QTest.keyClick(win.viewport, Qt.Key_Escape)
        pump(app, 0.2)
        return selected and after == before and frozen and vp._selected_point is None

    check("单点信息 + Delete 不删除 + Esc（相机冻结）", select_flow)

    print("=== 工程 / 导出 ===")

    def project_roundtrip():
        path = os.path.join(TMP, "audit_project.pls")
        if not win.save_project(path):
            return False
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        saved = len(data.get("files", []))
        # 清空后重新打开
        for entity in list(win.entities):
            win._remove_entity_now(entity)
        pump(app, 0.3)
        win.open_project(path)
        ok = wait_until(app, lambda: len(win.entities) >= 1, timeout=30)
        return ok and saved >= 1 and win.entities[0].point_count == 200_000

    check("工程保存/打开 .pls", project_roundtrip)

    def export_flow():
        path = os.path.join(TMP, "audit_export.ply")
        if os.path.exists(path):
            os.remove(path)
        ok = win.export_entity(win.entities[0], path)
        return ok and os.path.exists(path) and os.path.getsize(path) > 1000

    check("导出当前点云 .ply", export_flow)

    print("=== 处理链 / 脚本 / 主题 ===")

    def pipeline_flow():
        win.scene_panel.select_entity(win.entities[0])
        before = len(win.entities)
        act = find_action(win.btn_process.menu(), "处理链…")
        act.trigger()
        ok = wait_until(app, lambda: len(win.entities) == before + 1, timeout=90)
        if ok:
            win._undo()
            pump(app, 0.3)
        return ok

    check("处理链（自动两步）", pipeline_flow)

    def script_flow():
        from ui.widgets.script_dialog import ScriptDialog

        dialog = ScriptDialog(win, win)
        dialog.editor.setPlainText("log('AUDIT-SCRIPT-OK')")
        dialog._run()
        pump(app, 0.2)
        dialog.close()
        return "AUDIT-SCRIPT-OK" in win.log_view.toPlainText()

    check("脚本控制台执行", script_flow)

    def theme_flow():
        before = win.theme
        QTest.mouseClick(win.btn_theme, Qt.LeftButton)
        pump(app, 0.5)
        changed = win.theme != before and win.btn_theme.icon() is not None
        QTest.mouseClick(win.btn_theme, Qt.LeftButton)
        pump(app, 0.5)
        return changed and win.theme == before

    check("主题切换（含图标刷新）", theme_flow)

    print("=== 布局 / CLI ===")

    def layout_flow():
        win.resize(1024, 680)
        pump(app, 0.4)
        header = win.centralWidget().layout().itemAt(0).widget()
        max_right = max(child.mapTo(win, child.rect().topRight()).x()
                        for child in header.findChildren(object)
                        if hasattr(child, "isWidgetType") and child.isWidgetType()
                        and child.isVisible())
        return win.width() <= 1024 and max_right <= win.width() + 1 and win.overview_scroll.isVisible()

    check("1024×680 布局无裁切", layout_flow)

    def cli_flow():
        exe = os.path.join(ROOT, ".venv", "Scripts", "python.exe")
        proc = subprocess.run(
            [exe, "-m", "apps.cli", SMALL, "--info"],
            cwd=ROOT, capture_output=True, text=True, timeout=120,
            encoding="utf-8", errors="replace",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        return proc.returncode == 0 and "200,000" in (proc.stdout or "")

    check("CLI --info", cli_flow)

    print("=== 拖放 / Auto-Ingest / 工程状态 ===")

    def dragdrop_flow():
        from PySide6.QtCore import QMimeData, QPointF, QUrl
        from PySide6.QtGui import QDropEvent

        drop_path = os.path.join(TMP, "audit_drop.bin")
        shutil.copyfile(SMALL, drop_path)
        before = len(win.entities)
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(drop_path)])
        event = QDropEvent(QPointF(60, 60), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
        win.dropEvent(event)
        ok = wait_until(app, lambda: len(win.entities) >= before + 1, timeout=40)
        if ok:
            win._remove_entity(win.entities[-1])
            pump(app, 0.2)
        return ok

    check("拖放文件打开", dragdrop_flow)

    def medium_ingest():
        before = len(win.entities)
        win.open_paths([MEDIUM])
        ok = wait_until(app, lambda: any(e.point_count >= 5_000_000 and not e.is_preview
                                         for e in win.entities), timeout=180)
        if ok:
            for entity in [e for e in win.entities if e.point_count >= 5_000_000]:
                win._remove_entity(entity)
                pump(app, 0.2)
        return ok and len(win.entities) >= before

    check("M 级 Auto-Ingest 后台全量加载", medium_ingest)

    def project_state_roundtrip():
        entity = win.entities[0]
        expected_count = len(win.entities)
        entity.visible = False
        entity.color_mode = "height"
        entity.colormap = "turbo"
        entity.point_size = 3.5
        path = os.path.join(TMP, "audit_state.pls")
        if not win.save_project(path):
            return False
        for item in list(win.entities):
            win._remove_entity_now(item)
        pump(app, 0.3)
        win.open_project(path)
        ok = wait_until(app, lambda: len(win.entities) == expected_count, timeout=40)
        if not ok:
            return False
        restored = next(e for e in win.entities if e.path == entity.path)
        return (restored.visible is False and restored.color_mode == "height"
                and restored.colormap == "turbo" and abs(restored.point_size - 3.5) < 0.01)

    check("工程恢复可见性/颜色/点大小", project_state_roundtrip)

    def redo_flow():
        source_entity = win.entities[0]
        before = len(win.entities)
        act = find_action(win.btn_process.menu(), "体素降采样…")
        win.scene_panel.select_entity(source_entity)
        act.trigger()
        if not wait_until(app, lambda: len(win.entities) == before + 1, timeout=90):
            return False
        win._undo()
        pump(app, 0.3)
        undone = len(win.entities) == before
        win._redo()
        pump(app, 0.3)
        redone = len(win.entities) == before + 1
        win._undo()
        pump(app, 0.2)
        return undone and redone

    check("处理结果重做", redo_flow)

    def next_prev():
        if len(win.entities) < 2:
            return True
        first = win.scene_panel.current_entity()
        QTest.keyClick(win.viewport, Qt.Key_Right)
        pump(app, 0.2)
        nxt = win.scene_panel.current_entity()
        QTest.keyClick(win.viewport, Qt.Key_Left)
        pump(app, 0.2)
        back = win.scene_panel.current_entity()
        return nxt is not first and back is first

    check("方向键切换点云", next_prev)

    def export_pcd():
        path = os.path.join(TMP, "audit_export.pcd")
        if os.path.exists(path):
            os.remove(path)
        ok = win.export_entity(win.entities[0], path)
        return ok and os.path.exists(path) and os.path.getsize(path) > 1000

    check("导出 PCD", export_pcd)

    print("=== 对话框 / 裁剪弹层 / 视图菜单 ===")

    def param_dialog():
        dialog = mw.ParamDialog(win, "审计", [
            {"key": "a", "label": "A", "default": 1.5, "decimals": 2},
            {"key": "b", "label": "B", "default": 3, "kind": "int"},
            {"key": "c", "label": "C", "kind": "choice",
             "options": [("第一项", 0), ("第二项", 1)]},
        ], hint="测试参数")
        values = dialog.values()
        dialog.close()
        return abs(values["a"] - 1.5) < 1e-6 and values["b"] == 3 and values["c"] == 0

    check("参数对话框（浮点/整数/下拉）", param_dialog)

    def clip_popup():
        win.clip_popup.set_values(np.array([-1.0, -2.0, -3.0]), np.array([4.0, 5.0, 6.0]))
        mn, mx = win.clip_popup.values()
        ok = np.allclose(mn, [-1, -2, -3]) and np.allclose(mx, [4, 5, 6])
        win.clip_popup.set_enabled(False)
        return ok

    check("裁剪弹层读写范围", clip_popup)

    def grid_toggle():
        act = find_action(win.btn_view.menu(), "显示地面网格")
        act.trigger()
        pump(app, 0.3)
        hidden = act.isChecked() is False
        act.trigger()
        pump(app, 0.2)
        return hidden and act.isChecked() is True

    check("视图→网格开关", grid_toggle)

    def reset_view():
        act = find_action(win.btn_view.menu(), "重置视角")
        if act is None:
            return False
        act.trigger()
        pump(app, 0.4)
        return True

    check("视图→重置视角", reset_view)

    def remove_undo():
        entity = win.entities[0]
        before = len(win.entities)
        win._remove_entity(entity)
        pump(app, 0.3)
        removed = len(win.entities) == before - 1
        win._undo()
        pump(app, 0.3)
        restored = len(win.entities) == before and entity in win.entities
        return removed and restored

    check("移除点云 + 撤销恢复", remove_undo)

    def reload_flow():
        entity = next((e for e in win.entities if e.path), None)
        if entity is None:
            return False
        points = entity.point_count
        win._reload_entity(entity)
        ok = wait_until(app, lambda: win._filter_thread is None, timeout=60)
        return ok and entity.point_count == points and not entity.is_preview

    check("右键重新加载", reload_flow)

    # 汇总
    passed = sum(1 for _n, ok, _d in RESULTS if ok)
    print(f"\n[审计] {passed}/{len(RESULTS)} 项通过")
    failed = [(n, d) for n, ok, d in RESULTS if not ok]
    for name, detail in failed:
        print(f"  失败: {name} — {detail}")
    win.close()
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
