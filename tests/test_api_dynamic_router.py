"""Test phát hiện router động (TK2.1 — wiring router cho agent TK2-FEATURES).

Server PHẢI tự include mọi module src/hpvoice/api/routes_*.py có thuộc tính
``router`` — agent song song thêm routes_dialogue/batch/srt/files thì server
tự nhận, không cần sửa server.py.
"""
import importlib
import sys
from pathlib import Path


def test_server_tu_include_cac_router_hien_co(app_client):
    """create_app() include đủ 5 router TK2.1 qua cơ chế discovery."""
    client, app, engine, tmp_path = app_client
    included = set(app.state.included_routers)
    assert {"routes_tts", "routes_voices", "routes_jobs",
            "routes_history", "routes_settings"} <= included


def test_router_moi_them_duoc_tu_phat_hien(tmp_path, monkeypatch):
    """Thêm 1 module routes_probe.py tạm -> create_app() tự include nó;
    xóa file sau test (không để lại rác trong src/)."""
    api_dir = Path("src/hpvoice/api")
    probe = api_dir / "routes_probe.py"
    probe.write_text(
        '"""Router probe tạm (chỉ dùng trong test discovery)."""\n'
        "from fastapi import APIRouter\n"
        "router = APIRouter()\n\n\n"
        "@router.get('/api/probe')\n"
        "def probe():\n"
        "    return {'probe': 'ok'}\n",
        encoding="utf-8",
    )
    try:
        # Gỡ module cũ khỏi cache (nếu test chạy lại) rồi tạo app mới.
        sys.modules.pop("hpvoice.api.routes_probe", None)
        from fastapi.testclient import TestClient

        from conftest import FakeEngine
        from hpvoice.api.server import create_app
        from hpvoice.config import ConfigStore

        config = ConfigStore(path=tmp_path / "config.yaml")
        app = create_app(engine=FakeEngine(), config=config,
                         data_dir=tmp_path / "data")
        assert "routes_probe" in app.state.included_routers
        with TestClient(app) as client:
            resp = client.get("/api/probe")
            assert resp.status_code == 200
            assert resp.json() == {"probe": "ok"}
    finally:
        probe.unlink(missing_ok=True)
        sys.modules.pop("hpvoice.api.routes_probe", None)


def test_router_loi_import_khong_lam_chet_server(tmp_path):
    """Module routes_* import lỗi -> server bỏ qua + log, các router khác vẫn chạy."""
    api_dir = Path("src/hpvoice/api")
    broken = api_dir / "routes_broken.py"
    broken.write_text("raise ImportError('lỗi giả lập để test discovery')\n",
                      encoding="utf-8")
    try:
        sys.modules.pop("hpvoice.api.routes_broken", None)
        from fastapi.testclient import TestClient

        from conftest import FakeEngine
        from hpvoice.api.server import create_app
        from hpvoice.config import ConfigStore

        config = ConfigStore(path=tmp_path / "config.yaml")
        app = create_app(engine=FakeEngine(), config=config,
                         data_dir=tmp_path / "data")
        assert "routes_broken" not in app.state.included_routers
        assert "routes_tts" in app.state.included_routers
        with TestClient(app) as client:
            assert client.get("/health").status_code == 200
    finally:
        broken.unlink(missing_ok=True)
        sys.modules.pop("hpvoice.api.routes_broken", None)
