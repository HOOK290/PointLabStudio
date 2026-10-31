r"""P5 可视化验证：处理链对话框、脚本控制台、处理链结果。"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from PySide6.QtWidgets import QApplication

from core.pipeline import run_pipeline
from ui.main_window import MainWindow
from ui.widgets.pipeline_dialog import PipelineDialog
from ui.widgets.script_dialog import ScriptDialog

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
    win.show()
    win.open_paths([SMALL])
    pump(app, 3.0)

    # 1) 处理链对话框
    dialog = PipelineDialog(win, win.entities[0])
    dialog.show()
    pump(app, 0.5)
    dialog.grab().save(os.path.join(OUT, "p5_pipeline.png"))
    print("saved p5_pipeline.png")
    dialog.close()

    # 2) 脚本控制台
    script = ScriptDialog(win, win)
    script.show()
    pump(app, 0.5)
    script.grab().save(os.path.join(OUT, "p5_script.png"))
    print("saved p5_script.png")
    script.close()

    # 3) 执行处理链并截图结果
    source = win.entities[0]
    steps = [{"op": "voxel", "params": {"voxel": 0.6}},
             {"op": "sor", "params": {"k": 12, "std": 1.5}}]
    result = run_pipeline(source, steps)
    win._on_filter_done("处理链", result)
    pump(app, 2.0)
    win.grab().save(os.path.join(OUT, "p5_chain.png"))
    print("saved p5_chain.png")

    # 4) 脚本执行验证
    script = ScriptDialog(win, win)
    script.editor.setPlainText("log(f'脚本可见 {len(entities)} 片点云，共 {sum(e.point_count for e in entities):,} 点')")
    script._run()
    script.close()
    pump(app, 0.3)
    print("script run ok")
    win.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
