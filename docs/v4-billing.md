# Tính phí Cloud API v4 (TK2.2, SPEC §2.4/§3.3)

> Nguồn: OpenAPI `https://docs.vieneu.io/openapi.json` (đọc 19/11/2026) —
> mô tả `GET /v1/balance` + `GET /v1/engines`. Số multiplier thật chỉ biết
> khi gọi `GET /v1/engines` với key thật — **chờ kiểm chứng thật (C5)**.

## Công thức

```
phí (token) = max(50, số ký tự gửi) × billingMultiplier (engine) × globalMultiplier
```

- **Tối thiểu 50 ký tự/request**: câu mẫu ≤ 60 ký tự vẫn tính 50 ký tự
  (xem `PreviewCache` §3.3 — nghe thử V4 lần đầu mỗi giọng tốn 50 ký tự tối thiểu).
- `billingMultiplier`: hệ số từng engine, lấy từ `GET /v1/engines`
  (ví dụ trong OpenAPI: v4 = **3.4** — chỉ là ví dụ minh họa, không phải số thật).
- `globalMultiplier`: hệ số toàn hệ thống, lấy cùng endpoint (thường = 1).
- Token trừ lúc gửi, hoàn lại nếu job thất bại vĩnh viễn.
- `/v1/dub` tính phí theo **thời lượng audio đầu ra** (không phải ký tự).
- `/v1/srt` tính phí theo tổng ký tự cue (tối thiểu 50).
- `aiRefine: true` (mặc định HP để `false`) cộng thêm phụ phí AI + kiểm duyệt.

## Ví dụ số (dùng multiplier ví dụ trong OpenAPI: v4 = 3.4, global = 1.0)

| Text | Ký tự tính phí | Phí (token) |
|---|---|---|
| "Xin chào!" (9 ký tự) | max(50, 9) = 50 | 50 × 3.4 × 1.0 = **170** |
| Câu mẫu preview 55 ký tự | max(50, 55) = 55 | 55 × 3.4 × 1.0 = **187** |
| Đoạn 100 ký tự | 100 | 100 × 3.4 × 1.0 = **340** |
| Đoạn 1.000 ký tự | 1.000 | 1.000 × 3.4 × 1.0 = **3.400** |
| Đoạn 20.000 ký tự (tối đa/request HP) | 20.000 | 20.000 × 3.4 × 1.0 = **68.000** |

## Bẫy phí: tách `[nghỉ]` trên V4 nhân phí

`[nghỉ]` bị V4 xóa lặng lẽ nên HP tách text thành nhiều đoạn, mỗi đoạn 1 job
async (`POST /v1/tts` + `Idempotency-Key` riêng). Mỗi đoạn tính phí tối thiểu
50 ký tự — VD text 120 ký tự có 3 thẻ `[nghỉ]` tách thành 4 đoạn ngắn
(30 + 25 + 35 + 30 ký tự) thì phí = (50 + 50 + 50 + 50) × 3.4 = **680 token**
thay vì 120 × 3.4 = **408 token** nếu gửi nguyên. UI phải cảnh báo trước khi
tạo bằng V4 khi text chứa `[nghỉ]`.

## Số dư (màn hình Cài đặt)

- `GET /v1/balance` → `{remaining, spendableTokens, totalRemainingTokens, plan}`:
  `remaining` = request lớn nhất key trả được ngay; `spendableTokens` = tổng
  các plan còn chi được; `totalRemainingTokens` = tổng mọi plan đang hoạt động.
- `GET /v1/engines` → `{globalMultiplier, engines: [{key, billingMultiplier,
  isDefault, sampleRate, features}]}` — không cần auth theo OpenAPI nhưng HP
  vẫn gửi key khi có.
- Code: `V4Engine.get_balance()`, `V4Engine.get_engines()`,
  `V4Engine.estimate_cost(text)` (xem `src/hpvoice/engines/v4_engine.py`).
