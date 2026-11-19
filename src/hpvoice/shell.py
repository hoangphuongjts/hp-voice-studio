"""DesktopShell — vỏ desktop HP Voice Studio (TK4.8, SPEC §12/ADR-11, TH-26).

- Vỏ pywebview/WebView2 (Q20): mở UI local ``/ui/index.html`` trong cửa sổ
  desktop, KHÔNG mở trình duyệt tay.
- Ẩn console trên Windows: build PyInstaller dùng ``console=False``
  (xem ``packaging/windows/hp-voice-studio.spec``) — module này không tự
  ẩn console khi chạy từ source (để log còn thấy được khi debug).
- Sở hữu vòng đời server: khởi động server (uvicorn) trong thread nền ->
  chờ ``/health`` -> mở cửa sổ -> đóng cửa sổ thì dừng server + giải
  phóng cổng 8124 (không để tiến trình ma chiếm cổng, T4.5).
- Chống mở trùng instance: lock file (fcntl, Linux/macOS) / mutex hệ
  thống (CreateMutex, Windows). Instance thứ 2 báo rõ + thoát mã 2,
  không chạy chồng server.
- Graceful shutdown: bắt SIGINT/SIGTERM (chỉ ở main thread) -> dừng
  server + đóng cửa sổ + nhả lock.

pywebview là dependency TÙY CHỌN: chưa cài thì import module này vẫn
được (``webview`` = None); chỉ khi gọi ``run()`` mới báo rõ là thiếu
pywebview và thoát mã 3 (không crash import). Test dùng webview giả
inject qua ``webview_module=`` hoặc ``sys.modules["webview"]`` — không
cần cài pywebview thật để test logic vòng đời.
"""
from __future__ import annotations

import argparse
import os
import signal
import socket
import sys
import threading
import time
import urllib.request
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

# Chạy trực tiếp file này (``python src/hpvoice/shell.py`` hoặc entry
# PyInstaller) thì ``hpvoice`` chưa nằm trên sys.path — chèn src/ vào.
# Khi import như module (``from hpvoice.shell import ...``) thì bỏ qua.
if __package__ in (None, ""):
    _SRC_DIR = Path(__file__).resolve().parent.parent
    if str(_SRC_DIR) not in sys.path:
        sys.path.insert(0, str(_SRC_DIR))

try:
    import webview as _webview  # type: ignore[import-untyped]
except Exception:  # noqa: BLE001 - pywebview thiếu/hỏng thì báo lúc run(), không crash import
    _webview = None

#: Tên mutex Windows chống trùng instance (CreateMutex).
_WINDOWS_MUTEX_NAME = "HPVoiceStudio-single-instance"
#: Tên file lock Linux/macOS (đặt trong thư mục dữ liệu app).
_LOCK_FILENAME = "hp-voice-studio.lock"
#: Cổng mặc định (SPEC §4); 8123 đã có chủ (server TTS MODOLIVIO).
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8124

__all__ = [
    "DesktopShell",
    "WebViewMissingError",
    "DEFAULT_HOST",
    "DEFAULT_PORT",
]

class WebViewMissingError(RuntimeError):
    """pywebview chưa được cài — không mở được cửa sổ desktop."""


