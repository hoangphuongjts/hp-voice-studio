#!/usr/bin/env python3
"""Build gói Windows HP Voice Studio bằng PyInstaller (TK4.1, SPEC §12).

CHỈ CHẠY TRÊN WINDOWS — PyInstaller không build chéo Windows từ Linux
(SPEC §10 T4.1). Chạy trên Linux/macOS thì script thoát mã 2 + hướng dẫn
dùng GitHub Actions (xem .github/workflows/build-windows.yml).

Các bước:
1. Kiểm tra Python 3.12 + PyInstaller đã cài (chưa có thì hướng dẫn cài).
2. Chạy ``pyinstaller packaging/windows/hp-voice-studio.spec`` (one-dir,
   entry DesktopShell, console=False).
3. Post-build BẮT BUỘC: copy ``ui/`` ra gốc ``dist/hp-voice-studio/ui``
   (``server.py`` tính UI_DIR = parents[3] của file server = gốc dist;
   ``datas`` của PyInstaller chỉ đặt ui vào ``_internal/`` — thiếu bước
   này là GET / không redirect về /ui/index.html).
4. Kiểm chứng sau build: ``dist/hp-voice-studio/hp-voice-studio.exe
   --version`` và ``--check`` phải in version + thoát 0 (không nạp model);
   kiểm tra KHÔNG có binary FFmpeg trong dist (Q21); ghi ``.sha256`` cho
   toàn bộ file trong dist (để người tải kiểm trước khi cài — TK4.1(e)).

Dùng:  python scripts/build_windows.py [--distpath dist] [--workpath build]
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
SPEC = REPO_DIR / "packaging" / "windows" / "hp-voice-studio.spec"
DIST_NAME = "hp-voice-studio"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_ui_to_dist_root(dist_dir: Path) -> Path:
    """Copy ui/ ra gốc dist (bắt buộc — xem docstring đầu file + spec)."""
    src_ui = REPO_DIR / "ui"
    dest_ui = dist_dir / "ui"
    if dest_ui.is_dir():
        shutil.rmtree(dest_ui)
    shutil.copytree(src_ui, dest_ui)
    return dest_ui


def _check_no_ffmpeg_binary(dist_dir: Path) -> list[Path]:
    """Trả danh sách binary FFmpeg lọt vào dist (Q21 — phải rỗng)."""
    found = []
    for path in dist_dir.rglob("*"):
        name = path.name.lower()
        if "ffmpeg" in name and path.is_file() and path.suffix not in (".py", ".pyc"):
            found.append(path)
    return found


def _write_sha256(dist_dir: Path, out_path: Path) -> int:
    """Ghi sha256 của mọi file trong dist (đường dẫn tương đối, sort)."""
    lines = []
    for path in sorted(p for p in dist_dir.rglob("*") if p.is_file()):
        rel = path.relative_to(dist_dir).as_posix()
        lines.append(f"{_sha256_file(path)}  {rel}\n")
    out_path.write_text("".join(lines), encoding="utf-8")
    return len(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build gói Windows HP Voice Studio.")
    parser.add_argument("--distpath", default="dist", help="Thư mục đích (mặc định: dist).")
    parser.add_argument("--workpath", default="build", help="Thư mục build tạm (mặc định: build).")
    parser.add_argument("--skip-checks", action="store_true",
                        help="Bỏ qua kiểm chứng sau build (chỉ dùng khi debug build).")
    args = parser.parse_args(argv)

    if sys.platform != "win32":
        print(
            "build_windows.py CHỈ chạy trên Windows — PyInstaller không build "
            "chéo Windows từ Linux (SPEC §10 T4.1).\n"
            "Để build Windows: push tag v* lên repo GitHub để workflow "
            ".github/workflows/build-windows.yml chạy trên runner windows-latest, "
            "hoặc chạy script này trên máy Windows của anh."
        )
        return 2

    if sys.version_info[:2] != (3, 12):
        print(f"Cảnh báo: SPEC TK4.1 pin Python 3.12, máy này đang dùng {sys.version.split()[0]}.")

    pyinstaller = shutil.which("pyinstaller")
    if pyinstaller is None:
        print("Chưa có PyInstaller — cài bằng: pip install pyinstaller")
        return 2
    if not SPEC.is_file():
        print(f"Không tìm thấy spec: {SPEC}")
        return 2

    distpath = (REPO_DIR / args.distpath).resolve()
    workpath = (REPO_DIR / args.workpath).resolve()
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--distpath", str(distpath),
        "--workpath", str(workpath),
        str(SPEC),
    ]
    print("Chạy:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=str(REPO_DIR))  # noqa: S603 - lệnh build nội bộ, không input ngoài
    if result.returncode != 0:
        print("PyInstaller build THẤT BẠI.")
        return result.returncode

    dist_dir = distpath / DIST_NAME
    exe = dist_dir / "hp-voice-studio.exe"
    if not exe.is_file():
        print(f"Không tìm thấy .exe sau build: {exe}")
        return 1

    _copy_ui_to_dist_root(dist_dir)
    print(f"Đã copy ui/ ra gốc dist: {dist_dir / 'ui'}")

    if args.skip_checks:
        print("Bỏ qua kiểm chứng sau build (--skip-checks).")
        return 0

    # Kiểm chứng sau build (không nạp model).
    errors: list[str] = []
    for flag in ("--version", "--check"):
        check = subprocess.run([str(exe), flag], capture_output=True, text=True, timeout=120)  # noqa: S603 - .exe vừa build
        print(f"$ hp-voice-studio.exe {flag} -> thoát {check.returncode}: {check.stdout.strip()}")
        if check.returncode != 0:
            errors.append(f"{flag} thoát {check.returncode}: {check.stderr.strip()[:300]}")

    ffmpeg_found = _check_no_ffmpeg_binary(dist_dir)
    if ffmpeg_found:
        errors.append(
            "Q21 VI PHẠM: binary FFmpeg lọt vào dist: "
            + ", ".join(str(p) for p in ffmpeg_found)
        )
    else:
        print("Q21 OK: không có binary FFmpeg trong dist.")

    sha_path = distpath / f"{DIST_NAME}.sha256"
    n_files = _write_sha256(dist_dir, sha_path)
    print(f"Đã ghi SHA-256 cho {n_files} file: {sha_path}")

    total_mb = sum(p.stat().st_size for p in dist_dir.rglob("*") if p.is_file()) / 1024**2
    print(f"Kích thước dist: {total_mb:.1f} MB (ngân sách Q2 ~300–400 MB, chưa tính model tải lần đầu).")

    if errors:
        print("KIỂM CHỨNG SAU BUILD THẤT BẠI:")
        for err in errors:
            print(f"  - {err}")
        return 1
    print("Build Windows OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
