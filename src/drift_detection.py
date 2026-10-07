from __future__ import annotations

import argparse
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src.edge_score import gain_from_sums, image_edge_distance, nudge_sums
from src.qa_core import Perturb, load, physical_perturbation
from starter.datasets import list_frames


def detection_perturbations(levels=(0.5, 1.0, 2.0, 3.0), trans_cm: int = 10) -> list[Perturb]:
    out = [Perturb("baseline")]
    for d in levels:
        out += [Perturb(f"yaw_{d}deg", yaw_deg=d), Perturb(f"pitch_{d}deg", pitch_deg=d),
                Perturb(f"roll_{d}deg", roll_deg=d)]
    m = trans_cm / 100
    out += [Perturb(f"tleft_{trans_cm}cm", t_left_m=m), Perturb(f"tup_{trans_cm}cm", t_up_m=m),
            Perturb(f"tfwd_{trans_cm}cm", t_fwd_m=m)]
    return out


def collect_sums(data_root: str, perturbs: list[Perturb]) -> list[dict]:
    rows = []
    for fid in list_frames(data_root):
        t0 = time.perf_counter()
        fr = load(data_root, fid)
        dist_map = image_edge_distance(fr["image"])
        for p in perturbs:
            calib = physical_perturbation(fr["calib"], p, fr["dataset"])
            rows.append({"dataset": fr["dataset"], "frame_id": fid, "scene": fid.rsplit("_", 1)[0] if "_" in fid else "kitti",
                         "config": p.name, "axis": p.axis, "level": p.level,
                         "sums": nudge_sums(fr["points"], calib, fr["image"].shape, dist_map, fr["dataset"])})
        print(f"  {data_root} {fid}: {time.perf_counter() - t0:.1f}s")
    return rows


def windows(frame_ids: list[str], scenes: list[str], w: int) -> list[list[str]]:
    out = []
    for i in range(len(frame_ids) - w + 1):
        if len(set(scenes[i:i + w])) == 1:
            out.append(frame_ids[i:i + w])
    return out


def evaluate(rows: list[dict], w: int, margin: float = 0.02) -> tuple[pd.DataFrame, pd.DataFrame]:
    samples = []
    for ds in sorted({r["dataset"] for r in rows}):
        rd = [r for r in rows if r["dataset"] == ds]
        by_key = {(r["frame_id"], r["config"]): r for r in rd}
        frame_order = list(dict.fromkeys(r["frame_id"] for r in rd))
        scene_of = {r["frame_id"]: r["scene"] for r in rd}
        configs = list(dict.fromkeys(r["config"] for r in rd))
        for cfg in configs:
            meta = by_key[(frame_order[0], cfg)]
            for fid in frame_order:
                g = gain_from_sums([by_key[(fid, cfg)]["sums"]])
                samples.append({"dataset": ds, "detector": "single", "sample": fid, "config": cfg,
                                "axis": meta["axis"], "level": meta["level"], **g})
            for win in windows(frame_order, [scene_of[f] for f in frame_order], w):
                g = gain_from_sums([by_key[(f, cfg)]["sums"] for f in win])
                samples.append({"dataset": ds, "detector": f"window{w}", "sample": f"{win[0]}..{win[-1]}",
                                "config": cfg, "axis": meta["axis"], "level": meta["level"], **g})
    s = pd.DataFrame(samples)
    thr = (s[s["config"] == "baseline"].groupby(["dataset", "detector"])["gain"].max() + margin).rename("threshold")
    s = s.join(thr, on=["dataset", "detector"])
    s["detected"] = s["gain"] > s["threshold"]
    summ = (s.groupby(["dataset", "detector", "config", "axis", "level"])
            .agg(n=("gain", "size"), score_mean=("score", "mean"), gain_median=("gain", "median"),
                 threshold=("threshold", "first"), detect_pct=("detected", "mean"))
            .reset_index())
    summ["detect_pct"] *= 100
    return s, summ.round(4)


