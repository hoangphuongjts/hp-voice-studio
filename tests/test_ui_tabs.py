"""Test UI tab TK3.2/TK3.3/TK3.4 (SPEC §5, §10 T3.2–T3.6, §12 TK3.2–TK3.4).

Hai lớp kiểm chứng, KHÔNG load model (mọi test dùng TestClient + FakeEngine
qua fixture ``app_client`` trong tests/conftest.py):

1. Kiểm tĩnh trên file JS: mỗi file tab phải đăng ký đúng id/group/label qua
   ``registerTab``, phải gọi đúng endpoint API mà tab dùng, phải chứa các
   phần tử/chuỗi bắt buộc theo SPEC (khoá giọng, cam kết, 1,5× không cắt chữ,
   "v1 không OCR", mốc [P1], cảnh báo max_history_gb…).
2. Kiểm API thật qua TestClient: các endpoint mà tab dùng phải trả 200 với
   FakeEngine (conversation, srt-dub, batch, files/read, history).
   Riêng POST /api/voices/clone (tab Giọng của tôi): API CHƯA CÓ endpoint
   này — test ghi nhận 404 và đánh dấu là "thiếu, chờ coordinator bổ sung",
   không tự thêm endpoint.
"""
import io
import json
import re
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
UI = REPO / "ui"

SRT_BYTES = b"""1
00:00:00,000 --> 00:00:02,000
Xin chao cac ban!

2
00:00:02,500 --> 00:00:05,000
Tam biet nhe!
"""


def _read(name: str) -> str:
    return (UI / name).read_text(encoding="utf-8")


def _assert_registered(src: str, tab_id: str, group: str, label: str):
    assert "registerTab" in src, "thiếu lời gọi registerTab"
    pattern = re.compile(
        r"registerTab\(\{\s*id:\s*['\"]" + re.escape(tab_id) + r"['\"],\s*"
        r"group:\s*['\"]" + re.escape(group) + r"['\"],\s*"
        r"label:\s*['\"]" + re.escape(label) + r"['\"]",
        re.DOTALL,
    )
    assert pattern.search(src), (
        f"registerTab sai id/group/label, cần id={tab_id!r} group={group!r} label={label!r}"
    )


# --- TK3.2: Tab Hội thoại / Podcast ---------------------------------------

def test_tab_dialogue_registers_and_calls_conversation_api():
    src = _read("tabs-dialogue.js")
    _assert_registered(src, "dialogue", "Tạo", "Hội thoại / Podcast")
    assert "/api/tts/conversation" in src
    # Tối đa 8 nhân vật (MAX_SPEAKERS của ConversationEngine, TH-10).
    assert "MAX_SPEAKERS = 8" in src
    # Khoá giọng cố định theo nhân vật + lưu/mở kịch bản JSON.
    assert "Khoá giọng" in src or "locked" in src
    assert "dlg-add-speaker" in src and "dlg-add-line" in src
    assert "dlg-save" in src and "dlg-load" in src
    assert "dlg-pause" in src  # khoảng lặng giữa lượt


def test_tab_voices_registers_and_has_consent_and_mic():
    src = _read("tabs-voices.js")
    _assert_registered(src, "voices", "Thư viện", "Giọng của tôi")
    # Cả 2 cách lấy mẫu (Q13): thu micro + nhập file MP3/WAV/M4A.
    assert "MediaRecorder" in src and "getUserMedia" in src
    assert ".mp3" in src and ".wav" in src and ".m4a" in src
    # Đếm ngược 8 s, tự dừng.
    assert "MAX_CLIP_S = 8" in src
    assert "tự dừng" in src
    # Cam kết bắt buộc: tick + tên chủ giọng trước khi Tạo giọng.
    assert "voice-consent" in src and "voice-owner" in src
    assert "Cam kết quyền sử dụng" in src
    # Ghi chú pháp lý + cơ chế gỡ khi khiếu nại (TH-04/TH-17).
    assert "13/2023" in src and "147/2024" in src
    assert "khiếu nại" in src
    # Gọi endpoint clone theo hợp đồng (dù API chưa có — xem test cuối file).
    assert "/api/voices/clone" in src
    assert "voice-list" in src


