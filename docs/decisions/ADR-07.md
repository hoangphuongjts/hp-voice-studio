# ADR-07 — FFmpeg tải cài sau lần đầu chạy (Q21 — ĐÃ CHỐT 04:35 19/11)

- **Ngày:** 19/11/2026 · **Trạng thái:** ĐÃ CHỐT (anh chọn phương án 2 trong 4)
- **Ngữ cảnh (SPEC §13.7, TH-14/TH-31):** Server upstream chỉ xuất
  wav/pcm; SDK không có encoder MP3 nào. HP cần MP3 cả hai chiều: mã hoá
  MP3 đầu ra + giải mã MP3/M4A đầu vào cho clone giọng. Binary FFmpeg
  tĩnh qua `imageio-ffmpeg` 0.8.1 đo thật là **GPL v3**
  (`ffmpeg -buildconf`: `--enable-gpl --enable-version3 --enable-libx264
  --enable-libx265`), ~165 MB (Linux: 172.692.552 byte) — đóng gói kèm
  thì bộ cài chịu nghĩa vụ GPL + bẫy onefile (TH-31).
- **Quyết định:** Bộ cài **KHÔNG đóng gói kèm binary FFmpeg** (giữ 100%
  Apache 2.0). Lần đầu cần MP3/giải mã, app lấy FFmpeg theo thứ tự:
  (1) FFmpeg hệ thống nếu có; (2) binary LGPL tải thật về thư mục dữ
  liệu người dùng (`FFmpegManager.download()` — tải archive BtbN đã
  ghim, kiểm SHA-256 + chạy thử + kiểm giấy phép, xem dưới đây);
  (3) binary đi kèm wheel `imageio-ffmpeg==0.8.1` (dự phòng cũ, chỉ
  còn trên máy dev đã `pip install` — binary GPL v3, không có trong
  .exe); (4) không có → chỉ xuất WAV + báo rõ, không crash.
  `FFmpegManager` kiểm SHA-256 binary tải sau trước khi dùng (bảng
  ghim trong `src/hpvoice/audio/ffmpeg_manager.py`) và báo tiến trình
  tải qua callback `on_progress(bytes_done, bytes_total)`.
- **Tải thật (sửa khoảng trống Q21, đo thật 19/11/2026 — xem
  `evidence/ffmpeg-download/FFMPEG-DOWNLOAD-VERIFICATION.md`):**
  `download()` tải archive FFmpeg **LGPL tĩnh** từ BtbN/FFmpeg-Builds,
  release `autobuild-2026-11-18-12-39` (tag ngày cố định — KHÔNG dùng
  URL "latest" vì file thay đổi theo từng bản rebuild, checksum ghim
  sẽ lệch). Bảng ghim `FFMPEG_DOWNLOADS` trong
  `src/hpvoice/audio/ffmpeg_manager.py` (URL + SHA-256 archive +
  SHA-256 binary + kích thước) đã đo thật và đối chiếu với file
  `checksums.sha256` do chính BtbN công bố cho release đó:
  Linux x86_64 (`ffmpeg-n9.0.2-57-gd838f9f9ae-linux64-lgpl-9.0.tar.xz`,
  137.212.900 byte, SHA-256 `ead99a40…b1a342`; binary 142.747.536 byte,
  SHA-256 `7febfdf8…e9e195`) và Windows x86_64
  (`ffmpeg-n9.0.2-57-gd838f9f9ae-win64-lgpl-9.0.zip`, 171.850.772 byte,
  SHA-256 `51fcd008…ed366f`; binary `ffmpeg.exe` 134.459.392 byte,
  SHA-256 `ecc293ce…717663`). Tải có resume (HTTP Range, file `.part`),
  giải nén an toàn chỉ đúng file binary (không `extractall`), kiểm
  chứng binary trước khi dùng: SHA-256 + kích thước + chạy
  `ffmpeg -version` thật + `-buildconf` không có `--enable-gpl` /
  `--enable-nonfree` + có encoder `libmp3lame`. Binary lưu vào
  `<thư mục dữ liệu>/ffmpeg/` (không ghi vào thư mục cài đặt); hồ sơ
  tải ghi vào `ffmpeg-download.json`. Mất mạng: giữ `.part` để tải
  tiếp, báo tiếng Việt rõ ràng + hướng dẫn cài FFmpeg hệ thống; app
  vẫn xuất WAV được.
