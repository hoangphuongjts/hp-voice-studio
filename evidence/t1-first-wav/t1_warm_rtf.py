#!/usr/bin/env python3
"""T1 phu: do RTF am (warm) - cung text, infer 3 lan lien tiep trong 1 process."""
import time
from vieneu import Vieneu
TEXT = "Xin chào, đây là HP Voice Studio. Giọng đọc tiếng Việt chạy hoàn toàn trên máy của bạn."
t0 = time.perf_counter()
tts = Vieneu()
print(f"init: {time.perf_counter()-t0:.1f}s backend={tts.backend}", flush=True)
for i in range(3):
    t1 = time.perf_counter()
    audio = tts.infer(TEXT, voice="Hải Đăng")
    gen = time.perf_counter() - t1
    dur = len(audio) / tts.sample_rate
    print(f"lan {i+1}: tao {gen:.2f}s / audio {dur:.2f}s -> RTF {gen/dur:.3f}", flush=True)
print("WARM DONE", flush=True)
