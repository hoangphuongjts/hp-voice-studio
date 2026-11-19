# Giảm kích thước gói Linux — báo cáo evidence (19/11/2026)

- **Trước:** `dist/hp-voice-studio/` **596 MB** (vượt ngân sách Q2 ~300–400 MB)
- **Sau:** `dist/hp-voice-studio/` **277 MB** — tiết kiệm **319 MB (−54%)**, **TRONG ngân sách Q2**
- **Venv:** 921 MB → 629 MB (−292 MB)
- **Nhánh:** `build/v1` (chưa push — repo chưa có remote)

## Tử huyệt trước (Charter v1.1)

1. **Loại nhầm dependency làm app chết lúc chạy** (đặc biệt SDK v3 Turbo
   cần librosa/scipy lúc infer?) → đối phó: thí nghiệm chặn import + chạy
   TTS/clone thật TRƯỚC khi loại (xem §2).
2. **Model load fail sau khi gỡ** → đối phó: smoke test frozen + API thật
   sau rebuild (xem §5).
3. **Đường time-stretch mất fallback khi không có FFmpeg** → đối phó:
   lỗi rõ ràng `StretchUnavailableError` (API trả 400 + hướng dẫn tải
   FFmpeg), không crash 500 (xem §3).
4. **Spec PyInstaller sai REPO_DIR chặn mọi build** → phát hiện khi rebuild,
   đã sửa off-by-one (xem §4).

## 1. Breakdown thật (đo bằng `du`)

| Thành phần | Trước (MB) | Sau (MB) | Ghi chú |
|---|---:|---:|---|
| llvmlite | 171 | 0 | LOẠI — dep của numba/librosa |
| onnxruntime | 73 | 73 | GIỮ — engine TTS |
| pymupdf | 53 | 53 | GIỮ — tính năng đọc PDF thật |
| scipy | 42 | 0 | LOẠI — dep của librosa/sklearn |
| scipy.libs | 30 | 0 | LOẠI — theo scipy |
| numpy.libs | 23 | 23 | GIỮ — numpy |
| pandas | 18 | 0 | LOẠI — bị kéo vào qua sklearn |
| sklearn | 16 | 0 | LOẠI — dep của librosa |
| pillow.libs | 15 | 0 | LOẠI — theo PIL (gradio/hf inference) |
| numpy | 14 | 14 | GIỮ |
| cryptography | 14 | 14 | GIỮ — keyring (lưu key V4) |
| tokenizers | 12 | 12 | GIỮ — SDK |
| hf_xet | 11 | 11 | GIỮ — tải model |
| lxml | 9,4 | 9,4 | GIỮ — python-docx (đọc DOCX) |
| libpython3.12.so | 8,7 | 8,7 | GIỮ |
| sea_g2p | 6,9 | 6,9 | GIỮ — phonemizer của SDK |
| numba | 4,2 | 0 | LOẠI — dep của librosa |
| PIL | 4,1 | 0 | LOẠI — bị kéo qua gradio/hf inference |
| librosa | 0,05 | 0 | LOẠI — chỉ còn dự phòng tùy chọn (máy dev) |
| exe (PYZ nhúng) | 35 | 18,7 | Giảm nhờ .pyc gradio/sklearn/scipy ra khỏi PYZ |
| **Tổng dist** | **596** | **277** | **−319 MB (−54%)** |

Các gói khác trong venv nhưng KHÔNG có trong dist cũ (đã được PyInstaller
loại tự nhiên): gradio 82 MB (bị kéo vào qua `huggingface_hub._webhooks_server`),
imageio_ffmpeg 165 MB (binary GPL v3 — bộ lọc Q21 trong spec đã loại đúng;
trong dist cũ chỉ còn README 4 KB).

## 2. Kiểm chứng runtime trước khi loại (quyết định giữ/loại)

Thí nghiệm chặn import: `evidence/size-reduction/block_test.py` — chặn
`librosa, numba, llvmlite, scipy, sklearn, pandas, joblib, pooch, gradio, PIL`
rồi chạy đường chạy thật (log: `block_test.log`).

| Bước | Kết quả |
|---|---|
| Import các module hpvoice (engine, post, srt_dubber, routes_tts, readers, ffmpeg_manager) | PASS |
| Nạp model v3 Turbo + list 25 giọng preset | PASS |
| Synthesize thật, giọng Hải Đăng | PASS (103.680 samples @ 48 kHz) |
| Clone: encode_reference + add_voice + synthesize giọng clone | PASS (72.960 samples) |
| Import server hp_api | PASS |

**Kết luận:** SDK v3 Turbo KHÔNG cần librosa trên đường CPU. Các chỗ SDK
dùng librosa đều có fallback: `base._load_ref_mono` → soundfile+soxr,
`v3turbo` trim → numpy; `_v3_turbo_engine/` không nhắc librosa lần nào;
`turbo.py` (encode_reference) và `core_xpu.py` (torch/XPU) không thuộc đường
v3 Turbo. **Đính chính** docs/stretch-decision.md: nhận định "SDK vẫn cần
librosa" là SAI với đường v3 Turbo CPU.

