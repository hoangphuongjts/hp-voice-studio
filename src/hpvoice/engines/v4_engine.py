"""V4Engine — client HTTPS Cloud API v4 (TK2.2, SPEC §2.4/§3.3).

Hợp đồng (đã đọc OpenAPI ``https://docs.vieneu.io/openapi.json`` ngày 19/11/2026):
- Base ``https://api.vieneu.io/api/v1``; auth ``Authorization: Bearer <key>``
  (header ``X-API-Key`` cũng được — chỉ dùng Bearer ở đây).
- ``POST /v1/audio/speech`` (đồng bộ, trả audio bytes; ``parameters: []`` —
  KHÔNG có Idempotency-Key → KHÔNG retry sau timeout).
- ``POST /v1/tts`` (async, trả ``jobId``; poll ``GET /v1/tts/{jobId}`` tới
  ``completed`` rồi tải ``audioUrl``). Tham số header ``Idempotency-Key``
  (8–128 ký tự ASCII, UUID lý tưởng, nhớ 24 h theo API key): cùng key + cùng
  body → trả job ĐẦU TIÊN (``Idempotent-Replayed: true``); 409
  ``IDEMPOTENCY_IN_FLIGHT`` → retry CÙNG key sau ``Retry-After``; 422
  ``IDEMPOTENCY_KEY_REUSED`` (key cũ + body khác) → báo lỗi, không retry.
- ``POST /v1/dialogue`` (JSON ``{turns:[{speaker,voiceId,text}], ...}``,
  1–50 lượt), ``POST /v1/dub`` (multipart audio + voiceId, tính phí theo
  thời lượng audio đầu ra), ``POST /v1/srt`` (multipart file .srt + voiceId,
  tính phí theo ký tự cue). **Cả ba đều có ``parameters: []`` trong OpenAPI
  (đã kiểm tra 19/11/2026) — KHÔNG hỗ trợ Idempotency-Key → KHÔNG retry sau
  timeout khi chưa xác nhận** (xem :meth:`V4Engine.create_dialogue`...).
- ``GET /v1/voices?engine=v4`` (catalogue: ``id``, ``name``, ``gender``,
  ``region``, ``engine``, ``kind``), ``GET /v1/balance`` (``remaining``,
  ``spendableTokens``, ``totalRemainingTokens``, ``plan``),
  ``GET /v1/engines`` (``billingMultiplier`` từng engine + ``globalMultiplier``).
- Phí: ``ký tự (tối thiểu 50/request) × engine billingMultiplier ×
  globalMultiplier``; token trừ lúc gửi, hoàn lại nếu job thất bại vĩnh viễn.
- Mã lỗi riêng: 401 = key sai/thiếu/hết hạn; 403 = hết quota/bị khóa/không có
  quyền engine (402 chỉ ở audiobook — KHÔNG dùng 402 ở đây); 429 = rate limit
  + ``Retry-After``; 400 = giọng lạ/khác engine/text quá dài.

BẢO MẬT / CHI PHÍ (Charter §5–§6):
- Key lấy từ store qua keyring (tham số ``api_key`` hoặc callable
  ``key_getter``) — KHÔNG hardcode, KHÔNG đọc file config chứa key, KHÔNG log
  key, KHÔNG bao giờ trả key ra ngoài. Test chỉ dùng key giả ``"test-key-xxx"``
  truyền qua tham số + ``httpx.MockTransport`` — TUYỆT ĐỐI KHÔNG gọi
  ``api.vieneu.io`` thật trong test (sẽ phát sinh phí).
- ``[nghỉ ...]``: V4 xóa mọi tag lạ khỏi text (OpenAPI ``GET /v1/emotion-tags``)
  nên V4Engine tách đoạn bằng :class:`TextPreprocess` rồi gọi V4 từng đoạn
  (đường async + Idempotency-Key riêng từng đoạn) và nối bằng ``AudioPost`` —
  KHÔNG BAO GIỜ gửi chuỗi ``"[nghỉ"`` sang V4. Mỗi đoạn tính phí tối thiểu
  50 ký tự nên UI phải cảnh báo tách ``[nghỉ]`` trên V4 có thể nhân phí.
- ``synthesize()`` dùng đường ASYNC (``/v1/tts`` + Idempotency-Key) làm mặc
  định vì an toàn retry; ``synthesize_sync()`` dùng ``/v1/audio/speech`` cho
  trường hợp cần audio ngay (không retry sau timeout).
"""

