"""Các phép làm xấu point cloud cho topic C (degradation stress test).

Mọi hàm nhận/trả (N, 4) float32 [x, y, z, intensity] và không sửa input tại chỗ.
Luôn truyền `seed` để kết quả tái lập được giữa các lần chạy.
"""
from __future__ import annotations

import numpy as np


def random_dropout(points: np.ndarray, keep_ratio: float, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return points[rng.random(len(points)) < keep_ratio]


def range_dropout(points: np.ndarray, max_range_m: float) -> np.ndarray:
    return points[np.linalg.norm(points[:, :2], axis=1) <= max_range_m]


def sector_dropout(points: np.ndarray, az_start_deg: float, az_end_deg: float) -> np.ndarray:
    """Bỏ các điểm có azimuth trong [start, end] độ (0 = phía trước, dương = bên trái)."""
    az = np.degrees(np.arctan2(points[:, 1], points[:, 0]))
    return points[~((az >= az_start_deg) & (az <= az_end_deg))]


def beam_dropout(points: np.ndarray, keep_every: int = 2, n_beams: int = 64,
                 fov_deg: tuple[float, float] = (-24.9, 2.0)) -> np.ndarray:
    """Giả lập LiDAR ít beam hơn bằng cách gán beam theo góc elevation rồi giữ 1/keep_every."""
    elev = np.degrees(np.arctan2(points[:, 2], np.linalg.norm(points[:, :2], axis=1)))
    beam = np.clip(((elev - fov_deg[0]) / (fov_deg[1] - fov_deg[0]) * n_beams).astype(int), 0, n_beams - 1)
    return points[beam % keep_every == 0]


def gaussian_noise(points: np.ndarray, sigma_xyz_m: float = 0.02, sigma_intensity: float = 0.0,
                   seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    out = points.copy()
    out[:, :3] += rng.normal(0, sigma_xyz_m, size=(len(out), 3)).astype(out.dtype)
    if sigma_intensity:
        out[:, 3] = np.clip(out[:, 3] + rng.normal(0, sigma_intensity, len(out)), 0, 1)
    return out


def motion_smear(points: np.ndarray, ego_speed_mps: float, sweep_time_s: float = 0.1) -> np.ndarray:
    """Giả lập thiếu deskew: mỗi điểm bị dịch theo -x tỉ lệ với thời điểm quét của nó
    (suy từ azimuth, LiDAR quay 360° trong sweep_time_s)."""
    az = np.arctan2(points[:, 1], points[:, 0])
    t = (az + np.pi) / (2 * np.pi) * sweep_time_s
    out = points.copy()
    out[:, 0] -= (ego_speed_mps * t).astype(out.dtype)
    return out
