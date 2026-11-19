"""Routes hội thoại — POST /api/tts/conversation (TK2.4, SPEC §4 endpoint 7).

Body: ``{lines: [{speaker, text}], speakers: {name: voice_id}, format,
pause_s?}`` → 1 file WAV (+ header ``X-Speakers`` ghi khóa speaker→voice).
Engine lấy qua ``get_engine`` (xem ``hpvoice/api/helpers.py`` — quy ước DI
chung: ``app.state.engine``, fallback FakeEngine khi chưa gắn engine thật).
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from ..audio.conversation import ConversationEngine
from .helpers import error_response, get_engine, wav_response

router = APIRouter()


class ConversationLineIn(BaseModel):
    speaker: str
    text: str


class ConversationIn(BaseModel):
    lines: list[ConversationLineIn] = Field(min_length=1)
    speakers: dict[str, str] = Field(min_length=1)
    format: str = "wav"
    pause_s: float = 0.5


@router.post("/api/tts/conversation")
def create_conversation(body: ConversationIn, request: Request):
    """Hội thoại nhiều người nói → 1 file WAV (+ .srt theo speaker trong header)."""
    if body.format not in ("wav",):
        return error_response(
            400, "bad_format", f"format không hỗ trợ: {body.format!r} (v1 chỉ 'wav')."
        )
    engine = get_engine(request)
    try:
        result = ConversationEngine(engine, pause_between_turns_s=body.pause_s).synthesize(
            [{"speaker": ln.speaker, "text": ln.text} for ln in body.lines],
            body.speakers,
        )
    except ValueError as exc:
        return error_response(400, "bad_request", str(exc))
    except Exception as exc:  # noqa: BLE001 - lỗi engine -> 500 rõ ràng
        return error_response(500, "engine_error", f"Lỗi tạo hội thoại: {exc}")
    resp = wav_response(result.samples, result.sample_rate, "conversation.wav")
    resp.headers["X-Duration-Sec"] = f"{result.duration_s:.2f}"
    # Header HTTP chỉ chứa latin-1: quote tên speaker/giọng có dấu tiếng Việt.
    from urllib.parse import quote

    resp.headers["X-Speakers"] = quote(
        ",".join(f"{spk}={voice}" for spk, voice in result.voices_used.items()),
        safe="=,",
    )
    return resp
