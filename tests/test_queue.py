"""Test JobQueue (TK2.3, SPEC §3.3/§4/§9) — T2.9 (phần hàng đợi).

- 1 job chạy, tối đa 20 job chờ (Q16 đã chốt); đầy -> QueueFullError (API map 429).
- TTL 60 phút: job chờ quá TTL thì bị hủy + báo rõ khi quét (sweep_expired).
- Hủy job đang chờ / đang chạy (cờ cancel).
- Thứ tự FIFO, trạng thái đúng vòng đời queued -> running -> done/error.
"""
import time

import pytest

from hpvoice.jobs.queue import JobQueue, QueueFullError


def _run_fn(state, job):
    return {"result_bytes": b"fake-audio", "result_format": "wav",
            "result_media_type": "audio/wav", "duration_s": 0.5}


def test_submit_va_lay_job_theo_id():
    """Submit -> queued, lấy đúng job theo id, payload giữ nguyên."""
    q = JobQueue(max_waiting=20)
    job = q.submit(kind="tts", payload={"text": "Xin chào", "voice_id": "Hải Đăng"},
                   run_fn=_run_fn)
    assert job.status == "queued"
    assert job.kind == "tts"
    assert job.payload["text"] == "Xin chào"
    assert q.get(job.id) is job
    assert q.waiting_count() == 1
    assert q.get("không-tồn-tại") is None


def test_toi_da_20_job_cho_job_thu_21_bi_tu_choi():
    """Q16: tối đa 20 job chờ — job thứ 21 -> QueueFullError (API: 429)."""
    q = JobQueue(max_waiting=20)
    for _ in range(20):
        q.submit(kind="tts", payload={}, run_fn=_run_fn)
    assert q.waiting_count() == 20
    with pytest.raises(QueueFullError) as exc:
        q.submit(kind="tts", payload={}, run_fn=_run_fn)
    assert "20" in str(exc.value)  # thông báo ghi rõ giới hạn
    assert q.waiting_count() == 20  # job bị từ chối không vào hàng đợi


def test_job_dang_chay_khong_tinh_vao_20_job_cho():
    """Job đang chạy không chiếm suất chờ: 1 chạy + 20 chờ mới đầy."""
    q = JobQueue(max_waiting=20)
    first = q.submit(kind="tts", payload={}, run_fn=_run_fn)
    q.mark_running(first.id)
    assert q.waiting_count() == 0
    for _ in range(20):
        q.submit(kind="tts", payload={}, run_fn=_run_fn)
    with pytest.raises(QueueFullError):
        q.submit(kind="tts", payload={}, run_fn=_run_fn)


def test_peek_next_khong_doi_trang_thai_cho_tien_chay_that():
    """peek_next() không chuyển job sang running — job vẫn tính là đang chờ
    cho tới khi runner thực sự chiếm được CPU (đếm hàng đợi 20 mới đúng)."""
    q = JobQueue(max_waiting=20)
    job = q.submit(kind="tts", payload={}, run_fn=_run_fn)
    assert q.peek_next() is job
    assert job.status == "queued"
    assert q.waiting_count() == 1
    assert q.running_job() is None


def test_take_next_fifo_va_mark_done():
    """take_next lấy đúng thứ tự FIFO và chuyển sang running; done ghi kết quả."""
    q = JobQueue(max_waiting=20)
    j1 = q.submit(kind="tts", payload={"n": 1}, run_fn=_run_fn)
    j2 = q.submit(kind="tts", payload={"n": 2}, run_fn=_run_fn)
    nxt = q.take_next()
    assert nxt is j1
    assert nxt.status == "running"
    assert q.running_job() is j1
    q.mark_done(j1.id, result_path="/tmp/x.wav", duration_s=1.5, size_bytes=123)
    done = q.get(j1.id)
    assert done.status == "done"
    assert done.progress == 1.0
    assert done.result_path == "/tmp/x.wav"
    assert done.duration_s == 1.5
    assert q.take_next() is j2  # job sau mới được lấy


