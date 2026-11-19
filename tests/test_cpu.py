"""Test phát hiện VNNI + đo RTF (TK1.4) — T1.4, T1.7.

- Unit test (không cần model): logic phát hiện cờ, mặc định fp32 khi không đọc
  được cờ, nhánh dự phòng máy yếu.
- Integration test (model thật): đo RTF fp32 + int8 thật, ghi số đo + model CPU
  vào evidence/tk1-engine/rtf.json. KHÔNG assert ngưỡng mượt (RTF <= 1) trên
  VM này — CPU chia sẻ chậm hơn real-time là bằng chứng đo thật; ngưỡng cuối
  đo lại trên máy Windows thật (C6).
"""

import json
import statistics
import time

import pytest

from tk1_helpers import EVIDENCE_DIR, SHORT_TEXT, VOICE, engine_context


def test_phat_hien_vnni_tren_vm_nay():
    """TH-03: VM này có VNNI (dạng nào tùy host).

    LƯU Ý host đổi (19/11): T1-REPORT ghi host cũ AMD EPYC 9D25 có cả
    AVX-VNNI + AVX512-VNNI; host hiện tại AMD EPYC 9D64 chỉ còn AVX512-VNNI
    (``/proc/cpuinfo`` không còn cờ avx_vnni). Logic phát hiện không sai —
    nó báo đúng cờ của host mới — nên test này chỉ assert: model đọc được,
    CÓ VNNI (dạng nào cũng được), mặc định int8. Logic từng cờ riêng đã
    có test monkeypatch bên dưới (test_chi_co_avx_vnni_thi_int8,
    test_chi_co_avx512_vnni_thi_int8)."""
    from hpvoice.engines.cpu_detect import detect_cpu

    cpu = detect_cpu()
    assert cpu.model and cpu.model != "không xác định"
    assert cpu.has_vnni is True, f"VM này phải có VNNI (dạng nào cũng được): {cpu}"
    assert cpu.has_avx512_vnni is True, f"Host hiện tại phải có avx512_vnni: {cpu}"
    assert cpu.default_precision() == "int8"


def test_khong_doc_duoc_co_thi_mac_dinh_fp32(monkeypatch):
    """T1.4: không đọc được cờ -> mặc định fp32 (an toàn, không đoán mò)."""
    import hpvoice.engines.cpu_detect as mod

    monkeypatch.setattr(mod, "_flags_from_py_cpuinfo", lambda: (set(), ""))
    monkeypatch.setattr(mod, "_flags_from_proc_cpuinfo", lambda: (set(), ""))
    cpu = mod.detect_cpu()
    assert cpu.has_vnni is False
    assert cpu.source == ""
    assert cpu.default_precision() == "fp32"


def test_chi_co_avx_vnni_thi_int8(monkeypatch):
    """T1.4 (trường hợp v1.1 phát hiện sai): chỉ AVX-VNNI (VD i5 12th-gen) -> int8."""
    import hpvoice.engines.cpu_detect as mod

    monkeypatch.setattr(mod, "_flags_from_py_cpuinfo",
                        lambda: ({"avx_vnni", "avx2"}, "Intel i5-12400"))
    monkeypatch.setattr(mod, "_flags_from_proc_cpuinfo", lambda: (set(), ""))
    cpu = mod.detect_cpu()
    assert cpu.has_avx_vnni is True
    assert cpu.has_avx512_vnni is False
    assert cpu.default_precision() == "int8"


def test_chi_co_avx512_vnni_thi_int8(monkeypatch):
    """T1.4: chỉ AVX-512 VNNI -> int8."""
    import hpvoice.engines.cpu_detect as mod

    monkeypatch.setattr(mod, "_flags_from_py_cpuinfo",
                        lambda: ({"avx512vnni", "avx512f"}, "Intel Xeon"))
    monkeypatch.setattr(mod, "_flags_from_proc_cpuinfo", lambda: (set(), ""))
    cpu = mod.detect_cpu()
    assert cpu.has_avx512_vnni is True
    assert cpu.default_precision() == "int8"


def test_khong_co_vnni_thi_fp32(monkeypatch):
    """T1.4: CPU không có VNNI -> fp32."""
    import hpvoice.engines.cpu_detect as mod

    monkeypatch.setattr(mod, "_flags_from_py_cpuinfo",
                        lambda: ({"avx2", "sse4_1"}, "CPU cũ"))
    monkeypatch.setattr(mod, "_flags_from_proc_cpuinfo", lambda: (set(), ""))
    assert mod.detect_cpu().default_precision() == "fp32"


def test_nhanh_du_phong_may_yeu():
    """T1.4: RTF fp32 > 1,5 -> báo rõ máy yếu + đề xuất Nano (không implement Nano)."""
    from hpvoice.engines.cpu_detect import weak_machine_advice

    assert weak_machine_advice(0.8) == ""
    assert "chấp nhận" in weak_machine_advice(1.2)
    advice = weak_machine_advice(1.9)
    assert "máy yếu" in advice and "Nano" in advice
    assert "chưa có ở v1" in advice


def _measure_rtf(engine, repeats=2):
    """Đo RTF thật: 1 warmup + N lần infer, trả (rtf_values, load_seconds)."""
    warm = engine.synthesize(SHORT_TEXT, VOICE)
    assert warm.duration_s > 0
    values = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        result = engine.synthesize(SHORT_TEXT, VOICE)
        values.append((time.perf_counter() - t0) / result.duration_s)
    return values


def test_t14_t17_do_rtf_fp32_va_int8_that():
    """T1.4 + T1.7: đo RTF fp32/int8 thật + thời gian load, ghi rõ model CPU.

    Assert: RTF là số hữu hạn > 0, load < 120 s, int8 không chậm hơn fp32 quá
    nhiều (cùng câu, cùng VM). KHÔNG assert RTF <= 1 (VM chậm hơn real-time;
    ngưỡng mượt đo lại trên máy Windows thật — C6).
    """
    from hpvoice.engines.cpu_detect import detect_cpu, weak_machine_advice

    cpu = detect_cpu()
    report = {
        "cpu_model": cpu.model,
        "has_avx512_vnni": cpu.has_avx512_vnni,
        "has_avx_vnni": cpu.has_avx_vnni,
        "vnni_source": cpu.source,
        "default_precision": cpu.default_precision(),
        "precisions": {},
    }
    for precision in ("fp32", "int8"):
        t0 = time.perf_counter()
        with engine_context(precision) as engine:
            load_s = time.perf_counter() - t0
            # load_seconds của engine đo từ lúc ensure_loaded (chính xác hơn).
            load_s = engine.load_seconds or load_s
            values = _measure_rtf(engine, repeats=2)
        assert load_s < 120, f"Load {precision} quá chậm: {load_s}s"
        assert all(0 < v < 100 for v in values)
        report["precisions"][precision] = {
            "load_seconds": round(load_s, 1),
            "rtf_values": [round(v, 3) for v in values],
            "rtf_mean": round(statistics.mean(values), 3),
        }
    fp32_mean = report["precisions"]["fp32"]["rtf_mean"]
    report["weak_machine_advice"] = weak_machine_advice(fp32_mean)
    (EVIDENCE_DIR / "rtf.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nRTF thật trên VM này: " + json.dumps(report, ensure_ascii=False))
    # int8 phải nhanh hơn hoặc tương đương fp32 trên CPU có VNNI (không tệ hơn 1,5x).
    int8_mean = report["precisions"]["int8"]["rtf_mean"]
    assert int8_mean <= fp32_mean * 1.5, f"int8 ({int8_mean}) chậm bất thường so với fp32 ({fp32_mean})"
