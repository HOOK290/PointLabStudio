"""点云文件收集与自然排序（迁移自 vis_point_cloud.py）。"""

from __future__ import annotations

import os
import re

SUPPORTED_EXTS = {
    ".bin", ".pcd", ".ply", ".xyz", ".xyzn", ".xyzrgb", ".pts",
    ".npy", ".npz", ".txt", ".csv",
}

NUM_RE = re.compile(r"(\d+)")


def natural_key(path: str):
    return [int(x) if x.isdigit() else x.lower() for x in NUM_RE.split(str(path))]


def collect_files(path: str, recursive: bool = True):
    """路径 → 排序后的点云文件列表。"""
    path = os.path.abspath(os.path.expanduser(path))

    if os.path.isfile(path):
        ext = os.path.splitext(path)[1].lower()
        if ext not in SUPPORTED_EXTS:
            raise ValueError(f"不支持的文件类型: {ext}。支持: {sorted(SUPPORTED_EXTS)}")
        return [path]

    if not os.path.isdir(path):
        raise FileNotFoundError(f"路径不存在: {path}")

    files = []
    walker = os.walk(path) if recursive else [(path, [], os.listdir(path))]
    for root, _, names in walker:
        for name in names:
            file_path = os.path.join(root, name)
            if os.path.isfile(file_path) and os.path.splitext(name)[1].lower() in SUPPORTED_EXTS:
                files.append(file_path)

    return sorted(files, key=natural_key)
