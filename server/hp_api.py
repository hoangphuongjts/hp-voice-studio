#!/usr/bin/env python3
"""HP Voice Studio — API skeleton (T1).

Server HTTP local toi gian, FastAPI + uvicorn, goi truc tiep SDK vieneu
(VieNeu-TTS v3 Turbo, ONNX/CPU, fp32 mac dinh). KHONG dung code CIT, KHONG V4.

Endpoints:
  GET  /health            -> {status, engine, v3_ready, version}
  GET  /v1/voices         -> [{id, name}] (25 preset, doc tu SDK, khong hardcode)
  POST /v1/audio/speech   -> body {input, voice?, model?} tra WAV 48 kHz

Chay:  .venv/bin/python server/hp_api.py   (mac dinh 127.0.0.1:8124)
       hoac: HP_PORT=8124 .venv/bin/uvicorn server.hp_api:app --host 127.0.0.1 --port 8124
Chi bind loopback (quyet dinh 04:20 19/11: chi chay local, khong auth LAN).
"""
import os
import threading
import time
from io import BytesIO

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

HOST = os.environ.get("HP_HOST", "127.0.0.1")
PORT = int(os.environ.get("HP_PORT", "8124"))
VERSION = "0.1.0-t1"

app = FastAPI(title="HP Voice Studio API (T1 skeleton)", version=VERSION)

_tts = None
_tts_error = None
_lock = threading.Lock()
_started_at = time.time()


def _engine():
    global _tts, _tts_error
    if _tts is None and _tts_error is None:
        try:
            from vieneu import Vieneu

            _tts = Vieneu()  # v3turbo, ONNX/CPU, fp32 mac dinh
        except Exception as exc:  # noqa: BLE001 - ghi lai de /health bao loi
            _tts_error = str(exc)
    if _tts is None:
        raise HTTPException(status_code=503, detail=f"engine chua san sang: {_tts_error}")
    return _tts


class SpeechRequest(BaseModel):
    input: str = Field(..., min_length=1, max_length=20000)
    voice: str = "Hải Đăng"
    model: str = "v3turbo"


@app.get("/health")
def health():
    ready = _tts is not None
    return {
        "status": "ok" if ready else "starting",
        "engine": "v3",
        "v3_ready": ready,
        "v4_configured": False,
        "version": VERSION,
        "uptime_s": round(time.time() - _started_at, 1),
    }


@app.get("/v1/voices")
def voices():
    tts = _engine()
    return [{"id": vid, "name": label} for label, vid in tts.list_preset_voices()]


@app.post("/v1/audio/speech")
def speech(req: SpeechRequest):
    tts = _engine()
    if tts.resolve_voice_name(req.voice) is None:
        raise HTTPException(status_code=400, detail=f"voice khong ton tai: {req.voice}")
    with _lock:  # ONNX engine: tuan tu hoa inference cho an toan
        audio = tts.infer(req.input, voice=req.voice)
    buf = BytesIO()
    import soundfile as sf

    sf.write(buf, audio, tts.sample_rate, format="WAV")
    return Response(content=buf.getvalue(), media_type="audio/wav")


@app.on_event("startup")
def _startup():
    # Nap engine ngay khi khoi dong de /health bao ready som (tai model ~10s khi da cache).
    try:
        _engine()
    except HTTPException:
        pass


if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