def _port_free(host: str, port: int) -> bool:
    """True khi bind được host:port (không ai giữ).

    Đặt SO_REUSEADDR như uvicorn/server thật vẫn làm: sau khi server dừng,
    các kết nối cũ còn ở trạng thái TIME-WAIT trên cổng đó — bind không có
    SO_REUSEADDR sẽ báo bận sai dù không còn tiến trình nào listen.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind((host, port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


class _SingleInstanceLock:
    """Chống trùng instance: lock file (POSIX) hoặc mutex (Windows).

    - POSIX: ``fcntl.flock`` non-blocking trên file lock; giữ handle mở
      suốt vòng đời shell, đóng file = nhả lock.
    - Windows: ``CreateMutexW``; ``ERROR_ALREADY_EXISTS (183)`` nghĩa là
      đã có instance khác giữ mutex.
    """

    def __init__(self, lock_path: str | Path | None = None) -> None:
        self.lock_path = Path(lock_path) if lock_path else None
        self._file = None
        self._mutex_handle = None
        self.acquired = False

    def acquire(self) -> bool:
        """Giành lock. True = giành được (instance đầu tiên); False = đã có instance khác."""
        if os.name == "nt":
            return self._acquire_windows()
        return self._acquire_posix()

    def _acquire_posix(self) -> bool:
        import fcntl

        assert self.lock_path is not None
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._file = open(self.lock_path, "w", encoding="utf-8")  # noqa: SIM115 - giữ handle để giữ lock
        try:
            fcntl.flock(self._file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self._file.close()
            self._file = None
            return False
        self._file.write(str(os.getpid()))
        self._file.flush()
        self.acquired = True
        return True

    def _acquire_windows(self) -> bool:
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        kernel32.CreateMutexW.restype = ctypes.c_void_p
        handle = kernel32.CreateMutexW(None, False, _WINDOWS_MUTEX_NAME)
        if not handle:
            return False
        # GetLastError() == 183 (ERROR_ALREADY_EXISTS) -> mutex đã có chủ.
        if kernel32.GetLastError() == 183:
            kernel32.CloseHandle(handle)
            return False
        self._mutex_handle = handle
        self.acquired = True
        return True

    def release(self) -> None:
        """Nhả lock (gọi khi shell dừng; an toàn khi gọi nhiều lần)."""
        if not self.acquired:
            return
        self.acquired = False
        if self._file is not None:
            try:
                import fcntl

                fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
            except Exception:  # noqa: BLE001 - nhả lock lỗi cũng phải đóng file
                pass
            self._file.close()
            self._file = None
        if self._mutex_handle is not None:
            try:
                import ctypes

                ctypes.windll.kernel32.CloseHandle(self._mutex_handle)  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001 - nhả mutex lỗi thì bỏ qua
                pass
            self._mutex_handle = None


class DesktopShell:
    """Vỏ desktop: server uvicorn (thread nền) + cửa sổ pywebview.

    ``server_factory`` (test/inject): callable ``(host, port) -> server``
    trong đó server có ``start()`` (không chặn), ``stop()`` và thuộc tính
    ``port`` (cổng thật sau khi bind, để hỗ trợ port=0 trong test).
    Mặc định dùng :func:`hpvoice.api.server.create_app` + uvicorn.
    ``webview_module`` (test/inject): module có ``create_window`` +
    ``start``; mặc định là ``webview`` đã import (None nếu thiếu pywebview).
    """

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        config: Any = None,
        data_dir: str | Path | None = None,
        engine: Any = None,
        url_path: str = "/ui/index.html",
        title: str = "HP Voice Studio",
        webview_module: Any = None,
        lock_path: str | Path | None = None,
        server_factory: Callable[[str, int], Any] | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.config = config
        self.data_dir = Path(data_dir) if data_dir else None
        self.engine = engine
        self.url_path = url_path
        self.title = title
        self.webview_module = webview_module if webview_module is not None else _webview
        self.server_factory = server_factory
        self._lock = _SingleInstanceLock(lock_path=lock_path or self._default_lock_path())
        self._server: Any = None
        self._stop_requested = threading.Event()
        self._window: Any = None

    # --- Đường dẫn / engine -------------------------------------------------

    def _default_lock_path(self) -> Path:
        """File lock mặc định: <thư mục dữ liệu app>/hp-voice-studio.lock."""
        if self.data_dir is not None:
            return self.data_dir / _LOCK_FILENAME
        try:
            from hpvoice.config import default_data_dir

            return default_data_dir() / _LOCK_FILENAME
        except Exception:  # noqa: BLE001 - không tính được data dir thì dùng thư mục home
            return Path.home() / (".hp-voice-studio-" + _LOCK_FILENAME)

    def _resolve_engine(self) -> Any:
        """Engine cho server: đã inject > HPVOICE_ENGINE=fake > None (V3 lười nạp)."""
        if self.engine is not None:
            return self.engine
        if os.environ.get("HPVOICE_ENGINE", "").strip().lower() == "fake":
            from hpvoice.engines.fake import FakeEngine

            return FakeEngine()
        return None  # create_app tự tạo V3Engine lười nạp (không load model lúc khởi động)

    def _default_server_factory(self, host: str, port: int) -> Any:
        """Tạo server uvicorn thật (chạy thread nền qua ``start()``)."""
        import uvicorn

        from hpvoice.api.server import create_app
        from hpvoice.config import ConfigStore

        config = self.config or ConfigStore()
        data_dir = self.data_dir
        kwargs: dict[str, Any] = {"engine": self._resolve_engine(), "config": config}
        if data_dir is not None:
            kwargs["data_dir"] = data_dir
        app = create_app(**kwargs)
        uv_config = uvicorn.Config(app, host=host, port=port, log_level="warning")
        uv_server = uvicorn.Server(uv_config)

        class _UvicornServer:
            """Adapter: start()/stop()/port cho uvicorn.Server."""

            def __init__(self, server: Any) -> None:
                self._server = server
                self._thread: threading.Thread | None = None

            def start(self) -> None:
                self._thread = threading.Thread(target=self._server.run,
                                                name="hp-uvicorn", daemon=True)
                self._thread.start()

            def stop(self) -> None:
                self._server.should_exit = True
                if self._thread is not None:
                    self._thread.join(timeout=10)

            @property
            def port(self) -> int:
                try:
                    servers = self._server.servers or []
                    if servers and servers[0].sockets:
                        return int(servers[0].sockets[0].getsockname()[1])
                except Exception:  # noqa: BLE001 - chưa bind xong thì trả cổng yêu cầu
                    pass
                return port

        return _UvicornServer(uv_server)

    # --- Vòng đời ------------------------------------------------------------

    def acquire_lock(self) -> bool:
        """Giành lock chống trùng instance. False = đã có instance khác đang chạy."""
        return self._lock.acquire()

    def release_lock(self) -> None:
        self._lock.release()

    @property
    def lock_acquired(self) -> bool:
        return self._lock.acquired

    def start_server(self, timeout: float = 30.0) -> str:
        """Khởi động server, chờ /health 200. Trả URL gốc (http://host:port)."""
        factory = self.server_factory or self._default_server_factory
        self._server = factory(self.host, self.port)
        self._server.start()
        # port=0 (test): cổng thật chỉ biết sau khi bind xong.
        deadline = time.time() + timeout
        last_error: str = ""
        while time.time() < deadline:
            actual_port = self._actual_port()
            if actual_port:
                url = f"http://{self.host}:{actual_port}/health"
                try:
                    with urllib.request.urlopen(url, timeout=1) as resp:  # noqa: S310 - URL loopback do chính mình tạo
                        if resp.status == 200:
                            self.port = actual_port
                            return f"http://{self.host}:{actual_port}"
                except Exception as exc:  # noqa: BLE001 - server chưa sẵn sàng thì chờ tiếp
                    last_error = str(exc)
            time.sleep(0.1)
        self.stop_server()
        raise TimeoutError(
            f"Server HP Voice Studio không sẵn sàng sau {timeout:g}s "
            f"(host={self.host} port={self.port}): {last_error}"
        )

    def _actual_port(self) -> int | None:
        """Cổng server đang bind thật (port=0 -> cổng hệ thống cấp)."""
        if self._server is None:
            return None
        try:
            port = int(self._server.port)
        except Exception:  # noqa: BLE001 - server giả không có .port
            return self.port or None
        return port if port else None

    def stop_server(self) -> None:
        """Dừng server (nếu đang chạy) + giải phóng cổng."""
        server, self._server = self._server, None
        if server is None:
            return
        try:
            server.stop()
        except Exception:  # noqa: BLE001 - dừng lỗi thì vẫn coi như đã dừng (test assert cổng trống)
            pass

    def open_window(self, base_url: str) -> None:
        """Mở cửa sổ desktop ở ``base_url + url_path`` (chặn tới khi đóng cửa sổ)."""
        if self.webview_module is None:
            raise WebViewMissingError(
                "pywebview chưa được cài — không mở được cửa sổ desktop. "
                "Cài bằng: pip install pywebview "
                "(Windows cần WebView2 Runtime — xem docs/clean-machine-checklist.md). "
                "Hoặc chạy server riêng: python scripts/run_server.py rồi mở "
                "http://127.0.0.1:8124/ui/index.html bằng trình duyệt."
            )
        url = base_url.rstrip("/") + self.url_path
        self._window = self.webview_module.create_window(self.title, url)
        self.webview_module.start()

    # --- Graceful shutdown ---------------------------------------------------

    def request_stop(self) -> None:
        """Yêu cầu dừng (từ signal handler): đóng cửa sổ + dừng server."""
        self._stop_requested.set()
        try:
            if self._window is not None and hasattr(self._window, "destroy"):
                self._window.destroy()
        except Exception:  # noqa: BLE001 - cửa sổ đã đóng thì bỏ qua
            pass

    def _install_signal_handlers(self) -> None:
        """Bắt SIGINT/SIGTERM — chỉ cài được ở main thread (test thread thì bỏ qua)."""
        if threading.current_thread() is not threading.main_thread():
            return
        try:
            signal.signal(signal.SIGINT, lambda *_: self.request_stop())
            signal.signal(signal.SIGTERM, lambda *_: self.request_stop())
        except (ValueError, OSError, RuntimeError):
            pass  # không phải main thread / nền tảng không hỗ trợ -> bỏ qua

    # --- Chạy ----------------------------------------------------------------

    def run(self, timeout: float = 30.0) -> int:
        """Chạy shell đầy đủ: lock -> server -> cửa sổ -> dừng server + nhả lock.

        Mã thoát: 0 = chạy xong bình thường (đóng cửa sổ); 2 = đã có instance
        khác đang chạy; 3 = thiếu pywebview.
        """
        if not self.acquire_lock():
            print(
                "HP Voice Studio đã đang chạy — instance thứ 2 không khởi động "
                "để tránh chạy chồng server (cổng 8124). Hãy dùng cửa sổ đang mở, "
                "hoặc đóng app cũ rồi mở lại."
            )
            return 2
        try:
            if self.webview_module is None:
                print(
                    "pywebview chưa được cài — không mở được cửa sổ desktop. "
                    "Cài bằng: pip install pywebview "
                    "(Windows cần WebView2 Runtime — xem docs/clean-machine-checklist.md)."
                )
                return 3
            self._install_signal_handlers()
            base_url = self.start_server(timeout=timeout)
            print(f"HP Voice Studio đang chạy tại {base_url}{self.url_path}")
            try:
                self.open_window(base_url)
            finally:
                self.stop_server()
            return 0
        finally:
            self.release_lock()


def _print_version() -> int:
    """In version rồi thoát — không nạp model, không mở cửa sổ."""
    from hpvoice.api.server import VERSION

    print(f"HP Voice Studio {VERSION}")
    return 0


def _check_imports() -> int:
    """Kiểm tra import các module chính (không nạp model, không mở cửa sổ)."""
    from hpvoice.api.server import VERSION, create_app  # noqa: F401
    from hpvoice.config import ConfigStore  # noqa: F401
    from hpvoice.engines.fake import FakeEngine  # noqa: F401

    print(f"HP Voice Studio {VERSION} — kiểm import OK (không nạp model).")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point: ``python -m hpvoice.shell`` / PyInstaller .exe (TK4.8)."""
    parser = argparse.ArgumentParser(
        description="HP Voice Studio — vỏ desktop (server local + cửa sổ pywebview).")
    parser.add_argument("--host", default=None, help="Mặc định lấy từ config (127.0.0.1).")
    parser.add_argument("--port", type=int, default=None, help="Mặc định lấy từ config (8124).")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--version", action="store_true",
                        help="Chỉ in version rồi thoát (không nạp model).")
    parser.add_argument("--check", action="store_true",
                        help="Chỉ kiểm import rồi thoát (không nạp model, không mở cửa sổ).")
    args = parser.parse_args(argv)

    if args.version:
        return _print_version()
    if args.check:
        return _check_imports()

    from hpvoice.config import ConfigStore

    config_path = Path(args.config)
    config = ConfigStore(path=config_path) if config_path.is_file() else ConfigStore()
    host = args.host or str(config.get("server.host", DEFAULT_HOST))
    port = args.port or int(config.get("server.port", DEFAULT_PORT))
    shell = DesktopShell(host=host, port=port, config=config)
    return shell.run()


if __name__ == "__main__":
    sys.exit(main())
