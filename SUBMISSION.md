# Hướng dẫn nộp bài

Bài lab làm **cá nhân**. Mỗi học viên nộp một repo.

## 1. Deadline

| Mốc | Thời gian (múi giờ **UTC+7, giờ Việt Nam**) |
|---|---|
| Demo trước lớp (CP6) | Trong buổi lab, **Thứ Tư 07/10/2026** |
| **Deadline nộp repo** | **23:59 Thứ Tư 07/10/2026 (UTC+7)** |
| Hạn chót nộp muộn (bị trừ điểm) | 23:59 Thứ Năm 08/10/2026 (UTC+7) |

Bài được chấm theo **commit cuối cùng có trên remote trước deadline**. Quy định về nộp muộn và sửa bài sau deadline nằm trong [RULES.md](RULES.md) mục 4 và 5.

## 2. Nộp ở đâu

1. Push toàn bộ bài lên bản fork `<HoVaTen>-<MSSV>-Track4-Day21` của bạn.
2. Nộp lên hệ thống nộp bài của khoá học (LMS), mục bài tập **Day 6 Lab**, gồm 2 thứ:
   - Link repo.
   - Commit hash cuối cùng, lấy bằng lệnh `git rev-parse HEAD`.

## 3. Cấu trúc repo phải có khi nộp

```
<HoVaTen>-<MSSV>-Track4-Day21/
├── src/                            # BẮT BUỘC: toàn bộ code bạn tự viết (script .py hoặc notebook .ipynb)
├── starter/projection.py           # BẮT BUỘC với topic A, C, E, F: đã viết 2 hàm TODO(CP2)
├── results/
│   ├── <tên_thí_nghiệm>.csv        # BẮT BUỘC: ít nhất 1 bảng số liệu
│   └── figures/
│       ├── <tên_ảnh_demo>.png      # BẮT BUỘC: ít nhất 1 ảnh demo
│       └── fail_<số>_<mô_tả>.png   # BẮT BUỘC: ít nhất 1 ảnh failure case
└── report/
    └── REPORT.md                   # BẮT BUỘC: điền thông tin học viên + đủ 6 mục, không còn dấu [ĐIỀN]
```

Video demo lớn hơn 20 MB thì **không commit** vào repo. Hãy upload lên Google Drive hoặc YouTube (chế độ không công khai), rồi dán link vào mục 2 của REPORT.

## 4. Quy tắc đặt tên

| Đối tượng | Quy tắc | Ví dụ |
|---|---|---|
| Repo (bản fork) | `<HoVaTen>-<MSSV>-Track4-Day21`, họ tên viết liền, không dấu, viết hoa chữ cái đầu mỗi từ | `NguyenVanA-20240123-Track4-Day21` |
| Ảnh failure | `fail_<số thứ tự 2 chữ số>_<mô tả ngắn>.png` | `fail_01_yaw_2deg_pole.png` |
| File CSV kết quả | `<tên_thí_nghiệm>.csv`, chữ thường, các từ nối bằng dấu gạch dưới | `yaw_perturb_sweep.csv` |
| Commit message | `CPx: <mô tả ngắn>`, với x là số checkpoint | `CP3: yaw sweep 0-3 deg` |

MSSV chỉ gồm chữ và số, không có dấu cách hay ký tự đặc biệt.

## 5. Kiểm tra trước khi nộp

Chạy lệnh sau từ thư mục gốc của repo:

```bash
python tools/check_submission.py
```

Script kiểm tra các điểm sau, và in `[PASS]` hoặc `[FAIL]` cho từng điểm:

- `report/REPORT.md` có đủ 6 mục và đã điền hết, không còn dấu `[ĐIỀN]`.
- `results/` có ít nhất 1 file CSV, 1 ảnh demo và 1 ảnh có tên bắt đầu bằng `fail_`.
- Không có file nào lớn hơn 20 MB.
- Không có dữ liệu thô hay model checkpoint nằm **ngoài** thư mục `data/`. Dữ liệu đề bài trong `data/` là hợp lệ, không bị tính lỗi.
- Không commit file `.env`, và không có API key hay token trong code.

Kết quả đúng: mọi dòng đều là `[PASS]`, dòng cuối là `KẾT QUẢ: SẴN SÀNG NỘP`.

Ngoài script, bạn tự kiểm tra thêm 3 điểm sau:

- [ ] Clone lại repo vào một thư mục mới, chạy các lệnh ở mục 5 của REPORT, và ra đúng kết quả như trong báo cáo.
- [ ] Mở `report/REPORT.md` bằng trình xem Markdown (ví dụ trên GitHub), và mọi ảnh đều hiển thị được.
- [ ] Lệnh `git log origin/main -1` hiện đúng commit hash mà bạn đã nộp trên LMS.
