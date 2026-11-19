"""Phát hiện VNNI của CPU để chọn precision mặc định cho V3Engine (TK1.4, TH-03).

Phương pháp (SPEC §10 T1.4, sửa R2-Y9):
- AVX-512 VNNI: cờ ``avx512vnni`` của ``py-cpuinfo`` 9.0.0 (không gạch dưới).
- AVX-VNNI: CPUID leaf 7 subleaf 1 EAX bit 4; trên Linux đọc token ``avx_vnni``
  trong ``/proc/cpuinfo`` (kernel đã giải mã CPUID ra token này). ``py-cpuinfo``
  cũng expose cờ ``avx_vnni`` nên dùng chung một nguồn khi có thể.
- Không đọc được cờ nào -> mặc định fp32 (an toàn, không đoán mò).

Quy tắc precision mặc định: có VNNI (dạng nào cũng được) -> int8, ngược lại fp32.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class CpuInfo:
    """Kết quả phát hiện CPU (ghi rõ nguồn từng cờ để đối chiếu)."""

    model: str
    has_avx512_vnni: bool
    has_avx_vnni: bool
    # Nguồn cờ đã đọc được: "py-cpuinfo", "/proc/cpuinfo", hoặc "" (không đọc được).
    source: str

    @property
    def has_vnni(self) -> bool:
        """Có VNNI ở dạng nào cũng được (AVX-512 VNNI hoặc AVX-VNNI)."""
        return self.has_avx512_vnni or self.has_avx_vnni

    def default_precision(self) -> str:
        """Precision mặc định: VNNI -> int8, không có / không đọc được -> fp32."""
        return "int8" if self.has_vnni else "fp32"


def _flags_from_py_cpuinfo() -> tuple[set[str], str]:
    """Đọc cờ CPU qua py-cpuinfo. Trả (tập cờ, tên model). Lỗi -> (set(), '')."""
    try:
        import cpuinfo

        info = cpuinfo.get_cpu_info()
        flags = set(info.get("flags") or [])
        return flags, str(info.get("brand_raw") or "")
    except Exception:
        return set(), ""


def _flags_from_proc_cpuinfo() -> tuple[set[str], str]:
    """Đọc cờ CPU từ /proc/cpuinfo (Linux). Lỗi/không có file -> (set(), '')."""
    try:
        text = open("/proc/cpuinfo", encoding="utf-8", errors="ignore").read()
    except OSError:
        return set(), ""
    flags: set[str] = set()
    model = ""
    for line in text.splitlines():
        if line.startswith("flags") and ":" in line:
            flags.update(line.split(":", 1)[1].split())
        elif line.startswith("model name") and ":" in line and not model:
            model = line.split(":", 1)[1].strip()
    return flags, model


def _cpuid_leaf7_subleaf1_eax_bit4() -> bool | None:
    """Đọc trực tiếp CPUID leaf 7 subleaf 1 EAX bit 4 (AVX-VNNI).

    Python thuần không thực thi được lệnh CPUID nên hàm này dùng ``/proc/cpuinfo``
    làm đại diện trên Linux (kernel đã giải mã đúng bit này thành token
    ``avx_vnni``). Trên Windows dùng py-cpuinfo. Trả None khi không có nguồn nào.
    """
    flags, _ = _flags_from_proc_cpuinfo()
    if flags:
        return "avx_vnni" in flags
    return None


def detect_cpu() -> CpuInfo:
    """Phát hiện CPU + VNNI, gộp py-cpuinfo và /proc/cpuinfo (Linux).

    Ưu tiên py-cpuinfo (chạy cả Windows/Linux); /proc/cpuinfo bổ sung token
    ``avx_vnni`` khi py-cpuinfo thiếu. Không đọc được gì -> cả hai cờ False,
    source "" -> mặc định fp32.
    """
    flags, model = _flags_from_py_cpuinfo()
    source = "py-cpuinfo" if flags else ""
    proc_flags, proc_model = _flags_from_proc_cpuinfo()
    if proc_flags:
        flags = flags | proc_flags
        source = (source + "+/proc/cpuinfo") if source else "/proc/cpuinfo"
    if not model:
        model = proc_model
    has_avx512 = "avx512vnni" in flags or "avx512_vnni" in flags
    has_avx = "avx_vnni" in flags
    if not has_avx:
        direct = _cpuid_leaf7_subleaf1_eax_bit4()
        if direct:
            has_avx = True
    return CpuInfo(
        model=model or "không xác định",
        has_avx512_vnni=has_avx512,
        has_avx_vnni=has_avx,
        source=source,
    )


def default_precision() -> str:
    """Precision mặc định theo CPU máy này (int8 nếu có VNNI, không thì fp32)."""
    return detect_cpu().default_precision()


def weak_machine_advice(rtf_fp32: float) -> str:
    """Nhánh dự phòng khi fp32 RTF > 1 (SPEC T1.4, sửa R2).

    - RTF <= 1: đủ nhanh, không cần cảnh báo.
    - 1 < RTF <= 1,5: chấp nhận chậm, hiện tiến trình khi tạo.
    - RTF > 1,5: máy yếu -> đề xuất v3 Nano cho bản nháp. Nano CHƯA implement
      ở v1 (chỉ báo rõ, không tự chuyển), ghi rõ lý do trong thông báo.
    """
    if rtf_fp32 <= 1.0:
        return ""
    if rtf_fp32 <= 1.5:
        return (
            f"RTF fp32 = {rtf_fp32:.2f} (> 1): máy tạo chậm hơn real-time, "
            "chấp nhận được — app sẽ hiện tiến trình khi tạo."
        )
    return (
        f"RTF fp32 = {rtf_fp32:.2f} (> 1,5): máy yếu cho v3 Turbo. "
        "Đề xuất dùng v3 Nano cho bản nháp (nhẹ hơn, 24 kHz). "
        "Nano chưa có ở v1 — chỉ báo rõ ở đây, không tự chuyển engine."
    )
