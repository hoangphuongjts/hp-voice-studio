# Quyết định engine time-stretch mặc định (TK1.9 / TH-20)

- **Ngày đo:** 19/11/2026 · **Máy đo:** VM Linux của Annie (CPU chia sẻ ~1,5 CPU, RAM free thấp)
- **Nguồn đo:** file WAV mẫu thật `evidence/t1-first-wav/t1-first-wav-hai-dang.wav`
  (4,88 s, 48 kHz, giọng Hải Đăng) · **Script:** `scripts/measure_stretch.py`
  · **Kết quả thô:** `evidence/tk1-audio/stretch-measure.json`
- **Chất lượng nghe bằng tai:** để lại cho Annie/người dùng (không đo ở đây).

## Số đo thật

| Engine | Tốc độ | RTF (warm) | Thời gian xử lý | Tỉ lệ thời lượng (kỳ vọng) | RMS ra / vào | Đỉnh ra / vào |
|---|---|---|---|---|---|---|
| librosa | 0,75× | 0,022 | 0,11 s | 1,333 (1,333) | 0,069 / 0,101 | 0,699 / 0,865 |
| atempo | 0,75× | 0,085 | 0,42 s | 1,329 (1,333) | 0,102 / 0,101 | 0,865 / 0,865 |
| librosa | 1,5× | 0,010–0,059 | 0,05–0,29 s | 0,667 (0,667) | 0,065 / 0,101 | 0,481 / 0,865 |
| atempo | 1,5× | 0,018 | 0,09 s | 0,667 (0,667) | 0,099 / 0,101 | 0,853 / 0,865 |

(RTF librosa warm dao động 0,010–0,059 giữa các lần chạy do CPU chia sẻ; cả hai
engine đều đạt mục tiêu T2.4 là RTF time-stretch ≤ 1 với biên độ lớn.)

## Phát hiện

1. **Cả hai engine đều đủ nhanh (RTF warm ≪ 1)** và đúng tỉ lệ thời lượng
   (±10% theo T2.4) ở cả 0,75× và 1,5×.
2. **atempo giữ năng lượng/đỉnh tốt hơn hẳn:** RMS ra ≈ RMS vào (0,102 vs 0,101
   ở 0,75×; 0,099 vs 0,101 ở 1,5×), đỉnh giữ ~0,85–0,87. librosa làm suy giảm
   rõ: RMS còn ~2/3 (0,065–0,069) và đỉnh ở 1,5× chỉ còn 0,48 (so với 0,87)
   — phase vocoder làm mất năng lượng, nghe sẽ nhỏ/yếu hơn trừ khi chuẩn hoá
   lại sau stretch.
3. **librosa trả giá khởi động lớn:** lần gọi đầu trong tiến trình mới
   (import librosa + biên dịch JIT numba) mất **20,2 s cho 4,88 s audio
   (RTF lạnh ≈ 4,1)**; các lần sau mới nhanh. atempo không có chi phí này
   (tiến trình ffmpeg riêng, khởi động ~0,1 s).
4. atempo là code C trong FFmpeg — không thêm dependency Python nào; librosa
   kéo theo numba 0.68.1 / llvmlite 0.50.0 (nặng, JIT, rủi ro đóng gói
   PyInstaller trên Windows — đúng tử huyệt TH-20).

## Quyết định

**Engine mặc định: FFmpeg `atempo`. Dự phòng: librosa.**

- `AudioPost.stretch_audio_file()` thử `atempo` trước; không có FFmpeg
  (hoặc ffmpeg lỗi) thì fallback librosa trên mảng numpy — vẫn ra đúng tỉ lệ,
  không crash, không chặn tạo audio.
- Tốc độ 1,0× không qua stretch (chép nguyên file).
- Sau stretch vẫn chuẩn hoá đỉnh (`normalize_peak`, target 0,95) nên độ suy
  giảm năng lượng của librosa ở đường dự phòng được bù phần nào.

## Hệ quả / việc báo lại cho coordinator

- **KHÔNG pin numba/llvmlite vào requirements.txt** (không sửa file đó):
  librosa chỉ còn là đường dự phòng, và nó đã là dependency của SDK
  (`vieneu==3.8.4` kéo `librosa==1.0.1` + numba/llvmlite theo) nên không cần
  thêm dòng nào. Nếu sau này bỏ hẳn librosa khỏi code thì mới xét gỡ — không
  làm ở đợt này vì SDK vẫn cần nó.

## Bổ sung 19/11 — gỡ librosa khỏi bộ cài (giảm kích thước Q2)

- **Đính chính:** nhận định "SDK vẫn cần librosa" ở trên là SAI với đường
  v3 Turbo CPU. Kiểm chứng thật (evidence/size-reduction/block_test.py):
  chặn import librosa/numba/llvmlite/scipy/sklearn/pandas/gradio/PIL rồi
  chạy TTS thật + clone thật — TẤT CẢ PASS (nạp model, 25 giọng preset,
  synthesize, encode_reference/add_voice/synthesize clone). Các chỗ SDK
  dùng librosa đều có fallback (``base._load_ref_mono`` → soundfile+soxr,
  ``v3turbo`` trim → numpy); ``_v3_turbo_engine/`` không nhắc librosa lần nào.
- **Đã làm:** engine mặc định của ``time_stretch`` chuyển sang atempo
  (file tạm + FFmpegManager); librosa chỉ còn là dự phòng tùy chọn khi còn
  cài (bắt ImportError → ``StretchUnavailableError`` rõ ràng, API trả 400);
  gỡ librosa khỏi requirements.txt; spec PyInstaller exclude librosa,
  numba, llvmlite, scipy, sklearn, pandas, gradio, PIL, joblib, pooch.
  Tiết kiệm ~290 MB — xem evidence/size-reduction/SIZE-REDUCTION-REPORT.md.
- **Chờ kiểm chứng thật:** nghe đối chiếu atempo vs librosa bằng tai trên
  giọng thật (cùng câu mẫu ở 0,75×/1,5×) và đo lại RTF trên máy Windows thật
  của anh (CPU không bị chia sẻ như VM này) — số RTF trên VM này chỉ để tham
  khảo, không thay cho số trên máy anh (SPEC T1.4).
