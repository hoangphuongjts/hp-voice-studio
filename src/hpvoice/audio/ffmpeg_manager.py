"""FFmpegManager — TK1.6 tối thiểu + TK4.9 checksum + Q21 tải thật (BtbN LGPL).

Quyết định Q21 (SPEC §0, ADR-07): FFmpeg TÁCH KHỎI BỘ CÀI, tải cài sau.
Thứ tự tìm của ``locate()``:
1. FFmpeg hệ thống (``shutil.which("ffmpeg")``) — ưu tiên, không cần tải.
2. Binary LGPL đã tải về thư mục dữ liệu người dùng (``FFmpegManager.
   download()`` — tải thật từ BtbN/FFmpeg-Builds, xem bảng
   ``FFMPEG_DOWNLOADS``; kiểm SHA-256 + ``ffmpeg -version`` +
   ``-buildconf`` trước khi dùng).
3. Binary ``imageio-ffmpeg`` đi kèm wheel (đường dự phòng cũ, chỉ còn
   cho máy dev đã ``pip install`` — binary này là GPL v3, KHÔNG có trong
   .exe vì bộ lọc trong ``packaging/windows/hp-voice-studio.spec`` loại
   bỏ mọi binary imageio-ffmpeg khỏi bộ cài).
4. Không có → chỉ xuất WAV + báo rõ lý do, KHÔNG crash.

TẢI THẬT (sửa khoảng trống Q21, đo thật 19/11/2026): ``download()`` tải
archive FFmpeg LGPL tĩnh từ release BtbN đã ghim (tag autobuild cố
định, KHÔNG dùng URL "latest" — file "latest" thay đổi theo từng bản
rebuild nên checksum ghim sẽ lệch), kiểm SHA-256 của archive theo bảng
ghim (đã đối chiếu với ``checksums.sha256`` do chính BtbN công bố cho
release đó), giải nén an toàn CHỈ đúng file binary ``ffmpeg[.exe]``
(không ``extractall`` — chống path traversal), rồi kiểm chứng binary:
SHA-256 + kích thước + chạy ``ffmpeg -version`` thật + ``-buildconf``
không có ``--enable-gpl``/``--enable-nonfree`` + có encoder
``libmp3lame``. Chỉ khi tất cả đạt mới dùng binary đó.

LƯU Ý GIẤY PHÉP — ``--enable-version3`` KHÔNG phải GPL: theo giấy phép
của chính FFmpeg, ``--enable-version3`` chỉ nâng (L)GPL lên v3 (bản này
là LGPL v3 — file ``LICENSE.txt`` trong archive là văn bản LGPL v3);
chỉ ``--enable-gpl`` (kéo theo libx264/libx265, các thư viện chỉ-GPL)
mới biến binary thành GPL. BtbN README cũng ghi rõ bản ``lgpl`` "lacking
libraries that are GPL-only. Most prominently libx264 and libx265".
Vì vậy kiểm tra giấy phép chỉ từ chối khi thấy ``--enable-gpl`` hoặc
``--enable-nonfree``; ``--enable-version3`` được chấp nhận. Binary
imageio-ffmpeg cũ (đường 3) vẫn là GPL v3 — giữ lại chỉ làm dự phòng
cho máy dev, không phải nguồn tải chính.

Tải có resume (HTTP Range, file ``.part``), báo tiến trình tải qua
callback ``on_progress(bytes_done, bytes_total)``. Mất mạng giữa chừng:
giữ file ``.part`` để lần sau tải tiếp, không crash, không dùng file
dở. Không có mạng ngay từ đầu: trả None + thông báo tiếng Việt rõ
ràng, hướng dẫn cài FFmpeg hệ thống; app vẫn xuất WAV được.

Binary tải về lưu vào ``<thư mục dữ liệu>/ffmpeg/`` (mặc định
``~/.local/share/hp-voice-studio/ffmpeg`` trên Linux,
``%LOCALAPPDATA%\\HP Voice Studio\\ffmpeg`` trên Windows,
``~/Library/Application Support/HP Voice Studio/ffmpeg`` trên macOS),
KHÔNG ghi vào thư mục cài đặt. Hồ sơ tải (nguồn, checksum, giấy phép)
ghi vào ``ffmpeg-download.json`` trong thư mục đó; kết quả kiểm chứng
ghi vào ``ffmpeg-manifest.json`` trong ``data_dir`` (nếu có).
"""
from __future__ import annotations

import hashlib
import json
import os
import platform as platform_mod
import shutil
import subprocess
import sys
import tarfile
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

__all__ = [
    "FFmpegManager",
    "FFmpegError",
    "NO_FFMPEG_MESSAGE",
    "PINNED_FFMPEG_SHA256",
    "FFMPEG_DOWNLOADS",
    "sha256_file",
]

#: Kiểu callback tiến trình: on_progress(bytes_done, bytes_total).
ProgressCallback = Callable[[int, int], None]


class FFmpegError(RuntimeError):
    """Lỗi FFmpeg (không tìm thấy binary / tải thất bại / giải mã thất bại)."""


