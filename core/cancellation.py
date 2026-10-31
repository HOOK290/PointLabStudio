"""长任务取消：算法层只依赖一个返回 bool 的回调，不耦合 Qt/线程。"""

from __future__ import annotations

from typing import Callable, Optional

CancelCb = Optional[Callable[[], bool]]


class OperationCancelled(Exception):
    """用户请求取消当前长任务（如关闭窗口、移除实体）。"""


def check_cancel(cancel: CancelCb) -> None:
    if cancel is not None and cancel():
        raise OperationCancelled()
