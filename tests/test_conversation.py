"""Test ConversationEngine (TK2.4, T3.2 phần API — fake engine)."""

import pytest

from hpvoice.audio.conversation import ConversationEngine
from hpvoice.engines.fake import FakeEngine, fake_duration_s

LINES = [
    {"speaker": "An", "text": "Xin chào các bạn!"},
    {"speaker": "Bình", "text": "Chào An, hôm nay khỏe không?"},
    {"speaker": "An", "text": "Khỏe lắm, cảm ơn bạn nhé."},
]
SPEAKERS = {"An": "Trúc Ly", "Bình": "Hải Đăng"}


def test_conversation_two_speakers_three_turns():
    engine = ConversationEngine(FakeEngine(), pause_between_turns_s=0.5)
    result = engine.synthesize(LINES, SPEAKERS)
    assert result.voices_used == SPEAKERS
    assert len(result.cues) == 3
    # Voice-lock: mốc từng lượt đúng giọng (ghi trong cue text + voices_used).
    assert result.cues[0].text.startswith("An:")
    assert result.cues[1].text.startswith("Bình:")
    assert result.cues[2].text.startswith("An:")
    # Mốc giờ: lượt 1 từ 0; lượt sau = lượt trước + 0,5 s khoảng lặng.
    d0 = fake_duration_s(LINES[0]["text"])
    d1 = fake_duration_s(LINES[1]["text"])
    assert result.cues[0].start_s == pytest.approx(0.0)
    assert result.cues[0].end_s == pytest.approx(d0)
    assert result.cues[1].start_s == pytest.approx(d0 + 0.5)
    assert result.cues[1].end_s == pytest.approx(d0 + 0.5 + d1)
    total = d0 + d1 + fake_duration_s(LINES[2]["text"]) + 2 * 0.5
    assert result.duration_s == pytest.approx(total, abs=0.01)
    # .srt theo speaker.
    srt = result.to_srt()
    assert "An: Xin chào các bạn!" in srt
    assert "Bình: Chào An" in srt


def test_conversation_save_load_keeps_voice_lock(tmp_path):
    path = tmp_path / "kich-ban.json"
    ConversationEngine.save_script(path, LINES, SPEAKERS)
    lines, speakers = ConversationEngine.load_script(path)
    # Mở lại kịch bản -> giọng không đổi (đối chiếu voice_id trong file đã lưu).
    assert speakers == SPEAKERS
    assert [ln.speaker for ln in lines] == ["An", "Bình", "An"]
    result = ConversationEngine(FakeEngine()).synthesize(lines, speakers)
    assert result.voices_used == SPEAKERS


def test_conversation_errors():
    engine = ConversationEngine(FakeEngine())
    with pytest.raises(ValueError, match="chưa gán giọng"):
        engine.synthesize([{"speaker": "Lạ", "text": "Xin chào!"}], SPEAKERS)
    with pytest.raises(ValueError, match="rỗng"):
        engine.synthesize([{"speaker": "An", "text": "   "}], SPEAKERS)
    with pytest.raises(ValueError, match="Tối đa 8"):
        engine.synthesize(
            [{"speaker": f"S{i}", "text": "Xin chào!"} for i in range(9)],
            {f"S{i}": "Hải Đăng" for i in range(9)},
        )
    with pytest.raises(ValueError, match="rỗng"):
        engine.synthesize([], SPEAKERS)
    with pytest.raises(ValueError, match="20000"):
        engine.synthesize([{"speaker": "An", "text": "x" * 20001}], SPEAKERS)


def test_conversation_write_wav(tmp_path):
    engine = ConversationEngine(FakeEngine())
    result = engine.synthesize(LINES, SPEAKERS)
    out = ConversationEngine.write_wav(tmp_path / "hoi-thoai.wav", result)
    assert out.is_file()
    assert out.stat().st_size > 1000
