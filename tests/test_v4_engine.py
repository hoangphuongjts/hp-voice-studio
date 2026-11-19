"""Test V4Engine + EngineRouter (TK2.2, T2.6 phần mock).

TUYỆT ĐỐI KHÔNG gọi api.vieneu.io thật: mọi test dùng httpx.MockTransport
+ key giả "test-key-xxx". Phần key thật chờ kiểm chứng thật (C5).
"""

import httpx
import numpy as np
import pytest

from hpvoice.engines.fake import fake_wav_bytes
from hpvoice.engines.router import (
    DEFAULT_V3_VOICE,
    EngineRouter,
    FallbackInfo,
    map_v4_voice_to_v3,
)
from hpvoice.engines.v4_engine import (
    V4Engine,
    V4Error,
    estimate_cost_chars,
    idempotency_key_for,
)

TEST_KEY = "test-key-xxx"
AUDIO_URL = "https://example.invalid/audio.wav"

VOICES_PAYLOAD = {
    "voices": [
        {"id": "Hạ Vy", "name": "Hạ Vy", "gender": "female", "region": "north",
         "engine": "v4", "kind": "catalog", "description": "Giọng nữ miền Bắc."},
        {"id": "Ngọc Lan", "name": "Ngọc Lan", "gender": "female", "region": "south",
         "engine": "v4", "kind": "catalog", "description": "Giọng nữ miền Nam, ấm và rõ."},
    ],
    "count": 2,
}
ENGINES_PAYLOAD = {
    "globalMultiplier": 1.0,
    "engines": [
        {"key": "v4", "label": "V4", "isDefault": True, "sampleRate": 48000,
         "billingMultiplier": 3.4, "features": ["generate", "dialogue", "dub", "srt"]},
    ],
}
BALANCE_PAYLOAD = {
    "remaining": 100000,
    "spendableTokens": 250000,
    "totalRemainingTokens": 250000,
    "plan": {"name": "test-plan"},
}


def make_engine(handler, **kwargs):
    """V4Engine với MockTransport (không gọi mạng thật)."""
    transport = httpx.MockTransport(handler)
    kwargs.setdefault("poll_interval_s", 0)
    kwargs.setdefault("sleep_fn", lambda s: None)
    return V4Engine(api_key=TEST_KEY, transport=transport, **kwargs)


def ok_tts_handler(request: httpx.Request) -> httpx.Response:
    """Handler mock chuẩn: /v1/tts -> queued, poll -> completed, audioUrl -> WAV."""
    path = request.url.path
    if path == "/api/v1/tts" and request.method == "POST":
        return httpx.Response(201, json={"jobId": "job-1", "status": "queued",
                                         "message": "Job queued."})
    if path == "/api/v1/tts/job-1":
        return httpx.Response(200, json={"jobId": "job-1", "status": "completed",
                                         "audioUrl": AUDIO_URL})
    if str(request.url) == AUDIO_URL:
        return httpx.Response(200, content=fake_wav_bytes("Xin chào"))
    if path == "/api/v1/voices":
        return httpx.Response(200, json=VOICES_PAYLOAD)
    if path == "/api/v1/engines":
        return httpx.Response(200, json=ENGINES_PAYLOAD)
    if path == "/api/v1/balance":
        return httpx.Response(200, json=BALANCE_PAYLOAD)
    if path == "/api/v1/audio/speech":
        return httpx.Response(200, content=fake_wav_bytes("Xin chào"),
                              headers={"Content-Type": "audio/wav"})
    if path == "/api/v1/dialogue":
        return httpx.Response(201, json={"success": True, "turnsCount": 2,
                                         "speakers": ["A", "B"], "audioUrl": AUDIO_URL,
                                         "audioUrlExpiresIn": 3600, "duration": 1.0,
                                         "tokenCost": 100})
    if path == "/api/v1/dub":
        return httpx.Response(201, json={"success": True, "transcript": "Xin chào",
                                         "voiceUsed": "Hạ Vy", "audioUrl": AUDIO_URL,
                                         "audioUrlExpiresIn": 3600, "duration": 1.0,
                                         "tokenCost": 80})
    if path == "/api/v1/srt":
        return httpx.Response(201, json={"success": True, "cuesCount": 2,
                                         "audioUrl": AUDIO_URL, "audioUrlExpiresIn": 86400,
                                         "duration": 2.0, "sampleRate": 48000,
                                         "tokenCost": 100, "placements": []})
    return httpx.Response(404, json={"error": "not found"})


# --- Idempotency-Key ---

def test_idempotency_key_deterministic_per_job():
    k1 = idempotency_key_for("job-abc", 0)
    k2 = idempotency_key_for("job-abc", 0)
    k3 = idempotency_key_for("job-abc", 1)
    assert k1 == k2  # cùng job + cùng đoạn -> cùng key (retry an toàn)
    assert k1 != k3  # đoạn khác -> key khác
    assert 8 <= len(k1) <= 128


def test_synthesize_async_happy_path():
    engine = make_engine(ok_tts_handler)
    result = engine.synthesize("Xin chào các bạn!", "Hạ Vy")
    assert result.engine == "v4"
    assert result.sample_rate == 48000
    assert result.duration_s > 0
    assert engine.last_job_id == "job-1"
    assert engine.last_idempotency_key  # đã gửi Idempotency-Key


