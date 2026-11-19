"""Test PreviewCache nghe thử V3/V4 (TK3.1, SPEC §3.3 Y7, test T3.1).

- V3: mẫu thu sẵn — tạo lần đầu rồi cache trên đĩa, lần 2 không tổng hợp lại.
- V4: cache theo khóa (voice_id + câu mẫu) — nghe lần 2 không gọi lại API.
- Ước tính phí preview = max(50, len(câu mẫu)) × multiplier (TH-05).
- Trần cache 200 MB (mặc định), vượt trần dọn file cũ nhất.
- Dùng FakeEngine (không load model), KHÔNG gọi API V4 thật.
"""
import pytest

from hpvoice.audio.preview_cache import (
    DEFAULT_PREVIEW_CACHE_MB,
    MAX_PREVIEW_CACHE_BYTES,
    MIN_BILLABLE_CHARS,
    PreviewCache,
    billable_chars,
    estimate_preview_cost,
    preview_key,
)


def _wav_bytes(seed: str = "x") -> bytes:
    """Bytes giả làm audio WAV (nội dung không quan trọng, chỉ cần khác nhau theo seed)."""
    return b"RIFF" + seed.encode("utf-8") * 100


def test_preview_key_phaan_biet_engine_giong_cau_mau():
    """Khóa V3 khác V4, khác giọng khác khóa, khác câu mẫu khác khóa."""
    assert preview_key("v3", "Hải Đăng", "Xin chào.") != preview_key("v4", "Hải Đăng", "Xin chào.")
    assert preview_key("v3", "Hải Đăng", "Xin chào.") != preview_key("v3", "Mai Anh", "Xin chào.")
    assert preview_key("v3", "Hải Đăng", "Xin chào.") != preview_key("v3", "Hải Đăng", "Tạm biệt.")
    assert preview_key("v3", "Hải Đăng", "Xin chào.") == preview_key("v3", "Hải Đăng", "Xin chào.")


def test_preview_key_khong_nhan_engine_la():
    with pytest.raises(ValueError, match="Engine"):
        preview_key("v9", "Hải Đăng", "Xin chào.")
    with pytest.raises(ValueError, match="giọng"):
        preview_key("v3", "", "Xin chào.")
    with pytest.raises(ValueError, match="Câu mẫu"):
        preview_key("v3", "Hải Đăng", "   ")


def test_billable_chars_toi_thieu_50():
    """Câu mẫu ≤ 60 ký tự vẫn tính phí tối thiểu 50 ký tự (Y7/R2)."""
    assert MIN_BILLABLE_CHARS == 50
    assert billable_chars("Xin chào!") == 50  # 9 ký tự -> 50
    assert billable_chars("x" * 50) == 50
    assert billable_chars("x" * 55) == 55
    assert billable_chars("x" * 100) == 100


def test_estimate_preview_cost_cong_thuc():
    """Phí = max(50, ký tự) × billingMultiplier × globalMultiplier (docs/v4-billing.md)."""
    assert estimate_preview_cost("Xin chào!") == 50 * 3.4 * 1.0  # 170 token
    assert estimate_preview_cost("x" * 55) == 55 * 3.4 * 1.0  # 187 token
    assert estimate_preview_cost("x" * 100, engine_multiplier=2.0, global_multiplier=1.5) == 300.0
    # Khớp hàm gốc của V4Engine (1 công thức duy nhất, không 2 số khác nhau).
    from hpvoice.engines.v4_engine import estimate_cost_chars

    for text in ("Xin chào!", "x" * 55, "x" * 1000):
        assert estimate_preview_cost(text) == estimate_cost_chars(len(text), 3.4, 1.0)


def test_tran_cache_mac_dinh_200mb(tmp_path):
    assert DEFAULT_PREVIEW_CACHE_MB == 200
    assert MAX_PREVIEW_CACHE_BYTES == 200 * 1024 * 1024
    cache = PreviewCache(cache_dir=tmp_path / "preview")
    assert cache.max_bytes == 200 * 1024 * 1024


