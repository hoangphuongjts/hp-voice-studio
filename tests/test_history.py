"""Test HistoryStore bền vững (TK2.3/TK2.10, TH-16/TH-21/TH-30/TH-33) — T3.6 (phần API).

- Ghi atomic (file tạm + rename); file history hỏng -> đọc bản backup + báo rõ.
- Checkpoint sau mỗi mục: add() nào cũng ghi đĩa ngay, mở lại store vẫn thấy.
- Chặn tạo mới khi vượt max_history_gb + báo rõ hướng xoá/xuất bớt (TH-16).
- Kiểm tra dung lượng trống trước batch lớn (TH-21/TH-33).
- Dọn file tạm khi hủy/crash: quét lúc khởi động (cleanup_temp).
- PreviewCache: trần dung lượng + dọn cũ nhất khi vượt trần (TH-30).
"""
import json
import time

import pytest

from hpvoice.jobs.history import (
    HistoryFullError,
    HistoryStore,
    InsufficientSpaceError,
    PreviewCache,
)


def _store(tmp_path, max_gb=5):
    return HistoryStore(history_dir=tmp_path / "history", max_history_gb=max_gb)


def test_add_va_list_du_3_ban(tmp_path):
    """T3.6: tạo 3 bản -> danh sách hiện đủ 3, đúng metadata (§8 HistoryItem)."""
    store = _store(tmp_path)
    for i in range(3):
        item = store.add(text_preview=f"Câu {i}", voice_id="Hải Đăng",
                         engine="v3", speed=1.0, format="wav",
                         duration_sec=0.5, audio_bytes=b"WAV" * 100)
        assert item["id"]
        assert item["voice_id"] == "Hải Đăng"
        assert item["size_bytes"] == 300  # b"WAV" * 100 = 300 byte
        assert item["duration_sec"] == 0.5
    items, total = store.list_items()
    assert total == 3
    assert len(items) == 3
    assert items[0]["text_preview"] == "Câu 2"  # mới nhất lên đầu


def test_checkpoint_mo_lai_store_van_thay_du_ban(tmp_path):
    """Checkpoint: mỗi add() ghi đĩa ngay — mở store mới vẫn đọc đủ các bản."""
    store = _store(tmp_path)
    store.add(text_preview="Câu A", voice_id="Hải Đăng", format="wav",
              duration_sec=0.5, audio_bytes=b"X" * 10)
    store.add(text_preview="Câu B", voice_id="Mai Anh", format="wav",
              duration_sec=0.5, audio_bytes=b"Y" * 10)
    store2 = _store(tmp_path)
    _, total = store2.list_items()
    assert total == 2
    assert store2.get(store2.list_items()[0][0]["id"]) is not None


def test_get_va_delete_xoa_ca_file_audio(tmp_path):
    """Get trả đúng bản; delete xoá cả mục index lẫn file audio trên đĩa."""
    store = _store(tmp_path)
    item = store.add(text_preview="Câu xoá", voice_id="Hải Đăng", format="wav",
                     duration_sec=0.5, audio_bytes=b"Z" * 50)
    audio_path = store.history_dir / item["audio_path"]
    assert audio_path.is_file()
    assert store.get(item["id"])["text_preview"] == "Câu xoá"
    assert store.delete(item["id"]) is True
    assert store.get(item["id"]) is None
    assert not audio_path.exists()
    assert store.delete(item["id"]) is False  # xoá lần 2 -> False


def test_file_history_hong_doc_ban_backup_va_bao_ro(tmp_path):
    """TH-21: file history.json hỏng -> đọc bản backup + cờ corrupted + báo rõ."""
    store = _store(tmp_path)
    store.add(text_preview="Câu backup", voice_id="Hải Đăng", format="wav",
              duration_sec=0.5, audio_bytes=b"B" * 10)
    store.add(text_preview="Câu backup 2", voice_id="Hải Đăng", format="wav",
              duration_sec=0.5, audio_bytes=b"B" * 10)
    index = tmp_path / "history" / "history.json"
    assert (tmp_path / "history" / "history.json.bak").is_file()
    index.write_text("{ hỏng hẳn [[", encoding="utf-8")  # phá file chính
    store2 = _store(tmp_path)
    assert store2.corrupted is True
    assert store2.load_warning and "backup" in store2.load_warning
    items, total = store2.list_items()
    # Backup là checkpoint TRƯỚC lần ghi cuối (copy index cũ trước khi ghi mới)
    # nên khôi phục được 1 bản (bản đầu), bản thêm sau cùng có thể mất — chấp
    # nhận được, quan trọng là không mất toàn bộ + không crash.
    assert total == 1
    assert items[0]["text_preview"] == "Câu backup"


def test_file_chinh_va_backup_deu_hong_khong_crash(tmp_path):
    """Cả chính + backup đều hỏng -> store rỗng + báo rõ, app không crash."""
    store = _store(tmp_path)
    store.add(text_preview="Câu", voice_id="Hải Đăng", format="wav",
              duration_sec=0.5, audio_bytes=b"B" * 10)
    for name in ("history.json", "history.json.bak"):
        (tmp_path / "history" / name).write_text("{{{ hỏng", encoding="utf-8")
    store2 = _store(tmp_path)
    assert store2.corrupted is True
    _, total = store2.list_items()
    assert total == 0


