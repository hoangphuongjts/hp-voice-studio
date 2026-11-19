# HP Voice Studio — SPEC v1.3 (gộp phản biện team GPT1+G1+GPT2+G3+G4+G2 — BẢN CUỐI ĐƯA ANH CHỐT)

> **Trạng thái:** BẢN DRAFT PHÂN TÍCH — khâu to-spec của Bước 0. Chưa code implementation,
> chưa cài SDK, chưa tạo WAV thật. Bản v1.3 này gộp phản biện độc lập của cả team
> (GPT1 kết luận sớm + G1 + GPT2 + G3 + G4 + G2 — xem Phụ lục C, bảng đối chiếu)
> vào SPEC v1.2, kèm 2 quyết định mới của anh ngày 19/11/2026 (04:20): chỉ chạy
> local nên nới lỏng bảo mật mạng (§9.3), và thước đo cuối cùng là full tính năng
> dùng được (§0.1). Các điểm team nêu từ bản ZIP cắt cụt 497 dòng / snapshot
> 1.471 dòng đã được kiểm chứng lại trên SPEC đầy đủ 1.593 dòng trước khi sửa —
> cái nào là lỗi bản cắt/snapshot thì ghi rõ ở Phụ lục C, không sửa mù.
> **Ngày:** 19/11/2026 · **Nhánh:** `spec/v1.3` (tạo từ `spec/v1-r2`) · **Repo phân tích:** `upstream-vieneu-tts/`
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
| 10 | **Chỉ chạy local, dùng cá nhân — NỚI LỎNG bảo mật mạng** (quyết định anh 04:20 19/11): không áp mức chặt cho bản local-only. Biện pháp mạng duy nhất còn lại: API bind `127.0.0.1` mặc định. Các biện pháp chặt (xác thực key LAN bắt buộc, chống CSRF/DNS-rebinding, rate-limit đa client, JobQueue 2 mức ưu tiên) hạ xuống P2/backlog, liệt kê ở §9.3 để bật lại khi mở LAN | Quyết định anh 04:20 19/11 |
| 11 | **Thước đo cuối cùng: full tính năng dùng được** (quyết định anh 04:20 19/11): ưu tiên P0/P1/P2 theo §0.1; nghiệm thu mỗi giai đoạn bằng tính năng chạy thật, không bằng checklist giấy | Quyết định anh 04:20 19/11 |
| 12 | **Q13 — Clone giọng giữ CẢ HAI:** thu micro trực tiếp + upload file (kèm cam kết bắt buộc + cơ chế gỡ khi khiếu nại, TH-04/TH-17) | Anh chốt 04:32 19/11 |
| 13 | **Q16 — Hàng đợi 20 job:** 1 job chạy, tối đa **20 job chờ** + TTL 60 phút (đầy → 429); không dùng đề xuất tối đa 3 job chờ của GPT2 | Anh chốt 04:32 19/11 |
| 14 | **Q21 — FFmpeg TÁCH KHỎI BỘ CÀI, tải cài sau:** bộ cài **không đóng gói kèm binary FFmpeg** (giữ 100% Apache 2.0, không còn bẫy onefile TH-31); lần đầu chạy app tải binary FFmpeg về thư mục dữ liệu (cần mạng lần đầu, kiểm checksum SHA-256, báo tiến trình rõ); fallback FFmpeg hệ thống nếu có; không có FFmpeg → chỉ xuất WAV + báo rõ, không crash (xem TK4.9 + ADR-07). NOTICE ghi **LGPL v3 cho binary tải sau chính (BtbN)** + GPL v3 + source offer chỉ cho binary imageio-ffmpeg dự phòng (§13.7) | Anh chốt 04:35 19/11 (chọn phương án 2 trong 4: LGPL / tách khỏi bộ cài / giữ GPL+source offer / bỏ FFmpeg hẳn) |

### 0.1. Nguyên tắc ưu tiên — thước đo cuối cùng (quyết định của anh 04:20 19/11)

> **"Kết quả dùng được full tính năng là ok."** Thước đo cuối cùng của v1 là
> **ĐỦ TÍNH NĂNG + DÙNG ĐƯỢC THẬT** (7 nhóm tính năng ở quyết định 3, §0):
> Phòng thu, Hội thoại/Podcast, Lồng tiếng .srt, Đọc file, Tạo hàng loạt,
> Bản đã tạo, Cài đặt. Các tử huyệt (§1) và tiêu chí mượt (§10.5) vẫn ghi đầy
> đủ trong SPEC, nhưng xếp hạng xử lý theo mức độ ảnh hưởng tới "dùng được":
>
> - **P0 — chặn tính năng chạy được:** sửa trước khi chốt build. VD: không tải
>   được model, sai precision méo tiếng, cổng trùng, `.exe` thiếu file, UI treo,
>   SRT lệch mốc, clone không có cam kết, đường dẫn có dấu làm chết app.
> - **P1 — ảnh hưởng mượt mà:** RTF, tiếng đầu, phản hồi UI, RAM, thời gian
>   khởi động — sửa trong lúc build, nghiệm thu bằng số đo thật (§10.5).
> - **P2/backlog — hardening:** đặc biệt bảo mật mạng local (theo quyết định
>   local-only §9.3) — hạ xuống backlog, không để danh sách dài làm chậm build.
>
> **Nghiệm thu theo giai đoạn:** thứ tự build giữ nguyên theo ticket (§12:
> nền tảng → engine → API → UI → đóng gói), nhưng mỗi giai đoạn kết thúc khi
> **tính năng của giai đoạn đó chạy được thật với bằng chứng** (file WAV thật,
> response API thật, thao tác UI thật) — không phải khi checklist được tick
> trên giấy. Bảng tổng kết nghiệm thu theo tính năng ở §10.6 là thứ Annie báo
> cho anh khi SPEC xong.

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

### TH-01 — Giấy phép theo từng tài sản: model card v3 Turbo Apache 2.0; file `voices.json` cũ CC BY-NC không chứng minh 25 giọng Turbo bị cấm thương mại

- **DỮ KIỆN (kiểm chứng lại 19/11/2026):** model card Hugging Face
  `pnnbao-ump/VieNeu-TTS-v3-Turbo` (§"Usage Rights & Licensing FAQ", đọc qua
  trang HF ngày 19/11/2026) ghi rõ: *"Does Apache-2.0 cover every artifact in
  this repository? Yes. The license applies to **all** artifacts shipped here
  — `model.safetensors`, the ONNX exports, configs and tokenizers, and the
  bundled **preset-voice assets** (speaker embeddings + reference codes in
  `voices_v3_turbo.json`)."* Và: *"May I use the preset voices and the
  generated audio commercially? Yes. The bundled preset voices are distributed
  under the same Apache-2.0 license ... audio generated with them **may be used
  in commercial and monetized content** — no additional license or fee."* Các
  giọng preset được xác nhận có đồng ý của người nói/chủ quyền cho huấn luyện AI
  và tạo giọng tổng hợp. **Đính chính v1.3 (theo GPT2, đã kiểm chứng bằng model
  card):** bản v1.0–v1.2 viết "license giọng v3 Turbo chưa rõ ràng tuyệt đối"
  là **sai hướng** — file `voices.json` cũ (CC BY-NC 4.0, đã kiểm chứng lại
  bằng lệnh đọc file: meta `license: CC BY-NC 4.0`, `notice: "Model and voices
  are for non-commercial use only"`) **không tự chứng minh** 25 giọng v3 Turbo
  bị cấm thương mại, vì file đó là file giọng cũ, còn 25 giọng Turbo nằm trong
  `voices_v3_turbo.json` (meta chỉ ghi note về `featured`/`aliases`, **không
  ghi license** — đã kiểm chứng lại bằng lệnh đọc file) và được model card bao
  phủ bởi Apache 2.0.