#: Thông báo khi không tìm thấy FFmpeg — dùng cho UI/API để báo rõ.
NO_FFMPEG_MESSAGE = (
    "Không tìm thấy FFmpeg trên máy (cả FFmpeg hệ thống lẫn bản tải sau). "
    "Chỉ xuất được WAV; muốn xuất MP3 hãy để app tải FFmpeg LGPL về lần đầu "
    "chạy (cần mạng, ~137 MB trên Linux / ~172 MB trên Windows — gọi "
    "FFmpegManager.download()), hoặc cài FFmpeg hệ thống. Không có lỗi gì "
    "khác — audio WAV vẫn tạo bình thường."
)

#: Bảng checksum SHA-256 ghim cho binary FFmpeg của imageio-ffmpeg 0.8.1
#: (đường dự phòng cũ — xem docstring đầu file). Nguồn: đo thật bằng
#: ``sha256sum`` trên VM này ngày 19/11/2026 (xem
#: evidence/release-gate/RELEASE-GATE-v1.md). Chỉ platform đã đo thật mới
#: có ``sha256``; platform chưa đo để ``sha256=None`` kèm ghi chú — KHÔNG
#: bịa checksum cho platform chưa đo.
PINNED_FFMPEG_SHA256: dict[str, dict[str, object]] = {
    "linux-x86_64": {
        "imageio_ffmpeg_version": "0.8.1",
        "binary": "ffmpeg-linux-x86_64-v9.0.2",
        "size_bytes": 172692552,
        "sha256": "0d709a0bed1a43f24cd2c420878c63afea4580671b6949ad19ed124572f3bc3d",
        "source": "do that bang sha256sum tren VM Linux 19/11/2026 (TK4.9)",
        "license": "GPL v3 (ffmpeg -buildconf: --enable-gpl --enable-version3)",
    },
    # Chưa đo thật — đo ở TK4.1 trên runner Windows / máy macOS rồi ghim sau.
    "windows-x86_64": {
        "imageio_ffmpeg_version": "0.8.1",
        "binary": "ffmpeg-win-x86_64-v9.0.2.exe",
        "size_bytes": None,
        "sha256": None,
        "source": "CHUA DO — can do that o TK4.1 (runner Windows)",
        "license": "GPL v3 (du kien theo SPEC §13.7 — kiem tra bang -buildconf khi do)",
    },
    "windows-aarch64": {
        "imageio_ffmpeg_version": "0.8.1",
        "binary": "ffmpeg-win-aarch64-v9.0.1.exe",
        "size_bytes": None,
        "sha256": None,
        "source": "CHUA DO — can do that o TK4.1",
        "license": "GPL v3 (du kien — kiem tra bang -buildconf khi do)",
    },
    "macos-x86_64": {
        "imageio_ffmpeg_version": "0.8.1",
        "binary": "ffmpeg-macos-x86_64-v9.0.2",
        "size_bytes": None,
        "sha256": None,
        "source": "CHUA DO — ngoai muc tieu v1 (Windows + Linux)",
        "license": "GPL v3 (du kien — kiem tra bang -buildconf khi do)",
    },
    "macos-aarch64": {
        "imageio_ffmpeg_version": "0.8.1",
        "binary": "ffmpeg-macos-aarch64-v9.0",
        "size_bytes": None,
        "sha256": None,
        "source": "CHUA DO — ngoai muc tieu v1 (Windows + Linux)",
        "license": "GPL v3 (du kien — kiem tra bang -buildconf khi do)",
    },
    "linux-aarch64": {
        "imageio_ffmpeg_version": "0.8.1",
        "binary": "ffmpeg-linux-aarch64-v9.0.2",
        "size_bytes": None,
        "sha256": None,
        "source": "CHUA DO — ngoai muc tieu v1 (Windows + Linux)",
        "license": "GPL v3 (du kien — kiem tra bang -buildconf khi do)",
    },
}

