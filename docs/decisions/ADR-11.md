# ADR-11 — Desktop Shell: vỏ pywebview/WebView2

- **Ngày:** 19/11/2026 (SPEC v1.3 §14) · **Trạng thái:** ĐÃ CHỐT THIẾT KẾ,
  CHƯA BUILD (ticket TK4.8 — không thuộc đợt TK4-Release này)
- **Ngữ cảnh (SPEC TH-26, §3.3):** HP Voice Studio là app desktop cho
  máy Windows của anh, nhưng UI là web local (FastAPI + `ui/` tĩnh) và
  API chạy ở `127.0.0.1:8124`. Chạy server rồi mở trình duyệt tay thì:
  không có cửa sổ app, đóng tab không tắt server (tiến trình ma chiếm
  cổng), mở 2 instance thì instance sau bind trùng cổng.
- **Quyết định:** Vỏ desktop bằng **pywebview** (dùng WebView2 trên
  Windows — Q20), mở UI local `http://127.0.0.1:8124/ui` trong cửa sổ
  app. Vỏ sở hữu vòng đời server: khởi động server trước, đóng cửa sổ
  → dừng server + giải phóng cổng 8124 (graceful shutdown); ẩn console
  (`--noconsole` / pythonw — không để `.exe` chỉ hiện console đen);
  chống mở trùng instance (mutex/lock file — instance 2 báo rõ + không
  chạy chồng).
- **Phương án đã cân nhắc:**
  - Chỉ chạy uvicorn + mở trình duyệt tay — không có cửa sổ app, không
    tắt server khi đóng tab → loại (đúng lỗi TH-26).
  - WebView2 trực tiếp (không qua pywebview) — phương án dự phòng nếu
    pywebview không chạy được trên máy anh.
  - Electron + sidecar — nặng hơn nhiều, không cần cho UI web local
    đơn giản → loại (xem ADR-01).
- **Cách nó hỏng / điều kiện xét lại:** pywebview không chạy được trên
  máy anh (thiếu WebView2 / lỗi runtime) → xét WebView2 trực tiếp /
  trình duyệt + script tắt server. Kiểm chứng thật ở C1/C9/C19.
- **Liên quan:** SPEC §14 ADR-11, §15 Q20, §16 (vỏ desktop); TK4.8;
  test T4.1/T4.5; `docs/deployment-contract.md`.
