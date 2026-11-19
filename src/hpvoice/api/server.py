"""HpApiServer — FastAPI (TK2.1, SPEC §4).

- App factory ``create_app(engine=None, ...)``: engine thật/mocking qua
  dependency injection (test dùng FakeEngine, KHÔNG load model).
- Bind 127.0.0.1:8124 mặc định (config server.host/port); cổng bận thì
  fail-fast ở scripts/run_server.py (không tự nhảy cổng — §4).
- Mọi response lỗi dùng JSON ``{"error": {"code", "message"}}`` (SPEC §4);
  lỗi validate pydantic cũng map về 400 (không 422).
- Runner nền (daemon thread): quét job hết TTL, lấy job FIFO, chạy
  ``job.run_fn(state, job)`` dưới khóa tổng hợp (1 job TTS đồng thời,
  TH-19), ghi kết quả ra outputs/ + lưu history.
- Wiring router ĐỘNG: import mọi module ``src/hpvoice/api/routes_*.py``
  (nếu có) và include thuộc tính ``router`` của chúng; module lỗi thì bỏ
  qua + log rõ (để agent TK2-FEATURES thêm routes_dialogue/batch/srt/files
  mà server tự nhận, không cần sửa server.py).
"""
from __future__ import annotations

import importlib
import logging
import pkgutil
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse

from hpvoice.audio.ffmpeg_manager import FFmpegManager
from hpvoice.config import ConfigStore
from hpvoice.jobs.history import HistoryFullError, HistoryStore, PreviewCache
from hpvoice.jobs.queue import JobQueue
from hpvoice.jobs.worker import CancelledError

logger = logging.getLogger("hpvoice.api")

VERSION = "0.1.0"  # đồng bộ với pyproject.toml (v1 đầu tiên)
TITLE = "HP Voice Studio API"

#: keyring (TH-05): key V4 lưu qua keyring, không plaintext trong file.
_KEYRING_SERVICE = "hp-voice-studio"
_KEYRING_USERNAME = "v4_api_key"


#: Thư mục UI tĩnh (TK3.1): <repo>/ui. Chỉ mount khi thư mục tồn tại —
#: test/app vẫn chạy bình thường khi ui/ chưa có (khi đó GET / trả JSON cũ).
UI_DIR = Path(__file__).resolve().parents[3] / "ui"


def _discover_routers(app: FastAPI) -> list[str]:
    """Import mọi module routes_* trong gói hpvoice.api và include router.

    Module lỗi -> bỏ qua + log rõ (không làm chết server). Trả danh sách
    tên module đã include thành công (để /health hoặc log đối chiếu).
    """
    included: list[str] = []
    try:
        import hpvoice.api as api_pkg
    except ImportError as exc:
        logger.warning("Không import được gói hpvoice.api: %s", exc)
        return included
    for mod_info in pkgutil.iter_modules(api_pkg.__path__):
        name = mod_info.name
        if not name.startswith("routes_"):
            continue
        full_name = f"hpvoice.api.{name}"
        try:
            module = importlib.import_module(full_name)
        except Exception as exc:  # noqa: BLE001 - module lỗi thì bỏ qua + log rõ
            logger.warning("Bỏ qua router %s (import lỗi: %s)", full_name, exc)
            continue
        router = getattr(module, "router", None)
        if router is None:
            logger.warning("Bỏ qua %s (không có thuộc tính router)", full_name)
            continue
        app.include_router(router)
        included.append(name)
        logger.info("Đã include router %s", full_name)
    return included


def _runner_loop(app: FastAPI) -> None:
    """Vòng lặp runner nền: quét TTL -> lấy job FIFO -> chạy -> ghi kết quả."""
    state = app.state
    while True:
        try:
            state.queue.sweep_expired()
            job = state.queue.peek_next()
            if job is None:
                time.sleep(0.05)
                continue
            if job.cancel_event.is_set():
                state.queue.mark_cancelled(job.id, "Job đã bị hủy khi đang chờ.")
                continue
            if job.run_fn is None:
                state.queue.mark_error(job.id, "no_run_fn",
                                       "Job không có hàm chạy (lỗi nội bộ).")
                continue
            with state.synthesis_lock:
                # Chiếm được khóa CPU mới mark_running: job chờ vẫn tính là
                # chờ cho tới lúc thực sự chạy (đếm hàng đợi 20 mới đúng).
                current = state.queue.get(job.id)
                if current is None or current.status != "queued":
                    continue  # bị hủy/lỗi trong lúc chờ khóa
                state.queue.mark_running(job.id)
                if job.cancel_event.is_set():
                    state.queue.mark_cancelled(job.id, "Job đã bị hủy khi đang chờ.")
                    continue
                try:
                    result = job.run_fn(state, job)
                except CancelledError as exc:
                    state.queue.mark_cancelled(job.id, str(exc))
                    continue
                except HTTPException as exc:
                    state.queue.mark_error(job.id, str(exc.status_code),
                                           str(exc.detail))
                    continue
                except Exception as exc:  # noqa: BLE001 - ghi lỗi vào job, runner chạy tiếp
                    state.queue.mark_error(job.id, "job_error", str(exc))
                    continue
            _persist_job_result(state, job, result)
        except Exception as exc:  # noqa: BLE001 - runner không được chết
            logger.exception("Lỗi vòng lặp runner (bỏ qua, chạy tiếp): %s", exc)
            time.sleep(0.1)