- **HẠN CHẾ của bằng chứng model card (ghi rõ, không giấu):** model card đọc
  được ghi *"This card documents **SDK v3.7.1 (23 voices**, default `Minh
  Quân`)"* — HP ghim SDK **3.8.4 với 25 giọng** (default `Hải Đăng`). Hai giọng
  thêm và danh sách 25 giọng chưa được xác nhận đích danh trong bản card đọc
  được. Vì vậy: (a) v1 dùng cá nhân là an toàn tuyệt đối theo cả hai nguồn;
  (b) mốc kích hoạt thương mại (§9.2) **vẫn giữ** yêu cầu xin xác nhận bằng văn
  bản từ tác giả (pnnbao-ump) về giấy phép thương mại của đúng 25 giọng SDK
  3.8.4 — theo G4 — trước khi bán/chia sẻ rộng; (c) không phân phối lại file
  `voices.json` cũ, không dùng bản GGUF Q4 (CC BY-NC).
- **Bảng quyền từng tài sản:** xem §13.8 (mới ở v1.3).
- **Vì sao vẫn là tử huyệt:** nếu sau này thương mại hoá mà license thực tế
  khác với model card thì toàn bộ sản phẩm vi phạm bản quyền — không sửa bằng
  code được. Mức ưu tiên: **P1** (không chặn v1 dùng cá nhân; chặn kịch bản B).
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
- **Giải pháp (v1.2 — ĐÃ HẠ CẤP ở v1.3, chỉ còn áp dụng khi mở LAN; xem ghi chú ngay dưới):** mặc định bind `127.0.0.1` + cổng cấu hình được (không hardcode);
  chế độ LAN là **opt-in** trong Cài đặt, bật LAN bắt buộc sinh khoá API
  (header `X-API-Key`), LAN chỉ mở endpoint tạo giọng, **không mở** lịch sử /
  giọng clone / cài đặt / key V4; log mọi request từ xa.

[Sửa v1.3 — NỚI LỎNG theo quyết định anh 04:20 19/11: chỉ chạy local, dùng
cá nhân] Các yêu cầu chặt ở TH-06 (LAN opt-in **bắt buộc** sinh khoá API,
LAN chỉ mở endpoint tạo giọng, không mở lịch sử/giọng clone/cài đặt/key V4)
**hạ xuống P2/backlog, không còn là yêu cầu chặn của v1**. Mức mới v1:
(a) API server **chỉ bind `127.0.0.1` mặc định** — biện pháp mạng duy nhất
còn lại, vì đó là mặc định an toàn rẻ nhất, không phải "chặt chẽ";
(b) LAN là opt-in trong Cài đặt, **không bắt buộc xác thực key** ở v1 (khuyến
nghị mềm: nếu anh tự mở LAN thì nên đặt key — xem §9.3);
(c) các biện pháp chặt đã bỏ được liệt kê đầy đủ ở §9.3 "Bật lại khi mở LAN"
để sau này không phải tìm lại. Key V4 vẫn lưu qua `keyring`/DPAPI (TH-05) —
đó là bảo vệ tiền của anh, không phải bảo mật mạng, nên **không nới lỏng**.
Mức ưu tiên TH-06: **P2**.

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

### Bổ sung cho TH-01..TH-11 theo phản biện GPT2 (gộp v1.3)

GPT2 xác nhận 11 tử huyệt TH-01..TH-11 "đúng bản chất" nhưng mỗi cái thiếu phần
bổ sung. Đối chiếu trên SPEC đầy đủ v1.2:

- **TH-01:** đính chính theo model card + bảng quyền từng tài sản — đã làm ở
  TH-01 (viết lại ở v1.3) + §13.8.
- **TH-02:** bổ sung khôi phục tải dở — tải dở phải tiếp tục được (resume),
  không tải lại từ đầu; cache hỏng phát hiện bằng checksum và chỉ tải lại file
  hỏng, không xoá toàn bộ cache (TK1.3).
- **TH-03:** bổ sung đo RTF **p95 trên CPU 4 nhân sau warmup** (không đo 1 lần),
  ghi model CPU + có/không VNNI + precision đã chọn; đo cả cold-start (lần tạo
  đầu sau khởi động) — xem T1.4/T1.7 + §10.5.
- **TH-04:** bổ sung quản lý quyền clone — metadata giọng clone thêm trường
  `owner` + ngày cam kết (§8 `ClonedVoice`); cấm xuất file ref gốc (đã có);
  cơ chế gỡ giọng khi khiếu nại (đã có TH-17).
- **TH-05:** bổ sung — idempotency **chưa xác nhận** cho `POST /v1/dialogue`,
  `/v1/dub`, `/v1/srt` (OpenAPI chỉ xác nhận cho `/v1/tts`); trước khi dùng 3
  endpoint này phải đọc OpenAPI, nếu không hỗ trợ idempotency thì không retry
  sau timeout (như `/v1/audio/speech`) — TK2.2/TK2.13.
- **TH-06:** xem TH-22 mới (G3) + nới lỏng local-only §9.3.
- **TH-07:** bổ sung — sai số mốc đo theo **p95 từng câu** cho SRT dub (không
  chỉ ±0,3 s cho 10 câu đầu ở SrtWriter); T3.3 đo p95 — xem §10.5.
- **TH-08:** bổ sung — time-stretch giữ cao độ phải đo chất lượng nghe ở biên
  1,5× + benchmark librosa vs FFmpeg atempo (TH-20 mới, TK1.9).
- **TH-09:** không bổ sung (giữ P2 — không tuyên bố watermark).
- **TH-10:** không bổ sung mới — validate voice-lock trước khi chạy + lưu
  mapping speaker→voice vào file kịch bản đã có (§3.3, §8).
- **TH-11:** bổ sung khóa model revision — ghim không chỉ `vieneu==3.8.4` mà cả
  `backbone_repo` + `model_subfolder` + revision/commit HF của model (ghi vào
  config + README khi đo ở TK1.3); dữ liệu giọng (25 preset) đi theo SDK version
  đã ghim — nâng SDK thì kiểm lại danh sách giọng (T1.3). Xem §16.

### TH-19 — Treo cứng UI / đứng event loop FastAPI khi inference nặng trên CPU (GPT2 TH-13 + G3 TH-19 — cùng một lỗi, gộp thành 1)

- **DỮ KIỆN:** inference v3 Turbo trên CPU là tác vụ đồng bộ, nặng (RTF ~0,4–1,0
  — xem §10.5); SPEC v1.2 chưa nói inference chạy ở đâu so với luồng UI /
  event loop FastAPI. Nếu `infer()` chạy ngay trên event loop hoặc luồng UI thì
  trong lúc tạo, UI đóng băng, nút Dừng không phản hồi, API khác cũng đứng chờ.
- **Vì sao tử huyệt:** đúng lỗi "bấm Tạo rồi app chết đứng" — người dùng tưởng
  app treo, kill app giữa chừng (kéo theo TH-21/TH-33: history/temp dở dang).
- **Giải pháp:** `V3Engine` chạy inference trong worker thread riêng
  (`run_in_executor` / thread pool 1 worker cho inference — CPU chỉ chạy 1 job
  đồng thời, §4); API không `await` inference trên event loop; job có cờ hủy
  được kiểm tra giữa các chunk; UI cập nhật tiến trình qua poll endpoint 11,
  không chờ đồng bộ. Ticket TK1.8, test T1.8. Mức ưu tiên: **P0**.

### TH-20 — Nút thắt `librosa.effects.time_stretch` + phụ thuộc numba/llvmlite trên Windows/PyInstaller (G3 TH-20 + G4 TH-20 phần librosa — gộp)

- **DỮ KIỆN:** `AudioPost` dùng `librosa.effects.time_stretch` (phase vocoder)
  để đổi tốc độ giữ cao độ (TH-08); SPEC chưa có số đo RTF/chất lượng của bước
  này, cũng chưa tính librosa kéo theo `numba`/`llvmlite` — dependency nặng,
  biên dịch JIT, dễ lỗi khi đóng gói PyInstaller trên Windows. Trong khi đó
  FFmpeg (tải cài sau theo ADR-07/Q21 — không đóng gói kèm) có filter `atempo` giữ cao độ, viết
  bằng C, không thêm dependency.
- **Vì sao tử huyệt:** time-stretch chậm hơn thời lượng audio thì bài dài chờ
  lâu (mục tiêu RTF ≤ 1 ở T2.4 trượt); numba lỗi lúc đóng gói thì `.exe` chết
  ở đúng tính năng tốc độ (TH-18).
- **Giải pháp:** TK1.9 đo RTF + nghe đối chiếu librosa vs FFmpeg `atempo` trên
  cùng câu mẫu ở 0,75×/1,5×; nếu atempo đủ tốt thì dùng FFmpeg làm mặc định
  (bớt 1 dependency nặng), librosa làm dự phòng; nếu giữ librosa thì pin
  `numba`/`llvmlite` + kiểm tra đóng gói ở TK4.1. Mức ưu tiên: **P1** (phần rủi
  ro build PyInstaller là P0 tại TK4.1).

### TH-21 — Mất dữ liệu / corrupt history khi tắt app đột ngột hoặc tràn ổ đĩa (G3 TH-21)

- **DỮ KIỆN:** `HistoryStore` v1.2 ghi trực tiếp file JSON/audio; tắt app đột
  ngột (mất điện, kill) hoặc tràn ổ đĩa đúng lúc ghi thì file history có thể
  corrupt/mất, lần mở sau không đọc được lịch sử.
- **Vì sao tử huyệt:** mất toàn bộ "Bản đã tạo" — đúng dữ liệu người dùng đã
  tạo ra, không khôi phục được bằng cách tạo lại nhanh (phải tạo lại từng bản).
- **Giải pháp:** ghi atomic (ghi file tạm + rename), checkpoint sau mỗi mục
  batch, kiểm tra dung lượng trống trước batch lớn, file history hỏng thì đọc
  bản backup gần nhất + báo rõ (không crash app). Ticket TK2.10, test T3.6.
  Mức ưu tiên: **P1**.

### TH-22 — Bảo mật LAN: X-API-Key qua HTTP không mã hoá, CSRF/DNS Rebinding (G3 TH-22) — HẠ CẤP, P2/backlog

- **DỮ KIỆN (theo G3):** key LAN gửi qua HTTP plaintext thì nghe lén được trên
  LAN; trang web lạ có thể gọi API loopback từ trình duyệt (CSRF/DNS Rebinding)
  vì API không kiểm tra Origin/Host.
- **[HẠ CẤP v1.3 theo quyết định anh 04:20 — chỉ chạy local, dùng cá nhân]**
  TH-22 **không còn là yêu cầu chặn của v1**. Biện pháp mạng duy nhất còn lại
  là bind `127.0.0.1` mặc định. Các biện pháp (Host allowlist, Origin check,
  anti-CSRF token, HTTPS local) chuyển sang §9.3 "Bật lại khi mở LAN".
  Ticket TK2.11 → P2/backlog. Mức ưu tiên: **P2**.
- **Ghi chú phân biệt:** G3-TH-22 (bảo mật LAN) ≠ G4-TH-22 (quá tải đa client,
  xem TH-29) — hai lỗi khác nhau trùng số gốc, đã tách rõ ở đây.

### TH-23 — Trình đọc PDF/DOCX treo hoặc nhả chữ rác với PDF scan và bảng biểu (G3 TH-23)

- **DỮ KIỆN:** `FileReaders` dùng PyMuPDF/python-docx; PDF scan (ảnh, không có
  text layer) thì trích ra rỗng/chữ rác; DOCX/PDF có bảng biểu thì thứ tự đọc
  lộn xộn, mất nghĩa; file lớn có thể treo khi đọc (SPEC chưa đặt giới hạn).
- **Vì sao tử huyệt:** tab Đọc file là 1 trong 7 nhóm tính năng — đọc ra chữ
  rác thì giọng đọc cũng rác, người dùng không biết lỗi ở file hay ở app.
- **Giải pháp:** phát hiện PDF scan (trích được quá ít ký tự/trang) → báo rõ
  "PDF scan, v1 không OCR" + hướng dẫn (không bịa text); bảng: giữ thứ tự đọc
  theo cell, ghi rõ giới hạn; giới hạn kích thước file + timeout đọc theo
  trang. Ticket TK2.12, test T3.4. Mức ưu tiên: **P1**.

### TH-24 — Không có mục hợp đồng triển khai (GPT2 TH-12)

- **DỮ KIỆN:** thông tin triển khai (OS đích, Python, dung lượng đĩa, RAM tối
  thiểu, cổng, model revision, FFmpeg, WebView2, mạng lần đầu) nằm rải rác ở
  §6/§7/§12, không có một chỗ duy nhất để đối chiếu khi build/cài.
- **Vì sao tử huyệt:** thiếu hợp đồng triển khai thì mỗi người build/cài hiểu
  một kiểu — đúng kiểu lỗi "máy tôi chạy được, máy anh không" mà TH-12/TH-18
  đã gặp.
- **Giải pháp:** §16 mới (Hợp đồng triển khai) tập hợp toàn bộ + checklist;
  bản đầy đủ trong `docs/deployment-contract.md` (TK4.6). Mức ưu tiên: **P1**.

### TH-25 — Bộ cài không chạy trên máy sạch: runtime phụ thuộc ẩn (GPT2 TH-16)

- **DỮ KIỆN:** máy mới/máy anh có thể không có Python, WebView2, VC++
  Redistributable, ONNX Runtime DLLs — SPEC v1.2 mới nhắc WebView2 ở C1/C9 mà
  chưa liệt kê thành yêu cầu đóng gói.
- **Vì sao tử huyệt:** `.exe` mở lên chết ngay dù CI xanh (cùng họ lỗi TH-18
  nhưng ở tầng runtime hệ điều hành, không phải file đi kèm).
- **Giải pháp:** TK4.7 kiểm tra runtime phụ thuộc, đóng gói kèm hoặc hướng dẫn
  cài trước, smoke test trên runner sạch (T4.1) + kiểm tra trên máy anh
  (C1/C9). Mức ưu tiên: **P0**.

### TH-26 — Tiến trình ma chiếm cổng 8124 sau khi tắt app + mở trùng instance + `.exe` chỉ hiện console đen (G4 TH-19 + G2 TH-19 — cùng lỗi bóng ma, gộp thành 1)

- **DỮ KIỆN:** SPEC v1.2 có web UI local + `HpApiServer` nhưng **không có lớp
  vỏ Shell Desktop** (không pywebview/WebView2, không logic tắt server khi đóng
  cửa sổ — G4/G2 đều nêu). Đóng cửa sổ UI mà tiến trình Python/server còn chạy
  nền → mở lại app thì bind 8124 thất bại (fail-fast báo cổng bận dù "không có
  app nào chạy"). Mở 2 instance cùng lúc thì instance sau cũng bind thất bại
  mà không báo rõ. Chỉ chạy `uvicorn` thì trên Windows bấm `.exe` chỉ thấy
  console đen, không thấy cửa sổ app (G2).
- **Vì sao tử huyệt:** app không mở lại được sau khi tắt là lỗi "dùng được"
  ở mức cơ bản nhất — người dùng phải tự tìm kill tiến trình trong Task Manager.
- **Giải pháp:** `DesktopShell` (TK4.8, ADR-11): vỏ pywebview/WebView2 (Q20),
  ẩn console (`--noconsole`/pythonw), sở hữu vòng đời server (đóng cửa sổ →
  dừng server + giải phóng cổng 8124, graceful shutdown), chống mở trùng
  instance (mutex/lock file — instance sau báo rõ + không chạy chồng), PID file
  + kiểm tra tiến trình cũ lúc khởi động. Test T4.5, kiểm chứng thật C19.
  Mức ưu tiên: **P0**.

### TH-27 — Thiếu chuẩn hoá text tiếng Việt: số/tiền/ngày/giờ đọc sai (G4 TH-20 phần ViTextNormalizer)

- **DỮ KIỆN:** SDK đọc text thô; SPEC chưa có tầng chuẩn hoá tiếng Việt cho
  số ("1.500.000đ"), tiền tệ, ngày ("15/11/2026"), giờ ("19h30"), đơn vị
  ("3,5kg") — các dạng này có thể bị đọc sai/không tự nhiên.
- **Vì sao tử huyệt:** đọc sai số/tiền/ngày là giọng đọc sai nội dung — video
  bán hàng đọc sai giá/ngày là lỗi không chấp nhận được.
- **Giải pháp:** module `ViTextNormalizer` (TK1.10) trước `TextPreprocess`:
  số → chữ đọc, tiền tệ, ngày/giờ, đơn vị; có công tắc bật/tắt trong Cài đặt;
  test đơn vị T1.9. Mức ưu tiên: **P0**.

### TH-28 — Tràn RAM trình duyệt khi batch 100–500 mục (G4 TH-21)

- **DỮ KIỆN:** UI web render toàn bộ danh sách batch + mỗi mục một audio player
  thì RAM trình duyệt phình, lag/treo tab — khác với RAM engine ở TH-16 (RAM
  phía server khi tạo audio).
- **Vì sao tử huyệt:** tab Tạo hàng loạt là 1 trong 7 nhóm tính năng — UI treo
  ở batch lớn thì tính năng coi như không dùng được.
- **Giải pháp:** virtual list (chỉ render mục đang nhìn thấy) + singleton audio
  player (1 player dùng chung, đổi nguồn khi bấm nghe mục khác). Ticket TK3.7,
  test T3.5. Mức ưu tiên: **P1**.

### TH-29 — Quá tải API local khi nhiều client gọi đồng thời (G4 TH-22) — HẠ CẤP, P2/backlog

- **DỮ KIỆN (theo G4):** nhiều client (Annie + MODOLIVIO + UI) gửi TTS cùng
  lúc → hàng đợi phình, job chờ lâu, history ghi liên tục. Đề xuất gốc:
  JobQueue 2 mức ưu tiên + cờ `save_to_history`.
- **[HẠ CẤP v1.3 theo quyết định anh 04:20 — chỉ chạy local, 1 người dùng]**
  TH-29 **không còn là yêu cầu chặn của v1**; giữ hàng đợi đơn giản hiện tại
  (1 job chạy, tối đa 20 chờ, TTL 60' — §4). 2 mức ưu tiên + `save_to_history`
  → P2/backlog, bật lại khi mở LAN/nhiều client (§9.3). Ticket TK2.14 → P2.
  Mức ưu tiên: **P2**.
- **Ghi chú phân biệt:** G4-TH-22 (quá tải đa client) ≠ G3-TH-22 (bảo mật LAN,
  xem TH-22) — hai lỗi khác nhau trùng số gốc, đã tách rõ ở đây.

### TH-30 — Cache / file tạm phình không trần (GPT2 TH-15 phần còn lại)

- **DỮ KIỆN:** HF cache (model), PreviewCache (mẫu nghe thử), file tạm
  `~/.cache/vieneu/tmp`, log — không có trần dung lượng/tuổi thọ; ổ đĩa đầy
  dần dù `HistoryStore` đã chặn ở 5 GB (TH-16 chỉ bao history).
- **Vì sao tử huyệt:** ổ đĩa đầy giữa batch thì job chết + history cũng không
  ghi được — lỗi xuất hiện muộn, khó chẩn đoán.
- **Giải pháp:** trần + dọn tự động cho preview cache và file tạm (giữ model
  cache), hiển thị dung lượng cache trong Cài đặt, dọn khi vượt trần (TK2.3);
  dọn file tạm khi hủy/crash xem TH-33. Mức ưu tiên: **P1**.

### TH-31 — Bẫy license GPL v3: binary `imageio-ffmpeg` GPL nhúng trong `.exe` PyInstaller onefile phát hành cùng code Apache 2.0 (G2 TH-20)

- **DỮ KIỆN:** binary FFmpeg trong wheel `imageio-ffmpeg` 0.8.1 là **GPL v3**
  (`--enable-gpl --enable-version3`, đo thật ở v1.2 — §13.7/ADR-07); code HP
  là Apache 2.0 (§13.1). PyInstaller onefile **nhúng binary vào trong cùng
  một `.exe`** — không còn là hai file tách bạch đặt cạnh nhau, nên luận điểm
  "aggregate tách bạch" yếu đi: bộ cài phát hành rộng có thể bị coi là phân
  phối chung một chương trình chứa thành phần GPL.
- **Vì sao tử huyệt:** v1 dùng cá nhân (tự build, tự dùng) thì **không bị chặn**
  — nghĩa vụ GPL gắn với phân phối, không gắn với tự dùng. Nhưng phát hành
  rộng / kịch bản B mà giữ nguyên cách đóng gói thì hoặc vi phạm GPL, hoặc
  buộc toàn bộ bộ cài phải tuân thủ GPL (source offer + quyền tương ứng) —
  đúng điểm v1.2 mới ghi "NOTICE + source offer" mà chưa xử lý triệt để.
- **Giải pháp (TK4.9, Q21 — cần anh chốt trước khi phát hành rộng):** (a) đổi
  sang bản build FFmpeg **LGPL** (kiểm `ffmpeg -buildconf` không có
  `--enable-gpl` trước khi dùng — VD bản lgpl của BtbN/gyan.dev); (b) tách
  FFmpeg thành file kèm riêng ngoài `.exe` onefile (không nhúng) + source
  offer; (c) giữ GPL v3 + tuân thủ đầy đủ (NOTICE + source offer + kèm source
  hoặc written offer theo GPL v3 §6). Ghi quyết định vào ADR-07 + §13.7.
  Mức ưu tiên: **P1** (không chặn v1 cá nhân; chặn phát hành rộng/kịch bản B).

### TH-32 — Lỗi Unicode / đường dẫn Windows có dấu tiếng Việt hoặc khoảng trắng (G2 TH-21)

- **DỮ KIỆN (suy luận từ tiền lệ — chưa đo):** đường dẫn Windows của anh có thể
  chứa dấu tiếng Việt (`C:\Người dùng\...`, tên thư mục có dấu) và khoảng
  trắng; `onnxruntime`/`soundfile`/hàm load model từng có tiền lệ lỗi với
  đường dẫn non-ASCII/khoảng trắng trên Windows (G2 nêu; chưa kiểm chứng trên
  máy anh).
- **Vì sao tử huyệt:** model/cache/output mặc định nằm dưới thư mục người dùng
  — đường dẫn lỗi là app chết ngay lần chạy đầu trên đúng máy mục tiêu, không
  sửa được bằng cấu hình UI (người dùng không biết phải dời thư mục đi đâu).
- **Giải pháp:** TK1.1/TK4.7 thêm test đường dẫn có dấu + khoảng trắng cho
  model/cache/output (T4.5); nếu thành phần nào lỗi thì config `model_dir` /
  thư mục dữ liệu mặc định sang vị trí ASCII an toàn + ghi rõ trong README;
  mọi đường dẫn trong code dùng `pathlib` + UTF-8, không nối chuỗi thủ công.
  Mức ưu tiên: **P0**.

### TH-33 — Rò rỉ file tạm, tràn ổ đĩa khi bấm Hủy hoặc tắt máy giữa batch/SRT (G2 TH-22)

- **DỮ KIỆN:** batch/SRT tạo nhiều file tạm (chunk audio, file tạm của
  `TextPreprocess`/`AudioPost`, ZIP đang ghi dở); bấm Hủy hoặc tắt máy/mất
  điện giữa chừng thì file tạm còn lại trên đĩa, lần sau chạy tiếp lại sinh
  thêm — ổ đĩa đầy dần mà `HistoryStore` (chặn ở 5 GB) không bao quát.
  TH-16 chỉ tính RAM + history, TH-30 chỉ đặt trần cache — chưa có cơ chế dọn
  file tạm khi crash/hủy.
- **Giải pháp:** file tạm theo từng job trong thư mục tạm riêng
  (`<data>/tmp/<job_id>/`); hủy job → xoá thư mục tạm của job đó; khởi động app
  quét + xoá file tạm của job không còn chạy (crash lần trước); kiểm tra dung
  lượng trống trước batch lớn (TK2.10/TK2.6). Mức ưu tiên: **P1**.

### Bảng phân loại ưu tiên P0/P1/P2 — tất cả tử huyệt (v1.3, theo §0.1)

| Tử huyệt | Mức | Lý do xếp hạng (1 dòng) |
|---|---|---|
| TH-01 Giấy phép theo tài sản | P1 | Không chặn v1 cá nhân; chặn kịch bản B |
| TH-02 Model tải lần đầu | P0 | Không có model = không chạy |
| TH-03 CPU/VNNI/precision | P0 | Sai precision = méo tiếng / chậm không dùng được |
| TH-04 Clone giọng | P0 | Không rào chắn = cửa giả mạo |
| TH-05 V4 phí/fallback | P0 | Tính phí trùng / fallback sai giọng |
| TH-06 API LAN | P2 | Hạ cấp local-only (§9.3) |
| TH-07 SRT khớp giờ | P0 | Tính năng lồng tiếng cốt lõi |
| TH-08 Tốc độ | P0 | Tính năng tốc độ cốt lõi |
| TH-09 Watermark | P2 | Không tuyên bố ở v1; P2 backlog |
| TH-10 Voice-lock hội thoại | P0 | Trộn giọng = sai tính năng |
| TH-11 Trôi version SDK | P0 | Nâng SDK vỡ API |
| TH-12 Build Windows | P0 | Không có `.exe` = không tới được máy anh |
| TH-13 Cổng 8123 | P0 | Trùng cổng = không chạy cùng MODOLIVIO |
| TH-14 MP3 | P0 | Không có encoder = mất định dạng đã hứa |
| TH-15 Upstream/HF mất hẳn | P1 | Giảm thiểu (mirror/checksum), chưa chặn ngay |
| TH-16 RAM batch lớn | P0 | Batch lớn chết giữa chừng |
| TH-17 Cam kết clone | P1 | Pháp lý/quy trình; cam kết bắt buộc đã ở TH-04 |
| TH-18 `.exe` thiếu file | P0 | CI xanh, máy thật đỏ |
| TH-19 Treo UI/event loop | P0 | UI đóng băng = không dùng được |
| TH-20 librosa/numba | P1 | Mượt mà + rủi ro build (phần build là P0 ở TK4.1) |
| TH-21 History corrupt | P1 | Mất dữ liệu đã tạo |
| TH-22 LAN CSRF/DNS | P2 | Hạ cấp local-only (§9.3) |
| TH-23 PDF scan/bảng | P1 | Đọc rác = giọng đọc rác |
| TH-24 Hợp đồng triển khai | P1 | Tài liệu; giảm lỗi "máy tôi chạy được" |
| TH-25 Máy sạch | P0 | `.exe` chết ngay trên máy mới |
| TH-26 Tiến trình ma | P0 | Không mở lại được app |
| TH-27 Chuẩn hoá tiếng Việt | P0 | Đọc sai số/tiền/ngày = sai nội dung |
| TH-28 RAM trình duyệt batch | P1 | UI batch lag/treo ở batch lớn |
| TH-29 Đa client | P2 | Hạ cấp local-only (§9.3) |
| TH-30 Cache/temp phình | P1 | Ổ đĩa đầy dần |
| TH-31 Bẫy GPL FFmpeg | P1 | Không chặn v1 cá nhân; chặn phát hành rộng |
| TH-32 Unicode đường dẫn | P0 | Chết ngay lần chạy đầu trên máy mục tiêu |
| TH-33 Rò rỉ file tạm | P1 | Ổ đĩa đầy sau nhiều lần hủy/crash |

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
- [Sửa R2-V4] `Idempotency-Key` (OpenAPI `POST /v1/tts`, kiểm chứng 19/11/2026):
  header tùy chọn, 8–128 ký tự ASCII in được (UUID lý tưởng), nhớ 24 h theo API
  key; cùng key + cùng body → trả job ĐẦU TIÊN (không tính phí lần 2,
  `Idempotent-Replayed: true`); 409 `IDEMPOTENCY_IN_FLIGHT` → retry cùng key
  sau `Retry-After`; 422 `IDEMPOTENCY_KEY_REUSED` (key cũ + body khác).
  `POST /v1/audio/speech` **không có** tham số này (`parameters: []`) — không
  retry sau timeout. Mã lỗi: hết token → **403** (402 chỉ ở audiobook),
  rate limit → 429. Số dư: `GET /v1/balance` (TỒN TẠI — `remaining`,
  `spendableTokens`, `totalRemainingTokens`, `plan`); hệ số phí:
  `GET /v1/engines` (`billingMultiplier` từng engine + `globalMultiplier`);
  phí = ký tự (tối thiểu 50) × engine multiplier × globalMultiplier; token trừ
  lúc gửi, hoàn lại nếu job thất bại vĩnh viễn. `/v1/dialogue` 1–50 lượt;
  `/v1/dub` tính phí theo thời lượng audio đầu ra (không phải ký tự);
  `/v1/emotion-tags`: v4 xóa mọi tag lạ khỏi text (chỉ giữ `[cười]`/
  `[thở dài]`/`[hắng giọng]`).
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
3. **Local-first, fail-closed:** mặc định loopback, V4 mặc định tắt, LAN opt-in
   (key bắt buộc chỉ khi mở LAN — §9.3; v1 local-only không bắt buộc).
   [Sửa v1.3 — NỚI LỎNG theo quyết định anh 04:20] (TH-05, TH-06).
4. **Không hardcode:** máy, cổng, thư mục model, thư mục xuất đều qua config (mục 6).
5. **Ghi dần ra đĩa** cho bài dài; job có trạng thái, thử lại, huỷ được.
6. **Một nhân vật = một giọng cố định** trong hội thoại (TH-10).
7. **Desktop Shell sở hữu vòng đời server; inference không chạy trên luồng UI**
   (TH-19, TH-26): đóng cửa sổ → dừng server + giải phóng cổng; không có tiến
   trình ma, không mở trùng instance.

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
| `AudioPost` | Time-stretch giữ cao độ 0,75×–1,5× bằng `librosa.effects.time_stretch` (phase vocoder — xem TH-08/Y4; `soxr` chỉ resample, không dùng để đổi tốc độ); nối chunk + khoảng lặng (kể cả silence từ thẻ `[nghỉ]`); chuẩn hoá; xuất WAV (48 kHz V3 / theo engine V4) + MP3; ghi dần ra đĩa cho bài dài. [Sửa R1-Y1] MP3 mã hoá bằng **FFmpeg TẢI CÀI SAU (Q21 — ĐÃ CHỐT 04:35 19/11: không đóng gói kèm bộ cài; lần đầu chạy tải binary về thư mục dữ liệu, kiểm checksum, báo tiến trình; fallback sang FFmpeg hệ thống nếu có; không có FFmpeg → chỉ xuất WAV + báo rõ, không báo lỗi chung chung)**. FFmpeg cũng là bộ giải mã MP3/M4A cho đầu vào clone giọng (chiều ngược của Y1: `soundfile` không giải mã được MP3/M4A). [Sửa R2-Y1] **Số đo thật, bỏ con số "~25–30 MB" của v1.1:** binary Linux trong wheel `imageio-ffmpeg` 0.8.1 là `ffmpeg-linux-x86_64-v9.0.2` = **172.692.552 byte (~165 MB)**, wheel nén 68 MB — đo thật bằng binary trong wheel ngày 19/11/2026; số Windows chưa đo (cùng họ build BtbN full, cùng cấp độ lớn — đo ở TK4.1). Ngân sách bộ cài Q2 (~300–400 MB kèm model) **không còn cộng ~165 MB này** (Q21: FFmpeg tải riêng sau, không trong bộ cài). [Đính chính 19/11/2026 — đợt nối tiếp Q21] **License theo đường lấy binary:** binary **tải sau chính là LGPL v3 (BtbN)** — xem §13.7; câu dưới chỉ đúng cho binary **imageio-ffmpeg 0.8.1 dự phòng (máy dev)**: **GPL v3, không phải LGPL** — chạy `ffmpeg -buildconf` trên binary thật: `--enable-gpl --enable-version3 --enable-libx264 --enable-libx265`; license của wrapper `imageio-ffmpeg` là BSD-2-Clause, nhưng license của **binary** là GPL v3 (xem §13.7 + ADR-07). PyInstaller **KHÔNG** collect binary `imageio_ffmpeg/binaries/*` (Q21 — không đóng gói kèm; bẫy onefile TH-31 không còn). Quyết định ghi ở ADR-07 | TH-08; librosa đã là dependency SDK; FFmpeg |
| `PreviewCache` | [Sửa R1-Y7] Nghe thử giọng: V3 dùng mẫu thu sẵn (tạo lần đầu rồi cache trên đĩa, không tổng hợp lại mỗi lần mở tab); V4 preview cache theo khóa (voice_id + câu mẫu) — nghe lần 2 cùng giọng + cùng câu mẫu thì phát file cache, **không gọi lại API**; UI hiện ước tính ký tự trước khi nghe thử V4 lần đầu. [Sửa R2-Y7] Ước tính phí preview phải tính **tối thiểu 50 ký tự/request** (`max(50, len(câu mẫu))` × multiplier — xem TH-05): câu mẫu ≤ 60 ký tự thì lần nghe đầu mỗi giọng tốn 50 ký tự tối thiểu, không phải đúng số ký tự câu mẫu. Câu mẫu preview mặc định ≤ 60 ký tự (đề xuất; chốt ở Q12 §15) | Thiết kế HP |
| `PronDict` | Từ điển phát âm: thêm/sửa/xoá, import/export CSV, áp trước khi infer; giới hạn 2.000 mục (theo VieNeu Studio) | CIT, VieNeu Studio |
| `JobQueue` | Hàng đợi job (tạo → đang chạy → xong/lỗi); tạm dừng khi lỗi (theo VieNeu Desktop); huỷ; thử lại | VieNeu Desktop |
| `HistoryStore` | Lưu bản đã tạo (audio + SRT + metadata: text, giọng, engine, tốc độ, thời gian, dung lượng); nghe/tải lại; **chặn tạo mới khi vượt `max_history_gb`** + báo rõ lý do và hướng xoá/xuất bớt; **không tự xoá**. [Sửa R1-TH-16] Khi vượt `max_history_gb` (mặc định 5 GB): **chặn tạo mới + báo rõ lý do và hướng xoá/xuất bớt** — không chỉ nhắc, vì người dùng có thể bỏ qua nhắc; vẫn cho nghe/tải/xoá bản cũ để mở lại dung lượng | CIT |
| `ConfigStore` | Đọc/ghi `config.yaml` + key V4/key API LAN — xem mục 6. [Sửa R1-Y12] Key lưu qua `keyring` (Windows: DPAPI/Credential Manager; Linux: Secret Service, fallback file `secrets.json` quyền `0600`); không lưu key plaintext trên Windows | — |
| `HpApiServer` | FastAPI, mục 4 | `apps/openai_speech.py` (tham khảo) |

[Sửa v1.3 — module/bổ sung từ phản biện team]
- `ViTextNormalizer` (TH-27, TK1.10): chuẩn hoá số/tiền/ngày/giờ tiếng Việt
  thành chữ đọc được, chạy trước `TextPreprocess`; có công tắc bật/tắt.
- `DesktopShell` (G4/G2, TK4.8): vỏ desktop (pywebview/WebView2, Q20) mở UI
  local, sở hữu vòng đời `HpApiServer`: đóng cửa sổ → dừng server + giải phóng
  cổng 8124 (chống tiến trình ma TH-26); ẩn console (không để `.exe` chỉ hiện
  console đen); chống mở trùng instance (mutex/lock file).
- `SrtDubber` bổ sung (G4): parser **.vtt** (UI §5 hứa thả `.srt/.vtt` nhưng
  SPEC chỉ mô tả parse SRT — v1.3 chốt: `.vtt` được chuyển về dạng SRT nội bộ
  trước khi căn giờ: bỏ header `WEBVTT`, giữ mốc giờ + text); quy tắc
  `[nghỉ]` + tốc độ 0,75× (G3): tag `[nghỉ]` trong câu SRT được parse thành
  khoảng lặng tính vào độ dài slot của câu, không đưa vào `infer()`; tốc độ
  người dùng chọn (0,75×–1,5×) áp trước, hệ số căn giờ từng câu chỉ được
  phép đẩy tốc độ hiệu dụng tối đa tới 1,5× và tối thiểu 0,75× — vượt thì
  lấn khoảng lặng → đẩy câu sau → báo cáo câu bị lùi (như TH-07).
- `EngineRouter` bổ sung (G4): fallback V4→V3 cho cả `POST /v1/dialogue`,
  `/v1/dub`, `/v1/srt` theo cùng bảng ánh xạ giọng + `voice_strict` (§3.3);
  idempotency của 3 endpoint này chưa xác nhận trong OpenAPI (xem TH-05 bổ
  sung ở §1) — không retry sau timeout khi chưa xác nhận.
- `V3Engine` bổ sung (TH-19): inference chạy trong worker thread riêng, không
  chạy trên event loop FastAPI / luồng UI (TK1.8).
- `HistoryStore` bổ sung (TH-21/TH-30/TH-33): ghi atomic (file tạm + rename),
  checkpoint sau mỗi mục batch, trần + dọn preview cache/file tạm, file tạm
  theo từng job + xoá khi hủy + quét dọn lúc khởi động (TK2.10).
- `FileReaders` bổ sung (TH-23): phát hiện PDF scan → báo rõ "v1 không OCR",
  không bịa text; giới hạn kích thước/timeout đọc (TK2.12).
- Đóng gói bổ sung (TH-31/TH-32): quyết định license FFmpeg ở TK4.9 (Q21);
  test đường dẫn có dấu/khoảng trắng ở TK4.7 (T4.5).

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

[Sửa v1.3 — TH-29 hạ cấp] JobQueue 2 mức ưu tiên + cờ `save_to_history` (G4)
là P2/backlog, chỉ bật lại khi nhiều client (§9.3); v1 giữ hàng đợi đơn giản
(1 job chạy, tối đa 20 chờ, TTL 60').

Auth [Sửa v1.3 — NỚI LỎNG theo quyết định anh 04:20]: loopback không cần key;
server mặc định chỉ bind `127.0.0.1` (biện pháp mạng duy nhất còn lại). LAN là
opt-in trong Cài đặt, **không bắt buộc `X-API-Key` ở v1** (khuyến nghị mềm: tự
đặt key nếu mở LAN). Các yêu cầu chặt về LAN (key bắt buộc, giới hạn endpoint
LAN, chống CSRF/DNS-rebinding, rate-limit đa client) hạ xuống P2/backlog —
xem §9.3, bật lại khi mở LAN. (TH-06)
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
| 18 | `POST /v1/audio/speech` | **Tương thích OpenAI** (để Annie/tool khác dùng SDK OpenAI) | `{ input, model, voice, response_format: "wav"\|"mp3", speed? }` | audio bytes (MP3 qua FFmpeg tải sau — Q21, ĐÃ CHỐT; upstream chỉ có wav/pcm, HP thêm mp3 theo ADR-07; `speed` nếu chưa hỗ trợ thì báo header `X-VieNeu-Ignored: speed`, không lặng lẽ bỏ) |
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
| **Phòng thu / TTS Studio** | Ô nhập text (đếm ký tự); dropdown Giọng đọc (25 preset + clone, ghi rõ giới tính/vùng/phong cách, nghe thử từng giọng); chọn Engine V3/V4 (V4 hiện phí/ký tự); tốc độ 0,75×–1,5×; nút chèn cảm xúc `[cười]` `[thở dài]` `[hắng giọng]`, thẻ nghỉ `[nghỉ 2s]`/`[nghỉ 500ms]` (tối đa 10 s/thẻ — [Sửa R1-Y2] thẻ nghỉ do tầng app `TextPreprocess` xử lý, SDK không có sẵn); từ điển phát âm (nút Từ điển, CSV import/export); nút Tạo; trình phát nghe lại; xuất WAV/MP3 (MP3 qua FFmpeg tải sau, ADR-07 — Q21 ĐÃ CHỐT); tạo kèm .srt (mốc suy bằng `SrtWriter`, ±0,3 s/câu — Y3); hàng đợi (nhiều bản đọc xếp hàng, tạo bản sau trong lúc bản trước phát, nút Dừng phát) | T1.2, T2.2, T2.10, T3.1 |
| **Hội thoại / Podcast** | Bảng kịch bản: mỗi dòng (nhân vật, lời thoại); mỗi nhân vật gán 1 giọng cố định (dropdown, khoá); thêm/xoá nhân vật (tối đa 8); khoảng lặng giữa lượt; ghép thành 1 file; lưu/mở kịch bản | T3.2 |
| **Lồng tiếng .srt** | Thả file .srt/.vtt → danh sách câu + mốc giờ; chọn giọng + tốc độ; bấm Lồng tiếng; tiến trình từng câu; kết quả: audio dài đúng bằng video + SRT đã chỉnh mốc (nếu câu bị lùi) + danh sách câu bị lùi; quy tắc: câu dài đọc nhanh tối đa 1,5×, không cắt chữ | T3.3 |
| **Đọc file** | Thả PDF/DOCX/TXT → xem trước text → Làm sạch (bỏ khoảng trắng thừa, giữ công thức) → chuyển sang Phòng thu tạo giọng | T3.4 |
| **Tạo hàng loạt** | Nhập trực tiếp (mốc `[P1]`, `[P2]`…) hoặc tải file .txt/.json; mỗi mốc 1 file; tải từng file / tải tất cả (.zip); tiến trình từng mục; mục lỗi thử lại riêng | T3.5 |
| **Bản đã tạo** | Danh sách bản đã tạo (tên, giọng, engine, thời lượng, dung lượng, ngày); nghe lại, tải lại WAV/MP3/SRT, mở thư mục chứa file; xoá; hiển thị tổng dung lượng + **chặn tạo mới khi vượt `max_history_gb`** (TH-16) | T3.6 |
| **Giọng của tôi** | Danh sách giọng clone (tên, ngày tạo, cam kết); thu micro 3–8 s hoặc nhập file MP3/WAV/M4A (MP3/M4A giải mã bằng FFmpeg — Y1); màn hình cam kết quyền sử dụng (bắt buộc); nghe thử; xoá (xoá cùng cam kết; có cơ chế gỡ khi bị khiếu nại — TH-17) | T2.5 |
| **Cài đặt** | Giọng mặc định; model (precision fp32/int8 + tự phát hiện CPU, threads); thư mục lưu + thư mục model/cache; Engine V4: nhập/xoá key, hiện trạng thái (chưa có key / key hợp lệ / lỗi), ước tính phí, ngưỡng cảnh báo ký tự; API local: cổng, bật/tắt LAN (khoá API chỉ bắt buộc khi mở LAN — §9.3), nút tạo khoá mới; giao diện sáng/tối; giới thiệu + giấy phép + ghi công VieNeu-TTS | T3.7 (phần key V4: T2.6) |

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
  shell_backend: "pywebview"  # [Sửa v1.3 — G4/G2, Q20 §15] vỏ desktop (pywebview/WebView2); chốt ở Bước 3/4
server:
  host: "127.0.0.1"      # mặc định loopback; "0.0.0.0" chỉ khi bật LAN trong Cài đặt
  port: 8124             # [Sửa R1-R1] mặc định mới — 8123 đã có chủ (server TTS MODOLIVIO); xem bảng cổng §4
  lan_enabled: false     # [Sửa v1.3 — local-only] opt-in; mở LAN ở v1 KHÔNG bắt buộc key (xem §9.3); key LAN bắt buộc chỉ bật lại khi mở LAN cho nhiều client
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
    fallback_voice: "map"  # [Sửa R2-N-FB] "map" (ánh xạ V4→V3 theo docs/voice-fallback-map.md) | "default" (về "Hải Đăng") | "fail" (không fallback giọng)
    # Idempotency: V4Engine sinh Idempotency-Key = UUID theo HP job id cho mọi POST /v1/tts (lưu cùng job); KHÔNG retry POST /v1/audio/speech sau timeout (không hỗ trợ idempotency) — xem TH-05
    warn_chars: 100000   # ngưỡng cảnh báo ký tự/phiên (người dùng đổi được) — tính bằng KÝ TỰ, phí thật = ký tự (tối thiểu 50/request) × billingMultiplier × globalMultiplier (xem TH-05)
    timeout_sec: 60
    max_retries: 1       # chỉ retry lỗi 5xx/timeout TRÊN ĐƯỜNG ASYNC CÓ Idempotency-Key; không retry 4xx; không retry POST /v1/audio/speech sau timeout
audio:
  default_voice: "Hải Đăng"
  default_speed: 1.0     # 0.75–1.50
  default_format: "wav"  # "wav" | "mp3"
  mp3_encoder: "ffmpeg"  # [Sửa Q21 — ĐÃ CHỐT 04:35 19/11] FFmpeg TẢI CÀI SAU lần đầu chạy, không đóng gói kèm; không có FFmpeg → chỉ xuất WAV
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
  max_history_gb: 5      # chặn tạo mới + báo rõ khi vượt (TH-16)
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
├── requirements.txt         # [Sửa R2] ghim version đầy đủ (TK1.1): vieneu==3.8.4 + fastapi + uvicorn + imageio-ffmpeg==0.8.1 + keyring==25.7.0 + py-cpuinfo==9.0.0 + PyMuPDF==1.28.2 + python-docx==1.2.0 (+ pywin32-ctypes trên Windows, SecretStorage + jeepney trên Linux — dependency theo platform của keyring). PyMuPDF 1.28.2 = bản 1.x mới nhất tại thời điểm viết SPEC (19/11/2026), thỏa floor `PyMuPDF>=1.25.0` của extra `[pdf]` trong upstream `pyproject.toml:106`; tránh dòng 2.x chưa kiểm chứng; kiểm chứng tương thích ở TK1.1
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
| Hạn mức nhà cung cấp | V4: quota token theo gói; hết quota → job lỗi; Cloud API có thể đổi giá/endpoint. [Sửa R2-V4] Công thức phí thật (OpenAPI `GET /v1/balance` + `GET /v1/engines`, kiểm chứng 19/11/2026): **ký tự (tối thiểu 50/request) × engine `billingMultiplier` × `globalMultiplier`** (VD v4 multiplier 3,4; `globalMultiplier` thường là 1) — ước tính phí trong UI phải nhân đủ hệ số, không đếm ký tự trần. `GET /v1/balance` trả `remaining` (request lớn nhất trả được ngay lúc này — không phải tổng), `spendableTokens` (tổng các gói), `totalRemainingTokens`, `plan`; kèm `GET /v1/usage` (sổ chi tiết 92 ngày). Hết token → **403** (không phải 402; 402 chỉ ở audiobook) | Fallback V3 tự động (TH-05); `V4Engine` xử lý 401/403/429 riêng, báo rõ "hết quota"; `Idempotency-Key` cho `POST /v1/tts` tránh tính phí trùng khi retry | Khi dùng V4 thường xuyên: thêm màn hình số dư/quota dùng **`GET /v1/balance`** (TỒN TẠI — bỏ ghi "CHƯA RÕ" của v1.1); phương án dự phòng nếu endpoint đổi: **tự đếm ký tự đã gửi** (dữ liệu đã có từ `V4Engine`, nhân với multipliers lấy từ `GET /v1/engines`) |
| Quyền riêng tư | Nội dung qua V4 cloud rời khỏi máy (text gửi lên API); V3 local không rời máy. [Sửa R1-§7] Chưa có chính sách lưu trữ/xoá dữ liệu người dùng (text, giọng clone, lịch sử) khi có nhiều người dùng | UI ghi rõ: V3 = trên máy, V4 = gửi text lên cloud; mặc định V3; text/giọng clone chỉ lưu local, không đồng bộ cloud trừ khi người dùng bật | Khi xử lý text nhạy cảm: mặc định V3, cảnh báo trước khi gửi V4. Khi có >1 người dùng: viết chính sách lưu trữ/xoá + cơ chế gỡ giọng (TH-17) |

[Sửa v1.3 — G4 + model card] Mốc kích hoạt thương mại vẫn giữ yêu cầu xin xác
nhận **bằng văn bản từ tác giả (pnnbao-ump)** về giấy phép thương mại của đúng
25 giọng SDK 3.8.4 — vì model card đọc được chỉ ghi cho SDK v3.7.1/23 giọng
(xem TH-01) — trước khi bán/chia sẻ rộng. Không tự liên hệ tác giả khi chưa có
lệnh của anh; hạng mục này nằm trong danh sách việc cần anh/Annie làm ở Bước 4.

### 9.3. Nới lỏng local-only + bật lại khi mở LAN (quyết định anh 04:20 19/11)

HP Voice Studio v1 **chỉ chạy local, dùng cá nhân trên máy** nên không áp mức
chặt bảo mật mạng. Biện pháp mạng duy nhất còn lại ở v1: **API server bind
`127.0.0.1` mặc định** (không bind `0.0.0.0`).

Các biện pháp sau **đã bỏ khỏi yêu cầu chặn v1** (hạ xuống P2/backlog) — liệt
kê đầy đủ ở đây để sau này bật lại không phải tìm lại:

| # | Biện pháp đã bỏ (v1) | Nguồn gốc | Bật lại khi |
|---|---|---|---|
| L1 | LAN opt-in bắt buộc sinh khoá API + LAN chỉ mở endpoint tạo giọng | TH-06 | Mở LAN cho máy khác gọi API |
| L2 | Chống CSRF / DNS Rebinding (Host allowlist, Origin check, anti-CSRF token) | G3 TH-22 → TH-22 | Mở LAN hoặc mở UI qua trình duyệt ngoài |
| L3 | Rate-limit đa client + JobQueue 2 mức ưu tiên + cờ `save_to_history` | G4 TH-22 → TH-29 | Nhiều client (Annie + MODOLIVIO + UI) gọi đồng thời |
| L4 | HTTPS local / key LAN bắt buộc | TH-06/TH-22 | Mở LAN trên mạng không tin cậy |

**Mốc kích hoạt bật lại:** khi anh nói "mở LAN" hoặc "cho Annie gọi API từ
máy khác" — lúc đó cần anh chốt lại (không tự bật). **Không nới lỏng:**
key V4 lưu qua `keyring`/DPAPI (TH-05 — bảo vệ tiền), cam kết clone giọng
(TH-04/TH-17), giấy phép theo tài sản (TH-01), V4 fallback/idempotency
(TH-05), SRT/batch/đóng gói.

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

> [Sửa v1.3 — §0.1] Mỗi giai đoạn nghiệm thu bằng **tính năng chạy thật**
> (file WAV thật / response API thật / thao tác UI thật), không phải bằng
> checklist tick trên giấy. Bảng tổng kết nghiệm thu theo tính năng ở §10.6.

### Bước 1 — Engine V3 + WAV thật

| ID | Tính năng | Kiểm chứng chạy thật (lệnh / file ra / cách đo) | Đạt khi |
|---|---|---|---|
| T1.1 | Cài SDK + tải model | `pip install vieneu==3.8.4` (hoặc `uv sync` từ repo); chạy `scripts/download_model.py`; đo dung lượng cache HF trước/sau **từng thành phần** (`du -sh ~/.cache/huggingface` trước/sau từng bước: backbone, codec, speaker-encoder/denoiser, tokenizer) + thời gian tải. [Sửa R1-Y10] Sau khi tải xong: **chặn mạng hoàn toàn, khởi động lại app, tạo WAV** — kiểm tra không còn gọi HF | Model tải xong, ghi rõ tổng dung lượng **theo từng thành phần** vào README; lỗi mạng → báo rõ + thử lại được; chặn mạng vẫn tạo được WAV mới là "offline hoàn toàn", nếu không thì ghi rõ thành phần còn thiếu |
| T1.2 | WAV thật giọng preset | `python -c "from vieneu import Vieneu; v=Vieneu(); a=v.infer('Xin chào các bạn!', voice='Hải Đăng'); v.save(a,'outputs/t1_2.wav')"`; kiểm tra file: `ffprobe outputs/t1_2.wav` (48 kHz, mono), thời lượng > 0, nghe thử | WAV 48 kHz thật, nghe rõ tiếng Việt, đúng giọng preset |
| T1.3 | Liệt kê 25 giọng | `v.list_preset_voices()` → đếm = 25, có đủ 10 featured ⭐, default "Hải Đăng" | Khớp bảng §2.2; sai tên → ValueError rõ ràng |
| T1.4 | Hiệu năng CPU | Đo RTF: tạo 60 s audio, `RTF = thời gian xử lý / thời lượng audio` (script như README); thử cả fp32 và int8; ghi CPU máy đo. [Sửa R1-Y9/G9] Ghi rõ CPU tham chiếu (máy đo là CPU nào, có VNNI không — kiểm tra precision tự chọn đúng trên cả máy có VNNI và máy không có VNNI; không phát hiện được → mặc định fp32). [Sửa R1-§5] Mục tiêu RTF ≤ 1 gắn với CPU tham chiếu là **CPU máy anh, đo ở C6** — số RTF trên CPU khác chỉ để tham khảo, không thay cho số trên máy anh. [Sửa R2-Y9] Phát hiện VNNI theo phương pháp mới (TH-03): cờ **`avx512vnni`** của `py-cpuinfo` 9.0.0 (không gạch dưới) cho AVX-512 VNNI + **CPUID leaf 7 subleaf 1 EAX bit 4** (Linux: token `avx_vnni` trong `/proc/cpuinfo`; Windows: helper `ctypes` riêng) cho AVX-VNNI; kiểm chứng trên cả ba loại máy (chỉ AVX-512 VNNI, chỉ AVX-VNNI, không có VNNI) rằng precision tự chọn là đúng — riêng máy chỉ có AVX-VNNI (VD i5 12th-gen) là trường hợp v1.1 phát hiện sai, phải test riêng. "Méo" = nghe đối chiếu int8 vs fp32 trên cùng câu mẫu, anh nghe bằng tai + ghi nhận xét; khác biệt rõ ràng → fallback fp32. [Sửa R2 — nhánh dự phòng] Nếu fp32 RTF > 1 trên CPU máy anh: RTF ≤ 1,5 → chấp nhận chậm + hiện tiến trình; RTF > 1,5 → mặc định v3 Nano cho bản nháp (ghi rõ lý do trong UI); cả Nano cũng RTF > 1 → báo rõ máy không đủ + hướng dẫn nâng cấp | RTF ≤ 1 trên CPU máy anh, **ghi rõ model CPU** (không để "CPU 4 nhân" chung chung); int8 méo tiếng → fallback fp32 + ghi chú; precision tự chọn đúng theo VNNI (cả AVX-512 VNNI lẫn AVX-VNNI) |
| T1.5 | Stream | `infer_stream()` → chunk đầu tiên về trong ≤ 500 ms trên CPU (mục tiêu; README ghi ~140 ms int8 / ~300 ms fp32). [Sửa R1-§5] Đo thêm độ trễ **chunk thứ 2 trở đi** (không chỉ chunk đầu) | Nghe được audio ngay khi đang tạo (không chờ hết câu); chunk sau không trễ hơn 500 ms/chunk |
| T1.6 | Batch | `infer_batch([10 câu])` → 10 file, đúng thứ tự, đúng giọng. [Sửa R1-G8] Bỏ tiêu chí cũ "thời gian ≤ 10× infer đơn" (hiển nhiên đúng, không đo được gì) | Không lẫn câu/giọng; **RTF batch không tệ hơn 1,2× RTF infer đơn** trên cùng CPU |
| T1.7 | Thời gian khởi động | [Sửa R1-G9] Đo từ lúc mở app tới khi sẵn sàng tạo (model đã tải sẵn): ghi thời gian load model fp32/int8 riêng (README ghi int8 "load ~14 s", fp32 chưa rõ) | Sẵn sàng tạo trong ≤ 30 s trên máy anh (mục tiêu, đo thật ở C1); quá 30 s thì hiện tiến trình load, không đứng hình |
| T1.8 | UI không treo khi inference | Tạo câu dài (20.000 ký tự) → trong lúc tạo, UI vẫn phản hồi click/chuyển tab (đo thời gian phản hồi, xem §10.5), nút Dừng phản hồi; kiểm tra inference không chạy trên event loop/UI thread (log thread id) | Không đóng băng UI; Dừng ≤1,5 s (mục tiêu chặt ≤200 ms — §10.5) |
| T1.9 | Chuẩn hoá tiếng Việt | Nhập câu có số/tiền/ngày/giờ ('1.500.000đ', '15/11/2026', '19h30', '3,5kg') → tạo giọng → nghe: số/tiền/ngày đọc đúng dạng chữ tiếng Việt; tắt normalizer thì đọc thô như cũ | Nghe đúng; có công tắc bật/tắt |

### Bước 2 — API local

| ID | Tính năng | Kiểm chứng | Đạt khi |
|---|---|---|---|
| T2.1 | `GET /health`, `GET /voices` | [Sửa R1-R1] `python scripts/check_port.py` (8124 trống, không trùng bảng §4) rồi `curl http://127.0.0.1:8124/health`, `/voices` → JSON 200, đủ 25 giọng. Cố ý curl 8123 phải trả về MODOLIVIO (không phải HP) — test pass giả nếu nhầm cổng. [Sửa R2 💭] **Điều kiện tiên quyết:** curl 8123 chỉ trả về MODOLIVIO khi **server MODOLIVIO đang chạy lúc test**; nếu MODOLIVIO không chạy thì kết quả đúng phải là "connection refused", không phải trả về HP — ghi rõ trạng thái MODOLIVIO lúc test vào log test | Response thật từ HP (kiểm tra `version` trong `/health`), đúng schema `docs/api-contract.md` |
| T2.2 | `POST /api/tts/generate` | `curl -X POST .../api/tts/generate -d '{"text":"...","voice_id":"Mai Anh"}'` → WAV 48 kHz; test bằng OpenAI SDK trỏ `base_url` về HP (`/v1/audio/speech`) | WAV thật + OpenAI SDK gọi được |
| T2.3 | Stream API | `POST /api/tts/stream` → chunk đầu ≤ 1 s | Stream thật, không chờ hết |
| T2.4 | Tốc độ 0,75×–1,5× | Tạo cùng câu ở 1,0× và 1,5×; đo thời lượng bằng `ffprobe` → tỉ lệ ≈ 1/1,5 (±10%), nghe không méo nặng. [Sửa R1-Y4/G8] Đo thêm **RTF của bước time-stretch** (`librosa.effects.time_stretch`, thời gian xử lý / thời lượng audio); tốc độ 1,0× không qua time-stretch (không tốn thời gian xử lý thêm). [Sửa R2-Y4 💭] Đặt mục tiêu: **RTF time-stretch ≤ 1** (phase vocoder trên CPU mà chậm hơn thời lượng audio thì bài dài chờ lâu — vượt thì ghi rõ chấp nhận chậm + hiện tiến trình, không giấu). [Sửa v1.3 — TH-20] Đo thêm RTF + nghe đối chiếu `librosa` vs FFmpeg `atempo` ở 0,75×/1,5× (TK1.9) | Đúng tỉ lệ, nghe được; RTF time-stretch ≤ 1; có số đo so sánh librosa vs atempo (TK1.9) |
| T2.5 | Clone giọng | Thu/nhập clip 3–8 s của chính anh (có cam kết) → `POST /api/voices/clone` → tạo câu bằng giọng clone → nghe thử; thử clip không cam kết → 400 | Giọng clone nghe giống mẫu; không cam kết thì bị chặn |
| T2.6 | V4 (hỏi Annie trước, không tự test bằng key anh) | Nhập key test do người dùng cung cấp trong Cài đặt → `POST /api/tts/generate {"engine":"v4","voice_id":"Hạ Vy"}` → WAV; rút key / giả lỗi mạng → fallback V3 + báo rõ lý do **+ giọng mới** (theo bảng ánh xạ fallback §3.3). [Sửa R1-§5] Test thêm từng mã riêng: key sai → 401, hết quota → **403** (không phải 402 — [Sửa R2-V4] 402 chỉ ở audiobook), quá tải → 429 — mỗi mã báo đúng lý do (không gộp thành "lỗi V4"). [Sửa R2-V4] Test thêm idempotency: gửi `POST /v1/tts` 2 lần cùng `Idempotency-Key` + cùng body → cùng `jobId`, không tính phí lần 2 (`Idempotent-Replayed: true`); 409 → retry cùng key sau `Retry-After`; 422 (key cũ + body khác) → báo lỗi, không retry; gửi `POST /v1/audio/speech` sau timeout giả lập → **không tự retry** (chỉ retry khi chưa gửi đi được) | V4 ra WAV thật; fallback đúng + báo lý do + giọng mới; 401/**403**/429 phân biệt được; idempotency đúng |
| T2.7 | LAN (chỉ khi mở LAN — P2/backlog) | [Sửa v1.3 — NỚI LỎNG local-only] v1: kiểm tra server **chỉ bind `127.0.0.1`** (cổng ngoài không với tới); LAN opt-in không bắt buộc key. Test LAN + key chỉ chạy khi anh mở LAN (§9.3) | Bind loopback đúng; khi mở LAN thì key bắt buộc bật lại theo §9.3 |
| T2.8 | Test tự động | `pytest tests/test_api.py` (mock engine) → 100% pass; `pytest tests/` (cần model) → pass trên máy có model | Test log đính kèm, 0 lỗi |
| T2.9 | Giới hạn text/batch + hàng đợi | [Sửa R1-Y6] Gửi text 20.001 ký tự → 400 + thông báo giới hạn; gửi batch 501 mục → 400; gửi 2 request TTS đồng thời → request 2 xếp hàng (202 + `job_id`), không 429; lấp hàng đợi 20 job → 429 | Đúng giới hạn §4; hành vi vượt giới hạn đúng như thiết kế |
| T2.10 | Nghe thử + MP3 | [Sửa R1-Y1/Y7] `GET /voices/{id}/preview` giọng V3 lần 2 → trả từ cache (không tổng hợp lại); giọng V4 lần 2 cùng câu mẫu → trả từ cache (không gọi lại API); `POST /api/tts/generate {"format":"mp3"}` → file MP3 thật (kiểm tra bằng `ffprobe`); khi FFmpeg bị gỡ → chỉ WAV + báo rõ | Preview cache đúng; MP3 thật; thiếu FFmpeg thì WAV vẫn chạy + báo rõ |

