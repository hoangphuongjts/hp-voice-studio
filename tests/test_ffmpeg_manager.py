"""Test FFmpegManager tối thiểu — TK1.6/TK4.9 (Q21: FFmpeg tách khỏi bộ cài,
tải cài sau; fallback FFmpeg hệ thống; không có → chỉ WAV + báo rõ, không crash).

Chạy: .venv/bin/python -m pytest tests/test_ffmpeg_manager.py -v
"""
import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from hpvoice.audio import ffmpeg_manager as fm_mod
from hpvoice.audio.ffmpeg_manager import FFmpegManager, sha256_file

REPO = Path(__file__).resolve().parent.parent
SAMPLE_WAV = REPO / "evidence" / "t1-first-wav" / "t1-first-wav-hai-dang.wav"


def _imageio_exe() -> Path | None:
    """Binary imageio-ffmpeg trên máy này (None nếu wheel thiếu binary)."""
    try:
        import imageio_ffmpeg  # type: ignore

        exe = Path(imageio_ffmpeg.get_ffmpeg_exe())
        return exe if exe.exists() else None
    except Exception:  # noqa: BLE001
        return None


def _an_ffmpeg_he_thong(monkeypatch):
    """Giả lập máy không có FFmpeg hệ thống để test đường binary tải sau."""
    monkeypatch.setattr("shutil.which", lambda name: None)


def test_tim_thay_ffmpeg_he_thong_hoac_imageio():
    fm = FFmpegManager()
    path = fm.locate()
    # Máy này có ffmpeg hệ thống và/hoặc binary imageio-ffmpeg → phải tìm thấy
    assert path is not None, fm.status_message
    assert Path(path).exists()


def test_mp3_that_qua_ffprobe(tmp_path):
    """T2.10: MP3 thật, ffprobe đọc được (dùng WAV mẫu T1 làm nguồn)."""
    assert SAMPLE_WAV.exists(), "thiếu file WAV mẫu T1"
    fm = FFmpegManager()
    assert fm.available(), fm.status_message
    out = tmp_path / "out.mp3"
    ok = fm.encode_mp3(SAMPLE_WAV, out)
    assert ok is True
    assert out.exists() and out.stat().st_size > 1000
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_name,sample_rate",
         "-of", "csv=p=0", str(out)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0
    assert "mp3" in r.stdout


def test_thieu_ffmpeg_chi_wav_khong_crash(tmp_path, monkeypatch):
    """T2.10: không có FFmpeg → chỉ WAV + báo rõ, không crash."""
    fm = FFmpegManager()
    monkeypatch.setattr(fm, "locate", lambda: None)
    monkeypatch.setattr(fm, "available", lambda: False)
    from hpvoice.audio.ffmpeg_manager import NO_FFMPEG_MESSAGE

    fm.status_message = NO_FFMPEG_MESSAGE  # mô phỏng trạng thái "không có FFmpeg"
    assert fm.available() is False
    assert "WAV" in fm.status_message or "wav" in fm.status_message.lower()
    assert fm.encode_mp3(SAMPLE_WAV, tmp_path / "x.mp3") is False
    assert not (tmp_path / "x.mp3").exists()


def test_ffmpeg_he_thong_duoc_uu_tien(monkeypatch):
    """Ưu tiên FFmpeg hệ thống (shutil.which) trước binary tải sau."""
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/ffmpeg" if name == "ffmpeg" else None)
    fm = FFmpegManager()
    assert fm.locate() == "/usr/bin/ffmpeg"


# --- TK4.9: checksum SHA-256 + progress callback ---------------------------


def test_sha256_file_khop_hashlib(tmp_path):
    """sha256_file() tính đúng SHA-256 (đối chiếu hashlib trực tiếp)."""
    f = tmp_path / "a.bin"
    f.write_bytes(b"hp-voice-studio" * 1000)
    digest, size = sha256_file(f)
    assert size == f.stat().st_size
    assert digest == hashlib.sha256(f.read_bytes()).hexdigest()


