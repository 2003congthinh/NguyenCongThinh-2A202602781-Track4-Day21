# Day 6 Lab — 3D from Point Clouds & LiDAR-Camera Projection

**VinUni AI20K · Track 4: Computer Vision and Robotics · Mini project 2 giờ**

## Tóm tắt bài lab

Bài lab làm **cá nhân**. Trong 2 giờ, mỗi học viên chọn **1 trong 6 topic** thực chiến về point cloud và LiDAR-camera (liệt kê ở mục 5), và phải làm 4 việc:

1. Chạy được một demo thật trên dữ liệu thật hoặc dữ liệu mẫu.
2. Làm một benchmark hoặc stress test nhỏ, có ít nhất 3 mức so sánh, ra bảng số liệu.
3. Tìm ra ít nhất một trường hợp phương pháp hoạt động sai (failure case) và giải thích nguyên nhân.
4. Viết báo cáo ngắn `report/REPORT.md`. Cuối buổi, giảng viên gọi ngẫu nhiên một số học viên lên trình bày kết quả trong 3 phút.

> Bài lab **không chấm theo việc dùng model mới nhất hay code dài**. Bài chấm theo khả năng biến một câu hỏi mơ hồ (ví dụ "calibration lệch thì sao?") thành một thí nghiệm có số liệu và hình ảnh làm bằng chứng. Thang điểm chi tiết nằm trong [RUBRIC.md](RUBRIC.md).

---

## 1. Mục tiêu học tập

Sau buổi lab, mỗi học viên làm được 5 việc sau:

1. **Kiểm tra chất lượng dữ liệu point cloud trước khi dùng model:** đếm số điểm, phát hiện điểm lỗi (NaN), xem phân bố khoảng cách, mật độ theo góc quét, timestamp, và xác định dữ liệu đang ở hệ toạ độ nào.
2. **Tự viết phép chiếu điểm LiDAR lên ảnh camera** theo công thức `s·[u, v, 1]ᵀ = K·[R | t]·[x, y, z, 1]ᵀ`, biết lọc bỏ điểm nằm sau camera và ngoài khung ảnh, và dùng ảnh overlay để kiểm tra calibration đúng hay sai.
3. **Thiết kế một thí nghiệm nhỏ có kiểm soát:** thay đổi đúng một yếu tố (độ lệch calibration, mức suy giảm dữ liệu hoặc một tham số xử lý), giữ nguyên mọi yếu tố khác, rồi đo ảnh hưởng bằng số liệu.
4. **Phân tích failure case** và chỉ ra lỗi thuộc lớp nào trong 6 lớp: đọc dữ liệu (I/O), hình học/hệ toạ độ (Geometry), đồng bộ thời gian (Time), tiền xử lý (Preprocess), model, hay cách đo (Metric).
5. **Liên hệ kết quả với hệ thống thật** (xe tự hành/ADAS, robot, drone): nêu được đánh đổi giữa tốc độ, độ chính xác và độ bền, và nêu được hệ thống cần theo dõi chỉ số gì khi chạy thật.

## 2. Chuẩn bị TRƯỚC buổi học

Hoàn thành **toàn bộ** bảng dưới đây trước giờ lab. Danh sách tự kiểm tra từng bước nằm ở mục CP0 trong [CHECKPOINTS.md](CHECKPOINTS.md).

| Hạng mục | Cần làm cụ thể |
|---|---|
| Kiến thức | Đọc lại slide Day 6, đặc biệt slide 5–9 (point cloud), 17 (quy ước 3D box), 22–23 (projection và 10 lỗi projection hay gặp), 30 (6 lớp debug). Ôn lại phép biến đổi rigid transform và calibration của Day 4–5 |
| Phần mềm | Cài Python 3.10 trở lên, Git, VS Code hoặc Cursor. Nếu chọn topic D, cài thêm `pip install open3d`. Nếu chọn topic B, hoặc topic C có dùng model, phải cài sẵn MMDetection3D hoặc OpenPCDet trên máy có GPU NVIDIA và chạy được demo của thư viện đó trên 1 frame |
| Dữ liệu | **Có sẵn trong repo**, không cần tải riêng: dữ liệu mẫu `data/synthetic/`, 20 frame KITTI trong `data/kitti_mini/`, và 2 scene nuScenes trong `data/nuscenes_mini_subset/`. Repo nặng khoảng 135 MB, vì vậy **hãy clone ở nhà trước buổi học** để không làm quá tải mạng của lớp. Mô tả chi tiết dữ liệu nằm trong [data/README.md](data/README.md) |
| Repo | Fork repo đề bài và clone về máy **ở nhà**, theo mục 3, bước 1 |

