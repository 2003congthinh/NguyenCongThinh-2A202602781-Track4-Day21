from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np

from src.qa_core import Perturb, box_hit_stats, load, object_point_masks, physical_perturbation
from starter.projection import draw_box2d, overlay_points, project_velo_to_image


def render(fr: dict, calib, title: str, objs: list[dict] | None = None, max_depth: float = 50.0) -> np.ndarray:
    uv, depth, mask = project_velo_to_image(fr["points"], calib, fr["image"].shape)
    vis = overlay_points(fr["image"], uv, depth, max_depth=max_depth)
    objs = objs if objs is not None else object_point_masks(fr["points"], fr["calib"], fr["labels"])
    stats = {r["idx"]: r for r in box_hit_stats(fr["points"], objs, calib, fr["image"].shape)}
    for i, obj in enumerate(fr["labels"]):
        d = float(np.hypot(obj.location[0], obj.location[2]))
        if i in stats:
            hit = stats[i]["hit_ratio"]
            color = (0, 255, 0) if hit >= 0.8 else (0, 0, 255)
            label = f"{obj.type} {d:.0f}m hit={100 * hit:.0f}%"
        else:
            color, label = (200, 200, 200), f"{obj.type} {d:.0f}m"
        vis = draw_box2d(vis, obj.bbox, color=color, label=label)
    banner = np.zeros((34, vis.shape[1], 3), np.uint8)
    cv2.putText(banner, f"{title} | points in image: {int(mask.sum())}/{len(mask)} ({mask.mean():.1%})",
                (8, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 1, cv2.LINE_AA)
    return np.vstack([banner, vis])


def stack(images: list[np.ndarray]) -> np.ndarray:
    w = max(im.shape[1] for im in images)
    return np.vstack([cv2.copyMakeBorder(im, 0, 4, 0, w - im.shape[1], cv2.BORDER_CONSTANT) for im in images])


def main() -> None:
    ap = argparse.ArgumentParser(description="Render LiDAR->camera overlays at near/mid/far range and a yaw-drift panel")
    ap.add_argument("--data-root", default="data/kitti_mini")
    ap.add_argument("--near", default="000025", help="frame with a very close object (< 15 m)")
    ap.add_argument("--mid", default="000011", help="frame with objects at 15-30 m")
    ap.add_argument("--far", default="000012", help="frame with far objects (> 30 m)")
    ap.add_argument("--drift-frame", default="000011", help="frame used for the yaw 0/1/2/3 deg panel")
    ap.add_argument("--yaw-levels", nargs="+", type=float, default=[0.0, 1.0, 2.0, 3.0])
    ap.add_argument("--tag", default="kitti", help="prefix for output file names")
    ap.add_argument("--out-dir", default="results/figures")
    args = ap.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    panels = []
    for name, fid in (("near", args.near), ("mid", args.mid), ("far", args.far)):
        fr = load(args.data_root, fid)
        img = render(fr, fr["calib"], f"{args.tag} {fid} ({name}) - true calibration")
        cv2.imwrite(str(out / f"demo_{args.tag}_{name}_{fid}.png"), img)
        panels.append(img)
    cv2.imwrite(str(out / f"demo_{args.tag}_3distances.png"), stack(panels))

    fr = load(args.data_root, args.drift_frame)
    objs = object_point_masks(fr["points"], fr["calib"], fr["labels"])
    drift = [render(fr, physical_perturbation(fr["calib"], Perturb("yaw", yaw_deg=y), fr["dataset"]),
                    f"{args.tag} {args.drift_frame} yaw drift {y:g} deg", objs) for y in args.yaw_levels]
    cv2.imwrite(str(out / f"demo_{args.tag}_yaw_drift_{args.drift_frame}.png"), stack(drift))
    print(f"-> {out}/demo_{args.tag}_*.png")


if __name__ == "__main__":
    main()
