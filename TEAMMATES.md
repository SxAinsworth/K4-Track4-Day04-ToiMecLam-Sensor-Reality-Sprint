# Thành viên nhóm · T2 LiDAR corruption benchmark

| Thành viên | Role | Việc trong lab |
|---|---|---|
| Tạ Quang Dũng | Research & Report lead | Tìm tài liệu, ghi benchmark, trình bày |
| Trương Thị Lan Anh | Engineering & Benchmark lead | Chạy code, ghi benchmark, trình bày |

## Tạ Quang Dũng: Research & Report lead

**Đã làm:**
- **Tìm và đọc nguồn (Bước 2):** đọc Dong et al. CVPR 2023 và repo `thu-ml/3D_Corruptions_AD` (đọc cả code `LiDAR_corruptions.py` để lấy tham số severity), Robo3D (ICCV 2023), và Hahner et al. ICCV 2021 cho mô hình fog. Ghi input/output, dataset, metric, yêu cầu chạy và limitation do tác giả nêu vào [SOURCES.md](SOURCES.md).
- **Chốt đường chạy:** lý giải vì sao không chạy được demo gốc (dataset hàng trăm GB, MMDet3D, GPU) và chọn benchmark mô phỏng. Ghi rõ metric nào là proxy.
- **Đối chiếu tham số:** so tham số corruption của repo gốc với của nhóm (fog α dùng giống hệt; gaussian và dropout mở rộng thêm).
- **Phân tích failure case (Bước 5):** chọn motion smear là silent failure. Tách riêng ba loại câu: "Nhóm quan sát được", "Paper cho biết", "Giả thuyết". Viết limitation của benchmark.
- **Báo cáo (Bước 6):** viết [REPORT.md](REPORT.md) theo 5 mục, gồm bảng đối chiếu claim, engineering decision và trade-off ADAS/robot/drone.
- **Pitch:** trình bày Problem → Method → Failure case → Engineering decision.

## Trương Thị Lan Anh: Engineering & Benchmark lead

**Đã làm:**
- **Chốt claim (Bước 1):** viết 5 claim C1–C5 kèm metric, đơn vị và dự đoán trong [PLAN.md](PLAN.md).
- **Simulator** (`lidar_bench/sim.py`): LiDAR ray-cast 32 beam, 10 Hz, scene đường có 15 xe, 10 người đi bộ và 2 tường, seed cố định.
- **Corruption** (`lidar_bench/corruptions.py`): dropout, gaussian noise, beam missing, packet loss, fog (suy hao + backscatter), motion smear, mỗi loại 5 mức. Thêm cải tiến motion + deskew để kiểm chứng đề xuất.
- **Detector và health score** (`lidar_bench/detect.py`): ground removal, cluster Euclid, match GT. Health score không cần GT gồm 5 thành phần.
- **Thiết kế benchmark (Bước 3):** baseline cố định, mỗi điều kiện chỉ đổi một yếu tố, định nghĩa metric trước khi chạy. Viết [DESIGN.md](DESIGN.md).
- **Chạy benchmark và ghi kết quả (Bước 4):** `run_benchmark.py` chạy 8 scene × 6 corruption × 5 mức. Xuất `results/summary.csv` (mean ± std), `metrics_per_scene.csv` và log.
- **Plot:** đường cong suy giảm (ghi tham số thật cho từng mức), recall và point density theo khoảng cách, ảnh BEV trước/sau. Tự viết hàm vẽ bằng Pillow vì máy lab chặn DLL của matplotlib và sklearn.
- **Pitch:** trình bày Benchmark và demo chạy `python run_benchmark.py`.

## Làm chung
- Review claim, kết quả và báo cáo trước khi pitch.
- Mỗi người có báo cáo hoặc slide riêng để nộp (Bước 6).
