"""Interface engine chung cho HP Voice Studio (TK1.2, SPEC §3.1/§3.3).

Mọi engine (V3 local, V4 cloud sau này) cùng một interface
``synthesize(text, voice, options) -> AudioResult`` để UI, hàng đợi, SRT, batch,
history không biết đang dùng engine nào. UI/API KHÔNG import SDK trực tiếp.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Generator, Iterable

import numpy as np

SAMPLE_RATE_V3 = 48000
MAX_TEXT_CHARS = 20000  # mỗi request TTS (SPEC §6 api.max_text_chars)
MAX_CHUNK_CHARS = 256  # SDK tự chia chunk tối đa 256 ký tự (§2.2)


@dataclass
class AudioResult:
    """Kết quả tổng hợp một đoạn audio."""

    samples: np.ndarray  # float32, mono
    sample_rate: int = SAMPLE_RATE_V3
    engine: str = "v3"
    voice: str = ""

    @property
    def duration_s(self) -> float:
        """Độ dài audio (giây) = số mẫu / sample rate."""
        if self.sample_rate <= 0 or self.samples is None:
            return 0.0
        return float(len(self.samples)) / float(self.sample_rate)

    def __len__(self) -> int:
        return int(len(self.samples)) if self.samples is not None else 0


@dataclass
class SynthesisOptions:
    """Tùy chọn tổng hợp (mặc định khớp SDK v3 Turbo)."""

    temperature: float = 0.8
    top_k: int = 25
    top_p: float = 0.95
    max_chars: int = MAX_CHUNK_CHARS
    denoise: bool = True
    use_ref_codes: bool = True
    ref_audio: str | None = None  # clip mẫu cho clone tức thì (không cần đăng ký)


@dataclass
class VoiceInfo:
    """Một giọng đọc (preset hoặc clone)."""

    id: str  # tên giọng dùng khi gọi synthesize, VD "Hải Đăng"
    label: str = ""  # tên hiển thị (preset featured có prefix ⭐)
    gender: str = ""
    style: str = ""
    featured: int | None = None  # hạng editors' pick 1..10, None = không featured
    is_clone: bool = False
    description: str = ""


class EngineBase(ABC):
    """Interface chung mọi engine TTS."""

    name: str = "base"

    @abstractmethod
    def ensure_loaded(self, progress_callback=None) -> None:
        """Nạp model (lazy). progress_callback(stage: str) báo tiến trình."""

    @abstractmethod
    def synthesize(
        self, text: str, voice: str, options: SynthesisOptions | None = None
    ) -> AudioResult:
        """Tổng hợp toàn bộ text thành một AudioResult."""

    @abstractmethod
    def synthesize_stream(
        self, text: str, voice: str, options: SynthesisOptions | None = None
    ) -> Generator[AudioResult, None, None]:
        """Tổng hợp dạng stream: yield từng chunk AudioResult khi có."""

    @abstractmethod
    def synthesize_batch(
        self, texts: Iterable[str], voice: str, options: SynthesisOptions | None = None
    ) -> list[AudioResult]:
        """Tổng hợp nhiều câu, trả đúng thứ tự texts."""

    @abstractmethod
    def list_preset_voices(self) -> list[VoiceInfo]:
        """Liệt kê giọng preset (đọc từ engine, KHÔNG hardcode tên)."""

    @abstractmethod
    def resolve_voice(self, name: str | None) -> str | None:
        """Chuẩn hóa tên giọng (alias -> tên chính), None nếu không rõ."""

    @property
    @abstractmethod
    def sample_rate(self) -> int:
        """Sample rate của engine (V3 = 48000)."""

    def close(self) -> None:
        """Giải phóng engine (mặc định không làm gì)."""

    # --- Giọng clone (tùy chọn: chỉ V3 hỗ trợ thật) ---
    #: Handle SDK bên dưới (V3Engine gán object VieNeu thật sau ensure_loaded;
    #: FakeEngine/V4 giữ None). VoiceStore đọc thuộc tính này để lấy embedding.
    _tts = None

    def add_voice(
        self, name: str, ref_audio: str, description: str = "", gender: str = ""
    ) -> str:
        """Đăng ký giọng clone từ clip mẫu (chỉ trong bộ nhớ).

        Mặc định không hỗ trợ — engine nào clone được thì ghi đè (V3Engine,
        FakeEngine cho test). VoiceStore gọi method này trong ``clone_voice``.
        """
        raise NotImplementedError(f"Engine {self.name!r} không hỗ trợ clone giọng.")

    def remove_voice(self, name: str) -> None:
        """Gỡ giọng clone khỏi engine (chỉ trong bộ nhớ)."""
        raise NotImplementedError(f"Engine {self.name!r} không hỗ trợ gỡ giọng.")