- **Đính chính giấy phép — `--enable-version3` KHÔNG phải GPL:**
  theo giấy phép của chính FFmpeg, `--enable-version3` chỉ nâng
  (L)GPL lên v3 — bản BtbN lgpl là **LGPL v3** (file `LICENSE.txt`
  trong archive là văn bản LGPL v3; BtbN README: bản `lgpl` "lacking
  libraries that are GPL-only. Most prominently libx264 and libx265").
  Chỉ `--enable-gpl` (kéo theo libx264/libx265) mới biến binary thành
  GPL. Kiểm tra giấy phép trong code chỉ từ chối khi thấy
  `--enable-gpl` hoặc `--enable-nonfree`. Binary imageio-ffmpeg cũ
  (đường dự phòng 3) vẫn là GPL v3 — xem NOTICE mục 3.
- **Đính chính cũ (TK4.9, đo thật 19/11/2026):** `imageio-ffmpeg`
  0.8.1 đóng gói sẵn binary trong wheel — `get_ffmpeg_exe()` chỉ tìm
  file đã có, **không tải binary rời lúc chạy**. "Tải lần đầu" trong
  thực tế cũ là pip tải wheel (nén ~68 MB) lúc
  `pip install -r requirements.txt`. Đính chính này vẫn đúng cho đường
  wheel, nhưng từ nay đường tải chính là `download()` (BtbN LGPL) —
  SPEC v1.3 viết "`get_ffmpeg_exe()` tải lần đầu nếu chưa có" vẫn chưa
  đúng và cần sửa ở đợt SPEC sau.
- **Phương án đã cân nhắc:**
  - (a) `lameenc` — chỉ mã hoá, không giải mã MP3/M4A đầu vào → loại.
  - (b) Bỏ MP3 khỏi v1 — mất tính năng CIT đã có → loại.
  - (c) Đóng gói FFmpeg kèm bộ cài — bị loại bởi Q21 (nghĩa vụ GPL +
    bẫy onefile TH-31).
  - (d) Đổi sang bản build FFmpeg LGPL (kịch bản B, SPEC §13.7) — **ĐÃ
    LÀM: bản BtbN lgpl là nguồn tải chính từ nay**; bản imageio GPL
    chỉ còn làm dự phòng cho máy dev.
- **Checksum ghim:** bảng `FFMPEG_DOWNLOADS` (BtbN LGPL, đo thật cả
  Linux + Windows — Windows chỉ đo checksum + nội dung zip, chưa chạy
  thật trên Windows, xem C22) và bảng `PINNED_FFMPEG_SHA256` cũ
  (imageio wheel, chỉ `linux-x86_64` đã đo thật). Platform chưa ghim:
  app vẫn dùng binary nhưng ghi rõ "chưa có checksum ghim" + ghi
  SHA-256 đo được vào `ffmpeg-manifest.json` trong thư mục dữ liệu để
  đối chiếu tay. Checksum lệch bảng ghim → binary bị từ chối dùng.
- **Cách nó hỏng / điều kiện xét lại:** Tải FFmpeg lần đầu thất bại
  (không mạng / BtbN chết / checksum lệch) → app vẫn chạy WAV-only +
  báo rõ cách tải lại. Nếu BtbN xoay release (tag autobuild mới) thì
  cập nhật bảng ghim có chủ đích (đo lại + đối chiếu
  `checksums.sha256` của release mới) — KHÔNG tự động theo "latest".
  Nếu sau này cần tránh LGPL v3 hoàn toàn → xét lại sang bản build
  khác và cập nhật NOTICE.
- **Chưa xong (cần ticket nối tiếp):** `FFmpegManager.download()` đã
  làm thật nhưng **chưa có endpoint API hay nút UI nào gọi nó** — hiện
  MP3 vẫn báo 400 "không có FFmpeg" khi chưa có binary. Cần:
  `POST /api/ffmpeg/download` + nút "Tải FFmpeg" ở tab Cài đặt.
  Ngoài ra C22: binary Windows chưa chạy thật trên Windows (chỉ đo
  checksum) — kiểm ở TK4.1 trên runner Windows.
- **Liên quan:** SPEC §0 quyết định 14 (Q21), §13.7, §15 Q8/Q21;
  TK4.9; `NOTICE` mục 3; `docs/upgrade-sdk.md` (nâng imageio-ffmpeg);
  `evidence/ffmpeg-download/FFMPEG-DOWNLOAD-VERIFICATION.md`.
