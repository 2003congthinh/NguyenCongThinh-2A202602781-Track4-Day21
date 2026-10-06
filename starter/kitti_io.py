"""Đọc dữ liệu định dạng KITTI 3D object (velodyne, calib, image_2, label_2).

Quy ước KITTI cần nhớ:
- Velodyne frame: x forward, y left, z up (đơn vị mét).
- Camera (rectified) frame: x right, y down, z forward.
- Label 3D nằm trong rectified camera frame, `location` là BOTTOM center của box,
  `dimensions` theo thứ tự (h, w, l), `rotation_y` quay quanh trục y của camera.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass
class KittiCalib:
    P2: np.ndarray              # (3, 4) projection của camera trái màu (image_2), đã rectify
    R0_rect: np.ndarray         # (3, 3) rectification
    Tr_velo_to_cam: np.ndarray  # (3, 4) extrinsic: velodyne -> camera 0 (chưa rectify)

    @property
    def T_cam_velo(self) -> np.ndarray:
        """Ma trận 4x4 đưa điểm từ velodyne frame sang rectified camera frame."""
        R0 = np.eye(4)
        R0[:3, :3] = self.R0_rect
        Tr = np.eye(4)
        Tr[:3, :] = self.Tr_velo_to_cam
        return R0 @ Tr


@dataclass
class KittiObject:
    type: str
    truncated: float
    occluded: int
    alpha: float
    bbox: np.ndarray        # (4,) x1, y1, x2, y2 pixel
    dimensions: np.ndarray  # (3,) h, w, l mét
    location: np.ndarray    # (3,) x, y, z bottom center, rectified camera frame
    rotation_y: float
    score: float | None = None


def frame_paths(data_root: str | Path, frame_id: str, split: str = "training") -> dict[str, Path]:
    root = Path(data_root) / split
    return {
        "velodyne": root / "velodyne" / f"{frame_id}.bin",
        "calib": root / "calib" / f"{frame_id}.txt",
        "image": root / "image_2" / f"{frame_id}.png",
        "label": root / "label_2" / f"{frame_id}.txt",
    }


def list_frames(data_root: str | Path, split: str = "training") -> list[str]:
    return sorted(p.stem for p in (Path(data_root) / split / "velodyne").glob("*.bin"))


def load_velodyne(path: str | Path) -> np.ndarray:
    """Trả về (N, 4) float32: x, y, z, reflectance. Không tự lọc NaN."""
    raw = np.fromfile(path, dtype=np.float32)
    if raw.size % 4 != 0:
        raise ValueError(f"{path}: số float32 ({raw.size}) không chia hết cho 4 -> sai format?")
    return raw.reshape(-1, 4)


def load_calib(path: str | Path) -> KittiCalib:
    values: dict[str, np.ndarray] = {}
    for line in Path(path).read_text().splitlines():
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        values[key.strip()] = np.array(val.split(), dtype=np.float64)

    r0 = values.get("R0_rect", values.get("R_rect"))
    tr = values.get("Tr_velo_to_cam", values.get("Tr_velo_cam"))
    if r0 is None or tr is None or "P2" not in values:
        raise KeyError(f"{path}: thiếu P2 / R0_rect / Tr_velo_to_cam")
    return KittiCalib(
        P2=values["P2"].reshape(3, 4),
        R0_rect=r0.reshape(3, 3),
        Tr_velo_to_cam=tr.reshape(3, 4),
    )


def load_image(path: str | Path) -> np.ndarray:
    """Ảnh BGR uint8 (H, W, 3)."""
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(path)
    return img


def load_labels(path: str | Path) -> list[KittiObject]:
    objects = []
    path = Path(path)
    if not path.exists():
        return objects
    for line in path.read_text().splitlines():
        f = line.split()
        if not f or f[0] == "DontCare":
            continue
        objects.append(KittiObject(
            type=f[0],
            truncated=float(f[1]),
            occluded=int(float(f[2])),
            alpha=float(f[3]),
            bbox=np.array(f[4:8], dtype=np.float64),
            dimensions=np.array(f[8:11], dtype=np.float64),
            location=np.array(f[11:14], dtype=np.float64),
            rotation_y=float(f[14]),
            score=float(f[15]) if len(f) > 15 else None,
        ))
    return objects


def load_frame(data_root: str | Path, frame_id: str, split: str = "training") -> dict:
    p = frame_paths(data_root, frame_id, split)
    return {
        "frame_id": frame_id,
        "points": load_velodyne(p["velodyne"]),
        "calib": load_calib(p["calib"]),
        "image": load_image(p["image"]),
        "labels": load_labels(p["label"]),
    }