def test_checksum_linux_ghim_khop_binary_that(monkeypatch):
    """TK4.9: SHA-256 binary imageio trên VM này khớp bảng ghim linux-x86_64."""
    exe = _imageio_exe()
    if exe is None:
        pytest.skip("wheel imageio-ffmpeg trên máy này thiếu binary")
    if fm_mod._platform_key() != "linux-x86_64":
        pytest.skip("checksum ghim chỉ có cho linux-x86_64")
    fm = FFmpegManager()
    result = fm.verify_binary(exe)
    assert result["ok"] is True, result["message"]
    assert result["sha256"] == fm_mod.PINNED_FFMPEG_SHA256["linux-x86_64"]["sha256"]
    assert result["size_bytes"] == 172692552


def test_progress_callback_duoc_goi_khi_kiem_chung(monkeypatch):
    """TK4.9: on_progress nhận (bytes_done, bytes_total), tăng đơn điệu,
    lần cuối done == total == kích thước binary."""
    exe = _imageio_exe()
    if exe is None:
        pytest.skip("wheel imageio-ffmpeg trên máy này thiếu binary")
    calls: list[tuple[int, int]] = []
    fm = FFmpegManager()
    fm.verify_binary(exe, on_progress=lambda done, total: calls.append((done, total)))
    assert calls, "không có lần gọi on_progress nào"
    assert calls[-1][0] == calls[-1][1] == exe.stat().st_size
    assert all(a <= b for a, b in zip([c[0] for c in calls], [c[0] for c in calls][1:]))


def test_locate_goi_progress_va_kiem_checksum(monkeypatch, tmp_path):
    """TK4.9: locate(on_progress=...) qua đường binary tải sau vẫn kiểm
    checksum + báo tiến trình, và ghi manifest vào data_dir."""
    exe = _imageio_exe()
    if exe is None:
        pytest.skip("wheel imageio-ffmpeg trên máy này thiếu binary")
    if fm_mod._platform_key() != "linux-x86_64":
        pytest.skip("checksum ghim chỉ có cho linux-x86_64")
    _an_ffmpeg_he_thong(monkeypatch)
    calls: list[tuple[int, int]] = []
    fm = FFmpegManager(data_dir=tmp_path)
    path = fm.locate(on_progress=lambda done, total: calls.append((done, total)))
    assert path == str(exe)
    assert calls and calls[-1][0] == calls[-1][1] > 0
    assert fm.last_verification is not None and fm.last_verification["ok"] is True
    manifest = json.loads((tmp_path / "ffmpeg-manifest.json").read_text(encoding="utf-8"))
    assert manifest["sha256"] == fm_mod.PINNED_FFMPEG_SHA256["linux-x86_64"]["sha256"]
    assert manifest["pinned"] is True


def test_checksum_sai_bi_tu_choi(monkeypatch, tmp_path):
    """TK4.9: binary lệch checksum ghim → locate() trả None + báo rõ lý do,
    không dùng binary hỏng/khác bản."""
    fake = tmp_path / "ffmpeg-fake"
    fake.write_bytes(b"khong-phai-ffmpeg-that")
    _an_ffmpeg_he_thong(monkeypatch)
    monkeypatch.setattr(
        "imageio_ffmpeg.get_ffmpeg_exe", lambda: str(fake)
    )
    fm = FFmpegManager(data_dir=tmp_path)
    assert fm.locate() is None
    assert "SHA-256" in fm.status_message and "KHÔNG khớp" in fm.status_message


def test_platform_chua_ghim_ghi_manifest_khong_lang_le_bo_qua(monkeypatch, tmp_path):
    """TK4.9: platform chưa có checksum ghim → vẫn dùng binary nhưng ghi rõ
    'chưa ghim' + ghi SHA-256 đo được vào manifest, không lặng lẽ bỏ qua."""
    fake = tmp_path / "ffmpeg-fake2"
    fake.write_bytes(b"ffmpeg-gia-lap-cho-platform-chua-ghim")
    _an_ffmpeg_he_thong(monkeypatch)
    monkeypatch.setattr("imageio_ffmpeg.get_ffmpeg_exe", lambda: str(fake))
    monkeypatch.setattr(fm_mod, "PINNED_FFMPEG_SHA256", {})
    fm = FFmpegManager(data_dir=tmp_path)
    assert fm.locate() == str(fake)
    assert fm.last_verification is not None
    assert fm.last_verification["ok"] is None  # chưa kết luận an toàn
    assert "chưa có checksum ghim" in str(fm.last_verification["message"])
    manifest = json.loads((tmp_path / "ffmpeg-manifest.json").read_text(encoding="utf-8"))
    assert manifest["sha256"] == hashlib.sha256(fake.read_bytes()).hexdigest()
    assert manifest["pinned"] is False


