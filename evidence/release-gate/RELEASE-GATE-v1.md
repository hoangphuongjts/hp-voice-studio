# RELEASE GATE v1 — HP Voice Studio (TK4.4)

- **Ngày:** 19/11/2026 · **Nhánh:** `build/v1` · **SPEC:** v1.3
- **Phạm vi gate:** TK4-Release (TK4.3 README/LICENSE/NOTICE/ADR, TK4.5
  nâng SDK, TK4.6 hợp đồng triển khai, TK4.9 FFmpeg checksum/progress,
  TK4.4 release gate) trên nền TK1+TK2+TK3 đã merge main.
- **Môi trường đo:** VM Linux của Annie (Python 3.12.3, CPU chia sẻ
  ~1,5 CPU, RAM free thấp). Mọi kết quả dưới đây là **kiểm chứng trên
  máy ảo**, không phải kiểm chứng thật trên máy Windows của anh.

## Kết luận (verdict)

**PASS 100% các mục chạy được trên VM — với danh sách "chờ kiểm chứng
thật" riêng ở mục 4.**

- `pytest tests/`: **291 passed, 0 failed** (279,57 s) — log
  `pytest-full.log`, `PYTEST_EXIT=0`.
- `node --check ui/*.js`: **12/12 file OK** — log `node-check.log`.
- T4.3 (README + LICENSE + NOTICE): **PASS** — file đủ + nội dung đúng
  SPEC (xem mục 2).
- T4.4 (release gate): **PASS theo định nghĩa của ticket** — test tổng
  PASS 100% các mục chạy được + danh sách chờ kiểm chứng thật tổng hợp
  (mục 4). **KHÔNG ghi "đạt" cho bất cứ mục nào trong danh sách đó.**

## 1. Kết quả test theo nhóm

Log chính: `evidence/release-gate/pytest-full.log`
(`291 passed, 1 warning in 279.57s (0:04:39)`, `PYTEST_EXIT=0`).
Warning duy nhất: `RuntimeWarning: invalid value encountered in cast`
từ numba trong `test_srt_dub_route_vtt` — cảnh báo của dependency, không
phải lỗi test.

| Nhóm | File test | Số test | PASS | FAIL |
|---|---|---|---|---|
| Engine V3 | test_v3_engine.py (9), test_cpu.py (7), test_model_download.py (5) | 21 | 21 | 0 |
| Audio | test_audio_post.py (10), test_ffmpeg_manager.py (11), test_normalizer.py (8), test_text_preprocess.py (16), test_srt_writer.py (11), test_srt_dubber.py (11), test_pron_dict.py (9) | 76 | 76 | 0 |
| API | test_api_tts.py (12), test_api_voices.py (5), test_api_voices_clone.py (13), test_api_features.py (11), test_api_history.py (3), test_api_jobs.py (4), test_api_limits.py (2), test_api_settings.py (4), test_api_dynamic_router.py (3) | 57 | 57 | 0 |
| Tính năng | test_conversation.py (4), test_batch.py (8), test_file_readers.py (7), test_history.py (11), test_queue.py (12), test_worker.py (6), test_preview_cache.py (10), test_voice_store.py (9) | 67 | 67 | 0 |
| V4 (mock, không key thật) | test_v4_engine.py | 22 | 22 | 0 |
| UI (js + shell) | test_ui_shell.py (8), test_ui_tabs.py (13), test_ui_player.py (4), test_ui_settings.py (4) | 29 | 29 | 0 |
| Đóng gói / Shell / Unicode (TK4-PACKAGE) | test_shell.py (7), test_packaging.py (7), test_unicode_paths.py (5) | 19 | 19 | 0 |
| **Tổng** | **35 file** | **291** | **291** | **0** |

