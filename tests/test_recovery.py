"""E26：崩溃标记与异常钩子。"""

import logging
import sys

from core import recovery


def test_marker_lifecycle(tmp_path):
    marker = tmp_path / "session.running"
    assert not recovery.is_unclean(marker)
    recovery.mark_running(marker)
    assert marker.exists()
    assert recovery.is_unclean(marker)
    recovery.clear_running(marker)
    assert not recovery.is_unclean(marker)
    recovery.clear_running(marker)  # 幂等


def test_excepthook_logs_traceback(tmp_path):
    log = logging.getLogger("test-crash")
    log.setLevel(logging.INFO)
    handler = logging.FileHandler(tmp_path / "crash.log", encoding="utf-8")
    log.addHandler(handler)
    previous = sys.excepthook
    try:
        recovery.install_excepthook(log)
        try:
            raise RuntimeError("kaboom")
        except RuntimeError:
            sys.excepthook(*sys.exc_info())
    finally:
        sys.excepthook = previous
        handler.close()
    text = (tmp_path / "crash.log").read_text(encoding="utf-8")
    assert "kaboom" in text and "RuntimeError" in text
