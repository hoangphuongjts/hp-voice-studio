"""Test SrtDubber (TK2.5 + TK2.13, T3.3 phần API — fake engine).

Đo giới hạn SRT dub: test cuối đo thời gian parse 1000 cue (ghi số đo);
giới hạn cứng KHÔNG chốt ở v1 (SPEC §4 sửa — không lấy số 100.000 của batch).
"""

import time

import pytest

from hpvoice.audio.srt_dubber import (
    SrtDubber,
    SrtParseError,
    parse_srt_text,
    parse_subtitle_file,
    parse_vtt_text,
)
from hpvoice.engines.fake import FakeEngine, fake_duration_s
from hpvoice.engines.router import EngineRouter
from hpvoice.engines.v4_engine import V4Error

SRT_SAMPLE = """1
00:00:00,000 --> 00:00:02,000
<i>Xin chào các bạn!</i>

2
00:00:02,500 --> 00:00:05,000
Hôm nay chúng ta học [nghỉ 1s] cách phát âm.

3
00:00:06,000 --> 00:00:08,000
Tạm biệt nhé!
"""

VTT_SAMPLE = """WEBVTT

NOTE Đây là ghi chú, không phải cue.

1
00:00.000 --> 00:02.000 align:start position:10%
Xin chào các bạn!

00:03.000 --> 00:05.500
Hôm nay trời đẹp quá.
"""


def test_parse_srt_strips_formatting():
    cues = parse_srt_text(SRT_SAMPLE)
    assert len(cues) == 3
    assert cues[0].text == "Xin chào các bạn!"  # bỏ thẻ <i>
    assert cues[0].start_s == 0.0
    assert cues[0].end_s == 2.0
    assert cues[1].start_s == 2.5
    assert "[nghỉ 1s]" in cues[1].text  # tag giữ lại ở tầng parse (dub mới xử lý)


def test_parse_vtt_to_internal_srt():
    cues = parse_vtt_text(VTT_SAMPLE)
    assert len(cues) == 2  # NOTE bị bỏ
    assert cues[0].text == "Xin chào các bạn!"
    assert cues[0].start_s == 0.0 and cues[0].end_s == 2.0
    assert cues[1].start_s == 3.0 and cues[1].end_s == 5.5


def test_parse_errors():
    with pytest.raises(SrtParseError, match="Mốc giờ SRT sai"):
        parse_srt_text("1\n00:00:00 --> 00:00:02\nXin chào\n")
    with pytest.raises(SrtParseError, match="ngược"):
        parse_srt_text("1\n00:00:05,000 --> 00:00:02,000\nXin chào\n")
    with pytest.raises(SrtParseError, match="rỗng"):
        parse_srt_text("")
    with pytest.raises(SrtParseError, match="không hỗ trợ"):
        parse_subtitle_file("/tmp/khong-co.txt")


def test_dub_fits_slots_no_overflow():
    cues = parse_srt_text(SRT_SAMPLE)
    result = SrtDubber(FakeEngine()).dub(cues, "Hải Đăng")
    assert len(result.cues) == 3
    assert result.delayed == []  # slot rộng, không câu nào bị lùi
    # Audio dài ≈ bằng video (kết thúc cue cuối 8 s).
    assert result.duration_s == pytest.approx(8.0, abs=0.05)
    srt = result.to_srt()
    # Mốc bắt đầu các cue giữ đúng mốc gốc (không câu nào bị lùi).
    assert "00:00:00,000 -->" in srt
    assert "00:00:02,500 -->" in srt
    assert "00:00:06,000 -->" in srt
    # SRT đã chỉnh mốc không còn tag [nghỉ] (tag chỉ là timing).
    assert "[nghỉ" not in srt


def test_dub_long_cue_overflows_and_shifts_next():
    # Cue 1: text dài (fake audio tối đa 5 s) trong slot 1 s -> tràn, cue 2 bị lùi.
    srt = """1
00:00:00,000 --> 00:00:01,000
""" + "x" * 250 + """

2
00:00:01,000 --> 00:00:03,000
Ngắn thôi.
"""
    cues = parse_srt_text(srt)
    result = SrtDubber(FakeEngine()).dub(cues, "Hải Đăng")
    assert len(result.delayed) == 1
    assert result.delayed[0].index == 1
    assert result.cues[0].effective_rate == pytest.approx(1.5)  # đã đọc nhanh tối đa
    # Cue 2 bắt đầu muộn hơn mốc gốc (bị lùi) đúng bằng độ tràn.
    assert result.cues[1].actual_start_s > result.cues[1].scheduled_start_s
    assert result.cues[1].shift_s == pytest.approx(
        result.cues[0].actual_end_s - result.cues[0].scheduled_end_s, abs=0.01
    )


