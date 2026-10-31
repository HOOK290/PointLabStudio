"""E25：法线 / C2C / C2M / 网格读写。"""

import numpy as np

from core.geometry import mesh


def test_estimate_normals_on_plane():
    xs, ys = np.meshgrid(np.linspace(-2, 2, 30), np.linspace(-2, 2, 30))
    xyz = np.stack([xs.ravel(), ys.ravel(), np.zeros(xs.size)], axis=1)
    normals = mesh.estimate_normals(xyz, k=12)
    assert normals.shape == xyz.shape
    assert np.allclose(np.abs(normals[:, 2]), 1.0, atol=0.05)


def test_c2c_distance_offset_cloud():
    grid = np.stack(np.meshgrid(np.arange(4.0), np.arange(4.0), np.arange(4.0)), axis=-1)
    a = grid.reshape(-1, 3)
    b = a + np.array([0.5, 0.0, 0.0])
    dist = mesh.c2c_distance(a, b)
    assert dist.shape == (64,)
    assert abs(float(dist.mean()) - 0.5) < 0.05


def test_c2m_distance_to_triangle():
    verts = np.array([[0, 0, 0], [2, 0, 0], [0, 2, 0]], dtype=np.float32)
    tris = np.array([[0, 1, 2]], dtype=np.int32)
    points = np.array([[0.2, 0.2, 1.0], [0.2, 0.2, 2.0]], dtype=np.float32)
    dist = mesh.c2m_distance(points, verts, tris)
    assert dist.shape == (2,)
    assert abs(float(dist[0]) - 1.0) < 1e-4
    assert abs(float(dist[1]) - 2.0) < 1e-4


def test_mesh_ply_roundtrip(tmp_path):
    verts = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=np.float32)
    tris = np.array([[0, 1, 2]], dtype=np.int32)
    path = tmp_path / "tri.ply"
    mesh.write_mesh_ply(str(path), verts, tris)
    v2, t2 = mesh.read_mesh(str(path))
    assert np.allclose(v2, verts, atol=1e-5)
    assert np.array_equal(t2, tris)
