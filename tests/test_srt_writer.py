"""Test SrtWriter — suy mốc giờ (SPEC §3.3, TK1.6, test T3.1).

Quy tắc SPEC: chia chunk đúng như SDK (tối đa 256 ký tự), đo độ dài audio từng
chunk, cộng dồn + khoảng lặng theo gaps_to_silence 0,30/0,50/0,70 s TRỪ im lặng
mép đã đo (chỉ cộng phần zeros bù thêm), chia mốc trong chunk nhiều câu theo
tỉ lệ ký tự. Mục tiêu ±0,3 s/câu (10 câu đầu).

Test dùng audio numpy tổng hợp (mỗi chunk là tone có độ dài biết trước) nên
mốc kỳ vọng tính được chính xác, độc lập với SrtWriter.
"""
import numpy as np
import pytest

from hpvoice.audio.srt_writer import (
    GAPS_TO_SILENCE,
    SrtWriter,
    chunk_text,
    edge_silence_seconds,
    format_srt_time,
    split_sentences,
)

SR = 48000


def tone(dur, freq=440.0):
    t = np.arange(int(dur * SR)) / SR
    return (0.5 * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def test_hang_so_gaps_dung_spec():
    assert GAPS_TO_SILENCE == {"para": 0.70, "sentence": 0.50, "minor": 0.30}


def test_format_srt_time():
    assert format_srt_time(0.0) == "00:00:00,000"
    assert format_srt_time(61.5) == "00:01:01,500"
    assert format_srt_time(3661.123) == "01:01:01,123"


def test_split_sentences():
    s = split_sentences("Xin chào các bạn. Hôm nay trời đẹp! Bạn khỏe không? Tạm biệt.")
    assert s == ["Xin chào các bạn.", "Hôm nay trời đẹp!", "Bạn khỏe không?", "Tạm biệt."]


def test_chunk_text_toi_da_256_ky_tu():
    text = " ".join(f"Câu số {i} rất dài để kiểm tra việc chia chunk." for i in range(30))
    chunks, gaps = chunk_text(text)
    assert all(len(c) <= 256 for c in chunks)
    assert len(gaps) == len(chunks) - 1
    assert all(g in GAPS_TO_SILENCE for g in gaps)
    # Ghép lại (bỏ khoảng trắng nối) phải giữ đủ nội dung
    assert "".join(chunks).replace(" ", "") == text.replace(" ", "")


def test_edge_silence_seconds():
    # 0,2 s im lặng đầu + tone 0,5 s + 0,3 s im lặng cuối
    y = np.concatenate([np.zeros(int(0.2 * SR), dtype=np.float32), tone(0.5),
                        np.zeros(int(0.3 * SR), dtype=np.float32)])
    lead, tail = edge_silence_seconds(y, SR)
    assert lead == pytest.approx(0.2, abs=0.02)
    assert tail == pytest.approx(0.3, abs=0.02)


def test_moc_mot_chunk_hai_cau_chia_theo_ti_le_ky_tu():
    """Một chunk 4 s chứa 2 câu: câu ngắn (10 ký tự) / câu dài (30 ký tự)."""
    w = SrtWriter()
    text = "Chào bạn. Hôm nay mình giới thiệu sản phẩm mới rất hay."
    audios = [tone(4.0)]
    cues = w.build_cues(text, audios, SR)
    assert len(cues) == 2
    assert cues[0].start_s == pytest.approx(0.0, abs=0.01)
    # Chia theo tỉ lệ ký tự TRÊN CHUNK (chunk dài 55 ký tự: câu 1 = 9 ký tự,
    # 1 ký tự khoảng trắng nối, câu 2 = 45 ký tự).
    assert cues[0].end_s == pytest.approx(4.0 * 9 / 55, abs=0.02)
    assert cues[1].start_s == pytest.approx(4.0 * 10 / 55, abs=0.02)
    assert cues[1].end_s == pytest.approx(4.0, abs=0.01)


def test_moc_cong_don_chi_bu_zeros_thieu():
    """2 chunk, ranh giới sentence (0,50 s). Chunk 1 đuôi im lặng 0,30 s,
    chunk 2 đầu im lặng 0,10 s → chỉ bù thêm 0,10 s (không cộng cả 0,50 s).

    Text đủ dài để SDK chia 2 chunk: chunk 1 = câu 1 + câu 2, chunk 2 = câu 3.
    """
    w = SrtWriter()
    s1 = "Câu thứ nhất rất hay và dài để kiểm tra việc chia chunk đúng như SDK chia, thêm nội dung cho đủ dài."
    s2 = "Câu thứ hai cũng rất hay và dài để kiểm tra việc chia chunk đúng như SDK chia, thêm nội dung cho đủ dài."
    s3 = "Câu thứ ba cũng rất hay và dài để kiểm tra việc chia chunk đúng như SDK chia, thêm nội dung cho đủ dài."
    text = f"{s1} {s2} {s3}"
    chunks, gaps = chunk_text(text)
    assert len(chunks) == 2, chunks
    assert gaps == ["sentence"]
    c1 = np.concatenate([tone(1.0), np.zeros(int(0.30 * SR), dtype=np.float32)])
    c2 = np.concatenate([np.zeros(int(0.10 * SR), dtype=np.float32), tone(1.0)])
    cues = w.build_cues(text, [c1, c2], SR)
    assert len(cues) == 3
    # Chunk 1 dài 1,30 s; câu 1 chiếm len(s1)/(len(chunk1)) tỉ lệ.
    dur1 = 1.30
    assert cues[0].end_s == pytest.approx(dur1 * len(s1) / len(chunks[0]), abs=0.03)
    # Mốc câu 3 = 1,30 + bù zeros 0,10 = 1,40 (không phải 1,30 + 0,50 = 1,80)
    assert cues[2].start_s == pytest.approx(1.40, abs=0.03)
    assert cues[2].end_s == pytest.approx(1.40 + 1.10, abs=0.03)


def test_moc_khi_im_lang_mep_da_du_khong_cong_them():
    """Đuôi chunk 1 đã im lặng 0,60 s ≥ 0,50 s → bù 0, không cộng thêm."""
    w = SrtWriter()
    s1 = "Câu thứ nhất rất hay và dài để kiểm tra việc chia chunk đúng như SDK chia, thêm nội dung cho đủ dài."
    s2 = "Câu thứ hai cũng rất hay và dài để kiểm tra việc chia chunk đúng như SDK chia, thêm nội dung cho đủ dài."
    s3 = "Câu thứ ba cũng rất hay và dài để kiểm tra việc chia chunk đúng như SDK chia, thêm nội dung cho đủ dài."
    text = f"{s1} {s2} {s3}"
    chunks, gaps = chunk_text(text)
    assert len(chunks) == 2
    c1 = np.concatenate([tone(1.0), np.zeros(int(0.60 * SR), dtype=np.float32)])
    c2 = tone(1.0)
    cues = w.build_cues(text, [c1, c2], SR)
    assert cues[2].start_s == pytest.approx(1.60, abs=0.02)


def test_cau_bi_cat_cuoc_buc_qua_hai_chunk():
    """Một câu dài > 256 ký tự bị cắt cưỡng bức qua 2 chunk: mốc lấy theo
    tỉ lệ ký tự ở cả hai chunk, câu vẫn là một cue duy nhất."""
    w = SrtWriter()
    text = "Đây là một câu rất dài " + "và cứ tiếp tục mãi " * 20 + "cho tới khi hết."
    assert len(text) > 256
    chunks, _ = chunk_text(text)
    assert len(chunks) >= 2
    audios = [tone(2.0) for _ in chunks]
    cues = w.build_cues(text, audios, SR)
    assert len(cues) == 1
    assert cues[0].start_s == pytest.approx(0.0, abs=0.01)
    # Hết ở cuối chunk cuối (+ bù zeros giữa chunk, minor 0,30 s, mép tone
    # không im lặng nên bù đủ 0,30 s mỗi khe)
    expect = 2.0 * len(chunks) + 0.30 * (len(chunks) - 1)
    assert cues[0].end_s == pytest.approx(expect, abs=0.05)


def test_to_srt_dinh_dang_chuan():
    w = SrtWriter()
    text = "Chào bạn. Tạm biệt nhé."
    cues = w.build_cues(text, [tone(2.0)], SR)
    srt = w.to_srt(cues)
    assert srt.startswith("1\n00:00:00,000 --> 00:00:00,7")
    assert "\n2\n" in srt
    assert "Chào bạn." in srt and "Tạm biệt nhé." in srt


def test_write_srt_ghi_file(tmp_path):
    w = SrtWriter()
    cues = w.build_cues("Chào bạn. Tạm biệt nhé.", [tone(2.0)], SR)
    p = tmp_path / "out.srt"
    w.write_srt(p, cues)
    assert p.exists()
    assert "Chào bạn." in p.read_text(encoding="utf-8")
