"""Test ViTextNormalizer — TK1.10 / TH-27 (test T1.9).

Chuẩn hoá số/tiền/ngày/giờ/đơn vị tiếng Việt thành chữ đọc được, chạy trước
TextPreprocess; có công tắc bật/tắt.
"""
from hpvoice.audio.normalizer import ViTextNormalizer


def norm(text):
    return ViTextNormalizer(enabled=True).normalize(text)


def test_so_nguyen_co_ban():
    assert norm("có 3 người") == "có ba người"
    assert norm("15 sản phẩm") == "mười lăm sản phẩm"
    assert norm("21 ngày") == "hai mươi mốt ngày"
    assert norm("105 hộp") == "một trăm linh năm hộp"
    assert norm("1000 đơn") == "một nghìn đơn"
    assert norm("2026 rồi") == "hai nghìn không trăm hai mươi sáu rồi"


def test_tien_te():
    assert norm("Giá 1.500.000đ") == "Giá một triệu năm trăm nghìn đồng"
    assert norm("chỉ 50.000 đồng") == "chỉ năm mươi nghìn đồng"
    assert norm("giá 500k") == "giá năm trăm nghìn đồng"
    assert norm("giảm 20%") == "giảm hai mươi phần trăm"


def test_ngay_thang():
    assert norm("ngày 15/11/2026") == "ngày mười lăm tháng mười một năm hai nghìn không trăm hai mươi sáu"
    assert norm("hạn 15/11") == "hạn mười lăm tháng mười một"


def test_gio():
    assert norm("lúc 19h30") == "lúc mười chín giờ ba mươi phút"
    assert norm("lúc 7h") == "lúc bảy giờ"
    assert norm("lúc 7:30") == "lúc bảy giờ ba mươi phút"


def test_don_vi_va_so_thap_phan():
    assert norm("nặng 3,5kg") == "nặng ba phẩy năm ki-lô-gam"
    assert norm("dài 2,5km") == "dài hai phẩy năm ki-lô-mét"
    assert norm("cao 10cm") == "cao mười xăng-ti-mét"
    assert norm("dung tích 2l") == "dung tích hai lít"
    assert norm("giá 3.5 triệu") == "giá ba phẩy năm triệu"


def test_tat_normalizer_giu_nguyen_text():
    n = ViTextNormalizer(enabled=False)
    assert n.normalize("Giá 1.500.000đ, ngày 15/11/2026, lúc 19h30") == (
        "Giá 1.500.000đ, ngày 15/11/2026, lúc 19h30"
    )


def test_text_khong_co_so_giu_nguyen():
    assert norm("Xin chào các bạn, hôm nay trời đẹp.") == "Xin chào các bạn, hôm nay trời đẹp."


def test_so_lon_trieu_ty():
    assert norm("2.000.000.000đ") == "hai tỷ đồng"
    assert norm("1.250.000đ") == "một triệu hai trăm năm mươi nghìn đồng"
