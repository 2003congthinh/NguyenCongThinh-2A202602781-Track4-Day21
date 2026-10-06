# Sáu topic thực hành (chọn 1)

Mỗi topic có 3 mức. Mức **Basic là tối thiểu để đạt** phần "Demo chạy thật". Mức **Good** là mức mục tiêu để đạt điểm cao. Mức **Advanced** dành cho người còn thời gian, và thường đi kèm điểm bonus.

Mỗi học viên làm **1 topic** và phải nộp đủ 5 sản phẩm: **1 claim kỹ thuật · 1 bảng/plot số liệu · 1 ảnh/video demo · 1 failure case · 1 khuyến nghị triển khai**.

---

## A. LiDAR-camera projection QA

**Mục tiêu:** chứng minh calibration/projection đúng bằng overlay, rồi đo độ nhạy của nó với calibration drift.

Pipeline: `Load (image, velodyne, calib) → Project K[R|t] → Overlay màu theo depth → Perturb ±1° yaw / ±5 cm → So sánh visual + metric`

| Mức | Yêu cầu | Evidence |
|---|---|---|
| Basic | Cài đặt `velo_to_cam` + `cam_to_image`, lọc depth ≤ 0, NaN và ngoài FOV, overlay lên ảnh | 3 ảnh overlay ở 3 khoảng cách khác nhau |
| Good | Perturb extrinsic (yaw/pitch/roll 0.5–3°, translation 2–10 cm), đo mismatch | Bảng: mức perturb → % điểm inside FOV, % điểm rơi đúng vào 2D box của object, kèm ảnh lệch |
| Advanced | Thiết kế **alignment score**, ví dụ khớp depth edge với image edge (Canny) hoặc tỉ lệ điểm trong box, rồi tìm ngưỡng phát hiện drift | Plot score theo mức perturb, ngưỡng phát hiện, và 1 case score không phát hiện được |

**Câu hỏi thuyết trình:** nếu sensor bracket lệch 1° sau một va chạm nhẹ, hệ thống có tự phát hiện được không? Phát hiện ở khoảng cách nào?

**Starter:** `starter/projection.py` (`perturb_extrinsic`, `overlay_points`, `draw_box2d`).

---

## B. Chạy baseline 3D detector

**Mục tiêu:** chạy model để hiểu pipeline, chứ không chỉ để lấy screenshot.

Pipeline: `Setup MMDet3D/OpenPCDet → mini sample → Infer PointPillars/CenterPoint (checkpoint có sẵn) → Visualize 3D box + BEV → Report latency + cases`

| Mức | Yêu cầu | Evidence |
|---|---|---|
| Basic | Chạy inference bằng checkpoint có sẵn trên ≥ 5 frame và visualize box | Ảnh BEV/3D có box + lệnh chạy |
| Good | Đọc và giải thích config: `point_cloud_range`, `voxel_size`, `class_names`, `score_thr`, NMS, sweeps, test pipeline. Đo latency p50/p95, số box, score distribution, range của box | Bảng latency + histogram score + pass/fail trên 5 frame |
| Advanced | So sánh 2 model hoặc 2 config (ví dụ PointPillars với CenterPoint, hoặc 2 `score_thr`) | Bảng so sánh + failure riêng của từng bên |

**Failure cần tìm:** bỏ sót pedestrian/cyclist, false positive sát ego, yaw sai, vật xa bị drop, detector chậm.

**Lưu ý:** **không train**. Chỉ dùng checkpoint có sẵn. Tham khảo `demo/pcd_demo.py` của MMDetection3D hoặc `tools/demo.py` của OpenPCDet.

---

## C. Sensor degradation stress test

**Mục tiêu:** cố tình làm dữ liệu xấu đi để hiểu giới hạn của detector hoặc pipeline.

| Perturbation | Cách làm nhanh (`starter/perturb.py`) | Kỳ vọng quan sát |
|---|---|---|
| Random dropout | `random_dropout(keep_ratio=0.9/0.7/0.5/0.3)` | score giảm, miss vật nhỏ/xa |
| Range dropout | `range_dropout(max_range_m=30/50)` | range recall tụt |
| Sector / beam dropout | `sector_dropout`, `beam_dropout` | mất vật trong vùng bị che |
| Gaussian noise | `gaussian_noise(sigma_xyz_m=0.02/0.05/0.1)` | box jitter, yaw sai |
| Calibration drift | `projection.perturb_extrinsic` | projection mismatch |
| Motion smear | `motion_smear(ego_speed_mps=10/20/30)` | object bị kéo dài, box lệch |

