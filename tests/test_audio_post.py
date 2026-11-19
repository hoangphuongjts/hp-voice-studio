"""Test AudioPost + FFmpegManager (SPEC §3.3, TK1.6/TK1.9, test T2.4/T2.10).

Chạy: .venv/bin/python -m pytest tests/test_audio_post.py tests/test_ffmpeg_manager.py -v
Dùng audio numpy tổng hợp + file WAV mẫu evidence/t1-first-wav/ — không load model.
"""
import subprocess
from pathlib import Path

import numpy as np
import pytest

from hpvoice.audio.post import (
    SAMPLE_RATE,
    join_chunks,
    make_silence,
    normalize_peak,
    time_stretch,
    write_wav,
)
from hpvoice.audio.ffmpeg_manager import FFmpegManager

SR = SAMPLE_RATE
REPO = Path(__file__).resolve().parent.parent
SAMPLE_WAV = REPO / "evidence" / "t1-first-wav" / "t1-first-wav-hai-dang.wav"


def tone(freq=440.0, dur=2.0, sr=SR):
    t = np.arange(int(dur * sr)) / sr
    return (0.5 * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def test_toc_do_1x_khong_qua_time_stretch():
    """T2.4: tốc độ 1,0× không qua time-stretch — trả về đúng mẫu gốc."""
    y = tone(dur=1.0)
    out, stretched = time_stretch(y, SR, 1.0)
    assert stretched is False
    assert np.array_equal(out, y)


def test_time_stretch_ti_le_thoi_luong(tmp_path):
    """T2.4: tỉ lệ thời lượng ≈ 1/rate ±10% (đo trên tone 2 s).
    Engine mặc định là atempo (FFmpeg) — xem docs/stretch-decision.md."""
    y = tone(dur=2.0)
    for rate, expect in ((1.5, 2.0 / 1.5), (0.75, 2.0 / 0.75)):
        out, stretched = time_stretch(y, SR, rate)
        assert stretched is True
        assert len(out) / SR == pytest.approx(expect, rel=0.10)


def test_time_stretch_ngoai_khoang_bao_loi():
    y = tone(dur=0.5)
    with pytest.raises(ValueError):
        time_stretch(y, SR, 0.5)
    with pytest.raises(ValueError):
        time_stretch(y, SR, 2.0)


def test_join_chunks_chen_khoang_lang_dung_so_giay():
    a = tone(440, 1.0)
    b = tone(660, 1.0)
    out = join_chunks([a, b], SR, pauses=[2.0])
    # Tổng ≈ 1 + 2 + 1 (±0,3 s do bù im lặng mép theo quy tắc join_audio_chunks)
    assert len(out) / SR == pytest.approx(4.0, abs=0.35)
    # Giữa hai đoạn phải có im lặng thật ≥ 1,5 s
    mid = out[SR : 3 * SR]
    assert float(np.max(np.abs(mid))) < 0.01


def test_join_chunks_khong_pause_noi_thang():
    a = tone(440, 0.5)
    b = tone(660, 0.5)
    out = join_chunks([a, b], SR, pauses=[0.0])
    assert len(out) / SR == pytest.approx(1.0, abs=0.05)


def test_normalize_peak():
    y = tone(dur=0.5) * 0.2
    out = normalize_peak(y, target=0.9)
    assert float(np.max(np.abs(out))) == pytest.approx(0.9, abs=0.01)
    # Không đổi khi đã đủ lớn
    y2 = tone(dur=0.5)
    assert float(np.max(np.abs(normalize_peak(y2, target=0.9)))) == pytest.approx(0.9, abs=0.01)


def test_write_wav_48khz(tmp_path):
    p = tmp_path / "out.wav"
    write_wav(p, tone(dur=1.0), SR)
    import soundfile as sf

    info = sf.info(str(p))
    assert info.samplerate == 48000
    assert info.channels == 1
    assert info.duration == pytest.approx(1.0, abs=0.01)


def test_write_wav_ghi_dan_ra_dia(tmp_path):
    """Bài dài: ghi dần ra đĩa, không giữ toàn bộ trong RAM (SoundFile append)."""
    from hpvoice.audio.post import WavWriter

    p = tmp_path / "long.wav"
    with WavWriter(p, SR) as w:
        for _ in range(5):
            w.write(tone(dur=0.5))
    import soundfile as sf

    assert sf.info(str(p)).duration == pytest.approx(2.5, abs=0.02)


def test_make_silence():
    s = make_silence(2.0, SR)
    assert len(s) == 2 * SR
    assert float(np.max(np.abs(s))) == 0.0


def test_stretch_audio_file_mac_dinh_atempo_fallback_librosa(tmp_path):
    """TK1.9: file qua stretch_audio_file — dùng atempo khi có FFmpeg.
    Không có FFmpeg -> librosa nếu còn cài (máy dev); nếu librosa cũng
    không có (bộ cài frozen) -> StretchUnavailableError rõ ràng, hướng
    dẫn tải FFmpeg — không crash bằng ImportError khó hiểu."""
    from hpvoice.audio.ffmpeg_manager import FFmpegManager
    from hpvoice.audio.post import StretchUnavailableError, stretch_audio_file

    write_wav(tmp_path / "in.wav", tone(dur=2.0), SR)
    fm = FFmpegManager()
    engine = stretch_audio_file(tmp_path / "in.wav", tmp_path / "out.mp3.wav", 1.5, fm)
    assert engine == "atempo"
    import soundfile as sf

    assert sf.info(str(tmp_path / "out.mp3.wav")).duration == pytest.approx(2.0 / 1.5, rel=0.05)

    # Không có FFmpeg -> tùy librosa có cài hay không.
    fm2 = FFmpegManager()
    fm2.locate = lambda: None  # type: ignore[method-assign]
    fm2.run_atempo = lambda *a, **k: False  # type: ignore[method-assign]
    try:
        import librosa  # noqa: F401

        has_librosa = True
    except ImportError:
        has_librosa = False
    if has_librosa:
        engine2 = stretch_audio_file(tmp_path / "in.wav", tmp_path / "out2.wav", 1.5, fm2)
        assert engine2 == "librosa"
        assert sf.info(str(tmp_path / "out2.wav")).duration == pytest.approx(2.0 / 1.5, rel=0.10)
    else:
        with pytest.raises(StretchUnavailableError, match="FFmpeg"):
            stretch_audio_file(tmp_path / "in.wav", tmp_path / "out2.wav", 1.5, fm2)

    # 1,0× → chép nguyên, không stretch.
    assert stretch_audio_file(tmp_path / "in.wav", tmp_path / "out3.wav", 1.0, fm) == "copy"
    assert sf.info(str(tmp_path / "out3.wav")).duration == pytest.approx(2.0, abs=0.01)


def test_time_stretch_librosa_thieu_bao_loi_ro(tmp_path):
    """Size: engine librosa tường minh mà librosa chưa cài -> lỗi rõ ràng
    (StretchUnavailableError, ValueError) thay vì ImportError. Bỏ qua khi
    librosa còn cài (máy dev chưa gỡ)."""
    try:
        import librosa  # noqa: F401

        pytest.skip("librosa còn cài trên máy dev — đường lỗi chỉ xảy ra ở bộ cài frozen")
    except ImportError:
        pass
    from hpvoice.audio.post import StretchUnavailableError

    with pytest.raises(StretchUnavailableError, match="FFmpeg"):
        time_stretch(tone(dur=1.0), SR, 1.5, engine="librosa")
