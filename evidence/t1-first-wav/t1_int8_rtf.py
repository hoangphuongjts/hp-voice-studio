#!/usr/bin/env python3
"""T1 phu: do RTF int8 (CPU co AVX512-VNNI) - 1 lan infer."""
import time
from vieneu import Vieneu
TEXT = "Xin chào, đây là HP Voice Studio. Giọng đọc tiếng Việt chạy hoàn toàn trên máy của bạn."
t0 = time.perf_counter()
tts = Vieneu(precision="int8")
print(f"init int8: {time.perf_counter()-t0:.1f}s backend={tts.backend}", flush=True)
t1 = time.perf_counter()
audio = tts.infer(TEXT, voice="Hải Đăng")
gen = time.perf_counter() - t1
dur = len(audio) / tts.sample_rate
print(f"int8: tao {gen:.2f}s / audio {dur:.2f}s -> RTF {gen/dur:.3f}", flush=True)
tts.save(audio, "evidence/t1-first-wav/t1-int8-hai-dang.wav")
print("INT8 DONE", flush=True)
