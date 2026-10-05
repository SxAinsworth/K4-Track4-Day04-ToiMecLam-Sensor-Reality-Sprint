# Bước 1 · Chốt bài toán, claim và phân công

## Chủ đề

| Mục | Lựa chọn |
|---|---|
| Chủ đề | **T2 · LiDAR corruption benchmark** |
| Nền tảng | **Xe ADAS** (đường thành phố/cao tốc, 18–108 km/h) |
| Tính năng bị ảnh hưởng | Phát hiện vật cản 3D (xe, người đi bộ) dùng cho phanh khẩn cấp và giữ khoảng cách |
| Sensor | LiDAR quay 32 beam, 10 Hz |
| Failure case kiểm tra | Fog, point dropout, Gaussian noise, missing beams, packet loss, motion distortion (không deskew) |

**Baseline:** scan LiDAR sạch. **Degraded condition:** cùng scan đó, áp đúng một loại lỗi ở một mức tham số. Mọi điều kiện dùng chung scene, chung detector và chung cách tính metric (xem [DESIGN.md](DESIGN.md)).

## Claim, viết **trước khi chạy** (giả thuyết, chưa phải kết luận)

| # | Claim: điều kiện thay đổi → dấu hiệu dự đoán | Metric (đơn vị) | Dự đoán | So baseline thế nào |
|---|---|---|---|---|
| C1 | Khi fog dày lên (α tăng từ 0.005 lên 0.06 1/m), điểm ở xa mất trước nên recall vùng > 40 m giảm trước vùng gần | Points/object theo khoảng cách (điểm); recall theo bin 0–20/20–40/40–60 m (0–1) | Giảm, xa giảm nhanh hơn gần | Hiệu và tỉ lệ so với clean, theo từng bin |
| C2 | Khi tỉ lệ dropout hoặc beam chết tăng, point density giảm tuyến tính nhưng recall chỉ giảm khi object còn quá ít điểm | Object-point ratio (0–1); object recall (0–1) | Density giảm đều, recall giảm muộn hơn | Đường cong theo 5 mức |
| C3 | Khi σ nhiễu tăng, mặt đất bị "nổi" lên nên detector sinh ghost | FP cluster/scan | Tăng | So với 1.3 FP/scan của clean |
| C4 | Khi xe chạy nhanh hơn mà không deskew, object bị lệch hoặc xé đôi nên recall giảm, trong khi **số điểm không đổi** | Object recall (0–1); health score (0–1) | Recall giảm, health **không** đổi | So với clean; verdict `SILENT FAILURE` nếu recall giảm > 10% mà health ≥ 0.8 |
| C5 | Một health score không cần GT phát hiện được lỗi trước khi recall giảm > 10% | Health score (0–1, flag < 0.8) | Flag với C1–C3, **không** flag với C4 | Bảng verdict caught / silent / false alarm |

**Proxy:** chưa có nhãn thật và chưa có detector học sâu. Object recall của detector clustering trên dữ liệu tổng hợp **thay thế cho** mAP/recall của detector thật. Nó cho biết xu hướng và loại lỗi nào nguy hiểm, nhưng không cho biết mAP thật giảm bao nhiêu.

Kết quả đối chiếu claim nằm ở [REPORT.md](REPORT.md).

## Phân công (nhóm 2 thành viên)

| Thành viên | Tìm tài liệu | Chạy code | Ghi benchmark | Trình bày | Phần việc cụ thể |
|---|:-:|:-:|:-:|:-:|---|
| Tạ Quang Dũng | ✅ | | ✅ | ✅ | Đọc Dong et al., Robo3D, Hahner; viết [SOURCES.md](SOURCES.md), đối chiếu tham số nguồn với nhóm. Phân tích failure case, viết [REPORT.md](REPORT.md). Pitch phần Problem, Method, Failure, Decision. |
| Trương Thị Lan Anh | | ✅ | ✅ | ✅ | Simulator + corruption + detector + health score (`lidar_bench/`). Thiết kế benchmark ([DESIGN.md](DESIGN.md)), chạy `run_benchmark.py`, điền bảng kết quả, plot. Pitch phần Benchmark và demo. |