| Mức | Yêu cầu | Evidence |
|---|---|---|
| Basic | ≥ 2 loại perturbation × ≥ 3 mức. Đo một chỉ số không cần model: số điểm trên object (đếm điểm trong 3D box GT) và % điểm trong FOV | Đồ thị mức degradation → metric |
| Good | Có model (nối với topic B): đo score, số box và recall theo mức degradation | Đồ thị + 1 failure scene giải thích dễ hiểu |
| Advanced | Đề xuất một sensor health metric phát hiện được degradation trước khi model fail | Plot health metric so với model metric |

Không có GPU vẫn làm được mức Basic của topic C, vì mức này chỉ đo trên dữ liệu, không cần chạy model.

---

## D. Robot/drone obstacle

**Mục tiêu:** xây pipeline phát hiện vật cản đơn giản, không dùng deep learning, và hiểu tham số filter ảnh hưởng thế nào tới obstacle ở gần.

| Mức | Yêu cầu | Evidence |
|---|---|---|
| Basic | Voxel downsample → ground removal (RANSAC plane, `open3d.segment_plane`) → clustering (DBSCAN) → bounding box mỗi cluster | Ảnh trước/sau mỗi bước + số cluster |
| Good | Sweep 2 tham số (ví dụ `voxel_size` và `distance_threshold` hoặc `eps`), đo số cluster, kích thước, khoảng cách tới vật gần nhất và thời gian chạy | Bảng tham số → kết quả + latency |
| Advanced | Dựng occupancy grid 2D/BEV, hoặc so khớp cluster với GT box trong `label_2` | Ảnh BEV occupancy hoặc bảng precision/recall theo cluster |

**Câu hỏi thuyết trình:** tham số nào làm **mất vật thấp sát đất** (người ngồi, xe đẩy, pallet)? Robot trong kho cần chọn thế nào?

---

## E. Data health dashboard

**Mục tiêu:** từ log, tự động chỉ ra frame nào đáng tin, frame nào cần label/retrain và frame nào nên loại bỏ.

| Mức | Yêu cầu | Evidence |
|---|---|---|
| Basic | Mở rộng `starter/data_health.py`: histogram range, intensity, points/frame, invalid ratio | Dashboard (ảnh matplotlib nhiều subplot hoặc notebook) + CSV |
| Good | Thêm density theo azimuth/elevation, time gap từ `timestamps.txt`, và quy tắc cảnh báo (rule + ngưỡng) | Bảng frame → cờ cảnh báo, kèm lý do |
| Advanced | Chạy dashboard trên `data/kitti_mini` và `data/nuscenes_mini_subset`, so sánh hai sensor (64 beam của KITTI và 32 beam của nuScenes) và hai điều kiện ngày/đêm. Đề xuất một "frame score" để xếp hạng frame nào nên ưu tiên đưa đi gán nhãn | Ranking frame + ảnh minh hoạ frame bị gắn cờ |

**Gợi ý:** `data/synthetic` có một số lỗi cài sẵn. Dashboard tốt phải tự tìm ra chúng.

---

## F. Auto-label support

**Mục tiêu:** dùng 3D box hoặc điểm LiDAR để kiểm tra (QA) hoặc gợi ý 2D label cho camera.

| Mức | Yêu cầu | Evidence |
|---|---|---|
| Basic | Chiếu 8 góc 3D box (`box3d_corners_cam`) lên ảnh → 2D box gợi ý, so với 2D box trong label bằng IoU | Ảnh overlay 2 box + bảng IoU |
| Good | Dùng điểm LiDAR nằm trong 3D box để tạo 2D box chặt hơn (min/max của điểm đã chiếu). So sánh 2 cách | Bảng IoU của 2 cách × object |
| Advanced | Perturb calibration hoặc giả lập occlusion, rồi tìm ngưỡng IoU để tự động gắn cờ "label cần review" | Plot IoU theo perturb + failure case |

**Câu hỏi thuyết trình:** khi nào label support từ LiDAR **sai**, do calibration, occlusion, truncation ở rìa ảnh hay timestamp?
