"""统一的测试入口：解决 pygfx 缓存目录与受限沙箱下的临时目录问题。

用法：
    python tools/run_tests.py                 # 全量测试
    python tools/run_tests.py tests/test_core.py -q
    python tools/run_tests.py --sandbox       # 受限 Windows 沙箱（如 DSH）

为什么要这个入口：
- pygfx 默认把字体缓存写到 %LOCALAPPDATA%，在只读/受限环境下导入即失败；
  这里默认指向项目内 .tmp/pygfx，保证测试可重复。
- 某些 Windows 沙箱（例如 DSH 的文件沙箱）会把 os.mkdir(path, 0o700) 变成
  连创建者都无法列出的目录，而 pytest 正是用 0o700 建临时目录。--sandbox
  只在本地显式开启该兼容处理，普通环境不受影响。
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _prepare_sandbox() -> None:
    """Strips POSIX mode bits from os.mkdir and isolates temp dirs."""
    original_mkdir = os.mkdir

    def mkdir(path, mode=0o777, *, dir_fd=None):
        return original_mkdir(path, 0o777, dir_fd=dir_fd)

    os.mkdir = mkdir  # type: ignore[assignment]

    tmp = ROOT / ".tmp" / "pytmp"
    tmp.mkdir(parents=True, exist_ok=True)
    os.environ["TEMP"] = str(tmp)
    os.environ["TMP"] = str(tmp)
    tempfile.tempdir = None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--sandbox", action="store_true", help="启用受限沙箱兼容模式")
    args, rest = parser.parse_known_args(argv)

    os.environ.setdefault("PYGFX_DATA_DIR", str(ROOT / ".tmp" / "pygfx"))
    if args.sandbox:
        _prepare_sandbox()

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    import pytest

    return int(pytest.main(rest))


if __name__ == "__main__":
    raise SystemExit(main())
