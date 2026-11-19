"""Test giới hạn API (TK2.9) — T2.9 đầy đủ.

- Text 20.001 ký tự -> 400 (đã có ở test_api_tts, đây là bản tổng hợp).
- Batch 501 mục -> 400 (qua helper check_batch_size — route batch thuộc
  TK2-FEATURES, helper dùng chung đã test ở test_queue).
- Hàng đợi đầy 20 job chờ -> job thứ 21 trả 429 (Q16).
- Hàng đợi đầy thì job mới không làm mất job cũ (20 job chờ vẫn đủ).
"""
import threading
import time

from fastapi.testclient import TestClient

from conftest import FakeEngine, poll_job
from hpvoice.api.server import create_app
from hpvoice.config import ConfigStore


def test_hang_doi_day_20_job_thi_job_21_tra_429(tmp_path):
    """T2.9: lấp 1 chạy + 20 chờ -> request tiếp theo 429 + thông báo rõ."""
    engine = FakeEngine(block_first=True)
    config = ConfigStore(path=tmp_path / "config.yaml")
    app = create_app(engine=engine, config=config, data_dir=tmp_path / "data")
    c_main = TestClient(app)
    c_first = TestClient(app)
    holder = {}

    def first_request():
        with c_first:
            holder["resp"] = c_first.post("/api/tts/generate", json={
                "text": "Câu đầu tiên.", "voice_id": "Hải Đăng"})

    t = threading.Thread(target=first_request, daemon=True)
    t.start()
    deadline = time.time() + 10
    while time.time() < deadline and not engine.calls:
        time.sleep(0.05)
    assert engine.calls, "Request đầu phải bắt đầu synthesize trước"

    queued_ids = []
    with c_main:
        for i in range(20):
            resp = c_main.post("/api/tts/generate", json={
                "text": f"Câu chờ số {i}.", "voice_id": "Mai Anh"})
            assert resp.status_code == 202, f"job chờ {i}: {resp.status_code} {resp.text}"
            queued_ids.append(resp.json()["job_id"])
        # Job thứ 21 (20 chờ đã đầy) -> 429.
        resp = c_main.post("/api/tts/generate", json={
            "text": "Câu vượt giới hạn.", "voice_id": "Mai Anh"})
        assert resp.status_code == 429, resp.text
        assert "20" in resp.json()["error"]["message"]
    engine.release.set()
    t.join(timeout=10)
    assert holder["resp"].status_code == 200
    with c_main:
        for job_id in queued_ids:
            job = poll_job(c_main, job_id, timeout=15)
            assert job["status"] == "done", f"job {job_id}: {job}"


def test_hang_doi_day_khong_mat_job_cu(tmp_path):
    """Sau khi bị 429, 20 job chờ cũ vẫn còn nguyên trong hàng đợi."""
    engine = FakeEngine(block_first=True)
    config = ConfigStore(path=tmp_path / "config.yaml")
    app = create_app(engine=engine, config=config, data_dir=tmp_path / "data")
    c_main = TestClient(app)
    c_first = TestClient(app)
    holder = {}

    def first_request():
        with c_first:
            holder["resp"] = c_first.post("/api/tts/generate", json={
                "text": "Câu đầu.", "voice_id": "Hải Đăng"})

    t = threading.Thread(target=first_request, daemon=True)
    t.start()
    deadline = time.time() + 10
    while time.time() < deadline and not engine.calls:
        time.sleep(0.05)
    assert engine.calls
    with c_main:
        for i in range(20):
            assert c_main.post("/api/tts/generate", json={
                "text": f"Câu {i}.", "voice_id": "Mai Anh"}).status_code == 202
        assert c_main.post("/api/tts/generate", json={
            "text": "Câu thừa.", "voice_id": "Mai Anh"}).status_code == 429
        listing = c_main.get("/api/jobs").json()
        assert listing["total"] == 21  # 1 chạy + 20 chờ, không mất job nào
    engine.release.set()
    t.join(timeout=10)
