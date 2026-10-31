"""E22：文件日志（滚动写入应用数据目录，控制台仍输出）。"""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

from core.settings import log_path

_CONFIGURED = False
LOGGER_NAME = "pointlab"


def setup_logging(path: Path | None = None, level: int = logging.INFO) -> Path | None:
    """初始化滚动文件日志；返回日志文件路径（失败返回 None，不影响启动）。"""
    global _CONFIGURED
    target = Path(path) if path else log_path()
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    if _CONFIGURED:
        return target

    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(
            target, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8")
        handler.setFormatter(fmt)
        logger.addHandler(handler)
    except OSError:
        target = None

    stream = logging.StreamHandler()
    stream.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(stream)
    _CONFIGURED = True
    return target


def get_logger(name: str = "ui") -> logging.Logger:
    return logging.getLogger(f"{LOGGER_NAME}.{name}")
