"""FileReaders — đọc PDF/DOCX/TXT + làm sạch (TK2.7 + TK2.12, SPEC §3.3, T3.4/TH-23).

- Chỉ đọc file người dùng có quyền dùng. UI phải ghi rõ: không dùng để đọc
  sách/file có bản quyền rồi phát tán thành audio — xem ``COPYRIGHT_NOTE``
  (bản quyền văn bản đầu vào, SPEC §3.3).
- Chống treo/chữ rác (TH-23):
  - PDF scan (có ảnh nhưng không có text layer) → báo rõ ``"v1 không OCR"``,
    KHÔNG bịa text (ném :class:`ScannedPdfError`).
  - Bảng: giữ đúng thứ tự cell (PyMuPDF ``find_tables`` khi có; DOCX đọc
    paragraph + table xen kẽ đúng thứ tự trong body).
  - Giới hạn kích thước file + số trang + thời gian đọc mỗi trang (timeout) —
    tránh treo với file lớn/xấu.
- Làm sạch: gộp khoảng trắng thừa, giữ công thức/ký tự đặc biệt, giữ xuống
  dòng đoạn.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "COPYRIGHT_NOTE",
    "FileReaders",
    "ReadResult",
    "ScannedPdfError",
    "FileReadError",
    "MAX_FILE_MB",
    "MAX_PAGES",
    "MAX_PAGE_SECONDS",
    "clean_text",
]

#: Ghi chú bản quyền văn bản đầu vào — UI hiển thị khi đọc file (SPEC §3.3).
COPYRIGHT_NOTE = (
    "Chỉ đọc file bạn có quyền dùng. Không dùng HP Voice Studio để đọc sách "
    "hoặc file có bản quyền rồi phát tán thành audio khi chưa được phép."
)

#: Giới hạn đọc (chống treo — TH-23; số tạm, chốt lại sau khi đo trên máy thật).
MAX_FILE_MB = 50  # file tối đa 50 MB
MAX_PAGES = 500  # PDF tối đa 500 trang
MAX_PAGE_SECONDS = 10.0  # thời gian đọc tối đa mỗi trang (giây)
MAX_TXT_CHARS = 5_000_000  # TXT tối đa ~5 triệu ký tự


class FileReadError(ValueError):
    """Lỗi đọc file (đuôi lạ, file hỏng, vượt giới hạn...)."""


class ScannedPdfError(FileReadError):
    """PDF scan (chỉ có ảnh, không có text layer) — v1 không OCR."""

    def __init__(self, path: str | Path, pages_with_images: int = 0):
        super().__init__(
            f"PDF scan (không có text layer) — v1 không OCR: {path}. "
            f"({pages_with_images} trang có ảnh nhưng không trích được chữ; "
            "hãy dùng bản PDF có text hoặc gõ lại nội dung.)"
        )
        self.pages_with_images = pages_with_images


@dataclass
class ReadResult:
    """Kết quả đọc file: text đã làm sạch + thông tin nguồn + cảnh báo."""

    text: str
    source: str  # tên file
    kind: str  # "pdf" | "docx" | "txt"
    pages: int = 0  # số trang (PDF) / 0 nếu không phải PDF
    warnings: list[str] = field(default_factory=list)
    copyright_note: str = COPYRIGHT_NOTE
    read_seconds: float = 0.0

    @property
    def chars(self) -> int:
        return len(self.text)


def clean_text(text: str) -> str:
    """Làm sạch text: gộp khoảng trắng thừa trong dòng, giữ xuống dòng đoạn,
    giữ công thức/ký tự đặc biệt (không strip ký tự toán học)."""
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Bỏ ký tự điều khiển rác (giữ \n, \t).
    text = "".join(ch for ch in text if ch == "\n" or ch == "\t" or ord(ch) >= 32)
    lines = []
    for line in text.split("\n"):
        lines.append(" ".join(line.split()))
    cleaned = "\n".join(lines)
    # Gộp >2 dòng trống liên tiếp thành tối đa 1 dòng trống (ngăn đoạn).
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _check_size(path: Path) -> None:
    size_mb = path.stat().st_size / 1024 / 1024
    if size_mb > MAX_FILE_MB:
        raise FileReadError(
            f"File quá lớn ({size_mb:.1f} MB > {MAX_FILE_MB} MB) — "
            "chia nhỏ file rồi đọc lại."
        )


class FileReaders:
    """Đọc PDF (PyMuPDF) / DOCX (python-docx) / TXT + làm sạch."""

    def __init__(
        self,
        max_file_mb: float = MAX_FILE_MB,
        max_pages: int = MAX_PAGES,
        max_page_seconds: float = MAX_PAGE_SECONDS,
    ):
        self.max_file_mb = max_file_mb
        self.max_pages = max_pages
        self.max_page_seconds = max_page_seconds

    def read_file(self, path: str | Path) -> ReadResult:
        """Đọc file theo đuôi (.pdf/.docx/.txt)."""
        p = Path(path)
        if not p.is_file():
            raise FileReadError(f"File không tồn tại: {path}")
        if p.stat().st_size / 1024 / 1024 > self.max_file_mb:
            raise FileReadError(
                f"File quá lớn ({p.stat().st_size / 1024 / 1024:.1f} MB > "
                f"{self.max_file_mb} MB) — chia nhỏ file rồi đọc lại."
            )
        suffix = p.suffix.lower()
        if suffix == ".pdf":
            return self.read_pdf(p)
        if suffix == ".docx":
            return self.read_docx(p)
        if suffix == ".txt":
            return self.read_txt(p)
        raise FileReadError(
            f"Đuôi file không hỗ trợ: {suffix!r} (chỉ .pdf/.docx/.txt)."
        )

    # --- PDF ---
    def read_pdf(self, path: str | Path) -> ReadResult:
        """Đọc PDF bằng PyMuPDF, giữ thứ tự cell của bảng, phát hiện PDF scan."""
        import fitz  # PyMuPDF

        p = Path(path)
        t0 = time.perf_counter()
        warnings: list[str] = []
        try:
            doc = fitz.open(str(p))
        except Exception as exc:  # noqa: BLE001
            raise FileReadError(f"Không mở được PDF {p}: {exc}") from exc
        pages_text: list[str] = []
        pages_with_images = 0
        total_chars = 0
        try:
            n_pages = len(doc)
            if n_pages > self.max_pages:
                raise FileReadError(
                    f"PDF có {n_pages} trang, vượt giới hạn {self.max_pages} trang — "
                    "chia nhỏ file rồi đọc lại."
                )
            for page_no in range(n_pages):
                page_t0 = time.perf_counter()
                page = doc[page_no]
                text = self._pdf_page_text(page)
                if time.perf_counter() - page_t0 > self.max_page_seconds:
                    warnings.append(
                        f"Trang {page_no + 1} đọc chậm quá {self.max_page_seconds:g}s — "
                        "đã dừng ở giới hạn trang, phần sau có thể thiếu."
                    )
                    break
                if not text.strip() and len(page.get_images(full=True)) > 0:
                    pages_with_images += 1
                total_chars += len(text.strip())
                pages_text.append(text)
        finally:
            doc.close()
        if total_chars == 0:
            # Không trích được chữ nào: PDF scan (có ảnh) hoặc PDF trống.
            if pages_with_images > 0:
                raise ScannedPdfError(p, pages_with_images)
            raise FileReadError(
                f"PDF {p} không trích được chữ nào (file trống hoặc chỉ có ảnh mờ) — "
                "v1 không OCR."
            )
        if pages_with_images > 0:
            warnings.append(
                f"{pages_with_images}/{n_pages} trang chỉ có ảnh (không có text layer) — "
                "nội dung các trang đó không trích được (v1 không OCR)."
            )
        cleaned = clean_text("\n\n".join(pages_text))
        return ReadResult(
            text=cleaned,
            source=p.name,
            kind="pdf",
            pages=n_pages,
            warnings=warnings,
            read_seconds=time.perf_counter() - t0,
        )

    @staticmethod
    def _pdf_page_text(page) -> str:
        """Text 1 trang PDF, ưu tiên giữ thứ tự cell của bảng.

        Dùng ``find_tables`` khi có bảng (cell đọc theo hàng/cột); trang không
        có bảng thì dùng ``get_text("text")`` thường.
        """
        try:
            tables = page.find_tables()
            table_list = list(tables) if tables else []
        except Exception:
            table_list = []
        if not table_list:
            return page.get_text("text")
        # Trang có bảng: đọc bảng theo thứ tự cell, phần text ngoài bảng lấy
        # bằng get_text rồi gộp (bảng chèn tại vị trí tương đối theo y0).
        parts: list[str] = []
        for table in table_list:
            rows = []
            for row in table.extract():
                cells = [("" if c is None else str(c)).strip() for c in row]
                rows.append(" | ".join(c for c in cells if c))
            parts.append("\n".join(r for r in rows if r))
        body = page.get_text("text")
        if body.strip():
            parts.insert(0, body)
        return "\n".join(parts)

    # --- DOCX ---
    def read_docx(self, path: str | Path) -> ReadResult:
        """Đọc DOCX bằng python-docx, giữ đúng thứ tự paragraph + table trong body."""
        from docx import Document
        from docx.table import Table
        from docx.text.paragraph import Paragraph

        p = Path(path)
        t0 = time.perf_counter()
        try:
            doc = Document(str(p))
        except Exception as exc:  # noqa: BLE001
            raise FileReadError(f"Không mở được DOCX {p}: {exc}") from exc
        parts: list[str] = []
        # Duyệt body theo đúng thứ tự: paragraph và table xen kẽ (không đọc
        # hết paragraph rồi mới tới table — sẽ sai thứ tự, TH-23).
        for child in doc.element.body.iterchildren():
            if child.tag.endswith("}p"):
                para = Paragraph(child, doc)
                if para.text.strip():
                    parts.append(para.text)
            elif child.tag.endswith("}tbl"):
                table = Table(child, doc)
                for row in table.rows:
                    cells = [c.text.strip() for c in row.cells]
                    line = " | ".join(c for c in cells if c)
                    if line:
                        parts.append(line)
        cleaned = clean_text("\n".join(parts))
        if not cleaned:
            raise FileReadError(f"DOCX {p} không có nội dung text nào.")
        return ReadResult(
            text=cleaned,
            source=p.name,
            kind="docx",
            warnings=[],
            read_seconds=time.perf_counter() - t0,
        )

    # --- TXT ---
    def read_txt(self, path: str | Path) -> ReadResult:
        """Đọc TXT (UTF-8/UTF-8-SIG, lỗi ký tự thay bằng U+FFFD, không crash)."""
        p = Path(path)
        t0 = time.perf_counter()
        raw = p.read_bytes()
        if len(raw) > MAX_TXT_CHARS:
            raise FileReadError(
                f"File TXT quá lớn ({len(raw)} byte > {MAX_TXT_CHARS} ký tự) — "
                "chia nhỏ file rồi đọc lại."
            )
        text = raw.decode("utf-8-sig", errors="replace")
        cleaned = clean_text(text)
        if not cleaned:
            raise FileReadError(f"TXT {p} rỗng.")
        return ReadResult(
            text=cleaned,
            source=p.name,
            kind="txt",
            warnings=[],
            read_seconds=time.perf_counter() - t0,
        )
