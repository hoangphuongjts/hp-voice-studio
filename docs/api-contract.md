# HP Voice Studio — Hợp đồng API local (TK2.1, SPEC §4)

> Base mặc định: `http://127.0.0.1:8124` (config `server.host`/`server.port`).
> Mọi response lỗi dùng HTTP status + JSON `{ "error": { "code", "message" } }`.
> Lỗi validate cũng trả **400** (không 422). Loopback không cần key (quyết định
> local-only 04:20 19/11); LAN opt-in, v1 không bắt buộc `X-API-Key`.

## Giới hạn (SPEC §4/§6)

| Giới hạn | Giá trị | Vượt thì |
|---|---|---|
| Text mỗi request TTS | 20.000 ký tự | 400 + nêu giới hạn |
| Batch | 500 mục/lần (số tạm chờ đo RAM, TK2.6) | 400 |
| Hàng đợi | 1 job chạy, tối đa 20 job chờ | job thứ 21 → 429 |
| TTL job chờ | 60 phút | job tự hủy + báo "hết thời gian chờ, gửi lại" |
| Tốc độ | 0,75×–1,5× | 400 |
| History | `max_history_gb` (mặc định 5 GB) | chặn tạo bản history mới + báo rõ hướng xoá/xuất bớt; audio vẫn trả kèm header `X-History-Warning` |
| File SRT | chưa chốt số (đo ở TK2.5) | — |

Hành vi khi CPU bận: request TTS thứ 2 **xếp hàng** (202 + `job_id`), không 429;
chỉ 429 khi hàng đợi đã đầy 20 job chờ. Endpoint OpenAI `/v1/audio/speech`
không trả 202 (SDK không hiểu `job_id`) mà **chờ tới lượt CPU** (tối đa 300 s).

## Endpoint

