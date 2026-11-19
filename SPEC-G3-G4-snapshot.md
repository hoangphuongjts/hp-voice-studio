# HP Voice Studio — SPEC v1.2 (sửa theo phản biện R2)

> **Trạng thái:** BẢN DRAFT PHÂN TÍCH — khâu to-spec của Bước 0. Chưa code implementation,
> chưa cài SDK, chưa tạo WAV thật. Bản v1.1 đã qua vòng phản biện 2
> (`CRITIQUE-R2.md`, nhánh `critique/r2`, commit `f722c9c`): kết luận **CHƯA ĐẠT** —
> 1 lỗi 🔴 chặn (Y9) + 8 🟡 + 8 💭. Bản v1.2 này sửa theo toàn bộ §7 của báo cáo đó
> (xem Phụ lục B — nhật ký phiên bản); phần phản biện xác nhận đúng được giữ nguyên,
> không viết lại toàn bộ SPEC.
> **Ngày:** 19/11/2026 · **Nhánh:** `spec/v1-r2` (tạo từ `spec/v1-r1`) · **Repo phân tích:** `upstream-vieneu-tts/`
> (clone chỉ đọc của `pnnbao97/VieNeu-TTS`, commit `512de867`, SDK `3.8.4`).
> **Quy tắc đọc:** mỗi khẳng định ghi rõ **DỮ KIỆN** (đọc được từ file thật) /
> **SUY LUẬN** (suy ra từ dữ kiện) / **CHƯA RÕ** (cần kiểm chứng thêm).
> **Quy ước ID (sửa theo 🔴 R3):** test/tiêu chí kiểm chứng ở mục 10 dùng `T…`
> (VD `T2.5` = test clone giọng); ticket công việc ở mục 12 dùng `TK…`
> (VD `TK2.5` = ticket SrtDubber). Hai namespace khác nhau, không được viết tắt
> lẫn — mọi tham chiếu chéo trong SPEC này đã rà lại theo quy ước này.
> **Kỷ luật kiểm chứng:** không tuyên bố gì chưa chạy kiểm chứng; mọi điểm chỉ kiểm
> được trên máy Windows thật của anh nằm riêng ở mục 11 "Chờ kiểm chứng thật".

## 0. Tóm tắt quyết định (đã chốt bởi anh)

| # | Quyết định | Nguồn |
|---|-----------|-------|
| 1 | Build studio TTS tiếng Việt chạy local, dùng cá nhân, **không thương mại trong 2026** | Lệnh 03:31 19/11 |
| 2 | Engine chính: **VieNeu-TTS v3 Turbo** (SDK `vieneu`, Apache 2.0), 25 giọng preset, 48 kHz | Lệnh 03:35 19/11 |
| 3 | **FULL tính năng** (không cắt bản tối thiểu): Phòng thu, Hội thoại/Podcast, Lồng tiếng .srt, Đọc file, Tạo hàng loạt, Bản đã tạo, Cài đặt | Lệnh 03:35 19/11 |
| 4 | **Giữ cấu trúc giao diện studio chuẩn** (VieNeu Desktop + CIT): nhóm tab Tạo / Thư viện / Hệ thống, bố cục phòng thu quen thuộc. Chỉ đổi thương hiệu/nội dung sang HP Voice Studio. KHÔNG copy code, KHÔNG lấy logo/thương hiệu VieNeu hay CIT | Lệnh 03:35 19/11 |
| 5 | **Hai engine:** V3 local (mặc định, miễn phí) + **V4 cloud tùy chọn** qua API chính thức, key do người dùng nhập trong Cài đặt, không hardcode, không commit key; lỗi/chưa có key → fallback V3 + báo rõ lý do | Lệnh 03:34 19/11 |
| 6 | **V4 KHÔNG chạy local được** (độc quyền, không mã nguồn) — không hứa "clone V4 offline", chỉ dùng qua API | Lệnh 03:34 19/11 + README upstream |
| 7 | **KHÔNG fork/copy code CIT** — CIT chỉ là tài liệu tham khảo tính năng/cấu trúc | Lệnh 03:31 19/11 |
| 8 | Làm theo Charter v1.1 + full skill theo khâu (grilling → research → to-spec → to-tickets → implement+TDD → review → evidence QA → release gate). Chỉ làm phân tích ở Bước 0, DỪNG sau SPEC | Lệnh 03:33 + 03:37 19/11 |
| 9 | Key V4 thật của anh nằm trong connector `custom.vieneu` (Secure Vault) — **KHÔNG lấy giá trị key đó ra dùng trực tiếp**; app chỉ dùng key do người dùng nhập. Test V4 thì "hỏi Annie trước" | Lệnh 03:34 19/11 |

### Phạm vi v1 (đã chốt)

- Dùng cá nhân trên máy Windows của anh (mục tiêu chính) + chạy được trên Linux (máy Annie) để Annie dùng được; ai khác cũng dùng được (config, không hardcode máy/cổng).
- Local-first: V3 chạy offline hoàn toàn sau lần tải model đầu tiên (cần mạng lần đầu).
- API HTTP local để Annie / MODOLIVIO gọi được.
- Clone giọng **chỉ giọng có phép** (của mình hoặc đã được chủ giọng đồng ý), có cam kết quyền sử dụng.

### Ngoài phạm vi v1 (ghi rõ, không làm ngầm)

- Không Supertonic/Kokoro hay engine giọng nước ngoài (CIT có, HP v1 không — xem ticket dự phòng P2).
- Không trợ lý AI viết kịch bản bằng LLM bên thứ ba (VieNeu Desktop có — HP v1 không).
- Không LoRA fine-tune (upstream có `finetune/`, GPU-only).
- Không phát hành công khai / không thương mại (xem mục 9 — kịch bản thương mại chỉ phân tích + thiết kế sẵn + mốc kích hoạt).

---

## 1. GRILLING — TỬ HUYỆT (lỗi trước, giải pháp sau)

> Theo Charter v1.1 §3: tìm 5–10 vấn đề cốt yếu — điểm mà nếu sai thì toàn bộ
> phương án sụp đổ. Mỗi tử huyệt có **bằng chứng từ file thật** rồi mới tới giải pháp.
> Danh sách này chưa qua phản biện chéo vòng 2 (sẽ do agent khác chất vấn trước khi chốt).

### TH-01 — Mâu thuẫn giấy phép: repo Apache 2.0 nhưng file giọng ghi CC BY-NC "non-commercial use only"

- **DỮ KIỆN:** `LICENSE` của repo là Apache License 2.0 (đã đọc đầu file).
  Nhưng `src/vieneu/assets/voices.json` (file giọng của SDK) có meta:
  `"license": "CC BY-NC 4.0"`, `"notice": "Model and voices are for non-commercial use only.
  Mention pnnbao-ump when using."` — **đã kiểm chứng trực tiếp bằng lệnh đọc file
  trong repo clone ngày 19/11/2026.** File `voices_v3_turbo.json` (25 giọng v3 Turbo dùng
  trong HP) thì meta chỉ ghi note về `featured`/`aliases`, **không ghi license**.
  Nghiên cứu trước (`research_notes/vieneu-studio-clone-2026-11-19.md` §3.2) cũng ghi
  mâu thuẫn này và ngoại lệ GGUF Q4 CC BY-NC 4.0 (báo giá thương mại ~5.000 USD/năm).
- **Vì sao tử huyệt:** nếu sau này thương mại hoá mà license giọng thực tế là CC BY-NC
  thì toàn bộ sản phẩm vi phạm bản quyền — không sửa bằng code được.
- **Giải pháp (thiết kế trong SPEC):** v1 chỉ dùng cá nhân → **hiện không cản trở**
  (khớp quyết định "không thương mại 2026"). Ghi rõ trong SPEC + README + NOTICE:
  code Apache 2.0, giọng v3 Turbo dùng theo meta của `voices_v3_turbo.json`, **không dùng
  bản GGUF Q4**, không phân phối lại file `voices.json` cũ. Mốc kích hoạt thương mại
  (mục 9) bắt buộc: xin xác nhận bằng văn bản từ tác giả về license giọng v3 Turbo
  trước khi bán/chia sẻ rộng. Không được "cứ bán rồi tính".

### TH-02 — Model không có sẵn trong repo: lần chạy đầu phải tải từ Hugging Face, dung lượng v3 Turbo không ghi rõ

- **DỮ KIỆN:** repo clone chỉ 38 MB, không chứa weight. `V3TurboVieNeuTTS.__init__`
  mặc định `backbone_repo="pnnbao-ump/VieNeu-TTS-v3-Turbo"`, tải qua
  `hf_hub_download` trong `src/vieneu/_v3_turbo_engine/onnx_runtime_lite.py`
  (subfolder `onnx_int8` / `onnx_update`) và `hub_load_v3_turbo.py`
  (`model.safetensors`); tokenizer `OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano`.
  Cache mặc định của Hugging Face (`~/.cache/huggingface`, xem `.env.example`:
  `HF_HOME=/root/.cache/huggingface`). README **không ghi tổng dung lượng tải
  của v3 Turbo**. [Sửa R1-Y5] Con số "three cloning graphs, ~110 MB, download
  on first use" (`README.md:334`) nằm trong mục **v3 Nano**, KHÔNG phải của
  Turbo — bản v1.0 gán nhầm cho Turbo, bản này gỡ bỏ. Số của Nano (282 MB tải,
  README) cũng không dùng làm số của Turbo. Tổng dung lượng tải của Turbo
  vẫn **CHƯA RÕ** cho tới khi đo ở Bước 1.
- **Vì sao tử huyệt:** máy không mạng / mạng chặn Hugging Face → app chết ngay lần
  chạy đầu; người dùng tưởng "cài xong dùng ngay" nhưng thực tế phải chờ tải;
  tải dở bị ngắt → cache hỏng → lỗi khó hiểu.
- **Giải pháp:** (a) Bộ cài Windows **đóng gói sẵn model** (như CIT: bộ cài ~367 MB
  kèm model) HOẶC lần chạy đầu có màn hình tải model với tiến trình + thử lại +
  kiểm tra checksum; (b) config cho phép chỉ thư mục model/cache (`HF_HOME`,
  `onnx_dir` — SDK đã hỗ trợ `onnx_dir`/`onnx_repo`); (c) Bước 1 phải đo dung
  lượng tải thật và ghi vào SPEC/README (ticket TK1.3). [Sửa R1-Y5] Đo theo từng
  thành phần riêng (backbone, codec, speaker-encoder/denoiser, tokenizer),
  đo cache HF trước/sau từng bước — không ghi một con số gộp không rõ nguồn.
  [Sửa R1-Y10] "Đóng gói sẵn model" chưa đủ để kết luận chạy offline hoàn toàn:
  `hub_load_v3_turbo.py:26` chỉ kiểm tra thư mục local cho `model.safetensors`,
  còn codec (`_CODEC_REPO = "OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX"`)
  và speaker-encoder/denoiser vẫn tải qua `hf_hub_download`
  (`onnx_runtime_lite.py:90,190,212`). Vì vậy TK1.3 bắt buộc có bước kiểm chứng
  **chặn mạng hoàn toàn sau khi tải model, khởi động lại app, tạo WAV** — chỉ
  pass bước này mới được ghi "chạy offline hoàn toàn"; nếu còn gọi HF thì ghi rõ
  danh sách thành phần còn thiếu vào README và đóng gói kèm.

### TH-03 — CPU yếu là điểm nghẽn hiệu năng: int8 nhanh nhưng đòi VNNI, sai là méo tiếng

- **DỮ KIỆN:** README Benchmarks (máy đo: i5 12th-gen 6 P-core, Win 11, ONNX 1.24):
  v3 Turbo CPU RTF **0,62 (fp32) / 0,37 (int8)**; Nano RTF 0,11–0,22. README cảnh báo:
  "`Vieneu(precision=\"int8\")` ~1,6× faster and ~4× smaller, but it requires a CPU
  with VNNI (AVX-512 VNNI / AVX-VNNI); **on older CPUs int8 can produce garbled audio**."
  CIT đo trên laptop i7-8650U (2017, 4 nhân): 1 phút audio mất ~30 giây tạo; CIT
  khuyên máy yếu giữ Turbo INT8, Nano "không nhanh hơn" trên máy đó. `threads=0`
  mặc định ~số nhân vật lý, cap 8.
  [Sửa R2-Y9] **Mâu thuẫn CIT–README chưa gỡ (ghi rõ, không giấu):** i7-8650U
  (Kaby Lake Refresh, 2017) **không có AVX-512 VNNI lẫn AVX-VNNI** (VNNI chỉ xuất
  hiện từ Ice Lake / thế hệ 10 trở đi) — đúng loại CPU mà README cảnh báo int8
  "can produce garbled audio" — vậy mà CIT lại khuyên "máy yếu giữ Turbo INT8"
  trên chính CPU đó. Hai khả năng: CIT đã đo và thấy chất lượng chấp nhận được
  dù không có VNNI, hoặc int8 trên CPU đó méo nhẹ mà CIT chấp nhận. SPEC **không
  lặp lại lời khuyên của CIT như một khẳng định an toàn** cho tới khi TK1.4 đo
  thật: "méo" được định nghĩa ở đó (nghe đối chiếu int8 vs fp32 trên cùng câu
  mẫu, anh nghe bằng tai + ghi nhận xét; khác biệt rõ ràng → fallback fp32).
- **Vì sao tử huyệt:** máy anh / máy người dùng cuối không rõ CPU; chọn sai precision
  → hoặc chậm không dùng được, hoặc méo tiếng mà tưởng là lỗi giọng.
- **Giải pháp:** tự phát hiện CPU lúc cài/lần chạy đầu (có VNNI → int8, không → fp32)
  + cho đổi trong Cài đặt + ghi rõ trong UI; chunk dài tự chia nhỏ (max 256 ký tự/chunk
  theo SDK) và **ghi audio dần ra đĩa** (như CIT ≥1.0.1) để bài dài không phình RAM;
  mục tiêu hiệu năng v1: RTF ≤ 1 trên CPU máy anh (đo thật ở Bước 1, ticket TK1.4;
  CPU tham chiếu ghi bằng **model cụ thể sau khi đo ở C6**, không để "CPU 4 nhân"
  chung chung trong tiêu chí đạt — i7-8650U và i5-12400 đều "4 nhân" nhưng khác
  nhau rất xa).
  [Sửa R2-Y9 — 🔴, phương pháp phát hiện VNNI viết lại hoàn toàn vì bản v1.1
  **sai tên cờ và thiếu hẳn AVX-VNNI**] Tên cờ đúng của `py-cpuinfo` 9.0.0 là
  **`avx512vnni` (không có gạch dưới)** — đã kiểm chứng bằng file thật
  (`cpuinfo.py:1251`, CPUID leaf 7.0 ECX bit 11: `'avx512vnni' :
  _is_bit_set(ecx, 11)`); bản v1.1 viết `avx512_vnni` / `avx_vnni` là **sai**,
  code làm đúng bản đó sẽ không bao giờ phát hiện được VNNI. Nặng hơn,
  `py-cpuinfo` 9.0.0 **không hề có AVX-VNNI** (grep toàn file chỉ 1 kết quả
  `vnni`, không có code đọc CPUID leaf 7 subleaf 1) — trong khi CPU đo benchmark
  của chính README (i5 12th-gen, Alder Lake) **chỉ có AVX-VNNI, không có AVX-512
  VNNI** (Intel tắt AVX-512 trên Alder Lake): dùng mỗi `py-cpuinfo` thì đúng máy
  này bị kết luận "không có VNNI" → luôn fp32 → bỏ mất lợi ích int8 mà README
  đo được (RTF 0,37). Phương pháp chốt ở v1.2 (cả hai loại VNNI đều tính là
  "có VNNI", đủ điều kiện thử int8):
  (a) AVX-512 VNNI: cờ **`avx512vnni`** của `py-cpuinfo` 9.0.0;
  (b) AVX-VNNI: **CPUID trực tiếp leaf 7, subleaf 1, EAX bit 4** — trên Linux
  đọc dòng `flags` của `/proc/cpuinfo` (token `avx_vnni`; đã kiểm chứng trên máy
  Annie: CPU AMD EPYC hiện token này trong khi `py-cpuinfo` không thấy);
  trên Windows đọc CPUID leaf 7.1 bằng helper `ctypes` riêng của HP (kỹ thuật
  tương tự chính `py-cpuinfo` dùng để chạy CPUID trên Windows: cấp phát mã máy
  qua `VirtualAlloc`/`VirtualProtect` rồi gọi — xem `cpuinfo.py` class `ASM`);
  trên macOS Intel dùng `sysctl machdep.cpu.leaf7_features` (Apple Silicon
  không áp dụng — ngoài mục tiêu v1 Windows + Linux);
  (c) dự phòng thực nghiệm: nếu cả hai nguồn cờ đều không đọc được (VD: máy ảo
  che flags) thì **chạy thử int8 trên một câu mẫu ngắn và đối chiếu với fp32**
  (nghe + so sánh); méo/khác biệt rõ → fp32; không đối chiếu được thì **mặc
  định fp32 an toàn** (chậm nhưng không méo tiếng) và ghi rõ lý do trong log +
  Cài đặt. TK1.4 phải kiểm chứng trên cả ba loại máy (chỉ AVX-512 VNNI, chỉ
  AVX-VNNI, không có VNNI) rằng precision tự chọn là đúng; chỉ kiểm trên một
  loại máy thì chưa đạt.
  [Sửa R2 — nhánh dự phòng khi fp32 cũng chậm] Nếu đo ở C6 ra **fp32 RTF > 1
  trên CPU máy anh** thì không "chấp nhận mù": (1) RTF ≤ 1,5 → chấp nhận chậm,
  hiện tiến trình tạo + ước tính thời gian chờ trong UI; (2) RTF > 1,5 →
  mặc định chuyển sang **v3 Nano** cho bản nháp (RTF 0,11–0,22, 24 kHz, chất
  lượng thấp hơn; Turbo vẫn chọn được tay khi cần chất lượng), ghi rõ trong UI
  lý do chuyển; (3) nếu cả Nano cũng RTF > 1 → báo rõ máy không đủ cho studio
  này + hướng dẫn nâng cấp, không hứa "mượt". Ngưỡng 1,5 và nhánh Nano là
  **SUY LUẬN** chốt ở Bước 1 theo số đo thật, không phải số đo được.

### TH-04 — Clone giọng: SDK không xác minh danh tính, rủi ro giả mạo + pháp lý

