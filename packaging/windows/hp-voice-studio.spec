# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — HP Voice Studio, bản Windows (TK4.1, SPEC §12/§10 T4.1).

BLOCKER ĐÃ BIẾT (ghi rõ theo ticket TK4.1): repo HP Voice Studio hiện chỉ
tồn tại local (``git remote`` trống — chưa có repo GitHub), nên workflow
``.github/workflows/build-windows.yml`` CHƯA CHẠY ĐƯỢC. Spec này chỉ được
kiểm chứng bằng parse/syntax trên VM Linux (``py_compile`` + ``pyinstaller
--help``); build Windows thật + smoke test trên runner sạch chỉ chạy được
sau khi anh tạo repo GitHub và push code lên (xem workflow, mục "BLOCKER").

Chạy (chỉ trên Windows — PyInstaller KHÔNG build chéo từ Linux):
    python scripts/build_windows.py
hoặc trực tiếp:
    pyinstaller packaging/windows/hp-voice-studio.spec

Quyết định đóng gói (SPEC §12 TK4.1, §15 Q2/Q21, ADR-07):
- Entry: ``src/hpvoice/shell.py`` (DesktopShell TK4.8) — .exe mở cửa sổ
  desktop pywebview/WebView2, KHÔNG hiện console đen (``console=False``).
- One-dir (KHÔNG onefile — bẫy TH-31): thư mục ``dist/hp-voice-studio/``.
- Collect (TH-18 — thiếu là .exe chết lúc chạy): ``--collect-all keyring``
  (entry points backend + pywin32-ctypes), ``--collect-all onnxruntime``,
  ``--collect-all tokenizers``.
