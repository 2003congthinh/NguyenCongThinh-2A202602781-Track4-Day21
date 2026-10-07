# Dữ liệu cho Day 6 Lab

Toàn bộ dữ liệu cần cho bài lab **đã có sẵn trong repo**. Sau khi clone repo xong là dùng được ngay, không cần tải thêm gì.

Bài lab dùng **2 dataset public có cả camera và LiDAR**: KITTI 3D Object và nuScenes v1.0-mini. Mỗi dataset chỉ lấy một phần nhỏ, vừa đủ cho mini project 2 giờ. Ngoài ra có một bộ dữ liệu tổng hợp nhỏ để chạy thử code.

| Thư mục | Nguồn | Nội dung | Dung lượng |
|---|---|---|---|
| `data/synthetic/` | Tự sinh, định dạng KITTI | 5 frame, scene đơn giản: mặt đường, tường, cột, 1 xe, 1 người đi bộ | 2 MB |
| `data/kitti_mini/` | KITTI 3D Object | 20 frame: LiDAR + ảnh camera trái + calibration + label 3D | 55 MB |
| `data/nuscenes_mini_subset/` | nuScenes v1.0-mini | 2 scene, 80 keyframe: LiDAR (LIDAR_TOP) + camera trước (CAM_FRONT) + metadata + label 3D | 74 MB |

Gợi ý chọn dữ liệu:

- **Viết và debug code:** dùng `data/synthetic/`. Dữ liệu nhỏ, scene đơn giản, nhìn ảnh overlay là biết đúng hay sai ngay.
- **Thí nghiệm chính và kết quả đưa vào báo cáo:** dùng `data/kitti_mini/` hoặc `data/nuscenes_mini_subset/`, hoặc cả hai để so sánh.

---

## 1. Kiểm tra dữ liệu sau khi clone

Nếu clone bị ngắt giữa chừng hoặc nghi ngờ file bị hỏng, chạy:

```bash
python tools/verify_data.py --data-root data/kitti_mini
python tools/verify_data.py --data-root data/nuscenes_mini_subset
```

- **Kết quả đúng:** mỗi lệnh in ra `[PASS] Dữ liệu đầy đủ, dùng được.`
- **Có dòng `[THIẾU]` hoặc `[HỎNG]`:** chạy `git checkout -- data/` để lấy lại bản gốc từ repo, rồi chạy lại lệnh kiểm tra.

Sau đó chạy thử một lệnh đọc dữ liệu để chắc mọi thứ hoạt động:

```bash
python -m starter.data_health --data-root data/kitti_mini --out results/data_health_kitti.csv
python -m starter.data_health --data-root data/nuscenes_mini_subset --out results/data_health_nusc.csv
```

Kết quả đúng: lệnh thứ nhất in ra 20 dòng (frame `000001` … `000061`), lệnh thứ hai in ra 80 dòng (`scene-0103_000` … `scene-1094_039`).

---

## 2. Đọc dữ liệu trong code

Mọi code trong `starter/` đọc được cả 3 thư mục theo cùng một cách, thông qua `starter/datasets.py`:

```python
from starter.datasets import list_frames, load_frame

frames = list_frames("data/nuscenes_mini_subset")   # ['scene-0103_000', 'scene-0103_001', ...]
fr = load_frame("data/nuscenes_mini_subset", frames[10])

fr["points"]   # numpy (N, 4) float32: x, y, z, intensity (thang 0–1)
fr["calib"]    # KittiCalib: P2 (3x4), R0_rect (3x3), Tr_velo_to_cam (3x4)
fr["image"]    # ảnh BGR uint8 (H, W, 3)
fr["labels"]   # list[KittiObject]: 3D box trong camera frame + 2D box trên ảnh
```

Ví dụ frame id cho từng thư mục:

- `data/synthetic`: `000000` đến `000004`
- `data/kitti_mini`: `000001`, `000011`, `000049`… (in đủ danh sách bằng `list_frames`)
- `data/nuscenes_mini_subset`: `scene-0103_000` đến `scene-0103_039`, và `scene-1094_000` đến `scene-1094_039`

---

## 3. Cấu trúc và định dạng từng dataset

### 3.1 `data/synthetic/` và `data/kitti_mini/` (định dạng KITTI)

```
training/
├── velodyne/<id>.bin   # float32, mỗi điểm 4 số: x, y, z, reflectance
├── calib/<id>.txt      # P0..P3 (3x4), R0_rect (3x3), Tr_velo_to_cam (3x4), Tr_imu_to_velo
├── image_2/<id>.png    # ảnh camera trái màu, khoảng 1242 x 375
└── label_2/<id>.txt    # mỗi dòng 1 object: type, truncated, occluded, alpha, bbox 2D (4 số),
                        # dimensions h w l (m), location x y z (m, đáy box, camera frame), rotation_y
```

