"""Test endpoint clone/xoá giọng (endpoint 10 + DELETE /api/voices/{id}, TK3.2).

Dùng FakeEngine (không load model): VoiceStore.clone_voice enroll qua
FakeEngine.add_voice (bộ nhớ), kiểm tra độ dài clip bằng soundfile thật.
MP3 decode qua FFmpegManager (cần ffmpeg hệ thống — skip nếu không có).
"""
import io
import shutil
import subprocess

import numpy as np
import pytest
import soundfile as sf


def _wav_bytes(seconds: float, sr: int = 48000) -> bytes:
    """WAV sine 440 Hz dài ``seconds`` giây (PCM 16-bit, mono)."""
    t = np.arange(int(seconds * sr), dtype=np.float32) / sr
    samples = (0.3 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    buf = io.BytesIO()
    sf.write(buf, samples, sr, format="WAV", subtype="PCM_16")
    return buf.getvalue()


def _clone(client, wav: bytes, filename="clip.wav", **data):
    payload = {"name": "Giọng test", "owner": "Người test",
               "consent": "true", "consent_text": "Tôi cam kết đây là giọng của tôi."}
    payload.update(data)
    return client.post(
        "/api/voices/clone",
        files={"audio": (filename, wav)},
        data=payload,
    )


def test_clone_success_wav(app_client):
    client, _app, _engine, _tmp = app_client
    resp = _clone(client, _wav_bytes(4.0))
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["id"] == "Giọng test"
    assert body["is_clone"] is True
    assert abs(body["clip_seconds"] - 4.0) < 0.1
    # GET /voices liệt kê giọng clone vừa tạo.
    voices = client.get("/voices").json()
    clones = [v for v in voices if v.get("is_clone") and v["id"] == "Giọng test"]
    assert len(clones) == 1


def test_clone_missing_consent(app_client):
    client, _app, _engine, _tmp = app_client
    resp = _clone(client, _wav_bytes(4.0), consent="false")
    assert resp.status_code == 400, resp.text
    assert "cam kết" in resp.json()["error"]["message"]


def test_clone_missing_consent_text(app_client):
    client, _app, _engine, _tmp = app_client
    resp = _clone(client, _wav_bytes(4.0), consent_text="")
    assert resp.status_code == 400, resp.text


def test_clone_clip_too_short(app_client):
    client, _app, _engine, _tmp = app_client
    resp = _clone(client, _wav_bytes(2.0))
    assert resp.status_code == 400, resp.text
    assert "3" in resp.json()["error"]["message"]


def test_clone_clip_too_long(app_client):
    client, _app, _engine, _tmp = app_client
    resp = _clone(client, _wav_bytes(9.0))
    assert resp.status_code == 400, resp.text


def test_clone_duplicate_name(app_client):
    client, _app, _engine, _tmp = app_client
    assert _clone(client, _wav_bytes(4.0)).status_code == 201
    resp = _clone(client, _wav_bytes(4.0))
    assert resp.status_code == 400, resp.text
    assert "đã tồn tại" in resp.json()["error"]["message"]


def test_clone_preset_name(app_client):
    client, _app, _engine, _tmp = app_client
    resp = _clone(client, _wav_bytes(4.0), name="Hải Đăng")
    assert resp.status_code == 400, resp.text


def test_clone_bad_audio(app_client):
    client, _app, _engine, _tmp = app_client
    resp = _clone(client, b"RIFF....fake")
    assert resp.status_code == 400, resp.text


def test_clone_empty_file(app_client):
    client, _app, _engine, _tmp = app_client
    resp = _clone(client, b"")
    assert resp.status_code == 400, resp.text


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="cần ffmpeg hệ thống")
def test_clone_mp3_decoded_via_ffmpeg(app_client, tmp_path):
    client, _app, _engine, _tmp = app_client
    mp3_path = tmp_path / "clip.mp3"
    r = subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
         "-i", "sine=frequency=440:duration=4",
         "-ar", "48000", "-ac", "1", str(mp3_path)],
        capture_output=True, text=True, timeout=60,
    )
    assert r.returncode == 0, r.stderr
    resp = _clone(client, mp3_path.read_bytes(), filename="clip.mp3")
    assert resp.status_code == 201, resp.text
    assert abs(resp.json()["clip_seconds"] - 4.0) < 0.2


def test_delete_clone(app_client):
    client, _app, _engine, _tmp = app_client
    assert _clone(client, _wav_bytes(4.0)).status_code == 201
    resp = client.delete("/api/voices/Giọng test", params={"reason": "Chủ giọng yêu cầu gỡ."})
    assert resp.status_code == 204, resp.text
    voices = client.get("/voices").json()
    assert not [v for v in voices if v["id"] == "Giọng test"]
    # Xoá lần nữa -> 404.
    resp = client.delete("/api/voices/Giọng test", params={"reason": "Lại gỡ."})
    assert resp.status_code == 404, resp.text


def test_delete_preset_returns_404(app_client):
    client, _app, _engine, _tmp = app_client
    resp = client.delete("/api/voices/Hải Đăng", params={"reason": "Thử xoá preset."})
    assert resp.status_code == 404, resp.text


def test_delete_without_reason_returns_400(app_client):
    client, _app, _engine, _tmp = app_client
    assert _clone(client, _wav_bytes(4.0)).status_code == 201
    resp = client.delete("/api/voices/Giọng test")
    assert resp.status_code == 400, resp.text