> **Quy định nếu muốn chạy detector (topic B, hoặc topic C có dùng model):** nếu đến đầu giờ lab mà môi trường GPU của bạn vẫn chưa chạy được demo, bạn **phải đổi** sang một trong ba lựa chọn không cần GPU: topic A, topic E, hoặc topic C ở mức Basic (chỉ đo trên dữ liệu, không dùng model). Không được dùng thời gian lab để sửa lỗi cài đặt CUDA.

## 3. Cách bắt đầu

### Bước 1. Fork repo đề bài (khoảng 5 phút, làm ở nhà)

1. Đăng nhập GitHub, mở [repo đề bài](https://github.com/VinUni-AI20k/K4-Track4-Day06-3D-From-Point-Clouds) và bấm nút **Fork** ở góc trên bên phải.
2. Ở trang *Create a new fork*: ô *Owner* chọn tài khoản cá nhân của bạn, ô *Repository name* đặt theo cú pháp `<HoVaTen>-<MSSV>-Track4-Day21`. Họ tên viết liền, không dấu, viết hoa chữ cái đầu mỗi từ, ví dụ `NguyenVanA-20240123-Track4-Day21`. Bấm **Create fork**.
3. Clone bản fork về máy. Repo nặng khoảng 135 MB, nên hãy làm ở nhà:

```bash
git clone https://github.com/<username>/<HoVaTen>-<MSSV>-Track4-Day21.git
cd <HoVaTen>-<MSSV>-Track4-Day21
git remote add upstream https://github.com/VinUni-AI20k/K4-Track4-Day06-3D-From-Point-Clouds.git
```

Remote `upstream` dùng để lấy bản cập nhật của đề bài (`git pull upstream main`) khi giảng viên thông báo.

### Bước 2. Cài môi trường (khoảng 5 phút, làm ở nhà)

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

Kết quả đúng: lệnh `pip` kết thúc mà không có dòng `ERROR`.

### Bước 3. Kiểm tra dữ liệu đã có đủ

Dữ liệu đã nằm sẵn trong thư mục `data/` khi clone. Chạy 2 lệnh sau để chắc chắn clone không bị thiếu hay hỏng file:

```bash
python tools/verify_data.py --data-root data/kitti_mini
python tools/verify_data.py --data-root data/nuscenes_mini_subset
```

Kết quả đúng: mỗi lệnh in ra `[PASS] Dữ liệu đầy đủ, dùng được.` Nếu có dòng `[THIẾU]` hoặc `[HỎNG]`, chạy `git checkout -- data/` rồi kiểm tra lại.

### Bước 4. Chạy thử thống kê dữ liệu (chạy được ngay, chưa cần viết code)

```bash
python -m starter.data_health --data-root data/synthetic
```

Kết quả đúng: in ra 5 dòng, mỗi dòng một frame `000000` … `000004`, và tạo file `results/data_health.csv`.

### Bước 5. Viết phần còn thiếu của phép chiếu (checkpoint CP2)

Mở `starter/projection.py` và viết code cho 2 hàm có đánh dấu `TODO(CP2)`: `velo_to_cam` và `cam_to_image`. Docstring của mỗi hàm đã mô tả từng bước cần làm. Sau đó chạy:

```bash
python -m starter.projection --data-root data/synthetic --frame 000000
python -m starter.projection --data-root data/kitti_mini --frame 000011
python -m starter.projection --data-root data/nuscenes_mini_subset --frame scene-0103_010
```

Kết quả đúng: mỗi lệnh lưu một ảnh vào `results/figures/`. Trong ảnh, điểm LiDAR nằm khớp lên xe, người, cột và mặt đường, và không có điểm nào nằm trên bầu trời.

### Bước 6. Trước khi nộp

```bash
python tools/check_submission.py
```

Kết quả đúng: mọi dòng đều là `[PASS]` và dòng cuối là `KẾT QUẢ: SẴN SÀNG NỘP`.

## 4. Lịch 2 giờ

Thời gian tính từ lúc bắt đầu phần lab, sau phần lý thuyết.

| Thời gian | Checkpoint | Việc chính | Sản phẩm phải có khi kết thúc |
|---|---|---|---|
| Trước buổi | CP0 | Fork repo đề bài, cài môi trường, kiểm tra dữ liệu | Bản fork `<HoVaTen>-<MSSV>-Track4-Day21` đã clone, `data_health` chạy được |
| 0:00 – 0:15 | CP1 | Chọn topic và dataset, viết câu claim cần chứng minh | Mục 1 của `report/REPORT.md` có claim nháp |
| 0:15 – 0:50 | CP2 | Viết TODO projection, chạy demo đầu tiên của topic | Ảnh demo đầu tiên trong `results/figures/` |
| 0:50 – 1:25 | CP3 | Chạy thí nghiệm chính với ít nhất 3 mức | File CSV kết quả + 1 biểu đồ hoặc bảng |
| 1:25 – 1:45 | CP4 | Tìm và phân tích failure case | Ảnh `results/figures/fail_*.png` + giải thích trong REPORT |
| 1:45 – 2:00 | CP5 | Hoàn thiện REPORT, chạy `check_submission`, push | REPORT đủ 6 mục, repo đã push |
| 2:00 – 2:20 | CP6 | Giảng viên gọi ngẫu nhiên khoảng 5 học viên, mỗi người trình bày 3 phút + 1 phút hỏi đáp | Phần trình bày |

Mỗi checkpoint ghi rõ cần làm gì, cần hiểu gì và cách tự kiểm tra trong [CHECKPOINTS.md](CHECKPOINTS.md).

## 5. Sáu topic (mỗi học viên chọn 1)

| Topic | Tên | Nội dung chính | Độ khó | Cần GPU? |
|---|---|---|---|---|
| A | Kiểm tra calibration LiDAR-camera bằng projection | Chiếu điểm lên ảnh, cố tình làm lệch calibration, đo độ lệch | Dễ | Không |
| B | Chạy model phát hiện vật thể 3D có sẵn | Chạy PointPillars hoặc CenterPoint đã train sẵn, đọc config, đo tốc độ, tìm lỗi | Khó | Có |
| C | Stress test khi dữ liệu cảm biến bị suy giảm | Bỏ bớt điểm, thêm nhiễu, giả lập mưa hoặc chuyển động, đo ảnh hưởng | Trung bình (không model) đến Khó (có model) | Không bắt buộc |
| D | Phát hiện vật cản cho robot/drone | Lọc mặt đất, gom cụm điểm thành vật cản, không dùng deep learning | Trung bình | Không |
| E | Dashboard sức khoẻ dữ liệu | Thống kê và cảnh báo frame có dữ liệu bất thường | Dễ | Không |
| F | Hỗ trợ gán nhãn bằng LiDAR | Dùng box 3D để tạo hoặc kiểm tra box 2D trên ảnh | Trung bình | Không |

Yêu cầu chi tiết của từng topic theo 3 mức Basic, Good, Advanced, kèm bằng chứng cần nộp và câu hỏi thuyết trình, nằm trong [TOPICS.md](TOPICS.md).

## 6. Cấu trúc repo

```
<HoVaTen>-<MSSV>-Track4-Day21/
├── README.md               # file này: tổng quan và cách bắt đầu
├── TOPICS.md               # yêu cầu chi tiết của 6 topic
├── CHECKPOINTS.md          # CP0–CP6: cần làm gì, sản phẩm, cách tự kiểm tra
├── RUBRIC.md               # thang điểm 100 + bonus tối đa 10 + điều kiện mất điểm
├── SUBMISSION.md           # nộp gì, đặt tên thế nào, nộp ở đâu, deadline
├── RULES.md                # quy định: dùng AI, hợp tác, nộp muộn, bảo mật
├── requirements.txt        # thư viện Python cần cài
├── starter/                # code khởi đầu do giảng viên cung cấp
│   ├── datasets.py         #   đọc KITTI và nuScenes theo cùng một cách (đã viết xong)
│   ├── kitti_io.py         #   đọc file KITTI: velodyne, calib, ảnh, label (đã viết xong)
│   ├── nuscenes_io.py      #   đọc nuScenes và chuyển sang cùng cấu trúc với KITTI (đã viết xong)
│   ├── projection.py       #   chiếu điểm lên ảnh, vẽ overlay, làm lệch calibration (CÓ 2 HÀM TODO)
│   ├── data_health.py      #   thống kê point cloud ra CSV (đã viết xong; topic E mở rộng file này)
│   └── perturb.py          #   các phép làm suy giảm dữ liệu cho topic C (đã viết xong)
├── data/
│   ├── README.md           # mô tả dữ liệu, định dạng, hệ trục, cách đọc trong code
│   ├── synthetic/          # 5 frame dữ liệu mẫu (2 MB)
│   ├── kitti_mini/         # 20 frame KITTI 3D Object (55 MB)
│   └── nuscenes_mini_subset/  # 2 scene nuScenes v1.0-mini (74 MB)
├── src/                    # BẠN VIẾT: toàn bộ code bạn tự viết đặt ở đây
├── results/                # BẠN TẠO: file CSV số liệu, thư mục figures/ chứa ảnh
├── report/
│   └── REPORT.md           # BẠN ĐIỀN: thông tin học viên + báo cáo dạng chữ, 6 mục
└── tools/
    ├── check_submission.py       # kiểm tra bài trước khi nộp
    ├── verify_data.py            # kiểm tra dữ liệu trong data/ có đủ và không hỏng
    ├── download_kitti_subset.py  # TUỲ CHỌN: tải thêm frame KITTI (xem data/README.md mục 4)
    ├── download_nuscenes_subset.py  # TUỲ CHỌN: tải thêm scene nuScenes (xem data/README.md mục 4)
    └── remote_zip.py             # thư viện phụ cho script tải KITTI
```

Quy tắc: **chỉ sửa `starter/projection.py` tại 2 hàm TODO**. Mọi code khác bạn tự viết đặt trong `src/`, để giảng viên phân biệt được phần bạn tự làm.

## 7. Tài liệu tham khảo

- **Slide bài học:** `adas_day6_3d_pointclouds_lidar_camera.pdf`. Phần mini project là Section 05, slide 32–39.
- **Tài liệu của bài lab:** [CHECKPOINTS.md](CHECKPOINTS.md) · [TOPICS.md](TOPICS.md) · [RUBRIC.md](RUBRIC.md) · [SUBMISSION.md](SUBMISSION.md) · [RULES.md](RULES.md) · [data/README.md](data/README.md)
- **Tài liệu kỹ thuật:**
  - [OpenCV calib3d](https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html): mô hình camera pinhole và phép chiếu
  - [KITTI 3D Object benchmark](https://www.cvlibs.net/datasets/kitti/eval_object.php?obj_benchmark=3d): tải *object development kit*, file `readme.txt` bên trong mô tả định dạng label và calib
  - [nuScenes data format](https://www.nuscenes.org/nuscenes#data-format): ý nghĩa 13 bảng metadata
  - [MMDetection3D](https://github.com/open-mmlab/mmdetection3d) và [OpenPCDet](https://github.com/open-mmlab/OpenPCDet): thư viện model 3D cho topic B, C
  - [Open3D point cloud tutorial](https://www.open3d.org/docs/release/tutorial/geometry/pointcloud.html): downsample, tách mặt phẳng, DBSCAN cho topic D

## 8. Khi gặp khó khăn trong giờ lab

- Nếu kẹt ở cùng một lỗi **quá 10 phút**, hãy giơ tay gọi lab coach hoặc nhắn vào kênh chat chung của lớp.
- Khi hỏi, chuẩn bị sẵn 3 thứ để được hỗ trợ nhanh:
  1. Lệnh đã chạy.
  2. Toàn bộ thông báo lỗi. Copy nguyên văn, không chụp một phần.
  3. Những gì đã thử.
