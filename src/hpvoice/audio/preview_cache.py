"""PreviewCache nghe thử giọng V3/V4 (TK3.1, SPEC §3.3 Y7).

- V3: mẫu thu sẵn — tạo lần đầu rồi cache trên đĩa, lần 2 phát file cache,
  không tổng hợp lại mỗi lần mở tab.
- V4: cache theo khóa ``(voice_id + câu mẫu)`` — nghe lần 2 cùng giọng +
  cùng câu mẫu thì phát file cache, **không gọi lại API**.
- Ước tính phí preview V4 = ``max(50, len(câu mẫu)) × billingMultiplier ×
  globalMultiplier`` (TH-05, docs/v4-billing.md) — câu mẫu ≤ 60 ký tự vẫn
  tốn tối thiểu 50 ký tự.
- Trần cache mặc định 200 MB, vượt trần dọn file cũ nhất (theo mtime).

Module này kế thừa :class:`hpvoice.jobs.history.PreviewCache` (lớp đã có từ
TK2.3, server + endpoint ``GET /voices/{id}/preview`` đang dùng) để chỉ có
MỘT logic trần/dọn/ghi atomic, không viết trùng. Lớp ở đây chỉ thêm khóa
V3/V4 theo Y7, ước tính phí và hàm ``get_or_create``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from hpvoice.jobs.history import DEFAULT_PREVIEW_CACHE_MB
from hpvoice.jobs.history import PreviewCache as _BasePreviewCache

__all__ = [
    "DEFAULT_PREVIEW_CACHE_MB",
    "MAX_PREVIEW_CACHE_BYTES",
    "MIN_BILLABLE_CHARS",
    "PREVIEW_SAMPLE_MAX_CHARS",
    "PreviewCache",
    "billable_chars",
    "estimate_preview_cost",
    "preview_key",
]

#: Phí tối thiểu 50 ký tự/request (OpenAPI VieNeu, TH-05).
MIN_BILLABLE_CHARS = 50
#: Câu mẫu nghe thử mặc định ≤ 60 ký tự (config ``audio.preview_sample``).
PREVIEW_SAMPLE_MAX_CHARS = 60
#: Trần cache nghe thử: 200 MB (TH-30).
MAX_PREVIEW_CACHE_BYTES = DEFAULT_PREVIEW_CACHE_MB * 1024 * 1024
#: Hệ số billingMultiplier ví dụ trong OpenAPI ``GET /v1/engines`` (v4 = 3.4).
#: Chỉ là ví dụ minh họa — số thật lấy từ API khi có key, chờ kiểm chứng thật.
EXAMPLE_V4_MULTIPLIER = 3.4


def preview_key(engine: str, voice_id: str, sample: str) -> str:
    """Khóa cache Y7: ``preview:<engine>:<voice_id>:<câu mẫu>``.

    V3 và V4 khác khóa (không lẫn mẫu V3 miễn phí với mẫu V4 tính phí);
    cùng engine + giọng + câu mẫu -> cùng khóa -> HIT lần 2.
    """
    engine_name = str(engine or "").strip().lower()
    if engine_name not in ("v3", "v4"):
        raise ValueError(f"Engine nghe thử chỉ nhận v3/v4, nhận {engine!r}.")
    voice = str(voice_id or "").strip()
    if not voice:
        raise ValueError("Nghe thử cần chọn giọng (voice_id rỗng).")
    text = str(sample or "")
    if not text.strip():
        raise ValueError("Câu mẫu nghe thử rỗng — không có gì để nghe thử.")
    return f"preview:{engine_name}:{voice}:{text}"


def billable_chars(sample: str) -> int:
    """Số ký tự tính phí của 1 lần nghe thử V4: ``max(50, len(câu mẫu))``."""
    return max(MIN_BILLABLE_CHARS, len(str(sample or "")))


def estimate_preview_cost(sample: str, engine_multiplier: float = EXAMPLE_V4_MULTIPLIER,
                          global_multiplier: float = 1.0) -> float:
    """Ước tính phí (token) 1 lần nghe thử V4 chưa cache.

    Công thức = :func:`billable_chars` × billingMultiplier × globalMultiplier,
    giống :func:`hpvoice.engines.v4_engine.estimate_cost_chars` (1 công thức
    duy nhất — test assert hai hàm cho cùng số). ``engine_multiplier`` mặc
    định 3.4 là ví dụ trong OpenAPI, không phải số thật.
    """
    return billable_chars(sample) * float(engine_multiplier) * float(global_multiplier)


class PreviewCache(_BasePreviewCache):
    """Cache nghe thử trên đĩa theo khóa Y7 (kế thừa trần 200 MB + dọn cũ nhất).

    Lớp gốc ở ``hpvoice.jobs.history`` đã có ``get/put/usage_bytes/_prune/
    clear``; lớp này chỉ thêm khóa theo engine/giọng/câu mẫu và ước tính phí.
    """

    def preview_path(self, engine: str, voice_id: str, sample: str) -> Path:
        """Đường dẫn file cache của 1 lần nghe thử (chưa chắc đã tồn tại)."""
        return self._path_for(preview_key(engine, voice_id, sample))

    def has_preview(self, engine: str, voice_id: str, sample: str) -> bool:
        """Đã có mẫu cache cho giọng + câu mẫu này chưa (HIT/MISS)."""
        return self.get_preview(engine, voice_id, sample) is not None

    def get_preview(self, engine: str, voice_id: str, sample: str) -> bytes | None:
        """Trả bytes mẫu cache (HIT) hoặc None (MISS — cần tổng hợp/gọi API)."""
        return self.get(preview_key(engine, voice_id, sample))

    def put_preview(self, engine: str, voice_id: str, sample: str, data: bytes) -> Path:
        """Ghi mẫu nghe thử vào cache (ghi atomic + dọn cũ nhất nếu vượt trần)."""
        return self.put(preview_key(engine, voice_id, sample), data)

    def get_or_create(self, engine: str, voice_id: str, sample: str,
                      synthesize_fn: Callable[[str, str], bytes]) -> tuple[bytes, bool]:
        """Trả ``(audio_bytes, from_cache)`` cho 1 lần nghe thử.

        HIT -> trả file cache, **không gọi** ``synthesize_fn`` (V3 không tổng
        hợp lại, V4 không gọi lại API). MISS -> gọi ``synthesize_fn(câu mẫu,
        voice_id)`` 1 lần, ghi cache rồi trả. Dữ liệu rỗng -> lỗi rõ ràng,
        không ghi cache rỗng.
        """
        cached = self.get_preview(engine, voice_id, sample)
        if cached is not None:
            return cached, True
        data = synthesize_fn(str(sample), str(voice_id))
        if not data:
            raise ValueError(
                f"Nghe thử giọng {voice_id!r} không tạo được audio "
                "(engine trả về rỗng) — thử lại hoặc chọn giọng khác."
            )
        self.put_preview(engine, voice_id, sample, bytes(data))
        return bytes(data), False

    @staticmethod
    def estimate_preview_cost(sample: str,
                              engine_multiplier: float = EXAMPLE_V4_MULTIPLIER,
                              global_multiplier: float = 1.0) -> float:
        """Ước tính phí (token) 1 lần nghe thử V4 chưa cache (xem hàm cùng tên)."""
        return estimate_preview_cost(sample, engine_multiplier, global_multiplier)

    def usage_mb(self) -> float:
        """Dung lượng cache đã dùng (MB) — hiển thị ở Cài đặt."""
        return self.usage_bytes() / 1024 / 1024
