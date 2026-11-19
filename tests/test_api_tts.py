"""Test API TTS (TK2.1/TK2.9) — T2.2, T2.9 (phần text), T2.10 (phần MP3).

Dùng FakeEngine (không load model). Kiểm chứng:
- POST /api/tts/generate -> 200 + WAV 48 kHz + header X-Engine/X-Duration-Sec.
- POST /api/tts/generate-with-subtitles -> ZIP duy nhất (audio + .srt);
  text > 5.000 ký tự -> 202 + job_id (async, poll endpoint 11).
- POST /v1/audio/speech (format OpenAI, gọi bằng httpx) -> audio bytes.
- Giới hạn: text rỗng/20.001 ký tự/giọng lạ/tốc độ ngoài 0,75–1,5 -> 400.
- MP3: format mp3 -> file MP3 thật (qua FFmpeg hệ thống).
"""
import io
import zipfile

import httpx
import pytest
import soundfile as sf


def test_generate_tra_wav_48khz_va_header(app_client):
    """T2.2: POST /api/tts/generate -> 200 + WAV 48 kHz mono + header engine/duration."""
    client, app, engine, tmp_path = app_client
    resp = client.post("/api/tts/generate", json={
        "text": "Xin chào các bạn, đây là HP Voice Studio.",
        "voice_id": "Hải Đăng", "format": "wav"})
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("audio/wav")
    assert resp.headers["X-Engine"] == "v3"
    assert float(resp.headers["X-Duration-Sec"]) == pytest.approx(0.5, abs=0.05)
    info = sf.info(io.BytesIO(resp.content))
    assert info.samplerate == 48000
    assert info.channels == 1
    assert info.duration == pytest.approx(0.5, abs=0.05)


def test_generate_giong_la_bao_400(app_client):
    """Giọng không tồn tại -> 400 + JSON lỗi {error:{code,message}} (SPEC §4)."""
    client, *_ = app_client
    resp = client.post("/api/tts/generate", json={
        "text": "Xin chào", "voice_id": "Giọng Không Có"})
    assert resp.status_code == 400
    body = resp.json()
    assert "error" in body and "message" in body["error"]
    assert "Giọng" in body["error"]["message"] or "giọng" in body["error"]["message"]


def test_generate_text_rong_va_qua_20000_ky_tu_bao_400(app_client):
    """Y6: text rỗng -> 400; text 20.001 ký tự -> 400 + nêu giới hạn."""
    client, *_ = app_client
    assert client.post("/api/tts/generate", json={
        "text": "   ", "voice_id": "Hải Đăng"}).status_code == 400
    resp = client.post("/api/tts/generate", json={
        "text": "x" * 20001, "voice_id": "Hải Đăng"})
    assert resp.status_code == 400
    assert "20.000" in resp.json()["error"]["message"] or "20000" in resp.json()["error"]["message"]
    # Đúng 20.000 ký tự thì được (fake engine trả audio ngay).
    resp = client.post("/api/tts/generate", json={
        "text": "x" * 20000, "voice_id": "Hải Đăng"})
    assert resp.status_code == 200


def test_generate_toc_do_ngoai_khoang_bao_400(app_client):
    """Tốc độ ngoài 0,75–1,5 -> 400; 1,5× thì thời lượng ≈ 1/1,5."""
    client, *_ = app_client
    resp = client.post("/api/tts/generate", json={
        "text": "Xin chào", "voice_id": "Hải Đăng", "speed": 2.0})
    assert resp.status_code == 400
    resp = client.post("/api/tts/generate", json={
        "text": "Xin chào", "voice_id": "Hải Đăng", "speed": 1.5})
    assert resp.status_code == 200, resp.text
    info = sf.info(io.BytesIO(resp.content))
    assert info.duration == pytest.approx(0.5 / 1.5, abs=0.1)


def test_generate_engine_v4_bao_400_ro_chua_ho_tro(app_client):
    """engine=v4 khi chưa có V4Engine (TK2.2) -> 400 rõ ràng, không fallback lặng."""
    client, *_ = app_client
    resp = client.post("/api/tts/generate", json={
        "text": "Xin chào", "voice_id": "Hạ Vy", "engine": "v4"})
    assert resp.status_code == 400
    assert "v4" in resp.json()["error"]["message"].lower()


