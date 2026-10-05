# Bước 2 · Ghi chép nguồn và đường chạy

> Mục này chỉ ghi **điều nguồn nói**. Số liệu nhóm tự đo nằm ở [REPORT.md](REPORT.md) và `results/`.
> Ngày đọc: 2026-10-05.

## Nguồn chính: Dong et al., CVPR 2023 (S5 trong PDF)

| Câu hỏi | Ghi chép |
|---|---|
| **Nguồn** | *Benchmarking Robustness of 3D Object Detection to Common Corruptions in Autonomous Driving*, Y. Dong, C. Kang, J. Zhang, Z. Zhu, Y. Wang, X. Yang, H. Su, X. Wei, J. Zhu. CVPR 2023. arXiv:2303.11040 |
| **Repo** | https://github.com/thu-ml/3D_Corruptions_AD, commit `48c23f77fe82` (repo gốc `kkkcx/3D_Corruptions_AD`, commit `04c9a64231bd`, trỏ sang bản thu-ml) |
| **Input → output** | Point cloud `N×4` hoặc `N×5` (numpy) + severity 1–5 → point cloud đã bị corrupt. Nhóm object-level cần thêm 3D GT bbox; misalignment cần thêm ego pose. Hàm có sẵn trong `LiDAR_corruptions.py`. |
| **Corruption (LiDAR)** | 23 hàm. Weather: snow, rain, fog, strong sunlight. Sensor: density decrease, cutout, crosstalk, FOV lost, gaussian/uniform/impulse noise. Motion: motion compensation, moving object. Object: local density/cutout/noise, shear, scale, rotation. Alignment: spatial/temporal misalignment. |
| **Severity** | "Every corruption has five severities" |
| **Dataset** | KITTI-C, nuScenes-C, Waymo-C (tạo từ KITTI, nuScenes, Waymo gốc) |
| **Metric** | AP (KITTI), mAP và NDS (nuScenes). **RCE** = (AP_clean − AP_c,s) / AP_clean, tức tỉ lệ sụt giảm tương đối. |
| **Kết luận của nguồn** | Motion-level corruption gây hại nhiều nhất ("Moving Object" ~35% RCE). "FOV Lost" và "Motion Compensation" cũng ảnh hưởng mạnh. Fusion bền hơn LiDAR-only, camera-only rất dễ vỡ. |
| **Motion Compensation (theo nguồn)** | Mô phỏng sai số localization khi bù chuyển động: "adding small Gaussian noises to the rotation and translation matrices". Trong code: σ_t = 0.02–0.10 m, σ_R = 0.002–0.010. |
| **Limitation tác giả nêu** | "Although there inevitably exists a gap, we validate that the model performance on synthetic weathers are consistent with that on real data". Với camera thì "the gap is relatively large". |
| **Yêu cầu chạy** | Python 3.8.2, PyTorch 1.9.0, numpy, imagecorruptions. Phần đánh giá detector cần MMDetection3D/OpenPCDet đã sửa, dataset gốc nhiều trăm GB và GPU. |

**Tham số nguồn dùng (đọc từ `LiDAR_corruptions.py`), so với benchmark của nhóm:**

| Corruption | Nguồn (sev 1→5) | Nhóm (sev 1→5) | Ghi chú |
|---|---|---|---|
| Fog α (1/m) | 0.005, 0.01, 0.02, 0.03, 0.06 | **giống hệt** | Lấy theo Hahner et al. |
| Gaussian σ (m) | 0.02, 0.04, 0.06, 0.08, 0.10 | 0.02, 0.05, 0.10, 0.15, 0.25 | Nhóm mở rộng mức nặng hơn để thấy điểm gãy |
| Density decrease | bỏ 6–30% điểm | bỏ 20–90% điểm | Nhóm mở rộng |
| Motion | nhiễu pose (sai số khi đã bù) | **không bù** ở v = 5–30 m/s | Khác cơ chế, xem dưới |

## Nguồn phụ 1: Robo3D, Kong et al., ICCV 2023

