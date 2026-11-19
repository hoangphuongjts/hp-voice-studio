"""AudioPost — hậu xử lý audio (SPEC §3.3, TK1.6/TK1.9).

- Time-stretch giữ cao độ 0,75×–1,5× (engine mặc định FFmpeg ``atempo``
  qua file tạm — xem docs/stretch-decision.md; librosa phase vocoder chỉ là
  đường dự phòng TÙY CHỌN, KHÔNG đóng gói trong bộ cài frozen — xem
  evidence/size-reduction/SIZE-REDUCTION-REPORT.md: SDK v3 Turbo không cần
  librosa, và atempo giữ năng lượng/đỉnh tốt hơn librosa).
  Tốc độ 1,0× KHÔNG qua time-stretch.
- Nối chunk + khoảng lặng (kể cả silence từ thẻ ``[nghỉ]``): khoảng nghỉ đo
  được ở khe là im lặng đuôi chunk trước + zeros chèn + im lặng đầu chunk sau
  (đúng ngữ nghĩa ``join_audio_chunks`` của SDK) nên chỉ chèn zeros bù cho đủ
  tổng — không cộng cả khoảng nghỉ lên trên độ dài đã đo.
- Chuẩn hoá đỉnh, xuất WAV 48 kHz, MP3 qua FFmpegManager, ghi dần ra đĩa
  cho bài dài (``WavWriter`` — không giữ toàn bộ batch trong RAM).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

__all__ = [
    "SAMPLE_RATE",
    "MIN_RATE",
    "MAX_RATE",
    "StretchUnavailableError",
    "WavWriter",
    "edge_silence_seconds",
    "join_chunks",
    "make_silence",
    "normalize_peak",
    "stretch_audio_file",
    "time_stretch",
    "write_wav",
]

SAMPLE_RATE = 48000
MIN_RATE = 0.75
MAX_RATE = 1.5
#: Ngưỡng "có tiếng" trên envelope mean|x| cửa sổ 10 ms (khớp EDGE_THRESH_DB
#: của upstream core_utils).
EDGE_THRESH_DB = -45.0


class StretchUnavailableError(ValueError):
    """Đổi tốc độ không thực hiện được: không có FFmpeg (atempo) và cũng
    không có librosa dự phòng. API bắt lỗi này để trả 400 với hướng dẫn
    tải FFmpeg, thay vì 500 (xem routes_tts/routes_srt)."""


_default_ffmpeg_manager = None


def _get_ffmpeg_manager(ffmpeg_manager=None):
    """FFmpegManager đã truyền vào, hoặc singleton mặc định (lazy import để
    tránh vòng lặp import — post.py và ffmpeg_manager.py cùng package)."""
    global _default_ffmpeg_manager
    if ffmpeg_manager is not None:
        return ffmpeg_manager
    if _default_ffmpeg_manager is None:
        from .ffmpeg_manager import FFmpegManager

        _default_ffmpeg_manager = FFmpegManager()
    return _default_ffmpeg_manager


def _stretch_librosa(y: np.ndarray, rate: float) -> np.ndarray:
    """Phase vocoder librosa — CHỈ dùng khi librosa còn cài (máy dev).
    Bộ cài frozen KHÔNG đóng gói librosa (xem evidence/size-reduction) nên
    đường này ném StretchUnavailableError thay vì ImportError khó hiểu."""
    try:
        import librosa
    except ImportError as exc:
        raise StretchUnavailableError(
            "Không đổi được tốc độ: chưa có FFmpeg và librosa cũng chưa cài. "
            "Hãy tải FFmpeg ở tab Cài đặt (cần mạng lần đầu), rồi thử lại."
        ) from exc
    return librosa.effects.time_stretch(y, rate=float(rate))


def _stretch_atempo_array(
    y: np.ndarray, sr: int, rate: float, ffmpeg_manager=None
) -> np.ndarray | None:
    """Đổi tốc độ mảng numpy bằng FFmpeg ``atempo`` qua file tạm.
    Trả None khi không có FFmpeg (caller xét fallback librosa)."""
    import tempfile

    import soundfile as sf

    manager = _get_ffmpeg_manager(ffmpeg_manager)
    with tempfile.TemporaryDirectory(prefix="hp-stretch-") as tmpdir:
        in_wav = Path(tmpdir) / "in.wav"
        out_wav = Path(tmpdir) / "out.wav"
        sf.write(str(in_wav), np.asarray(y, dtype=np.float32), sr, subtype="PCM_16")
        if not manager.run_atempo(in_wav, out_wav, rate):
            return None
        out, _ = sf.read(str(out_wav), dtype="float32")
        return np.asarray(out, dtype=np.float32).reshape(-1)


def make_silence(seconds: float, sr: int = SAMPLE_RATE) -> np.ndarray:
    """Mảng zeros dài ``seconds`` giây."""
    return np.zeros(max(0, int(round(seconds * sr))), dtype=np.float32)


def edge_silence_seconds(
    wav: np.ndarray, sr: int, thresh_db: float = EDGE_THRESH_DB
) -> tuple[float, float]:
    """``(im lặng đầu, im lặng cuối)`` tính bằng giây (envelope mean|x| cửa
    sổ 10 ms, dưới ngưỡng là im lặng). Wav toàn im lặng → ``(độ dài, 0)``."""
    wav = np.asarray(wav, dtype=np.float32)
    n = int(wav.size)
    win = max(1, int(0.01 * sr))
    n_win = n // win
    if n_win == 0:
        return (n / sr if sr else 0.0, 0.0)
    env = np.abs(wav[: n_win * win]).reshape(n_win, win).mean(1)
    above = np.flatnonzero(env > 10 ** (thresh_db / 20))
    if not above.size:
        return (n / sr, 0.0)
    lead = int(above[0]) * win / sr
    tail = (n - (int(above[-1]) + 1) * win) / sr
    return (lead, tail)


def _pad_for_pause(
    prev: np.ndarray, nxt: np.ndarray, sr: int, pause_s: float
) -> int:
    """Số mẫu zeros cần chèn để khoảng nghỉ THẬT ở khe (đuôi trước + zeros +
    đầu sau) đạt ``pause_s``; 0 nếu im lặng mép đã đủ."""
    _, tail = edge_silence_seconds(prev, sr)
    lead, _ = edge_silence_seconds(nxt, sr)
    return max(0, int(round(pause_s * sr)) - int(round(tail * sr)) - int(round(lead * sr)))


def join_chunks(
    chunks: list[np.ndarray], sr: int = SAMPLE_RATE, pauses: list[float] | None = None
) -> np.ndarray:
    """Nối các chunk, chèn khoảng lặng ``pauses[i]`` giây giữa chunk ``i`` và
    ``i+1`` (bù zeros cho đủ tổng — xem :func:`_pad_for_pause`). ``pauses``
    thiếu thì mặc định 0 (nối thẳng)."""
    if not chunks:
        return np.array([], dtype=np.float32)
    pauses = list(pauses or [])
    parts: list[np.ndarray] = [np.asarray(chunks[0], dtype=np.float32)]
    for i in range(1, len(chunks)):
        pause_s = pauses[i - 1] if i - 1 < len(pauses) else 0.0
        nxt = np.asarray(chunks[i], dtype=np.float32)
        if pause_s > 0:
            # Đo im lặng mép trên chunk GỐC (không đo trên zeros vừa chèn).
            pad = _pad_for_pause(chunks[i - 1], nxt, sr, pause_s)
            if pad > 0:
                parts.append(np.zeros(pad, dtype=np.float32))
        parts.append(nxt)
    return np.concatenate(parts) if parts else np.array([], dtype=np.float32)


def time_stretch(
    audio: np.ndarray, sr: int, rate: float, engine: str = "atempo",
    ffmpeg_manager=None,
) -> tuple[np.ndarray, bool]:
    """Đổi tốc độ giữ cao độ. Trả ``(audio_mới, đã_stretch)``.

    - ``rate == 1.0`` → trả đúng mẫu gốc, ``đã_stretch=False`` (không tốn
      thời gian xử lý thêm — T2.4).
    - ``rate`` ngoài 0,75–1,5 → ``ValueError``.
    - ``engine="atempo"`` (mặc định): FFmpeg ``atempo`` qua file tạm — giữ
      năng lượng/đỉnh tốt hơn librosa, không cần numba JIT (xem
      docs/stretch-decision.md). Không có FFmpeg thì thử librosa dự phòng;
      cả hai đều không có → ``StretchUnavailableError`` (API trả 400).
    - ``engine="librosa"``: ``librosa.effects.time_stretch`` (phase vocoder)
      — chỉ chạy khi librosa còn cài (máy dev); bộ cài frozen không có
      librosa nên đường này ném ``StretchUnavailableError``.
    """
    if rate < MIN_RATE or rate > MAX_RATE:
        raise ValueError(
            f"Tốc độ phải trong khoảng {MIN_RATE}×–{MAX_RATE}×, nhận {rate}×."
        )
    y = np.asarray(audio, dtype=np.float32)
    if rate == 1.0:
        return y, False
    if engine == "atempo":
        out = _stretch_atempo_array(y, sr, rate, ffmpeg_manager)
        if out is not None:
            return out, True
        return _stretch_librosa(y, rate), True
    if engine == "librosa":
        return _stretch_librosa(y, rate), True
    raise ValueError(
        f"Engine time-stretch không hỗ trợ: {engine!r} (chỉ 'atempo'/'librosa')."
    )


def normalize_peak(audio: np.ndarray, target: float = 0.95) -> np.ndarray:
    """Chuẩn hoá đỉnh về ``target`` (mặc định 0,95): scale tuyến tính sao cho
    đỉnh = target. Audio im lặng giữ nguyên."""
    y = np.asarray(audio, dtype=np.float32)
    peak = float(np.max(np.abs(y))) if y.size else 0.0
    if peak <= 0:
        return y
    return (y * (target / peak)).astype(np.float32)


def stretch_audio_file(
    input_wav: str | Path,
    output_wav: str | Path,
    rate: float,
    ffmpeg_manager=None,
) -> str:
    """Đổi tốc độ file WAV giữ cao độ — engine mặc định theo TK1.9
    (xem docs/stretch-decision.md): thử FFmpeg ``atempo`` trước (giữ
    năng lượng/đỉnh tốt hơn, không cần numba JIT); không có FFmpeg thì
    fallback librosa trên mảng numpy (chỉ khi librosa còn cài — bộ cài
    frozen không có librosa). Cả hai đều không có → ``StretchUnavailableError``
    (API trả 400, hướng dẫn tải FFmpeg). ``rate == 1.0`` → chép nguyên file,
    không stretch.

    Trả ``"atempo"`` / ``"librosa"`` / ``"copy"`` (engine đã dùng).
    Ném ``ValueError`` khi rate ngoài 0,75–1,5.
    """
    if rate < MIN_RATE or rate > MAX_RATE:
        raise ValueError(
            f"Tốc độ phải trong khoảng {MIN_RATE}×–{MAX_RATE}×, nhận {rate}×."
        )
    import shutil

    if rate == 1.0:
        shutil.copyfile(str(input_wav), str(output_wav))
        return "copy"
    if ffmpeg_manager is not None and ffmpeg_manager.run_atempo(
        input_wav, output_wav, rate
    ):
        return "atempo"
    import soundfile as sf

    y, sr = sf.read(str(input_wav), dtype="float32")
    out = _stretch_librosa(y, rate)  # dự phòng; thiếu librosa -> StretchUnavailableError
    write_wav(output_wav, out, sr)
    return "librosa"


def write_wav(path: str | Path, audio: np.ndarray, sr: int = SAMPLE_RATE) -> Path:
    """Ghi WAV 48 kHz mono (PCM 16-bit)."""
    import soundfile as sf

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(p), np.asarray(audio, dtype=np.float32), sr, subtype="PCM_16")
    return p


class WavWriter:
    """Ghi WAV dần ra đĩa theo từng chunk (bài dài/batch: không giữ toàn bộ
    audio trong RAM). Dùng làm context manager."""

    def __init__(self, path: str | Path, sr: int = SAMPLE_RATE) -> None:
        self.path = Path(path)
        self.sr = sr
        self._sf = None

    def __enter__(self) -> "WavWriter":
        import soundfile as sf

        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._sf = sf.SoundFile(
            str(self.path), mode="w", samplerate=self.sr,
            channels=1, subtype="PCM_16",
        )
        return self

    def write(self, audio: np.ndarray) -> None:
        assert self._sf is not None, "WavWriter chưa mở (dùng with ...:)"
        self._sf.write(np.asarray(audio, dtype=np.float32))

    def __exit__(self, *exc) -> None:
        if self._sf is not None:
            self._sf.close()
            self._sf = None
