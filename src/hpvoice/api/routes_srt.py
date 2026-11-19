"""Routes lồng tiếng .srt — POST /api/tts/srt-dub (TK2.5/TK2.13, SPEC §4 endpoint 8).

Multipart: file ``.srt``/``.vtt`` + ``voice_id`` (+ ``speed`` 0,75–1,5,
``voice_strict``) → ZIP (audio WAV + ``dub.srt`` đã chỉnh mốc + ``report.json``
danh sách câu bị lùi).
Engine lấy qua ``get_engine`` (xem ``hpvoice/api/helpers.py``).
"""

from __future__ import annotations

import io
import json
import tempfile
import zipfile
from pathlib import Path

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import Response

from ..audio.srt_dubber import SrtDubber, parse_subtitle_file
from .helpers import error_response, get_engine

router = APIRouter()


@router.post("/api/tts/srt-dub")
async def srt_dub(
    request: Request,
    file: UploadFile = File(...),
    voice_id: str = Form("Hải Đăng"),
    speed: float = Form(1.0),
    voice_strict: bool = Form(False),
):
    """Lồng tiếng theo file .srt/.vtt → ZIP (WAV + SRT chỉnh mốc + report)."""
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in (".srt", ".vtt"):
        return error_response(
            400, "bad_format", f"File phụ đề không hỗ trợ: {suffix!r} (chỉ .srt/.vtt)."
        )
    engine = get_engine(request)
    router_obj = getattr(request.app.state, "router", None)
    try:
        with tempfile.TemporaryDirectory(prefix="hp-srt-") as tmpdir:
            sub_path = Path(tmpdir) / f"sub{suffix}"
            sub_path.write_bytes(await file.read())
            cues = parse_subtitle_file(sub_path)
            dubber = SrtDubber(engine)
            wav_path = Path(tmpdir) / "dub.wav"
            result = dubber.dub(
                cues, voice_id, speed=speed, output_path=wav_path,
                router=router_obj, voice_strict=voice_strict,
            )
            report = {
                "cues": len(result.cues),
                "delayed": [
                    {
                        "index": c.index,
                        "scheduled_start_s": round(c.scheduled_start_s, 3),
                        "actual_start_s": round(c.actual_start_s, 3),
                        "shift_s": round(c.shift_s, 3),
                        "effective_rate": c.effective_rate,
                    }
                    for c in result.delayed
                ],
                "duration_s": round(result.duration_s, 3),
                "fallback": (
                    result.fallback_info.message if result.fallback_info else None
                ),
                "performance_note": result.performance_note,
            }
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(wav_path, arcname="dub.wav")
                zf.writestr("dub.srt", result.to_srt())
                zf.writestr("report.json", json.dumps(report, ensure_ascii=False, indent=2))
            zip_bytes = buf.getvalue()
    except ValueError as exc:
        return error_response(400, "bad_request", str(exc))
    except Exception as exc:  # noqa: BLE001
        return error_response(500, "engine_error", f"Lỗi lồng tiếng SRT: {exc}")
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="srt-dub.zip"'},
    )
