"""V3Engine — adapter DUY NHẤT gọi SDK vieneu (TK1.2, SPEC §3.3).

- Lazy init: model chỉ nạp khi ``ensure_loaded()`` được gọi lần đầu.
- Precision: "auto" -> theo CPU (VNNI -> int8, không -> fp32, xem cpu_detect);
  "fp32"/"int8" ép theo config.
- Mọi gọi SDK (infer/infer_stream/infer_batch/list_preset_voices/add_voice)
  đều đi qua đây; UI/API không import ``vieneu`` trực tiếp (ADR-03).
- Inference tuần tự hoá bằng lock (ONNX engine chạy tuần tự cho an toàn, như T1).
"""

from __future__ import annotations

import threading
import time
from typing import Generator, Iterable

import numpy as np

from .base import (
    MAX_CHUNK_CHARS,
    MAX_TEXT_CHARS,
    AudioResult,
    EngineBase,
    SynthesisOptions,
    VoiceInfo,
)
from .cpu_detect import default_precision as cpu_default_precision
from .cpu_detect import detect_cpu


class V3Engine(EngineBase):
    """Adapter VieNeu-TTS v3 Turbo (SDK vieneu 3.8.4, ONNX/CPU, 48 kHz)."""

    name = "v3"

    def __init__(
        self,
        precision: str = "auto",
        backbone_repo: str = "pnnbao-ump/VieNeu-TTS-v3-Turbo",
        threads: int = 0,
        max_batch_size: int = 32,
        model_dir: str = "",
    ):
        self.requested_precision = (precision or "auto").lower()
        if self.requested_precision not in ("auto", "fp32", "int8"):
            raise ValueError(f'precision không hợp lệ: {precision} (chỉ "auto"/"fp32"/"int8")')
        self.backbone_repo = backbone_repo
        self.threads = threads
        self.max_batch_size = max_batch_size
        self.model_dir = model_dir
        self._tts = None  # instance SDK Vieneu (factory function)
        self._lock = threading.Lock()
        self._loaded = False
        self._load_error: str | None = None
        # Tên preset gốc (chụp ngay sau khi nạp model, TRƯỚC khi thêm giọng clone):
        # SDK list_preset_voices() trả cả giọng clone đã đăng ký, nên V3Engine giữ
        # snapshot này để list_preset_voices() luôn trả đúng 25 giọng gốc (T1.3).
        self._preset_names: list[str] = []
        self.load_seconds: float | None = None  # thời gian nạp model lần gần nhất
        self.last_first_chunk_latency_s: float | None = None
        # Precision thực tế sau khi resolve "auto" (ghi rõ để test/UI đối chiếu).
        self.precision = self._resolve_precision()

    # --- Precision ---
    def _resolve_precision(self) -> str:
        if self.requested_precision != "auto":
            return self.requested_precision
        return cpu_default_precision()

    @property
    def cpu_info(self):
        """Thông tin CPU + VNNI đã phát hiện (để UI/Cài đặt hiển thị)."""
        return detect_cpu()

    # --- Nạp model (lazy) ---
    def ensure_loaded(self, progress_callback=None) -> None:
        """Nạp model lần đầu (kèm báo tiến trình qua callback). Gọi lại thì no-op."""
        if self._loaded:
            return
        if self._load_error is not None:
            raise RuntimeError(f"Engine V3 nạp model thất bại trước đó: {self._load_error}")
        if progress_callback:
            progress_callback(f"Đang nạp model v3 Turbo ({self.precision})...")
        t0 = time.perf_counter()
        try:
            from vieneu import Vieneu

            kwargs: dict = {
                "backbone_repo": self.backbone_repo,
                "precision": self.precision,
                "threads": self.threads,
                "max_batch_size": self.max_batch_size,
            }
            if self.model_dir:
                kwargs["onnx_dir"] = self.model_dir
            self._tts = Vieneu(mode="v3turbo", **kwargs)
        except Exception as exc:  # noqa: BLE001 - ghi lại để /health báo lỗi rõ
            self._load_error = str(exc)
            raise RuntimeError(f"Không nạp được model v3 Turbo: {exc}") from exc
        self.load_seconds = time.perf_counter() - t0
        self._loaded = True
        # Chụp tên preset gốc (trước mọi add_voice sau này).
        try:
            self._preset_names = [vid for _, vid in self._tts.list_preset_voices()]
        except Exception:
            self._preset_names = []
        if progress_callback:
            progress_callback(f"Model v3 Turbo sẵn sàng sau {self.load_seconds:.1f}s.")

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def sample_rate(self) -> int:
        if self._tts is not None:
            return int(getattr(self._tts, "sample_rate", 48000))
        return 48000

    # --- Kiểm tra đầu vào chung ---
    def _check_text(self, text: str) -> str:
        if text is None or not str(text).strip():
            raise ValueError("Text rỗng — không có gì để tạo giọng.")
        text = str(text)
        if len(text) > MAX_TEXT_CHARS:
            raise ValueError(
                f"Text dài {len(text)} ký tự, vượt giới hạn {MAX_TEXT_CHARS} ký tự/request."
            )
        return text

    def _check_voice(self, voice: str) -> str:
        self.ensure_loaded()
        resolved = self._tts.resolve_voice_name(voice)
        if resolved is None:
            raise ValueError(f'Giọng không tồn tại: "{voice}"')
        return resolved

    def _options(self, options: SynthesisOptions | None) -> SynthesisOptions:
        return options or SynthesisOptions()

    # --- Interface EngineBase ---
    def synthesize(
        self, text: str, voice: str, options: SynthesisOptions | None = None
    ) -> AudioResult:
        text = self._check_text(text)
        voice = self._check_voice(voice)
        opts = self._options(options)
        with self._lock:
            audio = self._tts.infer(
                text,
                voice=voice,
                ref_audio=opts.ref_audio,
                temperature=opts.temperature,
                top_k=opts.top_k,
                top_p=opts.top_p,
                max_chars=opts.max_chars,
                denoise=opts.denoise,
                use_ref_codes=opts.use_ref_codes,
            )
        samples = np.asarray(audio, dtype=np.float32).reshape(-1)
        return AudioResult(
            samples=samples, sample_rate=self.sample_rate, engine="v3", voice=voice
        )

    def synthesize_stream(
        self, text: str, voice: str, options: SynthesisOptions | None = None
    ) -> Generator[AudioResult, None, None]:
        text = self._check_text(text)
        voice = self._check_voice(voice)
        opts = self._options(options)
        t0 = time.perf_counter()
        first = True
        # infer_stream là generator của SDK; khóa giữ trong suốt quá trình stream
        # để hai luồng không gọi ONNX cùng lúc.
        with self._lock:
            stream = self._tts.infer_stream(
                text,
                voice=voice,
                ref_audio=opts.ref_audio,
                temperature=opts.temperature,
                top_k=opts.top_k,
                top_p=opts.top_p,
                max_chars=opts.max_chars,
                denoise=opts.denoise,
                use_ref_codes=opts.use_ref_codes,
            )
            for chunk in stream:
                if first:
                    self.last_first_chunk_latency_s = time.perf_counter() - t0
                    first = False
                samples = np.asarray(chunk, dtype=np.float32).reshape(-1)
                if len(samples) == 0:
                    continue
                yield AudioResult(
                    samples=samples, sample_rate=self.sample_rate, engine="v3", voice=voice
                )
        if first:
            # Stream rỗng (text chỉ có khoảng trắng đã bị chặn ở trên; phòng hờ).
            self.last_first_chunk_latency_s = time.perf_counter() - t0

    def synthesize_batch(
        self, texts: Iterable[str], voice: str, options: SynthesisOptions | None = None
    ) -> list[AudioResult]:
        texts = [self._check_text(t) for t in texts]
        if not texts:
            return []
        voice = self._check_voice(voice)
        opts = self._options(options)
        with self._lock:
            audios = self._tts.infer_batch(
                texts,
                voice=voice,
                temperature=opts.temperature,
                top_k=opts.top_k,
                top_p=opts.top_p,
                max_chars=opts.max_chars,
                denoise=opts.denoise,
                use_ref_codes=opts.use_ref_codes,
            )
        if len(audios) != len(texts):
            raise RuntimeError(
                f"infer_batch trả {len(audios)} audio cho {len(texts)} câu (lệch thứ tự?)."
            )
        return [
            AudioResult(
                samples=np.asarray(a, dtype=np.float32).reshape(-1),
                sample_rate=self.sample_rate,
                engine="v3",
                voice=voice,
            )
            for a in audios
        ]

    def list_preset_voices(self) -> list[VoiceInfo]:
        """25 giọng preset, đọc từ SDK (KHÔNG hardcode tên giọng).

        Chỉ trả giọng trong snapshot preset gốc (SDK trả cả giọng clone đã đăng
        ký vào cùng danh sách, nên lọc theo snapshot chụp lúc nạp model).
        """
        self.ensure_loaded()
        voices: list[VoiceInfo] = []
        for label, voice_id in self._tts.list_preset_voices():
            if self._preset_names and str(voice_id) not in self._preset_names:
                continue  # giọng clone — không thuộc preset gốc
            gender = ""
            style = ""
            featured = None
            try:
                detail = self._tts.get_preset_voice(voice_id)
                gender = str(detail.get("gender", "") or "")
                style = str(detail.get("style", "") or "")
                featured = detail.get("featured")
            except Exception:
                pass
            if featured is None and isinstance(label, str) and label.startswith("⭐"):
                featured = 0  # featured nhưng SDK không trả hạng -> vẫn đánh dấu
            voices.append(
                VoiceInfo(
                    id=str(voice_id),
                    label=str(label),
                    gender=gender,
                    style=style,
                    featured=featured,
                    is_clone=False,
                )
            )
        return voices

    def resolve_voice(self, name: str | None) -> str | None:
        self.ensure_loaded()
        return self._tts.resolve_voice_name(name)

    # --- Giọng clone (dùng bởi VoiceStore; KHÔNG tự ghi đè assets) ---
    def add_voice(
        self,
        name: str,
        ref_audio: str,
        description: str = "",
        gender: str = "",
    ) -> str:
        """Đăng ký giọng clone vào engine (chỉ trong bộ nhớ; lưu file do VoiceStore)."""
        self.ensure_loaded()
        return self._tts.add_voice(
            name, ref_audio, description=description, gender=gender, save=False
        )

    def remove_voice(self, name: str) -> None:
        """Gỡ giọng khỏi engine (chỉ trong bộ nhớ; lưu file do VoiceStore)."""
        self.ensure_loaded()
        self._tts.remove_voice(name, save=False)

    def save_voices(self, path: str) -> str:
        """Ghi toàn bộ giọng (preset + clone) ra file HP riêng. KHÔNG ghi đè assets."""
        self.ensure_loaded()
        return self._tts.save_voices(path)

    def encode_reference(self, ref_audio: str):
        """Mã hóa clip mẫu -> (speaker_emb, ref_codes)."""
        self.ensure_loaded()
        return self._tts.encode_reference(ref_audio)

    def save_wav(self, result: AudioResult, path: str) -> str:
        """Ghi AudioResult ra WAV 48 kHz (dùng soundfile, không qua SDK)."""
        import soundfile as sf

        sf.write(path, result.samples, result.sample_rate, format="WAV")
        return path

    def close(self) -> None:
        if self._tts is not None:
            try:
                close = getattr(self._tts, "close", None)
                if callable(close):
                    close()
            except Exception:
                pass
        self._tts = None
        self._loaded = False
