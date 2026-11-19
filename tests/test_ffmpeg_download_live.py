"""Test TẢI THẬT FFmpeg LGPL từ BtbN — chỉ chạy khi HP_LIVE_DOWNLOAD=1.

Lý do gate bằng biến môi trường: tải thật ~137 MB (Linux) mỗi lần chạy
suite sẽ làm chậm toàn bộ test suite; test này chỉ chạy có chủ đích để
lấy bằng chứng (xem evidence/ffmpeg-download/).

Chạy: HP_LIVE_DOWNLOAD=1 .venv/bin/python -m pytest tests/test_ffmpeg_download_live.py -v
"""
import json
import os
import subprocess
from pathlib import Path

import pytest

from hpvoice.audio.ffmpeg_manager import FFMPEG_DOWNLOADS, FFmpegManager

REPO = Path(__file__).resolve().parent.parent
SAMPLE_WAV = REPO / "evidence" / "t1-first-wav" / "t1-first-wav-hai-dang.wav"

pytestmark = pytest.mark.skipif(
    os.environ.get("HP_LIVE_DOWNLOAD") != "1",
    reason="tải thật ~137 MB — chỉ chạy khi HP_LIVE_DOWNLOAD=1",
)


def _khong_co_ffmpeg_nao(monkeypatch):
    """Giả lập máy sạch: không FFmpeg hệ thống, không wheel imageio."""
    monkeypatch.setattr("shutil.which", lambda name: None)
    monkeypatch.setattr(
        "imageio_ffmpeg.get_ffmpeg_exe",
        lambda: (_ for _ in ()).throw(ImportError("wheel bi an di cho test")),
    )


def test_download_that_btbn_linux_lgpl_va_mp3_that(monkeypatch, tmp_path):
    """Q21 tải thật: trên máy sạch, download() tải archive BtbN LGPL thật,
    kiểm checksum + -version + -buildconf (LGPL) + libmp3lame, rồi xuất
    MP3 thật từ WAV mẫu T1 bằng chính binary vừa tải."""
    assert SAMPLE_WAV.exists(), "thiếu file WAV mẫu T1"
    _khong_co_ffmpeg_nao(monkeypatch)
    fm = FFmpegManager(data_dir=tmp_path)
    calls: list[tuple[int, int]] = []
    path = fm.download(on_progress=lambda d, t: calls.append((d, t)))
    assert path is not None, fm.status_message
    assert Path(path) == fm.ffmpeg_dir / "ffmpeg"
    assert Path(path).exists()
    # Tiến trình tải: có gọi callback, lần cuối done == total == cỡ archive ghim.
    assert calls, "download thật phải báo tiến trình"
    assert calls[-1][0] == calls[-1][1] == FFMPEG_DOWNLOADS["linux-x86_64"]["archive_size_bytes"]
    assert all(a <= b for a, b in zip(
        [c[0] for c in calls], [c[0] for c in calls][1:]))
    # Hồ sơ tải ghi đủ nguồn + giấy phép LGPL + checksum.
    manifest = json.loads(
        (fm.ffmpeg_dir / "ffmpeg-download.json").read_text(encoding="utf-8"))
    assert "BtbN" in str(manifest["source_url"])
    assert "LGPL" in str(manifest["license"])
    assert manifest["archive_sha256"] == FFMPEG_DOWNLOADS["linux-x86_64"]["archive_sha256"]
    assert manifest["verification"]["ok"] is True
    # ffmpeg -version thật bằng binary vừa tải.
    r = subprocess.run([path, "-version"], capture_output=True, text=True)
    assert r.returncode == 0
    assert "ffmpeg version n9.0.2" in r.stdout
    # MP3 thật bằng binary vừa tải (ffprobe đọc được).
    out = tmp_path / "live.mp3"
    assert fm.encode_mp3(SAMPLE_WAV, out) is True
    assert out.exists() and out.stat().st_size > 1000
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_name,sample_rate",
         "-of", "csv=p=0", str(out)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0
    assert "mp3" in r.stdout
