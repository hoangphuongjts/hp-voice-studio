# Máy sạch + Unicode path — checklist kiểm tra (TK4.7, SPEC §12/§10 T4.1/T4.5)

> Tài liệu này thuộc ticket TK4.7. Agent RELEASE đưa nội dung mục 1–2 vào
> README (mục "Yêu cầu hệ thống / Máy sạch") — file này giữ bản đầy đủ
> kèm lệnh kiểm tra để coordinator/kiểm chứng viên chạy lại được.
>
> Trạng thái kiểm chứng (19/11/2026, VM Linux của Annie):
> - Mục 1a (WebView2) + 1b (VC++ Redistributable): **chỉ kiểm được trên
>   máy Windows thật** — ghi "chờ kiểm chứng thật" (C9). Lệnh kiểm tra
>   Windows đã ghi sẵn ở dưới, chưa từng chạy.
> - Mục 1c (ONNX DLLs): **đã kiểm trên VM Linux** — `onnxruntime 1.32.0`,
>   `libonnxruntime.so.1.32.0` có trong venv; gói Linux đóng gói kèm qua
>   `--collect-all onnxruntime` (xem `evidence/tk4-package/linux-build.log`).
>   Bản Windows: DLL `onnxruntime.dll` đi kèm qua cùng collect-all —
>   chờ kiểm chứng thật trên máy Windows (C1).
> - Mục 2 (Unicode path): **đã kiểm trên VM Linux** — test
>   `tests/test_unicode_paths.py` PASS (thư mục "Thư mục có dấu tiếng
>   Việt", config/history/output/WAV). Đường dẫn Windows
>   `C:\Người dùng\HP Voice Studio` vẫn **chờ kiểm chứng thật** (C21).

## 1. Runtime phụ thuộc trên máy sạch (Windows)

Máy đích (máy anh) có thể không có Python — bộ cài PyInstaller one-dir
đã gồm Python + mọi package trong `requirements.txt`, nên **không cần
cài Python**. Ba thứ dưới đây KHÔNG nằm trong bộ cài và phải kiểm tra
riêng trước khi mở app:

### 1a. WebView2 Runtime (bắt buộc cho cửa sổ desktop — TK4.8)

- Vì sao cần: `DesktopShell` dùng pywebview, trên Windows pywebview chạy
  trên Microsoft Edge WebView2. Không có WebView2 thì cửa sổ không mở
  được (shell báo rõ + thoát mã 3, server không chạy chồng).
- Kiểm tra (PowerShell, chạy trên máy Windows thật):
  ```powershell
  Get-ItemProperty "HKLM:\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-9251-2340B7922D9D}" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty pv
  ```
  Có giá trị `pv` (VD `130.0.2849.80`) = đã cài. Không có khóa này =
  chưa cài.
- Khắc phục: tải **Microsoft Edge WebView2 Runtime (Evergreen Standalone
  Installer)** từ trang chính thức của Microsoft
  (`https://developer.microsoft.com/microsoft-edge/webview2/`), chạy file
  cài, mở lại app. Windows 11 thường đã có sẵn WebView2 theo Edge.
- Lưu ý: GitHub Actions runner `windows-latest` đã có sẵn WebView2 nên
  smoke test trong workflow chạy được; máy anh thì phải kiểm tay (C9).

### 1b. VC++ Redistributable (bắt buộc cho ONNX Runtime DLL)

- Vì sao cần: `onnxruntime.dll` (đóng gói kèm qua `--collect-all
  onnxruntime`) phụ thuộc Visual C++ runtime. Thiếu thì .exe chết lúc
  nạp model với lỗi `VCRUNTIME140.dll / MSVCP140.dll was not found`.
- Kiểm tra (PowerShell):
  ```powershell
  Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" -ErrorAction SilentlyContinue | Select-Object Installed, Version
  ```
  `Installed = 1` = đã cài.
- Khắc phục: tải **Microsoft Visual C++ Redistributable 2015–2022 (x64)**
  từ trang chính thức của Microsoft, cài rồi mở lại app.

### 1c. ONNX Runtime DLLs (đóng gói kèm — không cần cài thêm)

- `onnxruntime.dll` + `onnxruntime_providers_shared.dll` được PyInstaller
  đóng gói kèm qua `--collect-all onnxruntime` (SPEC TK4.1(d), TH-18).
  Người dùng **không cần cài thêm**.
- Kiểm tra sau khi build (trên máy build / trong dist):
  ```powershell
  Get-ChildItem dist\hp-voice-studio -Recurse -Filter "onnxruntime*.dll" | Select-Object Name, Length
  ```
  Phải thấy ít nhất `onnxruntime.dll`. Không thấy = build lỗi collect,
  không được phát hành (kiểm chứng lại ở TK4.1).
- Trên VM Linux đã kiểm tương đương: `onnxruntime 1.32.0`,
  `libonnxruntime.so.1.32.0` có trong `.venv` và được collect vào gói
  Linux (xem `evidence/tk4-package/linux-build.log`).

### 1d. FFmpeg — KHÔNG kèm bộ cài (Q21, xem thêm TK4.9)

- Bộ cài **không** chứa binary FFmpeg (giữ 100% Apache 2.0). Không có
  FFmpeg thì app vẫn chạy, chỉ xuất WAV + báo rõ khi cần MP3.
- Muốn xuất MP3: cài FFmpeg hệ thống (VD `winget install Gyan.FFmpeg`)
  rồi mở lại app — `FFmpegManager` tự tìm `ffmpeg` trên PATH.

## 2. Đường dẫn có dấu tiếng Việt / khoảng trắng (T4.5, C21)

- Vấn đề (TH-32): app cài vào thư mục có dấu/khoảng trắng
  (VD `C:\Người dùng\HP Voice Studio`) hoặc model/cache/output đặt ở
  đường dẫn như vậy — thành phần nào không xử lý Unicode thì lỗi.
- Đã kiểm trên VM Linux (`tests/test_unicode_paths.py`, PASS):
  thư mục `Thư mục có dấu tiếng Việt` chứa config (`ConfigStore`
  đọc/ghi), history (`HistoryStore.add` + `list_items`), preview cache
  (`PreviewCache.put/get`), file WAV ghi/đọc lại bằng `soundfile`.
- Chờ kiểm chứng thật trên máy Windows (C21): cài app vào
  `C:\Người dùng\HP Voice Studio` -> chạy T1.2 (tạo WAV thật) -> đóng
  app -> kiểm tra không còn tiến trình chiếm 8124 -> mở lại -> bind
  8124 thành công; mở 2 instance -> instance 2 báo rõ + không chạy
  chồng (T4.5).
- Nếu một thành phần lỗi trên đường dẫn có dấu: đặt `storage.output_dir`
  / `storage.history_dir` / `engine.v3.model_dir` trong `config.yaml`
  sang đường dẫn ASCII tạm thời rồi báo lại cho team (ghi rõ thành phần
  nào lỗi, kèm log).

## 3. Đóng/mở lại + chống trùng instance (T4.5)

- Đóng cửa sổ app -> `DesktopShell` dừng server + giải phóng cổng 8124.
  Kiểm tra (PowerShell, sau khi đóng app):
  ```powershell
  Get-NetTCPConnection -LocalPort 8124 -ErrorAction SilentlyContinue
  ```
  Không trả kết nối nào = cổng đã được giải phóng. Còn kết nối = tiến
  trình ma — tìm PID (`Get-Process`) và dừng tay, báo lại cho team.
- Lưu ý khi kiểm bằng `bind()` tay (đã gặp khi test trên VM): ngay sau
  khi server dừng, các kết nối cũ còn ở trạng thái TIME-WAIT trên cổng
  8124 — `bind()` KHÔNG đặt `SO_REUSEADDR` sẽ báo "cổng bận" sai dù
  không còn tiến trình nào listen (đã kiểm bằng `ss`: không còn socket
  LISTEN, chỉ còn TIME-WAIT). Server thật (uvicorn) luôn đặt
  `SO_REUSEADDR` nên mở lại bind được ngay — đây là hành vi TCP bình
  thường, không phải tiến trình ma. Code kiểm cổng trong
  `src/hpvoice/shell.py::_port_free` đã đặt `SO_REUSEADDR` cho đúng.
- Mở 2 instance: instance thứ 2 in thông báo "HP Voice Studio đã đang
  chạy" + thoát mã 2, không mở cửa sổ mới, không chạy chồng server
  (lock file trên Linux / mutex `HPVoiceStudio-single-instance` trên
  Windows — xem `src/hpvoice/shell.py`).
- Kiểm chứng bằng test (không cần Windows):
  `pytest tests/test_shell.py -v` — test vòng đời + trùng instance bằng
  webview giả + server thật (FakeEngine).
