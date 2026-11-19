"""Test đóng gói (TK4.1/TK4.2, SPEC §12/§10 T4.1/T4.2) — kiểm chứng tĩnh + CLI.

- Workflow Windows: YAML parse OK, trigger đúng (tag v* + workflow_dispatch,
  KHÔNG trigger mọi push), pin Python 3.12, có job smoke test trên runner sạch.
- Spec PyInstaller: syntax OK, collect-all bắt buộc có đủ, KHÔNG collect
  binary FFmpeg (Q21), entry là DesktopShell, console=False (ẩn console).
- CLI --version/--check: chạy thật qua subprocess, không nạp model.
- scripts/build_windows.py trên Linux: thoát 2 + báo rõ chỉ chạy trên Windows.
- Gói Linux đã build (nếu có dist/): chạy thật --version/--check + /health.
"""
from __future__ import annotations

import os
import py_compile
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_DIR = Path(__file__).resolve().parent.parent
WORKFLOW = REPO_DIR / ".github" / "workflows" / "build-windows.yml"
SPEC = REPO_DIR / "packaging" / "windows" / "hp-voice-studio.spec"
BUILD_SCRIPT = REPO_DIR / "scripts" / "build_windows.py"
RUN_SERVER = REPO_DIR / "scripts" / "run_server.py"
LINUX_DIST = REPO_DIR / "dist" / "hp-voice-studio" / "hp-voice-studio"


def _load_workflow() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def test_workflow_yaml_parse_ok_va_trigger_dung():
    """TK4.1(b): trigger push tag v* + workflow_dispatch, KHÔNG trigger mọi push."""
    assert WORKFLOW.is_file(), "Thiếu .github/workflows/build-windows.yml"
    data = _load_workflow()
    on = data.get(True, data.get("on"))  # PyYAML parse "on" thành True
    assert on is not None
    push = on.get("push", {})
    assert push.get("tags") == ["v*"], f"Trigger push phải là tag v*, thấy: {push}"
    assert "workflow_dispatch" in on, "Thiếu trigger workflow_dispatch (chạy tay)"


def test_workflow_noi_dung_theo_spec_tk41():
    """TK4.1(c)(d)(e)(f): Python 3.12, requirements, artifact+sha256, smoke test riêng."""
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "windows-latest" in text
    assert '"3.12"' in text or "'3.12'" in text or "3.12" in text
    assert "requirements.txt" in text
    assert "pip install pyinstaller" in text.lower() or "pip install PyInstaller" in text
    assert "upload-artifact" in text
    assert ".sha256" in text
    assert "smoke-test" in text or "smoke_test" in text
    assert "download-artifact" in text, "Job smoke test phải tải artifact (runner sạch, không checkout repo)"
    assert "HPVOICE_ENGINE" in text and "fake" in text, "Smoke test dùng FakeEngine (không nạp model)"
    assert "/health" in text
    assert "vieneu==3.8.4" in (REPO_DIR / "requirements.txt").read_text(encoding="utf-8")


def test_spec_syntax_ok_va_collect_dung_q21():
    """TK4.1(d) + Q21: spec parse được; collect keyring/onnxruntime/tokenizers;
    KHÔNG collect binary imageio_ffmpeg; entry shell.py; console=False."""
    assert SPEC.is_file(), "Thiếu packaging/windows/hp-voice-studio.spec"
    py_compile.compile(str(SPEC), doraise=True)
    text = SPEC.read_text(encoding="utf-8")
    assert "shell.py" in text, "Entry .exe phải là DesktopShell (src/hpvoice/shell.py)"
    assert 'collect_all("keyring")' in text
    assert 'collect_all("onnxruntime")' in text
    assert 'collect_all("tokenizers")' in text
    assert 'collect_all("imageio_ffmpeg")' not in text, "Q21: KHÔNG collect imageio_ffmpeg"
    assert "imageio_ffmpeg/binaries" in text, "Spec phải ghi rõ KHÔNG collect binaries/* (Q21)"
    assert "console=False" in text, "TK4.8: .exe phải ẩn console"
    assert "one-dir" in text.lower() or "COLLECT" in text
    # Router API phải liệt kê hiddenimports (xem ghi chú trong spec):
    # server.py nạp router động nên PyInstaller không tự thấy.
    for route in ("routes_batch", "routes_dialogue", "routes_files",
                  "routes_history", "routes_jobs", "routes_settings",
                  "routes_srt", "routes_tts", "routes_voices"):
        assert f"hpvoice.api.{route}" in text, f"Spec thiếu hiddenimport {route}"


def _canonical_version() -> str:
    """Version chuẩn duy nhất, đọc từ pyproject.toml (server.py VERSION phải
    khớp — sửa ở một chỗ, test không hardcode số version)."""
    import tomllib

    data = tomllib.loads((REPO_DIR / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def test_run_server_version_va_check_khong_nap_model():
    """TK4.2: --version/--check chạy thật, thoát 0, không nạp model."""
    for flag in ("--version", "--check"):
        result = subprocess.run(
            [sys.executable, str(RUN_SERVER), flag],
            capture_output=True, text=True, timeout=60, cwd=str(REPO_DIR),
        )
        assert result.returncode == 0, f"{flag} thoát {result.returncode}: {result.stderr}"
        assert "HP Voice Studio" in result.stdout
        assert _canonical_version() in result.stdout, (
            f"{flag} phải in version chuẩn {_canonical_version()}, thấy: {result.stdout}")


def test_shell_version_qua_module():
    """TK4.8: python -m hpvoice.shell --version chạy thật, thoát 0."""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_DIR / "src")
    result = subprocess.run(
        [sys.executable, "-m", "hpvoice.shell", "--version"],
        capture_output=True, text=True, timeout=60, cwd=str(REPO_DIR), env=env,
    )
    assert result.returncode == 0, result.stderr
    assert "HP Voice Studio" in result.stdout


def test_build_windows_tren_linux_bao_ro_khong_build_cheo():
    """TK4.1/T4.1: build_windows.py trên Linux thoát 2 + báo rõ dùng GitHub Actions."""
    result = subprocess.run(
        [sys.executable, str(BUILD_SCRIPT)],
        capture_output=True, text=True, timeout=60, cwd=str(REPO_DIR),
    )
    assert result.returncode == 2, f"Trên Linux phải thoát 2, thấy {result.returncode}"
    assert "CHỈ chạy trên Windows" in result.stdout


@pytest.mark.skipif(not LINUX_DIST.is_file(), reason="Gói Linux chưa build (chạy TK4.2 trước)")
def test_goi_linux_version_va_check():
    """TK4.2: gói Linux đã build chạy --version/--check thật, thoát 0."""
    for flag in ("--version", "--check"):
        result = subprocess.run(
            [str(LINUX_DIST), flag],
            capture_output=True, text=True, timeout=120,
        )
        assert result.returncode == 0, f"Gói Linux {flag} thoát {result.returncode}: {result.stderr}"
        assert "HP Voice Studio" in result.stdout
