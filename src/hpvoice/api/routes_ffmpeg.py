"""Route FFmpeg — trạng thái + tải FFmpeg LGPL về lần đầu (nối tiếp Q21).

- ``GET /api/ffmpeg/status``: FFmpeg hiện có hay chưa (hệ thống / LGPL tải
  về / wheel imageio-ffmpeg / chưa có) + trạng thái tải.
- ``POST /api/ffmpeg/download``: bắt đầu tải FFmpeg LGPL (BtbN) trong luồng
  nền, trả ngay (202) — không chặn request. Bấm lần 2 trong lúc đang tải
  thì trả trạng thái đang tải, KHÔNG khởi động thêm luồng (tử huyệt: 2 lần
  tải cùng lúc sẽ ghi đè file ``.part``/archive lẫn nhau -> file hỏng,
  checksum lệch). Đã có FFmpeg thì trả ``already_available``, không tải lại.
- ``GET /api/ffmpeg/download``: poll trạng thái tải (tiến trình % + thông
  báo tiếng Việt).

Vì sao KHÔNG dùng JobQueue (SPEC §4, Q16): runner của JobQueue sau khi
``run_fn`` xong sẽ gọi ``_persist_job_result`` — ghi kết quả ra outputs/
+ lưu history như một bản TTS. Tải FFmpeg không phải job TTS (không có
audio, không lưu history) nên dùng luồng nền riêng + state trên
``app.state.ffmpeg_download`` (mỗi app một state, test không lẫn nhau).

Tiến trình %: callback ``on_progress`` của ``FFmpegManager.download()``
chỉ báo trong lúc tải archive (giai đoạn kiểm chứng SHA-256 + giải nén
không báo tiến trình) nên map: tải archive = 0–90%, kiểm chứng/giải nén
= 90% (stage "verifying"), xong = 100%. Không bịa % cho giai đoạn kiểm
chứng. Mất mạng giữa chừng: ``download()`` giữ file ``.part`` để lần sau
tải tiếp + trả thông báo tiếng Việt rõ ràng; endpoint chỉ hiện lại thông
báo đó, không crash.
"""
from __future__ import annotations

import shutil
import threading
from pathlib import Path

from fastapi import APIRouter, Request

from hpvoice.audio.ffmpeg_manager import FFmpegManager

router = APIRouter()

#: Tải archive chiếm 90% thanh tiến trình; 10% còn lại là kiểm chứng +
#: giải nén (không báo tiến trình từng bước nên giữ 90% tới khi xong).
_DOWNLOAD_FRACTION = 0.9


def _state(request: Request):
    return request.app.state


