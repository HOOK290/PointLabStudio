"""E23：LAS/LAZ/E57 读写。

- .las：原生 numpy 实现（1.2 常用点格式 0/1/2/3，及 1.4 的 6/7/8），
  保留 intensity、classification、RGB；不依赖第三方库。
- .laz / .e57：需要可选的 laspy[lazrs] / pye57；未安装时给出明确提示。
"""

from __future__ import annotations

import os

import numpy as np

from core.model.entities import CloudEntity, ScalarField

LAS_SIGNATURE = b"LASF"


def _fmt_arrays(point_format: int):
    """返回 (name, dtype) 列表（不含尾部附加字节）。"""
    base = [
        ("X", "<i4"), ("Y", "<i4"), ("Z", "<i4"),
        ("intensity", "<u2"), ("flags", "u1"), ("classification", "u1"),
        ("scan_angle", "i1"), ("user", "u1"), ("point_source", "<u2"),
    ]
    gps = [("gps_time", "<f8")]
    rgb = [("red", "<u2"), ("green", "<u2"), ("blue", "<u2")]
    fmt6 = [
        ("X", "<i4"), ("Y", "<i4"), ("Z", "<i4"), ("intensity", "<u2"),
        ("return_bits", "u1"), ("flags", "u1"), ("classification", "u1"),
        ("user", "u1"), ("scan_angle", "<i2"), ("point_source", "<u2"),
    ] + gps
    table = {
        0: base,
        1: base + gps,
        2: base + rgb,
        3: base + gps + rgb,
        6: fmt6,
        7: fmt6 + rgb,
        8: fmt6 + rgb + [("nir", "<u2")],
    }
    return table.get(point_format)


def _parse_header(buf: bytes) -> dict:
    if buf[:4] != LAS_SIGNATURE:
        raise ValueError("不是有效的 LAS 文件（缺少 LASF 签名）")
    major = buf[24]
    minor = buf[25]
    header_size = int(np.frombuffer(buf, dtype="<u2", count=1, offset=94)[0])
    offset = int(np.frombuffer(buf, dtype="<u4", count=1, offset=96)[0])
    fmt_byte = int(buf[104])
    point_format = fmt_byte & 0x3F
    record_length = int(np.frombuffer(buf, dtype="<u2", count=1, offset=105)[0])
    legacy_count = int(np.frombuffer(buf, dtype="<u4", count=1, offset=107)[0])
    scale = np.frombuffer(buf, dtype="<f8", count=3, offset=131)
    origin = np.frombuffer(buf, dtype="<f8", count=3, offset=155)
    count = legacy_count
    if (major, minor) >= (1, 4) and len(buf) >= 255:
        count = int(np.frombuffer(buf, dtype="<u8", count=1, offset=247)[0]) or legacy_count
    if header_size < 227 or offset < header_size:
        raise ValueError("LAS 头损坏（header_size/offset 非法）")
    return {
        "version": f"{major}.{minor}",
        "point_format": point_format,
        "record_length": record_length,
        "count": count,
        "scale": scale.astype(np.float64),
        "origin": origin.astype(np.float64),
        "offset": offset,
    }


def read_las(path: str) -> CloudEntity:
    with open(path, "rb") as f:
        data = f.read()
    if len(data) < 227:
        raise ValueError("LAS 文件过短")
    meta = _parse_header(data)
    layout = _fmt_arrays(meta["point_format"])
    if layout is None:
        raise ValueError(f"暂不支持 LAS 点格式 {meta['point_format']}（支持 0/1/2/3/6/7/8）")

    dtype = np.dtype(layout)
    if dtype.itemsize > meta["record_length"]:
        raise ValueError("LAS 记录长度小于点格式所需字节数")
    # 用 record_length 对齐，跳过格式尾部扩展字节
    padded = np.dtype({"names": [n for n, _ in layout] + ["_pad"],
                       "formats": [d for _, d in layout] + [f"V{meta['record_length'] - dtype.itemsize}"],
                       "offsets": list(np.cumsum([0] + [np.dtype(d).itemsize for _, d in layout])[:-1]) + [dtype.itemsize],
                       "itemsize": meta["record_length"]})
    raw = np.frombuffer(data, dtype=padded, count=meta["count"], offset=meta["offset"])

    s, o = meta["scale"], meta["origin"]
    xyz = np.c_[raw["X"] * s[0] + o[0],
                raw["Y"] * s[1] + o[1],
                raw["Z"] * s[2] + o[2]].astype(np.float32)

    fields = {"intensity": ScalarField(
        "intensity", raw["intensity"].astype(np.float32), kind="scalar")}
    classification = raw["classification"]
    if meta["point_format"] < 6:
        classification = classification & 0x1F
    fields["classification"] = ScalarField(
        "classification", classification.astype(np.float32), kind="label")
    if "red" in raw.dtype.names:
        rgb = np.c_[raw["red"], raw["green"], raw["blue"]].astype(np.float32) / 65535.0
        fields["rgb"] = ScalarField("rgb", rgb, kind="color")

    entity = CloudEntity(name=os.path.basename(path), path=os.path.abspath(path), xyz=xyz,
                         fields=fields, dim_hint=3 + len(fields))
    entity.info = f"LAS {meta['version']} fmt{meta['point_format']} · {len(xyz):,} 点"
    return entity


