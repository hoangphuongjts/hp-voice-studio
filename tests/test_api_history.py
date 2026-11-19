"""Test API history (TK2.3/TK2.10) — T3.6 (phần API).

- Tạo 3 bản qua /api/tts/generate -> GET /api/history hiện đủ 3.
- Nghe/tải lại từng bản (GET /api/history/{id}); xoá từng bản (DELETE -> 204).
- Phân trang limit/offset; tổng dung lượng hiển thị đúng.
"""
import io

import soundfile as sf


def _make_three(client):
    ids = []
    for i, voice in enumerate(["Hải Đăng", "Mai Anh", "Thu Hà"]):
        resp = client.post("/api/tts/generate", json={
            "text": f"Câu lịch sử số {i}.", "voice_id": voice})
        assert resp.status_code == 200, resp.text
        ids.append(resp.headers.get("X-History-Id"))
    return ids


def test_history_hien_du_3_ban_sau_3_lan_tao(app_client):
    """T3.6: tạo 3 bản -> danh sách hiện đủ 3, đúng voice + dung lượng."""
    client, *_ = app_client
    _make_three(client)
    resp = client.get("/api/history")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert len(body["items"]) == 3
    voices = {item["voice_id"] for item in body["items"]}
    assert voices == {"Hải Đăng", "Mai Anh", "Thu Hà"}
    assert body["total_bytes"] > 0
    assert body["max_history_gb"] == 5
    for item in body["items"]:
        assert item["duration_sec"] == 0.5
        assert item["format"] == "wav"
        assert item["engine"] == "v3"


def test_history_tai_lai_va_xoa_tung_ban(app_client):
    """Nghe/tải lại 1 bản (GET -> WAV); xoá (DELETE -> 204), xoá lại -> 404."""
    client, *_ = app_client
    ids = _make_three(client)
    item_id = ids[0]
    assert item_id, "Response generate phải trả X-History-Id"
    got = client.get(f"/api/history/{item_id}")
    assert got.status_code == 200
    assert got.headers["content-type"].startswith("audio/wav")
    info = sf.info(io.BytesIO(got.content))
    assert info.samplerate == 48000
    assert client.get("/api/history/khong-co").status_code == 404

    deleted = client.delete(f"/api/history/{item_id}")
    assert deleted.status_code == 204
    assert client.get("/api/history").json()["total"] == 2
    assert client.delete(f"/api/history/{item_id}").status_code == 404


def test_history_phan_trang_limit_offset(app_client):
    """GET /api/history?limit&offset phân trang đúng."""
    client, *_ = app_client
    _make_three(client)
    page1 = client.get("/api/history", params={"limit": 2, "offset": 0}).json()
    assert len(page1["items"]) == 2 and page1["total"] == 3
    page2 = client.get("/api/history", params={"limit": 2, "offset": 2}).json()
    assert len(page2["items"]) == 1
    assert page2["items"][0]["id"] != page1["items"][0]["id"]
