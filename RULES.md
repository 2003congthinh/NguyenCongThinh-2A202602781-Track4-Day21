# Quy định làm bài

## 1. Làm bài

- Bài lab làm **cá nhân**. Mỗi học viên tự chọn 1 topic, tự viết code, tự viết báo cáo và tự nộp bài.
- Đổi topic sau CP2 thì phải báo lab coach, để lab coach ghi nhận và hỗ trợ đúng topic.
- Được tự do chọn thư viện, nhưng **không train model từ đầu** trong giờ lab. Topic B và topic C có model chỉ dùng checkpoint đã train sẵn.
- Trong `starter/`, chỉ được sửa 2 hàm có đánh dấu `TODO(CP2)` trong `projection.py`. Mọi code khác bạn tự viết đặt trong `src/`.
- Kẹt ở cùng một lỗi quá 10 phút thì phải hỏi lab coach. Nếu làm topic B/C mà môi trường GPU bị hỏng, hãy đổi sang topic không cần GPU (A, E, hoặc C ở mức Basic) thay vì ngồi sửa môi trường.

## 2. Sử dụng AI (ChatGPT, Claude, Copilot, Cursor...)

**Được phép và khuyến khích**, với 3 điều kiện:

1. **Khai báo đầy đủ** trong mục 6 của `report/REPORT.md`: dùng công cụ nào, dùng cho việc gì, và bạn đã tự kiểm chứng kết quả của AI bằng cách nào.
2. **Bạn chịu trách nhiệm** về mọi dòng code và mọi con số đã nộp. Khi giảng viên hỏi "dòng này làm gì?" hay "vì sao số này ra như vậy?", bạn phải trả lời được. Phần nào không giải thích được thì phần đó bị tính 0 điểm (xem `RUBRIC.md` mục 4).
3. **Không dùng AI để bịa** số liệu, ảnh kết quả hay failure case. Mọi bằng chứng phải được tạo ra từ code chạy thật trong repo.

Gợi ý dùng AI hiệu quả: nhờ giải thích thông báo lỗi, tra cách dùng hàm của Open3D/OpenCV, viết code vẽ biểu đồ, hoặc nhờ rà lại logic biến đổi hệ toạ độ. Nhưng **luôn tự test lại** bằng một trường hợp dễ kiểm tra, ví dụ điểm `(10, 0, 0)` ở CP2.

Không khai báo sử dụng AI bị trừ 10 điểm (xem `RUBRIC.md` mục 3).

## 3. Trao đổi và sao chép

- **Được** trao đổi ý tưởng, hỏi nhau cách debug, và thảo luận kết quả với học viên khác.
- **Không được** copy code, số liệu, ảnh hay báo cáo của học viên khác, kể cả của khoá trước.
- **Không được** đưa code của mình cho người khác copy. Người đưa bị xử lý như người copy.
- Code lấy từ nguồn mở (GitHub, tài liệu chính thức, StackOverflow) **phải ghi nguồn** bằng comment ở đầu file hoặc đầu hàm, và phải tuân thủ license của nguồn đó.
- Hai bài có code hoặc số liệu giống nhau bất thường sẽ bị gọi vấn đáp giải trình. Nếu xác định vi phạm thì **0 điểm toàn bài** cho tất cả học viên liên quan, và báo cáo theo quy chế học thuật của chương trình.
- Làm giả số liệu bị xử lý như đạo văn.

## 4. Nộp muộn

| Thời điểm nộp | Xử lý |
|---|---|
| Trước 23:59 07/10/2026 (UTC+7) | Chấm bình thường |
| Từ 00:00 đến 23:59 ngày 08/10/2026 (UTC+7) | **−10 điểm** trên tổng điểm (sau khi đã cộng bonus) |
| Sau 23:59 08/10/2026 (UTC+7) | **0 điểm** phần repo, chỉ giữ điểm Trình bày |

- Thời điểm nộp được xác định bằng **cả hai mốc**: lúc push commit cuối lên remote và lúc nộp trên LMS. Mốc nào muộn hơn thì lấy mốc đó.
- Nếu có lý do bất khả kháng (ốm, sự cố hệ thống của trường), phải báo giảng viên **trước deadline**, kèm minh chứng.

## 5. Sửa bài sau deadline

- Giảng viên chấm **commit cuối cùng trước deadline**. Các commit sau deadline bị bỏ qua.
- Muốn được chấm bản sửa sau deadline thì phải nộp lại trên LMS, và bài sẽ bị tính là **nộp muộn** theo mục 4.
- Trước deadline, bạn được sửa thoải mái sau buổi demo (lỗi chính tả, đường dẫn ảnh, bổ sung giải thích) mà không bị trừ điểm.
- **Không được** force-push hay viết lại lịch sử git sau deadline. Ngoại lệ duy nhất là xoá API key hoặc dữ liệu nhạy cảm bị lộ, và khi đó phải báo giảng viên.

## 6. Bảo mật API key và dữ liệu

**API key và token**
- Không bao giờ ghi trực tiếp key vào code hay notebook. Hãy đặt key trong biến môi trường hoặc file `.env`. File `.env` đã nằm sẵn trong `.gitignore`.
- Lỡ commit key thì phải **thu hồi (revoke) key ngay** trên trang quản lý của nhà cung cấp, rồi mới xoá khỏi repo. Chỉ xoá commit thì chưa đủ, vì key vẫn còn trong lịch sử git.
- `tools/check_submission.py` có quét các dạng key phổ biến, nhưng bạn vẫn phải tự kiểm tra.

**Dữ liệu**
- Dữ liệu KITTI và nuScenes trong thư mục `data/` có giấy phép CC BY-NC-SA: chỉ dùng cho học tập và nghiên cứu phi thương mại. **Không** dùng dữ liệu này cho mục đích thương mại.
- **Không sửa và không xoá** file trong `data/kitti_mini/`, `data/nuscenes_mini_subset/` và `data/synthetic/`. Nếu cần dữ liệu đã biến đổi (ví dụ bỏ bớt điểm cho topic C), hãy tạo trong code và lưu kết quả vào `results/`, không ghi đè lên dữ liệu gốc.
- **Không commit** dữ liệu bạn tự tải thêm (xem `data/README.md` mục 4) hay các file nén `.zip`/`.tgz`, vì chúng làm repo nặng.
- Nếu dùng dữ liệu log thật của công ty hoặc dự án cá nhân: chỉ dùng khi đã được phép, và phải che thông tin nhạy cảm (biển số xe, khuôn mặt, toạ độ GPS) trước khi đưa ảnh vào báo cáo.

## 7. Sử dụng tài nguyên chung

- Nếu lớp có GPU hoặc server dùng chung: chỉ chạy job trong giờ lab, tắt job ngay khi chạy xong, và không để job chạy nền sau giờ lab.
- Không tải dataset qua mạng của lớp trong giờ lab. Dữ liệu cần thiết đã có sẵn trong repo. Hãy clone repo ở nhà trước buổi học.
