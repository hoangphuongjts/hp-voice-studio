"""Worker inference riêng (TK1.8, TH-19).

Inference KHÔNG chạy trên event loop FastAPI / luồng UI: mọi tổng hợp dài chạy
trong thread pool 1 worker qua ``InferenceWorker`` (tương đương
``asyncio.run_in_executor`` ở tầng API). Job có cờ hủy (``threading.Event``)
được kiểm tra GIỮA CÁC CHUNK (mỗi chunk <= 256 ký tự) — hủy xong chunk đang
chạy thì dừng, không tạo tiếp chunk sau.

Lưu ý: một chunk ``infer()`` đang chạy không ngắt giữa chừng được (SDK không có
API hủy giữa chunk), nên thời gian hủy tối đa ≈ thời gian tạo 1 chunk.
"""

from __future__ import annotations

import asyncio
import re
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from ..engines.base import MAX_CHUNK_CHARS, AudioResult, SynthesisOptions

# Ranh giới câu tiếng Việt để cắt chunk (giữ dấu câu ở cuối câu).
_SENTENCE_END = re.compile(r"(?<=[.!?…])\s+|(?<=[.!?…]$)")


def split_text_chunks(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    """Cắt text thành chunk <= max_chars, ưu tiên cắt ở ranh giới câu.

    - Câu dài hơn max_chars mà không có ranh giới câu -> cắt cứng tại max_chars.
    - Khoảng trắng thừa được gọn lại; chunk rỗng bị bỏ.
    """
    text = " ".join(str(text).split())
    if not text:
        return []
    chunks: list[str] = []
    for sentence in _SENTENCE_END.split(text):
        sentence = sentence.strip()
        if not sentence:
            continue
        while len(sentence) > max_chars:
            chunks.append(sentence[:max_chars])
            sentence = sentence[max_chars:].strip()
        if sentence:
            # Gộp vào chunk trước nếu còn chỗ (tránh quá nhiều chunk nhỏ).
            if chunks and len(chunks[-1]) + 1 + len(sentence) <= max_chars:
                chunks[-1] = chunks[-1] + " " + sentence
            else:
                chunks.append(sentence)
    return chunks


@dataclass
class SynthesisJob:
    """Một job tổng hợp chạy trong worker."""

    job_id: str
    cancel_event: threading.Event = field(default_factory=threading.Event)
    thread_id: int | None = None
    main_thread_id: int | None = None
    started_at: float = 0.0
    finished_at: float | None = None
    chunks_done: int = 0
    chunks_total: int = 0
    cancelled: bool = False
    error: str | None = None
    future: object = field(default=None, repr=False)  # Future chạy nền (nếu nộp qua submit_long)

    def cancel(self) -> None:
        """Đặt cờ hủy (job dừng sau chunk đang chạy)."""
        self.cancel_event.set()

    @property
    def ran_off_main_thread(self) -> bool:
        """True khi job chạy ở thread khác main thread (bằng chứng T1.8)."""
        return (
            self.thread_id is not None
            and self.main_thread_id is not None
            and self.thread_id != self.main_thread_id
        )

    @property
    def elapsed_s(self) -> float:
        end = self.finished_at if self.finished_at else time.perf_counter()
        return end - self.started_at


class InferenceWorker:
    """Thread pool 1 worker cho inference (TH-19)."""

    def __init__(self, max_workers: int = 1):
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="hp-inference"
        )
        self._jobs: dict[str, SynthesisJob] = {}
        self._jobs_lock = threading.Lock()

    @property
    def executor(self) -> ThreadPoolExecutor:
        """Executor thô (để API dùng ``loop.run_in_executor``)."""
        return self._executor

    def submit(self, fn: Callable, *args, **kwargs):
        """Chạy fn trong worker, trả Future (dùng cho API/async)."""
        return self._executor.submit(fn, *args, **kwargs)

    async def run_in_executor(self, fn: Callable, *args, **kwargs):
        """Chạy fn trong worker từ event loop FastAPI (không chặn loop)."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, lambda: fn(*args, **kwargs))

    def synthesize_long(
        self,
        engine,
        text: str,
        voice: str,
        options: SynthesisOptions | None = None,
        on_chunk: Callable[[int, int, AudioResult], None] | None = None,
        job: SynthesisJob | None = None,
    ) -> tuple[AudioResult, SynthesisJob]:
        """Tổng hợp text dài theo từng chunk trong worker thread.

        Trả (AudioResult nối các chunk, job). Nếu bị hủy giữa chừng -> raise
        ``CancelledError`` kèm số chunk đã xong trong job.
        """
        job = job or SynthesisJob(job_id=uuid.uuid4().hex[:12])
        job.main_thread_id = threading.main_thread().ident
        job.started_at = time.perf_counter()
        with self._jobs_lock:
            self._jobs[job.job_id] = job
        chunks = split_text_chunks(text)
        job.chunks_total = len(chunks)
        parts: list[np.ndarray] = []
        try:
            for index, chunk_text in enumerate(chunks):
                if job.cancel_event.is_set():
                    job.cancelled = True
                    raise CancelledError(
                        f"Job {job.job_id} đã hủy sau {job.chunks_done}/{job.chunks_total} chunk."
                    )
                job.thread_id = threading.get_ident()
                result = engine.synthesize(chunk_text, voice, options)
                parts.append(np.asarray(result.samples, dtype=np.float32).reshape(-1))
                job.chunks_done = index + 1
                if on_chunk is not None:
                    on_chunk(index + 1, len(chunks), result)
                if job.cancel_event.is_set():
                    job.cancelled = True
                    raise CancelledError(
                        f"Job {job.job_id} đã hủy sau {job.chunks_done}/{job.chunks_total} chunk."
                    )
        except CancelledError:
            job.finished_at = time.perf_counter()
            raise
        except Exception as exc:  # noqa: BLE001 - ghi lỗi vào job rồi ném tiếp
            job.error = str(exc)
            job.finished_at = time.perf_counter()
            raise
        job.finished_at = time.perf_counter()
        samples = np.concatenate(parts) if parts else np.zeros(0, dtype=np.float32)
        return (
            AudioResult(
                samples=samples,
                sample_rate=getattr(engine, "sample_rate", 48000),
                engine=getattr(engine, "name", "v3"),
                voice=voice,
            ),
            job,
        )

    def submit_long(
        self, engine, text: str, voice: str, options: SynthesisOptions | None = None,
        on_chunk: Callable[[int, int, AudioResult], None] | None = None,
    ) -> SynthesisJob:
        """Nộp job tổng hợp dài vào worker, trả job ngay (Future chạy nền)."""
        job = SynthesisJob(job_id=uuid.uuid4().hex[:12])
        future = self._executor.submit(
            self.synthesize_long, engine, text, voice, options, on_chunk, job
        )
        job.future = future
        with self._jobs_lock:
            self._jobs[job.job_id] = job
        return job

    def cancel(self, job_id: str) -> bool:
        """Hủy job (đặt cờ; job dừng sau chunk đang chạy). Trả False nếu không có job."""
        with self._jobs_lock:
            job = self._jobs.get(job_id)
        if job is None:
            return False
        job.cancel()
        return True

    def get_job(self, job_id: str) -> SynthesisJob | None:
        with self._jobs_lock:
            return self._jobs.get(job_id)

    def shutdown(self, wait: bool = True) -> None:
        self._executor.shutdown(wait=wait)


class CancelledError(RuntimeError):
    """Job bị hủy bởi người dùng (nút Dừng)."""