def _persist_job_result(state, job, result: dict) -> None:
    """Ghi kết quả job ra outputs/ + lưu history; đánh dấu job done/error."""
    try:
        result_bytes = result.get("result_bytes")
        fmt = result.get("result_format", "wav")
        if result_bytes is None and result.get("result_path"):
            result_path = Path(result["result_path"])
            size = result_path.stat().st_size if result_path.is_file() else 0
        elif result_bytes is not None:
            result_path = state.output_dir / f"{job.id}.{fmt}"
            result_path.parent.mkdir(parents=True, exist_ok=True)
            result_path.write_bytes(bytes(result_bytes))
            size = len(result_bytes)
        else:
            state.queue.mark_error(job.id, "no_result",
                                   "Job chạy xong nhưng không trả kết quả.")
            return
        history_id: str | None = None
        history_warning: str | None = None
        try:
            item = state.history.add_from_result(result)
            if item is not None:
                history_id = item["id"]
        except HistoryFullError as exc:
            history_warning = str(exc)
        state.queue.mark_done(
            job.id,
            result_path=str(result_path),
            result_format=fmt,
            result_media_type=result.get("result_media_type"),
            duration_s=result.get("duration_s"),
            size_bytes=size,
            history_id=history_id,
            history_warning=history_warning,
        )
    except Exception as exc:  # noqa: BLE001 - lỗi ghi kết quả thì job error rõ ràng
        state.queue.mark_error(job.id, "persist_error", f"Không ghi được kết quả job: {exc}")


