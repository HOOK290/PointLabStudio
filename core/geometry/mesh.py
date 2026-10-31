"""E25：法线、网格重建与 C2C / C2M 距离。"""

from __future__ import annotations

import numpy as np


def estimate_normals(xyz: np.ndarray, k: int = 20) -> np.ndarray:
    """k 近邻 PCA 法线，按“背离质心”统一朝向。"""
    from core.algorithms.registration import estimate_normals as _est
    return _est(xyz, k=k)


def c2c_distance(source: np.ndarray, target: np.ndarray) -> np.ndarray:
    """源点云每点到目标点云的最近距离。"""
    from scipy.spatial import cKDTree

    source = np.asarray(source, dtype=np.float64)
    target = np.asarray(target, dtype=np.float64)
    if len(target) == 0:
        raise ValueError("目标点云为空")
    dist, _ = cKDTree(target).query(source, k=1, workers=-1)
    return dist.astype(np.float32)


def poisson_mesh(xyz: np.ndarray, normals: np.ndarray | None = None,
                 depth: int = 8) -> tuple[np.ndarray, np.ndarray]:
    """Poisson 表面重建，返回 (vertices, triangles)。"""
    import open3d as o3d

    xyz = np.asarray(xyz, dtype=np.float64)
    if len(xyz) < 100:
        raise ValueError("网格重建需要至少 100 个点")
    cloud = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(xyz))
    if normals is None:
        cloud.estimate_normals(o3d.geometry.KDTreeSearchParamKNN(knn=30))
        try:
            cloud.orient_normals_consistent_tangent_plane(20)
        except RuntimeError:
            # 平面/退化输入（Qhull 共面）无法做切线平面定向，改为朝向 +Z。
            cloud.orient_normals_to_align_with_direction(np.array([0.0, 0.0, 1.0]))
    else:
        cloud.normals = o3d.utility.Vector3dVector(np.asarray(normals, dtype=np.float64))
    mesh, _ = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(cloud, depth=depth)
    mesh.remove_degenerate_triangles()
    mesh.remove_duplicated_vertices()
    return (np.asarray(mesh.vertices, dtype=np.float32),
            np.asarray(mesh.triangles, dtype=np.int32))


def write_mesh_ply(path: str, vertices: np.ndarray, triangles: np.ndarray) -> None:
    import open3d as o3d

    mesh = o3d.geometry.TriangleMesh()
    mesh.vertices = o3d.utility.Vector3dVector(np.asarray(vertices, dtype=np.float64))
    mesh.triangles = o3d.utility.Vector3iVector(np.asarray(triangles, dtype=np.int32))
    mesh.compute_vertex_normals()
    if not o3d.io.write_triangle_mesh(path, mesh):
        raise RuntimeError(f"网格写入失败: {path}")


def read_mesh(path: str) -> tuple[np.ndarray, np.ndarray]:
    import open3d as o3d

    mesh = o3d.io.read_triangle_mesh(path)
    if len(mesh.vertices) == 0:
        raise ValueError(f"无法读取网格: {path}")
    return (np.asarray(mesh.vertices, dtype=np.float32),
            np.asarray(mesh.triangles, dtype=np.int32))


def c2m_distance(points: np.ndarray, vertices: np.ndarray, triangles: np.ndarray) -> np.ndarray:
    """点到三角网格的最近距离（Open3D RaycastingScene）。"""
    import open3d as o3d

    points = np.asarray(points, dtype=np.float32)
    verts = np.asarray(vertices, dtype=np.float32)
    tris = np.asarray(triangles, dtype=np.uint32)
    if len(tris) == 0:
        raise ValueError("网格没有三角面")
    scene = o3d.t.geometry.RaycastingScene()
    scene.add_triangles(o3d.t.geometry.TriangleMesh(
        o3d.core.Tensor(verts), o3d.core.Tensor(tris)))
    query = o3d.core.Tensor(points, dtype=o3d.core.Dtype.Float32)
    return scene.compute_distance(query).numpy().astype(np.float32)
