r"""生成合成测试点云：覆盖 S / M / L 三级（Auto-Ingest 验证 + 渲染基准）。

用法：
    .venv\Scripts\python.exe tools/make_test_data.py --out data
    .venv\Scripts\python.exe tools/make_test_data.py --out data --big   # 追加 6000 万点（约 1GB）
"""

from __future__ import annotations

import argparse
import os

import numpy as np


def make_scene(n: int, seed: int = 0):
    """多球 + 地形波浪 + 噪声，带强度场，形状可辨。"""
    rng = np.random.default_rng(seed)
    xyz = np.empty((n, 3), dtype=np.float32)
    intensity = np.empty(n, dtype=np.float32)

    filled = 0
    parts = [
        (0.5, 20.0, (0, 0, 0)),          # 地形波浪
        (0.2, 6.0, (-60, 40, 25)),       # 球
        (0.15, 9.0, (50, -30, 18)),      # 球
        (0.15, 4.0, (10, 60, 40)),       # 小球
    ]
    for frac, size, (cx, cy, cz) in parts:
        k = int(n * frac)
        if filled + k > n:
            k = n - filled
        if k <= 0:
            continue
        r = rng.random(k)
        if abs(cx) + abs(cy) == 0:  # 地形
            x = rng.uniform(-90, 90, k)
            y = rng.uniform(-90, 90, k)
            z = 3.0 * np.sin(x * 0.06) * np.cos(y * 0.05) + rng.normal(0, 0.3, k)
        else:
            theta = rng.uniform(0, 2 * np.pi, k)
            phi = np.arccos(rng.uniform(-1, 1, k))
            rad = size * r ** (1 / 3)
            x = cx + rad * np.sin(phi) * np.cos(theta)
            y = cy + rad * np.sin(phi) * np.sin(theta)
            z = cz + rad * np.cos(phi)
        xyz[filled: filled + k, 0] = x
        xyz[filled: filled + k, 1] = y
        xyz[filled: filled + k, 2] = z
        intensity[filled: filled + k] = rng.uniform(0, 1, k)
        filled += k

    return xyz, intensity


def write_bin(path: str, xyz: np.ndarray, intensity: np.ndarray):
    pts = np.hstack([xyz, intensity[:, None]]).astype(np.float32)
    pts.tofile(path)
    return pts.nbytes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data")
    parser.add_argument("--big", action="store_true", help="追加 L 级大文件（约 1GB）")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)

    # S：20 万点
    xyz, it = make_scene(200_000, seed=1)
    write_bin(os.path.join(args.out, "scene_small.bin"), xyz, it)
    print(f"[S] scene_small.bin: 200,000 点 · {os.path.getsize(os.path.join(args.out, 'scene_small.bin'))/1e6:.1f} MB")

    # M：500 万点
    xyz, it = make_scene(5_000_000, seed=2)
    write_bin(os.path.join(args.out, "scene_medium.bin"), xyz, it)
    print(f"[M] scene_medium.bin: 5,000,000 点 · {os.path.getsize(os.path.join(args.out, 'scene_medium.bin'))/1e6:.1f} MB")

    if args.big:
        # L：6000 万点（约 1GB，分块写出避免峰值内存）
        path = os.path.join(args.out, "scene_large.bin")
        chunk = 1_000_000
        with open(path, "wb") as f:
            for start in range(0, 60_000_000, chunk):
                k = min(chunk, 60_000_000 - start)
                x, i = make_scene(k, seed=3 + start // chunk)
                np.hstack([x, i[:, None]]).astype(np.float32).tofile(f)
        print(f"[L] scene_large.bin: 60,000,000 点 · {os.path.getsize(path)/1e6:.0f} MB")


if __name__ == "__main__":
    main()
