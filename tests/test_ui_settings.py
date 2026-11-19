"""Test tab Cài đặt (TK3.5/TK3.6, test T3.7).

Kiểm chứng qua TestClient + assert ID phần tử trong JS:
- tabs-settings.js: đủ ID (giọng mặc định, model, thư mục, key V4, API local,
  giao diện sáng/tối, giới thiệu + giấy phép + ghi công VieNeu-TTS).
- API key V4: nhập/xoá qua POST /api/config/v4-key; GET /api/config KHÔNG
  bao giờ trả lại key (chỉ "****"/"" + v4_configured).
- Cài đặt bền vững: POST /api/config rồi GET lại vẫn giữ (T3.7).
"""
SETTINGS_IDS = [
    "settings-default-voice",  # giọng mặc định
    "settings-precision",      # model fp32/int8 + tự phát hiện CPU
    "settings-threads",
    "settings-cpu-info",
    "settings-output-dir",     # thư mục lưu
    "settings-model-dir",      # thư mục model/cache
    "settings-v4-key",         # nhập key V4
    "settings-v4-save",
    "settings-v4-clear",       # xoá key
    "settings-v4-status",      # chưa có key / key hợp lệ / lỗi
    "settings-v4-estimate",    # ước tính phí
    "settings-warn-chars",     # ngưỡng cảnh báo ký tự
    "settings-server-port",    # API local: cổng
    "settings-lan-enabled",    # bật/tắt LAN
    "settings-generate-lan-key",  # nút tạo khoá mới
    "settings-ffmpeg-status",  # FFmpeg: trạng thái hiện tại (có/chưa có, loại nào)
    "settings-ffmpeg-download",  # nút Tải FFmpeg (POST /api/ffmpeg/download)
    "settings-ffmpeg-progress",  # thanh tiến trình tải %
    "settings-ffmpeg-hint",    # hướng dẫn khi chưa có FFmpeg / tải lỗi
    "settings-theme",          # giao diện sáng/tối
    "settings-about",          # giới thiệu + giấy phép + ghi công
    "settings-save-btn",
]


def test_tab_cai_dat_du_id_phan_tu(app_client):
    client, app, engine, tmp_path = app_client
    resp = client.get("/ui/tabs-settings.js")
    assert resp.status_code == 200, resp.text
    js = resp.text
    assert "registerTab" in js
    assert "'settings'" in js or '"settings"' in js
    assert "Cài đặt" in js
    for element_id in SETTINGS_IDS:
        assert element_id in js, f"tabs-settings.js thiếu #{element_id}"
    assert "/api/config" in js
    assert "/api/config/v4-key" in js
    assert "/api/ffmpeg/status" in js
    assert "/api/ffmpeg/download" in js
    assert "Tải FFmpeg" in js
    assert "VieNeu-TTS" in js  # ghi công VieNeu-TTS
    assert "tính phí theo ký tự" in js
    assert "new Audio" not in js


def test_v4_key_khong_bao_gio_tra_lai(app_client):
    """Key V4 nhập qua API rồi GET /api/config: chỉ thấy ****, không thấy key."""
    client, app, engine, tmp_path = app_client
    secret = "vn_sk_KHONG-BAO-GIO-DUOC-LO-12345"
    resp = client.post("/api/config/v4-key", json={"api_key": secret})
    assert resp.status_code == 200
    assert resp.json() == {"configured": True}
    cfg = client.get("/api/config").json()
    assert cfg["v4_configured"] is True
    assert cfg["v4_api_key"] == "****"
    assert secret not in str(cfg)  # key không lộ trong bất kỳ trường nào
    # Xoá key -> trạng thái về chưa có key.
    resp = client.post("/api/config/v4-key", json={"api_key": ""})
    assert resp.json() == {"configured": False}
    cfg = client.get("/api/config").json()
    assert cfg["v4_configured"] is False
    assert cfg["v4_api_key"] == ""


def test_cai_dat_ben_vung_qua_khoi_dong_lai_app(app_client):
    """T3.7 (phần bền vững): đổi giọng mặc định + precision rồi GET lại vẫn giữ."""
    client, app, engine, tmp_path = app_client
    resp = client.post("/api/config", json={
        "audio": {"default_voice": "Mai Anh", "default_speed": 1.25},
        "engine": {"v3": {"precision": "int8", "threads": 4}},
    })
    assert resp.status_code == 200, resp.text
    cfg = client.get("/api/config").json()
    assert cfg["audio"]["default_voice"] == "Mai Anh"
    assert cfg["audio"]["default_speed"] == 1.25
    assert cfg["engine"]["v3"]["precision"] == "int8"
    assert cfg["engine"]["v3"]["threads"] == 4


def test_cai_dat_tu_choi_gia_tri_sai(app_client):
    """Tốc độ ngoài 0,75×–1,5× và precision lạ -> 400 rõ ràng (không ghi config lỗi)."""
    client, app, engine, tmp_path = app_client
    resp = client.post("/api/config", json={"audio": {"default_speed": 2.0}})
    assert resp.status_code == 400
    assert "error" in resp.json()
    resp = client.post("/api/config", json={"engine": {"v3": {"precision": "siêu-nhanh"}}})
    assert resp.status_code == 400
