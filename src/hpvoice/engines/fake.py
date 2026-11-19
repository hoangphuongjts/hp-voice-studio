"""FakeEngine — engine giả tạo WAV tổng hợp (KHÔNG load model).

Dùng cho test + làm engine dự phòng trong routes khi app chưa gắn engine
thật (``app.state.engine`` trống). Âm thanh là sóng sin xác định theo text
(tần số phụ thuộc độ dài text) nên test đối chiếu được độ dài, sample rate,
giọng — nhưng KHÔNG phải giọng thật. Mọi kết quả dùng FakeEngine đều là
"kiểm chứng trên máy ảo/sandbox", không phải kiểm chứng thật.
"""

from __future__ import annotations

from typing import Generator, Iterable

import numpy as np

from .base import AudioResult, EngineBase, SynthesisOptions, VoiceInfo

__all__ = ["FakeEngine", "fake_wav_bytes"]

SAMPLE_RATE = 48000
#: Độ dài audio giả mỗi ký tự (giây) — đủ dài để đo mốc giờ, đủ ngắn để test nhanh.
SECONDS_PER_CHAR = 0.02
MIN_DURATION_S = 0.2
MAX_DURATION_S = 5.0

FAKE_VOICES = (
    ("Hải Đăng", "Nam", "Bắc"),
    ("Trúc Ly", "Nữ", "Bắc"),
    ("Mai Anh", "Nữ", "Bắc"),
    ("Thùy Dung", "Nữ", "Nam"),
    ("Quang Sơn", "Nam", "Trung"),
)


def fake_duration_s(text: str) -> float:
    """Độ dài audio giả cho một text (xác định, để test đối chiếu)."""
    dur = len(text) * SECONDS_PER_CHAR
    return max(MIN_DURATION_S, min(MAX_DURATION_S, dur))


def fake_samples(text: str, sr: int = SAMPLE_RATE) -> np.ndarray:
    """Sóng sin 440 Hz, biên độ 0,3, dài theo :func:`fake_duration_s`."""
    n = int(round(fake_duration_s(text) * sr))
    t = np.arange(n, dtype=np.float32) / sr
    return (0.3 * np.sin(2 * np.pi * 440.0 * t)).astype(np.float32)


def fake_wav_bytes(text: str, sr: int = SAMPLE_RATE) -> bytes:
    """WAV bytes (PCM 16-bit) của audio giả — dùng làm body mock cho V4."""
    import io

    import soundfile as sf

    buf = io.BytesIO()
    sf.write(buf, fake_samples(text, sr), sr, format="WAV", subtype="PCM_16")
    return buf.getvalue()


class FakeEngine(EngineBase):
    """Engine giả: không load model, trả sóng sin xác định theo text."""

    name = "fake"
    _tts = None  # không có SDK thật — VoiceStore hiểu là "không có embedding"

    def __init__(self, voices: tuple = FAKE_VOICES):
        self._voices = list(voices)
        self._loaded = False
        self._clone_names: set[str] = set()

    def ensure_loaded(self, progress_callback=None) -> None:
        self._loaded = True

    @property
    def is_loaded(self) -> bool:
        """True sau ensure_loaded — để /health báo đúng trạng thái."""
        return self._loaded

    @is_loaded.setter
    def is_loaded(self, value: bool) -> None:
        # Cho phép test double (tests/conftest.py) gán is_loaded trực tiếp.
        self._loaded = bool(value)

    @property
    def sample_rate(self) -> int:
        return SAMPLE_RATE

    def synthesize(
        self, text: str, voice: str, options: SynthesisOptions | None = None
    ) -> AudioResult:
        if text is None or not str(text).strip():
            raise ValueError("Text rỗng — không có gì để tạo giọng.")
        return AudioResult(
            samples=fake_samples(str(text)),
            sample_rate=SAMPLE_RATE,
            engine="fake",
            voice=voice or "Hải Đăng",
        )

    def synthesize_stream(
        self, text: str, voice: str, options: SynthesisOptions | None = None
    ) -> Generator[AudioResult, None, None]:
        yield self.synthesize(text, voice, options)

    def synthesize_batch(
        self, texts: Iterable[str], voice: str, options: SynthesisOptions | None = None
    ) -> list[AudioResult]:
        return [self.synthesize(t, voice, options) for t in texts]

    def list_preset_voices(self) -> list[VoiceInfo]:
        return [
            VoiceInfo(id=name, label=name, gender=gender, style="")
            for name, gender, _region in self._voices
        ]

    def resolve_voice(self, name: str | None) -> str | None:
        if name is None:
            return None
        known = {v[0] for v in self._voices} | self._clone_names
        return name if name in known else None

    def add_voice(
        self, name: str, ref_audio: str, description: str = "", gender: str = ""
    ) -> str:
        """Đăng ký giọng clone giả (chỉ ghi tên vào bộ nhớ — cho test route clone)."""
        self._clone_names.add(name)
        return name

    def remove_voice(self, name: str) -> None:
        """Gỡ giọng clone giả khỏi bộ nhớ."""
        if name not in self._clone_names:
            raise ValueError(f'Không có giọng clone "{name}" để gỡ.')
        self._clone_names.discard(name)
