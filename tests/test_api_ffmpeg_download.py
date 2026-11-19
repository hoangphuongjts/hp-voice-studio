"""Test endpoint FFmpeg — GET /api/ffmpeg/status, POST /api/ffmpeg/download,
GET /api/ffmpeg/download (nối tiếp Q21).

Không tải mạng thật: thay ``app.state.ffmpeg`` bằng stub (locate/download
giả lập). Tải thật đã có test riêng, gate bằng HP_LIVE_DOWNLOAD=1
(tests/test_ffmpeg_download_live.py).
"""
import time


class _StubFFmpeg:
    """FFmpegManager giả: locate/download theo kịch bản test."""

    def __init__(self, tmp_path, locate_path=None, download_result="ok",
                 download_error="Không có mạng (giả lập).", step_sleep=0.1):
        self.ffmpeg_dir = tmp_path / "ffmpeg"
        self._locate_path = locate_path
        self._download_result = download_result  # "ok" | "fail"
        self._download_error = download_error
        self._step_sleep = step_sleep
        self.status_message = "Chưa tìm FFmpeg."
        self.locate_calls = 0
        self.download_calls = 0
        self.downloaded_path = str(self.ffmpeg_dir / "ffmpeg")
        self._downloaded = False

    def locate(self):
        self.locate_calls += 1
        if self._downloaded:
            self.status_message = f"Dùng FFmpeg LGPL v3 đã tải về: {self.downloaded_path}"
            return self.downloaded_path
        if self._locate_path:
            self.status_message = f"Dùng FFmpeg: {self._locate_path}"
            return self._locate_path
        self.status_message = "Không tìm thấy FFmpeg trên máy."
        return None

    def download(self, on_progress=None):
        """Giả lập tải: báo tiến trình 3 lần (mỗi lần nghỉ 0,1 s để test
        bắt gặp trạng thái downloading), rồi trả path hoặc None."""
        self.download_calls += 1
        total = 1000
        for done in (300, 700, 1000):
            if on_progress is not None:
                on_progress(done, total)
            time.sleep(self._step_sleep)
        if self._download_result == "ok":
            self._downloaded = True
            self.status_message = "Đã tải FFmpeg LGPL v3 về lần đầu chạy."
            return self.downloaded_path
        self.status_message = self._download_error
        return None


def _poll_download(client, timeout=10.0):
    """Poll GET /api/ffmpeg/download tới khi done/error (hoặc hết giờ)."""
    deadline = time.time() + timeout
    last = {}
    while time.time() < deadline:
        resp = client.get("/api/ffmpeg/download")
        assert resp.status_code == 200, resp.text
        last = resp.json()
        if last.get("status") in ("done", "error"):
            return last
        time.sleep(0.05)
    raise AssertionError(f"Tải không xong sau {timeout}s, trạng thái cuối: {last}")


def _use_stub(app, tmp_path, **kw):
    stub = _StubFFmpeg(tmp_path, **kw)
    app.state.ffmpeg = stub
    return stub


def test_status_chua_co_ffmpeg(app_client, tmp_path):
    """Chưa có FFmpeg: available False, kind none, download idle."""
    client, app, engine, _ = app_client
    _use_stub(app, tmp_path)
    resp = client.get("/api/ffmpeg/status")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["available"] is False
    assert data["kind"] == "none"
    assert data["path"] is None
    assert data["download"]["status"] == "idle"


def test_status_phan_loai_he_thong_tai_ve_wheel(app_client, tmp_path, monkeypatch):
    """kind: system (shutil.which) / downloaded (trong ffmpeg_dir) / wheel."""
    client, app, engine, _ = app_client
    # Hệ thống: locate trả đúng đường which() tìm được.
    monkeypatch.setattr("shutil.which",
                        lambda name: "/usr/bin/ffmpeg" if name == "ffmpeg" else None)
    _use_stub(app, tmp_path, locate_path="/usr/bin/ffmpeg")
    data = client.get("/api/ffmpeg/status").json()
    assert data["available"] is True and data["kind"] == "system"
    assert "Không xác định" in (data["license"] or "")
    # Tải về: đường dẫn nằm trong ffmpeg_dir.
    stub = _use_stub(app, tmp_path, locate_path=None)
    stub._downloaded = True
    data = client.get("/api/ffmpeg/status").json()
    assert data["kind"] == "downloaded"
    assert "LGPL" in (data["license"] or "")
    # Wheel: đường dẫn chứa imageio_ffmpeg.
    _use_stub(app, tmp_path,
              locate_path="/tmp/x/site-packages/imageio_ffmpeg/binaries/ffmpeg")
    data = client.get("/api/ffmpeg/status").json()
    assert data["kind"] == "wheel"
    assert "GPL v3" in (data["license"] or "")