def write_las(entity, path: str, *, scale: float = 0.001) -> None:
    """写 LAS 1.2：有点格式 2（RGB）或 0；保留 intensity/classification。"""
    xyz = np.asarray(entity.xyz, dtype=np.float64)
    if len(xyz) == 0:
        raise ValueError("空点云无法导出 LAS")
    if not np.isfinite(xyz).all() or not np.isfinite(scale) or scale <= 0:
        raise ValueError("LAS 导出需要有限坐标和正的坐标精度")
    has_rgb = "rgb" in entity.fields and np.asarray(entity.fields["rgb"].data).shape == (len(xyz), 3)
    point_format = 2 if has_rgb else 0
    record_length = 26 if has_rgb else 20

    origin = np.floor(xyz.min(axis=0)).astype(np.float64)
    scale_arr = np.array([scale, scale, scale], dtype=np.float64)
    quantized = np.round((xyz - origin) / scale_arr)
    if np.any(quantized > np.iinfo(np.int32).max):
        raise ValueError("坐标范围超出毫米精度 LAS 的表示范围，请改用 PLY/PCD")
    ints = quantized.astype(np.int32)

    intensity = entity.fields.get("intensity")
    if intensity is not None:
        values = np.asarray(intensity.data, dtype=np.float64).reshape(-1)
        if values.size and np.nanmax(values) <= 1.0001:
            values = values * 65535.0
        intensity_u16 = np.clip(np.round(values), 0, 65535).astype("<u2")
    else:
        intensity_u16 = np.zeros(len(xyz), dtype="<u2")

    labels = entity.fields.get("classification") or entity.fields.get("labels")
    if labels is not None:
        values = np.asarray(labels.data, dtype=np.float64)
        if not np.isfinite(values).all() or np.any((values < 0) | (values > 31)):
            raise ValueError("LAS 1.2 分类值需在 0–31 范围内；请改用 PLY/PCD 保留当前标签")
        cls = np.round(values).astype("u1")
    else:
        cls = np.zeros(len(xyz), dtype="u1")

    header_size, offset = 227, 227
    version = (1, 2)
    header = bytearray(header_size)
    header[0:4] = LAS_SIGNATURE
    header[24] = version[0]
    header[25] = version[1]
    np.frombuffer(header, dtype="<u2", count=1, offset=94)[:] = header_size
    np.frombuffer(header, dtype="<u4", count=1, offset=96)[:] = offset
    header[104] = point_format
    np.frombuffer(header, dtype="<u2", count=1, offset=105)[:] = record_length
    np.frombuffer(header, dtype="<u4", count=1, offset=107)[:] = len(xyz)
    np.frombuffer(header, dtype="<f8", count=3, offset=131)[:] = scale_arr
    np.frombuffer(header, dtype="<f8", count=3, offset=155)[:] = origin
    # 包围盒（float64 位置 179..227）
    mins, maxs = xyz.min(axis=0), xyz.max(axis=0)
    np.frombuffer(header, dtype="<f8", count=6, offset=179)[:] = np.c_[maxs, mins].ravel()

    if has_rgb:
        rgb = np.asarray(entity.fields["rgb"].data, dtype=np.float64)
        if rgb.size and np.nanmax(rgb) <= 1.0001:
            rgb = rgb * 65535.0
        rgb_u16 = np.clip(np.round(rgb), 0, 65535).astype("<u2")
        dtype = np.dtype([("X", "<i4"), ("Y", "<i4"), ("Z", "<i4"),
                          ("intensity", "<u2"), ("flags", "u1"), ("classification", "u1"),
                          ("scan_angle", "i1"), ("user", "u1"), ("point_source", "<u2"),
                          ("red", "<u2"), ("green", "<u2"), ("blue", "<u2")])
        rec = np.zeros(len(xyz), dtype=dtype)
        rec["red"], rec["green"], rec["blue"] = rgb_u16[:, 0], rgb_u16[:, 1], rgb_u16[:, 2]
    else:
        dtype = np.dtype([("X", "<i4"), ("Y", "<i4"), ("Z", "<i4"),
                          ("intensity", "<u2"), ("flags", "u1"), ("classification", "u1"),
                          ("scan_angle", "i1"), ("user", "u1"), ("point_source", "<u2")])
        rec = np.zeros(len(xyz), dtype=dtype)
    rec["X"], rec["Y"], rec["Z"] = ints[:, 0], ints[:, 1], ints[:, 2]
    rec["intensity"] = intensity_u16
    rec["classification"] = cls

    with open(path, "wb") as f:
        f.write(bytes(header))
        f.write(rec.tobytes())


