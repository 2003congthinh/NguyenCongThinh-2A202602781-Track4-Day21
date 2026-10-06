"""Một cửa duy nhất để đọc dữ liệu: tự nhận biết KITTI hay nuScenes dựa trên cấu trúc thư mục.

    from starter.datasets import list_frames, load_frame, load_points
    frames = list_frames("data/kitti_mini")              # ['000001', '000004', ...]
    frames = list_frames("data/nuscenes_mini_subset")    # ['scene-0103_000', ...]
    fr = load_frame("data/kitti_mini", frames[0])        # dict: points, calib, image, labels

- KITTI: thư mục có training/velodyne/*.bin (data/synthetic, data/kitti_mini).
- nuScenes: thư mục có v1.0-mini/sample.json (data/nuscenes_mini_subset).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from starter import kitti_io, nuscenes_io


def dataset_type(data_root: str | Path) -> str:
    if nuscenes_io.is_nuscenes_root(data_root):
        return "nuscenes"
    if (Path(data_root) / "training" / "velodyne").is_dir():
        return "kitti"
    raise FileNotFoundError(
        f"'{data_root}' không giống KITTI (thiếu training/velodyne/) cũng không giống nuScenes "
        f"(thiếu v1.0-mini/sample.json). Kiểm tra lại đường dẫn --data-root hoặc xem data/README.md.")


def list_frames(data_root: str | Path) -> list[str]:
    if dataset_type(data_root) == "nuscenes":
        return nuscenes_io.list_frames(data_root)
    return kitti_io.list_frames(data_root)


def load_points(data_root: str | Path, frame_id: str) -> np.ndarray:
    """Chỉ đọc point cloud (N, 4), nhanh hơn load_frame khi không cần ảnh/label."""
    if dataset_type(data_root) == "nuscenes":
        return nuscenes_io.load_lidar(nuscenes_io.lidar_path(data_root, frame_id))
    return kitti_io.load_velodyne(kitti_io.frame_paths(data_root, frame_id)["velodyne"])


def load_frame(data_root: str | Path, frame_id: str, **kwargs) -> dict:
    """kwargs chỉ dùng cho nuScenes: camera="CAM_FRONT", use_ego_motion=True."""
    if dataset_type(data_root) == "nuscenes":
        return nuscenes_io.load_frame(data_root, frame_id, **kwargs)
    return kitti_io.load_frame(data_root, frame_id)
