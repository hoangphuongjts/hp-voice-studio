"""HistoryStore bền vững + PreviewCache + dọn file tạm
(TK2.3/TK2.10, SPEC §3.3, TH-16/TH-21/TH-30/TH-33).

HistoryStore:
- Lưu bản đã tạo (audio + SRT + metadata theo §8 HistoryItem) trong
  ``history_dir``: file ``history.json`` (index) + file audio/SRT từng bản.
- Ghi atomic: ghi file tạm + ``os.replace`` (rename), tránh corrupt khi tắt
  đột ngột (TH-21). Trước mỗi lần ghi index, copy index cũ sang
  ``history.json.bak``; file chính hỏng -> đọc bản backup + báo rõ.
- Checkpoint: mỗi ``add()`` ghi đĩa ngay (cả audio lẫn index) — batch xong
  mục nào là mục đó đã bền, không chờ cuối batch.
- Chặn tạo mới khi vượt ``max_history_gb`` (TH-16): ``add()`` ném
  :class:`HistoryFullError` + hướng xoá/xuất bớt; vẫn cho nghe/tải/xoá bản cũ.
- Kiểm tra dung lượng trống trước batch lớn: :meth:`ensure_free_space`.
- Dọn file tạm khi hủy/crash: :meth:`cleanup_temp` quét thư mục tạm lúc
  khởi động, xoá thư mục tạm của job không còn chạy (TH-33).

PreviewCache (TH-30): cache nghe thử giọng trên đĩa, có trần dung lượng
(``max_bytes``) — vượt trần thì dọn file cũ nhất trước (LRU theo mtime),
giữ cache model (HF cache không thuộc phạm vi dọn ở đây).
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

__all__ = [
    "DEFAULT_MAX_HISTORY_GB",
    "DEFAULT_PREVIEW_CACHE_MB",
    "HistoryFullError",
    "HistoryStore",
    "InsufficientSpaceError",
    "PreviewCache",
]

#: Mặc định SPEC §6 storage.max_history_gb.
DEFAULT_MAX_HISTORY_GB = 5
#: Trần preview cache mặc định (TH-30): 200 MB.
DEFAULT_PREVIEW_CACHE_MB = 200
#: Dự trữ tối thiểu khi kiểm tra dung lượng trống (tránh ghi tới sát 0).
FREE_SPACE_RESERVE_BYTES = 10 * 1024 * 1024


class HistoryFullError(RuntimeError):
    """Lịch sử đã vượt max_history_gb — chặn tạo mới (TH-16)."""


class InsufficientSpaceError(RuntimeError):
    """Ổ đĩa không đủ trống cho thao tác sắp làm (TH-21/TH-33)."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _atomic_write_bytes(path: Path, data: bytes) -> Path:
    """Ghi bytes ra file bằng file tạm + rename (atomic, TH-21)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex[:8]}.tmp")
    try:
        tmp.write_bytes(data)
        os.replace(tmp, path)
    except BaseException:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    return path


def _atomic_write_text(path: Path, text: str) -> Path:
    return _atomic_write_bytes(path, text.encode("utf-8"))


class HistoryStore:
    """Kho 'Bản đã tạo': index JSON + file audio/SRT trên đĩa."""

    def __init__(self, history_dir: str | Path, max_history_gb: float = DEFAULT_MAX_HISTORY_GB):
        self.history_dir = Path(history_dir)
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.max_history_gb = float(max_history_gb)
        self.index_path = self.history_dir / "history.json"
        self.backup_path = self.history_dir / "history.json.bak"
        #: True khi file chính hỏng và phải đọc backup (hoặc cả hai đều hỏng).
        self.corrupted = False
        #: Thông báo rõ khi load gặp vấn đề (để API/UI báo cho người dùng).
        self.load_warning: str | None = None
        self._items: list[dict] = []
        self._load()

    # --- Nạp index (kèm backup) ---
    def _load_from(self, path: Path) -> list[dict]:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("File history phải chứa danh sách JSON.")
        return [dict(item) for item in data if isinstance(item, dict)]

    def _load(self) -> None:
        if not self.index_path.is_file():
            self._items = []
            return
        try:
            self._items = self._load_from(self.index_path)
            return
        except Exception as exc:  # noqa: BLE001 - file chính hỏng -> thử backup
            main_error = str(exc)
        if self.backup_path.is_file():
            try:
                self._items = self._load_from(self.backup_path)
                self.corrupted = True
                self.load_warning = (
                    "File lịch sử chính bị hỏng "
                    f"({main_error}) nên đã đọc từ bản backup gần nhất. "
                    "Hãy kiểm tra lại danh sách Bản đã tạo."
                )
                return
            except Exception as backup_exc:  # noqa: BLE001 - cả hai đều hỏng
                self.corrupted = True
                self.load_warning = (
                    "File lịch sử chính và bản backup đều hỏng "
                    f"(chính: {main_error}; backup: {backup_exc}) — "
                    "lịch sử bắt đầu lại từ rỗng, file audio cũ vẫn còn "
                    "trên đĩa và không bị xoá."
                )
                self._items = []
                return
        self.corrupted = True
        self.load_warning = (
            f"File lịch sử chính bị hỏng ({main_error}) và không có bản "
            "backup — lịch sử bắt đầu lại từ rỗng, file audio cũ vẫn còn "
            "trên đĩa và không bị xoá."
        )
        self._items = []

    def _save_index(self) -> None:
        """Ghi index atomic: backup index cũ -> ghi tạm -> rename."""
        if self.index_path.is_file():
            try:
                shutil.copyfile(self.index_path, self.backup_path)
            except OSError:
                pass  # backup lỗi thì vẫn ghi tiếp, không chặn tạo mới
        payload = json.dumps(self._items, ensure_ascii=False, indent=2)
        _atomic_write_text(self.index_path, payload)

    # --- Dung lượng ---
    @property
    def max_history_bytes(self) -> int:
        return int(self.max_history_gb * 1024**3)

    @property
    def total_bytes(self) -> int:
        """Tổng dung lượng các bản trong index (để hiển thị + đối chiếu `du`)."""
        return sum(int(item.get("size_bytes", 0) or 0) for item in self._items)

    def would_exceed(self, new_bytes: int) -> bool:
        """True nếu thêm ``new_bytes`` nữa thì vượt max_history_gb."""
        return self.total_bytes + int(new_bytes) > self.max_history_bytes

    def ensure_free_space(self, required_bytes: int, path: str | Path | None = None) -> None:
        """Kiểm tra dung lượng trống trước batch lớn (TH-21/TH-33).

        Ném :class:`InsufficientSpaceError` khi ổ trống (trừ dự trữ 10 MB)
        nhỏ hơn số byte cần — gọi TRƯỚC khi tổng hợp, không đợi ghi lỗi.
        """
        target = Path(path) if path else self.history_dir
        target.mkdir(parents=True, exist_ok=True)
        free = shutil.disk_usage(str(target)).free
        if free - FREE_SPACE_RESERVE_BYTES < int(required_bytes):
            raise InsufficientSpaceError(
                f"Ổ đĩa chỉ còn trống {free / 1024**2:.0f} MB, cần "
                f"{int(required_bytes) / 1024**2:.0f} MB cho thao tác này "
                "(đã trừ 10 MB dự trữ) — hãy dọn bớt file rồi thử lại."
            )

    # --- CRUD ---
    def add(self, text_preview: str, voice_id: str, engine: str = "v3",
            speed: float = 1.0, format: str = "wav", duration_sec: float = 0.0,
            audio_bytes: bytes | None = None, audio_path: str | Path | None = None,
            srt_text: str | None = None) -> dict:
        """Thêm 1 bản đã tạo (checkpoint: ghi đĩa ngay).

        - ``audio_bytes``: ghi file audio mới (atomic) rồi mới ghi index.
        - ``audio_path``: file audio đã có sẵn (VD job ghi trực tiếp ra đĩa).
        - Vượt max_history_gb -> :class:`HistoryFullError`, KHÔNG tạo bản mới.
        """
        if audio_bytes is not None:
            size = len(audio_bytes)
        elif audio_path is not None:
            size = Path(audio_path).stat().st_size
        else:
            raise ValueError("add() cần audio_bytes hoặc audio_path.")
        if self.would_exceed(size):
            raise HistoryFullError(
                f"Lịch sử đã dùng {self.total_bytes / 1024**2:.1f} MB / "
                f"giới hạn {self.max_history_gb:g} GB — đã chặn tạo bản mới. "
                "Hãy xoá hoặc xuất bớt bản cũ trong tab Bản đã tạo rồi thử lại."
            )
        item_id = uuid.uuid4().hex[:12]
        audio_name = f"{item_id}.{format}"
        if audio_bytes is not None:
            _atomic_write_bytes(self.history_dir / audio_name, audio_bytes)
            stored_audio_path = audio_name
        else:
            src = Path(audio_path)
            dest = self.history_dir / audio_name
            if src.resolve() != dest.resolve():
                shutil.copyfile(src, dest)
            stored_audio_path = audio_name
        srt_name: str | None = None
        if srt_text:
            srt_name = f"{item_id}.srt"
            _atomic_write_text(self.history_dir / srt_name, srt_text)
        item = {
            "id": item_id,
            "created_at": _now_iso(),
            "text_preview": (text_preview or "")[:200],
            "voice_id": voice_id,
            "engine": engine,
            "speed": float(speed),
            "format": format,
            "duration_sec": round(float(duration_sec), 3),
            "size_bytes": int(size),
            "audio_path": stored_audio_path,
            "srt_path": srt_name,
        }
        self._items.insert(0, item)  # mới nhất lên đầu
        self._save_index()
        return dict(item)

    def add_from_result(self, result: dict) -> dict | None:
        """Lưu kết quả job vào history (dùng chung đường sync + job nền).

        ``result`` là dict do ``run_fn`` trả: cần ``history_audio_bytes``
        (hoặc ``result_bytes`` khi format là wav/mp3) + metadata.
        ZIP batch (không có audio đơn) -> None (không lưu history).
        """
        audio = result.get("history_audio_bytes")
        if audio is None and result.get("result_format") in ("wav", "mp3"):
            audio = result.get("result_bytes")
        if audio is None:
            return None
        return self.add(
            text_preview=str(result.get("text_preview", "")),
            voice_id=str(result.get("voice_id", "")),
            engine=str(result.get("engine", "v3")),
            speed=float(result.get("speed", 1.0)),
            format=str(result.get("result_format", "wav")),
            duration_sec=float(result.get("duration_s", 0.0)),
            audio_bytes=bytes(audio),
            srt_text=result.get("history_srt_text"),
        )

    def list_items(self, limit: int = 50, offset: int = 0) -> tuple[list[dict], int]:
        """Danh sách bản đã tạo, mới nhất trước. Trả (items, total)."""
        total = len(self._items)
        return [dict(i) for i in self._items[offset:offset + limit]], total

    def get(self, item_id: str) -> dict | None:
        for item in self._items:
            if item["id"] == item_id:
                return dict(item)
        return None

    def delete(self, item_id: str) -> bool:
        """Xoá 1 bản: khỏi index + xoá file audio/SRT trên đĩa."""
        for index, item in enumerate(self._items):
            if item["id"] != item_id:
                continue
            self._items.pop(index)
            self._save_index()
            for key in ("audio_path", "srt_path"):
                name = item.get(key)
                if name:
                    try:
                        (self.history_dir / name).unlink(missing_ok=True)
                    except OSError:
                        pass
            return True
        return False

    # --- Dọn file tạm (TH-33) ---
    def cleanup_temp(self, tmp_dir: str | Path,
                     running_job_ids: set[str] | frozenset[str] = frozenset()) -> int:
        """Quét thư mục tạm lúc khởi động: xoá thư mục tạm ``<job_id>/`` của
        job không còn chạy (crash/hủy lần trước) + file ``*.tmp`` lẻ.

        Trả số mục đã xoá. Job đang chạy được giữ lại.
        """
        tmp_path = Path(tmp_dir)
        if not tmp_path.is_dir():
            return 0
        removed = 0
        for entry in list(tmp_path.iterdir()):
            if entry.name in running_job_ids:
                continue
            try:
                if entry.is_dir():
                    shutil.rmtree(entry, ignore_errors=True)
                    removed += 1
                elif entry.is_file() and entry.suffix == ".tmp":
                    entry.unlink(missing_ok=True)
                    removed += 1
            except OSError:
                continue
        return removed


class PreviewCache:
    """Cache nghe thử giọng trên đĩa, có trần dung lượng (TH-30).

    Khóa cache = chuỗi bất kỳ (VD ``preview:v3:<voice_id>:<câu mẫu>``);
    file lưu theo SHA-256 của khóa. Vượt trần -> dọn file cũ nhất (mtime)
    cho tới khi vừa trần.
    """

    def __init__(self, cache_dir: str | Path,
                 max_bytes: int = DEFAULT_PREVIEW_CACHE_MB * 1024 * 1024):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_bytes = int(max_bytes)

    def _path_for(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{digest}.wav"

    def get(self, key: str) -> bytes | None:
        """Trả bytes cache (HIT) hoặc None (MISS)."""
        path = self._path_for(key)
        if not path.is_file():
            return None
        try:
            return path.read_bytes()
        except OSError:
            return None

    def put(self, key: str, data: bytes) -> Path:
        """Ghi cache + dọn cũ nhất nếu vượt trần. Trả đường dẫn file."""
        path = self._path_for(key)
        _atomic_write_bytes(path, data)
        self._prune()
        return path

    def usage_bytes(self) -> int:
        total = 0
        for entry in self.cache_dir.iterdir():
            if entry.is_file():
                try:
                    total += entry.stat().st_size
                except OSError:
                    continue
        return total

    def _prune(self) -> None:
        """Dọn file cũ nhất (theo mtime) cho tới khi vừa trần."""
        if self.usage_bytes() <= self.max_bytes:
            return
        files = []
        for entry in self.cache_dir.iterdir():
            if entry.is_file():
                try:
                    files.append((entry.stat().st_mtime, entry))
                except OSError:
                    continue
        files.sort(key=lambda item: item[0])
        for _, entry in files:
            if self.usage_bytes() <= self.max_bytes:
                break
            try:
                entry.unlink(missing_ok=True)
            except OSError:
                continue

    def clear(self) -> int:
        """Xoá toàn bộ cache. Trả số file đã xoá."""
        count = 0
        for entry in list(self.cache_dir.iterdir()):
            if entry.is_file():
                try:
                    entry.unlink(missing_ok=True)
                    count += 1
                except OSError:
                    continue
        return count
