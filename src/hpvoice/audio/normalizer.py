"""ViTextNormalizer — chuẩn hoá số/tiền/ngày/giờ/đơn vị tiếng Việt thành chữ
đọc được (SPEC §3.3, TH-27, TK1.10, test T1.9).

Chạy TRƯỚC TextPreprocess; có công tắc bật/tắt (mặc định bật). Tắt thì text
giữ nguyên như cũ (SDK đọc thô).

Ví dụ:
- ``"1.500.000đ"`` → ``"một triệu năm trăm nghìn đồng"``
- ``"15/11/2026"`` → ``"mười lăm tháng mười một năm hai nghìn không trăm hai mươi sáu"``
- ``"19h30"`` → ``"mười chín giờ ba mươi phút"``
- ``"3,5kg"`` → ``"ba phẩy năm ki-lô-gam"``

Thứ tự áp dụng (quan trọng — dạng đặc thù trước, số thường sau): ngày →
giờ → tiền (đ/đồng/k/$) → phần trăm → đơn vị → số thập phân → số nguyên.
Mọi dạng sau khi thay đều không còn chữ số nên không bị thay lại lần hai.
"""
from __future__ import annotations

import re

__all__ = ["ViTextNormalizer", "read_int_vi", "read_number_vi"]

_DIGIT = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]
_SCALES = ["", "nghìn", "triệu", "tỷ", "nghìn tỷ", "triệu tỷ", "tỷ tỷ"]

_UNITS = {
    "kg": "ki-lô-gam",
    "km": "ki-lô-mét",
    "cm": "xăng-ti-mét",
    "mm": "mi-li-mét",
    "ml": "mi-li-lít",
    "g": "gam",
    "l": "lít",
    "m": "mét",
}

# Số: nhóm nghìn viết bằng dấu chấm (1.500.000) hoặc số thường, có thể kèm
# phần thập phân sau dấu phẩy/chấm (3,5 / 3.5).
_NUMBER_RE = r"\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?"


def _read_two_digits(t: int, u: int, has_hundreds: bool, leading_zero_group: bool) -> str:
    """Đọc phần chục + đơn vị (0–99) trong một nhóm 3 chữ số."""
    if t == 0 and u == 0:
        return ""
    if t == 0:
        # 05 → "linh năm" (khi có trăm hoặc nhóm 0 ở giữa, VD 1.005);
        # số đơn độc thì chỉ "năm".
        prefix = "linh " if (has_hundreds or leading_zero_group) else ""
        return prefix + _DIGIT[u]
    if t == 1:
        if u == 0:
            return "mười"
        if u == 1:
            return "mười một"
        if u == 5:
            return "mười lăm"
        return "mười " + _DIGIT[u]
    out = _DIGIT[t] + " mươi"
    if u == 0:
        return out
    if u == 1:
        return out + " mốt"
    if u == 5:
        return out + " lăm"
    return out + " " + _DIGIT[u]


def _read_group(value: int, most_significant: bool) -> str:
    """Đọc một nhóm 3 chữ số (0–999). Nhóm 0 → "" (caller bỏ qua)."""
    if value == 0:
        return ""
    h, rem = divmod(value, 100)
    t, u = divmod(rem, 10)
    parts: list[str] = []
    if h > 0:
        parts.append(_DIGIT[h] + " trăm")
    elif not most_significant:
        # Nhóm giữa bị 0 trăm nhưng khác 0 (VD 026 trong 2026):
        # "không trăm hai mươi sáu".
        parts.append("không trăm")
    tail = _read_two_digits(t, u, has_hundreds=h > 0, leading_zero_group=not most_significant and h == 0)
    if tail:
        parts.append(tail)
    return " ".join(parts)


def read_int_vi(n: int) -> str:
    """Đọc số nguyên (≥ 0) thành chữ tiếng Việt."""
    if n == 0:
        return "không"
    if n < 0:
        return "âm " + read_int_vi(-n)
    groups: list[int] = []
    rest = n
    while rest > 0:
        groups.append(rest % 1000)
        rest //= 1000
    parts: list[str] = []
    for i in range(len(groups) - 1, -1, -1):
        g = groups[i]
        if g == 0:
            continue
        words = _read_group(g, most_significant=(i == len(groups) - 1))
        scale = _SCALES[i] if i < len(_SCALES) else ""
        parts.append((words + " " + scale).strip())
    return " ".join(parts)


