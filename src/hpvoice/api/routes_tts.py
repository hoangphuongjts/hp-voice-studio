"""Route TTS (TK2.1) — endpoint 4, 5, 18, 20 (SPEC §4).

- POST /api/tts/generate: CPU rảnh -> 200 + audio bytes (header X-Engine,
  X-Duration-Sec, X-Job-Id); CPU bận -> 202 + {job_id} để poll (endpoint 11).
- POST /api/tts/generate-with-subtitles: ZIP duy nhất (audio + .srt, Y11);
  text > 5.000 ký tự -> 202 + job_id (async, tránh timeout HTTP).
- POST /v1/audio/speech: tương thích OpenAI (để Annie/tool khác dùng SDK
  OpenAI trỏ base_url về HP); luôn chạy đồng bộ (chờ tới lượt CPU).
- GET /v1/models: [{id: "v3-turbo"}].

Mọi request TTS (cả đường sync 200) đều đi qua JobQueue: submit ->
mark_running -> chạy -> persist (ghi outputs/ + history + mark_done) — nhờ
vậy GET /api/jobs liệt kê đủ mọi job và đếm hàng đợi luôn đúng (T2.9).

Giới hạn (Y6): text tối đa 20.000 ký tự/request, vượt -> 400. Tốc độ
0,75×–1,5× qua AudioPost (TH-08). Thẻ [nghỉ] được TextPreprocess tách đoạn,
KHÔNG bao giờ đưa chuỗi "[nghỉ" vào infer().
"""
from __future__ import annotations

import asyncio
import io
import json
import uuid
import zipfile

import numpy as np
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel

from hpvoice.audio.post import (
    StretchUnavailableError,
    join_chunks,
    make_silence,
    time_stretch,
)
from hpvoice.audio.srt_writer import GAPS_TO_SILENCE, SrtWriter, chunk_text
from hpvoice.audio.text_preprocess import TextPreprocess, TextPreprocessError
from hpvoice.jobs.queue import QueueFullError

router = APIRouter()

#: Ngưỡng endpoint 5 chuyển async (SPEC §4, SUY LUẬN — chốt ở Bước 2).
SUBTITLES_ASYNC_CHARS = 5000


# --- Request model (không đặt max_length ở pydantic để lỗi trả 400, không 422) ---
class GenerateRequest(BaseModel):
    text: str = ""
    voice_id: str | None = None
    engine: str = "v3"
    speed: float = 1.0
    format: str = "wav"


class SpeechRequest(BaseModel):
    input: str = ""
    model: str = "v3-turbo"
    voice: str | None = None
    response_format: str = "mp3"
    speed: float = 1.0


# --- Helper dùng chung ---
def _state(request: Request):
    return request.app.state


def _max_text_chars(state) -> int:
    try:
        return int(state.config.get("api.max_text_chars", 20000))
    except Exception:
        return 20000


def _default_voice(state) -> str:
    try:
        return str(state.config.get("audio.default_voice", "Hải Đăng"))
    except Exception:
        return "Hải Đăng"


def _wav_bytes(samples: np.ndarray, sr: int) -> bytes:
    """Mã hoá mảng float32 thành WAV PCM 16-bit (BytesIO, không ghi đĩa)."""
    import soundfile as sf

    buf = io.BytesIO()
    sf.write(buf, np.asarray(samples, dtype=np.float32), sr, format="WAV",
             subtype="PCM_16")
    return buf.getvalue()


def _mp3_bytes(state, wav_bytes: bytes) -> bytes:
    """Mã hoá WAV -> MP3 qua FFmpegManager. Không có FFmpeg -> 400 rõ ràng."""
    tmp_dir = state.tmp_dir
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tag = uuid.uuid4().hex[:8]
    wav_path = tmp_dir / f"mp3-{tag}.wav"
    mp3_path = tmp_dir / f"mp3-{tag}.mp3"
    try:
        wav_path.write_bytes(wav_bytes)
        ok = state.ffmpeg.encode_mp3(wav_path, mp3_path)
        if not ok:
            raise HTTPException(
                status_code=400,
                detail="Không tìm thấy FFmpeg trên máy nên chỉ xuất được WAV; "
                       "muốn xuất MP3 hãy cài FFmpeg hệ thống hoặc để app tải "
                       "FFmpeg về lần đầu chạy (cần mạng). Audio WAV vẫn tạo "
                       "bình thường — hãy gọi lại với format=wav.",
            )
        return mp3_path.read_bytes()
    finally:
        for path in (wav_path, mp3_path):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass


