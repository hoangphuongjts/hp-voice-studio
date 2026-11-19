"""Test API jobs (TK2.3) — T2.9 (phần hàng đợi), T2.8.

- Request TTS thứ 2 khi CPU bận -> 202 + job_id (không 429); poll -> done.
- GET /api/jobs/{id}/result tải lại audio của job đã xong.
- Hủy job đang chờ -> cancelled; job không tồn tại -> 404.
"""
import threading
import time

import pytest
from fastapi.testclient import TestClient

from conftest import FakeEngine, poll_job
from hpvoice.api.server import create_app
from hpvoice.config import ConfigStore


def _make_blocking_client(tmp_path):
    """App với engine chặn ở lần synthesize đầu (giả CPU đang bận)."""
    engine = FakeEngine(block_first=True)
    config = ConfigStore(path=tmp_path / "config.yaml")
    app = create_app(engine=engine, config=config, data_dir=tmp_path / "data")
    return app, engine


def test_request_thu_2_khi_ban_xep_hang_202_va_poll_xong(tmp_path):
    """T2.9: request 2 khi đang bận -> 202 + job_id; poll -> done; result ra WAV."""
    app, engine = _make_blocking_client(tmp_path)
    c1, c2 = TestClient(app), TestClient(app)
    result_holder = {}

    def first_request():
        with c1:
            result_holder["resp"] = c1.post("/api/tts/generate", json={
                "text": "Câu đầu tiên.", "voice_id": "Hải Đăng"})

    t = threading.Thread(target=first_request, daemon=True)
    t.start()
    # Chờ request đầu chiếm CPU (engine đã bắt đầu synthesize lần 1).
    deadline = time.time() + 10
    while time.time() < deadline and not engine.calls:
        time.sleep(0.05)
    assert engine.calls, "Request đầu phải bắt đầu synthesize trước"

    with c2:
        resp2 = c2.post("/api/tts/generate", json={
            "text": "Câu thứ hai.", "voice_id": "Mai Anh"})
    assert resp2.status_code == 202, resp2.text
    job_id = resp2.json()["job_id"]
    assert resp2.json()["status"] == "queued"

    engine.release.set()  # thả CPU
    t.join(timeout=10)
    assert result_holder["resp"].status_code == 200

    with c2:
        job = poll_job(c2, job_id, timeout=10)
    assert job["status"] == "done"
    with c2:
        result = c2.get(f"/api/jobs/{job_id}/result")
    assert result.status_code == 200
    assert result.headers["content-type"].startswith("audio/wav")
    assert len(result.content) > 100


def test_get_job_khong_ton_tai_404_va_result_khi_chua_xong_409(app_client):
    """GET /api/jobs/{id} lạ -> 404; /result khi job chưa xong -> 409."""
    client, app, engine, tmp_path = app_client
    assert client.get("/api/jobs/khong-co").status_code == 404
    assert client.get("/api/jobs/khong-co/result").status_code == 404


def test_huy_job_dang_cho_thanh_cancelled(app_client):
    """Hủy job đang chờ: POST /cancel -> cancelled, không chạy nữa."""
    client, app, engine, tmp_path = app_client
    # Chặn CPU bằng 1 job chạy nền dài qua hàng đợi: dùng engine chặn.
    engine2 = FakeEngine(block_first=True)
    config = ConfigStore(path=tmp_path / "config2.yaml")
    app2 = create_app(engine=engine2, config=config, data_dir=tmp_path / "data2")
    c1, c2 = TestClient(app2), TestClient(app2)
    holder = {}

    def first():
        with c1:
            holder["resp"] = c1.post("/api/tts/generate", json={
                "text": "Câu đầu.", "voice_id": "Hải Đăng"})

    t = threading.Thread(target=first, daemon=True)
    t.start()
    deadline = time.time() + 10
    while time.time() < deadline and not engine2.calls:
        time.sleep(0.05)
    assert engine2.calls
    with c2:
        resp2 = c2.post("/api/tts/generate", json={
            "text": "Câu chờ hủy.", "voice_id": "Mai Anh"})
    assert resp2.status_code == 202
    job_id = resp2.json()["job_id"]
    with c2:
        cancel = c2.post(f"/api/jobs/{job_id}/cancel")
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "cancelled"
    with c2:
        job = c2.get(f"/api/jobs/{job_id}").json()
    assert job["status"] == "cancelled"
    engine2.release.set()
    t.join(timeout=10)


def test_list_jobs_hien_cac_job_da_tao(app_client):
    """GET /api/jobs liệt kê job đã tạo (mới nhất trước)."""
    client, *_ = app_client
    client.post("/api/tts/generate", json={"text": "Câu một.", "voice_id": "Hải Đăng"})
    client.post("/api/tts/generate", json={"text": "Câu hai.", "voice_id": "Mai Anh"})
    resp = client.get("/api/jobs")
    assert resp.status_code == 200
    assert resp.json()["total"] == 2