| # | Method + Path | Việc | Request | Response |
|---|---|---|---|---|
| 1 | `GET /health` | Trạng thái server + engine | — | `{ status, engine: "v3", v3_ready, v4_configured, version, uptime_s }` |
| 2 | `GET /voices` | Giọng preset + clone | `?engine=v3\|v4` | `[{ id, name, gender, region, style, engine, featured, is_clone? }]` — `engine=v4` khi chưa có V4 → 400 |
| 3 | `GET /voices/{id}/preview` | Nghe thử giọng (câu mẫu ≤ 60 ký tự) | — | audio WAV; header `X-Cache: HIT\|MISS` (lần 2 trả từ cache, không tổng hợp lại); giọng lạ → 404 |
| 4 | `POST /api/tts/generate` | Text → audio | `{ text, voice_id, engine?, speed?, format: "wav"\|"mp3" }` | **Hai dạng trả** (client phải xử lý cả hai): CPU rảnh → **200 + audio bytes** (header `X-Engine`, `X-Duration-Sec`, `X-Job-Id`, `X-History-Id`); CPU bận → **202 + `{ job_id, status: "queued", message }`** để poll endpoint 11 |
| 5 | `POST /api/tts/generate-with-subtitles` | Audio kèm phụ đề .srt | như (4), chỉ `format: "wav"` | **Một dạng duy nhất: ZIP đồng bộ** (`audio.wav` + `subtitles.srt`) cho text ≤ 5.000 ký tự; text **> 5.000 ký tự** → **`202 + { job_id }`** (async, poll endpoint 11 rồi tải ZIP qua `/result`). Text > 20.000 ký tự → 400. Text chứa thẻ `[nghỉ]` → 400 (dùng endpoint 4 cho text có `[nghỉ]`) |
| 6 | `POST /api/tts/stream` | Đọc theo thời gian thực | như (4) | **Chưa làm trong TK2.1** (không thuộc ticket TK2.1/TK2.3/TK2.9/TK2.10) |
| 7 | `POST /api/tts/conversation` | Hội thoại nhiều người nói | — | Do agent TK2-FEATURES (`routes_dialogue.py`, TK2.4) — server tự include khi file tồn tại |
| 8 | `POST /api/tts/srt-dub` | Lồng tiếng theo file .srt | — | Do agent TK2-FEATURES (`routes_srt.py`, TK2.5/TK2.13) |
| 9 | `POST /api/tts/batch` | Tạo hàng loạt | — | Do agent TK2-FEATURES (`routes_batch.py`, TK2.6); giới hạn 500 mục kiểm tra bằng helper chung `hpvoice.jobs.queue.check_batch_size` (vượt → 400) |
| 10 | `POST /api/voices/clone` | Clone giọng từ clip (cần cam kết) | multipart audio + `{ name, consent: true, consent_text }` (+ owner/gender/description) | **Xong ở TK3** (`routes_voices.py`): 201 `{ id, name, gender, is_clone, clip_seconds }`; thiếu cam kết/clip <3 s/>8 s/tên trùng/file hỏng -> 400 rõ lý do; MP3/M4A/AAC giải mã bằng FFmpeg trước (Y1) |
| 11 | `GET /api/jobs/{job_id}` | Trạng thái job | — | `{ id, job_id, kind, status: queued\|running\|done\|error\|cancelled, progress, result_url?, error?, error_code?, history_id?, duration_s?, size_bytes? }`; lạ → 404 |
| 11b | `GET /api/jobs/{job_id}/result` | Tải kết quả job đã xong | — | audio bytes (WAV/MP3) hoặc ZIP; chưa xong → 409; lạ → 404 |
| 11c | `POST /api/jobs/{job_id}/cancel` | Hủy job chờ/chạy | — | `{ job_id, status: cancelled\|cancelling }`; đã xong → 409; lạ → 404 |
| 11d | `GET /api/jobs` | Liệt kê job (mới nhất trước) | `?limit&offset` | `{ items, total }` |
| 12 | `GET /api/history` | Danh sách bản đã tạo | `?limit&offset` | `{ items: [{ id, created_at, text_preview, voice_id, engine, speed, format, duration_sec, size_bytes, audio_path, srt_path? }], total, total_bytes, max_history_gb }` |
| 13 | `GET /api/history/{id}` | Tải lại bản đã tạo | — | audio bytes; lạ → 404 |
| 14 | `DELETE /api/history/{id}` | Xoá 1 bản | — | 204; lạ → 404 |
| 15 | `GET /api/dict` / `POST /api/dict` / `DELETE /api/dict/{word}` | Từ điển phát âm (tối đa 2.000 mục) | `{ word, reading }` | danh sách `{ items, total }` / 201 `{ word, reading }` / 204; thiếu trường → 400 |
| 16 | `GET /api/config` / `POST /api/config` | Cài đặt | JSON patch (VD `{ "audio": { "default_voice": "Mai Anh" } }`) | config; key V4 **không bao giờ** trả lại (chỉ `v4_configured` + `v4_api_key: "****"\|""`); tốc độ ngoài khoảng → 400 |
| 17 | `POST /api/config/v4-key` | Nhập/xoá key V4 | `{ api_key }` (rỗng = xoá) | `{ configured: true\|false }`; key lưu qua keyring (fallback bộ nhớ phiên khi không có backend), không log/không trả lại |
| 18 | `POST /v1/audio/speech` | Tương thích OpenAI | `{ input, model: "v3-turbo", voice, response_format: "wav"\|"mp3", speed? }` | audio bytes + header `X-Engine`, `X-Duration-Sec`; `model: "v4"` → 400; `speed` được áp dụng thật (0,75×–1,5×) nên không có header `X-VieNeu-Ignored`; MP3 qua FFmpeg tải sau (Q21) — không có FFmpeg → 400 rõ ràng, chỉ xuất WAV |
| 19 | `GET /v1/voices` | Tương thích OpenAI: danh sách giọng | — | `[{ id, name }]` |
| 20 | `GET /v1/models` | Tương thích OpenAI: model | — | `{ object: "list", data: [{ id: "v3-turbo", object: "model", owned_by: "hp-voice-studio" }] }` |
| 21 | `DELETE /api/voices/{voice_id}` | Gỡ giọng clone khi khiếu nại (TH-17) | `?reason=...` (bắt buộc) | **Thêm ở TK3** (`routes_voices.py`): 204; không phải clone/preset -> 404; thiếu reason -> 400 |
| 22 | `GET /api/ffmpeg/status` | Trạng thái FFmpeg hiện tại + trạng thái tải | — | `{ available, kind: "system"\|"downloaded"\|"wheel"\|"other"\|"none", path?, license?, message, download: { status, stage, progress, percent, message, path? } }` — `kind` phân biệt FFmpeg hệ thống (ưu tiên) / bản LGPL tải về / binary wheel imageio-ffmpeg (dự phòng máy dev) / chưa có |
| 23 | `POST /api/ffmpeg/download` | Bắt đầu tải FFmpeg LGPL (BtbN) về lần đầu | — | Chạy nền, trả ngay: chưa có + chưa tải → **202** `{ ...envelope như (22), download.status: "downloading" }`; đã có FFmpeg → **200** (không tải lại); đang tải → **200** `downloading` (bấm lần 2 không khởi động thêm — chống race ghi đè file `.part`); tải xong trước đó → **200** `done`. Poll tiến trình qua (24). Không dùng JobQueue cho tải này (runner sẽ ghi kết quả thành audio/history — xem `routes_ffmpeg.py`) |
| 24 | `GET /api/ffmpeg/download` | Poll trạng thái tải FFmpeg | — | `{ status: "idle"\|"downloading"\|"done"\|"error", stage: "idle"\|"downloading"\|"verifying"\|"done"\|"error", progress: 0.0–1.0, percent: 0–100, message, path? }` — tiến trình: tải archive = 0–90%, kiểm chứng/giải nén = 90%, xong = 100%; lỗi (mất mạng / platform chưa ghim / checksum lệch) → `error` + thông báo tiếng Việt rõ lý do + hướng cài FFmpeg hệ thống |