### Bước 3 — UI đủ tab

| ID | Tính năng | Kiểm chứng (bấm thật trong app đang chạy + bằng chứng) | Đạt khi |
|---|---|---|---|
| T3.1 | Phòng thu | Nhập text → chọn giọng → Tạo → nghe + tải WAV/MP3; chèn `[cười]` → nghe có cười; thẻ `[nghỉ 2s]` → đo khoảng lặng ≈ 2 s (±0,3 s) bằng ffprobe/sóng âm. [Sửa R1-Y2/Y3] `[nghỉ]` do `TextPreprocess` xử lý (không đưa nguyên tag vào `infer()`); file .srt kèm audio: đo sai số **từng mốc** (mỗi mốc ±0,3 s cho 10 câu đầu; ghi thêm sai số tối đa ở câu cuối cho bài dài), **đo độc lập bằng phát hiện khoảng lặng trên sóng âm thật (ffprobe `silencedetect` / envelope) hoặc nghe đối chiếu — [Sửa R2-Y3] không "đo bằng `SrtWriter`"** (đo vòng tròn), không chỉ đo tổng | Mọi nút bấm có kết quả thật; ảnh chụp UI đính kèm |
| T3.2 | Hội thoại/Podcast | Kịch bản 2 nhân vật × 3 lượt → 1 file; kiểm tra từng lượt đúng giọng (nghe); mở lại kịch bản → giọng không đổi. [Sửa R1-G8] "Giọng không đổi" đo được bằng cách đối chiếu `voice_id` trong file kịch bản đã lưu, không chỉ nghe bằng tai | Voice-lock giữ đúng; không trộn giọng |
| T3.3 | Lồng tiếng .srt | File .srt mẫu 5 câu (có 1 câu dài cố ý) → audio dài ≈ bằng video (±0,5 s); đo mốc từng câu (ffprobe + nghe); câu dài bị lùi → có SRT đã chỉnh mốc + danh sách câu bị lùi. [Sửa R1-G8] Đo sai số **từng mốc** (mỗi mốc ±0,3 s) — 5 câu lệch dồn vẫn có thể pass tổng ±0,5 s nên chỉ đo tổng là không đủ | Khớp mốc giờ từng câu, không cắt chữ |
| T3.4 | Đọc file | PDF 2 trang + DOCX + TXT mẫu + PDF scan mẫu + DOCX có bảng → text trích đúng, làm sạch đúng, chuyển sang Phòng thu tạo được giọng. [Sửa v1.3 — TH-23] PDF scan phải báo rõ 'v1 không OCR', không bịa text; bảng giữ đúng thứ tự cell | Text không mất chữ, không dính ký tự rác; PDF scan báo rõ 'v1 không OCR' (TK2.12) |
| T3.5 | Tạo hàng loạt | File 10 mục `[P1]`… → 10 file + ZIP; 1 mục lỗi (text rỗng) → 9 file xong + mục lỗi báo rõ + thử lại riêng được. [Sửa R1-TH-16] Đo **peak RAM** với batch 100 mục và 500 mục (ghi số đo, đối chiếu ngân sách RAM); đo thời gian/mục. [Sửa R2-TH-16 💭] Ngân sách RAM bằng số (mục tiêu đo, chốt theo số đo ở TK2.6): **peak RAM ≤ 2 GB** với batch 100 mục và 500 mục trên máy tối thiểu 8 GB RAM (audio ghi dần ra đĩa nên RAM phải gần như phẳng theo số mục — vượt 2 GB thì giảm `max_batch_items` cho tới khi đạt, không chốt 500 bằng cảm tính) | Đủ file, lỗi xử lý riêng; peak RAM ≤ 2 GB (100 và 500 mục); UI batch 100–500 mục không lag (virtual list + singleton player, TK3.7) |
| T3.6 | Bản đã tạo | Tạo 3 bản → danh sách hiện đủ 3; nghe lại/tải lại/xoá từng bản; tổng dung lượng hiển thị đúng (`du` đối chiếu) | CRUD thật trên file đĩa; tắt đột ngột/tràn đĩa không làm corrupt history (ghi atomic + checkpoint, TK2.10) |
| T3.7 | Cài đặt | Đổi giọng mặc định → khởi động lại app vẫn giữ; đổi thư mục lưu → file mới vào đúng thư mục; đổi precision → tạo lại đúng tốc độ/chất lượng. [Sửa R1-G8] "Đúng" đo được: đổi precision fp32→int8 thì RTF giảm (số đo) và file vẫn 48 kHz/mono; đổi thư mục thì file mới nằm đúng thư mục mới (`ls` đối chiếu) | Cài đặt bền vững qua khởi động lại |

