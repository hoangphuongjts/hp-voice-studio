"""Route history (TK2.3) — endpoint 12, 13, 14 (SPEC §4).

- GET /api/history?limit&offset: danh sách bản đã tạo + tổng dung lượng
  (đối chiếu được bằng `du`).
- GET /api/history/{id}: tải lại audio của 1 bản.
- DELETE /api/history/{id}: xoá 1 bản (khỏi index + xoá file đĩa) -> 204.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

router = APIRouter()


def _state(request: Request):
    return request.app.state


@router.get("/api/history")
def list_history(request: Request, limit: int = 50, offset: int = 0):
    state = _state(request)
    items, total = state.history.list_items(limit=limit, offset=offset)
    return {
        "items": items,
        "total": total,
        "total_bytes": state.history.total_bytes,
        "max_history_gb": state.history.max_history_gb,
    }


@router.get("/api/history/{item_id}")
def get_history_item(request: Request, item_id: str):
    state = _state(request)
    item = state.history.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Không có bản đã tạo {item_id!r}.")
    path = state.history.history_dir / item["audio_path"]
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"File audio của bản {item_id} không còn trên đĩa.")
    media = {"wav": "audio/wav", "mp3": "audio/mpeg"}.get(item["format"], "audio/wav")
    return Response(content=path.read_bytes(), media_type=media,
                    headers={"Content-Disposition":
                             f'attachment; filename="hp-voice-{item_id}.{item["format"]}"'})


@router.delete("/api/history/{item_id}", status_code=204)
def delete_history_item(request: Request, item_id: str):
    state = _state(request)
    if not state.history.delete(item_id):
        raise HTTPException(status_code=404, detail=f"Không có bản đã tạo {item_id!r}.")
    return Response(status_code=204)
