"""P3 分割与配准算法测试。"""

from __future__ import annotations

import numpy as np

from core.algorithms import registration, segmentation


def test_plane_ransac_finds_ground():
    rng = np.random.default_rng(0)
    plane = np.stack([
        rng.uniform(-10, 10, 800),
        rng.uniform(-10, 10, 800),
        rng.normal(0, 0.01, 800),
    ], axis=1)
    outliers = rng.uniform(-10, 10, (200, 3))
    pts = np.vstack([plane, outliers]).astype(np.float32)

    (normal, d), mask = segmentation.plane_ransac(pts, distance=0.05, max_iterations=200)
    assert abs(float(normal[2])) > 0.9
    assert mask[:800].mean() > 0.95
    assert mask[800:].mean() < 0.2


def test_extract_ground_rejects_vertical_plane():
    rng = np.random.default_rng(1)
    ground = np.stack([rng.uniform(-5, 5, 600), rng.uniform(-5, 5, 600),
                       rng.normal(0, 0.005, 600)], axis=1)
    wall = np.stack([np.zeros(300), rng.uniform(-5, 5, 300),
                     rng.uniform(0, 3, 300)], axis=1)
    pts = np.vstack([ground, wall]).astype(np.float32)

    (normal, d), mask = segmentation.extract_ground(pts, distance=0.05, max_iterations=300)
    assert abs(float(normal[2])) > 0.9
    assert mask[:600].mean() > 0.9


def test_dbscan_clusters():
    rng = np.random.default_rng(2)
    c1 = rng.normal(0, 0.2, (120, 3))
    c2 = rng.normal(5, 0.2, (120, 3))
    noise = np.array([[20, 20, 20], [21, 21, 21]], dtype=np.float32)
    pts = np.vstack([c1, c2, noise]).astype(np.float32)

    labels = segmentation.dbscan(pts, eps=0.6, min_samples=5)
    clusters = set(labels[labels >= 0].tolist())
    assert len(clusters) == 2
    assert (labels[240:] == -1).all()


def test_icp_recovers_transform():
    rng = np.random.default_rng(3)
    target = rng.uniform(-2, 2, (1500, 3))
    angle = np.deg2rad(8.0)
    rotation = np.array([
        [np.cos(angle), -np.sin(angle), 0],
        [np.sin(angle), np.cos(angle), 0],
        [0, 0, 1],
    ])
    translation = np.array([0.3, -0.2, 0.1])
    source = (target @ rotation.T + translation).astype(np.float32)
    target = target.astype(np.float32)

    transform, rmse = registration.icp(source, target, max_iterations=60)
    aligned = registration.apply_transform(source, transform)
    err = float(np.mean(np.linalg.norm(aligned - target, axis=1)))
    assert err < 0.05
    assert rmse < 0.1
