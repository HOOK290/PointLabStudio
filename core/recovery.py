"""E26：崩溃恢复的轻量实现。

启动时在应用目录写 ``session.running`` 标记；正常退出删除标记。
下次启动若发现标记仍在，说明上次未正常退出，可提示用户并记录日志。
"""

from __future__ import annotations

import os
import sys
import threading
import traceback
from pathlib import Path

from core.applog import get_logger
from core.settings import app_home

MARKER_NAME = "session.running"


def marker_path(path: str | os.PathLike | None = None) -> Path:
    return Path(path) if path is not None else app_home() / MARKER_NAME


def mark_running(path: str | os.PathLike | None = None) -> None:
    """写运行标记；目录不可写时只记日志，绝不阻断启动。"""
    target = marker_path(path)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"{os.getpid()}\n", encoding="utf-8")
    except OSError as exc:
        get_logger("recovery").warning("无法写入运行标记 %s：%s", target, exc)


def clear_running(path: str | os.PathLike | None = None) -> None:
    try:
        marker_path(path).unlink()
    except FileNotFoundError:
        pass
    except OSError as exc:
        get_logger("recovery").warning("无法删除运行标记：%s", exc)


def is_unclean(path: str | os.PathLike | None = None) -> bool:
    """存在残留标记 = 上次没有正常退出；读不到目录时按“干净”处理。"""
    try:
        return marker_path(path).exists()
    except OSError:
        return False


def install_excepthook(logger=None) -> None:
    """把未捕获异常写进日志；保留原钩子行为。"""
    log = logger or get_logger("crash")
    previous = sys.excepthook
    lock = threading.Lock()

    def hook(exc_type, exc, tb):
        with lock:
            log.error("未捕获异常:\n%s", "".join(traceback.format_exception(exc_type, exc, tb)))
        previous(exc_type, exc, tb)

    sys.excepthook = hook
