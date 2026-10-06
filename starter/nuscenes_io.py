"""Đọc nuScenes (data/nuscenes_mini_subset, bản v1.0-mini đã lọc) và trả về cùng cấu trúc với KITTI.

Không cần cài nuscenes-devkit. Hàm `load_frame` trả về dict giống `kitti_io.load_frame`:
points, calib (KittiCalib), image, labels (KittiObject), nên code projection viết cho KITTI
chạy được nguyên vẹn trên nuScenes.

Khác biệt quan trọng so với KITTI, cần nhớ khi phân tích:
- LiDAR frame của nuScenes: x sang PHẢI, y về PHÍA TRƯỚC, z lên trên (KITTI: x phía trước, y sang trái).
  Vì vậy azimuth 0° trong data_health.py ở nuScenes là hướng bên phải xe, không phải phía trước.
- Point cloud có 5 cột (x, y, z, intensity 0–255, ring index). Ở đây intensity được chia 255 để cùng thang 0–1 với KITTI.
- LiDAR và camera chụp ở hai thời điểm khác nhau (lệch tới vài chục ms), nên chuỗi biến đổi phải đi qua
  global frame bằng ego pose ở từng thời điểm:
      cam <- ego(t_cam) <- global <- ego(t_lidar) <- lidar
  Truyền `use_ego_motion=False` để bỏ qua bước này (giả định hai sensor chụp cùng lúc) và xem lỗi Time.
- frame id có dạng "<scene>_<số thứ tự keyframe 3 chữ số>", ví dụ "scene-0103_000".
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import numpy as np

from starter.kitti_io import KittiCalib, KittiObject, load_image

VERSION = "v1.0-mini"
CATEGORY_MAP = {
    "vehicle.car": "Car", "vehicle.truck": "Truck", "vehicle.trailer": "Trailer",
    "vehicle.bus.bendy": "Bus", "vehicle.bus.rigid": "Bus", "vehicle.construction": "ConstructionVehicle",
    "vehicle.bicycle": "Bicycle", "vehicle.motorcycle": "Motorcycle",
    "human.pedestrian.adult": "Pedestrian", "human.pedestrian.child": "Pedestrian",
    "human.pedestrian.construction_worker": "Pedestrian", "human.pedestrian.police_officer": "Pedestrian",
    "movable_object.barrier": "Barrier", "movable_object.trafficcone": "TrafficCone",
}
# nuScenes visibility (1: 0–40%, 2: 40–60%, 3: 60–80%, 4: 80–100% nhìn thấy) -> KITTI occluded (0 = thấy rõ)
VISIBILITY_TO_OCCLUDED = {"1": 2, "2": 2, "3": 1, "4": 0}


def is_nuscenes_root(data_root: str | Path) -> bool:
    return (Path(data_root) / VERSION / "sample.json").exists()


def _quat_to_rot(q) -> np.ndarray:
    w, x, y, z = q
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])


def _pose(rec: dict) -> np.ndarray:
    T = np.eye(4)
    T[:3, :3] = _quat_to_rot(rec["rotation"])
    T[:3, 3] = rec["translation"]
    return T


class _Tables:
    def __init__(self, root: Path):
        def load(name):
            return json.loads((root / VERSION / f"{name}.json").read_text(encoding="utf-8"))

        self.root = root
        idx = {name: {r["token"]: r for r in load(name)} for name in
               ("scene", "sample", "sample_data", "calibrated_sensor", "sensor", "ego_pose",
                "sample_annotation", "instance", "category", "visibility")}
        self.__dict__.update(idx)
        self.data_of_sample: dict[str, dict[str, dict]] = {}
        for d in self.sample_data.values():
            if d["is_key_frame"]:
                channel = self.sensor[self.calibrated_sensor[d["calibrated_sensor_token"]]["sensor_token"]]["channel"]
                self.data_of_sample.setdefault(d["sample_token"], {})[channel] = d
        self.anns_of_sample: dict[str, list[dict]] = {}
        for a in self.sample_annotation.values():
            self.anns_of_sample.setdefault(a["sample_token"], []).append(a)
        self.frames: dict[str, str] = {}
        for scene in sorted(self.scene.values(), key=lambda s: s["name"]):
            token, i = scene["first_sample_token"], 0
            while token:
                self.frames[f"{scene['name']}_{i:03d}"] = token
                token, i = self.sample[token]["next"], i + 1


@lru_cache(maxsize=4)
def _tables(data_root: str) -> _Tables:
    return _Tables(Path(data_root))


def list_frames(data_root: str | Path) -> list[str]:
    return list(_tables(str(data_root)).frames)


def lidar_path(data_root: str | Path, frame_id: str) -> Path:
    t = _tables(str(data_root))
    return t.root / t.data_of_sample[t.frames[frame_id]]["LIDAR_TOP"]["filename"]


def load_lidar(path: str | Path) -> np.ndarray:
    """(N, 4) float32 x, y, z, intensity (đã chia 255). Ring index bị bỏ để cùng format với KITTI."""
    pts = np.fromfile(path, dtype=np.float32).reshape(-1, 5)[:, :4].copy()
    pts[:, 3] /= 255.0
    return pts


def load_frame(data_root: str | Path, frame_id: str, camera: str = "CAM_FRONT",
               use_ego_motion: bool = True) -> dict:
    t = _tables(str(data_root))
    if frame_id not in t.frames:
        raise KeyError(f"Không có frame '{frame_id}'. Ví dụ frame hợp lệ: {list(t.frames)[:3]}")
    sample_token = t.frames[frame_id]
    lidar, cam = t.data_of_sample[sample_token]["LIDAR_TOP"], t.data_of_sample[sample_token][camera]
    cs_lidar, cs_cam = t.calibrated_sensor[lidar["calibrated_sensor_token"]], t.calibrated_sensor[cam["calibrated_sensor_token"]]
    ego_lidar = _pose(t.ego_pose[lidar["ego_pose_token"]])
    ego_cam = _pose(t.ego_pose[cam["ego_pose_token"]]) if use_ego_motion else ego_lidar

    T_cam_global = np.linalg.inv(_pose(cs_cam)) @ np.linalg.inv(ego_cam)
    T_cam_lidar = T_cam_global @ ego_lidar @ _pose(cs_lidar)
    K = np.array(cs_cam["camera_intrinsic"])
    calib = KittiCalib(P2=np.hstack([K, np.zeros((3, 1))]), R0_rect=np.eye(3), Tr_velo_to_cam=T_cam_lidar[:3, :])

    image = load_image(t.root / cam["filename"])
    return {
        "frame_id": frame_id,
        "points": load_lidar(t.root / lidar["filename"]),
        "calib": calib,
        "image": image,
        "labels": _labels(t, sample_token, T_cam_global, K, image.shape),
        "timestamp_lidar_us": lidar["timestamp"],
        "timestamp_camera_us": cam["timestamp"],
    }


def _labels(t: _Tables, sample_token: str, T_cam_global: np.ndarray, K: np.ndarray,
            image_shape) -> list[KittiObject]:
    from starter.projection import box3d_corners_cam

    h_img, w_img = image_shape[:2]
    R_cg = T_cam_global[:3, :3]
    objects = []
    for a in t.anns_of_sample.get(sample_token, []):
        category = t.category[t.instance[a["instance_token"]]["category_token"]]["name"]
        w, l, h = a["size"]
        center = T_cam_global @ np.r_[a["translation"], 1.0]
        bottom = center[:3] + R_cg @ np.array([0.0, 0.0, -h / 2])
        heading = R_cg @ _quat_to_rot(a["rotation"]) @ np.array([1.0, 0.0, 0.0])
        ry = float(np.arctan2(-heading[2], heading[0]))
        obj = KittiObject(type=CATEGORY_MAP.get(category, category.split(".")[-1]), truncated=0.0,
                          occluded=VISIBILITY_TO_OCCLUDED.get(a["visibility_token"], 3),
                          alpha=ry - float(np.arctan2(bottom[0], bottom[2])), bbox=np.zeros(4),
                          dimensions=np.array([h, w, l]), location=bottom, rotation_y=ry)
        corners = box3d_corners_cam(obj)
        if (corners[:, 2] <= 0.1).any():
            continue
        uv = (K @ corners.T).T
        uv = uv[:, :2] / uv[:, 2:3]
        x1, y1 = uv.min(0)
        x2, y2 = uv.max(0)
        cx1, cy1, cx2, cy2 = max(x1, 0), max(y1, 0), min(x2, w_img - 1), min(y2, h_img - 1)
        if cx1 >= cx2 or cy1 >= cy2:
            continue
        obj.bbox = np.array([cx1, cy1, cx2, cy2])
        obj.truncated = float(1 - (cx2 - cx1) * (cy2 - cy1) / max((x2 - x1) * (y2 - y1), 1e-6))
        objects.append(obj)
    return objects
