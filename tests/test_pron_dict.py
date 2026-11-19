"""Test PronDict — TK1.7 (SPEC §3.3: CRUD + CSV import/export + áp trước infer,
giới hạn 2.000 mục).
"""
import csv

import pytest

from hpvoice.voices.pron_dict import PronDict, PronDictError

MAX_ITEMS = 2000


def test_crud_co_ban():
    d = PronDict()
    d.add("Obagi", "ô-ba-gi")
    assert d.get("Obagi") == "ô-ba-gi"
    assert d.count() == 1
    d.add("Obagi", "ô ba gi")  # sửa (ghi đè)
    assert d.get("Obagi") == "ô ba gi"
    assert d.count() == 1
    assert d.remove("Obagi") is True
    assert d.get("Obagi") is None
    assert d.remove("Obagi") is False


def test_ap_truoc_infer_thay_dung_tu():
    d = PronDict()
    d.add("Obagi", "ô-ba-gi")
    d.add("Retinol", "rê-ti-nôn")
    out = d.apply("Kem Obagi chứa Retinol 1% rất tốt, Obagi là thương hiệu lớn.")
    assert out == "Kem ô-ba-gi chứa rê-ti-nôn 1% rất tốt, ô-ba-gi là thương hiệu lớn."


def test_ap_khong_thay_tu_con():
    """'Obagi' không được thay bên trong 'Obagixyz'."""
    d = PronDict()
    d.add("Obagi", "ô-ba-gi")
    out = d.apply("Từ Obagixyz không đổi, còn Obagi thì đổi.")
    assert "Obagixyz" in out
    assert out.count("ô-ba-gi") == 1


def test_ap_tu_dai_truoc_tu_ngan():
    d = PronDict()
    d.add("kem chống nắng", "kem chống nắng đọc chậm")
    d.add("kem", "kem đọc nhanh")
    out = d.apply("Thoa kem chống nắng mỗi ngày.")
    assert "kem chống nắng đọc chậm" in out
    assert "kem đọc nhanh" not in out


def test_gioi_han_2000_muc():
    d = PronDict()
    for i in range(MAX_ITEMS):
        d.add(f"tu{i}", f"đọc {i}")
    assert d.count() == MAX_ITEMS
    with pytest.raises(PronDictError, match="2.000"):
        d.add("tu-vuot", "đọc vượt")


def test_csv_import_export(tmp_path):
    d = PronDict()
    d.add("Obagi", "ô-ba-gi")
    d.add("La Roche-Posay", "la-rốc-pô-dây")
    p = tmp_path / "dict.csv"
    d.export_csv(p)
    with open(p, encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows[0] == ["word", "reading"]
    assert ["Obagi", "ô-ba-gi"] in rows

    d2 = PronDict()
    n = d2.import_csv(p)
    assert n == 2
    assert d2.get("La Roche-Posay") == "la-rốc-pô-dây"
    # Import lại (ghi đè) không tăng số mục
    assert d2.import_csv(p) == 2
    assert d2.count() == 2


def test_csv_import_bo_qua_dong_trong_va_tieu_de():
    d = PronDict()
    import io
    text = "word,reading\nObagi,ô-ba-gi\n\nRetinol,rê-ti-nôn\n"
    n = d.import_csv(io.StringIO(text))
    assert n == 2
    assert d.count() == 2


def test_json_save_load(tmp_path):
    d = PronDict()
    d.add("Obagi", "ô-ba-gi")
    p = tmp_path / "dict.json"
    d.save(p)
    d2 = PronDict.load(p)
    assert d2.get("Obagi") == "ô-ba-gi"


def test_tu_rong_hoac_doc_rong_bao_loi():
    d = PronDict()
    with pytest.raises(PronDictError):
        d.add("", "đọc")
    with pytest.raises(PronDictError):
        d.add("Obagi", "")