class FFmpegDownloadState:
    """Trạng thái tải FFmpeg của một app (an toàn luồng).

    ``status``: idle | downloading | done | error.
    ``stage``: idle | downloading | verifying | done | error.
    ``progress``: 0.0–1.0 (theo quy ước Job.progress); ``percent``: 0–100.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._data: dict = {
            "status": "idle",
            "stage": "idle",
            "progress": 0.0,
            "percent": 0,
            "message": "Chưa tải FFmpeg.",
            "path": None,
        }

    def snapshot(self) -> dict:
        """Bản sao trạng thái hiện tại (đọc không chặn tải)."""
        with self._lock:
            return dict(self._data)

    def _set(self, **fields) -> None:
        with self._lock:
            self._data.update(fields)

    def is_downloading(self) -> bool:
        with self._lock:
            return self._data["status"] == "downloading"

    def start(self, manager: FFmpegManager) -> bool:
        """Khởi động luồng tải nếu chưa có luồng nào đang chạy.

        Trả False khi đã có luồng đang tải (caller trả trạng thái hiện tại,
        không khởi động thêm).
        """
        with self._lock:
            if self._data["status"] == "downloading":
                return False
            self._data.update({
                "status": "downloading",
                "stage": "downloading",
                "progress": 0.0,
                "percent": 0,
                "message": "Đang tải FFmpeg LGPL về lần đầu (cần mạng)…",
                "path": None,
            })
        thread = threading.Thread(
            target=self._run, args=(manager,),
            name="hp-ffmpeg-download", daemon=True)
        with self._lock:
            self._thread = thread
        thread.start()
        return True

    def _run(self, manager: FFmpegManager) -> None:
        """Luồng tải: gọi manager.download() + map tiến trình."""
        def on_progress(done: int, total: int) -> None:
            if total and total > 0:
                frac = max(0.0, min(1.0, done / total))
                if done >= total:
                    self._set(stage="verifying",
                              progress=_DOWNLOAD_FRACTION,
                              percent=int(_DOWNLOAD_FRACTION * 100),
                              message="Đã tải xong archive — đang kiểm tra "
                                      "checksum + giải nén…")
                else:
                    self._set(progress=_DOWNLOAD_FRACTION * frac,
                              percent=int(_DOWNLOAD_FRACTION * frac * 100))

        try:
            path = manager.download(on_progress=on_progress)
        except Exception as exc:  # noqa: BLE001 - lỗi lạ cũng thành trạng thái error rõ ràng
            self._set(status="error", stage="error", progress=0.0, percent=0,
                      message=f"Tải FFmpeg thất bại (lỗi không ngờ tới): {exc}. "
                              "Hãy thử lại, hoặc cài FFmpeg hệ thống để xuất MP3 ngay.")
            return
        if path:
            self._set(status="done", stage="done", progress=1.0, percent=100,
                      message="Đã có FFmpeg — xuất MP3 được.",
                      path=str(path))
        else:
            # download() đã ghi lý do tiếng Việt vào status_message
            # (mất mạng / platform chưa ghim / checksum lệch).
            self._set(status="error", stage="error", progress=0.0, percent=0,
                      message=str(manager.status_message or
                                  "Tải FFmpeg thất bại — thử lại hoặc cài "
                                  "FFmpeg hệ thống để xuất MP3 ngay."))


def _download_state(state) -> FFmpegDownloadState:
    """State tải FFmpeg của app (tạo lười — mỗi app một state riêng)."""
    dl = getattr(state, "ffmpeg_download", None)
    if dl is None:
        dl = FFmpegDownloadState()
        state.ffmpeg_download = dl
    return dl


def _describe(manager: FFmpegManager, path: str | None) -> dict:
    """Mô tả FFmpeg hiện có: loại (system/downloaded/wheel/other/none),
    giấy phép, thông báo tiếng Việt. Không bịa license của FFmpeg hệ
    thống (do người dùng tự cài — ghi rõ không xác định)."""
    if not path:
        return {
            "available": False,
            "kind": "none",
            "path": None,
            "license": None,
            "message": str(manager.status_message or
                           "Chưa có FFmpeg — chỉ xuất được WAV."),
        }
    if shutil.which("ffmpeg") == path:
        kind, license_text = "system", (
            "Không xác định (FFmpeg hệ thống do người dùng tự cài — xem "
            "`ffmpeg -version` trên máy).")
    elif str(path).startswith(str(manager.ffmpeg_dir)):
        kind, license_text = "downloaded", "LGPL v3 (BtbN/FFmpeg-Builds)"
    elif "imageio_ffmpeg" in str(path):
        kind, license_text = "wheel", (
            "GPL v3 (imageio-ffmpeg 0.8.1 — đường dự phòng cho máy dev, "
            "binary đi kèm wheel lúc pip install, không có trong bộ cài).")
    else:
        kind, license_text = "other", "Không xác định."
    return {
        "available": True,
        "kind": kind,
        "path": str(path),
        "license": license_text,
        "message": str(manager.status_message or f"Đã có FFmpeg: {path}"),
    }


def _envelope(state, manager: FFmpegManager) -> dict:
    """Envelope chung cho GET /status và POST /download."""
    path = manager.locate()
    info = _describe(manager, path)
    info["download"] = _download_state(state).snapshot()
    return info


@router.get("/api/ffmpeg/status")
def ffmpeg_status(request: Request):
    """Trạng thái FFmpeg hiện tại + trạng thái tải (không khởi động tải)."""
    state = _state(request)
    return _envelope(state, state.ffmpeg)


@router.get("/api/ffmpeg/download")
def ffmpeg_download_status(request: Request):
    """Poll trạng thái tải FFmpeg (để UI cập nhật thanh tiến trình)."""
    return _download_state(_state(request)).snapshot()


@router.post("/api/ffmpeg/download")
def ffmpeg_download(request: Request):
    """Bắt đầu tải FFmpeg LGPL (trả ngay, không chặn).

    - Đã có FFmpeg -> 200 ``already_available`` (không tải lại).
    - Đang tải -> 200 ``downloading`` (không khởi động thêm).
    - Chưa có + chưa tải -> 202 ``downloading`` (luồng nền đã bắt đầu).
    - Tải xong trước đó -> 200 ``done``.
    """
    state = _state(request)
    manager: FFmpegManager = state.ffmpeg
    dl = _download_state(state)
    snap = dl.snapshot()
    if snap["status"] in ("downloading", "done"):
        return _envelope(state, manager)
    # Kiểm tra FFmpeg hiện có trước (hệ thống / đã tải / wheel):
    # có rồi thì không tải lại; chưa có thì khởi động luồng nền.
    path = manager.locate()
    if path:
        info = _describe(manager, path)
        info["download"] = snap
        return info
    started = dl.start(manager)
    if not started:
        # Cuộc đua hiếm: một request khác vừa khởi động xong.
        return _envelope(state, manager)
    # 202: tải đã bắt đầu ở luồng nền; client poll GET /api/ffmpeg/download.
    # Không gọi _envelope() ở đây (tránh locate() lần 2 trong lúc luồng tải
    # đang chạy); dùng thông tin "chưa có FFmpeg" từ lần kiểm tra trên.
    from fastapi.responses import JSONResponse

    info = _describe(manager, None)
    info["download"] = dl.snapshot()
    return JSONResponse(status_code=202, content=info)
