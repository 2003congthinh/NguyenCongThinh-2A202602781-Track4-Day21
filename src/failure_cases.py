from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

from src.edge_score import drift_gain, image_edge_distance
from src.qa_core import Perturb, box_hit_stats, load, object_point_masks, physical_perturbation
from src.qa_core import _uv_all
from starter.projection import overlay_points, project_velo_to_image


def put_lines(img: np.ndarray, lines: list[str], scale: float = 0.6) -> np.ndarray:
    banner = np.zeros((26 * len(lines) + 8, img.shape[1], 3), np.uint8)
    for i, t in enumerate(lines):
        cv2.putText(banner, t, (8, 24 + 26 * i), cv2.FONT_HERSHEY_SIMPLEX, scale, (255, 255, 255), 1, cv2.LINE_AA)
    return np.vstack([banner, img])


def object_points_canvas(fr: dict, calib, obj: dict, pad: int = 700) -> np.ndarray:
    img = fr["image"]
    h, w = img.shape[:2]
    canvas = np.full((h, w + 2 * pad, 3), 40, np.uint8)
    canvas[:, pad:pad + w] = img
    cv2.rectangle(canvas, (pad, 0), (pad + w - 1, h - 1), (255, 255, 255), 2)
    uv = _uv_all(fr["points"][obj["mask"], :3], calib)
    uv = uv[np.isfinite(uv).all(1)]
    x1, y1, x2, y2 = obj["bbox"]
    inside = (uv[:, 0] >= x1) & (uv[:, 0] <= x2) & (uv[:, 1] >= y1) & (uv[:, 1] <= y2)
    for (u, v), ok in zip(uv, inside):
        if -pad <= u < w + pad and 0 <= v < h:
            cv2.circle(canvas, (int(u) + pad, int(v)), 2, (0, 255, 0) if ok else (0, 0, 255), -1)
    cv2.rectangle(canvas, (int(x1) + pad, int(y1)), (int(x2) + pad, int(y2)), (255, 255, 0), 2)
    return canvas


def fail_truncated(root: str, fid: str, out: Path) -> dict:
    fr = load(root, fid)
    objs = object_point_masks(fr["points"], fr["calib"], fr["labels"])
    stats = box_hit_stats(fr["points"], objs, fr["calib"], fr["image"].shape)
    worst = min(range(len(objs)), key=lambda i: stats[i]["hit_ratio"])
    o, s = objs[worst], stats[worst]
    uv = _uv_all(fr["points"][o["mask"], :3], fr["calib"])
    h, w = fr["image"].shape[:2]
    outside = float(((uv[:, 0] < 0) | (uv[:, 0] >= w) | (uv[:, 1] < 0) | (uv[:, 1] >= h)).mean())
    img = put_lines(object_points_canvas(fr, fr["calib"], o), [
        f"FAIL (Metric): KITTI {fid} {o['type']} {o['dist_m']:.1f} m, truncated={o['truncated']:.2f}, TRUE calibration",
        f"hit ratio = {100 * s['hit_ratio']:.0f}% -> metric says 'miscalibrated', but {100 * outside:.0f}% of the car's "
        f"points project OUTSIDE the image (grey area)",
        "green = point inside GT 2D box (cyan), red = outside. White frame = real image border.",
    ])
    path = out / f"fail_01_truncated_box_metric_{fid}.png"
    cv2.imwrite(str(path), img)
    return {"case": path.name, "frame": fid, "object": o["type"], "dist_m": round(o["dist_m"], 1),
            "truncated": o["truncated"], "hit_pct_true_calib": round(100 * s["hit_ratio"], 1),
            "pct_points_outside_image": round(100 * outside, 1)}


def crop_union(boxes, shape, margin: int = 60):
    x1 = max(int(min(b[0] for b in boxes)) - margin, 0)
    y1 = max(int(min(b[1] for b in boxes)) - margin, 0)
    x2 = min(int(max(b[2] for b in boxes)) + margin, shape[1])
    y2 = min(int(max(b[3] for b in boxes)) + margin, shape[0])
    return x1, y1, x2, y2


def fail_time(root: str, fid: str, out: Path) -> dict:
    a = load(root, fid, use_ego_motion=True)
    b = load(root, fid, use_ego_motion=False)
    objs = [o for o in object_point_masks(a["points"], a["calib"], a["labels"]) if o["eval_ok"]]
    sa = box_hit_stats(a["points"], objs, a["calib"], a["image"].shape)
    sb = box_hit_stats(a["points"], objs, b["calib"], a["image"].shape, calib_true=a["calib"])
    panels = []
    for fr_calib, tag, st in ((a["calib"], "WITH ego-motion compensation", sa), (b["calib"], "WITHOUT (ignore 35 ms offset)", sb)):
        uv, depth, _ = project_velo_to_image(a["points"], fr_calib, a["image"].shape)
        vis = overlay_points(a["image"], uv, depth, max_depth=40, radius=3)
        for o in objs:
            x1, y1, x2, y2 = (int(v) for v in o["bbox"])
            cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 2)
        x1, y1, x2, y2 = crop_union([o["bbox"] for o in objs], a["image"].shape)
        hit = 100 * np.mean([r["hit_ratio"] for r in st])
        panels.append(put_lines(vis[y1:y2, x1:x2], [f"{tag}: mean hit {hit:.0f}%"], 0.55))
    dt_ms = (a["timestamp_camera_us"] - a["timestamp_lidar_us"]) / 1000
    shift = float(np.nanmean([r["px_shift"] for r in sb]))
    hmax = max(p.shape[0] for p in panels)
    panels = [cv2.copyMakeBorder(p, 0, hmax - p.shape[0], 0, 6, cv2.BORDER_CONSTANT) for p in panels]
    img = put_lines(np.hstack(panels), [
        f"FAIL (Time): nuScenes {fid} (night), camera - LiDAR timestamp = {dt_ms:.1f} ms",
        f"Without ego-motion compensation, object points move {shift:.1f} px on average (= ~1 deg yaw drift),",
        "but the hit-ratio metric barely changes: nuScenes 2D boxes are loose (built from 3D box corners).",
    ], 0.55)
    path = out / f"fail_02_time_sync_no_ego_motion_{fid}.png"
    cv2.imwrite(str(path), img)
    return {"case": path.name, "frame": fid, "dt_ms": round(dt_ms, 1), "px_shift": round(shift, 1),
            "hit_pct_ego": round(100 * np.mean([r["hit_ratio"] for r in sa]), 1),
            "hit_pct_no_ego": round(100 * np.mean([r["hit_ratio"] for r in sb]), 1)}


