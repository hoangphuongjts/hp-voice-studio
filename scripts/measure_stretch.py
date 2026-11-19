"""Đo RTF + chất lượng librosa time-stretch vs FFmpeg atempo (TK1.9, TH-20).

Dùng file WAV mẫu thật (evidence/t1-first-wav/t1-first-wav-hai-dang.wav,
4,88 s, giọng Hải Đăng) — KHÔNG load model, KHÔNG dùng V4.

Đo mỗi cách ở 0,75× và 1,5× (sau 1 lần warmup cho librosa vì numba JIT):
- RTF = thời gian xử lý / thời lượng audio gốc (mục tiêu ≤ 1 ở T2.4).
- Tỉ lệ thời lượng = độ dài ra / độ dài vào (kỳ vọng 1/rate ±10%).
- Năng lượng: RMS ra / RMS vào, đỉnh ra (phát hiện méo/cắt).
- Nghe đối chiếu bằng tai để lại cho Annie/người dùng (không đo ở đây).

Chạy: .venv/bin/python scripts/measure_stretch.py [--out evidence/tk1-audio/stretch-measure.json]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from hpvoice.audio.ffmpeg_manager import FFmpegManager  # noqa: E402
from hpvoice.audio.post import SAMPLE_RATE, time_stretch  # noqa: E402

SAMPLE_WAV = REPO / "evidence" / "t1-first-wav" / "t1-first-wav-hai-dang.wav"


def _stats(y: np.ndarray, sr: int) -> dict:
    return {
        "duration_s": round(len(y) / sr, 3),
        "rms": round(float(np.sqrt(np.mean(y.astype(np.float64) ** 2))), 5),
        "peak": round(float(np.max(np.abs(y))), 4),
    }


def _ffprobe_duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True,
    )
    return float(r.stdout.strip())


def measure_librosa(y: np.ndarray, sr: int, rate: float) -> dict:
    # Warmup (numba JIT lần đầu rất chậm — không tính vào RTF).
    time_stretch(y[: sr // 2], sr, rate)
    t0 = time.perf_counter()
    out, _ = time_stretch(y, sr, rate)
    dt = time.perf_counter() - t0
    in_dur = len(y) / sr
    res = {"engine": "librosa", "rate": rate, "rtf": round(dt / in_dur, 3),
           "proc_s": round(dt, 3), "duration_ratio": round(len(out) / len(y), 3)}
    res.update({f"out_{k}": v for k, v in _stats(out, sr).items()})
    return res


def measure_atempo(wav: Path, tmp: Path, rate: float) -> dict:
    fm = FFmpegManager()
    out_path = tmp / f"atempo-{rate}.wav"
    y, sr = sf.read(str(wav), dtype="float32")
    in_dur = len(y) / sr
    t0 = time.perf_counter()
    ok = fm.run_atempo(wav, out_path, rate)
    dt = time.perf_counter() - t0
    if not ok:
        return {"engine": "atempo", "rate": rate, "error": "ffmpeg không chạy được: " + fm.status_message}
    y2, sr2 = sf.read(str(out_path), dtype="float32")
    res = {"engine": "atempo", "rate": rate, "rtf": round(dt / in_dur, 3),
           "proc_s": round(dt, 3), "duration_ratio": round(len(y2) / len(y), 3),
           "ffprobe_duration_s": round(_ffprobe_duration(out_path), 3)}
    res.update({f"out_{k}": v for k, v in _stats(y2, sr2).items()})
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="evidence/tk1-audio/stretch-measure.json")
    args = ap.parse_args()
    y, sr = sf.read(str(SAMPLE_WAV), dtype="float32")
    in_stats = _stats(y, sr)
    print(f"Nguồn: {SAMPLE_WAV.name} — {in_stats}")
    results = {"source": str(SAMPLE_WAV), "input": in_stats, "measurements": []}
    tmp = Path("evidence/tk1-audio/tmp-stretch")
    tmp.mkdir(parents=True, exist_ok=True)
    for rate in (0.75, 1.5):
        for fn in (measure_librosa, measure_atempo):
            if fn is measure_librosa:
                m = measure_librosa(y, sr, rate)
            else:
                m = measure_atempo(SAMPLE_WAV, tmp, rate)
            results["measurements"].append(m)
            print(m)
    out_path = REPO / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Đã ghi: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