def test_post_khi_da_co_ffmpeg_khong_tai_lai(app_client, tmp_path, monkeypatch):
    """Đã có FFmpeg hệ thống: POST trả 200, không gọi download()."""
    client, app, engine, _ = app_client
    monkeypatch.setattr("shutil.which",
                        lambda name: "/usr/bin/ffmpeg" if name == "ffmpeg" else None)
    stub = _use_stub(app, tmp_path, locate_path="/usr/bin/ffmpeg")
    resp = client.post("/api/ffmpeg/download")
    assert resp.status_code == 200, resp.text
    assert resp.json()["available"] is True
    assert stub.download_calls == 0


def test_post_bat_dau_tai_nen_va_poll_tien_trinh(app_client, tmp_path):
    """POST trả 202 ngay (không chặn), poll GET tới done, tiến trình 0->100%."""
    client, app, engine, _ = app_client
    stub = _use_stub(app, tmp_path)
    resp = client.post("/api/ffmpeg/download")
    assert resp.status_code == 202, resp.text
    assert resp.json()["download"]["status"] == "downloading"
    assert stub.download_calls == 1
    # Poll tới khi done; tiến trình cuối phải 100%.
    final = _poll_download(client)
    assert final["status"] == "done"
    assert final["progress"] == 1.0
    assert final["percent"] == 100
    assert final["path"] == stub.downloaded_path
    assert "MP3" in final["message"]
    # GET /status sau khi tải xong: available + kind downloaded.
    data = client.get("/api/ffmpeg/status").json()
    assert data["available"] is True and data["kind"] == "downloaded"


def test_post_lan_2_trong_luc_dang_tai_khong_tai_trung(app_client, tmp_path):
    """Tử huyệt race: POST lần 2 trong lúc đang tải -> 200 downloading,
    download() chỉ gọi đúng 1 lần (không ghi đè .part lẫn nhau)."""
    client, app, engine, _ = app_client
    stub = _use_stub(app, tmp_path, step_sleep=0.3)
    resp1 = client.post("/api/ffmpeg/download")
    assert resp1.status_code == 202
    resp2 = client.post("/api/ffmpeg/download")
    assert resp2.status_code == 200, resp2.text
    assert resp2.json()["download"]["status"] == "downloading"
    final = _poll_download(client)
    assert final["status"] == "done"
    assert stub.download_calls == 1


def test_tai_loi_mat_mang_bao_ro_tieng_viet(app_client, tmp_path):
    """download() trả None (mất mạng giả lập): trạng thái error + đúng
    thông báo tiếng Việt của manager; app vẫn báo chưa có FFmpeg."""
    client, app, engine, _ = app_client
    stub = _use_stub(app, tmp_path, download_result="fail",
                     download_error="Không có mạng hoặc không tới được máy "
                                    "chủ tải FFmpeg (giả lập).")
    resp = client.post("/api/ffmpeg/download")
    assert resp.status_code == 202
    final = _poll_download(client)
    assert final["status"] == "error"
    assert "Không có mạng" in final["message"]
    assert final["progress"] == 0.0
    data = client.get("/api/ffmpeg/status").json()
    assert data["available"] is False
    # Tải lại sau lỗi được phép (không kẹt ở trạng thái error).
    resp = client.post("/api/ffmpeg/download")
    assert resp.status_code in (200, 202)
    final = _poll_download(client)
    assert final["status"] == "error"  # stub vẫn fail — quan trọng là retry được


def test_get_download_khi_chua_tai(app_client, tmp_path):
    """Chưa bấm tải: GET /api/ffmpeg/download trả idle, không lỗi."""
    client, app, engine, _ = app_client
    _use_stub(app, tmp_path)
    resp = client.get("/api/ffmpeg/download")
    assert resp.status_code == 200
    assert resp.json()["status"] == "idle"
    assert resp.json()["percent"] == 0