## Quy tắc tương thích (api-contract-compatibility-testing-vn)

- V3/V4 voice id không lẫn: giọng V4 qua engine v3 → 400 rõ ràng (và ngược lại
  khi có V4); `engine: "v4"` ở endpoint 4/18 hiện trả 400 "chưa hỗ trợ" (TK2.2).
- `POST /v1/audio/speech` chạy được bằng httpx/OpenAI SDK trỏ `base_url` về
  `http://127.0.0.1:8124` (test `tests/test_api_tts.py`, không cần gói `openai`).
- Endpoint 4 trả cả hai dạng 200/202 — client (MODOLIVIO/Annie) phải xử lý cả hai.

## Wiring router động (cho TK2-FEATURES)

`create_app()` quét mọi module `src/hpvoice/api/routes_*.py` và include thuộc
tính `router` của chúng. Module import lỗi → bỏ qua + log warning (server vẫn
chạy). Test: `tests/test_api_dynamic_router.py` (thêm/xoá module probe tạm).

## Ghi chú khác

- MP3: mã hoá bằng `FFmpegManager` (TK1.6) — FFmpeg hệ thống trước, rồi tới
  binary tải sau (Q21); không có FFmpeg → chỉ WAV + báo rõ (T2.10). Tải
  FFmpeg lần đầu qua endpoint 23 + nút "Tải FFmpeg" ở tab Cài đặt
  (`ui/tabs-settings.js`); xem trạng thái qua endpoint 22, poll qua 24.
- Preview cache: `PreviewCache` (trần mặc định 200 MB, dọn file cũ nhất khi
  vượt trần — TH-30), khóa `preview:v3:<voice_id>:<câu mẫu>`.
- History bền vững (TH-21/TH-33): ghi atomic (tạm + rename), backup
  `history.json.bak` trước mỗi lần ghi index, checkpoint sau mỗi mục,
  `ensure_free_space()` kiểm tra ổ trống trước batch lớn, `cleanup_temp()`
  quét file tạm lúc khởi động.
- Cổng: `scripts/check_port.py` kiểm tra 8124 trước khi chạy; bận → fail-fast,
  thoát mã 2, không tự nhảy cổng (`scripts/run_server.py`).
