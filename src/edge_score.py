from __future__ import annotations

import cv2
import numpy as np

from starter.kitti_io import KittiCalib
from starter.projection import perturb_extrinsic, project_velo_to_image

SIGMA_PX = 3.0
EDGE_JUMP_REL = 0.15
EDGE_JUMP_MIN_M = 0.5
NEIGHBOR_KERNEL = {"kitti": (3, 11), "nuscenes": (9, 31)}


def image_edge_distance(image: np.ndarray, low: int = 50, high: int = 150) -> np.ndarray:
    gray = cv2.GaussianBlur(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), (5, 5), 0)
    edges = cv2.Canny(gray, low, high)
    return cv2.distanceTransform((edges == 0).astype(np.uint8), cv2.DIST_L2, 3)


def depth_edge_mask(uv: np.ndarray, depth: np.ndarray, image_shape, kernel=(3, 11)) -> np.ndarray:
    h, w = image_shape[:2]
    u = uv[:, 0].astype(np.int32)
    v = uv[:, 1].astype(np.int32)
    zbuf = np.full((h, w), np.inf, dtype=np.float32)
    np.minimum.at(zbuf, (v, u), depth.astype(np.float32))
    zbuf[~np.isfinite(zbuf)] = 0.0
    far = cv2.dilate(zbuf, np.ones(kernel, np.uint8))
    jump = far[v, u] - depth
    is_front = zbuf[v, u] >= depth - 1e-3
    return is_front & (jump > np.maximum(EDGE_JUMP_MIN_M, EDGE_JUMP_REL * depth))


def edge_sum(points: np.ndarray, calib: KittiCalib, image_shape, dist_map: np.ndarray,
             dataset: str = "kitti", max_depth: float = 60.0) -> tuple[float, int]:
    uv, depth, _ = project_velo_to_image(points, calib, image_shape)
    keep = depth < max_depth
    uv, depth = uv[keep], depth[keep]
    e = depth_edge_mask(uv, depth, image_shape, NEIGHBOR_KERNEL[dataset])
    d = dist_map[uv[e, 1].astype(np.int32), uv[e, 0].astype(np.int32)]
    return float(np.exp(-d / SIGMA_PX).sum()), int(e.sum())


def edge_alignment_score(points: np.ndarray, calib: KittiCalib, image_shape, dist_map: np.ndarray,
                         dataset: str = "kitti", max_depth: float = 60.0) -> tuple[float, int]:
    s, n = edge_sum(points, calib, image_shape, dist_map, dataset, max_depth)
    return (s / n if n else float("nan")), n


NUDGE_LEVELS_DEG = (0.5, 1.0, 2.0, 3.0)


def nudges(levels_deg=NUDGE_LEVELS_DEG) -> list[tuple[str, dict]]:
    out = [("none", {})]
    for axis in ("roll", "pitch", "yaw"):
        for mag in levels_deg:
            for sign in (-1, 1):
                d = sign * mag
                out.append((f"{axis}{d:+.1f}", {f"{axis}_deg": d}))
    return out


def nudge_sums(points: np.ndarray, calib: KittiCalib, image_shape, dist_map: np.ndarray,
               dataset: str = "kitti", levels_deg=NUDGE_LEVELS_DEG) -> dict[str, tuple[float, int]]:
    return {name: edge_sum(points, perturb_extrinsic(calib, **kw) if kw else calib, image_shape, dist_map, dataset)
            for name, kw in nudges(levels_deg)}


def gain_from_sums(sums_list: list[dict[str, tuple[float, int]]]) -> dict:
    pooled = {k: (sum(s[k][0] for s in sums_list), sum(s[k][1] for s in sums_list)) for k in sums_list[0]}
    score = {k: (v[0] / v[1] if v[1] else 0.0) for k, v in pooled.items()}
    s0 = score["none"]
    best_name = max(score, key=lambda k: (score[k], k == "none"))
    best = score[best_name]
    return {"score": s0, "best_score": best, "gain": best / s0 - 1 if s0 > 0 else float("nan"),
            "best_nudge": best_name, "n_edge": pooled["none"][1]}


def drift_gain(points: np.ndarray, calib: KittiCalib, image_shape, dist_map: np.ndarray,
               dataset: str = "kitti", levels_deg=NUDGE_LEVELS_DEG) -> dict:
    return gain_from_sums([nudge_sums(points, calib, image_shape, dist_map, dataset, levels_deg)])
