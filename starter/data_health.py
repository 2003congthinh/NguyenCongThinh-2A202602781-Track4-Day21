"""Thống kê sức khoẻ point cloud cho từng frame -> CSV.

Mọi học viên nên chạy ở CP0/CP1, trước khi benchmark model ("benchmark data health trước").
Topic E mở rộng file này thành dashboard (histogram, time gaps, density theo góc...).

    python -m starter.data_health --data-root data/synthetic --out results/data_health.csv
    python -m starter.data_health --data-root data/kitti_mini --out results/data_health_kitti.csv
    python -m starter.data_health --data-root data/nuscenes_mini_subset --out results/data_health_nusc.csv

Lưu ý nuScenes: trục x của LiDAR hướng sang phải xe, nên azimuth 0° là bên phải, không phải phía trước.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np

from starter.datasets import list_frames, load_points


def point_stats(points: np.ndarray, n_azimuth_bins: int = 36) -> dict[str, float]:
    finite = np.isfinite(points).all(axis=1)
    p = points[finite]
    rng = np.linalg.norm(p[:, :2], axis=1)
    az = np.degrees(np.arctan2(p[:, 1], p[:, 0]))
    az_hist, _ = np.histogram(az, bins=n_azimuth_bins, range=(-180, 180))
    return {
        "n_points": int(len(points)),
        "invalid_ratio": float(1 - finite.mean()) if len(points) else 1.0,
        "range_min": float(rng.min()) if len(rng) else np.nan,
        "range_p50": float(np.percentile(rng, 50)) if len(rng) else np.nan,
        "range_p95": float(np.percentile(rng, 95)) if len(rng) else np.nan,
        "range_max": float(rng.max()) if len(rng) else np.nan,
        "ratio_beyond_50m": float((rng > 50).mean()) if len(rng) else np.nan,
        "z_min": float(p[:, 2].min()) if len(p) else np.nan,
        "z_max": float(p[:, 2].max()) if len(p) else np.nan,
        "intensity_mean": float(p[:, 3].mean()) if len(p) else np.nan,
        "empty_azimuth_bins": int((az_hist == 0).sum()),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Thống kê sức khoẻ point cloud của từng frame, ghi ra CSV")
    ap.add_argument("--data-root", default="data/synthetic", help="thư mục KITTI hoặc nuScenes")
    ap.add_argument("--out", default="results/data_health.csv", help="file CSV kết quả")
    args = ap.parse_args()

    rows = [{"frame_id": fid, **point_stats(load_points(args.data_root, fid))} for fid in list_frames(args.data_root)]
    if not rows:
        raise SystemExit(f"Không tìm thấy frame nào trong {args.data_root}. Xem data/README.md để tải dữ liệu.")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print(f"{r['frame_id']}: n={r['n_points']} invalid={r['invalid_ratio']:.2%} "
              f"range_p95={r['range_p95']:.1f}m empty_az_bins={r['empty_azimuth_bins']}")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
