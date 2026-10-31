"""测量结果导出：折线点、分段长度、多边形面积 → CSV 文本。"""

from __future__ import annotations

import csv
import io

import numpy as np

HEADER = ["kind", "index", "x1", "y1", "z1", "x2", "y2", "z2", "length_m", "area_m2"]


def measurements_to_csv(summary: dict) -> str:
    """把 viewport.measurement_summary() 的结果转成 CSV 文本（UTF-8，带表头）。"""
    points = np.asarray(summary.get("points", np.zeros((0, 3))), dtype=np.float64).reshape(-1, 3)
    segments = list(summary.get("segments") or [])
    length = float(summary.get("length", 0.0) or 0.0)
    area = float(summary.get("area", 0.0) or 0.0)

    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(HEADER)
    for i, p in enumerate(points, start=1):
        writer.writerow(["point", i, f"{p[0]:.6f}", f"{p[1]:.6f}", f"{p[2]:.6f}",
                         "", "", "", "", ""])
    for i, seg in enumerate(segments, start=1):
        p1, p2 = points[i - 1], points[i]
        writer.writerow(["segment", i,
                         f"{p1[0]:.6f}", f"{p1[1]:.6f}", f"{p1[2]:.6f}",
                         f"{p2[0]:.6f}", f"{p2[1]:.6f}", f"{p2[2]:.6f}",
                         f"{float(seg):.6f}", ""])
    writer.writerow(["summary", len(points), "", "", "", "", "", "",
                     f"{length:.6f}", f"{area:.6f}"])
    return buf.getvalue()


def write_measurements_csv(summary: dict, path: str) -> bool:
    try:
        with open(path, "w", encoding="utf-8-sig", newline="") as fh:
            fh.write(measurements_to_csv(summary))
        return True
    except OSError:
        return False