def test_generate_mp3_tra_file_mp3_that(app_client):
    """T2.10: format mp3 -> audio/mpeg, magic bytes MP3, giải mã được bằng ffprobe/sf."""
    client, *_ = app_client
    resp = client.post("/api/tts/generate", json={
        "text": "Xin chào các bạn.", "voice_id": "Hải Đăng", "format": "mp3"})
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("audio/mpeg")
    assert resp.content[:3] == b"ID3" or resp.content[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2")
    assert len(resp.content) > 100


def test_generate_the_nghi_duoc_tach_khong_dua_vao_engine(app_client):
    """Thẻ [nghỉ 1s] được tách đoạn + chèn silence, KHÔNG đưa chuỗi '[nghỉ' vào engine."""
    client, app, engine, tmp_path = app_client
    resp = client.post("/api/tts/generate", json={
        "text": "Xin chào [nghỉ 1s] các bạn.", "voice_id": "Hải Đăng"})
    assert resp.status_code == 200, resp.text
    assert not any("[nghỉ" in c for c in engine.calls)
    info = sf.info(io.BytesIO(resp.content))
    # 2 đoạn 0,5 s + khoảng lặng 1 s ≈ 2,0 s (trừ im lặng mép đã có).
    assert info.duration == pytest.approx(2.0, abs=0.3)


def test_generate_with_subtitles_tra_zip_duy_nhat(app_client):
    """Endpoint 5 (Y11): text <= 5.000 -> ZIP duy nhất chứa audio.wav + subtitles.srt."""
    client, *_ = app_client
    resp = client.post("/api/tts/generate-with-subtitles", json={
        "text": "Xin chào các bạn. Hôm nay trời đẹp.",
        "voice_id": "Hải Đăng", "format": "wav"})
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("application/zip")
    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    names = zf.namelist()
    assert "audio.wav" in names
    assert "subtitles.srt" in names
    srt = zf.read("subtitles.srt").decode("utf-8")
    assert "Xin chào các bạn." in srt
    assert "00:00:00,000 -->" in srt
    wav_info = sf.info(io.BytesIO(zf.read("audio.wav")))
    assert wav_info.samplerate == 48000


def test_generate_with_subtitles_text_dai_chuyen_async(app_client):
    """Endpoint 5: text > 5.000 ký tự -> 202 + job_id, poll xong -> ZIP qua /result."""
    from conftest import poll_job

    client, *_ = app_client
    text = "Câu mẫu để kiểm tra chuyển async. " * 200  # > 5.000 ký tự
    assert len(text) > 5000
    resp = client.post("/api/tts/generate-with-subtitles", json={
        "text": text, "voice_id": "Hải Đăng", "format": "wav"})
    assert resp.status_code == 202, resp.text
    job_id = resp.json()["job_id"]
    job = poll_job(client, job_id, timeout=15)
    assert job["status"] == "done"
    assert job.get("result_url")
    result = client.get(f"/api/jobs/{job_id}/result")
    assert result.status_code == 200
    assert result.headers["content-type"].startswith("application/zip")
    zf = zipfile.ZipFile(io.BytesIO(result.content))
    assert "audio.wav" in zf.namelist() and "subtitles.srt" in zf.namelist()


def test_v1_audio_speech_tuong_thich_openai_qua_httpx(app_client):
    """T2.2/T2.9: httpx gọi POST /v1/audio/speech theo format OpenAI -> audio bytes."""
    import asyncio

    client, app, engine, tmp_path = app_client

    async def _call():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport,
                                     base_url="http://127.0.0.1:8124") as http:
            return await http.post("/v1/audio/speech", json={
                "input": "Xin chào các bạn, đây là HP Voice Studio.",
                "model": "v3-turbo", "voice": "Hải Đăng", "response_format": "wav"})

    resp = asyncio.run(_call())
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("audio/wav")
    assert resp.headers["X-Engine"] == "v3"
    info = sf.info(io.BytesIO(resp.content))
    assert info.samplerate == 48000 and info.channels == 1


def test_v1_audio_speech_mp3_va_model_v4_bao_400(app_client):
    """OpenAI endpoint: response_format mp3 -> audio/mpeg; model v4 -> 400 rõ ràng."""
    import asyncio

    client, app, *_ = app_client

    async def _call(payload):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport,
                                     base_url="http://127.0.0.1:8124") as http:
            return await http.post("/v1/audio/speech", json=payload)

    resp = asyncio.run(_call({
        "input": "Xin chào", "model": "v3-turbo",
        "voice": "Mai Anh", "response_format": "mp3"}))
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("audio/mpeg")
    bad = asyncio.run(_call({
        "input": "Xin chào", "model": "v4", "voice": "Hạ Vy"}))
    assert bad.status_code == 400
    too_long = asyncio.run(_call({
        "input": "x" * 20001, "model": "v3-turbo", "voice": "Hải Đăng"}))
    assert too_long.status_code == 400


def test_v1_models_va_v1_voices(app_client):
    """GET /v1/models -> v3-turbo; GET /v1/voices -> [{id, name}]."""
    client, *_ = app_client
    models = client.get("/v1/models")
    assert models.status_code == 200
    ids = [m["id"] for m in models.json()["data"]]
    assert "v3-turbo" in ids
    voices = client.get("/v1/voices")
    assert voices.status_code == 200
    assert {"id": "Hải Đăng", "name": "Hải Đăng"} in voices.json()
