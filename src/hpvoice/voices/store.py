"""VoiceStore — preset + giọng clone (TK1.5, SPEC §3.3, TH-04/TH-17).

- Preset: đọc từ SDK qua V3Engine, KHÔNG hardcode tên giọng.
- Clone: ``add_voice`` của SDK, ghi ra file RIÊNG của HP (config storage.voices_file,
  mặc định ``~/.local/share/HPVoiceStudio/voices.json``) — KHÔNG BAO GIỜ ghi đè
  ``assets/voices_v3_turbo.json`` trong package (SDK mặc định ghi đè file đó khi
  gọi ``save_voices()`` không tham số; VoiceStore luôn truyền path HP).
- Cam kết quyền sử dụng: clone bắt buộc có ``consent=True`` kèm văn bản cam kết;
  không cam kết -> lỗi rõ (tương đương 400 ở API), không tạo giọng.
- Gỡ giọng khi khiếu nại (TH-17): ``takedown()`` gỡ khỏi engine + file HP và
  ghi lại lý do + thời gian vào sổ gỡ giọng.
- Clip mẫu: nhận 3–8 s (SPEC §2.2), kiểm tra bằng soundfile trước khi enroll.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import time
from pathlib import Path

import numpy as np

from ..engines.base import VoiceInfo
from ..engines.v3_engine import V3Engine

MIN_CLIP_SECONDS = 3.0
MAX_CLIP_SECONDS = 8.0
CONSENT_TEXT = (
    "Tôi cam kết clip mẫu này là giọng của chính tôi hoặc tôi đã được chủ giọng "
    "đồng ý cho dùng để tạo giọng đọc AI trong HP Voice Studio (dùng cá nhân, "
    "không phát tán khi chưa được phép)."
)


class VoiceStoreError(ValueError):
    """Lỗi giọng đọc (tên trùng, clip sai, thiếu cam kết...) — API map thành 400."""


def clip_duration_seconds(path: str | Path) -> float:
    """Độ dài clip (giây) qua soundfile (không giải mã toàn bộ)."""
    import soundfile as sf

    info = sf.info(str(path))
    if info.samplerate <= 0:
        raise VoiceStoreError(f"Không đọc được sample rate của clip: {path}")
    return float(info.frames) / float(info.samplerate)


def sha256_file(path: str | Path) -> str:
    """SHA-256 của file (để đối chiếu clip mẫu đã đăng ký)."""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


class VoiceStore:
    """Kho giọng: 25 preset (SDK) + giọng clone (file HP riêng)."""

    def __init__(self, engine: V3Engine, voices_file: str | Path | None = None,
                 data_dir: str | Path | None = None):
        self.engine = engine
        self.voices_file = Path(voices_file) if voices_file else Path("voices.json")
        self.data_dir = Path(data_dir) if data_dir else self.voices_file.parent
        self.data_dir.mkdir(parents=True, exist_ok=True)
        # Hồ sơ clone của HP: {name: {consent, consent_text, ref_sha256, ...}}.
        self._clones: dict[str, dict] = {}
        # Sổ gỡ giọng (TH-17): [{name, reason, at}].
        self._takedowns: list[dict] = []
        self._load_hp_file()

    # --- File HP riêng ---
    def _load_hp_file(self) -> None:
        """Đọc file HP (nếu có) và khôi phục giọng clone vào engine."""
        if not self.voices_file.is_file():
            return
        try:
            data = json.loads(self.voices_file.read_text(encoding="utf-8"))
        except Exception:
            return  # file hỏng -> bỏ qua, không crash app; ghi đè khi clone mới
        self._clones = dict(data.get("clones", {}) or {})
        self._takedowns = list(data.get("takedowns", []) or [])
        # Khôi phục embedding clone vào engine (cùng cấu trúc SDK dùng ở
        # _load_v3_voices: speaker_emb + codes). File hỏng từng giọng thì bỏ giọng đó.
        try:
            self.engine.ensure_loaded()
        except Exception:
            return
        sdk = self.engine._tts
        if sdk is None:
            return
        for name, rec in self._clones.items():
            emb = rec.get("speaker_emb")
            codes = rec.get("codes")
            if emb is None:
                continue
            try:
                sdk._preset_voices[name] = {
                    "description": rec.get("description", ""),
                    "gender": rec.get("gender", ""),
                    "style": rec.get("style", sdk.default_style),
                    "speaker_emb": np.asarray(emb, dtype=np.float32),
                    "codes": np.asarray(codes, dtype=np.int64) if codes is not None else None,
                }
            except Exception:
                continue

    def _save_hp_file(self) -> None:
        """Ghi file HP (ghi atomic: file tạm + rename, tránh corrupt khi tắt đột ngột)."""
        self.voices_file.parent.mkdir(parents=True, exist_ok=True)
        data = {"clones": self._clones, "takedowns": self._takedowns}
        tmp = self.voices_file.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.voices_file)

    # --- Preset ---
    def list_preset_voices(self) -> list[VoiceInfo]:
        """25 giọng preset từ SDK."""
        return self.engine.list_preset_voices()

    def list_clone_voices(self) -> list[VoiceInfo]:
        """Giọng clone đã đăng ký (file HP)."""
        return [
            VoiceInfo(
                id=name,
                label=name,
                gender=str(rec.get("gender", "") or ""),
                style=str(rec.get("style", "") or ""),
                is_clone=True,
                description=str(rec.get("description", "") or ""),
            )
            for name, rec in self._clones.items()
        ]

    def list_all_voices(self) -> list[VoiceInfo]:
        """Tất cả giọng: preset + clone."""
        return self.list_preset_voices() + self.list_clone_voices()

    def resolve_voice(self, name: str | None) -> str | None:
        if name in self._clones:
            return name
        return self.engine.resolve_voice(name)

    # --- Clone (Q13: giữ cả micro + upload file — ở tầng engine chỉ nhận file) ---
    def clone_voice(
        self,
        name: str,
        ref_audio: str | Path,
        consent: bool,
        consent_text: str = "",
        description: str = "",
        gender: str = "",
        keep_ref_copy: bool = True,
    ) -> VoiceInfo:
        """Đăng ký giọng clone từ clip mẫu 3–8 s.

        - ``consent=False`` hoặc thiếu văn bản cam kết -> lỗi rõ, không tạo giọng.
        - Clip < 3 s hoặc > 8 s -> lỗi rõ.
        - Tên trùng preset/clone đã có -> lỗi rõ.
        """
        name = (name or "").strip()
        if not name:
            raise VoiceStoreError("Tên giọng clone không được để trống.")
        if not consent:
            raise VoiceStoreError(
                "Chưa có cam kết quyền sử dụng — không thể tạo giọng clone. "
                "Chỉ tạo giọng của chính bạn hoặc giọng đã được chủ giọng đồng ý."
            )
        if not (consent_text or "").strip():
            raise VoiceStoreError("Thiếu văn bản cam kết quyền sử dụng giọng.")
        ref_path = Path(ref_audio)
        if not ref_path.is_file():
            raise VoiceStoreError(f"Không tìm thấy clip mẫu: {ref_audio}")
        duration = clip_duration_seconds(ref_path)
        if duration < MIN_CLIP_SECONDS or duration > MAX_CLIP_SECONDS:
            raise VoiceStoreError(
                f"Clip mẫu dài {duration:.1f}s — chỉ nhận clip 3–8 s "
                "(Turbo dùng tối đa 8 s có tiếng)."
            )
        if self.engine.resolve_voice(name) is not None or name in self._clones:
            raise VoiceStoreError(f'Tên giọng "{name}" đã tồn tại (trùng preset hoặc clone).')

        # Enroll qua SDK (chỉ bộ nhớ; KHÔNG save=True để khỏi ghi đè assets).
        self.engine.add_voice(name, str(ref_path), description=description, gender=gender)
        # Lấy embedding vừa enroll để lưu vào file HP riêng.
        sdk = self.engine._tts
        record = sdk._preset_voices.get(name, {}) if sdk is not None else {}
        emb = record.get("speaker_emb")
        codes = record.get("codes")
        ref_copy_path = ""
        if keep_ref_copy:
            ref_copy_path = str(self.data_dir / f"ref_{name}.wav")
            try:
                shutil.copyfile(ref_path, ref_copy_path)
            except OSError:
                ref_copy_path = ""
        self._clones[name] = {
            "description": description,
            "gender": gender,
            "style": record.get("style", ""),
            "speaker_emb": [round(float(x), 6) for x in np.asarray(emb).reshape(-1)]
            if emb is not None else None,
            "codes": np.asarray(codes, dtype=int).tolist() if codes is not None else None,
            "consent": True,
            "consent_text": consent_text,
            "ref_sha256": sha256_file(ref_path),
            "ref_copy": ref_copy_path,
            "clip_seconds": round(duration, 2),
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        self._save_hp_file()
        return VoiceInfo(id=name, label=name, gender=gender, is_clone=True,
                         description=description)

    # --- Gỡ giọng khi khiếu nại (TH-17) ---
    def takedown(self, name: str, reason: str) -> None:
        """Gỡ giọng clone khi có khiếu nại: khỏi engine + khỏi file HP, ghi sổ."""
        name = (name or "").strip()
        if name not in self._clones:
            raise VoiceStoreError(f'Không có giọng clone "{name}" để gỡ.')
        if not (reason or "").strip():
            raise VoiceStoreError("Gỡ giọng cần ghi rõ lý do khiếu nại.")
        self.engine.remove_voice(name)
        self._clones.pop(name, None)
        self._takedowns.append({
            "name": name,
            "reason": reason,
            "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        })
        self._save_hp_file()

    def list_takedowns(self) -> list[dict]:
        """Sổ gỡ giọng (để đối chiếu khi có khiếu nại)."""
        return list(self._takedowns)
