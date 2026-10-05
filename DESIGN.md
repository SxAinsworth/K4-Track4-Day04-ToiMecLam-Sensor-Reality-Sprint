# Bước 3 · Thiết kế benchmark có đối chứng

## Dữ liệu và cấu hình baseline (cố định cho mọi điều kiện)

| Thành phần | Giá trị |
|---|---|
| Dữ liệu | **Tổng hợp.** 8 scene, seed 0–7 (`numpy.random.default_rng(seed)`). Đường thẳng, 2 tường ở y = ±16 m, 15 xe (4.5×1.9×1.6 m) và 10 người đi bộ (0.7×0.7×1.8 m) đặt ngẫu nhiên trong |y| < 12 m, khoảng cách 5–60 m. |
| Sensor | LiDAR quay 32 beam, FOV dọc −25°..+15°, độ phân giải azimuth 0.4° (900 cột), 10 Hz, tầm tối đa 80 m, nhiễu range σ = 1 cm, gắn cao 1.8 m. ~20 000 điểm/scan. |
| GT | Object có ≥ 5 điểm trong scan clean, trung bình ~21 object/scene (171 object tổng cộng) |
| Pipeline | Bỏ điểm z < mặt đất + 0.25 m và điểm < 1 m → cluster Euclid bán kính 0.8 m, ≥ 3 điểm → bỏ cluster có kích thước xy > 7 m hoặc cao > 3 m → match với GT theo khoảng cách tâm xy < 2.5 m (xe) / 1.0 m (người) |
| Health baseline | Trung vị của số điểm, số điểm từng beam, số điểm từng sector 10° và độ nhám mặt đất trên 8 scan clean |

**Mỗi điều kiện lỗi chỉ thay đúng một yếu tố.** Cùng scan clean, cùng detector, cùng ngưỡng. Seed của corruption là `1000·scene + severity`.

## Điều kiện và tham số thực tế

| Điều kiện | Tham số thay đổi | Mức 1 → 5 | Mô phỏng hiện tượng gì |
|---|---|---|---|
| Baseline | không có | không có | LiDAR sạch |
| dropout | xác suất bỏ mỗi điểm | 0.2 / 0.4 / 0.6 / 0.8 / 0.9 | Kính bẩn, vật phản xạ thấp |
| gaussian_noise | σ nhiễu xyz (m) | 0.02 / 0.05 / 0.10 / 0.15 / 0.25 | Rung, nhiễu, sensor lão hoá |
| beam_missing | tỉ lệ beam chết | 0.2 / 0.4 / 0.6 / 0.75 / 0.875 | Hỏng laser/receiver |
| packet_loss | tỉ lệ gói UDP mất (mỗi gói 4.8°) | 0.05 / 0.1 / 0.2 / 0.3 / 0.5 | Ethernet quá tải, driver drop |
| fog | α (1/m), MOR ≈ 3/α | 0.005 / 0.01 / 0.02 / 0.03 / 0.06 (≈600 / 300 / 150 / 100 / 50 m) | Sương mù: suy hao + backscatter |
| motion_smear | tốc độ ego (m/s), **không** bù | 5 / 10 / 15 / 20 / 30 (18–108 km/h) | Thiếu deskew, sai timestamp |
| **motion+deskew** (cải tiến) | như trên, deskew bằng odometry sai số 5% | 5 / 10 / 15 / 20 / 30 | Kiểm chứng đề xuất ở Bước 5 |

## Metric, định nghĩa trước khi chạy

| Metric | Công thức | Đơn vị | Tốt khi | Loại | Cho phép kết luận gì |
|---|---|---|---|---|---|
| **Object recall** | số GT match được / số GT | 0–1 | cao | Chất lượng thuật toán (**proxy**) | Corruption làm detector *clustering* mất object. **Không** suy ra mAP của detector học sâu. |
| Recall theo khoảng cách | recall trong 0–20 / 20–40 / 40–60 m | 0–1 | cao | Thuật toán (proxy) | Vùng nào bị mù trước |
| FP clusters | cluster hợp lệ không gần GT nào | cluster/scan | thấp | Thuật toán (proxy) | Ghost, hệ quả là phanh oan |
| Points per object | số điểm rơi trên GT / số GT, theo khoảng cách | điểm/object | cao | **Sensor health** (point density) | Dữ liệu đầu vào thưa đi bao nhiêu |
| Object-point ratio | số điểm trên GT khi lỗi / khi clean | 0–1 | cao | Sensor health | Như trên, gộp mọi khoảng cách |
| **Health score** | min của 5 thành phần: return rate, beam coverage, sector coverage, near clutter, ground flatness | 0–1, flag < 0.8 | cao khi sensor tốt | Sensor health, **không cần GT** | Hệ thống có tự biết mình đang hỏng không |
| Verdict | recall giảm tương đối > 10% và health flag (≥ 50% scene) → `caught`; giảm mà không flag → `SILENT FAILURE`; flag mà không giảm → `false alarm` | nhãn | không có | Đánh giá monitor | Loại lỗi nào monitor bỏ sót |

Mỗi metric báo **trung bình ± độ lệch chuẩn qua 8 scene** (`summary.csv`, cột `*_std`).

## Bằng chứng tái hiện

| Bằng chứng | File |
|---|---|
| Lệnh | `python run_benchmark.py` (mặc định `--scenes 8 --out results`) |
| Log stdout | `results/run_log.txt` |
| Số liệu thô / tổng hợp | `results/metrics_per_scene.csv`, `results/summary.csv` |
| Plot mức lỗi so với metric | `results/degradation_curve.png` (tham số thật ghi dưới plot) |
| Theo khoảng cách | `results/recall_by_distance.png` |
| Ảnh trước/sau | `results/bev_before_after.png` |
| Môi trường | Windows 11, Python 3.11.9, numpy 2.4.6, scipy 1.17.1, Pillow 12.3.0, CPU, ~15 s |
