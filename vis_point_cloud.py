#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用点云可视化脚本：支持输入单个点云文件或点云目录。

示例：
    python vis_point_cloud.py \
        "D:\data\points" \                 # 点云文件或点云目录
        --bin-dim auto \                   # .bin 点维度，auto 自动识别；KITTI/gt_database 常用 4，nuScenes 常用 5
        --dtype float32 \                  # .bin 数据类型，默认 float32
        --npy-key points \                 # npy/npz/dict 中点云数组的 key；不确定可不写
        --no-recursive \                   # 目录模式下不进入子目录；需要进入时不写
        --color-mode auto \                # 颜色模式：auto/height/intensity/rgb/none
        --color-file colors.npy \          # 额外颜色文件；没有单独颜色文件时不写
        --point-size 2 \                   # 点大小，默认 2
        --axis-size 0.5 \                  # 坐标轴大小；设为 0 可隐藏
        --zoom 0.8 \                       # 初始缩放；Open3D 中通常越大越近；不确定可不写
        --max-points 0 \                   # 最大显示点数；0 表示不采样，显示全部点
        --reset-each \                     # 切换文件时自动重置视角；不需要时不写
        --background dark \                # 背景颜色：dark/light
        --verbose                          # 打印调试信息，例如 .bin 自动识别维度结果；不需要时不写

常用简化命令：python D:\Desktop\lidar\vis_point_cloud.py "D:\Desktop\lidar\map.pcd"
    

按键：
    ← / ↑        上一个文件
    → / ↓        下一个文件
    R             重置视角
    H             打印帮助
    C             循环颜色模式: auto / height / intensity / rgb / none
    + / =         增大点大小
    - / _         减小点大小
    W/S/A/D       上/下/左/右平移相机
    Q/E           后退/前进平移相机
