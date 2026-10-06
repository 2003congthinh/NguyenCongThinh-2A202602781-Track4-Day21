"""TUỲ CHỌN: tạo thêm một phần của nuScenes v1.0-mini (scene khác, hoặc đủ sensor cho detector).

Repo đã có sẵn 2 scene (LIDAR_TOP + CAM_FRONT) trong data/nuscenes_mini_subset, nên KHÔNG cần
chạy script này để làm lab. Chỉ dùng khi:
  - muốn thêm scene khác: dùng --scenes và --out tới một thư mục MỚI;
  - làm topic B và cần đủ 6 camera + LiDAR sweeps cho MMDetection3D/CenterPoint: dùng --profile full.

nuScenes chỉ phát hành dạng file .tgz (4.2 GB), không tải từng file được. Script này đọc
file .tgz dạng stream (vừa tải vừa đọc), chỉ GHI XUỐNG ĐĨA các file thuộc scene và sensor
được chọn, rồi dừng ngay khi đã đủ file. Lượng đọc qua mạng có thể lên tới vài GB, nên hãy
chạy ở nhà, KHÔNG chạy trong giờ lab.

Chạy từ gốc repo:
    python tools/download_nuscenes_subset.py --list-scenes            # xem 10 scene có trong mini
    python tools/download_nuscenes_subset.py --scenes scene-0553 scene-1100 --out data/nuscenes_extra
    python tools/download_nuscenes_subset.py --profile full --out data/nuscenes_full
    python tools/download_nuscenes_subset.py --source D:/v1.0-mini.tgz --out data/nuscenes_extra   # dùng file .tgz có sẵn

Profile:
    lite : keyframe (2 Hz) của LIDAR_TOP + CAM_FRONT. Đủ cho projection QA, degradation, data health, label support.
    full : mọi sensor + sweeps (20 Hz LiDAR) của các scene đã chọn. Cần cho detector multi-sweep như CenterPoint.

Kết quả: data/nuscenes_mini_subset/{v1.0-mini/*.json, samples/..., sweeps/...} + MANIFEST.json.
Metadata JSON đã được lọc cho khớp với các file thực sự có, nên các bảng không trỏ tới file bị thiếu.

License: nuScenes phát hành theo CC BY-NC-SA 4.0, chỉ dùng cho học tập và nghiên cứu phi thương mại.
"""
from __future__ import annotations

import argparse
import json
import sys
import tarfile
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_data import write_manifest  # noqa: E402

URLS = [
    "https://www.nuscenes.org/data/v1.0-mini.tgz",
    "https://d36yt3mvayqw5m.cloudfront.net/public/v1.0/v1.0-mini.tgz",
]
VERSION = "v1.0-mini"
TABLES = ["attribute", "calibrated_sensor", "category", "ego_pose", "instance", "log", "map", "sample",
          "sample_annotation", "sample_data", "scene", "sensor", "visibility"]
# Một cặp ngày/đêm để so sánh độ bền:
# scene-0103: ban ngày, nhiều người đi bộ bên phải, có cyclist và xe rẽ.
# scene-1094: ban đêm sau mưa, nhiều người đi bộ, người băng qua đường sai luật, xe tải, scooter.
DEFAULT_SCENES = ["scene-0103", "scene-1094"]
LITE_CHANNELS = ["LIDAR_TOP", "CAM_FRONT"]


class CountingReader:
    def __init__(self, f, total: int | None):
        self.f, self.total, self.n, self.t0, self.last = f, total, 0, time.time(), 0.0

    def read(self, size: int = -1) -> bytes:
        b = self.f.read(size)
        self.n += len(b)
        if time.time() - self.last > 1:
            self.last = time.time()
            speed = self.n / 1e6 / max(self.last - self.t0, 1e-6)
            total = f"/{self.total / 1e9:.2f}" if self.total else ""
            print(f"\r  đã đọc {self.n / 1e9:.2f}{total} GB  ({speed:.0f} MB/s)   ", end="", flush=True)
        return b


def open_source(source: str | None):
    if source and Path(source).exists():
        path = Path(source)
        return CountingReader(path.open("rb"), path.stat().st_size)
    errors = []
    for url in ([source] if source else URLS):
        try:
            r = urllib.request.urlopen(url, timeout=60)
            return CountingReader(r, int(r.headers.get("Content-Length", 0)) or None)
        except Exception as e:  # noqa: BLE001
            errors.append(f"{url}: {e}")
    raise SystemExit("Không mở được nguồn dữ liệu nuScenes:\n  " + "\n  ".join(errors))