`node --check` (12 file): `ui/api.js`, `app.js`, `player.js`,
`tabs-batch.js`, `tabs-dialogue.js`, `tabs-files.js`, `tabs-history.js`,
`tabs-settings.js`, `tabs-srt.js`, `tabs-studio.js`, `tabs-voices.js`,
`virtual-list.js` — tất cả OK.

### Lưu ý về các lần chạy (ghi rõ, không giấu)

1. **Lần chạy 1:** 279 test, **277 passed, 2 failed** — cả hai đều ở
   `tests/test_shell.py`
   (`test_run_day_du_vong_doi_server_that`,
   `test_start_stop_server_that_health_200`): assert cổng trống ngay
   sau `stop_server()` thất bại (cổng vẫn bound). Log đầy đủ của lần
   này đã bị ghi đè khi chạy lại (chỉ còn số đếm từ dấu chấm trong log
   lúc đó: 277 pass + 2 F, và đoạn tail failure đã lưu trong báo cáo
   chạy). Chạy riêng `tests/test_shell.py` sau đó: **7/7 pass, hai lần
   liên tiếp**.
   Chẩn đoán: race khi tắt uvicorn dưới tải nặng — lúc chạy full suite,
   agent TK4-PACKAGE đang chạy song song trên cùng VM (~1,5 CPU) nên
   thread uvicorn chưa kịp giải phóng cổng lúc assert chạy; test assert
   cổng trống ngay lập tức, không chờ/thử lại. Đây là test + code của
   agent TK4-PACKAGE (`src/hpvoice/shell.py`, `tests/test_shell.py`) —
   TK4-Release **không sửa file của agent kia**; ghi lại đây để agent
   đó (hoặc coordinator) xét có nên thêm chờ/thử lại khi kiểm cổng sau
   stop hay không. Không che giấu bằng cách chạy lại cho tới khi pass
   rồi báo "chưa từng fail".
2. **Lần chạy 2** (log `pytest-full-run2.log`): agent TK4-PACKAGE đã
   thêm 12 test mới (tổng 291):
   **290 passed, 1 skipped, 0 failed**.
3. **Lần chạy 3** (log `pytest-full-run3-quiet.log`): **291 passed,
   0 failed, 0 skipped, exit 0** (đếm từ dấu chấm; log này thiếu dòng
   tổng kết vì lỗi `-q` kép — xem mục 4).
4. **Lần chạy cuối, bản chính thức** (log `pytest-full.log`):
   **291 passed, 1 warning, 279,57 s (0:04:39), exit 0**.
5. **Hiện tượng log:** các log `-q` thiếu dòng tổng kết
   `... passed in ...s` vì lệnh chạy dùng `-q` trong khi `pyproject.toml`
   đã có `addopts = "-q"` — hai lần `-q` thành `-qq` (pytest 9.2.0 tắt
   luôn dòng tổng kết). Log chính thức chạy với `-o addopts=""` nên có
   đủ dòng tổng kết. Đây là lỗi ghi log của người chạy, không phải lỗi
   test — đã xác minh bằng cách đếm dấu chấm trong log cũ (run 1:
   277 pass + 2 F; run 2: 290 pass + 1 skip, 0 F) và chạy probe nhỏ
   (`pytest tests/test_queue.py` có tổng kết, `-q` hai lần thì mất).

## 2. Đối chiếu ticket TK4 (T4.3 / T4.4)

### T4.3 — README + LICENSE + NOTICE: PASS

- `README.md` (viết lại đầy đủ): cài đặt Linux/Windows, tải model lần
  đầu + verify + offline, chạy server + mở UI (`/ui`), dùng từng tab
  (8 tab, 3 nhóm Tạo/Thư viện/Hệ thống), clone giọng + cam kết + gỡ
  giọng, V4 cloud tùy chọn + công thức phí + fallback, API local (21
  endpoint, link `docs/api-contract.md`), cấu hình, đóng gói, nâng cấp
  SDK (checklist tóm tắt + link `docs/upgrade-sdk.md`), khắc phục sự
  cố, giấy phép + ghi công, danh sách chờ kiểm chứng thật.
