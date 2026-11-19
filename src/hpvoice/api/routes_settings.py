"""Route settings/config/dict (TK2.1) — endpoint 15, 16, 17 (SPEC §4).

- GET /api/config: cài đặt (key V4 KHÔNG bao giờ trả lại — chỉ báo
  ``v4_configured`` + che ``****``).
- POST /api/config: đổi cài đặt (giọng/tốc độ/format/precision...), ghi bền
  vào config.yaml qua ConfigStore.save() (TK2.1 thêm method này).
- POST /api/config/v4-key: nhập/xoá key V4 — lưu qua keyring (Windows DPAPI /
  Linux Secret Service); keyring không có backend thì chỉ giữ trong bộ nhớ
  phiên này + ghi rõ. Key KHÔNG log, KHÔNG trả lại.
- GET/POST/DELETE /api/dict: từ điển phát âm (PronDict, tối đa 2.000 mục),
  lưu bền vào file dict của config.
"""
from __future__ import annotations

import copy

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from hpvoice.voices.pron_dict import PronDict, PronDictError

router = APIRouter()

#: Tên service/username khi lưu key V4 qua keyring (TH-05).
_KEYRING_SERVICE = "hp-voice-studio"
_KEYRING_USERNAME = "v4_api_key"


def _state(request: Request):
    return request.app.state


def _masked_config(state) -> dict:
    """Config trả qua API: bản sao + trường key che kín, không lộ giá trị."""
    data = copy.deepcopy(state.config.data)
    data["v4_configured"] = bool(state.v4_configured())
    data["v4_api_key"] = "****" if state.v4_configured() else ""
    return data


@router.get("/api/config")
def get_config(request: Request):
    return _masked_config(_state(request))


@router.post("/api/config")
def update_config(request: Request, patch: dict):
    state = _state(request)
    if not isinstance(patch, dict) or not patch:
        raise HTTPException(status_code=400, detail="Body phải là JSON object cài đặt cần đổi.")
    # Kiểm tra các giá trị nhạy trước khi ghi (không ghi config lỗi).
    audio = patch.get("audio", {}) if isinstance(patch.get("audio", {}), dict) else {}
    if "default_speed" in audio:
        speed = float(audio["default_speed"])
        if speed < 0.75 or speed > 1.5:
            raise HTTPException(status_code=400,
                                detail=f"Tốc độ mặc định phải trong 0,75×–1,5×, nhận {speed}×.")
    if "default_format" in audio and audio["default_format"] not in ("wav", "mp3"):
        raise HTTPException(status_code=400, detail="default_format chỉ nhận wav/mp3.")
    engine_v3 = patch.get("engine", {}).get("v3", {}) if isinstance(patch.get("engine", {}), dict) else {}
    if "precision" in engine_v3 and str(engine_v3["precision"]).lower() not in ("auto", "fp32", "int8"):
        raise HTTPException(status_code=400, detail="precision chỉ nhận auto/fp32/int8.")
    # Không cho đổi key qua endpoint này (key chỉ qua /api/config/v4-key).
    patch = copy.deepcopy(patch)
    for section in ("engine",):
        v4 = (patch.get(section) or {}).get("v4", {}) if isinstance(patch.get(section), dict) else {}
        v4.pop("api_key", None)
    state.config.update(patch)
    return _masked_config(state)


class V4KeyRequest(BaseModel):
    api_key: str = ""


@router.post("/api/config/v4-key")
def set_v4_key(request: Request, body: V4KeyRequest):
    """Nhập/xoá key V4. Trả {configured} — key không bao giờ trả lại hay log."""
    state = _state(request)
    key = (body.api_key or "").strip()
    if not key:
        state.v4_clear_key()
        return {"configured": False}
    state.v4_store_key(key)
    return {"configured": True}


# --- Từ điển phát âm (endpoint 15) ---
def _load_dict(state) -> PronDict:
    return PronDict.load(state.dict_file)


class DictEntry(BaseModel):
    word: str = ""
    reading: str = ""


@router.get("/api/dict")
def list_dict(request: Request):
    state = _state(request)
    pron = _load_dict(state)
    return {"items": [{"word": w, "reading": r} for w, r in pron.entries().items()],
            "total": pron.count()}


@router.post("/api/dict", status_code=201)
def add_dict(request: Request, body: DictEntry):
    state = _state(request)
    pron = _load_dict(state)
    try:
        pron.add(body.word, body.reading)
    except PronDictError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    pron.save(state.dict_file)
    return {"word": body.word.strip(), "reading": body.reading.strip()}


@router.delete("/api/dict/{word}", status_code=204)
def delete_dict(request: Request, word: str):
    from fastapi.responses import Response

    state = _state(request)
    pron = _load_dict(state)
    if not pron.remove(word):
        raise HTTPException(status_code=404, detail=f"Không có từ {word!r} trong từ điển.")
    pron.save(state.dict_file)
    return Response(status_code=204)
