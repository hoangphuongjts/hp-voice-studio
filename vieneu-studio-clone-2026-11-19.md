# Nghiên cứu: Clone VieNeu Studio — có làm được không, có đáng làm không?

- Ngày nghiên cứu: 19/11/2026 (rạng sáng; các trang được crawler đọc lúc 18:00 UTC ngày 18/11/2026)
- Trang đích: https://www.vieneu.io/#/studio
- Phương pháp: đọc trang chủ vieneu.io, tài liệu docs.vieneu.io, README + trang Releases của repo GitHub pnnbao97/VieNeu-TTS, kiểm tra thư mục CIT Voice Studio đã cài trên máy Annie, đối chiếu MEMORY.md. **Không cài đặt gì thêm, không tải code của họ về để copy, không bắt đầu build.**
- Quy ước: **[ĐÃ XÁC MINH]** = đọc trực tiếp từ nguồn; **[SUY RA]** = suy luận từ bằng chứng; **[CHƯA RÕ]** = chưa kiểm chứng được.
- Nguyên tắc clone: clean-room — chỉ sao **chức năng/luồng**, KHÔNG copy code, logo hay thương hiệu VieNeu.

## 1. Kết luận nhanh

| Câu hỏi | Trả lời |
|---|---|
| Clone được không? | **Được, về mặt kỹ thuật.** Engine mở (Apache 2.0), SDK + giao diện demo + API server đều có sẵn trong repo. |
| Có đáng làm mới không? | **KHÔNG.** CIT Voice Studio đã là bản "tương tự" hoàn chỉnh, đã cài và chạy được thật trên máy Annie (18/11). Viết lại từ đầu chỉ trùng lặp công sức. |
| Cái gì KHÔNG clone được? | Giọng V4 + kho 1.222 giọng V4, API đám mây + tính phí/token, tài khoản, MCP server của họ, trợ lý AI dùng LLM bên thứ ba. |
| Đường nhanh nhất là gì? | (1) Dùng ngay CIT Voice Studio (đã có) hoặc VieNeu Desktop chính chủ (tải miễn phí) cho nhu cầu studio; (2) Nếu cần trong MODOLIVIO thì **mở rộng tích hợp VieNeu-TTS đã có** (clone giọng KOC, SRT khớp giờ, hội thoại nhiều giọng) thay vì build app mới; (3) Nếu vẫn muốn studio mang tên riêng thì **fork/đóng góp cho CIT** (Apache 2.0) thay vì viết lại. |

## 2. VieNeu Studio là gì?

### 2.1. Nền tảng web (vieneu.io)

**[ĐÃ XÁC MINH]** (trang chủ vieneu.io, đọc 18/11/2026):

- Slogan: "Giọng đọc AI tiếng Việt tự nhiên như người thật". **1.222 giọng đủ ba miền**, đọc đúng cả công thức toán – hoá. Gõ một câu là nghe thử ngay — **không cần đăng ký** (ô thử giới hạn 100 ký tự).
- **707 giọng V4 nhân bản chất lượng cao** — nam/nữ đủ ba miền, song ngữ Anh–Việt.
- Tính năng chính:
  - **Đọc đúng công thức toán & hoá** (phân số, tích phân, lũy thừa, phương trình phản ứng).
  - **Cảm xúc thật**: emotional tag chỉnh sắc thái (ấm áp, nghiêm túc, hào hứng, nhẹ nhàng).
  - **Voice cloning chất lượng cao**: nhân bản giọng bất kỳ từ đoạn mẫu **6–15 giây** — trên web hoặc trong ứng dụng máy tính.
  - **Phản hồi nhanh**: phát âm thanh ngay khi đang tạo (chunk streaming), tiếng đầu tiên sau 1–2 giây.
  - **API sẵn sàng cho production**: REST trên HTTPS tại `api.vieneu.io`, tương thích client OpenAI, có streaming, việc chạy nền và webhook.
  - **Từ điển đọc chuẩn**: thuật ngữ y khoa, tên thuốc, từ viết tắt — tối đa **2.000 mục**, nhập từ tệp văn bản, xuất ra dùng chung cả nhóm.
  - **Dùng trong Claude, ChatGPT, Cursor, VS Code…** qua MCP tại `https://api.vieneu.io/mcp` (cần tài khoản VieNeu có gói token còn hạn).
  - Ba tính năng dùng chung mọi gói: **Chuyển văn bản thành giọng nói · Podcast (nhiều giọng) · Lồng tiếng**.