- KHÔNG collect binary FFmpeg (Q21 — ĐÃ CHỐT 04:35 19/11: FFmpeg tải cài
  sau, bộ cài giữ 100% Apache 2.0): KHÔNG ``--collect-all imageio_ffmpeg``,
  KHÔNG ``--add-data`` thư mục ``imageio_ffmpeg/binaries/*`` — bộ lọc cuối
  file này còn loại bỏ mọi binary FFmpeg lọt vào TOC. Không có FFmpeg thì
  app chỉ xuất WAV + báo rõ (FFmpegManager, TK4.9), không crash; lần đầu
  cần MP3, ``FFmpegManager.download()`` tải thật bản LGPL tĩnh từ
  BtbN/FFmpeg-Builds (release đã ghim, kiểm SHA-256 + giấy phép — xem
  ADR-07) về thư mục dữ liệu người dùng.
- Model theo Q2 — mặc định TẢI LẦN ĐẦU (chưa chốt kèm model sẵn): KHÔNG
  ``--add-data`` model vào bộ cài. Lần chạy đầu, V3Engine lười nạp tải
  model (~608 MB, đã đo trên VM) về thư mục dữ liệu + kiểm checksum, UI
  hiện màn hình tải/tiến trình (xem docs/model-download.md). Ngân sách bộ
  cài Q2 ~300–400 MB (không cộng ~165 MB binary FFmpeg — Q21).
- Giảm kích thước (19/11, evidence/size-reduction/SIZE-REDUCTION-REPORT.md):
  KHÔNG đóng gói librosa/numba/llvmlite/scipy/sklearn/pandas/gradio/PIL —
  đã kiểm chứng bằng thí nghiệm chặn import + TTS/clone thật: SDK v3 Turbo
  không cần chúng (các chỗ dùng librosa trong SDK đều có fallback
  soundfile+soxr/numpy), time-stretch mặc định đã chuyển sang FFmpeg atempo
  (post.py, engine mặc định "atempo"; librosa chỉ còn là dự phòng tùy chọn
  trên máy dev). Tiết kiệm ~290 MB (llvmlite 171M + scipy 72M + sklearn
  16M + pandas 18M + numba 4M + phần .pyc trong exe). Giữ PyMuPDF (53M,
  tính năng đọc PDF thật) và onnxruntime (73M, engine) — xem bảng trước/sau
  trong báo cáo evidence.
- UI web (``ui/``) đóng gói kèm làm data (server phục vụ ở /ui).
  LƯU Ý layout frozen: ``server.py`` tính ``UI_DIR`` = parents[3] của
  file server (tức thư mục gốc của dist, cạnh .exe) — nên ``ui/`` phải nằm
  ở GỐC dist, không nằm trong ``_internal/``. ``datas`` của PyInstaller
  đặt file vào ``_internal/`` nên ``scripts/build_windows.py`` sau khi
  build sẽ copy ``ui/`` ra gốc dist (bước post-build, có kiểm chứng).
  Bước copy đó là bắt buộc — thiếu là GET / trả JSON thay vì redirect
  về /ui/index.html.
"""
import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

REPO_DIR = Path(SPECPATH).resolve().parent.parent  # packaging/windows/ -> repo
# LƯU Ý (19/11, sửa lỗi off-by-one): SPECPATH của PyInstaller là THƯ MỤC
# chứa spec (không phải đường dẫn file spec), nên từ packaging/windows/
# chỉ cần .parent.parent để về repo root. Bản cũ dùng .parent.parent.parent
# nên REPO_DIR trỏ ra ngoài repo (workspace) và build lỗi "script .../src/
# hpvoice/shell.py not found" — lỗi này chặn MỌI build từ spec này (cả
# Windows CI sau này), không riêng build Linux. Đã kiểm chứng bằng build
# Linux sau khi sửa (xem evidence/size-reduction/pyinstaller-build.log).
SRC_DIR = REPO_DIR / "src"

# --- Collect-all bắt buộc (TH-18) -------------------------------------------
tmp_ret = collect_all("keyring")
keyring_datas = tmp_ret[0]
keyring_binaries = tmp_ret[1]
keyring_hiddenimports = tmp_ret[2]

tmp_ret = collect_all("onnxruntime")
onnx_datas = tmp_ret[0]
onnx_binaries = tmp_ret[1]
onnx_hiddenimports = tmp_ret[2]

tmp_ret = collect_all("tokenizers")
tokenizers_datas = tmp_ret[0]
tokenizers_binaries = tmp_ret[1]
tokenizers_hiddenimports = tmp_ret[2]

a = Analysis(
    [str(SRC_DIR / "hpvoice" / "shell.py")],
    pathex=[str(SRC_DIR)],
    binaries=[],
    datas=[
        (str(REPO_DIR / "ui"), "ui"),  # UI tĩnh (xem lưu ý UI_DIR ở đầu file)
        (str(REPO_DIR / "config.example.yaml"), "."),
    ]
    + keyring_datas
    + onnx_datas
    + tokenizers_datas,
    hiddenimports=[
        "uvicorn",
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "fastapi",
        "pydantic",
        "httpx",
        "yaml",
        "keyring",
        "webview",  # pywebview (tùy chọn lúc chạy — có thì mở cửa sổ, thiếu thì báo rõ)
        "clr_loader",  # backend .NET của pywebview trên Windows
        "imageio_ffmpeg",  # CHỈ code (không kèm binary — xem bộ lọc dưới)
        "soundfile",
        "numpy",
        "fitz",  # PyMuPDF (đọc PDF)
        "docx",  # python-docx
        # Router API (BẮT BUỘC — TH-18): server.py nạp router ĐỘNG bằng
        # pkgutil.iter_modules + importlib.import_module (tên module ghép
        # từ chuỗi) nên PyInstaller KHÔNG thấy qua static analysis. Không
        # liệt kê ở đây thì TOC có 0 module routes_* -> .exe boot được,
        # GET / còn redirect về /ui, nhưng mọi API (/health, /v1/voices,
        # /v1/audio/speech...) đều 404. Đã gặp thật ở build Linux TK4.2
        # (lần build đầu thiếu hiddenimports này).
        "hpvoice.api.routes_batch",
        "hpvoice.api.routes_dialogue",
        "hpvoice.api.routes_files",
        "hpvoice.api.routes_history",
        "hpvoice.api.routes_jobs",
        "hpvoice.api.routes_settings",
        "hpvoice.api.routes_srt",
        "hpvoice.api.routes_tts",
        "hpvoice.api.routes_voices",
    ]
    + keyring_hiddenimports
    + onnx_hiddenimports
    + tokenizers_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "torch",  # VieNeu-TTS v3 dùng ONNX, không cần torch
        "tensorflow",
        "matplotlib",
        "tkinter",
        "PyQt5",
        "PyQt6",
        "PySide2",
        "PySide6",
        # Giảm kích thước Q2 (19/11 — xem evidence/size-reduction):
        # SDK v3 Turbo + app đều không cần các gói này lúc chạy (đã kiểm
        # chứng bằng thí nghiệm chặn import + TTS/clone thật). librosa chỉ
        # còn là dự phòng tùy chọn trên máy dev (post.py bắt ImportError
        # thành StretchUnavailableError rõ ràng). gradio bị kéo vào qua
        # huggingface_hub._webhooks_server (không dùng); PIL bị kéo qua
        # gradio + huggingface_hub.inference (không dùng); pandas/sklearn/
        # scipy/numba/llvmlite chỉ là dependency của librosa.
        "librosa",
        "numba",
        "llvmlite",
        "scipy",
        "sklearn",
        "pandas",
        "gradio",
        "PIL",
        "joblib",
        "pooch",
    ],
    noarchive=False,
    optimize=0,
)

# --- Q21: loại bỏ MỌI binary FFmpeg lọt vào TOC ------------------------------
# (binary imageio-ffmpeg là GPL v3, ~165 MB — không đóng gói kèm bộ cài.)
def _is_ffmpeg_binary(toc_entry):
    dest_name = str(toc_entry[0]).lower()
    src_path = str(toc_entry[1]).lower() if len(toc_entry) > 1 else ""
    return "ffmpeg" in dest_name or "imageio_ffmpeg" in src_path


a.binaries = [entry for entry in a.binaries if not _is_ffmpeg_binary(entry)]
a.datas = [entry for entry in a.datas if "imageio_ffmpeg" not in str(entry[1]).lower()]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="hp-voice-studio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX nén DLL ONNX hay gây lỗi lúc chạy — tắt cho chắc
    console=False,  # TK4.8: ẩn console đen (--noconsole/pythonw)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="hp-voice-studio",
)

# Ghi chú cho bước post-build (scripts/build_windows.py): copy ui/ ra gốc
# dist/hp-voice-studio/ui (xem lưu ý UI_DIR ở đầu file) + ghi .sha256.
# Không copy ở đây vì DISTPATH chưa chắc đã là thư mục đích cuối khi spec
# được gọi với --distpath khác — build_windows.py làm bước này sau build.
