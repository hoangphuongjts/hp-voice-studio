#!/usr/bin/env python3
"""T1 — WAV that dau tien cua HP Voice Studio (VieNeu-TTS v3 Turbo, ONNX/CPU).

- Liet ke giong preset (ky vong 25 giong).
- Tong hop 1 cau tieng Viet ngan bang giong preset mac dinh "Hai Dang".
- Luu WAV 48 kHz, do RTF that = thoi gian tao / do dai audio.
- Ghi log ra stdout (de luu thanh evidence) + ghi danh sach giong ra voices.json.
Chi dung SDK vieneu (khong CIT, khong V4).
"""
import json
import subprocess
import sys
import time
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent
TEXT = "Xin chào, đây là HP Voice Studio. Giọng đọc tiếng Việt chạy hoàn toàn trên máy của bạn."
VOICE = "Hải Đăng"


def hf_cache_size() -> str:
    p = Path.home() / ".cache" / "huggingface"
    r = subprocess.run(["du", "-sh", str(p)], capture_output=True, text=True)
    return r.stdout.strip() or "n/a"


def main() -> int:
    print(f"HF cache truoc khi chay: {hf_cache_size()}", flush=True)
    t0 = time.perf_counter()
    from vieneu import Vieneu

    print("Khoi tao Vieneu() [v3turbo, mac dinh fp32, ONNX/CPU] ...", flush=True)
    tts = Vieneu()
    print(f"Khoi tao xong sau {time.perf_counter() - t0:.1f}s "
          f"(backend={tts.backend}, sample_rate={tts.sample_rate})", flush=True)

    voices = tts.list_preset_voices()
    print(f"So giong preset: {len(voices)}", flush=True)
    for label, vid in voices:
        print(f"  - {label} | id={vid}", flush=True)
    (OUT_DIR / "voices.json").write_text(
        json.dumps([{"label": l, "id": v} for l, v in voices],
                   ensure_ascii=False, indent=2), encoding="utf-8")
    has_default = any(v == VOICE for _, v in voices)
    print(f'Giong mac dinh "{VOICE}" co trong preset: {has_default}', flush=True)
    if not has_default:
        print("LOI: khong tim thay giong Hai Dang trong preset.", flush=True)
        return 2

    print(f'Tong hop: "{TEXT}" (voice={VOICE}) ...', flush=True)
    t1 = time.perf_counter()
    audio = tts.infer(TEXT, voice=VOICE)
    gen_s = time.perf_counter() - t1
    wav_path = OUT_DIR / "t1-first-wav-hai-dang.wav"
    tts.save(audio, wav_path)
    dur_s = len(audio) / tts.sample_rate
    rtf = gen_s / dur_s if dur_s else float("nan")
    print(f"WAV: {wav_path}", flush=True)
    print(f"  so mau: {len(audio)}, sample_rate: {tts.sample_rate}", flush=True)
    print(f"  do dai audio: {dur_s:.2f}s", flush=True)
    print(f"  thoi gian tao (infer): {gen_s:.2f}s", flush=True)
    print(f"  RTF = {gen_s:.2f} / {dur_s:.2f} = {rtf:.3f}", flush=True)
    print(f"HF cache sau khi chay: {hf_cache_size()}", flush=True)
    print("T1 DONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