- Số liệu họ công bố: **2,9k★ GitHub · 1,4 triệu+ lượt tải/tháng trên HuggingFace · hạng 7** bảng TTS tải nhiều nhất của HuggingFace (VieNeu-TTS-v3-Turbo 0.1B, 1,47M tải).

**[CHƯA RÕ]**: Trang Studio (`/#/studio`) là SPA chạy bằng JavaScript theo hash-route — crawler chỉ lấy được trang chủ, **không đọc trực tiếp được màn hình bên trong Studio** (các ô nhập, nút bấm, bố cục tab). Các tính năng Studio dưới đây được suy ra từ trang chủ + ghi chú phát hành Desktop + tài liệu, không phải quan sát trực tiếp giao diện Studio.

### 2.2. VieNeu Desktop (app Windows chính chủ)

**[ĐÃ XÁC MINH]** (trang Releases của repo GitHub, đọc 18/11/2026 — bản mới nhất **VieNeu Desktop 0.18.27**):

- Bộ cài Windows x64 ~90 MB, **chưa ký chứng chỉ thương mại** (SmartScreen sẽ cảnh báo, chọn "More info → Run anyway").
- Các tab/tính năng (theo ghi chú phát hành 0.18.23–0.18.27):
  - **Phòng thu (Studio)**: tạo nhiều bản đọc V3 xếp hàng; bản sau được tạo ngay trong lúc bản trước đang phát; nút "Dừng phát"; hàng đợi tạm dừng khi gặp lỗi.
  - **Tạo hàng loạt**: từ tệp danh sách (.txt, .json) hoặc **tệp phụ đề .srt** — mỗi câu thoại bắt đầu đúng giây ghi trong phụ đề (khớp mốc thời gian), câu dài tự đọc nhanh cho vừa (tối đa 2×, giữ cao độ); nhận tới **100.000 câu/tệp**.
  - **Lồng tiếng**: phụ đề (.srt, phụ đề in vào video, karaoke) đi theo giọng đọc; dùng được cả V3 (trên máy) lẫn V4 (khoá API).
  - **Sách nói, Bài giảng, Podcast**: tạo kịch bản bằng trợ lý AI (dịch lồng tiếng, kịch bản podcast, bài giảng, sách nói) — dùng LLM bên thứ ba (Gemini, DeepSeek, OpenAI, Anthropic), có tự thử lại khi nhà cung cấp quá tải (503/429).
  - **Bộ tăng tốc GPU** (card NVIDIA): tự hồi phục khi CUDA hỏng; **VieNeu SDK 3.8.4**.
  - **Server VieNeu-TTS / MCP** tích hợp trong app.
- Đây chính là "Studio" bản desktop — cùng họ tính năng với Studio web, chỉ khác V3 chạy trên máy, V4 qua API key.

### 2.3. Miễn phí hay trả phí, có cần tài khoản không?

**[ĐÃ XÁC MINH]**:

- **Thử nhanh trên web: miễn phí, không cần đăng ký** (ô gõ 1 câu, giới hạn 100 ký tự).
- **Dùng đầy đủ trên web: cần tài khoản VieNeu + gói token còn hạn.** Tài khoản mới có **free trial** (theo docs.vieneu.io; mức token trial cụ thể không ghi rõ trên trang đã đọc).
- **Giá gói token** (trang chủ, tiền Việt):
  - Starter V4: 99Kđ — ~4 giờ audio, 400.000 token, hạn 6 tháng.
  - Creator V4: 299Kđ — ~13 giờ, 1.500.000 token, hạn 6 tháng.
  - Pro V4: 799Kđ — ~44 giờ, 5.000.000 token, hạn 6 tháng.
  - Studio V4: 1,69Mđ — ~105 giờ, 12.000.000 token, hạn 12 tháng, không giới hạn theo ngày.
  - Hội viên tháng V4: 499Kđ / gói 30 ngày — ~35 giờ, 4.000.000 token, không tự động gia hạn.
  - Enterprise: liên hệ (node GPU riêng, lane riêng 8–64 luồng streaming, SLA, hoá đơn điện tử).
  - Mọi gói đều dùng được cả 3 tính năng (TTS, Podcast, Lồng tiếng); API dùng 100% quota.