def test_download_tra_ve_binary_va_bao_tien_trinh(monkeypatch):
    """TK4.9: download(on_progress=...) trả đường dẫn binary + báo tiến trình
    (trên VM này FFmpeg hệ thống có sẵn nên download trả về FFmpeg hệ thống)."""
    calls: list[tuple[int, int]] = []
    fm = FFmpegManager()
    path = fm.download(on_progress=lambda done, total: calls.append((done, total)))
    assert path is not None and Path(path).exists()


# --- Q21 tải thật (BtbN LGPL) — test mock, không cần mạng ------------------

_FAKE_FFMPEG_SCRIPT = """#!/bin/sh
if [ "$1" = "-version" ]; then
  echo "ffmpeg version n9.0.2-57-gd838f9f9ae-20261118 Copyright (c) 2000-2026 the FFmpeg developers"
  echo "configuration: --prefix=/ffbuild --enable-version3 --enable-libmp3lame"
  exit 0
fi
if [ "$1" = "-buildconf" ]; then
  echo "configuration: --prefix=/ffbuild --enable-version3 --enable-libmp3lame"
  exit 0
fi
if [ "$1" = "-hide_banner" ] && [ "$2" = "-encoders" ]; then
  echo " A....D libmp3lame           libmp3lame MP3 (MPEG audio layer 3) (codec mp3)"
  exit 0
fi
exit 0
"""

_FAKE_FFMPEG_SCRIPT_GPL = _FAKE_FFMPEG_SCRIPT.replace(
    "--enable-version3 --enable-libmp3lame",
    "--enable-gpl --enable-version3 --enable-libmp3lame",
)

_BTBN_PREFIX = "https://github.com/BtbN/FFmpeg-Builds/releases/download/"


def _make_fake_archive(tmp_path, member, script):
    """Tạo tar.xz giả chứa 1 script ffmpeg giả. Trả (archive_path, script_bytes)."""
    import tarfile

    script_bytes = script.encode("utf-8")
    src = tmp_path / "src" / "ffmpeg"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_bytes(script_bytes)
    archive = tmp_path / "fake-ffmpeg.tar.xz"
    with tarfile.open(archive, "w:xz") as tf:
        tf.add(src, arcname=member)
    return archive, script_bytes


def _fake_entry(archive, member, script_bytes, url=None):
    data = archive.read_bytes()
    return {
        "release": "test-1",
        "url": url or (_BTBN_PREFIX + "test/fake.tar.xz"),
        "archive": archive.name,
        "archive_sha256": hashlib.sha256(data).hexdigest(),
        "archive_size_bytes": len(data),
        "binary_member": member,
        "binary_name": "ffmpeg",
        "binary_sha256": hashlib.sha256(script_bytes).hexdigest(),
        "binary_size_bytes": len(script_bytes),
        "version": "test",
        "license": "LGPL v3 (gia lap)",
        "source": "test",
    }


class _FakeResp:
    """Response giả cho urllib (hỗ trợ Range + Content-Length)."""

    def __init__(self, data: bytes, status: int = 200):
        self._data = data
        self._pos = 0
        self.status = status
        self.headers = {"Content-Length": str(len(data))}

    def getcode(self):
        return self.status

    def read(self, n=-1):
        if self._pos >= len(self._data):
            return b""
        chunk = self._data[self._pos:self._pos + n] if n > 0 else self._data[self._pos:]
        self._pos += len(chunk)
        return chunk

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _fake_urlopen_factory(data: bytes, support_range=True):
    def fake_urlopen(req, timeout=None):
        range_hdr = req.get_header("Range")
        if support_range and range_hdr:
            start = int(range_hdr.split("=")[1].split("-")[0])
            return _FakeResp(data[start:], status=206)
        return _FakeResp(data, status=200)

    return fake_urlopen


