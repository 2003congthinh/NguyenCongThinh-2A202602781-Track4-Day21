"""Tự kiểm tra bài trước khi nộp. Chạy từ gốc repo:

    python tools/check_submission.py

Exit code 0 = đủ điều kiện nộp; 1 = còn lỗi bắt buộc (xem dòng [FAIL]).
Script chỉ kiểm tra hình thức; điểm nội dung chấm theo RUBRIC.md.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLACEHOLDER_RE = re.compile(r"\[ĐIỀN[^\]]*\]")
MSSV_RE = re.compile(r"\*\*MSSV:\*\*\s*([A-Za-z0-9]+)")
REPORT_SECTIONS = ["## 1. Claim", "## 2. Evidence", "## 3. Failure case", "## 4. Khuyến nghị", "## 5. Cách chạy lại",
                   "## 6. Khai báo sử dụng AI"]
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"hf_[A-Za-z0-9]{30,}"),
    re.compile(r"ghp_[A-Za-z0-9]{30,}"),
    re.compile(r"AIza[0-9A-Za-z_\-]{35}"),
    re.compile(r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*['\"][^'\"\s]{12,}['\"]"),
]
MAX_FILE_MB = 20
TEXT_SUFFIXES = {".py", ".md", ".txt", ".yaml", ".yml", ".json", ".ipynb", ".cfg", ".toml", ".sh", ".ps1"}

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))


def tracked_files() -> list[Path]:
    try:
        out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
        return [ROOT / f for f in out.splitlines() if f]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return [p for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts]


def main() -> int:
    report = ROOT / "report" / "REPORT.md"
    text = report.read_text(encoding="utf-8") if report.exists() else ""
    missing = [s for s in REPORT_SECTIONS if s not in text]
    check("report/REPORT.md đủ 6 mục", report.exists() and not missing, f"thiếu: {missing}")
    left = PLACEHOLDER_RE.findall(text)
    check("report/REPORT.md đã điền hết", bool(text) and not left,
          f"còn {len(left)} chỗ chưa điền, ví dụ {left[:3]}")
    mssv_match = MSSV_RE.search(text)
    mssv = mssv_match.group(1) if mssv_match else None
    check("report/REPORT.md có dòng **MSSV:** hợp lệ (chỉ chữ và số)", mssv is not None)

    res = ROOT / "results"
    csvs = list(res.rglob("*.csv")) if res.exists() else []
    media = [p for ext in ("*.png", "*.jpg", "*.gif", "*.mp4") for p in res.rglob(ext)] if res.exists() else []
    check("results/ có >= 1 bảng số liệu (.csv)", len(csvs) >= 1, f"{len(csvs)} file")
    check("results/ có >= 1 ảnh/video demo", len(media) >= 1, f"{len(media)} file")
    fail_media = [p for p in media if "fail" in p.name.lower()]
    check("results/ có ảnh failure case (tên chứa 'fail')", len(fail_media) >= 1, "đặt tên ví dụ fail_01_yaw_drift.png")

    files = tracked_files()
    big = [f"{p.relative_to(ROOT)} ({p.stat().st_size / 1e6:.0f} MB)" for p in files
           if p.exists() and p.stat().st_size > MAX_FILE_MB * 1e6]
    check(f"Không có file > {MAX_FILE_MB} MB", not big, ", ".join(big))

    # Dữ liệu đề bài nằm trong data/ là hợp lệ; chỉ chặn dữ liệu thô/checkpoint học viên tự thêm ở chỗ khác.
    raw = [str(p.relative_to(ROOT)) for p in files
           if p.suffix in {".bin", ".pcd", ".bag", ".db3", ".pth", ".pt", ".ckpt"}
           and p.relative_to(ROOT).parts[0] != "data"]
    check("Không commit dữ liệu thô / checkpoint ngoài thư mục data/", not raw, ", ".join(raw[:5]))

    check("Không commit .env", not any(p.name == ".env" for p in files))
    leaks = []
    for p in files:
        if p.suffix in TEXT_SUFFIXES and p.exists() and p.name != "check_submission.py":
            content = p.read_text(encoding="utf-8", errors="ignore")
            if any(pat.search(content) for pat in SECRET_PATTERNS):
                leaks.append(str(p.relative_to(ROOT)))
    check("Không lộ API key / token", not leaks, ", ".join(leaks))

    hard_fail = False
    for name, ok, detail in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + ("" if ok or not detail else f"  -> {detail}"))
        hard_fail |= not ok
    print("\nKẾT QUẢ:", "SẴN SÀNG NỘP" if not hard_fail else "CHƯA ĐỦ ĐIỀU KIỆN NỘP")
    return 1 if hard_fail else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
