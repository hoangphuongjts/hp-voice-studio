"""Test TextPreprocess — thẻ [nghỉ]/cảm xúc (SPEC §3.3, TK1.6).

Chạy: .venv/bin/python -m pytest tests/test_text_preprocess.py -v
Không cần model, không import vieneu.
"""
import pytest

from hpvoice.audio.text_preprocess import (
    TextPreprocess,
    TextPreprocessError,
    ensure_no_pause_tag,
)

PP = TextPreprocess()


def test_khong_co_tag_tra_nguyen_text():
    r = PP.split("Xin chào các bạn, hôm nay mình giới thiệu sản phẩm mới.")
    assert len(r.segments) == 1
    assert r.segments[0].text == "Xin chào các bạn, hôm nay mình giới thiệu sản phẩm mới."
    assert r.segments[0].pause_after_s == 0.0
    assert r.leading_pause_s == 0.0


def test_the_cam_xuc_giu_nguyen_di_vao_infer():
    r = PP.split("Hay quá [cười] mình rất thích, thật sự [thở dài] mệt ghê [hắng giọng] rồi.")
    assert len(r.segments) == 1
    assert "[cười]" in r.segments[0].text
    assert "[thở dài]" in r.segments[0].text
    assert "[hắng giọng]" in r.segments[0].text


def test_nghi_giua_cau_cat_doan_va_giu_khoang_lang():
    r = PP.split("Xin chào các bạn. [nghỉ 2s] Hôm nay mình giới thiệu sản phẩm mới.")
    assert [s.text for s in r.segments] == [
        "Xin chào các bạn.",
        "Hôm nay mình giới thiệu sản phẩm mới.",
    ]
    assert r.segments[0].pause_after_s == pytest.approx(2.0)
    assert r.segments[1].pause_after_s == 0.0
    # Không đoạn nào còn chứa chuỗi [nghỉ
    assert all("[nghỉ" not in s.text for s in r.segments)


def test_nghi_ms_va_so_thap_phan_va_khoang_trang_va_hoa_thuong():
    r = PP.split("A. [nghỉ 500ms] B. [nghỉ 2.5s] C. [nghỉ 2 s] D. [nghỉ 1S] E. [nghỉ 250MS] F.")
    assert [s.pause_after_s for s in r.segments[:-1]] == pytest.approx(
        [0.5, 2.5, 2.0, 1.0, 0.25]
    )
    assert len(r.segments) == 6


def test_nghi_dau_cau_va_cuoi_cau_van_chen_silence():
    r = PP.split("[nghỉ 1s] Xin chào. Tạm biệt nhé. [nghỉ 500ms]")
    assert r.leading_pause_s == pytest.approx(1.0)
    assert len(r.segments) == 1
    assert r.segments[0].text == "Xin chào. Tạm biệt nhé."
    assert r.segments[0].pause_after_s == pytest.approx(0.5)


def test_nhieu_tag_lien_tiep_cong_don():
    r = PP.split("A. [nghỉ 2s][nghỉ 3s] B.")
    assert r.segments[0].pause_after_s == pytest.approx(5.0)
    assert [s.text for s in r.segments] == ["A.", "B."]


def test_tag_giua_tu_bao_loi_khong_tao():
    with pytest.raises(TextPreprocessError):
        PP.split("xin[nghỉ 1s]chào các bạn")


def test_tag_sai_dinh_dang_bao_loi():
    for bad in (
        "A. [nghỉ xyz] B.",
        "A. [nghỉ 2] B.",          # thiếu đơn vị
        "A. [nghỉ -1s] B.",        # số âm
        "A. [nghỉ 2x] B.",         # đơn vị lạ
        "A. [nghỉ] B.",            # thiếu số + đơn vị
    ):
        with pytest.raises(TextPreprocessError, match="nghỉ"):
            PP.split(bad)


def test_tag_vuot_10s_bao_loi():
    with pytest.raises(TextPreprocessError):
        PP.split("A. [nghỉ 11s] B.")
    with pytest.raises(TextPreprocessError):
        PP.split("A. [nghỉ 10001ms] B.")


def test_tong_lien_tiep_vuot_10s_bao_loi():
    with pytest.raises(TextPreprocessError):
        PP.split("A. [nghỉ 6s] [nghỉ 5s] B.")


def test_tong_lien_tiep_dung_10s_duoc_chap_nhan():
    r = PP.split("A. [nghỉ 6s] [nghỉ 4s] B.")
    assert r.segments[0].pause_after_s == pytest.approx(10.0)


def test_tag_canh_the_cam_xuc_tach_tai_nghi():
    r = PP.split("Hay quá [cười] [nghỉ 1s] tiếp tục nào.")
    assert r.segments[0].text == "Hay quá [cười]"
    assert r.segments[0].pause_after_s == pytest.approx(1.0)
    assert r.segments[1].text == "tiếp tục nào."


def test_ten_the_viet_hoa_sai_bao_loi():
    # SPEC: tên thẻ phải viết đúng "nghỉ" thường.
    with pytest.raises(TextPreprocessError):
        PP.split("A. [Nghỉ 1s] B.")


def test_khong_bao_gio_dua_nghi_vao_infer_hay_v4():
    """Mock assert: mọi đoạn đưa vào infer() và mọi request V4 đều sạch [nghỉ."""
    text = "Xin chào. [nghỉ 2s] Hôm nay [cười] rất vui. [nghỉ 500ms] Tạm biệt."
    r = PP.split(text)
    infer_inputs = [s.text for s in r.segments]
    assert infer_inputs  # có đoạn để infer
    for t in infer_inputs:
        ensure_no_pause_tag(t)
    # Mô phỏng body request V4 ghép từ các đoạn (kèm Idempotency-Key riêng từng đoạn)
    v4_bodies = [{"text": t, "idempotency_key": f"job-1-seg-{i}"} for i, t in enumerate(infer_inputs)]
    for body in v4_bodies:
        ensure_no_pause_tag(body["text"])
        assert "[nghỉ" not in body["text"]


def test_ensure_no_pause_tag_nem_loi_khi_con_tag():
    with pytest.raises(TextPreprocessError):
        ensure_no_pause_tag("Xin chào [nghỉ 2s] các bạn")


def test_text_rong():
    r = PP.split("")
    assert r.segments == []
    assert r.leading_pause_s == 0.0
    with pytest.raises(TextPreprocessError):
        PP.split("   [nghỉ 1s]   ")
