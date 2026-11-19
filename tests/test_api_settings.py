"""Test API settings/config/dict (TK2.1) — endpoint 15, 16, 17 (SPEC §4).

- GET /api/config: trả config, KHÔNG bao giờ lộ key (key che ****).
- POST /api/config: đổi giọng mặc định/tốc độ, bền vững (ghi config.yaml).
- POST /api/config/v4-key: nhập/xoá key -> {configured}, key không trả lại/log.
- GET/POST /api/dict: từ điển phát âm (đọc/ghi), 201 khi thêm mới.
"""
import json


def test_get_config_khong_lo_key(app_client):
    """GET /api/config -> có server.port 8124, v4_configured false, không có key thật."""
    client, app, engine, tmp_path = app_client
    resp = client.get("/api/config")
    assert resp.status_code == 200
    body = resp.json()
    assert body["server"]["port"] == 8124
    assert body["server"]["host"] == "127.0.0.1"
    assert body["v4_configured"] is False
    assert "vn_sk_" not in json.dumps(body)
    # Trường key chỉ được là "" (chưa nhập) hoặc "****" (đã che) — không lộ giá trị thật.
    assert body["v4_api_key"] in ("", "****")


def test_post_config_doi_giong_mac_dinh_va_ghi_file(app_client):
    """POST /api/config đổi default_voice -> 200 + ghi bền vào config.yaml."""
    client, app, engine, tmp_path = app_client
    resp = client.post("/api/config", json={"audio": {"default_voice": "Mai Anh"}})
    assert resp.status_code == 200, resp.text
    assert resp.json()["audio"]["default_voice"] == "Mai Anh"
    # Đọc lại từ file: đổi bền vững qua khởi động lại (T3.7 phần API).
    saved = (tmp_path / "config.yaml").read_text(encoding="utf-8")
    assert "Mai Anh" in saved
    # Tốc độ ngoài khoảng -> 400.
    bad = client.post("/api/config", json={"audio": {"default_speed": 3.0}})
    assert bad.status_code == 400


def test_post_v4_key_nhap_va_xoa_khong_tra_lai_key(app_client):
    """POST /api/config/v4-key: nhập -> configured true; xoá -> false; key không trả lại."""
    client, *_ = app_client
    resp = client.post("/api/config/v4-key", json={"api_key": "vn_sk_test_khong_that"})
    assert resp.status_code == 200
    assert resp.json() == {"configured": True}
    assert "vn_sk_test" not in resp.text
    assert client.get("/api/config").json()["v4_configured"] is True
    # Xoá key.
    resp2 = client.post("/api/config/v4-key", json={"api_key": ""})
    assert resp2.json() == {"configured": False}
    assert client.get("/api/config").json()["v4_configured"] is False


def test_dict_doc_ghi_va_xoa(app_client):
    """GET /api/dict rỗng lúc đầu; POST thêm -> 201; GET thấy; DELETE xoá được."""
    client, *_ = app_client
    assert client.get("/api/dict").json() == {"items": [], "total": 0}
    resp = client.post("/api/dict", json={"word": "HP", "reading": "hát pê"})
    assert resp.status_code == 201, resp.text
    assert resp.json() == {"word": "HP", "reading": "hát pê"}
    got = client.get("/api/dict").json()
    assert got["total"] == 1
    assert got["items"][0]["word"] == "HP"
    # Thiếu reading -> 400.
    assert client.post("/api/dict", json={"word": "ABC"}).status_code == 400
    assert client.delete("/api/dict/HP").status_code == 204
    assert client.get("/api/dict").json()["total"] == 0
    assert client.delete("/api/dict/HP").status_code == 404
