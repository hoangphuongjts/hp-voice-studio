# T1 — REPORT: Nền tảng HP Voice Studio (SDK + WAV thật đầu tiên + API skeleton)

- **Ngày:** 19/11/2026 (21:10–21:23 +07, máy Annie — VM Linux)
- **Nhánh:** `foundation/t1` (tạo từ `spec/v1-r1`) · **SPEC tham khảo:** v1.1, không sửa SPEC
- **Kết luận nhanh:** ✅ **WAV đầu tiên PASS** (48 kHz thật, giọng Hải Đăng) · ✅ **API skeleton chạy được** (3/3 endpoint curl PASS trên cổng 8124) · ⚠️ **RTF fp32 trên máy ảo này ~1,9–2,1 — CHẬM HƠN real-time**, không đạt ngưỡng SPEC/G1 (≤0,95 fp32); int8 cải thiện còn ~1,15 nhưng vẫn >1,0. Đây là bằng chứng đo thật, không phải lỗi cài đặt.

## 1. Môi trường & cài đặt

| Hạng mục | Giá trị đo được |
|---|---|
| Python | 3.12.3 (`python --version`) |
| CPU máy ảo | AMD EPYC 9D25, 4 vCPU, quota ~1,5 CPU; có AVX2 + AVX-VNNI + AVX512-VNNI (`/proc/cpuinfo`) |
| RAM | 7.934 MB total; lúc chạy còn ~600–800 MB free (eo hẹp — vẫn chạy được) |
| venv | `~/workspace/hp-voice-studio/.venv` (921 MB, pip 24.0) |
| `vieneu` | **3.8.4** (`pip show vieneu`) |
| `onnxruntime` | 1.32.0 · `fastapi` 0.165.0 · `uvicorn` 0.54.0 · `numpy` 2.5.5 · `soundfile` 0.14.0 |
| `ffprobe`/`ffmpeg`/`curl` | có sẵn (`/usr/bin/ffprobe` …) |

**Lỗi gặp khi cài (đã sửa, cách 1/3):** lần `pip install vieneu==3.8.4` đầu tiên FAIL với
`OSError: [Errno 28] No space left on device` khi đang tải `gradio-6.32.0` (31,4 MB).
Nguyên nhân gốc: `/tmp` là tmpfs chỉ 512 MB, đã dùng 460 MB (90%) — pip dùng `/tmp`
làm nơi giải nén wheel, trong khi `/home/hatch` còn 128 GB trống. Cách sửa: đặt
`TMPDIR=$PWD/.tmp-pip` (thư mục dưới `/home/hatch`) + `--no-cache-dir`, cài lại
**thành công** (exit 0, `import vieneu` OK). Không đổi hướng sang CIT hay V4.

## 2. WAV thật đầu tiên — ✅ PASS

- **Script:** `evidence/t1-first-wav/t1_first_wav.py` — `Vieneu()` mặc định (v3turbo,
  ONNX/CPU, fp32), `infer(text, voice="Hải Đăng")`, `save()` ra WAV.
- **Text:** “Xin chào, đây là HP Voice Studio. Giọng đọc tiếng Việt chạy hoàn toàn trên máy của bạn.”
- **File:** `evidence/t1-first-wav/t1-first-wav-hai-dang.wav` (468.524 byte)
  — *file WAV không commit (đã có trong `.gitignore`), chỉ giữ local làm evidence.*
- **ffprobe (chạy thật):**
  `Audio: pcm_s16le, 48000 Hz, 1 channels, s16, 768 kb/s` · `Duration: 00:00:04.88`
- **Giọng preset:** `list_preset_voices()` trả **25 giọng** (đúng kỳ vọng) — danh sách đầy đủ
  trong `voices.json`; giọng “Hải Đăng” (⭐ Nam · Bắc · Phong cách tự nhiên) có trong preset.
- **Thời gian khởi tạo engine lần đầu (cold, kèm tải model): 236,4 s.** Lần sau (model đã cache): **9,4 s**.

## 3. RTF đo thật (fp32 mặc định, CPU máy ảo này)

| Lần đo | Thời gian tạo | Độ dài audio | RTF |
|---|---|---|---|
| Lần đầu (T1, cold infer) | 10,09 s | 4,88 s | **2,068** |
| Warm lần 1 | 13,93 s | 4,88 s | 2,855 |
| Warm lần 2 | 9,47 s | 4,72 s | 2,006 |
| Warm lần 3 | 9,19 s | 4,96 s | **1,852** |
| **int8** (1 lần, CPU có VNNI) | 5,50 s | 4,80 s | **1,147** |

- RTF = thời gian `infer()` / độ dài audio. Số warm ổn định quanh **~1,9–2,0 (fp32)**.
- **So sánh:** upstream README đo trên i5 12th-gen 6 P-core: fp32 0,62 / int8 0,37.
  Máy ảo này chậm hơn ~3× — nguyên nhân hợp lý nhất là CPU chia sẻ/quota thấp
  (1,5 CPU) chứ không phải lỗi SDK; int8 nhanh hơn fp32 ~1,7×, khớp tỉ lệ ~1,6×
  trong README. int8 init 27,0 s (phải tải thêm subfolder `onnx_int8`).
- **Hệ quả cho SPEC:** trên máy ảo Annie, fp32 **không đạt** ngưỡng mượt G1 (≤0,95)
  hay GPT2 (p95 ≤0,90); int8 cũng chưa đạt ngưỡng G1 (≤0,55) và vẫn >1,0.
  Cần đo lại trên máy Windows thật của anh trước khi chốt ngưỡng “mượt”.
  Gợi ý: auto-detect VNNI → mặc định int8 trên máy có VNNI (SPEC TH-03 đã nêu hướng này).
