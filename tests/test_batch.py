"""Test BatchRunner (TK2.6, T3.5 phần API — fake engine).

Đo peak RAM 100/500 mục bằng ru_maxrss (ghi số đo); giới hạn 500 mục là số
tạm — chốt lại theo số đo (xem test_batch_500_items_ram_measured).
"""

import json
import time
import zipfile

import pytest

from hpvoice.jobs.batch import (
    BatchRunner,
    cleanup_temp_files,
    parse_batch_file,
    parse_batch_json,
    parse_batch_txt,
)
from hpvoice.engines.fake import FakeEngine


def test_parse_batch_txt_markers():
    items = parse_batch_txt("[P1] Xin chào\n[P2] Tạm biệt\ncâu tiếp\n[P3]\n")
    assert [i.id for i in items] == ["P1", "P2", "P3"]
    assert items[1].text == "Tạm biệt câu tiếp"
    assert items[2].text == ""  # mốc rỗng giữ lại để báo lỗi riêng
    with pytest.raises(ValueError, match="mốc"):
        parse_batch_txt("Không có mốc nào cả")


def test_parse_batch_json_and_srt(tmp_path):
    items = parse_batch_json(json.dumps([
        {"id": "a", "text": "Xin chào", "voice_id": "Hải Đăng"},
        {"id": "b", "text": "Tạm biệt"},
    ]))
    assert items[0].voice == "Hải Đăng"
    assert items[1].voice == ""
    srt_path = tmp_path / "list.srt"
    srt_path.write_text(
        "1\n00:00:00,000 --> 00:00:02,000\nXin chào\n\n"
        "2\n00:00:02,000 --> 00:00:04,000\nTạm biệt\n", encoding="utf-8")
    items = parse_batch_file(srt_path)
    assert [i.text for i in items] == ["Xin chào", "Tạm biệt"]


def test_batch_run_writes_each_item_and_zip(tmp_path):
    runner = BatchRunner(FakeEngine(), tmp_path)
    items = [{"id": f"P{i}", "text": f"Câu số {i}."} for i in range(1, 11)]
    result = runner.run(items, batch_id="b10")
    assert result.done_count == 10
    assert result.error_count == 0
    wavs = sorted(tmp_path.glob("b10-*.wav"))
    assert len(wavs) == 10  # mỗi mục 1 file ghi ra đĩa ngay
    manifest = tmp_path / "b10-manifest.json"
    assert manifest.is_file()
    assert len(json.loads(manifest.read_text(encoding="utf-8"))["items"]) == 10
    zip_path = runner.export_zip(result)
    assert zip_path.is_file()
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
    assert len([n for n in names if n.endswith(".wav")]) == 10
    assert "b10-manifest.json" in names


def test_batch_one_bad_item_does_not_kill_batch_and_retry(tmp_path):
    runner = BatchRunner(FakeEngine(), tmp_path)
    items = [
        {"id": "P1", "text": "Xin chào!"},
        {"id": "P2", "text": "   "},  # mục lỗi: text rỗng
        {"id": "P3", "text": "Tạm biệt!"},
    ]
    result = runner.run(items, batch_id="b3")
    assert result.done_count == 2
    assert result.error_count == 1
    assert result.failed_items[0].item_id == "P2"
    assert "rỗng" in result.failed_items[0].error
    # Thử lại riêng mục lỗi sau khi sửa text.
    fixed = [
        {"id": "P1", "text": "Xin chào!"},
        {"id": "P2", "text": "Đã sửa rồi nhé!"},
        {"id": "P3", "text": "Tạm biệt!"},
    ]
    result = runner.retry_failed(fixed, result)
    assert result.done_count == 3
    assert result.error_count == 0


def test_batch_limits():
    runner = BatchRunner(FakeEngine(), "/tmp", max_items=5)
    with pytest.raises(ValueError, match="tối đa 5"):
        runner.run([{"id": f"P{i}", "text": "x"} for i in range(6)])
    with pytest.raises(ValueError, match="rỗng"):
        runner.run([])


def test_cleanup_temp_files(tmp_path):
    (tmp_path / "hp-voice-tmp-x.wav.tmp").write_text("x")
    (tmp_path / "keep.wav").write_text("x")
    assert cleanup_temp_files(tmp_path) == 1
    assert not (tmp_path / "hp-voice-tmp-x.wav.tmp").exists()
    assert (tmp_path / "keep.wav").exists()
    # BatchRunner quét dọn file tạm còn sót lúc khởi tạo (TH-33).
    (tmp_path / "hp-voice-tmp-y.wav.tmp").write_text("x")
    runner = BatchRunner(FakeEngine(), tmp_path)
    assert runner.cleaned_temp_files == 1
    assert not (tmp_path / "hp-voice-tmp-y.wav.tmp").exists()


def _measure_batch(n, tmp_path):
    runner = BatchRunner(FakeEngine(), tmp_path)
    items = [{"id": f"P{i}", "text": f"Mục số {i} trong batch."} for i in range(1, n + 1)]
    t0 = time.perf_counter()
    result = runner.run(items, batch_id=f"b{n}")
    elapsed = time.perf_counter() - t0
    assert result.done_count == n
    return result, elapsed


def test_batch_100_items_ram_measured(tmp_path):
    result, elapsed = _measure_batch(100, tmp_path)
    print(f"\n[ĐO] batch 100 mục: {elapsed:.2f} s, peak RSS tuyệt đối {result.peak_rss_mb:.1f} MB "
          f"(tăng {result.rss_delta_mb:.1f} MB trong batch)")
    assert result.peak_rss_mb < 2000.0  # ngân sách T3.5 (fake engine; đo lại với engine thật)


def test_batch_500_items_ram_measured(tmp_path):
    result, elapsed = _measure_batch(500, tmp_path)
    print(f"\n[ĐO] batch 500 mục: {elapsed:.2f} s ({elapsed / 500 * 1000:.0f} ms/mục), "
          f"peak RSS tuyệt đối {result.peak_rss_mb:.1f} MB "
          f"(tăng {result.rss_delta_mb:.1f} MB trong batch)")
    # Ngân sách T3.5: peak RAM ≤ 2 GB với batch 500 mục (máy tối thiểu 8 GB).
    # Số đo này là với fake engine trên VM — cần đo lại với engine thật trên máy anh (C3).
    assert result.peak_rss_mb < 2000.0