# --- TK3.3: Tab Lồng tiếng .srt + Đọc file --------------------------------

def test_tab_srt_registers_and_calls_srt_dub_api():
    src = _read("tabs-srt.js")
    _assert_registered(src, "srt", "Tạo", "Lồng tiếng .srt")
    assert "/api/tts/srt-dub" in src
    assert ".srt" in src and ".vtt" in src
    # Quy tắc hiện rõ trong UI: tối đa 1,5×, không cắt chữ.
    assert "1,5" in src
    assert "không cắt chữ" in src.lower() or "không bao giờ cắt chữ" in src
    # Tiến trình từng câu + danh sách câu bị lùi + SRT đã chỉnh mốc.
    assert "srt-cues" in src and "srt-delayed" in src
    assert "report.json" in src and "dub.srt" in src
    assert "srt-progress" in src


def test_tab_files_registers_and_calls_files_read_api():
    src = _read("tabs-files.js")
    _assert_registered(src, "files", "Tạo", "Đọc file")
    assert "/api/files/read" in src
    assert ".pdf" in src and ".docx" in src and ".txt" in src
    # Làm sạch + chuyển sang Phòng thu qua openStudio.
    assert "file-clean" in src and "file-to-studio" in src
    assert "openStudio" in src
    # PDF scan: báo rõ "v1 không OCR", không bịa text.
    assert "v1 không OCR" in src
    assert "file-preview" in src


# --- TK3.4: Tab Tạo hàng loạt + Bản đã tạo --------------------------------

def test_tab_batch_registers_and_calls_batch_api():
    src = _read("tabs-batch.js")
    _assert_registered(src, "batch", "Tạo", "Tạo hàng loạt")
    assert "/api/tts/batch" in src
    assert "/api/tts/batch/upload" in src
    # Mốc [P1]…, tải từng file / tải tất cả (.zip), thử lại riêng mục lỗi.
    assert "[P1]" in src
    assert "batch-download-all" in src
    assert "Thử lại riêng" in src
    # Danh sách dùng VirtualList (TK3.7) + nghe qua player dùng chung.
    assert "VirtualList" in src
    assert "NS.player" in src or "window.HPVoiceStudio.player" in src


def test_tab_history_registers_and_calls_history_api():
    src = _read("tabs-history.js")
    _assert_registered(src, "history", "Thư viện", "Bản đã tạo")
    assert "/api/history" in src
    # Nghe lại / tải lại / xoá / mở thư mục + tổng dung lượng + cảnh báo vượt giới hạn.
    assert "history-list" in src and "history-total" in src
    assert "history-warning" in src
    assert "max_history_gb" in src
    assert "DELETE" in src
    assert "VirtualList" in src


# --- API thật qua TestClient + FakeEngine (các endpoint tab dùng) ----------

def test_api_conversation_tab_endpoint(app_client):
    client, _app, _engine, _tmp = app_client
    resp = client.post("/api/tts/conversation", json={
        "lines": [
            {"speaker": "An", "text": "Xin chào các bạn!"},
            {"speaker": "Bình", "text": "Chào An nhé!"},
            {"speaker": "An", "text": "Khỏe không bạn?"},
        ],
        "speakers": {"An": "Hải Đăng", "Bình": "Mai Anh"},
        "pause_s": 0.5,
    })
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("audio/wav")
    assert len(resp.content) > 1000