| Câu hỏi | Ghi chép |
|---|---|
| **Nguồn** | *Robo3D: Towards Robust and Reliable 3D Perception against Corruptions*, L. Kong, Y. Liu, X. Li, R. Chen, W. Zhang, J. Ren, L. Pan, K. Chen, Z. Liu. ICCV 2023. arXiv:2303.17597 |
| **Repo** | https://github.com/worldbench/Robo3D (trước đây là `ldkong1205/Robo3D`), commit `481a3b8634b2` |
| **Corruption** | 8 loại: fog, wet ground, snow, motion blur, beam missing, crosstalk, incomplete echo, cross-sensor |
| **Severity** | 3 mức |
| **Dataset** | KITTI-C, SemanticKITTI-C, nuScenes-C, WOD-C (host trên OpenDataLab) |
| **Metric** | **mCE**: corruption error trung bình so với model baseline. **mRR**: resilience rate trung bình so với kết quả clean của chính model. Tính trên mọi loại corruption × 3 mức. |
| **Kết luận của nguồn** | Model SOTA vẫn dễ vỡ dưới corruption. Cách biểu diễn dữ liệu, augmentation và training strategy ảnh hưởng nhiều tới độ bền. |
| **Yêu cầu chạy** | Xây trên MMDetection3D, cần dataset gốc và GPU |

## Nguồn phụ 2: Hahner et al., ICCV 2021 (mô hình fog)

| Câu hỏi | Ghi chép |
|---|---|
| **Nguồn** | *Fog Simulation on Real LiDAR Point Clouds for 3D Object Detection in Adverse Weather*, M. Hahner, C. Sakaridis, D. Dai, L. Van Gool. ICCV 2021. arXiv:2108.05249. Code: http://www.trace.ethz.ch/lidar_fog_simulation |
| **Mô hình** | Hard target bị suy hao `exp(−2αR₀)`. Soft target (backscatter) `β·U(R₀−R)` tạo điểm giả gần sensor. β = 0.046/MOR. |
| **α ↔ tầm nhìn** | α ∈ {0.005, 0.01, 0.02, 0.03, 0.06} tương ứng MOR ≈ {600, 300, 150, 100, 50} m |
| **Dataset / kết quả** | Seeing Through Fog (STF). Train với fog mô phỏng giúp tăng AP trên tập dense fog thật, ví dụ PV-RCNN Car AP@0.5 từ 45.03 lên 46.69. |
| **Limitation tác giả nêu** | Class hiếm (Cyclist) chưa tốt, do mất cân bằng dữ liệu (28 cyclist so với 1186 car trong tập dense fog). |

## Đường chạy đã chốt và lý do

| Câu hỏi | Quyết định |
|---|---|
| **Vì sao không chạy demo gốc?** | Đánh giá detector theo nguồn cần KITTI/nuScenes (hàng trăm GB), MMDetection3D/OpenPCDet và GPU CUDA. Máy lab là Windows, không có GPU, và Application Control còn chặn cả DLL của matplotlib/sklearn. Không thể làm trong 120 phút. |
| **Nhóm tái hiện phần nào?** | **Benchmark mô phỏng nhỏ.** Tự viết LiDAR 32 beam ray-cast. Corruption **viết lại theo đúng công thức/tham số của nguồn** (fog α, gaussian, density). Bổ sung beam missing (Robo3D), packet loss và motion **không bù**. |
| **Metric thật hay proxy?** | Object recall với detector clustering cổ điển là **proxy** cho detector học sâu. Nó đo được xu hướng "corruption → mất object", nhưng **không** cho biết mAP/NDS của PointPillars hay CenterPoint giảm bao nhiêu. Point density và health score là metric về **sensor health**, không phải chất lượng thuật toán. |
| **Claim ban đầu kiểm tra được gì?** | (1) Corruption nào làm mất object nhiều nhất và ở khoảng cách nào. (2) Một health monitor đơn giản, không cần GT, có phát hiện được từng loại corruption không. |
| **Lệnh chạy** | `pip install -r requirements.txt && python run_benchmark.py` (seed 0–7) |
