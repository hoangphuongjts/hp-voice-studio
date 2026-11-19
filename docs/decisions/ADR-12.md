# ADR-12 — Local-only: biện pháp mạng duy nhất là bind 127.0.0.1

- **Ngày:** 19/11/2026 (SPEC v1.3 §14) · **Trạng thái:** ĐÃ CHỐT
  (theo quyết định local-only của anh 04:20 19/11)
- **Ngữ cảnh (SPEC TH-06, §9.3):** API local phục vụ Annie/MODOLIVIO
  trên cùng máy. Upstream mặc định mở khi không có key; CIT mặc định
  chỉ cùng máy gọi được, bật LAN thì phải có khoá. HP v1 chỉ chạy local,
  dùng cá nhân — không áp mức chặt cho bản local-only.
- **Quyết định:** Biện pháp mạng duy nhất ở v1 là API server **chỉ bind
  `127.0.0.1` mặc định**. LAN là opt-in trong Cài đặt, **không bắt buộc
  xác thực key** ở v1. Các biện pháp chặt hạ xuống P2/backlog, liệt kê
  ở SPEC §9.3 để bật lại khi mở LAN:
  - L1: LAN bắt buộc sinh khoá API (`X-API-Key`).
  - L2: LAN chỉ mở endpoint tạo giọng; không mở lịch sử / giọng clone /
    cài đặt / key V4.
  - L3: Host allowlist + Origin check + anti-CSRF token (TH-22).
  - L4: JobQueue 2 mức ưu tiên + rate-limit đa client (TH-29).
- **Không nới lỏng:** Key V4 vẫn lưu qua `keyring`/DPAPI (TH-05) — đó
  là bảo vệ tiền của anh, không phải bảo mật mạng. Key không log, không
  commit, không trả lại qua API.
- **Phương án đã cân nhắc:** Áp mức chặt ngay từ v1 (key LAN bắt buộc,
  giới hạn endpoint, CSRF) — làm chậm build, không cần cho máy cá nhân
  → loại ở v1, giữ lại làm backlog.
- **Cách nó hỏng / điều kiện xét lại:** Anh nói "mở LAN" → bật lại
  L1–L4 theo SPEC §9.3 (hỏi trước ở Q18: bật toàn bộ hay chỉ key bắt
  buộc). Kiểm chứng LAN chỉ khi mở LAN (C7/C16).
- **Liên quan:** SPEC §0 quyết định 10, §9.3, §14 ADR-12, §15 Q18;
  TK2.8/TK2.11/TK2.14 (P2/backlog); test T2.7.
