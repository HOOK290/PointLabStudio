"""Auto-Ingest 自动分级加载引擎。

核心承诺：无论点云大小，同一窗口、同一套操作，系统自动判断并展示。

分级策略：
  S（< 100 万点）     ：直接全量读取，由界面调度到后台
  M（100 万 ~ 1 亿）  ：先显示预览，后台全量加载后替换
  L（≥ 1 亿）         ：先显示预览；后台全量加载，超过内存阈值时保持
                        高质量均匀采样并明确提示（分块渲染在后续版本）
"""

from __future__ import annotations

import os
from typing import Optional

from core.io.readers import ReadOptions, read_preview
from core.model.entities import TIER_L, TIER_M, TIER_S

# 内存安全阈值：超过则不做全量载入（v1 策略，见方案 §4.4 备注）
MAX_FULL_POINTS = 50_000_000

# 文件大小粗分档（字节）
SIZE_S = 48 * 1024 * 1024      # ~ 1M 点（binary 16B/pt / ascii ~40B/pt）
SIZE_M = 3 * 1024 * 1024 * 1024  # ~ 1 亿点


def tier_by_size(file_bytes: int) -> str:
    if file_bytes < SIZE_S:
        return TIER_S
    if file_bytes < SIZE_M:
        return TIER_M
    return TIER_L


def tier_by_points(n_points: int) -> str:
    if n_points < 1_000_000:
        return TIER_S
    if n_points < 100_000_000:
        return TIER_M
    return TIER_L


class IngestPlan:
    """一次加载的计划：tier、是否需要后台全量、预览实体（可选）、估算点数。"""

    def __init__(self, path: str, tier: str, total_points: Optional[int] = None,
                 preview=None, needs_full: bool = False):
        self.path = path
        self.tier = tier
        self.total_points = total_points
        self.preview = preview
        self.needs_full = needs_full

    def __repr__(self):
        return (f"IngestPlan({os.path.basename(self.path)}, tier={self.tier}, "
                f"total={self.total_points}, preview={self.preview is not None}, full={self.needs_full})")


def plan_ingest(path: str, options: ReadOptions) -> IngestPlan:
    """决定加载策略：是否预览、是否后台全量、最终层级。"""
    file_bytes = os.path.getsize(path)
    tier = tier_by_size(file_bytes)

    if tier == TIER_S:
        return IngestPlan(path, tier)

    preview = read_preview(path, options)
    total = preview[1] if preview else None

    # 用真实点数修正层级
    if total is not None:
        tier = tier_by_points(total)

    needs_full = True
    if total is not None and total > MAX_FULL_POINTS:
        # 超过内存阈值：v1 保持高质量均匀采样预览，不整载
        needs_full = False

    return IngestPlan(path, tier, total, preview[0] if preview else None, needs_full)


def preview_sample_limit(total_points: int) -> int:
    """预览目标点数：保证秒开，同时形状可辨。"""
    if total_points <= 600_000:
        return total_points
    return min(600_000, max(50_000, total_points // 100))