- **DỮ KIỆN:** `add_voice(name, ref_audio, ...)` và `infer(..., ref_audio=...)` nhận
  **bất kỳ file audio nào**, không có bước xác minh chủ giọng trong SDK
  (đã đọc `src/vieneu/v3turbo.py:395-434`). CIT giải quyết bằng cam kết: "Chỉ dùng
  giọng của bạn hoặc giọng đã được chủ giọng cho phép… đây là cam kết, không phải
  xác minh danh tính"; CIT giữ tối đa 15 giây, Turbo dùng tối đa 8 giây có tiếng;
  "không gửi về tác giả, không tự sao chép file âm thanh gốc".
  V4 clone giọng chỉ làm được trên web (vieneu.io/#/clone), **không qua API**.
- **Vì sao tử huyệt:** một tính năng clone không rào chắn là cửa cho giả mạo giọng
  người khác (lừa đảo, bôi nhọ) — rủi ro pháp lý và uy tín, không sửa được bằng
  "thêm nút".
- **Giải pháp:** (a) Trước khi lưu giọng clone: màn hình cam kết quyền sử dụng
  (checkbox + ghi log cam kết kèm thời gian, lưu cùng giọng, xoá cùng nhau);
  (b) Chỉ nhận clip 3–8 s, 1 người nói, không nhạc nền (validate độ dài + SNR cơ bản);
  (c) Watermark mặc định bật khi có thể (xem TH-09); (d) Giọng clone lưu **local**,
  không đồng bộ cloud, không xuất file ref gốc; (e) Khi đăng tải nội dung mô phỏng
  giọng người thật phải ghi rõ "giọng đọc được tạo bằng AI" (theo CIT §Sử dụng có
  trách nhiệm). Không có ngoại lệ "cho nhanh". [Sửa R1-TH-17] Cam kết là lời hứa,
  không phải xác minh — SPEC thừa nhận điều này. Bổ sung: (f) cơ chế gỡ giọng khi
  bị khiếu nại (xoá giọng + cam kết kèm theo, ghi log gỡ); (g) ghi chú pháp lý
  trong UI/Cài đặt: giọng nói là dữ liệu cá nhân theo Nghị định 13/2023, nội dung
  AI phải ghi nhãn theo Nghị định 147/2024; (h) câu hỏi mở Q13 (§15): có giới hạn
  v1 chỉ cho clone bằng thu micro trực tiếp (khó giả mạo hơn upload file lạ)
  hay không — chưa chốt, cần anh quyết.

### TH-05 — V4 độc quyền, cloud-only, tính phí theo ký tự: key lộ / hết quota / cloud lỗi là mất engine

- **DỮ KIỆN:** README upstream: "v4 is proprietary and will not be open-sourced…
  available exclusively through the VieNeu API / vieneu.io." Connector
  `custom.vieneu/CONNECTOR.md` (đã kiểm chứng 19/11 với key thật của anh):
  base `https://api.vieneu.io/api/v1`, auth `Bearer vn_sk_...`, engine **v4 only**
  (v3 đã retired khỏi Cloud API 24/09/2026), **billing per submitted character**,
  707 giọng (`GET /v1/audio/voices?engine=v4`), voice id là **tên hiển thị tiếng Việt**
  (VD "Hạ Vy") — khác hẳn 25 tên preset V3; test thật ra WAV PCM 16-bit 48 kHz mono
  2,91 s. Voice cloning **web-only**, không qua API. Giá gói token (trang chủ, theo
  nghiên cứu 18/11): Starter 99Kđ ~4 giờ/400.000 token/6 tháng … Studio 1,69Mđ
  ~105 giờ/12.000.000 token/12 tháng — **cần đọc lại khi tới mốc thương mại**.
- **Vì sao tử huyệt:** V4 là đường trả phí + phụ thuộc mạng + phụ thuộc nhà cung cấp;
  key lộ = người khác đốt tiền của anh; hết token giữa chừng = job dở dang; cloud lỗi
  = studio "chết" nếu thiết kế coi V4 là mặc định.
- **Giải pháp:** (a) V3 local là mặc định, V4 **mặc định TẮT**; (b) key V4 do người
  dùng nhập trong Cài đặt, lưu trong store riêng của app (file cấu hình local, quyền
  hạn chế), **không hardcode, không commit git, không log**; [Sửa R1-Y12] "quyền
  hạn chế" kiểu `chmod 0700` là khái niệm Unix, không có nghĩa trên Windows (nền
  tảng mục tiêu chính). Cơ chế chốt cho Windows: lưu key bằng **DPAPI qua thư viện
  `keyring`** (Windows Credential Manager) — key không nằm dạng plaintext trong
  file; trên Linux dùng `keyring` (Secret Service) hoặc file `secrets.json` với
  quyền `0600` khi không có keyring. [Sửa R2-Y12] Trong app đóng gói PyInstaller,
  `keyring` tìm backend qua **entry points** (`[keyring.backends]` trong
  `entry_points.txt` — đã kiểm chứng trên `keyring` 25.7.0 thật); metadata này
  thường không được đóng gói theo mặc định → phải `--collect-all keyring` (xem
  TK4.1) hoặc khởi tạo backend trực tiếp (`WinVaultKeyring` trên Windows);
  backend Windows cần `pywin32-ctypes` trong bản đóng gói (dependency theo
  platform của `keyring` 25.7.0). Luân chuyển/thu hồi: Cài đặt có nút "Xoá key"
  (xoá khỏi store + ghi log đã xoá, không log giá trị key). Kiểm tra key hợp lệ
  mà không đốt ký tự: [Sửa R2-Y12/Q14 — ĐÃ TRẢ LỜI] dùng **`GET /v1/balance`**
  (OpenAPI chính thức, operation `getBalance` — TỒN TẠI, không còn "CHƯA RÕ"):
  vừa ping key (401 = key sai) vừa lấy số dư cho màn hình quota; bỏ ứng viên cũ
  `GET /v1/audio/voices` làm ping key (xem C13 §11). (c) UI hiển thị rõ
  "V4 tính phí theo ký tự" + ước tính ký tự trước khi gửi + cảnh báo khi vượt ngưỡng
  do người dùng đặt; [Sửa R2-V4] ước tính phí tính theo công thức thật
  **ký tự (tối thiểu 50/request) × engine `billingMultiplier` ×
  `globalMultiplier`** (lấy từ `GET /v1/engines`, VD multiplier v4 = 3,4) —
  không đếm ký tự trần như v1.1; lưu ý: `warn_chars` trong config là **ký tự**,
  không phải token, và 100.000 ký tự ≠ 100.000 token khi multiplier ≠ 1.
  (d) **fallback tự động về V3** khi chưa có key / 401-403 / timeout /
  5xx / hết quota, và **báo rõ lý do + giọng mới** (không fallback lặng lẽ —
  xem ánh xạ giọng fallback ở `EngineRouter` §3.3); (e) mọi lỗi V4 ghi log
  kèm mã lỗi, không retry vô hạn (tối đa 1 lần với lỗi 5xx, không retry 4xx).
  [Sửa R2-V4 — `Idempotency-Key` + bảng mã lỗi, theo OpenAPI chính thức
  `https://docs.vieneu.io/openapi.json`, kiểm chứng lại 19/11/2026] (f)
  `V4Engine` sinh **`Idempotency-Key` = UUID theo HP job id cho mọi
  `POST /v1/tts`** (async), lưu key cùng job để retry đúng key; key 8–128 ký tự
  ASCII in được (UUID là lý tưởng), có phạm vi theo API key, nhớ **24 giờ**;
  retry cùng key + cùng body → trả về job **ĐẦU TIÊN** (cùng `jobId`, không tính
  phí lần 2, header `Idempotent-Replayed: true`); 409 `IDEMPOTENCY_IN_FLIGHT`
  → chờ `Retry-After` rồi retry **cùng key, không bao giờ tạo key mới**;
  422 `IDEMPOTENCY_KEY_REUSED` (key dùng lại với body khác) → **báo lỗi lập
  trình, không retry**. (g) **Không retry `POST /v1/audio/speech` sau timeout:**
  endpoint đồng bộ này **không hỗ trợ idempotency** (`parameters: []` trong
  OpenAPI) nên retry sau timeout có thể bị tính phí trùng (trường hợp timeout
  xảy ra sau khi server đã xử lý xong nhưng response chưa về — OpenAPI chỉ hứa
  hoàn tiền khi "synthesis fails", không hứa cho trường hợp timeout mập mờ);
  chỉ retry khi **chưa gửi request đi được** (lỗi kết nối trước khi gửi), hoặc
  chuyển sang đường async `POST /v1/tts` có idempotency. Quy tắc retry này
  thay thế câu "timeout + retry 1 lần (5xx)" của v1.1 ở mọi chỗ. (h) Bảng mã lỗi
  V4 chốt: key sai → **401**, hết quota/hết token → **403** (không phải 402),
  quá tải/rate limit → **429** (kèm `Retry-After` + header `X-RateLimit-*`);
  **402 chỉ xuất hiện ở audiobook** (`POST /v1/audiobooks/{bookId}/start`,
  `insufficient_tokens`) — ngoài phạm vi v1, không dùng làm mã "hết quota" cho
  các endpoint HP dùng. Bản v1.1 tự mâu thuẫn (TH-05 viết "401-403", module
  `V4Engine` viết "401/402/429") — v1.2 thống nhất thành **401/403/429** ở mọi
  chỗ (TH-05, §3.3, T2.6, TK2.2, §9.2).

### TH-06 — API local mở ra LAN là cửa lộ: upstream mặc định mở khi không có key

- **DỮ KIỆN:** `apps/openai_speech.py:492-496`: "Loopback unless told otherwise:
  the API is open when `VIENEU_API_KEY` is unset" — nếu bind khác loopback mà
  không đặt `VIENEU_API_KEY` thì server cảnh báo là ai với tới cổng cũng gọi được.
  Auth: `Authorization: Bearer <key>` qua env `VIENEU_API_KEY` (hmac compare).
  CIT: mặc định chỉ cùng máy gọi được, không cần khoá; bật LAN thì phải có khoá
  `X-API-Key` + chỉ cho gọi API tạo giọng, không xem lịch sử/cài đặt.
- **Vì sao tử huyệt:** HP API phục vụ Annie/MODOLIVIO; nếu mặc định bind `0.0.0.0`
  không khoá thì bất kỳ ai trong mạng LAN cũng tạo giọng / đọc được lịch sử.
- **Giải pháp:** mặc định bind `127.0.0.1` + cổng cấu hình được (không hardcode);
  chế độ LAN là **opt-in** trong Cài đặt, bật LAN bắt buộc sinh khoá API
  (header `X-API-Key`), LAN chỉ mở endpoint tạo giọng, **không mở** lịch sử /
  giọng clone / cài đặt / key V4; log mọi request từ xa.

### TH-07 — Lồng tiếng .srt khớp giờ: SDK không có API SRT, logic căn giờ phải tự viết và dễ sai

- **DỮ KIỆN:** SDK không có hàm SRT. Logic nằm ở app: `apps/srt_speech.py`
  `srt_to_speech(tts, srt_path, voice_id, keep_timing, fmt, stop_requested,
  batch_size=32)` — Gradio generator, dùng `infer_batch` + `lay_on_timeline`
  (xếp clip lên timeline). CIT: câu dài được đọc nhanh cho vừa (tối đa 1,5×),
  vẫn chưa vừa thì lấn khoảng lặng sau hoặc đẩy câu sau lùi, **không bao giờ cắt chữ**,
  kèm file phụ đề đã chỉnh mốc. VieNeu Desktop 0.18.25+: tối đa 2×, giữ cao độ,
  nhận tới 100.000 câu/tệp.
- **Vì sao tử huyệt:** đây là tính năng "phải dùng được" cho video; căn giờ sai
  → audio lệch hình, không sửa được bằng cách "tăng tốc chung" (tốc độ là thuộc
  tính của engine, xem TH-08).
- **Giải pháp:** implement `SrtDubber` riêng: parse SRT (bỏ thẻ `<i>`, `{\an8}`…),
  áp dụng từ điển phát âm, đo độ dài từng câu → tính hệ số tốc độ/câu trong
  [0,75×–1,5×] (giới hạn theo CIT; [Sửa R1-G5] bỏ mức 2×: VieNeu Desktop cho
  tối đa 2× nhưng UI §5 của HP không có chỗ chọn 2×, SPEC chốt **tối đa 1,5×**
  thống nhất mọi chỗ), overflow thì
  lấn khoảng lặng → đẩy câu sau → **báo cáo danh sách câu bị lùi** + xuất SRT đã
  chỉnh mốc; kiểm chứng bằng file WAV + đo độ lệch mốc (test T3.3, mục 10).

### TH-08 — "Tốc độ đọc" không phải tham số của SDK v3 Turbo: chỉnh tốc độ phải làm ở tầng app

- **DỮ KIỆN:** chữ ký `infer()` (đã đọc `src/vieneu/v3turbo.py:600-648`) **không có
  tham số speed/rate** — chỉ có `temperature/top_k/top_p/max_new_frames/
  repetition_penalty/max_chars/silence_p/crossfade_p/apply_watermark/batch_size`.
  `style` đã deprecated và bị bỏ qua. Tốc độ trong app upstream/CIT là xử lý sau
  (resample/time-stretch) hoặc qua tham số của server OpenAI (`speed` bị liệt vào
  `X-VieNeu-Ignored` trong `apps/openai_speech.py`).
- **Vì sao tử huyệt:** nếu SPEC hứa "chỉnh tốc độ 0,75×–1,5×" mà tưởng SDK có sẵn
  thì tới lúc build mới phát hiện phải viết thêm — vỡ tiến độ và chất lượng
  (time-stretch kém làm méo tiếng).
- **Giải pháp:** tầng `AudioPost` riêng: time-stretch giữ cao độ (dùng
  `librosa.effects.time_stretch` — phase vocoder; [Sửa R1-Y4] `soxr` là
  **resample** (đổi tần số lấy mẫu), đổi tốc độ bằng soxr sẽ đổi luôn cao độ
  (giọng chipmunk khi nhanh, trầm khi chậm) nên **không dùng soxr để đổi tốc độ**;
  soxr chỉ dùng khi cần đổi sample rate, VD V4 trả về khác 48 kHz) với dải
  0,75×–1,5×; tốc độ là
  metadata của job, không lẫn vào engine; kiểm chứng bằng đo thời lượng WAV
  trước/sau (ticket TK2.4). [Sửa R1-Y4] TK2.4 đo thêm RTF của bước time-stretch
  (thời gian xử lý / thời lượng audio) và chỉ áp time-stretch khi tốc độ ≠ 1×;
  chất lượng ở biên 1,5× do anh nghe bằng tai và ghi vào C-kiểm chứng (§11).

### TH-09 — Watermark mặc định bật nhưng thực tế thường TẮT: cần quyết chính sách, không để "tưởng có"

