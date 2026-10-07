from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from starter.kitti_io import list_frames, load_frame


def audit(data_root: str) -> pd.DataFrame:
    frames = list_frames(data_root)
    data = {f: load_frame(data_root, f) for f in frames}
    rows = []

    hists, counts = {}, {}
    for f, fr in data.items():
        p = fr["points"]
        finite = np.isfinite(p).all(axis=1)
        if (~finite).any():
            rows.append({"rule": "R1 invalid points", "frame_id": f,
                         "evidence": f"{int((~finite).sum())} NaN/Inf points ({(~finite).mean():.2%})",
                         "how_detected": "np.isfinite on x,y,z,intensity"})
        q = p[finite]
        az = np.degrees(np.arctan2(q[:, 1], q[:, 0]))
        hists[f], _ = np.histogram(az, bins=36, range=(-180, 180))
        counts[f] = len(p)

    H = np.stack([hists[f] for f in frames])
    med_bin = np.median(H, axis=0)
    for i, f in enumerate(frames):
        low = np.where(H[i] < 0.7 * med_bin)[0]
        if len(low):
            sectors = ", ".join(f"[{-180 + 10 * b}, {-170 + 10 * b}] deg: {H[i, b]} vs median {med_bin[b]:.0f}" for b in low)
            rows.append({"rule": "R2 sector dropout", "frame_id": f, "evidence": sectors,
                         "how_detected": "per-bin azimuth histogram vs median of all frames"})
    med_n = np.median(list(counts.values()))
    for f, n in counts.items():
        if n < 0.95 * med_n:
            rows.append({"rule": "R3 low point count", "frame_id": f, "evidence": f"{n} points vs median {med_n:.0f}",
                         "how_detected": "n_points < 95% of median"})

    ts_path = Path(data_root) / "training" / "timestamps.txt"
    if ts_path.exists():
        ts = np.array([float(x) for x in ts_path.read_text().split()])
        dt = np.diff(ts)
        med_dt = np.median(dt)
        for i, d in enumerate(dt):
            if abs(d - med_dt) > 0.5 * med_dt:
                rows.append({"rule": "R4 time gap", "frame_id": f"{frames[i]}->{frames[i + 1]}",
                             "evidence": f"dt={d:.3f}s vs median {med_dt:.3f}s",
                             "how_detected": "diff(timestamps.txt) vs median step"})
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description="Find planted anomalies in a KITTI-format folder (NaN, sector dropout, time gaps)")
    ap.add_argument("--data-root", default="data/synthetic")
    ap.add_argument("--out", default="results/synthetic_anomalies.csv")
    args = ap.parse_args()
    df = audit(args.data_root)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)
    print(df.to_string(index=False))
    print(f"-> {args.out}")


if __name__ == "__main__":
    main()