def _encode_audio(state, samples: np.ndarray, sr: int, fmt: str) -> tuple[bytes, str]:
    """Mã hoá audio theo format. Trả (bytes, media_type)."""
    wav = _wav_bytes(samples, sr)
    if fmt == "wav":
        return wav, "audio/wav"
    if fmt == "mp3":
        return _mp3_bytes(state, wav), "audio/mpeg"
    raise HTTPException(status_code=400, detail=f"Định dạng không hỗ trợ: {fmt!r} (chỉ wav/mp3).")


def _validate_tts(state, text: str, voice_id: str | None, engine_name: str,
                  speed: float, fmt: str) -> str:
    """Kiểm tra đầu vào chung, ném HTTPException 400 khi sai. Trả voice đã resolve."""
    max_chars = _max_text_chars(state)
    if text is None or not str(text).strip():
        raise HTTPException(status_code=400, detail="Text rỗng — không có gì để tạo giọng.")
    text = str(text)
    if len(text) > max_chars:
        raise HTTPException(
            status_code=400,
            detail=f"Text dài {len(text)} ký tự, vượt giới hạn {max_chars} ký tự/request "
                   "(SPEC §4) — hãy chia nhỏ text rồi gửi lại.",
        )
    if engine_name not in ("v3", "v3-turbo", "v3turbo"):
        raise HTTPException(
            status_code=400,
            detail=f"Engine {engine_name!r} chưa hỗ trợ ở bản này (TK2.2 — V4 cloud "
                   "chưa có trong TK2.1). Chỉ dùng được engine v3 local.",
        )
    if speed < 0.75 or speed > 1.5:
        raise HTTPException(
            status_code=400,
            detail=f"Tốc độ phải trong khoảng 0,75×–1,5×, nhận {speed}×.",
        )
    if fmt not in ("wav", "mp3"):
        raise HTTPException(status_code=400, detail=f"Định dạng không hỗ trợ: {fmt!r} (chỉ wav/mp3).")
    voice = voice_id or _default_voice(state)
    resolved = state.engine.resolve_voice(voice)
    if resolved is None:
        raise HTTPException(status_code=400, detail=f"Giọng không tồn tại: {voice!r}.")
    if fmt == "mp3" and not state.ffmpeg.available():
        raise HTTPException(
            status_code=400,
            detail="Không tìm thấy FFmpeg trên máy nên chỉ xuất được WAV; "
                   "muốn xuất MP3 hãy cài FFmpeg hệ thống hoặc để app tải "
                   "FFmpeg về lần đầu chạy (cần mạng).",
        )
    return resolved


def _synthesize_audio(state, text: str, voice: str, speed: float) -> tuple[np.ndarray, int]:
    """Tổng hợp text -> (samples, sr), đã xử lý [nghỉ] + tốc độ.

    - TextPreprocess tách thẻ [nghỉ] thành đoạn + khoảng lặng; mỗi đoạn gọi
      engine.synthesize riêng; nối bằng AudioPost.join_chunks.
    - Tốc độ != 1× qua time_stretch giữ cao độ; 1× không stretch (T2.4).
    """
    try:
        split = TextPreprocess().split(text)
    except TextPreprocessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not split.segments:
        raise HTTPException(status_code=400, detail="Text rỗng — không có gì để tạo giọng.")
    sr = int(getattr(state.engine, "sample_rate", 48000))
    parts: list[np.ndarray] = []
    pauses: list[float] = []
    if split.leading_pause_s > 0:
        parts.append(make_silence(split.leading_pause_s, sr))
    for index, segment in enumerate(split.segments):
        result = state.engine.synthesize(segment.text, voice)
        parts.append(np.asarray(result.samples, dtype=np.float32).reshape(-1))
        if index < len(split.segments) - 1:
            pauses.append(segment.pause_after_s)
    # Khoảng lặng sau đoạn cuối không nối thêm đoạn nào thì bỏ (không kéo dài đuôi).
    samples = join_chunks(parts, sr, pauses) if len(parts) > 1 else parts[0]
    if speed != 1.0:
        try:
            samples, _ = time_stretch(samples, sr, float(speed))
        except StretchUnavailableError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return np.asarray(samples, dtype=np.float32), sr