**Giữ lại (chưa giảm được):**
- `onnxruntime` 73 MB — engine, không thay thế được.
- `pymupdf` 53 MB — tính năng đọc PDF thật (giữ thứ tự cell của bảng +
  phát hiện PDF scan). Thay bằng pypdf sẽ mất 2 hành vi này → không đổi
  ở đợt này.
- `cryptography` 14 MB, `lxml` 9,4 MB, `hf_xet` 11 MB — dependency của
  tính năng thật (keyring / DOCX / tải model).
- `gradio_client` 456 KB + `hf-gradio` 24 KB còn trong venv (client nhỏ
  của huggingface_hub, không đáng kể, không exclude).

## 3. Thay đổi code (để loại librosa an toàn)

- `src/hpvoice/audio/post.py`:
  - `time_stretch()` đổi engine mặc định `librosa` → **`atempo`** (qua file
    tạm + `FFmpegManager.run_atempo`; atempo đã đo tốt hơn librosa về
    RMS/đỉnh — xem docs/stretch-decision.md).
  - Thêm `StretchUnavailableError(ValueError)`: không có FFmpeg và không có
    librosa → lỗi rõ ràng bằng tiếng Việt, hướng dẫn tải FFmpeg ở tab Cài
    đặt (thay vì ImportError khó hiểu / crash).
  - `stretch_audio_file()`: fallback librosa có guard (thiếu librosa →
    `StretchUnavailableError`).
  - `engine="librosa"` tường minh vẫn chạy khi librosa còn cài (máy dev).
- `src/hpvoice/api/routes_tts.py`: bắt `StretchUnavailableError` ở cả 2
  đường synthesize → HTTP 400 (không 500). `routes_srt` không cần sửa
  (ValueError → 400 sẵn có).
- `tests/test_audio_post.py`: test tỉ lệ thời lượng giữ nguyên (giờ chạy
  atempo); test fallback viết lại theo 2 nhánh (có/không có librosa); thêm
  test engine librosa thiếu → lỗi rõ ràng.
- `requirements.txt`: gỡ `librosa==1.0.1` (kèm chú thích); gỡ khỏi venv:
  librosa, numba, llvmlite, scipy, scikit-learn, pandas, gradio, pillow,
  joblib, pooch (venv 921 → 629 MB). Lưu ý: thư mục librosa còn sót lại
  sau `pip uninstall` chỉ chứa cache numba (.nbi/.nbc) — đã xóa tay.
- `packaging/windows/hp-voice-studio.spec`: bỏ `librosa` khỏi hiddenimports;
  thêm excludes: librosa, numba, llvmlite, scipy, sklearn, pandas, gradio,
  PIL, joblib, pooch (kèm chú thích + trỏ về báo cáo này).
- `docs/stretch-decision.md`: bổ sung đính chính "SDK vẫn cần librosa" là sai.

## 4. Sửa lỗi spec chặn mọi build (phát hiện khi rebuild)

- Lỗi: `REPO_DIR = Path(SPECPATH).resolve().parent.parent.parent` — sai
  off-by-one vì `SPECPATH` của PyInstaller là **thư mục** chứa spec (không
  phải đường dẫn file spec), nên REPO_DIR trỏ ra ngoài repo (`/home/hatch/
  workspace`) và build lỗi `script '.../src/hpvoice/shell.py' not found`.
  Lỗi này tồn tại từ commit TK4 (4d85645) — spec chưa từng build thành công
  từ chính nó (build Windows CI chưa chạy được; dist Linux cũ build bằng
  cách khác). Đã sửa thành `.parent.parent` + ghi chú trong spec.
- Build lại: `.venv/bin/python -m PyInstaller --noconfirm --clean
  --distpath dist --workpath build packaging/windows/hp-voice-studio.spec`
  (log: `pyinstaller-build2.log`; lần build đầu `pyinstaller-build.log`
  thất bại đúng lỗi trên). Sau build copy `ui/` ra gốc dist (bước post-build
  bắt buộc theo spec).

## 5. Kiểm chứng sau rebuild

### 5.1 Gói frozen mới
- Kích thước: **277 MB** (trước 596 MB). Exe 35 → 18,7 MB.
- 10 gói loại đều vắng mặt trong `dist/_internal/` (kiểm bằng `ls`).
- Không có binary FFmpeg nào trong dist (Q21 giữ nguyên — `find` không
  trả file nào; `imageio_ffmpeg` chỉ còn code trong PYZ).
- Analysis toc mới: 23 module quan trọng đều có (9 routes_*, v3_engine,
  post, ffmpeg_manager, srt_dubber, vieneu, onnxruntime, soundfile, fitz,
  docx, fastapi, uvicorn, keyring, tokenizers); tên các gói loại chỉ xuất
  hiện trong chính danh sách `excludes` của spec (dương tính giả khi grep
  thô — đã đối chiếu ngữ cảnh).
- Frozen `--version` / `--check`: PASS (`HP Voice Studio 0.1.0`, kiểm
  import OK, không nạp model).

