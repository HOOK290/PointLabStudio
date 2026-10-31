"""PointLabStudio 启动脚本。

用法：
    python run.py
    python run.py "D:\\data\\points"          # 直接打开点云文件或目录
    python run.py --background light "path"

双击 start.bat 时用 pythonw 启动，没有控制台；本文件捕获启动期异常并弹出
系统消息框，避免“双击后什么都没发生”。
"""

import os
import sys
import traceback
from pathlib import Path


def _prepare_gpu_cache() -> None:
    """pygfx 默认写 %LOCALAPPDATA%，受限环境会导入失败；这里提前指到可写目录。"""
    if os.environ.get("PYGFX_DATA_DIR"):
        return
    candidates = []
    try:
        from core.settings import app_home

        candidates.append(app_home() / "pygfx")
    except Exception:  # noqa: BLE001
        pass
    candidates.append(Path(__file__).resolve().parent / ".tmp" / "pygfx")
    for folder in candidates:
        try:
            folder.mkdir(parents=True, exist_ok=True)
            os.environ["PYGFX_DATA_DIR"] = str(folder)
            return
        except OSError:
            continue


_prepare_gpu_cache()

def _report_fatal(detail: str) -> None:
    try:
        from core.applog import get_logger, setup_logging

        setup_logging()
        get_logger("crash").error("启动失败：\n%s", detail)
    except Exception:  # noqa: BLE001 - 日志失败也要尽量弹窗
        pass
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(
            None,
            "PointLab Studio 启动失败：\n\n" + detail.strip()[-1200:],
            "PointLab Studio",
            0x10,
        )
    except Exception:  # noqa: BLE001
        pass


if __name__ == "__main__":
    try:
        from apps.desktop import main

        main()
    except SystemExit:
        raise
    except BaseException:  # noqa: BLE001 - 包括 KeyboardInterrupt 之外的启动错误
        _report_fatal(traceback.format_exc())
        sys.exit(1)