### Bước 4 — Đóng gói + README

| ID | Tính năng | Kiểm chứng | Đạt khi |
|---|---|---|---|
| T4.1 | Đóng gói Windows | [Sửa R1-🔴 R2] **Không build `.exe` Windows trên máy Annie (Linux)** — PyInstaller không build chéo Windows từ Linux, Inno Setup cũng cần Windows. Build bằng **GitHub Actions Windows runner** (`windows-latest`, miễn phí cho repo public — hướng team đã dùng cho S1/MODOLIVIO, xem MEMORY.md): workflow `.github/workflows/build-windows.yml` chạy PyInstaller + Inno Setup trên runner Windows → artifact `.exe`/installer + SHA-256 hash → tải về cài trên **máy Windows thật của anh** (mục 11, C1) → mở app → T1.2 chạy được. Phương án dự phòng: build tại chỗ trên máy Windows của anh khi anh mở máy. Không dùng Wine làm phương án chính. [Sửa R2-TH-18] Trước khi đưa sang máy anh: **smoke test `.exe` trên runner sạch** (runner Windows mới, không có Python, không có repo — chạy `.exe` → T1.2 thu nhỏ pass); smoke test fail → build fail, không đưa artifact sang máy anh | `.exe` build từ runner Windows + hash; smoke test trên runner sạch pass; cài được trên máy anh; T1.2 pass trên máy anh (xem mục 11) |
| T4.2 | Đóng gói Linux | Build tương đương trên máy Annie → chạy → T1.2 + T2.1 pass | App chạy trên Linux không cần repo |
| T4.3 | README + LICENSE + NOTICE | README có: cài đặt, chạy, cấu hình, API, giấy phép, ghi công VieNeu-TTS; [Sửa R1-G7] LICENSE là **license Apache 2.0 của HP Voice Studio** (của HP, không copy nguyên file LICENSE của upstream làm LICENSE của mình) + NOTICE ghi công upstream + license giọng + license FFmpeg | Người mới đọc README làm theo chạy được (anh kiểm bằng mắt) |
| T4.4 | Release gate | Chạy `release_readiness_gate` + `pre_launch_security_checklist` (skill team) → 0 mục chặn; test tổng PASS 100% các mục chạy được | Có log gate đính kèm |
| T4.5 | Đường dẫn Unicode + đóng/mở lại | Cài app vào thư mục có dấu tiếng Việt + khoảng trắng (VD `C:\Người dùng\HP Voice Studio`) → T1.2 pass; đóng app → kiểm tra không còn tiến trình chiếm 8124 → mở lại → bind 8124 thành công; mở 2 instance → instance 2 báo rõ + không chạy chồng | T1.2 pass trên đường dẫn có dấu; không còn tiến trình ma; chống trùng instance |

---

### 10.5. Bảng tiêu chí nghiệm thu "mượt" thống nhất (v1.3 — G1 + GPT2 + G3 + G4 + G2 + v1.2)

> **Quy tắc đọc bảng này (theo G4):** tách rõ **số ĐÃ ĐO từ nguồn** (chỉ có
> số upstream README/CIT) và **ngưỡng mục tiêu CHƯA ĐO** (mọi ngưỡng của team
> đều là suy luận, cần đo thật ở Bước 1–2). Chỗ nào các bên khác nhau thì ghi
> **cả hai kèm nguồn** + đề xuất (mục tiêu chặt / mức tối thiểu chấp nhận được),
> không tự ý chọn một bên mà giấu bên kia. Mức P0/P1 theo §0.1.

| Chỉ tiêu | Số ĐÃ ĐO (nguồn) | Mục tiêu chặt | Mức tối thiểu chấp nhận được | Mức | Nguồn |
|---|---|---|---|---|---|
| RTF int8 (CPU 4 nhân, sau warmup, p95) | 0,37 (README, i5 12th-gen 6 nhân) | ≤0,45 (G3) / ≤0,55 (G1) / ≤0,60 (G2) | p95 ≤0,90 | P1 | G1/G3/G2/GPT2 |
| RTF fp32 (CPU 4 nhân, sau warmup, p95) | 0,62 (README, i5 12th-gen); ~0,50 (CIT, i7-8650U) | ≤0,85 (G3) | ≤1,00 (v1.2 T1.4; G2) | P1 | G1/G3/G2/v1.2 |
| Tiếng đầu TTFA (qua UI) | ~140 ms int8 / ~300 ms fp32 (README, CPU) | ≤500 ms (G2/G3 int8) / ≤600 ms (G1) | p95 ≤2 s | P1 | G1/G3/G2/GPT2/G4 |
| Phản hồi UI (click/chuyển tab, p95) | chưa đo | <100 ms | p95 ≤100 ms | P1 | GPT2/G3 |
| Chặn main thread / input lag bài 20.000 ký tự | chưa đo | ≤50 ms | ≤100 ms | P1 | GPT2/G4 |
| Đóng băng UI khi tạo | chưa đo | 0 ms | Không treo cứng (T1.8) | P0 | G2 |
| Nút Dừng phản hồi | chưa đo | ≤100 ms | ≤200 ms | P1 | G2/GPT2 |
| Hủy job (từ lúc bấm Hủy tới khi dừng hẳn) | chưa đo | ≤200 ms (GPT2) | ≤2 s (G2; ≤1,5 s G1/G3/G4) | P1 | GPT2/G1/G3/G4/G2 |
| Thanh tiến trình load hiện | chưa đo | ≤1,5 s | ≤1,5 s | P1 | G2 |
| Khởi động lạnh (cold start, model đã tải) | int8 load ~14 s (README) | int8 ≤15 s, fp32 ≤30 s (G2); UI ≤2 s (G3) | UI ≤3 s, app ≤30 s (T1.7) | P1 | G2/G3/G4/v1.2 |
| RAM idle | chưa đo | ≤1,2 GB | ≤1,2 GB | P1 | G1/G3 |
| RAM đỉnh bài dài (1 job) | chưa đo | ≤1,8 GB | ≤2,2 GB | P1 | G2 |
| RAM đỉnh batch 500 mục | chưa đo | ≤2,0 GB (v1.2 T3.5) | ≤2,5 GB (G2; ≤2,2 GB G3/G4) | P1 | v1.2/G3/G4/G2 |
| RAM đỉnh app+worker (máy 8 GB) | chưa đo | ≤2,2 GB | ≤4 GiB | P1 | GPT2 |
| Rò rỉ RAM batch 500 | chưa đo | ≤+100 MB | ≤+100 MB | P1 | G4 |
| Fallback V4→V3 (từ lúc lỗi tới khi bắt đầu tạo bằng V3) | chưa đo | ≤500 ms | ≤2 s | P1 | G1/G3 |
| Sai số mốc SRT dub (mốc gốc, p95) | chưa đo | p95 ≤100 ms | ±0,3 s | P0 | GPT2/G4/v1.2 |
| Sai số mốc SrtWriter (suy mốc, 10 câu đầu) | chưa đo | ±0,3 s | ±0,3 s | P0 | v1.2 |
| Đệm streaming đầu | chưa đo | ≥300 ms | ≥300 ms | P1 | GPT2 |
| RTF time-stretch | chưa đo | ≤1 | ≤1 | P1 | v1.2 |
| PreviewCache (cache hit) | chưa đo | ≤100 ms | ≤100 ms | P1 | G4 |
| Lỗi hiển thị tiếng Việt (nguyên nhân + cách khắc phục) | chưa đo | ≤200 ms | ≤200 ms | P1 | G2 |
| Hàng đợi | — | 1 job chạy, ≤3 chờ (GPT2) | 1 chạy, ≤20 chờ + TTL 60' | P1 | **ĐÃ CHỐT Q16 (04:32 19/11): 20 job chờ** |
| Batch lớn: 1 mục lỗi không chết batch; ghi dần ra đĩa + checkpoint/resume | chưa đo (v1.2 T3.5 đã có "lỗi riêng") | Có checkpoint/resume | Có "lỗi riêng", ghi dần ra đĩa | P0 | G3/GPT2/v1.2 |

