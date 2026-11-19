"""Route voices/health/preview (TK2.1/TK2.9) — endpoint 1, 2, 3, 19 (SPEC §4).

- GET /health: trạng thái server + engine (không nạp model — chỉ đọc cờ).
- GET /voices: preset + clone, kèm gender/region/style/engine (?engine=v3|v4).
- GET /v1/voices: tương thích OpenAI [{id, name}].
- GET /voices/{id}/preview: nghe thử giọng — lần 1 tổng hợp câu mẫu rồi cache
  trên đĩa (PreviewCache, TH-30), lần 2 trả từ cache (header X-Cache HIT/MISS).
"""
from __future__ import annotations

import time
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response

from hpvoice.audio.post import join_chunks
from hpvoice.audio.text_preprocess import TextPreprocess

router = APIRouter()


def _state(request: Request):
    return request.app.state


@router.get("/health")
def health(request: Request):
    state = _state(request)
    engine = state.engine
    ready = bool(getattr(engine, "is_loaded", False))
    return {
        "status": "ok" if ready else "starting",
        "engine": "v3",
        "v3_ready": ready,
        "v4_configured": bool(state.v4_configured()),
        "version": state.version,
        "uptime_s": round(time.time() - state.started_at, 1),
    }


def _voices_list(state, engine_name: str) -> list[dict]:
    """Danh sách giọng theo engine. v4 chưa có (TK2.2) -> 400 rõ ràng."""
    if engine_name == "v4":
        raise HTTPException(
            status_code=400,
            detail="Engine v4 (cloud) chưa có trong bản này (TK2.2) — "
                   "chỉ liệt kê được giọng v3 local.",
        )
    if engine_name not in ("v3", "", None):
        raise HTTPException(status_code=400, detail=f"Engine không hợp lệ: {engine_name!r}.")
    voices = []
    for voice in state.engine.list_preset_voices():
        voices.append({
            "id": voice.id,
            "name": voice.label or voice.id,
            "gender": getattr(voice, "gender", "") or "",
            "region": getattr(voice, "region", "") or "",
            "style": getattr(voice, "style", "") or "",
            "engine": "v3",
            "featured": getattr(voice, "featured", None),
        })
    if state.voice_store is not None:
        for voice in state.voice_store.list_clone_voices():
            voices.append({
                "id": voice.id,
                "name": voice.label or voice.id,
                "gender": getattr(voice, "gender", "") or "",
                "region": "",
                "style": getattr(voice, "style", "") or "",
                "engine": "v3",
                "featured": None,
                "is_clone": True,
            })
    return voices


@router.get("/voices")
def list_voices(request: Request, engine: str = "v3"):
    return _voices_list(_state(request), engine)


@router.get("/v1/voices")
def list_voices_openai(request: Request):
    state = _state(request)
    voices = state.engine.list_preset_voices()
    return [{"id": voice.id, "name": voice.label or voice.id} for voice in voices]


@router.get("/voices/{voice_id}/preview")
async def preview_voice(request: Request, voice_id: str):
    """Nghe thử giọng: câu mẫu từ config (<= 60 ký tự), cache theo voice_id."""
    import asyncio

    state = _state(request)
    resolved = state.engine.resolve_voice(voice_id)
    if resolved is None and not (state.voice_store and state.voice_store.resolve_voice(voice_id)):
        raise HTTPException(status_code=404, detail=f"Giọng không tồn tại: {voice_id!r}.")
    voice = resolved or voice_id
    try:
        sample = str(state.config.get("audio.preview_sample", "Xin chào."))
    except Exception:
        sample = "Xin chào."
    cache_key = f"preview:v3:{voice}:{sample}"
    cached = state.preview_cache.get(cache_key)
    if cached is not None:
        return Response(content=cached, media_type="audio/wav",
                        headers={"X-Cache": "HIT", "X-Engine": "v3"})
    # MISS: tổng hợp câu mẫu (chờ khóa CPU trong executor, không chặn loop).
    loop = asyncio.get_running_loop()
    acquired = await loop.run_in_executor(
        None, lambda: state.synthesis_lock.acquire(timeout=120))
    if not acquired:
        raise HTTPException(status_code=503, detail="CPU đang bận quá lâu, hãy thử lại sau.")
    try:
        def _make():
            split = TextPreprocess().split(sample)
            import numpy as np

            sr = int(getattr(state.engine, "sample_rate", 48000))
            parts = []
            for segment in split.segments:
                result = state.engine.synthesize(segment.text, voice)
                parts.append(np.asarray(result.samples, dtype=np.float32).reshape(-1))
            samples = join_chunks(parts, sr, [s.pause_after_s for s in split.segments[:-1]])
            from hpvoice.api.routes_tts import _wav_bytes

            return _wav_bytes(samples, sr)

        wav_bytes = await loop.run_in_executor(None, _make)
    finally:
        state.synthesis_lock.release()
    state.preview_cache.put(cache_key, wav_bytes)
    return Response(content=wav_bytes, media_type="audio/wav",
                    headers={"X-Cache": "MISS", "X-Engine": "v3"})