- `LICENSE`: văn bản Apache License 2.0 chuẩn đầy đủ, chủ sở hữu
  "Copyright 2026 HP Voice Studio" (của HP — không copy nguyên LICENSE
  của upstream làm LICENSE của mình, SPEC §13.1/G7).
- `NOTICE`: ghi công VieNeu-TTS (tác giả Phạm Nguyễn Ngọc Bảo) +
  license giọng v3 Turbo theo model card (kèm lưu ý 25 giọng SDK 3.8.4
  chưa được xác nhận đích danh trong card 3.7.1) + FFmpeg binary GPL v3
  + **source offer theo GPL v3 §6** (ffmpeg.org, git.ffmpeg.org,
  BtbN/FFmpeg-Builds, imageio-ffmpeg) + V4 độc quyền + quy tắc giọng
  clone (NĐ 13/2023, NĐ 147/2024).
- `docs/decisions/ADR-07.md` (FFmpeg tải sau — Q21, kèm đính chính
  TK4.9 về imageio-ffmpeg 0.8.1), `ADR-11.md` (Desktop Shell
  pywebview/WebView2), `ADR-12.md` (local-only, bind 127.0.0.1),
  `ADR-13.md` (thước đo: full tính năng dùng được).

### TK4.9 — FFmpeg license + tải cài sau: PASS (trên VM)

- (a) **KHÔNG đóng gói binary FFmpeg:** đã kiểm tra
  `packaging/windows/hp-voice-studio.spec` của agent TK4-PACKAGE —
  spec **không** `--collect-all imageio_ffmpeg`, không `--add-data`
  `imageio_ffmpeg/binaries/*`, và có bộ lọc cuối loại bỏ mọi binary
  FFmpeg lọt vào TOC (`a.datas` lọc `imageio_ffmpeg`). Đạt.
- (b) **Checksum SHA-256 + progress:** `FFmpegManager` thêm
  `PINNED_FFMPEG_SHA256` (ghim `linux-x86_64`: binary
  `ffmpeg-linux-x86_64-v9.0.2`, 172.692.552 byte, SHA-256
  `0d709a0bed1a43f24cd2c420878c63afea4580671b6949ad19ed124572f3bc3d` —
  đo thật bằng `sha256sum` trên VM này 19/11/2026), `sha256_file()`,
  `verify_binary()`, `download(on_progress=...)`; `locate()` nhận
  `on_progress(bytes_done, bytes_total)`. Platform chưa ghim (Windows/
  macOS/...) thì báo rõ + ghi SHA-256 đo được vào
  `ffmpeg-manifest.json`, không lặng lẽ bỏ qua; checksum lệch bảng ghim
  → binary bị từ chối. Test mới 7 test trong
  `tests/test_ffmpeg_manager.py` (tổng file 11/11 pass).
- **Kiểm chứng chạy thật trên VM:** ép không dùng FFmpeg hệ thống →
  `download()` trả đúng binary imageio
  (`.../imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v9.0.2`), verify
  SHA-256 khớp bảng ghim (`ok: True`), 165 lần gọi progress, lần cuối
  `(172692552, 172692552)`; `encode_mp3` ra MP3 thật (ffprobe:
  `mp3,48000`); `decode_to_wav` MP3→WAV thật (ffprobe:
  `pcm_s16le,48000,1`); manifest ghi đúng SHA-256.
- **Đính chính quan trọng (TK4.9):** `imageio-ffmpeg` 0.8.1 đóng gói
  sẵn binary trong wheel — `get_ffmpeg_exe()` chỉ tìm file đã có,
  **không tải binary rời lúc chạy**. "Tải lần đầu" trong thực tế là pip
  tải wheel (nén ~68 MB) lúc `pip install`. SPEC v1.3 viết
  "`get_ffmpeg_exe()` tải lần đầu nếu chưa có" là chưa đúng với 0.8.1;
  `FFmpegManager` + README + ADR-07 đã sửa theo thực tế này: callback
  `on_progress` báo **tiến trình kiểm chứng SHA-256** (băm 165 MB theo
  khối), không phải tiến trình tải mạng. Nếu wheel thiếu binary thì app
  báo rõ + hướng dẫn cài lại/cài FFmpeg hệ thống.
