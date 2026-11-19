# NHIỆM VỤ PHÂN TÍCH — HP Voice Studio (vòng team, trước khi build)

Anh Hoàng Phương giao: team phân tích + xây dựng cùng nhau TRƯỚC KHI bắt tay vào việc.
Yêu cầu: FULL tính năng, PHẢI DÙNG ĐƯỢC, và ĐẢM BẢO MƯỢT MÀ (chạy mượt, không giật/lag/treo).

## Tài liệu kèm theo (đọc đủ trước khi làm)

1. `SPEC.md` — bản draft phân tích (tử huyệt TH-01..TH-11, bản đồ repo/SDK, hợp đồng V4).
2. `vieneu-studio-clone-2026-11-19.md` — nghiên cứu clone VieNeu Studio trước đó.

## Việc cần làm (làm theo Charter v1.1: grilling → research → to-spec → to-tickets)

1. **MỔ SẺ SPEC:** đọc kỹ từng mục, chất vấn từng khẳng định: cái nào đúng, cái nào thiếu bằng chứng, cái nào sai, cái nào còn mâu thuẫn. Tìm thêm tử huyệt mà SPEC chưa nêu (ít nhất 3 điểm mới nếu có).
2. **MƯỢT MÀ:** soi riêng hiệu năng + trải nghiệm mượt: RTF trên CPU 4 nhân, tiếng đầu tiên bao lâu, UI có bị đứng khi tạo bài dài không, RAM khi batch lớn, streaming, hàng đợi, lỗi thì báo thế nào. Đề xuất tiêu chí "mượt" đo được cho từng tính năng (con số cụ thể, cách đo).
3. **KẾ HOẠCH BUILD:** chia SPEC thành ticket nhỏ theo thứ tự (to-tickets), mỗi ticket có: việc làm, file chạm vào, cách kiểm chứng chạy thật, tiêu chí xong. Ghi rõ ticket nào làm trước, ticket nào chờ ticket khác.
4. **HAI KỊCH BẢN:** phân tích cả dùng cá nhân (máy anh, Windows) và người khác dùng (máy khác, Linux, Annie gọi API).
5. **CHỜ KIỂM CHỨNG THẬT:** liệt kê riêng những điểm chỉ kiểm được trên máy/tài khoản thật của anh (cài .exe Windows thật, clone giọng thật, V4 bằng key thật) — không tuyên bố xong những điểm này.

## Trả về

Bản phân tích bằng tiếng Việt, ghi rõ: (a) SPEC đúng chỗ nào / sai-thiếu chỗ nào (kèm bằng chứng), (b) tử huyệt bổ sung, (c) tiêu chí mượt mà đo được, (d) danh sách ticket theo thứ tự, (e) điểm chờ kiểm chứng thật. Không code implementation ở vòng này. Không bịa số liệu — số nào chưa đo thì ghi "chưa đo".