def test_api_srt_dub_tab_endpoint(app_client):
    client, _app, _engine, _tmp = app_client
    resp = client.post(
        "/api/tts/srt-dub",
        files={"file": ("phu-de.srt", SRT_BYTES)},
        data={"voice_id": "Hải Đăng", "speed": "1.0"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        names = zf.namelist()
        report = json.loads(zf.read("report.json"))
    assert {"dub.wav", "dub.srt", "report.json"} <= set(names)
    assert report["cues"] == 2
    assert report["delayed"] == []  # 2 câu ngắn, không câu nào bị lùi


def test_api_batch_tab_endpoints(app_client):
    client, _app, _engine, _tmp = app_client
    resp = client.post("/api/tts/batch", json={
        "items": [
            {"id": "P1", "text": "Xin chào!"},
            {"id": "P2", "text": ""},  # mục lỗi: không chết batch
            {"id": "P3", "text": "Tạm biệt!"},
        ]
    })
    assert resp.status_code == 200, resp.text
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        names = zf.namelist()
        manifest = json.loads(zf.read([n for n in names if n.endswith("manifest.json")][0]))
    assert len([n for n in names if n.endswith(".wav")]) == 2
    statuses = {i["id"]: i["status"] for i in manifest["items"]}
    assert statuses == {"P1": "done", "P2": "error", "P3": "done"}

    resp = client.post(
        "/api/tts/batch/upload",
        files={"file": ("danh-sach.txt", b"[P1] Xin chao\n[P2] Tam biet\n")},
    )
    assert resp.status_code == 200, resp.text
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        names = zf.namelist()
    assert len([n for n in names if n.endswith(".wav")]) == 2


def test_api_files_read_tab_endpoint(app_client):
    client, _app, _engine, _tmp = app_client
    resp = client.post(
        "/api/files/read",
        files={"file": ("ghi-chu.txt", "Xin   chào\ncác bạn!".encode("utf-8"))},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["text"] == "Xin chào\ncác bạn!"
    assert data["kind"] == "txt"


def test_api_history_tab_endpoint(app_client):
    client, _app, _engine, _tmp = app_client
    resp = client.get("/api/history?limit=50&offset=0")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert set(data.keys()) >= {"items", "total", "total_bytes", "max_history_gb"}
    assert isinstance(data["items"], list)
    assert data["max_history_gb"] == 5


def test_api_voices_list_tab_endpoint(app_client):
    client, _app, _engine, _tmp = app_client
    resp = client.get("/voices?engine=v3")
    assert resp.status_code == 200, resp.text
    voices = resp.json()
    assert any(v["id"] == "Hải Đăng" for v in voices)
    # Nghe thử giọng (tab Giọng của tôi dùng để nghe thử clone).
    resp = client.get("/voices/Hải Đăng/preview")
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("audio/wav")


def test_api_voices_clone_endpoint_missing_documented(app_client):
    """Endpoint clone giọng CHƯA CÓ — ghi nhận để coordinator bổ sung.

    Tab Giọng của tôi gửi đúng request theo hợp đồng (multipart: audio +
    name + consent + consent_text + owner, endpoint 10 docs/api-contract.md),
    nhưng server hiện trả 404 vì chưa có route POST /api/voices/clone
    (logic clone đã có sẵn ở VoiceStore.clone_voice, TK1.5).
    Test này PASS khi API trả 404/405 (chưa có endpoint) HOẶC 200/400
    (endpoint đã được bổ sung sau) — không được pass giả khi trả lỗi khác.
    """
    client, _app, _engine, _tmp = app_client
    resp = client.post(
        "/api/voices/clone",
        files={"audio": ("clip.wav", b"RIFF....fake")},
        data={"name": "Giọng test", "owner": "Người test",
              "consent": "true", "consent_text": "Tôi cam kết."},
    )
    assert resp.status_code in (404, 405, 200, 400), resp.text
    if resp.status_code in (404, 405):
        # Ghi rõ vào kết quả test: endpoint thiếu, tab đã xử lý 404 bằng
        # thông báo rõ ràng (không bịa là đã tạo xong).
        src = _read("tabs-voices.js")
        assert "API chưa có endpoint POST /api/voices/clone" in src
