"""Helper chung cho các routes TK2 (không thuộc về riêng route nào).

Quy ước dependency injection (để coordinator hợp nhất với agent API-CORE):
- Mỗi routes file lấy engine qua ``get_engine(request)``: đọc
  ``request.app.state.engine`` nếu server đã gắn engine thật (V3/V4/Router);
  chưa có thì dùng :class:`FakeEngine` (tạo WAV tổng hợp — chỉ để test/dev,
  KHÔNG phải giọng thật).
- Lỗi trả JSON ``{"error": {"code", "message"}}`` theo SPEC §4.
"""

from __future__ import annotations

import io

import numpy as np
from fastapi import Request
from fastapi.responses import JSONResponse, Response

from ..engines.fake import FakeEngine

__all__ = ["error_response", "get_engine", "wav_response"]


def get_engine(request: Request):
    """Engine cho route: ``app.state.engine`` nếu có, ngược lại FakeEngine."""
    engine = getattr(request.app.state, "engine", None)
    if engine is None:
        engine = FakeEngine()
        request.app.state.engine = engine
    return engine


def wav_response(samples: np.ndarray, sr: int, filename: str = "audio.wav") -> Response:
    """Response WAV bytes (PCM 16-bit) từ mảng numpy."""
    import soundfile as sf

    buf = io.BytesIO()
    sf.write(buf, np.asarray(samples, dtype=np.float32), sr, format="WAV", subtype="PCM_16")
    return Response(
        content=buf.getvalue(),
        media_type="audio/wav",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def error_response(status: int, code: str, message: str) -> JSONResponse:
    """Response lỗi chuẩn SPEC §4: ``{"error": {"code", "message"}}``."""
    return JSONResponse(
        status_code=status, content={"error": {"code": code, "message": message}}
    )
