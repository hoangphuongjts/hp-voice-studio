"""BatchRunner — tạo hàng loạt (TK2.6, SPEC §3.3, T3.5/TH-16/TH-33).

- Đọc file danh sách (.txt mốc ``[P1]``… / .json / .srt) hoặc nhận list mục trực tiếp.
- Chạy tuần tự; mỗi mục 1 file WAV ghi ra đĩa NGAY sau khi xong (không giữ
  toàn bộ batch trong RAM); manifest JSON ghi lại sau mỗi mục (checkpoint —
  tắt đột ngột vẫn biết mục nào xong); xuất ZIP; mục lỗi thử lại riêng.
- Đo peak RAM (``resource.ru_maxrss``) ở T3.5 với 100 và 500 mục; giới hạn
  500 mục/lần là số tạm chờ đo RAM (SPEC §4) — chốt lại theo số đo thật
  (xem :attr:`BatchRunner.measured_peak_rss_mb` + test đo RAM).
- Dọn file tạm khi hủy/crash (TH-33): file tạm theo từng job (đuôi ``.tmp``
  trong thư mục batch) + :func:`cleanup_temp_files` quét lúc khởi động.
"""

from __future__ import annotations

import json
import re
import resource
import shutil
import threading
import time
import uuid
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from ..audio.post import write_wav
from ..audio.srt_dubber import parse_srt_text, parse_vtt_text
from ..engines.base import MAX_TEXT_CHARS

__all__ = [
    "BatchItem",
    "BatchResult",
    "BatchRunner",
    "MAX_BATCH_ITEMS",
    "cleanup_temp_files",
    "parse_batch_file",
    "parse_batch_json",
    "parse_batch_txt",
]

#: Số mục tối đa/lần — SỐ TẠM chờ đo RAM ở TK2.6 (SPEC §4); chốt lại theo số đo.
MAX_BATCH_ITEMS = 500
TEMP_PREFIX = "hp-voice-tmp-"

_MARKER_RE = re.compile(r"^\s*\[(P\d+)\]\s*(.*)$")


@dataclass
class BatchItem:
    """Một mục batch: id + text + giọng (mặc định giọng chung của batch)."""

    id: str
    text: str
    voice: str = ""


@dataclass
class BatchItemResult:
    """Kết quả 1 mục: file ra + trạng thái + lỗi (nếu có)."""

    item_id: str
    status: str = "pending"  # pending | done | error | skipped
    output_file: str = ""
    duration_s: float = 0.0
    error: str = ""
    attempts: int = 0


@dataclass
class BatchResult:
    """Kết quả cả batch: danh sách mục + manifest + peak RAM đo được."""

    batch_id: str
    items: list[BatchItemResult] = field(default_factory=list)
    output_dir: Path | None = None
    zip_path: Path | None = None
    peak_rss_mb: float = 0.0  # peak RSS TUYỆT ĐỐI của tiến trình lúc kết thúc batch
    rss_delta_mb: float = 0.0  # peak RSS tăng thêm trong lúc chạy batch
    elapsed_s: float = 0.0
    cancelled: bool = False

    @property
    def done_count(self) -> int:
        return sum(1 for i in self.items if i.status == "done")

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.items if i.status == "error")

    @property
    def failed_items(self) -> list[BatchItemResult]:
        return [i for i in self.items if i.status == "error"]


def parse_batch_txt(text: str) -> list[BatchItem]:
    """Parse file .txt mốc ``[P1]``…: mỗi mốc 1 mục; text trước mốc đầu bị bỏ.

    Mục rỗng (chỉ có mốc, không có text) vẫn giữ lại để BatchRunner báo lỗi
    riêng từng mục (T3.5: 1 mục lỗi không chết batch).
    """
    items: list[BatchItem] = []
    current_id: str | None = None
    current_lines: list[str] = []

    def flush() -> None:
        if current_id is not None:
            items.append(
                BatchItem(id=current_id, text=" ".join(current_lines).strip())
            )

    for line in str(text).splitlines():
        m = _MARKER_RE.match(line)
        if m:
            flush()
            current_id = m.group(1)
            current_lines = [m.group(2)] if m.group(2).strip() else []
        elif current_id is not None:
            current_lines.append(line)
    flush()
    if not items:
        raise ValueError(
            "File batch .txt không có mốc [P1]… nào — mỗi mục bắt đầu bằng [P1], [P2]…"
        )
    return items