- (c) NOTICE đã ghi GPL v3 + source offer (TK4.3, mục 3).
- (d) Fallback FFmpeg hệ thống giữ nguyên; không có FFmpeg → chỉ WAV +
  báo rõ (test cũ `test_thieu_ffmpeg_chi_wav_khong_crash` vẫn pass;
  không xoá test cũ nào).

### TK4.5 — Quy trình nâng SDK: PASS

- Checklist nâng cấp trong README (mục "Nâng cấp SDK") + đầy đủ trong
  `docs/upgrade-sdk.md`: theo dõi release upstream mỗi quý, ghim
  version, test tương thích bắt buộc, kiểm lại 25 giọng, mirror model +
  checksum SHA-256 (TH-15), xử lý khi nâng vỡ API, nâng
  imageio-ffmpeg phải đo lại `-buildconf` + ghim checksum mới.

### TK4.6 — Hợp đồng triển khai: PASS (phần hợp đồng của T4.4)

- `docs/deployment-contract.md`: bản đầy đủ SPEC §16 — OS, Python
  3.12, SDK + model revision HF (`61b85e3d…`), CPU/RAM, ổ đĩa, bảng
  cổng (8124 HP / 8123 MODOLIVIO / 8001 CIT / 8000-7860 upstream),
  runtime Windows, vỏ desktop, dữ liệu + giới hạn vận hành, hiệu năng
  tham chiếu, bảo mật local-only, tài liệu đi kèm.

## 3. Việc của agent song song (ghi nhận, không nhận công)

Trong lúc TK4-Release chạy, agent TK4-PACKAGE làm việc cùng repo
(`build/v1`): thêm `src/hpvoice/shell.py` (DesktopShell TK4.8),
`packaging/windows/hp-voice-studio.spec`,
`.github/workflows/build-windows.yml`, `scripts/build_windows.py`,
`docs/clean-machine-checklist.md`, test shell/packaging/unicode
(19 test, đều pass ở lần chạy cuối), sửa `scripts/run_server.py`
(`--version`/`--check`, `HPVOICE_ENGINE=fake`), và **đo lại**
`evidence/tk1-engine/*.json` (VD `rtf.json`: fp32 mean 1,68, int8 1,06
— số trong `docs/cpu-reference.md` và README vẫn là số đo trước đó:
fp32 ~1,92 / int8 ~1,43; cả hai đều là số đo thật trên VM, dao động do
CPU chia sẻ — xem `docs/cpu-reference.md` mục "Độ dao động"). Những
file đó **không thuộc TK4-Release**; TK4-Release chỉ kiểm tra spec
không collect FFmpeg (mục 2, TK4.9a) và chạy toàn bộ test (kể cả test
mới của agent kia) trong release gate. Theo spec của agent kia:
repo chưa có remote GitHub nên workflow build Windows **chưa chạy
được** (blocker ghi trong spec + workflow) — cần anh tạo repo GitHub
rồi push code lên.

## 4. Chờ kiểm chứng thật — TỔNG HỢP (KHÔNG tính là đạt)

Từ SPEC §11 (C1..C21) + ghi chú các giai đoạn TK1–TK3. Mọi mục dưới
đây chỉ kiểm được trên máy/tài khoản thật của anh; pass trên VM không
thay thế được.

