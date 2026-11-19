"""Thí nghiệm chặn import — kiểm chứng SDK v3 Turbo + HP Voice Studio có
chạy được khi KHÔNG có librosa/numba/llvmlite/scipy/sklearn/pandas/gradio/PIL
(hướng loại khỏi gói frozen để giảm kích thước).

Chạy bằng .venv python. Model đã cache sẵn, HF_HUB_OFFLINE=1.
Kết quả ghi ra stdout; chạy nền: nohup .venv/bin/python evidence/size-reduction/block_test.py > evidence/size-reduction/block_test.log 2>&1 &
"""
import sys

BLOCKED = {"librosa", "numba", "llvmlite", "scipy", "sklearn", "pandas",
           "joblib", "pooch", "gradio", "PIL"}


class _Blocker:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in BLOCKED:
            raise ImportError(f"BLOCKED (size test): {fullname}")
        return None


sys.meta_path.insert(0, _Blocker())

import os

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["HPVOICE_DATA_DIR"] = "/tmp/block-test-data"
sys.path.insert(0, "src")

results = {}


def step(name, fn):
    try:
        out = fn()
        results[name] = ("PASS", out)
        print(f"PASS {name}: {out}", flush=True)
    except Exception as exc:  # noqa: BLE001
        results[name] = ("FAIL", f"{type(exc).__name__}: {exc}")
        print(f"FAIL {name}: {type(exc).__name__}: {exc}", flush=True)


def _import_hpvoice():
    import hpvoice.engines.v3_engine  # noqa: F401
    import hpvoice.audio.post  # noqa: F401
    import hpvoice.audio.srt_dubber  # noqa: F401
    import hpvoice.api.routes_tts  # noqa: F401
    import hpvoice.files.readers  # noqa: F401
    import hpvoice.audio.ffmpeg_manager  # noqa: F401
    return "hpvoice modules imported"


def _engine_load():
    from hpvoice.engines.v3_engine import V3Engine

    eng = V3Engine(precision="fp32")
    eng.ensure_loaded()
    n = len(eng.list_preset_voices())
    assert n == 25, f"preset voices = {n}, expected 25"
    step._eng = eng
    return "model loaded, 25 preset voices"


def _synthesize():
    eng = step._eng
    r = eng.synthesize("Xin chào, đây là kiểm tra giọng nói.", "Hải Đăng")
    assert len(r.samples) > 1000, f"samples={len(r.samples)}"
    return f"{len(r.samples)} samples @ {r.sample_rate} Hz"


def _clone_ref():
    eng = step._eng
    ref = "evidence/t1-first-wav/t1-first-wav-hai-dang.wav"
    # encode_reference: _load_ref_mono (librosa -> soundfile+soxr fallback)
    emb = eng.encode_reference(ref)
    # add_voice: trim ref clip (librosa -> numpy fallback)
    vid = eng.add_voice("test-block-clone", ref)
    r = eng.synthesize("Giọng clone kiểm tra.", vid)
    assert len(r.samples) > 1000
    return f"clone voice {vid} synthesized {len(r.samples)} samples"


def _server_import():
    sys.path.insert(0, "server")
    import hp_api  # noqa: F401

    return "hp_api imported"


step("import_hpvoice", _import_hpvoice)
step("engine_load_25_voices", _engine_load)
step("synthesize_preset", _synthesize)
step("clone_encode_add_voice", _clone_ref)
step("server_import", _server_import)

failed = [k for k, (s, _) in results.items() if s == "FAIL"]
print("RESULT:", "ALL PASS" if not failed else f"FAILED: {failed}", flush=True)
sys.exit(0 if not failed else 1)