### 5.2 Smoke test API thật (server nguồn, venv đã gỡ đúng các gói như frozen)
Vì VM headless không có GUI backend (pywebview cần QT/GTK — cả bản frozen
cũ và mới đều không mở được cửa sổ ở đây; xem §5.3), API được kiểm tra bằng
server nguồn `scripts/run_server.py` chạy trên venv đã gỡ các gói (tập
dependency giống hệt frozen), cổng 127.0.0.1:8124, `HF_HUB_OFFLINE=1`:

| Kiểm tra | Kết quả |
|---|---|
| GET /health | 200 `{"status":"starting","engine":"v3",...}` |
| GET / → 302 /ui/index.html; GET /ui/index.html | 302, 200 |
| GET /v1/voices | 25 giọng, có Hải Đăng |
| POST /v1/audio/speech speed 1.0, wav | 200, WAV 314.924 byte, pcm_s16le 48 kHz mono 3,28 s |
| POST /v1/audio/speech speed 1.25, wav | 200, WAV 252.354 byte, 2,63 s (= 3,28/1,25 ✓ — atempo đúng tỉ lệ, không librosa) |
| POST /v1/audio/speech format mp3 | 200, MP3 61.101 byte, 2,48 s (FFmpeg hệ thống) |

File output: `evidence/size-reduction/smoke/` (speech-1x.wav, speech-1x25.wav,
speech.mp3). Log server: `smoke-server.log`.

### 5.3 Giới hạn kiểm chứng (chưa kiểm chứng thật)
- **Cửa sổ desktop của bản frozen chưa mở được trên VM này** (pywebview
  cần QT/GTK; venv không có qtpy/gi; thử stub webview qua PYTHONPATH và
  sitecustomize đều không có tác dụng với app frozen — đã gỡ shim, không
  để lại gì trong dist). Server của bản frozen đã khởi động được (log in
  URL trước khi crash ở cửa sổ). **Cần kiểm chứng thật:** mở bản frozen
  trên máy Windows/macOS có GUI (C-item — giống giới hạn của bản 596 MB
  trước đây, không phải hồi quy do đợt này).
- API của bản frozen chưa chạy trực tiếp (lý do trên); đã kiểm chứng qua
  server nguồn + tập dependency giống hệt + frozen --version/--check +
  Analysis toc. Cần kiểm chứng thật trên máy có GUI.
- RTF/chất lượng nghe atempo vs librosa trên máy Windows thật: giữ nguyên
  từ docs/stretch-decision.md (chờ kiểm chứng thật).

## 6. Test suite

- Trước thay đổi: 307 passed, 1 skipped (commit c29f0e3).
- Sau thay đổi (chạy 19/11, log `pytest-full.log`): 307 passed, 1 skipped,
  **1 failed** — `test_phat_hien_vnni_tren_vm_nay`.
- **FAIL này KHÔNG do đợt này:** test assert host có cả AVX-VNNI +
  AVX512-VNNI (ghi ở T1-REPORT cho host cũ AMD EPYC 9D25). Host đã đổi
  sang AMD EPYC 9D64 (chỉ còn avx512_vnni, `/proc/cpuinfo` không còn cờ
  avx_vnni) — VM migrate/restart giữa đợt làm việc. Logic phát hiện không
  sai (báo đúng cờ host mới). File `test_cpu.py`/`cpu_detect.py` không nằm
  trong diff đợt này.
- **Đã sửa test** (ghi rõ trong test): chỉ assert có VNNI (dạng nào cũng
  được) + mặc định int8; logic từng cờ đã có test monkeypatch riêng.
- Chạy lại `tests/test_cpu.py`: **7/7 PASS** (log `pytest-cpu.log`).
- Chạy lại full suite sau sửa: **308 passed, 1 skipped trong 318,21 s**
  (log `pytest-full-after.log`) — 308 = 307 cũ + 1 test mới
  (`test_time_stretch_librosa_thieu_bao_loi_ro`). **100% mục chạy được PASS.**

## 7. File thay đổi (commit trên nhánh build/v1)

- `src/hpvoice/audio/post.py` — atempo mặc định + StretchUnavailableError
- `src/hpvoice/api/routes_tts.py` — map lỗi stretch → HTTP 400
- `tests/test_audio_post.py` — test atempo + 2 nhánh fallback + test lỗi rõ
- `tests/test_cpu.py` — sửa test VNNI theo host mới (ghi rõ lý do)
- `packaging/windows/hp-voice-studio.spec` — excludes + sửa REPO_DIR off-by-one
- `requirements.txt` — gỡ librosa
- `docs/stretch-decision.md` — đính chính "SDK cần librosa" là sai
- `evidence/size-reduction/*` — báo cáo này + script/log/file smoke
  (file audio smoke `smoke/*.wav|*.mp3` chỉ để trên đĩa, KHÔNG track theo
  `.gitignore` — giống file WAV T1; số đo ffprobe đã ghi trong báo cáo này).
- KHÔNG commit: `dist/`, `build/` (gitignored); `evidence/tk1-engine/*.json`
  (số đo đổi theo mỗi lần chạy test — đã modified từ trước đợt này, để nguyên).
