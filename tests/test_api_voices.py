"""Test API voices/health/preview (TK2.1/TK2.9) — T2.1, T2.10 (phần preview cache).

- GET /health đúng schema SPEC §4 endpoint 1.
- GET /voices đủ giọng preset (fake: 3 giọng) kèm gender/style/engine.
- GET /voices/{id}/preview: lần 1 MISS (tổng hợp), lần 2 HIT (từ cache,
  engine không được gọi lại) — T2.10.
"""
import io

import soundfile as sf


def test_health_dung_schema(app_client):
    """T2.1: GET /health -> 200 + {status, engine, v3_ready, v4_configured, version}."""
    client, *_ = app_client
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["engine"] == "v3"
    assert body["v3_ready"] is True
    assert body["v4_configured"] is False
    assert body["version"]


def test_voices_tra_danh_sach_giong_kem_thuoc_tinh(app_client):
    """GET /voices -> đủ giọng preset, mỗi giọng có id/name/gender/style/engine."""
    client, *_ = app_client
    resp = client.get("/voices")
    assert resp.status_code == 200
    voices = resp.json()
    assert len(voices) == 3
    hai_dang = next(v for v in voices if v["id"] == "Hải Đăng")
    assert hai_dang["name"] == "Hải Đăng"
    assert hai_dang["gender"] == "Nam"
    assert hai_dang["engine"] == "v3"
    assert "featured" in hai_dang


def test_voices_engine_v4_bao_400(app_client):
    """GET /voices?engine=v4 khi chưa có V4 -> 400 rõ ràng (không trả danh sách rỗng lặng)."""
    client, *_ = app_client
    resp = client.get("/voices", params={"engine": "v4"})
    assert resp.status_code == 400
    assert "v4" in resp.json()["error"]["message"].lower()


def test_preview_lan_2_tra_tu_cache_khong_tong_hop_lai(app_client):
    """T2.10: preview lần 1 MISS, lần 2 HIT — engine chỉ synthesize 1 lần."""
    client, app, engine, tmp_path = app_client
    r1 = client.get("/voices/Hải Đăng/preview")
    assert r1.status_code == 200, r1.text
    assert r1.headers["content-type"].startswith("audio/wav")
    assert r1.headers.get("X-Cache") == "MISS"
    assert len(engine.calls) == 1
    info = sf.info(io.BytesIO(r1.content))
    assert info.samplerate == 48000

    r2 = client.get("/voices/Hải Đăng/preview")
    assert r2.status_code == 200
    assert r2.headers.get("X-Cache") == "HIT"
    assert len(engine.calls) == 1  # không tổng hợp lại
    assert r2.content == r1.content  # đúng file cache


def test_preview_giong_khac_co_cache_rieng_va_giong_la_404(app_client):
    """Mỗi giọng có cache riêng; giọng không tồn tại -> 404."""
    client, app, engine, tmp_path = app_client
    client.get("/voices/Hải Đăng/preview")
    assert len(engine.calls) == 1
    client.get("/voices/Mai Anh/preview")
    assert len(engine.calls) == 2
    resp = client.get("/voices/Giọng%20Không%20Có/preview")
    assert resp.status_code == 404