"""

import argparse
import os
import re
import sys
from dataclasses import dataclass
from typing import Optional, Sequence, Tuple

import numpy as np
import open3d as o3d


SUPPORTED_EXTS = {
    ".bin", ".pcd", ".ply", ".xyz", ".xyzn", ".xyzrgb", ".pts",
    ".npy", ".npz", ".txt", ".csv"
}
COLOR_MODES = ["auto", "height", "intensity", "rgb", "none"]
NUM_RE = re.compile(r"(\d+)")


# =========================
# 参数区
# =========================
def build_argparser():
    parser = argparse.ArgumentParser(description="通用 Open3D 点云可视化工具。")
    parser.add_argument("path", type=str, help="点云文件路径或点云目录路径。")

    # 读取参数
    parser.add_argument("--bin-dim", type=str, default="auto",
                        help=".bin 每个点的维度，默认 auto；常见：KITTI/gt_database=4，nuScenes=5。")
    parser.add_argument("--dtype", type=str, default="float32", help=".bin 文件 dtype，默认 float32。")
    parser.add_argument("--npy-key", type=str, default=None, help="npy/npz/dict 中点云数组的 key。")
    parser.add_argument("--no-recursive", action="store_true", help="目录模式下不递归子目录。")

    # 颜色参数
    parser.add_argument("--color-mode", type=str, default="auto", choices=COLOR_MODES,
                        help="颜色模式，默认 auto。")
    parser.add_argument("--color-file", type=str, default=None,
                        help="额外颜色文件，支持 npy/npz/txt/csv/bin，支持 Nx1/Nx3/Nx4。")
    parser.add_argument("--color-key", type=str, default=None, help="颜色 npy/npz/dict 中的 key。")
    parser.add_argument("--color-bin-dim", type=int, default=None, help="颜色 bin/一维数组的维度。")

    # 显示参数
    parser.add_argument("--point-size", type=float, default=2.0, help="点大小，默认 2.0。")
    parser.add_argument("--axis-size", type=float, default=0.5, help="坐标轴大小，默认 0.5；设为 0 可隐藏。")
    parser.add_argument("--zoom", type=float, default=None, help="初始缩放；Open3D 中通常越大越近。")
    parser.add_argument("--max-points", type=int, default=0, help="最多显示点数；0 表示不采样。")
    parser.add_argument("--reset-each", action="store_true", help="切换文件时自动重置视角。")
    parser.add_argument("--background", type=str, default="dark", choices=["dark", "light"], help="背景颜色。")

    # 调试参数
    parser.add_argument("--verbose", action="store_true", help="打印自动识别维度等详细信息。")
    return parser


@dataclass
class CloudData:
    xyz: np.ndarray
    intensity: Optional[np.ndarray] = None
    rgb: Optional[np.ndarray] = None
    dim: Optional[int] = None
    info: str = ""
    debug: str = ""


# =========================
# 基础工具
# =========================
def natural_key(path: str):
    return [int(x) if x.isdigit() else x.lower() for x in NUM_RE.split(str(path))]


def parse_bin_dim(value: str) -> Optional[int]:
    value = str(value).strip().lower()
    return None if value in {"auto", "none", ""} else int(value)


def collect_files(path: str, recursive: bool = True):
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


def robust_norm(values: np.ndarray, eps: float = 1e-12):
    values = np.asarray(values, dtype=np.float32)
    mask = np.isfinite(values)
    if not np.any(mask):
        return np.zeros_like(values, dtype=np.float32)

    lo, hi = np.percentile(values[mask], [2, 98])
    if abs(hi - lo) < eps:
        return np.zeros_like(values, dtype=np.float32)

    return np.clip((values - lo) / (hi - lo), 0.0, 1.0).astype(np.float32)


def scalar_to_rgb(values: np.ndarray):
    """把 intensity / height / label 等标量转成伪彩色。"""
    t = robust_norm(values).reshape(-1, 1)
    c0 = np.array([0.08, 0.20, 0.60], dtype=np.float32)
    c1 = np.array([0.10, 0.85, 0.75], dtype=np.float32)
    c2 = np.array([0.98, 0.92, 0.22], dtype=np.float32)

    rgb = np.where(
        t < 0.5,
        c0 + (c1 - c0) * (t / 0.5),
        c1 + (c2 - c1) * ((t - 0.5) / 0.5),
    )
    return np.clip(rgb.astype(np.float32), 0.0, 1.0)


def array_to_rgb(array: np.ndarray):
    """支持 Nx1 标量、Nx3 RGB、Nx4 RGBA。"""
    array = np.asarray(array)
    if array.ndim == 1:
        array = array.reshape(-1, 1)

    if array.ndim != 2:
        raise ValueError(f"颜色数组必须是 Nx1/Nx3/Nx4，实际 shape={array.shape}")

    if array.shape[1] == 1:
        return scalar_to_rgb(array[:, 0])

    if array.shape[1] >= 3:
        rgb = array[:, :3].astype(np.float32)
        rgb = rgb / 255.0 if float(np.nanmax(rgb)) > 1.5 else rgb
        return np.clip(rgb, 0.0, 1.0)

    raise ValueError(f"颜色数组列数不足: shape={array.shape}")


def sanitize_cloud(xyz, intensity=None, rgb=None):
    xyz = np.asarray(xyz, dtype=np.float32)
    if xyz.ndim != 2 or xyz.shape[1] < 3:
        raise ValueError(f"点云不是 Nx3+: shape={xyz.shape}")

    xyz = xyz[:, :3]
    mask = np.all(np.isfinite(xyz), axis=1)

    xyz = xyz[mask]
    intensity = None if intensity is None else np.asarray(intensity)[mask]
    rgb = None if rgb is None else np.asarray(rgb, dtype=np.float32)[mask]
    return xyz, intensity, rgb


def sample_cloud(cloud: CloudData, max_points: int, seed: int = 0):
    if not max_points or max_points <= 0 or cloud.xyz.shape[0] <= max_points:
        return cloud

    rng = np.random.default_rng(seed)
    index = rng.choice(cloud.xyz.shape[0], size=max_points, replace=False)
    index.sort()

    cloud.xyz = cloud.xyz[index]
    if cloud.intensity is not None:
        cloud.intensity = cloud.intensity[index]
    if cloud.rgb is not None:
        cloud.rgb = cloud.rgb[index]
    return cloud


# =========================
# .bin 维度自动识别
# =========================
def path_dim_hint(path: str):
    path_lower = path.replace("\\", "/").lower()
    name = os.path.basename(path_lower)

    if "lidar_top" in path_lower or name.endswith(".pcd.bin") or ("nuscenes" in path_lower and "samples" in path_lower):
        return 5
    if "velodyne" in path_lower or "kitti" in path_lower or "gt_database" in path_lower or "database" in path_lower:
        return 4
    return None


def score_bin_dim(points: np.ndarray, dim: int):
    """启发式评分：.bin 没有文件头，自动识别无法保证 100% 正确。"""
    xyz = points[: min(len(points), 200000), :3]
    finite = np.all(np.isfinite(xyz), axis=1)
    if finite.size == 0 or finite.mean() < 0.98:
        return -1e6

    xyz = xyz[finite]
    q1, q99 = np.percentile(xyz, [1, 99], axis=0)
    extent = q99 - q1
    abs99 = np.percentile(np.abs(xyz), 99, axis=0)

    xy_extent = max(float(extent[0]), float(extent[1]))
    z_extent = float(extent[2])
    max_abs = float(np.max(abs99))

    score = 100.0
    if max_abs > 1e5:
        score -= 250
    elif max_abs > 1e4:
        score -= 80
    if xy_extent < 0.05:
        score -= 50
    if z_extent > max(80.0, xy_extent * 3.0):
        score -= 80

    if dim == 5 and points.shape[1] >= 5:
        ring = points[: min(len(points), 200000), 4]
        ring = ring[np.isfinite(ring)]
        if ring.size:
            integer_like = np.mean(np.abs(ring - np.round(ring)) < 1e-3)
            if np.percentile(ring, 1) >= -1e-3 and np.percentile(ring, 99) <= 255 and integer_like > 0.8:
                score += 18

    score += {4: 4, 5: 3, 3: 1}.get(dim, 0)
    return float(score)


def infer_bin_dim(path: str, array: np.ndarray, user_dim: Optional[int]) -> Tuple[int, str]:
    if user_dim is not None:
        if user_dim < 3 or array.size % user_dim != 0:
            raise ValueError(f"无法按 --bin-dim={user_dim} reshape，float 数量={array.size}")
        return user_dim, f"dim={user_dim}"

    candidates = [d for d in [3, 4, 5, 6, 7, 8] if array.size % d == 0]
    if not candidates:
        raise ValueError(f"无法自动识别 .bin 维度，float 数量={array.size}，请指定 --bin-dim")

    scores = {d: score_bin_dim(array.reshape(-1, d), d) for d in candidates}
    hint = path_dim_hint(path)
    if hint in scores:
        scores[hint] += 60

    dim = max(scores, key=scores.get)
    debug = "auto_dim={}, hint={}, scores={}".format(
        dim, hint, ",".join(f"{k}:{v:.1f}" for k, v in sorted(scores.items()))
    )
    return dim, debug


# =========================
# 文件读取
# =========================
def load_array_file(path: str, key: Optional[str] = None):
    ext = os.path.splitext(path)[1].lower()

    if ext == ".npy":
        obj = np.load(path, allow_pickle=True)
        if isinstance(obj, np.ndarray) and obj.dtype == object:
            try:
                obj = obj.item()
            except Exception:
                pass
        if isinstance(obj, dict):
            keys = [key] if key else ["points", "pointcloud", "point_cloud", "pc", "xyz", "lidar", "data", "arr_0",
                                      "colors", "color", "rgb", "rgba", "labels", "label"]
            for k in keys:
                if k in obj:
                    return np.asarray(obj[k]), k
            raise KeyError(f"找不到 key，已有 keys={list(obj.keys())}")
        return np.asarray(obj), None

    if ext == ".npz":
        obj = np.load(path, allow_pickle=True)
        keys = [key] if key else ["points", "pointcloud", "point_cloud", "pc", "xyz", "lidar", "data", "arr_0",
                                  "colors", "color", "rgb", "rgba", "labels", "label"]
        for k in keys:
            if k in obj.files:
                return np.asarray(obj[k]), k
        return np.asarray(obj[obj.files[0]]), obj.files[0]

    if ext in [".txt", ".csv"]:
        return np.loadtxt(path, dtype=np.float32, delimiter="," if ext == ".csv" else None), None

    if ext == ".bin":
        return np.fromfile(path, dtype=np.float32), None

    raise ValueError(f"不支持的数组文件类型: {ext}")


def load_bin(path: str, bin_dim=None, dtype="float32"):
    array = np.fromfile(path, dtype=np.dtype(dtype))
    if array.size < 3:
        raise ValueError("bin 文件太小")

    dim, debug = infer_bin_dim(path, array, bin_dim)
    points = array.reshape(-1, dim)

    xyz = points[:, :3]
    intensity = points[:, 3] if dim >= 4 else None
    rgb = array_to_rgb(points[:, 3:6]) if dim >= 6 else None

    xyz, intensity, rgb = sanitize_cloud(xyz, intensity, rgb)
    return CloudData(xyz=xyz, intensity=intensity, rgb=rgb, dim=dim, info=f"bin dim={dim}", debug=debug)


def load_npy_npz(path: str, key=None, bin_dim=None):
    array, used_key = load_array_file(path, key)
    array = np.asarray(array)

    if array.ndim == 1:
        dim, debug = infer_bin_dim(path, array.astype(np.float32), bin_dim)
        array = array.reshape(-1, dim)
    else:
        if array.ndim != 2 or array.shape[1] < 3:
            raise ValueError(f"npy/npz 不是 Nx3+: shape={array.shape}")
        dim, debug = array.shape[1], f"key={used_key}"

    xyz = array[:, :3]
    intensity = array[:, 3] if dim >= 4 else None
    rgb = array_to_rgb(array[:, 3:6]) if dim >= 6 else None

    xyz, intensity, rgb = sanitize_cloud(xyz, intensity, rgb)
    return CloudData(xyz=xyz, intensity=intensity, rgb=rgb, dim=dim, info=f"array dim={dim}", debug=debug)


def load_ascii(path: str):
    ext = os.path.splitext(path)[1].lower()
    array = np.loadtxt(path, dtype=np.float32, delimiter="," if ext == ".csv" else None)
    if array.ndim == 1:
        array = array.reshape(1, -1)
    if array.shape[1] < 3:
        raise ValueError(f"文本点云不是 Nx3+: shape={array.shape}")

    dim = array.shape[1]
    xyz = array[:, :3]
    intensity = array[:, 3] if dim >= 4 else None
    rgb = array_to_rgb(array[:, 3:6]) if dim >= 6 else None

    xyz, intensity, rgb = sanitize_cloud(xyz, intensity, rgb)
    return CloudData(xyz=xyz, intensity=intensity, rgb=rgb, dim=dim, info=f"text dim={dim}")


def load_open3d_cloud(path: str):
    point_cloud = o3d.io.read_point_cloud(path)
    if point_cloud.is_empty():
        raise ValueError("Open3D 读取为空")

    xyz = np.asarray(point_cloud.points, dtype=np.float32)
    rgb = np.asarray(point_cloud.colors, dtype=np.float32) if np.asarray(point_cloud.colors).size else None
    xyz, _, rgb = sanitize_cloud(xyz, None, rgb)
    return CloudData(xyz=xyz, rgb=rgb, dim=3, info="open3d")


def load_color_file(path: str, n_points: int, key=None, color_bin_dim=None):
    array, _ = load_array_file(path, key)

    if array.ndim == 1 and array.size != n_points:
        if array.size == n_points * 3:
            array = array.reshape(n_points, 3)
        elif array.size == n_points * 4:
            array = array.reshape(n_points, 4)
        elif color_bin_dim and array.size % color_bin_dim == 0:
            array = array.reshape(-1, color_bin_dim)
        else:
            raise ValueError(f"颜色数量不匹配: color_size={array.size}, points={n_points}")

    if array.ndim == 2 and array.shape[0] != n_points:
        raise ValueError(f"颜色行数不匹配: color_shape={array.shape}, points={n_points}")

    return array_to_rgb(array)


def read_cloud(path: str, args):
    ext = os.path.splitext(path)[1].lower()
    bin_dim = parse_bin_dim(args.bin_dim)

    if ext == ".bin":
        cloud = load_bin(path, bin_dim, args.dtype)
    elif ext in [".npy", ".npz"]:
        cloud = load_npy_npz(path, args.npy_key, bin_dim)
    elif ext in [".txt", ".csv"]:
        cloud = load_ascii(path)
    elif ext in [".pcd", ".ply", ".xyz", ".xyzn", ".xyzrgb", ".pts"]:
        cloud = load_open3d_cloud(path)
    else:
        raise ValueError(f"不支持的文件类型: {ext}")

    if args.color_file:
        cloud.rgb = load_color_file(args.color_file, cloud.xyz.shape[0], args.color_key, args.color_bin_dim)
        cloud.info += " + color-file"

    return sample_cloud(cloud, args.max_points)


# =========================
# 可视化
# =========================
def make_open3d_cloud(cloud: CloudData, color_mode: str):
    point_cloud = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(cloud.xyz))

    if color_mode == "none":
        return point_cloud, "none"

    if color_mode in ["auto", "rgb"] and cloud.rgb is not None:
        point_cloud.colors = o3d.utility.Vector3dVector(cloud.rgb)
        return point_cloud, "rgb"

    if color_mode in ["auto", "intensity"] and cloud.intensity is not None:
        point_cloud.colors = o3d.utility.Vector3dVector(scalar_to_rgb(cloud.intensity))
        return point_cloud, "intensity"

    point_cloud.colors = o3d.utility.Vector3dVector(scalar_to_rgb(cloud.xyz[:, 2]))
    return point_cloud, "height"


def xyz_range_text(xyz: np.ndarray):
    mn, mx = xyz.min(axis=0), xyz.max(axis=0)
    return f"x[{mn[0]:.1f},{mx[0]:.1f}] y[{mn[1]:.1f},{mx[1]:.1f}] z[{mn[2]:.1f},{mx[2]:.1f}]"


class PointCloudViewer:
    KEY_LEFT, KEY_RIGHT, KEY_DOWN, KEY_UP = 263, 262, 264, 265

    def __init__(self, files: Sequence[str], args):
        self.files = list(files)
        self.args = args
        self.index = 0
        self.point_size = float(args.point_size)
        self.color_mode = args.color_mode

        self.viewer = o3d.visualization.VisualizerWithKeyCallback()
        self.point_cloud = o3d.geometry.PointCloud()
        self.axis = None
        self.geometry_added = False

    def run(self):
        self.viewer.create_window("Point Cloud Viewer", 1280, 720)
        self._register_callbacks()
        self._print_help()
        self._show(reset_view=True)
        self.viewer.run()
        self.viewer.destroy_window()

    def _register_callbacks(self):
        callbacks = {
            self.KEY_LEFT: self._previous_file,
            self.KEY_UP: self._previous_file,
            self.KEY_RIGHT: self._next_file,
            self.KEY_DOWN: self._next_file,
            ord("R"): self._reset_view_callback,
            ord("H"): self._help_callback,
            ord("C"): self._cycle_color,
            ord("+"): lambda v: self._change_point_size(+1),
            ord("="): lambda v: self._change_point_size(+1),
            ord("-"): lambda v: self._change_point_size(-1),
            ord("_"): lambda v: self._change_point_size(-1),
            ord("A"): lambda v: (self._pan_camera(dx=-self._step()), False)[1],
            ord("D"): lambda v: (self._pan_camera(dx=+self._step()), False)[1],
            ord("W"): lambda v: (self._pan_camera(dy=+self._step()), False)[1],
            ord("S"): lambda v: (self._pan_camera(dy=-self._step()), False)[1],
            ord("Q"): lambda v: (self._pan_camera(dz=-self._step()), False)[1],
            ord("E"): lambda v: (self._pan_camera(dz=+self._step()), False)[1],
        }
        for key, callback in callbacks.items():
            self.viewer.register_key_callback(key, callback)

    def _print_help(self):
        print(__doc__)

    def _apply_render_options(self):
        options = self.viewer.get_render_option()
        options.background_color = np.asarray([1, 1, 1] if self.args.background == "light" else [0.02, 0.02, 0.02])
        options.point_size = float(self.point_size)

    def _show(self, reset_view=False):
        path = self.files[self.index]
        try:
            cloud, color_name = self._load_current_cloud(path)
        except Exception as error:
            print(f"\n读取失败: {path}\n原因: {error}")
            return

        if not self.geometry_added:
            self.viewer.add_geometry(self.point_cloud, reset_bounding_box=True)
            self.geometry_added = True

            if self.args.axis_size > 0:
                self.axis = o3d.geometry.TriangleMesh.create_coordinate_frame(size=self.args.axis_size, origin=[0, 0, 0])
                self.viewer.add_geometry(self.axis, reset_bounding_box=False)

            self._apply_render_options()
            self._reset_view()
        else:
            self.viewer.update_geometry(self.point_cloud)
            if reset_view or self.args.reset_each:
                self._reset_view()

        self.viewer.poll_events()
        self.viewer.update_renderer()
        self._print_cloud_info(path, cloud, color_name)

    def _load_current_cloud(self, path: str):
        cloud = read_cloud(path, self.args)
        if cloud.xyz.size == 0:
            raise ValueError("点云为空")

        point_cloud, color_name = make_open3d_cloud(cloud, self.color_mode)
        self.point_cloud.points = point_cloud.points
        self.point_cloud.colors = point_cloud.colors if np.asarray(point_cloud.colors).size else o3d.utility.Vector3dVector()
        return cloud, color_name

    def _print_cloud_info(self, path: str, cloud: CloudData, color_name: str):
        print(f"\n[{self.index + 1}/{len(self.files)}] {os.path.basename(path)} | {cloud.info} | color={color_name} | pts={len(cloud.xyz)}")
        print(f"{xyz_range_text(cloud.xyz)} | point={self.point_size:.1f} | axis={self.args.axis_size:.2f}")
        if self.args.verbose and cloud.debug:
            print(f"debug: {cloud.debug}")

    def _reset_view(self):
        if len(self.point_cloud.points) == 0:
            return

        bbox = self.point_cloud.get_axis_aligned_bounding_box()
        view = self.viewer.get_view_control()
        view.set_lookat(bbox.get_center())
        view.set_front([0.0, -1.0, 0.45])
        view.set_up([0.0, 0.0, 1.0])
        view.set_zoom(float(self.args.zoom) if self.args.zoom is not None else 0.70)

    def _step(self):
        if len(self.point_cloud.points) == 0:
            return 1.0
        extent = self.point_cloud.get_axis_aligned_bounding_box().get_extent()
        return float(0.01 * (np.linalg.norm(extent) + 1e-6))

    def _pan_camera(self, dx=0.0, dy=0.0, dz=0.0):
        view = self.viewer.get_view_control()
        params = view.convert_to_pinhole_camera_parameters()
        extrinsic = params.extrinsic.copy()

        rotation, translation = extrinsic[:3, :3], extrinsic[:3, 3]
        center = -rotation.T @ translation

        right = rotation.T @ np.array([1.0, 0.0, 0.0])
        up = -rotation.T @ np.array([0.0, 1.0, 0.0])
        forward = rotation.T @ np.array([0.0, 0.0, 1.0])

        center += dx * right + dy * up + dz * forward
        extrinsic[:3, 3] = -rotation @ center
        params.extrinsic = extrinsic

        view.convert_from_pinhole_camera_parameters(params, allow_arbitrary=True)
        self.viewer.update_renderer()

    def _previous_file(self, viewer):
        self.index = (self.index - 1) % len(self.files)
        self._show()
        return False

    def _next_file(self, viewer):
        self.index = (self.index + 1) % len(self.files)
        self._show()
        return False

    def _reset_view_callback(self, viewer):
        self._show(reset_view=True)
        return False

    def _help_callback(self, viewer):
        self._print_help()
        return False

    def _cycle_color(self, viewer):
        current = COLOR_MODES.index(self.color_mode)
        self.color_mode = COLOR_MODES[(current + 1) % len(COLOR_MODES)]
        self._show()
        return False

    def _change_point_size(self, delta: float):
        self.point_size = min(max(self.point_size + delta, 1.0), 30.0)
        self._apply_render_options()
        self.viewer.update_renderer()
        print(f"point_size={self.point_size:.1f}")
        return False


def main():
    args = build_argparser().parse_args()

    try:
        files = collect_files(args.path, recursive=not args.no_recursive)
    except Exception as error:
        print(f"收集文件失败: {error}")
        sys.exit(1)

    if not files:
        print(f"没有找到支持的点云文件: {args.path}")
        return

    print(f"找到 {len(files)} 个点云文件。")
    PointCloudViewer(files, args).run()


if __name__ == "__main__":
    main()
