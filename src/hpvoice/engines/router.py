"""EngineRouter — chọn engine + fallback V4→V3 (TK2.2, SPEC §3.3/TH-05).

- Interface chung ``synthesize(text, voice, options) -> (AudioResult, FallbackInfo|None)``
  để UI/hàng đợi/SRT/batch không biết đang dùng engine nào.
- Fallback V3 khi V4 lỗi (401/403/429/5xx/timeout/mất mạng): đổi giọng qua
  bảng ánh xạ ``docs/voice-fallback-map.md`` (giới tính + vùng → preset V3
  gần nhất; không có preset tương đương gần → mặc định ``"Hải Đăng"``).
  Kết quả job + log PHẢI ghi rõ cả lý do lẫn giọng mới, VD:
  ``"V4 lỗi 403 hết quota → fallback V3, giọng đổi Hạ Vy → Trúc Ly"``.
- Job khóa giọng (``voice_strict=True``) thì KHÔNG fallback — trả lỗi thay vì
  đổi giọng lặng lẽ.
- Quy tắc fallback giọng trong config: ``fallback_voice: "map" | "default" | "fail"``
  (mặc định ``"map"``).
- Fallback V4→V3 cho cả ``/v1/dialogue``, ``/v1/dub``, ``/v1/srt`` dùng cùng
  bảng ánh xạ + ``voice_strict`` (SPEC §3.3 bổ sung G4): xem
  :meth:`EngineRouter.fallback_voice_for` và :meth:`EngineRouter.should_fallback`.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..engines.base import AudioResult, EngineBase, SynthesisOptions
from .v4_engine import V4Error

__all__ = [
    "DEFAULT_V3_VOICE",
    "EngineRouter",
    "FallbackInfo",
    "KNOWN_V4_VOICES",
    "V3_PRESETS",
    "map_v4_voice_to_v3",
]

#: Giọng V3 mặc định khi không map được giọng V4 nào gần (SPEC §3.3).
DEFAULT_V3_VOICE = "Hải Đăng"

#: 25 preset V3 Turbo (SPEC §2.2, ``voices_v3_turbo.json``): tên → (giới tính, vùng, phong cách).
V3_PRESETS: dict[str, tuple[str, str, str]] = {
    "Adam bựa": ("Nam", "Bắc", "tự nhiên"),
    "Trúc Ly": ("Nữ", "Bắc", "tự nhiên"),
    "Thiện Minh": ("Nam", "Bắc", "kể chuyện"),
    "Mai Anh": ("Nữ", "Bắc", "tin tức"),
    "Hải Đăng": ("Nam", "Bắc", "tự nhiên"),
    "Thùy Dung": ("Nữ", "Nam", "tin tức"),
    "Thiền Tâm Đức": ("Nam", "Bắc", "kể chuyện"),
    "Ngọc Huyền": ("Nữ", "Bắc", "tự nhiên"),
    "Quang Sơn": ("Nam", "Trung", "tự nhiên"),
    "Ngọc Trân": ("Nữ", "Trung", "tự nhiên"),
    "Minh Đức": ("Nam", "Bắc", "tin tức"),
    "Phạm Tuyên": ("Nam", "Bắc", "tự nhiên"),
    "Thái Sơn": ("Nam", "Nam", "kể chuyện"),
    "Xuân Vĩnh": ("Nam", "Bắc", "tự nhiên"),
    "Thanh Bình": ("Nam", "Bắc", "kể chuyện"),
    "Ngọc Linh": ("Nữ", "Bắc", "kể chuyện"),
    "Đoan Trang": ("Nữ", "Bắc", "tự nhiên"),
    "Thục Đoan": ("Nữ", "Nam", "kể chuyện"),
    "Minh Triết": ("Nam", "Nam", "tin tức"),
    "Mỹ Duyên": ("Nữ", "Nam", "đọc truyện"),
    "Quỳnh Anh": ("Nữ", "Bắc", "đọc truyện"),
    "Đức Trí": ("Nam", "Nam", "đọc truyện"),
    "Kim Thanh": ("Nữ", "Nam", "đọc truyện"),
    "Adam": ("Nam", "Nam", "tự nhiên"),
    "Quốc Tuấn": ("Nam", "Bắc", "tự nhiên"),
}

#: Giọng V4 ĐÃ BIẾT (mẫu — xem docs/voice-fallback-map.md): tên hiển thị/id →
#: (giới tính, vùng, phong cách, đã_xác_nhận_từ_catalogue?).
#: - "Hạ Vy": giọng V4 đã kiểm chứng tạo WAV thật 19/11 (SPEC §2.4); giới tính/
#:   vùng ghi "Nữ · Bắc" là GIẢ ĐỊNH theo catalogue (182 giọng nữ Bắc) — CHƯA
#:   xác nhận bằng GET /v1/voices thật, cần key thật để soát lại.
#: - "Ngọc Lan": tên xuất hiện trong ví dụ OpenAPI (PublicVoiceDto/PublicDubResponseDto)
#:   với mô tả "Giọng nữ miền Nam, ấm và rõ" → Nữ · Nam (đã xác nhận từ OpenAPI).
#: - "Trúc Ly": V4 cũng có preset trùng tên V3 (ví dụ PublicTtsRequestDto dùng
#:   voiceId "Trúc Ly" — và OpenAPI ghi voiceId "Thiện Minh" render ra "Anh Khôi",
#:   tức V4 có alias riêng); map cùng tên là điểm bắt đầu, vẫn cần catalogue thật.
#: Bảng ĐẦY ĐỦ 707 giọng chỉ sinh được từ GET /v1/voices với key thật —
#: chờ kiểm chứng thật, không đoán mò thêm.
KNOWN_V4_VOICES: dict[str, tuple[str, str, str, bool]] = {
    "Hạ Vy": ("Nữ", "Bắc", "tự nhiên", False),
    "Ngọc Lan": ("Nữ", "Nam", "tự nhiên", True),
    "Trúc Ly": ("Nữ", "Bắc", "tự nhiên", False),
}


def _score_preset(
    preset_meta: tuple[str, str, str],
    gender: str | None,
    region: str | None,
    style: str | None,
) -> int:
    """Điểm gần của một preset V3 với giọng V4 (giới tính > vùng > phong cách)."""
    p_gender, p_region, p_style = preset_meta
    score = 0
    if gender and p_gender == gender:
        score += 4
    if region and p_region == region:
        score += 2
    if style and p_style == style:
        score += 1
    return score


def map_v4_voice_to_v3(
    v4_voice: str,
    gender: str | None = None,
    region: str | None = None,
    style: str | None = None,
) -> str:
    """Ánh xạ giọng V4 → preset V3 gần nhất theo (giới tính, vùng, phong cách).

    - Giọng V4 đã biết trong :data:`KNOWN_V4_VOICES` thì dùng đúng giới tính/
      vùng/phong cách đã ghi (người gọi có thể đè bằng tham số).
    - Giọng V4 đã là tên preset V3 (VD "Trúc Ly") thì giữ nguyên tên.
    - Không có preset nào cùng giới tính + vùng (điểm 0) → mặc định "Hải Đăng".
    """
    if v4_voice in V3_PRESETS:
        return v4_voice
    known = KNOWN_V4_VOICES.get(v4_voice)
    if known is not None:
        gender = gender or known[0]
        region = region or known[1]
        style = style or known[2]
    best_name = DEFAULT_V3_VOICE
    best_score = 0
    for name, meta in V3_PRESETS.items():
        score = _score_preset(meta, gender, region, style)
        if score > best_score:
            best_score = score
            best_name = name
    return best_name if best_score > 0 else DEFAULT_V3_VOICE


@dataclass
class FallbackInfo:
    """Ghi rõ lần fallback V4→V3 (lý do + giọng mới) để job/UI/log hiển thị."""

    reason: str  # VD "V4 lỗi 403 hết quota"
    from_engine: str = "v4"
    to_engine: str = "v3"
    from_voice: str = ""
    to_voice: str = ""

    @property
    def message(self) -> str:
        """Câu báo chuẩn, VD "V4 lỗi 403 hết quota → fallback V3, giọng đổi Hạ Vy → Trúc Ly"."""
        voice_part = (
            f", giọng đổi {self.from_voice} → {self.to_voice}"
            if self.from_voice and self.to_voice and self.from_voice != self.to_voice
            else (f", giọng giữ {self.to_voice}" if self.to_voice else "")
        )
        return f"{self.reason} → fallback {self.to_engine.upper()}{voice_part}"


class EngineRouter:
    """Chọn engine theo cài đặt + từng job; fallback V4→V3 có báo lý do."""

    def __init__(
        self,
        v3_engine: EngineBase,
        v4_engine: EngineBase | None = None,
        default_engine: str = "v3",
        fallback_to_v3: bool = True,
        fallback_voice: str = "map",
    ):
        """``fallback_voice``: ``"map"`` (ánh xạ theo bảng) | ``"default"``
        (luôn về "Hải Đăng") | ``"fail"`` (không fallback giọng — lỗi thay vì đổi)."""
        if fallback_voice not in ("map", "default", "fail"):
            raise ValueError(
                f'fallback_voice không hợp lệ: {fallback_voice!r} '
                '(chỉ "map"/"default"/"fail")'
            )
        self.v3_engine = v3_engine
        self.v4_engine = v4_engine
        self.default_engine = default_engine
        self.fallback_to_v3 = fallback_to_v3
        self.fallback_voice = fallback_voice

    # --- Ánh xạ giọng fallback (dùng chung cho /v1/dialogue, /v1/dub, /v1/srt) ---
    def fallback_voice_for(
        self, v4_voice: str, gender: str | None = None, region: str | None = None,
        style: str | None = None,
    ) -> str:
        """Giọng V3 dùng khi fallback từ giọng V4 (theo quy tắc config)."""
        if self.fallback_voice == "fail":
            raise V4Error(
                f"Giọng V4 {v4_voice!r} lỗi và cấu hình fallback_voice='fail' — "
                "không đổi giọng lặng lẽ.",
                code="fallback_disabled",
            )
        if self.fallback_voice == "default":
            return DEFAULT_V3_VOICE
        return map_v4_voice_to_v3(v4_voice, gender, region, style)

    def should_fallback(self, error: Exception, voice_strict: bool) -> bool:
        """Có được fallback V4→V3 không? Khóa giọng → không; tắt fallback → không."""
        if voice_strict:
            return False
        if not self.fallback_to_v3:
            return False
        return isinstance(error, (V4Error, TimeoutError, ConnectionError))

    def describe_error(self, error: Exception) -> str:
        """Câu lý do ngắn cho lỗi V4 (để ghi vào FallbackInfo.message)."""
        if isinstance(error, V4Error):
            if error.code == "unauthorized":
                return "V4 lỗi 401 key sai/thiếu/hết hạn"
            if error.code == "quota_exceeded":
                return "V4 lỗi 403 hết quota"
            if error.code == "rate_limited":
                return "V4 lỗi 429 quá tải"
            if error.code == "timeout_no_retry":
                return "V4 timeout (không retry được)"
            if error.code == "no_api_key":
                return "V4 chưa có key"
            return f"V4 lỗi {error.code}"
        return f"V4 lỗi {type(error).__name__}"

    def resolve_cloud_fallback(
        self, error: Exception, v4_voice: str, voice_strict: bool
    ) -> str:
        """Fallback giọng V3 cho các endpoint cloud ``/v1/dialogue``, ``/v1/dub``,
        ``/v1/srt`` (cùng bảng ánh xạ + ``voice_strict`` như ``synthesize``).

        Trả giọng V3 để gọi lại bằng engine local; ``voice_strict=True`` hoặc
        cấu hình tắt fallback thì ném lại lỗi gốc (không đổi giọng lặng lẽ).
        Idempotency của 3 endpoint này chưa xác nhận (OpenAPI ``parameters: []``)
        nên phía gọi KHÔNG retry request cloud sau timeout — chỉ fallback local.
        """
        if not self.should_fallback(error, voice_strict):
            raise error
        return self.fallback_voice_for(v4_voice)

    # --- Interface chung ---
    def synthesize(
        self,
        text: str,
        voice: str,
        options: SynthesisOptions | None = None,
        engine: str | None = None,
        voice_strict: bool = False,
        job_id: str | None = None,
    ) -> tuple[AudioResult, FallbackInfo | None]:
        """Tổng hợp qua engine chọn (mặc định theo cài đặt).

        Trả ``(AudioResult, FallbackInfo|None)`` — ``FallbackInfo`` khác None
        khi đã fallback V4→V3 (ghi rõ lý do + giọng mới). ``voice_strict=True``
        thì V4 lỗi → ném lỗi, không fallback.
        """
        chosen = (engine or self.default_engine or "v3").lower()
        if chosen == "v4":
            if self.v4_engine is None:
                raise V4Error(
                    "Engine V4 được chọn nhưng chưa cấu hình (thiếu key/engine).",
                    code="no_api_key",
                )
            try:
                result = self.v4_engine.synthesize(text, voice, options)
                return result, None
            except Exception as exc:  # noqa: BLE001 - mọi lỗi V4 đều xét fallback
                if not self.should_fallback(exc, voice_strict):
                    raise
                new_voice = self.fallback_voice_for(voice)
                result = self.v3_engine.synthesize(text, new_voice, options)
                info = FallbackInfo(
                    reason=self.describe_error(exc),
                    from_voice=voice,
                    to_voice=new_voice,
                )
                return result, info
        return self.v3_engine.synthesize(text, voice, options), None