#: Bảng tải FFmpeg LGPL ghim cho ``download()`` — đo thật 19/11/2026, đối
#: chiếu với file ``checksums.sha256`` do chính BtbN công bố cho release
#: ``autobuild-2026-11-18-12-39`` (xem evidence/ffmpeg-download/).
#: Release autobuild có tag ngày cố định nên file không thay đổi; KHÔNG
#: dùng URL "latest" (file thay đổi theo từng bản rebuild, checksum ghim
#: sẽ lệch). Binary tải về là bản TĨNH (static), một file duy nhất, không
#: cần DLL kèm theo. ``binary_sha256`` của Windows đo bằng cách đọc
#: stream ``ffmpeg.exe`` trong file .zip (không chạy .exe trên Linux).
#: Windows: checksum archive + nội dung zip đã đo thật trên Linux; việc
#: CHẠY binary Windows (``-version``/``-buildconf``/MP3) chỉ kiểm được
#: trên máy Windows thật — ghi "chờ kiểm chứng thật" (C22).
FFMPEG_DOWNLOADS: dict[str, dict[str, object]] = {
    "linux-x86_64": {
        "release": "autobuild-2026-11-18-12-39",
        "url": "https://github.com/BtbN/FFmpeg-Builds/releases/download/"
               "autobuild-2026-11-18-12-39/"
               "ffmpeg-n9.0.2-57-gd838f9f9ae-linux64-lgpl-9.0.tar.xz",
        "archive": "ffmpeg-n9.0.2-57-gd838f9f9ae-linux64-lgpl-9.0.tar.xz",
        "archive_sha256": "ead99a4068892760a01a27fa437bdf1975e29a967bc011554d518ae906b1a342",
        "archive_size_bytes": 137212900,
        "binary_member": "ffmpeg-n9.0.2-57-gd838f9f9ae-linux64-lgpl-9.0/bin/ffmpeg",
        "binary_name": "ffmpeg",
        "binary_sha256": "7febfdf8a1615bc18c9af3fb7c9cb2b7945ec5bee010a3d0a806a0eac7e9e195",
        "binary_size_bytes": 142747536,
        "version": "n9.0.2-57-gd838f9f9ae-20261118",
        "license": "LGPL v3 (BtbN lgpl; LICENSE.txt trong archive la LGPL v3; "
                   "buildconf: khong --enable-gpl/--enable-nonfree; "
                   "--enable-version3 = LGPL len v3)",
        "source": "BtbN/FFmpeg-Builds, do that + doi chieu checksums.sha256 "
                  "cua release, 19/11/2026; ffmpeg -version/-buildconf/-encoders "
                  "(libmp3lame) chay that tren VM Linux",
    },
    "windows-x86_64": {
        "release": "autobuild-2026-11-18-12-39",
        "url": "https://github.com/BtbN/FFmpeg-Builds/releases/download/"
               "autobuild-2026-11-18-12-39/"
               "ffmpeg-n9.0.2-57-gd838f9f9ae-win64-lgpl-9.0.zip",
        "archive": "ffmpeg-n9.0.2-57-gd838f9f9ae-win64-lgpl-9.0.zip",
        "archive_sha256": "51fcd00803e75229da76bac035fdec7b8f641ef2ef50bec3f9fce0e474ed366f",
        "archive_size_bytes": 171850772,
        "binary_member": "ffmpeg-n9.0.2-57-gd838f9f9ae-win64-lgpl-9.0/bin/ffmpeg.exe",
        "binary_name": "ffmpeg.exe",
        "binary_sha256": "ecc293ceb96c499984911e23c2493265d5a93b17ee72aea4747defeaa1717663",
        "binary_size_bytes": 134459392,
        "version": "n9.0.2-57-gd838f9f9ae-20261118 (du kien — chua chay that)",
        "license": "LGPL v3 (du kien theo ten ban lgpl + LICENSE.txt LGPL v3 "
                   "trong zip; buildconf chua kiem duoc tren Windows)",
        "source": "BtbN/FFmpeg-Builds, do checksum archive + sha256 ffmpeg.exe "
                  "trong zip + doi chieu checksums.sha256 cua release, "
                  "19/11/2026 tren Linux; CHUA CHAY THAT TREN WINDOWS (C22)",
    },
}

#: Chỉ cho phép tải từ host release đã ghim (chống URL bị tráo).
_ALLOWED_DOWNLOAD_PREFIX = (
    "https://github.com/BtbN/FFmpeg-Builds/releases/download/"
)


def _platform_key() -> str:
    """Khóa platform theo quy ước của imageio-ffmpeg (VD ``linux-x86_64``)."""
    try:
        from imageio_ffmpeg._definitions import get_platform  # type: ignore

        return str(get_platform())
    except Exception:  # noqa: BLE001 — gói chưa cài thì suy ra từ sys.platform
        machine = platform_mod.machine().lower()
        arch = "aarch64" if machine in ("arm64", "aarch64") else "x86_64"
        if sys.platform.startswith("win"):
            return f"windows-{arch}"
        if sys.platform.startswith("darwin"):
            return f"macos-{arch}"
        return f"linux-{arch}"


