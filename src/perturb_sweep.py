from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.qa_core import (DIST_BINS, box_hit_stats, dist_bin, fov_ratio, load, object_point_masks,
                         physical_perturbation, sweep_perturbations)
from starter.datasets import list_frames


def run_dataset(data_root: str, perturbs) -> tuple[pd.DataFrame, pd.DataFrame]:
    obj_rows, frame_rows = [], []
    for fid in list_frames(data_root):
        fr = load(data_root, fid)
        objs = object_point_masks(fr["points"], fr["calib"], fr["labels"])
        for p in perturbs:
            calib = physical_perturbation(fr["calib"], p, fr["dataset"])
            frame_rows.append({"dataset": fr["dataset"], "frame_id": fid, "config": p.name, "axis": p.axis,
                               "level": p.level, "fov_pct": 100 * fov_ratio(fr["points"], calib, fr["image"].shape)})
            for r in box_hit_stats(fr["points"], objs, calib, fr["image"].shape, calib_true=fr["calib"]):
                obj_rows.append({"dataset": fr["dataset"], "frame_id": fid, "config": p.name, "axis": p.axis,
                                 "level": p.level, **r, "dist_bin": dist_bin(r["dist_m"])})
        print(f"  {data_root} {fid}: {len(objs)} objects")
    return pd.DataFrame(obj_rows), pd.DataFrame(frame_rows)


def summarize(objs: pd.DataFrame, frames: pd.DataFrame) -> pd.DataFrame:
    ok = objs[objs["eval_ok"]]
    g = ok.groupby(["dataset", "config", "axis", "level"])
    s = g.agg(n_objects=("hit_ratio", "size"), hit_pct=("hit_ratio", "mean"), px_shift=("px_shift", "mean"))
    s["hit_pct"] *= 100
    s["pct_objects_below_80"] = g["hit_ratio"].apply(lambda x: 100 * (x < 0.8).mean())
    for _, _, b in DIST_BINS:
        s[f"hit_pct_{b}"] = 100 * ok[ok["dist_bin"] == b].groupby(["dataset", "config", "axis", "level"])["hit_ratio"].mean()
    s["fov_pct"] = frames.groupby(["dataset", "config", "axis", "level"])["fov_pct"].mean()
    s = s.reset_index()
    base = s[s["config"] == "baseline"].set_index("dataset")
    s["hit_drop_pts"] = s.apply(lambda r: base.loc[r["dataset"], "hit_pct"] - r["hit_pct"], axis=1)
    s["fov_change_pts"] = s.apply(lambda r: r["fov_pct"] - base.loc[r["dataset"], "fov_pct"], axis=1)
    order = {"baseline": 0, "yaw": 1, "pitch": 2, "roll": 3, "tleft": 4, "tup": 5, "tfwd": 6}
    s = s.sort_values(["dataset", "axis", "level"], key=lambda c: c.map(order) if c.name == "axis" else c)
    return s.round(2)


def plot(summary: pd.DataFrame, out_png: Path) -> None:
    datasets = list(summary["dataset"].unique())
    fig, axes = plt.subplots(2, len(datasets), figsize=(6 * len(datasets), 8), squeeze=False)
    for j, ds in enumerate(datasets):
        d = summary[summary["dataset"] == ds]
        base = d[d["config"] == "baseline"]["hit_pct"].iloc[0]
        for axis, ax_i, unit in [(("yaw", "pitch", "roll"), 0, "deg"), (("tleft", "tup", "tfwd"), 1, "cm")]:
            ax = axes[ax_i, j]
            for a in axis:
                da = d[d["axis"] == a].sort_values("level")
                ax.plot([0] + list(da["level"]), [base] + list(da["hit_pct"]), marker="o", label=a)
            ax.set_xlabel(f"drift magnitude ({unit})")
            ax.set_ylabel("object points inside GT 2D box (%)")
            ax.set_ylim(0, 102)
            ax.set_title(f"{ds}: {'rotation' if ax_i == 0 else 'translation'} drift")
            ax.grid(alpha=0.3)
            ax.legend()
    fig.tight_layout()
    fig.savefig(out_png, dpi=120)
    plt.close(fig)


def plot_distance(objs: pd.DataFrame, out_png: Path, axes_names=("yaw", "tleft")) -> None:
    ok = objs[objs["eval_ok"]]
    datasets = list(ok["dataset"].unique())
    fig, axes = plt.subplots(1, 2 * len(datasets), figsize=(5 * 2 * len(datasets), 4), squeeze=False)
    k = 0
    for ds in datasets:
        for axis_name in axes_names:
            ax = axes[0, k]
            k += 1
            d = ok[(ok["dataset"] == ds) & ok["axis"].isin([axis_name, "baseline"])]
            for _, _, b in DIST_BINS:
                db = d[d["dist_bin"] == b].groupby("level")["hit_ratio"].agg(["mean", "size"])
                if db.empty:
                    continue
                ax.plot(db.index, 100 * db["mean"], marker="o", label=f"{b} (n={int(db['size'].iloc[0])})")
            ax.set_title(f"{ds}: {axis_name} drift by distance")
            ax.set_xlabel("deg" if axis_name in ("yaw", "pitch", "roll") else "cm")
            ax.set_ylabel("hit %")
            ax.set_ylim(0, 102)
            ax.grid(alpha=0.3)
            ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out_png, dpi=120)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description="Sweep LiDAR-camera calibration drift and measure FOV %% and "
                                             "%% of object points that stay inside their GT 2D box")
    ap.add_argument("--data-roots", nargs="+", default=["data/kitti_mini", "data/nuscenes_mini_subset"],
                    help="one or more KITTI / nuScenes folders")
    ap.add_argument("--rot-levels", nargs="+", type=float, default=[0.5, 1.0, 2.0, 3.0], help="rotation drift (deg)")
    ap.add_argument("--trans-levels-cm", nargs="+", type=int, default=[2, 5, 10], help="translation drift (cm)")
    ap.add_argument("--out-dir", default="results", help="CSV goes here, figures go to <out-dir>/figures")
    args = ap.parse_args()

    perturbs = sweep_perturbations(args.rot_levels, args.trans_levels_cm)
    all_objs, all_frames = [], []
    for root in args.data_roots:
        o, f = run_dataset(root, perturbs)
        all_objs.append(o)
        all_frames.append(f)
    objs, frames = pd.concat(all_objs), pd.concat(all_frames)

    out = Path(args.out_dir)
    (out / "figures").mkdir(parents=True, exist_ok=True)
    objs.to_csv(out / "perturb_sweep_objects.csv", index=False, float_format="%.4f")
    summary = summarize(objs, frames)
    summary.to_csv(out / "perturb_sweep.csv", index=False)
    plot(summary, out / "figures" / "sweep_hit_vs_drift.png")
    plot_distance(objs, out / "figures" / "sweep_hit_by_distance.png")
    cols = ["dataset", "config", "n_objects", "fov_pct", "hit_pct", "hit_drop_pts", "px_shift",
            "pct_objects_below_80"] + [f"hit_pct_{b}" for _, _, b in DIST_BINS]
    print(summary[cols].to_string(index=False))
    print(f"-> {out / 'perturb_sweep.csv'}, {out / 'figures'}")


if __name__ == "__main__":
    main()