def test_dub_pause_tag_counts_in_slot_not_in_speech():
    srt = """1
00:00:00,000 --> 00:00:05,000
Xin chào [nghỉ 1s] các bạn nhé!
"""
    cues = parse_srt_text(srt)
    result = SrtDubber(FakeEngine()).dub(cues, "Hải Đăng")
    # Audio cue = 2 đoạn đọc (0,2 + 0,24 s) đọc chậm 0,75× (slot rộng) + 1 s khoảng lặng.
    assert result.cues[0].actual_end_s == pytest.approx((0.2 + 0.24) / 0.75 + 1.0, abs=0.05)
    assert result.duration_s == pytest.approx(5.0, abs=0.05)
    assert result.delayed == []


def test_dub_user_speed_applied_first():
    srt = """1
00:00:00,000 --> 00:00:10,000
""" + "x" * 100 + """
"""
    cues = parse_srt_text(srt)
    # Text 100 ký tự -> fake 2 s; tốc độ user 1,5× -> cần 1,33 s trong slot 10 s:
    # hệ số căn giờ kéo về 0,75× (tối thiểu) -> hiệu dụng 0,75×, audio 2/0,75 s.
    result = SrtDubber(FakeEngine()).dub(cues, "Hải Đăng", speed=1.5)
    assert result.cues[0].effective_rate == pytest.approx(0.75)
    # Audio cue = 2 s / 0,75× ≈ 2,67 s; tổng audio đệm tới hết mốc video (10 s).
    assert result.cues[0].actual_end_s == pytest.approx(2.0 / 0.75, abs=0.1)
    assert result.duration_s == pytest.approx(10.0, abs=0.05)


def test_dub_speed_out_of_range():
    cues = parse_srt_text(SRT_SAMPLE)
    with pytest.raises(ValueError, match="0.75"):
        SrtDubber(FakeEngine()).dub(cues, "Hải Đăng", speed=2.0)


def test_dub_to_file_streams_to_disk(tmp_path):
    cues = parse_srt_text(SRT_SAMPLE)
    out = tmp_path / "dub.wav"
    result = SrtDubber(FakeEngine()).dub(cues, "Hải Đăng", output_path=out)
    assert result.samples is None  # ghi thẳng ra đĩa, không giữ RAM
    assert out.is_file()
    assert result.duration_s == pytest.approx(8.0, abs=0.05)


def test_dub_v4_fallback_to_v3_via_router():
    class _FailingV4:
        name = "v4"
        sample_rate = 48000

        def synthesize(self, text, voice, options=None):
            raise V4Error("V4 lỗi 403 hết quota", status=403, code="quota_exceeded")

    router = EngineRouter(v3_engine=FakeEngine(), v4_engine=_FailingV4())
    cues = parse_srt_text(SRT_SAMPLE)
    result = SrtDubber(_FailingV4()).dub(cues, "Hạ Vy", router=router)
    assert result.fallback_info is not None
    assert "403" in result.fallback_info.message
    assert result.fallback_info.to_voice == "Trúc Ly"
    assert len(result.cues) == 3
    # voice_strict -> không fallback, ném lỗi.
    with pytest.raises(V4Error):
        SrtDubber(_FailingV4()).dub(cues, "Hạ Vy", router=router, voice_strict=True)


def test_srt_1000_cues_parse_time_measured():
    """Đo thời gian parse 1000 cue (giới hạn SRT dub đo ở Bước 3 — ghi số đo)."""
    lines = []
    for i in range(1, 1001):
        lines.append(f"{i}\n00:{i // 60:02d}:{i % 60:02d},000 --> 00:{i // 60:02d}:{(i % 60) + 1:02d},000\nCâu số {i}.\n")
    text = "\n".join(lines)
    t0 = time.perf_counter()
    cues = parse_srt_text(text)
    elapsed = time.perf_counter() - t0
    assert len(cues) == 1000
    # Ghi số đo ra stdout để pytest -v thấy (không assert chặt — chỉ đo).
    print(f"\n[ĐO] parse 1000 cue SRT: {elapsed:.3f} s")
    assert elapsed < 5.0
