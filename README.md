# HP Voice Studio

Studio TTS tiếng Việt chạy local, dùng cá nhân — không thương mại trong
2026. Engine chính **VieNeu-TTS v3 Turbo** (SDK `vieneu==3.8.4`,
Apache 2.0): 25 giọng preset, 48 kHz, chạy offline hoàn toàn sau lần tải
model đầu tiên. **V4 cloud là tùy chọn** (key người dùng tự nhập trong
Cài đặt, mặc định tắt, lỗi → fallback V3 + báo rõ lý do và giọng mới).

> **Trạng thái bản này (v1, nhánh `build/v1`):** TK1 (engine V3) +
> TK2 (API + V4 + tính năng) + TK3 (UI 8 tab) đã xong và merge main,
> 265/265 test PASS trên máy ảo (xem
> `evidence/release-gate/RELEASE-GATE-v1.md`). Đợt TK4-Release này làm
> tài liệu + FFmpeg checksum + release gate. **Bản Windows `.exe` chưa
> có trong đợt này** — đóng gói Windows/Linux (TK4.1/TK4.2) do agent
> TK4-PACKAGE phụ trách; xem mục [Đóng gói](#đóng-gói).
>
> **Đặc tả đầy đủ:** `SPEC.md` v1.3 (33 tử huyệt, 40 ticket, 21 điểm
> "chờ kiểm chứng thật" C1..C21). README này là hướng dẫn dùng; chỗ nào
> README và SPEC khác nhau thì SPEC là chuẩn.

## Mục lục

- [Yêu cầu](#yêu-cầu)
- [Cài đặt](#cài-đặt)
- [Tải model lần đầu](#tải-model-lần-đầu)
- [Chạy server + mở UI](#chạy-server--mở-ui)
- [Dùng từng tab](#dùng-từng-tab)
- [Clone giọng + cam kết](#clone-giọng--cam-kết)
- [V4 cloud tùy chọn + phí](#v4-cloud-tùy-chọn--phí)
- [API local](#api-local)
- [Cấu hình](#cấu-hình)
- [Đóng gói](#đóng-gói)
- [Nâng cấp SDK](#nâng-cấp-sdk)
- [Khắc phục sự cố](#khắc-phục-sự-cố)
- [Giấy phép + ghi công](#giấy-phép--ghi-công)
- [Chờ kiểm chứng thật](#chờ-kiểm-chứng-thật)

## Yêu cầu

| Hạng mục | Yêu cầu |
|---|---|
| OS đích | Windows 10/11 64-bit (chính); Linux (dùng được) |
| Python | **3.12** (khớp `.python-version` của upstream) |
| CPU/RAM tối thiểu | 4 nhân / 8 GB RAM (theo CIT — CHƯA ĐO trên máy anh, C6/C12) |
| Ổ đĩa | Model ~**822 MB** đủ 5 thành phần (tối thiểu để chạy ONNX/CPU: **580,5 MB** — xem `docs/model-download.md`) + FFmpeg ~165 MB tải sau + history tối đa 5 GB |
| Mạng lần đầu | Cần mạng để tải model (Hugging Face) + pip; sau đó offline hoàn toàn (đã kiểm chứng chặn mạng ở T1.1) |
| Cổng | API `127.0.0.1:8124` duy nhất; bận → fail-fast, không tự nhảy cổng |

**Hiệu năng đo thật trên máy ảo (tham khảo, không thay cho máy anh):**
VM Linux CPU chia sẻ ~1,5 CPU đo RTF fp32 ~1,92 / int8 ~1,43 — **chậm
hơn real-time trên VM này** (upstream README đo trên i5 12th-gen 6 nhân:
fp32 0,62 / int8 0,37). Ngưỡng mượt RTF ≤ 1 phải đo lại trên CPU Windows
thật của anh (C6). Chi tiết: `docs/cpu-reference.md`.

## Cài đặt

### Linux

```bash
git clone <repo-hp-voice-studio> && cd hp-voice-studio
python3.12 -m venv .venv
TMPDIR=$PWD/.tmp-pip .venv/bin/pip install --no-cache-dir -r requirements.txt
cp config.example.yaml config.yaml   # sửa theo máy của mình (không commit config.yaml)
```

Lưu ý: `/tmp` trên máy ảo chỉ 512 MB — cài pip phải đặt `TMPDIR` dưới
workspace (xem `evidence/t1-first-wav/T1-REPORT.md`). Mọi dependency
đều ghim version trong `requirements.txt` (`vieneu==3.8.4`,
`imageio-ffmpeg==0.8.1`, `keyring==25.7.0`, `fastapi==0.165.0`, …).

### Windows

```powershell
# Cần Python 3.12 (python.org) + Git. Mở PowerShell trong thư mục repo:
py -3.12 -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy config.example.yaml config.yaml
.venv\Scripts\python scripts\download_model.py
```

Lưu ý Windows (chưa kiểm chứng thật trên máy anh — C1/C9/C21):

- Bản `.exe` đóng gói (TK4.1) chưa có trong đợt này; chạy từ source
  theo hướng dẫn trên cho tới khi có `.exe`.
- Cài vào thư mục **không có dấu tiếng Việt/khoảng trắng** nếu gặp lỗi
  đường dẫn (test T4.5 chưa chạy trên máy thật — C21).
- Cần WebView2 + VC++ Redistributable cho vỏ desktop (kiểm tra ở TK4.7);
  chạy API + UI web thì không cần hai thứ này.

## Tải model lần đầu

```bash
.venv/bin/python scripts/download_model.py            # tải đủ 5 thành phần
.venv/bin/python scripts/download_model.py --verify-only   # chỉ kiểm tra cache
.venv/bin/python scripts/download_model.py --repair        # chỉ tải lại file hỏng
```

- Dung lượng thật theo từng thành phần (đo 19/11/2026, xem
  `docs/model-download.md`): backbone fp32 453,4 MB + int8 157,8 MB +
  denoiser 40,7 MB + tokenizer 84,1 MB + codec ONNX 86,4 MB = **822,4 MB**.
  Repo tokenizer 84,1 MB không cần cho đường ONNX/CPU (đã kiểm chứng).
- Model revision HF đã đo: snapshot
  `61b85e3d937fbbacb387714180e8182823512523` của repo
  `pnnbao-ump/VieNeu-TTS-v3-Turbo` (subfolder `onnx_update` / `onnx_int8`).
- Tải dở được tiếp tục (resume); cache hỏng phát hiện bằng checksum
  SHA-256 trong manifest `evidence/tk1-engine/model-download.json` và chỉ
  tải lại file hỏng, không xoá toàn bộ cache.
- **Offline hoàn toàn:** sau khi tải xong, chạy với
  `HF_HUB_OFFLINE=1` vẫn nạp engine + tạo WAV mới được (đã kiểm chứng ở
  T1.1 — test `test_offline_hoan_toan_tao_wav_moi`).

## Chạy server + mở UI

```bash
.venv/bin/python scripts/run_server.py   # mặc định http://127.0.0.1:8124
curl http://127.0.0.1:8124/health
```

- Server kiểm tra cổng trước bằng `scripts/check_port.py`: cổng 8124 bận
  → fail-fast, thoát mã 2, **không tự nhảy cổng**. Cổng 8123 đã có chủ
  (server TTS của MODOLIVIO) — không dùng 8123 cho HP.
- Engine V3 nạp lười: model chỉ nạp khi request TTS/voices đầu tiên tới;
  khởi động server không chờ tải model.
- Mở UI trong trình duyệt: **http://127.0.0.1:8124/ui** (UI tĩnh mount
  tại `/ui`). Vỏ desktop pywebview/WebView2 (TK4.8) sẽ mở chính địa chỉ
  này trong cửa sổ app; đóng cửa sổ → dừng server + giải phóng cổng.
- Server chỉ bind `127.0.0.1` mặc định (quyết định local-only 04:20
  19/11). Mở LAN là opt-in trong Cài đặt; v1 không bắt buộc key LAN
  (bật lại lớp bảo mật khi mở LAN — xem SPEC §9.3).

## Dùng từng tab

UI chia 3 nhóm: **Tạo / Thư viện / Hệ thống** (giữ cấu trúc studio chuẩn
của VieNeu Desktop + CIT, chỉ đổi thương hiệu sang HP).

### Nhóm Tạo

| Tab | Dùng thế nào |
|---|---|
| **Phòng thu** | Nhập text (tối đa 20.000 ký tự/request) → chọn giọng (dropdown: 25 preset + clone, ghi rõ giới tính/vùng/phong cách) → chọn engine V3/V4 → tốc độ 0,75×–1,5× → bấm Tạo → nghe lại → tải WAV/MP3. Chèn cảm xúc `[cười]` `[thở dài]` `[hắng giọng]`; thẻ nghỉ `[nghỉ 2s]` / `[nghỉ 500ms]` (tối đa 10 s/thẻ). Từ điển phát âm (nút Từ điển, CSV import/export). Tạo kèm `.srt` (mốc suy bằng `SrtWriter`, ±0,3 s/câu cho 10 câu đầu). |
| **Hội thoại / Podcast** | Kịch bản = danh sách (nhân vật, câu thoại). **Mỗi nhân vật khoá 1 giọng cố định** xuyên suốt — validate trước khi chạy, báo lỗi nếu nhân vật chưa gán giọng; mở lại kịch bản vẫn đúng giọng (mapping lưu trong file kịch bản). Tối đa 8 nhân vật. |
| **Lồng tiếng .srt** | Nạp file `.srt` (hoặc `.vtt`) → app căn giờ từng câu (tốc độ hiệu dụng 0,75×–1,5×; câu dài thì lấn khoảng lặng → đẩy câu sau, **không bao giờ cắt chữ**) → xuất audio + file SRT đã chỉnh mốc + danh sách câu bị lùi. Sai số mốc mục tiêu ±0,3 s/câu (p95). |
| **Đọc file** | Nạp PDF / DOCX / TXT → trích text → làm sạch → đưa sang Phòng thu tạo giọng. **PDF scan: v1 không OCR** — app báo rõ, không bịa text. DOCX có bảng giữ đúng thứ tự cell. |
| **Tạo hàng loạt** | File TXT/JSON/SRT nhiều mục (tối đa 500 mục/lần — số tạm chờ đo RAM) → tạo từng mục, ghi ra đĩa ngay → tải ZIP. 1 mục lỗi thì các mục khác vẫn xong, mục lỗi báo rõ + thử lại riêng được. |

### Nhóm Thư viện

| Tab | Dùng thế nào |
|---|---|
| **Bản đã tạo** | Danh sách history: nghe lại / tải lại / xoá từng bản; tổng dung lượng hiển thị đối chiếu được bằng `du`. Trần history mặc định 5 GB — vượt trần thì **chặn tạo mới + báo rõ** (vẫn cho xoá/xuất bớt để mở lại). History ghi atomic (file tạm + rename) + backup, tắt đột ngột không corrupt. |
| **Giọng của tôi** | Quản lý giọng clone: tạo (xem mục dưới), nghe thử, xoá/gỡ giọng khi khiếu nại (bắt buộc ghi lý do). Giọng clone lưu local, không đồng bộ cloud. |

### Nhóm Hệ thống

| Tab | Dùng thế nào |
|---|---|
| **Cài đặt** | Giọng mặc định, precision (auto/fp32/int8 — auto theo CPU: có VNNI → int8, không → fp32), thư mục lưu, key V4 (nhập/xoá, kiểm tra bằng `GET /v1/balance`), ngưỡng cảnh báo phí V4 (mặc định 100.000 ký tự/phiên), bật/tắt chuẩn hoá tiếng Việt, API LAN (opt-in). Cài đặt bền vững qua khởi động lại. Đổi precision fp32→int8 thì RTF giảm và file vẫn 48 kHz/mono. |

**Giới hạn chung:** text 20.000 ký tự/request (vượt → 400); batch
500 mục/lần (vượt → 400); hàng đợi 1 job chạy + tối đa 20 job chờ
(đầy → 429, TTL job chờ 60 phút); tốc độ 0,75×–1,5× (ngoài → 400).
Request TTS thứ 2 khi CPU bận sẽ **xếp hàng** (202 + `job_id`), không 429.

## Clone giọng + cam kết

Chỉ clone **giọng của chính mình hoặc giọng đã được chủ giọng đồng ý**.
Hai cách nạp mẫu (Q13 — đã chốt 04:32 19/11: giữ cả hai):

1. **Thu micro trực tiếp** trong tab Giọng của tôi.
2. **Upload file** WAV/MP3/M4A (MP3/M4A giải mã bằng FFmpeg — xem mục
   FFmpeg dưới đây).

Quy tắc bắt buộc (SPEC TH-04/TH-17):

- Clip **3–8 giây**, 1 người nói, không nhạc nền (app validate độ dài).
- Trước khi lưu giọng clone: màn hình **cam kết quyền sử dụng** (checkbox
  + ghi log cam kết kèm thời gian, lưu cùng giọng, xoá cùng nhau).
  Không tick cam kết → API trả 400, không tạo giọng.
- Metadata giọng clone có `owner` + ngày cam kết; không xuất file ref gốc.
- **Cơ chế gỡ khi khiếu nại:** tab Giọng của tôi → Xoá giọng → bắt buộc
  ghi lý do (`DELETE /api/voices/{voice_id}?reason=...`).
- Giọng nói là dữ liệu cá nhân (Nghị định 13/2023); nội dung mô phỏng
  giọng người thật khi đăng công khai phải ghi rõ "giọng đọc được tạo
  bằng AI" (Nghị định 147/2024).
- Cam kết là lời hứa, không phải xác minh danh tính — SPEC thừa nhận
  điều này; không dùng HP Voice Studio để giả mạo giọng người khác.

## FFmpeg — MP3 và giải mã (tải cài sau, Q21)

- Bộ cài **không đóng gói kèm binary FFmpeg** (Q21 — đã chốt 04:35
  19/11) nên bộ cài giữ 100% Apache 2.0. FFmpeg cần cho: xuất MP3 và
  giải mã MP3/M4A đầu vào cho clone giọng.
- Thứ tự tìm của `FFmpegManager`: (1) FFmpeg hệ thống (`ffmpeg` trong
  PATH) — ưu tiên; (2) binary LGPL đã tải về thư mục dữ liệu người
  dùng (`FFmpegManager.download()` — tải thật, xem dưới đây);
  (3) binary đi kèm wheel `imageio-ffmpeg==0.8.1` (dự phòng cũ, chỉ
  còn trên máy dev đã `pip install`); (4) không có → **chỉ xuất WAV +
  báo rõ**, không crash.
- **Tải thật (đo thật 19/11/2026, xem
  `evidence/ffmpeg-download/FFMPEG-DOWNLOAD-VERIFICATION.md`):**
  `download()` tải archive FFmpeg **LGPL tĩnh** từ BtbN/FFmpeg-Builds,
  release `autobuild-2026-11-18-12-39` (tag ngày cố định, không dùng
  URL "latest"), kiểm SHA-256 archive theo bảng ghim (đã đối chiếu với
  `checksums.sha256` do chính BtbN công bố), giải nén an toàn chỉ đúng
  file binary, kiểm chứng binary (`ffmpeg -version` + `-buildconf`
  không `--enable-gpl`/`--enable-nonfree` + có `libmp3lame`) rồi mới
  dùng. Tải có resume (file `.part`) + tiến trình qua
  `on_progress(bytes_done, bytes_total)`. Kích thước tải: ~137 MB
  (Linux x86_64) / ~172 MB (Windows x86_64). Binary lưu vào
  `<thư mục dữ liệu>/ffmpeg/`; hồ sơ tải ghi vào
  `ffmpeg-download.json`. Mất mạng: giữ `.part` để tải tiếp, báo
  tiếng Việt rõ ràng + hướng dẫn cài FFmpeg hệ thống.
- **Checksum SHA-256:** bảng ghim `FFMPEG_DOWNLOADS` trong
  `src/hpvoice/audio/ffmpeg_manager.py` (BtbN LGPL — Linux +
  Windows đã đo thật; Windows chỉ đo checksum, chưa chạy thật trên
  Windows — C22) và bảng `PINNED_FFMPEG_SHA256` (imageio wheel cũ,
  chỉ `linux-x86_64` đã đo: `0d709a0bed1a43f24cd2c420878c63afea4580671b6949ad19ed124572f3bc3d`).
  Platform chưa ghim thì app vẫn dùng binary nhưng ghi rõ "chưa có
  checksum ghim" và ghi SHA-256 đo được vào `ffmpeg-manifest.json`
  trong thư mục dữ liệu để đối chiếu tay. Checksum lệch bảng ghim →
  binary bị từ chối.
- **Giấy phép binary tải về: LGPL v3** (`LICENSE.txt` trong archive là
  văn bản LGPL v3; `ffmpeg -buildconf` không có `--enable-gpl` /
  `--enable-nonfree` — `--enable-version3` chỉ nâng LGPL lên v3,
  không phải GPL). Binary imageio-ffmpeg cũ (đường dự phòng) vẫn là
  GPL v3 — xem `NOTICE` (mục 3).
- **Chưa xong:** `download()` đã làm thật nhưng chưa có endpoint API
  hay nút UI nào gọi nó — MP3 vẫn báo lỗi "không có FFmpeg" khi chưa
  có binary (xem ADR-07).

## V4 cloud tùy chọn + phí

- V4 **mặc định TẮT**. Bật trong tab Cài đặt bằng cách nhập key của
  chính mình; key lưu qua `keyring` (Windows: DPAPI/Credential Manager;
  Linux: Secret Service, fallback file `secrets.json` quyền 0600),
  **không hardcode, không commit git, không log**. Nút "Xoá key" xoá
  khỏi store + ghi log đã xoá.
- V4 **không chạy local được** (độc quyền, không mã nguồn) — chỉ dùng qua
  Cloud API `https://api.vieneu.io/api/v1`. V4 clone giọng chỉ làm được
  trên web (vieneu.io), không qua API.
- **Tính phí theo ký tự** (chi tiết: `docs/v4-billing.md`):
  `phí (token) = max(50, số ký tự gửi) × billingMultiplier × globalMultiplier`
  (ví dụ trong OpenAPI: v4 = 3,4 — chỉ là ví dụ, số thật lấy từ
  `GET /v1/engines` với key thật). UI hiện ước tính ký tự trước khi gửi +
  cảnh báo khi vượt ngưỡng do người dùng đặt (mặc định 100.000 ký tự/phiên;
  lưu ý: ngưỡng tính bằng **ký tự**, phí thật tính bằng token sau nhân
  multiplier — 100.000 ký tự ≠ 100.000 token).
- **Bẫy phí `[nghỉ]` trên V4:** V4 xoá lặng lẽ thẻ `[nghỉ]` nên HP tách
  text thành nhiều đoạn, mỗi đoạn tính phí tối thiểu 50 ký tự — UI cảnh
  báo trước khi tạo bằng V4 khi text chứa `[nghỉ]`.
- **Kiểm tra key không đốt ký tự:** dùng `GET /v1/balance` (vừa ping key
  — 401 = key sai — vừa lấy số dư cho màn hình quota). Chưa kiểm chứng
  rằng gọi endpoint này không trừ token (C13).
- **Fallback V4 → V3:** khi chưa có key / 401 / 403 (hết quota) / 429 /
  timeout / 5xx → tự fallback V3 và **báo rõ lý do + giọng mới** theo
  bảng ánh xạ `docs/voice-fallback-map.md` (VD: Hạ Vy → Trúc Ly). Job
  khoá giọng (`voice_strict: true`) thì không fallback mà trả lỗi.
  Không retry `POST /v1/audio/speech` sau timeout (endpoint đồng bộ
  không hỗ trợ idempotency — retry có thể bị tính phí trùng); đường
  async `POST /v1/tts` dùng `Idempotency-Key` = UUID theo HP job id.
- **TUYỆT ĐỐI KHÔNG dùng key V4 trong Secure Vault / key của anh để test
  tự động.** Test V4 chỉ làm khi anh đồng ý và cung cấp key test (C5).

## API local

Base mặc định: `http://127.0.0.1:8124`. Hợp đồng đầy đủ (21 endpoint):
`docs/api-contract.md`. Tóm tắt:

| Endpoint | Việc |
|---|---|
| `GET /health` | Trạng thái server + engine |
| `GET /voices`, `GET /voices/{id}/preview` | 25 giọng preset + clone; nghe thử (cache — lần 2 không tổng hợp lại) |
| `POST /api/tts/generate` | Text → audio (200 audio trực tiếp, hoặc 202 + `job_id` khi CPU bận) |
| `POST /api/tts/generate-with-subtitles` | Audio kèm `.srt` (trả ZIP; text > 5.000 ký tự → async 202) |
| `POST /api/tts/stream` | Đọc theo thời gian thực |
| `POST /api/tts/conversation` | Hội thoại nhiều người nói (voice-lock) |
| `POST /api/tts/srt-dub` | Lồng tiếng theo file `.srt`/`.vtt` |
| `POST /api/tts/batch` | Tạo hàng loạt (ZIP) |
| `POST /api/voices/clone`, `DELETE /api/voices/{id}` | Clone giọng (cần cam kết) / gỡ giọng (cần lý do) |
| `GET /api/jobs[/{id}[/result]]`, `POST /api/jobs/{id}/cancel`, `GET /api/jobs` | Trạng thái / tải kết quả / huỷ job |
| `GET /api/history[/{id}]`, `DELETE /api/history/{id}` | Bản đã tạo |
| `GET/POST /api/dict`, `DELETE /api/dict/{word}` | Từ điển phát âm (tối đa 2.000 mục) |
| `GET/POST /api/config`, `POST /api/config/v4-key` | Cài đặt (key V4 không bao giờ trả lại) |
| `POST /v1/audio/speech`, `GET /v1/voices`, `GET /v1/models` | Tương thích OpenAI (để Annie/MODOLIVIO dùng SDK OpenAI, `base_url` trỏ về `127.0.0.1:8124`) |

Lỗi validate trả **400** (không 422) với JSON
`{ "error": { "code", "message" } }`. Ví dụ:

```bash
curl http://127.0.0.1:8124/health
curl http://127.0.0.1:8124/voices
curl -X POST http://127.0.0.1:8124/api/tts/generate \
  -H 'Content-Type: application/json' \
  -d '{"text":"Xin chào các bạn!","voice_id":"Hải Đăng","format":"wav"}' \
  --output out.wav
```

## Cấu hình

Chép `config.example.yaml` thành `config.yaml` rồi sửa (không commit
`config.yaml`; key không ghi vào file này):

- `server.host` / `server.port`: mặc định `127.0.0.1` / `8124`.
- `engine.v3.precision`: `auto` (theo CPU) | `fp32` | `int8`.
- `engine.v4.warn_chars`: ngưỡng cảnh báo phí (ký tự/phiên).
- `audio.default_voice` / `default_speed` / `default_format` (`wav`|`mp3`).
- `storage.max_history_gb`: mặc định 5.
- Thư mục dữ liệu mặc định theo OS (SPEC §6 — SUY LUẬN, chờ anh chốt
  Q17): Windows `%LOCALAPPDATA%\HPVoiceStudio\`, Linux
  `~/.local/share/HPVoiceStudio/`.

## Đóng gói

- **Windows `.exe` (TK4.1):** build bằng **GitHub Actions Windows
  runner** (`windows-latest`, workflow
  `.github/workflows/build-windows.yml`), không build trên Linux
  (PyInstaller không build chéo Windows). Artifact `.exe`/installer +
  file `.sha256`; kiểm SHA-256 trước khi cài; smoke test `.exe` trên
  runner sạch (không Python, không repo) phải pass rồi mới đưa sang máy
  anh (C1). PyInstaller **KHÔNG** collect binary `imageio_ffmpeg/binaries/*`
  (Q21) nhưng phải `--collect-all keyring`, `--collect-all onnxruntime`,
  `--collect-all tokenizers`. **Trạng thái: chưa có trong đợt TK4-Release
  này** (do agent TK4-PACKAGE phụ trách; `packaging/windows/` hiện trống).
- **Linux (TK4.2):** build tương đương trên máy dev → chạy → T1.2 + T2.1 pass.
- Ngân sách bộ cài (Q2 — chưa chốt): ~300–400 MB kèm model sẵn (không
  còn cộng ~165 MB FFmpeg vì FFmpeg tải sau — Q21).

## Nâng cấp SDK

Checklist nâng cấp đầy đủ: `docs/upgrade-sdk.md`. Tóm tắt:

1. Không nâng lặng lẽ: nâng theo đợt, mỗi quý theo dõi release upstream
   (`vieneu`, VieNeu-TTS, model card).
2. Ghim version: `vieneu==3.8.4` trong `requirements.txt`; nâng thì đổi
   số ghim + ghi lý do, kèm model revision HF mới.
3. Chạy test tương thích đầy đủ (`pytest tests/`) + kiểm lại danh sách
   25 giọng (T1.3) trước khi chốt nâng.
4. Mirror model + checksum SHA-256 từng file (TH-15) — xem
   `scripts/download_model.py` + `docs/model-download.md`.

## Khắc phục sự cố

| Triệu chứng | Cách xử lý |
|---|---|
| Cổng 8124 bận / server thoát mã 2 | Chạy `python scripts/check_port.py` xem ai đang chiếm 8124 (8123 là MODOLIVIO — không dùng). Đóng app cũ / tiến trình ma rồi mở lại; server không tự nhảy cổng. |
| Tải model lỗi / mạng chậm | Kiểm tra mạng tới Hugging Face (C10); chạy lại `scripts/download_model.py` (resume, không tải lại từ đầu); file hỏng thì `--repair` chỉ tải lại file hỏng. |
| Tạo WAV chậm (RTF > 1) | Trên VM chia sẻ là bình thường; đo lại trên máy thật (C6). Nếu fp32 RTF > 1,5 thì app báo máy yếu và đề xuất v3 Nano cho bản nháp (Nano chưa có ở v1 — chỉ báo, không tự chuyển). |
| int8 méo tiếng | CPU không có VNNI mà dùng int8 có thể méo — chuyển precision sang `fp32` trong Cài đặt (mặc định `auto` đã chọn fp32 khi không đọc được cờ VNNI). |
| Không xuất được MP3 | App báo rõ "không có FFmpeg" — gọi `FFmpegManager.download()` để tải bản LGPL về lần đầu chạy (cần mạng, ~137 MB Linux / ~172 MB Windows), hoặc cài FFmpeg hệ thống; WAV vẫn tạo bình thường. Chưa có nút UI tải FFmpeg (xem ADR-07). |
| Clone giọng bị 400 | Kiểm tra: đã tick cam kết chưa; clip 3–8 s, 1 người nói, không nhạc nền; tên giọng chưa trùng; file MP3/M4A cần FFmpeg để giải mã. |
| V4 báo 401 / 403 / 429 | 401 = key sai/thiếu/hết hạn; 403 = hết quota/token; 429 = quá tải/rate limit (chờ `Retry-After`). App fallback V3 + báo rõ lý do + giọng mới; kiểm tra số dư bằng `GET /v1/balance` trong Cài đặt. |
| Đường dẫn có dấu/khoảng trắng lỗi | Dời repo/thư mục dữ liệu sang đường dẫn không dấu (VD `C:\HPVoiceStudio`) — test T4.5 chưa chạy trên máy thật (C21). |
| UI treo khi tạo câu dài | Inference chạy worker thread riêng, không chặn UI; nếu nút Dừng không phản hồi thì kiểm tra log server (TH-19, T1.8). |

## Giấy phép + ghi công

- **Code HP Voice Studio:** Apache License 2.0 (của HP) — xem `LICENSE`.
  Không copy nguyên file LICENSE của upstream làm LICENSE của mình.
- **Engine/model/giọng v3 Turbo:** Apache 2.0 theo model card
  (SPEC §13.8 / TH-01). File `voices.json` cũ (CC BY-NC) và bản GGUF Q4
  (CC BY-NC) không dùng, không phân phối lại.
- **FFmpeg binary tải sau:** GPL v3 + source offer — xem `NOTICE` mục 3.
- **V4 + kho giọng V4:** độc quyền, qua API trả phí.
- Ghi công đầy đủ từng tài sản: `NOTICE` + SPEC §13.8.
- Không dùng logo/thương hiệu VieNeu hay CIT; không fork/copy code CIT.

## Chờ kiểm chứng thật

Các mục sau **chỉ kiểm được trên máy/tài khoản thật của anh** và
**không được tính là đạt** khi chỉ pass trên máy ảo (SPEC §11, C1..C21).
Danh sách tổng hợp + kết quả release gate: xem
`evidence/release-gate/RELEASE-GATE-v1.md`. Nổi bật:

- C1: cài `.exe` trên máy Windows thật, tạo WAV thật (T1.2).
- C2: clone giọng thật của anh (thu micro 3–8 s) + cam kết.
- C5/C13: test V4 bằng key thật (khi anh đồng ý) + kiểm tra
  `GET /v1/balance` không trừ token.
- C6: RTF/ngưỡng mượt + phát hiện VNNI trên CPU thật của anh.
- C8: trùng cổng 8124 trên máy anh (8123 MODOLIVIO, 8001 CIT…).
- C9: SmartScreen + WebView2 khi cài `.exe` chưa ký.
- C10: tốc độ tải model từ Hugging Face trên mạng nhà anh.
- C11: gõ Telex trong UI + thu micro trên Windows.
- C20: MODOLIVIO gọi API HP thật qua `127.0.0.1:8124`.
- C21: cài + chạy trong thư mục có dấu tiếng Việt/khoảng trắng.
