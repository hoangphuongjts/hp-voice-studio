"""Route jobs (TK2.3) — endpoint 11 + tải kết quả + hủy job (SPEC §4).

- GET /api/jobs: liệt kê job (mới nhất trước, limit/offset).
- GET /api/jobs/{job_id}: trạng thái job {status, progress, result_url?, error?}.
- GET /api/jobs/{job_id}/result: tải file kết quả (audio WAV/MP3 hoặc ZIP).
- POST /api/jobs/{job_id}/cancel: hủy job chờ/chạy (dọn file tạm của job).
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

router = APIRouter()


def _state(request: Request):
    return request.app.state


@router.get("/api/jobs")
def list_jobs(request: Request, limit: int = 50, offset: int = 0):
    state = _state(request)
    jobs, total = state.queue.list_all(limit=limit, offset=offset)
    return {"items": [job.to_dict() for job in jobs], "total": total}


@router.get("/api/jobs/{job_id}")
def get_job(request: Request, job_id: str):
    job = _state(request).queue.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Không có job {job_id!r}.")
    return job.to_dict()


@router.get("/api/jobs/{job_id}/result")
def get_job_result(request: Request, job_id: str):
    state = _state(request)
    job = state.queue.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Không có job {job_id!r}.")
    if job.status != "done" or not job.result_path:
        raise HTTPException(
            status_code=409,
            detail=f"Job {job_id} chưa xong (trạng thái: {job.status}) — "
                   "hãy poll GET /api/jobs/{job_id} tới khi done rồi tải lại.",
        )
    path = Path(job.result_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"File kết quả của job {job_id} không còn trên đĩa.")
    media = job.result_media_type or "application/octet-stream"
    suffix = {"audio/wav": "wav", "audio/mpeg": "mp3",
              "application/zip": "zip"}.get(media, "bin")
    return Response(content=path.read_bytes(), media_type=media,
                    headers={"Content-Disposition":
                             f'attachment; filename="hp-voice-{job_id}.{suffix}"'})


@router.post("/api/jobs/{job_id}/cancel")
def cancel_job(request: Request, job_id: str):
    state = _state(request)
    job = state.queue.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Không có job {job_id!r}.")
    if job.status in ("done", "error", "cancelled"):
        raise HTTPException(
            status_code=409,
            detail=f"Job {job_id} đã kết thúc (trạng thái: {job.status}) nên không hủy được.",
        )
    state.queue.cancel(job_id)
    # Dọn file tạm của job ngay khi hủy (TH-33).
    tmp_job_dir = state.tmp_dir / job_id
    try:
        import shutil

        if tmp_job_dir.is_dir():
            shutil.rmtree(tmp_job_dir, ignore_errors=True)
    except OSError:
        pass
    status = "cancelled" if job.status == "cancelled" else "cancelling"
    return {"job_id": job_id, "status": status,
            "message": "Đã hủy job." if status == "cancelled"
                       else "Đã gửi lệnh hủy — job dừng sau chunk đang chạy."}