# ---------------- 可选依赖格式 ----------------

def _require(module: str, hint: str):
    try:
        return __import__(module)
    except ImportError:
        raise ValueError(f"{hint}。请先安装：{module}") from None


def read_laz(path: str) -> CloudEntity:
    _require("laspy", "读取 .laz 需要 laspy（含 lazrs）")
    import laspy

    las = laspy.read(path)
    xyz = np.c_[las.x, las.y, las.z].astype(np.float32)
    fields = {}
    dims = set(las.point_format.dimension_names)
    if "intensity" in dims:
        fields["intensity"] = ScalarField(
            "intensity", np.asarray(las.intensity, dtype=np.float32), kind="scalar")
    if {"red", "green", "blue"} <= dims:
        fields["rgb"] = ScalarField(
            "rgb", np.c_[las.red, las.green, las.blue].astype(np.float32) / 65535.0, kind="color")
    if "classification" in dims:
        fields["classification"] = ScalarField(
            "classification", np.asarray(las.classification, dtype=np.float32), kind="label")
    entity = CloudEntity(name=os.path.basename(path), path=os.path.abspath(path), xyz=xyz,
                         fields=fields, dim_hint=3 + len(fields))
    entity.info = f"LAZ · {len(xyz):,} 点"
    return entity


def read_e57(path: str) -> CloudEntity:
    _require("pye57", "读取 .e57 需要 pye57")
    import pye57

    parts: list[np.ndarray] = []
    intensity_parts: list[np.ndarray] = []
    color_parts: list[np.ndarray] = []
    has_intensity = has_color = False
    with pye57.E57(path) as e57:
        for i in range(int(e57.scan_count)):
            data = e57.read_scan(i, intensity=True, colors=True, transform=True,
                                 ignore_missing_fields=True)
            pts = np.c_[data["cartesianX"], data["cartesianY"], data["cartesianZ"]].astype(np.float32)
            valid = np.isfinite(pts).all(axis=1)
            parts.append(pts[valid])
            intensity = np.zeros(len(pts), dtype=np.float32)
            if "intensity" in data:
                intensity = np.asarray(data["intensity"], dtype=np.float32)
                has_intensity = True
            intensity_parts.append(intensity[valid])
            rgb = np.full((len(pts), 3), 0.6, dtype=np.float32)
            if {"colorRed", "colorGreen", "colorBlue"} <= set(data):
                # pye57 exposes E57 colors as uint8, including scans with a pose.
                rgb = np.c_[data["colorRed"], data["colorGreen"], data["colorBlue"]].astype(np.float32) / 255.0
                has_color = True
            color_parts.append(rgb[valid])
    if not parts or not any(len(part) for part in parts):
        raise ValueError("E57 中没有可读的点")
    xyz = np.concatenate(parts, axis=0)
    fields = {}
    if has_intensity:
        fields["intensity"] = ScalarField(
            "intensity", np.concatenate(intensity_parts).astype(np.float32), kind="scalar")
    if has_color:
        rgb = np.concatenate(color_parts).astype(np.float32)
        fields["rgb"] = ScalarField("rgb", np.clip(rgb, 0.0, 1.0), kind="color")
    entity = CloudEntity(name=os.path.basename(path), path=os.path.abspath(path), xyz=xyz,
                         fields=fields, dim_hint=3 + len(fields))
    entity.info = f"E57 · {len(xyz):,} 点 · {len(parts)} 扫描"
    return entity
