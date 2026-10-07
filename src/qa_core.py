from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from starter.datasets import dataset_type, load_frame
from starter.kitti_io import KittiCalib, KittiObject
from starter.projection import cam_to_image, perturb_extrinsic, project_velo_to_image, velo_to_cam

EVAL_CLASSES = {"Car", "Van", "Truck", "Tram", "Bus", "Trailer", "ConstructionVehicle",
                "Pedestrian", "Person_sitting", "Cyclist", "Bicycle", "Motorcycle"}
MIN_OBJ_POINTS = 10
GROUND_MARGIN_M = 0.10
MAX_TRUNCATED = 0.3
MAX_OCCLUDED = 1
DIST_BINS = [(0.0, 15.0, "near<15m"), (15.0, 30.0, "mid15-30m"), (30.0, 1e9, "far>30m")]


@dataclass
class Perturb:
    name: str
    roll_deg: float = 0.0
    pitch_deg: float = 0.0
    yaw_deg: float = 0.0
    t_fwd_m: float = 0.0
    t_left_m: float = 0.0
    t_up_m: float = 0.0

    @property
    def axis(self) -> str:
        return self.name.split("_")[0]

    @property
    def level(self) -> float:
        rot = max(abs(self.roll_deg), abs(self.pitch_deg), abs(self.yaw_deg))
        if rot:
            return rot
        return 100 * max(abs(self.t_fwd_m), abs(self.t_left_m), abs(self.t_up_m))


def sweep_perturbations(rot_levels=(0.5, 1.0, 2.0, 3.0), trans_levels_cm=(2, 5, 10)) -> list[Perturb]:
    out = [Perturb("baseline")]
    for d in rot_levels:
        out += [Perturb(f"yaw_{d}deg", yaw_deg=d), Perturb(f"pitch_{d}deg", pitch_deg=d),
                Perturb(f"roll_{d}deg", roll_deg=d)]
    for c in trans_levels_cm:
        m = c / 100
        out += [Perturb(f"tfwd_{c}cm", t_fwd_m=m), Perturb(f"tleft_{c}cm", t_left_m=m),
                Perturb(f"tup_{c}cm", t_up_m=m)]
    return out


def physical_perturbation(calib: KittiCalib, p: Perturb, dataset: str) -> KittiCalib:
    if dataset == "nuscenes":
        return perturb_extrinsic(calib, roll_deg=-p.pitch_deg, pitch_deg=p.roll_deg, yaw_deg=p.yaw_deg,
                                 t_xyz_m=(-p.t_left_m, p.t_fwd_m, p.t_up_m))
    return perturb_extrinsic(calib, roll_deg=p.roll_deg, pitch_deg=p.pitch_deg, yaw_deg=p.yaw_deg,
                             t_xyz_m=(p.t_fwd_m, p.t_left_m, p.t_up_m))


def load(data_root: str, frame_id: str, use_ego_motion: bool = True) -> dict:
    ds = dataset_type(data_root)
    kwargs = {"use_ego_motion": use_ego_motion} if ds == "nuscenes" else {}
    fr = load_frame(data_root, frame_id, **kwargs)
    fr["dataset"] = ds
    fr["points"] = fr["points"][np.isfinite(fr["points"]).all(axis=1)]
    return fr


def points_in_box3d(points_cam: np.ndarray, obj: KittiObject, ground_margin: float = GROUND_MARGIN_M) -> np.ndarray:
    h, w, l = obj.dimensions
    c, s = np.cos(obj.rotation_y), np.sin(obj.rotation_y)
    R = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    local = (points_cam - obj.location) @ R
    return ((np.abs(local[:, 0]) <= l / 2) & (np.abs(local[:, 2]) <= w / 2) &
            (local[:, 1] <= -ground_margin) & (local[:, 1] >= -h))


def object_point_masks(points: np.ndarray, calib_true: KittiCalib, labels: list[KittiObject]) -> list[dict]:
    pts_cam = velo_to_cam(points[:, :3], calib_true)
    out = []
    for i, obj in enumerate(labels):
        if obj.type not in EVAL_CLASSES:
            continue
        m = points_in_box3d(pts_cam, obj)
        if m.sum() < MIN_OBJ_POINTS:
            continue
        ok = obj.truncated <= MAX_TRUNCATED and obj.occluded <= MAX_OCCLUDED
        out.append({"idx": i, "type": obj.type, "dist_m": float(np.hypot(obj.location[0], obj.location[2])),
                    "occluded": obj.occluded, "truncated": float(obj.truncated), "eval_ok": bool(ok),
                    "bbox": obj.bbox, "mask": m})
    return out


def box_hit_stats(points: np.ndarray, objects: list[dict], calib: KittiCalib, image_shape,
                  calib_true: KittiCalib | None = None) -> list[dict]:
    rows = []
    for o in objects:
        obj_pts = points[o["mask"], :3]
        uv, _, valid = project_velo_to_image(obj_pts, calib, image_shape)
        x1, y1, x2, y2 = o["bbox"]
        inside = (uv[:, 0] >= x1) & (uv[:, 0] <= x2) & (uv[:, 1] >= y1) & (uv[:, 1] <= y2)
        shift = np.nan
        if calib_true is not None:
            a = _uv_all(obj_pts, calib_true)
            b = _uv_all(obj_pts, calib)
            ok = np.isfinite(a).all(1) & np.isfinite(b).all(1)
            shift = float(np.linalg.norm(a[ok] - b[ok], axis=1).mean()) if ok.any() else np.nan
        meta = {k: v for k, v in o.items() if k not in ("mask", "bbox")}
        rows.append({**meta, "n_pts": int(len(obj_pts)), "hit_ratio": float(inside.sum() / len(obj_pts)),
                     "px_shift": shift})
    return rows


def _uv_all(points_xyz: np.ndarray, calib: KittiCalib) -> np.ndarray:
    cam = velo_to_cam(points_xyz, calib)
    proj = np.hstack([cam, np.ones((len(cam), 1))]) @ calib.P2.T
    uv = proj[:, :2] / proj[:, 2:3]
    uv[cam[:, 2] <= 0.1] = np.nan
    return uv


def fov_ratio(points: np.ndarray, calib: KittiCalib, image_shape) -> float:
    _, _, mask = cam_to_image(velo_to_cam(points[:, :3], calib), calib.P2, image_shape)
    return float(mask.mean())


def dist_bin(d: float) -> str:
    for lo, hi, name in DIST_BINS:
        if lo <= d < hi:
            return name
    return DIST_BINS[-1][2]