def plot(summ: pd.DataFrame, out_png: Path) -> None:
    datasets = list(summ["dataset"].unique())
    detectors = list(summ["detector"].unique())
    fig, axes = plt.subplots(len(datasets), 2, figsize=(12, 4 * len(datasets)), squeeze=False)
    for i, ds in enumerate(datasets):
        d = summ[summ["dataset"] == ds]
        ax = axes[i, 0]
        for det in detectors:
            dd = d[d["detector"] == det]
            base = dd[dd["config"] == "baseline"]["score_mean"].iloc[0]
            for axis in ("yaw", "pitch", "roll"):
                da = dd[dd["axis"] == axis].sort_values("level")
                if det == detectors[0]:
                    ax.plot([0] + list(da["level"]), [base] + list(da["score_mean"]), marker="o", label=axis)
        ax.set_title(f"{ds}: mean edge-alignment score vs rotation drift")
        ax.set_xlabel("drift (deg)")
        ax.set_ylabel("score (higher = better aligned)")
        ax.grid(alpha=0.3)
        ax.legend()
        ax = axes[i, 1]
        for det, ls in zip(detectors, ("-", "--")):
            dd = d[d["detector"] == det]
            for axis in ("yaw", "pitch", "roll"):
                da = dd[dd["axis"] == axis].sort_values("level")
                ax.plot([0] + list(da["level"]), [0] + list(da["detect_pct"]), marker="o", linestyle=ls,
                        label=f"{axis} ({det})")
        ax.set_title(f"{ds}: detection rate (thr = max baseline gain + margin)")
        ax.set_xlabel("drift (deg)")
        ax.set_ylabel("% samples flagged as drifted")
        ax.set_ylim(-5, 105)
        ax.grid(alpha=0.3)
        ax.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(out_png, dpi=120)
    plt.close(fig)


def plot_gain_hist(samples: pd.DataFrame, out_png: Path) -> None:
    combos = samples[["dataset", "detector"]].drop_duplicates().values.tolist()
    fig, axes = plt.subplots(1, len(combos), figsize=(4.5 * len(combos), 3.5), squeeze=False)
    for ax, (ds, det) in zip(axes[0], combos):
        d = samples[(samples["dataset"] == ds) & (samples["detector"] == det)]
        for cfg, color in (("baseline", "tab:green"), ("yaw_1.0deg", "tab:red"), ("yaw_0.5deg", "tab:orange")):
            ax.hist(d[d["config"] == cfg]["gain"], bins=15, alpha=0.5, color=color, label=cfg)
        ax.axvline(d["threshold"].iloc[0], color="k", linestyle="--", label="threshold")
        ax.set_title(f"{ds} / {det}")
        ax.set_xlabel("gain = best nudge / current - 1")
        ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(out_png, dpi=120)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description="Label-free calibration drift detection with an edge-alignment "
                                             "score (single frame vs pooled window of frames)")
    ap.add_argument("--data-roots", nargs="+", default=["data/kitti_mini", "data/nuscenes_mini_subset"])
    ap.add_argument("--levels", nargs="+", type=float, default=[0.5, 1.0, 2.0, 3.0], help="rotation drift (deg)")
    ap.add_argument("--trans-cm", type=int, default=10, help="translation drift tested on each axis (cm)")
    ap.add_argument("--window", type=int, default=5, help="frames pooled by the window detector")
    ap.add_argument("--margin", type=float, default=0.02, help="added to the max baseline gain to get the threshold")
    ap.add_argument("--out-dir", default="results")
    args = ap.parse_args()

    perturbs = detection_perturbations(args.levels, args.trans_cm)
    rows = []
    for root in args.data_roots:
        rows += collect_sums(root, perturbs)
    samples, summ = evaluate(rows, args.window, args.margin)

    out = Path(args.out_dir)
    (out / "figures").mkdir(parents=True, exist_ok=True)
    samples.to_csv(out / "drift_detection_samples.csv", index=False, float_format="%.4f")
    summ.to_csv(out / "drift_detection.csv", index=False)
    plot(summ, out / "figures" / "drift_score_and_detection.png")
    plot_gain_hist(samples, out / "figures" / "drift_gain_hist.png")
    print(summ.to_string(index=False))


if __name__ == "__main__":
    main()
