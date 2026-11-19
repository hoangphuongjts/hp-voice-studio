# Tải model v3 Turbo — dung lượng thật theo từng thành phần (TK1.3)

> Số đo thật trên máy ảo Annie (VM Linux, ngày 19/11/2026), script
> `scripts/download_model.py`, báo cáo + manifest SHA-256:
> `evidence/tk1-engine/model-download.json`.
> Lần tải đầu từ mạng HF mất 45,5 s (chỉ repo tokenizer là mới — 41,5 s — còn
> lại đã có sẵn trong cache từ T1). Chạy lại khi đã cache: 1,6 s (chỉ kiểm
> tra, không tải lại).

## Dung lượng thật từng thành phần

| Thành phần | Repo | Dung lượng thật | File |
|---|---|---|---|
| backbone-fp32 | `pnnbao-ump/VieNeu-TTS-v3-Turbo` (`onnx_update/`) | **453,4 MB** | 7 |
| backbone-int8 | cùng repo (`onnx_int8/`) | **157,8 MB** | 7 |
| denoiser-root | cùng repo (gốc: `denoiser.onnx`, `config.json`) | **40,7 MB** | 2 |
| tokenizer | `OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano` | **84,1 MB** | 8 |
| codec-onnx | `OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX` | **86,4 MB** | 8 |
| **Tổng 5 thành phần** | | **822,4 MB** | 32 |

So sánh với T1-REPORT (đo bằng `du` qua symlink snapshot): backbone fp32
475,4 MB / codec 90,6 MB / tổng fp32 ~608,6 MB. Chênh lệch nhỏ do cách đo
(T1 cộng cả `denoiser.onnx` + config/tokenizer trong cùng repo; số ở đây đo
riêng từng file qua `stat()` theo symlink). Tổng tối thiểu để chạy ONNX/CPU
chỉ cần fp32 + denoiser-root + codec-onnx = **580,5 MB**; thêm int8 thì
**738,3 MB**.

## Hai phát hiện khi đo thật (đã kiểm chứng, không phải suy luận)

1. **Repo tokenizer 84,1 MB KHÔNG cần cho đường ONNX/CPU.**
   Kiểm chứng: giấu thư mục cache `models--OpenMOSS-Team--MOSS-Audio-Tokenizer-Nano`
   rồi chạy `HF_HUB_OFFLINE=1` nạp engine fp32 + tạo WAV mới — vẫn OK
   (audio 2,48 s). Đường ONNX dùng codec `MOSS-Audio-Tokenizer-Nano-ONNX` +
   `tokenizer.json` trong `onnx_update/`; repo safetensors 84,1 MB chỉ phục vụ
   đường PyTorch (GPU). Script vẫn tải nó theo SPEC, nhưng có thể bỏ để tiết
   kiệm 84,1 MB nếu chỉ dùng ONNX/CPU.
2. **File `voices_v3_turbo.json` KHÔNG có ở gốc repo HF.**
   Thành phần denoiser-root chỉ tải được 2 file (`denoiser.onnx`, `config.json`);
   SDK `_load_repo_voices` thử tải file này và bỏ qua lặng lẽ khi thiếu — giọng
   preset vẫn đủ 25 vì SDK đọc file `assets/voices_v3_turbo.json` trong package.
   Không ảnh hưởng chạy.

## Resume + checksum

- Tải dở được tiếp tục: `snapshot_download(..., resume_download=True)`.
- Checksum: manifest SHA-256 từng file trong `model-download.json`.
  `scripts/download_model.py --verify-only` kiểm tra cache theo manifest;
  `--repair` chỉ xóa blob hỏng rồi tải lại đúng file đó (không tải lại cả model).
  Test: `tests/test_model_download.py` (đổi 1 byte -> báo `corrupt`).

## Kiểm chứng offline hoàn toàn

`HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1` + nạp `V3Engine` + tạo WAV mới:
PASS (test `test_offline_hoan_toan_tao_wav_moi`). Không còn gọi HF sau khi tải.

## Chạy lại

```bash
# Tải đủ 5 thành phần (lần đầu cần mạng)
.venv/bin/python scripts/download_model.py

# Chỉ kiểm tra cache (không mạng, không tải)
.venv/bin/python scripts/download_model.py --verify-only

# Kiểm tra + sửa file hỏng (chỉ tải lại file hỏng)
.venv/bin/python scripts/download_model.py --repair
```
