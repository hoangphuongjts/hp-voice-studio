"""Test tải model + kiểm chứng offline (TK1.3) — T1.1.

- Unit test (không cần mạng/model): manifest phát hiện file hỏng, repair chỉ
  xóa file hỏng.
- Integration test (model đã cache): download script --verify-only pass trên
  cache thật; subprocess HF_HUB_OFFLINE=1 nạp engine + tạo WAV mới (offline
  hoàn toàn).
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_DIR = Path(__file__).resolve().parent.parent
REPORT = REPO_DIR / "evidence" / "tk1-engine" / "model-download.json"


def _run_download_script(*args, env_extra=None, timeout=600):
    env = dict(os.environ)
    env.pop("HF_HUB_OFFLINE", None)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, str(REPO_DIR / "scripts" / "download_model.py"), *args],
        capture_output=True, text=True, timeout=timeout, cwd=str(REPO_DIR), env=env,
    )


def test_download_script_tai_du_thanh_phan_va_ghi_manifest():
    """T1.1: script tải đủ 5 thành phần, ghi manifest + dung lượng thật từng cái."""
    result = _run_download_script("--report", str(REPORT))
    assert result.returncode == 0, result.stdout + result.stderr
    assert REPORT.is_file()
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    names = set(report["components"])
    assert names == {"backbone-fp32", "backbone-int8", "denoiser-root",
                     "tokenizer", "codec-onnx"}, names
    for name, comp in report["components"].items():
        assert comp["size_bytes"] > 0, name
        assert comp["files"] > 0, name
        assert comp["manifest"], name  # có SHA-256 từng file
    assert report["total_size_mb"] > 500  # riêng backbone fp32 đã ~475 MB
    print("\n" + json.dumps(
        {n: {"MB": c["size_mb"], "s": c["seconds"], "files": c["files"]}
         for n, c in report["components"].items()},
        ensure_ascii=False, indent=2))


def test_verify_only_pass_tren_cache_that():
    """T1.1: --verify-only pass khi cache nguyên vẹn (không tải lại)."""
    result = _run_download_script("--verify-only", "--report", str(REPORT))
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["checked"] > 0


def test_manifest_phat_hien_file_hong(tmp_path):
    """TK1.3: checksum phát hiện cache hỏng (đổi 1 byte -> verify báo corrupt)."""
    sys.path.insert(0, str(REPO_DIR / "scripts"))
    import download_model

    good = tmp_path / "a.bin"
    good.write_bytes(b"hello-model-bytes")
    manifest_path = tmp_path / "manifest.json"
    snap = tmp_path
    manifest_path.write_text(json.dumps({
        "components": {
            "fake-comp": {
                "local_dir": str(snap),
                "manifest": {"a.bin": {
                    "size": len(b"hello-model-bytes"),
                    "sha256": download_model.sha256_file(good),
                }},
            }
        },
    }), encoding="utf-8")
    assert download_model.verify_manifest(manifest_path)["ok"] is True
    good.write_bytes(b"hello-model-bytex")  # hỏng 1 byte
    result = download_model.verify_manifest(manifest_path)
    assert result["ok"] is False
    assert result["problems"][0]["issue"] == "corrupt"
    assert result["problems"][0]["file"] == "a.bin"


def test_repair_chi_xoa_file_hong(tmp_path):
    """TK1.3: repair chỉ xóa file hỏng, file lành còn nguyên."""
    sys.path.insert(0, str(REPO_DIR / "scripts"))
    import download_model

    good = tmp_path / "good.bin"
    bad = tmp_path / "bad.bin"
    good.write_bytes(b"good-bytes")
    bad.write_bytes(b"bad-bytes")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({
        "components": {
            "fake-comp": {
                "local_dir": str(tmp_path),
                "manifest": {
                    "good.bin": {"size": 10,
                                 "sha256": download_model.sha256_file(good)},
                    "bad.bin": {"size": 9,
                                "sha256": "0" * 64},  # sai checksum cố ý
                },
            }
        },
    }), encoding="utf-8")
    result = download_model.verify_manifest(manifest_path)
    assert result["ok"] is False
    repaired = download_model.repair_problems(result["problems"], manifest_path)
    assert repaired == ["fake-comp/bad.bin"]
    assert good.is_file()
    assert not bad.exists()


def test_offline_hoan_toan_tao_wav_moi(tmp_path):
    """T1.1 (offline): HF_HUB_OFFLINE=1, nạp engine + tạo WAV mới, không gọi HF."""
    code = (
        "import sys; sys.path.insert(0, 'src')\n"
        "from hpvoice.engines import V3Engine\n"
        "e = V3Engine(precision='fp32')\n"
        "e.ensure_loaded()\n"
        "r = e.synthesize('Kiểm tra offline hoàn toàn.', 'Hải Đăng')\n"
        "assert r.sample_rate == 48000 and len(r.samples) > 0\n"
        "e.save_wav(r, sys.argv[1])\n"
        "print('OFFLINE OK', r.duration_s)\n"
    )
    wav_path = tmp_path / "offline.wav"
    env = dict(os.environ)
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    result = subprocess.run(
        [sys.executable, "-c", code, str(wav_path)],
        capture_output=True, text=True, timeout=600, cwd=str(REPO_DIR), env=env,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert wav_path.is_file() and wav_path.stat().st_size > 1000
    assert "OFFLINE OK" in result.stdout
