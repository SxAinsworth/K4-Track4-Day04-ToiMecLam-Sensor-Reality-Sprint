# Hướng Dẫn Xây Dựng Mini-Benchmark Đánh Giá Độ Bền (Robustness) Mô Hình LiDAR 3D

Tài liệu này tổng hợp 5 nhóm thông tin cốt lõi từ 3 bài báo khoa học tiêu biểu (*Dong et al. - KITTI-C/nuScenes-C*, *Robo3D*, và *STF Fog Simulation*) nhằm giúp bạn thiết kế một phiên bản benchmark thu nhỏ cho bài toán nhận diện 3D / LiDAR.

---

## Bảng Tóm Tắt Tổng Quan 3 Paper

| Paper | Kiểu Corruption chính | Mức độ / Severity | Metrics chính | Link Code / Resource |
| :--- | :--- | :--- | :--- | :--- |
| **Dong et al.** *(2303.11040)* | 27 loại (Weather, Sensor, Motion, Object, Alignment) | 5 mức (Severity 1–5) | $AP_{cor}$, $mAP_{cor}$, $RCE$ | [lidar-camera-robust-benchmark](https://github.com/kcyu2014/lidar-camera-robust-benchmark) |
| **Robo3D** *(2303.17597)* | 8 loại (Fog, Wet Ground, Snow, Motion Blur, Beam Missing, Crosstalk, Echo, Cross-Sensor) | 3 mức (Light, Moderate, Heavy) | $mCE$ (Corruption Error), $mRR$ (Resilience Rate) | [Robo3D / LaserMix](https://github.com/ldkong1205/LaserMix) |
| **STF Fog** *(2108.05249)* | Sương mù (Light fog, Dense fog) dựa trên mô phỏng vật lý | 2 mức thực tế + mô phỏng hạt | $mAP$ trên dữ liệu thời tiết xấu | [LiDAR_fog_sim](https://github.com/MartinHahner/LiDAR_fog_sim) |

---

## 1. Các Kiểu Làm Hỏng Dữ Liệu (Corruption Types)

Các bài báo phân loại việc làm hỏng dữ liệu Point Cloud và Ảnh thành các nhóm chính:

- **Thời tiết xấu (Weather-level):**
  - *Mưa / Tuyết / Sương mù:* Giảm mật độ điểm LiDAR, tạo nhiễu hạt do sự suy giảm (attenuation) và tán xạ ngược (backscattering) của tia laser, đồng thời làm mờ ảnh camera.
  - *Mặt đường ướt (Wet Ground):* Tăng phản xạ bất thường trên mặt đường, khiến LiDAR bỏ sót các điểm mặt đường.
- **Nhiễu cảm biến (Sensor-level):**
  - *Dropout / Beam Missing:* Bỏ bớt các tia LiDAR (ví dụ bỏ 16, 32 hoặc 48 tia trên hệ thống 64 tia).
  - *Nhiễu Gaussian / Uniform:* Thêm nhiễu ngẫu nhiên vào tọa độ $(x, y, z)$ của điểm.
  - *Cutout / Mất góc nhìn (FOV Lost):* Bỏ hẳn một vùng không gian hoặc giảm mật độ toàn cục.
  - *LiDAR Crosstalk / Echo không đầy đủ:* Nhiễu do các cảm biến bị nhiễu chéo hoặc dải phản hồi bị gián đoạn.
- **Lỗi chuyển động (Motion-level):**
  - *Motion Blur / Lỗi bù chuyển động:* Xe di chuyển nhanh hoặc xóc làm lệch hệ tọa độ tính toán giữa các điểm thu nhận.

> **Đề xuất cho Mini-Benchmark:** Chọn **3–4 kiểu tiêu biểu** dễ cài đặt bằng Python/NumPy:
> 1. **Global Point Dropout:** Bỏ ngẫu nhiên $X\%$ số điểm.
> 2. **Gaussian Spatial Noise:** Thêm nhiễu $\mathcal{N}(0, \sigma^2)$ vào tọa độ $(x, y, z)$.
> 3. **Local Cutout / BBox Dropout:** Bỏ các điểm nằm bên trong bounding box của vật thể.
> 4. **Camera Motion Blur / Noise** *(nếu làm Multimodal/Fusion)*: Dùng `imgaug` hoặc OpenCV.

---

## 2. Phân Chia Mức Độ Hỏng (Severity Levels & Parameters)

- **Dong et al. (CVPR 2023):** Chia làm 5 mức Severity (1–5).
  - *Rain / Snow (LiDAR):* Lượng mưa/tuyết $r_s \in \{0.20, 0.73, 1.56, 3.125, 7.29\}\text{ mm/h}$.
  - *Local Noise:* Độ lệch chuẩn nhiễu trong 3D Bounding Box $\sigma \in \{0.02\text{m}, 0.04\text{m}, 0.06\text{m}, 0.08\text{m}, 0.10\text{m}\}$.
- **Robo3D:** Chia 3 mức (Light, Moderate, Heavy) để tiết kiệm chi phí tính toán:
  - *Beam Missing:* Mất ngẫu nhiên $\{16, 32, 48\}$ tia trên tổng số 64 tia (tương ứng mất $25\%, 50\%, 75\%$ dữ liệu).
  - *Motion Blur:* Độ lệch chuẩn nhiễu tọa độ $\sigma_t \in \{0.04, 0.08, 0.10\}\text{m}$ (trên KITTI).
  - *Fog:* Hệ số tán xạ ngược $\beta \in \{0.008, 0.05, 0.2\}$.

> **Đề xuất tham số cho Mini-Benchmark:** Chọn **3 mức độ (Nhẹ - 10% / Vừa - 30% / Nặng - 50%)**:
> - *Random Point Dropout:* Mất 10%, 30%, 50% số điểm.
> - *Gaussian Spatial Noise:* $\sigma \in \{0.02\text{m}, 0.05\text{m}, 0.10\text{m}\}$.

---

## 3. Metrics Đánh Giá Suy Giảm (Evaluation Metrics)

1. **Relative Corruption Error ($RCE$):**
   $$RCE = \frac{AP_{clean} - AP_{cor}}{AP_{clean}} \times 100\%$$
2. **Mean Resilience Rate ($mRR$) trong Robo3D:** Tỷ lệ hiệu năng còn giữ được so với tập sạch:
   $$mRR = \frac{AP_{cor}}{AP_{clean}} \times 100\%$$
3. **Mean Corruption Error ($mCE$) trong Robo3D:** Đánh giá tổng hợp lỗi bằng cách so sánh mức giảm của mô hình thử nghiệm với một mô hình baseline chuẩn (ví dụ: CenterPoint hoặc MinkUNet).

> **Đề xuất Metric cho Mini-Benchmark:**
> - **Absolute Recall / mAP:** Điểm nhận diện trên tập bị hỏng ($AP_{cor}$).
> - **Relative Resilience Rate (Tỷ lệ chống chịu tương đối):**
>   $$\text{Recall Tương Đối} = \frac{\text{Số vật thể nhận ra khi hỏng}}{\text{Số vật thể nhận ra khi dữ liệu sạch}} \times 100\%$$

---

## 4. Xu Hướng Kết Quả (Main Results & Findings)

- **Kiểu hỏng gây hại nặng nhất:** Thời tiết nặng (*Snow, Dense Fog*) và các lỗi mất góc nhìn/mất tia (*FOV Lost, Beam Missing*) làm mAP sụt giảm từ **30% đến 60%** trên cả mô hình LiDAR và Fusion.
- **Tính dễ tổn thương của Camera-only:** Các mô hình chỉ dùng Camera bị ảnh hưởng nặng nề nhất bởi các hiện tượng nhiễu thị giác và thời tiết (mAP rớt thảm hại, có thể giảm hơn 80%).
- **Độ bền tương đối:** Các mô hình có độ chính xác trên tập sạch càng cao thì trên tập hỏng điểm vẫn duy trì ở mức cao hơn, nhưng tỷ lệ phần trăm sụt giảm ($RCE$) vẫn rất đáng kể nếu không có chiến lược gia cố dữ liệu (data augmentation).

---

## 5. Mã Nguồn & Tài Nguyên Tái Sử Dụng (Code & Resources)

- **Robo3D Benchmark Codebase:** [LaserMix / Robo3D GitHub](https://github.com/ldkong1205/LaserMix) *(Chứa logic biến đổi 8 loại corruption và script tính mCE/mRR)*.
- **KITTI-C / nuScenes-C Toolkit:** [lidar-camera-robust-benchmark GitHub](https://github.com/kcyu2014/lidar-camera-robust-benchmark).
- **Mô phỏng Thời tiết LiDAR:** [LiDAR_fog_sim](https://github.com/MartinHahner/LiDAR_fog_sim) & [LiDAR_snow_sim](https://github.com/SysCV/LiDAR_snow_sim).
- **Framework Model Pretrained:** Sử dụng [OpenPCDet](https://github.com/open-mmlab/OpenPCDet) để tải checkpoint sẵn của SECOND, PointPillars, PV-RCNN trên tập KITTI.

---

## Mẫu Đoạn Viết "Related Work" Cho Báo Cáo

> *"Gần đây, các benchmark như KITTI-C, nuScenes-C (Dong et al., 2023) và Robo3D (Kong et al., 2023) đã đề xuất hệ thống đánh giá độ bền (robustness) của các mô hình nhận diện 3D trước các hiện tượng nhiễu cảm biến, biến đổi thời tiết và lỗi chuyển động. Dựa trên các nghiên cứu này, trong bài báo này chúng tôi xây dựng một benchmark thu nhỏ tập trung vào 3 biến đổi phổ biến nhất là: (1) Random Point Dropout, (2) Gaussian Spatial Noise, và (3) Local Bounding-box Cutout với 3 mức độ nghiêm trọng (10%, 30%, 50%) để đánh giá khả năng chống chịu tương đối của mô hình."*
