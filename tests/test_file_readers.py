"""Test FileReaders (TK2.7 + TK2.12, T3.4 — file mẫu tự tạo).

Gồm 1 PDF scan giả (chỉ ảnh, không text layer) + 1 PDF có bảng.
"""

import fitz  # PyMuPDF
import pytest
from docx import Document

from hpvoice.files.readers import (
    COPYRIGHT_NOTE,
    FileReaders,
    ScannedPdfError,
    clean_text,
)


def make_pdf(path, pages_text):
    doc = fitz.open()
    for text in pages_text:
        page = doc.new_page()
        page.insert_text((72, 72), text, fontsize=12)
    doc.save(str(path))
    doc.close()


def make_pdf_with_table(path):
    """PDF có bảng thật (đường kẻ + text) để test giữ thứ tự cell."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 40), "Bang gia san pham", fontsize=12)
    # Vẽ bảng 2x2 bằng đường kẻ.
    x0, y0, cw, rh = 72, 80, 150, 30
    for r in range(3):
        page.draw_line((x0, y0 + r * rh), (x0 + 2 * cw, y0 + r * rh))
    for c in range(3):
        page.draw_line((x0 + c * cw, y0), (x0 + c * cw, y0 + 2 * rh))
    cells = [["Ten", "Gia"], ["Kem A", "100"], ["Kem B", "200"]]
    for r, row in enumerate(cells):
        for c, val in enumerate(row):
            page.insert_text((x0 + c * cw + 5, y0 + r * rh + 20), val, fontsize=11)
    doc.save(str(path))
    doc.close()


def make_scanned_pdf(path):
    """PDF scan giả: trang chỉ có ảnh (pixmap đặc), không có text layer."""
    doc = fitz.open()
    page = doc.new_page()
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 200, 200))
    pix.set_rect(pix.irect, (200, 200, 200))  # ảnh xám đặc
    page.insert_image(fitz.Rect(72, 72, 272, 272), pixmap=pix)
    doc.save(str(path))
    doc.close()


def test_read_pdf_two_pages(tmp_path):
    # LƯU Ý fixture: font mặc định của PyMuPDF không có dấu tiếng Việt nên
    # test dùng text không dấu (giới hạn của fixture, không phải của reader).
    pdf = tmp_path / "hai-trang.pdf"
    make_pdf(pdf, ["Trang mot: Xin chao cac ban.", "Trang hai: Tam biet nhe."])
    result = FileReaders().read_file(pdf)
    assert result.kind == "pdf"
    assert result.pages == 2
    assert "Xin chao cac ban" in result.text
    assert "Tam biet nhe" in result.text
    assert result.copyright_note == COPYRIGHT_NOTE
    assert result.read_seconds >= 0


def test_read_pdf_table_keeps_cell_order(tmp_path):
    pdf = tmp_path / "bang.pdf"
    make_pdf_with_table(pdf)
    result = FileReaders().read_file(pdf)
    text = result.text
    # Thứ tự cell phải đúng: Ten -> Gia -> Kem A -> 100 -> Kem B -> 200.
    idx = [text.find(v) for v in ["Ten", "Gia", "Kem A", "100", "Kem B", "200"]]
    assert all(i >= 0 for i in idx), f"thiếu cell trong text trích: {text!r}"
    assert idx == sorted(idx)


def test_read_pdf_scanned_reports_no_ocr(tmp_path):
    pdf = tmp_path / "scan.pdf"
    make_scanned_pdf(pdf)
    with pytest.raises(ScannedPdfError) as excinfo:
        FileReaders().read_file(pdf)
    assert "v1 không OCR" in str(excinfo.value)


def test_read_docx_table_order(tmp_path):
    path = tmp_path / "bang.docx"
    doc = Document()
    doc.add_paragraph("Đoạn mở đầu.")
    table = doc.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Cột A"
    table.cell(0, 1).text = "Cột B"
    table.cell(1, 0).text = "Giá trị 1"
    table.cell(1, 1).text = "Giá trị 2"
    doc.add_paragraph("Đoạn kết thúc.")
    doc.save(str(path))
    result = FileReaders().read_file(path)
    assert result.kind == "docx"
    text = result.text
    # Thứ tự đúng trong body: mở đầu -> bảng -> kết thúc (không đọc hết
    # paragraph rồi mới tới table).
    idx = [text.find(v) for v in ["Đoạn mở đầu", "Cột A", "Giá trị 1", "Đoạn kết thúc"]]
    assert all(i >= 0 for i in idx), f"text trích: {text!r}"
    assert idx == sorted(idx)


def test_read_txt_and_clean(tmp_path):
    path = tmp_path / "ghi-chu.txt"
    path.write_text("Xin   chào\n\n\n\ncác   bạn!  Công thức: E = mc^2.\n", encoding="utf-8")
    result = FileReaders().read_file(path)
    assert result.kind == "txt"
    assert "Xin chào" in result.text
    assert "E = mc^2" in result.text  # giữ công thức
    assert "   " not in result.text


def test_clean_text():
    assert clean_text("a   b\n\n\n\nc") == "a b\n\nc"
    assert clean_text("") == ""


def test_read_errors(tmp_path):
    readers = FileReaders()
    with pytest.raises(ValueError, match="không tồn tại"):
        readers.read_file(tmp_path / "khong-co.pdf")
    bad = tmp_path / "x.xyz"
    bad.write_text("x")
    with pytest.raises(ValueError, match="không hỗ trợ"):
        readers.read_file(bad)
    pdf = tmp_path / "hai-trang.pdf"
    make_pdf(pdf, ["Một.", "Hai."])
    with pytest.raises(ValueError, match="500 trang|vượt giới hạn"):
        FileReaders(max_pages=1).read_file(pdf)
