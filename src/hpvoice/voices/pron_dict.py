"""PronDict — từ điển phát âm (SPEC §3.3, TK1.7).

Thêm/sửa/xoá, import/export CSV, áp trước khi infer; giới hạn 2.000 mục
(theo VieNeu Studio). Áp dụng thay đúng từ (không thay bên trong từ khác),
từ dài được ưu tiên trước từ ngắn.
"""
from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path

__all__ = ["MAX_ITEMS", "PronDict", "PronDictError"]

MAX_ITEMS = 2000


class PronDictError(ValueError):
    """Lỗi từ điển phát âm (vượt giới hạn, từ/đọc rỗng...)."""


class PronDict:
    """Từ điển phát âm: ánh xạ từ/cụm từ → cách đọc."""

    def __init__(self, entries: dict[str, str] | None = None) -> None:
        self._entries: dict[str, str] = {}
        if entries:
            for word, reading in entries.items():
                self.add(word, reading)

    def add(self, word: str, reading: str) -> None:
        """Thêm mới hoặc sửa cách đọc của một từ. Ghi đè không tăng số mục."""
        word = (word or "").strip()
        reading = (reading or "").strip()
        if not word:
            raise PronDictError("Từ trong từ điển không được rỗng.")
        if not reading:
            raise PronDictError(f"Cách đọc của {word!r} không được rỗng.")
        if word not in self._entries and len(self._entries) >= MAX_ITEMS:
            raise PronDictError(
                f"Từ điển đã đủ {MAX_ITEMS:,} mục — xoá bớt mục cũ trước "
                "khi thêm mục mới."
            )
        self._entries[word] = reading

    def get(self, word: str) -> str | None:
        return self._entries.get((word or "").strip())

    def remove(self, word: str) -> bool:
        return self._entries.pop((word or "").strip(), None) is not None

    def count(self) -> int:
        return len(self._entries)

    def entries(self) -> dict[str, str]:
        return dict(self._entries)

    def apply(self, text: str) -> str:
        """Áp từ điển vào text trước khi infer: thay đúng từ (ranh giới từ),
        cụm dài trước cụm ngắn. Một lượt duy nhất — không thay lại bên trong
        cách đọc vừa thay. Text không chứa từ nào thì trả nguyên."""
        if not text or not self._entries:
            return text
        words = sorted(self._entries, key=len, reverse=True)
        pattern = re.compile(
            r"(?<!\w)(?:" + "|".join(re.escape(w) for w in words) + r")(?!\w)"
        )
        return pattern.sub(lambda m: self._entries[m.group(0)], text)

    def export_csv(self, path: str | Path) -> Path:
        """Xuất CSV với header ``word,reading`` (UTF-8)."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["word", "reading"])
            for word, reading in self._entries.items():
                w.writerow([word, reading])
        return p

    def import_csv(self, source: str | Path | io.TextIOBase) -> int:
        """Nhập CSV (header ``word,reading``; bỏ qua dòng trống/header lặp).
        Trả số mục đã nhập (ghi đè mục trùng)."""
        if isinstance(source, (str, Path)) and not hasattr(source, "read"):
            f = open(source, encoding="utf-8", newline="")
            close = True
        else:
            f = source  # type: ignore[assignment]
            close = False
        count = 0
        try:
            for row in csv.reader(f):
                if not row or all(not c.strip() for c in row):
                    continue
                if len(row) < 2:
                    continue
                word, reading = row[0].strip(), row[1].strip()
                if word == "word" and reading == "reading":
                    continue
                if not word or not reading:
                    continue
                self.add(word, reading)
                count += 1
        finally:
            if close:
                f.close()
        return count

    def save(self, path: str | Path) -> Path:
        """Lưu JSON (định dạng mặc định của config ``dict_file``)."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps(self._entries, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return p

    @classmethod
    def load(cls, path: str | Path) -> "PronDict":
        """Nạp JSON đã lưu bằng :meth:`save` (file không có → từ điển rỗng)."""
        p = Path(path)
        if not p.exists():
            return cls()
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise PronDictError(f"File từ điển sai định dạng: {path}")
        return cls({str(k): str(v) for k, v in data.items()})
