# Rubric chấm điểm

Bài lab làm **cá nhân**. Điểm của mỗi học viên tính như sau:

- **Phần bắt buộc: 100 điểm**, gồm 5 tiêu chí (mục 1).
- **Bonus: cộng tối đa 10 điểm**, chấm riêng (mục 2). **Tổng điểm sau bonus không vượt quá 100.**
- **Trừ điểm và mất điểm:** xem mục 3.
- **Vấn đáp xác minh:** xem mục 4.

> Bài được chấm theo **bằng chứng (evidence) và khả năng giải thích**. Dùng model mới nhất hay viết code dài không được cộng điểm.

---

## 1. Phần bắt buộc (100 điểm)

### 1.1 Demo chạy thật — 30 điểm

| Mức | Điểm | Mô tả |
|---|---|---|
| Xuất sắc | 26–30 | Có ảnh hoặc video kết quả chạy thật, input và output rõ ràng. Giảng viên chạy lệnh ở mục 5 của REPORT trên repo vừa clone và ra đúng kết quả mà không phải sửa gì |
| Đạt | 18–25 | Có code và ảnh/video kết quả, input và output rõ ràng, nhưng giảng viên phải sửa nhẹ (ví dụ sai đường dẫn) mới chạy lại được |
| Yếu | 8–17 | Code chỉ chạy được một phần, hoặc chỉ có ảnh mà không rõ ảnh được tạo ra từ lệnh nào |
| Không đạt | 0–7 | Chỉ mô tả lý thuyết, không có kết quả chạy thật |

**Bằng chứng cần có:** ảnh/video trong `results/`, code trong `src/` và 2 hàm TODO trong `starter/projection.py`, lệnh chạy lại ở mục 5 của REPORT.

### 1.2 Benchmark và số liệu kiểm tra — 25 điểm

| Mức | Điểm | Mô tả |
|---|---|---|
| Xuất sắc | 22–25 | Có ít nhất 3 cấu hình hoặc mức thay đổi. Metric phù hợp topic, ví dụ % điểm nằm trong box, IoU, số điểm trên object, latency p50/p95, AP/NDS. Có cố định seed, chạy lại ra cùng số. Bảng hoặc biểu đồ cho thấy rõ xu hướng |
| Đạt | 15–21 | Có bảng số liệu nhưng chỉ có 2 mức, hoặc thiếu mô tả cấu hình của từng lần chạy |
| Yếu | 6–14 | Chỉ có 1 con số, hoặc metric không liên quan tới claim |
| Không đạt | 0–5 | Không có số liệu |

**Bằng chứng cần có:** `results/*.csv`, `results/figures/*.png`, mục 2 của REPORT.

### 1.3 Phân tích failure case — 25 điểm

| Mức | Điểm | Mô tả |
|---|---|---|
| Xuất sắc | 22–25 | Chỉ rõ **khi nào** sai và **vì sao** sai. Chỉ ra đúng lớp debug: I/O, Geometry, Time, Preprocess, Model hoặc Metric. Liên hệ được với sensor, calibration hoặc cách biểu diễn dữ liệu. Đề xuất cách phát hiện lỗi này khi chạy thật |
| Đạt | 15–21 | Có failure case kèm ảnh minh hoạ và giải thích hợp lý, nhưng chưa chỉ ra nguyên nhân gốc |
| Yếu | 6–14 | Chỉ nêu chung chung, ví dụ "model kém với vật xa", không có ảnh hay số liệu |
| Không đạt | 0–5 | Không có failure case |

**Bằng chứng cần có:** `results/figures/fail_*.png`, mục 3 của REPORT.

### 1.4 Liên hệ thực tế — 10 điểm

| Mức | Điểm | Mô tả |
|---|---|---|
| Xuất sắc | 9–10 | Nêu use-case cụ thể (ADAS, robot hoặc drone). Nêu rõ đánh đổi khi triển khai (tốc độ, tài nguyên tính toán, an toàn). Đề xuất chỉ số hệ thống cần ghi log khi chạy thật |
| Đạt | 5–8 | Có nhắc use-case nhưng chung chung, không nêu đánh đổi cụ thể |
| Không đạt | 0–4 | Không liên hệ thực tế |

**Bằng chứng cần có:** mục 4 của REPORT.

### 1.5 Trình bày — 10 điểm

Học viên được gọi lên demo (CP6) chấm theo phần trình bày và trả lời câu hỏi. Học viên không được gọi chấm theo REPORT đã nộp. Cả hai trường hợp dùng chung thang điểm sau:

| Mức | Điểm | Mô tả |
|---|---|---|
| Xuất sắc | 9–10 | Một claim rõ ràng, REPORT gọn, người đọc hiểu được kết quả chính mà không cần giải thích thêm. Nếu được gọi lên: nói đúng giờ (3 phút) và trả lời được câu hỏi |
| Đạt | 5–8 | Nội dung đúng nhưng REPORT rối hoặc dài dòng. Nếu được gọi lên: quá giờ hoặc trả lời chưa chắc chắn |
| Không đạt | 0–4 | Không có claim, REPORT khó đọc. Nếu được gọi lên: không trả lời được câu hỏi |