- **Hệ trục LiDAR:** x hướng về phía trước xe, y sang trái, z lên trên.
- **Hệ trục camera:** x sang phải, y xuống dưới, z hướng về phía trước.
- **Chuỗi chiếu điểm lên ảnh:** `P2 · R0_rect · Tr_velo_to_cam · [x y z 1]ᵀ`.
- **20 frame của `kitti_mini`** được chọn để có đủ các tình huống khó, mỗi nhóm frame ứng với một tình huống:

  | Tình huống | Frame |
  |---|---|
  | Nhiều người đi bộ | 000011, 000015, 000043, 000048 |
  | Có cyclist | 000001, 000007, 000021, 000023 |
  | Đông xe | 000008, 000010, 000032 |
  | Xe xa hơn 50 m | 000004, 000009, 000012 |
  | Vật rất gần, dưới 6 m | 000019, 000025 |
  | Nhiều vật bị che khuất | 000016, 000049 |
  | Có van/truck | 000031, 000061 |

- `data/synthetic/` có thêm file `training/timestamps.txt` ghi thời điểm của từng frame, tính bằng giây. KITTI 3D Object không phát hành timestamp, nên `kitti_mini` không có file này.

### 3.2 `data/nuscenes_mini_subset/` (định dạng nuScenes, đã lọc)

```
v1.0-mini/*.json              # 13 bảng metadata (scene, sample, sample_data, ego_pose, calibrated_sensor, ...),
                              # đã lọc chỉ còn 2 scene bên dưới
samples/LIDAR_TOP/*.pcd.bin   # float32, mỗi điểm 5 số: x, y, z, intensity (0–255), ring
samples/CAM_FRONT/*.jpg       # ảnh camera trước, 1600 x 900
```

- **2 scene**, mỗi scene 40 keyframe cách nhau 0.5 giây:
  - `scene-0103`: ban ngày, nhiều người đi bộ bên phải, có cyclist.
  - `scene-1094`: ban đêm sau mưa, nhiều người đi bộ, có người băng qua đường sai luật.
- **Hệ trục LiDAR khác KITTI:** x hướng **sang phải**, y hướng **về phía trước**, z lên trên. Vì vậy trong `data_health.py`, azimuth 0° của nuScenes là phía bên phải xe, không phải phía trước.
- **LiDAR 32 beam** (KITTI là 64 beam), nên mỗi frame chỉ có 34 720 điểm, thưa hơn KITTI khoảng 3 lần.
- **LiDAR và camera chụp ở hai thời điểm khác nhau**, lệch khoảng vài chục ms. `load_frame` mặc định đã bù chuyển động của xe trong khoảng lệch đó.
  - Để tắt bù và quan sát lỗi đồng bộ thời gian: truyền `use_ego_motion=False` khi gọi `load_frame`, hoặc thêm `--ignore-ego-motion` khi chạy `starter.projection`.
  - Độ lệch thời gian của từng frame có trong `fr["timestamp_camera_us"] - fr["timestamp_lidar_us"]`, đơn vị micro giây.
- **Label** được đổi sang `KittiObject`, tên class gọn hơn, ví dụ `Car`, `Pedestrian`, `Bicycle`, `TrafficCone`. Bảng ánh xạ nằm ở `CATEGORY_MAP` trong `starter/nuscenes_io.py`.
- Nếu muốn, bạn có thể đọc thư mục này bằng thư viện chính thức `nuscenes-devkit`: `NuScenes(version="v1.0-mini", dataroot="data/nuscenes_mini_subset")`. Việc này không bắt buộc.

---

## 4. Tuỳ chọn: lấy thêm dữ liệu

**Không cần làm mục này để hoàn thành bài lab.** Chỉ dùng khi bạn thật sự cần thêm dữ liệu, và **chạy ở nhà, không chạy trong giờ lab** để tránh làm quá tải mạng của lớp.

| Muốn | Lệnh (chạy từ gốc repo) | Lượng tải qua mạng |
|---|---|---|
| Thêm frame KITTI khác (id từ `000000` đến `007480`) | `python tools/download_kitti_subset.py --frames 000100 000200 --out data/kitti_extra` | khoảng 3 MB mỗi frame |
| Xem mô tả 10 scene có trong nuScenes mini | `python tools/download_nuscenes_subset.py --list-scenes` | khoảng 10 MB |
| Lấy thêm scene nuScenes khác | `python tools/download_nuscenes_subset.py --scenes scene-0553 scene-1100 --out data/nuscenes_extra` | 0.6–4 GB, tuỳ vị trí scene trong file gốc |
| Topic B: đủ 6 camera + LiDAR sweeps 20 Hz cho MMDetection3D/CenterPoint | `python tools/download_nuscenes_subset.py --profile full --out data/nuscenes_full` | gần hết 4.2 GB. Ghi ra đĩa khoảng 0.8 GB (ước tính) |

Lưu ý khi lấy thêm dữ liệu:

- Luôn dùng `--out` tới một **thư mục mới** như ví dụ trên, để không ghi đè dữ liệu gốc của đề bài.
- **Không commit** các thư mục dữ liệu bạn tự tải thêm, vì chúng làm repo nặng. Hãy thêm tên thư mục đó vào file `.gitignore` trong repo của bạn, ví dụ thêm dòng `data/kitti_extra/`.

---

## 5. Bản quyền

- KITTI phát hành theo giấy phép **CC BY-NC-SA 3.0**, nuScenes theo **CC BY-NC-SA 4.0**. Cả hai **chỉ được dùng cho học tập và nghiên cứu phi thương mại**.
- Khi đưa ảnh từ dataset vào báo cáo, ghi nguồn "KITTI Vision Benchmark Suite" hoặc "nuScenes (Motional)".