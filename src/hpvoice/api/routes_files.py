"""Routes đọc file — POST /api/files/read (TK2.7/TK2.12, SPEC §4/T3.4).

Multipart: file ``.pdf``/``.docx``/``.txt`` → JSON ``{text, kind, pages,
warnings, copyright_note, chars, read_seconds}``.
PDF scan → 400 + thông báo rõ ``"v1 không OCR"`` (không bịa text).
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, UploadFile

from ..files.readers import FileReaders, ScannedPdfError
from .helpers import error_response

router = APIRouter()


@router.post("/api/files/read")
async def read_file(file: UploadFile = File(...)):
    """Đọc file PDF/DOCX/TXT → text đã làm sạch (kèm ghi chú bản quyền)."""
    import tempfile

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in (".pdf", ".docx", ".txt"):
        return error_response(
            400, "bad_format", f"File không hỗ trợ: {suffix!r} (chỉ .pdf/.docx/.txt)."
        )
    try:
        with tempfile.TemporaryDirectory(prefix="hp-read-") as tmpdir:
            tmp_path = Path(tmpdir) / f"upload{suffix}"
            tmp_path.write_bytes(await file.read())
            result = FileReaders().read_file(tmp_path)
    except ScannedPdfError as exc:
        return error_response(400, "scanned_pdf_no_ocr", str(exc))
    except ValueError as exc:
        return error_response(400, "bad_request", str(exc))
    except Exception as exc:  # noqa: BLE001
        return error_response(500, "read_error", f"Lỗi đọc file: {exc}")
    return {
        "text": result.text,
        "kind": result.kind,
        "pages": result.pages,
        "chars": result.chars,
        "warnings": result.warnings,
        "copyright_note": result.copyright_note,
        "read_seconds": round(result.read_seconds, 3),
    }