def _synthesize_with_subtitles(state, text: str, voice: str,
                               speed: float) -> tuple[np.ndarray, int, str]:
    """Tổng hợp + suy mốc .srt (endpoint 5): trả (samples, sr, srt_text).

    Chia text đúng như SDK chia (chunk_text <= 256 ký tự), infer từng chunk,
    đo độ dài thật từng chunk rồi SrtWriter suy mốc từng câu.
    Text chứa thẻ [nghỉ] -> 400 (endpoint này chưa hỗ trợ thẻ nghỉ, dùng
    /api/tts/generate cho text có [nghỉ]).
    """
    if "[nghỉ" in text or "[Nghỉ" in text:
        raise HTTPException(
            status_code=400,
            detail="Endpoint generate-with-subtitles chưa hỗ trợ thẻ [nghỉ ...] — "
                   "hãy dùng /api/tts/generate cho text có thẻ nghỉ.",
        )
    chunks, gaps = chunk_text(text)
    if not chunks:
        raise HTTPException(status_code=400, detail="Text rỗng — không có gì để tạo giọng.")
    sr = int(getattr(state.engine, "sample_rate", 48000))
    chunk_audios: list[np.ndarray] = []
    for chunk in chunks:
        result = state.engine.synthesize(chunk, voice)
        chunk_audios.append(np.asarray(result.samples, dtype=np.float32).reshape(-1))
    pauses = [GAPS_TO_SILENCE.get(gap, 0.50) for gap in gaps]
    samples = join_chunks(chunk_audios, sr, pauses)
    if speed != 1.0:
        try:
            samples, _ = time_stretch(samples, sr, float(speed))
        except StretchUnavailableError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    cues = SrtWriter(sr=sr).build_cues(text, chunk_audios)
    srt_text = SrtWriter(sr=sr).to_srt(cues)
    return np.asarray(samples, dtype=np.float32), sr, srt_text


def _zip_bytes(audio_bytes: bytes, srt_text: str) -> bytes:
    """Đóng gói ZIP duy nhất (audio.wav + subtitles.srt) cho endpoint 5 (Y11)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("audio.wav", audio_bytes)
        zf.writestr("subtitles.srt", srt_text.encode("utf-8"))
    return buf.getvalue()


def synthesize_tts_payload(state, payload: dict) -> dict:
    """Chạy 1 payload TTS (dùng chung đường sync + job nền).

    Trả dict kết quả chuẩn cho runner/persist: result_bytes/result_format/
    result_media_type/duration_s + history_audio_bytes/history_srt_text +
    metadata (text_preview/voice_id/engine/speed).
    """
    text = payload["text"]
    voice = payload["voice_id"]
    speed = float(payload.get("speed", 1.0))
    fmt = payload.get("format", "wav")
    with_subtitles = bool(payload.get("with_subtitles", False))
    if with_subtitles:
        samples, sr, srt_text = _synthesize_with_subtitles(state, text, voice, speed)
        wav_bytes = _wav_bytes(samples, sr)
        return {
            "result_bytes": _zip_bytes(wav_bytes, srt_text),
            "result_format": "zip",
            "result_media_type": "application/zip",
            "duration_s": len(samples) / sr,
            "history_audio_bytes": wav_bytes,
            "history_srt_text": srt_text,
            "text_preview": text[:200],
            "voice_id": voice,
            "engine": "v3",
            "speed": speed,
        }
    samples, sr = _synthesize_audio(state, text, voice, speed)
    audio_bytes, media_type = _encode_audio(state, samples, sr, fmt)
    return {
        "result_bytes": audio_bytes,
        "result_format": fmt,
        "result_media_type": media_type,
        "duration_s": len(samples) / sr,
        "history_audio_bytes": audio_bytes if fmt in ("wav", "mp3") else None,
        "history_srt_text": None,
        "text_preview": text[:200],
        "voice_id": voice,
        "engine": "v3",
        "speed": speed,
    }


def run_tts_job(state, job) -> dict:
    """Hàm chạy job TTS trong runner (server.py gọi). Kiểm tra cờ hủy trước
    khi chạy; hủy giữa chừng do worker kiểm tra giữa các chunk (TK1.8)."""
    from hpvoice.jobs.worker import CancelledError

    if job.cancel_event.is_set():
        raise CancelledError(f"Job {job.id} đã hủy khi đang chờ.")
    return synthesize_tts_payload(state, job.payload)


# --- Vòng đời job cho đường sync ---
def _submit_job(state, payload: dict):
    """Nộp job vào hàng đợi (quét hết TTL trước). Đầy -> 429."""
    state.queue.sweep_expired()
    try:
        return state.queue.submit(kind="tts", payload=payload, run_fn=run_tts_job)
    except QueueFullError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc


async def _run_in_worker(fn):
    """Chạy hàm đồng bộ trong executor mặc định (không chặn event loop, TH-19)."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, fn)