def test_synthesize_splits_pause_tags_and_never_sends_them():
    seen_bodies: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/api/v1/tts":
            seen_bodies.append(request.content.decode("utf-8"))
        return ok_tts_handler(request)

    engine = make_engine(handler)
    result = engine.synthesize("Xin chào [nghỉ 1s] các bạn nhé!", "Hạ Vy")
    # 2 đoạn -> 2 lần POST /v1/tts, không body nào chứa "[nghỉ".
    assert len(seen_bodies) == 2
    assert all("[nghỉ" not in b for b in seen_bodies)
    # Độ dài = 2 đoạn fake + 1 s khoảng lặng.
    assert result.duration_s == pytest.approx(0.2 + 0.2 + 1.0, abs=0.05)


def test_synthesize_409_retries_same_key():
    keys: list[str] = []
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/api/v1/tts":
            calls["n"] += 1
            keys.append(request.headers.get("Idempotency-Key", ""))
            if calls["n"] == 1:
                return httpx.Response(409, json={"code": "IDEMPOTENCY_IN_FLIGHT"},
                                      headers={"Retry-After": "0"})
        return ok_tts_handler(request)

    engine = make_engine(handler)
    result = engine.synthesize("Xin chào!", "Hạ Vy")
    assert calls["n"] == 2
    assert keys[0] == keys[1]  # retry CÙNG key
    assert result.duration_s > 0


def test_synthesize_422_no_retry():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/api/v1/tts":
            calls["n"] += 1
            return httpx.Response(422, json={"code": "IDEMPOTENCY_KEY_REUSED"})
        return ok_tts_handler(request)

    engine = make_engine(handler)
    with pytest.raises(V4Error) as excinfo:
        engine.synthesize("Xin chào!", "Hạ Vy")
    assert excinfo.value.code == "idempotency_reused"
    assert calls["n"] == 1  # không retry


@pytest.mark.parametrize("status,code", [(401, "unauthorized"), (403, "quota_exceeded"),
                                         (429, "rate_limited")])
def test_error_codes_distinguished(status, code):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(status, json={"error": "x"},
                                  headers={"Retry-After": "5"})
        return ok_tts_handler(request)

    engine = make_engine(handler)
    with pytest.raises(V4Error) as excinfo:
        engine.synthesize("Xin chào!", "Hạ Vy")
    assert excinfo.value.code == code
    assert excinfo.value.status == status
    if status == 429:
        assert excinfo.value.retry_after_s == 5.0
    if status == 403:
        assert "403" in str(excinfo.value)


def test_synthesize_sync_no_retry_after_timeout():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/audio/speech":
            calls["n"] += 1
            raise httpx.TimeoutException("giả lập timeout", request=request)
        return ok_tts_handler(request)

    engine = make_engine(handler)
    with pytest.raises(V4Error) as excinfo:
        engine.synthesize_sync("Xin chào!", "Hạ Vy")
    assert excinfo.value.code == "timeout_no_retry"
    assert calls["n"] == 1  # KHÔNG retry sau timeout (không có idempotency)


def test_synthesize_sync_happy_path():
    engine = make_engine(ok_tts_handler)
    result = engine.synthesize_sync("Xin chào!", "Hạ Vy")
    assert result.engine == "v4"
    assert result.duration_s > 0


def test_no_api_key_error():
    engine = V4Engine(api_key=None, transport=httpx.MockTransport(ok_tts_handler))
    with pytest.raises(V4Error) as excinfo:
        engine.synthesize("Xin chào!", "Hạ Vy")
    assert excinfo.value.code == "no_api_key"


# --- Catalogue / số dư / phí ---

def test_list_preset_voices_mock():
    engine = make_engine(ok_tts_handler)
    voices = engine.list_preset_voices()
    assert len(voices) == 2
    assert voices[0].id == "Hạ Vy"
    assert voices[1].gender == "female"


def test_get_balance_and_engines_mock():
    engine = make_engine(ok_tts_handler)
    balance = engine.get_balance()
    assert balance["remaining"] == 100000
    assert balance["spendableTokens"] == 250000
    engines = engine.get_engines()
    assert engines["globalMultiplier"] == 1.0
    assert engines["engines"][0]["billingMultiplier"] == 3.4


def test_estimate_cost_formula():
    # Công thức: max(50, ký tự) × engine × global — ví dụ số trong docs/v4-billing.md.
    assert estimate_cost_chars(100, 3.4, 1.0) == pytest.approx(340.0)
    assert estimate_cost_chars(9, 3.4, 1.0) == pytest.approx(170.0)  # tối thiểu 50
    assert estimate_cost_chars(1000, 3.4, 1.0) == pytest.approx(3400.0)
    engine = make_engine(ok_tts_handler)
    assert engine.estimate_cost("x" * 100) == pytest.approx(340.0)


# --- Dialogue / dub / srt trên cloud (không idempotency) ---

