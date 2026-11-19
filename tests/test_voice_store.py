"""Test VoiceStore (TK1.5) — T2.5 phần engine.

Dùng clip WAV thật từ T1 (4,88 s, giọng Hải Đăng) làm ref_audio để test clone.
- Clone có cam kết -> tạo được giọng, synthesize bằng giọng clone ra audio thật.
- Không cam kết / thiếu văn bản cam kết -> lỗi rõ (tương đương 400 ở API).
- Clip < 3 s hoặc > 8 s -> lỗi rõ.
- Gỡ giọng khi khiếu nại (TH-17) -> khỏi engine + file HP, có sổ gỡ giọng.
- File HP riêng, KHÔNG ghi đè assets/voices_v3_turbo.json của package.
"""

import hashlib
import json
from pathlib import Path

import pytest
import soundfile as sf

from tk1_helpers import SAMPLE_WAV, SHORT_TEXT, engine_context
from hpvoice.voices.store import CONSENT_TEXT, VoiceStore, clip_duration_seconds


@pytest.fixture(scope="module")
def engine_fp32():
    with engine_context("fp32") as engine:
        yield engine


@pytest.fixture()
def store(engine_fp32, tmp_path):
    return VoiceStore(engine_fp32, voices_file=tmp_path / "voices.json",
                      data_dir=tmp_path)


def test_clip_mau_dung_3_8_giay():
    """Clip mẫu T1 dài 4,88 s — nằm trong khoảng nhận 3-8 s."""
    assert SAMPLE_WAV.is_file()
    duration = clip_duration_seconds(SAMPLE_WAV)
    assert 3.0 <= duration <= 8.0, duration


def test_preset_doc_tu_sdk_khong_hardcode(engine_fp32, store):
    """Preset đọc từ SDK: 25 giọng, có Hải Đăng."""
    voices = store.list_preset_voices()
    assert len(voices) == 25
    assert any(v.id == "Hải Đăng" for v in voices)


def test_clone_co_cam_ket_tao_duoc_giong_va_noi_duoc(store, tmp_path):
    """T2.5 (engine): clone có cam kết -> synthesize bằng giọng clone ra audio thật."""
    assert SAMPLE_WAV.is_file(), "Thiếu clip mẫu T1"
    voice = store.clone_voice(
        "Giọng Test TK1", SAMPLE_WAV, consent=True, consent_text=CONSENT_TEXT,
        description="Giọng test TK1", gender="Nam",
    )
    assert voice.is_clone and voice.id == "Giọng Test TK1"
    # File HP riêng được ghi, có hồ sơ cam kết.
    hp_file = tmp_path / "voices.json"
    assert hp_file.is_file()
    data = json.loads(hp_file.read_text(encoding="utf-8"))
    rec = data["clones"]["Giọng Test TK1"]
    assert rec["consent"] is True
    assert rec["consent_text"] == CONSENT_TEXT
    assert rec["ref_sha256"] == hashlib.sha256(SAMPLE_WAV.read_bytes()).hexdigest()
    # Nói được bằng giọng clone.
    result = store.engine.synthesize(SHORT_TEXT, "Giọng Test TK1")
    assert result.sample_rate == 48000 and len(result.samples) > 0
    assert result.duration_s > 0
    # Liệt kê có giọng clone.
    assert any(v.id == "Giọng Test TK1" for v in store.list_clone_voices())
    assert any(v.id == "Giọng Test TK1" for v in store.list_all_voices())


def test_clone_khong_cam_ket_bi_chan(store):
    """T2.5 (nhánh lỗi): clip không cam kết -> lỗi rõ, không tạo giọng."""
    with pytest.raises(ValueError, match="cam kết"):
        store.clone_voice("Giọng Không Cam Kết", SAMPLE_WAV,
                          consent=False, consent_text=CONSENT_TEXT)
    with pytest.raises(ValueError, match="cam kết"):
        store.clone_voice("Giọng Thiếu Văn Bản", SAMPLE_WAV,
                          consent=True, consent_text="   ")
    assert "Giọng Không Cam Kết" not in [v.id for v in store.list_clone_voices()]


def test_clip_qua_ngan_bi_chan(store, tmp_path):
    """Clip < 3 s -> lỗi rõ."""
    short_clip = tmp_path / "short.wav"
    data, sr = sf.read(str(SAMPLE_WAV))
    sf.write(str(short_clip), data[:sr], sr)  # đúng 1 s
    assert clip_duration_seconds(short_clip) < 3.0
    with pytest.raises(ValueError, match="3–8"):
        store.clone_voice("Giọng Clip Ngắn", short_clip,
                          consent=True, consent_text=CONSENT_TEXT)


def test_clip_qua_dai_bi_chan(store, tmp_path):
    """Clip > 8 s -> lỗi rõ."""
    long_clip = tmp_path / "long.wav"
    data, sr = sf.read(str(SAMPLE_WAV))
    import numpy as np

    long_data = np.concatenate([data, data])  # ~9,8 s
    sf.write(str(long_clip), long_data, sr)
    assert clip_duration_seconds(long_clip) > 8.0
    with pytest.raises(ValueError, match="3–8"):
        store.clone_voice("Giọng Clip Dài", long_clip,
                          consent=True, consent_text=CONSENT_TEXT)


def test_ten_trung_preset_bi_chan(store):
    """Tên trùng preset đã có -> lỗi rõ (không ghi đè giọng gốc)."""
    with pytest.raises(ValueError, match="đã tồn tại"):
        store.clone_voice("Hải Đăng", SAMPLE_WAV,
                          consent=True, consent_text=CONSENT_TEXT)


def test_takedown_go_giong_khi_khieu_nai(store):
    """TH-17: gỡ giọng khi khiếu nại -> khỏi engine + file HP, có sổ gỡ giọng."""
    store.clone_voice("Giọng Bị Khiếu Nại", SAMPLE_WAV,
                      consent=True, consent_text=CONSENT_TEXT)
    assert store.resolve_voice("Giọng Bị Khiếu Nại") == "Giọng Bị Khiếu Nại"
    store.takedown("Giọng Bị Khiếu Nại", reason="Chủ giọng khiếu nại chưa đồng ý.")
    assert store.resolve_voice("Giọng Bị Khiếu Nại") is None
    assert "Giọng Bị Khiếu Nại" not in [v.id for v in store.list_clone_voices()]
    takedowns = store.list_takedowns()
    assert len(takedowns) == 1
    assert takedowns[0]["name"] == "Giọng Bị Khiếu Nại"
    assert "khiếu nại" in takedowns[0]["reason"]
    with pytest.raises(ValueError, match="lý do"):
        store.clone_voice("Giọng Bị Khiếu Nại 2", SAMPLE_WAV,
                          consent=True, consent_text=CONSENT_TEXT)
        store.takedown("Giọng Bị Khiếu Nại 2", reason="   ")


def test_khong_ghi_de_assets_voices_cua_package(store):
    """TK1.5: clone chỉ ghi file HP riêng — assets trong package không bị sửa."""
    import vieneu

    assets_path = Path(vieneu.__file__).parent / "assets" / "voices_v3_turbo.json"
    before = assets_path.read_bytes() if assets_path.is_file() else None
    store.clone_voice("Giọng Không Đè Assets", SAMPLE_WAV,
                      consent=True, consent_text=CONSENT_TEXT)
    after = assets_path.read_bytes() if assets_path.is_file() else None
    assert before == after, "assets/voices_v3_turbo.json đã bị ghi đè!"
