#!/usr/bin/env python3
"""Tải model v3 Turbo lần đầu, theo từng thành phần (TK1.3, SPEC §2.2/§10 T1.1).

Thành phần (đo dung lượng + thời gian thật từng cái):
  1. backbone-fp32  — repo pnnbao-ump/VieNeu-TTS-v3-Turbo, subfolder onnx_update
  2. backbone-int8  — cùng repo, subfolder onnx_int8
  3. denoiser-root  — cùng repo, file gốc: denoiser.onnx, config.json,
                      voices_v3_turbo.json (speaker-encoder/denoiser + giọng)
  4. tokenizer      — repo OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano
  5. codec-onnx     — repo OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX

- Resume khi tải dở: ``huggingface_hub`` tự tiếp tục file tải dở (resume_download).
- Checksum phát hiện cache hỏng: manifest SHA-256 từng file; ``--verify-only``
  kiểm tra manifest, ``--repair`` chỉ tải lại file hỏng (xóa blob hỏng rồi tải lại).
- Kiểm chứng offline hoàn toàn: chạy với ``HF_HUB_OFFLINE=1`` rồi tạo WAV mới
  (xem tests/test_model_download.py — script này chỉ lo phần tải + kiểm tra file).

Chạy:  .venv/bin/python scripts/download_model.py [--verify-only] [--repair]
        [--report evidence/tk1-engine/model-download.json]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_DIR / "src"))

BACKBONE_REPO = "pnnbao-ump/VieNeu-TTS-v3-Turbo"
TOKENIZER_REPO = "OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano"
CODEC_REPO = "OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX"

# Mỗi thành phần: (tên, repo, allow_patterns). None = toàn bộ repo.
COMPONENTS: list[tuple[str, str, list[str] | None]] = [
    ("backbone-fp32", BACKBONE_REPO, ["onnx_update/*"]),
    ("backbone-int8", BACKBONE_REPO, ["onnx_int8/*"]),
    ("denoiser-root", BACKBONE_REPO, ["denoiser.onnx", "config.json", "voices_v3_turbo.json"]),
    ("tokenizer", TOKENIZER_REPO, None),
    ("codec-onnx", CODEC_REPO, None),
]

DEFAULT_REPORT = REPO_DIR / "evidence" / "tk1-engine" / "model-download.json"


def hf_cache_dir() -> Path:
    """Thư mục cache Hugging Face (tôn trọng HF_HOME)."""
    import os

    home = os.environ.get("HF_HOME") or os.environ.get("HF_HUB_CACHE")
    if home:
        return Path(home)
    return Path.home() / ".cache" / "huggingface"


def snapshot_files(snapshot_dir: Path) -> list[Path]:
    """Liệt kê file thật trong snapshot (theo symlink tới blob)."""
    files: list[Path] = []
    if not snapshot_dir.is_dir():
        return files
    for path in sorted(snapshot_dir.rglob("*")):
        if path.is_file():
            files.append(path)
    return files


def dir_size_bytes(path: Path) -> int:
    """Tổng dung lượng file trong thư mục (theo symlink, tính kích thước thật)."""
    total = 0
    for file in snapshot_files(path):
        try:
            total += file.stat().st_size
        except OSError:
            pass
    return total


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def build_manifest(snapshot_dir: Path) -> dict[str, dict]:
    """Manifest {đường dẫn tương đối: {size, sha256}} cho snapshot."""
    manifest: dict[str, dict] = {}
    for file in snapshot_files(snapshot_dir):
        rel = str(file.relative_to(snapshot_dir))
        try:
            manifest[rel] = {"size": file.stat().st_size, "sha256": sha256_file(file)}
        except OSError as exc:
            manifest[rel] = {"size": -1, "sha256": "", "error": str(exc)}
    return manifest


def download_component(name: str, repo: str, patterns: list[str] | None) -> dict:
    """Tải một thành phần, đo dung lượng trước/sau + thời gian thật."""
    from huggingface_hub import snapshot_download

    t0 = time.perf_counter()
    local_dir = snapshot_download(
        repo_id=repo,
        allow_patterns=patterns,
        resume_download=True,
    )
    elapsed = time.perf_counter() - t0
    snap = Path(local_dir)
    # Chỉ tính file thuộc thành phần này (theo allow_patterns).
    files = snapshot_files(snap)
    if patterns:
        import fnmatch

        files = [f for f in files if any(
            fnmatch.fnmatch(str(f.relative_to(snap)), pat) for pat in patterns
        )]
    size = 0
    for file in files:
        try:
            size += file.stat().st_size
        except OSError:
            pass
    return {
        "name": name,
        "repo": repo,
        "patterns": patterns,
        "local_dir": str(snap),
        "files": len(files),
        "size_bytes": size,
        "size_mb": round(size / 1048576, 1),
        "seconds": round(elapsed, 1),
    }


def verify_manifest(manifest_path: Path) -> dict:
    """Kiểm tra cache theo manifest: file nào thiếu/hỏng (sai size hoặc SHA-256)."""
    if not manifest_path.is_file():
        return {"ok": False, "error": f"Chưa có manifest: {manifest_path} (chạy tải trước)."}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    problems: list[dict] = []
    checked = 0
    for comp_name, comp in manifest.get("components", {}).items():
        snap = Path(comp.get("local_dir", ""))
        for rel, expect in comp.get("manifest", {}).items():
            checked += 1
            path = snap / rel
            if not path.is_file():
                problems.append({"component": comp_name, "file": rel, "issue": "missing"})
                continue
            try:
                actual_size = path.stat().st_size
                actual_sha = sha256_file(path)
            except OSError as exc:
                problems.append({"component": comp_name, "file": rel, "issue": str(exc)})
                continue
            if actual_size != expect.get("size") or actual_sha != expect.get("sha256"):
                problems.append({
                    "component": comp_name,
                    "file": rel,
                    "issue": "corrupt",
                    "expected_size": expect.get("size"),
                    "actual_size": actual_size,
                })
    return {"ok": not problems, "checked": checked, "problems": problems}


def repair_problems(problems: list[dict], manifest_path: Path) -> list[str]:
    """Xóa blob hỏng để lần tải sau tải lại đúng file đó (chỉ file hỏng)."""
    repaired: list[str] = []
    for prob in problems:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        comp = manifest.get("components", {}).get(prob["component"], {})
        snap = Path(comp.get("local_dir", ""))
        path = snap / prob["file"]
        try:
            if path.is_symlink():
                target = path.resolve()  # blob thật sau symlink
                if target.is_file():
                    target.unlink()
                path.unlink()
            elif path.is_file():
                path.unlink()  # file thường (test) — xóa thẳng file hỏng
            repaired.append(f'{prob["component"]}/{prob["file"]}')
        except OSError as exc:
            print(f"  Không xóa được {path}: {exc}", flush=True)
    return repaired


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Tải model v3 Turbo theo từng thành phần.")
    parser.add_argument("--verify-only", action="store_true",
                        help="Chỉ kiểm tra cache theo manifest, không tải.")
    parser.add_argument("--repair", action="store_true",
                        help="Xóa file hỏng rồi tải lại chỉ file đó.")
    parser.add_argument("--report", default=str(DEFAULT_REPORT),
                        help="Đường dẫn file JSON báo cáo/manifest.")
    parser.add_argument("--components", nargs="*", default=None,
                        help="Chỉ tải các thành phần này (mặc định: tất cả).")
    args = parser.parse_args(argv)
    report_path = Path(args.report)

    if args.verify_only:
        result = verify_manifest(report_path)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("ok") else 2

    if args.repair:
        result = verify_manifest(report_path)
        if result.get("ok"):
            print("Cache nguyên vẹn — không có gì để sửa.")
            return 0
        repaired = repair_problems(result["problems"], report_path)
        print(f"Đã xóa {len(repaired)} file hỏng, tải lại...")
        for item in repaired:
            print(f"  - {item}")
        # Tải lại các thành phần có file hỏng.
        bad_components = sorted({p["component"] for p in result["problems"]})
        args.components = bad_components

    selected = [c for c in COMPONENTS if args.components is None or c[0] in args.components]
    if not selected:
        print(f"Không có thành phần nào khớp: {args.components}")
        return 2

    # Đọc manifest cũ (nếu có) để giữ lại thành phần không tải lại.
    old: dict = {}
    if report_path.is_file():
        try:
            old = json.loads(report_path.read_text(encoding="utf-8"))
        except Exception:
            old = {}
    report: dict = {
        "components": dict(old.get("components", {})),
        "total_size_mb": 0.0,
        "total_seconds": 0.0,
    }

    from huggingface_hub import snapshot_download  # noqa: F401 (kiểm tra import sớm)

    for name, repo, patterns in selected:
        print(f"[{name}] tải từ {repo} ...", flush=True)
        try:
            info = download_component(name, repo, patterns)
        except Exception as exc:  # noqa: BLE001 - báo rõ lỗi mạng/tải
            print(f"[{name}] LỖI: {exc}", flush=True)
            print("  Kiểm tra mạng rồi chạy lại — file tải dở sẽ được tiếp tục (resume).",
                  flush=True)
            return 1
        snap = Path(info["local_dir"])
        info["manifest"] = build_manifest(snap)
        # Manifest chỉ giữ file thuộc thành phần này.
        if patterns:
            import fnmatch

            info["manifest"] = {
                rel: meta for rel, meta in info["manifest"].items()
                if any(fnmatch.fnmatch(rel, pat) for pat in patterns)
            }
        report["components"][name] = info
        print(f"[{name}] xong: {info['files']} file, {info['size_mb']} MB, "
              f"{info['seconds']}s.", flush=True)

    total_size = sum(c["size_mb"] for c in report["components"].values())
    total_time = sum(c["seconds"] for c in report["components"].values())
    report["total_size_mb"] = round(total_size, 1)
    report["total_seconds"] = round(total_time, 1)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                           encoding="utf-8")
    print(f"Tổng: {report['total_size_mb']} MB trong {report['total_seconds']}s.")
    print(f"Báo cáo + manifest: {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
