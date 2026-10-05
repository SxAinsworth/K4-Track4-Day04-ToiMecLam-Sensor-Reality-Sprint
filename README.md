# K4-Track4-Day04 · Sensor Reality Sprint · T2 LiDAR corruption benchmark

Benchmark mô phỏng nhỏ: LiDAR 32 beam quay 360° trên xe ADAS → 6 loại corruption × 5 mức severity
→ detector clustering cổ điển → đo recall, false positive, mật độ điểm theo khoảng cách, cùng một
**health score không cần GT** để xem sensor có tự phát hiện mình đang bị suy giảm hay không.

| Bước | File |
|---|---|
| 1 · Chủ đề, claim, phân công | [PLAN.md](PLAN.md) |
| 2 · Nguồn và đường chạy | [SOURCES.md](SOURCES.md) |
| 3 · Thiết kế benchmark | [DESIGN.md](DESIGN.md) |
| 4 · Kết quả | `results/` |
| 5–6 · Failure case, báo cáo 1 trang | [REPORT.md](REPORT.md) |

## Chạy

```bash
pip install -r requirements.txt
python run_benchmark.py            # 8 scene, ~15 s trên CPU
python run_benchmark.py --scenes 20 --out results_20
```

Chỉ dùng numpy + scipy + Pillow. Không dùng matplotlib/sklearn vì máy lab bị Windows Application
Control chặn DLL của hai thư viện này: plot vẽ bằng PIL, clustering dùng KD-tree + connected components.

## Cấu trúc

| File | Nội dung |
|---|---|
| `lidar_bench/sim.py` | Ray-cast LiDAR 32 beam, FOV dọc -25°..+15°, azimuth 0.4°, 10 Hz, tầm tối đa 80 m. Scene: đường có 15 xe + 10 người đi bộ, 2 bức tường hai bên. |
| `lidar_bench/corruptions.py` | dropout, gaussian_noise, beam_missing, packet_loss, fog (suy hao 2 chiều + backscatter), motion_smear (không bù chuyển động). `FIXES`: motion+deskew, là cải tiến được kiểm chứng cho failure case. |
| `lidar_bench/detect.py` | Lọc mặt đất → cluster Euclid 0.8 m → lọc theo kích thước → match với GT. Health score = component tệ nhất trong return rate, beam coverage, sector coverage, near clutter, ground flatness. |
| `lidar_bench/plots.py` | Vẽ line chart và BEV bằng PIL. |
| `run_benchmark.py` | Chạy toàn bộ benchmark, ghi CSV và PNG vào `results/`. |

## Output (`results/`)

- `summary.csv`: trung bình (và `*_std` qua các scene) theo (corruption, severity), kèm verdict: `ok` / `caught` / `false alarm` / `SILENT FAILURE`
- `metrics_per_scene.csv`: số liệu thô từng scene
- `degradation_curve.png`: recall, số FP cluster và health score theo severity
- `recall_by_distance.png`: recall và số điểm/object theo khoảng cách (severity 3)
- `bev_before_after.png`: ảnh BEV clean / fog / beam missing / motion smear. GT xanh lá = detect được, đỏ = bị miss, chấm hồng = ghost do sương mù
- `run_log.txt`: log stdout của lần chạy đã commit