def test_mark_error_ghi_ma_va_thong_bao():
    """Job lỗi: status error + error_code/error_message rõ ràng để API trả về."""
    q = JobQueue(max_waiting=20)
    job = q.submit(kind="tts", payload={}, run_fn=_run_fn)
    q.mark_running(job.id)
    q.mark_error(job.id, code="engine_error", message="Engine lỗi giả lập")
    got = q.get(job.id)
    assert got.status == "error"
    assert got.error_code == "engine_error"
    assert "Engine lỗi" in got.error_message


def test_huy_job_dang_cho():
    """Hủy job đang chờ -> cancelled, không chạy nữa (take_next bỏ qua)."""
    q = JobQueue(max_waiting=20)
    j1 = q.submit(kind="tts", payload={"n": 1}, run_fn=_run_fn)
    j2 = q.submit(kind="tts", payload={"n": 2}, run_fn=_run_fn)
    assert q.cancel(j1.id) is True
    assert q.get(j1.id).status == "cancelled"
    assert q.take_next() is j2
    assert q.cancel("không-tồn-tại") is False


def test_huy_job_dang_chay_dat_co_cancel():
    """Hủy job đang chạy -> đặt cờ cancel (worker kiểm tra giữa các chunk)."""
    q = JobQueue(max_waiting=20)
    job = q.submit(kind="tts", payload={}, run_fn=_run_fn)
    q.mark_running(job.id)
    assert q.cancel(job.id) is True
    assert job.cancel_event.is_set()
    assert job.status == "running"  # vẫn running cho tới khi worker dừng hẳn


def test_ttl_het_han_job_cho_bi_huy_va_bao_ro():
    """TTL 60': job chờ quá TTL -> sweep hủy + thông báo 'hết thời gian chờ'."""
    q = JobQueue(max_waiting=20, ttl_seconds=0.2)
    job = q.submit(kind="tts", payload={}, run_fn=_run_fn)
    assert q.sweep_expired() == []  # chưa hết TTL
    time.sleep(0.3)
    swept = q.sweep_expired()
    assert swept == [job.id]
    got = q.get(job.id)
    assert got.status == "cancelled"
    assert "hết thời gian chờ" in got.error_message.lower()
    assert q.waiting_count() == 0


def test_ttl_khong_huy_job_dang_chay():
    """Job đang chạy thì TTL chờ không áp dụng (chỉ job chờ mới hết hạn)."""
    q = JobQueue(max_waiting=20, ttl_seconds=0.2)
    job = q.submit(kind="tts", payload={}, run_fn=_run_fn)
    q.mark_running(job.id)
    time.sleep(0.3)
    assert q.sweep_expired() == []
    assert q.get(job.id).status == "running"


def test_cap_nhat_tien_trinh():
    """Tiến trình job cập nhật được (để API poll /api/jobs/{id} hiển thị)."""
    q = JobQueue(max_waiting=20)
    job = q.submit(kind="tts", payload={}, run_fn=_run_fn)
    q.mark_running(job.id)
    q.update_progress(job.id, 0.5)
    assert q.get(job.id).progress == 0.5
    q.update_progress(job.id, 2.0)  # kẹp về 1.0, không vượt
    assert q.get(job.id).progress == 1.0


def test_check_batch_size_501_bi_tu_choi():
    """Giới hạn batch 500 (SPEC §4): 501 mục -> ValueError rõ giới hạn.

    Hàm này để routes_batch.py (TK2-FEATURES) dùng chung cho HTTP 400;
    test ở đây vì batch route không thuộc TK2.1.
    """
    from hpvoice.jobs.queue import check_batch_size

    check_batch_size(500, limit=500)  # đúng 500 thì được
    with pytest.raises(ValueError) as exc:
        check_batch_size(501, limit=500)
    assert "500" in str(exc.value)
