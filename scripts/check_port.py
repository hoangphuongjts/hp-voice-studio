#!/usr/bin/env python3
"""Kiểm tra cổng HP Voice Studio trước khi chạy server (TK2.1, SPEC §4, TH-13).

- Cổng mặc định 8124 (8123 đã có chủ: server TTS của MODOLIVIO).
- Cổng bận -> in thông báo rõ (kèm dịch vụ có thể đang chiếm theo bảng §4)
  và thoát mã 2 — server fail-fast, KHÔNG tự nhảy sang cổng khác.
- Cổng trống -> in OK, thoát 0.

Dùng:  .venv/bin/python scripts/check_port.py [--host 127.0.0.1] [--port 8124]
"""
from __future__ import annotations

import argparse
import socket
import sys

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8124

#: Bảng cổng đã chiếm (SPEC §4) — để báo rõ ai có thể đang giữ cổng.
KNOWN_PORTS = {
    5678: "n8n (máy Annie)",
    7860: "Gradio demo upstream (vieneu-web)",
    8000: "API server tương thích OpenAI của upstream",
    8001: "CIT Voice Studio / streaming demo upstream",
    8123: "server TTS của MODOLIVIO",
    8124: "HP Voice Studio (mặc định)",
    8765: "Ebook Library (production)",
    8766: "Ebook Library (staging)",
    23333: "Launcher serve.py của upstream",
}


def is_port_free(host: str, port: int) -> bool:
    """True khi bind được host:port (không có ai giữ)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((host, port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def check_port(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> tuple[bool, str]:
    """Kiểm tra cổng. Trả (trống?, thông báo)."""
    if is_port_free(host, port):
        return True, f"Cổng {port} trên {host} đang trống — HP Voice Studio chạy được."
    owner = KNOWN_PORTS.get(port)
    hint = f" (có thể bởi {owner})" if owner else ""
    return False, (
        f"Cổng {port} trên {host} đã bị chiếm{hint} — HP Voice Studio KHÔNG khởi động "
        "để tránh gọi nhầm đích. Hãy dừng dịch vụ đang chiếm cổng, hoặc đổi "
        "`server.port` trong config.yaml rồi chạy lại. Server không tự nhảy "
        "sang cổng khác (SPEC §4)."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Kiểm tra cổng HP Voice Studio.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args(argv)
    free, message = check_port(args.host, args.port)
    print(message)
    return 0 if free else 2


if __name__ == "__main__":
    sys.exit(main())
