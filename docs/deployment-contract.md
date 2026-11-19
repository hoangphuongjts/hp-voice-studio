# Hợp đồng triển khai — HP Voice Studio v1 (TK4.6, SPEC §16)

> Bản đầy đủ của SPEC v1.3 §16 (GPT2 TH-12 → TH-24). Một chỗ duy nhất
> chốt môi trường chạy. Mọi mục chưa đo ghi **CHƯA ĐO** + ticket đo.
> Ngày: 19/11/2026 · Nhánh: `build/v1`.

## 1. Môi trường đích

| Hạng mục | Chốt ở v1.3 |
|---|---|
| OS đích | Windows 10/11 64-bit (chính); Linux (máy Annie, dùng được) |
| Python | **3.12** (khớp `.python-version` upstream; TK4.1 pin) |
| SDK | `vieneu==3.8.4`; backbone `pnnbao-ump/VieNeu-TTS-v3-Turbo`, subfolder `onnx_update` (fp32) / `onnx_int8` (int8); revision HF đã đo: snapshot `61b85e3d937fbbacb387714180e8182823512523` (TK1.3) |
| CPU/RAM tối thiểu | 4 nhân / 8 GB RAM / 3 GB trống (theo CIT) — **CHƯA ĐO trên máy anh (C6/C12)** |
| Ổ đĩa | Model 822,4 MB đủ 5 thành phần (tối thiểu ONNX/CPU 580,5 MB — `docs/model-download.md`) + FFmpeg ~165 MB tải sau (Linux đo thật; Windows đo ở TK4.1) + history tối đa 5 GB + cache (trần ở TK2.3) |
| Cổng | API `127.0.0.1:8124` duy nhất; fail-fast khi bận (§4); không tự nhảy cổng |
| Mạng lần đầu | Cần mạng để tải model (HF) + pip; sau đó offline hoàn toàn (kiểm chứng chặn mạng ở T1.1) |
| Runtime Windows | WebView2 (kiểm tra ở C9) + VC++ Redistributable (kiểm tra ở TK4.7) + ONNX Runtime DLLs (collect ở TK4.1) |
| Vỏ desktop | pywebview/WebView2 (TK4.8, Q20); đóng cửa sổ → dừng server + giải phóng cổng (TH-26); ẩn console |
| V4 | Opt-in, key người dùng nhập, tắt mặc định; fallback V3 (§3.3, ADR-10) |
| Dữ liệu | SPEC §6 (đường dẫn theo OS — SUY LUẬN, chờ anh chốt Q17): Windows `%LOCALAPPDATA%\HPVoiceStudio\`, Linux `~/.local/share/HPVoiceStudio/` |
| Tài liệu đi kèm | README + LICENSE (HP) + NOTICE (ghi công + GPL v3 FFmpeg + source offer) + file này |

## 2. Bảng cổng (SPEC §4)

| Cổng | Chủ sở hữu | Ghi chú |
|---|---|---|
| 8123 | Server TTS của MODOLIVIO | HP **không dùng** 8123 (TH-13) |
| **8124** | **HP Voice Studio API** | Mặc định duy nhất; bận → fail-fast, thoát mã 2 |
| 8001 | CIT Voice Studio | Kiểm tra trùng ở C8 |
| 8000 / 7860 | Upstream VieNeu demo | Kiểm tra trùng ở C8 |

Kiểm tra trước khi chạy: `python scripts/check_port.py` (bận → báo rõ,
không tự nhảy cổng). Cổng đang chiếm chỉ xác nhận được trên máy anh (C8).

## 3. Cài đặt từ source (môi trường dev / máy anh trước khi có .exe)

```bash
# Linux
python3.12 -m venv .venv
TMPDIR=$PWD/.tmp-pip .venv/bin/pip install --no-cache-dir -r requirements.txt
cp config.example.yaml config.yaml
.venv/bin/python scripts/download_model.py   # tải model lần đầu (cần mạng)
.venv/bin/python scripts/run_server.py       # http://127.0.0.1:8124, UI tại /ui
```

Windows: như trên với `py -3.12 -m venv .venv` +
`.venv\Scripts\pip install -r requirements.txt`. Chi tiết đầy đủ:
`README.md` (mục Cài đặt). `/tmp` trên máy ảo chỉ 512 MB — cài pip
đặt `TMPDIR` dưới workspace.

## 4. Đóng gói (.exe / installer — TK4.1/TK4.2)

- **Windows:** build bằng GitHub Actions Windows runner
  (`windows-latest`, workflow `.github/workflows/build-windows.yml`),
  không build trên Linux. Artifact `.exe`/installer + file `.sha256`;
  kiểm SHA-256 trước khi cài. Smoke test `.exe` trên runner sạch
  (không Python, không repo) phải pass rồi mới đưa sang máy anh (C1).
  **Trạng thái: chưa có trong đợt TK4-Release này** (TK4.1/TK4.2 do
  agent TK4-PACKAGE phụ trách; `packaging/windows/` hiện trống).
- **PyInstaller collect (TH-18 — thiếu là `.exe` chết lúc chạy):**
  `--collect-all keyring`, `--collect-all onnxruntime`,
  `--collect-all tokenizers`; model theo Q2 (kèm sẵn thì `--add-data`
  model + checksum, tải lần đầu thì màn hình tải + checksum).
  **KHÔNG collect binary `imageio_ffmpeg/binaries/*`** (Q21 — FFmpeg
  tải cài sau, TK4.9).
- **Linux:** build tương đương trên máy dev → chạy → T1.2 + T2.1 pass.
- Ngân sách bộ cài (Q2 — chưa chốt): ~300–400 MB kèm model sẵn (không
  cộng ~165 MB FFmpeg vì FFmpeg tải sau).

## 5. Runtime Windows (TK4.7 — kiểm tra trên máy sạch)

- WebView2 Runtime có sẵn không (C9 — `.exe` chưa ký còn gặp
  SmartScreen, cần hướng dẫn bấm qua).
- VC++ Redistributable (x64) — ONNX Runtime cần.
- ONNX Runtime DLLs — collect ở TK4.1.
- Thư mục cài có dấu tiếng Việt/khoảng trắng (VD
  `C:\Người dùng\HP Voice Studio`) — test T4.5 (C21, chưa chạy).

## 6. Vỏ desktop (TK4.8, ADR-11)

- pywebview/WebView2 (Q20) mở UI local; ẩn console; sở hữu vòng đời
  server (đóng cửa sổ → dừng server + giải phóng 8124); chống mở trùng
  instance (mutex/lock file); graceful shutdown (T4.5, C19).

## 7. Dữ liệu và giới hạn vận hành

| Hạng mục | Giá trị |
|---|---|
| Text mỗi request TTS | 20.000 ký tự (vượt → 400) |
| Batch | 500 mục/lần — số tạm chờ đo RAM (TK2.6) |
| Hàng đợi | 1 job chạy, tối đa 20 job chờ (đầy → 429), TTL 60 phút (Q16) |
| History | Tối đa 5 GB — vượt thì chặn tạo mới + báo rõ |
| Preview cache | Trần mặc định 200 MB, dọn file cũ nhất khi vượt |
| Tốc độ | 0,75×–1,5× |
| Thư mục dữ liệu | Theo OS (§6) — xem mục 1; `config.yaml` đổi được `output_dir` / `history_dir` / `voices_file` / `dict_file` |

## 8. Hiệu năng tham chiếu (số đo thật trên VM — không thay cho máy anh)

- VM Linux CPU chia sẻ ~1,5 CPU: RTF fp32 ~1,92 / int8 ~1,43 (chậm hơn
  real-time trên VM); upstream README (i5 12th-gen 6 nhân): fp32 0,62 /
  int8 0,37. Ngưỡng mượt RTF ≤ 1 + chunk đầu ≤ 500 ms đo lại trên CPU
  Windows thật của anh (C6). Chi tiết: `docs/cpu-reference.md`.
- Time-stretch: mặc định FFmpeg `atempo`, dự phòng librosa (RTF warm
  ≪ 1 cả hai; atempo giữ năng lượng tốt hơn). Chi tiết:
  `docs/stretch-decision.md`.

## 9. Bảo mật vận hành (local-only)

- API chỉ bind `127.0.0.1` mặc định (ADR-12). LAN opt-in, v1 không bắt
  buộc key; bật lại L1–L4 (SPEC §9.3) khi mở LAN.
- Key V4 lưu qua `keyring`/DPAPI, không plaintext trên Windows, không
  log, không commit, không trả lại qua API (TH-05, ADR-09).
- Key LAN (nếu bật sau này) lưu cùng cơ chế.

## 10. Tài liệu đi kèm bản phát hành

- `README.md` (cài đặt, chạy, dùng từng tab, V4, đóng gói, nâng cấp SDK,
  khắc phục sự cố, giấy phép) · `LICENSE` (Apache 2.0 của HP) ·
  `NOTICE` (ghi công VieNeu-TTS + license giọng + FFmpeg GPL v3 +
  source offer) · `SPEC.md` v1.3 · `docs/api-contract.md` (21 endpoint) ·
  `docs/voice-fallback-map.md` · `docs/v4-billing.md` ·
  `docs/model-download.md` · `docs/cpu-reference.md` ·
  `docs/upgrade-sdk.md` · `docs/decisions/` (ADR-07/11/12/13) · file này.
- Bằng chứng release gate: `evidence/release-gate/RELEASE-GATE-v1.md`
  (+ `pytest-full.log`, `node-check.log`).
