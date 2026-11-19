# ADR-13 — Thước đo cuối cùng: full tính năng dùng được

- **Ngày:** 19/11/2026 (SPEC v1.3 §14) · **Trạng thái:** ĐÃ CHỐT
  (theo quyết định của anh 04:20 19/11: "Kết quả dùng được full tính
  năng là ok.")
- **Ngữ cảnh (SPEC §0.1):** SPEC có 33 tử huyệt + bảng tiêu chí mượt
  §10.5 rất dài. Nếu nghiệm thu bằng checklist giấy / đếm tiêu chí mượt
  thì dễ "đạt trên giấy" trong khi tính năng chính chưa chạy được — hoặc
  ngược lại, danh sách dài làm chậm build trong khi tính năng đã dùng được.
- **Quyết định:** Thước đo cuối cùng của v1 là **ĐỦ TÍNH NĂNG + DÙNG
  ĐƯỢC THẬT** (7 nhóm: Phòng thu, Hội thoại/Podcast, Lồng tiếng .srt,
  Đọc file, Tạo hàng loạt, Bản đã tạo, Cài đặt). Ưu tiên xử lý theo mức
  ảnh hưởng tới "dùng được":
  - **P0 — chặn tính năng chạy được:** sửa trước khi chốt build.
  - **P1 — ảnh hưởng mượt mà** (RTF, tiếng đầu, phản hồi UI, RAM, thời
    gian khởi động): sửa trong lúc build, nghiệm thu bằng số đo thật.
  - **P2/backlog — hardening** (đặc biệt bảo mật mạng local): không để
    danh sách dài làm chậm build.
  - Nghiệm thu mỗi giai đoạn bằng **tính năng chạy thật** (file WAV
    thật / response API thật / thao tác UI thật), không bằng checklist
    tick trên giấy. Điểm chỉ kiểm được trên máy/tài khoản thật của anh
    liệt kê riêng là "chờ kiểm chứng thật" (SPEC §11, C1..C21), không
    tính là đạt.
- **Phương án đã cân nhắc:** Nghiệm thu bằng checklist giấy / đếm tiêu
  chí mượt — dễ đạt giả, không chứng minh được tính năng chạy → loại.
- **Cách nó hỏng / điều kiện xét lại:** Anh đổi thước đo → cập nhật
  SPEC §0.1 + §10.5/§10.6. Nếu một tính năng "dùng được" nhưng vi phạm
  luật cứng (VD: clone giọng không cam kết, nêu giá trong video) thì
  vẫn là CHƯA ĐẠT — thước đo này không ghi đè các rào chắn pháp lý /
  an toàn (TH-04/TH-17).
- **Liên quan:** SPEC §0.1, §10.5, §10.6, §11, §14 ADR-13; TK4.4
  (release gate); skill `verification-before-completion-team`.