def _khong_co_ffmpeg_nao(monkeypatch):
    """Giả lập máy không có FFmpeg hệ thống lẫn wheel imageio."""
    import urllib.error

    monkeypatch.setattr("shutil.which", lambda name: None)
    monkeypatch.setattr(
        "imageio_ffmpeg.get_ffmpeg_exe",
        lambda: (_ for _ in ()).throw(ImportError("wheel bi an di cho test")),
    )


def test_download_tai_that_tu_archive_gia_co_resume(monkeypatch, tmp_path):
    """Q21 tải thật (mock mạng): download() tải archive, resume từ .part,
    kiểm checksum, giải nén đúng binary, kiểm -version/-buildconf/LGPL/
    libmp3lame, ghi ffmpeg-download.json, trả đường dẫn binary chạy được."""
    import urllib.request

    member = "top-1.0/bin/ffmpeg"
    archive, script_bytes = _make_fake_archive(
        tmp_path, member, _FAKE_FFMPEG_SCRIPT)
    entry = _fake_entry(archive, member, script_bytes)
    monkeypatch.setattr(fm_mod, "FFMPEG_DOWNLOADS", {"linux-x86_64": entry})
    _khong_co_ffmpeg_nao(monkeypatch)
    data = archive.read_bytes()
    # Giả lập lần tải trước dở dang: .part đã có nửa đầu archive.
    fm = FFmpegManager(data_dir=tmp_path)
    part = fm.ffmpeg_dir / (archive.name + ".part")
    fm.ffmpeg_dir.mkdir(parents=True, exist_ok=True)
    part.write_bytes(data[: len(data) // 2])
    monkeypatch.setattr(
        urllib.request, "urlopen", _fake_urlopen_factory(data))
    calls: list[tuple[int, int]] = []
    path = fm.download(on_progress=lambda d, t: calls.append((d, t)))
    assert path is not None, fm.status_message
    assert Path(path) == fm.ffmpeg_dir / "ffmpeg"
    assert Path(path).exists()
    assert calls and calls[-1][0] == calls[-1][1] == len(data)
    assert all(a <= b for a, b in zip(
        [c[0] for c in calls], [c[0] for c in calls][1:]))
    assert not part.exists(), "file .part phải được đổi tên thành archive"
    manifest = json.loads(
        (fm.ffmpeg_dir / "ffmpeg-download.json").read_text(encoding="utf-8"))
    assert "LGPL" in str(manifest["license"])
    assert manifest["archive_sha256"] == entry["archive_sha256"]
    assert manifest["verification"]["ok"] is True
    # Binary tải về chạy được thật (script giả).
    r = subprocess.run([path, "-version"], capture_output=True, text=True)
    assert r.returncode == 0 and "ffmpeg version" in r.stdout
    # Lần locate() sau dùng lại binary đã tải, không tải lại.
    fm2 = FFmpegManager(data_dir=tmp_path)
    assert fm2.locate() == str(fm.ffmpeg_dir / "ffmpeg")


def test_download_checksum_archive_sai_bi_tu_choi(monkeypatch, tmp_path):
    """Q21: archive tải về lệch checksum ghim → download() trả None, xóa
    archive, báo rõ SHA-256 — không giải nén file chưa kiểm chứng."""
    import urllib.request

    member = "top-1.0/bin/ffmpeg"
    archive, script_bytes = _make_fake_archive(
        tmp_path, member, _FAKE_FFMPEG_SCRIPT)
    entry = _fake_entry(archive, member, script_bytes)
    monkeypatch.setattr(fm_mod, "FFMPEG_DOWNLOADS", {"linux-x86_64": entry})
    _khong_co_ffmpeg_nao(monkeypatch)
    # Dữ liệu bị tráo nhưng ĐỦ kích thước ghim → tải "đủ" rồi mới lòi
    # checksum sai ở bước kiểm chứng (đúng lỗi cần test).
    data = bytearray(archive.read_bytes())
    data[100] ^= 0xFF
    data[200] ^= 0xFF
    monkeypatch.setattr(
        urllib.request, "urlopen",
        _fake_urlopen_factory(bytes(data)))
    fm = FFmpegManager(data_dir=tmp_path)
    assert fm.download() is None
    assert "SHA-256" in fm.status_message or "checksum" in fm.status_message
    assert not (fm.ffmpeg_dir / archive.name).exists()
    assert fm._downloaded_exe() is None


def test_download_binary_gpl_bi_tu_choi(monkeypatch, tmp_path):
    """Q21: binary tải về có --enable-gpl trong -buildconf → bị từ chối
    (vi phạm Q21), file bị xóa, download() trả None."""
    import urllib.request

    member = "top-1.0/bin/ffmpeg"
    archive, script_bytes = _make_fake_archive(
        tmp_path, member, _FAKE_FFMPEG_SCRIPT_GPL)
    entry = _fake_entry(archive, member, script_bytes)
    monkeypatch.setattr(fm_mod, "FFMPEG_DOWNLOADS", {"linux-x86_64": entry})
    _khong_co_ffmpeg_nao(monkeypatch)
    monkeypatch.setattr(
        urllib.request, "urlopen",
        _fake_urlopen_factory(archive.read_bytes()))
    fm = FFmpegManager(data_dir=tmp_path)
    assert fm.download() is None
    assert "LGPL" in fm.status_message or "--enable-gpl" in fm.status_message
    assert fm._downloaded_exe() is None


def test_download_khong_mang_bao_tieng_viet_khong_crash(monkeypatch, tmp_path):
    """Q21: không có mạng → download() trả None + thông báo tiếng Việt rõ
    (mạng + hướng dẫn cài FFmpeg hệ thống), không ném lỗi, không crash."""
    import urllib.error
    import urllib.request

    member = "top-1.0/bin/ffmpeg"
    archive, script_bytes = _make_fake_archive(
        tmp_path, member, _FAKE_FFMPEG_SCRIPT)
    entry = _fake_entry(archive, member, script_bytes)
    monkeypatch.setattr(fm_mod, "FFMPEG_DOWNLOADS", {"linux-x86_64": entry})
    _khong_co_ffmpeg_nao(monkeypatch)

    def _no_network(req, timeout=None):
        raise urllib.error.URLError("khong co mang (gia lap)")

    monkeypatch.setattr(urllib.request, "urlopen", _no_network)
    fm = FFmpegManager(data_dir=tmp_path)
    assert fm.download() is None
    assert "mạng" in fm.status_message
    assert "FFmpeg hệ thống" in fm.status_message
    assert "WAV" in fm.status_message


def test_download_url_ngoai_danh_sach_bi_tu_choi(monkeypatch, tmp_path):
    """Q21: URL tải không nằm trong danh sách BtbN đã ghim → từ chối ngay,
    không gửi request mạng nào."""
    import urllib.request

    from hpvoice.audio.ffmpeg_manager import FFmpegError

    member = "top-1.0/bin/ffmpeg"
    archive, script_bytes = _make_fake_archive(
        tmp_path, member, _FAKE_FFMPEG_SCRIPT)
    entry = _fake_entry(
        archive, member, script_bytes,
        url="https://evil.example.com/ffmpeg.tar.xz")
    fm = FFmpegManager(data_dir=tmp_path)
    calls = {"n": 0}

    def _counting_urlopen(req, timeout=None):
        calls["n"] += 1
        return _FakeResp(b"")

    monkeypatch.setattr(urllib.request, "urlopen", _counting_urlopen)
    with pytest.raises(FFmpegError):
        fm._http_download(entry)
    assert calls["n"] == 0, "không được gửi request tới URL lạ"


def test_download_platform_chua_ghim_bao_ro(monkeypatch, tmp_path):
    """Q21: platform chưa có bản tải sau ghim → download() trả None + báo
    rõ platform, không tải bừa."""
    monkeypatch.setattr(fm_mod, "FFMPEG_DOWNLOADS", {})
    _khong_co_ffmpeg_nao(monkeypatch)
    fm = FFmpegManager(data_dir=tmp_path)
    assert fm.download() is None
    assert "chưa có bản FFmpeg tải sau" in fm.status_message


def test_extract_tu_choi_archive_thieu_binary(monkeypatch, tmp_path):
    """Q21: archive không chứa đúng member binary đã ghim → từ chối giải
    nén (không extractall, không lấy file lạ)."""
    import tarfile

    from hpvoice.audio.ffmpeg_manager import FFmpegError

    other = tmp_path / "other.txt"
    other.write_text("khong phai ffmpeg", encoding="utf-8")
    archive = tmp_path / "thieu.tar.xz"
    with tarfile.open(archive, "w:xz") as tf:
        tf.add(other, arcname="top-1.0/README.txt")
    entry = {
        "archive": archive.name,
        "binary_member": "top-1.0/bin/ffmpeg",
        "binary_name": "ffmpeg",
    }
    fm = FFmpegManager(data_dir=tmp_path)
    with pytest.raises(FFmpegError):
        fm._extract_archive_member(archive, entry)
    assert fm._downloaded_exe() is None


def test_locate_uu_tien_binary_da_tai_truoc_wheel(monkeypatch, tmp_path):
    """Q21: locate() ưu tiên binary LGPL đã tải về trước binary wheel
    imageio-ffmpeg (GPL)."""
    import os

    member = "top-1.0/bin/ffmpeg"
    archive, script_bytes = _make_fake_archive(
        tmp_path, member, _FAKE_FFMPEG_SCRIPT)
    entry = _fake_entry(archive, member, script_bytes)
    monkeypatch.setattr(fm_mod, "FFMPEG_DOWNLOADS", {"linux-x86_64": entry})
    _an_ffmpeg_he_thong(monkeypatch)
    wheel_fake = tmp_path / "ffmpeg-wheel-fake"
    wheel_fake.write_bytes(b"wheel-binary")
    monkeypatch.setattr(
        "imageio_ffmpeg.get_ffmpeg_exe", lambda: str(wheel_fake))
    fm = FFmpegManager(data_dir=tmp_path)
    fm.ffmpeg_dir.mkdir(parents=True, exist_ok=True)
    downloaded = fm.ffmpeg_dir / "ffmpeg"
    downloaded.write_bytes(script_bytes)
    os.chmod(downloaded, 0o755)
    assert fm.locate() == str(downloaded)
    assert "LGPL" in fm.status_message


def test_locate_binary_da_tai_hong_bi_xoa_fallback_wheel(monkeypatch, tmp_path):
    """Q21: binary đã tải hỏng checksum → locate() xóa nó, fallback sang
    wheel hợp lệ, không dùng binary hỏng."""
    import os

    member = "top-1.0/bin/ffmpeg"
    archive, script_bytes = _make_fake_archive(
        tmp_path, member, _FAKE_FFMPEG_SCRIPT)
    entry = _fake_entry(archive, member, script_bytes)
    monkeypatch.setattr(fm_mod, "FFMPEG_DOWNLOADS", {"linux-x86_64": entry})
    _an_ffmpeg_he_thong(monkeypatch)
    # Wheel hợp lệ: ghim checksum của chính file giả này.
    wheel = tmp_path / "ffmpeg-wheel-ok"
    wheel.write_bytes(b"wheel-hop-le")
    monkeypatch.setattr(
        "imageio_ffmpeg.get_ffmpeg_exe", lambda: str(wheel))
    monkeypatch.setattr(fm_mod, "PINNED_FFMPEG_SHA256", {
        "linux-x86_64": {
            "sha256": hashlib.sha256(b"wheel-hop-le").hexdigest(),
        },
    })
    fm = FFmpegManager(data_dir=tmp_path)
    fm.ffmpeg_dir.mkdir(parents=True, exist_ok=True)
    downloaded = fm.ffmpeg_dir / "ffmpeg"
    downloaded.write_bytes(b"binary-hong-khac-checksum")
    os.chmod(downloaded, 0o755)
    assert fm.locate() == str(wheel)
    assert not downloaded.exists(), "binary hỏng phải bị xóa"