**Bằng chứng cần có:** `report/REPORT.md`, phần trình bày ở CP6 nếu được gọi.

---

## 2. Bonus (cộng tối đa 10 điểm)

Bonus **chỉ được tính khi tiêu chí bắt buộc liên quan đã đạt mức "Đạt" trở lên**. Nội dung nào đã là yêu cầu chính của topic thì không được tính bonus. Ví dụ: làm topic C thì không nhận bonus B2, làm topic B thì không nhận bonus B3.

| Mã | Nội dung | Tối đa | Bằng chứng |
|---|---|---|---|
| B1 | So sánh **2 thuật toán hoặc 2 cấu hình** trên cùng dữ liệu, cùng metric | +4 | Bảng so sánh, kèm nhận xét ưu nhược điểm của từng bên |
| B2 | **Stress test suy giảm dữ liệu:** ít nhất 2 loại suy giảm, mỗi loại ít nhất 3 mức | +3 | Biểu đồ mức suy giảm theo metric |
| B3 | Đo **latency p50/p95** đúng cách: bỏ lần chạy đầu, chạy ít nhất 20 lần | +2 | File CSV latency, kèm mô tả phần cứng (CPU/GPU) |
| B4 | **Tool dùng lại được** cho bài sau: script có tham số dòng lệnh và `--help`, hoặc checklist debug tự viết | +3 | File trong `src/`, kèm hướng dẫn chạy trong REPORT |
| B5 | Chạy cùng thí nghiệm trên **cả hai dataset thật** (`data/kitti_mini` và `data/nuscenes_mini_subset`), và giải thích vì sao kết quả khác nhau. Ví dụ do số beam LiDAR, độ phân giải ảnh, điều kiện ngày/đêm, hay độ lệch thời gian giữa LiDAR và camera | +2 | Bảng kết quả trên 2 dataset, kèm đoạn giải thích trong mục 2 của REPORT |
| B6 | Phát hiện được **tất cả lỗi cài sẵn** trong `data/synthetic` và giải thích đúng | +2 | Bảng gồm 3 cột: lỗi, frame bị lỗi, cách phát hiện |

Tổng các mục bonus có thể vượt 10, nhưng **chỉ được cộng tối đa 10 điểm**.

---

## 3. Điều kiện trừ điểm và mất điểm

| Vi phạm | Hậu quả |
|---|---|
| Thiếu 1 trong 5 sản phẩm bắt buộc: claim, bảng số liệu, ảnh/video demo, failure case, khuyến nghị | Tiêu chí tương ứng chỉ được tối đa mức "Yếu" |
| Giảng viên chạy lại không ra số liệu như trong báo cáo (khác đáng kể và không giải thích được) | Tiêu chí 1.2 chỉ được tối đa 50% điểm |
| Nộp muộn | Theo `RULES.md` mục 4: muộn trong vòng 24 giờ bị −10 điểm. Muộn quá 24 giờ thì 0 điểm phần repo, chỉ giữ điểm Trình bày |
| Đặt sai tên file hoặc sai cấu trúc thư mục, khiến không chấm tự động được | −5 điểm |
| Không khai báo sử dụng AI (mục 6 của REPORT) | −10 điểm |
| Commit thêm dữ liệu ngoài phần đề bài đã cung cấp trong `data/`, model checkpoint (`.pth`, `.ckpt`...), file nén, hoặc bất kỳ file nào lớn hơn 20 MB | −5 điểm, và phải xoá khỏi lịch sử git |
| Sửa hoặc xoá file dữ liệu gốc của đề bài trong `data/` | −5 điểm |
| Lộ API key hoặc token trong repo | −10 điểm, và phải thu hồi key ngay |
| Sao chép bài của người khác, hoặc làm giả số liệu | 0 điểm toàn bài, xử lý theo `RULES.md` mục 3 |

---

## 4. Vấn đáp xác minh

Giảng viên có thể gọi **bất kỳ học viên nào** vấn đáp 5 phút, trong buổi lab hoặc trong vòng 1 tuần sau deadline, để xác minh bài là do chính học viên làm. Các trường hợp sau chắc chắn bị gọi:

- Lịch sử commit chỉ có 1–2 commit dồn vào cuối giờ, không theo các checkpoint.
- Code hoặc số liệu giống bất thường với bài của học viên khác.
- Mục 6 của REPORT (khai báo AI) không khớp với code đã nộp.

Trong buổi vấn đáp, học viên phải giải thích được code mình nộp và các con số trong báo cáo. **Phần nào không giải thích được thì phần đó bị tính 0 điểm.**