#: Hậu tố cần FFmpeg giải mã trước khi đo độ dài/clone (soundfile/libsndfile
#: không đọc được MP3/M4A/AAC — Y1).
_NEED_FFMPEG_DECODE = {".mp3", ".m4a", ".aac"}
#: Clip mẫu tối đa 8 s — 20 MB là giới hạn rộng rãi, chặn upload quá lớn.
_MAX_CLONE_UPLOAD_BYTES = 20 * 1024 * 1024


@router.post("/api/voices/clone", status_code=201)
async def clone_voice_route(
    request: Request,
    audio: UploadFile = File(...),
    name: str = Form(...),
    owner: str = Form(""),
    consent: bool = Form(False),
    consent_text: str = Form(""),
    gender: str = Form(""),
    description: str = Form(""),
):
    """Clone giọng từ clip mẫu 3–8 s (endpoint 10, TK3.2).

    Multipart: audio + name + owner + consent + consent_text (+ gender,
    description). MP3/M4A/AAC giải mã bằng FFmpeg trước (Y1). Mọi lỗi nghiệp
    vụ (thiếu cam kết, clip sai độ dài, tên trùng, file không đọc được)
    -> 400 với lý do rõ ràng, không tạo giọng.
    """
    from hpvoice.audio.ffmpeg_manager import FFmpegError
    from hpvoice.voices.store import VoiceStoreError, clip_duration_seconds

    state = _state(request)
    store = state.voice_store
    if store is None:
        raise HTTPException(
            status_code=503, detail="Kho giọng clone chưa khả dụng trên server này.")
    raw = await audio.read()
    if not raw:
        raise HTTPException(
            status_code=400,
            detail="File clip mẫu rỗng — hãy gửi file MP3/WAV/M4A có tiếng nói rõ.")
    if len(raw) > _MAX_CLONE_UPLOAD_BYTES:
        raise HTTPException(
            status_code=400, detail="File clip mẫu quá lớn (tối đa 20 MB cho clip 3–8 s).")
    suffix = Path(audio.filename or "").suffix.lower()
    tmp_in = state.tmp_dir / f"clone-{uuid.uuid4().hex}{suffix or '.wav'}"
    tmp_wav = state.tmp_dir / f"clone-{uuid.uuid4().hex}.wav"
    try:
        tmp_in.write_bytes(raw)
        wav_path = tmp_in
        if suffix in _NEED_FFMPEG_DECODE:
            try:
                wav_path = state.ffmpeg.decode_to_wav(tmp_in, tmp_wav)
            except FFmpegError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
        try:
            duration = clip_duration_seconds(wav_path)
        except VoiceStoreError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:  # noqa: BLE001 - file hỏng/libsndfile lỗi -> 400
            raise HTTPException(
                status_code=400,
                detail=f"Không đọc được clip mẫu — hãy gửi file WAV/MP3/M4A có tiếng nói rõ ({exc}).",
            ) from exc
        desc = description.strip() or (
            f"Chủ giọng: {owner.strip()}" if owner.strip() else "")
        try:
            info = store.clone_voice(
                name=name.strip(), ref_audio=wav_path, consent=bool(consent),
                consent_text=consent_text.strip(), description=desc,
                gender=gender.strip(),
            )
        except VoiceStoreError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:  # noqa: BLE001 - lỗi engine/SDK -> 500 rõ lý do
            raise HTTPException(
                status_code=500, detail=f"Không tạo được giọng clone: {exc}") from exc
        return {
            "id": info.id,
            "name": info.label or info.id,
            "gender": info.gender or "",
            "is_clone": True,
            "clip_seconds": round(duration, 2),
        }
    finally:
        for p in (tmp_in, tmp_wav):
            try:
                p.unlink(missing_ok=True)
            except OSError:
                pass


@router.delete("/api/voices/{voice_id}", status_code=204)
def delete_clone_voice(request: Request, voice_id: str, reason: str = Query("")):
    """Gỡ giọng clone khi có khiếu nại (TH-17) — bắt buộc ghi rõ lý do.

    Chỉ gỡ được giọng clone; giọng preset không xoá được (-> 404).
    """
    from hpvoice.voices.store import VoiceStoreError

    state = _state(request)
    store = state.voice_store
    if store is None:
        raise HTTPException(
            status_code=503, detail="Kho giọng clone chưa khả dụng trên server này.")
    if not (reason or "").strip():
        raise HTTPException(
            status_code=400, detail="Gỡ giọng cần ghi rõ lý do khiếu nại (?reason=...).")
    clone_ids = {v.id for v in store.list_clone_voices()}
    if voice_id not in clone_ids:
        raise HTTPException(
            status_code=404,
            detail=f'Không có giọng clone "{voice_id}" để gỡ (giọng preset không xoá được).',
        )
    try:
        store.takedown(voice_id, reason.strip())
    except VoiceStoreError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Response(status_code=204)