from __future__ import annotations

import io
import time
import uuid
from typing import Callable, Generator, Iterable

import httpx
import numpy as np

from ..audio.post import join_chunks, make_silence
from ..audio.text_preprocess import TextPreprocess, ensure_no_pause_tag
from .base import (
    MAX_TEXT_CHARS,
    AudioResult,
    EngineBase,
    SynthesisOptions,
    VoiceInfo,
)

__all__ = [
    "V4Engine",
    "V4Error",
    "estimate_cost_chars",
    "idempotency_key_for",
]

DEFAULT_BASE_URL = "https://api.vieneu.io/api/v1"
MIN_BILLABLE_CHARS = 50  # phí tối thiểu 50 ký tự/request (OpenAPI)
DEFAULT_TIMEOUT_SEC = 60
DEFAULT_POLL_INTERVAL_S = 2.0
DEFAULT_MAX_POLLS = 120  # 120 lần × 2 s ≈ 4 phút chờ job tối đa
MAX_TTS_TEXT_CHARS = 50000  # maxLength của POST /v1/tts (OpenAPI)
MAX_DIALOGUE_TURNS = 50
MAX_DUB_FILE_MB = 10  # /v1/dub: file tối đa 10 MB (OpenAPI)

#: Namespace UUID ổn định để sinh Idempotency-Key theo HP job id (xác định,
#: không ngẫu nhiên — retry cùng job id dùng lại đúng key cũ).
_IDEMPOTENCY_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def idempotency_key_for(job_id: str, segment_index: int = 0) -> str:
    """Idempotency-Key = UUID v5 theo HP job id + chỉ số đoạn.

    36 ký tự, trong khoảng 8–128 ký tự ASCII cho phép. Cùng job id + cùng
    đoạn → cùng key (retry an toàn); đoạn khác → key khác.
    """
    return str(uuid.uuid5(_IDEMPOTENCY_NAMESPACE, f"hp-voice:{job_id}:{segment_index}"))


def estimate_cost_chars(
    chars: int, engine_multiplier: float, global_multiplier: float = 1.0
) -> float:
    """Ước tính phí (token) = max(50, ký tự) × engine multiplier × global.

    Công thức theo OpenAPI ``GET /v1/balance`` + ``GET /v1/engines``.
    """
    billable = max(MIN_BILLABLE_CHARS, int(chars))
    return billable * float(engine_multiplier) * float(global_multiplier)


