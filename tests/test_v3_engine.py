"""Test V3Engine (TK1.2) — T1.2, T1.3, T1.5, T1.6.

Chạy với model thật (đã cache). Ghi số đo thật ra evidence/tk1-engine/.

Lưu ý trung thực (SPEC §10.5): ngưỡng "mượt" (RTF <= 1, chunk đầu <= 500 ms)
được đo trên CPU tham chiếu là máy Windows thật của anh (C6). Trên VM này CPU
chia sẻ ~1,5 CPU nên số đo CHẬM hơn ngưỡng — test assert TÍNH NĂNG (WAV thật
48 kHz, đủ 25 giọng, stream ra chunk, batch đúng thứ tự) và GHI SỐ ĐO THẬT,
không assert ngưỡng mượt (ngưỡng đó chờ kiểm chứng thật, không tính là đạt).
"""

import json
import time

import numpy as np
import pytest

from tk1_helpers import EVIDENCE_DIR, SAMPLE_WAV, SHORT_TEXT, VOICE, engine_context


@pytest.fixture(scope="module")
def engine_fp32():
    with engine_context("fp32") as engine:
        yield engine


def test_engine_khoi_tao_lazy_va_load_model_that(engine_fp32):
    """T1.7 (phần engine): ensure_loaded nạp model thật, ghi thời gian load."""
    assert engine_fp32.is_loaded
    assert engine_fp32.load_seconds is not None
    assert engine_fp32.load_seconds > 0
    assert engine_fp32.sample_rate == 48000
    assert engine_fp32.precision == "fp32"
    (EVIDENCE_DIR / "engine-load.json").write_text(
        json.dumps(
            {"precision": "fp32", "load_seconds": round(engine_fp32.load_seconds, 1),
             "sample_rate": engine_fp32.sample_rate},
            ensure_ascii=False, indent=2,
        ),
        encoding="utf-8",
    )


def test_t12_wav_that_48khz_giong_preset(engine_fp32, tmp_path):
    """T1.2: WAV thật 48 kHz, mono, độ dài > 0, đúng giọng preset."""
    import soundfile as sf

    t0 = time.perf_counter()
    result = engine_fp32.synthesize("Xin chào các bạn!", VOICE)
    gen_s = time.perf_counter() - t0
    assert result.sample_rate == 48000
    assert result.engine == "v3"
    assert result.voice == VOICE
    assert len(result.samples) > 0
    assert result.duration_s > 0
    assert np.max(np.abs(result.samples)) > 0  # có tín hiệu thật, không im lặng
    wav_path = tmp_path / "t1_2.wav"
    engine_fp32.save_wav(result, str(wav_path))
    info = sf.info(str(wav_path))
    assert info.samplerate == 48000
    assert info.channels == 1
    rtf = gen_s / result.duration_s
    (EVIDENCE_DIR / "t12-wav.json").write_text(
        json.dumps(
            {"text": "Xin chào các bạn!", "voice": VOICE, "sample_rate": 48000,
             "duration_s": round(result.duration_s, 2), "gen_seconds": round(gen_s, 2),
             "rtf": round(rtf, 3)},
            ensure_ascii=False, indent=2,
        ),
        encoding="utf-8",
    )


def test_t13_liet_ke_25_giong(engine_fp32):
    """T1.3: đủ 25 giọng, đủ 10 featured, default Hải Đăng, không hardcode tên."""
    voices = engine_fp32.list_preset_voices()
    assert len(voices) == 25, f"Preset phải có 25 giọng, thực tế {len(voices)}"
    ids = [v.id for v in voices]
    assert VOICE in ids
    featured = [v for v in voices if v.featured is not None]
    assert len(featured) >= 10, f"Phải có >= 10 giọng featured, thực tế {len(featured)}"
    assert len(set(ids)) == 25  # không trùng tên
    (EVIDENCE_DIR / "t13-voices.json").write_text(
        json.dumps(
            [{"id": v.id, "label": v.label, "gender": v.gender,
              "featured": v.featured} for v in voices],
            ensure_ascii=False, indent=2,
        ),
        encoding="utf-8",
    )


def test_giong_sai_bao_loi_ro(engine_fp32):
    """T1.3 (nhánh lỗi): giọng không tồn tại -> ValueError rõ ràng."""
    with pytest.raises(ValueError, match="không tồn tại"):
        engine_fp32.synthesize(SHORT_TEXT, "Không Có Giọng Này")


