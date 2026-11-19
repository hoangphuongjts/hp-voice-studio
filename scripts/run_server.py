#!/usr/bin/env python3
"""Chạy HP Voice Studio API server (TK2.1, SPEC §4/§6).

- Đọc config.yaml (không có thì dùng mặc định: 127.0.0.1:8124).
- Kiểm tra cổng trước bằng scripts/check_port.py: bận -> fail-fast, thoát 2,
  KHÔNG tự nhảy cổng.
- Engine V3 lười nạp: model chỉ nạp khi request TTS/voices đầu tiên tới
  (khởi động server không chờ tải model).

Dùng:  .venv/bin/python scripts/run_server.py [--host 127.0.0.1] [--port 8124]
        [--config config.yaml]
        .venv/bin/python scripts/run_server.py --version   # chỉ in version, không nạp model
        .venv/bin/python scripts/run_server.py --check     # chỉ kiểm import, không nạp model

Biến môi trường HPVOICE_ENGINE=fake -> dùng FakeEngine (test/smoke gói đóng gói,
KHÔNG nạp model). Mọi giá trị khác -> V3Engine lười nạp như mặc định.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_DIR / "src"))
sys.path.insert(0, str(REPO_DIR / "scripts"))

from check_port import check_port  # noqa: E402


def _print_version() -> int:
    """In version rồi thoát — không đọc config, không kiểm cổng, không nạp model."""
    from hpvoice.api.server import VERSION

    print(f"HP Voice Studio {VERSION}")
    return 0


def _check_imports() -> int:
    """Kiểm tra import các module chính (không nạp model, không mở cổng)."""
    from hpvoice.api.server import VERSION, create_app  # noqa: F401
    from hpvoice.config import ConfigStore  # noqa: F401
    from hpvoice.engines.fake import FakeEngine  # noqa: F401

    print(f"HP Voice Studio {VERSION} — kiểm import OK (không nạp model).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Chạy HP Voice Studio API server.")
    parser.add_argument("--host", default=None, help="Mặc định lấy từ config.")
    parser.add_argument("--port", type=int, default=None, help="Mặc định lấy từ config.")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--version", action="store_true",
                        help="Chỉ in version rồi thoát (không nạp model).")
    parser.add_argument("--check", action="store_true",
                        help="Chỉ kiểm import rồi thoát (không nạp model, không mở cổng).")
    args = parser.parse_args(argv)

    if args.version:
        return _print_version()
    if args.check:
        return _check_imports()

    from hpvoice.api.server import create_app
    from hpvoice.config import ConfigStore

    config_path = Path(args.config)
    config = ConfigStore(path=config_path) if config_path.is_file() else ConfigStore()
    host = args.host or str(config.get("server.host", "127.0.0.1"))
    port = args.port or int(config.get("server.port", 8124))

    free, message = check_port(host, port)
    print(message)
    if not free:
        return 2

    # TK4.2: HPVOICE_ENGINE=fake -> FakeEngine (smoke test gói đóng gói, không nạp model).
    engine = None
    if os.environ.get("HPVOICE_ENGINE", "").strip().lower() == "fake":
        from hpvoice.engines.fake import FakeEngine

        engine = FakeEngine()
        print("Engine: FakeEngine (HPVOICE_ENGINE=fake — không nạp model thật).")

    app = create_app(engine=engine, config=config)
    print(f"HP Voice Studio API đang chạy tại http://{host}:{port} "
          f"(engine V3 lười nạp — model tải khi request đầu tiên tới).")
    import uvicorn

    uvicorn.run(app, host=host, port=port, log_level="info")
    return 0


if __name__ == "__main__":
    sys.exit(main())