def test_create_dialogue_no_idempotency_header():
    seen_headers: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/dialogue":
            seen_headers.append(dict(request.headers))
        return ok_tts_handler(request)

    engine = make_engine(handler)
    result = engine.create_dialogue([
        {"speaker": "A", "voiceId": "Hạ Vy", "text": "Xin chào!"},
        {"speaker": "B", "voiceId": "Ngọc Lan", "text": "Chào bạn!"},
    ])
    assert result.duration_s > 0
    # OpenAPI parameters: [] -> KHÔNG gửi Idempotency-Key.
    assert "idempotency-key" not in {k.lower() for k in seen_headers[0]}
    with pytest.raises(ValueError):
        engine.create_dialogue([{"speaker": "A", "voiceId": "Hạ Vy", "text": "x"}] * 51)


def test_create_dub_and_srt_mock():
    engine = make_engine(ok_tts_handler)
    dub = engine.create_dub(fake_wav_bytes("Xin chào"), "Hạ Vy")
    assert dub.duration_s > 0
    srt = engine.create_srt(b"1\n00:00:00,000 --> 00:00:02,000\nXin chao\n", "Hạ Vy")
    assert srt.duration_s > 0
    with pytest.raises(ValueError):
        engine.create_dub(b"x" * (10 * 1024 * 1024 + 1), "Hạ Vy")


def test_create_dialogue_timeout_no_retry():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/dialogue":
            raise httpx.TimeoutException("giả lập timeout", request=request)
        return ok_tts_handler(request)

    engine = make_engine(handler)
    with pytest.raises(V4Error) as excinfo:
        engine.create_dialogue([{"speaker": "A", "voiceId": "Hạ Vy", "text": "Xin chào!"}])
    assert excinfo.value.code == "timeout_no_retry"


# --- EngineRouter + fallback ---

class _FailingV4:
    """Engine V4 giả luôn lỗi 403 (để test fallback không cần mạng)."""

    name = "v4"
    sample_rate = 48000

    def synthesize(self, text, voice, options=None):
        raise V4Error("V4 lỗi 403 hết quota", status=403, code="quota_exceeded")


def test_router_map_v4_voice_to_v3():
    assert map_v4_voice_to_v3("Hạ Vy") == "Trúc Ly"  # Nữ Bắc -> Trúc Ly
    assert map_v4_voice_to_v3("Ngọc Lan") == "Thùy Dung"  # Nữ Nam -> Thùy Dung
    assert map_v4_voice_to_v3("Trúc Ly") == "Trúc Ly"  # đã là preset V3
    assert map_v4_voice_to_v3("Giọng Lạ 123") == DEFAULT_V3_VOICE  # không biết -> Hải Đăng
    assert map_v4_voice_to_v3("X", gender="Nữ", region="Trung") == "Ngọc Trân"
    assert map_v4_voice_to_v3("X", gender="Nam", region="Trung") == "Quang Sơn"


def test_router_fallback_reports_reason_and_new_voice():
    from hpvoice.engines.fake import FakeEngine

    router = EngineRouter(v3_engine=FakeEngine(), v4_engine=_FailingV4())
    result, info = router.synthesize("Xin chào!", "Hạ Vy", engine="v4")
    assert result.engine == "fake"
    assert isinstance(info, FallbackInfo)
    assert info.from_voice == "Hạ Vy"
    assert info.to_voice == "Trúc Ly"
    assert info.message == (
        "V4 lỗi 403 hết quota → fallback V3, giọng đổi Hạ Vy → Trúc Ly"
    )


def test_router_voice_strict_no_fallback():
    from hpvoice.engines.fake import FakeEngine

    router = EngineRouter(v3_engine=FakeEngine(), v4_engine=_FailingV4())
    with pytest.raises(V4Error) as excinfo:
        router.synthesize("Xin chào!", "Hạ Vy", engine="v4", voice_strict=True)
    assert excinfo.value.code == "quota_exceeded"


def test_router_fallback_voice_modes():
    from hpvoice.engines.fake import FakeEngine

    router = EngineRouter(v3_engine=FakeEngine(), v4_engine=_FailingV4(),
                          fallback_voice="default")
    _r, info = router.synthesize("Xin chào!", "Hạ Vy", engine="v4")
    assert info.to_voice == "Hải Đăng"
    router_fail = EngineRouter(v3_engine=FakeEngine(), v4_engine=_FailingV4(),
                               fallback_voice="fail")
    with pytest.raises(V4Error):
        router_fail.synthesize("Xin chào!", "Hạ Vy", engine="v4")
    with pytest.raises(ValueError):
        EngineRouter(v3_engine=FakeEngine(), fallback_voice="sai")


def test_router_resolve_cloud_fallback():
    from hpvoice.engines.fake import FakeEngine

    router = EngineRouter(v3_engine=FakeEngine(), v4_engine=_FailingV4())
    err = V4Error("V4 lỗi 403 hết quota", status=403, code="quota_exceeded")
    assert router.resolve_cloud_fallback(err, "Hạ Vy", voice_strict=False) == "Trúc Ly"
    with pytest.raises(V4Error):
        router.resolve_cloud_fallback(err, "Hạ Vy", voice_strict=True)
