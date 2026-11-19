"""Test khung UI + tab Phòng thu (TK3.1/TK3.6, test T3.1).

Kiểm chứng qua TestClient (phục vụ UI thật qua HTTP, không load model):
- GET / -> redirect /ui/index.html (khi ui/ tồn tại); GET /ui/index.html -> 200.
- index.html: header + nav + vùng nội dung + include script đúng thứ tự
  api.js -> player.js -> virtual-list.js -> tabs-*.js -> app.js (app.js cuối).
- app.js: registry tab + render nav từ registry (tab thiếu thì nav không hiện).
- Tab Phòng thu (tabs-studio.js): đủ ID phần tử theo SPEC §5.
"""
import re

import pytest

STUDIO_IDS = [
    "studio-text",           # ô nhập text
    "studio-char-count",     # đếm ký tự (giới hạn 20.000)
    "studio-voice",          # dropdown Giọng đọc
    "studio-voice-preview",  # nghe thử từng giọng (PreviewCache)
    "studio-preview-cost",   # ước tính phí nghe thử V4
    "studio-engine",         # chọn Engine V3/V4
    "studio-v4-fee",         # V4 hiện phí/ký tự trước khi gửi
    "studio-speed",          # tốc độ 0,75×–1,5×
    "studio-speed-value",
    "studio-insert-laugh",   # [cười]
    "studio-insert-sigh",    # [thở dài]
    "studio-insert-throat",  # [hắng giọng]
    "studio-insert-pause-2s",      # [nghỉ 2s]
    "studio-insert-pause-500ms",   # [nghỉ 500ms]
    "studio-dict-btn",       # nút Từ điển
    "studio-dict-panel",
    "studio-format",         # xuất WAV/MP3
    "studio-with-srt",       # tạo kèm .srt
    "studio-create-btn",     # nút Tạo
    "studio-stop-btn",       # nút Dừng phát
    "studio-queue",          # hàng đợi
    "studio-status",
]

# Script phải include theo đúng thứ tự (TK3.1): api -> player -> virtual-list
# -> tabs-*.js -> app.js cuối. File của agent TK3-UI-TABS có thể chưa có lúc
# chạy test này — chỉ assert index.html KHAI ĐÚNG tên file + thứ tự, không
# assert file đó trả 200 (trừ file của TK3-UI-CORE).
SCRIPT_ORDER = [
    "/ui/api.js",
    "/ui/player.js",
    "/ui/virtual-list.js",
    "/ui/tabs-studio.js",
    "/ui/tabs-dialogue.js",
    "/ui/tabs-srt.js",
    "/ui/tabs-files.js",
    "/ui/tabs-batch.js",
    "/ui/tabs-history.js",
    "/ui/tabs-voices.js",
    "/ui/tabs-settings.js",
    "/ui/app.js",
]


def test_root_redirect_ve_ui(app_client):
    client, app, engine, tmp_path = app_client
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code in (302, 307), resp.text
    assert resp.headers["location"] == "/ui/index.html"
    # Theo redirect thì tới được trang chính.
    followed = client.get("/", follow_redirects=True)
    assert followed.status_code == 200
    assert "HP Voice Studio" in followed.text


def test_index_html_khung_full_page_va_thu_tu_script(app_client):
    client, app, engine, tmp_path = app_client
    resp = client.get("/ui/index.html")
    assert resp.status_code == 200, resp.text
    html = resp.text
    assert "HP Voice Studio" in html
    for element_id in ("app-nav", "tab-content", "engine-status",
                       "engine-select", "toast-container"):
        assert f'id="{element_id}"' in html, f"thiếu #{element_id} trong index.html"
    for group in ("Tạo", "Thư viện", "Hệ thống"):
        assert group in html, f"thiếu nhóm tab {group}"
    positions = []
    for src in SCRIPT_ORDER:
        assert f'src="{src}"' in html, f"index.html thiếu script {src}"
        positions.append(html.index(f'src="{src}"'))
    assert positions == sorted(positions), "script không đúng thứ tự api -> ... -> app.js cuối"
    assert html.index('src="/ui/app.js"') > html.index('src="/ui/tabs-settings.js"')


def test_file_tinh_cua_tk3_ui_core_phuc_vu_duoc(app_client):
    """File JS/CSS của TK3-UI-CORE phải trả 200 (file agent kia chưa có thì thôi)."""
    client, app, engine, tmp_path = app_client
    for path in ("/ui/app.js", "/ui/api.js", "/ui/styles.css",
                 "/ui/tabs-studio.js", "/ui/tabs-settings.js"):
        resp = client.get(path)
        assert resp.status_code == 200, f"{path} -> {resp.status_code}"


def test_app_js_registry_va_chiu_duoc_tab_thieu(app_client):
    """app.js: registerTab + render nav từ registry; tab chưa đăng ký thì không hiện."""
    client, app, engine, tmp_path = app_client
    js = client.get("/ui/app.js").text
    assert "registerTab" in js
    assert "_pendingTabs" in js  # tab nạp trước app.js (script cuối) vẫn đăng ký được
    assert "engine-status" in js  # trạng thái engine luôn thấy ở header (TK3.6)
    assert "/health" in js  # poll trạng thái engine
    assert "toast" in js.lower()
    # Không tự tạo Audio mới — trình phát dùng chung của player.js (TK3.7).
    assert "new Audio" not in js


def test_api_js_wrapper_va_uoc_tinh_phi_v4(app_client):
    client, app, engine, tmp_path = app_client
    js = client.get("/ui/api.js").text
    assert "127.0.0.1:8124" in js
    assert "estimateV4Cost" in js
    assert "MAX" in js or "50" in js  # tối thiểu 50 ký tự/request
    assert "error" in js  # xử lý envelope {"error": {code, message}}
    assert "fetchJson" in js  # tab dialogue (agent kia) dùng fetchJson
    assert "new Audio" not in js


def test_tab_phong_thu_du_id_phan_tu(app_client):
    """Tab Phòng thu: đủ ID phần tử SPEC §5 (assert trong tabs-studio.js)."""
    client, app, engine, tmp_path = app_client
    js = client.get("/ui/tabs-studio.js").text
    assert "registerTab" in js
    assert "'studio'" in js or '"studio"' in js
    assert "Phòng thu" in js
    for element_id in STUDIO_IDS:
        assert element_id in js, f"tabs-studio.js thiếu #{element_id}"
    assert "20000" in js or "20.000" in js  # giới hạn ký tự
    assert "/api/tts/generate" in js
    assert "/voices" in js  # nạp danh sách giọng
    assert "preview" in js.lower()  # nghe thử qua PreviewCache
    assert "tính phí theo ký tự" in js  # V4 luôn ghi rõ trước khi gửi (TK3.6)
    assert "HPVoiceStudio.player" in js or "window.HPVoiceStudio.player" in js
    assert "new Audio" not in js  # dùng singleton player, không tạo Audio mới


def test_tab_phong_thu_khong_tu_tao_audio_moi(app_client):
    """Studio không được `new Audio()` — chỉ player singleton (TK3.7)."""
    client, app, engine, tmp_path = app_client
    for path in ("/ui/tabs-studio.js", "/ui/tabs-settings.js", "/ui/api.js", "/ui/app.js"):
        assert "new Audio" not in client.get(path).text, path


def test_health_khong_vo_khi_gan_static(app_client):
    """Gắn static mount không làm vỡ API hiện có."""
    client, app, engine, tmp_path = app_client
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] in ("ok", "starting")
    resp = client.get("/voices")
    assert resp.status_code == 200