def create_app(engine: Any = None, config: ConfigStore | None = None,
               data_dir: str | Path | None = None,
               queue: JobQueue | None = None,
               history: HistoryStore | None = None,
               preview_cache: PreviewCache | None = None,
               ffmpeg: FFmpegManager | None = None) -> FastAPI:
    """Tạo FastAPI app. ``engine=None`` -> V3Engine lười nạp (không load model
    lúc tạo app); test truyền FakeEngine qua dependency injection."""
    cfg = config or ConfigStore()
    if engine is None:
        from hpvoice.engines import V3Engine

        engine = V3Engine(
            precision=str(cfg.get("engine.v3.precision", "auto")),
            backbone_repo=str(cfg.get("engine.v3.backbone_repo",
                                      "pnnbao-ump/VieNeu-TTS-v3-Turbo")),
            threads=int(cfg.get("engine.v3.threads", 0)),
            max_batch_size=int(cfg.get("engine.v3.max_batch_size", 32)),
            model_dir=str(cfg.get("engine.v3.model_dir", "") or ""),
        )
    base_dir = Path(data_dir) if data_dir else Path(cfg.data_dir)
    history_dir = Path(str(cfg.get("storage.history_dir", "") or "") or (base_dir / "history"))
    output_dir = Path(str(cfg.get("storage.output_dir", "") or "") or (base_dir / "outputs"))
    tmp_dir = base_dir / "tmp"
    preview_dir = base_dir / "preview"
    for folder in (history_dir, output_dir, tmp_dir, preview_dir):
        folder.mkdir(parents=True, exist_ok=True)
    max_history_gb = float(cfg.get("storage.max_history_gb", 5))
    store = history or HistoryStore(history_dir=history_dir, max_history_gb=max_history_gb)
    job_queue = queue or JobQueue(
        max_waiting=int(cfg.get("api.max_queue_jobs", 20)),
        ttl_seconds=3600,
    )
    cache = preview_cache or PreviewCache(cache_dir=preview_dir)
    ffmpeg_manager = ffmpeg or FFmpegManager(data_dir=base_dir)
    dict_file = Path(str(cfg.get("storage.dict_file", "") or "") or (base_dir / "pronunciation-dict.json"))

    # Kho giọng clone (VoiceStore TK1.5) — file HP riêng, không load model
    # khi chưa có file clone (trả None nếu engine test không hỗ trợ).
    voice_store = None
    try:
        from hpvoice.voices.store import VoiceStore

        voice_store = VoiceStore(engine, voices_file=base_dir / "voices.json",
                                 data_dir=base_dir)
    except Exception as exc:  # noqa: BLE001 - không có kho clone thì API vẫn chạy
        logger.warning("Không khởi tạo được VoiceStore (giọng clone tắt): %s", exc)

    app = FastAPI(title=TITLE, version=VERSION)
    state = SimpleNamespace(
        version=VERSION,
        started_at=time.time(),
        engine=engine,
        config=cfg,
        data_dir=base_dir,
        history_dir=history_dir,
        output_dir=output_dir,
        tmp_dir=tmp_dir,
        preview_dir=preview_dir,
        dict_file=dict_file,
        queue=job_queue,
        history=store,
        preview_cache=cache,
        ffmpeg=ffmpeg_manager,
        voice_store=voice_store,
        synthesis_lock=threading.Lock(),
    )

    # --- Key V4 (TH-05): keyring, fallback bộ nhớ phiên khi không có backend ---
    _v4_memory: dict[str, str] = {}

    def v4_configured() -> bool:
        if _v4_memory.get("key"):
            return True
        try:
            import keyring

            return keyring.get_password(_KEYRING_SERVICE, _KEYRING_USERNAME) is not None
        except Exception:
            return False

    def v4_store_key(key: str) -> None:
        try:
            import keyring

            keyring.set_password(_KEYRING_SERVICE, _KEYRING_USERNAME, key)
            _v4_memory.pop("key", None)
        except Exception:
            # Không có backend keyring (VD VM không có Secret Service):
            # chỉ giữ trong bộ nhớ phiên này, không ghi file plaintext.
            _v4_memory["key"] = key
            logger.warning("Keyring không khả dụng — key V4 chỉ lưu trong bộ nhớ phiên này.")

    def v4_clear_key() -> None:
        _v4_memory.pop("key", None)
        try:
            import keyring

            keyring.delete_password(_KEYRING_SERVICE, _KEYRING_USERNAME)
        except Exception:
            pass

    state.v4_configured = v4_configured
    state.v4_store_key = v4_store_key
    state.v4_clear_key = v4_clear_key

    app.state = state

    # --- Envelope lỗi chuẩn SPEC §4 ---
    @app.exception_handler(HTTPException)
    async def _http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": str(exc.status_code), "message": str(exc.detail)}},
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(request: Request, exc: RequestValidationError):
        errors = exc.errors()
        first = errors[0] if errors else {}
        message = f"Dữ liệu gửi lên không hợp lệ: {first.get('msg', exc)}"
        return JSONResponse(status_code=400,
                            content={"error": {"code": "400", "message": message}})

    @app.get("/")
    def root():
        # TK3.1: có UI thì / dẫn về trang chính; chưa có ui/ thì giữ JSON cũ
        # để test/app cũ không vỡ.
        if (UI_DIR / "index.html").is_file():
            return RedirectResponse(url="/ui/index.html", status_code=302)
        return {"name": "HP Voice Studio", "version": VERSION,
                "docs": "/docs", "health": "/health"}

    # Dọn file tạm của job đã chết/crash lần trước (TH-33) ngay khi tạo app.
    try:
        removed = store.cleanup_temp(tmp_dir)
        if removed:
            logger.info("Đã dọn %d file/thư mục tạm cũ lúc khởi động.", removed)
    except Exception as exc:  # noqa: BLE001 - dọn lỗi không chặn khởi động
        logger.warning("Dọn file tạm lúc khởi động lỗi: %s", exc)

    included = _discover_routers(app)
    app.state.included_routers = included

    # TK3.1: phục vụ UI tĩnh ở /ui (chỉ khi thư mục ui/ tồn tại).
    if UI_DIR.is_dir():
        try:
            from fastapi.staticfiles import StaticFiles

            app.mount("/ui", StaticFiles(directory=str(UI_DIR)), name="ui")
        except Exception as exc:  # noqa: BLE001 - không mount được thì API vẫn chạy
            logger.warning("Không mount được UI tĩnh /ui (%s): %s", UI_DIR, exc)

    # Runner nền xử lý hàng đợi (daemon — tắt cùng tiến trình).
    thread = threading.Thread(target=_runner_loop, args=(app,),
                              name="hp-job-runner", daemon=True)
    thread.start()
    return app
