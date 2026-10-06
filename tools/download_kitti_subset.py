"""TUỲ CHỌN: tải thêm frame KITTI 3D Object từ server chính thức.

Repo đã có sẵn 20 frame trong data/kitti_mini, nên KHÔNG cần chạy script này để làm lab.
Chỉ dùng khi bạn muốn thêm frame khác (ví dụ để có nhiều mẫu hơn cho benchmark).

Script không tải cả bộ dữ liệu: nó dùng HTTP Range để chỉ lấy đúng các frame được chọn
từ các file zip gốc (velodyne 29 GB, image_2 12 GB, calib 27 MB, label_2 6 MB).
Mỗi frame khoảng 3 MB. File đã có sẽ được bỏ qua.

Chạy từ gốc repo:
    python tools/download_kitti_subset.py --frames 000100 000200 000300
    python tools/download_kitti_subset.py --frames 000100 --out data/kitti_extra

Frame id hợp lệ: 6 chữ số, từ 000000 đến 007480 (split training).
Kết quả: <out>/training/{velodyne,calib,image_2,label_2}/<frame>.* và <out>/MANIFEST.json.

License: KITTI phát hành theo CC BY-NC-SA 3.0, chỉ dùng cho học tập và nghiên cứu phi thương mại.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from remote_zip import fetch_members, list_remote_zip  # noqa: E402
from verify_data import write_manifest  # noqa: E402

BASE_URL = "https://s3.eu-central-1.amazonaws.com/avg-kitti/"
# zip trên server -> (thư mục con, đuôi file)
PARTS = {
    "data_object_calib.zip": ("calib", ".txt"),
    "data_object_label_2.zip": ("label_2", ".txt"),
    "data_object_image_2.zip": ("image_2", ".png"),
    "data_object_velodyne.zip": ("velodyne", ".bin"),
}
# 20 frame trong split training, chọn từ label_2 để phủ các tình huống cần cho lab:
# nhiều pedestrian (000011, 000015, 000043, 000048), có cyclist (000001, 000007, 000021, 000023),
# đông xe (000008, 000010, 000032), xe xa > 50 m (000004, 000009, 000012),
# vật rất gần < 6 m (000019, 000025), bị che nhiều (000016, 000049), van/truck (000031, 000061).
DEFAULT_FRAMES = [
    "000001", "000004", "000007", "000008", "000009", "000010", "000011", "000012", "000015", "000016",
    "000019", "000021", "000023", "000025", "000031", "000032", "000043", "000048", "000049", "000061",
]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="data/kitti_mini", help="thư mục đích (mặc định: data/kitti_mini)")
    ap.add_argument("--frames", nargs="+", help="danh sách frame id 6 chữ số, ghi đè danh sách mặc định")
    ap.add_argument("--num-frames", type=int, default=len(DEFAULT_FRAMES),
                    help="lấy N frame đầu tiên của danh sách mặc định (mặc định: 20)")
    ap.add_argument("--workers", type=int, default=8,
                    help="số kết nối tải song song (mặc định: 8; mạng lớp yếu thì giảm xuống 2-4)")
    args = ap.parse_args()

    frames = args.frames or DEFAULT_FRAMES[: args.num_frames]
    out = Path(args.out)
    t0 = time.time()
    total_bytes = 0
    print(f"Tải {len(frames)} frame KITTI vào {out}/training ...")

    for zip_name, (sub, ext) in PARTS.items():
        dst_dir = out / "training" / sub
        dst_dir.mkdir(parents=True, exist_ok=True)
        todo = [f for f in frames if not (dst_dir / f"{f}{ext}").exists()]
        if not todo:
            print(f"  {sub:9s} đã có đủ, bỏ qua")
            continue
        index, index_bytes = list_remote_zip(BASE_URL + zip_name)
        members = {}
        for fid in todo:
            name = f"training/{sub}/{fid}{ext}"
            if name not in index:
                raise SystemExit(f"Không tìm thấy {name} trong {zip_name}. Frame id phải có đúng 6 chữ số "
                                 f"và thuộc split training (000000 đến 007480).")
            members[name] = dst_dir / f"{fid}{ext}"
        done = []

        def progress(_name: str, nbytes: int) -> None:
            done.append(_name)
            print(f"\r  {sub:9s} {len(done)}/{len(todo)} file  ({nbytes / 1e6:.1f} MB)", end="", flush=True)

        total_bytes += index_bytes + fetch_members(BASE_URL + zip_name, members, index, args.workers, progress)
        print()

    write_manifest(out)
    print(f"Xong sau {time.time() - t0:.0f}s, tổng tải {total_bytes / 1e6:.1f} MB. "
          f"Kiểm tra: python tools/verify_data.py --data-root {out}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