- **DỮ KIỆN:** `infer(..., apply_watermark=True)` mặc định True, nhưng
  `BaseVieneuTTS._init_watermarker` chỉ bật được khi cài `resemble-perth`
  (`pip install vieneu[watermark]`, cần torch/torchaudio); nếu không có thì
  `watermarker=None` và audio **không được watermark** (chỉ log debug).
  PyPI package tên `perth` là package khác, không được dùng (issue #191).
- **Vì sao tử huyệt:** tuyên bố "audio có watermark chống giả mạo" trong khi
  bản cài torch-free không watermark được là tuyên bố sai — và TH-04 cần watermark
  làm rào chắn clone.
- **Giải pháp:** v1: **không tuyên bố watermark**; ghi rõ trong SPEC/UI là
  "watermark Perth chỉ có khi cài thêm `vieneu[watermark]` (cần torch)".
  Ticket dự phòng P2: đóng gói watermark như extra tùy chọn + hiển thị trạng thái
  watermark trong Cài đặt (Bật/Tắt/Không khả dụng). Không tự viết watermark riêng.

### TH-10 — Không có "Conversation API" trong SDK: hội thoại nhiều giọng là logic app, dễ vỡ voice-lock

- **DỮ KIỆN:** SDK không có class/hàm Conversation. Hội thoại chỉ tồn tại ở
  `apps/gradio_main.py`: `MAX_SPEAKERS = 8`, `synthesize_conversation` /
  `_synthesize_conversation_v3` — batch **toàn bộ hội thoại ở batch_size 32**,
  mỗi dòng gắn với một giọng; voice lọc theo cờ `podcast=True` trong metadata
  giọng. Yêu cầu của MODOLIVIO (MEMORY.md): mỗi nhân vật **một giọng cố định
  xuyên suốt video và các tập sau**, không trộn giọng.
- **Vì sao tử huyệt:** nếu implement hội thoại bằng cách gọi `infer()` từng dòng
  riêng lẻ mà không khoá giọng theo nhân vật thì giọng sẽ trôi/lẫn giữa các lượt —
  đúng lỗi đã từng xảy ra ở MODOLIVIO (voice anchoring).
- **Giải pháp:** `ConversationEngine` riêng: kịch bản = danh sách (speaker, line);
  **mỗi speaker khoá 1 voice_id cố định** (validate trước khi chạy, báo lỗi nếu
  speaker chưa gán giọng); gom line theo speaker → `infer_batch` → ghép theo
  thứ tự kịch bản với khoảng lặng cấu hình được; lưu mapping speaker→voice vào
  file kịch bản để mở lại vẫn đúng giọng.

### TH-11 — SDK đang phát triển nhanh, CIT ghim bản cũ: trôi phiên bản là vỡ API

- **DỮ KIỆN:** repo đang hoạt động (commit `512de867`, 750 commit, Desktop 0.18.27
  mới phát hành, `Archived: No` — nghiên cứu 18/11). SDK hiện tại **3.8.4**
  (`pyproject.toml`); CIT ghim `vieneu==3.3.0` — [Sửa R1] **CHƯA KIỂM CHỨNG LẠI:**
  phản biện R1 không tìm thấy dòng ghim trong `cit-voice-studio/pyproject.toml`
  đã đọc (file đó là pyproject của gói `vieneu` được vendored trong repo CIT);
  vòng sửa kiểm lại cũng không thấy `vieneu==` trong file đó. Con số 3.3.0 chỉ
  còn là "theo nghiên cứu 18/11" — không trích như dữ kiện tự đọc cho tới khi
  đọc được file pin đúng của CIT (VD `app-desktop/.../requirements.txt`).
  Thay đổi gần đây: `style` deprecated, backend ONNX/PyTorch tự chọn, subfolder
  model `update`/`onnx_int8`/`onnx_update`.
- **Vì sao tử huyệt:** không ghim version + không có lớp trừu tượng thì một lần
  `pip install --upgrade` có thể đổi chữ ký hàm / tên subfolder model → app chết.
- **Giải pháp:** ghim `vieneu==3.8.4` trong HP (`requirements.txt`/`pyproject.toml`);
  **mọi gọi SDK đi qua `V3Engine`** (lớp adapter, mục 3) — app không import
  `vieneu` trực tiếp ở UI/API; test tương thích chạy lại khi nâng SDK (ticket TK4.5);
  theo dõi release upstream mỗi quý, nâng theo đợt, không nâng lặng lẽ.

### TH-12 — Không có môi trường build Windows (🔴 R2)

- **DỮ KIỆN:** máy Annie là Linux VM; PyInstaller chỉ build được `.exe` trên
  đúng hệ điều hành đích (không build chéo Windows từ Linux), Inno Setup cũng
  cần Windows. SPEC v1.0 viết ticket "build `.exe` trên máy Annie" mà không nêu
  môi trường build Windows nào.
- **Vì sao tử huyệt:** không có `.exe` thì không tới được máy Windows của anh —
  mục tiêu chính của dự án ("dùng cá nhân trên máy Windows của anh").
- **Giải pháp (chốt ở v1.1, xem 🔴 R2 ở §3.2/§12 TK4.1):** build `.exe` bằng
  **GitHub Actions Windows runner** (`windows-latest`, miễn phí cho repo public)
  — hướng team đã dùng cho S1/MODOLIVIO; artifact `.exe` + hash được tải về cài
  trên máy anh (C1). Phương án dự phòng: build tại chỗ trên máy Windows của anh
  khi anh mở máy. Không dùng Wine làm phương án chính (rủi ro đóng gói Python +
  ONNX trên Wine chưa kiểm chứng).

### TH-13 — Cổng 8123 đã có chủ: máy chủ TTS của MODOLIVIO (🔴 R1)

- **DỮ KIỆN:** nghiên cứu nền §5.2 (cùng dự án): server TTS của MODOLIVIO chạy
  ở `127.0.0.1:8123` (đổi từ cổng 8000 ngày 16/11). SPEC v1.0 chọn đúng cổng đó
  làm mặc định cho HP.
- **Vì sao tử huyệt:** trên máy anh, HP và MODOLIVIO không thể cùng chạy — server
  mở sau bind thất bại, hoặc MODOLIVIO gọi API trúng HP server với hợp đồng khác.
- **Giải pháp (chốt ở v1.1, xem 🔴 R1 ở §4/§6):** cổng mặc định của HP là
  **`8124`**; bảng cổng đã chiếm + quy tắc kiểm tra trùng cổng + hành vi fail-fast
  khi cổng bận được ghi ở §4; kiểm tra thật trên máy anh ở C8 (§11).

### TH-14 — MP3 không có đường làm (🟡 Y1)

- **DỮ KIỆN:** server upstream chỉ xuất wav/pcm (`apps/openai_speech.py:360-366`,
  `:412`; `response_format` chỉ chấp nhận `pcm`/`wav`, khác → 400). SDK không có
  dependency mã hoá MP3 nào (`pyproject.toml`: không `ffmpeg`, `lameenc`,
  `pydub`). Chiều ngược cũng vậy: clone nhận file MP3/M4A (§5) nhưng `soundfile`
  (dependency của SDK) không giải mã MP3/M4A; `librosa` cần backend FFmpeg.
- **Vì sao tử huyệt:** định dạng xuất MP3 được hứa khắp SPEC (§3.3, §4, §5) mà
  không có encoder thì tới Bước 2 mới phát hiện — vỡ hợp đồng API.
- **Giải pháp (chốt ở v1.1, xem 🟡 Y1 ở §3.3/ADR-07):** đóng gói **FFmpeg** kèm
  app (binary tĩnh qua `imageio-ffmpeg`, fallback sang FFmpeg hệ thống nếu có;
  không có FFmpeg → chỉ xuất WAV + báo rõ lý do, không báo lỗi chung chung).
  Một công cụ giải quyết cả hai chiều: mã hoá MP3 đầu ra + giải mã MP3/M4A đầu
  vào cho clone. Ghi chú license FFmpeg vào NOTICE ở TK4.3.

### TH-15 — Upstream bỏ rơi v3 / Hugging Face không với tới được

- **DỮ KIỆN:** tác giả tập trung vào v4 thương mại; nghiên cứu §7 đã cảnh báo v3
  "có thể chỉ nhận cập nhật nhỏ". Repo/model nằm trên GitHub + Hugging Face —
  nhà cung cấp có thể xoá, chuyển private, hoặc mạng VN chặn/chậm HF.
  TH-11 chỉ nói "trôi version", không nói "mất hẳn".
- **Vì sao tử huyệt:** lần chạy đầu chết (không tải được model) và không có đường
  khác thì app không chạy được trên máy mới — đúng điểm TH-02 chưa bao quát.
- **Giải pháp:** (a) ghim version + mirror model: `scripts/download_model.py`
  lưu checksum (SHA-256) từng file model, hỗ trợ nguồn dự phòng (mirror HF
  hoặc file model đóng gói sẵn trong bộ cài — quyết ở Q2 §15); (b) đo tốc độ
  tải HF từ mạng nhà anh ở C10 (§11) trước khi chốt "tải lần đầu" hay "đóng gói
  sẵn"; (c) theo dõi release upstream mỗi quý (TK4.5).

### TH-16 — RAM khi batch lớn không có ngân sách

- **DỮ KIỆN:** SPEC cho batch tối đa 500 mục/lần (§4, số tạm — xem G6) nhưng
  không tính RAM: 500 mục × audio dài + history `max_history_gb: 5` "không tự
  xoá" + "nhắc dọn" (người dùng có thể bỏ qua) = đầy ổ / tràn RAM giữa chừng,
  job dở dang. TH-03 chỉ nói CPU/RTF, không nói RAM theo quy mô batch. CIT đo:
  1 giờ WAV ~330 MB → history 5 GB chỉ chứa ~15 giờ audio, batch lớn chạm
  ngưỡng rất nhanh.
- **Vì sao tử huyệt:** job batch lớn chết giữa chừng không khôi phục được là lỗi
  "phải dùng được" ở đúng tính năng nặng nhất của studio.
- **Giải pháp:** (a) ngân sách RAM: `BatchRunner` ghi audio từng mục ra đĩa ngay
  (không giữ toàn bộ batch trong RAM), đo peak RAM ở T3.5 với 100 và 500 mục;
  (b) quy tắc khi vượt `max_history_gb`: **chặn tạo mới + báo rõ** (không chỉ
  nhắc — người dùng đã bỏ qua nhắc thì chặn là rào chắn cuối; vẫn cho xoá/xuất
  bớt để mở lại); (c) batch 500 là số tạm chờ đo RAM ở Bước 2 (TK2.6), chốt số
  cuối theo số đo, không chốt theo cảm tính.

### TH-17 — Cam kết clone giọng không ngăn được lạm dụng + giọng là dữ liệu cá nhân

- **DỮ KIỆN:** checkbox + log là lời hứa, không phải xác minh (SPEC tự thừa nhận
  ở TH-04). Người dùng có thể clone giọng người khác chỉ bằng một cú tick.
  Giọng nói là dữ liệu cá nhân theo Nghị định 13/2023; nội dung AI phải ghi nhãn
  theo Nghị định 147/2024 — SPEC v1.0 có câu "ghi rõ giọng đọc được tạo bằng AI"
  nhưng không dẫn luật.
- **Vì sao tử huyệt:** HP trở thành công cụ tạo deepfake giọng nói — rủi ro pháp
  lý và uy tín, không sửa được bằng "thêm nút".
- **Giải pháp:** xem TH-04 (f)–(h) đã bổ sung ở v1.1: cơ chế gỡ giọng khi bị
  khiếu nại, ghi chú pháp lý NĐ 13/2023 + NĐ 147/2024 trong UI/Cài đặt, và câu
  hỏi mở Q13 (§15) về việc chỉ cho clone bằng thu micro trực tiếp ở v1.
  Kịch bản B (§9.2) bổ sung thêm: điều khoản VieNeu có cho bán lại V4 không,
  license phân phối lại weight, mô hình giá bán lại — xem 💭 G12.

### TH-18 — Build CI pass nhưng `.exe` thiếu file đi kèm, chết lúc chạy trên máy anh (🟡 R2-detail, đề xuất ở CRITIQUE-R2 §6.1)

- **DỮ KIỆN:** PyInstaller chỉ đóng gói những gì nó thấy (import tĩnh + hook).
  Các thành phần sau **không tự hiện** trong phân tích import: binary
  `imageio-ffmpeg` (file dữ liệu trong wheel — đo thật 172.692.552 byte,
  ~165 MB, xem TH-14/Y1), metadata entry points của `keyring` (tìm backend lúc
  chạy — `[keyring.backends]` trong `entry_points.txt`, xem TH-05/Y12),
  data/model của `onnxruntime`/`tokenizers`, file model (nếu Q2 chốt "kèm
  model"). Build trên runner có thể pass (artifact + SHA-256 đầy đủ) trong khi
  `.exe` chết ngay lần chạy đầu trên máy anh vì thiếu file.
- **Vì sao tử huyệt:** đúng kiểu lỗi "CI xanh, máy thật đỏ" mà T4.1/C1 được tạo
  ra để bắt — nhưng TH-12 chỉ nói "không có môi trường build", chưa nói "build
  xong nhưng chạy lỗi vì thiếu file". T4.1/C1 bắt được lỗi này ở cuối Bước 4,
  sau khi đã tốn cả vòng build.
- **Giải pháp:** đưa **danh sách collect PyInstaller** vào TK4.1 ngay từ đầu
  (`--collect-all keyring`, `--collect-all onnxruntime`, `--collect-all
  tokenizers`, collect binary `imageio_ffmpeg/binaries/*`, model theo Q2) +
  bước **smoke test `.exe` trên runner sạch** (runner Windows mới, không có
  Python, không có repo: chạy `.exe` → T1.2 thu nhỏ phải pass) **trước khi**
  đưa sang máy anh (C1). Smoke test trên runner sạch fail → build fail, không
  được đưa artifact sang máy anh.

> **Phản biện vòng 1 (tự chất vấn, chờ vòng 2):** TH-02 và TH-03 có thể gộp không?
> Không — TH-02 là "có model để chạy không", TH-03 là "chạy đủ nhanh/không méo không":
> hai điểm hỏng khác nhau, hai giải pháp khác nhau. TH-09 có thổi phồng không? Không —
> nó quyết định một tuyên bố đối ngoại (watermark) và liên quan trực tiếp TH-04.
> Điểm có thể còn thiếu (ghi để vòng phản biện kiểm tra): bản quyền văn bản đầu vào
> (PDF/sách) và dung lượng ổ đĩa khi lịch sử phình (WAV 48 kHz ~330 MB/giờ theo CIT).
> [Sửa R1] Phản biện R1 xác nhận cả hai đều là điểm mù thật: dung lượng ổ đĩa đã
> thành TH-16; bản quyền văn bản đầu vào bổ sung ở §3.3 (`FileReaders` — chỉ đọc
> file người dùng có quyền dùng, UI ghi rõ không đọc sách/file có bản quyền để
> phát tán) và §9.2 kịch bản B.

---

## 2. RESEARCH — BẢN ĐỒ REPO / SDK (dữ kiện đã đọc từ file thật)

Nguồn chính: `upstream-vieneu-tts/` (clone 19/11/2026, commit `512de867d49b883d50cc47989c445d070f62362f`),
`~/workspace/cuongit/cit-voice-studio/README.md` (v1.0.6, chỉ lấy tính năng/cấu trúc),
`~/workspace/research_notes/vieneu-studio-clone-2026-11-19.md` (§2.2, §3),
`~/workspace/custom-connectors/custom.vieneu/CONNECTOR.md` (hợp đồng V4).

### 2.1. Repo upstream — cấu trúc

| Đường dẫn | Nội dung (đã đọc) |
|---|---|
| `README.md` / `README.vi.md` / `README_PYPI.md` | Hướng dẫn cài + SDK + benchmark; ghi rõ Dubbing/Lecture/TikTok Reel/Audiobook **chỉ có trong official VieNeu App**, repo chỉ có Gradio demo đơn giản + SDK |
| `src/vieneu/__init__.py` | Chỉ export `Vieneu` (factory) |
| `src/vieneu/factory.py` | `Vieneu(mode="v3turbo", **kwargs)` — xem §2.2 |
| `src/vieneu/v3turbo.py` | Engine chính v3 Turbo (ONNX/CPU torch-free hoặc PyTorch/GPU) |
| `src/vieneu/v3nano.py` | v3 Nano preview: 24 kHz, 11 giọng (theo file `voices_v3_nano.json`), flow 48M tham số |
| `src/vieneu/base.py` | `BaseVieneuTTS`: codec, watermark, `save()`, `_resolve_ref_voice` |
| `src/vieneu/standard.py`, `turbo.py`, `fast.py`, `core_xpu.py`, `remote.py` | Backend cũ/GPU/XPU/API — **HP v1 không dùng** (chỉ v3turbo; `remote` là V3 API cũ, không phải V4 cloud) |
| `src/vieneu/_v3_turbo_engine/` | ONNX runtime lite, hub load, inference, speaker encoder (fbank/onnx), prompt, rep_history |
| `src/vieneu/v3_turbo_serve/` | Serve GPU: batched acoustic/backbone, cudagraph, stream |
| `src/vieneu/assets/` | `voices.json` (ghi CC BY-NC 4.0 — xem TH-01), `voices_v3_turbo.json` (25 giọng), `voices_v3_nano.json` (11 giọng), `samples/` (6 mẫu .pt/.txt/.wav: Bình, Ly, Ngọc, Tuyên, Vĩnh, Đoan) |
| `src/vieneu/serve.py` | **Launcher** chạy server qua subprocess, cổng mặc định **23333**, `--model-name` mặc định v2 — không phải API server |
| `apps/gradio_main.py` | Demo Gradio `vieneu-web` (cổng 7860): tab Đọc truyện / Hội thoại / SRT / Voice Cloning; `MAX_SPEAKERS=8`; `CONV_VOICES_CACHE` |
| `apps/openai_speech.py` | **API server tương thích OpenAI** (FastAPI, cổng 8000) — xem §2.5 |
| `apps/srt_speech.py` | Logic SRT → speech: `parse_srt`, `lay_on_timeline`, `concatenate`, `srt_to_speech` |
| `apps/web_stream.py` | Demo streaming FastAPI (cổng 8001): `GET /`, `GET /voices`, `GET/POST /stream` |
| `apps/user_voices.py`, `ui_constants.py`, `ui_utils.py` | Hỗ trợ UI Gradio |
| `examples/` | `main.py`, `main_v3turbo.py`, `main_v3nano.py`, `main_remote.py`, `openai_speech_client.py`, `srt/sample_vi.srt`, `audio_ref/*.wav` |
| `config.yaml` | `text_settings.max_chars_per_chunk: 256`, `max_total_chars_streaming: 3000`; repo model: v3 Turbo `pnnbao-ump/VieNeu-TTS-v3-Turbo`, v3 Nano, v2, v1; codec NeuCodec/VieNeu-Codec |
| `pyproject.toml` | `vieneu==3.8.4`, Python `>=3.10` (`.python-version` 3.12); xem §2.3 |
| `docker/`, `Makefile`, `docs/` | `Deploy.md`, `streaming.md`, `CUSTOM_MODEL_USAGE.md`, `CUSTOM_V3_TURBO_BACKEND_FIX.md` |
| `tests/` | Test của upstream (tham khảo khi viết test HP, không copy) |
| `finetune/` | LoRA fine-tune (GPU-only) — ngoài phạm vi v1 |

### 2.2. SDK `vieneu` — sự thật quan trọng

**Cài đặt (DỮ KIỆN — README + pyproject.toml):**

```bash
pip install vieneu            # CPU mặc định: torch-free, chạy v3 Turbo qua ONNX Runtime
pip install "vieneu[cuda]"    # GPU: cần cài torch trước trên Windows
pip install torch==2.8.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cu128
pip install "transformers==4.57.6"   # pinned — GPU SDK
pip install vieneu            # sau khi có torch CUDA (Windows)
# Từ repo (dev): uv sync  /  uv sync --extra cuda ; chạy demo: uv run vieneu-web  # http://127.0.0.1:7860
```

- Python `>=3.10` (3.10–3.13), repo dùng 3.12. Core dependencies: `sea-g2p`,
  `onnxruntime>=1.20.0`, `numpy`, `soundfile`, `soxr`, `kaldi-native-fbank>=1.20`,
  `tokenizers>=0.20`, `huggingface_hub`, `PyYAML`, `gradio>=5.49.1`, `librosa>=0.11.0`.
  Extra: `[legacy]` (torch/transformers/neucodec), `[pdf]` (PyMuPDF), `[watermark]`
  (resemble-perth, cần torch), `[cuda]` (torch 2.8.0 + transformers + safetensors),
  `[finetune]` (peft/accelerate). Entry points: `vieneu-web`, `vieneu-stream`.

**Factory (DỮ KIỆN — `src/vieneu/factory.py`):**

```python
from vieneu import Vieneu
vieneu = Vieneu()                    # mặc định mode="v3turbo", 48 kHz
vieneu = Vieneu(mode="v3nano")       # 24 kHz, CPU yếu
vieneu = Vieneu(backend="onnx")     # ép ONNX/CPU dù có GPU
# Các mode khác (HP v1 KHÔNG dùng): "standard", "fast"/"gpu", "turbo", "turbo_gpu", "remote"|"api", "xpu"
```

**`V3TurboVieNeuTTS.__init__` (DỮ KIỆN — `src/vieneu/v3turbo.py:134-160`):**

```python
Vieneu(
    backbone_repo="pnnbao-ump/VieNeu-TTS-v3-Turbo",
    model_subfolder="update",
    moss_tokenizer="OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano",
    device="auto", dtype="auto",
    backend="auto",        # "auto" → ONNX trên CPU, PyTorch trên GPU; "onnx"|"pytorch" để ép
    onnx_repo=None, onnx_dir=None,
    precision="fp32",      # ONNX/CPU: "fp32" (mặc định) | "int8" (nhanh ~3x/frame, nhỏ 4x; cần CPU VNNI)
    # [Sửa R1-G1] "~3x/frame" là comment trong code (per-frame); README ghi "~1,6× faster"
    # là tốc độ tổng thể. Hai số đo khác nhau, không mâu thuẫn — SPEC trích cả hai, ghi rõ phạm vi đo.
    threads=0,             # 0 = mặc định engine (~số nhân vật lý, cap 8)
    max_batch_size=32, max_streams=16,
)
# self.sample_rate = 48000
```

**Suy luận giọng (DỮ KIỆN — `src/vieneu/v3turbo.py:600-842`):**

```python
audio = vieneu.infer(text, voice="Phạm Tuyên")     # np.ndarray float32 @ 48 kHz
vieneu.save(audio, "output.wav")
# infer(text, ref_audio=None, voice=None, style=None /*DEPRECATED, bị bỏ qua*/,
#        denoise=True, use_ref_codes=True, temperature=0.8, top_k=25, top_p=0.95,
#        max_new_frames=300, repetition_penalty=1.2, repetition_window=...,
#        max_chars=256, silence_p=0.15, crossfade_p=0.0,
#        apply_watermark=True, batch_size=None) -> np.ndarray
for chunk in vieneu.infer_stream("Xin chào các bạn!", voice="Mai Anh"):  # Generator[np.ndarray]
    play(chunk)
audios = vieneu.infer_batch(texts, voice="Hải Đăng")  # List[np.ndarray], cùng thứ tự texts
```

- Text tự chia chunk tối đa 256 ký tự (`normalize_to_chunks_v3_with_gaps`); rỗng → mảng rỗng.
- Streaming: GPU first audio ~115 ms, 16 luồng đồng thời trên RTX 3060 (continuous
  batching, 1 CUDA graph); CPU/ONNX first audio ~140 ms (int8) / ~300 ms (fp32),
  1 luồng (2 với int8). VRAM đỉnh 1,1 GB ở 16 luồng (README §4).
- Hiệu năng CPU (README §4, i5 12th-gen): Turbo fp32 RTF 0,62; int8 RTF 0,37;
  Nano RTF 0,11–0,22, download 282 MB, load ~3 s. GPU RTF ~0,02 batched.
- Thẻ cảm xúc **thử nghiệm**: `[cười]`, `[thở dài]`, `[hắng giọng]` chèn trong text.

**Liệt kê giọng (DỮ KIỆN — `src/vieneu/v3turbo.py:305-335` + file JSON):**

```python
voices = vieneu.list_preset_voices()   # -> [(label, voice_id), ...]; editors' picks (featured 1..10) có prefix ⭐, đứng trước
vieneu.get_preset_voice("Hải Đăng")    # -> dict; sai tên raise ValueError
vieneu.resolve_voice_name("Minh Quân Pro")  # -> "Hải Đăng" (alias); None nếu không rõ
```

- **25 giọng v3 Turbo** (`voices_v3_turbo.json`, `meta.count=25`, `default_voice="Hải Đăng"`):

| # | Giọng | Giới tính · Vùng · Phong cách |
|---|---|---|
| ⭐1 | Adam bựa | Nam · Bắc · tự nhiên |
| ⭐2 | Trúc Ly | Nữ · Bắc · tự nhiên |
| ⭐3 | Thiện Minh | Nam · Bắc · kể chuyện |
| ⭐4 | Mai Anh | Nữ · Bắc · tin tức |
| ⭐5 | Hải Đăng (mặc định) | Nam · Bắc · tự nhiên |
| ⭐6 | Thùy Dung | Nữ · Nam · tin tức |
| ⭐7 | Thiền Tâm Đức | Nam · Bắc · kể chuyện |
| ⭐8 | Ngọc Huyền | Nữ · Bắc · tự nhiên |
| ⭐9 | Quang Sơn | Nam · Trung · tự nhiên |
| ⭐10 | Ngọc Trân | Nữ · Trung · tự nhiên |
| 11 | Minh Đức | Nam · Bắc · tin tức |
| 12 | Phạm Tuyên | Nam · Bắc · tự nhiên |
| 13 | Thái Sơn | Nam · Nam · kể chuyện |
| 14 | Xuân Vĩnh | Nam · Bắc · tự nhiên |
| 15 | Thanh Bình | Nam · Bắc · kể chuyện |
| 16 | Ngọc Linh | Nữ · Bắc · kể chuyện |
| 17 | Đoan Trang | Nữ · Bắc · tự nhiên |
| 18 | Thục Đoan | Nữ · Nam · kể chuyện |
| 19 | Minh Triết | Nam · Nam · tin tức |
| 20 | Mỹ Duyên | Nữ · Nam · đọc truyện |
| 21 | Quỳnh Anh | Nữ · Bắc · đọc truyện |
| 22 | Đức Trí | Nam · Nam · đọc truyện |
| 23 | Kim Thanh | Nữ · Nam · đọc truyện |
| 24 | Adam | Nam · Nam · tự nhiên |
| 25 | Quốc Tuấn | Nam · Bắc · tự nhiên |

- v3 Nano: 11 giọng trong file (`Adam, Ái Hân, Mỹ Duyên, Đức Trí, Hữu Quân, Xuân Tiên,
  Mai Anh, Trúc Ly, Anh Khôi, Minh Quân, Mạnh Dũng`), 24 kHz. **CHƯA RÕ:** `config.yaml`
  ghi Nano "chỉ 6 giọng có sẵn, không clone" — mâu thuẫn với README ("11 preset voices
  + voice cloning") và file JSON (11 tên). HP v1 chỉ dùng Turbo nên không chặn, nhưng
  không được trích số 6 giọng đó đi nơi khác khi chưa xác minh.
- 6 mẫu giọng kèm repo: Bình, Ly, Ngọc, Tuyên, Vĩnh, Đoan (`.pt` + `.txt` + `.wav`).

**Clone giọng (DỮ KIỆN — `src/vieneu/v3turbo.py:337-470`):**

```python
vieneu.encode_reference("my_voice.wav")          # -> (speaker_emb, ref_codes)
audio = vieneu.infer("...", ref_audio="my_voice.wav")   # clone tức thì, không cần đăng ký trước
vieneu.add_voice(name, ref_audio, denoise=True, use_ref_codes=True,
                 description="", gender="", style=None, save=False) -> str
vieneu.remove_voice(name, save=False)
vieneu.save_voices(path=None)   # MẶC ĐỊNH ghi đè assets/voices_v3_turbo.json trong package — HP KHÔNG được dùng mặc định này
vieneu.denoise(ref_audio, out_path=None, max_seconds=None)  # -> (wav, 44100)
```

- Clip mẫu: README/example ghi **3–5 s** (`main_v3turbo.py`), README chính ghi
  "clip of a few seconds", CIT: thu micro 3–8 s, giữ tối đa 15 s, Turbo dùng tối đa
  8 s có tiếng. HP chốt: **nhận 3–8 s** (validate), enroll ≈ 2,7 s trên CPU 6 nhân
  (comment trong code, đo 15/09/2026). `_preclean_reference_audio` cắt lặng đầu/cuối
  (librosa trim top_db=30), file tạm vào `~/.cache/vieneu/tmp` (chmod 0700).
- `style` **deprecated, không có tác dụng** trên v3 Turbo (phong cách nằm trong
  reference) — chữ ký vẫn nhận để tương thích ngược.

**Hội thoại / Podcast (DỮ KIỆN):** SDK **không có** API Conversation. Chỉ có ở
`apps/gradio_main.py`: `MAX_SPEAKERS = 8`, `synthesize_conversation` /
`_synthesize_conversation_v3` (batch toàn bộ hội thoại, batch_size 32), giọng lọc
theo cờ `podcast=True`. HP phải tự implement (xem TH-10, §3.3).

**Model tải về (DỮ KIỆN):** lần đầu tải qua `hf_hub_download` từ
`pnnbao-ump/VieNeu-TTS-v3-Turbo` (subfolder `onnx_int8`/`onnx_update`) +
tokenizer `OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano` + codec ONNX
(`OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX`) + speaker-encoder/denoiser ở
repo root (xem TH-02/Y10). [Sửa R1-Y5] Đã gỡ con số "~110 MB graph clone" khỏi
đoạn Turbo — con số đó thuộc mục Nano (`README.md:334`), không phải Turbo.
Cache HF mặc định `~/.cache/huggingface`
(`HF_HOME` đổi được). **CHƯA RÕ:** tổng dung lượng tải v3 Turbo (README không ghi;
xem TH-02, đo ở Bước 1 — đo riêng từng thành phần, TK1.3).

### 2.3. API server có sẵn trong repo upstream?

**CÓ — 2 server tham khảo (DỮ KIỆN, chỉ tham khảo kiến trúc, HP viết server riêng):**

| Server | File | Cổng | Endpoint |
|---|---|---|---|
| OpenAI-compatible API | `apps/openai_speech.py` (FastAPI + uvicorn) | 8000 (`HOST=127.0.0.1 PORT=8000`, env đổi được) | `POST /v1/audio/speech` (body: `model` bất kỳ, `voice` = tên preset hoặc đã thêm qua `POST /v1/voices`, `response_format` pcm/wav, `sample_rate` ∈ {48000, 24000, 16000, 8000}, `stream_format` audio/sse; `speed`/`instructions` bị bỏ qua, báo qua header `X-VieNeu-Ignored`); `GET /v1/models`; `GET /v1/voices`; `POST /v1/voices` (409 nếu trùng giọng built-in — [Sửa R1-G2] code chỉ kiểm
  chứng 409 với built-in, alias có bị 409 không **chưa rõ**); `GET /health`; auth `VIENEU_API_KEY` env (Bearer, hmac compare); hết slot → 429; engine lỗi → 503; voice lạ → 400 |
| Streaming demo | `apps/web_stream.py` (FastAPI) | 8001 | `GET /`, `GET /voices`, `GET/POST /stream` (query/body `text`, `voice_id`) |
| Gradio demo | `apps/gradio_main.py` (`vieneu-web`) | 7860 | UI web, không phải API |

- `src/vieneu/serve.py` chỉ là launcher (cổng 23333). Docker có profile
  `api-gpu` / `api-cpu` (`docker compose -f docker/docker-compose.yml --profile api-cpu up`).
  [Sửa R1-G3] Phản biện R1 chưa đọc thấy `api-cpu` trong lần kiểm chứng của họ;
  kiểm chứng lại ở vòng sửa: `docker/docker-compose.yml:102` có service
  `api-cpu` (`profiles: ["api-cpu"]`) — cả hai profile đều tồn tại.

### 2.4. V4 Cloud API — hợp đồng (DỮ KIỆN — connector `custom.vieneu`, đã kiểm chứng 19/11)

- Base: `https://api.vieneu.io/api/v1`; auth `Authorization: Bearer <key>` (`vn_sk_...`,
  header `X-API-Key` cũng được); engine **v4 only**; **billing per submitted character**.
- `GET /v1/audio/voices?engine=v4` → 707 giọng (đã kiểm chứng 200).
  `GET /v1/voices?engine=v4` → catalogue giàu (`id`, `name`, `gender`, `region`,
  `description`) + giọng clone của chính tài khoản; 182 giọng nữ Bắc.
- `POST /v1/audio/speech` — body: `input` (bắt buộc), `model: "v4"`,
  `voice` = **tên hiển thị tiếng Việt** (VD "Hạ Vy"), `response_format`: `mp3`
  (mặc định), `wav`, `opus`, `pcm`, `ulaw`. Đã kiểm chứng: voice "Hạ Vy" → 200,
  WAV PCM 16-bit 48 kHz mono 2,91 s (`~/workspace/vieneu-test/vieneu-test-ha-vy.wav`).
  Voice id sai engine → 400.
- Async: `POST /v1/tts` → `jobId`; poll `GET /v1/tts/{jobId}`. Streaming:
  `POST /v1/tts/stream`. Hội thoại/lồng tiếng/SRT: `POST /v1/dialogue`,
  `POST /v1/dub`, `POST /v1/srt`.
- Clone giọng: **chỉ trên web** (vieneu.io/#/clone), không qua API.
- Docs: `https://docs.vieneu.io/docs/cloud-api/overview/`, OpenAPI
  `https://docs.vieneu.io/openapi.json`, MCP `https://api.vieneu.io/mcp`.
- **BẢO MẬT (lệnh anh):** key thật nằm trong connector `custom.vieneu` (Secure Vault).
  App HP **chỉ dùng key do người dùng nhập**; không lấy giá trị key đó ra; test V4
  phải hỏi Annie trước.

### 2.5. Cấu trúc tính năng tham khảo (chỉ cấu trúc/luồng — KHÔNG copy code)

**VieNeu Desktop 0.18.23–0.18.27** (ghi chú phát hành, nghiên cứu 18/11):
Phòng thu (nhiều bản đọc xếp hàng; bản sau tạo trong lúc bản trước phát; nút "Dừng
phát"; hàng đợi tạm dừng khi lỗi) · Tạo hàng loạt (từ .txt/.json/.srt, tới 100.000
câu/tệp, câu dài đọc nhanh tối đa 2× giữ cao độ) · Lồng tiếng (.srt, phụ đề in vào
video, karaoke; V3 + V4) · Sách nói/Bài giảng/Podcast (trợ lý AI viết kịch bản bằng
LLM bên thứ ba, tự thử lại khi 503/429) · Bộ tăng tốc GPU (tự hồi phục khi CUDA hỏng;
SDK 3.8.4) · Server VieNeu-TTS/MCP tích hợp. Bộ cài Win x64 ~90 MB, **chưa ký**.

**CIT Voice Studio v1.0.6** (README + cấu trúc thư mục `app-desktop/cit-voice-app/src`):
route `home`, `TtsStudio`; feature `tts/` (`api`, `audio-engine`, `batch-parse`,
`history`, `playback`, `pronunciation-csv`, `read-text-file`, `ref-audio`,
`text-cleanup`, `text-tools`, `zip`…). Tính năng (đã đọc README): 25 giọng; nghe thử
từng giọng; tốc độ 0,75×–1,5×; xuất WAV/MP3 (Turbo 48 kHz); thẻ cảm xúc `[cười]`
`[thở dài]` `[hắng giọng]`; thẻ nghỉ `[nghỉ 2s]`/`[nghỉ 500ms]` (tối đa 10 s/thẻ);
từ điển phát âm (CSV import/export, tối đa — CIT không ghi giới hạn, VieNeu Studio
ghi 2.000 mục); clone 3–8 s (micro/file MP3/WAV/M4A, tối đa 15 s); hội thoại nhiều
giọng; đọc PDF/DOCX/TXT; tạo hàng loạt bằng mốc `[P1]`… + file TXT, xuất ZIP;
phụ đề .srt kèm audio; lồng tiếng .srt (tốc độ tối đa 1,5×, không cắt chữ, xuất SRT
đã chỉnh mốc); Bản đã tạo (lưu máy, nghe/tải lại, nhắc dọn khi nặng ổ đĩa);
API `127.0.0.1:8001` (`/health`, `/voices`, `/stream`, `/api/tts/generate`,
`/api/tts/generate-with-subtitles`, `/api/tts/conversation`); LAN opt-in + `X-API-Key`;
cấu hình máy tối thiểu 4 nhân/8 GB RAM/3 GB trống; bài dài ghi dần ra đĩa
(~84.000 ký tự đã thử, ~1 GB RAM); 1 giờ WAV ~330 MB. Bộ cài Win ~367 MB, Linux
~460 MB, macOS ~428–443 MB; **chưa ký** (SmartScreen/macOS chặn lần đầu).

> **Kết luận research:** mọi tính năng HP v1 cần đều đã có tiền lệ chạy được
> (upstream SDK + 2 studio tham khảo). Không có tính năng nào phải "phát minh".
> Rủi ro nằm ở tích hợp + giấy phép + hiệu năng + đóng gói (mục 1), không nằm ở
> "không biết làm".

---

## 3. TO-SPEC — KIẾN TRÚC

### 3.1. Nguyên tắc thiết kế

1. **Mọi gọi SDK đi qua một adapter duy nhất** (`V3Engine`) — UI/API không import
   `vieneu` trực tiếp (đánh trúng TH-11).
2. **Mọi engine cùng một interface** (`synthesize(text, voice, options) -> audio`) —
   UI, hàng đợi, SRT, batch, history không biết đang dùng engine nào (yêu cầu lệnh 03:34).
3. **Local-first, fail-closed:** mặc định loopback, V4 mặc định tắt, LAN opt-in + key
   (TH-05, TH-06).
4. **Không hardcode:** máy, cổng, thư mục model, thư mục xuất đều qua config (mục 6).
5. **Ghi dần ra đĩa** cho bài dài; job có trạng thái, thử lại, huỷ được.
6. **Một nhân vật = một giọng cố định** trong hội thoại (TH-10).

### 3.2. Kiến trúc 3 lớp

```
┌─────────────────────────────────────────────────────────────────┐
│ UI (lớp 3) — Desktop app (web UI chạy local)                    │
│  Phòng thu · Hội thoại · Lồng tiếng .srt · Đọc file ·           │
│  Tạo hàng loạt · Bản đã tạo · Cài đặt                           │
│  + API client nội bộ (gọi lớp 2 qua HTTP loopback)              │
├─────────────────────────────────────────────────────────────────┤
│ API (lớp 2) — HP API server (FastAPI, Python)                   │
│  REST + OpenAI-compatible subset · Job queue · Auth (LAN key)   │
│  Validation · Rate limit nội bộ · History/Storage service       │
├─────────────────────────────────────────────────────────────────┤
│ ENGINE (lớp 1) — TTS Engine abstraction                         │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐     │
│  │ V3Engine     │  │ V4Engine     │  │ AudioPost (chung)  │     │
│  │ (vieneu SDK  │  │ (Cloud API   │  │ speed 0.75–1.5×,   │     │
│  │  v3 Turbo)   │  │  v4, HTTPS)  │  │ SRT dub, join,     │     │
│  └──────────────┘  └──────────────┘  │ normalize, MP3)    │     │
│  ConversationEngine · SrtDubber · SrtWriter · BatchRunner · PronDict    │
│  VoiceStore (preset + clone) · FileReaders (PDF/DOCX/TXT)               │
│  TextPreprocess (thẻ [nghỉ]/cảm xúc) · PreviewCache (nghe thử)          │
└─────────────────────────────────────────────────────────────────┘
        ↓ model lần đầu tải từ Hugging Face (TH-02) · cache local
```

**So sánh phương án (theo system-design-planning-vn):**

| Phương án | Ưu | Nhược | Kết luận |
|---|---|---|---|
| A. Python + FastAPI + web UI local (chọn) | Dùng thẳng SDK `vieneu`; 1 ngôn ngữ cho engine+API; UI web dùng lại được trên Win/Linux; CIT/VieNeu Desktop đều đi hướng này (server local + UI) | Cần đóng gói Python (PyInstaller/uv) cho Windows; WebView2 trên Win | **Chọn** — rủi ro thấp nhất, khớp tiền lệ |
| B. Electron + Python sidecar | UI desktop "xịn" hơn | 2 runtime, đóng gói nặng, IPC phức tạp | Không chọn v1 |
| C. Dùng thẳng Gradio demo của upstream | Nhanh nhất | Chỉ là demo đơn giản (README nói rõ); không có history/batch/SRT đầy đủ, không có V4, không có API HP | Không chọn — chỉ tham khảo |
| D. Fork CIT Voice Studio rồi đổi thương hiệu + thêm tính năng riêng | Nhanh nhất tới "dùng được": CIT đã chạy thật (v1.0.6, 25 giọng, clone, SRT, batch, history, API 8001, LAN key); Apache 2.0 cho phép fork | **Trái lệnh anh 03:31** — "KHÔNG fork/copy code CIT, CIT chỉ là tài liệu tham khảo tính năng/cấu trúc"; kiến trúc CIT gắn với nhu cầu của họ, không phải kiến trúc riêng cho MODOLIVIO/HP | **Đã cân nhắc, loại** — xem ADR-01. Đây là phương án nghiên cứu nền §6.4 khuyến nghị; SPEC v1.0 bỏ sót, v1.1 bổ sung cho đủ hồ sơ quyết định (Charter §2) |

**Quyết định ADR-01:** Phương án A. Điều kiện xét lại: nếu đóng gói Python trên
Windows (bằng GitHub Actions Windows runner, TK4.1) thất bại 2 lần thì xét lại
phương án B. Phương án D đã cân nhắc và loại vì lệnh anh 03:31 (không fork/copy
code CIT) + cần kiến trúc riêng cho MODOLIVIO — không phải vì D kém về kỹ thuật.

### 3.3. Module (lớp Engine + API)

| Module | Trách nhiệm | Dựa trên (không copy code) |
|---|---|---|
| `V3Engine` | Adapter duy nhất gọi SDK: `Vieneu()`, `infer/infer_stream/infer_batch`, `list_preset_voices`, `add_voice`, `encode_reference`; quản lý `precision` (fp32/int8 theo CPU), `threads`, load model + báo tiến trình tải lần đầu | `vieneu` SDK §2.2 |
| `V4Engine` | Client HTTPS Cloud API v4: `POST /v1/audio/speech`, `GET /v1/audio/voices`, `POST /v1/tts` (async), `POST /v1/dialogue`, `POST /v1/srt`, `GET /v1/balance`, `GET /v1/engines`; auth Bearer (key lấy từ store); đếm ký tự + ước tính phí theo công thức **ký tự (tối thiểu 50/request) × engine `billingMultiplier` × `globalMultiplier`** (lấy từ `GET /v1/engines`); **`Idempotency-Key` = UUID theo HP job id cho mọi `POST /v1/tts`**, lưu cùng job (409 → chờ `Retry-After`, retry cùng key; 422 → báo lỗi, không retry); **không retry `POST /v1/audio/speech` sau timeout** (endpoint đồng bộ không hỗ trợ idempotency — chỉ retry khi chưa gửi request đi được, hoặc chuyển sang đường async); **fallback V3** khi lỗi; xử lý riêng 401 (key sai) / **403 (hết quota)** / 429 (quá tải) — mỗi mã báo rõ lý do, không gộp thành "lỗi V4" | Connector `custom.vieneu` + OpenAPI `docs.vieneu.io/openapi.json` (kiểm chứng 19/11/2026) |
| `EngineRouter` | Chọn engine theo cài đặt + từng job; interface chung `synthesize(text, voice, options) -> AudioResult`; fallback V3 + lý do (TH-05). [Sửa R2-N-FB] **Ánh xạ giọng fallback V4→V3:** voice V4 là tên hiển thị (VD "Hạ Vy") — đưa sang V3 sẽ 400 theo hợp đồng §4 nếu không có mapping, nên fallback phải đổi giọng qua **bảng ánh xạ** `docs/voice-fallback-map.md` (viết ở Bước 2): mỗi giọng V4 (`id` trong catalogue `GET /v1/voices`) map sang preset V3 gần nhất theo (giới tính, vùng, phong cách) trong 25 preset; giọng V4 không có preset tương đương gần → map về giọng mặc định **"Hải Đăng"**; bảng sinh từ catalogue thật rồi soát tay, không đoán mò. Hành vi khi fallback đổi giọng: kết quả job + UI + log **phải ghi rõ cả lý do lẫn giọng mới** (VD "V4 lỗi 403 hết quota → fallback V3, giọng đổi Hạ Vy → Hải Đăng"). Job nào **khóa giọng** (API param `voice_strict: true`, hoặc UI tick "chỉ dùng giọng này") thì **không fallback** — trả lỗi thay vì đổi giọng lặng lẽ. Quy tắc fallback giọng mặc định trong config: `fallback_voice: "map" \| "default" \| "fail"` (mặc định `"map"`) | — |
| `VoiceStore` | 25 preset (đọc từ SDK, không hardcode tên) + giọng clone (file riêng của HP, **không** ghi đè `assets/voices_v3_turbo.json`); alias; giọng mặc định; cam kết quyền sử dụng kèm mỗi giọng clone. [Sửa R1-G10] Khóa chính của giọng V4 là trường **`id`** trong catalogue `GET /v1/voices` (connector đã kiểm chứng catalogue có `id` riêng), **không khóa theo tên hiển thị** — tên hiển thị chỉ để hiển thị, vì hai giọng khác nhau có thể trùng tên (chưa xác minh tên là duy nhất) | SDK `add_voice/save_voices` |
| `TextPreprocess` | [Sửa R1-Y2] Tiền xử lý text trước khi đưa vào `infer()`: (a) thẻ cảm xúc `[cười]`/`[thở dài]`/`[hắng giọng]` giữ nguyên — SDK hỗ trợ thật; (b) thẻ nghỉ `[nghỉ 2s]`/`[nghỉ 500ms]` **SDK không có** (grep toàn bộ upstream: 0 kết quả) nên tầng này tự xử lý: parse tag → cắt text thành đoạn → gọi `infer()` từng đoạn → chèn silence đúng số giây bằng `AudioPost`. [Sửa R2-Y2 — ngữ pháp + quy tắc còn thiếu] Ngữ pháp chốt: `[nghỉ <số><đơn vị>]`, số thập phân cho phép (VD `2`, `2.5`, `500`), đơn vị `s` (giây) hoặc `ms` (mili giây), cho phép 0–1 khoảng trắng giữa số và đơn vị (`[nghỉ 2 s]` chấp nhận), đơn vị không phân biệt hoa/thường (`2S`/`500MS` chấp nhận), tên thẻ phải viết đúng `nghỉ` thường. Quy tắc: tag ở đầu/cuối câu vẫn chèn silence tương ứng; **tag giữa từ** (VD `xin[nghỉ 1s]chào` — không có khoảng trắng/ranh giới từ hai bên) → **báo lỗi rõ + không tạo** (cắt giữa từ sẽ phá phát âm); nhiều tag liên tiếp được phép, khoảng lặng cộng dồn nhưng **tổng liên tiếp ≤ 10 s**; tag đứng cạnh thẻ cảm xúc thì tách tại `[nghỉ]`, thẻ cảm xúc ở lại trong đoạn của nó và đi vào `infer()` như thường; giới hạn 10 s/thẻ (và 10 s/tổng liên tiếp), áp ở tầng này (không phải ở engine); tag sai định dạng (VD `[nghỉ xyz]`, thiếu đơn vị, số âm) → báo lỗi rõ + không tạo. Đoạn sau khi cắt dài > 256 ký tự thì SDK tự chia chunk tiếp **bên trong đoạn** — khoảng lặng SDK chèn (`gaps_to_silence`, xem `SrtWriter`) chỉ nằm trong đoạn, không tương tác với silence `[nghỉ]` mà `AudioPost` chèn **giữa các đoạn** sau khi `infer()` xong từng đoạn. **Đường V4:** OpenAPI `GET /v1/emotion-tags` ghi v4 "deletes any other tag from your text" — `[nghỉ]` gửi thẳng sang V4 sẽ **bị xóa lặng lẽ, không có khoảng lặng nào**; vì vậy V4 cũng phải tách đoạn + gọi V4 từng đoạn + nối bằng `AudioPost` như V3 (dùng `POST /v1/tts` async kèm `Idempotency-Key` riêng từng đoạn — không dùng endpoint đồng bộ cho đường này, xem `V4Engine`), mỗi đoạn V4 tính phí tối thiểu 50 ký tự nên UI phải cảnh báo: tách `[nghỉ]` trên V4 có thể nhân phí (mỗi đoạn ngắn vẫn tính 50 ký tự). Chỉ 3 thẻ cảm xúc `[cười]`/`[thở dài]`/`[hắng giọng]` sống sót trên V4, các tag khác đều bị xóa. Không bao giờ đưa nguyên text chứa `[nghỉ …]` vào `infer()` (SDK sẽ đọc thành tiếng) hay vào request V4. Test nhánh lỗi (TK1.6): unit test cho tag sai định dạng, vượt 10 s, tag giữa từ, tổng liên tiếp > 10 s, và test mock assert **không có chuỗi `[nghỉ` trong bất kỳ request body nào gửi sang V4** | CIT (tính năng), thiết kế HP |
| `ConversationEngine` | Kịch bản [(speaker, line)]; khoá speaker→voice; gom line theo speaker → `infer_batch` → ghép đúng thứ tự + khoảng lặng; tối đa 8 speaker (theo upstream) | `gradio_main.py` |
| `SrtDubber` | Parse SRT (bỏ thẻ định dạng), áp từ điển, tính tốc độ/câu, xếp timeline, xuất WAV/MP3 + SRT đã chỉnh mốc + báo cáo câu bị lùi | `apps/srt_speech.py`, CIT |
| `SrtWriter` | [Sửa R1-Y3] Suy mốc giờ cho file .srt kèm audio ở Phòng thu (endpoint 5): `infer()` chỉ trả `np.ndarray`, không có timestamp. [Sửa R2-Y3 — phương pháp v1.1 **sai hằng số**] Phương pháp chốt: chia text thành chunk đúng như SDK chia (tối đa 256 ký tự, `normalize_to_chunks_v3_with_gaps` — hàm này trả kèm loại ranh giới `gaps[i] ∈ {"para","sentence","minor"}`), gọi `infer()` từng chunk, **đo độ dài audio từng chunk** (số mẫu / 48.000), cộng dồn + khoảng lặng giữa chunk **theo `gaps_to_silence`, không dùng `silence_p`** — `silence_p` (0,15 s) là tham số của `infer()` nhưng đường v3 Turbo **không dùng nó**: `v3turbo.py:646` nối chunk bằng `join_audio_chunks(..., silence_ps=gaps_to_silence(gaps))`, `silence_p` chỉ còn dùng ở đường v1/v2 (`fast.py:149`, `standard.py:232`, `remote.py:201`). Hằng số đúng (`core_utils.py:77` `V3_GAP_SILENCE`): ngắt đoạn `para` = **0,70 s**, hết câu `sentence` = **0,50 s**, ngắt trong câu/cắt cưỡng bức `minor` = **0,30 s**. **Tinh chỉnh quan trọng** (đọc từ comment `core_utils.py:66-76`): các số trên là khoảng nghỉ **TỔNG** nghe được ở khe (im lặng đuôi chunk trước + zeros chèn + im lặng đầu chunk sau) — `join_audio_chunks` giữ nguyên audio model sinh và **chỉ chèn zeros bù cho đủ** tổng đó; vì vậy `SrtWriter` không được cộng cả 0,30/0,50/0,70 s lên trên độ dài chunk đã đo (độ dài đo được đã chứa đuôi im lặng model tự sinh — preset v3 Turbo tự phát ~300 ms im lặng trước EOS, giọng clone hầu như không), mà phải đo im lặng ở mép chunk (hàm `edge_silence` có sẵn trong `core_utils.py`) rồi chỉ cộng phần zeros bù thêm = `max(0, gaps_to_silence − im lặng mép đã đo)`. Cộng dồn sai mỗi mốc 0,15–0,55 s như v1.1 thì tiêu chí ±0,3 s/câu sẽ trượt ở các câu sau. **Quy tắc chia mốc trong chunk nhiều câu (chunk ≠ câu):** một chunk có thể chứa nhiều câu hoặc cắt giữa câu (`phonemize_text.py:354` cắt tối đa 256 ký tự, có "cắt cưỡng bức") — mốc từng câu trong cùng chunk được chia theo **tỉ lệ độ dài ký tự** của từng câu trong chunk (số ký tự câu / tổng số ký tự chunk × độ dài audio chunk), ghi rõ đây là ước lượng (không có forced alignment); mốc của câu bị cắt cưỡng bức qua hai chunk lấy theo tỉ lệ ký tự ở cả hai chunk. **Giới hạn sai số tích lũy (ghi rõ, không hứa đều):** độ dài audio mỗi chunk do model sinh ra có phương sai (cùng câu, hai lần chạy cho độ dài khác nhau do sampling temperature/top_k) nên sai số mốc **tăng dần theo số câu** — mục tiêu ±0,3 s/câu áp cho **10 câu đầu**; với bài dài hơn, đo và báo sai số tối đa ở **câu cuối** (T3.1 ghi cả hai số), không hứa ±0,3 s cho mọi câu của bài dài. **Cách đo độc lập (bỏ đo vòng tròn):** T3.1 đo sai số từng mốc bằng **phát hiện khoảng lặng trên sóng âm thật** (ffprobe `silencedetect` / envelope âm lượng) đối chiếu từng mốc, hoặc nghe đối chiếu từng mốc — **không "đo bằng `SrtWriter`"** (đo sản phẩm bằng chính công cụ tạo ra nó). Sai số mục tiêu ±0,3 s/câu (10 câu đầu, đo ở T3.1). Nếu sai số vượt ngưỡng ở Bước 3 thì hạ phạm vi: v1 chỉ xuất .srt ở tab Lồng tiếng (nơi mốc đã có sẵn từ file gốc) | Thiết kế HP |
| `BatchRunner` | Đọc file danh sách (.txt mốc `[P1]`… / .json) hoặc .srt; chạy tuần tự theo hàng đợi; mỗi mục 1 file; xuất ZIP; dừng/tiếp tục khi lỗi. [Sửa R1-TH-16] Ghi audio từng mục ra đĩa ngay sau khi xong (không giữ toàn bộ batch trong RAM); đo peak RAM ở T3.5 với 100 và 500 mục; giới hạn 500 mục/lần là số tạm chờ đo RAM (TK2.6) | VieNeu Desktop, CIT |
| `FileReaders` | Đọc PDF (PyMuPDF — extra `[pdf]` của SDK), DOCX (thư viện **`python-docx`** — nêu tên lần đầu ở v1.2, xem §7/TK1.1), TXT; làm sạch text (bỏ khoảng trắng thừa, giữ công thức). [Sửa R1] Chỉ đọc file người dùng có quyền dùng; UI ghi rõ: không dùng để đọc sách/file có bản quyền rồi phát tán thành audio (bản quyền văn bản đầu vào — điểm mù phản biện R1 xác nhận) | CIT |
| `AudioPost` | Time-stretch giữ cao độ 0,75×–1,5× bằng `librosa.effects.time_stretch` (phase vocoder — xem TH-08/Y4; `soxr` chỉ resample, không dùng để đổi tốc độ); nối chunk + khoảng lặng (kể cả silence từ thẻ `[nghỉ]`); chuẩn hoá; xuất WAV (48 kHz V3 / theo engine V4) + MP3; ghi dần ra đĩa cho bài dài. [Sửa R1-Y1] MP3 mã hoá bằng **FFmpeg đóng gói kèm app** (binary tĩnh qua `imageio-ffmpeg`; fallback sang FFmpeg hệ thống nếu có; không có FFmpeg → chỉ xuất WAV + báo rõ, không báo lỗi chung chung). FFmpeg cũng là bộ giải mã MP3/M4A cho đầu vào clone giọng (chiều ngược của Y1: `soundfile` không giải mã được MP3/M4A). [Sửa R2-Y1] **Số đo thật, bỏ con số "~25–30 MB" của v1.1:** binary Linux trong wheel `imageio-ffmpeg` 0.8.1 là `ffmpeg-linux-x86_64-v9.0.2` = **172.692.552 byte (~165 MB)**, wheel nén 68 MB — đo thật bằng binary trong wheel ngày 19/11/2026; số Windows chưa đo (cùng họ build BtbN full, cùng cấp độ lớn — đo ở TK4.1). Ngân sách bộ cài Q2 (~300–400 MB kèm model) phải cộng thêm ~165 MB này. **License: GPL v3, không phải LGPL** — chạy `ffmpeg -buildconf` trên binary thật: `--enable-gpl --enable-version3 --enable-libx264 --enable-libx265`; license của wrapper `imageio-ffmpeg` là BSD-2-Clause, nhưng license của **binary** là GPL v3 (xem §13.7 + ADR-07). PyInstaller phải collect binary `imageio_ffmpeg/binaries/*` (xem TK4.1/TH-18). Quyết định ghi ở ADR-07 | TH-08; librosa đã là dependency SDK; FFmpeg |
| `PreviewCache` | [Sửa R1-Y7] Nghe thử giọng: V3 dùng mẫu thu sẵn (tạo lần đầu rồi cache trên đĩa, không tổng hợp lại mỗi lần mở tab); V4 preview cache theo khóa (voice_id + câu mẫu) — nghe lần 2 cùng giọng + cùng câu mẫu thì phát file cache, **không gọi lại API**; UI hiện ước tính ký tự trước khi nghe thử V4 lần đầu. [Sửa R2-Y7] Ước tính phí preview phải tính **tối thiểu 50 ký tự/request** (`max(50, len(câu mẫu))` × multiplier — xem TH-05): câu mẫu ≤ 60 ký tự thì lần nghe đầu mỗi giọng tốn 50 ký tự tối thiểu, không phải đúng số ký tự câu mẫu. Câu mẫu preview mặc định ≤ 60 ký tự (đề xuất; chốt ở Q12 §15) | Thiết kế HP |
| `PronDict` | Từ điển phát âm: thêm/sửa/xoá, import/export CSV, áp trước khi infer; giới hạn 2.000 mục (theo VieNeu Studio) | CIT, VieNeu Studio |
| `JobQueue` | Hàng đợi job (tạo → đang chạy → xong/lỗi); tạm dừng khi lỗi (theo VieNeu Desktop); huỷ; thử lại | VieNeu Desktop |
| `HistoryStore` | Lưu bản đã tạo (audio + SRT + metadata: text, giọng, engine, tốc độ, thời gian, dung lượng); nghe/tải lại; **chặn tạo mới khi vượt `max_history_gb`** + báo rõ lý do và hướng xoá/xuất bớt; **không tự xoá**. [Sửa R1-TH-16] Khi vượt `max_history_gb` (mặc định 5 GB): **chặn tạo mới + báo rõ lý do và hướng xoá/xuất bớt** — không chỉ nhắc, vì người dùng có thể bỏ qua nhắc; vẫn cho nghe/tải/xoá bản cũ để mở lại dung lượng | CIT |
| `ConfigStore` | Đọc/ghi `config.yaml` + key V4/key API LAN — xem mục 6. [Sửa R1-Y12] Key lưu qua `keyring` (Windows: DPAPI/Credential Manager; Linux: Secret Service, fallback file `secrets.json` quyền `0600`); không lưu key plaintext trên Windows | — |
| `HpApiServer` | FastAPI, mục 4 | `apps/openai_speech.py` (tham khảo) |

### 3.4. Luồng chính (hành trình "phải dùng được")

1. Mở app → load config → `V3Engine` khởi tạo (tải model lần đầu nếu chưa có, có
   tiến trình) → UI Phòng thu sẵn sàng.
2. Nhập text → chọn giọng (dropdown, nghe thử) → bấm Tạo → job vào hàng đợi →
   engine synthesize → `AudioPost` (tốc độ nếu khác 1×) → ghi WAV/MP3 → History.
3. Hội thoại: nhập kịch bản → gán giọng mỗi nhân vật (khoá) → tạo 1 file.
4. SRT: thả file .srt → xem danh sách câu + mốc → chọn giọng → Lồng tiếng →
   file audio dài đúng bằng video + SRT đã chỉnh mốc (nếu có câu bị lùi).
5. Batch: nhập file danh sách → mỗi mục 1 file → ZIP.
6. API: Annie/MODOLIVIO gọi `POST /api/tts/generate` trên loopback → nhận WAV.

---

## 4. API LOCAL (lớp 2)

Base mặc định: `http://127.0.0.1:8124` (port cấu hình được, xem mục 6; **không
hardcode 8001** — CIT dùng 8001, upstream dùng 8000/7860/23333).

**[Sửa R1-🔴 R1] Cổng mặc định đổi từ `8123` sang `8124`.** Lý do: `8123` đã có
chủ — server TTS của MODOLIVIO chạy ở `127.0.0.1:8123` trên máy anh (nghiên cứu
nền §5.2; đổi từ 8000 ngày 16/11). SPEC v1.0 chọn đúng cổng đó rồi hỏi ở §15 Q1
"có cổng nào trùng không?" như thể chưa biết — câu trả lời đã nằm trong hồ sơ
dự án. Bảng cổng đã chiếm (đã biết, kiểm tra lại thật trên máy anh ở C8):

| Cổng | Chủ sở hữu | Nguồn |
|---|---|---|
| 5678 | n8n (máy Annie) | MEMORY.md |
| 7860 | Gradio demo upstream (`vieneu-web`) | `apps/gradio_main.py` |
| 8000 | API server tương thích OpenAI của upstream | `apps/openai_speech.py` |
| 8001 | CIT Voice Studio + streaming demo upstream | CIT README; `apps/web_stream.py` |
| **8123** | **Server TTS của MODOLIVIO** | Nghiên cứu nền §5.2 |
| **8124** | **HP Voice Studio (mặc định mới)** | SPEC này |
| 8765 / 8766 | Ebook Library (production / staging) | MEMORY.md |
| 23333 | Launcher `serve.py` của upstream | `src/vieneu/serve.py` |

Quy tắc kiểm tra trùng cổng (bắt buộc, TK2.1): (a) `scripts/check_port.py`
quét cổng 8124 trên máy chạy trước khi chốt; (b) server khi khởi động thử bind
8124 — nếu bận thì **fail-fast**: thoát với thông báo rõ ("cổng 8124 đã bị chiếm,
có thể bởi <dịch vụ theo bảng trên nếu nhận diện được>, đổi `server.port` trong
config rồi chạy lại"), **không tự nhảy sang cổng khác trong im lặng** (cổng
tự nhảy làm client gọi sai đích — đúng lỗi R1 cảnh báo); (c) C8 kiểm tra lại
toàn bộ bảng trên máy anh trước khi chốt phát hành.

[Sửa R1-Y6] **Giới hạn độ dài text / batch (mới):** upstream giới hạn `input`
tối đa **20.000 ký tự** (`apps/openai_speech.py:310` `max_length=20_000`) — HP
lấy đúng giới hạn này cho mỗi request TTS (`POST /api/tts/generate`,
`/v1/audio/speech`, `/api/tts/stream`): vượt → **400 + thông báo rõ giới hạn**.
Mỗi mục batch tối đa 20.000 ký tự; batch tối đa 500 mục/lần (số tạm chờ đo RAM,
TK2.6). Đồng thời: HP chỉ chạy **1 job TTS đồng thời** trên CPU — request TTS
thứ 2 khi đang bận sẽ **xếp hàng** (trả `202` + `job_id` để poll), không trả 429;
chỉ trả 429 khi hàng đợi đầy (giới hạn hàng đợi: 20 job chờ — **SUY LUẬN**, chốt
ở Bước 2). "Rate limit nội bộ" (§4, bảng giới hạn ở đầu mục này) từ nay có số cụ thể này, không còn chung chung. [Sửa R2-Y6 💭] Hàng đợi chưa có thời gian chờ tối đa: job chờ quá **60 phút** thì tự hủy + báo "hết thời gian chờ, gửi lại" (60 phút là **SUY LUẬN**, chốt ở Bước 2 — 20 job × 20.000 ký tự có thể là nhiều giờ chờ nếu không có TTL).

Auth: loopback không cần key; **LAN opt-in bắt buộc `X-API-Key`** (TH-06).
Mọi response lỗi dùng HTTP status + JSON `{ "error": { "code", "message" } }`.

| # | Method + Path | Việc | Request chính | Response |
|---|---|---|---|---|
| 1 | `GET /health` | Trạng thái server + engine | — | `{ status, engine: "v3"\|"v4", v3_ready, v4_configured, version }` |
| 2 | `GET /voices` | Danh sách giọng (preset + clone, kèm giới tính/vùng/phong cách/engine) | `?engine=v3\|v4` | `[{ id, name, gender, region, style, engine, featured }]` |
| 3 | `GET /voices/{id}/preview` | Nghe thử giọng (câu mẫu ngắn) | — | audio WAV (V3: mẫu thu sẵn/cache; V4: cache theo voice_id + câu mẫu, hiện ước tính ký tự trước khi nghe — xem `PreviewCache` §3.3, Y7) |
| 4 | `POST /api/tts/generate` | Text → audio | `{ text, voice_id, engine?, speed?, format: "wav"\|"mp3", response_format? }` | [Sửa R2-Y6 💭] **Hai dạng trả** (ghi cả hai vào `docs/api-contract.md` ở Bước 2): CPU rảnh → **200 + audio bytes** (WAV/MP3) + header `X-Engine`, `X-Duration-Sec`; CPU đang bận → **202 + `{ job_id }`** để poll (endpoint 11). Client phải xử lý cả hai dạng, không giả định luôn 200 |
| 5 | `POST /api/tts/generate-with-subtitles` | Audio kèm phụ đề .srt (khớp từng câu, mốc suy bằng `SrtWriter` §3.3) | như (4) | [Sửa R1-Y11] **Một dạng duy nhất: ZIP đồng bộ** (audio + .srt) cho text ≤ 20.000 ký tự; text dài hơn → 400 (giới hạn Y6), dùng tab Lồng tiếng/batch thay thế. Không còn phương án "ZIP hoặc JSON" — hợp đồng cố định trong `docs/api-contract.md` (Bước 2). [Sửa R2 💭] ZIP đồng bộ cho text 20.000 ký tự (~25 phút audio, tạo mất nhiều phút) có thể vượt timeout HTTP của client/proxy: text **> 5.000 ký tự** → trả **`job_id` (async, poll endpoint 11)** thay vì giữ kết nối chờ ZIP (ngưỡng 5.000 là **SUY LUẬN**, chốt ở Bước 2 theo số đo thời gian tạo) |
| 6 | `POST /api/tts/stream` | Đọc theo thời gian thực (chunked) | như (4) | stream audio (chunked; V3 dùng `infer_stream`) |
| 7 | `POST /api/tts/conversation` | Hội thoại nhiều người nói | `{ lines: [{ speaker, text }], speakers: { name: voice_id }, format }` | 1 file audio |
| 8 | `POST /api/tts/srt-dub` | Lồng tiếng theo file .srt | multipart `.srt` + `{ voice_id, engine?, keep_timing }` | audio + `.srt` đã chỉnh mốc (nếu có) |
| 9 | `POST /api/tts/batch` | Tạo hàng loạt | `{ items: [{ id, text, voice_id? }], format }` hoặc file upload | `{ job_id }` → poll (11); xong trả ZIP |
| 10 | `POST /api/voices/clone` | Clone giọng từ clip (cần cam kết) | multipart audio + `{ name, consent: true, consent_text }` | `{ voice_id }`; thiếu consent → 400 |
| 11 | `GET /api/jobs/{job_id}` | Trạng thái job | — | `{ status, progress, result_url?, error? }` |
| 12 | `GET /api/history` | Danh sách bản đã tạo | `?limit&offset` | `[{ id, created_at, text_preview, voice, engine, duration_sec, size_bytes, format }]` |
| 13 | `GET /api/history/{id}` | Tải lại bản đã tạo | — | audio bytes |
| 14 | `DELETE /api/history/{id}` | Xoá 1 bản | — | 204 |
| 15 | `GET /api/dict` / `POST /api/dict` | Từ điển phát âm (đọc/ghi) | `{ word, reading }` | danh sách / 201 |
| 16 | `GET /api/config` / `POST /api/config` | Cài đặt (giọng mặc định, model, thư mục) — **không trả key** | — | config (key che `****`) |
| 17 | `POST /api/config/v4-key` | Nhập/xoá key V4 | `{ api_key }` | `{ configured: true }`; key **không bao giờ** trả lại hay log |
| 18 | `POST /v1/audio/speech` | **Tương thích OpenAI** (để Annie/tool khác dùng SDK OpenAI) | `{ input, model, voice, response_format: "wav"\|"mp3", speed? }` | audio bytes (MP3 qua FFmpeg đóng gói kèm — upstream chỉ có wav/pcm, HP thêm mp3 theo ADR-07; `speed` nếu chưa hỗ trợ thì báo header `X-VieNeu-Ignored: speed`, không lặng lẽ bỏ) |
| 19 | `GET /v1/voices` | Tương thích OpenAI: danh sách giọng | — | `[{ id, name }]` |
| 20 | `GET /v1/models` | Tương thích OpenAI: model | — | `[{ id: "v3-turbo" / "v4" }]` |

**Hợp đồng + kiểm thử (api-contract-compatibility-testing-vn):** mỗi endpoint có
schema request/response cố định trong `docs/api-contract.md` (viết ở Bước 2); test
tương thích chạy trước mỗi release: V3/V4 voice id không lẫn (V4 voice qua V3 → 400
rõ ràng, và ngược lại); `POST /v1/audio/speech` chạy được bằng OpenAI Python SDK
trỏ `base_url` về HP API (như ví dụ của upstream).

**Giới hạn:** 1 job TTS đồng thời trên CPU (hàng đợi tuần tự — request thứ 2
xếp hàng, trả `202` + `job_id`; hàng đợi đầy 20 job → 429; GPU mới xét song song);
text tối đa/chunk 256 ký tự (SDK tự chia); mỗi request TTS tối đa **20.000 ký tự**
(vượt → 400, xem Y6 ở đầu §4); [Sửa R1-G4] file SRT: **chưa rõ giới hạn** — con
số 100.000 câu/tệp của VieNeu Desktop là giới hạn **Tạo hàng loạt**, không phải
SRT dub; SPEC v1.0 gán nhầm. Giới hạn SRT dub đo ở Bước 3 (TK2.5), trước đó không
ghi số; batch tối đa 500 mục/lần
(**SUY LUẬN** — số tạm chờ đo RAM ở Bước 2, xem G6/Q4 §15).

---

## 5. UI — TAB VÀ MÀN HÌNH (giữ cấu trúc studio chuẩn)

Nhóm tab theo **Tạo / Thư viện / Hệ thống** (cấu trúc chung của VieNeu Desktop +
CIT; HP chỉ đổi thương hiệu/nội dung, không phát minh bố cục mới, không lấy
logo/thương hiệu của họ).

```
┌──────────────────────────────────────────────────────────────┐
│ HP Voice Studio        [Engine: V3 local ▾]  [Trạng thái]    │
├──────────┬───────────────────────────────────────────────────┤
│ TẠO      │                                                   │
│  Phòng thu                                                │
│  Hội thoại / Podcast                                      │
│  Lồng tiếng .srt                                          │
│  Đọc file                                                 │
│  Tạo hàng loạt                                            │
│ THƯ VIỆN │  (nội dung tab đang chọn)                         │
│  Bản đã tạo                                               │
│  Giọng của tôi (clone)                                    │
│ HỆ THỐNG │                                                   │
│  Cài đặt                                                  │
└──────────┴───────────────────────────────────────────────────┘
```

| Tab | Nội dung (đầy đủ, không cắt) | Bằng chứng "dùng được" (mục 10) |
|---|---|---|
| **Phòng thu / TTS Studio** | Ô nhập text (đếm ký tự); dropdown Giọng đọc (25 preset + clone, ghi rõ giới tính/vùng/phong cách, nghe thử từng giọng); chọn Engine V3/V4 (V4 hiện phí/ký tự); tốc độ 0,75×–1,5×; nút chèn cảm xúc `[cười]` `[thở dài]` `[hắng giọng]`, thẻ nghỉ `[nghỉ 2s]`/`[nghỉ 500ms]` (tối đa 10 s/thẻ — [Sửa R1-Y2] thẻ nghỉ do tầng app `TextPreprocess` xử lý, SDK không có sẵn); từ điển phát âm (nút Từ điển, CSV import/export); nút Tạo; trình phát nghe lại; xuất WAV/MP3 (MP3 qua FFmpeg, ADR-07); tạo kèm .srt (mốc suy bằng `SrtWriter`, ±0,3 s/câu — Y3); hàng đợi (nhiều bản đọc xếp hàng, tạo bản sau trong lúc bản trước phát, nút Dừng phát) | T1.2, T2.2, T2.10, T3.1 |
| **Hội thoại / Podcast** | Bảng kịch bản: mỗi dòng (nhân vật, lời thoại); mỗi nhân vật gán 1 giọng cố định (dropdown, khoá); thêm/xoá nhân vật (tối đa 8); khoảng lặng giữa lượt; ghép thành 1 file; lưu/mở kịch bản | T3.2 |
| **Lồng tiếng .srt** | Thả file .srt/.vtt → danh sách câu + mốc giờ; chọn giọng + tốc độ; bấm Lồng tiếng; tiến trình từng câu; kết quả: audio dài đúng bằng video + SRT đã chỉnh mốc (nếu câu bị lùi) + danh sách câu bị lùi; quy tắc: câu dài đọc nhanh tối đa 1,5×, không cắt chữ | T3.3 |
| **Đọc file** | Thả PDF/DOCX/TXT → xem trước text → Làm sạch (bỏ khoảng trắng thừa, giữ công thức) → chuyển sang Phòng thu tạo giọng | T3.4 |
| **Tạo hàng loạt** | Nhập trực tiếp (mốc `[P1]`, `[P2]`…) hoặc tải file .txt/.json; mỗi mốc 1 file; tải từng file / tải tất cả (.zip); tiến trình từng mục; mục lỗi thử lại riêng | T3.5 |
| **Bản đã tạo** | Danh sách bản đã tạo (tên, giọng, engine, thời lượng, dung lượng, ngày); nghe lại, tải lại WAV/MP3/SRT, mở thư mục chứa file; xoá; hiển thị tổng dung lượng + **chặn tạo mới khi vượt `max_history_gb`** (TH-16) | T3.6 |
| **Giọng của tôi** | Danh sách giọng clone (tên, ngày tạo, cam kết); thu micro 3–8 s hoặc nhập file MP3/WAV/M4A (MP3/M4A giải mã bằng FFmpeg — Y1); màn hình cam kết quyền sử dụng (bắt buộc); nghe thử; xoá (xoá cùng cam kết; có cơ chế gỡ khi bị khiếu nại — TH-17) | T2.5 |
| **Cài đặt** | Giọng mặc định; model (precision fp32/int8 + tự phát hiện CPU, threads); thư mục lưu + thư mục model/cache; Engine V4: nhập/xoá key, hiện trạng thái (chưa có key / key hợp lệ / lỗi), ước tính phí, ngưỡng cảnh báo ký tự; API local: cổng, bật/tắt LAN + khoá API, nút tạo khoá mới; giao diện sáng/tối; giới thiệu + giấy phép + ghi công VieNeu-TTS | T3.7 (phần key V4: T2.6) |

**Quy tắc UI chung:** full-page, 1 màn hình 1 hành động chính; dropdown chọn giọng
(theo quy tắc MODOLIVIO: không liệt kê dài ngoài màn hình); tiếng Việt; mọi lỗi
hiện rõ lý do + cách sửa (không báo "lỗi chung chung"); V4 luôn ghi rõ "tính phí
theo ký tự" trước khi gửi.

**KHÔNG làm ở v1:** trợ lý AI viết kịch bản (LLM bên thứ ba), LoRA fine-tune,
giọng nước ngoài (Supertonic/Kokoro), Dubbing/Lecture/TikTok Reel/Audiobook
của official VieNeu App (README ghi rõ chỉ có trong app chính chủ).

---

## 6. CONFIG — KHÔNG HARDCODE

File `config.yaml` (người dùng sửa được, có ghi chú tiếng Việt) + key V4/key API
LAN lưu qua `keyring` (Windows: DPAPI/Credential Manager; xem TH-05/Y12 — **không**
lưu key plaintext trên Windows; file `secrets.json` chỉ còn là fallback trên
Linux khi không có keyring, quyền `0600`, **không commit git**):

```yaml
# HP Voice Studio — config (mẫu; đường dẫn mặc định theo OS, không hardcode máy)
app:
  name: "HP Voice Studio"
  language: "vi"
server:
  host: "127.0.0.1"      # mặc định loopback; "0.0.0.0" chỉ khi bật LAN trong Cài đặt
  port: 8124             # [Sửa R1-R1] mặc định mới — 8123 đã có chủ (server TTS MODOLIVIO); xem bảng cổng §4
  lan_enabled: false
  # api_key_file: secrets.json (không ghi key vào file này)
  # Khởi động: bind 8124 thất bại → fail-fast + báo rõ (không tự nhảy cổng); xem §4
engine:
  default: "v3"          # "v3" | "v4"
  v3:
    backbone_repo: "pnnbao-ump/VieNeu-TTS-v3-Turbo"
    precision: "auto"    # "auto" (theo CPU: VNNI→int8, không→fp32) | "fp32" | "int8"
    threads: 0           # 0 = mặc định SDK
    max_batch_size: 32
    model_dir: ""        # trống = cache HF mặc định; đặt đường dẫn để đóng gói sẵn model
  v4:
    base_url: "https://api.vieneu.io/api/v1"
    model: "v4"
    fallback_to_v3: true
    warn_chars: 100000   # ngưỡng cảnh báo ký tự/phiên (người dùng đổi được)
    timeout_sec: 60
    max_retries: 1       # chỉ retry lỗi 5xx/timeout, không retry 4xx
audio:
  default_voice: "Hải Đăng"
  default_speed: 1.0     # 0.75–1.50
  default_format: "wav"  # "wav" | "mp3"
  mp3_encoder: "ffmpeg"  # [Sửa R1-Y1/ADR-07] FFmpeg đóng gói kèm (imageio-ffmpeg); không có FFmpeg → chỉ xuất WAV
  preview_sample: "Xin chào, đây là giọng đọc mẫu của HP Voice Studio."  # ≤ 60 ký tự (Q12 §15)
  sample_rate_v3: 48000
api:
  max_text_chars: 20000  # [Sửa R1-Y6] mỗi request TTS; vượt → 400 (như upstream)
  max_batch_items: 500   # số tạm chờ đo RAM (TK2.6)
  max_queue_jobs: 20     # hàng đợi đầy → 429
storage:
  output_dir: ""         # trống = thư mục mặc định theo OS (xem README)
  history_dir: ""        # trống = <data>/history
  voices_file: ""        # trống = <data>/voices.json (giọng clone — KHÔNG ghi vào package)
  dict_file: ""          # trống = <data>/pronunciation-dict.json
  max_history_gb: 5      # nhắc dọn khi vượt
```

Thư mục dữ liệu theo OS (theo tiền lệ CIT — **SUY LUẬN** lấy theo, chốt ở Bước 4):
Windows `%LOCALAPPDATA%\HPVoiceStudio\`, Linux `~/.local/share/HPVoiceStudio/`
(hoặc `~/HPVoiceStudio/`), macOS `~/Library/Application Support/HP Voice Studio/`.
Model V3: cache HF (`HF_HOME`) hoặc `model_dir` trong config.

```json
// secrets.json — CHỈ fallback trên Linux khi không có keyring (quyền 0600).
// Trên Windows key lưu qua keyring/DPAPI, KHÔNG lưu plaintext trong file này.
// KHÔNG commit, KHÔNG log, KHÔNG đọc ra ngoài app.
{ "v4_api_key": "<người dùng nhập trong Cài đặt>", "lan_api_key": "<tự sinh khi bật LAN>" }
```

---

## 7. CẤU TRÚC THƯ MỤC `~/workspace/hp-voice-studio/`

```
hp-voice-studio/
├── SPEC.md                  # file này (draft phân tích → chốt sau phản biện)
├── README.md                # hướng dẫn dùng (viết ở Bước 4)
├── LICENSE                  # Apache 2.0 của HP Voice Studio (riêng, không copy nguyên file của upstream — xem G7 §13)
├── NOTICE                   # ghi công VieNeu-TTS + tác giả + license giọng + license FFmpeg — Bước 4
├── .gitignore               # upstream-vieneu-tts/, models/, outputs/, secrets.json, *.wav...
├── upstream-vieneu-tts/     # clone CHỈ ĐỌC để tham khảo (không commit, không sửa)
├── config.example.yaml      # mẫu config (mục 6)
├── requirements.txt         # vieneu==3.8.4 + fastapi + uvicorn + ... (ghim version)
├── pyproject.toml           # (Bước 2) metadata + test config
├── src/hpvoice/
│   ├── __init__.py
│   ├── config.py            # ConfigStore
│   ├── engines/
│   │   ├── base.py          # interface Engine chung
│   │   ├── v3_engine.py     # V3Engine (adapter SDK)
│   │   ├── v4_engine.py     # V4Engine (Cloud API)
│   │   └── router.py        # EngineRouter + fallback
│   ├── audio/
│   │   ├── post.py          # AudioPost (tốc độ, nối, xuất — MP3 qua FFmpeg)
│   │   ├── text_preprocess.py # [Sửa R1-Y2] TextPreprocess (thẻ [nghỉ]/cảm xúc)
│   │   ├── srt_writer.py    # [Sửa R1-Y3] SrtWriter (suy mốc giờ audio → .srt)
│   │   ├── conversation.py  # ConversationEngine
│   │   ├── srt_dub.py       # SrtDubber
│   │   └── batch.py         # BatchRunner
│   ├── voices/
│   │   ├── store.py         # VoiceStore (preset + clone; V4 khóa theo `id`)
│   │   ├── preview_cache.py # [Sửa R1-Y7] PreviewCache (nghe thử V3/V4)
│   │   └── pron_dict.py     # PronDict
│   ├── files/
│   │   └── readers.py       # PDF/DOCX/TXT
│   ├── jobs/
│   │   ├── queue.py         # JobQueue
│   │   └── history.py       # HistoryStore
│   └── api/
│       ├── server.py        # HpApiServer (FastAPI)
│       ├── schemas.py       # request/response schema
│       └── auth.py          # LAN X-API-Key
├── ui/                      # web UI local (HTML/JS, gọi API loopback)
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── tests/
│   ├── test_v3_engine.py    # cần model thật (chạy ở Bước 1)
│   ├── test_api.py          # mock engine, không cần model
│   ├── test_srt.py
│   ├── test_batch.py
│   └── test_conversation.py
├── scripts/
│   ├── download_model.py    # tải model lần đầu + kiểm tra checksum
│   ├── check_port.py        # [Sửa R1-R1] kiểm tra cổng 8124 trống/trùng trước khi chạy
│   ├── run_server.py        # chạy API server
│   └── build_windows.py     # đóng gói .exe (Bước 4 — chạy trên GitHub Actions Windows runner, TK4.1)
├── packaging/
│   └── windows/             # Inno Setup / PyInstaller spec (Bước 4)
├── docs/
│   ├── api-contract.md      # hợp đồng API (Bước 2)
│   └── decisions/           # ADR (ADR-01...)
└── outputs/                 # WAV/test tạm (không commit)
```

**Quy tắc:** `upstream-vieneu-tts/` không commit (đã cho vào `.gitignore`);
không commit `secrets.json`, model, file WAV, `__pycache__`, `.venv`.

---

## 8. MÔ HÌNH DỮ LIỆU (rút gọn)

- **Job:** `{ id, kind: tts|conversation|srt|batch|clone, status: queued|running|done|error,
  progress, engine, voice_id, speed, input_ref, output_path, error_code, error_message, created_at }`
- **HistoryItem:** `{ id, created_at, text_preview, voice_id, engine, speed, format,
  duration_sec, size_bytes, audio_path, srt_path? }`
- **ClonedVoice:** `{ id, name, created_at, consent: { text, agreed_at }, ref_info:
  { duration_sec, denoised }, embedding_path }` — không lưu file ref gốc.
- **PronDictEntry:** `{ word, reading }` (tối đa 2.000 mục).
- **ConversationScript:** `{ title, speakers: { name: voice_id }, lines: [{ speaker, text }] }`

---

## 9. TÍNH ĐỦ HAI KỊCH BẢN (Charter §4 — phân tích + thiết kế sẵn + mốc kích hoạt)

### 9.1. Kịch bản A — Dùng cá nhân (v1, hiện tại)

- Kinh tế: chi phí = 0 (V3 local miễn phí) + điện/máy sẵn có; V4 chỉ khi người dùng
  tự mua token, tự chịu phí theo ký tự.
- Pháp lý: dùng cá nhân, không phân phối lại; tuân TH-01 (không dùng GGUF Q4,
  không phân phối lại `voices.json` cũ); clone chỉ giọng có phép + cam kết.
- Vận hành: 1 người dùng/máy; không cần tài khoản, không server trung tâm,
  không thu thập dữ liệu; cập nhật thủ công (tải bản mới).

### 9.2. Kịch bản B — Thương mại sau này (CHƯA làm, đã phân tích + thiết kế sẵn)

| Hạng mục | Phân tích | Thiết kế sẵn trong v1 | Mốc kích hoạt |
|---|---|---|---|
| Kinh tế đơn vị | V3 local: chi phí biên ~0/audio (điện + khấu hao máy). V4: phí theo ký tự/token — giá gói tham khảo (trang chủ 18/11): Starter 99Kđ ~4 giờ/400.000 token; Creator 299Kđ ~13 giờ/1,5M; Pro 799Kđ ~44 giờ/5M; Studio 1,69Mđ ~105 giờ/12M; tháng 499Kđ ~35 giờ/4M. **Số này phải đọc lại từ docs.vieneu.io khi tới mốc**. [Sửa R1-§7] Chưa có mô hình giá bán lại (bán theo ký tự? theo giờ audio? markup bao nhiêu?) và chưa có chi phí vận hành/hỗ trợ/cập nhật — bổ sung ở mốc thương mại, không xây ngay | `EngineRouter` đã tách V3/V4; `V4Engine` đếm ký tự từng job → có sẵn dữ liệu tính giá vốn; config `warn_chars` | Khi anh nói "bán/chia sẻ rộng" hoặc doanh thu V4 > 0 |
| Bản quyền/pháp lý | TH-01: license giọng v3 Turbo chưa rõ ràng tuyệt đối (Apache 2.0 repo vs CC BY-NC trong `voices.json` cũ); V4 độc quyền, chỉ qua API; GGUF Q4 CC BY-NC cấm thương mại. [Sửa R1-G12/TH-17] Bổ sung: (a) license **phân phối lại weight** trong bộ cài — weight v3 Turbo theo model card Apache 2.0, phải xác nhận lại trước khi phân phối bộ cài kèm model; (b) điều khoản VieNeu có cho **bán lại V4 dưới dạng dịch vụ** không — v1.0 giả định "người dùng tự mua token" thì né được, nhưng kịch bản B có "dịch vụ lồng tiếng" (đó là bán lại), phải đọc điều khoản Cloud API trước mốc thương mại; (c) luật VN: giọng nói là dữ liệu cá nhân (Nghị định 13/2023), nội dung AI phải ghi nhãn (Nghị định 147/2024) — UI/Cài đặt ghi rõ từ v1 (TH-17) | NOTICE + ghi công từ v1; không dùng Q4; log cam kết clone; cơ chế gỡ giọng khi khiếu nại (TH-17) | **Bắt buộc trước khi thương mại:** xin xác nhận license giọng v3 Turbo bằng văn bản từ tác giả (pnnbao-ump) + rà soát lại `voices_v3_turbo.json` + điều khoản V4 (bán lại) + license phân phối weight |
| Thanh toán | Chưa có. V4 do người dùng tự mua token trực tiếp với VieNeu (app không bán token, không thu tiền hộ) | Không xây cổng thanh toán; app chỉ dùng key người dùng nhập | Khi bán gói dịch vụ dùng HP Studio (VD: dịch vụ lồng tiếng) → thiết kế riêng, không nhét vào v1 |
| Vận hành | 1 máy → nhiều máy: cần cập nhật tự động, báo lỗi từ xa, đồng bộ giọng clone (có phép) | Config + thư mục dữ liệu tách bạch (mục 6–7) để sau này thêm auto-update/sync; `JobQueue` + `HistoryStore` đã có id ổn định | Khi có >1 người dùng thường xuyên hoặc yêu cầu cập nhật tự động |
| Hạn mức nhà cung cấp | V4: quota token theo gói; hết quota → job lỗi; Cloud API có thể đổi giá/endpoint | Fallback V3 tự động (TH-05); `V4Engine` xử lý 429/402 riêng, báo rõ "hết quota" | Khi dùng V4 thường xuyên: thêm màn hình số dư/quota (cần endpoint số dư — **CHƯA RÕ** có API số dư không, kiểm tra ở Bước 2; nếu không có endpoint thì phương án dự phòng là **tự đếm ký tự đã gửi** — dữ liệu đã có từ `V4Engine`) |
| Quyền riêng tư | Nội dung qua V4 cloud rời khỏi máy (text gửi lên API); V3 local không rời máy. [Sửa R1-§7] Chưa có chính sách lưu trữ/xoá dữ liệu người dùng (text, giọng clone, lịch sử) khi có nhiều người dùng | UI ghi rõ: V3 = trên máy, V4 = gửi text lên cloud; mặc định V3; text/giọng clone chỉ lưu local, không đồng bộ cloud trừ khi người dùng bật | Khi xử lý text nhạy cảm: mặc định V3, cảnh báo trước khi gửi V4. Khi có >1 người dùng: viết chính sách lưu trữ/xoá + cơ chế gỡ giọng (TH-17) |

> Không gạt bỏ kịch bản B với lý do "chưa cần" — bảng trên là phân tích +
> thiết kế sẵn + mốc kích hoạt theo Charter §4. Nhưng **không xây** thanh toán,
> tài khoản, server trung tâm trong v1.

---

## 10. TIÊU CHÍ "PHẢI DÙNG ĐƯỢC" — KIỂM CHỨNG CHẠY THẬT TỪNG TÍNH NĂNG

> Mỗi tính năng phải có **lệnh chạy + file ra + cách đo** cụ thể. Không checklist suông.
> Bằng chứng: file WAV thật / response API thật / test log / ảnh chụp UI.
> Phân loại: **kiểm chứng thật** (máy/tài khoản thật của anh) vs **kiểm chứng sandbox/CI**
> (máy Annie) — ghi rõ loại, không nhập nhèm (skill verification-before-completion-team).
> [Sửa R1-R3] ID test ở mục này dùng namespace `T…`; ticket công việc ở mục 12
> dùng `TK…` — tham chiếu "TKx.y" nghĩa là ticket, "Tx.y" nghĩa là test.

### Bước 1 — Engine V3 + WAV thật

| ID | Tính năng | Kiểm chứng chạy thật (lệnh / file ra / cách đo) | Đạt khi |
|---|---|---|---|
| T1.1 | Cài SDK + tải model | `pip install vieneu==3.8.4` (hoặc `uv sync` từ repo); chạy `scripts/download_model.py`; đo dung lượng cache HF trước/sau **từng thành phần** (`du -sh ~/.cache/huggingface` trước/sau từng bước: backbone, codec, speaker-encoder/denoiser, tokenizer) + thời gian tải. [Sửa R1-Y10] Sau khi tải xong: **chặn mạng hoàn toàn, khởi động lại app, tạo WAV** — kiểm tra không còn gọi HF | Model tải xong, ghi rõ tổng dung lượng **theo từng thành phần** vào README; lỗi mạng → báo rõ + thử lại được; chặn mạng vẫn tạo được WAV mới là "offline hoàn toàn", nếu không thì ghi rõ thành phần còn thiếu |
| T1.2 | WAV thật giọng preset | `python -c "from vieneu import Vieneu; v=Vieneu(); a=v.infer('Xin chào các bạn!', voice='Hải Đăng'); v.save(a,'outputs/t1_2.wav')"`; kiểm tra file: `ffprobe outputs/t1_2.wav` (48 kHz, mono), thời lượng > 0, nghe thử | WAV 48 kHz thật, nghe rõ tiếng Việt, đúng giọng preset |
| T1.3 | Liệt kê 25 giọng | `v.list_preset_voices()` → đếm = 25, có đủ 10 featured ⭐, default "Hải Đăng" | Khớp bảng §2.2; sai tên → ValueError rõ ràng |
| T1.4 | Hiệu năng CPU | Đo RTF: tạo 60 s audio, `RTF = thời gian xử lý / thời lượng audio` (script như README); thử cả fp32 và int8; ghi CPU máy đo. [Sửa R1-Y9/G9] Ghi rõ CPU tham chiếu (máy đo là CPU nào, có VNNI không — kiểm tra precision tự chọn đúng trên cả máy có VNNI và máy không có VNNI; không phát hiện được → mặc định fp32). [Sửa R1-§5] Mục tiêu RTF ≤ 1 gắn với CPU tham chiếu là **CPU máy anh, đo ở C6** — số RTF trên CPU khác chỉ để tham khảo, không thay cho số trên máy anh | RTF ≤ 1 trên CPU 4 nhân (fp32 hoặc int8); int8 méo tiếng → fallback fp32 + ghi chú; precision tự chọn đúng theo VNNI |
| T1.5 | Stream | `infer_stream()` → chunk đầu tiên về trong ≤ 500 ms trên CPU (mục tiêu; README ghi ~140 ms int8 / ~300 ms fp32). [Sửa R1-§5] Đo thêm độ trễ **chunk thứ 2 trở đi** (không chỉ chunk đầu) | Nghe được audio ngay khi đang tạo (không chờ hết câu); chunk sau không trễ hơn 500 ms/chunk |
| T1.6 | Batch | `infer_batch([10 câu])` → 10 file, đúng thứ tự, đúng giọng. [Sửa R1-G8] Bỏ tiêu chí cũ "thời gian ≤ 10× infer đơn" (hiển nhiên đúng, không đo được gì) | Không lẫn câu/giọng; **RTF batch không tệ hơn 1,2× RTF infer đơn** trên cùng CPU |
| T1.7 | Thời gian khởi động | [Sửa R1-G9] Đo từ lúc mở app tới khi sẵn sàng tạo (model đã tải sẵn): ghi thời gian load model fp32/int8 riêng (README ghi int8 "load ~14 s", fp32 chưa rõ) | Sẵn sàng tạo trong ≤ 30 s trên máy anh (mục tiêu, đo thật ở C1); quá 30 s thì hiện tiến trình load, không đứng hình |

### Bước 2 — API local

| ID | Tính năng | Kiểm chứng | Đạt khi |
|---|---|---|---|
| T2.1 | `GET /health`, `GET /voices` | [Sửa R1-R1] `python scripts/check_port.py` (8124 trống, không trùng bảng §4) rồi `curl http://127.0.0.1:8124/health`, `/voices` → JSON 200, đủ 25 giọng. Cố ý curl 8123 phải trả về MODOLIVIO (không phải HP) — test pass giả nếu nhầm cổng | Response thật từ HP (kiểm tra `version` trong `/health`), đúng schema `docs/api-contract.md` |
| T2.2 | `POST /api/tts/generate` | `curl -X POST .../api/tts/generate -d '{"text":"...","voice_id":"Mai Anh"}'` → WAV 48 kHz; test bằng OpenAI SDK trỏ `base_url` về HP (`/v1/audio/speech`) | WAV thật + OpenAI SDK gọi được |
| T2.3 | Stream API | `POST /api/tts/stream` → chunk đầu ≤ 1 s | Stream thật, không chờ hết |
| T2.4 | Tốc độ 0,75×–1,5× | Tạo cùng câu ở 1,0× và 1,5×; đo thời lượng bằng `ffprobe` → tỉ lệ ≈ 1/1,5 (±10%), nghe không méo nặng. [Sửa R1-Y4/G8] Đo thêm **RTF của bước time-stretch** (`librosa.effects.time_stretch`, thời gian xử lý / thời lượng audio); tốc độ 1,0× không qua time-stretch (không tốn thời gian xử lý thêm) | Đúng tỉ lệ, nghe được; RTF time-stretch ghi rõ số đo (không có mục tiêu cứng ở v1, chỉ ghi số thật) |
| T2.5 | Clone giọng | Thu/nhập clip 3–8 s của chính anh (có cam kết) → `POST /api/voices/clone` → tạo câu bằng giọng clone → nghe thử; thử clip không cam kết → 400 | Giọng clone nghe giống mẫu; không cam kết thì bị chặn |
| T2.6 | V4 (hỏi Annie trước, không tự test bằng key anh) | Nhập key test do người dùng cung cấp trong Cài đặt → `POST /api/tts/generate {"engine":"v4","voice_id":"Hạ Vy"}` → WAV; rút key / giả lỗi mạng → fallback V3 + báo rõ lý do. [Sửa R1-§5] Test thêm từng mã riêng: key sai → 401, hết quota → 402, quá tải → 429 — mỗi mã báo đúng lý do (không gộp thành "lỗi V4") | V4 ra WAV thật; fallback đúng + báo lý do; 401/402/429 phân biệt được |
| T2.7 | LAN + key | Bật LAN + key → gọi từ máy khác có key → 200; không key → 401; gọi `/api/history` từ LAN → 403 | Đúng phân quyền TH-06 |
| T2.8 | Test tự động | `pytest tests/test_api.py` (mock engine) → 100% pass; `pytest tests/` (cần model) → pass trên máy có model | Test log đính kèm, 0 lỗi |
| T2.9 | Giới hạn text/batch + hàng đợi | [Sửa R1-Y6] Gửi text 20.001 ký tự → 400 + thông báo giới hạn; gửi batch 501 mục → 400; gửi 2 request TTS đồng thời → request 2 xếp hàng (202 + `job_id`), không 429; lấp hàng đợi 20 job → 429 | Đúng giới hạn §4; hành vi vượt giới hạn đúng như thiết kế |
| T2.10 | Nghe thử + MP3 | [Sửa R1-Y1/Y7] `GET /voices/{id}/preview` giọng V3 lần 2 → trả từ cache (không tổng hợp lại); giọng V4 lần 2 cùng câu mẫu → trả từ cache (không gọi lại API); `POST /api/tts/generate {"format":"mp3"}` → file MP3 thật (kiểm tra bằng `ffprobe`); khi FFmpeg bị gỡ → chỉ WAV + báo rõ | Preview cache đúng; MP3 thật; thiếu FFmpeg thì WAV vẫn chạy + báo rõ |

### Bước 3 — UI đủ tab

| ID | Tính năng | Kiểm chứng (bấm thật trong app đang chạy + bằng chứng) | Đạt khi |
|---|---|---|---|
| T3.1 | Phòng thu | Nhập text → chọn giọng → Tạo → nghe + tải WAV/MP3; chèn `[cười]` → nghe có cười; thẻ `[nghỉ 2s]` → đo khoảng lặng ≈ 2 s (±0,3 s) bằng ffprobe/sóng âm. [Sửa R1-Y2/Y3] `[nghỉ]` do `TextPreprocess` xử lý (không đưa nguyên tag vào `infer()`); file .srt kèm audio: đo sai số **từng mốc** (mỗi mốc ±0,3 s, đo bằng `SrtWriter`), không chỉ đo tổng | Mọi nút bấm có kết quả thật; ảnh chụp UI đính kèm |
| T3.2 | Hội thoại/Podcast | Kịch bản 2 nhân vật × 3 lượt → 1 file; kiểm tra từng lượt đúng giọng (nghe); mở lại kịch bản → giọng không đổi. [Sửa R1-G8] "Giọng không đổi" đo được bằng cách đối chiếu `voice_id` trong file kịch bản đã lưu, không chỉ nghe bằng tai | Voice-lock giữ đúng; không trộn giọng |
| T3.3 | Lồng tiếng .srt | File .srt mẫu 5 câu (có 1 câu dài cố ý) → audio dài ≈ bằng video (±0,5 s); đo mốc từng câu (ffprobe + nghe); câu dài bị lùi → có SRT đã chỉnh mốc + danh sách câu bị lùi. [Sửa R1-G8] Đo sai số **từng mốc** (mỗi mốc ±0,3 s) — 5 câu lệch dồn vẫn có thể pass tổng ±0,5 s nên chỉ đo tổng là không đủ | Khớp mốc giờ từng câu, không cắt chữ |
| T3.4 | Đọc file | PDF 2 trang + DOCX + TXT mẫu → text trích đúng, làm sạch đúng, chuyển sang Phòng thu tạo được giọng | Text không mất chữ, không dính ký tự rác |
| T3.5 | Tạo hàng loạt | File 10 mục `[P1]`… → 10 file + ZIP; 1 mục lỗi (text rỗng) → 9 file xong + mục lỗi báo rõ + thử lại riêng được. [Sửa R1-TH-16] Đo **peak RAM** với batch 100 mục và 500 mục (ghi số đo, đối chiếu ngân sách RAM); đo thời gian/mục | Đủ file, lỗi xử lý riêng; peak RAM ghi rõ số đo |
| T3.6 | Bản đã tạo | Tạo 3 bản → danh sách hiện đủ 3; nghe lại/tải lại/xoá từng bản; tổng dung lượng hiển thị đúng (`du` đối chiếu) | CRUD thật trên file đĩa |
| T3.7 | Cài đặt | Đổi giọng mặc định → khởi động lại app vẫn giữ; đổi thư mục lưu → file mới vào đúng thư mục; đổi precision → tạo lại đúng tốc độ/chất lượng. [Sửa R1-G8] "Đúng" đo được: đổi precision fp32→int8 thì RTF giảm (số đo) và file vẫn 48 kHz/mono; đổi thư mục thì file mới nằm đúng thư mục mới (`ls` đối chiếu) | Cài đặt bền vững qua khởi động lại |

### Bước 4 — Đóng gói + README

| ID | Tính năng | Kiểm chứng | Đạt khi |
|---|---|---|---|
| T4.1 | Đóng gói Windows | [Sửa R1-🔴 R2] **Không build `.exe` Windows trên máy Annie (Linux)** — PyInstaller không build chéo Windows từ Linux, Inno Setup cũng cần Windows. Build bằng **GitHub Actions Windows runner** (`windows-latest`, miễn phí cho repo public — hướng team đã dùng cho S1/MODOLIVIO, xem MEMORY.md): workflow `.github/workflows/build-windows.yml` chạy PyInstaller + Inno Setup trên runner Windows → artifact `.exe`/installer + SHA-256 hash → tải về cài trên **máy Windows thật của anh** (mục 11, C1) → mở app → T1.2 chạy được. Phương án dự phòng: build tại chỗ trên máy Windows của anh khi anh mở máy. Không dùng Wine làm phương án chính | `.exe` build từ runner Windows + hash; cài được trên máy anh; T1.2 pass trên máy anh (xem mục 11) |
| T4.2 | Đóng gói Linux | Build tương đương trên máy Annie → chạy → T1.2 + T2.1 pass | App chạy trên Linux không cần repo |
| T4.3 | README + LICENSE + NOTICE | README có: cài đặt, chạy, cấu hình, API, giấy phép, ghi công VieNeu-TTS; [Sửa R1-G7] LICENSE là **license Apache 2.0 của HP Voice Studio** (của HP, không copy nguyên file LICENSE của upstream làm LICENSE của mình) + NOTICE ghi công upstream + license giọng + license FFmpeg | Người mới đọc README làm theo chạy được (anh kiểm bằng mắt) |
| T4.4 | Release gate | Chạy `release_readiness_gate` + `pre_launch_security_checklist` (skill team) → 0 mục chặn; test tổng PASS 100% các mục chạy được | Có log gate đính kèm |

---

## 11. CHỜ KIỂM CHỨNG THẬT (chỉ làm được trên máy/tài khoản thật của anh)

> Theo skill verification-before-completion-team: các mục này **không được tính là
> xong** khi chỉ pass trên máy Annie/CI. Ghi riêng, báo anh, không tuyên bố xong.

| # | Việc | Vì sao chỉ kiểm được trên máy thật |
|---|---|---|
| C1 | Cài file `.exe` trên máy Windows thật của anh, mở app, tạo WAV thật (T1.2) | SmartScreen/WebView2/driver âm thanh chỉ có trên máy anh |
| C2 | Clone giọng thật của anh (thu micro 3–8 s) + cam kết | Giọng + micro + sự đồng ý của anh |
| C3 | Batch lớn (≥ 100 mục / bài ≥ 30 phút) trên máy anh | RAM/CPU/ổ đĩa thật của máy anh |
| C4 | Tạo video thật bằng giọng HP (ghép vào MODOLIVIO) | Luồng thật cuối cùng |
| C5 | Test V4 bằng key của anh (khi anh đồng ý) | Key + quota thật của anh; **không tự test** |
| C6 | Đổi precision int8/fp32 trên CPU thật của anh | VNNI/méo tiếng phụ thuộc CPU thật |
| C7 | LAN API từ máy khác trong mạng nhà anh | Mạng/tường lửa thật |
| C8 | Kiểm tra trùng cổng trên máy anh (8123 MODOLIVIO, 8001 CIT, 8000/7860 upstream, 8124 HP) trước khi chốt cổng HP | [Sửa R1-G11/R1] Cổng đang chiếm chỉ có trên máy anh — hệ quả trực tiếp của 🔴 R1; chạy `scripts/check_port.py` trên máy anh |
| C9 | Cài `.exe` chưa ký: SmartScreen + WebView2 có sẵn không | Chỉ có trên máy Windows thật của anh |
| C10 | Tốc độ tải model từ Hugging Face trên mạng nhà anh (HF có bị chặn/chậm không) | Mạng nhà anh; quyết định TH-02/TH-15 (đóng gói sẵn model hay tải lần đầu) |
| C11 | Gõ Telex trong UI web local + thu micro trên Windows (quyền micro) | Lỗi Telex từng xảy ra ở MODOLIVIO; micro + quyền chỉ có trên máy anh |
| C12 | Đo peak RAM batch 100/500 mục + dung lượng ổ đĩa sau batch lớn | RAM/ổ đĩa thật của máy anh (TH-16) |
| C13 | Kiểm tra key V4 hợp lệ bằng endpoint rẻ nhất (không đốt ký tự) | Key + quota thật của anh; cần xác minh `GET /v1/audio/voices` có miễn phí không trước khi dùng làm "ping key" (Y12) — nếu endpoint đó tính phí thì không dùng làm ping |

---

## 12. TO-TICKETS — DANH SÁCH VIỆC BƯỚC 1–4 (full phạm vi)

> Mỗi ticket: đầu vào, đầu ra, tiêu chí đạt (tham chiếu mục 10), ước lượng tương đối
> (S/M/L — **SUY LUẬN**, chốt lại khi giao việc). Thứ tự làm theo số ticket.
> [Sửa R1-R3] Ticket ở mục này dùng namespace `TK…` (VD `TK2.5` = ticket SrtDubber);
> tiêu chí đạt tham chiếu sang namespace test `T…` ở mục 10 (VD `T2.5` = test clone
> giọng). `TKx.y` và `Tx.y` là hai thứ khác nhau — không viết tắt lẫn.

### Bước 1 — Engine V3 + WAV thật

| Ticket | Việc | Tiêu chí đạt |
|---|---|---|
| TK1.1 | Dựng repo HP: `.gitignore`, `requirements.txt` (`vieneu==3.8.4` ghim), `config.example.yaml`, cấu trúc `src/hpvoice/` | Cài mới từ README chạy được tới bước import |
| TK1.2 | `V3Engine`: adapter gọi SDK (init, infer, stream, batch, list voices, precision auto theo CPU) | T1.2, T1.3, T1.5 pass |
| TK1.3 | Tải model lần đầu: `scripts/download_model.py` + đo dung lượng/thời gian thật **theo từng thành phần** (backbone, codec, speaker-encoder/denoiser, tokenizer) + kiểm chứng **chặn mạng hoàn toàn sau khi tải, khởi động lại, tạo WAV** (Y10), ghi vào README | T1.1 pass; có số dung lượng thật theo từng thành phần; offline hoàn toàn được xác nhận hoặc ghi rõ thành phần còn thiếu |
| TK1.4 | Đo hiệu năng CPU (fp32/int8, RTF) + phát hiện VNNI bằng `py-cpuinfo` (mặc định fp32 khi không đọc được cờ) + quyết precision mặc định theo CPU | T1.4, T1.7 pass; quyết định ghi vào SPEC (ADR) |
| TK1.5 | `VoiceStore`: preset (đọc từ SDK) + clone (`add_voice`, file riêng HP) + cam kết + cơ chế gỡ giọng khi khiếu nại (TH-17) | T2.5 (phần engine) pass |
| TK1.6 | `AudioPost` (time-stretch `librosa.effects.time_stretch`, nối chunk, xuất WAV/MP3 qua **FFmpeg đóng gói kèm** — ADR-07) + `TextPreprocess` (thẻ `[nghỉ]`/cảm xúc — Y2) + `SrtWriter` (suy mốc giờ — Y3) | T2.4, T2.10, T3.1 pass |
| TK1.7 | `PronDict`: CRUD + CSV import/export + áp trước infer | Test đơn vị pass; dùng trong T3.1 |

### Bước 2 — API local + V4

| Ticket | Việc | Tiêu chí đạt |
|---|---|---|
| TK2.1 | `HpApiServer` FastAPI + `docs/api-contract.md` (mục 4) + `scripts/check_port.py` (cổng 8124, fail-fast khi bận — R1) + giới hạn text/batch/hàng đợi (Y6) + endpoint 5 trả **ZIP duy nhất** (Y11) | T2.1, T2.2, T2.9 pass |
| TK2.2 | `EngineRouter` + `V4Engine` (Cloud API v4, key từ store qua `keyring`/DPAPI, fallback V3 + báo lý do; xử lý riêng 401/402/429) | T2.6 pass (khi có key test do người dùng cung cấp) |
| TK2.3 | `JobQueue` + `HistoryStore` (chặn tạo mới khi vượt `max_history_gb` — TH-16) + endpoint history/jobs | T2.8, T3.6 (phần API) pass |
| TK2.4 | `ConversationEngine` (khoá speaker→voice, batch, ghép) | T3.2 (phần API) pass |
| TK2.5 | `SrtDubber` (parse, căn giờ, SRT đã chỉnh mốc) + đo giới hạn SRT dub ở Bước 3 (G4 — không lấy số 100.000 của Tạo hàng loạt) | T3.3 (phần API) pass |
| TK2.6 | `BatchRunner` (txt/json/srt, ZIP, thử lại mục lỗi; ghi từng mục ra đĩa ngay; đo peak RAM 100/500 mục — TH-16; chốt giới hạn batch theo số đo) | T3.5 (phần API) pass |
| TK2.7 | `FileReaders` (PDF/DOCX/TXT + làm sạch; ghi chú bản quyền văn bản đầu vào) | T3.4 (phần API) pass |
| TK2.8 | Auth LAN (`X-API-Key`, opt-in) + test bảo mật cơ bản | T2.7 pass |
| TK2.9 | Test API (mock engine) + test tương thích OpenAI SDK + test giới hạn text/batch/hàng đợi + test preview cache/MP3 | T2.8, T2.9, T2.10 pass, 100% |

### Bước 3 — UI đủ tab

| Ticket | Việc | Tiêu chí đạt |
|---|---|---|
| TK3.1 | Khung UI + điều hướng nhóm Tạo/Thư viện/Hệ thống + tab Phòng thu + `PreviewCache` (nghe thử V3/V4 — Y7) | T3.1 pass |
| TK3.2 | Tab Hội thoại/Podcast + Giọng của tôi (clone + cam kết) | T3.2 pass |
| TK3.3 | Tab Lồng tiếng .srt + Đọc file | T3.3, T3.4 pass |
| TK3.4 | Tab Tạo hàng loạt + Bản đã tạo | T3.5, T3.6 pass |
| TK3.5 | Tab Cài đặt (giọng/model/thư mục/V4 key/API LAN) | T3.7 pass |
| TK3.6 | Polish UI: thông báo lỗi rõ lý do, trạng thái engine, ước tính phí V4 | Review bằng mắt (anh) + evidence QA |

### Bước 4 — Đóng gói + phát hành

| Ticket | Việc | Tiêu chí đạt |
|---|---|---|
| TK4.1 | Đóng gói Windows (.exe/installer, kèm model hoặc tải lần đầu) — **build trên GitHub Actions Windows runner** (`windows-latest`, workflow `.github/workflows/build-windows.yml`), không build trên máy Annie (Linux); artifact + SHA-256; cài thử trên máy anh (C1) | T4.1 pass; C1 chờ kiểm chứng thật |
| TK4.2 | Đóng gói Linux (chạy trên máy Annie) | T4.2 pass |
| TK4.3 | README + LICENSE (của HP — G7) + NOTICE (ghi công upstream + license giọng + license FFmpeg) + `docs/decisions/` (ADR) | T4.3 pass |
| TK4.4 | Release gate (skill team) + test tổng 100% + danh sách "chờ kiểm chứng thật" | T4.4 pass |
| TK4.5 | Quy trình nâng SDK (test tương thích + ghim version + theo dõi release upstream; mirror model + checksum — TH-15) | Có checklist nâng cấp trong README |

### Dự phòng (P2 — không làm trong v1, ghi để không quên)

- P2.1: Watermark Perth (`vieneu[watermark]`, cần torch) + hiển thị trạng thái (TH-09).
- P2.2: Giọng nước ngoài (Supertonic/Kokoro) — chỉ khi có nhu cầu, rà soát license riêng
  (Supertonic OpenRAIL-M; Kokoro Apache-2.0 + bộ tách âm GPL).
- P2.3: v3 Nano cho máy yếu (làm rõ mâu thuẫn 6 vs 11 giọng trước).
- P2.4: Trợ lý AI viết kịch bản (LLM bên thứ ba) — như VieNeu Desktop.
- P2.5: Auto-update + đồng bộ giọng clone (khi sang kịch bản B).

---

## 13. GIẤY PHÉP — GHI CHÚ BẮT BUỘC

1. **Code HP Voice Studio:** [Sửa R1-G7] code HP là code mới — `LICENSE` là
   **Apache 2.0 của HP Voice Studio** (lựa chọn riêng của HP, ghi chủ sở hữu là
   HP), **không copy nguyên file LICENSE của upstream làm LICENSE của mình**
   (copy nguyên gây nhầm lẫn về chủ sở hữu bản quyền). `NOTICE` ghi công riêng:
   VieNeu-TTS © Phạm Nguyễn Ngọc Bảo (pnnbao-ump) + license giọng (mục 2) +
   license FFmpeg (mục 7).
2. **Giọng v3 Turbo:** xem TH-01 — file `voices_v3_turbo.json` không ghi license;
   file `voices.json` cũ ghi CC BY-NC 4.0 "non-commercial use only". V1 dùng cá
   nhân là an toàn; thương mại phải xin xác nhận trước (mục 9).
3. **V4 + kho giọng V4:** độc quyền, chỉ qua API trả phí; không clone offline.
4. **Không dùng:** bản GGUF Q4 (CC BY-NC), không fork/copy code CIT (CIT là Apache
   2.0 nhưng lệnh anh là không copy — chỉ tham khảo tính năng/cấu trúc).
5. **Không lấy:** logo/thương hiệu VieNeu hay CIT; HP Voice Studio dùng thương
   hiệu riêng.
6. **Giọng clone:** chỉ giọng có phép + cam kết; nội dung mô phỏng giọng người thật
   khi đăng công khai phải ghi rõ "giọng đọc được tạo bằng AI". Giọng nói là dữ
   liệu cá nhân (NĐ 13/2023); nội dung AI phải ghi nhãn (NĐ 147/2024) — xem TH-17.
7. **FFmpeg:** [Sửa R1-Y1] FFmpeg đóng gói kèm app — ghi license FFmpeg vào NOTICE
   ở TK4.3 (bản build tĩnh chuẩn dùng LGPL; kiểm tra lại giấy phép của đúng bản
   binary đóng gói ở Bước 4, không ghi bừa "LGPL" nếu bản đó chứa thành phần GPL).

---

## 14. ADR (quyết định kiến trúc rút gọn)

| ADR | Quyết định | Phương án đã cân nhắc | Cách nó hỏng / điều kiện xét lại |
|---|---|---|---|
| ADR-01 | Stack: Python + FastAPI + web UI local | B. Electron+sidecar; C. Gradio demo có sẵn; **D. Fork CIT Voice Studio** (đã cân nhắc, loại vì lệnh anh 03:31 không fork/copy code CIT + cần kiến trúc riêng cho MODOLIVIO — xem §3.2) | Đóng gói Windows (GitHub Actions runner, TK4.1) thất bại 2 lần → xét B |
| ADR-02 | Engine chính v3 Turbo, ghim `vieneu==3.8.4` | Nano (yếu hơn, 24 kHz); backend v2/v1 GPU (cũ) | SDK ra bản sửa lỗi nghiêm trọng → nâng theo checklist TK4.5 |
| ADR-03 | Mọi gọi SDK qua `V3Engine`; mọi engine cùng interface | Gọi SDK trực tiếp từ API/UI | Đổi SDK/engine → chỉ sửa adapter |
| ADR-04 | V3 mặc định, V4 opt-in + fallback V3 | V4 mặc định (tốn phí, phụ thuộc cloud) | Người dùng chọn V4 làm mặc định trong Cài đặt (quyền của họ) |
| ADR-05 | API mặc định loopback; LAN opt-in + key | Mở LAN mặc định (rủi ro TH-06) | Nhu cầu Annie gọi từ máy khác → bật LAN có key |
| ADR-06 | Tốc độ làm ở tầng `AudioPost` bằng `librosa.effects.time_stretch`, không trong engine; `soxr` chỉ resample, không đổi tốc độ (Y4) | Chờ SDK thêm tham số speed | SDK thêm `speed` chính thức → chuyển sang dùng SDK, giữ interface |
| ADR-07 | MP3 mã hoá/giải mã bằng **FFmpeg đóng gói kèm** (binary tĩnh qua `imageio-ffmpeg`, fallback FFmpeg hệ thống; không có FFmpeg → chỉ WAV + báo rõ) | `lameenc` (chỉ mã hoá, không giải mã MP3/M4A đầu vào); bỏ MP3 khỏi v1 (mất tính năng CIT đã có) | FFmpeg không đóng gói được trên Windows runner → xét `lameenc` + giới hạn clone chỉ nhận WAV |
| ADR-08 | Cổng API mặc định **`8124`**; khởi động bind thất bại → fail-fast + báo rõ, không tự nhảy cổng (R1) | Giữ 8123 (trùng MODOLIVIO — loại); tự nhảy cổng khi bận (khó lường, client gọi sai đích — loại) | C8 phát hiện 8124 cũng bị chiếm trên máy anh → đổi số khác trong bảng §4, cập nhật mọi tham chiếu |
| ADR-09 | Key V4/key LAN lưu qua **`keyring`** (Windows: DPAPI/Credential Manager; Linux: Secret Service, fallback `secrets.json` 0600) — không lưu plaintext trên Windows (Y12) | File `secrets.json` + `chmod 0700` (không có nghĩa trên Windows — loại) | `keyring` không chạy được trên máy anh → fallback file + ACL Windows, ghi rõ trong README |

---

## 15. ĐIỂM CẦN QUYẾT / CÂU HỎI MỞ (đưa anh chốt cùng SPEC)

1. **Cổng API mặc định:** [Sửa R1-R1 — ĐÃ TRẢ LỜI, không còn là câu hỏi mở]
   Mặc định mới là **`8124`** (8123 đã có chủ: server TTS MODOLIVIO, nghiên cứu
   nền §5.2). Còn lại một việc kiểm chứng, không phải một quyết định: anh/Annie
   chạy `scripts/check_port.py` trên máy anh (C8) để xác nhận không có dịch vụ
   nào khác đang chiếm 8124.
2. **Model trong bộ cài hay tải lần đầu:** bộ cài ~300–400 MB kèm model sẵn
   (dùng ngay, nặng) hay bộ cài nhẹ + tải model lần đầu (nhẹ, cần mạng)? CIT chọn
   kèm sẵn; VieNeu Desktop ~90 MB (tải thêm sau). Anh chọn hướng nào? (Quyết
   sau khi có số đo tốc độ HF ở C10 — xem TH-15.)
3. **Ngưỡng cảnh báo phí V4:** mặc định 100.000 ký tự/phiên trong SPEC — anh muốn
   số khác không? (Và có muốn chặn hẳn khi vượt ngưỡng không, hay chỉ cảnh báo?)
4. **Giới hạn batch:** [Sửa R1-G6] SPEC tạm 500 mục/lần — **500 là số tạm chờ đo
   RAM ở Bước 2 (TK2.6), không phải số đã chốt**. Anh có batch lớn hơn không
   (VD: 100.000 câu như VieNeu Desktop)? Nếu có thì Bước 2 phải đo RAM kỹ hơn.
5. **Watermark:** v1 không tuyên bố watermark (TH-09) — anh có muốn đầu tư
   `vieneu[watermark]` (cần torch, nặng hơn) ngay từ đầu không, hay để P2?
6. **Tên + thương hiệu:** "HP Voice Studio" đã chốt tên; logo/ảnh đại diện có
   muốn làm riêng không (không dùng logo VieNeu/CIT)?
7. **Build Windows — GitHub Actions hay máy anh?** [Sửa R1-R2 — ĐÃ TRẢ LỜI]
   Chốt: **GitHub Actions Windows runner làm chính** (miễn phí cho repo public,
   team đã dùng cho S1/MODOLIVIO — xem MEMORY.md), máy Windows của anh là nơi
   cài + kiểm chứng (C1) và là phương án dự phòng để build tại chỗ. Không còn
   hỏi "build ở đâu", chỉ còn việc làm ở TK4.1.
8. **MP3 — đóng gói FFmpeg hay chỉ xuất WAV?** [Sửa R1-Y1 — ĐÃ TRẢ LỜI]
   Chốt: **đóng gói FFmpeg kèm app** (ADR-07). Căn cứ: server upstream chỉ xuất
   wav/pcm, SDK không có encoder MP3 nào (`apps/openai_speech.py:360-366,412`;
   `pyproject.toml` không có `ffmpeg`/`lameenc`/`pydub`); FFmpeg giải quyết cả
   hai chiều (mã hoá MP3 + giải mã MP3/M4A cho clone); FFmpeg đã có sẵn trên
   máy Annie (`/usr/bin/ffmpeg`) để kiểm chứng ở Bước 2. Bộ cài tăng dung
   lượng thêm ~25–30 MB (binary tĩnh, con số ước lượng — đo thật ở TK4.1).
9. **Thẻ `[nghỉ]` — giữ ở v1 hay dời lại?** [Sửa R1-Y2 — ĐÃ TRẢ LỜI]
   Chốt: **giữ ở v1**, với thiết kế tầng app `TextPreprocess` (§3.3) — parse tag,
   cắt đoạn, chèn silence bằng `AudioPost`; không đưa tag vào `infer()`. Căn cứ:
   grep toàn bộ upstream 0 kết quả cho `[nghỉ` (tính năng của CIT, không phải SDK).
10. **`.srt` kèm audio ở Phòng thu — giữ hay chỉ xuất ở tab Lồng tiếng?**
    [Sửa R1-Y3 — ĐÃ TRẢ LỜI] Chốt: **giữ**, với phương pháp suy mốc của `SrtWriter`
    (§3.3: chia chunk như SDK, đo độ dài audio từng chunk, cộng dồn + khoảng lặng),
    sai số mục tiêu ±0,3 s/câu (T3.1). Nếu Bước 3 đo vượt ngưỡng thì hạ phạm vi
    xuống chỉ xuất `.srt` ở tab Lồng tiếng.
11. **Giới hạn text — anh có bài dài hơn 20.000 ký tự/lần tạo không?**
    [Sửa R1-Y6 — TRẢ LỜI MỘT PHẦN] Giới hạn mặc định chốt là **20.000 ký tự/request**
    (lấy đúng upstream, `apps/openai_speech.py:310`); vượt → 400. Phần còn lại
    **cần anh trả lời**: nếu anh có bài dài hơn thì giới hạn phải nâng kèm đo RAM
    (TK2.6); nếu không thì giữ 20.000.
12. **Preview V4 — đồng ý tốn ký tự trả phí mỗi lần nghe thử, hay cache mẫu?**
    [Sửa R1-Y7 — ĐÃ TRẢ LỜI THIẾT KẾ, CÒN 1 Ý NHỎ CẦN ANH CHỐT] Thiết kế chốt:
    cache theo (voice_id + câu mẫu), nghe lần 2 không gọi lại API; UI hiện ước
    tính ký tự trước khi nghe lần đầu. Cần anh chốt: **câu mẫu preview chuẩn**
    (đề xuất ≤ 60 ký tự, `config.yaml: preview_sample`) — câu càng dài càng tốn
    ký tự cho lần nghe đầu của mỗi giọng.
13. **Clone giọng — chỉ cho thu micro trực tiếp ở v1?** [Sửa R1-TH-17 — CHƯA TRẢ LỜI,
    CẦN ANH CHỐT] Đề xuất của phản biện: v1 chỉ cho clone bằng thu micro trực tiếp
    (khó giả mạo hơn upload file lạ), upload file thì cần thêm bước xác minh sau.
    SPEC v1.1 giữ nguyên phương án cũ (micro + upload file, kèm cam kết bắt buộc
    + cơ chế gỡ khi khiếu nại) cho tới khi anh quyết — vì giới hạn micro-only sẽ
    bỏ đi một luồng dùng thật (anh đã có sẵn file mẫu giọng mình). Anh chọn:
    (a) giữ cả hai như hiện tại, hay (b) micro-only ở v1?
14. **Kiểm tra key V4 hợp lệ bằng endpoint nào mà không đốt ký tự?**
    [Sửa R1-Y12 — CHƯA TRẢ LỜI, CẦN KIỂM CHỨNG Ở C13] Ứng viên là
    `GET /v1/audio/voices` (chỉ liệt kê giọng) — **chưa rõ có miễn phí không**.
    Kiểm chứng ở C13 trước khi dùng làm "ping key"; nếu tính phí thì trạng thái
    key trong Cài đặt chỉ ghi "đã nhập (chưa kiểm tra)" cho tới khi có lần gọi
    TTS V4 thành công thật.

---

## Phụ lục A. Nguồn đã đọc (để phản biện kiểm tra lại)

- `upstream-vieneu-tts/README.md`, `README_PYPI.md`, `pyproject.toml`, `config.yaml`,
  `.env.example`, `src/vieneu/factory.py`, `src/vieneu/v3turbo.py` (init/infer/
  infer_stream/infer_batch/list_preset_voices/add_voice/encode_reference),
  `src/vieneu/base.py`, `src/vieneu/assets/voices*.json`,
  `src/vieneu/_v3_turbo_engine/hub_load_v3_turbo.py`,
  `src/vieneu/_v3_turbo_engine/onnx_runtime_lite.py`,
  `apps/openai_speech.py`, `apps/srt_speech.py`, `apps/web_stream.py`,
  `apps/gradio_main.py` (tab + conversation), `examples/main_v3turbo.py`,
  `src/vieneu/serve.py`, `LICENSE` (Apache 2.0).
- `~/workspace/cuongit/cit-voice-studio/README.md` (v1.0.6) + cấu trúc
  `app-desktop/cit-voice-app/src` (routes/features — chỉ tên file/thư mục).
- `~/workspace/research_notes/vieneu-studio-clone-2026-11-19.md` (§2.2, §3).
- `~/workspace/custom-connectors/custom.vieneu/CONNECTOR.md` (hợp đồng V4).
- Skill: `team_working_charter` v1.1, `verification-before-completion-team`,
  `system-design-planning-vn` (đã đọc; api-contract/security/test/docs sẽ đọc
  kỹ ở đúng khâu Bước 2–4).

## Phụ lục B. Nhật ký phiên bản SPEC

- v1.0 draft — 19/11/2026, Bước 0 (grilling → research → to-spec). Chưa qua phản
  biện chéo vòng 2 (GPT1 + G1–G4 phân tích độc lập, rồi gộp đưa anh chốt).
  Thay đổi sau phản biện sẽ ghi ở đây kèm ngày + lý do.
- v1.1 — 19/11/2026, nhánh `spec/v1-r1` (từ `spec/v1`). Sửa theo phản biện vòng 1
  (`CRITIQUE-R1.md`, nhánh `critique/r1`, commit `6022056`). Không viết lại toàn
  bộ SPEC; phần phản biện xác nhận đúng được giữ nguyên.
  - 🔴 R1: cổng mặc định `8123` → **`8124`** (8123 đã có chủ: MODOLIVIO); bảng cổng
    đã chiếm + quy tắc kiểm tra trùng cổng + fail-fast (§4, §6, T2.1, ADR-08);
    bỏ câu hỏi Q1 kiểu "chưa biết".
  - 🔴 R2: build `.exe` Windows chuyển sang **GitHub Actions Windows runner**
    làm chính (team đã dùng cho S1), máy anh là nơi cài/kiểm chứng + dự phòng
    (TH-12, §3.2, T4.1, TK4.1, ADR-01).
  - 🔴 R3: ticket đổi sang namespace **`TK…`**, test giữ `T…`; rà toàn bộ tham
    chiếu chéo (§10, §12, §14). Lưu ý sửa kèm: điều kiện xét lại ADR-01 trước đây
    ghi nhầm ticket T4.2 (đóng gói Linux) — nay ghi đúng TK4.1 (đóng gói Windows).
  - 🟡 Y1/TH-14: MP3 = **FFmpeg đóng gói kèm** (ADR-07; cả mã hoá MP3 lẫn giải mã
    MP3/M4A cho clone); Y2: thẻ `[nghỉ]` do `TextPreprocess` xử lý; Y3: `SrtWriter`
    suy mốc giờ (±0,3 s/câu); Y4: time-stretch = `librosa.effects.time_stretch`,
    `soxr` chỉ resample; Y5: gỡ "~110 MB graph clone" khỏi đoạn Turbo (số của Nano);
    Y6: giới hạn 20.000 ký tự/request + batch 500 tạm + hàng đợi 20 job; Y7:
    `PreviewCache` cho nghe thử V3/V4; Y8: thêm phương án D (fork CIT) vào §3.2 +
    ADR-01; Y9: phát hiện VNNI bằng `py-cpuinfo`, mặc định fp32 khi không đọc được;
    Y10: kiểm chứng offline hoàn toàn (chặn mạng, khởi động lại, tạo WAV) ở TK1.3;
    Y11: endpoint 5 chốt **ZIP đồng bộ duy nhất**; Y12: key lưu qua `keyring`/DPAPI
    trên Windows, không lưu plaintext (ADR-09).
  - 💭 G1: chú thích int8 "~3x/frame" (per-frame) vs "~1,6×" (tổng thể); G2: 409 chỉ
    kiểm chứng với built-in (alias chưa rõ); G3: xác minh lại `api-cpu` tồn tại
    (`docker-compose.yml:102`); G4: giới hạn SRT dub "chưa rõ" (100.000 là của Tạo
    hàng loạt); G5: chốt SRT tối đa 1,5× (bỏ 2×); G6: 500 là số tạm chờ đo RAM;
    G7: LICENSE là của HP, không copy nguyên file upstream; G8: sửa tiêu chí đo
    (T1.6, T2.4, T3.1, T3.2, T3.3, T3.5, T3.7); G9: thêm T1.7 thời gian khởi động
    (≤ 30 s); G10: giọng V4 khóa theo trường `id`, không theo tên hiển thị; G11:
    bổ sung C8–C13; G12: bổ sung §9.2 (bán lại V4, license weight, NĐ 13/2023 +
    NĐ 147/2024, mô hình giá, chính sách lưu trữ).
  - Tử huyệt mới TH-12–TH-17 (§1): build Windows, cổng 8123, MP3, upstream/HF mất
    hẳn, RAM batch lớn, cam kết clone + giọng là dữ liệu cá nhân.
  - Test mới: T1.7 (khởi động), T2.9 (giới hạn + hàng đợi), T2.10 (preview cache +
    MP3); T2.6 thêm 401/402/429; T1.4 gắn CPU tham chiếu là CPU máy anh (C6).
  - §15: trả lời 8 câu hỏi của phản biện — 5 câu trả lời xong bằng bằng chứng
    (cổng, build, MP3, `[nghỉ]`, `.srt`), 2 câu trả lời một phần (giới hạn text,
    preview V4 — còn 1 ý nhỏ cần anh chốt mỗi câu), 1 câu chưa trả lời (clone
    micro-only — Q13, cần anh chốt); thêm Q14 (ping key V4 rẻ nhất — chờ C13).