def test_text_rong_va_text_qua_dai_bao_loi(engine_fp32):
    """Giới hạn text: rỗng -> lỗi; > 20000 ký tự -> lỗi rõ."""
    with pytest.raises(ValueError, match="rỗng"):
        engine_fp32.synthesize("   ", VOICE)
    with pytest.raises(ValueError, match="vượt giới hạn"):
        engine_fp32.synthesize("a" * 20001, VOICE)


def test_t15_stream_chunk_dau_va_chunk_tiep_theo(engine_fp32):
    """T1.5: stream yield chunk, chunk đầu có audio; GHI độ trễ chunk đầu thật.

    Không assert <= 500 ms trên VM này (CPU chia sẻ chậm ~3x so với i5 12th-gen;
    số đo thật xem evidence/tk1-engine/t15-stream.json — chờ kiểm chứng thật
    trên máy Windows của anh, C6). Assert tính năng: chunk đầu về, có tín hiệu,
    các chunk sau không rỗng, nối lại thành audio đầy đủ.
    """
    t0 = time.perf_counter()
    chunks = []
    first_latency = None
    for chunk in engine_fp32.synthesize_stream(SHORT_TEXT, VOICE):
        if first_latency is None:
            first_latency = time.perf_counter() - t0
        chunks.append(chunk)
    assert len(chunks) >= 1
    assert all(c.sample_rate == 48000 and len(c.samples) > 0 for c in chunks)
    total_s = sum(c.duration_s for c in chunks)
    assert total_s > 0
    (EVIDENCE_DIR / "t15-stream.json").write_text(
        json.dumps(
            {"precision": "fp32", "num_chunks": len(chunks),
             "first_chunk_latency_s": round(first_latency, 3),
             "total_duration_s": round(total_s, 2),
             "target_first_chunk_s": 0.5,
             "target_met_on_this_vm": bool(first_latency and first_latency <= 0.5),
             "note": "Muc tieu <=500ms do lai tren may Windows that (C6)."},
            ensure_ascii=False, indent=2,
        ),
        encoding="utf-8",
    )


def test_t16_batch_10_cau_dung_thu_tu_va_giong(engine_fp32):
    """T1.6: batch 10 câu -> 10 audio, đúng thứ tự (độ dài tương ứng từng câu),
    đúng giọng; GHI RTF batch thật để đối chiếu RTF đơn (<= 1,2x)."""
    texts = [
        "Xin chào các bạn.",
        "Hôm nay trời đẹp quá.",
        "Đây là câu thứ ba.",
        "Giọng đọc tiếng Việt rất tự nhiên.",
        "HP Voice Studio chạy hoàn toàn trên máy.",
        "Câu ngắn.",
        "Một câu dài hơn một chút để kiểm tra thứ tự batch có bị lẫn không nhé.",
        "Bảy.",
        "Tám tám tám.",
        "Câu cuối cùng của batch.",
    ]
    t0 = time.perf_counter()
    results = engine_fp32.synthesize_batch(texts, VOICE)
    gen_s = time.perf_counter() - t0
    assert len(results) == len(texts)
    assert all(r.voice == VOICE and r.sample_rate == 48000 for r in results)
    assert all(len(r.samples) > 0 for r in results)
    # Đúng thứ tự: câu dài ("Một câu dài hơn...") phải cho audio dài hơn câu "Bảy.".
    assert results[6].duration_s > results[7].duration_s
    total_audio = sum(r.duration_s for r in results)
    batch_rtf = gen_s / total_audio if total_audio else float("nan")
    (EVIDENCE_DIR / "t16-batch.json").write_text(
        json.dumps(
            {"num_items": len(texts), "gen_seconds": round(gen_s, 2),
             "total_audio_s": round(total_audio, 2),
             "batch_rtf": round(batch_rtf, 3),
             "durations_s": [round(r.duration_s, 2) for r in results]},
            ensure_ascii=False, indent=2,
        ),
        encoding="utf-8",
    )


def test_precision_auto_theo_cpu():
    """TK1.2: precision 'auto' resolve theo CPU (VM này có VNNI -> int8)."""
    from hpvoice.engines import V3Engine
    from hpvoice.engines.cpu_detect import detect_cpu

    engine = V3Engine(precision="auto")
    assert engine.precision == detect_cpu().default_precision()
    engine.close()


def test_precision_sai_bao_loi():
    """Precision ngoài auto/fp32/int8 -> lỗi rõ ngay khi khởi tạo."""
    from hpvoice.engines import V3Engine

    with pytest.raises(ValueError, match="precision"):
        V3Engine(precision="int4")