### 10.6. Bảng tổng kết nghiệm thu theo tính năng — báo anh (v1.3)

> Bảng này là thứ Annie báo cho anh khi SPEC xong: 7 nhóm tính năng × tiêu chí
> kiểm chứng chạy thật × kiểm được trên máy Annie (Linux VM) hay còn chờ máy
> Windows của anh.

| Nhóm tính năng | Tiêu chí kiểm chứng chạy thật | Kiểm được trên máy Annie (Linux VM) | Chờ máy Windows của anh |
|---|---|---|---|
| Phòng thu | T1.2, T1.4, T1.8, T1.9, T2.2, T2.4, T2.10, T3.1 — WAV 48 kHz thật, đúng giọng, tốc độ 0,75–1,5×, MP3, SRT kèm, UI không treo, số/tiền/ngày đọc đúng | Có — WAV/API/UI local | C1 (`.exe`), C6 (RTF/VNNI CPU thật), C11 (Telex/micro), C19 (đóng/mở lại) |
| Hội thoại / Podcast | T3.2 — 2 nhân vật × 3 lượt, voice-lock giữ đúng, mở lại kịch bản không đổi giọng | Có — API + file kịch bản | C14 (hội thoại nhiều giọng, SRT dài) |
| Lồng tiếng .srt | T3.3 — 5 câu, mốc từng câu ±0,3 s, câu dài bị lùi có SRT chỉnh mốc + danh sách câu bị lùi; parser .vtt | Có — file mẫu | C14 (SRT dài ≥30 câu) |
| Đọc file | T3.4 — PDF/DOCX/TXT trích đúng; PDF scan báo rõ "v1 không OCR"; DOCX bảng giữ thứ tự | Có — file mẫu | C17 (PDF scan/DOCX bảng trên máy anh) |
| Tạo hàng loạt | T3.5 — 10/100/500 mục, ZIP, lỗi riêng, peak RAM ≤2 GB, virtual list + singleton player | Có — tới 500 mục trên VM | C3/C12/C15 (batch lớn + checkpoint/resume + tắt giữa chừng) |
| Bản đã tạo + Giọng của tôi (clone) | T3.6, T2.5 — CRUD thật, chặn khi vượt 5 GB, ghi atomic; clone 3–8 s có cam kết, nghe giống mẫu | Có — clone bằng file mẫu (giọng Annie/test) | C2 (clone giọng thật của anh), C15 (tắt giữa chừng không corrupt) |
| Cài đặt (+ API local) | T3.7, T2.1, T2.6, T2.7 — cài đặt bền vững, health/voices, V4 fallback + báo giọng mới, bind loopback | Có — trừ V4 key thật | C5/C13 (V4 key thật), C7 (LAN — chỉ khi mở LAN), C8 (cổng), C9 (SmartScreen/WebView2), C20 (MODOLIVIO gọi API HP), C21 (đường dẫn có dấu) |

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
| C6 | Đổi precision int8/fp32 trên CPU thật của anh | VNNI/méo tiếng phụ thuộc CPU thật; **ghi rõ model CPU máy anh** (không để "CPU 4 nhân" chung chung) + kết quả phát hiện VNNI theo phương pháp mới (TH-03: `avx512vnni` / AVX-VNNI leaf 7.1) |
| C7 | LAN API từ máy khác trong mạng nhà anh — **chỉ khi mở LAN (§9.3, P2)** | Mạng/tường lửa thật; v1 local-only không chặn |
| C8 | Kiểm tra trùng cổng trên máy anh (8123 MODOLIVIO, 8001 CIT, 8000/7860 upstream, 8124 HP) trước khi chốt cổng HP | [Sửa R1-G11/R1] Cổng đang chiếm chỉ có trên máy anh — hệ quả trực tiếp của 🔴 R1; chạy `scripts/check_port.py` trên máy anh |
| C9 | Cài `.exe` chưa ký: SmartScreen + WebView2 có sẵn không | Chỉ có trên máy Windows thật của anh |
| C10 | Tốc độ tải model từ Hugging Face trên mạng nhà anh (HF có bị chặn/chậm không) | Mạng nhà anh; quyết định TH-02/TH-15 (đóng gói sẵn model hay tải lần đầu) |
| C11 | Gõ Telex trong UI web local + thu micro trên Windows (quyền micro) | Lỗi Telex từng xảy ra ở MODOLIVIO; micro + quyền chỉ có trên máy anh |
| C12 | Đo peak RAM batch 100/500 mục + dung lượng ổ đĩa sau batch lớn | RAM/ổ đĩa thật của máy anh (TH-16) |
| C13 | Kiểm tra key V4 hợp lệ bằng endpoint rẻ nhất (không đốt ký tự) | Key + quota thật của anh; [Sửa R2-Y12/Q14 — ĐÃ TRẢ LỜI] dùng **`GET /v1/balance`** (vừa ping key vừa lấy số dư cho màn hình quota — endpoint TỒN TẠI theo OpenAPI, bỏ ứng viên cũ `GET /v1/audio/voices`); kiểm chứng ở C13 rằng `GET /v1/balance` không trừ token khi gọi |
| C14 | SRT dài (≥30 câu) + hội thoại nhiều giọng trên máy anh | Mốc giờ + voice-lock chỉ tin được trên CPU/âm thanh thật (GPT2/G1) |
| C15 | Batch lớn (≥100 mục) tắt app giữa chừng rồi mở lại: checkpoint/resume + history không corrupt + file tạm được dọn | Trạng thái dở dang + ổ đĩa thật (GPT2/G3/G2) |
| C16 | Kiểm tra LAN hardening từ máy khác (Host/Origin/CSRF) — chỉ khi mở LAN | Mạng thật; v1 local-only không chặn (G3 TH-22) |
| C17 | Đọc PDF scan + DOCX có bảng trên máy anh | File thật + mắt anh (G3 TH-23) |
| C18 | Nghe đối chiếu time-stretch librosa vs FFmpeg atempo ở 0,75×/1,5× trên máy anh | Tai anh + CPU thật (G3/G4 TH-20) |
| C19 | Đóng app rồi mở lại nhiều lần: không còn tiến trình ma chiếm cổng 8124; mở 2 instance thì instance sau báo rõ | Vòng đời tiến trình chỉ có trên máy Windows thật (G4/G2 TH-19) |
| C20 | MODOLIVIO gọi API HP thật qua `127.0.0.1:8124` (tạo WAV từ link sản phẩm) | Tích hợp thật cuối cùng (G2) |
| C21 | Cài + chạy app trong thư mục có dấu tiếng Việt/khoảng trắng trên máy anh | Đường dẫn thật của máy anh (G2 TH-21) |

---

## 12. TO-TICKETS — DANH SÁCH VIỆC BƯỚC 1–4 (full phạm vi)

> Mỗi ticket: đầu vào, đầu ra, tiêu chí đạt (tham chiếu mục 10), ước lượng tương đối
> (S/M/L — **SUY LUẬN**, chốt lại khi giao việc). Thứ tự làm theo số ticket.
> [Sửa R1-R3] Ticket ở mục này dùng namespace `TK…` (VD `TK2.5` = ticket SrtDubber);
> tiêu chí đạt tham chiếu sang namespace test `T…` ở mục 10 (VD `T2.5` = test clone
> giọng). `TKx.y` và `Tx.y` là hai thứ khác nhau — không viết tắt lẫn.

### Bước 1 — Engine V3 + WAV thật

| Ticket | Việc | Tiêu chí đạt | Ưu tiên |
|---|---|---|
| TK1.1 | Dựng repo HP: `.gitignore`, `requirements.txt` (`vieneu==3.8.4` ghim), `config.example.yaml`, cấu trúc `src/hpvoice/` — [Sửa R2] `requirements.txt` liệt kê đủ + ghim version: `vieneu==3.8.4`, `imageio-ffmpeg==0.8.1`, `keyring==25.7.0`, `py-cpuinfo==9.0.0`, `PyMuPDF==1.28.2` (bản 1.x mới nhất 19/11/2026, thỏa floor `>=1.25.0` của extra `[pdf]` upstream; tránh dòng 2.x chưa kiểm chứng — kiểm chứng tương thích ở ticket này), `python-docx==1.2.0`, fastapi + uvicorn (ghim theo bản cài ở ticket này, ghi số vào `requirements.txt`); `pywin32-ctypes` (Windows) / `SecretStorage` + `jeepney` (Linux) là dependency theo platform của `keyring`, ghi rõ trong `requirements.txt` bằng environment marker | Cài mới từ README chạy được tới bước import | P0 |
| TK1.2 | `V3Engine`: adapter gọi SDK (init, infer, stream, batch, list voices, precision auto theo CPU) | T1.2, T1.3, T1.5 pass | P0 |
| TK1.3 | Tải model lần đầu: `scripts/download_model.py` + đo dung lượng/thời gian thật **theo từng thành phần** (backbone, codec, speaker-encoder/denoiser, tokenizer) + kiểm chứng **chặn mạng hoàn toàn sau khi tải, khởi động lại, tạo WAV** (Y10), ghi vào README; [Sửa v1.3 — GPT2] tải dở tiếp tục được (resume), cache hỏng phát hiện bằng checksum và chỉ tải lại file hỏng | T1.1 pass; có số dung lượng thật theo từng thành phần; offline hoàn toàn được xác nhận hoặc ghi rõ thành phần còn thiếu | P0 |
| TK1.4 | Đo hiệu năng CPU (fp32/int8, RTF) + phát hiện VNNI theo phương pháp mới (TH-03: cờ `avx512vnni` của `py-cpuinfo` 9.0.0 + CPUID leaf 7 subleaf 1 EAX bit 4 cho AVX-VNNI; mặc định fp32 khi không đọc được cờ; dự phòng thực nghiệm chạy thử int8 đối chiếu fp32) + quyết precision mặc định theo CPU + nhánh dự phòng khi fp32 RTF > 1 (≤ 1,5 chấp nhận chậm; > 1,5 mặc định Nano; cả Nano > 1 thì báo máy không đủ) + ghi model CPU tham chiếu vào SPEC (ADR) | T1.4, T1.7 pass; quyết định ghi vào SPEC (ADR) | P0 |
| TK1.5 | `VoiceStore`: preset (đọc từ SDK) + clone (`add_voice`, file riêng HP) + cam kết + cơ chế gỡ giọng khi khiếu nại (TH-17) | T2.5 (phần engine) pass | P0 |
| TK1.6 | `AudioPost` (time-stretch `librosa.effects.time_stretch`, nối chunk, xuất WAV/MP3 qua **FFmpeg tải sau (Q21 — ĐÃ CHỐT)** — ADR-07) + `TextPreprocess` (thẻ `[nghỉ]`/cảm xúc — Y2: ngữ pháp chốt + quy tắc tag giữa từ/nhiều tag/tag + cảm xúc + đường V4 tách đoạn, test nhánh lỗi) + `SrtWriter` (suy mốc giờ — Y3: hằng số `gaps_to_silence` 0,30/0,50/0,70 s + quy tắc bù zeros theo im lặng mép đã đo + chia mốc theo tỉ lệ ký tự trong chunk nhiều câu) | T2.4, T2.10, T3.1 pass | P0 |
| TK1.7 | `PronDict`: CRUD + CSV import/export + áp trước infer | Test đơn vị pass; dùng trong T3.1 | P1 |
| TK1.8 | `V3Engine` chạy worker thread riêng (TH-19): inference qua `run_in_executor`/thread pool 1 worker, không chạy trên event loop FastAPI / luồng UI; job có cờ hủy kiểm tra giữa các chunk | T1.8 pass | P0 |
| TK1.9 | `AudioPost`: đo RTF + nghe đối chiếu `librosa.effects.time_stretch` vs FFmpeg `atempo` ở 0,75×/1,5× (TH-20); chốt engine mặc định (atempo nếu đủ tốt thì bỏ librosa làm mặc định); pin `numba`/`llvmlite` nếu giữ librosa | T2.4 pass | P1 |
| TK1.10 | `ViTextNormalizer` (TH-27): chuẩn hoá số/tiền/ngày/giờ/đơn vị tiếng Việt thành chữ đọc được, chạy trước `TextPreprocess`; công tắc bật/tắt trong Cài đặt | T1.9 pass | P0 |

### Bước 2 — API local + V4