class V4Error(Exception):
    """Lỗi Cloud API v4 — luôn mang mã riêng, không gộp thành "lỗi V4"."""

    def __init__(
        self,
        message: str,
        status: int | None = None,
        code: str = "v4_error",
        retry_after_s: float | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code
        self.retry_after_s = retry_after_s

    def __str__(self) -> str:  # noqa: D105
        return self.message


def _retry_after(headers: httpx.Headers, default: float = 1.0) -> float:
    """Đọc ``Retry-After`` (giây); thiếu thì dùng mặc định."""
    raw = headers.get("Retry-After") or headers.get("retry-after")
    try:
        return max(0.0, float(raw)) if raw is not None else default
    except (TypeError, ValueError):
        return default


class V4Engine(EngineBase):
    """Client Cloud API v4, cùng interface :class:`EngineBase` với V3Engine."""

    name = "v4"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout_sec: float = DEFAULT_TIMEOUT_SEC,
        transport: httpx.BaseTransport | None = None,
        key_getter: Callable[[], str | None] | None = None,
        poll_interval_s: float = DEFAULT_POLL_INTERVAL_S,
        max_polls: int = DEFAULT_MAX_POLLS,
        sleep_fn: Callable[[float], None] | None = None,
    ):
        """``api_key``: key do người dùng nhập (truyền qua tham số — test dùng
        key giả). ``key_getter``: callable lấy key từ store/keyring khi không
        truyền ``api_key`` trực tiếp. KHÔNG đọc file config chứa key."""
        self._api_key = api_key
        self._key_getter = key_getter
        self.base_url = str(base_url).rstrip("/")
        self.timeout_sec = timeout_sec
        self.poll_interval_s = poll_interval_s
        self.max_polls = max_polls
        self._sleep = sleep_fn or time.sleep
        self._client: httpx.Client | None = None
        self._transport = transport
        self._voices_cache: list[VoiceInfo] | None = None
        self._engines_cache: dict | None = None
        self.last_job_id: str | None = None  # job V4 gần nhất (để UI/log đối chiếu)
        self.last_idempotency_key: str | None = None
        self.last_replayed: bool = False  # True khi server trả Idempotent-Replayed

    # --- Key + client ---
    @property
    def api_key(self) -> str | None:
        """Key hiện tại (từ tham số hoặc key_getter). Không log giá trị này."""
        if self._api_key:
            return self._api_key
        if self._key_getter is not None:
            try:
                return self._key_getter()
            except Exception:
                return None
        return None

    @property
    def is_configured(self) -> bool:
        """True khi đã có key (chưa kiểm tra key có hợp lệ không)."""
        return bool(self.api_key)

    def _headers(self) -> dict[str, str]:
        key = self.api_key
        if not key:
            raise V4Error(
                "Chưa có key V4 — nhập key trong Cài đặt trước khi dùng engine V4.",
                code="no_api_key",
            )
        return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    def _client_or_new(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                timeout=self.timeout_sec, transport=self._transport
            )
        return self._client

    def _url(self, path: str) -> str:
        # Base đã là .../api/v1 nên path chỉ còn phần sau (VD "/audio/speech").
        return f"{self.base_url}{path}"

    def ensure_loaded(self, progress_callback=None) -> None:
        """V4 không nạp model local — chỉ kiểm tra đã có key chưa."""
        if not self.is_configured:
            raise V4Error(
                "Chưa có key V4 — nhập key trong Cài đặt trước khi dùng engine V4.",
                code="no_api_key",
            )

    @property
    def sample_rate(self) -> int:
        return 48000  # V4 native 48 kHz (OpenAPI: v4 48kHz)

    # --- Ánh xạ lỗi HTTP -> V4Error có mã riêng ---
    @staticmethod
    def _raise_for_status(resp: httpx.Response, context: str = "") -> None:
        """Ném V4Error với mã riêng theo status (401/403/429 tách bạch)."""
        if resp.status_code < 400:
            return
        try:
            body = resp.json()
        except Exception:
            body = {}
        server_msg = ""
        if isinstance(body, dict):
            server_msg = str(
                body.get("message") or body.get("error") or body.get("code") or ""
            )
        prefix = f"{context}: " if context else ""
        status = resp.status_code
        if status == 401:
            raise V4Error(
                f"{prefix}Key V4 sai, thiếu hoặc đã bị thu hồi (401) — "
                "kiểm tra lại key trong Cài đặt."
                + (f" Server báo: {server_msg}" if server_msg else ""),
                status=401,
                code="unauthorized",
            )
        if status == 403:
            raise V4Error(
                f"{prefix}Hết quota / grant hết token / gói không gồm engine này "
                f"(403) — nạp thêm token hoặc đổi gói. (402 chỉ dùng cho audiobook.)"
                + (f" Server báo: {server_msg}" if server_msg else ""),
                status=403,
                code="quota_exceeded",
            )
        if status == 429:
            raise V4Error(
                f"{prefix}Quá tải / vượt rate limit (429) — thử lại sau "
                f"{_retry_after(resp.headers):g} giây."
                + (f" Server báo: {server_msg}" if server_msg else ""),
                status=429,
                code="rate_limited",
                retry_after_s=_retry_after(resp.headers),
            )
        if status == 422:
            raise V4Error(
                f"{prefix}Idempotency-Key đã dùng với body khác (422 "
                "IDEMPOTENCY_KEY_REUSED) — không retry, tạo job mới với key mới."
                + (f" Server báo: {server_msg}" if server_msg else ""),
                status=422,
                code="idempotency_reused",
            )
        if status == 409:
            raise V4Error(
                f"{prefix}Job với Idempotency-Key này đang chạy (409 "
                "IDEMPOTENCY_IN_FLIGHT) — retry CÙNG key sau "
                f"{_retry_after(resp.headers):g} giây.",
                status=409,
                code="idempotency_in_flight",
                retry_after_s=_retry_after(resp.headers),
            )
        if status == 400:
            raise V4Error(
                f"{prefix}Request sai (400) — giọng lạ/khác engine hoặc text quá dài."
                + (f" Server báo: {server_msg}" if server_msg else ""),
                status=400,
                code="bad_request",
            )
        raise V4Error(
            f"{prefix}Cloud V4 lỗi server ({status})."
            + (f" Server báo: {server_msg}" if server_msg else ""),
            status=status,
            code="server_error",
        )

    # --- Giải mã WAV bytes -> np.ndarray ---
    @staticmethod
    def _decode_wav(data: bytes, voice: str) -> AudioResult:
        """Giải mã WAV bytes (PCM 16-bit 48 kHz) thành AudioResult."""
        import soundfile as sf

        try:
            samples, sr = sf.read(io.BytesIO(data), dtype="float32")
        except Exception as exc:  # noqa: BLE001
            raise V4Error(f"Không giải mã được audio WAV trả về từ V4: {exc}") from exc
        return AudioResult(
            samples=np.asarray(samples, dtype=np.float32).reshape(-1),
            sample_rate=int(sr),
            engine="v4",
            voice=voice,
        )

    def _download_audio_url(self, audio_url: str, voice: str) -> AudioResult:
        """Tải audio từ presigned ``audioUrl`` (S3, hạn 24 h).

        Dùng cùng transport mock trong test (URL giả được MockTransport chặn);
        với URL thật thì request đi thẳng tới S3, KHÔNG kèm header auth V4.
        """
        client = self._client_or_new()
        try:
            resp = client.get(audio_url)
        except httpx.TimeoutException as exc:
            raise V4Error(
                f"Tải audio V4 timeout (URL: {audio_url[:60]}...) — thử tải lại, "
                "audio đã tạo xong trên server nên không tính phí thêm.",
                code="timeout",
            ) from exc
        except httpx.HTTPError as exc:
            raise V4Error(f"Không tải được audio V4: {exc}", code="network_error") from exc
        if resp.status_code >= 400:
            raise V4Error(
                f"Tải audio V4 thất bại (HTTP {resp.status_code}).", code="download_error"
            )
        return self._decode_wav(resp.content, voice)

    # --- Đường async /v1/tts (có Idempotency-Key) ---
    def submit_tts_job(
        self,
        text: str,
        voice: str,
        job_id: str | None = None,
        segment_index: int = 0,
        speed: float = 1.0,
    ) -> dict:
        """Gửi ``POST /v1/tts`` với Idempotency-Key = UUID theo HP job id.

        Trả dict submit response (``jobId``, ``status``, ``audioUrl?``).
        409 → chờ ``Retry-After`` rồi retry CÙNG key (tối đa 3 lần);
        422 → báo lỗi, không retry; 401/403/429 → mã riêng (không retry 4xx).
        5xx/timeout TRÊN ĐƯỜNG ASYNC này được retry 1 lần cùng key (SPEC §6
        ``max_retries: 1``) vì Idempotency-Key bảo vệ khỏi tính phí 2 lần.
        """
        ensure_no_pause_tag(text)  # hàng rào cuối: không gửi "[nghỉ" sang V4
        job_id = job_id or uuid.uuid4().hex
        key = idempotency_key_for(job_id, segment_index)
        self.last_idempotency_key = key
        body = {
            "text": text,
            "voiceId": voice,
            "engine": "v4",
            "speed": speed,
            "aiRefine": False,
            "applyPronunciation": True,
        }
        headers = dict(self._headers())
        headers["Idempotency-Key"] = key
        client = self._client_or_new()
        attempts_409 = 0
        attempts_5xx = 0
        while True:
            try:
                resp = client.post(self._url("/tts"), json=body, headers=headers)
            except httpx.TimeoutException as exc:
                # Timeout TRÊN ĐƯỜNG ASYNC có Idempotency-Key: retry cùng key
                # 1 lần (job có thể đã được tạo — key cũ trả đúng job đầu).
                if attempts_5xx == 0:
                    attempts_5xx += 1
                    continue
                raise V4Error(
                    "Gửi job V4 timeout sau 1 lần thử lại cùng Idempotency-Key — "
                    "job có thể đã được tạo; kiểm tra lại bằng job id trước khi gửi mới.",
                    code="timeout",
                ) from exc
            except httpx.HTTPError as exc:
                raise V4Error(f"Không kết nối được Cloud V4: {exc}", code="network_error") from exc
            if resp.status_code == 409:
                attempts_409 += 1
                if attempts_409 > 3:
                    raise V4Error(
                        "Job V4 vẫn đang chạy sau 3 lần chờ Retry-After (409) — "
                        "thử lại sau, dùng CÙNG Idempotency-Key.",
                        status=409,
                        code="idempotency_in_flight",
                    )
                self._sleep(_retry_after(resp.headers, default=1.0))
                continue  # retry CÙNG key, CÙNG body
            if resp.status_code >= 500 and attempts_5xx == 0:
                attempts_5xx += 1
                self._sleep(1.0)
                continue  # retry 1 lần cùng key (đường async có idempotency)
            self._raise_for_status(resp, "POST /v1/tts")
            self.last_replayed = resp.headers.get("Idempotent-Replayed") == "true"
            data = resp.json()
            self.last_job_id = str(data.get("jobId") or "")
            return data

    def poll_tts_job(self, job_id: str, voice: str) -> AudioResult:
        """Poll ``GET /v1/tts/{jobId}`` tới ``completed`` rồi tải ``audioUrl``."""
        client = self._client_or_new()
        for _ in range(self.max_polls):
            try:
                resp = client.get(
                    self._url(f"/tts/{job_id}"), headers=self._headers()
                )
            except httpx.TimeoutException as exc:
                raise V4Error(
                    f"Poll job V4 {job_id} timeout — job vẫn chạy trên server, "
                    "poll lại sau (không tính phí thêm).",
                    code="timeout",
                ) from exc
            except httpx.HTTPError as exc:
                raise V4Error(f"Không kết nối được Cloud V4 khi poll job: {exc}", code="network_error") from exc
            self._raise_for_status(resp, f"GET /v1/tts/{job_id}")
            data = resp.json()
            status = str(data.get("status") or "")
            if status == "completed":
                audio_url = data.get("audioUrl")
                if not audio_url:
                    raise V4Error(
                        f"Job V4 {job_id} báo completed nhưng không có audioUrl.",
                        code="server_error",
                    )
                return self._download_audio_url(str(audio_url), voice)
            if status == "failed":
                raise V4Error(
                    f"Job V4 {job_id} thất bại: {data.get('error') or 'không rõ lý do'} "
                    "(token sẽ được hoàn lại theo OpenAPI).",
                    code="job_failed",
                )
            self._sleep(self.poll_interval_s)
        raise V4Error(
            f"Job V4 {job_id} chưa xong sau {self.max_polls} lần poll — "
            "dừng chờ, job vẫn chạy trên server (poll lại bằng job id, không gửi mới).",
            code="poll_timeout",
        )

    def _synthesize_one_segment(
        self, text: str, voice: str, job_id: str, segment_index: int, speed: float = 1.0
    ) -> AudioResult:
        """Một đoạn text (đã tách [nghỉ]) qua đường async /v1/tts."""
        data = self.submit_tts_job(text, voice, job_id, segment_index, speed)
        if data.get("status") == "completed" and data.get("audioUrl"):
            return self._download_audio_url(str(data["audioUrl"]), voice)
        remote_job = str(data.get("jobId") or "")
        if not remote_job:
            raise V4Error("POST /v1/tts không trả jobId.", code="server_error")
        return self.poll_tts_job(remote_job, voice)

    # --- Interface EngineBase ---
    def synthesize(
        self, text: str, voice: str, options: SynthesisOptions | None = None
    ) -> AudioResult:
        """Tổng hợp qua đường async /v1/tts (mặc định — an toàn retry).

        Tách ``[nghỉ]`` thành đoạn (mỗi đoạn 1 job async + Idempotency-Key
        riêng), nối bằng ``AudioPost.join_chunks`` + silence. Mỗi đoạn tính
        phí tối thiểu 50 ký tự — xem :meth:`estimate_cost`.
        """
        if text is None or not str(text).strip():
            raise ValueError("Text rỗng — không có gì để tạo giọng.")
        if len(str(text)) > MAX_TEXT_CHARS:
            raise ValueError(
                f"Text dài {len(text)} ký tự, vượt giới hạn {MAX_TEXT_CHARS} ký tự/request."
            )
        self.ensure_loaded()
        job_id = uuid.uuid4().hex
        split = TextPreprocess().split(str(text))
        if not split.segments:
            raise ValueError("Text rỗng sau khi tách thẻ [nghỉ] — không có gì để tạo giọng.")
        parts: list[np.ndarray] = []
        pauses: list[float] = []
        sr = self.sample_rate
        if split.leading_pause_s > 0:
            parts.append(make_silence(split.leading_pause_s, sr))
            pauses.append(0.0)
        for i, seg in enumerate(split.segments):
            result = self._synthesize_one_segment(
                seg.text, voice, job_id, i
            )
            sr = result.sample_rate
            parts.append(np.asarray(result.samples, dtype=np.float32))
            pauses.append(seg.pause_after_s)
        # pauses[i] là khoảng lặng SAU parts[i]; join_chunks nhận pauses giữa
        # các chunk — phần tử cuối (sau chunk cuối) bị bỏ, đúng ngữ nghĩa.
        joined = join_chunks(parts, sr, pauses=pauses)
        return AudioResult(samples=joined, sample_rate=sr, engine="v4", voice=voice)

    def synthesize_sync(
        self, text: str, voice: str, options: SynthesisOptions | None = None
    ) -> AudioResult:
        """Tổng hợp qua ``POST /v1/audio/speech`` (đồng bộ, trả audio ngay).

        KHÔNG retry sau timeout (endpoint không hỗ trợ Idempotency-Key —
        retry có thể tính phí 2 lần). Chỉ retry khi request CHƯA gửi đi được
        (lỗi kết nối trước khi gửi) — httpx phân biệt bằng
        ``TimeoutException`` xảy ra sau khi đã gửi nên ở đây không retry
        timeout dưới mọi hình thức; lỗi kết nối (không tới được server) được
        thử lại 1 lần vì chắc chắn server chưa nhận request.
        """
        if text is None or not str(text).strip():
            raise ValueError("Text rỗng — không có gì để tạo giọng.")
        ensure_no_pause_tag(str(text))  # [nghỉ] gửi thẳng sẽ bị V4 xóa lặng lẽ
        self.ensure_loaded()
        body = {
            "input": str(text),
            "model": "v4",
            "voice": voice,
            "response_format": "wav",
        }
        client = self._client_or_new()
        try:
            resp = client.post(
                self._url("/audio/speech"), json=body, headers=self._headers()
            )
        except httpx.TimeoutException as exc:
            # Timeout sau khi gửi: KHÔNG retry (không có idempotency).
            raise V4Error(
                "POST /v1/audio/speech timeout — KHÔNG tự retry vì endpoint "
                "không hỗ trợ Idempotency-Key (retry có thể tính phí 2 lần). "
                "Dùng đường async /v1/tts thay thế.",
                code="timeout_no_retry",
            ) from exc
        except httpx.ConnectError as exc:
            # Chưa kết nối được (chưa gửi request đi) → thử lại 1 lần.
            try:
                resp = client.post(
                    self._url("/audio/speech"), json=body, headers=self._headers()
                )
            except httpx.HTTPError as exc2:
                raise V4Error(
                    f"Không kết nối được Cloud V4: {exc2}", code="network_error"
                ) from exc2
        except httpx.HTTPError as exc:
            raise V4Error(f"Không kết nối được Cloud V4: {exc}", code="network_error") from exc
        self._raise_for_status(resp, "POST /v1/audio/speech")
        return self._decode_wav(resp.content, voice)

    def synthesize_stream(
        self, text: str, voice: str, options: SynthesisOptions | None = None
    ) -> Generator[AudioResult, None, None]:
        """Stream V4: hiện tại tổng hợp async rồi yield 1 chunk duy nhất.

        (``POST /v1/tts/stream`` trả frame WAV độ dài-prefix — chưa triển khai
        ở v1; yield 1 chunk vẫn đúng interface EngineBase.)
        """
        yield self.synthesize(text, voice, options)

    def synthesize_batch(
        self, texts: Iterable[str], voice: str, options: SynthesisOptions | None = None
    ) -> list[AudioResult]:
        return [self.synthesize(t, voice, options) for t in texts]

    def list_preset_voices(self) -> list[VoiceInfo]:
        """Catalogue V4 qua ``GET /v1/voices?engine=v4`` (cache trong phiên)."""
        if self._voices_cache is not None:
            return list(self._voices_cache)
        self.ensure_loaded()
        client = self._client_or_new()
        try:
            resp = client.get(
                self._url("/voices"), params={"engine": "v4"}, headers=self._headers()
            )
        except httpx.HTTPError as exc:
            raise V4Error(f"Không tải được catalogue giọng V4: {exc}", code="network_error") from exc
        self._raise_for_status(resp, "GET /v1/voices")
        data = resp.json()
        if isinstance(data, dict) and data.get("error"):
            raise V4Error(
                "Catalogue giọng V4 không đọc được (server trả error) — thử lại sau.",
                code="server_error",
            )
        voices: list[VoiceInfo] = []
        for item in (data.get("voices") or []):
            voices.append(
                VoiceInfo(
                    id=str(item.get("id") or ""),
                    label=str(item.get("name") or item.get("id") or ""),
                    gender=str(item.get("gender") or ""),
                    style=str(item.get("description") or ""),
                    is_clone=(item.get("kind") == "cloned"),
                )
            )
        self._voices_cache = voices
        return list(voices)

    def resolve_voice(self, name: str | None) -> str | None:
        """Chuẩn hóa tên giọng V4: khớp ``id`` hoặc tên hiển thị trong catalogue."""
        if name is None:
            return None
        try:
            voices = self.list_preset_voices()
        except V4Error:
            return None
        for v in voices:
            if v.id == name or v.label == name:
                return v.id
        return None

    # --- Số dư + hệ số phí (màn hình Cài đặt) ---
    def get_balance(self) -> dict:
        """``GET /v1/balance`` → ``{remaining, spendableTokens,
        totalRemainingTokens, plan, ...}`` (mock test)."""
        self.ensure_loaded()
        client = self._client_or_new()
        try:
            resp = client.get(self._url("/balance"), headers=self._headers())
        except httpx.HTTPError as exc:
            raise V4Error(f"Không tải được số dư V4: {exc}", code="network_error") from exc
        self._raise_for_status(resp, "GET /v1/balance")
        return resp.json()

    def get_engines(self) -> dict:
        """``GET /v1/engines`` → ``{globalMultiplier, engines:[{key,
        billingMultiplier, isDefault, ...}]}`` (cache trong phiên)."""
        if self._engines_cache is not None:
            return self._engines_cache
        client = self._client_or_new()
        try:
            resp = client.get(self._url("/engines"), headers=self._headers())
        except httpx.HTTPError as exc:
            raise V4Error(f"Không tải được bảng engine V4: {exc}", code="network_error") from exc
        self._raise_for_status(resp, "GET /v1/engines")
        self._engines_cache = resp.json()
        return self._engines_cache

    def engine_multiplier(self, engine: str = "v4") -> tuple[float, float]:
        """``(billingMultiplier của engine, globalMultiplier)`` từ /v1/engines."""
        data = self.get_engines()
        global_mult = float(data.get("globalMultiplier", 1.0))
        for item in data.get("engines") or []:
            if item.get("key") == engine:
                return float(item.get("billingMultiplier", 1.0)), global_mult
        raise V4Error(f"Engine {engine!r} không có trong GET /v1/engines.", code="server_error")

    def estimate_cost(self, text: str, engine: str = "v4") -> float:
        """Ước tính phí (token) cho một text trên engine V4.

        Dùng multiplier thật từ ``GET /v1/engines`` (đã kiểm chứng bằng mock;
        số thật chờ key thật). Xem ``docs/v4-billing.md``.
        """
        eng_mult, global_mult = self.engine_multiplier(engine)
        return estimate_cost_chars(len(text), eng_mult, global_mult)

    # --- Hội thoại / lồng tiếng / SRT trên cloud (KHÔNG idempotency) ---
    def create_dialogue(
        self, turns: list[dict], pause_between_turns_ms: int = 500
    ) -> AudioResult:
        """``POST /v1/dialogue`` — 1–50 lượt, trả WAV ghép sẵn qua ``audioUrl``.

        LƯU Ý IDEMPOTENCY (đã đọc OpenAPI 19/11/2026): endpoint này có
        ``parameters: []`` — KHÔNG hỗ trợ header ``Idempotency-Key``. Vì vậy
        KHÔNG retry sau timeout (không biết server đã tạo job chưa; retry có
        thể tính phí 2 lần). Timeout → ném ``V4Error(code="timeout_no_retry")``
        để tầng trên quyết định (fallback local qua EngineRouter hoặc báo user).
        Mỗi lượt: ``{speaker, voiceId, text}`` (text tối đa 5000 ký tự/lượt).
        """
        if not turns:
            raise ValueError("Hội thoại rỗng — cần ít nhất 1 lượt.")
        if len(turns) > MAX_DIALOGUE_TURNS:
            raise ValueError(
                f"Hội thoại tối đa {MAX_DIALOGUE_TURNS} lượt, nhận {len(turns)}."
            )
        self.ensure_loaded()
        body = {
            "turns": [
                {
                    "speaker": str(t.get("speaker") or ""),
                    "voiceId": str(t.get("voiceId") or t.get("voice") or ""),
                    "text": str(t.get("text") or ""),
                }
                for t in turns
            ],
            "pauseBetweenTurnsMs": int(pause_between_turns_ms),
            "engine": "v4",
            "aiRefine": False,
        }
        client = self._client_or_new()
        try:
            resp = client.post(
                self._url("/dialogue"), json=body, headers=self._headers()
            )
        except httpx.TimeoutException as exc:
            raise V4Error(
                "POST /v1/dialogue timeout — KHÔNG tự retry vì endpoint không hỗ trợ "
                "Idempotency-Key (OpenAPI parameters: []). Dùng fallback local hoặc gửi lại tay.",
                code="timeout_no_retry",
            ) from exc
        except httpx.HTTPError as exc:
            raise V4Error(f"Không kết nối được Cloud V4: {exc}", code="network_error") from exc
        self._raise_for_status(resp, "POST /v1/dialogue")
        data = resp.json()
        audio_url = data.get("audioUrl")
        if not audio_url:
            raise V4Error("POST /v1/dialogue không trả audioUrl.", code="server_error")
        return self._download_audio_url(str(audio_url), voice="")

    def create_dub(self, audio_bytes: bytes, voice: str, filename: str = "audio.wav") -> AudioResult:
        """``POST /v1/dub`` — multipart audio tiếng Việt + voiceId, trả WAV lồng lại.

        LƯU Ý: ``parameters: []`` trong OpenAPI — KHÔNG có Idempotency-Key →
        KHÔNG retry sau timeout (như create_dialogue). File tối đa 10 MB;
        tính phí theo THỜI LƯỢNG audio đầu ra (không phải ký tự).
        """
        if not audio_bytes:
            raise ValueError("File audio rỗng — không có gì để lồng tiếng lại.")
        if len(audio_bytes) > MAX_DUB_FILE_MB * 1024 * 1024:
            raise ValueError(
                f"File audio lồng tiếng tối đa {MAX_DUB_FILE_MB} MB, "
                f"nhận {len(audio_bytes) / 1024 / 1024:.1f} MB."
            )
        self.ensure_loaded()
        client = self._client_or_new()
        headers = {"Authorization": f"Bearer {self.api_key}"}
        files = {"audio": (filename, audio_bytes, "audio/wav")}
        data = {"voiceId": voice, "engine": "v4"}
        try:
            resp = client.post(self._url("/dub"), files=files, data=data, headers=headers)
        except httpx.TimeoutException as exc:
            raise V4Error(
                "POST /v1/dub timeout — KHÔNG tự retry vì endpoint không hỗ trợ "
                "Idempotency-Key (OpenAPI parameters: []).",
                code="timeout_no_retry",
            ) from exc
        except httpx.HTTPError as exc:
            raise V4Error(f"Không kết nối được Cloud V4: {exc}", code="network_error") from exc
        self._raise_for_status(resp, "POST /v1/dub")
        payload = resp.json()
        audio_url = payload.get("audioUrl")
        if not audio_url:
            raise V4Error("POST /v1/dub không trả audioUrl.", code="server_error")
        return self._download_audio_url(str(audio_url), voice)

    def create_srt(self, srt_bytes: bytes, voice: str, filename: str = "sub.srt") -> AudioResult:
        """``POST /v1/srt`` — multipart file .srt + voiceId, trả WAV căn theo mốc.

        LƯU Ý: ``parameters: []`` trong OpenAPI — KHÔNG có Idempotency-Key →
        KHÔNG retry sau timeout (như create_dialogue). Tính phí theo tổng ký
        tự cue (tối thiểu 50).
        """
        if not srt_bytes:
            raise ValueError("File .srt rỗng.")
        self.ensure_loaded()
        client = self._client_or_new()
        headers = {"Authorization": f"Bearer {self.api_key}"}
        files = {"file": (filename, srt_bytes, "text/plain")}
        data = {"voiceId": voice, "engine": "v4"}
        try:
            resp = client.post(self._url("/srt"), files=files, data=data, headers=headers)
        except httpx.TimeoutException as exc:
            raise V4Error(
                "POST /v1/srt timeout — KHÔNG tự retry vì endpoint không hỗ trợ "
                "Idempotency-Key (OpenAPI parameters: []).",
                code="timeout_no_retry",
            ) from exc
        except httpx.HTTPError as exc:
            raise V4Error(f"Không kết nối được Cloud V4: {exc}", code="network_error") from exc
        self._raise_for_status(resp, "POST /v1/srt")
        payload = resp.json()
        audio_url = payload.get("audioUrl")
        if not audio_url:
            raise V4Error("POST /v1/srt không trả audioUrl.", code="server_error")
        return self._download_audio_url(str(audio_url), voice)

    def close(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None
