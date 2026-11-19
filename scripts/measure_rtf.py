#!/usr/bin/env python3
"""Đo hiệu năng CPU thật cho V3Engine (TK1.4, SPEC §10 T1.4/T1.7).

Đo, theo từng precision (fp32/int8):
- thời gian nạp model (cold, model đã cache) — T1.7,
- RTF = thời gian infer / độ dài audio (nhiều lần, lấy trung bình + min/max),
- độ trễ chunk đầu của infer_stream (mục tiêu <= 500 ms — T1.5).

Ghi rõ model CPU máy đo + VNNI (xem docs/cpu-reference.md). Số đo trên VM này
CHẬM hơn real-time là bằng chứng đo thật — ghi số thật, không "sửa" cho đạt
ngưỡng; ngưỡng mượt cuối cùng đo lại trên máy Windows thật (C6).

Chạy:  .venv/bin/python scripts/measure_rtf.py [--precisions fp32 int8]
        [--repeats 3] [--output evidence/tk1-engine/rtf.json]
"""

from __future__ import annotations

import argparse
import gc
import json
import statistics
import sys
import time
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_DIR / "src"))

TEXT = "Xin chào, đây là HP Voice Studio. Giọng đọc tiếng Việt chạy hoàn toàn trên máy của bạn."
VOICE = "Hải Đăng"
DEFAULT_OUTPUT = REPO_DIR / "evidence" / "tk1-engine" / "rtf.json"


def measure_precision(precision: str, repeats: int) -> dict:
    """Đo load + RTF + first-chunk latency cho một precision. Giải phóng sau khi đo."""
    from hpvoice.engines import V3Engine

    t0 = time.perf_counter()
    engine = V3Engine(precision=precision)
    engine.ensure_loaded()
    load_s = time.perf_counter() - t0

    # Warmup 1 lần (không tính).
    warm = engine.synthesize(TEXT, VOICE)
    warm_rtf = (time.perf_counter() - t0)  # không dùng, chỉ để warmup chạy xong
    _ = warm_rtf
    rtf_values: list[float] = []
    for _ in range(repeats):
        t1 = time.perf_counter()
        result = engine.synthesize(TEXT, VOICE)
        gen_s = time.perf_counter() - t1
        rtf_values.append(gen_s / result.duration_s if result.duration_s else float("nan"))
    # Độ trễ chunk đầu của stream.
    t2 = time.perf_counter()
    first_latency = None
    for chunk in engine.synthesize_stream(TEXT, VOICE):
        first_latency = time.perf_counter() - t2
        break
    engine.close()
    del engine
    gc.collect()
    return {
        "precision": precision,
        "load_seconds": round(load_s, 1),
        "audio_seconds": round(warm.duration_s, 2),
        "rtf_values": [round(v, 3) for v in rtf_values],
        "rtf_mean": round(statistics.mean(rtf_values), 3),
        "rtf_min": round(min(rtf_values), 3),
        "rtf_max": round(max(rtf_values), 3),
        "first_chunk_latency_s": round(first_latency, 3) if first_latency is not None else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Đo RTF fp32/int8 thật của V3Engine.")
    parser.add_argument("--precisions", nargs="*", default=["fp32", "int8"])
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    from hpvoice.engines.cpu_detect import detect_cpu, weak_machine_advice

    cpu = detect_cpu()
    report: dict = {
        "cpu_model": cpu.model,
        "has_avx512_vnni": cpu.has_avx512_vnni,
        "has_avx_vnni": cpu.has_avx_vnni,
        "vnni_source": cpu.source,
        "default_precision": cpu.default_precision(),
        "text": TEXT,
        "voice": VOICE,
        "repeats": args.repeats,
        "precisions": {},
    }
    for precision in args.precisions:
        print(f"Đo {precision} ...", flush=True)
        result = measure_precision(precision, args.repeats)
        report["precisions"][precision] = result
        print(f"  load {result['load_seconds']}s, RTF mean {result['rtf_mean']} "
              f"(min {result['rtf_min']}, max {result['rtf_max']}), "
              f"chunk đầu {result['first_chunk_latency_s']}s.", flush=True)
    fp32_rtf = report["precisions"].get("fp32", {}).get("rtf_mean")
    if fp32_rtf is not None:
        report["weak_machine_advice"] = weak_machine_advice(fp32_rtf)
        if report["weak_machine_advice"]:
            print(report["weak_machine_advice"], flush=True)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Báo cáo: {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