| Ticket | Việc | Tiêu chí đạt | Ưu tiên |
|---|---|---|
| TK2.1 | `HpApiServer` FastAPI + `docs/api-contract.md` (mục 4 — ghi cả hai dạng trả của endpoint 4: 200 audio / 202 + `job_id`; endpoint 5 chuyển async khi text > 5.000 ký tự; TTL hàng đợi 60 phút) + `scripts/check_port.py` (cổng 8124, fail-fast khi bận — R1) + giới hạn text/batch/hàng đợi (Y6) + endpoint 5 trả **ZIP duy nhất** (Y11) | T2.1, T2.2, T2.9 pass | P0 |
| TK2.2 | `EngineRouter` + `V4Engine` (Cloud API v4, key từ store qua `keyring`/DPAPI, fallback V3 + báo lý do **+ giọng mới** theo bảng ánh xạ `docs/voice-fallback-map.md` — N-FB; xử lý riêng 401/**403**/429; `Idempotency-Key` = UUID theo HP job id cho mọi `POST /v1/tts`, 409 retry cùng key, 422 báo lỗi; không retry `POST /v1/audio/speech` sau timeout; ước tính phí theo công thức ký tự × multiplier, dùng `GET /v1/balance` + `GET /v1/engines` cho màn hình số dư; [Sửa v1.3] idempotency của `/v1/dialogue`, `/v1/dub`, `/v1/srt` chưa xác nhận — đọc OpenAPI trước khi dùng, không retry sau timeout nếu chưa xác nhận) | T2.6 pass (khi có key test do người dùng cung cấp) | P0 |
| TK2.3 | `JobQueue` + `HistoryStore` (chặn tạo mới khi vượt `max_history_gb` — TH-16) + endpoint history/jobs; [Sửa v1.3 — TH-30] trần + dọn preview cache/file tạm | T2.8, T3.6 (phần API) pass | P0 |
| TK2.4 | `ConversationEngine` (khoá speaker→voice, batch, ghép) | T3.2 (phần API) pass | P0 |
| TK2.5 | `SrtDubber` (parse, căn giờ, SRT đã chỉnh mốc) + đo giới hạn SRT dub ở Bước 3 (G4 — không lấy số 100.000 của Tạo hàng loạt); [Sửa v1.3] xem thêm TK2.13 (.vtt + `[nghỉ]`/0,75×) | T3.3 (phần API) pass | P0 |
| TK2.6 | `BatchRunner` (txt/json/srt, ZIP, thử lại mục lỗi; ghi từng mục ra đĩa ngay; đo peak RAM 100/500 mục — TH-16; chốt giới hạn batch theo số đo; [Sửa v1.3 — TH-33] dọn file tạm khi hủy/crash (quét lúc khởi động)) | T3.5 (phần API) pass | P0 |
| TK2.7 | `FileReaders` (PDF/DOCX/TXT + làm sạch; ghi chú bản quyền văn bản đầu vào) | T3.4 (phần API) pass | P1 |
| TK2.8 | Auth LAN (`X-API-Key`, opt-in) + test bảo mật cơ bản — **[Sửa v1.3: P2/backlog, chỉ làm khi mở LAN (§9.3); v1 local-only không chặn]** | T2.7 pass (phần bind loopback); phần key LAN chỉ khi mở LAN | P2 |
| TK2.9 | Test API (mock engine) + test tương thích OpenAI SDK + test giới hạn text/batch/hàng đợi + test preview cache/MP3 | T2.8, T2.9, T2.10 pass, 100% | P0 |
| TK2.10 | `HistoryStore` bền vững (TH-21/TH-33): ghi atomic (file tạm + rename), checkpoint sau mỗi mục batch, kiểm tra dung lượng trống trước batch lớn, file history hỏng thì đọc bản backup + báo rõ; dọn file tạm khi hủy/crash (quét lúc khởi động) | T3.6 pass | P1 |
| TK2.11 | LAN hardening (TH-22) — **P2/backlog, chỉ khi mở LAN (§9.3)**: Host allowlist, Origin check, anti-CSRF token; không làm ở v1 | T2.7 (phần LAN) pass khi mở LAN | P2 |
| TK2.12 | `FileReaders` chống treo/chữ rác (TH-23): phát hiện PDF scan → báo rõ 'v1 không OCR', giữ thứ tự cell của bảng, giới hạn kích thước/timeout đọc theo trang | T3.4 pass | P1 |
| TK2.13 | `SrtDubber`: parser **.vtt** (chuyển về dạng SRT nội bộ) + quy tắc `[nghỉ]`/0,75× (§3.3) + fallback V4→V3 cho `/v1/dialogue`, `/v1/dub`, `/v1/srt` (cùng bảng ánh xạ + `voice_strict`; idempotency 3 endpoint này đọc OpenAPI trước khi dùng) | T3.3 pass | P0 |
| TK2.14 | `JobQueue` 2 mức ưu tiên + cờ `save_to_history` (TH-29) — **P2/backlog, chỉ khi nhiều client (§9.3)**; v1 giữ hàng đợi đơn giản (1 chạy, ≤20 chờ, TTL 60') | T2.9 pass | P2 |

### Bước 3 — UI đủ tab

| Ticket | Việc | Tiêu chí đạt | Ưu tiên |
|---|---|---|
| TK3.1 | Khung UI + điều hướng nhóm Tạo/Thư viện/Hệ thống + tab Phòng thu + `PreviewCache` (nghe thử V3/V4 — Y7) | T3.1 pass | P0 |
| TK3.2 | Tab Hội thoại/Podcast + Giọng của tôi (clone + cam kết) | T3.2 pass | P0 |
| TK3.3 | Tab Lồng tiếng .srt + Đọc file | T3.3, T3.4 pass | P0 |
| TK3.4 | Tab Tạo hàng loạt + Bản đã tạo | T3.5, T3.6 pass | P0 |
| TK3.5 | Tab Cài đặt (giọng/model/thư mục/V4 key/API LAN) | T3.7 pass | P0 |
| TK3.6 | Polish UI: thông báo lỗi rõ lý do, trạng thái engine, ước tính phí V4 | Review bằng mắt (anh) + evidence QA | P1 |
| TK3.7 | UI batch chống tràn RAM (TH-28): virtual list cho danh sách batch + singleton audio player (1 player dùng chung) | T3.5 pass | P1 |

### Bước 4 — Đóng gói + phát hành

| Ticket | Việc | Tiêu chí đạt | Ưu tiên |
|---|---|---|
| TK4.1 | Đóng gói Windows (.exe/installer, kèm model hoặc tải lần đầu) — **build trên GitHub Actions Windows runner** (`windows-latest`, workflow `.github/workflows/build-windows.yml`), không build trên máy Annie (Linux); artifact + SHA-256; cài thử trên máy anh (C1). [Sửa R2-R2-detail/TH-18 — chi tiết thực thi còn thiếu ở v1.1] (a) **Repo:** tạo repo GitHub riêng cho HP Voice Studio (tên + public/private chốt ở Bước 4 trước khi viết workflow — "miễn phí cho repo public" chỉ đúng với repo public; repo private thì Windows runner tốn phút gấp 2, phải tính lại chi phí); ticket này chưa xong nếu chưa có repo. (b) **Trigger:** `push` tag `v*` + `workflow_dispatch` (chạy tay); không trigger trên mọi push (tránh tốn phút runner). (c) **Pin:** Python **3.12** (khớp `.python-version` của upstream), `pip` cache bật, `vieneu==3.8.4` + toàn bộ `requirements.txt` (TK1.1). (d) **Danh sách collect PyInstaller** (TH-18 — thiếu là `.exe` chết lúc chạy): `--collect-all keyring` (entry points backend + `pywin32-ctypes`), `--collect-all onnxruntime`, `--collect-all tokenizers`, **[Sửa Q21 — ĐÃ CHỐT 04:35 19/11] KHÔNG collect binary FFmpeg** (FFmpeg tải cài sau, không đóng gói kèm — TK4.9), model theo Q2 (kèm sẵn thì `--add-data` model + checksum, tải lần đầu thì màn hình tải + checksum ở lần chạy đầu). (e) **Tải artifact + kiểm SHA-256:** workflow đăng artifact + file `.sha256`; người tải (Annie hoặc anh) kiểm `sha256sum` khớp rồi mới cài — ghi rõ ai tải, kiểm ở đâu (log workflow). (f) **Smoke test trên runner sạch:** job riêng chạy `.exe` trên runner Windows mới (không Python, không repo) → T1.2 thu nhỏ pass mới cho artifact qua; fail → build fail. (g) "Kèm model hoặc tải lần đầu" chỉ thực thi được sau khi Q2 chốt — nếu Q2 chưa chốt lúc build thì mặc định **tải lần đầu** + màn hình tải (không giả định kèm model) | T4.1 pass; C1 chờ kiểm chứng thật | P0 |
| TK4.2 | Đóng gói Linux (chạy trên máy Annie) | T4.2 pass | P0 |
| TK4.3 | README + LICENSE (của HP — G7) + NOTICE (ghi công upstream + license giọng + license FFmpeg) + `docs/decisions/` (ADR) | T4.3 pass | P0 |
| TK4.4 | Release gate (skill team) + test tổng 100% + danh sách "chờ kiểm chứng thật" | T4.4 pass | P0 |
| TK4.5 | Quy trình nâng SDK (test tương thích + ghim version + theo dõi release upstream; mirror model + checksum — TH-15) | Có checklist nâng cấp trong README | P1 |
| TK4.6 | Hợp đồng triển khai (TH-24): viết `docs/deployment-contract.md` — bản đầy đủ của §16 (OS, Python, model revision, đĩa/RAM, cổng, runtime Windows, vỏ desktop) | T4.4 pass | P1 |
| TK4.7 | Máy sạch + Unicode path (TH-25/TH-32): kiểm tra WebView2 + VC++ Redistributable + ONNX DLLs; test đường dẫn có dấu tiếng Việt/khoảng trắng (model/cache/output); ghi hướng dẫn khắc phục vào README | T4.1, T4.5 pass | P0 |
| TK4.8 | Desktop Shell (TH-26, G4/G2): vỏ desktop pywebview/WebView2 (Q20), ẩn console (`--noconsole`/pythonw — không để `.exe` chỉ hiện console đen), sở hữu vòng đời server (đóng cửa sổ → dừng server + giải phóng 8124), chống mở trùng instance (mutex/lock file), graceful shutdown | T4.1, T4.5 pass | P0 |
| TK4.9 | FFmpeg license + tải cài sau (TH-31, G2) — **[ĐÃ CHỐT Q21 04:35 19/11: phương án (b) tách khỏi bộ cài, tải cài sau]**: (a) KHÔNG đóng gói binary FFmpeg vào bộ cài/`exe` (bộ cài giữ 100% Apache 2.0; PyInstaller KHÔNG collect `imageio_ffmpeg/binaries/*`); (b) module `FFmpegManager` (`src/hpvoice/audio/ffmpeg_manager.py`): lần đầu cần MP3/giải mã MP3/M4A thì tải binary FFmpeg về thư mục dữ liệu app (nguồn tải tin cậy, kiểm SHA-256, báo tiến trình rõ, thử lại được khi lỗi mạng); (c) fallback FFmpeg hệ thống nếu có; không có FFmpeg → chỉ xuất WAV + báo rõ cách tải, không crash; (d) NOTICE ghi LGPL v3 cho binary tải sau chính (BtbN) + GPL v3 + source offer chỉ cho binary imageio-ffmpeg dự phòng (§13.7); ghi quyết định vào ADR-07 + §13.7 | T4.3 pass; MP3 thật sau khi tải FFmpeg; không FFmpeg → WAV + báo rõ | P1 |

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
   nhân là an toàn; thương mại phải xin xác nhận trước (mục 9, §13.8).
3. **V4 + kho giọng V4:** độc quyền, chỉ qua API trả phí; không clone offline.
4. **Không dùng:** bản GGUF Q4 (CC BY-NC), không fork/copy code CIT (CIT là Apache
   2.0 nhưng lệnh anh là không copy — chỉ tham khảo tính năng/cấu trúc).
5. **Không lấy:** logo/thương hiệu VieNeu hay CIT; HP Voice Studio dùng thương
   hiệu riêng.
6. **Giọng clone:** chỉ giọng có phép + cam kết; nội dung mô phỏng giọng người thật
   khi đăng công khai phải ghi rõ "giọng đọc được tạo bằng AI". Giọng nói là dữ
   liệu cá nhân (NĐ 13/2023); nội dung AI phải ghi nhãn (NĐ 147/2024) — xem TH-17.
7. **FFmpeg:** [Sửa R1-Y1] FFmpeg **TẢI CÀI SAU, không đóng gói kèm app (Q21 —
   ĐÃ CHỐT 04:35 19/11)** — ghi license FFmpeg vào NOTICE
   ở TK4.3. [Đính chính 19/11/2026 — đợt nối tiếp Q21] Có HAI binary khác
   nhau, không được lẫn:
   (a) Binary **tải sau chính: BtbN LGPL v3** — `FFmpegManager.download()`
   tải archive tĩnh đã ghim (release `autobuild-2026-11-18-12-39`, kiểm
   SHA-256 + chạy thử + kiểm `-buildconf` không có `--enable-gpl` /
   `--enable-nonfree`) về thư mục dữ liệu lần đầu cần MP3/giải mã; NOTICE
   ghi **LGPL v3** cho binary này, không cần source offer GPL.
   (b) Binary **imageio-ffmpeg 0.8.1 dự phòng (chỉ máy dev đã pip
   install)** là **GPL v3** (đo thật: `ffmpeg -buildconf` cho
   `--enable-gpl --enable-version3 --enable-libx264 --enable-libx265`;
   wrapper `imageio-ffmpeg` là BSD-2-Clause nhưng **binary** là GPL v3).
   Binary này **đi kèm wheel lúc pip install** — `get_ffmpeg_exe()` chỉ
   tìm file đã có, **KHÔNG tải binary rời lúc chạy** (câu cũ "tải lần
   đầu" thực chất là pip tải wheel nén ~68 MB lúc cài requirements).
   Binary này không có trong bộ cài .exe. NOTICE ghi **GPL v3 + source
   offer** (đường dẫn lấy source FFmpeg + build script, theo GPL v3 §6)
   CHỈ cho binary dự phòng này; toàn bộ bộ cài phân phối kèm binary GPL
   sẽ chịu nghĩa vụ GPL (không được ghi "LGPL" vào NOTICE cho binary này).
   **[Sửa Q21]** Vì bộ cài **không chứa binary FFmpeg** (tải cài sau lần đầu chạy),
   bộ cài giữ 100% Apache 2.0 và không còn bẫy onefile (TH-31).
   **Kịch bản B (đổi sang bản LGPL) — ĐÃ LÀM XONG 19/11/2026 (commit
   7f9dd6b):** bản lgpl của BtbN là nguồn tải chính từ nay (xem (a)); bản
   imageio GPL chỉ còn làm dự phòng cho máy dev. Không còn "mặc định giữ
   GPL v3 + source offer" cho đường tải chính.

8. **Bảng quyền từng tài sản (v1.3, theo GPT2 + kiểm chứng model card 19/11/2026):**

| Tài sản | Giấy phép | Căn cứ | Ghi chú |
|---|---|---|---|
| Code HP Voice Studio (mới) | Apache 2.0 (của HP) | Lựa chọn riêng của HP (§13.1) | Không copy nguyên LICENSE upstream |
| Code SDK `vieneu` 3.8.4 | Apache 2.0 | `LICENSE` repo upstream | Dùng qua pip, ghim version |
| Model v3 Turbo (`model.safetensors`, ONNX, config, tokenizer) | Apache 2.0 | Model card HF: "license applies to **all** artifacts shipped here" | Card đọc được ghi cho SDK 3.7.1 — xem TH-01 |
| 25 giọng preset v3 Turbo (`voices_v3_turbo.json`) | Apache 2.0 (theo model card) | Model card FAQ: preset-voice assets + audio thương mại được phép | File JSON không ghi license; xác nhận bằng văn bản cho đúng 25 giọng 3.8.4 trước thương mại (§9.2) |
| File `voices.json` cũ | CC BY-NC 4.0 | Meta trong file (đã đọc) | Không phân phối lại; không dùng làm căn cứ cho 25 giọng Turbo |
| Bản GGUF Q4 (v2) | CC BY-NC 4.0 | Nghiên cứu 18/11 | Không dùng |
| FFmpeg binary tải sau chính (BtbN LGPL, release autobuild-2026-11-18-12-39) | LGPL v3 | LICENSE.txt trong archive + `-buildconf` không `--enable-gpl` (đo thật 19/11/2026) | Nguồn tải chính của `FFmpegManager.download()`; NOTICE mục 3 (§13.7); không đóng gói kèm |
| FFmpeg binary dự phòng (`imageio-ffmpeg` 0.8.1, chỉ máy dev) | GPL v3 | `ffmpeg -buildconf` đo thật | Đi kèm wheel lúc pip install (`get_ffmpeg_exe()` không tải lúc chạy); không đóng gói kèm (Q21 — ĐÃ CHỐT); NOTICE + source offer (§13.7); bẫy onefile không còn |
| Giọng clone (của người dùng) | Quyền của chủ giọng | Cam kết TH-04/TH-17 | Chỉ giọng có phép; không đồng bộ cloud |
| V4 + kho giọng V4 | Độc quyền, qua API trả phí | Connector `custom.vieneu` | Không clone offline; điều khoản bán lại đọc trước mốc thương mại |
| Codec MOSS-Audio-Tokenizer-Nano / sea-g2p | Apache 2.0 (theo model card §Third-party) | Model card | Giữ notice khi phân phối lại |

## 14. ADR (quyết định kiến trúc rút gọn)

| ADR | Quyết định | Phương án đã cân nhắc | Cách nó hỏng / điều kiện xét lại |
|---|---|---|---|
| ADR-01 | Stack: Python + FastAPI + web UI local | B. Electron+sidecar; C. Gradio demo có sẵn; **D. Fork CIT Voice Studio** (đã cân nhắc, loại vì lệnh anh 03:31 không fork/copy code CIT + cần kiến trúc riêng cho MODOLIVIO — xem §3.2) | Đóng gói Windows (GitHub Actions runner, TK4.1) thất bại 2 lần → xét B |
| ADR-02 | Engine chính v3 Turbo, ghim `vieneu==3.8.4` | Nano (yếu hơn, 24 kHz); backend v2/v1 GPU (cũ) | SDK ra bản sửa lỗi nghiêm trọng → nâng theo checklist TK4.5 |
| ADR-03 | Mọi gọi SDK qua `V3Engine`; mọi engine cùng interface | Gọi SDK trực tiếp từ API/UI | Đổi SDK/engine → chỉ sửa adapter |
| ADR-04 | V3 mặc định, V4 opt-in + fallback V3 (fallback đổi giọng theo bảng ánh xạ — xem ADR-10) | V4 mặc định (tốn phí, phụ thuộc cloud) | Người dùng chọn V4 làm mặc định trong Cài đặt (quyền của họ) |
| ADR-05 | API mặc định loopback **chỉ** (v1.3 — local-only); LAN opt-in, **không bắt buộc key ở v1** | Mở LAN mặc định (rủi ro TH-06) | Anh nói "mở LAN" → bật lại key bắt buộc + giới hạn endpoint + chống CSRF (§9.3) |
| ADR-06 | Tốc độ làm ở tầng `AudioPost` bằng `librosa.effects.time_stretch`, không trong engine; `soxr` chỉ resample, không đổi tốc độ (Y4) | Chờ SDK thêm tham số speed | SDK thêm `speed` chính thức → chuyển sang dùng SDK, giữ interface |
| ADR-07 | MP3 mã hoá/giải mã bằng **FFmpeg TẢI CÀI SAU lần đầu chạy (Q21 — ĐÃ CHỐT 04:35 19/11)**: bộ cài **không đóng gói kèm** binary FFmpeg (giữ 100% Apache 2.0); module `FFmpegManager` tải binary về thư mục dữ liệu khi cần (cần mạng lần đầu, kiểm SHA-256, báo tiến trình); fallback FFmpeg hệ thống nếu có; không có FFmpeg → chỉ WAV + báo rõ. [Sửa R2-Y1] Binary Linux 0.8.1 đo thật **~165 MB** (172.692.552 byte; Windows đo ở TK4.1) — bỏ con số "~25–30 MB" của v1.1; [Đính chính 19/11/2026] binary **tải sau chính là LGPL v3 (BtbN)** (xem §13.7) — NOTICE ghi LGPL cho binary tải sau; GPL v3 + source offer chỉ cho binary imageio-ffmpeg 0.8.1 dự phòng trên máy dev. | `lameenc` (chỉ mã hoá, không giải mã MP3/M4A đầu vào); bỏ MP3 khỏi v1 (mất tính năng CIT đã có); đóng gói FFmpeg kèm (bị loại bởi Q21) | Tải FFmpeg lần đầu thất bại (không mạng) → app vẫn chạy WAV-only + báo rõ cách tải lại (TK4.9) |
| ADR-08 | Cổng API mặc định **`8124`**; khởi động bind thất bại → fail-fast + báo rõ, không tự nhảy cổng (R1) | Giữ 8123 (trùng MODOLIVIO — loại); tự nhảy cổng khi bận (khó lường, client gọi sai đích — loại) | C8 phát hiện 8124 cũng bị chiếm trên máy anh → đổi số khác trong bảng §4, cập nhật mọi tham chiếu |
| ADR-09 | Key V4/key LAN lưu qua **`keyring`** (Windows: DPAPI/Credential Manager; Linux: Secret Service, fallback `secrets.json` 0600) — không lưu plaintext trên Windows (Y12). [Sửa R2-Y12] PyInstaller phải `--collect-all keyring` (entry points backend) hoặc khởi tạo backend trực tiếp (`WinVaultKeyring`); backend Windows cần `pywin32-ctypes` trong bản đóng gói. Ping key dùng **`GET /v1/balance`** (vừa kiểm tra key vừa lấy số dư — xem Q14) | File `secrets.json` + `chmod 0700` (không có nghĩa trên Windows — loại) | `keyring` không chạy được trên máy anh → fallback file + ACL Windows, ghi rõ trong README |
| ADR-10 | Fallback V4→V3 đổi giọng qua **bảng ánh xạ** `docs/voice-fallback-map.md` (N-FB, §3.3): map từng giọng V4 sang preset V3 gần nhất (giới tính, vùng, phong cách), không có thì về "Hải Đăng"; fallback phải báo rõ cả lý do lẫn giọng mới; job khóa giọng (`voice_strict: true`) thì không fallback mà trả lỗi | Fallback không đổi giọng (giữ nguyên voice_id V4 → V3 báo 400, fallback hỏng); fallback lặng lẽ đổi giọng (người dùng nghe giọng khác mà không biết lý do — loại) | Catalogue V4 đổi (giọng mới/xóa giọng) → cập nhật bảng ánh xạ ở Bước 2, job cũ map về "Hải Đăng" nếu giọng đã mất |
| ADR-11 | Desktop Shell: vỏ pywebview/WebView2 (Q20) mở UI local, ẩn console, sở hữu vòng đời server (đóng cửa sổ → dừng server + giải phóng cổng), chống trùng instance | Chỉ chạy uvicorn + mở trình duyệt tay (không có cửa sổ app, không tắt server khi đóng tab) | pywebview không chạy được trên máy anh → xét WebView2 trực tiếp / trình duyệt + script tắt server |
| ADR-12 | Local-only: biện pháp mạng duy nhất là bind `127.0.0.1` mặc định; các biện pháp chặt (L1–L4 §9.3) hạ xuống P2/backlog | Áp mức chặt ngay từ v1 (làm chậm build, không cần cho máy cá nhân) | Anh nói "mở LAN" → bật lại L1–L4 theo §9.3 |
| ADR-13 | Thước đo cuối cùng: full tính năng dùng được (§0.1); ưu tiên P0/P1/P2; nghiệm thu mỗi giai đoạn bằng tính năng chạy thật, không bằng checklist giấy | Nghiệm thu bằng checklist giấy / đếm tiêu chí mượt | Anh đổi thước đo → cập nhật §0.1 + §10.5/§10.6 |

---

## 15. ĐIỂM CẦN QUYẾT / CÂU HỎI MỞ (đưa anh chốt cùng SPEC)

1. **Cổng API mặc định:** [Sửa R1-R1 — ĐÃ TRẢ LỜI, không còn là câu hỏi mở]
   Mặc định mới là **`8124`** (8123 đã có chủ: server TTS MODOLIVIO, nghiên cứu
   nền §5.2). Còn lại một việc kiểm chứng, không phải một quyết định: anh/Annie
   chạy `scripts/check_port.py` trên máy anh (C8) để xác nhận không có dịch vụ
   nào khác đang chiếm 8124.
2. **Model trong bộ cài hay tải lần đầu:** bộ cài ~300–400 MB kèm model sẵn
   (dùng ngay, nặng) hay bộ cài nhẹ + tải model lần đầu (nhẹ, cần mạng)? CIT chọn
   kèm sẵn; VieNeu Desktop ~90 MB (tải thêm sau). [Sửa R2-Y1] Ngân sách
   ~300–400 MB **không còn cộng thêm ~165 MB binary FFmpeg** [Sửa Q21 — ĐÃ CHỐT
   04:35 19/11: FFmpeg tải cài sau, không trong bộ cài] — kèm model thì bộ cài
   vẫn ~300–400 MB (số đo Windows đo ở TK4.1).
   Anh chọn hướng nào? (Quyết sau khi có số đo tốc độ HF ở C10 — xem TH-15.)
3. **Ngưỡng cảnh báo phí V4:** mặc định 100.000 ký tự/phiên trong SPEC — anh muốn
   số khác không? (Và có muốn chặn hẳn khi vượt ngưỡng không, hay chỉ cảnh báo?)
   [Sửa R2-V4] Lưu ý: phí thật = ký tự (tối thiểu 50/request) × engine multiplier
   × globalMultiplier (VD v4 = 3,4) nên "100.000 ký tự" ≠ "100.000 token" —
   ngưỡng trong config là ký tự, không phải token.
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
   Chốt ban đầu: **đóng gói FFmpeg kèm app** (ADR-07). **[Sửa Q21 — ĐÃ CHỐT 04:35
   19/11: quyết định này BỊ THAY THẾ — FFmpeg TÁCH KHỎI BỘ CÀI, tải cài sau lần
   đầu chạy; bộ cài không đóng gói kèm binary FFmpeg. Không có FFmpeg → chỉ xuất
   WAV + báo rõ.]** Căn cứ: server upstream chỉ xuất
   wav/pcm, SDK không có encoder MP3 nào (`apps/openai_speech.py:360-366,412`;
   `pyproject.toml` không có `ffmpeg`/`lameenc`/`pydub`); FFmpeg giải quyết cả
   hai chiều (mã hoá MP3 + giải mã MP3/M4A cho clone); FFmpeg đã có sẵn trên
   máy Annie (`/usr/bin/ffmpeg`) để kiểm chứng ở Bước 2. [Sửa R2-Y1] Bộ cài tăng
   dung lượng thêm **~165 MB** (binary Linux trong wheel `imageio-ffmpeg` 0.8.1
   đo thật 172.692.552 byte ngày 19/11/2026 — **bỏ con số "~25–30 MB" của v1.1**,
   sai ~5,5×; số Windows đo ở TK4.1). Binary là **GPL v3** (xem §13.7):
   [Đính chính 19/11/2026] Binary tải sau chính là **LGPL v3 (BtbN — kịch bản B đã làm xong, xem §13.7)**; GPL v3 + source offer chỉ cho binary imageio-ffmpeg 0.8.1 dự phòng trên máy dev.
9. **Thẻ `[nghỉ]` — giữ ở v1 hay dời lại?** [Sửa R1-Y2 — ĐÃ TRẢ LỜI]
   Chốt: **giữ ở v1**, với thiết kế tầng app `TextPreprocess` (§3.3) — parse tag,
   cắt đoạn, chèn silence bằng `AudioPost`; không đưa tag vào `infer()`. [Sửa
   R2-Y2] Ngữ pháp + quy tắc đã chốt đầy đủ ở §3.3 (đơn vị `s`/`ms`, số thập phân,
   tag giữa từ → báo lỗi, nhiều tag liên tiếp tổng ≤ 10 s, đường V4 tách đoạn +
   cảnh báo phí tối thiểu 50 ký tự/đoạn). Căn cứ:
   grep toàn bộ upstream 0 kết quả cho `[nghỉ` (tính năng của CIT, không phải SDK).
10. **`.srt` kèm audio ở Phòng thu — giữ hay chỉ xuất ở tab Lồng tiếng?**
    [Sửa R1-Y3 — ĐÃ TRẢ LỜI] Chốt: **giữ**, với phương pháp suy mốc của `SrtWriter`
    (§3.3: chia chunk như SDK, đo độ dài audio từng chunk, cộng dồn + khoảng lặng),
    sai số mục tiêu ±0,3 s/câu (T3.1). [Sửa R2-Y3] Hằng số khoảng lặng đã sửa đúng
    thành `gaps_to_silence` 0,30/0,50/0,70 s + quy tắc bù zeros theo im lặng mép
    đã đo (không dùng `silence_p` 0,15 s); mục tiêu ±0,3 s áp cho 10 câu đầu,
    bài dài ghi thêm sai số tối đa ở câu cuối; đo mốc bằng sóng âm thật, không đo
    bằng `SrtWriter`. Nếu Bước 3 đo vượt ngưỡng thì hạ phạm vi
    xuống chỉ xuất `.srt` ở tab Lồng tiếng.
11. **Giới hạn text — anh có bài dài hơn 20.000 ký tự/lần tạo không?**
    [Sửa R1-Y6 — TRẢ LỜI MỘT PHẦN] Giới hạn mặc định chốt là **20.000 ký tự/request**
    (lấy đúng upstream, `apps/openai_speech.py:310`); vượt → 400. Phần còn lại
    **cần anh trả lời**: nếu anh có bài dài hơn thì giới hạn phải nâng kèm đo RAM
    (TK2.6); nếu không thì giữ 20.000.
12. **Preview V4 — đồng ý tốn ký tự trả phí mỗi lần nghe thử, hay cache mẫu?**
    [Sửa R1-Y7 — ĐÃ TRẢ LỜI THIẾT KẾ, CÒN 1 Ý NHỎ CẦN ANH CHỐT] Thiết kế chốt:
    cache theo (voice_id + câu mẫu), nghe lần 2 không gọi lại API; UI hiện ước
    tính ký tự trước khi nghe lần đầu. [Sửa R2-Y7] Ước tính phí tính tối thiểu
    **50 ký tự/request** (`max(50, len(câu mẫu))` × multiplier). Cần anh chốt: **câu mẫu preview chuẩn**
    (đề xuất ≤ 60 ký tự, `config.yaml: preview_sample`) — câu càng dài càng tốn
    ký tự cho lần nghe đầu của mỗi giọng.
13. **Clone giọng — chỉ cho thu micro trực tiếp ở v1?** [Sửa R1-TH-17 — **ĐÃ CHỐT 04:32 19/11: (a) giữ cả hai**] Anh chọn **giữ cả hai như hiện tại** (thu micro + upload file, kèm cam kết bắt buộc + cơ chế gỡ khi khiếu nại) — không micro-only.
14. **Kiểm tra key V4 hợp lệ bằng endpoint nào mà không đốt ký tự?**
    [Sửa R2-Y12/Q14 — ĐÃ TRẢ LỜI, C13 chỉ còn việc kiểm chứng] Dùng
    **`GET /v1/balance`** (OpenAPI chính thức, operation `getBalance` — endpoint
    TỒN TẠI, không còn "CHƯA RÕ" như v1.1): vừa ping key (401 = key sai) vừa lấy
    số dư (`remaining` / `spendableTokens` / `totalRemainingTokens` / `plan`) cho
    màn hình quota. Bỏ ứng viên cũ `GET /v1/audio/voices` làm ping key. C13
    kiểm chứng rằng gọi `GET /v1/balance` không trừ token. (Các câu hỏi mở còn lại: Q2/Q3/Q11/Q12/Q13 + Q15–Q21 mới ở v1.3.)

---

15. **SrtDubber `[nghỉ]` + tốc độ 0,75× — giữ quy tắc v1.3 hay đổi?** [Sửa
    v1.3 — G3, §3.3] Quy tắc đã chốt ở §3.3: tag `[nghỉ]` trong câu SRT tính
    vào độ dài slot của câu (không đưa vào `infer()`); tốc độ hiệu dụng
    (tốc độ người dùng × hệ số căn giờ) giới hạn 0,75×–1,5×, vượt thì lấn
    khoảng lặng → đẩy câu sau → báo cáo câu bị lùi. Anh xác nhận giữ hay đổi?
16. **Hàng đợi: 20 job chờ + TTL 60' (v1.2) hay tối đa 3 job chờ (GPT2)?**
    [**ĐÃ CHỐT 04:32 19/11: 20 job chờ**] Anh chọn **20 job chờ + TTL 60'** (1 job chạy, đầy → 429); không dùng đề xuất tối đa 3 job chờ của GPT2. Áp dụng §4, §6 (`max_queue_jobs: 20`), §10.5, TK2.1/TK2.9/TK2.14.
17. **Đường dẫn lưu dữ liệu — giữ mặc định theo OS (§6) hay đổi?** [Sửa v1.3
    — G1] §6 đang để SUY LUẬN: Windows `%LOCALAPPDATA%\HPVoiceStudio\`,
    Linux `~/.local/share/HPVoiceStudio/`. Anh chốt giữ hay đổi sang thư mục
    khác (VD `~/HPVoiceStudio/`)?
18. **Khi mở LAN sau này: bật lại toàn bộ L1–L4 (§9.3) hay chỉ key bắt buộc?**
    [Sửa v1.3 — TH-22/TH-29] Hỏi trước để khỏi thiết kế lại — không chặn v1.
19. **PDF scan: v1 chỉ báo rõ "không OCR" (TH-23) — anh có file PDF scan cần
    đọc không, hay dời OCR sang P2?** [Sửa v1.3 — G3]
20. **Vỏ Desktop: pywebview (đề xuất v1.3, dùng WebView2 trên Windows) hay
    WebView2 trực tiếp?** [Sửa v1.3 — G4/G2, TK4.8] Chốt ở Bước 3/4.
21. **FFmpeg GPL v3 — đổi LGPL, tách binary, hay giữ GPL + source offer?**
    [**ĐÃ CHỐT 04:35 19/11: phương án (b) — TÁCH KHỎI BỘ CÀI, TẢI CÀI SAU**]
    Anh chọn **tách FFmpeg khỏi bộ cài, tải cài sau** (phương án 2 trong 4 phương án
    Annie đưa: LGPL / tách khỏi bộ cài / giữ GPL+source offer / bỏ FFmpeg hẳn):
    bộ cài không đóng gói kèm binary FFmpeg (giữ 100% Apache 2.0); lần đầu chạy
    app tải binary FFmpeg về thư mục dữ liệu (cần mạng lần đầu, kiểm checksum,
    báo tiến trình rõ); fallback FFmpeg hệ thống nếu có; không có FFmpeg → chỉ
    xuất WAV + báo rõ, không crash. NOTICE ghi LGPL v3 cho binary tải sau chính (BtbN) + GPL v3 + source offer chỉ cho binary imageio-ffmpeg dự phòng (§13.7). Xem TK4.9 + ADR-07 (đã sửa theo quyết định này).

## 16. HỢP ĐỒNG TRIỂN KHAI (mới v1.3 — GPT2 TH-12 → TH-24)

Một chỗ duy nhất chốt môi trường chạy. Mọi mục chưa đo ghi CHƯA ĐO + ticket đo.

| Hạng mục | Chốt ở v1.3 |
|---|---|
| OS đích | Windows 10/11 64-bit (chính); Linux (máy Annie, dùng được) |
| Python | 3.12 (khớp `.python-version` upstream; TK4.1 pin) |
| SDK | `vieneu==3.8.4`; backbone `pnnbao-ump/VieNeu-TTS-v3-Turbo`, subfolder `update`; revision HF ghi vào README ở TK1.3 |
| CPU/RAM tối thiểu | 4 nhân / 8 GB RAM / 3 GB trống (theo CIT) — CHƯA ĐO trên máy anh (C6/C12) |
| Ổ đĩa | Model (CHƯA ĐO, TK1.3) + FFmpeg ~165 MB (Linux đo thật; Windows đo ở TK4.1) + history tối đa 5 GB + cache (trần ở TK2.3) |
| Cổng | API `127.0.0.1:8124` duy nhất; fail-fast khi bận (§4); không tự nhảy cổng |
| Mạng lần đầu | Cần mạng để tải model (HF) + pip; sau đó offline hoàn toàn (kiểm chứng chặn mạng ở T1.1) |
| Runtime Windows | WebView2 (kiểm tra ở C9) + VC++ Redistributable (kiểm tra ở TK4.7) + ONNX Runtime DLLs (collect ở TK4.1) |
| Vỏ desktop | pywebview/WebView2 (TK4.8, Q20); đóng cửa sổ → dừng server + giải phóng cổng (TH-26); ẩn console |
| V4 | Opt-in, key người dùng nhập, tắt mặc định; fallback V3 (§3.3, ADR-10) |
| Dữ liệu | §6 (đường dẫn theo OS — SUY LUẬN, chờ anh chốt Q17) |
| Tài liệu đi kèm | README + LICENSE (HP) + NOTICE (ghi công + GPL v3 FFmpeg + source offer) + `docs/deployment-contract.md` (TK4.6 — bản đầy đủ của mục này) |

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
  - 🟡 Y1/TH-14: MP3 = **FFmpeg tải cài sau** [Sửa Q21 — ĐÃ CHỐT 04:35 19/11; trước đó là "đóng gói kèm"] (ADR-07; cả mã hoá MP3 lẫn giải mã
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
- v1.2 — 19/11/2026, nhánh `spec/v1-r2` (từ `spec/v1-r1`). Sửa theo phản biện vòng 2
  (`CRITIQUE-R2.md`, nhánh `critique/r2`, commit `f722c9c`, §7 — 8 điểm, không
  phân tích lại toàn bộ). Kiểm chứng lại bằng file thật trước khi sửa (theo skill
  `receiving-code-review-team`): `py-cpuinfo` 9.0.0 (`cpuinfo.py:1251` cờ
  `avx512vnni`, không có AVX-VNNI), `v3turbo.py:646` + `core_utils.py:77,171-256`
  (`gaps_to_silence`, `join_audio_chunks` chỉ bù zeros cho đủ tổng), wheel
  `imageio-ffmpeg` 0.8.1 (binary Linux 172.692.552 byte + `ffmpeg -buildconf`
  `--enable-gpl --enable-version3`), `keyring` 25.7.0 (entry points
  `[keyring.backends]`, `pywin32-ctypes` trên Windows), OpenAPI chính thức
  `https://docs.vieneu.io/openapi.json` (crawl 19/11/2026: `Idempotency-Key`,
  403 hết token, 402 chỉ audiobook, `GET /v1/balance`, `GET /v1/engines`,
  phí = ký tự tối thiểu 50 × multiplier).
  - 🔴 Y9: tên cờ đúng `avx512vnni` (không gạch dưới); thêm phát hiện AVX-VNNI
    (CPUID leaf 7 subleaf 1 EAX bit 4; Linux `/proc/cpuinfo`, Windows helper
    `ctypes`, macOS Intel `sysctl`); dự phòng thực nghiệm int8 đối chiếu fp32;
    ghi rõ mâu thuẫn CIT-i7-8650U (không có VNNI mà CIT vẫn khuyên INT8) +
    định nghĩa "méo"; nhánh dự phòng khi fp32 RTF > 1 (≤ 1,5 chấp nhận chậm;
    > 1,5 mặc định Nano; cả Nano > 1 thì báo máy không đủ); CPU tham chiếu ghi
    bằng model cụ thể sau C6 (TH-03, T1.4, TK1.4, C6).
  - §5 + tham chiếu lệch: Hội thoại → T3.2, Đọc file → T3.4, Tạo hàng loạt →
    T3.5, Bản đã tạo → T3.6; Phòng thu "T1–T2" → T1.2/T2.2/T2.10/T3.1; Cài đặt
    ghi rõ T2.6 là phần key V4; TH-07 "(ticket TK3.3)" → "(test T3.3)"; §4
    "Rate limit nội bộ (§3.2)" → "(§4)"; "nhắc dọn" → "chặn tạo mới" (§5, §6,
    §3.3 `HistoryStore`).
  - 🟡 Y3: hằng số đúng `gaps_to_silence` 0,30/0,50/0,70 s + đuôi tự sinh theo
    giọng, không dùng `silence_p`; quy tắc bù zeros (chỉ cộng phần thiếu sau khi
    đo im lặng mép chunk); chia mốc trong chunk nhiều câu theo tỉ lệ ký tự;
    mục tiêu ±0,3 s áp cho 10 câu đầu + ghi sai số tối đa câu cuối; đo mốc độc
    lập bằng sóng âm thật, bỏ "đo bằng `SrtWriter`" (§3.3, T3.1, TK1.6, Q10).
  - 🟡 Y1: binary Linux ~165 MB (bỏ "~25–30 MB"); license **GPL v3** (NOTICE +
    source offer; kịch bản B đổi bản LGPL); pin `imageio-ffmpeg==0.8.1` +
    collect binary PyInstaller (§3.3, §7, §13.7, ADR-07, Q2, Q8).
  - 🟡 V4 (N-V4): `Idempotency-Key` = UUID theo HP job id cho mọi `POST /v1/tts`
    (409 retry cùng key, 422 báo lỗi); không retry `POST /v1/audio/speech` sau
    timeout; bảng mã lỗi thống nhất **401/403/429** (402 chỉ audiobook);
    `GET /v1/balance` + `GET /v1/engines` cho ước tính phí (tối thiểu 50 ký tự
    × multiplier) và màn hình số dư; T2.6 "hết quota → 402" thành "→ 403"
    (TH-05, §2.4, §3.3, §6, §9.2, T2.6, TK2.2, Q3, Q14).
  - 🟡 N-FB: bảng ánh xạ giọng fallback V4→V3 (`docs/voice-fallback-map.md`,
    map theo giới tính/vùng/phong cách, không có thì về "Hải Đăng"); fallback
    phải báo rõ cả lý do lẫn giọng mới; job khóa giọng (`voice_strict: true`)
    thì không fallback mà trả lỗi; config `fallback_voice: map|default|fail`
    (§3.3, §6, ADR-10, TK2.2, T2.6).
  - 🟡 R2-detail + TH-18 (mới, §1): TK4.1 bổ sung repo (tên/public-private chốt
    ở Bước 4), trigger (tag `v*` + `workflow_dispatch`), pin Python 3.12,
    danh sách collect PyInstaller (keyring, onnxruntime, tokenizers,
    imageio-ffmpeg, model theo Q2), tải artifact + kiểm SHA-256, smoke test
    `.exe` trên runner sạch (T4.1, TH-18).
  - 🟡 Y2: ngữ pháp thẻ `[nghỉ]` chốt (số thập phân, đơn vị `s`/`ms`, tag giữa
    từ → báo lỗi, nhiều tag liên tiếp tổng ≤ 10 s, tag + cảm xúc) + đường V4
    (v4 xóa tag lạ → tách đoạn + gọi từng đoạn, cảnh báo phí tối thiểu
    50 ký tự/đoạn) + test nhánh lỗi (§3.3, TK1.6, Q9).
  - 🟡 Y12: `keyring` trong app đóng gói (`--collect-all keyring` /
    `WinVaultKeyring`, `pywin32-ctypes`); ping key đổi sang `GET /v1/balance`
    (TH-05, §6, §11 C13, ADR-09, Q14).
  - 💭 còn lại: endpoint 4 hai dạng trả (200/202) + TTL hàng đợi 60 phút + endpoint 5
    chuyển async khi text > 5.000 ký tự (§4, TK2.1); ước tính preview V4 tối thiểu
    50 ký tự (§3.3, Q12); `requirements.txt` pin đủ (`imageio-ffmpeg==0.8.1`,
    `keyring==25.7.0`, `py-cpuinfo==9.0.0`, `PyMuPDF==1.28.2`,
    `python-docx==1.2.0` — nêu tên thư viện DOCX lần đầu) (§7, TK1.1);
    ngân sách RAM TH-16 bằng số (peak ≤ 2 GB với batch 100/500 mục, T3.5);
    điều kiện tiên quyết T2.1 (curl 8123 chỉ trả MODOLIVIO khi server đó đang
    chạy); mục tiêu RTF time-stretch ≤ 1 (T2.4).
  - Quyết định tự chốt kèm căn cứ (không chờ anh): (a) khoảng nghỉ `gaps_to_silence`
    là TỔNG ở khe nên `SrtWriter` chỉ cộng zeros bù thêm (đọc từ comment
    `core_utils.py:66-76`); (b) TTL hàng đợi 60 phút, ngưỡng async endpoint 5 là
    5.000 ký tự, peak RAM ≤ 2 GB, RTF time-stretch ≤ 1 — đều ghi là SUY LUẬN,
    chốt theo số đo ở Bước 1–2; (c) PyMuPDF pin bản 1.x mới nhất (1.28.2),
    tránh dòng 2.x chưa kiểm chứng; (d) repo GitHub + public/private để mở ở
    Bước 4 (chưa chốt tên repo trong SPEC vì chưa có quyết định của anh).
  - Còn mở sau v1.2: Q2 (model kèm sẵn hay tải lần đầu), Q3 (ngưỡng cảnh báo
    phí), Q11 (bài dài hơn 20.000 ký tự), Q12 (câu mẫu preview chuẩn), Q13
    (clone micro-only hay giữ upload file) — cần anh chốt trước Bước 2; số
    binary FFmpeg Windows + tổng dung lượng Turbo + tương thích PyMuPDF 1.28.2
    đo/kiểm ở TK1.1/TK1.3/TK4.1.

- v1.3 — 19/11/2026, nhánh `spec/v1.3` (từ `spec/v1-r2`). Gộp phản biện độc lập
  của cả team (GPT1 kết luận sớm + G1 + GPT2 + G3 + G4 + G2 — xem Phụ lục C) +
  2 quyết định mới của anh 04:20 (local-only nới lỏng bảo mật mạng; thước đo
  cuối cùng là full tính năng dùng được). **BẢN CUỐI ĐƯA ANH CHỐT.**
  - Kiểm chứng lại bằng file thật/trang thật trước khi sửa: model card HF
    `pnnbao-ump/VieNeu-TTS-v3-Turbo` (đọc 19/11/2026: FAQ Apache 2.0 bao phủ
    mọi artifact incl. preset voices — nhưng card ghi cho SDK 3.7.1/23 giọng,
    HP ghim 3.8.4/25 giọng); `voices_v3_turbo.json` (meta không ghi license) +
    `voices.json` cũ (CC BY-NC 4.0) đọc lại bằng lệnh; grep toàn SPEC v1.2 cho
    các mâu thuẫn team nêu (402, FFmpeg 25–30 MB, "nhắc dọn", T3.1 vs §3.3,
    `GET /v1/audio/voices` làm ping key).
  - TH-01 viết lại: giấy phép theo từng tài sản (model card Apache 2.0 cho cả
    model/ONNX/preset voices) + bảng quyền §13.8; vẫn giữ mốc xin xác nhận bằng
    văn bản cho đúng 25 giọng 3.8.4 trước thương mại (§9.2).
  - Tử huyệt mới TH-19..TH-33 (12 cái, đánh số thống nhất sau TH-18 — xem
    Phụ lục C.2): treo UI/event loop, librosa/numba, history corrupt, LAN
    CSRF/DNS (hạ cấp P2), PDF scan/bảng, hợp đồng triển khai, máy sạch, tiến
    trình ma + trùng instance + console đen, ViTextNormalizer, RAM trình duyệt
    batch, đa client (hạ cấp P2), cache/temp phình, bẫy GPL FFmpeg, Unicode
    đường dẫn, rò rỉ file tạm. Bổ sung GPT2 cho TH-01..TH-11 (§1).
  - §0.1 nguyên tắc ưu tiên P0/P1/P2 + nghiệm thu giai đoạn bằng tính năng chạy
    thật; §9.3 nới lỏng local-only + danh sách bật lại khi mở LAN (L1–L4);
    TH-06/TH-22/TH-29 hạ cấp P2; biện pháp mạng duy nhất còn lại: bind
    `127.0.0.1`.
  - §10.5 bảng tiêu chí "mượt" thống nhất (G1+GPT2+G3+G4+G2+v1.2, tách số ĐÃ ĐO
    vs ngưỡng CHƯA ĐO, ghi cả hai bên khi khác nhau); §10.6 bảng tổng kết 7 nhóm
    tính năng × tiêu chí chạy thật × máy Annie / máy anh.
  - Ticket mới: TK1.8–TK1.10, TK2.10–TK2.14, TK3.7, TK4.6–TK4.9; test mới
    T1.8, T1.9, T4.5; C mới C14–C21; §16 hợp đồng triển khai; ADR-11/12/13;
    Q15–Q21; §3.3 bổ sung module (ViTextNormalizer, DesktopShell, .vtt,
    `[nghỉ]`/0,75×, fallback dialogue/dub/srt, worker thread, ghi atomic).
  - §6 xoá cụm "nhắc dọn" khỏi comment `max_history_gb` (quy tắc hiện hành là
    chặn tạo mới — cụm cũ chỉ còn trong 2 chỗ trích dẫn hành vi cũ).
  - Còn mở sau v1.3: Q2 (model kèm sẵn hay tải lần đầu), Q3 (ngưỡng phí),
    Q11 (bài >20.000 ký tự), Q12 (câu mẫu preview), Q13 (clone micro-only),
    Q15 (`[nghỉ]`/0,75×), Q16 (hàng đợi 20 vs 3), Q17 (đường dẫn dữ liệu),
    Q18 (bật lại LAN mức nào), Q19 (PDF scan/OCR), Q20 (pywebview hay WebView2),
    Q21 (FFmpeg GPL: LGPL/tách binary/giữ GPL) — cần anh chốt; Q21 + Q16 +
    Q13 là 3 câu quan trọng nhất trước build/phát hành.

## Phụ lục C. Đối chiếu phản biện team — v1.3 (GPT1+G1+GPT2+G3+G4+G2)

> Nguồn: tóm tắt phản biện do parent agent chuyển (file gốc nằm trong thread
> ChatGPT/Gemini, chưa tải về được — đối chiếu theo tóm tắt, ghi rõ chỗ nào
> chỉ suy từ tóm tắt). G1 đọc bản ZIP cắt cụt dòng 497; G3/G4/G2 đọc snapshot
> 1.471 dòng; SPEC đầy đủ trên đĩa là 1.593 dòng — mọi điểm dưới đây đã kiểm
> chứng lại trên bản đầy đủ trước khi kết luận.

### C.1. Lỗi bản cắt / bản snapshot — không phải lỗi SPEC (không sửa)

| Điểm team nêu | Nguồn | Kết luận kiểm chứng trên SPEC đầy đủ v1.2 |
|---|---|---|
| Thiếu mục 3, 9, 10, 11 | GPT1, GPT2 | **Lỗi bản cắt 497 dòng.** Bản đầy đủ có §3 (dòng 772), §9 (1141), §10 (1169), §11 (1228). Không sửa. |
| Cắt cụt dòng 497 | G1 | **Lỗi bản cắt.** Không sửa. |
| Thiếu PyMuPDF/ffmpeg/lameenc/python-docx | G1 | **ĐÃ CÓ v1.2:** PyMuPDF 1.28.2, python-docx 1.2.0, imageio-ffmpeg 0.8.1 (§7/TK1.1); `lameenc` đã thay bằng FFmpeg (ADR-07 — lameenc chỉ mã hoá, không giải mã MP3/M4A đầu vào). Không sửa. |
| Xung đột cổng 8000 vs 8001 vs 8123 | G1 | **ĐÃ CÓ v1.2:** HP 8124 + bảng cổng §4 (TH-13). Không sửa. |
| Thiếu bộ ánh xạ giọng fallback V4→V3 | G1 | **ĐÃ CÓ v1.2** (ADR-10, §3.3, TK2.2, T2.6). Không sửa. |
| Mã hết quota 403 vs 402 còn sót ở T2.6/TK2.2 (§9.2/§10/§12) | G3, G4, G2 | **Lỗi bản snapshot.** Bản đầy đủ: T2.6, TK2.2, §9.2 đều ghi **403**; "402" chỉ còn trong câu giải thích "402 chỉ ở audiobook" + 2 dòng nhật ký lịch sử v1.1 (TH-05 dòng 265 trích văn bản cũ v1.1, Phụ lục B dòng 1514/1555 — đúng là lịch sử, không phải quy tắc hiện hành). Không sửa. |
| FFmpeg ~165 MB vs ~25–30 MB cũ ở §15 Q8 | G3, G4, G2 | **Lỗi bản snapshot.** v1.2 đã sửa thành ~165 MB ở §3.3/ADR-07/Q8; số cũ chỉ còn trong câu "bỏ con số ~25–30 MB của v1.1". Không sửa. |
| max_history_gb chặn tạo mới vs "nhắc dọn" | G3, G4 | **Lỗi đọc snapshot.** Quy tắc hiện hành là **chặn tạo mới** (§3.3 HistoryStore, §5, §6, TH-16); "nhắc dọn" chỉ còn trong 2 chỗ trích dẫn hành vi cũ (TH-16 DỮ KIỆN mô tả SPEC v1.0 + §2.5 mô tả tính năng CIT). v1.3 đã xoá cụm này khỏi comment §6 để khỏi nhầm. |
| §15/C13/§9.2/T2.6/TK2.2 giữ văn bản cũ v1.1 về `GET /v1/audio/voices` làm ping key | G4 | **Lỗi bản snapshot.** TH-05/T2.6/TK2.2/Q14/C13 đều ghi `GET /v1/balance` + 401/403/429; `GET /v1/audio/voices` còn lại ở §2.4/TH-05 là endpoint liệt kê giọng (đúng chức năng), không phải ping key. Không sửa. |
| Phương pháp đo sai số mốc .srt ở T3.1 mâu thuẫn §3.3 | G2 | **Lỗi bản snapshot.** Bản đầy đủ: T3.1 và §3.3 đều chốt đo độc lập bằng phát hiện khoảng lặng trên sóng âm thật (`silencedetect`/envelope) hoặc nghe đối chiếu, **không** "đo bằng `SrtWriter`" (đo vòng tròn). Không sửa. |
| RTF CPU 4 nhân chưa đo | G1, GPT2 | **Đúng là chưa đo** — không phải lỗi SPEC mà là việc đo (T1.4/C6 + §10.5). Không thêm TH mới. |
| Chưa chốt đường dẫn lưu dữ liệu | G1 | **Đúng một phần:** §6 có mặc định theo OS dạng SUY LUẬN → thành Q17 (cần anh chốt). |
| Thiếu quy tắc fallback V4→V3 | G4 | **ĐÃ CÓ phần lớn** (ADR-10, §3.3, §6, TK2.2); phần thật sự thiếu: fallback cho `/v1/dialogue`, `/v1/dub`, `/v1/srt` + idempotency chưa xác nhận → bổ sung §3.3/TK2.2/TK2.13. |
| Thiếu parser .vtt | G4 | **Đúng:** UI hứa `.srt/.vtt` nhưng SPEC chỉ mô tả parse SRT → bổ sung §3.3/TK2.13. |
| Thiếu Desktop Shell/WebView; thiếu graceful shutdown + chống trùng instance | G4, G2 | **Đúng** → TH-26/TK4.8/ADR-11 (kèm chi tiết "console đen" của G2). |
| Thiếu dọn file tạm khi crash | G2 | **Đúng** → TH-33/TK2.10/TK2.6. |

### C.2. Bảng đối chiếu tử huyệt — ID gốc của team → ID mới trong SPEC

| ID gốc (team) | Nội dung | ID mới / trạng thái | Nguồn |
|---|---|---|---|
| G1 TH-12..TH-16 (5 cái) | Thiếu dependency / cổng / fallback map / RTF 4 nhân / đường dẫn dữ liệu (suy từ 6 điểm G1 nêu; file gốc chưa tải về) | **ĐÃ CÓ:** dependency (TK1.1), cổng (TH-13/§4), fallback map (ADR-10), RTF (TH-03/T1.4/C6 — việc đo); đường dẫn dữ liệu → Q17 | G1 |
| GPT2 TH-12 | Thiếu mục hợp đồng triển khai | **TH-24** (mới) | GPT2 |
| GPT2 TH-13 | Engine chiếm luồng UI | **TH-19** (mới; gộp với G3 TH-19) | GPT2 + G3 |
| GPT2 TH-14 | Hàng đợi không giới hạn | Không TH mới: hàng đợi đã giới hạn 20 + TTL 60' ở v1.2 (§4); 2 mức ưu tiên → P2/backlog (§9.3, TH-29) | GPT2 |
| GPT2 TH-15 | RAM/cache/ổ đĩa phình | TH-16 (bổ sung trần cache) + **TH-30** (cache/temp phình) | GPT2 |
| GPT2 TH-16 | Bộ cài không chạy trên máy sạch | **TH-25** (mới) | GPT2 |
| GPT2 TH-17 | V4 tính phí lặp / fallback sai giọng | **ĐÃ CÓ** TH-05 (Idempotency-Key + fallback map); bổ sung: idempotency `/v1/dialogue,/v1/dub,/v1/srt` chưa xác nhận | GPT2 |
| GPT2 TH-18 | File/API là cửa truy cập trái phép | **ĐÃ CÓ** TH-06 + **TH-22** (góc LAN/CSRF/DNS — hạ cấp P2) | GPT2 + G3 |
| GPT2 TH-19 | Khác biệt nền tảng / quyền khai thác tài sản | **ĐÃ CÓ** TH-01/TH-15 + bảng quyền §13.8 | GPT2 |
| G3 TH-19 | Treo UI/event loop FastAPI | **TH-19** (gộp với GPT2 TH-13) | G3 + GPT2 |
| G3 TH-20 | librosa time_stretch nút thắt Windows/PyInstaller | **TH-20** (gộp phần librosa của G4 TH-20) | G3 + G4 |
| G3 TH-21 | Mất/corrupt history khi tắt đột ngột/tràn đĩa | **TH-21** (mới) | G3 |
| G3 TH-22 | Lỗ hổng LAN (X-API-Key HTTP, CSRF/DNS Rebinding) | **TH-22** (mới; **HẠ CẤP P2** — local-only) | G3 |
| G3 TH-23 | PDF/DOCX treo/chữ rác (scan, bảng) | **TH-23** (mới) | G3 |
| G4 TH-19 | Tiến trình ma chiếm cổng 8124 | **TH-26** (mới; gộp với G2 TH-19) | G4 + G2 |
| G4 TH-20 | Thiếu ViTextNormalizer + librosa phụ thuộc numba/llvmlite | **TH-27** (normalizer) + **TH-20** (phần librosa) | G4 |
| G4 TH-21 | Tràn RAM trình duyệt batch 100–500 | **TH-28** (mới) | G4 |
| G4 TH-22 | Quá tải API local nhiều client | **TH-29** (mới; **HẠ CẤP P2** — local-only) | G4 |
| G2 TH-19 | Bóng ma chiếm cổng 8124 | **TH-26** (gộp với G4 TH-19) | G2 + G4 |
| G2 TH-20 | Bẫy license GPL v3 của binary imageio-ffmpeg | **TH-31** (mới; Q21) | G2 |
| G2 TH-21 | Lỗi Unicode/đường dẫn Windows có dấu/khoảng trắng | **TH-32** (mới) | G2 |
| G2 TH-22 | Rò rỉ file tạm khi Hủy/tắt máy giữa batch/SRT | **TH-33** (mới) | G2 |

Lưu ý: G3-TH-19 ≠ G4-TH-19 ≠ G2-TH-19 ở số gốc nhưng G4-TH-19 và G2-TH-19 là
cùng một lỗi (bóng ma chiếm cổng) nên gộp thành TH-26; G3-TH-19 là lỗi khác
(treo UI) nên thành TH-19. G3-TH-22 ≠ G4-TH-22 (bảo mật LAN vs quá tải đa
client) nên tách thành TH-22 và TH-29.

### C.3. Bảng đối chiếu ticket — ticket team → ticket SPEC

| Ticket team | Nội dung (theo tóm tắt) | Ticket SPEC tương đương / mới |
|---|---|---|
| GPT1 (không có ticket riêng) | 3 kết luận: thiếu mục (lỗi bản cắt), RTF 4 nhân, Idempotency-Key | Mục (lỗi bản cắt); RTF → T1.4/C6; Idempotency-Key → ĐÃ CÓ v1.2 (TH-05) |
| G1 T-01..T-09 (9 ticket) | Thứ tự build (file gốc chưa tải về — đối chiếu theo phạm vi) | T-01..T-03 → TK1.1–TK1.4; T-04..T-06 → TK2.1–TK2.2; T-07..T-08 → TK3.1–TK3.6; T-09 → TK4.1. Không thêm ticket mới (đã có tương đương). |
| GPT2 T00–T20 (21 ticket, 4 giai đoạn) | T00–T04 nền; T05–T09 engine V3/âm thanh; T10–T17 tính năng; T18–T20 đóng gói/nghiệm thu | T00–T04 → TK1.1–TK1.4, TK2.1; T05–T09 → TK1.2, TK1.6 + **TK1.8** (worker thread), **TK1.9** (atempo), **TK1.10** (normalizer); T10–T17 → TK2.3–TK2.7, TK3.1–TK3.6 + **TK2.10–TK2.14**; T18–T20 → TK4.1–TK4.5 + **TK4.6–TK4.9** |
| G3 TK-01..TK-16 (16 ticket, 4 giai đoạn) | GĐ1 Core Engine & Audio; GĐ2 Local API/Queue; GĐ3 UI Studio; GĐ4 Đóng gói/Release Gate | GĐ1 → TK1.2/TK1.4/TK1.6/**TK1.8**/**TK1.9**; GĐ2 → TK2.1–TK2.3/**TK2.10**/**TK2.11** (P2); GĐ3 → TK3.1–**TK3.7**; GĐ4 → TK4.1–**TK4.8** |
| G4 TK1.1–TK4.2 (4 giai đoạn) | TK1.1–1.5 lõi V3/VNNI/model offline/chuẩn hoá/AudioPost; TK2.1–2.3 API 8124/V4/JobQueue; TK3.1–3.2 UI 8 tab; TK4.1–4.2 đóng gói | TK1.1–1.5 → TK1.1–TK1.4 + **TK1.10** (normalizer); TK2.1–2.3 → TK2.1–TK2.2 + **TK2.10**/**TK2.13** + **TK4.8** (Shell/chống orphan); TK3.1–3.2 → TK3.1–TK3.6; TK4.1–4.2 → TK4.1–**TK4.8** |
| G2 TK1.1–TK4.5 | TK1.1–1.7 nền tảng V3; TK2.1–2.9 API/V4/job/history; TK3.1–3.6 UI + chống đơ; TK4.1–4.5 đóng gói/README/Release Gate | Đã có tương đương toàn bộ; mới: **TK4.8** (Shell/graceful shutdown/chống trùng instance), **TK4.9** (FFmpeg license), **TK4.7** (máy sạch + Unicode path), **TK2.10** (dọn file tạm), **TK2.6** (bổ sung dọn temp) |

### C.4. Bảng đối chiếu "chờ kiểm chứng thật" — mục team → C trong SPEC

| Mục team nêu | Trạng thái |
|---|---|
| GPT2 (10 mục): đo CPU/VNNI/RAM/RTF/TTFA; cài `.exe` thật; SRT dài; hội thoại nhiều giọng; batch lớn; thử trên Linux Annie; V4 khi Annie phê duyệt | Đã có: C6/C12 (đo), C1/C9 (`.exe`), C3/C12 (batch), C5/C13 (V4). Mới: **C14** (SRT dài + hội thoại nhiều giọng), **C15** (batch checkpoint/resume). "Thử trên Linux Annie" là kiểm chứng sandbox, không phải C (máy thật của anh). |
| G1 (6 mục) | Đối chiếu theo tóm tắt: C1/C6/C8/C10 + **C14/C15**. Không thêm C mới riêng (chi tiết file gốc chưa tải về). |
| G3 (8 mục): cài `.exe`/SmartScreen; cổng 8124 vs 8123; tải model/offline; RTF int8 vs fp32; micro/clone; Telex; batch ≥100 đo RAM; V4 key thật | Toàn bộ trùng C1/C9/C8/C10/C6/C2/C11/C3/C12/C5/C13. Khía cạnh mới: nghe đối chiếu atempo → **C18**; batch ≥100 đo RAM + checkpoint → **C15**. |
| G4 (7 mục): C1, C2&C11, C6, C8, C10, C5&C13, C3&C12 | Toàn bộ đã có trong SPEC. Không thêm C mới. |
| G2 (15 mục, đánh số C1–C15 trùng với C1..C13 của SPEC) | Đã có: `.exe` (C1), micro/clone (C2), batch ≥100 (C3/C12), V4 key (C5/C13), RTF (C6), LAN+X-API-Key (C7/**C16** — chỉ khi mở LAN), cổng (C8), installer chưa ký (C9), tải model (C10), Telex/VNI WebView2 (C11), peak RAM (C12), `GET /v1/balance` (C13), đóng/mở lại (C19). Mới: **C20** (MODOLIVIO gọi API HP qua `127.0.0.1:8124`), **C21** (đường dẫn có dấu tiếng Việt/khoảng trắng). |

### C.5. Quyết định tự chốt kèm căn cứ (v1.3, không chờ anh)

- (a) Model card HF là căn cứ đủ để đính chính TH-01 theo hướng Apache 2.0 cho
  cả model/ONNX/preset voices (FAQ đọc được 19/11/2026), NHƯNG vẫn giữ cửa xin
  xác nhận bằng văn bản cho đúng 25 giọng 3.8.4 vì card ghi cho SDK 3.7.1/23
  giọng — thận trọng, không suy diễn quá bằng chứng.
- (b) SrtDubber `[nghỉ]` + 0,75×: tag `[nghỉ]` tính vào slot, tốc độ hiệu dụng
  giới hạn 0,75×–1,5× (Q15 để anh xác nhận).
- (c) Hàng đợi: giữ 20 job chờ + TTL 60' (v1.2) làm mức tối thiểu, ghi đề xuất
  3 job chờ của GPT2 làm mục tiêu chặt — Q16 để anh chốt, không tự chọn.
- (d) Các ngưỡng "mượt" khác nhau (hủy job 200 ms vs 1,5 s vs 2 s; TTFA 500 ms
  vs 600 ms vs 2 s; fallback 500 ms vs 2 s; RAM batch 2,0 vs 2,2 vs 2,5 GB):
  ghi cả hai bên ở §10.5 (mục tiêu chặt / mức tối thiểu), không giấu bên nào.
- (e) Vỏ desktop: đề xuất pywebview (dùng WebView2 trên Windows) — Q20 để anh
  chốt ở Bước 3/4.
- (f) FFmpeg GPL: không tự chọn 1 trong 3 phương án (LGPL/tách binary/giữ GPL)
  — Q21 để anh chốt trước phát hành rộng; v1 cá nhân không bị chặn.
- (g) Nới lỏng local-only (TH-06/TH-22/TH-29 hạ cấp P2, chỉ giữ bind
  `127.0.0.1`) là **quyết định của anh 04:20**, không phải quyết định tự chốt
  của agent — ghi rõ nguồn ở §0 quyết định 10, §9.3, ADR-12.
