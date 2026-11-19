"""SrtDubber — lồng tiếng theo file .srt/.vtt (TK2.5 + TK2.13, SPEC §3.3, T3.3).

- Parse .srt (bỏ thẻ định dạng) và .vtt (bỏ header ``WEBVTT``/NOTE/cài đặt cue,
  chuyển về dạng SRT nội bộ) rồi căn giờ.
- Quy tắc ``[nghỉ]`` + tốc độ 0,75× (G3): tag ``[nghỉ]`` trong câu SRT được
  parse thành khoảng lặng tính vào độ dài slot của câu, KHÔNG đưa vào
  ``infer()`` (dùng :class:`TextPreprocess` tách đoạn như đường V4).
- Tốc độ người dùng chọn (0,75×–1,5×) áp trước; hệ số căn giờ từng câu chỉ
  được phép đẩy tốc độ hiệu dụng tối đa tới 1,5× và tối thiểu 0,75× — vượt
  thì lấn khoảng lặng → đẩy câu sau → báo cáo câu bị lùi (như TH-07).
- Không cắt chữ: câu dài quá slot dù đã đọc nhanh 1,5× thì vẫn đọc hết, câu
  sau bị lùi (ghi vào ``delayed`` + SRT đã chỉnh mốc).
- Giới hạn SRT dub: SPEC §4 sửa — con số 100.000 câu/tệp của VieNeu Desktop là
  giới hạn **Tạo hàng loạt**, KHÔNG phải SRT dub. V1 KHÔNG chốt số cứng;
  ``DubResult.performance_note`` cảnh báo khi > 1000 cue (chưa đo hiệu năng)
  và giới hạn thật được đo ở Bước 3 (TK2.5) — xem test đo thời gian parse/plan.
- Fallback V4→V3 cho ``/v1/dialogue``, ``/v1/dub``, ``/v1/srt``: cùng bảng
  ánh xạ giọng + ``voice_strict`` qua :class:`EngineRouter` (tham số ``router``);
  idempotency của 3 endpoint này CHƯA xác nhận trong OpenAPI (``parameters: []``)
  nên không retry sau timeout — xem ``V4Engine.create_dialogue``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from ..audio.post import MIN_RATE, MAX_RATE, join_chunks, make_silence, time_stretch, write_wav
from ..audio.srt_writer import SrtCue, format_srt_time
from ..audio.text_preprocess import TextPreprocess
from ..engines.base import AudioResult

__all__ = [
    "DubResult",
    "SrtDubber",
    "SrtParseError",
    "parse_srt_text",
    "parse_vtt_text",
    "parse_subtitle_file",
    "PERFORMANCE_WARN_CUES",
]

#: Số cue trở lên thì ghi chú "chưa đo hiệu năng" (giới hạn thật đo ở Bước 3).
PERFORMANCE_WARN_CUES = 1000

_SRT_TIME_RE = re.compile(
    r"(\d+):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d+):(\d{2}):(\d{2})[,.](\d{3})"
)
_VTT_TIME_RE = re.compile(
    r"(?:(\d+):)?(\d{2}):(\d{2})\.(\d{3})\s*-->\s*(?:(\d+):)?(\d{2}):(\d{2})\.(\d{3})"
)
_FMT_TAG_RE = re.compile(r"<[^>]+>|\{[^}]*\}")
_PAUSE_TAG_RE = re.compile(r"\[\s*nghỉ[^\]]*\]", re.IGNORECASE)


class SrtParseError(ValueError):
    """Lỗi parse file phụ đề (.srt/.vtt sai định dạng)."""


def _to_seconds(h: int, m: int, s: int, ms: int) -> float:
    return h * 3600 + m * 60 + s + ms / 1000.0


def _clean_text(text: str) -> str:
    """Bỏ thẻ định dạng SRT/VTT (<i>, {..}) + gộp khoảng trắng."""
    text = _FMT_TAG_RE.sub("", text)
    return " ".join(text.split())


def parse_srt_text(text: str) -> list[SrtCue]:
    """Parse chuỗi .srt → list cue (mốc giây + text đã bỏ thẻ định dạng)."""
    if text is None or not str(text).strip():
        raise SrtParseError("File .srt rỗng.")
    text = str(text).replace("\r\n", "\n").replace("\r", "\n")
    blocks = [b.strip("\n") for b in re.split(r"\n\s*\n", text) if b.strip()]
    cues: list[SrtCue] = []
    for block in blocks:
        lines = [ln for ln in block.split("\n")]
        time_idx = None
        for i, ln in enumerate(lines):
            if "-->" in ln:
                time_idx = i
                break
        if time_idx is None:
            raise SrtParseError(f"Khối SRT thiếu dòng mốc giờ: {block[:80]!r}")
        m = _SRT_TIME_RE.search(lines[time_idx])
        if not m:
            raise SrtParseError(f"Mốc giờ SRT sai định dạng: {lines[time_idx]!r}")
        start = _to_seconds(int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)))
        end = _to_seconds(int(m.group(5)), int(m.group(6)), int(m.group(7)), int(m.group(8)))
        if end <= start:
            raise SrtParseError(
                f"Mốc giờ SRT ngược (kết thúc ≤ bắt đầu): {lines[time_idx]!r}"
            )
        cue_text = _clean_text("\n".join(lines[time_idx + 1 :]))
        if not cue_text:
            raise SrtParseError(f"Cue SRT rỗng text ở mốc {lines[time_idx]!r}.")
        cues.append(SrtCue(index=len(cues) + 1, start_s=start, end_s=end, text=cue_text))
    if not cues:
        raise SrtParseError("File .srt không có cue nào.")
    return cues


def parse_vtt_text(text: str) -> list[SrtCue]:
    """Parse chuỗi .vtt → list cue dạng SRT nội bộ.

    Bỏ header ``WEBVTT``, khối ``NOTE``, cài đặt cue sau mốc giờ
    (VD ``align:start position:10%``); mốc ``MM:SS.mmm`` hoặc ``HH:MM:SS.mmm``.
    """
    if text is None or not str(text).strip():
        raise SrtParseError("File .vtt rỗng.")
    text = str(text).replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    # Bỏ header WEBVTT (+ metadata header tới dòng trống đầu tiên).
    start = 0
    if lines and lines[0].strip().upper().startswith("WEBVTT"):
        start = 1
        while start < len(lines) and lines[start].strip():
            start += 1
    cues: list[SrtCue] = []
    i = start
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line.upper().startswith("NOTE"):
            # Khối NOTE: bỏ tới dòng trống.
            i += 1
            while i < len(lines) and lines[i].strip():
                i += 1
            continue
        # Dòng id cue (không chứa -->) thì bỏ qua, mốc ở dòng sau.
        if "-->" not in line:
            i += 1
            continue
        m = _VTT_TIME_RE.search(line)
        if not m:
            raise SrtParseError(f"Mốc giờ VTT sai định dạng: {line!r}")
        h1 = int(m.group(1)) if m.group(1) else 0
        start_s = _to_seconds(h1, int(m.group(2)), int(m.group(3)), int(m.group(4)))
        h2 = int(m.group(5)) if m.group(5) else 0
        end_s = _to_seconds(h2, int(m.group(6)), int(m.group(7)), int(m.group(8)))
        if end_s <= start_s:
            raise SrtParseError(f"Mốc giờ VTT ngược (kết thúc ≤ bắt đầu): {line!r}")
        i += 1
        text_lines: list[str] = []
        while i < len(lines) and lines[i].strip():
            text_lines.append(lines[i])
            i += 1
        cue_text = _clean_text("\n".join(text_lines))
        if not cue_text:
            raise SrtParseError(f"Cue VTT rỗng text ở mốc {line!r}.")
        cues.append(SrtCue(index=len(cues) + 1, start_s=start_s, end_s=end_s, text=cue_text))
    if not cues:
        raise SrtParseError("File .vtt không có cue nào.")
    return cues


def parse_subtitle_file(path: str | Path) -> list[SrtCue]:
    """Parse file .srt/.vtt theo đuôi file."""
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix not in (".srt", ".vtt"):
        raise SrtParseError(f"Đuôi file phụ đề không hỗ trợ: {suffix!r} (chỉ .srt/.vtt).")
    try:
        raw = p.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise SrtParseError(f"Không đọc được file phụ đề {p}: {exc}") from exc
    if suffix == ".srt":
        return parse_srt_text(raw)
    return parse_vtt_text(raw)


@dataclass
class DubbedCue:
    """Một cue sau khi lồng tiếng: mốc đã chỉnh + tốc độ hiệu dụng + có bị lùi không."""

    index: int
    scheduled_start_s: float  # mốc gốc trong file
    scheduled_end_s: float
    actual_start_s: float  # mốc thực sau khi căn giờ (bị lùi nếu tràn slot)
    actual_end_s: float
    text: str
    effective_rate: float  # tốc độ hiệu dụng (đã kẹp 0,75–1,5)
    overflowed: bool  # True = câu bị lùi (tràn slot dù đã đọc nhanh 1,5×)

    @property
    def shift_s(self) -> float:
        return self.actual_start_s - self.scheduled_start_s


@dataclass
class DubResult:
    """Kết quả lồng tiếng: audio + SRT đã chỉnh mốc + báo cáo câu bị lùi."""

    samples: np.ndarray | None = None  # None khi ghi thẳng ra file (output_path)
    sample_rate: int = 48000
    output_path: Path | None = None
    cues: list[DubbedCue] = field(default_factory=list)
    fallback_info: object | None = None  # FallbackInfo khi đã fallback V4→V3
    performance_note: str = ""
    total_s: float = 0.0  # tổng độ dài timeline (gồm đệm cuối tới hết mốc video)

    @property
    def duration_s(self) -> float:
        if self.total_s > 0:
            return self.total_s
        if self.samples is not None:
            return float(len(self.samples)) / self.sample_rate if self.sample_rate else 0.0
        if self.cues:
            return max(c.actual_end_s for c in self.cues)
        return 0.0

    @property
    def delayed(self) -> list[DubbedCue]:
        """Các câu bị lùi (tràn slot, đẩy câu sau)."""
        return [c for c in self.cues if c.overflowed]

    def to_srt(self) -> str:
        """Xuất SRT đã chỉnh mốc (text đã bỏ thẻ [nghỉ] — tag chỉ là timing)."""
        lines: list[str] = []
        for c in self.cues:
            lines.append(str(c.index))
            lines.append(
                f"{format_srt_time(c.actual_start_s)} --> {format_srt_time(c.actual_end_s)}"
            )
            lines.append(c.text)
            lines.append("")
        return "\n".join(lines)


class SrtDubber:
    """Lồng tiếng theo mốc .srt/.vtt: parse → căn giờ → audio + SRT chỉnh mốc."""

    def __init__(self, engine):
        self.engine = engine

    def _synthesize_cue_segments(
        self, text: str, voice: str, engine
    ) -> tuple[list[np.ndarray], list[float], float, int]:
        """Tổng hợp text của 1 cue thành các đoạn đọc + khoảng lặng [nghỉ].

        Trả ``(đoạn_đọc, pauses_giữa_đoạn, leading_pause_s, sr)``: tag
        ``[nghỉ]`` KHÔNG bao giờ đưa vào infer()/V4; khoảng lặng giữ đúng số
        giây (không bị time-stretch kéo dài theo — stretch chỉ áp lên đoạn đọc).
        """
        split = TextPreprocess().split(text)
        if not split.segments:
            raise ValueError(f"Cue chỉ gồm thẻ [nghỉ] mà không có nội dung: {text!r}")
        parts: list[np.ndarray] = []
        pauses: list[float] = []
        sr = getattr(engine, "sample_rate", 48000)
        for seg in split.segments:
            result = engine.synthesize(seg.text, voice)
            sr = result.sample_rate
            parts.append(np.asarray(result.samples, dtype=np.float32))
            pauses.append(seg.pause_after_s)
        return parts, pauses, split.leading_pause_s, sr

    @staticmethod
    def _pause_seconds_in(text: str) -> float:
        """Tổng số giây [nghỉ] trong text của cue (tính vào độ dài slot)."""
        split = TextPreprocess().split(text)
        total = split.leading_pause_s
        for seg in split.segments:
            total += seg.pause_after_s
        return total

    def dub(
        self,
        cues: list[SrtCue],
        voice: str,
        speed: float = 1.0,
        output_path: str | Path | None = None,
        router=None,
        voice_strict: bool = False,
    ) -> DubResult:
        """Lồng tiếng danh sách cue.

        ``speed``: tốc độ người dùng chọn (0,75–1,5) áp trước; tốc độ hiệu
        dụng từng câu bị kẹp trong [0,75, 1,5] — vượt thì câu bị lùi.
        ``router`` (EngineRouter, tùy chọn): khi engine chính là V4 và lỗi,
        fallback sang V3 theo bảng ánh xạ + ``voice_strict`` (không fallback
        khi khóa giọng). ``output_path``: ghi WAV dần ra đĩa (bài dài/SRT
        nhiều câu — không giữ toàn bộ audio trong RAM).
        """
        if not cues:
            raise ValueError("Không có cue nào để lồng tiếng.")
        if speed < MIN_RATE or speed > MAX_RATE:
            raise ValueError(f"Tốc độ phải trong khoảng {MIN_RATE}×–{MAX_RATE}×, nhận {speed}×.")
        engine = self.engine
        current_voice = voice
        fallback_info = None
        sr = getattr(engine, "sample_rate", 48000)

        from ..audio.post import WavWriter

        writer = None
        collected: list[np.ndarray] = []
        if output_path is not None:
            writer = WavWriter(output_path, sr)
            writer.__enter__()

        dubbed: list[DubbedCue] = []
        cursor_s = 0.0  # vị trí ghi hiện tại trong timeline (giây)
        shift_s = 0.0  # độ lùi tích lũy do các cue trước tràn slot
        try:
            for cue in cues:
                clean_text = _PAUSE_TAG_RE.sub("", cue.text).strip()
                clean_text = " ".join(clean_text.split())
                pause_total = self._pause_seconds_in(cue.text)
                # Tổng hợp cue (fallback V4→V3 một lần cho toàn bộ dub nếu lỗi).
                try:
                    parts, pauses, leading_pause, sr = self._synthesize_cue_segments(
                        cue.text, current_voice, engine
                    )
                except Exception as exc:  # noqa: BLE001 - xét fallback rồi mới báo lỗi
                    if (
                        router is not None
                        and getattr(engine, "name", "") == "v4"
                        and router.should_fallback(exc, voice_strict)
                    ):
                        new_voice = router.fallback_voice_for(current_voice)
                        from ..engines.router import FallbackInfo

                        fallback_info = FallbackInfo(
                            reason=router.describe_error(exc),
                            from_voice=current_voice,
                            to_voice=new_voice,
                        )
                        engine = router.v3_engine
                        current_voice = new_voice
                        parts, pauses, leading_pause, sr = self._synthesize_cue_segments(
                            cue.text, current_voice, engine
                        )
                    else:
                        raise
                natural_dur = sum(len(p) for p in parts) / sr if sr else 0.0
                slot = cue.end_s - cue.start_s
                avail = max(0.0, slot - pause_total)  # thời gian dành cho phần đọc
                # Tốc độ hiệu dụng: tốc độ user × hệ số căn giờ, kẹp [0,75, 1,5].
                if avail <= 0:
                    fit = float("inf")  # slot toàn là [nghỉ] — đọc ở tốc độ tối đa
                elif natural_dur <= 0:
                    fit = 1.0
                else:
                    fit = (natural_dur / speed) / avail
                effective_rate = min(MAX_RATE, max(MIN_RATE, speed * fit))
                # Stretch CHỈ đoạn đọc (khoảng lặng [nghỉ] giữ đúng số giây).
                stretched_parts: list[np.ndarray] = []
                for part in parts:
                    if abs(effective_rate - 1.0) > 1e-9:
                        stretched_parts.append(time_stretch(part, sr, effective_rate)[0])
                    else:
                        stretched_parts.append(part)
                all_parts: list[np.ndarray] = []
                all_pauses: list[float] = []
                if leading_pause > 0:
                    all_parts.append(make_silence(leading_pause, sr))
                    all_pauses.append(0.0)
                for i, part in enumerate(stretched_parts):
                    all_parts.append(part)
                    all_pauses.append(pauses[i] if i < len(pauses) else 0.0)
                samples = join_chunks(all_parts, sr, pauses=all_pauses)
                cue_audio_dur = len(samples) / sr if sr else 0.0
                # Mốc thực: mốc gốc + độ lùi tích lũy; nếu cue trước tràn thì
                # cue này bắt đầu muộn hơn mốc gốc (không đè lên cue trước).
                actual_start = cue.start_s + shift_s
                if actual_start < cursor_s:
                    actual_start = cursor_s
                actual_end = actual_start + cue_audio_dur
                overflowed = cue_audio_dur > slot + 1e-6
                if overflowed:
                    shift_s += cue_audio_dur - slot
                # Ghi audio: lấp khoảng trống tới actual_start rồi ghi cue
                # (khoảng lặng [nghỉ] đã nằm trong `samples`).
                gap = actual_start - cursor_s
                if writer is not None:
                    if gap > 0:
                        writer.write(make_silence(gap, sr))
                    writer.write(np.asarray(samples, dtype=np.float32))
                else:
                    if gap > 0:
                        collected.append(make_silence(gap, sr))
                    collected.append(np.asarray(samples, dtype=np.float32))
                cursor_s = actual_end
                dubbed.append(
                    DubbedCue(
                        index=cue.index,
                        scheduled_start_s=cue.start_s,
                        scheduled_end_s=cue.end_s,
                        actual_start_s=actual_start,
                        actual_end_s=actual_end,
                        text=clean_text,
                        effective_rate=effective_rate,
                        overflowed=overflowed,
                    )
                )
            # Đệm im lặng cuối tới hết mốc video (audio dài đúng bằng video).
            video_end = max(c.end_s for c in cues)
            if cursor_s < video_end:
                tail = video_end - cursor_s
                if writer is not None:
                    writer.write(make_silence(tail, sr))
                else:
                    collected.append(make_silence(tail, sr))
                cursor_s = video_end
        finally:
            if writer is not None:
                writer.__exit__(None, None, None)

        result = DubResult(
            samples=None if writer is not None else (
                np.concatenate(collected) if collected else np.zeros(0, dtype=np.float32)
            ),
            sample_rate=sr,
            output_path=Path(output_path) if output_path is not None else None,
            cues=dubbed,
            fallback_info=fallback_info,
            total_s=cursor_s,
        )
        if len(cues) >= PERFORMANCE_WARN_CUES:
            result.performance_note = (
                f"SRT có {len(cues)} cue (≥ {PERFORMANCE_WARN_CUES}) — hiệu năng "
                "chưa đo; giới hạn SRT dub thật được đo ở Bước 3 (TK2.5), "
                "không lấy số 100.000 của Tạo hàng loạt."
            )
        return result

    def dub_file(
        self,
        path: str | Path,
        voice: str,
        speed: float = 1.0,
        output_path: str | Path | None = None,
        router=None,
        voice_strict: bool = False,
    ) -> DubResult:
        """Lồng tiếng từ file .srt/.vtt (parse theo đuôi file)."""
        cues = parse_subtitle_file(path)
        return self.dub(cues, voice, speed, output_path, router, voice_strict)
