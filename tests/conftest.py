"""Chèn src/ vào sys.path để pytest import được gói hpvoice mà không cần
cài đặt (venv T1 không có setuptools để pip install -e .).

Bổ sung TK2: ``FakeEngine`` + fixture ``app_client`` dùng chung cho mọi test
API — engine giả KHÔNG load model (VM không đủ RAM/CPU để load model trong
mọi test), trả audio sine 0,5 s/1 lần synthesize.
"""
import sys
import threading
import time
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from hpvoice.engines.base import AudioResult, VoiceInfo  # noqa: E402
from hpvoice.engines.fake import FakeEngine as _BaseFakeEngine  # noqa: E402
# FakeEngine dùng chung cho test API là lớp con của FakeEngine chuẩn ở
# hpvoice/engines/fake.py (1 bản gốc duy nhất — xem TK2-FEATURES): lớp con chỉ
# thêm hành vi riêng cho test (ghi calls, block_first, audio cố định 0,5 s,
# tên engine "v3", 3 giọng) mà không đổi ngữ nghĩa của các test cũ.

FAKE_VOICES = [
    VoiceInfo(id="Hải Đăng", label="Hải Đăng", gender="Nam", style="Trẻ trung"),
    VoiceInfo(id="Mai Anh", label="Mai Anh", gender="Nữ", style="Nhẹ nhàng"),
    VoiceInfo(id="Thu Hà", label="Thu Hà", gender="Nữ", style="Trầm ấm"),
]
FAKE_VOICE_IDS = [v.id for v in FAKE_VOICES]


def _fake_audio(seconds: float = 0.5, sr: int = 48000) -> np.ndarray:
    """Audio sine 440 Hz, biên độ 0,3 — có tín hiệu thật (không im lặng)."""
    t = np.arange(int(seconds * sr), dtype=np.float32) / sr
    return (0.3 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)


class FakeEngine(_BaseFakeEngine):
    """Engine giả cho test API: không load model, không gọi SDK/V4.

    - ``synthesize`` trả 0,5 s audio sine, ghi lại mọi text đã nhận.
    - ``block_first``: lần synthesize đầu tiên chờ ``release`` (để giả lập
      CPU đang bận trong test hàng đợi/luồng đồng thời).
    """

    name = "v3"
    sample_rate = 48000

    def __init__(self, block_first: bool = False):
        super().__init__()
        self.calls: list[str] = []
        self.is_loaded = True
        self.load_seconds = 0.0
        self.precision = "fp32"
        self._block_first = block_first
        self._first_pending = block_first
        self.release = threading.Event()
        self.release.set()  # mặc định không chặn; test chặn thì clear()
        if block_first:
            self.release.clear()

    def ensure_loaded(self, progress_callback=None) -> None:
        self._loaded = True
        self.is_loaded = True
        return None

    def synthesize(self, text, voice, options=None):
        self.calls.append(text)
        if self._first_pending:
            self._first_pending = False
            self.release.wait(timeout=30)
        return AudioResult(
            samples=_fake_audio(), sample_rate=48000, engine="v3", voice=voice
        )

    def synthesize_stream(self, text, voice, options=None):
        yield self.synthesize(text, voice, options)

    def synthesize_batch(self, texts, voice, options=None):
        return [self.synthesize(t, voice, options) for t in texts]

    def list_preset_voices(self):
        return list(FAKE_VOICES)

    def resolve_voice(self, name):
        if name is None:
            return None
        return name if name in FAKE_VOICE_IDS else None

    def close(self):
        return None


@pytest.fixture()
def fake_engine():
    """FakeEngine mặc định (không chặn)."""
    return FakeEngine()


@pytest.fixture()
def app_client(tmp_path, fake_engine):
    """TestClient của app TK2 với FakeEngine + thư mục dữ liệu tạm.

    Trả ``(client, app, engine, tmp_path)`` — client là TestClient đã mở
    (context manager) để lifespan/startup chạy nếu có.
    """
    from fastapi.testclient import TestClient

    from hpvoice.api.server import create_app
    from hpvoice.config import ConfigStore

    config = ConfigStore(path=tmp_path / "config.yaml")
    app = create_app(engine=fake_engine, config=config, data_dir=tmp_path / "data")
    with TestClient(app) as client:
        yield client, app, fake_engine, tmp_path


def poll_job(client, job_id: str, timeout: float = 10.0) -> dict:
    """Poll GET /api/jobs/{id} tới khi done/error/cancelled (hoặc hết giờ)."""
    deadline = time.time() + timeout
    last = {}
    while time.time() < deadline:
        resp = client.get(f"/api/jobs/{job_id}")
        assert resp.status_code == 200, resp.text
        last = resp.json()
        if last.get("status") in ("done", "error", "cancelled"):
            return last
        time.sleep(0.05)
    raise AssertionError(f"Job {job_id} không xong sau {timeout}s, trạng thái cuối: {last}")
