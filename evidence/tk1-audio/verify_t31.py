"""Kiểm chứng T3.1 ĐỘC LẬP (không đo bằng chính công cụ tạo ra nó).

1. Thẻ [nghỉ 2s]: nối 2 đoạn tone bằng AudioPost.join_chunks với pause 2,0 s,
   ghi WAV, đo khoảng lặng bằng ffprobe silencedetect (độc lập) — kỳ vọng
   ≈ 2 s ± 0,3 s. Lặp lại với 2 nửa file WAV mẫu T1 thật.
2. Mốc .srt: SrtWriter suy mốc từ chunk audio tổng hợp; mốc kiểm chứng bằng
   phát hiện onset trên envelope sóng âm của audio đã nối (ngưỡng -45 dB,
   cửa sổ 10 ms) — so sánh từng mốc, báo sai số từng câu (10 câu đầu) và
   sai số tối đa ở câu cuối.

Chạy: .venv/bin/python evidence/tk1-audio/verify_t31.py
Ghi JSON ra evidence/tk1-audio/t31-verify.json
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "src"))

from hpvoice.audio.post import SAMPLE_RATE, join_chunks, write_wav  # noqa: E402
from hpvoice.audio.srt_writer import SrtWriter, chunk_text  # noqa: E402

SR = SAMPLE_RATE
OUT = REPO / "evidence" / "tk1-audio"
OUT.mkdir(parents=True, exist_ok=True)


def tone(freq: float, dur: float) -> np.ndarray:
    t = np.arange(int(dur * SR)) / SR
    return (0.5 * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def silences_ffprobe(path: Path, noise_db: float = -45.0, min_dur: float = 0.1):
    """Các khoảng lặng do ffprobe silencedetect phát hiện: [(start, end)]."""
    r = subprocess.run(
        ["ffmpeg", "-i", str(path), "-af",
         f"silencedetect=noise={noise_db}dB:d={min_dur}", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    return list(zip(starts, ends))


def onsets_envelope(y: np.ndarray, sr: int, thresh_db: float = -45.0):
    """Mốc bắt đầu có tiếng (envelope mean|x| cửa sổ 10 ms vượt ngưỡng)."""
    win = max(1, int(0.01 * sr))
    n_win = len(y) // win
    env = np.abs(y[: n_win * win]).reshape(n_win, win).mean(1)
    above = np.flatnonzero(env > 10 ** (thresh_db / 20))
    if not above.size:
        return []
    # Gom các cửa sổ liên tiếp thành từng đoạn có tiếng; lấy mốc đầu mỗi đoạn.
    onsets = [float(above[0] * win / sr)]
    for i in range(1, len(above)):
        if above[i] - above[i - 1] > 5:  # cách nhau > 50 ms → đoạn mới
            onsets.append(float(above[i] * win / sr))
    return onsets


def main() -> int:
    report: dict = {}

    # --- 1. [nghỉ 2s] trên tone tổng hợp ---
    joined = join_chunks([tone(440, 1.0), tone(660, 1.0)], SR, pauses=[2.0])
    p1 = OUT / "t31-pause-tone.wav"
    write_wav(p1, joined, SR)
    sil = silences_ffprobe(p1)
    longest = max((e - s for s, e in sil), default=0.0)
    report["pause_tone"] = {
        "file": p1.name, "expected_s": 2.0, "silences_detected": sil,
        "longest_silence_s": round(longest, 3),
        "error_s": round(longest - 2.0, 3),
        "pass_pm_0_3s": abs(longest - 2.0) <= 0.3,
    }

    # --- 1b. [nghỉ 2s] trên WAV mẫu T1 thật (cắt 2 nửa) ---
    sample = REPO / "evidence" / "t1-first-wav" / "t1-first-wav-hai-dang.wav"
    y, sr = sf.read(str(sample), dtype="float32")
    half = len(y) // 2
    joined2 = join_chunks([y[:half], y[half:]], sr, pauses=[2.0])
    p2 = OUT / "t31-pause-sample.wav"
    write_wav(p2, joined2, sr)
    sil2 = silences_ffprobe(p2)
    longest2 = max((e - s for s, e in sil2), default=0.0)
    report["pause_sample"] = {
        "file": p2.name, "expected_s": 2.0, "silences_detected": sil2,
        "longest_silence_s": round(longest2, 3),
        "error_s": round(longest2 - 2.0, 3),
        "pass_pm_0_3s": abs(longest2 - 2.0) <= 0.3,
    }

    # --- 2. Mốc .srt đo độc lập bằng onset envelope ---
    # 3 đoạn (ngắt đoạn → gap para 0,70 s), mỗi đoạn 1 câu.
    text = ("Câu thứ nhất rất hay.\n\nCâu thứ hai cũng rất hay.\n\n"
            "Câu thứ ba cũng rất hay.")
    # 3 chunk: tone 1,0 s + đuôi im lặng 0,30 s (chunk 1-2), chunk 3 tone 1,0 s.
    # Ranh giới para → tổng nghỉ 0,70 s, bù zeros 0,40 s mỗi khe.
    c1 = np.concatenate([tone(440, 1.0), np.zeros(int(0.30 * SR), dtype=np.float32)])
    c2 = np.concatenate([tone(550, 1.0), np.zeros(int(0.30 * SR), dtype=np.float32)])
    c3 = tone(660, 1.0)
    chunks, gaps = chunk_text(text)
    assert len(chunks) == 3, chunks
    assert gaps == ["para", "para"], gaps
    w = SrtWriter()
    cues = w.build_cues(text, [c1, c2, c3], SR)
    # Audio nối như engine nối: khoảng lặng TỔNG ở khe = gaps_to_silence
    # (para 0,70 s); join_chunks chỉ bù zeros cho phần còn thiếu sau khi trừ
    # im lặng mép (0,30 s đuôi) → pad 0,40 s mỗi khe.
    joined3 = join_chunks([c1, c2, c3], SR, pauses=[0.70, 0.70])
    p3 = OUT / "t31-srt-audio.wav"
    write_wav(p3, joined3, SR)
    detected = onsets_envelope(joined3, SR)
    errors = []
    for cue, det in zip(cues, detected):
        errors.append({"sentence": cue.text, "srt_start_s": round(cue.start_s, 3),
                       "detected_onset_s": round(det, 3),
                       "error_s": round(det - cue.start_s, 3)})
    max_err = max((abs(e["error_s"]) for e in errors), default=None)
    report["srt_cues"] = {
        "file": p3.name, "gaps": gaps, "cues": errors,
        "max_abs_error_first_10_s": max_err,
        "max_abs_error_last_sentence_s": abs(errors[-1]["error_s"]) if errors else None,
        "pass_pm_0_3s_first_10": (max_err is not None and max_err <= 0.3),
    }
    (OUT / "t31-verify.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    ok = (report["pause_tone"]["pass_pm_0_3s"]
          and report["pause_sample"]["pass_pm_0_3s"]
          and report["srt_cues"]["pass_pm_0_3s_first_10"])
    print("KET LUAN T3.1:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