def filter_tables(tables: dict[str, list], scene_names: list[str], channels: list[str] | None,
                  keyframes_only: bool) -> dict[str, list]:
    scenes = [s for s in tables["scene"] if s["name"] in scene_names]
    unknown = set(scene_names) - {s["name"] for s in scenes}
    if unknown:
        valid = ", ".join(sorted(s["name"] for s in tables["scene"]))
        raise SystemExit(f"Scene không có trong {VERSION}: {sorted(unknown)}. Các scene hợp lệ: {valid}")
    scene_tokens = {s["token"] for s in scenes}
    samples = [s for s in tables["sample"] if s["scene_token"] in scene_tokens]
    sample_tokens = {s["token"] for s in samples}

    sensor_channel = {s["token"]: s["channel"] for s in tables["sensor"]}
    cs_channel = {c["token"]: sensor_channel[c["sensor_token"]] for c in tables["calibrated_sensor"]}
    sample_data = [d for d in tables["sample_data"]
                   if d["sample_token"] in sample_tokens
                   and (channels is None or cs_channel[d["calibrated_sensor_token"]] in channels)
                   and (d["is_key_frame"] or not keyframes_only)]

    # Nối lại prev/next để chuỗi sample_data của mỗi sensor không trỏ vào bản ghi đã bị lọc bỏ.
    by_sensor: dict[tuple[str, str], list[dict]] = {}
    scene_of_sample = {s["token"]: s["scene_token"] for s in samples}
    for d in sample_data:
        key = (scene_of_sample[d["sample_token"]], cs_channel[d["calibrated_sensor_token"]])
        by_sensor.setdefault(key, []).append(d)
    for chain in by_sensor.values():
        chain.sort(key=lambda d: d["timestamp"])
        for i, d in enumerate(chain):
            d["prev"] = chain[i - 1]["token"] if i > 0 else ""
            d["next"] = chain[i + 1]["token"] if i + 1 < len(chain) else ""

    annotations = [a for a in tables["sample_annotation"] if a["sample_token"] in sample_tokens]
    ann_tokens = {a["token"] for a in annotations}
    for a in annotations:
        a["prev"] = a["prev"] if a["prev"] in ann_tokens else ""
        a["next"] = a["next"] if a["next"] in ann_tokens else ""
    sample_time = {s["token"]: s["timestamp"] for s in samples}
    anns_of_instance: dict[str, list[dict]] = {}
    for a in annotations:
        anns_of_instance.setdefault(a["instance_token"], []).append(a)
    instances = []
    for inst in tables["instance"]:
        anns = sorted(anns_of_instance.get(inst["token"], []), key=lambda a: sample_time[a["sample_token"]])
        if anns:
            inst = dict(inst, nbr_annotations=len(anns), first_annotation_token=anns[0]["token"],
                        last_annotation_token=anns[-1]["token"])
            instances.append(inst)
    ego_tokens = {d["ego_pose_token"] for d in sample_data}
    log_tokens = {s["log_token"] for s in scenes}

    out = dict(tables)
    out.update(scene=scenes, sample=samples, sample_data=sample_data, sample_annotation=annotations,
               instance=instances, ego_pose=[e for e in tables["ego_pose"] if e["token"] in ego_tokens],
               log=[lg for lg in tables["log"] if lg["token"] in log_tokens],
               map=[dict(m, log_tokens=[t for t in m["log_tokens"] if t in log_tokens])
                    for m in tables["map"] if set(m["log_tokens"]) & log_tokens])
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="data/nuscenes_mini_subset", help="thư mục đích")
    ap.add_argument("--scenes", nargs="+", default=DEFAULT_SCENES, help=f"tên scene (mặc định: {DEFAULT_SCENES})")
    ap.add_argument("--profile", choices=["lite", "full"], default="lite", help="lite (mặc định) hoặc full")
    ap.add_argument("--source", help="URL hoặc đường dẫn tới file v1.0-mini.tgz đã có trên máy")
    ap.add_argument("--list-scenes", action="store_true", help="chỉ in danh sách scene rồi thoát")
    args = ap.parse_args()

    out = Path(args.out)
    channels = LITE_CHANNELS if args.profile == "lite" else None
    reader = open_source(args.source)
    print(f"Đọc {VERSION}.tgz dạng stream, profile={args.profile}, scenes={args.scenes}")

    tables: dict[str, list] = {}
    wanted: set[str] | None = None
    written = 0
    with tarfile.open(fileobj=reader, mode="r|gz") as tf:
        for member in tf:
            name = member.name.lstrip("./")
            if name.startswith(f"{VERSION}/") and name.endswith(".json"):
                tables[Path(name).stem] = json.load(tf.extractfile(member))
                if all(t in tables for t in TABLES):
                    if args.list_scenes:
                        print()
                        for s in tables["scene"]:
                            print(f"  {s['name']}: {s['nbr_samples']} sample — {s['description']}")
                        return
                    filtered = filter_tables(tables, args.scenes, channels, keyframes_only=args.profile == "lite")
                    (out / VERSION).mkdir(parents=True, exist_ok=True)
                    for t, rows in filtered.items():
                        (out / VERSION / f"{t}.json").write_text(json.dumps(rows, indent=0), encoding="utf-8")
                    wanted = {d["filename"] for d in filtered["sample_data"]}
                    print(f"\n  metadata đã lọc: {len(filtered['sample'])} sample, {len(wanted)} file sensor cần lấy")
                continue
            if wanted is None or name not in wanted or not member.isfile():
                continue
            dst = out / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(tf.extractfile(member).read())
            wanted.discard(name)
            written += member.size
            if not wanted:
                break

    if wanted is None:
        raise SystemExit("File .tgz không chứa đủ metadata JSON. File có thể bị hỏng hoặc không phải v1.0-mini.")
    if wanted:
        raise SystemExit(f"\nThiếu {len(wanted)} file sensor (ví dụ {sorted(wanted)[:3]}). Hãy chạy lại script.")
    write_manifest(out)
    print(f"\nXong: ghi {written / 1e6:.1f} MB vào {out}, đọc qua mạng {reader.n / 1e9:.2f} GB. "
          f"Kiểm tra: python tools/verify_data.py --data-root {out}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
