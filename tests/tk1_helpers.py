"""Helper riêng cho test TK1 (không đụng conftest.py chung của repo).

Mỗi module test TK1 tự định nghĩa fixture module-scoped từ ``engine_context``:
nạp engine 1 lần cho cả module rồi giải phóng cuối module, vì RAM máy ảo eo
hẹp — KHÔNG giữ 2 engine cùng lúc.
"""

import contextlib
import gc
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
EVIDENCE_DIR = REPO_DIR / "evidence" / "tk1-engine"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

# Clip mẫu 3-8 s có sẵn (WAV thật từ T1, giọng Hải Đăng, 4,88 s).
SAMPLE_WAV = REPO_DIR / "evidence" / "t1-first-wav" / "t1-first-wav-hai-dang.wav"

SHORT_TEXT = "Xin chào, đây là HP Voice Studio."
VOICE = "Hải Đăng"


@contextlib.contextmanager
def engine_context(precision: str):
    """Nạp V3Engine (precision cho trước), yield, rồi giải phóng + gc."""
    from hpvoice.engines import V3Engine

    engine = V3Engine(precision=precision)
    engine.ensure_loaded()
    try:
        yield engine
    finally:
        engine.close()
        del engine
        gc.collect()
