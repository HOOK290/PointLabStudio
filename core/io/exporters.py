"""点云导出：统一 GUI / CLI 的写盘逻辑。

优先使用原生写入器（core/io/native_io.py），完整保留 intensity / labels /
自定义标量场与法线；只有目标格式无法表达时才退化为位置 + 颜色。
"""

from __future__ import annotations

import os

import numpy as np

from core.io import native_io


def export_entity(entity, path: str, *, include_fields: bool = True) -> None:
    """把点云写成 .ply / .pcd / .xyz / .txt（按扩展名）。

    include_fields=True 时写出全部标量场与真实颜色；不会把当前显示伪彩色
    烘焙成 RGB（那是显示状态，不是数据）。
    """
    ext = os.path.splitext(path)[1].lower()
    if not include_fields:
        ext = ".xyz"

    if ext == ".las":
        from core.io.las_io import write_las
        write_las(entity, path)
    elif ext == ".laz":
        raise ValueError("暂不支持导出 .laz，请改用 .las/.ply")
    elif ext == ".e57":
        raise ValueError("暂不支持导出 .e57，请改用 .las/.ply")
    elif ext == ".ply":
        native_io.write_ply(entity, path)
    elif ext == ".pcd":
        native_io.write_pcd(entity, path)
    elif ext == ".pts":
        native_io.write_pts(entity, path)
    elif ext in (".xyz", ".txt", ".csv"):
        native_io.write_text(entity, path)
    else:
        _write_open3d(entity, path, include_fields)


def _write_open3d(entity, path: str, include_fields: bool) -> None:
    """兜底：open3d 只支持位置/颜色/法线。"""
    import open3d as o3d

    cloud = o3d.geometry.PointCloud()
    cloud.points = o3d.utility.Vector3dVector(np.asarray(entity.xyz, dtype=np.float64))
    field = entity.fields.get("rgb")
    if include_fields and field is not None:
        cloud.colors = o3d.utility.Vector3dVector(np.asarray(field.data, dtype=np.float64))
    if not o3d.io.write_point_cloud(path, cloud):
        raise RuntimeError(f"写入失败: {path}")