def parse_batch_json(text: str) -> list[BatchItem]:
    """Parse file .json: list ``[{id, text, voice?}]`` hoặc ``{items: [...]}``."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"File batch .json sai định dạng: {exc}") from exc
    raw = data.get("items") if isinstance(data, dict) else data
    if not isinstance(raw, list) or not raw:
        raise ValueError("File batch .json phải là list mục [{id, text, ...}] không rỗng.")
    items: list[BatchItem] = []
    for i, entry in enumerate(raw, start=1):
        if not isinstance(entry, dict) or not str(entry.get("text") or "").strip():
            # Mục thiếu text: giữ lại với text rỗng để báo lỗi riêng (không chết batch).
            items.append(
                BatchItem(id=str(entry.get("id") or f"P{i}"), text="", voice=str(entry.get("voice_id") or entry.get("voice") or ""))
            )
            continue
        items.append(
            BatchItem(
                id=str(entry.get("id") or f"P{i}"),
                text=str(entry["text"]),
                voice=str(entry.get("voice_id") or entry.get("voice") or ""),
            )
        )
    return items


def parse_batch_file(path: str | Path) -> list[BatchItem]:
    """Parse file batch theo đuôi: .txt (mốc [P1]) / .json / .srt / .vtt."""
    p = Path(path)
    suffix = p.suffix.lower()
    raw = p.read_text(encoding="utf-8-sig")
    if suffix == ".txt":
        return parse_batch_txt(raw)
    if suffix == ".json":
        return parse_batch_json(raw)
    if suffix == ".srt":
        return [BatchItem(id=f"P{c.index}", text=c.text) for c in parse_srt_text(raw)]
    if suffix == ".vtt":
        return [BatchItem(id=f"P{c.index}", text=c.text) for c in parse_vtt_text(raw)]
    raise ValueError(f"Đuôi file batch không hỗ trợ: {suffix!r} (chỉ .txt/.json/.srt/.vtt).")


def cleanup_temp_files(directory: str | Path) -> int:
    """Quét + xóa file tạm HP (``hp-voice-tmp-*``) trong thư mục — chạy lúc
    khởi động (TH-33: dọn file tạm khi hủy/crash). Trả số file đã xóa."""
    d = Path(directory)
    if not d.is_dir():
        return 0
    removed = 0
    for p in d.iterdir():
        if p.is_file() and p.name.startswith(TEMP_PREFIX):
            try:
                p.unlink()
                removed += 1
            except OSError:
                continue
    return removed


def _peak_rss_mb() -> float:
    """Peak RSS của tiến trình hiện tại (MB) — Linux ru_maxrss tính bằng KB."""
    return float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) / 1024.0


class BatchRunner:
    """Chạy batch tuần tự, ghi từng mục ra đĩa ngay, manifest sau mỗi mục."""

    def __init__(
        self,
        engine,
        output_dir: str | Path,
        max_items: int = MAX_BATCH_ITEMS,
        default_voice: str = "Hải Đăng",
    ):
        self.engine = engine
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        # Dọn file tạm còn sót từ lần chạy trước (crash/hủy) ngay lúc khởi tạo.
        self.cleaned_temp_files = cleanup_temp_files(self.output_dir)
        self.max_items = max_items
        self.default_voice = default_voice
        self._cancel = threading.Event()
        self.measured_peak_rss_mb: float = 0.0  # peak RAM đo ở lần run gần nhất

    def cancel(self) -> None:
        """Đặt cờ hủy — batch dừng sau mục đang chạy (TH-33: file tạm được dọn)."""
        self._cancel.set()

    @property
    def is_cancelled(self) -> bool:
        return self._cancel.is_set()

    def _manifest_path(self, batch_id: str) -> Path:
        return self.output_dir / f"{batch_id}-manifest.json"

    def _write_manifest(self, batch_id: str, result: BatchResult) -> None:
        """Ghi manifest sau mỗi mục (checkpoint — ghi atomic tmp + rename)."""
        data = {
            "batch_id": batch_id,
            "items": [
                {
                    "id": r.item_id,
                    "status": r.status,
                    "output_file": r.output_file,
                    "duration_s": r.duration_s,
                    "error": r.error,
                    "attempts": r.attempts,
                }
                for r in result.items
            ],
        }
        tmp = self.output_dir / f"{TEMP_PREFIX}{batch_id}-manifest.json.tmp"
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self._manifest_path(batch_id))

    def _run_one(
        self, item: BatchItem, result_item: BatchItemResult, batch_id: str
    ) -> None:
        """Chạy 1 mục: tổng hợp → ghi WAV ngay → cập nhật kết quả."""
        result_item.attempts += 1
        voice = item.voice or self.default_voice
        if not item.text.strip():
            raise ValueError(f"Mục {item.id} rỗng — không có text để tạo giọng.")
        if len(item.text) > MAX_TEXT_CHARS:
            raise ValueError(
                f"Mục {item.id} dài {len(item.text)} ký tự, vượt giới hạn "
                f"{MAX_TEXT_CHARS} ký tự/mục."
            )
        audio = self.engine.synthesize(item.text, voice)
        samples = np.asarray(audio.samples, dtype=np.float32)
        out_path = self.output_dir / f"{batch_id}-{item.id}.wav"
        # Ghi qua file tạm rồi rename (tránh file dở khi crash giữa chừng).
        # File tạm GIỮ đuôi .wav để soundfile đoán được format (đuôi .tmp lỗi).
        tmp_path = self.output_dir / f"{TEMP_PREFIX}{batch_id}-{item.id}.wav"
        write_wav(tmp_path, samples, audio.sample_rate)
        tmp_path.replace(out_path)
        result_item.output_file = str(out_path)
        result_item.duration_s = float(len(samples)) / audio.sample_rate
        result_item.status = "done"

    def run(
        self,
        items: list[BatchItem] | list[dict] | str | Path,
        batch_id: str | None = None,
    ) -> BatchResult:
        """Chạy batch. ``items``: list mục, dict, hoặc đường dẫn file batch.

        Mục lỗi chỉ ghi lỗi vào manifest, batch vẫn chạy tiếp; hủy giữa chừng
        thì dừng sau mục đang chạy và dọn file tạm.
        """
        if isinstance(items, (str, Path)) and Path(items).is_file():
            parsed = parse_batch_file(items)
        elif isinstance(items, (str, Path)):
            raise ValueError(f"File batch không tồn tại: {items}")
        else:
            parsed = [
                it if isinstance(it, BatchItem) else BatchItem(
                    id=str(it.get("id") or f"P{i+1}"),
                    text=str(it.get("text") or ""),
                    voice=str(it.get("voice_id") or it.get("voice") or ""),
                )
                for i, it in enumerate(items)
            ]
        if len(parsed) > self.max_items:
            raise ValueError(
                f"Batch tối đa {self.max_items} mục/lần, nhận {len(parsed)} mục."
            )
        if not parsed:
            raise ValueError("Batch rỗng — không có mục nào.")
        batch_id = batch_id or uuid.uuid4().hex[:12]
        self._cancel.clear()
        t0 = time.perf_counter()
        rss_before = _peak_rss_mb()
        result = BatchResult(batch_id=batch_id, output_dir=self.output_dir)
        try:
            for item in parsed:
                if self._cancel.is_set():
                    result.cancelled = True
                    break
                r = BatchItemResult(item_id=item.id)
                result.items.append(r)
                try:
                    self._run_one(item, r, batch_id)
                except Exception as exc:  # noqa: BLE001 - lỗi 1 mục không chết batch
                    r.status = "error"
                    r.error = str(exc)
                self._write_manifest(batch_id, result)
        finally:
            # Dọn file tạm còn sót của batch này (hủy/crash giữa chừng, TH-33).
            cleanup_temp_files(self.output_dir)
        result.elapsed_s = time.perf_counter() - t0
        # ru_maxrss là peak của CẢ TIẾN TRÌNH từ lúc khởi động (không reset
        # được) nên báo cả hai số: peak tuyệt đối + phần tăng trong batch.
        result.peak_rss_mb = _peak_rss_mb()
        result.rss_delta_mb = max(0.0, result.peak_rss_mb - rss_before)
        self.measured_peak_rss_mb = result.peak_rss_mb
        return result

    def retry_failed(
        self, items: list[BatchItem] | list[dict], result: BatchResult
    ) -> BatchResult:
        """Thử lại riêng các mục lỗi của một batch đã chạy (giữ nguyên batch_id)."""
        failed_ids = {r.item_id for r in result.failed_items}
        if not failed_ids:
            return result
        lookup = {
            (it.id if isinstance(it, BatchItem) else str(it.get("id"))): it
            for it in items
        }
        self._cancel.clear()
        for r in result.items:
            if r.item_id not in failed_ids:
                continue
            item = lookup.get(r.item_id)
            if item is None:
                continue
            if self._cancel.is_set():
                result.cancelled = True
                break
            item = item if isinstance(item, BatchItem) else BatchItem(
                id=str(item.get("id")), text=str(item.get("text") or ""),
                voice=str(item.get("voice_id") or item.get("voice") or ""),
            )
            try:
                self._run_one(item, r, result.batch_id)
                r.error = ""
            except Exception as exc:  # noqa: BLE001 - vẫn lỗi thì giữ lỗi mới
                r.status = "error"
                r.error = str(exc)
            self._write_manifest(result.batch_id, result)
        cleanup_temp_files(self.output_dir)
        return result

    def export_zip(self, result: BatchResult, zip_path: str | Path | None = None) -> Path:
        """Đóng gói các file WAV đã xong + manifest thành ZIP."""
        zip_path = Path(zip_path) if zip_path else (
            self.output_dir / f"{result.batch_id}.zip"
        )
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for r in result.items:
                if r.status == "done" and r.output_file and Path(r.output_file).is_file():
                    zf.write(r.output_file, arcname=Path(r.output_file).name)
            manifest = self._manifest_path(result.batch_id)
            if manifest.is_file():
                zf.write(manifest, arcname=manifest.name)
        result.zip_path = zip_path
        return zip_path
