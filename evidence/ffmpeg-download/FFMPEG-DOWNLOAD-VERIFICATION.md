# Kiểm chứng tải FFmpeg thật (Q21) — BtbN LGPL

- **Ngày:** 19/11/2026 (23:29–23:35 +07) · **Máy:** VM Linux của Annie
- **Kết luận:** `FFmpegManager.download()` tải thật được FFmpeg LGPL từ
  BtbN, kiểm chứng đầy đủ (checksum + chạy thử + giấy phép + MP3 thật).
  Binary Windows chỉ đo checksum + liệt kê zip trên Linux — **chưa chạy
  thật trên Windows (C22)**.

## 1. Nguồn đã chọn — BtbN/FFmpeg-Builds, release autobuild cố định

- Release: `autobuild-2026-11-18-12-39` (tag ngày cố định — file không
  thay đổi; KHÔNG dùng URL "latest": file `ffmpeg-n9.0-latest-...` đổi
  kích thước giữa 17/11 và 18/11 — 135.292.760 → 137.211.408 byte bản
  Linux LGPL — nên checksum ghim cho URL "latest" sẽ lệch).
- Bản chọn: **LGPL tĩnh** (static, một file binary duy nhất, không cần
  DLL kèm theo). BtbN README: bản `lgpl` "lacking libraries that are
  GPL-only. Most prominently libx264 and libx265" (xem `btbn-readme.md`).
- File `checksums.sha256` do chính BtbN công bố cho release này đã tải
  về (`checksums-autobuild-2026-11-18-12-39.sha256`) và dùng đối chiếu.

## 2. Số đo thật (đã đối chiếu 2 nguồn: đo tay + checksums.sha256 của BtbN)

| Platform | Archive | Kích thước | SHA-256 archive |
|---|---|---|---|
| linux-x86_64 | `ffmpeg-n9.0.2-57-gd838f9f9ae-linux64-lgpl-9.0.tar.xz` | 137.212.900 byte | `ead99a4068892760a01a27fa437bdf1975e29a967bc011554d518ae906b1a342` |
| windows-x86_64 | `ffmpeg-n9.0.2-57-gd838f9f9ae-win64-lgpl-9.0.zip` | 171.850.772 byte | `51fcd00803e75229da76bac035fdec7b8f641ef2ef50bec3f9fce0e474ed366f` |

- Binary trong archive:
  - Linux: `.../bin/ffmpeg`, 142.747.536 byte, SHA-256
    `7febfdf8a1615bc18c9af3fb7c9cb2b7945ec5bee010a3d0a806a0eac7e9e195`.
  - Windows: `.../bin/ffmpeg.exe`, 134.459.392 byte, SHA-256
    `ecc293ceb96c499984911e23c2493265d5a93b17ee72aea4747defeaa1717663`
    (đo bằng cách đọc stream trong zip, không chạy .exe trên Linux).
- `ffmpeg -version` (Linux, chạy thật): `ffmpeg version
  n9.0.2-57-gd838f9f9ae-20261118`, built with gcc 16.2.0.
- `ffmpeg -buildconf` (Linux, chạy thật): **không có `--enable-gpl`,
  không có `--enable-nonfree`** (đếm bằng grep = 0); có
  `--enable-version3` (x2 — in cả ở `-version` lẫn `-buildconf`).
- `LICENSE.txt` trong cả hai archive là văn bản **GNU LESSER GENERAL
  PUBLIC LICENSE v3**.
- Encoder MP3: `libmp3lame` có trong `-encoders` (chạy thật).

### Đính chính quan trọng về `--enable-version3`
`--enable-version3` KHÔNG biến binary thành GPL. Theo giấy phép của
chính FFmpeg, `--enable-version3` chỉ nâng (L)GPL lên v3 — bản này là
**LGPL v3** (khớp với LICENSE.txt LGPL v3 trong archive); chỉ
`--enable-gpl` (kéo theo libx264/libx265 — đã `--disable` trong bản
này) mới biến binary thành GPL. Vì vậy kiểm tra giấy phép trong code
chỉ từ chối khi thấy `--enable-gpl` hoặc `--enable-nonfree`.

## 3. Kiểm chứng code mới chạy thật

- **Live test** `tests/test_ffmpeg_download_live.py` (chạy với
  `HP_LIVE_DOWNLOAD=1`, 19/11/2026, **PASS trong 35,10 s**): trên máy
  giả lập sạch (ẩn FFmpeg hệ thống + wheel imageio),
  `FFmpegManager.download()` tải archive thật 137.212.900 byte từ BtbN,
  báo tiến trình (lần cuối done == total == 137.212.900), kiểm checksum
  khớp bảng ghim, giải nén đúng binary, kiểm `-version` /
  `-buildconf` / `libmp3lame`, ghi `ffmpeg-download.json`, rồi xuất
  **MP3 thật** từ WAV mẫu T1 (`t1-first-wav-hai-dang.wav`) bằng chính
  binary vừa tải — ffprobe đọc được codec mp3.
- **Test mock** `tests/test_ffmpeg_manager.py`: 20/20 PASS (11 test cũ
  giữ nguyên + 9 test mới cho tải thật: resume từ `.part`, checksum
  archive sai bị từ chối, binary GPL bị từ chối, mất mạng báo tiếng
  Việt, URL lạ bị từ chối, platform chưa ghim, archive thiếu binary,
  locate() ưu tiên binary đã tải, binary hỏng bị xóa + fallback wheel).

## 4. Chưa kiểm chứng thật

- **C22 — binary Windows:** chưa chạy `ffmpeg.exe` thật trên Windows
  (`-version`/`-buildconf`/MP3), chưa đo RTF/luồng tải trên máy
  Windows thật. Chỉ đo checksum archive + SHA-256 `ffmpeg.exe` trong
  zip + đối chiếu `checksums.sha256` của BtbN (trên Linux). Cần chạy
  trên runner Windows/máy anh (TK4.1).
- **macOS / Windows ARM:** BtbN không có bản macOS; Windows ARM chưa
  ghim (có asset `winarm64-lgpl` trong release nhưng chưa đo) —
  `download()` trả None + báo rõ trên các platform này.
- **Endpoint/UI gọi download():** `FFmpegManager.download()` đã làm
  thật nhưng **chưa có endpoint API hay nút UI nào gọi nó** — hiện
  MP3 vẫn báo 400 "không có FFmpeg" khi chưa có binary. Cần ticket nối
  tiếp: `POST /api/ffmpeg/download` + nút "Tải FFmpeg" ở tab Cài đặt
  (xem ADR-07).

## 5. File bằng chứng trong thư mục này

- `ffmpeg-n9.0.2-57-gd838f9f9ae-linux64-lgpl-9.0.tar.xz` (137 MB) +
  `ffmpeg-n9.0.2-57-gd838f9f9ae-win64-lgpl-9.0.zip` (172 MB) — archive
  gốc tải từ BtbN (đối chiếu checksum ở §2).
- `checksums-autobuild-2026-11-18-12-39.sha256` — file checksum do BtbN
  công bố. `btbn-readme.md` — README BtbN (mục phân biệt gpl/lgpl).
- `FFMPEG-DOWNLOAD-VERIFICATION.md` — file này.
