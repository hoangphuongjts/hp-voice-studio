"""TextPreprocess — tiền xử lý text trước khi đưa vào ``infer()`` (SPEC §3.3, TK1.6).

Quy tắc SPEC (đã chốt):
- Thẻ cảm xúc ``[cười]`` / ``[thở dài]`` / ``[hắng giọng]`` giữ nguyên, đi vào
  ``infer()`` như thường (SDK hỗ trợ thật).
- Thẻ nghỉ ``[nghỉ <số><đơn vị>]``: SDK không có nên tầng này tự xử lý — parse
  tag → cắt text thành đoạn → mỗi đoạn gọi ``infer()`` riêng → chèn silence
  bằng ``AudioPost``. KHÔNG BAO GIỜ đưa chuỗi ``"[nghỉ"`` vào ``infer()`` hay
  request V4 (V4 sẽ xóa lặng lẽ, SDK sẽ đọc thành tiếng).
- Ngữ pháp: số thập phân cho phép; 0–1 khoảng trắng giữa số và đơn vị; đơn vị
  ``s``/``ms`` không phân biệt hoa/thường; tên thẻ phải viết đúng ``nghỉ`` thường.
- Tag ở đầu/cuối câu vẫn chèn silence tương ứng; tag giữa từ → báo lỗi + không
  tạo; nhiều tag liên tiếp cộng dồn, tổng liên tiếp ≤ 10 s; tag cạnh thẻ cảm xúc
  thì tách tại ``[nghỉ]``; tag sai định dạng / vượt 10 s / số âm → báo lỗi.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

__all__ = [
    "EMOTION_TAGS",
    "MAX_PAUSE_S",
    "MAX_CONSECUTIVE_PAUSE_S",
    "TextPreprocess",
    "TextPreprocessError",
    "TextSegment",
    "SplitResult",
    "ensure_no_pause_tag",
]

#: Ba thẻ cảm xúc duy nhất được SDK/V4 giữ lại.
EMOTION_TAGS = ("[cười]", "[thở dài]", "[hắng giọng]")

#: Giới hạn một thẻ nghỉ và tổng các thẻ nghỉ liên tiếp (giây).
MAX_PAUSE_S = 10.0
MAX_CONSECUTIVE_PAUSE_S = 10.0

# Tag nghỉ hợp lệ: [nghỉ 2s] / [nghỉ 500ms] / [nghỉ 2.5 s] / [nghỉ 1S] ...
_VALID_TAG_RE = re.compile(
    r"\[nghỉ\s*(\d+(?:\.\d+)?)\s*(s|ms)\]", re.IGNORECASE
)
# Bất kỳ chuỗi nào trông giống thẻ nghỉ (để phát hiện tag sai định dạng).
# Tên thẻ viết hoa ("Nghỉ") cũng bắt ở đây rồi báo lỗi rõ (SPEC: phải viết
# đúng "nghỉ" thường).
_ANY_TAG_RE = re.compile(r"\[\s*nghỉ[^\]]*\]", re.IGNORECASE)
# Ký tự thuộc "từ" (chữ cái tiếng Việt, số, gạch dưới) — dùng để phát hiện
# tag nằm giữa từ.
_WORD_CHAR_RE = re.compile(r"[\wÀ-ỹ]", re.UNICODE)


class TextPreprocessError(ValueError):
    """Lỗi tiền xử lý text: tag [nghỉ] sai / vượt giới hạn / nằm giữa từ."""


@dataclass
class TextSegment:
    """Một đoạn text đưa vào ``infer()`` + khoảng lặng chèn SAU đoạn đó."""

    text: str
    pause_after_s: float = 0.0


@dataclass
class SplitResult:
    """Kết quả tách text: các đoạn + khoảng lặng đầu (tag [nghỉ] ở đầu text)."""

    segments: list[TextSegment] = field(default_factory=list)
    leading_pause_s: float = 0.0

    def infer_texts(self) -> list[str]:
        """Text của từng đoạn — chính là input đưa vào ``infer()``/V4."""
        return [s.text for s in self.segments]


def ensure_no_pause_tag(text: str) -> None:
    """Bảo vệ đường V4/infer: ném lỗi nếu text còn chứa chuỗi ``"[nghỉ"``.

    Dùng làm assert trong test mock và làm hàng rào cuối trước khi gửi request.
    """
    if "[nghỉ" in text or "[Nghỉ" in text or "[NGHỈ" in text:
        raise TextPreprocessError(
            "Text chứa thẻ [nghỉ ...] — phải tách đoạn bằng TextPreprocess "
            "trước khi đưa vào infer() hay request V4, không được gửi nguyên tag."
        )


class TextPreprocess:
    """Tách text theo thẻ ``[nghỉ ...]``, giữ nguyên thẻ cảm xúc."""

    def split(self, text: str) -> SplitResult:
        """Cắt ``text`` thành các đoạn + khoảng lặng.

        Ném :class:`TextPreprocessError` (và không tạo audio) khi gặp tag sai
        định dạng, vượt 10 s/thẻ hoặc 10 s/tổng liên tiếp, số âm, tag giữa từ,
        hoặc tên thẻ viết sai hoa/thường.
        """
        if text is None:
            raise TextPreprocessError("Text rỗng (None).")
        result = SplitResult()
        buf: list[str] = []  # ký tự của đoạn đang gom
        pending_pause = 0.0  # pause của tag vừa gặp, chờ gắn vào đoạn vừa đóng
        run_pause = 0.0  # tổng pause của chuỗi tag liên tiếp (chưa có text xen vào)

        def flush_segment() -> None:
            nonlocal pending_pause, run_pause
            seg_text = "".join(buf).strip()
            buf.clear()
            if seg_text:
                result.segments.append(
                    TextSegment(text=seg_text, pause_after_s=pending_pause)
                )
            elif pending_pause:
                # Chỉ khoảng trắng giữa các tag: pause dồn vào đoạn trước đó
                # (hoặc thành leading nếu chưa có đoạn nào).
                if result.segments:
                    result.segments[-1].pause_after_s += pending_pause
                else:
                    result.leading_pause_s += pending_pause
            pending_pause = 0.0

        pos = 0
        for m in _ANY_TAG_RE.finditer(text):
            raw = m.group(0)
            valid = _VALID_TAG_RE.fullmatch(raw)
            if valid is None:
                raise TextPreprocessError(
                    f"Thẻ nghỉ sai định dạng: {raw!r} — đúng dạng là "
                    "[nghỉ <số><s|ms>], VD [nghỉ 2s] hay [nghỉ 500ms]."
                )
            # Tên thẻ phải viết đúng "nghỉ" thường (không "Nghỉ"/"NGHỈ").
            if not raw.startswith("[nghỉ"):
                raise TextPreprocessError(
                    f"Tên thẻ phải viết đúng 'nghỉ' thường: {raw!r} "
                    "(không viết hoa, VD [Nghỉ 1s] là sai)."
                )
            # Tag giữa từ: hai bên đều là ký tự từ (không có ranh giới từ).
            before = text[m.start() - 1] if m.start() > 0 else ""
            after = text[m.end()] if m.end() < len(text) else ""
            if before and after and _WORD_CHAR_RE.match(before) and _WORD_CHAR_RE.match(after):
                raise TextPreprocessError(
                    f"Thẻ nghỉ nằm giữa từ: ...{text[max(0, m.start()-6):m.end()+6]!r}... — "
                    "cắt giữa từ sẽ phá phát âm; hãy đặt tag ở ranh giới từ "
                    "(có khoảng trắng/dấu câu hai bên)."
                )
            number = float(valid.group(1))
            unit = valid.group(2).lower()
            seconds = number / 1000.0 if unit == "ms" else number
            if seconds <= 0:
                raise TextPreprocessError(
                    f"Thẻ nghỉ phải > 0 giây: {raw!r}."
                )
            if seconds > MAX_PAUSE_S:
                raise TextPreprocessError(
                    f"Thẻ nghỉ vượt giới hạn 10 s/thẻ: {raw!r} "
                    f"({seconds:g} s)."
                )
            # Có nội dung thật xen giữa hai tag → chuỗi tag liên tiếp kết thúc.
            if text[pos : m.start()].strip():
                run_pause = 0.0
            run_pause += seconds
            if run_pause > MAX_CONSECUTIVE_PAUSE_S:
                raise TextPreprocessError(
                    "Tổng các thẻ nghỉ liên tiếp vượt 10 s "
                    f"({run_pause:g} s) — hãy chia nhỏ khoảng nghỉ."
                )
            pending_pause = seconds
            # Text trước tag thuộc đoạn hiện tại; tag kết thúc đoạn đó.
            buf.append(text[pos : m.start()])
            flush_segment()
            pos = m.end()
        buf.append(text[pos:])
        flush_segment()

        # Text chỉ gồm tag nghỉ (không có đoạn nào): SPEC coi là lỗi — không tạo.
        if not result.segments and (result.leading_pause_s > 0 or pending_pause > 0):
            raise TextPreprocessError(
                "Text chỉ gồm thẻ [nghỉ ...] mà không có nội dung để đọc."
            )
        if not result.segments and not text.strip():
            return SplitResult()
        return result
