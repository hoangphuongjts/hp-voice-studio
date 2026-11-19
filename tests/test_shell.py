"""Test DesktopShell (TK4.8, SPEC §12/§10 T4.1/T4.5) — bằng mock, KHÔNG cần pywebview thật.

- Webview giả inject qua ``webview_module=``: ``start()`` trả ngay (mô phỏng
  người dùng đóng cửa sổ) — kiểm được vòng đời server + nhả lock + cổng trống.
- Server thật (create_app + uvicorn + FakeEngine, KHÔNG load model) trên cổng
  trống ngẫu nhiên — kiểm được start -> /health 200 -> stop -> cổng trống.
"""
from __future__ import annotations

import socket
import urllib.request
from types import SimpleNamespace

import pytest

import hpvoice.shell as shell_module
from hpvoice.engines.fake import FakeEngine
from hpvoice.shell import DesktopShell


def _free_port() -> int:
    """Cổng trống ngẫu nhiên trên 127.0.0.1 (tránh đụng 8124 của máy)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])
    finally:
        sock.close()


def _port_free(host: str, port: int) -> bool:
    # SO_REUSEADDR như server thật: kết nối cũ còn TIME-WAIT sau khi dừng
    # server không có nghĩa là cổng còn bị chiếm (xem shell._port_free).
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind((host, port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


class FakeWebview:
    """Webview giả: ghi lại cửa sổ đã mở, start() trả ngay (mô phỏng đóng cửa sổ)."""

    def __init__(self) -> None:
        self.created: list = []
        self.started = False

    def create_window(self, title, url):
        window = SimpleNamespace(title=title, url=url, destroyed=False)
        window.destroy = lambda: setattr(window, "destroyed", True)
        self.created.append(window)
        return window

    def start(self):
        self.started = True


class FakeServer:
    """Server giả (không mở cổng thật): đếm start/stop, cổng cố định."""

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True


def _shell(tmp_path, **kwargs):
    kwargs.setdefault("data_dir", tmp_path / "data")
    kwargs.setdefault("lock_path", tmp_path / "hp-voice-studio.lock")
    return DesktopShell(**kwargs)


def test_import_khong_can_pywebview():
    """Import shell phải được dù chưa cài pywebview (thiếu thì báo lúc run())."""
    assert shell_module is not None
    assert hasattr(shell_module, "DesktopShell")


def test_run_day_du_vong_doi_server_that(tmp_path):
    """run(): lock -> server thật (FakeEngine) -> mở cửa sổ -> đóng -> server dừng + cổng trống."""
    port = _free_port()
    fake_webview = FakeWebview()
    shell = _shell(tmp_path, host="127.0.0.1", port=port,
                   engine=FakeEngine(), webview_module=fake_webview)
    assert _port_free("127.0.0.1", port)

    rc = shell.run(timeout=15)

    assert rc == 0
    assert fake_webview.started is True
    assert len(fake_webview.created) == 1
    window = fake_webview.created[0]
    assert window.title == "HP Voice Studio"
    assert window.url == f"http://127.0.0.1:{port}/ui/index.html"
    assert shell.lock_acquired is False  # nhả lock sau khi chạy xong
    assert _port_free("127.0.0.1", port)  # cổng được giải phóng, không còn tiến trình ma


def test_start_stop_server_that_health_200(tmp_path):
    """start_server() -> GET /health 200; stop_server() -> cổng trống."""
    port = _free_port()
    shell = _shell(tmp_path, host="127.0.0.1", port=port, engine=FakeEngine())
    base_url = shell.start_server(timeout=15)
    try:
        assert base_url == f"http://127.0.0.1:{port}"
        assert _port_free("127.0.0.1", port) is False  # server đang giữ cổng
        with urllib.request.urlopen(f"{base_url}/health", timeout=5) as resp:  # noqa: S310 - URL loopback do test tạo
            assert resp.status == 200
            assert resp.read().find(b"version") >= 0
    finally:
        shell.stop_server()
    assert _port_free("127.0.0.1", port)


def test_mo_trung_instance_lan_2_bi_chan(tmp_path):
    """Instance 1 đang giữ lock -> instance 2 run() trả 2, KHÔNG khởi động server."""
    lock_path = tmp_path / "hp-voice-studio.lock"
    shell1 = _shell(tmp_path, lock_path=lock_path, engine=FakeEngine())
    assert shell1.acquire_lock() is True
    try:
        calls = {"server_started": False}

        def _factory(host, port):
            calls["server_started"] = True
            return FakeServer(host, port)

        shell2 = _shell(tmp_path, lock_path=lock_path, engine=FakeEngine(),
                        webview_module=FakeWebview(), server_factory=_factory)
        rc = shell2.run()
        assert rc == 2
        assert calls["server_started"] is False  # instance 2 không chạy server
        assert shell2.lock_acquired is False
    finally:
        shell1.release_lock()


def test_thieu_pywebview_bao_ro_thoat_3(tmp_path, monkeypatch):
    """Chưa cài pywebview -> run() trả 3 + không crash import (TK4.8)."""
    monkeypatch.setattr(shell_module, "_webview", None)
    shell = _shell(tmp_path, engine=FakeEngine(), webview_module=None)
    rc = shell.run()
    assert rc == 3
    assert shell.lock_acquired is False


def test_request_stop_dong_cua_so(tmp_path):
    """request_stop() (signal handler) -> đóng cửa sổ đang mở."""
    shell = _shell(tmp_path, engine=FakeEngine(), webview_module=FakeWebview())
    window = SimpleNamespace(destroyed=False)
    window.destroy = lambda: setattr(window, "destroyed", True)
    shell._window = window  # noqa: SLF001 - test truy cập trạng thái nội bộ có chủ đích
    shell.request_stop()
    assert window.destroyed is True
    assert shell._stop_requested.is_set()  # noqa: SLF001


def test_lock_nha_roi_mo_lai_duoc(tmp_path):
    """Nhả lock xong thì instance mới giành lại được (mô phỏng đóng/mở lại, T4.5)."""
    lock_path = tmp_path / "hp-voice-studio.lock"
    shell1 = _shell(tmp_path, lock_path=lock_path)
    assert shell1.acquire_lock() is True
    shell1.release_lock()
    shell2 = _shell(tmp_path, lock_path=lock_path)
    assert shell2.acquire_lock() is True
    shell2.release_lock()