def _finalize_sync(state, job, result: dict) -> None:
    """Ghi kết quả job sync ra outputs/ + history + mark_done (dùng chung
    hàm persist của runner trong server.py)."""
    from hpvoice.api.server import _persist_job_result

    _persist_job_result(state, job, result)


def _audio_response(state, job, result: dict) -> Response:
    """Response audio/ZIP cho đường sync, kèm header X-Engine/X-Duration-Sec/
    X-Job-Id/X-History-Id (và X-History-Warning nếu history đầy)."""
    headers = {
        "X-Engine": "v3",
        "X-Duration-Sec": f"{result['duration_s']:.3f}",
        "X-Job-Id": job.id,
    }
    if job.history_id:
        headers["X-History-Id"] = job.history_id
    if job.history_warning:
        headers["X-History-Warning"] = job.history_warning
    return Response(content=result["result_bytes"],
                    media_type=result["result_media_type"], headers=headers)


def _queued_response(job, message: str) -> Response:
    return Response(
        content=json.dumps({"job_id": job.id, "status": "queued",
                            "message": message}, ensure_ascii=False).encode("utf-8"),
        status_code=202, media_type="application/json",
    )


def _cpu_idle(state) -> bool:
    """CPU có rảnh không: không job đang chạy/chờ nào."""
    return (state.queue.waiting_count() == 0
            and state.queue.running_job() is None)


# --- Endpoint 4: POST /api/tts/generate ---
@router.post("/api/tts/generate")
async def generate(request: Request, body: GenerateRequest):
    state = _state(request)
    fmt = (body.format or "wav").lower()
    voice = _validate_tts(state, body.text, body.voice_id, body.engine,
                          body.speed, fmt)
    payload = {"text": body.text, "voice_id": voice, "engine": "v3",
               "speed": float(body.speed), "format": fmt, "with_subtitles": False}
    if _cpu_idle(state) and state.synthesis_lock.acquire(blocking=False):
        job = None
        try:
            # Chiếm được khóa + hàng đợi đang trống: kiểm tra lại một lần
            # (request khác có thể đã xếp hàng trong lúc chờ khóa).
            if not _cpu_idle(state):
                job = _submit_job(state, payload)
                return _queued_response(
                    job, "CPU đang bận — job đã xếp hàng, poll "
                         f"GET /api/jobs/{job.id} để lấy kết quả.")
            job = _submit_job(state, payload)
            state.queue.mark_running(job.id)
            result = await _run_in_worker(lambda: synthesize_tts_payload(state, payload))
        except HTTPException as exc:
            # Lỗi validate/tổng hợp sau khi đã mark_running: ghi job error.
            # (Nếu job chưa tạo được — VD hàng đợi đầy -> 429 — thì cứ để
            # lỗi gốc đi qua, không ghi job.)
            if job is not None:
                state.queue.mark_error(job.id, str(exc.status_code), str(exc.detail))
            raise
        except Exception as exc:  # noqa: BLE001
            if job is not None:
                state.queue.mark_error(job.id, "job_error", str(exc))
            raise HTTPException(status_code=500, detail=f"Lỗi tổng hợp: {exc}") from exc
        finally:
            state.synthesis_lock.release()
        _finalize_sync(state, job, result)
        return _audio_response(state, job, result)
    # CPU bận -> xếp hàng, trả 202 + job_id (SPEC §4).
    job = _submit_job(state, payload)
    return _queued_response(
        job, "CPU đang bận — job đã xếp hàng, poll "
             f"GET /api/jobs/{job.id} để lấy kết quả.")


