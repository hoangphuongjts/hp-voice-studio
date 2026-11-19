"""Test worker inference riêng (TK1.8) — T1.8.

- Unit test với engine giả (không cần model): cắt chunk, chạy ngoài main thread,
  hủy giữa các chunk.
- Integration test với engine thật: tổng hợp trong worker (thread id khác main),
  hủy job câu dài 20.000 ký tự (dừng sau chunk đang chạy, không tạo tiếp).
"""

import threading
import time

import numpy as np
import pytest

from tk1_helpers import SHORT_TEXT, VOICE, engine_context
from hpvoice.engines.base import AudioResult
from hpvoice.jobs.worker import CancelledError, InferenceWorker, split_text_chunks


# --- Unit test: không cần model ---

class FakeEngine:
    """Engine giả: mỗi synthesize tốn 0,05 s, trả audio 0,1 s."""

    name = "fake"
    sample_rate = 48000

    def __init__(self):
        self.calls = []

    def synthesize(self, text, voice, options=None):
        self.calls.append(text)
        time.sleep(0.3)
        return AudioResult(samples=np.zeros(4800, dtype=np.float32),
                           sample_rate=48000, engine="fake", voice=voice)


def test_split_text_chunks_cat_o_ranh_gioi_cau():
    """Cắt chunk <= 256 ký tự, ưu tiên ranh giới câu."""
    text = "Câu một ngắn. " + "Câu hai cũng ngắn. " * 10 + "Câu cuối."
    chunks = split_text_chunks(text)
    assert chunks
    assert all(len(c) <= 256 for c in chunks)
    assert " ".join(chunks).replace("  ", " ") == " ".join(text.split())
    # Câu dài không có ranh giới câu -> cắt cứng tại 256.
    long = "a" * 600
    hard = split_text_chunks(long)
    assert hard == ["a" * 256, "a" * 256, "a" * 88]


def test_worker_chay_ngoai_main_thread_va_noi_chunk():
    """T1.8 (logic): job chạy ngoài main thread, nối đủ chunk theo thứ tự."""
    worker = InferenceWorker()
    try:
        engine = FakeEngine()
        text = "Câu một. Câu hai. Câu ba. Câu bốn. Câu năm."
        future = worker.submit(worker.synthesize_long, engine, text, "Giọng Giả")
        result, job = future.result(timeout=30)
        assert job.ran_off_main_thread, (
            f"Job phải chạy ngoài main thread (job thread {job.thread_id} "
            f"vs main {job.main_thread_id})"
        )
        assert job.chunks_done == job.chunks_total > 0
        assert len(result.samples) == job.chunks_done * 4800
        assert result.duration_s > 0
        # Thứ tự chunk giữ nguyên (engine giả ghi lại từng câu gọi).
        assert " ".join(engine.calls) == " ".join(text.split())
    finally:
        worker.shutdown()


def test_worker_huy_giua_cac_chunk():
    """T1.8 (nút Dừng): hủy giữa chừng -> dừng sau chunk đang chạy, không tạo tiếp."""
    worker = InferenceWorker()
    try:
        engine = FakeEngine()
        text = " ".join(f"Câu thứ {i}." for i in range(60))
        job_holder: dict = {}

        def run():
            job = job_holder["job"]
            return worker.synthesize_long(engine, text, "Giọng Giả", job=job)

        from hpvoice.jobs.worker import SynthesisJob

        job_holder["job"] = SynthesisJob(job_id="test-cancel")
        future = worker.submit(run)
        time.sleep(0.35)  # để chunk đầu chạy xong, chunk sau đang chạy (mỗi chunk 0,3 s)
        worker.cancel("test-cancel")
        with pytest.raises(CancelledError):
            future.result(timeout=10)
        job = job_holder["job"]
        assert job.cancelled is True
        assert 0 < job.chunks_done < job.chunks_total
        assert len(engine.calls) == job.chunks_done
    finally:
        worker.shutdown()


def test_run_in_executor_khong_chan_event_loop():
    """T1.8 (API): run_in_executor chạy fn trong worker từ event loop."""
    import asyncio

    async def main():
        worker = InferenceWorker()
        try:
            main_id = threading.get_ident()
            result = await worker.run_in_executor(lambda: threading.get_ident())
            assert result != main_id
            return True
        finally:
            worker.shutdown()

    assert asyncio.run(main())


# --- Integration test: engine thật ---

@pytest.fixture(scope="module")
def engine_fp32():
    with engine_context("fp32") as engine:
        yield engine


def test_t18_tong_hop_trong_worker_thread_rieng(engine_fp32):
    """T1.8: tổng hợp thật trong worker — thread id khác main, audio đúng."""
    worker = InferenceWorker()
    try:
        main_id = threading.get_ident()
        future = worker.submit(worker.synthesize_long, engine_fp32,
                               SHORT_TEXT + " " + SHORT_TEXT, VOICE)
        result, job = future.result(timeout=300)
        assert job.thread_id is not None and job.thread_id != main_id
        assert job.ran_off_main_thread
        assert job.chunks_done == job.chunks_total >= 1
        assert result.sample_rate == 48000 and len(result.samples) > 0
        assert result.duration_s > 0
    finally:
        worker.shutdown()


def test_t18_huy_job_cau_dai_20000_ky_tu(engine_fp32):
    """T1.8: tạo câu dài 20.000 ký tự trong worker, hủy -> dừng, không chạy tiếp.

    Câu 20.000 ký tự mà tạo hết sẽ mất hàng chục phút trên VM nên test chỉ
    chứng minh: job bắt đầu ngoài main thread, hủy có tác dụng (dừng sau chunk
    đang chạy, CancelledError, không tạo thêm chunk). Thời gian hủy tối đa
    ≈ thời gian tạo 1 chunk (SDK không hủy được giữa chunk).
    """
    worker = InferenceWorker()
    try:
        sentence = "Đây là một câu kiểm tra hủy job trong lúc tạo giọng đọc dài. "
        long_text = (sentence * 400)[:20000]
        assert len(long_text) == 20000
        chunks = split_text_chunks(long_text)
        assert len(chunks) > 10  # đủ dài để hủy giữa chừng có ý nghĩa
        job_holder: dict = {}

        from hpvoice.jobs.worker import SynthesisJob

        job = SynthesisJob(job_id="test-long-cancel")
        job_holder["job"] = job
        future = worker.submit(worker.synthesize_long, engine_fp32,
                               long_text, VOICE, None, None, job)
        # Chờ job bắt đầu chạy chunk đầu (tối đa 60 s), rồi hủy.
        t0 = time.perf_counter()
        while job.thread_id is None and time.perf_counter() - t0 < 60:
            time.sleep(0.5)
        assert job.thread_id is not None, "Job không bắt đầu trong 60 s"
        assert job.thread_id != threading.get_ident()
        cancel_t0 = time.perf_counter()
        worker.cancel(job.job_id)
        with pytest.raises(CancelledError):
            future.result(timeout=300)
        cancel_s = time.perf_counter() - cancel_t0
        assert job.cancelled is True
        assert job.chunks_done < job.chunks_total
        print(f"\nHủy job 20.000 ký tự: dừng sau {cancel_s:.1f}s, "
              f"đã xong {job.chunks_done}/{job.chunks_total} chunk.")
    finally:
        worker.shutdown()
