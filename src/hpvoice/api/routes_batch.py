"""Routes tạo hàng loạt — POST /api/tts/batch (TK2.6, SPEC §4 endpoint 9).

- JSON: ``{items: [{id, text, voice_id?}], format}`` → chạy batch → ZIP.
- Multipart: file ``.txt`` (mốc ``[P1]``) / ``.json`` / ``.srt`` / ``.vtt``.
- Trả ZIP (các WAV đã xong + manifest). Mục lỗi chỉ ghi vào manifest, không
  chết batch. Giới hạn 500 mục/lần (số tạm chờ đo RAM — TK2.6).
Engine lấy qua ``get_engine`` (xem ``hpvoice/api/helpers.py``).
"""

from __future__ import annotations

import io
import tempfile
import zipfile
from pathlib import Path

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from ..jobs.batch import BatchRunner, MAX_BATCH_ITEMS
from .helpers import error_response, get_engine

router = APIRouter()


class BatchItemIn(BaseModel):
    id: str = ""
    text: str = ""
    voice_id: str = ""


class BatchIn(BaseModel):
    items: list[BatchItemIn] = Field(min_length=1)
    format: str = "wav"


def _zip_response(zip_bytes: bytes) -> Response:
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="batch.zip"'},
    )


def _run_to_zip(engine, items, tmpdir: str) -> bytes:
    """Chạy batch trong thư mục tạm rồi đóng ZIP bytes (xóa file tạm sau đó)."""
    runner = BatchRunner(engine, output_dir=tmpdir)
    result = runner.run(items)
    zip_path = runner.export_zip(result)
    return Path(zip_path).read_bytes(), result


@router.post("/api/tts/batch")
def create_batch(body: BatchIn, request: Request):
    """Tạo hàng loạt từ JSON → ZIP."""
    if len(body.items) > MAX_BATCH_ITEMS:
        return error_response(
            400,
            "batch_too_large",
            f"Batch tối đa {MAX_BATCH_ITEMS} mục/lần, nhận {len(body.items)} mục.",
        )
    engine = get_engine(request)
    items = [
        {"id": it.id or f"P{i + 1}", "text": it.text, "voice_id": it.voice_id}
        for i, it in enumerate(body.items)
    ]
    try:
        with tempfile.TemporaryDirectory(prefix="hp-batch-") as tmpdir:
            zip_bytes, _result = _run_to_zip(engine, items, tmpdir)
    except ValueError as exc:
        return error_response(400, "bad_request", str(exc))
    except Exception as exc:  # noqa: BLE001
        return error_response(500, "engine_error", f"Lỗi tạo hàng loạt: {exc}")
    return _zip_response(zip_bytes)


@router.post("/api/tts/batch/upload")
async def create_batch_upload(request: Request, file: UploadFile = File(...)):
    """Tạo hàng loạt từ file upload (.txt/.json/.srt/.vtt) → ZIP."""
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in (".txt", ".json", ".srt", ".vtt"):
        return error_response(
            400, "bad_format", f"File batch không hỗ trợ: {suffix!r} (chỉ .txt/.json/.srt/.vtt)."
        )
    engine = get_engine(request)
    try:
        with tempfile.TemporaryDirectory(prefix="hp-batch-") as tmpdir:
            up_path = Path(tmpdir) / f"upload{suffix}"
            up_path.write_bytes(await file.read())
            zip_bytes, _result = _run_to_zip(engine, up_path, tmpdir)
    except ValueError as exc:
        return error_response(400, "bad_request", str(exc))
    except Exception as exc:  # noqa: BLE001
        return error_response(500, "engine_error", f"Lỗi tạo hàng loạt: {exc}")
    return _zip_response(zip_bytes)