- **VieNeu Desktop: tải miễn phí**, chạy V3 trên máy không tốn token; chỉ tính token khi dùng V4 qua API key.
- **Giới hạn**: **[CHƯA RÕ]** mức token của free trial và giới hạn ngày của từng gói (trừ gói Studio/tháng ghi "không giới hạn theo ngày").

## 3. Mã nguồn mở VieNeu-TTS (repo GitHub)

**[ĐÃ XÁC MINH]** (github.com/pnnbao97/VieNeu-TTS, đọc 18/11/2026):

- Repo: **pnnbao97/VieNeu-TTS** — Public, nhánh `main`, commit hiện tại `512de867`, **750 commit, 3.479 sao, 1.059 fork, 42 release, 131 tag**, tạo ngày 28/10/2025, **giấy phép Apache License 2.0**, **Archived: No** (đang hoạt động).
- **V4 là độc quyền, KHÔNG mở mã nguồn** — README ghi rõ: "Due to the strength of its voice-cloning capabilities and the potential for misuse, v4 is proprietary and will not be open-sourced. It is available exclusively through the VieNeu API / vieneu.io."
- **VieNeu-TTS v3 Turbo là bản mở mới nhất trong repo.** "Future open-source releases, including potential v3.x updates, may also be published here."
- Engine v3 Turbo gồm:
  - **48 kHz**, **25 giọng preset** (10 giọng editors' picks), ổn định, không cần clip mẫu.
  - **Emotion / non-verbal cues (thử nghiệm)**: chèn `[cười]`, `[thở dài]`, `[hắng giọng]` vào văn bản.
  - **Batched generation** (batch tối đa 32), chế độ **Conversation** nhiều người nói.
  - **Instant voice cloning từ clip 3–8 giây**, tự khử ồn đoạn mẫu.
  - **Real-time streaming + API tương thích OpenAI + Docker** — `POST /v1/audio/speech`; tiếng đầu ~115 ms; 16 luồng đồng thời trên 1 card RTX 3060; streaming được cả trên CPU.
  - **LoRA fine-tuning** — tự huấn luyện giọng/phong cách trên 1 GPU phổ thông.
  - **VieNeu-TTS v3 Nano (preview)** cho thiết bị yếu: nhanh gấp ~3× Turbo fp32 trên CPU (RTF 0,11–0,22), 24 kHz, 11 giọng preset + clone, chất lượng thấp hơn rõ rệt (nhất là tiếng Anh/song ngữ).
  - Thành phần: codec **MOSS-Audio-Tokenizer-Nano**, phonemizer **sea-g2p** (cả hai đều Apache 2.0 theo các nguồn độc lập).
  - SDK Python `vieneu`: `pip install vieneu`; `Vieneu()` mặc định v3 Turbo 48 kHz; **CPU chạy torch-free qua ONNX Runtime** (không import PyTorch), GPU tự chuyển sang PyTorch; RTF ≈ 0,5 trên CPU (nhanh gấp ~2× real-time), int8 nhanh hơn ~1,6×; các hàm `infer()`, `infer_stream()`, `infer_batch()`, `list_preset_voices()`.
  - **Giao diện web demo**: `uv run vieneu-web`, mở tại `http://127.0.0.1:7860` — README nói rõ đây chỉ là **"simplified Gradio demo interface"**; các tính năng **Dubbing, Lecture, TikTok Reel, Audiobook chỉ có trong official VieNeu App**.
  - Thư mục gốc trong repo: `apps`, `client`, `docker`, `docs`, `examples`, `finetune`, `src`, `tests`. Có bản cài Windows standalone tại `vieneu.io/#/download`, hỗ trợ Docker (profile `api-gpu` / `api-cpu`).
- **Phiên bản SDK mới nhất**: **[CHƯA RÕ]** chính xác theo tag (repo có 42 release; CIT đang ghim 3.3.0; ghi chú VieNeu Desktop 0.18.23 nhắc **"lên VieNeu SDK 3.8.4"**; một dự án khác ghi dùng SDK 3.8.3 — ước chừng mới nhất khoảng **3.8.4**).

### 3.1. Đính chính: repo KHÔNG bị archive

- Một tài liệu nghiên cứu bên thứ ba (Bright.md, tháng 8/2026) ghi "Repo announced July 23, 2026 that it will be archived with no further official open-source development/support."
- **[ĐÃ XÁC MINH] Mâu thuẫn này đã được giải quyết theo hướng repo VẪN HOẠT ĐỘNG**: metadata GitHub trực tiếp ngày 18/11/2026 ghi `Archived: No`, 750 commit, commit mới nhất `512de867`, bản Desktop 0.18.27 vừa phát hành. Khả năng cao tài liệu kia nhầm với **Supertonic** (hãng này đúng là đã thông báo dừng phát triển mã nguồn mở sau tháng 8/2026). Kết luận: **không có bằng chứng VieNeu-TTS bị archive; coi như đang được duy trì.**

### 3.2. Lưu ý giấy phép (quan trọng nếu phát hành)

- **Code repo + model v3 Turbo: Apache 2.0** (README + model card HuggingFace) — được phép dùng, sửa, phân phối lại, kể cả thương mại, kèm ghi chú bản quyền.
- **Ngoại lệ 1**: bản **VieNeu-TTS-0.3B GGUF (Q4)** trên HuggingFace ghi giấy phép **CC BY-NC 4.0** — cấm dùng thương mại, tác giả báo giá thương mại ~5.000 USD/năm. Tránh dùng bản này.
- **Ngoại lệ 2**: một kiểm toán độc lập (repo notivn/AIEV) phát hiện `vieneu/assets/voices.json` trong gói SDK có ghi `"license": "CC BY-NC — Model and voices are for non-commercial use only"`. Mâu thuẫn với Apache 2.0 của repo — **[CHƯA RÕ]** phạm vi chính xác; trước khi phân phối lại tài sản giọng đọc cần đọc kỹ file đó.
- **Với riêng anh**: không thương mại hoá trong 2026 (chỉ dùng cá nhân) nên các ngoại lệ trên **hiện không cản trở**; chỉ cần ghi nhớ khi có ý định phát hành rộng hơn.
- **V4 + kho giọng V4**: độc quyền, không có đường clone hợp pháp — chỉ dùng được qua API trả phí của họ.

## 4. Đánh giá khả năng clone

### 4.1. Một app "tương tự" cần những gì?

| Thành phần | Nguồn mở có sẵn? | Ghi chú |
|---|---|---|
| Engine TTS tiếng Việt | ✅ Có — VieNeu-TTS v3 Turbo (Apache 2.0) | `pip install vieneu`, chạy CPU ONNX, 48 kHz |
| Danh sách giọng | ⚠️ Chỉ 25 preset của v3 | Kho 1.222 giọng V4 trên web là dữ liệu độc quyền, không clone được |
| Clone giọng từ clip 3–8s | ✅ Có sẵn trong SDK | `infer(..., ref_audio=...)`, tự khử ồn; cần xin phép chủ giọng |
| Giao diện studio (nhập text, chọn giọng, nghe thử, xuất file) | ⚠️ Phải tự viết (repo chỉ có Gradio demo đơn giản) | Đây là phần việc chính của clone |
| Podcast/hội thoại nhiều giọng | ✅ Có sẵn chế độ Conversation trong SDK | Chỉ cần UI gán giọng theo nhân vật |
| Lồng tiếng theo .srt khớp mốc giờ | ⚠️ Logic phải tự viết (đọc SRT, chia câu, căn giờ) | VieNeu Desktop 0.18.27 vừa làm tính năng này; CIT đã có |
| Xuất WAV/MP3 + phụ đề .srt | ✅ Dễ (SDK trả mảng audio 48 kHz) | FFmpeg/Python đều làm được |
| Streaming phát ngay khi đang tạo | ✅ Có sẵn `infer_stream()` | Tiếng đầu ~115–300 ms |
| Tài khoản, tính phí, token | ❌ Không — phải tự xây backend + thanh toán | Chỉ cần nếu muốn bán; dùng cá nhân thì bỏ qua |
| Trợ lý AI (viết kịch bản, dịch lồng tiếng) | ⚠️ Cần key LLM bên thứ ba (Gemini/OpenAI…) | Không thuộc engine TTS |

### 4.2. Mức độ khó và thời gian ước tính

**[SUY RA]** (dựa trên độ phức tạp các thành phần + việc CIT đã làm được):

- **Bản tối thiểu chạy được** (nhập text → chọn 1 trong 25 giọng → nghe thử → xuất WAV/MP3; clone giọng từ clip mẫu; 1 giọng/nhân vật cho podcast): **1–2 tuần** cho 1 dev làm quen SDK (phần lớn là UI + gọi API, engine đã xong).
- **Bản ngang CIT Voice Studio** (thêm thư viện bản thu, hàng đợi, tạo hàng loạt từ .srt khớp giờ, cài đặt tốc độ, API HTTP nội bộ, bản Windows đóng gói): **3–4 tuần** nữa.
- **Bản ngang VieNeu Desktop chính chủ** (thêm GPU accelerator, Whisper nhận diện lời thoại để lồng tiếng, trợ lý AI, cập nhật tự động): **không khả thi trong thời gian ngắn** — nhiều tháng, và vẫn thiếu V4.
- **Phần khó thật sự không phải UI**: (a) kho giọng — chỉ 25 preset, muốn nhiều giọng "nghe như người thật" phải tự thu/clone từng giọng; (b) chất lượng V4 — đóng, không với tới; (c) độ ổn định chạy dài (batch 100.000 câu, chống tràn RAM, tự thử lại); (d) đóng gói Windows mượt (SmartScreen, driver GPU).
- **Bằng chứng clone đã có người làm**: K-Voice Studio (khome.asia) — app Windows dùng chính engine v3 Turbo, 25 giọng, clone 3–5s, 100% offline, xuất WAV/MP3 + .srt, có TTS Studio / Voice Cloning / Hội thoại & Podcast / Đọc file / Tạo hàng loạt. Tức là "clone VieNeu Studio" **đã tồn tại ngoài thị trường**, không cần phát minh lại.

## 5. Đối chiếu với những gì đã có sẵn

### 5.1. CIT Voice Studio — đã cài trên máy Annie (18/11/2026)

**[ĐÃ XÁC MINH]** (kiểm tra trực tiếp thư mục `~/workspace/cuongit/cit-voice-studio` ngày 19/11/2026 + MEMORY.md):

- **v1.0.6, Apache 2.0**, mã nguồn mở (repo Cuongyd196/cit-voice-studio), tác giả Cường IT.
- Tính năng (theo README của nó): **25 giọng tiếng Việt 48 kHz** (nam/nữ, ba miền); **nhân bản giọng** (thu micro 3–8s hoặc file MP3/WAV/M4A); giọng nước ngoài (Supertonic 31 ngôn ngữ, Kokoro 41 giọng); **Podcast/hội thoại** (mỗi nhân vật một giọng, ghép 1 file); **lồng tiếng theo .srt khớp mốc thời gian**; **API cho phần mềm khác** qua `http://127.0.0.1:8001`; không cần tài khoản, không cần Internet sau khi cài, văn bản/giọng không rời khỏi máy.
- **Đã test chạy thật ngày 18/11**: server `uv run vieneu-stream` tại 127.0.0.1:8001, `/health` OK, 25 giọng, tạo được **file WAV thật** (giọng Mai Anh, 3,84s, 368.838 byte, PCM 16-bit mono 48 kHz — kiểm chứng bằng ffprobe). Nhân bản giọng **chưa test** (cần clip mẫu + đồng ý chủ giọng). Server đã dừng sau test; khởi động lại: `cd ~/workspace/cuongit/cit-voice-studio && uv run vieneu-stream`.
- CIT ghim SDK `vieneu` **3.3.0** (cũ hơn 3.8.4 mà Desktop mới dùng — có thể cập nhật sau, không gấp).
- **Kết luận đối chiếu: CIT Voice Studio chính là bản clone tương tự VieNeu Studio (phía on-device) mà anh đang hỏi — đã có sẵn, đã chạy được, cùng engine v3 Turbo.** Làm thêm một app nữa = viết lại đúng thứ đã có.

### 5.2. MODOLIVIO — tích hợp VieNeu-TTS đã có

**[ĐÃ XÁC MINH]** (MEMORY.md):

- VieNeu-TTS **v3.8.4**, Apache 2.0, TTS tiếng Việt trên thiết bị, **25 preset, clone từ clip 3–8s**; **tab Giọng đọc đủ 18 giọng**, gồm giọng nữ Hà Nội trẻ trung năng động và Adam – Dominant bản tiếng Việt.
- Server TTS chạy ở **127.0.0.1:8123** (đã sửa từ cổng 8000 ngày 16/11).
- **Khoảng trống thật sự của MODOLIVIO không phải là "thiếu một app studio"** mà là: giọng đọc chưa chạy thật trong luồng tạo video (S2/S5 đang kẹt ở đăng nhập Muse), giọng KOC clone chưa gắn cố định theo nhân vật trong video, SRT chưa khớp thời gian từng câu thoại. Những thứ này là **mở rộng tích hợp**, không phải app mới.

### 5.3. Bảng so sánh nhanh

| | VieNeu Studio (web, V4) | VieNeu Desktop (chính chủ) | CIT Voice Studio (đã có) | Clone mới tự viết |
|---|---|---|---|---|
| Engine | V4 độc quyền | V3 trên máy + V4 qua API | V3 Turbo | V3 Turbo |
| Số giọng | 1.222 | 25 (V3) + V4 qua key | 25 (+Kokoro/Supertonic nước ngoài) | 25 |
| Clone giọng | 6–15s (web) | Có | 3–8s | 3–8s |
| Podcast nhiều giọng | Có | Có | Có | Làm được |
| Lồng tiếng .srt khớp giờ | Có | Có (0.18.25+) | Có | Làm được |
| Tài khoản / trả phí | Có, token | Không bắt buộc (V3) | Không | Không cần |
| Trạng thái | Đang chạy | Tải miễn phí, 0.18.27 | **Đã cài + chạy được thật** | Chưa bắt đầu |
| Chi phí | Token theo gói | Miễn phí (V3) | Miễn phí | 1–6 tuần công sức |

## 6. Khuyến nghị — đường nhanh nhất

1. **Không build app clone mới.** CIT Voice Studio đã đáp ứng đúng nhu cầu "studio TTS tiếng Việt trên máy" — 25 giọng, clone, podcast, lồng tiếng .srt, API nội bộ. Nếu cần dùng ngay: mở CIT lên mà dùng (server 127.0.0.1:8001).
2. **Nếu muốn trải nghiệm bản chính chủ**: tải **VieNeu Desktop 0.18.27** miễn phí từ trang Releases của repo (file `VieNeu_0.18.27_x64-setup.exe`, ~90 MB) — có thêm trợ lý AI + GPU accelerator + cập nhật tự động. (Cài trên máy Windows của anh khi mở máy; không cài gì lên máy Annie trong đợt này.)
3. **Nếu cần giọng phục vụ video MODOLIVIO**: mở rộng tích hợp đã có — gắn CIT/VieNeu-TTS vào luồng tạo video (giọng KOC clone cố định theo nhân vật, SRT khớp giờ từng câu, hội thoại nhiều giọng cho cảnh có 2 nhân vật). Đây mới là việc còn thiếu, và nó nằm trong luồng S2/S5–S6, không cần app studio riêng.
4. **Nếu sau này vẫn muốn một studio mang thương hiệu riêng**: fork CIT Voice Studio (Apache 2.0, được phép) rồi đổi giao diện + thêm tính năng riêng — nhanh hơn viết lại từ đầu nhiều lần, và không vi phạm clean-room (code gốc mở, có giấy phép).
5. **Không đụng tới**: giọng V4, kho 1.222 giọng, API/token/billing của VieNeu — đó là tài sản độc quyền của họ; dùng thì mua gói của họ, không clone.

## 7. Rủi ro và lưu ý

- **Nhầm lẫn thường gặp**: "VieNeu mở mã nguồn" chỉ đúng với **v3 Turbo**; **v4 đóng hoàn toàn**. Ai hứa clone được "y hệt VieNeu web" là hứa quá — giọng V4 không có đường lấy hợp pháp.
- **Giấy phép**: dùng v3 Turbo (Apache 2.0) thì an toàn; tránh bản GGUF 0.3B (CC BY-NC); đọc kỹ `voices.json` trước khi phân phối lại giọng; dùng cá nhân trong 2026 thì không vướng gì.
- **Repo sống hay chết**: đang sống (không bị archive — xem mục 3.1). Nhưng tác giả tập trung vào v4 thương mại; v3 mã nguồn mở có thể chỉ nhận cập nhật nhỏ, không có tính năng lớn mới. Nên **ghim phiên bản SDK** khi tích hợp (như CIT ghim 3.3.0), đừng `pip install -U` bừa.
- **Clone giọng**: chỉ nhân bản giọng của chính mình hoặc người đã đồng ý rõ ràng — cả VieNeu, CIT và MODOLIVIO đều ghi rõ điều này.
- **Ưu tiên hiện tại của anh vẫn là tạo video như Vanzo (S1/S2/S5)** — studio TTS là công cụ phụ trợ, không phải mục tiêu chính; đừng để nó chiếm thời gian của luồng video.

## 8. Nguồn

- Trang chủ VieNeu — https://www.vieneu.io/ (đọc 18/11/2026; trang Studio `/#/studio` là SPA nên crawler chỉ trả về trang chủ)
- Tài liệu VieNeu — https://docs.vieneu.io/ (đọc 18/11/2026)
- Repo VieNeu-TTS — https://github.com/pnnbao97/VieNeu-TTS (đọc 18/11/2026: 3.479 sao, Apache 2.0, Archived: No)
- Trang Releases (VieNeu Desktop 0.18.27) — https://github.com/pnnbao97/VieNeu-TTS/releases (đọc 18/11/2026)
- Đánh giá độc lập VieNeu — https://www.natecue.com/en/resources/vieneu-vietnamese-ai-text-to-speech/ (v3 mở / v4 đóng)
- Phân tích VieNeu-TTS v3 Turbo — https://alphasignal.ai/news/vieneu-tts-v3-turbo-runs-vietnamese-voice-cloning-on-a-consumer-gpu (15/11/2026)
- Nghiên cứu Bright.md về repo archive — https://github.com/thanhjash/bright/blob/HEAD/docs/research/external/Offline%20bilingual%20classroom%20speech%20IO%20for%20Bright.md (đã đối chiếu và bác bỏ phần "archive")
- Cảnh báo giấy phép voices.json (CC BY-NC) — commit notivn/AIEV `7c4be34` (github.com/notivn/aiev)
- K-Voice Studio (app bên thứ ba dùng engine v3 Turbo) — https://khome.asia/k-voice-studio
- CIT Voice Studio v1.0.6 — thư mục `~/workspace/cuongit/cit-voice-studio` (kiểm tra trực tiếp 19/11/2026) + MEMORY.md (cài + test WAV thật 18/11/2026)
- MODOLIVIO tích hợp VieNeu-TTS — MEMORY.md (v3.8.4, 25 preset, tab Giọng đọc 18 giọng, cổng 8123)
