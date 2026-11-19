# CPU tham chiếu + hiệu năng đo thật (TK1.4)

> Số đo thật trên máy ảo Annie (VM Linux, ngày 19/11/2026), test
> `tests/test_cpu.py` + script `scripts/measure_rtf.py`, báo cáo:
> `evidence/tk1-engine/rtf.json`.
> **Ngưỡng mượt cuối cùng (RTF ≤ 1, chunk đầu ≤ 500 ms) đo lại trên máy
> Windows thật của anh (C6) — số dưới đây CHỈ là số đo trên VM, không thay cho
> số trên máy anh.**

## CPU máy đo

| Hạng mục | Giá trị đo được |
|---|---|
| CPU | **AMD EPYC 9D25 126-Core Processor** (VM chia sẻ, quota ~1,5 CPU) |
| RAM | 7.934 MB total; lúc chạy còn ~600–900 MB free |
| AVX-VNNI | **có** (token `avx_vnni` trong `/proc/cpuinfo` + cờ `avx_vnni` của py-cpuinfo) |
| AVX-512 VNNI | **có** (cờ `avx512vnni` của py-cpuinfo 9.0.0) |
| Precision mặc định theo CPU | **int8** (có VNNI) |

## RTF đo thật (câu mẫu "Xin chào, đây là HP Voice Studio.", giọng Hải Đăng)

| Precision | Thời gian load model (đã cache) | RTF từng lần | RTF trung bình |
|---|---|---|---|
| fp32 | 8,0 s | 1,816 / 2,015 | **1,916** |
| int8 | 4,8 s | 1,104 / 1,757 | **1,430** |

- RTF = thời gian `infer()` / độ dài audio. Số đo dao động giữa các lần
  (int8 lần 2 chậm hơn lần 1: 1,757 so với 1,104 — CPU chia sẻ, tải thay đổi).
- So sánh: upstream README (i5 12th-gen 6 nhân): fp32 0,62 / int8 0,37.
  T1 cũng đo fp32 ~1,85–2,86, int8 1,147. VM này chậm hơn ~3× — nguyên nhân
  hợp lý nhất là CPU chia sẻ/quota thấp, không phải lỗi SDK.
- **Kết luận trên VM này: cả fp32 lẫn int8 đều CHẬM hơn real-time (RTF > 1),
  không đạt ngưỡng mượt.** Ghi số thật, không "sửa" cho đạt.

## Độ trễ stream (T1.5) và batch (T1.6)

- Chunk đầu của `infer_stream` (fp32): **0,936 s** — mục tiêu ≤ 0,5 s
  **không đạt trên VM này** (README ghi ~300 ms fp32 trên i5 12th-gen).
- Batch 10 câu ngắn (fp32): RTF batch **2,47** (tổng 34,0 s tạo / 13,8 s audio),
  so với RTF đơn ~1,92 trên cùng VM → tỉ lệ ~1,29× — mục tiêu ≤ 1,2×
  **không đạt trên VM này** với câu ngắn (mỗi câu ngắn chịu chi phí cố định
  mỗi lần gọi infer). Cần đo lại trên máy Windows với câu dài thực tế.

## Thời gian khởi động (T1.7)

- Load model fp32 (đã cache): **8,0–8,1 s**; int8: **4,8 s** (trong cùng
  tiến trình pytest, sau khi fp32 đã nạp — thư viện đã ở sẵn trong RAM nên
  nhanh hơn con số 27 s của T1; không lấy số này làm chuẩn cold-start).
  Cả hai đều dưới mục tiêu ≤ 30 s (T1.7), nhưng số này đo trên VM, chưa phải
  máy anh.

## Độ dao động giữa các lần đo (ghi rõ, không giấu)

Chạy lại bằng script độc lập `measure_rtf.py` (câu mẫu dài hơn của T1, 5,2 s
audio, int8, 1 lần lặp — `evidence/tk1-engine/rtf-script.json`): load 8,5 s,
RTF int8 **2,324**, chunk đầu 0,536 s — chậm hơn hẳn lần đo trong pytest
(RTF int8 trung bình 1,430, load 4,8 s). CPU VM chia sẻ nên số đo dao động
lớn giữa các lần chạy (có thể do agent song song cùng chạy nặng). Vì vậy mọi
số RTF/load trên VM này chỉ mang tính tham khảo; ngưỡng mượt chốt bằng số đo
trên máy Windows thật của anh (C6).

## Nhánh dự phòng máy yếu (T1.4)

RTF fp32 = 1,92 (> 1,5) → theo quy tắc SPEC, VM này thuộc diện "máy yếu cho
v3 Turbo": **đề xuất v3 Nano cho bản nháp** (nhẹ hơn, 24 kHz). Nano **chưa có
ở v1** — `weak_machine_advice()` chỉ báo rõ, không tự chuyển engine.
Quyết định precision/Nano cuối cùng chờ số đo trên CPU thật của anh (C6).

## Cách đo lại

```bash
# Đo nhanh bằng script (fp32 + int8, 3 lần lặp mỗi loại)
.venv/bin/python scripts/measure_rtf.py

# Chỉ đo int8, 1 lần lặp, ghi ra file riêng
.venv/bin/python scripts/measure_rtf.py --precisions int8 --repeats 1 \
    --output evidence/tk1-engine/rtf-script.json
```
