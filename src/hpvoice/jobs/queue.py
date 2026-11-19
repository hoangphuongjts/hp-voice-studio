"""JobQueue — hàng đợi job TTS (TK2.3, SPEC §3.3/§4, Q16 đã chốt).

- 1 job chạy, tối đa 20 job chờ (``max_waiting`` từ config ``api.max_queue_jobs``);
  đầy -> :class:`QueueFullError` (API map thành 429).
- TTL 60 phút (``ttl_seconds`` mặc định 3600): job CHỜ quá TTL thì
  :meth:`JobQueue.sweep_expired` hủy + ghi rõ "hết thời gian chờ, gửi lại".
  Job đang chạy không bị TTL chờ hủy.
- Trạng thái: queued -> running -> done | error | cancelled.
- Hủy: job chờ -> cancelled ngay; job chạy -> đặt cờ ``cancel_event`` để
  worker kiểm tra giữa các chunk (TH-19/TK1.8).
- ``run_fn``: callable ``run_fn(state, job) -> dict`` do route đăng ký khi
  submit (mỗi loại job — tts, batch, srt, dialogue — có hàm chạy riêng);
  JobQueue không biết nội dung job, chỉ quản lý vòng đời.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

__all__ = [
    "DEFAULT_MAX_WAITING",
    "DEFAULT_TTL_SECONDS",
    "Job",
    "JobQueue",
    "QueueFullError",
    "check_batch_size",
]

#: Q16 (anh chốt 04:32 19/11): 1 chạy, tối đa 20 chờ, TTL 60 phút.
DEFAULT_MAX_WAITING = 20
DEFAULT_TTL_SECONDS = 3600

#: Giới hạn batch (SPEC §4, số tạm chờ đo RAM ở TK2.6).
DEFAULT_MAX_BATCH_ITEMS = 500


class QueueFullError(RuntimeError):
    """Hàng đợi đã đầy (20 job chờ) — API trả 429."""


def check_batch_size(n_items: int, limit: int = DEFAULT_MAX_BATCH_ITEMS) -> None:
    """Kiểm tra số mục batch (SPEC §4: tối đa 500 mục/lần).

    Ném ``ValueError`` rõ giới hạn khi vượt. Hàm dùng chung cho
    ``routes_batch.py`` (TK2-FEATURES) để HTTP 400 đúng một chỗ.
    """
    if n_items > limit:
        raise ValueError(
            f"Batch có {n_items} mục, vượt giới hạn {limit} mục/lần "
            "(SPEC §4) — hãy chia nhỏ batch rồi gửi lại."
        )
    if n_items <= 0:
        raise ValueError("Batch phải có ít nhất 1 mục.")


@dataclass
class Job:
    """Một job trong hàng đợi (mô hình dữ liệu §8 SPEC)."""

    id: str
    kind: str  # tts | conversation | srt | batch | clone
    status: str = "queued"  # queued | running | done | error | cancelled
    progress: float = 0.0
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0.0  # created_at + TTL (chỉ áp cho job chờ)
    started_at: float | None = None
    finished_at: float | None = None
    result_path: str | None = None
    result_format: str | None = None  # wav | mp3 | zip
    result_media_type: str | None = None
    duration_s: float | None = None
    size_bytes: int | None = None
    error_code: str | None = None
    error_message: str | None = None
    history_id: str | None = None  # id bản history (nếu đã lưu)
    history_warning: str | None = None  # VD history đầy nên không lưu được
    cancel_event: threading.Event = field(default_factory=threading.Event, repr=False)
    run_fn: Callable | None = field(default=None, repr=False)

    def to_dict(self) -> dict[str, Any]:
        """Dạng JSON trả qua GET /api/jobs/{id} (endpoint 11, SPEC §4)."""
        data: dict[str, Any] = {
            "id": self.id,
            "job_id": self.id,
            "kind": self.kind,
            "status": self.status,
            "progress": round(self.progress, 3),
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_s": self.duration_s,
            "size_bytes": self.size_bytes,
            "error_code": self.error_code,
            "error": self.error_message,
            "error_message": self.error_message,
            "history_id": self.history_id,
        }
        if self.status == "done" and self.result_path:
            data["result_url"] = f"/api/jobs/{self.id}/result"
        if self.history_warning:
            data["history_warning"] = self.history_warning
        return data


class JobQueue:
    """Hàng đợi tuần tự, an toàn luồng (1 job chạy, tối đa N job chờ)."""

    def __init__(self, max_waiting: int = DEFAULT_MAX_WAITING,
                 ttl_seconds: int = DEFAULT_TTL_SECONDS):
        self.max_waiting = int(max_waiting)
        self.ttl_seconds = float(ttl_seconds)  # giữ float — int(0.2) = 0 sẽ hết hạn ngay
        self._jobs: dict[str, Job] = {}
        self._order: list[str] = []  # thứ tự submit (FIFO)
        self._lock = threading.Lock()

    # --- Nộp / lấy ---
    def submit(self, kind: str, payload: dict[str, Any] | None = None,
               run_fn: Callable | None = None) -> Job:
        """Nộp job mới vào cuối hàng đợi. Đầy -> QueueFullError (API: 429)."""
        with self._lock:
            if self._waiting_count_locked() >= self.max_waiting:
                raise QueueFullError(
                    f"Hàng đợi đã đầy ({self.max_waiting} job đang chờ, "
                    f"TTL {int(self.ttl_seconds // 60)} phút/job) — hãy chờ job "
                    "đang chạy xong rồi gửi lại, không gửi dồn."
                )
            now = time.time()
            job = Job(
                id=uuid.uuid4().hex[:12],
                kind=kind,
                payload=dict(payload or {}),
                created_at=now,
                expires_at=now + self.ttl_seconds,
                run_fn=run_fn,
            )
            self._jobs[job.id] = job
            self._order.append(job.id)
            return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list_all(self, limit: int = 100, offset: int = 0) -> tuple[list[Job], int]:
        """Tất cả job, mới nhất trước (để GET /api/jobs)."""
        with self._lock:
            jobs = [self._jobs[jid] for jid in reversed(self._order)]
        total = len(jobs)
        return jobs[offset:offset + limit], total

    # --- Đếm / trạng thái ---
    def _waiting_count_locked(self) -> int:
        return sum(1 for j in self._jobs.values() if j.status == "queued")

    def waiting_count(self) -> int:
        with self._lock:
            return self._waiting_count_locked()

    def running_job(self) -> Job | None:
        with self._lock:
            for jid in self._order:
                job = self._jobs[jid]
                if job.status == "running":
                    return job
        return None

    def has_capacity(self) -> bool:
        """Còn suất chờ không (để route quyết định 202 hay 429)."""
        return self.waiting_count() < self.max_waiting

    # --- Chuyển trạng thái ---
    def peek_next(self) -> Job | None:
        """Job chờ đầu tiên (FIFO) mà KHÔNG đổi trạng thái.

        Runner dùng peek trước khi chiếm khóa tổng hợp, chỉ mark_running
        SAU KHI đã có khóa — nếu không job bị đánh "running" trong lúc vẫn
        đang chờ CPU, vừa sai đếm hàng đợi (job chờ không đầy 20) vừa sai
        trạng thái hiển thị.
        """
        with self._lock:
            for jid in self._order:
                job = self._jobs[jid]
                if job.status == "queued":
                    return job
        return None

    def take_next(self) -> Job | None:
        """Lấy job chờ đầu tiên (FIFO) và chuyển sang running. Hết -> None."""
        with self._lock:
            for jid in self._order:
                job = self._jobs[jid]
                if job.status == "queued":
                    job.status = "running"
                    job.started_at = time.time()
                    return job
        return None

    def mark_running(self, job_id: str) -> Job | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is not None and job.status == "queued":
                job.status = "running"
                job.started_at = time.time()
            return job

    def update_progress(self, job_id: str, progress: float) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is not None:
                job.progress = max(0.0, min(1.0, float(progress)))

    def mark_done(self, job_id: str, result_path: str | None = None,
                  result_format: str | None = None,
                  result_media_type: str | None = None,
                  duration_s: float | None = None,
                  size_bytes: int | None = None,
                  history_id: str | None = None,
                  history_warning: str | None = None) -> Job | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            job.status = "done"
            job.progress = 1.0
            job.finished_at = time.time()
            job.result_path = result_path
            job.result_format = result_format
            job.result_media_type = result_media_type
            job.duration_s = duration_s
            job.size_bytes = size_bytes
            job.history_id = history_id
            job.history_warning = history_warning
            return job

    def mark_error(self, job_id: str, code: str, message: str) -> Job | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            job.status = "error"
            job.finished_at = time.time()
            job.error_code = code
            job.error_message = message
            return job

    def mark_cancelled(self, job_id: str, message: str = "") -> Job | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            job.status = "cancelled"
            job.finished_at = time.time()
            job.error_message = message or job.error_message
            return job

    # --- Hủy / hết hạn ---
    def cancel(self, job_id: str) -> bool:
        """Hủy job: chờ -> cancelled ngay; chạy -> đặt cờ để worker dừng
        sau chunk đang chạy (TH-19). Trả False nếu không có job."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return False
            if job.status == "queued":
                job.status = "cancelled"
                job.finished_at = time.time()
                job.error_message = "Job đã bị hủy khi đang chờ."
            elif job.status == "running":
                job.cancel_event.set()
            return True

    def sweep_expired(self, now: float | None = None) -> list[str]:
        """Hủy mọi job CHỜ đã quá TTL (60'). Trả danh sách id đã hủy.

        Runner gọi định kỳ; route cũng có thể gọi trước khi submit để
        giải phóng suất chờ đã hết hạn.
        """
        now = now if now is not None else time.time()
        swept: list[str] = []
        with self._lock:
            for job in self._jobs.values():
                if job.status == "queued" and now > job.expires_at:
                    job.status = "cancelled"
                    job.finished_at = now
                    job.error_message = (
                        "Hết thời gian chờ 60 phút, gửi lại. "
                        "(Job chờ quá lâu trong hàng đợi nên tự hủy để "
                        "không chiếm suất của job khác.)"
                    )
                    swept.append(job.id)
        return swept