def test_v3_tao_lan_dau_roi_cache_lan_2_khong_tong_hop_lai(tmp_path, fake_engine):
    """Y7 (V3): lần 1 MISS -> tổng hợp; lần 2 HIT -> không gọi engine nữa."""
    cache = PreviewCache(cache_dir=tmp_path / "preview")
    calls_before = len(fake_engine.calls)

    def synthesize(sample_text, voice_id):
        result = fake_engine.synthesize(sample_text, voice_id)
        import io

        import soundfile as sf

        buf = io.BytesIO()
        sf.write(buf, result.samples, result.sample_rate, format="WAV", subtype="PCM_16")
        return buf.getvalue()

    data1, from_cache1 = cache.get_or_create("v3", "Hải Đăng", "Xin chào.", synthesize)
    assert from_cache1 is False
    assert data1[:4] == b"RIFF"
    assert len(fake_engine.calls) == calls_before + 1

    data2, from_cache2 = cache.get_or_create("v3", "Hải Đăng", "Xin chào.", synthesize)
    assert from_cache2 is True
    assert data2 == data1
    assert len(fake_engine.calls) == calls_before + 1  # không tổng hợp lại


def test_v4_cache_theo_khoa_giong_cau_mau(tmp_path):
    """Y7 (V4): cùng voice_id + câu mẫu -> HIT; đổi giọng/câu -> MISS."""
    cache = PreviewCache(cache_dir=tmp_path / "preview")
    calls = {"n": 0}

    def synthesize(sample_text, voice_id):
        calls["n"] += 1
        return _wav_bytes(f"{voice_id}:{sample_text}")

    cache.get_or_create("v4", "Hạ Vy", "Xin chào.", synthesize)
    assert calls["n"] == 1
    cache.get_or_create("v4", "Hạ Vy", "Xin chào.", synthesize)
    assert calls["n"] == 1  # nghe lần 2 không gọi lại API
    cache.get_or_create("v4", "Hạ Vy", "Tạm biệt.", synthesize)
    assert calls["n"] == 2  # câu mẫu khác -> tổng hợp mới
    cache.get_or_create("v4", "Minh Quân", "Xin chào.", synthesize)
    assert calls["n"] == 3  # giọng khác -> tổng hợp mới


def test_get_put_tron_vong_va_usage(tmp_path):
    cache = PreviewCache(cache_dir=tmp_path / "preview")
    assert cache.get_preview("v3", "Hải Đăng", "Xin chào.") is None
    assert cache.has_preview("v3", "Hải Đăng", "Xin chào.") is False
    path = cache.put_preview("v3", "Hải Đăng", "Xin chào.", _wav_bytes("a"))
    assert path.is_file()
    assert cache.get_preview("v3", "Hải Đăng", "Xin chào.") == _wav_bytes("a")
    assert cache.has_preview("v3", "Hải Đăng", "Xin chào.") is True
    assert cache.usage_bytes() == len(_wav_bytes("a"))
    assert cache.usage_mb() == pytest.approx(len(_wav_bytes("a")) / 1024 / 1024)
    assert cache.clear() == 1
    assert cache.get_preview("v3", "Hải Đăng", "Xin chào.") is None


def test_vuot_tran_don_file_cu_nhat(tmp_path):
    """Vượt trần -> dọn file cũ nhất (mtime) cho tới khi vừa trần."""
    import time

    cache = PreviewCache(cache_dir=tmp_path / "preview", max_bytes=250)
    cache.put_preview("v3", "Hải Đăng", "Câu một.", b"a" * 100)
    time.sleep(0.02)
    cache.put_preview("v3", "Mai Anh", "Câu hai.", b"b" * 100)
    time.sleep(0.02)
    cache.put_preview("v3", "Thu Hà", "Câu ba.", b"c" * 100)
    assert cache.usage_bytes() <= 250
    # File cũ nhất (câu một) đã bị dọn, file mới nhất còn lại.
    assert cache.get_preview("v3", "Hải Đăng", "Câu một.") is None
    assert cache.get_preview("v3", "Thu Hà", "Câu ba.") == b"c" * 100


def test_get_or_create_tu_choi_du_lieu_rong(tmp_path):
    cache = PreviewCache(cache_dir=tmp_path / "preview")
    with pytest.raises(ValueError, match="rỗng"):
        cache.get_or_create("v3", "Hải Đăng", "Xin chào.", lambda t, v: b"")
    with pytest.raises(ValueError, match="rỗng"):
        cache.get_or_create("v3", "Hải Đăng", "Xin chào.", lambda t, v: None)