# --- Endpoint 5: POST /api/tts/generate-with-subtitles ---
@router.post("/api/tts/generate-with-subtitles")
async def generate_with_subtitles(request: Request, body: GenerateRequest):
    state = _state(request)
    fmt = (body.format or "wav").lower()
    if fmt != "wav":
        raise HTTPException(
            status_code=400,
            detail="generate-with-subtitles chỉ xuất audio WAV trong ZIP "
                   "(MP3 kèm SRT chưa hỗ trợ ở bản này).",
        )
    voice = _validate_tts(state, body.text, body.voice_id, body.engine,
                          body.speed, fmt)
    payload = {"text": body.text, "voice_id": voice, "engine": "v3",
               "speed": float(body.speed), "format": "wav", "with_subtitles": True}
    # Text > 5.000 ký tự -> async ngay (tránh timeout HTTP khi tạo ZIP dài).
    if len(body.text) > SUBTITLES_ASYNC_CHARS:
        job = _submit_job(state, payload)
        return _queued_response(
            job, "Text dài — job chạy nền, poll "
                 f"GET /api/jobs/{job.id} để lấy file ZIP.")
    if _cpu_idle(state) and state.synthesis_lock.acquire(blocking=False):
        job = None
        try:
            if not _cpu_idle(state):
                job = _submit_job(state, payload)
                return _queued_response(
                    job, "CPU đang bận — job đã xếp hàng, poll "
                         f"GET /api/jobs/{job.id} để lấy file ZIP.")
            job = _submit_job(state, payload)
            state.queue.mark_running(job.id)
            result = await _run_in_worker(lambda: synthesize_tts_payload(state, payload))
        except HTTPException as exc:
            if job is not None:
                state.queue.mark_error(job.id, str(exc.status_code), str(exc.detail))
            raise
        except Exception as exc:  # noqa: BLE001
            if job is not None:
                state.queue.mark_error(job.id, "job_error", str(exc))
            raise HTTPException(status_code=500, detail=f"Lỗi tổng hợp: {exc}") from exc
        finally:
            state.synthesis_lock.release()
        _finalize_sync(state, job, result)
        return _audio_response(state, job, result)
    job = _submit_job(state, payload)
    return _queued_response(
        job, "CPU đang bận — job đã xếp hàng, poll "
             f"GET /api/jobs/{job.id} để lấy file ZIP.")


# --- Endpoint 18: POST /v1/audio/speech (tương thích OpenAI) ---
@router.post("/v1/audio/speech")
async def speech_openai(request: Request, body: SpeechRequest):
    state = _state(request)
    fmt = (body.response_format or "mp3").lower()
    voice = _validate_tts(state, body.input, body.voice, body.model,
                          body.speed, fmt)
    payload = {"text": body.input, "voice_id": voice, "engine": "v3",
               "speed": float(body.speed), "format": fmt, "with_subtitles": False}
    job = _submit_job(state, payload)
    state.queue.mark_running(job.id)
    # OpenAI SDK chờ audio đồng bộ nên endpoint này chờ tới lượt CPU
    # (không trả 202 — SDK không hiểu job_id). Chờ khóa trong executor để
    # không chặn event loop (TH-19).
    acquired = await _run_in_worker(lambda: state.synthesis_lock.acquire(timeout=300))
    if not acquired:
        state.queue.mark_error(job.id, "busy_timeout", "CPU đang bận quá lâu, hãy thử lại sau.")
        raise HTTPException(status_code=503, detail="CPU đang bận quá lâu, hãy thử lại sau.")
    try:
        result = await _run_in_worker(lambda: synthesize_tts_payload(state, payload))
    except HTTPException as exc:
        state.queue.mark_error(job.id, str(exc.status_code), str(exc.detail))
        raise
    except Exception as exc:  # noqa: BLE001
        state.queue.mark_error(job.id, "job_error", str(exc))
        raise HTTPException(status_code=500, detail=f"Lỗi tổng hợp: {exc}") from exc
    finally:
        state.synthesis_lock.release()
    _finalize_sync(state, job, result)
    return _audio_response(state, job, result)


# --- Endpoint 20: GET /v1/models ---
@router.get("/v1/models")
def list_models():
    return {"object": "list", "data": [
        {"id": "v3-turbo", "object": "model", "created": 0, "owned_by": "hp-voice-studio"},
    ]}