def _default_data_dir() -> Path:
    """Thư mục dữ liệu người dùng mặc định (không phải thư mục cài đặt)."""
    if sys.platform.startswith("win"):
        base = Path(os.environ.get(
            "LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "HP Voice Studio"
    if sys.platform.startswith("darwin"):
        return Path.home() / "Library" / "Application Support" / "HP Voice Studio"
    return Path(os.environ.get(
        "XDG_DATA_HOME", Path.home() / ".local" / "share")) / "hp-voice-studio"


def sha256_file(
    path: str | Path,
    on_progress: ProgressCallback | None = None,
    chunk_size: int = 1024 * 1024,
) -> tuple[str, int]:
    """Băm SHA-256 một file, báo tiến trình từng khối.

    Trả ``(hexdigest, size_bytes)``. Callback nhận ``(bytes_done,
    bytes_total)`` sau mỗi khối — dùng để hiện tiến trình kiểm chứng binary
    FFmpeg ~165 MB lần đầu (TK4.9).
    """
    path = Path(path)
    total = path.stat().st_size
    digest = hashlib.sha256()
    done = 0
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
            done += len(chunk)
            if on_progress is not None:
                on_progress(done, total)
    if on_progress is not None and total == 0:
        on_progress(0, 0)
    return digest.hexdigest(), total


class FFmpegManager:
    """Tìm/lấy đường dẫn FFmpeg và mã hoá MP3."""

    def __init__(self, data_dir: str | Path | None = None) -> None:
        self.data_dir = Path(data_dir) if data_dir else None
        #: Thư mục chứa binary FFmpeg tải về (luôn có, kể cả khi data_dir
        #: là None — khi đó dùng thư mục dữ liệu người dùng mặc định).
        self.ffmpeg_dir = (
            Path(data_dir) / "ffmpeg" if data_dir
            else _default_data_dir() / "ffmpeg"
        )
        self._cached_path: str | None = None
        self._cached = False
        self._cached_size: int | None = None
        self._cached_sha256: str | None = None
        self.status_message: str = "Chưa tìm FFmpeg."
        #: Kết quả kiểm chứng binary tải sau gần nhất (None nếu dùng FFmpeg
        #: hệ thống hoặc chưa tìm). Xem :meth:`verify_binary`.
        self.last_verification: dict[str, object] | None = None

    # -- kiểm chứng checksum (TK4.9) -------------------------------------

    def verify_binary(
        self, exe: str | Path, on_progress: ProgressCallback | None = None
    ) -> dict[str, object]:
        """Kiểm SHA-256 của một binary imageio-ffmpeg.

        Trả dict ``{platform, binary, size_bytes, sha256, expected_sha256,
        pinned, ok, message}``. ``ok=True`` khi khớp bảng ghim; ``ok=False``
        khi lệch bảng ghim (binary hỏng/khác bản — phải từ chối dùng);
        ``ok=None`` khi platform chưa có checksum ghim — khi đó SHA-256 đo
        được vẫn ghi vào manifest (nếu có ``data_dir``) để đối chiếu tay,
        KHÔNG lặng lẽ bỏ qua.
        """
        exe = Path(exe)
        platform = _platform_key()
        pinned = PINNED_FFMPEG_SHA256.get(platform, {})
        expected = pinned.get("sha256")
        actual, size = sha256_file(exe, on_progress=on_progress)
        if expected is None:
            ok: bool | None = None
            message = (
                f"Binary FFmpeg {exe.name} ({platform}): chưa có checksum "
                f"ghim cho platform này — SHA-256 đo được {actual} "
                f"({size} byte) đã ghi vào manifest để đối chiếu tay lần "
                "đầu, không tự kết luận an toàn."
            )
        elif actual == expected:
            ok = True
            message = (
                f"Binary FFmpeg {exe.name} ({platform}): SHA-256 khớp bảng "
                f"ghim ({actual[:16]}…, {size} byte)."
            )
        else:
            ok = False
            message = (
                f"Binary FFmpeg {exe.name} ({platform}): SHA-256 KHÔNG khớp "
                f"bảng ghim — đo được {actual}, ghim {expected}. Binary có "
                "thể hỏng hoặc khác bản imageio-ffmpeg 0.8.1; KHÔNG dùng. "
                "Hãy cài lại imageio-ffmpeg==0.8.1 hoặc dùng FFmpeg hệ thống."
            )
        result: dict[str, object] = {
            "platform": platform,
            "binary": exe.name,
            "size_bytes": size,
            "sha256": actual,
            "expected_sha256": expected,
            "pinned": expected is not None,
            "ok": ok,
            "message": message,
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }
        self.last_verification = result
        self._cached_sha256 = actual
        self._cached_size = size
        if self.data_dir is not None:
            self._write_manifest(result)
        return result

    def _write_manifest(self, result: dict[str, object]) -> Path | None:
        """Ghi kết quả kiểm chứng vào ``ffmpeg-manifest.json`` trong
        data_dir (gộp với nội dung cũ nếu có — không ghi đè mất hồ sơ
        tải trước đó)."""
        if self.data_dir is None:
            return None
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            manifest_path = self.data_dir / "ffmpeg-manifest.json"
            merged: dict[str, object] = {}
            if manifest_path.exists():
                try:
                    merged = json.loads(
                        manifest_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    merged = {}
            merged.update(result)
            manifest_path.write_text(
                json.dumps(merged, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            return manifest_path
        except OSError:
            return None

    # -- binary LGPL tải về (Q21 tải thật) --------------------------------

    def _downloaded_exe(self) -> Path | None:
        """Đường dẫn binary LGPL đã tải về (None nếu chưa tải)."""
        name = "ffmpeg.exe" if sys.platform.startswith("win") else "ffmpeg"
        candidate = self.ffmpeg_dir / name
        return candidate if candidate.exists() else None

    def _verify_downloaded(
        self, exe: str | Path, entry: dict[str, object],
        on_progress: ProgressCallback | None = None,
    ) -> dict[str, object]:
        """Kiểm chứng binary LGPL tải về trước khi dùng.

        Thứ tự: SHA-256 + kích thước theo bảng ghim → chạy
        ``ffmpeg -version`` thật → ``-buildconf`` không có ``--enable-gpl``
        / ``--enable-nonfree`` (``--enable-version3`` được chấp nhận — đó
        là LGPL v3, xem docstring đầu file) → có encoder ``libmp3lame``.
        Binary chỉ chạy sau khi checksum đã khớp (không bao giờ chạy file
        chưa kiểm chứng). Trả dict như :meth:`verify_binary` + ``license``.
        """
        exe = Path(exe)
        platform = _platform_key()
        expected_sha = entry.get("binary_sha256")
        expected_size = entry.get("binary_size_bytes")
        actual, size = sha256_file(exe, on_progress=on_progress)
        ok: bool | None = True
        message = ""
        if expected_sha is not None and actual != expected_sha:
            ok = False
            message = (
                f"Binary FFmpeg tải về {exe.name} ({platform}): SHA-256 "
                f"KHÔNG khớp bảng ghim — đo được {actual}, ghim "
                f"{expected_sha}. Binary có thể hỏng hoặc bị thay thế; "
                "KHÔNG dùng. Hãy xóa file và tải lại."
            )
        elif expected_size is not None and size != int(expected_size):
            ok = False
            message = (
                f"Binary FFmpeg tải về {exe.name} ({platform}): kích thước "
                f"không khớp bảng ghim — đo được {size} byte, ghim "
                f"{expected_size} byte. KHÔNG dùng."
            )
        else:
            # Checksum đã khớp (hoặc platform chưa ghim binary) mới chạy.
            try:
                r = subprocess.run(
                    [str(exe), "-version"], capture_output=True, text=True,
                    timeout=30,
                )
            except (subprocess.SubprocessError, OSError) as exc:
                ok = False
                message = (
                    f"Không chạy được binary FFmpeg tải về {exe.name}: "
                    f"{exc}. Hãy xóa file và tải lại."
                )
                r = None
            if ok is True and r is not None:
                if r.returncode != 0 or "ffmpeg version" not in (r.stdout or ""):
                    ok = False
                    message = (
                        f"Binary FFmpeg tải về {exe.name} chạy "
                        "`ffmpeg -version` thất bại — file có thể không "
                        "phải FFmpeg. KHÔNG dùng."
                    )
            if ok is True:
                try:
                    r2 = subprocess.run(
                        [str(exe), "-buildconf"], capture_output=True,
                        text=True, timeout=30,
                    )
                except (subprocess.SubprocessError, OSError) as exc:
                    ok = False
                    message = (
                        f"Không kiểm tra được giấy phép binary FFmpeg tải "
                        f"về {exe.name}: {exc}. KHÔNG dùng."
                    )
                    r2 = None
                if ok is True and r2 is not None:
                    conf = r2.stdout or ""
                    if "--enable-gpl" in conf or "--enable-nonfree" in conf:
                        ok = False
                        message = (
                            f"Binary FFmpeg tải về {exe.name} KHÔNG phải "
                            "LGPL (có --enable-gpl/--enable-nonfree trong "
                            "-buildconf) — vi phạm Q21, KHÔNG dùng."
                        )
            if ok is True:
                try:
                    r3 = subprocess.run(
                        [str(exe), "-hide_banner", "-encoders"],
                        capture_output=True, text=True, timeout=30,
                    )
                except (subprocess.SubprocessError, OSError) as exc:
                    ok = False
                    message = (
                        f"Không kiểm tra được encoder của binary FFmpeg "
                        f"tải về {exe.name}: {exc}. KHÔNG dùng."
                    )
                    r3 = None
                if ok is True and r3 is not None:
                    if "libmp3lame" not in (r3.stdout or ""):
                        ok = False
                        message = (
                            f"Binary FFmpeg tải về {exe.name} thiếu bộ mã "
                            "hoá MP3 (libmp3lame) — không dùng được cho "
                            "xuất MP3. KHÔNG dùng."
                        )
        if ok is True:
            message = (
                f"Binary FFmpeg LGPL tải về {exe.name} ({platform}): SHA-256 "
                f"khớp bảng ghim ({actual[:16]}…, {size} byte), chạy "
                "`ffmpeg -version` được, giấy phép LGPL (không "
                "--enable-gpl/--enable-nonfree), có libmp3lame."
            )
        result: dict[str, object] = {
            "platform": platform,
            "binary": exe.name,
            "size_bytes": size,
            "sha256": actual,
            "expected_sha256": expected_sha,
            "pinned": expected_sha is not None,
            "ok": ok,
            "license": entry.get("license"),
            "message": message,
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }
        self.last_verification = result
        self._cached_sha256 = actual
        self._cached_size = size
        if self.data_dir is not None:
            self._write_manifest(result)
        return result

    def _write_download_manifest(
        self, entry: dict[str, object], check: dict[str, object]
    ) -> Path | None:
        """Ghi hồ sơ tải vào ``ffmpeg-download.json`` trong ffmpeg_dir."""
        try:
            self.ffmpeg_dir.mkdir(parents=True, exist_ok=True)
            path = self.ffmpeg_dir / "ffmpeg-download.json"
            data = {
                "platform": _platform_key(),
                "source_url": entry.get("url"),
                "release": entry.get("release"),
                "archive": entry.get("archive"),
                "archive_sha256": entry.get("archive_sha256"),
                "archive_size_bytes": entry.get("archive_size_bytes"),
                "binary": check.get("binary"),
                "binary_sha256": check.get("sha256"),
                "binary_size_bytes": check.get("size_bytes"),
                "version": entry.get("version"),
                "license": entry.get("license"),
                "downloaded_at": datetime.now(timezone.utc).isoformat(),
                "verification": check,
            }
            path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            return path
        except OSError:
            return None

    def _http_download(
        self, entry: dict[str, object],
        on_progress: ProgressCallback | None = None,
    ) -> Path:
        """Tải archive FFmpeg (có resume qua HTTP Range).

        Trả đường dẫn archive đầy đủ đã kiểm tra kích thước. Ném
        ``FFmpegError`` với thông báo tiếng Việt khi: URL không nằm trong
        danh sách cho phép, không có mạng, HTTP lỗi, tải dở (giữ file
        ``.part`` để lần sau tải tiếp). Chỉ tải qua HTTPS.
        """
        url = str(entry["url"])
        if not url.startswith(_ALLOWED_DOWNLOAD_PREFIX):
            raise FFmpegError(
                "URL tải FFmpeg không nằm trong danh sách cho phép "
                "(BtbN/FFmpeg-Builds) — từ chối tải để tránh binary lạ."
            )
        self.ffmpeg_dir.mkdir(parents=True, exist_ok=True)
        archive_path = self.ffmpeg_dir / str(entry["archive"])
        part_path = self.ffmpeg_dir / (str(entry["archive"]) + ".part")
        total = int(entry.get("archive_size_bytes") or 0)
        existing = part_path.stat().st_size if part_path.exists() else 0
        if total > 0 and existing > total:
            part_path.unlink(missing_ok=True)
            existing = 0
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "HP-Voice-Studio/1.0 (ffmpeg-download)"},
        )
        if existing > 0:
            req.add_header("Range", f"bytes={existing}-")
        try:
            resp = urllib.request.urlopen(req, timeout=30)
        except urllib.error.HTTPError as exc:
            if exc.code == 416 and total > 0 and existing >= total:
                # Server báo phần đã tải đủ — dùng file .part làm archive.
                os.replace(part_path, archive_path)
                return archive_path
            raise FFmpegError(
                f"Không tải được FFmpeg từ BtbN (HTTP {exc.code}). Hãy kiểm "
                "tra mạng rồi thử lại, hoặc cài FFmpeg hệ thống để xuất MP3 "
                "ngay (WAV vẫn tạo bình thường)."
            ) from exc
        except urllib.error.URLError as exc:
            raise FFmpegError(
                "Không có mạng hoặc không tới được máy chủ tải FFmpeg "
                f"({exc.reason}). Muốn xuất MP3 ngay hãy cài FFmpeg hệ "
                "thống; WAV vẫn tạo bình thường. Khi có mạng, gọi lại "
                "FFmpegManager.download() để tải tiếp."
            ) from exc
        except OSError as exc:
            raise FFmpegError(
                f"Không tải được FFmpeg (lỗi hệ thống/mạng: {exc}). Hãy "
                "kiểm tra mạng rồi thử lại, hoặc cài FFmpeg hệ thống."
            ) from exc
        status = resp.getcode()
        resume = status == 206 and existing > 0
        done = existing if resume else 0
        if total <= 0:
            try:
                length = resp.headers.get("Content-Length")
                total = (int(length) + done) if length else 0
            except (TypeError, ValueError):
                total = 0
        try:
            with resp, part_path.open("ab" if resume else "wb") as out:
                while True:
                    chunk = resp.read(1024 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)
                    done += len(chunk)
                    if on_progress is not None:
                        on_progress(done, total)
        except OSError as exc:
            raise FFmpegError(
                f"Tải FFmpeg bị ngắt giữa chừng (đã tải {done} byte"
                + (f"/{total} byte" if total > 0 else "")
                + f"): {exc}. File dở đã giữ lại — lần sau app tải tiếp "
                "từ chỗ dừng. WAV vẫn tạo bình thường."
            ) from exc
        if total > 0 and done < total:
            raise FFmpegError(
                f"Tải FFmpeg chưa đủ ({done}/{total} byte) — mạng bị ngắt. "
                "File dở đã giữ lại, lần sau app tải tiếp từ chỗ dừng; "
                "hoặc cài FFmpeg hệ thống để xuất MP3 ngay."
            )
        os.replace(part_path, archive_path)
        return archive_path

    def _verify_archive(
        self, archive_path: str | Path, entry: dict[str, object]
    ) -> None:
        """Kiểm SHA-256 + kích thước archive tải về. Lệch → xóa file, ném
        ``FFmpegError`` (không bao giờ giải nén archive chưa kiểm chứng)."""
        archive_path = Path(archive_path)
        actual, size = sha256_file(archive_path)
        expected = str(entry["archive_sha256"])
        expected_size = int(entry.get("archive_size_bytes") or 0)
        if actual != expected or (expected_size > 0 and size != expected_size):
            try:
                archive_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise FFmpegError(
                "File FFmpeg tải về không khớp checksum ghim (đo được "
                f"{actual}, {size} byte; ghim {expected}, {expected_size} "
                "byte) — file có thể hỏng hoặc bị thay thế. Đã xóa file "
                "tải về; hãy thử tải lại hoặc cài FFmpeg hệ thống."
            )

    def _extract_archive_member(
        self, archive_path: str | Path, entry: dict[str, object]
    ) -> Path:
        """Giải nén an toàn CHỈ đúng file binary trong archive.

        Không dùng ``extractall`` — chỉ đọc đúng member đã ghim bằng
        stream (chống path traversal và file lạ trong archive). Ghi ra
        file tạm rồi ``os.replace`` để không để lại binary dở. Trả đường
        dẫn binary.
        """
        archive_path = Path(archive_path)
        member = str(entry["binary_member"])
        parts = Path(member).parts
        if member.startswith(("/", "\\")) or ".." in parts:
            raise FFmpegError(
                "Tên file binary trong bảng ghim không an toàn — từ chối "
                "giải nén."
            )
        dest = self.ffmpeg_dir / str(entry["binary_name"])
        tmp_dest = dest.with_name(dest.name + ".tmp")
        try:
            if str(archive_path).endswith(".zip"):
                with zipfile.ZipFile(archive_path) as zf:
                    if member not in zf.namelist():
                        raise FFmpegError(
                            "Archive FFmpeg tải về thiếu file binary "
                            f"{member} — file có thể khác bản đã ghim. Hãy "
                            "thử tải lại hoặc cài FFmpeg hệ thống."
                        )
                    with zf.open(member) as src, tmp_dest.open("wb") as out:
                        shutil.copyfileobj(src, out, length=1024 * 1024)
            else:
                with tarfile.open(archive_path, "r:xz") as tf:
                    try:
                        info = tf.getmember(member)
                    except KeyError:
                        raise FFmpegError(
                            "Archive FFmpeg tải về thiếu file binary "
                            f"{member} — file có thể khác bản đã ghim. Hãy "
                            "thử tải lại hoặc cài FFmpeg hệ thống."
                        ) from None
                    if not info.isfile():
                        raise FFmpegError(
                            f"Member {member} trong archive không phải file "
                            "thường — từ chối giải nén."
                        )
                    src = tf.extractfile(info)
                    if src is None:
                        raise FFmpegError(
                            f"Không đọc được member {member} trong archive."
                        )
                    with src, tmp_dest.open("wb") as out:
                        shutil.copyfileobj(src, out, length=1024 * 1024)
        except FFmpegError:
            raise
        except (OSError, tarfile.TarError, zipfile.BadZipFile) as exc:
            raise FFmpegError(
                f"Giải nén archive FFmpeg thất bại: {exc}. Hãy thử tải lại "
                "hoặc cài FFmpeg hệ thống."
            ) from exc
        os.replace(tmp_dest, dest)
        if os.name == "posix":
            os.chmod(dest, 0o755)
        return dest

    # -- tìm binary -------------------------------------------------------

    def locate(self, on_progress: ProgressCallback | None = None) -> str | None:
        """Trả về đường dẫn ffmpeg khả thi, hoặc None (kèm status_message).

        Thứ tự: (1) FFmpeg hệ thống; (2) binary LGPL đã tải về thư mục dữ
        liệu (kiểm chứng SHA-256 + chạy thử trước khi dùng — binary hỏng
        hoặc không đạt sẽ bị xóa để lần sau tải lại sạch); (3) binary
        imageio-ffmpeg đi kèm wheel (dự phòng cũ, GPL v3); (4) không có →
        chỉ WAV + báo rõ. ``on_progress(bytes_done, bytes_total)`` được
        gọi trong lúc kiểm chứng SHA-256 binary tải sau (lần đầu); nếu
        binary đã kiểm chứng trong instance này thì gọi một lần
        ``(size, size)`` để báo hoàn tất. FFmpeg hệ thống không qua
        checksum (là bản người dùng tự cài).
        """
        if self._cached:
            if on_progress is not None and self._cached_size is not None:
                on_progress(self._cached_size, self._cached_size)
            return self._cached_path
        self._cached = True
        # 1. FFmpeg hệ thống — ưu tiên.
        system = shutil.which("ffmpeg")
        if system:
            self._cached_path = system
            self.status_message = f"Dùng FFmpeg hệ thống: {system}"
            return system
        # 2. Binary LGPL đã tải về thư mục dữ liệu (Q21 — tải thật).
        downloaded = self._downloaded_exe()
        if downloaded is not None:
            entry = FFMPEG_DOWNLOADS.get(_platform_key(), {})
            check = self._verify_downloaded(
                downloaded, entry, on_progress=on_progress)
            if check["ok"] is True:
                self._cached_path = str(downloaded)
                self.status_message = (
                    "Dùng FFmpeg LGPL v3 đã tải về: "
                    f"{downloaded} — " + str(check["message"])
                )
                return self._cached_path
            # Binary tải về hỏng/không đạt → xóa để lần sau tải lại sạch,
            # rồi thử đường wheel bên dưới (không dùng binary hỏng).
            try:
                downloaded.unlink(missing_ok=True)
            except OSError:
                pass
            self.status_message = str(check["message"])
        # 3. Binary imageio-ffmpeg (đi kèm wheel 0.8.1 — xem docstring đầu file).
        try:
            import imageio_ffmpeg  # type: ignore

            exe = imageio_ffmpeg.get_ffmpeg_exe()
            if exe and Path(exe).exists():
                check = self.verify_binary(exe, on_progress=on_progress)
                if check["ok"] is False:
                    self._cached_path = None
                    self.status_message = str(check["message"])
                    return None
                self._cached_path = str(exe)
                self.status_message = (
                    "Dùng FFmpeg đi kèm wheel imageio-ffmpeg (máy dev): "
                    f"{exe} — binary GPL v3, ~165 MB, không đóng gói kèm bộ cài (Q21). "
                    "[Đính chính 19/11/2026: binary này đi kèm wheel lúc pip install; "
                    "get_ffmpeg_exe() chỉ tìm file có sẵn, KHÔNG tải lúc chạy.] "
                    + str(check["message"])
                )
                return self._cached_path
        except Exception as exc:  # noqa: BLE001 — mọi lỗi tải đều thành "không có"
            self._cached_path = None
            self.status_message = (
                "Không tải được FFmpeg (imageio-ffmpeg lỗi: "
                f"{exc}). {NO_FFMPEG_MESSAGE}"
            )
            return None
        self._cached_path = None
        self.status_message = NO_FFMPEG_MESSAGE
        return None

    def download(self, on_progress: ProgressCallback | None = None) -> str | None:
        """Tải FFmpeg LGPL về lần đầu chạy (Q21 — tải thật).

        Trả đường dẫn ffmpeg hoặc None. Luồng: đã có FFmpeg (hệ thống /
        đã tải / wheel) → trả về ngay, không tải lại; chưa có → tải
        archive BtbN đã ghim theo platform (có resume + tiến trình),
        kiểm SHA-256 archive, giải nén an toàn chỉ file binary, kiểm
        chứng binary (SHA-256 + ``ffmpeg -version`` + ``-buildconf``
        LGPL + ``libmp3lame``) rồi mới dùng. Mất mạng → None + thông
        báo tiếng Việt rõ ràng, hướng dẫn cài FFmpeg hệ thống; app vẫn
        xuất WAV được, không crash. Platform chưa có bản ghim (VD macOS,
        Windows ARM) → None + báo rõ.
        """
        self._cached = False
        self._cached_path = None
        existing = self.locate()
        if existing is not None:
            return existing
        entry = FFMPEG_DOWNLOADS.get(_platform_key())
        if entry is None:
            self.status_message = (
                f"Platform {_platform_key()} chưa có bản FFmpeg tải sau "
                "được ghim (hiện chỉ có linux-x86_64 và windows-x86_64). "
                + NO_FFMPEG_MESSAGE
            )
            return None
        try:
            archive_path = self._http_download(entry, on_progress=on_progress)
            self._verify_archive(archive_path, entry)
            exe = self._extract_archive_member(archive_path, entry)
            check = self._verify_downloaded(exe, entry)
            if check["ok"] is not True:
                try:
                    exe.unlink(missing_ok=True)
                except OSError:
                    pass
                self.status_message = str(check["message"])
                return None
            self._write_download_manifest(entry, check)
            self._cached = True
            self._cached_path = str(exe)
            self._cached_size = check.get("size_bytes")
            if isinstance(self._cached_size, int):
                self._cached_sha256 = str(check.get("sha256"))
            self.status_message = (
                "Đã tải FFmpeg LGPL v3 về lần đầu chạy: "
                f"{exe} — " + str(check["message"])
            )
            return str(exe)
        except FFmpegError as exc:
            self.status_message = str(exc)
            return None

    def available(self) -> bool:
        """True nếu có FFmpeg để mã hoá MP3."""
        return self.locate() is not None

    def encode_mp3(
        self, input_wav: str | Path, output_mp3: str | Path, bitrate: str = "192k"
    ) -> bool:
        """Mã hoá WAV → MP3 bằng FFmpeg. Trả False (không ném lỗi) khi không
        có FFmpeg hoặc ffmpeg chạy lỗi — caller báo rõ và giữ lại WAV."""
        exe = self.locate()
        if exe is None:
            return False
        try:
            r = subprocess.run(
                [exe, "-y", "-v", "error", "-i", str(input_wav),
                 "-codec:a", "libmp3lame", "-b:a", bitrate, str(output_mp3)],
                capture_output=True, text=True, timeout=600,
            )
        except (subprocess.SubprocessError, OSError):
            return False
        if r.returncode != 0 or not Path(output_mp3).exists():
            return False
        return True

    def run_atempo(
        self, input_wav: str | Path, output_wav: str | Path, rate: float
    ) -> bool:
        """Đổi tốc độ giữ cao độ bằng filter ``atempo`` của FFmpeg
        (dùng cho TK1.9 so sánh với librosa; atempo chỉ nhận 0,5–100 nên
        0,75×/1,5× đều trong khoảng). Trả False khi không có FFmpeg/lỗi."""
        exe = self.locate()
        if exe is None:
            return False
        try:
            r = subprocess.run(
                [exe, "-y", "-v", "error", "-i", str(input_wav),
                 "-filter:a", f"atempo={rate}", str(output_wav)],
                capture_output=True, text=True, timeout=600,
            )
        except (subprocess.SubprocessError, OSError):
            return False
        return r.returncode == 0 and Path(output_wav).exists()

    def decode_to_wav(
        self, src: str | Path, dst: str | Path, sample_rate: int = 48000
    ) -> Path:
        """Giải mã MP3/M4A/AAC → WAV 48 kHz mono (cho clip clone giọng).

        Ném ``FFmpegError`` khi không có FFmpeg hoặc ffmpeg chạy lỗi — caller
        báo rõ cho người dùng (không crash). File đích ghi đè nếu đã có.
        """
        exe = self.locate()
        if exe is None:
            raise FFmpegError(
                "Không giải mã được MP3/M4A vì chưa có FFmpeg. " + NO_FFMPEG_MESSAGE
            )
        dst = Path(dst)
        try:
            r = subprocess.run(
                [exe, "-y", "-v", "error", "-i", str(src),
                 "-ar", str(sample_rate), "-ac", "1", str(dst)],
                capture_output=True, text=True, timeout=120,
            )
        except (subprocess.SubprocessError, OSError) as exc:
            raise FFmpegError(f"FFmpeg giải mã thất bại: {exc}") from exc
        if r.returncode != 0 or not dst.exists():
            tail = (r.stderr or "").strip().splitlines()[-1:]
            raise FFmpegError(
                "FFmpeg không giải mã được file này"
                + (f": {tail[0]}" if tail else ".")
                + " Hãy gửi file WAV/MP3/M4A có tiếng nói rõ."
            )
        return dst
