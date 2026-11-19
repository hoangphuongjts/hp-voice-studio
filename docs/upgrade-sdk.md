# Quy trình nâng cấp SDK (TK4.5, SPEC TH-11/TH-15)

> Nâng SDK **theo đợt, không nâng lặng lẽ**. Mọi lần nâng phải có lý do,
> test tương thích chạy lại đầy đủ, và ghi lại model revision mới.
> Ngày viết: 19/11/2026 · SDK đang ghim: `vieneu==3.8.4`.

## 1. Version đang ghim (không đổi nếu không có lý do)

| Thành phần | Ghim hiện tại | Ghi chú |
|---|---|---|
| SDK `vieneu` | `==3.8.4` | `requirements.txt`; mọi gọi SDK đi qua `V3Engine` (ADR-03) |
| `imageio-ffmpeg` | `==0.8.1` | Chỉ làm downloader/locator binary FFmpeg; KHÔNG collect binary vào bộ cài (Q21) |
| `keyring` | `==25.7.0` | Lưu key V4; PyInstaller phải `--collect-all keyring` (entry points backend) |
| `py-cpuinfo` | `==9.0.0` | Phát hiện VNNI — cờ đúng là `avx512vnni` (không gạch dưới) + AVX-VNNI qua CPUID leaf 7.1 |
| `PyMuPDF` | `==1.28.2` | Dòng 1.x mới nhất 19/11/2026; tránh dòng 2.x chưa kiểm chứng |
| `python-docx` | `==1.2.0` | Đọc file DOCX |
| `fastapi` / `uvicorn` | `==0.165.0` / `==0.54.0` | API local |
| Model backbone | `pnnbao-ump/VieNeu-TTS-v3-Turbo`, subfolder `onnx_update`/`onnx_int8` | Revision HF đã đo: snapshot `61b85e3d937fbbacb387714180e8182823512523` |

## 2. Checklist nâng cấp (chạy đủ từng bước, theo thứ tự)

### Bước 1 — Theo dõi release upstream (mỗi quý)

- [ ] Đọc release notes upstream: repo `pnnbao97/VieNeu-TTS`
  (GitHub) + model card HF `pnnbao-ump/VieNeu-TTS-v3-Turbo` + PyPI
  `vieneu`.
- [ ] Ghi lại: version mới, thay đổi chữ ký hàm (`infer`, `infer_batch`,
  `infer_stream`, `add_voice`, `list_preset_voices`), subfolder model
  mới (`onnx_update`/`onnx_int8`/…), giọng preset thêm/bớt/đổi tên,
  thay đổi license (model card / `voices_v3_turbo.json`).
- [ ] Đánh giá: bản mới có sửa lỗi nghiêm trọng / tính năng v1 cần
  không? Nếu không thì **giữ nguyên bản ghim** — không nâng vì "có bản
  mới".

### Bước 2 — Quyết định nâng (ghi lý do)

- [ ] Lý do nâng ghi rõ (VD: sửa lỗi X, thêm giọng Y, vá bảo mật Z) +
  người chốt + ngày. Không nâng lặng lẽ, không nâng "cho mới".
- [ ] Nếu upstream **bỏ rơi v3 / xoá repo** (TH-15): chuyển sang phương
  án mirror (mục 4) trước khi nâng — không nâng lên bản không còn nguồn
  tải model.

### Bước 3 — Nâng trong nhánh riêng, ghim version mới

- [ ] Tạo nhánh `upgrade/vieneu-<version>` (không nâng thẳng trên
  `build/v1`/`main`).
- [ ] Đổi số ghim trong `requirements.txt` (`vieneu==<mới>`) + ghi
  model revision HF mới vào `README.md` + `docs/model-download.md`.
- [ ] Cài mới vào `.venv` sạch (`pip install -r requirements.txt`)
  rồi chạy `scripts/download_model.py --verify-only` để kiểm tra cache
  model còn hợp lệ với bản mới.

### Bước 4 — Test tương thích (bắt buộc, PASS 100% mới chốt)

- [ ] `TMPDIR=$PWD/.tmp-test .venv/bin/python -m pytest tests/ -q`
  — toàn bộ suite phải PASS (đặc biệt `tests/test_v3_engine.py`,
  `tests/test_api_tts.py`, `tests/test_ffmpeg_manager.py`).