def test_chan_tao_moi_khi_vuot_max_history_gb(tmp_path):
    """TH-16: vượt max_history_gb -> chặn tạo mới + báo rõ hướng xoá/xuất bớt."""
    store = _store(tmp_path, max_gb=0.000001)  # ~1 KB
    store.add(text_preview="Câu 1", voice_id="Hải Đăng", format="wav",
              duration_sec=0.5, audio_bytes=b"A" * 500)
    with pytest.raises(HistoryFullError) as exc:
        store.add(text_preview="Câu 2", voice_id="Hải Đăng", format="wav",
                  duration_sec=0.5, audio_bytes=b"B" * 600)
    assert "xoá" in str(exc.value) or "xuất" in str(exc.value)
    _, total = store.list_items()
    assert total == 1  # bản vượt ngưỡng không được tạo
    # Xoá bớt thì tạo lại được (mở lại dung lượng).
    store.delete(store.list_items()[0][0]["id"])
    store.add(text_preview="Câu 2", voice_id="Hải Đăng", format="wav",
              duration_sec=0.5, audio_bytes=b"B" * 600)


def test_would_exceed_bao_truoc_khi_tao(tmp_path):
    """would_exceed() cho API kiểm tra trước khi tổng hợp (để trả 507 sớm)."""
    store = _store(tmp_path, max_gb=0.000001)
    assert store.would_exceed(10) is False
    assert store.would_exceed(10_000_000) is True


def test_kiem_tra_dung_luong_trong_truoc_batch_lon(tmp_path):
    """TH-21/TH-33: batch cần dung lượng lớn hơn ổ trống -> lỗi rõ, chưa làm gì."""
    store = _store(tmp_path)
    with pytest.raises(InsufficientSpaceError):
        store.ensure_free_space(10**18)  # 1 EB — chắc chắn vượt ổ trống
    store.ensure_free_space(1024)  # 1 KB thì phải đủ


def test_cleanup_temp_quét_file_tam_cua_job_da_chet(tmp_path):
    """TH-33: quét lúc khởi động xoá thư mục tạm của job không còn chạy."""
    tmp_dir = tmp_path / "tmp"
    (tmp_dir / "job-cu-1").mkdir(parents=True)
    (tmp_dir / "job-cu-1" / "audio.tmp").write_bytes(b"x")
    (tmp_dir / "job-cu-2").mkdir(parents=True)
    (tmp_dir / "job-dang-chay").mkdir(parents=True)
    (tmp_dir / "job-dang-chay" / "audio.tmp").write_bytes(b"x")
    store = _store(tmp_path)
    removed = store.cleanup_temp(tmp_dir, running_job_ids={"job-dang-chay"})
    assert removed == 2
    assert not (tmp_dir / "job-cu-1").exists()
    assert not (tmp_dir / "job-cu-2").exists()
    assert (tmp_dir / "job-dang-chay").exists()  # job đang chạy được giữ lại


def test_preview_cache_hit_miss_va_tran_dung_luong(tmp_path):
    """TH-30: PreviewCache hit/miss đúng; vượt trần -> dọn file cũ nhất trước."""
    cache = PreviewCache(cache_dir=tmp_path / "preview", max_bytes=1000)
    assert cache.get("giong-a") is None  # miss
    cache.put("giong-a", b"A" * 400)
    assert cache.get("giong-a") == b"A" * 400  # hit
    assert cache.usage_bytes() == 400
    time.sleep(0.02)
    cache.put("giong-b", b"B" * 400)
    time.sleep(0.02)
    cache.put("giong-c", b"C" * 400)  # tổng 1200 > trần 1000 -> dọn cũ nhất
    assert cache.usage_bytes() <= 1000
    assert cache.get("giong-a") is None  # cũ nhất đã bị dọn
    assert cache.get("giong-c") == b"C" * 400


def test_add_from_result_luu_audio_va_srt(tmp_path):
    """add_from_result(): job xong -> lưu audio + srt vào history (dùng chung
    cho đường sync và đường job chạy nền)."""
    store = _store(tmp_path)
    item = store.add_from_result({
        "history_audio_bytes": b"WAVDATA", "history_srt_text": "1\n00:00:00,000 --> 00:00:00,500\nXin chào\n",
        "result_format": "wav", "duration_s": 0.5,
        "text_preview": "Xin chào", "voice_id": "Hải Đăng",
        "engine": "v3", "speed": 1.0,
    })
    assert item is not None
    assert item["srt_path"] is not None
    srt_file = store.history_dir / item["srt_path"]
    assert "Xin chào" in srt_file.read_text(encoding="utf-8")
    item2 = store.add_from_result({"result_format": "zip", "duration_s": 1.0})
    assert item2 is None  # ZIP batch không có audio đơn -> không lưu history
