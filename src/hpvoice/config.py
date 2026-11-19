"""ConfigStore tối thiểu cho HP Voice Studio (TK1.2, SPEC §6).

Đọc ``config.yaml`` (YAML), hợp nhất với mặc định lấy từ ``config.example.yaml``.
Không hardcode máy/cổng/thư mục: mọi giá trị đều qua config, key KHÔNG nằm ở đây
(key V4/key LAN lưu qua keyring — xem SPEC §6/TH-05, không thuộc ticket này).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

DEFAULTS: dict[str, Any] = {
    "app": {"name": "HP Voice Studio", "language": "vi", "shell_backend": "pywebview"},
    "server": {"host": "127.0.0.1", "port": 8124, "lan_enabled": False},
    "engine": {
        "default": "v3",
        "v3": {
            "backbone_repo": "pnnbao-ump/VieNeu-TTS-v3-Turbo",
            "precision": "auto",
            "threads": 0,
            "max_batch_size": 32,
            "model_dir": "",
        },
        "v4": {
            "base_url": "https://api.vieneu.io/api/v1",
            "model": "v4",
            "fallback_to_v3": True,
            "fallback_voice": "map",
            "warn_chars": 100000,
            "timeout_sec": 60,
            "max_retries": 1,
        },
    },
    "audio": {
        "default_voice": "Hải Đăng",
        "default_speed": 1.0,
        "default_format": "wav",
        "mp3_encoder": "ffmpeg",
        "preview_sample": "Xin chào, đây là giọng đọc mẫu của HP Voice Studio.",
        "sample_rate_v3": 48000,
    },
    "api": {"max_text_chars": 20000, "max_batch_items": 500, "max_queue_jobs": 20},
    "storage": {
        "output_dir": "",
        "history_dir": "",
        "voices_file": "",
        "dict_file": "",
        "max_history_gb": 5,
    },
}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Gộp đệ quy: giá trị trong override thắng, khóa thiếu giữ nguyên base."""
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def default_data_dir() -> Path:
    """Thư mục dữ liệu theo OS (SPEC §6): Windows %LOCALAPPDATA%, Linux ~/.local/share."""
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "HPVoiceStudio"
    if os.environ.get("XDG_DATA_HOME"):
        return Path(os.environ["XDG_DATA_HOME"]) / "HPVoiceStudio"
    return Path.home() / ".local" / "share" / "HPVoiceStudio"


class ConfigStore:
    """Đọc config.yaml + mặc định. File không tồn tại -> dùng toàn mặc định."""

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else Path("config.yaml")
        self._data: dict[str, Any] = dict(DEFAULTS)
        self.loaded_from_file = False
        self.load()

    def load(self) -> dict[str, Any]:
        """Đọc lại file config (nếu có) và gộp lên mặc định."""
        if self.path.is_file():
            try:
                import yaml

                raw = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
            except Exception as exc:  # noqa: BLE001 - file lỗi thì báo rõ, dùng mặc định
                raise ValueError(f"Không đọc được config {self.path}: {exc}") from exc
            if not isinstance(raw, dict):
                raise ValueError(f"Config {self.path} phải là YAML mapping ở cấp cao nhất.")
            self._data = _deep_merge(DEFAULTS, raw)
            self.loaded_from_file = True
        return self._data

    def get(self, dotted: str, default: Any = None) -> Any:
        """Lấy giá trị theo đường dẫn chấm, VD get("server.port")."""
        node: Any = self._data
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def save(self) -> None:
        """Ghi config hiện tại ra file (atomic: file tạm + rename).

        Thêm ở TK2.1 cho POST /api/config — TK1 chỉ có đọc.
        """
        import yaml

        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".yaml.tmp")
        tmp.write_text(
            yaml.safe_dump(self._data, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        tmp.replace(self.path)
        self.loaded_from_file = True

    def update(self, patch: dict[str, Any]) -> dict[str, Any]:
        """Gộp patch vào config rồi ghi file. Trả toàn bộ config sau khi gộp."""
        self._data = _deep_merge(self._data, patch)
        self.save()
        return self._data

    @property
    def data(self) -> dict[str, Any]:
        """Toàn bộ config đã gộp (chỉ đọc)."""
        return self._data

    # --- Các giá trị hay dùng (đọc qua config, không hardcode) ---
    @property
    def precision(self) -> str:
        """Precision V3: "auto" | "fp32" | "int8" (mặc định "auto")."""
        value = str(self.get("engine.v3.precision", "auto")).lower()
        return value if value in ("auto", "fp32", "int8") else "auto"

    @property
    def backbone_repo(self) -> str:
        return str(self.get("engine.v3.backbone_repo", DEFAULTS["engine"]["v3"]["backbone_repo"]))

    @property
    def default_voice(self) -> str:
        return str(self.get("audio.default_voice", "Hải Đăng"))

    @property
    def max_text_chars(self) -> int:
        return int(self.get("api.max_text_chars", 20000))

    @property
    def max_queue_jobs(self) -> int:
        return int(self.get("api.max_queue_jobs", 20))

    @property
    def data_dir(self) -> Path:
        """Thư mục dữ liệu app (config storage.* trống -> mặc định theo OS)."""
        return default_data_dir()

    @property
    def voices_file(self) -> Path:
        """File giọng clone của HP (KHÔNG ghi vào package assets)."""
        configured = str(self.get("storage.voices_file", "") or "").strip()
        if configured:
            return Path(configured)
        return self.data_dir / "voices.json"

    @property
    def output_dir(self) -> Path:
        configured = str(self.get("storage.output_dir", "") or "").strip()
        if configured:
            return Path(configured)
        return self.data_dir / "outputs"