| # | Việc | Vì sao chỉ kiểm được trên máy thật |
|---|---|---|
| C1 | Cài file `.exe` trên máy Windows thật của anh, mở app, tạo WAV thật (T1.2) | SmartScreen/WebView2/driver âm thanh chỉ có trên máy anh. `.exe` chưa build (blocker repo GitHub, mục 3) |
| C2 | Clone giọng thật của anh (thu micro 3–8 s) + cam kết | Giọng + micro + sự đồng ý của anh |
| C3 | Batch lớn (≥ 100 mục / bài ≥ 30 phút) trên máy anh | RAM/CPU/ổ đĩa thật của máy anh |
| C4 | Tạo video thật bằng giọng HP (ghép vào MODOLIVIO) | Luồng thật cuối cùng |
| C5 | Test V4 bằng key của anh (khi anh đồng ý) — **không tự test** | Key + quota thật của anh |
| C6 | Đổi precision int8/fp32 trên CPU thật của anh; RTF/ngưỡng mượt (RTF ≤ 1, chunk đầu ≤ 500 ms) | VNNI/méo tiếng phụ thuộc CPU thật; ghi rõ model CPU máy anh. Trên VM: RTF fp32 ~1,92 / int8 ~1,43 — **chậm hơn real-time, không đạt ngưỡng mượt trên VM** |
| C7 | LAN API từ máy khác trong mạng nhà anh — chỉ khi mở LAN (§9.3, P2) | Mạng/tường lửa thật; v1 local-only không chặn |
| C8 | Kiểm tra trùng cổng trên máy anh (8123 MODOLIVIO, 8001 CIT, 8000/7860 upstream, 8124 HP) | Cổng đang chiếm chỉ có trên máy anh |
| C9 | Cài `.exe` chưa ký: SmartScreen + WebView2 có sẵn không | Chỉ có trên máy Windows thật |
| C10 | Tốc độ tải model từ Hugging Face trên mạng nhà anh (HF có bị chặn/chậm không) | Mạng nhà anh; quyết định TH-02/TH-15 (đóng gói sẵn model hay tải lần đầu) |
| C11 | Gõ Telex trong UI web local + thu micro trên Windows (quyền micro) | Lỗi Telex từng xảy ra ở MODOLIVIO; micro + quyền chỉ có trên máy anh |
| C12 | Đo peak RAM batch 100/500 mục + dung lượng ổ đĩa sau batch lớn | RAM/ổ đĩa thật của máy anh (TH-16) |
| C13 | Kiểm tra key V4 hợp lệ bằng `GET /v1/balance` — kiểm chứng rằng gọi endpoint này không trừ token | Key + quota thật của anh |
| C14 | SRT dài (≥30 câu) + hội thoại nhiều giọng trên máy anh | Mốc giờ + voice-lock chỉ tin được trên CPU/âm thanh thật |
| C15 | Batch lớn (≥100 mục) tắt app giữa chừng rồi mở lại: checkpoint/resume + history không corrupt + file tạm được dọn | Trạng thái dở dang + ổ đĩa thật |
| C16 | Kiểm tra LAN hardening từ máy khác (Host/Origin/CSRF) — chỉ khi mở LAN | Mạng thật; v1 local-only không chặn |
| C17 | Đọc PDF scan + DOCX có bảng trên máy anh | File thật + mắt anh |
| C18 | Nghe đối chiếu time-stretch librosa vs FFmpeg atempo ở 0,75×/1,5× trên máy anh | Tai anh + CPU thật |
| C19 | Đóng app rồi mở lại nhiều lần: không còn tiến trình ma chiếm cổng 8124; mở 2 instance thì instance sau báo rõ | Vòng đời tiến trình chỉ có trên máy Windows thật |
| C20 | MODOLIVIO gọi API HP thật qua `127.0.0.1:8124` (tạo WAV từ link sản phẩm) | Tích hợp thật cuối cùng |
| C21 | Cài + chạy app trong thư mục có dấu tiếng Việt/khoảng trắng trên máy anh | Đường dẫn thật của máy anh |
| — | **TTL 60 phút thật của hàng đợi** (job chờ quá 60' tự hủy + báo "hết thời gian chờ") | Cần chờ đủ 60 phút thật; test chỉ mock thời gian |
| — | **PDF/DOCX có dấu tiếng Việt** đọc + tạo giọng trên máy anh | File thật + mắt anh (T3.4 đã test file mẫu trên VM) |
| — | **Tải FFmpeg lần đầu trên Windows**: wheel Windows tải về, checksum Windows ghim, MP3 thật sau khi tải | Binary Windows chưa đo (SHA-256 chưa ghim — xem TK4.9b); chỉ mới đo trên Linux |
| — | **UI nhìn bằng mắt thật** (8 tab, chat, kéo-thả, nút bấm) trên trình duyệt/WebView2 thật | Test UI hiện tại là test logic + `node --check` cú pháp, không phải bấm thật |
| — | **Thu micro / phát audio thật** trên Windows (quyền micro, driver âm thanh) | Không có micro/loa thật trên VM |
| — | **Cổng 8124 chạy cùng MODOLIVIO 8123** trên máy anh (hai server cùng chạy, không nhầm đích) | Cần cả hai server thật cùng chạy (T2.1) |
| — | **Build Windows + cài thử trên máy anh** (TK4.1/T4.1, smoke test runner sạch) | Cần repo GitHub + runner Windows + máy anh (mục 3) |
| — | **Đường dẫn có dấu + đóng/mở lại** (T4.5: cài vào `C:\Người dùng\HP Voice Studio`, đóng → không còn tiến trình ma → mở lại bind 8124) | Chỉ có trên máy Windows thật |

## 5. File đã tạo/sửa trong đợt TK4-Release (không commit)

Tạo mới: `LICENSE`, `NOTICE`, `README.md` (viết lại),
`docs/decisions/ADR-07.md`, `docs/decisions/ADR-11.md`,
`docs/decisions/ADR-12.md`, `docs/decisions/ADR-13.md`,
`docs/deployment-contract.md`, `docs/upgrade-sdk.md`,
`evidence/release-gate/RELEASE-GATE-v1.md` (file này),
`evidence/release-gate/pytest-full.log`,
`evidence/release-gate/pytest-full-run2.log`,
`evidence/release-gate/pytest-full-run3-quiet.log`,
`evidence/release-gate/node-check.log`.

Sửa: `src/hpvoice/audio/ffmpeg_manager.py` (checksum SHA-256 +
progress callback + `download()` — không đổi API cũ),
`tests/test_ffmpeg_manager.py` (bổ sung 7 test, không xoá test cũ).

Không sửa: `SPEC.md`, `server/`, `evidence/` (trừ file evidence do
agent TK4-PACKAGE đo lại — xem mục 3), `requirements.txt`,
`config.example.yaml`, `.gitignore`; không đổi nhánh, không commit.
Thư mục `.tmp-test/` (TMPDIR của pytest) đã xoá sau khi chạy xong.

## 6. Kiểm chứng cuối của coordinator (sau khi gate viết xong)

- Lần chạy full đầu của coordinator: **6 failed, 223 passed, 62 errors** — do
  coordinator thêm property `is_loaded` vào `FakeEngine` (để `/health` báo
  đúng với FakeEngine) nhưng property không có setter, trong khi
  `tests/conftest.py` gán `self.is_loaded = True` → AttributeError ở mọi
  fixture `app_client`. Đã sửa: thêm setter cho property (commit TK4).
- Lần chạy full thứ hai: **290 passed, 1 failed** —
  `test_run_server_version_va_check_khong_nap_model` (test hardcode "0.2.0"
  trong khi coordinator đã thống nhất VERSION = "0.1.0" theo pyproject.toml).
  Đã sửa: test đọc version chuẩn từ `pyproject.toml` (commit TK4).
- Lần chạy full cuối: **291 passed, 1 warning, 173,56 s, exit 0**
  (log `evidence/release-gate/pytest-final-coordinator.log`). Không còn fail/error.
- Smoke test gói Linux đã build, do coordinator chạy tay (FakeEngine, cổng 8131):
  `--version` → `HP Voice Studio 0.1.0` (trước khi sửa version là 0.2.0-tk2);
  `/health` → 200; `/v1/voices` → 200 (5 giọng fake); `POST /v1/audio/speech`
  → 200, WAV 48 kHz 0,82 s (khớp công thức FakeEngine 41 ký tự × 0,02 s);
  cổng 8131 trống sau khi dừng. Gói Linux 596 MB (vượt ngân sách Q2 ~300–400 MB —
  xem mục khoảng trống ở báo cáo tổng kết).

## 7. Bổ sung sau phát hành v1 — Q21 tải FFmpeg thật (19/11/2026)

- **Khoảng trống đã sửa:** `FFmpegManager.download()` ở v1 chỉ là stub
  (gọi `locate()`; `imageio-ffmpeg` 0.8.1 đóng gói sẵn binary trong
  wheel nên trong .exe — nơi bộ lọc spec loại bỏ mọi binary
  imageio-ffmpeg — app mãi chỉ xuất WAV trừ khi máy có FFmpeg hệ
  thống). Nay `download()` tải thật (xem ADR-07 + README mục FFmpeg +
  `evidence/ffmpeg-download/FFMPEG-DOWNLOAD-VERIFICATION.md`).
- **Cơ chế mới:** tải archive FFmpeg **LGPL tĩnh** từ BtbN/FFmpeg-Builds,
  release `autobuild-2026-11-18-12-39` đã ghim (không dùng URL
  "latest"); kiểm SHA-256 archive + binary; giải nén an toàn chỉ đúng
  file binary; kiểm chứng binary (`-version` + `-buildconf` không
  `--enable-gpl`/`--enable-nonfree` + `libmp3lame`); resume qua HTTP
  Range + tiến trình; lưu vào `<thư mục dữ liệu>/ffmpeg/`.
- **Kiểm chứng thật trên VM Linux:** live test
  `tests/test_ffmpeg_download_live.py` (HP_LIVE_DOWNLOAD=1) **PASS
  trong 35,10 s** — tải thật 137.212.900 byte, checksum khớp bảng ghim
  và `checksums.sha256` của BtbN, MP3 thật từ WAV mẫu T1 bằng chính
  binary vừa tải (ffprobe đọc được codec mp3). Test mock
  `tests/test_ffmpeg_manager.py`: **20/20 PASS** (11 cũ + 9 mới).
  Full suite sau sửa: **300 passed, 1 skipped, 168,05 s, exit 0**
  (log `evidence/release-gate/pytest-q21-download.log`; 1 skipped là
  test tải thật, chỉ chạy khi `HP_LIVE_DOWNLOAD=1`).
- **Đính chính giấy phép:** `--enable-version3` KHÔNG phải GPL — bản
  BtbN lgpl là **LGPL v3** (LICENSE.txt trong archive + BtbN README).
  Binary imageio-ffmpeg cũ vẫn là GPL v3 (dự phòng cho máy dev).
- **Chưa xong (không tính là đạt):**
  - **C22 — binary Windows chưa chạy thật trên Windows** (chỉ đo
    checksum archive + SHA-256 `ffmpeg.exe` trong zip trên Linux).
    Kiểm ở TK4.1 trên runner Windows.
  - **Chưa có endpoint API / nút UI nào gọi `download()`** — MP3 vẫn
    báo 400 "không có FFmpeg" khi chưa có binary. Cần ticket nối tiếp:
    `POST /api/ffmpeg/download` + nút "Tải FFmpeg" ở tab Cài đặt.
  - macOS / Windows ARM chưa có bản tải sau ghim.
