"""ConversationEngine — hội thoại/podcast nhiều giọng (TK2.4, SPEC §3.3, T3.2).

- Kịch bản: danh sách lượt ``(speaker, text)``; mỗi speaker khóa 1 giọng cố
  định (voice-lock, TH-10) — một speaker không đổi giọng giữa chừng, mở lại
  kịch bản đã lưu thì giọng không đổi (đối chiếu ``voice_id`` trong file).
- Gom lượt theo speaker → ``synthesize_batch`` từng nhóm → ghép ĐÚNG THỨ TỰ
  lượt gốc + khoảng lặng giữa lượt (mặc định 0,5 s) thành 1 file + .srt theo
  speaker (mốc từng lượt).
- Tối đa 8 speaker (theo upstream). Lượt rỗng → lỗi rõ. Text mỗi lượt tối đa
  20.000 ký tự (giới hạn request TTS §4).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from ..engines.base import MAX_TEXT_CHARS, AudioResult
from .post import join_chunks, make_silence
from .srt_writer import SrtCue, format_srt_time

__all__ = [
    "ConversationEngine",
    "ConversationLine",
    "ConversationResult",
    "MAX_SPEAKERS",
    "DEFAULT_PAUSE_S",
]

MAX_SPEAKERS = 8  # tối đa 8 speaker (theo upstream)
DEFAULT_PAUSE_S = 0.5  # khoảng lặng giữa hai lượt (giây)


@dataclass
class ConversationLine:
    """Một lượt thoại: ai nói + nói gì."""

    speaker: str
    text: str


@dataclass
class ConversationResult:
    """Kết quả hội thoại: audio ghép + mốc từng lượt + giọng đã dùng."""

    samples: np.ndarray
    sample_rate: int = 48000
    cues: list[SrtCue] = field(default_factory=list)  # mốc từng lượt (text = "Speaker: line")
    voices_used: dict[str, str] = field(default_factory=dict)  # speaker -> voice_id
    engine: str = ""

    @property
    def duration_s(self) -> float:
        return float(len(self.samples)) / self.sample_rate if self.sample_rate else 0.0

    def to_srt(self) -> str:
        """Xuất .srt theo speaker (mỗi lượt 1 cue)."""
        lines: list[str] = []
        for c in self.cues:
            lines.append(str(c.index))
            lines.append(f"{format_srt_time(c.start_s)} --> {format_srt_time(c.end_s)}")
            lines.append(c.text)
            lines.append("")
        return "\n".join(lines)


class ConversationEngine:
    """Ghép kịch bản nhiều giọng thành 1 file audio + .srt theo speaker."""

    def __init__(self, engine, pause_between_turns_s: float = DEFAULT_PAUSE_S):
        self.engine = engine
        self.pause_between_turns_s = pause_between_turns_s

    def _check(self, lines: list[ConversationLine], speakers: dict[str, str]) -> None:
        if not lines:
            raise ValueError("Kịch bản rỗng — cần ít nhất 1 lượt thoại.")
        if len(speakers) > MAX_SPEAKERS:
            raise ValueError(
                f"Tối đa {MAX_SPEAKERS} nhân vật, nhận {len(speakers)}."
            )
        for i, line in enumerate(lines, start=1):
            if not str(line.speaker).strip():
                raise ValueError(f"Lượt {i} thiếu tên nhân vật.")
            if line.speaker not in speakers:
                raise ValueError(
                    f"Lượt {i}: nhân vật {line.speaker!r} chưa gán giọng "
                    "(mỗi nhân vật phải có đúng 1 giọng cố định)."
                )
            if not str(line.text).strip():
                raise ValueError(f"Lượt {i} của {line.speaker!r} rỗng — không có gì để đọc.")
            if len(str(line.text)) > MAX_TEXT_CHARS:
                raise ValueError(
                    f"Lượt {i} dài {len(line.text)} ký tự, vượt giới hạn "
                    f"{MAX_TEXT_CHARS} ký tự/lượt."
                )

    def synthesize(
        self,
        lines: list[ConversationLine] | list[dict],
        speakers: dict[str, str],
        pause_between_turns_s: float | None = None,
    ) -> ConversationResult:
        """Tổng hợp kịch bản thành 1 audio + mốc từng lượt.

        Gom lượt theo speaker → ``synthesize_batch`` từng nhóm (giữ đúng thứ
        tự lượt gốc khi ghép) → nối bằng ``join_chunks`` + khoảng lặng.
        """
        norm_lines = [
            line if isinstance(line, ConversationLine) else ConversationLine(
                speaker=str(line.get("speaker") or ""),
                text=str(line.get("text") or ""),
            )
            for line in lines
        ]
        speakers = {str(k): str(v) for k, v in speakers.items()}
        self._check(norm_lines, speakers)
        pause_s = self.pause_between_turns_s if pause_between_turns_s is None else pause_between_turns_s

        # Gom chỉ số lượt theo speaker (giữ thứ tự gốc trong mỗi nhóm).
        grouped: dict[str, list[int]] = {}
        for idx, line in enumerate(norm_lines):
            grouped.setdefault(line.speaker, []).append(idx)
        # Batch từng nhóm speaker (1 lần gọi / speaker).
        audios_by_index: dict[int, np.ndarray] = {}
        sr = getattr(self.engine, "sample_rate", 48000)
        for speaker, idxs in grouped.items():
            results = self.engine.synthesize_batch(
                [norm_lines[i].text for i in idxs], speakers[speaker]
            )
            if len(results) != len(idxs):
                raise RuntimeError(
                    f"synthesize_batch trả {len(results)} audio cho {len(idxs)} "
                    f"lượt của {speaker!r} (lệch thứ tự?)."
                )
            for i, result in zip(idxs, results):
                sr = result.sample_rate
                audios_by_index[i] = np.asarray(result.samples, dtype=np.float32)

        # Ghép đúng thứ tự lượt gốc + khoảng lặng giữa lượt.
        parts: list[np.ndarray] = []
        pauses: list[float] = []
        cues: list[SrtCue] = []
        cursor_s = 0.0
        for idx, line in enumerate(norm_lines):
            audio = audios_by_index[idx]
            dur = len(audio) / sr if sr else 0.0
            if idx > 0:
                # Khoảng lặng trước lượt này (đã chèn bằng join_chunks).
                cursor_s += pause_s
            cues.append(
                SrtCue(
                    index=idx + 1,
                    start_s=cursor_s,
                    end_s=cursor_s + dur,
                    text=f"{line.speaker}: {line.text}",
                )
            )
            parts.append(audio)
            if idx < len(norm_lines) - 1:
                pauses.append(pause_s)
            cursor_s += dur
        joined = join_chunks(parts, sr, pauses=pauses)
        return ConversationResult(
            samples=joined,
            sample_rate=sr,
            cues=cues,
            voices_used=dict(speakers),
            engine=getattr(self.engine, "name", ""),
        )

    # --- Lưu/mở kịch bản (T3.2: mở lại kịch bản → giọng không đổi) ---
    @staticmethod
    def save_script(
        path: str | Path,
        lines: list[ConversationLine] | list[dict],
        speakers: dict[str, str],
    ) -> Path:
        """Lưu kịch bản (lượt + khóa speaker→voice) ra JSON."""
        data = {
            "speakers": {str(k): str(v) for k, v in speakers.items()},
            "lines": [
                {
                    "speaker": line.speaker if isinstance(line, ConversationLine) else str(line.get("speaker")),
                    "text": line.text if isinstance(line, ConversationLine) else str(line.get("text")),
                }
                for line in lines
            ],
        }
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(p)  # ghi atomic (tránh corrupt khi tắt đột ngột, TH-21)
        return p

    @staticmethod
    def load_script(path: str | Path) -> tuple[list[ConversationLine], dict[str, str]]:
        """Mở kịch bản JSON → (lượt, khóa speaker→voice)."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        lines = [
            ConversationLine(speaker=str(item["speaker"]), text=str(item["text"]))
            for item in data.get("lines", [])
        ]
        speakers = {str(k): str(v) for k, v in (data.get("speakers") or {}).items()}
        return lines, speakers

    @staticmethod
    def write_wav(path: str | Path, result: ConversationResult) -> Path:
        """Ghi audio hội thoại ra WAV."""
        from .post import write_wav

        return write_wav(path, result.samples, result.sample_rate)
