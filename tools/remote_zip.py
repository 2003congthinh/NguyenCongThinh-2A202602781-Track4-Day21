"""Lấy một vài file con từ file .zip nằm trên HTTP server mà không tải cả file zip.

Cách làm: đọc mục lục (central directory) ở cuối file zip bằng HTTP Range, rồi với mỗi
file con chỉ tải đúng đoạn byte chứa nó và giải nén tại chỗ. Nhờ vậy lấy 20 frame từ file
zip velodyne 29 GB chỉ tốn khoảng 40 MB. Server phải hỗ trợ header `Range` (S3 của KITTI có).
"""
from __future__ import annotations

import io
import struct
import time
import urllib.error
import urllib.request
import zipfile
import zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable

LOCAL_HEADER = struct.Struct("<4s5H3I2H")  # 30 byte, xem đặc tả ZIP APPNOTE mục 4.3.7
LOCAL_EXTRA_SLACK = 1024  # local header có thể có extra field dài hơn central directory


def http_range(url: str, start: int, end: int, retries: int = 5, timeout: int = 60) -> bytes:
    """Tải byte [start, end] (tính cả end). Tự thử lại khi lỗi mạng."""
    req = urllib.request.Request(url, headers={"Range": f"bytes={start}-{end}"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                if r.status != 206:
                    raise OSError(f"Server không hỗ trợ HTTP Range (status {r.status}): {url}")
                return r.read()
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if attempt == retries - 1:
                raise
            wait = 2 ** attempt
            print(f"\n  lỗi mạng ({e}), thử lại sau {wait}s...")
            time.sleep(wait)
    raise AssertionError("unreachable")


class HttpRangeFile(io.RawIOBase):
    """File-like chỉ đọc, dùng để `zipfile` đọc được mục lục của zip từ xa."""

    def __init__(self, url: str):
        self.url, self.pos, self.bytes_downloaded = url, 0, 0
        req = urllib.request.Request(url, headers={"Range": "bytes=0-0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            content_range = r.headers.get("Content-Range")
            if r.status != 206 or not content_range:
                raise OSError(f"Server không hỗ trợ HTTP Range: {url}")
            self.size = int(content_range.split("/")[-1])

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self.pos

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        base = {io.SEEK_SET: 0, io.SEEK_CUR: self.pos, io.SEEK_END: self.size}[whence]
        self.pos = max(0, base + offset)
        return self.pos

    def readinto(self, b) -> int:
        if self.pos >= self.size or len(b) == 0:
            return 0
        data = http_range(self.url, self.pos, min(self.pos + len(b), self.size) - 1)
        b[: len(data)] = data
        self.pos += len(data)
        self.bytes_downloaded += len(data)
        return len(data)


def list_remote_zip(url: str) -> tuple[dict[str, zipfile.ZipInfo], int]:
    """Trả về ({tên file con: ZipInfo}, số byte đã tải để đọc mục lục)."""
    raw = HttpRangeFile(url)
    zf = zipfile.ZipFile(io.BufferedReader(raw, buffer_size=256 * 1024))
    return {i.filename: i for i in zf.infolist()}, raw.bytes_downloaded


def _fetch_one(url: str, info: zipfile.ZipInfo) -> bytes:
    start = info.header_offset
    blob = http_range(url, start, start + LOCAL_HEADER.size + len(info.filename.encode()) + LOCAL_EXTRA_SLACK
                      + info.compress_size - 1)
    sig, *_, name_len, extra_len = LOCAL_HEADER.unpack_from(blob)
    if sig != b"PK\x03\x04":
        raise OSError(f"{info.filename}: local header sai, file zip trên server có thể đã đổi")
    offset = LOCAL_HEADER.size + name_len + extra_len
    if offset + info.compress_size > len(blob):
        blob += http_range(url, start + len(blob), start + offset + info.compress_size - 1)
    payload = blob[offset: offset + info.compress_size]
    if info.compress_type == zipfile.ZIP_STORED:
        data = payload
    elif info.compress_type == zipfile.ZIP_DEFLATED:
        data = zlib.decompress(payload, -15)
    else:
        raise OSError(f"{info.filename}: kiểu nén {info.compress_type} chưa hỗ trợ")
    if zlib.crc32(data) != info.CRC:
        raise OSError(f"{info.filename}: sai CRC, dữ liệu tải về bị hỏng")
    return data


def fetch_members(url: str, members: dict[str, Path], index: dict[str, zipfile.ZipInfo], workers: int = 8,
                  on_done: Callable[[str, int], None] | None = None) -> int:
    """Tải song song các file con `members` ({tên trong zip: đường dẫn đích}). Trả về tổng byte đã tải."""
    total = 0

    def job(name: str, dst: Path) -> int:
        data = _fetch_one(url, index[name])
        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp = dst.with_name(dst.name + ".part")
        tmp.write_bytes(data)
        tmp.replace(dst)
        return index[name].compress_size

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(job, n, d): n for n, d in members.items()}
        for fut in as_completed(futures):
            total += fut.result()
            if on_done:
                on_done(futures[fut], total)
    return total
