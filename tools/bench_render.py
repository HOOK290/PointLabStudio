r"""P0 技术验证：GPU 适配器 + 1000 万点离屏渲染基准。

用法：
    .venv\Scripts\python.exe tools/bench_render.py
    .venv\Scripts\python.exe tools/bench_render.py --n 10000000
"""

from __future__ import annotations

import argparse
import time

import numpy as np
import wgpu

import pygfx as gfx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=10_000_000)
    args = parser.parse_args()

    print("== 1. GPU 适配器 ==")
    enumerate_adapters = getattr(wgpu.gpu, "enumerate_adapters_sync", None) or wgpu.gpu.enumerate_adapters
    adapters = enumerate_adapters()
    if not adapters:
        print("!! 未发现任何 GPU 适配器（可能缺驱动/远程桌面会话）")
        return 1
    for a in adapters:
        print(f"  - {a.summary}")

    print("== 2. 请求设备 ==")
    adapter = wgpu.gpu.request_adapter_sync(power_preference="high-performance")
    device = adapter.request_device_sync()
    print(f"  设备就绪: {adapter.summary}")

    print("== 3. 离屏渲染基准 ==")
    try:
        from rendercanvas.offscreen import RenderCanvas as WgpuCanvas
        canvas = WgpuCanvas()
    except Exception:
        print("  offscreen canvas 不可用，改用 Qt offscreen")
        from PySide6.QtWidgets import QApplication
        app = QApplication([])
        from rendercanvas.qt import RenderCanvas as WgpuCanvas
        canvas = WgpuCanvas()

    renderer = gfx.WgpuRenderer(canvas)
    scene = gfx.Scene()
    camera = gfx.PerspectiveCamera(50, 16 / 9)
    camera.local.position = (0, -150, 60)
    camera.look_at((0, 0, 0))

    rng = np.random.default_rng(0)
    n = args.n
    xyz = np.empty((n, 3), dtype=np.float32)
    xyz[:, 0] = rng.uniform(-100, 100, n)
    xyz[:, 1] = rng.uniform(-100, 100, n)
    xyz[:, 2] = rng.uniform(-20, 20, n)
    colors = np.empty((n, 4), dtype=np.float32)
    colors[:, :3] = np.clip((xyz[:, 2] + 20) / 40.0, 0, 1)[:, None] * np.array([0.1, 0.7, 1.0])
    colors[:, 3] = 1.0

    points = gfx.Points(
        gfx.Geometry(positions=xyz, colors=colors),
        gfx.PointsMaterial(size=2, size_space="screen", color_mode="vertex"),
    )
    scene.add(points)
    print(f"  点数: {n:,} · 显存上传完成")

    renderer.render(scene, camera)  # warmup（含管线编译）
    frames = 100
    t0 = time.perf_counter()
    for _ in range(frames):
        renderer.render(scene, camera)
    dt = time.perf_counter() - t0
    print(f"  渲染 {frames} 帧耗时 {dt:.3f}s → {frames / dt:.1f} FPS")
    print("== P0 渲染验证通过 ==")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
