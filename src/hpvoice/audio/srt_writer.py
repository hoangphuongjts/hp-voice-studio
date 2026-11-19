"""SrtWriter — suy mốc giờ cho file .srt kèm audio ở Phòng thu (SPEC §3.3, TK1.6).

Phương pháp chốt (SPEC v1.3, sửa sai hằng số của v1.1):
- Chia text thành chunk đúng như SDK chia (tối đa 256 ký tự), gọi ``infer()``
  từng chunk, đo độ dài audio từng chunk (số mẫu / 48.000).
- Cộng dồn + khoảng lặng giữa chunk theo ``gaps_to_silence`` — KHÔNG dùng
  ``silence_p`` (đường v3 Turbo không dùng nó):
  ngắt đoạn ``para`` = 0,70 s; hết câu ``sentence`` = 0,50 s;
  ngắt trong câu/cắt cưỡng bức ``minor`` = 0,30 s.
- Các số trên là khoảng nghỉ TỔNG nghe được ở khe (im lặng đuôi chunk trước +
  zeros chèn + im lặng đầu chunk sau) — chỉ cộng phần zeros bù thêm =
  ``max(0, gaps_to_silence − im lặng mép đã đo)``. Cộng cả 0,30/0,50/0,70 s
  lên trên độ dài chunk đã đo sẽ lệch mỗi mốc 0,15–0,55 s.
- Mốc từng câu trong cùng chunk chia theo TỈ LỆ ĐỘ DÀI KÝ TỰ (ước lượng, không
  có forced alignment); câu bị cắt cưỡng bức qua hai chunk lấy theo tỉ lệ ký
  tự ở cả hai chunk.
- Mục tiêu ±0,3 s/câu áp cho 10 câu đầu; bài dài ghi thêm sai số tối đa ở câu
  cuối (xem :func:`SrtWriter.build_cues` — trường ``max_error_note``).
- Đo sai số ĐỘC LẬP bằng silencedetect/envelope trên sóng âm thật (T3.1),
  KHÔNG đo bằng chính SrtWriter.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from hpvoice.audio.post import edge_silence_seconds

__all__ = [
    "GAPS_TO_SILENCE",
    "MAX_CHUNK_CHARS",
    "SrtCue",
    "SrtWriter",
    "chunk_text",
    "edge_silence_seconds",
    "format_srt_time",
    "split_sentences",
]

#: Hằng số đúng (upstream core_utils.py:77 ``V3_GAP_SILENCE``).
GAPS_TO_SILENCE: dict[str, float] = {"para": 0.70, "sentence": 0.50, "minor": 0.30}
MAX_CHUNK_CHARS = 256
#: Số câu đầu áp mục tiêu ±0,3 s (SPEC §3.3).
TARGET_SENTENCES = 10

_SENT_END_RE = re.compile(r"(?<=[.!?…])\s+")
_PARA_SPLIT_RE = re.compile(r"\n+")


@dataclass
class SrtCue:
    """Một mục phụ đề: mốc bắt đầu/kết thúc (giây) + text câu."""

    index: int
    start_s: float
    end_s: float
    text: str


def split_sentences(text: str) -> list[str]:
    """Tách text thành câu theo dấu kết thúc (. ! ? …)."""
    text = " ".join((text or "").split())
    if not text:
        return []
    parts = _SENT_END_RE.split(text)
    return [p.strip() for p in parts if p.strip()]


def _classify_gap(chunk_text_: str) -> str:
    """Loại ranh giới sau chunk: hết câu (. ! ? …) → sentence, còn lại minor."""
    t = chunk_text_.rstrip()
    if t and t[-1] in ".!?…":
        return "sentence"
    return "minor"


def chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> tuple[list[str], list[str]]:
    """Chia text thành chunk ≤ ``max_chars`` ký tự như SDK
    (``normalize_to_chunks_v3_with_gaps``): gom câu theo đoạn, cắt cưỡng bức
    câu quá dài. Trả ``(chunks, gaps)`` với ``gaps[i]`` là ranh giới giữa
    chunk ``i`` và ``i+1`` (``para``/``sentence``/``minor``)."""
    chunks: list[str] = []
    gaps: list[str] = []
    paras = [p for p in _PARA_SPLIT_RE.split(text or "") if p.strip()]
    for para in paras:
        sentences = split_sentences(para)
        if not sentences:
            continue
        if chunks:
            gaps.append("para")
        cur = ""
        for sent in sentences:
            # Câu đơn đã dài hơn giới hạn → cắt cưỡng bức thành nhiều chunk.
            while len(sent) > max_chars:
                if cur:
                    chunks.append(cur)
                    gaps.append(_classify_gap(cur))
                    cur = ""
                chunks.append(sent[:max_chars])
                gaps.append("minor")
                sent = sent[max_chars:]
            if not cur:
                cur = sent
            elif len(cur) + 1 + len(sent) <= max_chars:
                cur = cur + " " + sent
            else:
                chunks.append(cur)
                gaps.append(_classify_gap(cur))
                cur = sent
        if cur:
            chunks.append(cur)
    # gaps phải có đúng len(chunks)-1 phần tử (ranh giới para đã thêm thừa
    # khi đoạn mới bắt đầu mà chunk trước vừa đóng — kiểm tra lại).
    gaps = gaps[: max(0, len(chunks) - 1)]
    while len(gaps) < max(0, len(chunks) - 1):
        gaps.append(_classify_gap(chunks[len(gaps)]))
    return chunks, gaps


class SrtWriter:
    """Suy mốc giờ từng câu từ độ dài audio từng chunk."""

    def __init__(self, sr: int = 48000) -> None:
        self.sr = sr

    def build_cues(
        self, text: str, chunk_audios: list[np.ndarray], sr: int | None = None
    ) -> list[SrtCue]:
        """Suy mốc từng câu.

        ``chunk_audios[i]`` là audio của chunk thứ ``i`` theo
        :func:`chunk_text` (độ dài đo thật = số mẫu / sr). Trả list cue theo
        thứ tự câu; câu bị cắt qua nhiều chunk là một cue duy nhất.
        """
        sr = sr or self.sr
        chunks, gaps = chunk_text(text)
        if len(chunk_audios) != len(chunks):
            raise ValueError(
                f"Số audio chunk ({len(chunk_audios)}) khác số chunk text "
                f"({len(chunks)}) — phải infer đúng từng chunk như SDK chia."
            )
        sentences = split_sentences(text)
        if not sentences:
            return []

        # --- Tính span gọn, đúng: duyệt câu × chunk theo số ký tự ---
        # Mỗi câu được cắt thành các phần, mỗi phần nằm trong một chunk.
        # Chunk chứa các câu nối nhau bằng " " (1 ký tự) hoặc cắt cưỡng bức
        # (0 ký tự nối). Dùng lại logic chunk_text ngược: tổng độ dài chunk =
        # tổng độ dài câu trong chunk + số khoảng trắng nối.
        spans = []
        ci = 0
        offset_in_chunk = 0  # ký tự đã dùng trong chunk hiện tại
        for sent in sentences:
            parts: list[tuple[int, int, int]] = []
            remaining_sent = len(sent)
            while remaining_sent > 0:
                if ci >= len(chunks):
                    raise ValueError("Hết chunk khi đang chia mốc câu (lỗi nội bộ).")
                chunk_len = len(chunks[ci])
                avail = chunk_len - offset_in_chunk
                if avail <= 0:
                    ci += 1
                    offset_in_chunk = 0
                    continue
                take = min(avail, remaining_sent)
                # Lưu vị trí THEO CHUNK (không phải theo câu) để chia tỉ lệ đúng.
                parts.append((ci, offset_in_chunk, offset_in_chunk + take))
                remaining_sent -= take
                offset_in_chunk += take
                if remaining_sent > 0:
                    # Hết chunk giữa câu → sang chunk sau (cắt cưỡng bức).
                    ci += 1
                    offset_in_chunk = 0
            spans.append(parts)
            # Sau mỗi câu (trừ câu cuối trong chunk) có 1 ký tự " " nối —
            # trừ khi câu kết thúc đúng cuối chunk (cắt cưỡng bức / hết chunk).
            if ci < len(chunks):
                if offset_in_chunk < len(chunks[ci]):
                    offset_in_chunk += 1  # khoảng trắng nối giữa hai câu
                    if offset_in_chunk >= len(chunks[ci]):
                        ci += 1
                        offset_in_chunk = 0

        # --- Tính mốc giờ ---
        durations = [len(a) / sr for a in chunk_audios]
        # Khoảng lặng bù thêm sau mỗi chunk (trừ chunk cuối).
        pads: list[float] = []
        for i in range(len(chunks) - 1):
            gap_kind = gaps[i] if i < len(gaps) else "sentence"
            total_pause = GAPS_TO_SILENCE.get(gap_kind, 0.50)
            _, tail = edge_silence_seconds(chunk_audios[i], sr)
            lead, _ = edge_silence_seconds(chunk_audios[i + 1], sr)
            pads.append(max(0.0, total_pause - tail - lead))
        # Mốc bắt đầu của từng chunk (cộng dồn độ dài + pad).
        chunk_start = [0.0]
        for i in range(len(chunks) - 1):
            chunk_start.append(chunk_start[-1] + durations[i] + pads[i])

        cues: list[SrtCue] = []
        for idx, (sent, parts) in enumerate(zip(sentences, spans)):
            start = None
            end = None
            for (ci2, a, b) in parts:
                chunk_len = len(chunks[ci2])
                frac_a = a / chunk_len if chunk_len else 0.0
                frac_b = b / chunk_len if chunk_len else 0.0
                s = chunk_start[ci2] + frac_a * durations[ci2]
                e = chunk_start[ci2] + frac_b * durations[ci2]
                if start is None:
                    start = s
                end = e
            cues.append(SrtCue(index=idx + 1, start_s=start, end_s=end, text=sent))
        return cues

    def to_srt(self, cues: list[SrtCue]) -> str:
        """Xuất chuỗi .srt chuẩn."""
        lines: list[str] = []
        for c in cues:
            lines.append(str(c.index))
            lines.append(f"{format_srt_time(c.start_s)} --> {format_srt_time(c.end_s)}")
            lines.append(c.text)
            lines.append("")
        return "\n".join(lines)

    def write_srt(self, path: str | Path, cues: list[SrtCue]) -> Path:
        """Ghi file .srt (UTF-8)."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.to_srt(cues), encoding="utf-8")
        return p


def format_srt_time(seconds: float) -> str:
    """Giây (float) → ``HH:MM:SS,mmm``."""
    total_ms = int(round(max(0.0, seconds) * 1000))
    h, rem = divmod(total_ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