def _parse_number_token(tok: str) -> tuple[int, str | None]:
    """Tách token số thành (phần nguyên, phần thập phân hoặc None).

    Dấu chấm nhóm 3 chữ số = phân cách nghìn (1.500.000); dấu phẩy/chấm lẻ
    = thập phân (3,5 / 3.5). Trả phần nguyên dạng int và phần thập phân dạng
    chuỗi chữ số (giữ số 0 ở đầu, VD 3,05 → "05").
    """
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", tok):
        return int(tok.replace(".", "")), None
    if "," in tok:
        int_part, frac = tok.split(",", 1)
        return int(int_part.replace(".", "")), frac
    if "." in tok:
        # Một dấu chấm lẻ, không nhóm 3 → thập phân (3.5).
        if re.fullmatch(r"\d+\.\d+", tok):
            int_part, frac = tok.split(".", 1)
            return int(int_part), frac
        return int(tok.replace(".", "")), None
    return int(tok), None


def read_number_vi(tok: str) -> str:
    """Đọc token số (nguyên / nghìn / thập phân) thành chữ."""
    int_part, frac = _parse_number_token(tok)
    words = read_int_vi(int_part)
    if frac is None:
        return words
    frac_words = " ".join(_DIGIT[int(ch)] for ch in frac)
    return f"{words} phẩy {frac_words}"


class ViTextNormalizer:
    """Chuẩn hoá text tiếng Việt trước TextPreprocess."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    def normalize(self, text: str) -> str:
        """Chuẩn hoá ``text``; tắt (``enabled=False``) thì trả nguyên text."""
        if not self.enabled or not text:
            return text
        out = text
        out = self._normalize_dates(out)
        out = self._normalize_times(out)
        out = self._normalize_money(out)
        out = self._normalize_percent(out)
        out = self._normalize_units(out)
        out = self._normalize_numbers(out)
        return out

    # -- từng dạng ---------------------------------------------------------

    @staticmethod
    def _normalize_dates(text: str) -> str:
        def full(m: re.Match) -> str:
            d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            return (
                f"{read_int_vi(d)} tháng {read_int_vi(mo)} "
                f"năm {read_int_vi(y)}"
            )

        text = re.sub(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", full, text)

        def short(m: re.Match) -> str:
            d, mo = int(m.group(1)), int(m.group(2))
            return f"{read_int_vi(d)} tháng {read_int_vi(mo)}"

        return re.sub(r"\b(\d{1,2})/(\d{1,2})\b", short, text)

    @staticmethod
    def _normalize_times(text: str) -> str:
        def repl(m: re.Match) -> str:
            h = int(m.group(1))
            minute = m.group(2)
            out = f"{read_int_vi(h)} giờ"
            if minute is not None:
                out += f" {read_int_vi(int(minute))} phút"
            return out

        # 19h30 / 19h / 7:30 — "h" viết thường hoặc hoa.
        text = re.sub(r"\b(\d{1,2})[hH](\d{1,2})?\b", repl, text)
        return re.sub(r"\b(\d{1,2}):(\d{2})\b", repl, text)

    @staticmethod
    def _normalize_money(text: str) -> str:
        def with_unit(m: re.Match) -> str:
            return read_number_vi(m.group(1)) + " đồng"

        # 1.500.000đ / 50.000 đồng / 1.250.000 VNĐ
        text = re.sub(
            rf"\b({_NUMBER_RE})\s*(?:đ|đồng|VNĐ|vnd)\b", with_unit, text
        )

        def k_money(m: re.Match) -> str:
            # 500k = 500 nghìn đồng (quy ước bán hàng).
            return read_int_vi(int(m.group(1)) * 1000) + " đồng"

        text = re.sub(r"\b(\d+)\s*[kK]\b", k_money, text)

        def dollar(m: re.Match) -> str:
            return read_number_vi(m.group(1)) + " đô la"

        return re.sub(rf"\$\s*({_NUMBER_RE})", dollar, text)

    @staticmethod
    def _normalize_percent(text: str) -> str:
        return re.sub(
            rf"\b({_NUMBER_RE})%",
            lambda m: read_number_vi(m.group(1)) + " phần trăm",
            text,
        )

    @staticmethod
    def _normalize_units(text: str) -> str:
        unit_alt = "|".join(sorted(_UNITS, key=len, reverse=True))
        pattern = re.compile(
            rf"\b({_NUMBER_RE})\s*({unit_alt})(?![\wÀ-ỹ])"
        )

        def repl(m: re.Match) -> str:
            return read_number_vi(m.group(1)) + " " + _UNITS[m.group(2).lower()]

        return pattern.sub(repl, text)

    @staticmethod
    def _normalize_numbers(text: str) -> str:
        return re.sub(
            rf"\b({_NUMBER_RE})\b",
            lambda m: read_number_vi(m.group(1)),
            text,
        )
