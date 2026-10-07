from __future__ import annotations

import argparse
import os
import platform
import time
from pathlib import Path

import numpy as np
import pandas as pd

from src.edge_score import drift_gain, edge_alignment_score, image_edge_distance
from src.qa_core import load
from starter.projection import project_velo_to_image


def timeit(fn, runs: int) -> np.ndarray:
    fn()
    out = []
    for _ in range(runs):
        t0 = time.perf_counter()
        fn()
        out.append(1000 * (time.perf_counter() - t0))
    return np.array(out)


def main() -> None:
    ap = argparse.ArgumentParser(description="Measure p50/p95 latency of projection and edge-alignment drift check")
    ap.add_argument("--targets", nargs="+", default=["data/kitti_mini:000011", "data/nuscenes_mini_subset:scene-0103_030"],
                    help="data_root:frame_id pairs")
    ap.add_argument("--runs", type=int, default=30, help="timed runs after 1 discarded warm-up (>= 20)")
    ap.add_argument("--out", default="results/latency.csv")
    args = ap.parse_args()

    hw = f"{platform.processor() or platform.machine()} | {os.cpu_count()} logical CPUs | {platform.system()} {platform.release()}"
    rows = []
    for target in args.targets:
        root, fid = target.rsplit(":", 1)
        fr = load(root, fid)
        pts, calib, shape, ds = fr["points"], fr["calib"], fr["image"].shape, fr["dataset"]
        dist_map = image_edge_distance(fr["image"])
        steps = {
            "projection": lambda: project_velo_to_image(pts, calib, shape),
            "edge_map": lambda: image_edge_distance(fr["image"]),
            "edge_score": lambda: edge_alignment_score(pts, calib, shape, dist_map, ds),
            "drift_check": lambda: drift_gain(pts, calib, shape, dist_map, ds),
        }
        for name, fn in steps.items():
            t = timeit(fn, args.runs)
            rows.append({"dataset": ds, "frame_id": fid, "n_points": len(pts), "image": f"{shape[1]}x{shape[0]}",
                         "step": name, "runs": args.runs, "p50_ms": np.percentile(t, 50), "p95_ms": np.percentile(t, 95),
                         "mean_ms": t.mean(), "hardware": hw})
    df = pd.DataFrame(rows).round(2)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)
    print(df.drop(columns="hardware").to_string(index=False))
    print(f"hardware: {hw}\n-> {args.out}")


if __name__ == "__main__":
    main()