- [ ] `node --check ui/*.js` — UI không đổi nhưng chạy lại cho đủ bộ.
- [ ] Kiểm lại **danh sách 25 giọng** (T1.3): `list_preset_voices()`
  đếm đúng số giọng, đủ 10 featured ⭐, default "Hải Đăng" — nâng SDK
  thì kiểm lại danh sách giọng vì dữ liệu giọng đi theo SDK version.
- [ ] Tạo WAV thật giọng preset (T1.2) + nghe đối chiếu với bản cũ;
  đo RTF fp32/int8 lại (T1.4) + kiểm precision tự chọn theo VNNI.
- [ ] Kiểm tra `infer()`/`infer_batch()`/`infer_stream()` còn đúng chữ
  ký (không tham số mới bắt buộc, `style` vẫn deprecated/bị bỏ qua).
- [ ] Kiểm tra đường offline: `HF_HUB_OFFLINE=1` nạp engine + tạo WAV
  mới được (T1.1).
- [ ] Nếu có thay đổi API SDK: chỉ sửa adapter `V3Engine` (ADR-03),
  không sửa UI/API gọi trực tiếp SDK.

### Bước 5 — Ghi lại + phát hành

- [ ] Cập nhật `README.md` (version SDK + model revision + số đo RTF
  mới nếu đổi), `docs/model-download.md` (dung lượng + manifest SHA-256
  mới), `docs/cpu-reference.md` (nếu RTF đổi).
- [ ] Ghi evidence vào `evidence/upgrade-sdk-<version>/` (log pytest +
  WAV mẫu + `model-download.json` mới).
- [ ] Merge nhánh nâng cấp vào `main` theo quy tắc Git của team
  (commit + push + merge sau khi test ổn định).
- [ ] Cập nhật `NOTICE` nếu license upstream/model card đổi.

## 3. Trường hợp nâng làm vỡ API (không tương thích ngược)

- Giữ bản ghim cũ cho tới khi adapter `V3Engine` sửa xong; không phát
  hành bản nâng nửa vời.
- Nếu SDK mới đổi tên subfolder model / đổi format giọng: cập nhật
  `scripts/download_model.py` + `V3Engine` + manifest checksum cùng lúc,
  đo lại dung lượng từng thành phần (TK1.3) rồi mới chốt.

## 4. Mirror model + checksum (TH-15 — phòng khi HF không với tới được)

- Mirror: `scripts/download_model.py` lưu manifest SHA-256 từng file
  model (`evidence/tk1-engine/model-download.json`); hỗ trợ nguồn dự
  phòng (mirror HF hoặc file model đóng gói sẵn trong bộ cài — quyết ở
  Q2 §15). Khi nâng SDK: tải model mới về mirror, tính lại checksum,
  lưu manifest mới trước khi đổi ghim.
- Kiểm tra định kỳ: `scripts/download_model.py --verify-only` (không
  mạng, không tải) — file nào `corrupt` thì `--repair` chỉ tải lại
  file đó.
- Nếu HF bị chặn/chậm trên mạng nhà anh (C10): đo tốc độ tải trước khi
  chốt "tải lần đầu" hay "đóng gói sẵn model" (TH-02/TH-15).

## 5. Nâng các dependency khác (cùng nguyên tắc)

- `imageio-ffmpeg`: nâng thì **đo lại binary** (`-buildconf` kiểm GPL
  v3 còn đúng không + `sha256sum` binary mới) rồi ghim checksum mới vào
  `PINNED_FFMPEG_SHA256` trong `src/hpvoice/audio/ffmpeg_manager.py`
  (TK4.9) — Windows/macOS cũng đo rồi ghim khi có máy đo.
- `keyring`/`py-cpuinfo`/`fastapi`: nâng theo cùng checklist (test
  tương thích + ghi lý do); riêng `keyring` phải kiểm lại backend entry
  points trong bản đóng gói PyInstaller (`--collect-all keyring`).
- Không nâng `numpy`/`onnxruntime`/`librosa` vượt khỏi dải tương thích
  của SDK `vieneu` trừ khi SDK yêu cầu.