- WAV int8 kiểm chứng: `t1-int8-hai-dang.wav`, ffprobe 48 kHz / 4,80 s (không commit).

## 4. Dung lượng model tải thật (trả lời TH-02 — README không ghi số Turbo)

HF cache `~/.cache/huggingface`: **trước 1,1 GB → sau lần chạy đầu 1,6 GB → sau test int8 1,7 GB**.
Đo riêng từng thành phần (cộng kích thước file thật qua symlink snapshot):

| Thành phần | Dung lượng |
|---|---|
| Backbone `pnnbao-ump/VieNeu-TTS-v3-Turbo`, subfolder `onnx_update` (fp32) | **475,4 MB** (7 file; lớn nhất `vieneu_backbone_shared.data` 415,3 MB, `vieneu_v3_heads.npz` 52,2 MB) |
| + `denoiser.onnx` + config/tokenizer trong cùng repo | **518,1 MB** cả repo snapshot |
| Codec `OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX` | **90,6 MB** (6 file; 2 file `.data` ~44 MB mỗi file) |
| **Tổng fp32 (backbone + codec)** | **~608,6 MB** |
| Thêm subfolder `onnx_int8` (nếu dùng int8) | **+165,5 MB** → tổng cả 2 precision ≈ 774 MB |

- Lưu ý: 2 file ONNX nhỏ (`vieneu_prefill.onnx`, `vieneu_decode_step.onnx`, 0,3 MB mỗi file)
  đã có trong cache từ 11/11 (lần chạy CIT trước trên máy này) — không đáng kể so với tổng.
- Repo `MOSS-Audio-Tokenizer-Nano` (bản không ONNX) **không** được tải — engine ONNX chỉ cần bản `-ONNX`.

## 5. API skeleton — ✅ CHẠY ĐƯỢC (3/3 endpoint)

- **Server:** `server/hp_api.py` — FastAPI + uvicorn, code HP viết mới (không copy
  `apps/openai_speech.py` của upstream, không code CIT). Bind `127.0.0.1:8124`
  (cổng SPEC chốt; 8123 MODOLIVIO, 8001 CIT — đã kiểm tra 8124 trống trước khi chạy).
  Không auth (quyết định 04:20 19/11: chỉ chạy local, bind loopback).
  Engine nạp ở startup; inference khóa bằng `threading.Lock` (chạy tuần tự).
- **Chạy:** `.venv/bin/python server/hp_api.py` → `Uvicorn running on http://127.0.0.1:8124`,
  log `api-server.log`. Đã dừng server sau khi test xong (cổng 8124 trống trở lại).

| # | Endpoint | Kết quả curl |
|---|---|---|
| 1 | `GET /health` | **200** `{"status":"ok","engine":"v3","v3_ready":true,"v4_configured":false,"version":"0.1.0-t1","uptime_s":24.1}` |
| 2 | `GET /v1/voices` | **200**, 0,003 s, **25 voices** (`api-voices.json`) |
| 3 | `POST /v1/audio/speech` `{"input":"Xin chào, đây là HP Voice Studio qua API.","voice":"Hải Đăng"}` | **200**, 5,20 s, 268.844 B → `api-speech.wav`, ffprobe **48 kHz, mono, 2,80 s** (RTF qua API ≈ 5,2/2,8 ≈ 1,86, khớp RTF fp32 warm) |

- **Trường hợp lỗi (kiểm chứng thêm):** `POST /v1/audio/speech` với voice không tồn tại →
  **400** `{"detail":"voice khong ton tai: Khong Co Giong Nay"}` (xem `api-curl.log`).
- Log curl đầy đủ: `api-curl.log`, `api-voices.json`, `api-server.log`.

## 6. File đã làm (nhánh `foundation/t1`)

- `server/hp_api.py` — API skeleton (mới)
- `evidence/t1-first-wav/t1_first_wav.py`, `t1_warm_rtf.py`, `t1_int8_rtf.py` — script đo
- `evidence/t1-first-wav/T1-REPORT.md` (file này), `t1-run.log`, `t1-warm-rtf.log`,
  `t1-int8-rtf.log`, `voices.json`, `api-voices.json`, `api-curl.log`, `api-server.log`
- **Không commit:** `.venv/` (921 MB), `*.wav` (3 file evidence local), `__pycache__/` —
  đã có sẵn trong `.gitignore` nên không cần sửa `.gitignore`. Không sửa `SPEC.md`.
- File untracked có sẵn từ trước trên nhánh (`NHIEM-VU.md`, `SPEC-G3-G4-snapshot.md`,
  `vieneu-studio-clone-2026-11-19.md`) **không** commit trong đợt này.

## 7. Lỗi còn tồn / việc chưa làm

1. **RTF fp32 ~1,9–2,1 trên máy ảo Annie** — chưa đạt ngưỡng mượt; cần đo lại trên máy
   Windows thật của anh và cân nhắc mặc định int8 khi CPU có VNNI. Không phải lỗi chặn T1.
2. **Chưa test clone giọng** — chờ anh gửi mp3 mẫu (bước riêng sau, theo nhiệm vụ).
3. **Chưa test chạy offline hoàn toàn** (chặn mạng sau khi tải model — yêu cầu TH-02/SPEC TK1.3).
4. API skeleton chưa có: `POST /v1/voices` (thêm giọng clone), streaming, `response_format=mp3`,
   `GET /v1/models` — thuộc các bước sau, không thuộc T1.
5. `pip install` lần đầu fail do `/tmp` tmpfs đầy (đã sửa bằng `TMPDIR`, xem §1) —
   ghi chú cho máy khác: dùng `TMPDIR` trỏ vào ổ đủ trống khi cài.