def fail_translation(root: str, fid: str, thr_single: float, window_rate: float, out: Path,
                     t_left_m: float = 0.10) -> dict:
    fr = load(root, fid)
    p = Perturb(f"tleft_{int(100 * t_left_m)}cm", t_left_m=t_left_m)
    calib = physical_perturbation(fr["calib"], p, fr["dataset"])
    objs = [o for o in object_point_masks(fr["points"], fr["calib"], fr["labels"]) if o["eval_ok"]]
    s0 = box_hit_stats(fr["points"], objs, fr["calib"], fr["image"].shape)
    s1 = box_hit_stats(fr["points"], objs, calib, fr["image"].shape, calib_true=fr["calib"])
    k = max(range(len(objs)), key=lambda i: s0[i]["hit_ratio"] - s1[i]["hit_ratio"])
    o = objs[k]
    box_w = o["bbox"][2] - o["bbox"][0]
    dm = image_edge_distance(fr["image"])
    g = drift_gain(fr["points"], calib, fr["image"].shape, dm, fr["dataset"])
    panels = []
    for c, tag in ((fr["calib"], f"true calib: hit {100 * s0[k]['hit_ratio']:.0f}%"),
                   (calib, f"LiDAR 10 cm left: hit {100 * s1[k]['hit_ratio']:.0f}%")):
        canvas = object_points_canvas(fr, c, o, pad=0)
        x1, y1, x2, y2 = crop_union([o["bbox"]], fr["image"].shape, 30)
        crop = cv2.resize(canvas[y1:y2, x1:x2], None, fx=3, fy=3, interpolation=cv2.INTER_NEAREST)
        panels.append(put_lines(crop, [tag], 0.55))
    hmax = max(q.shape[0] for q in panels)
    panels = [cv2.copyMakeBorder(q, 0, hmax - q.shape[0], 0, 6, cv2.BORDER_CONSTANT) for q in panels]
    drop = 100 * (s0[k]["hit_ratio"] - s1[k]["hit_ratio"])
    img = put_lines(np.hstack(panels), [
        f"FAIL (Geometry, undetected): KITTI {fid}",
        f"{o['type']} {o['dist_m']:.1f} m, 2D box {box_w:.0f} px wide (x3 zoom)",
        f"10 cm lateral shift = {s1[k]['px_shift']:.1f} px, hit -{drop:.0f} pts",
        f"self-check gain {g['gain']:.3f} < thr {thr_single:.3f} (1 frame)",
        f"5-frame window: {window_rate:.0f}% of tleft_10cm flagged",
    ], 0.5)
    path = out / f"fail_03_translation_undetected_{fid}.png"
    cv2.imwrite(str(path), img)
    return {"case": path.name, "frame": fid, "object": o["type"], "dist_m": round(o["dist_m"], 1),
            "box_width_px": round(box_w, 1), "px_shift": round(s1[k]["px_shift"], 1),
            "hit_pct": round(100 * s1[k]["hit_ratio"], 1), "hit_pct_true_calib": round(100 * s0[k]["hit_ratio"], 1),
            "gain": round(g["gain"], 4), "threshold": round(thr_single, 4)}


def main() -> None:
    ap = argparse.ArgumentParser(description="Render failure-case figures fail_01..fail_03 into results/figures")
    ap.add_argument("--kitti", default="data/kitti_mini")
    ap.add_argument("--nusc", default="data/nuscenes_mini_subset")
    ap.add_argument("--truncated-frame", default="000011")
    ap.add_argument("--time-frame", default="scene-1094_015")
    ap.add_argument("--translation-frame", default="000015")
    ap.add_argument("--drift-csv", default="results/drift_detection.csv",
                    help="output of src.drift_detection (KITTI threshold + window detection rate)")
    ap.add_argument("--out-dir", default="results")
    args = ap.parse_args()

    out = Path(args.out_dir) / "figures"
    out.mkdir(parents=True, exist_ok=True)
    d = pd.read_csv(args.drift_csv)
    k = d[d["dataset"] == "kitti"]
    thr = float(k[k["detector"] == "single"]["threshold"].iloc[0])
    win_rate = float(k[(k["detector"] != "single") & (k["config"] == "tleft_10cm")]["detect_pct"].iloc[0])
    rows = [fail_truncated(args.kitti, args.truncated_frame, out),
            fail_time(args.nusc, args.time_frame, out),
            fail_translation(args.kitti, args.translation_frame, thr, win_rate, out)]
    df = pd.DataFrame(rows)
    df.to_csv(Path(args.out_dir) / "failure_cases.csv", index=False)
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
