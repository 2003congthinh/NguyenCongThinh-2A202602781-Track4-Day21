"""Kiểm tra bộ dữ liệu trong data/ có đầy đủ và không bị hỏng (so với MANIFEST.json).

Dùng sau khi clone repo (nếu nghi clone bị lỗi) hoặc sau khi chạy script tải thêm dữ liệu:
    python tools/verify_data.py --data-root data/kitti_mini
    python tools/verify_data.py --data-root data/nuscenes_mini_subset

Exit code 0 = dữ liệu đúng; 1 = thiếu file hoặc file bị hỏng (in ra danh sách cụ thể).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

MANIFEST = "MANIFEST.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_manifest(root: str | Path) -> Path:
    root = Path(root)
    files = sorted(p for p in root.rglob("*") if p.is_file() and p.name != MANIFEST and not p.name.endswith(".part"))
    entries = {p.relative_to(root).as_posix(): {"size": p.stat().st_size, "sha256": sha256(p)} for p in files}
    out = root / MANIFEST
    out.write_text(json.dumps({"n_files": len(entries), "total_bytes": sum(e["size"] for e in entries.values()),
                               "files": entries}, indent=1), encoding="utf-8")
    return out


def verify(root: Path) -> int:
    manifest_path = root / MANIFEST
    if not manifest_path.exists():
        print(f"[FAIL] Không thấy {manifest_path}. Kiểm tra lại đường dẫn --data-root (ví dụ data/kitti_mini).")
        return 1
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    missing, corrupted = [], []
    for rel, meta in manifest["files"].items():
        p = root / rel
        if not p.exists():
            missing.append(rel)
        elif p.stat().st_size != meta["size"] or sha256(p) != meta["sha256"]:
            corrupted.append(rel)
    n = manifest["n_files"]
    print(f"{root}: {n - len(missing) - len(corrupted)}/{n} file đúng, "
          f"tổng {manifest['total_bytes'] / 1e6:.1f} MB")
    for rel in missing:
        print(f"  [THIẾU] {rel}")
    for rel in corrupted:
        print(f"  [HỎNG]  {rel}  (kích thước hoặc checksum khác bản gốc)")
    if missing or corrupted:
        print("[FAIL] Dữ liệu chưa đầy đủ. Chạy `git checkout -- data/` để lấy lại bản gốc từ repo, "
              "hoặc `git pull` nếu bạn clone chưa xong.")
        return 1
    print("[PASS] Dữ liệu đầy đủ, dùng được.")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-root", required=True, help="thư mục dữ liệu, ví dụ data/kitti_mini")
    sys.exit(verify(Path(ap.parse_args().data_root)))
