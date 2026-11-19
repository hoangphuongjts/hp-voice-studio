# Bảng ánh xạ giọng fallback V4 → V3 (TK2.2, SPEC §3.3 — EngineRouter)

> **Trạng thái bảng:** BẢN MẪU — chỉ gồm giọng V4 đã biết từ nguồn kiểm chứng
> được (connector `custom.vieneu` 19/11 + OpenAPI `docs.vieneu.io/openapi.json`
> đọc ngày 19/11/2026). Bảng ĐẦY ĐỦ 707 giọng chỉ sinh được từ
> `GET /v1/voices?engine=v4` với key thật rồi soát tay — **chờ kiểm chứng thật
> (C5)**, không đoán mò thêm. Khi có catalogue thật: sinh bảng đầy đủ bằng
> script (ghép `id` + `gender` + `region` + `description`), soát tay từng
> giọng rồi thay bảng mẫu này.

## Quy tắc ánh xạ (theo SPEC §3.3)

1. Giọng V4 là **tên hiển thị hoặc `id`** trong catalogue `GET /v1/voices`
   (khóa chính là trường `id` — hai giọng khác nhau có thể trùng tên hiển thị).
2. Map sang preset V3 gần nhất theo thứ tự ưu tiên: **giới tính (4 điểm) >
   vùng (2 điểm) > phong cách (1 điểm)** — xem `map_v4_voice_to_v3()` trong
   `src/hpvoice/engines/router.py`.
3. Giọng V4 đã là tên preset V3 (VD "Trúc Ly" — V4 cũng có preset trùng tên
   này theo ví dụ `PublicTtsRequestDto`) thì giữ nguyên tên.
4. Không có preset nào cùng giới tính + vùng (0 điểm) → mặc định **"Hải Đăng"**
   (giọng mặc định của V3, Nam · Bắc · tự nhiên).
5. Khi fallback đổi giọng, job + UI + log **phải ghi rõ cả lý do lẫn giọng mới**,
   VD: `V4 lỗi 403 hết quota → fallback V3, giọng đổi Hạ Vy → Trúc Ly`.
6. Job khóa giọng (`voice_strict: true`, hoặc UI tick "chỉ dùng giọng này")
   thì **không fallback** — trả lỗi thay vì đổi giọng lặng lẽ.
7. Quy tắc fallback giọng trong config: `fallback_voice: "map" | "default" | "fail"`
   (mặc định `"map"`).

## 25 preset V3 (nguồn: SPEC §2.2, `voices_v3_turbo.json`, `meta.count=25`)

| Giọng | Giới tính | Vùng | Phong cách |
|---|---|---|---|
| Adam bựa | Nam | Bắc | tự nhiên |
| Trúc Ly | Nữ | Bắc | tự nhiên |
| Thiện Minh | Nam | Bắc | kể chuyện |
| Mai Anh | Nữ | Bắc | tin tức |
| Hải Đăng (mặc định) | Nam | Bắc | tự nhiên |
| Thùy Dung | Nữ | Nam | tin tức |
| Thiền Tâm Đức | Nam | Bắc | kể chuyện |
| Ngọc Huyền | Nữ | Bắc | tự nhiên |
| Quang Sơn | Nam | Trung | tự nhiên |
| Ngọc Trân | Nữ | Trung | tự nhiên |
| Minh Đức | Nam | Bắc | tin tức |
| Phạm Tuyên | Nam | Bắc | tự nhiên |
| Thái Sơn | Nam | Nam | kể chuyện |
| Xuân Vĩnh | Nam | Bắc | tự nhiên |
| Thanh Bình | Nam | Bắc | kể chuyện |
| Ngọc Linh | Nữ | Bắc | kể chuyện |
| Đoan Trang | Nữ | Bắc | tự nhiên |
| Thục Đoan | Nữ | Nam | kể chuyện |
| Minh Triết | Nam | Nam | tin tức |
| Mỹ Duyên | Nữ | Nam | đọc truyện |
| Quỳnh Anh | Nữ | Bắc | đọc truyện |
| Đức Trí | Nam | Nam | đọc truyện |
| Kim Thanh | Nữ | Nam | đọc truyện |
| Adam | Nam | Nam | tự nhiên |
| Quốc Tuấn | Nam | Bắc | tự nhiên |

## Bảng mẫu giọng V4 đã biết → V3

| Giọng V4 (`id`/tên hiển thị) | Giới tính · Vùng · Phong cách (V4) | Map sang V3 | Căn cứ / trạng thái |
|---|---|---|---|
| Hạ Vy | Nữ · Bắc · tự nhiên | **Trúc Ly** (Nữ · Bắc · tự nhiên, ⭐ featured) | Giọng V4 đã kiểm chứng tạo WAV thật 19/11 (SPEC §2.4). Giới tính/vùng là **giả định** theo catalogue (182 giọng nữ Bắc) — **chưa xác nhận** bằng `GET /v1/voices` thật, cần soát lại khi có key thật. |
| Ngọc Lan | Nữ · Nam · tự nhiên | **Thùy Dung** (Nữ · Nam · tin tức) hoặc **Mỹ Duyên** (Nữ · Nam · đọc truyện) — code chọn Thùy Dung (cùng vùng + giới tính; phong cách tin tức gần tự nhiên hơn đọc truyện) | OpenAPI `PublicVoiceDto` ví dụ: "Giọng nữ miền Nam, ấm và rõ" → Nữ · Nam. Đã xác nhận từ OpenAPI, chưa xác nhận bằng catalogue thật. |
| Trúc Ly | Nữ · Bắc · tự nhiên | **Trúc Ly** (giữ nguyên tên) | OpenAPI `PublicTtsRequestDto` dùng `voiceId: "Trúc Ly"`. Lưu ý OpenAPI ghi `voiceId "Thiện Minh"` render ra giọng "Anh Khôi" — V4 có alias riêng, tên hiển thị không phải lúc nào cũng là `id` thật. |

## Ví dụ hành vi fallback

- `V4 lỗi 403 hết quota → fallback V3, giọng đổi Hạ Vy → Trúc Ly`
- `V4 lỗi 401 key sai/thiếu/hết hạn → fallback V3, giọng đổi Ngọc Lan → Thùy Dung`
- Giọng V4 không biết (VD "Giọng Lạ 123", không có giới tính/vùng) → `Hải Đăng`
- `voice_strict: true` + V4 lỗi → lỗi `V4 lỗi 403 hết quota (giọng đã khóa, không fallback)`, không tạo audio

## Công thức phí V4

Xem `docs/v4-billing.md`: phí = `max(50, ký tự) × billingMultiplier × globalMultiplier`.
