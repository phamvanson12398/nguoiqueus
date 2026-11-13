# WhyShorts Studio — bản thiết kế dự án

Tool trên Windows để làm video hoạt hình "Why…" bằng Blender. **Claude là bộ não, tool là đôi tay**: mọi việc cần suy nghĩ (content, phân cảnh, thiết kế đạo cụ/bối cảnh/nhân vật mới) đều gọi Claude CLI (`claude -p`). Tool chỉ lo giao diện, lưu trữ, dựng cảnh từ thư viện và render.

Người dùng nói tiếng Việt. Trả lời và viết giao diện bằng tiếng Việt; lời đọc video bằng tiếng Anh.

## Môi trường máy người dùng
- Windows, Blender 5.2.3 (`C:\Program Files\Blender Foundation\Blender 5.2\blender.exe`), card NVIDIA, EEVEE.
- Thư mục làm việc cũ: `%USERPROFILE%\Videos\claude_test\` (có `manhole_scene_v2.py` = script v2 đã render thật, 1.540 dòng, và `voice.wav` của các video trước).
- Claude CLI đăng nhập bằng gói Pro/Max. Tool phải cảnh báo nếu có biến `ANTHROPIC_API_KEY` (nếu có, CLI tính phí API thay vì dùng gói).
- Bộ gõ Unikey: không gõ phím vào Blender; luôn chạy Blender bằng dòng lệnh.

## Tài liệu tham chiếu (thư mục `reference/`)
- `SKILL_blender-why-shorts.md`: skill gốc v3. Chứa toàn bộ luật phong cách, ngữ pháp camera v3, luật hài, luật âm thanh. **Đọc kỹ trước khi code.**
- `template_v1_scene.py`: cảnh mẫu 12 giây (nhân vật 2D, bối cảnh sa mạc, phụ đề, 22 SFX numpy, mixer).
- `module_v2.py`: easing, nhép miệng, bụi, phản ứng, `pose_char` v2 (IK), viền inverted hull, compositor, hold key motion blur.
- `camera_v3.py`: `solve_camera`, `cam_report`, `bake_camera`.
- `align_vo.py`: canh từng chữ theo `voice.wav` không cần model.
- `preview.py`: render vài khung xem trước.
- Nên đọc thêm `manhole_scene_v2.py` trong `Videos\claude_test` (bản tích hợp đầy đủ nhất).

## Kiến trúc

```
whyshorts/
  core/            thư viện Blender (tách từ reference, KHÔNG viết lại logic đã chạy ổn)
    look.py camera.py chars.py faces.py captions.py fx.py sfx.py mixer.py timing.py
  library/         thư viện tự lớn dần
    props/<ten>/   build.py + meta.json + thumb.png
    sets/<ten>/    build.py (có tham số) + meta.json + thumb.png
    chars/<ten>/   cấu hình nhân vật (màu, món đồ nhận diện, dáng)
  projects/<slug>/ story.json, voice.wav, preview/, out.mp4, log
  builder.py       đọc story.json -> dựng cảnh trong Blender (chạy bằng blender -b -P)
  server.py        web server cục bộ + trang điều khiển
  claude_bridge.py mọi lệnh gọi `claude -p`
  STYLE.md         luật phong cách rút gọn, đưa kèm mỗi lần gọi Claude
```

### 1. Trang điều khiển (localhost, mở trong trình duyệt)
- Nhập chủ đề hoặc bấm "Gợi ý ý tưởng" (Claude trả 10 ý tưởng theo mục 1 của skill, người dùng chọn).
- **Chọn số phút** (ô số, bước 0,5). Hiện ngay: số từ lời đọc dự kiến (~190 từ/phút giọng AI; đo thật 198–201, tự hiệu chỉnh theo giọng đã tải lên), số chuỗi máy, **thời gian render ước tính** (~1,4 giây/khung × 30 khung/giây).
- Nút "Viết content" → Claude viết lời đọc tiếng Anh, bản dịch Việt, bảng chuỗi máy.
- **Sửa content**: mỗi chuỗi là một thẻ có ô sửa lời đọc, hành động, bối cảnh, đạo cụ, nhân vật, biểu cảm, gag, tiếng động, kiểu chuyển cảnh. Thêm/xóa/kéo đổi thứ tự chuỗi. Nút "Viết lại đoạn này" (gửi Claude chỉ chuỗi đó + ngữ cảnh + yêu cầu của người dùng). Lưu lịch sử phiên bản.
- Ô tải `voice.wav` (người dùng tự làm giọng) → chạy `align_vo.py` → hiện thời gian từng câu.
- Nút "Duyệt & dựng" → kiểm tra thư viện → thiết kế phần thiếu → xem trước → render.
- Thanh tiến độ render (đọc log Blender), nút mở mp4.

### 2. Claude CLI bridge
- Gọi `claude -p` với `--output-format json`, cwd là thư mục dự án để Claude đọc `CLAUDE.md`/`STYLE.md`. Giới hạn công cụ bằng `--allowedTools` cho từng loại việc.
- Các loại việc: `ideas`, `write_content`, `rewrite_seq`, `plan_shots` (content đã duyệt → `story.json` theo khung hình, sau khi có WORDS), `design_prop`, `design_set`, `design_char`, `fix_from_preview` (đưa ảnh preview + lỗi để Claude sửa).
- Đầu ra luôn kiểm tra theo JSON schema; sai thì gửi lại lỗi cho Claude sửa (tối đa 2 lần).
- Ghi log mọi lệnh gọi (prompt, thời gian, kết quả) để người dùng biết đã dùng bao nhiêu lượt.

### 3. Thư viện tự lớn dần
- `plan_shots` liệt kê mọi bối cảnh/đạo cụ/nhân vật cần. Builder so với `library/`.
- Thiếu → gọi `design_*`: Claude viết `build.py` theo API chuẩn (`build(params) -> root object`), dùng khối cơ bản (hộp bo góc, trụ, cầu, khối tiện từ profile, khối đùn từ hình 2D, chữ 3D) + vật liệu chuẩn của `core/look.py`. Tool render thumbnail 1 khung, Claude tự xem và sửa; sau đó hiện cho người dùng duyệt ("to hơn", "đổi màu"…) rồi lưu vào thư viện.
- Cho phép nhập model CC0 dạng .glb (Kenney, Quaternius, Poly Haven); tool tự áp vật liệu hoạt hình + viền.
- Đạo cụ cầm tay là 2D, đạo cụ rơi/lăn là 3D (theo skill mục 8).

### 4. Builder và render
- `blender -b -P builder.py -- projects/<slug>/story.json --preview 50,200,366` → PNG xem trước (35%).
- `... --render` → mp4 1080x1920 30 fps + audio (VO + nhạc + SFX).
- Trước render bắt buộc: `cam_report` in `CAMERA OK`, kiểm tra luật chuyển động và âm thanh trong skill mục 6-7. Đo tốc độ 2 khung (khung đầu luôn chậm do biên dịch shader).
- Có thể render lại một phần (từ khung A đến B) rồi ghép bằng ffmpeg khi chỉ sửa một chuỗi.

### 5. Thời lượng
- Mặc định Shorts 45-75 giây. Cho chọn tới tối đa 10 phút. Video dài: nhiều bối cảnh hơn, chia chương, mỗi chương 4-7 chuỗi; các luật nhịp hài và camera giữ nguyên. (Hỏi người dùng nếu cần ưu tiên video dài.)

## Lộ trình
1. Đọc `reference/` + `manhole_scene_v2.py`. Tách thành `core/`, chạy lại cảnh nắp cống từ core để chắc kết quả **giống hệt** bản cũ (so vài khung).
2. Định nghĩa `story.json` schema; viết `builder.py`; chuyển cảnh nắp cống sang `story.json` + thư viện (nắp cống, đường phố).
3. `claude_bridge.py` + `STYLE.md`; thử `design_prop` với 3 đạo cụ mới.
4. `server.py` + trang điều khiển (chọn phút, viết/sửa content, duyệt, render).
5. Làm thử trọn một video mới từ đầu đến cuối; ghi lại lỗi và sửa.
6. Rút gọn skill `blender-why-shorts` thành hướng dẫn dùng tool.

Mỗi bước xong thì chạy thử thật trên máy và báo người dùng kết quả (ảnh/khung hình) trước khi sang bước sau.

## Tiến độ

### Bước 1 — xong (chờ người dùng xác nhận trên máy Windows)
- `core/` tách từ `reference/manhole_scene_v2.py` (giữ nguyên logic): `ctx` (reset + thông số render + trạng thái dùng chung), `look`, `geo` (khối 3D + bộ công cụ 2D), `timing`, `camera` (v2 `bake_shots` mà video nắp cống dùng + v3 `solve_camera`), `faces`, `chars`, `fx`, `captions`, `sfx`, `mixer`.
- `projects/manhole-round/scene_v2_core.py`: cảnh nắp cống dựng lại bằng core. Bối cảnh (phố, văn phòng, sơ đồ) và nhân vật (Joe, Gary, Sam) vẫn nằm trong script này; bước 2 sẽ chuyển sang `library/`.
- Kiểm tra: `tools/fingerprint.py` (dump mọi thuộc tính, keyframe, ma trận đã tính ở 16 khung, compositor, mã băm âm thanh + render PNG) và `tools/compare.py`. Kết quả trong container (Blender 5.2.3): dữ liệu cảnh giống hệt (1.211 object, 350.166 keyframe), âm thanh giống hệt, 5 khung render giống từng điểm ảnh.
- Lưu ý: `primitive_uv_sphere_add` của Blender cho thứ tự loop khác nhau giữa các lần chạy (tọa độ đỉnh vẫn giống). Đôi khi việc này làm lệch 1/255 ở vài điểm ảnh, kể cả khi chạy bản gốc hai lần. Vì vậy fingerprint so topology đã chuẩn hóa thay vì thứ tự loop.
- Trên Windows: chạy `tools\verify_manhole.bat`.
- Script cảnh mới: gọi `core.start(N, FPS, out_dir)` trước tiên; `geo.init()`, `fx.init()`, `faces.init()` sau khi tạo camera. Script tự xóa `core.*` khỏi `sys.modules` để chạy lại trong giao diện Blender không giữ trạng thái cũ.

### Bước 2 — xong (chờ người dùng xác nhận trên máy Windows)
- Định dạng video: `story.json`, đặc tả trong `STORY.md`, kiểm tra bằng `story.schema.json` (JSON Schema 2020-12). Giá trị là số hoặc biểu thức an toàn (`core/expr.py`, chỉ cho phép danh sách tên trắng, không có thuộc tính/import).
- `builder.py`: `--check`, `--preview a,b,c`, `--render`. Báo lỗi theo đường dẫn trong file (ví dụ `chars[0].expressions[2]: unknown face 'confused'`). Camera `shots_v2` (kiểu cũ) và `v3` (dùng cho video mới, có `cam_report`).
- Thư viện: `library/sets/{street,office,diagram_board}`, `library/props/{manhole_cover,manhole_hole,cover2d,clipboard,bill,diagram_square_hole,diagram_round_hole}`, `library/chars/{joe,gary,sam}/char.json` (cấu hình + mô tả, đóng vai meta), `library/motions/{drop_tumble,drop_seat}.json`. Mỗi món có `thumb.png` (`tools/thumbs.py`); xem tổng hợp ở `library/contact_sheet.png`.
- `projects/manhole-round/story.json`: dựng ra **giống hệt** `manhole_scene_v2.py` (dữ liệu cảnh, âm thanh, 5 khung render). `projects/demo-v3/story.json`: ví dụ ngắn dùng camera v3, làm mẫu cho `plan_shots`.
- Core thêm: lưu đệm vật liệu theo tên, `geo.arrow2d/label/points`, `fx.add_steam/add_drips`.
- Trên Windows: chạy `tools\verify_story.bat`.
- Thứ tự trong `sets`/`props`/`chars` là thứ tự tạo vật thể: đổi thứ tự sẽ đổi dãy nhà ngẫu nhiên và tên lưới (render vẫn đúng, chỉ không còn giống hệt bản cũ).

### Bước 3 — xong (đã chạy thật Claude CLI trong container)
- `STYLE.md` (luật phong cách rút gọn từ skill, gắn vào mỗi lần gọi bằng `--append-system-prompt-file`), `library/AUTHORING.md` (API viết đồ thư viện).
- `claude_bridge.py`:
  - Các việc: `ideas`, `write_content`, `rewrite_seq`, `plan_shots`, `design_prop`, `design_set`, `fix_from_preview`; thêm `approve` và `usage`. `design_char` mới có schema, chưa có hàm.
  - Mỗi lần gọi: `claude -p --output-format json --json-schema` (nếu CLI không hỗ trợ thì tự tách khối ```json), `--tools`/`--allowedTools` theo từng việc, prompt gửi qua stdin.
  - Kết quả kiểm bằng `schemas/*.json` (`jsonval.py`, chỉ dùng thư viện chuẩn) cộng kiểm tra riêng; có lỗi thì gửi lại cùng phiên (`--resume`), tối đa 2 lần.
  - Ghi `logs/claude_calls.jsonl` và `logs/calls/*.json`.
  - Có biến `ANTHROPIC_API_KEY` thì cảnh báo và bỏ biến đó (giữ lại nếu đặt `WHYSHORTS_KEEP_API_KEY=1`).
  - `design_*`:
    1. Claude viết `build.py`.
    2. Quét an toàn AST (chỉ cho import math/random/bpy/bmesh/mathutils/core; `bpy.ops` chỉ primitive/shade; không file, os, eval…).
    3. Dựng trong Blender (`tools/thumbs.py --views --tag rN`: ảnh thumb, front, side, top, iso_back, scale cạnh Joe).
    4. Dựng lỗi thì gửi traceback cho Claude sửa; Claude dùng Read xem ảnh và chấm điểm, sửa tối đa 2 vòng.
    5. Ghi `meta.json` với `status: draft` cùng nhận xét. `--feedback` để người dùng yêu cầu sửa; `approve` để duyệt.
- Core thêm khối cơ bản: `rbox`, `cone`, `torus`, `lathe`, `extrude`, `text3d`, `group3d`/`attach`, `import_glb`, `keep_hidden`.
- `storycheck.py` (kiểm tra story không cần Blender) dùng chung cho builder và bridge.
- Thử thật 3 đạo cụ (`traffic_light`, `milk_carton`, `smartphone`), mỗi cái mất 85-200 giây, đều đạt 8/10 khi Claude tự xem lại. Thêm một lần sửa theo góp ý "to hơn, đổi đỏ". Đã đưa cả ba vào `projects/demo-v3`. Cả ba đang ở trạng thái nháp, chờ người dùng duyệt.
- Chạy bridge trên Windows bằng bất kỳ Python 3.10+ nào, kể cả `python.exe` đi kèm Blender. `WHYSHORTS_BLENDER` mặc định là `C:\Program Files\Blender Foundation\Blender 5.2\blender.exe`.

### Bước 4 — xong (đã thử trong container bằng Playwright)
- `server.py`:
  - Chỉ dùng thư viện chuẩn; Windows mở bằng `start_studio.bat` (Python đi kèm Blender), địa chỉ http://127.0.0.1:1111 (trước đây 8765).
  - Việc nền chạy theo job: log, tiến độ, nút hủy (giết luôn tiến trình con), mỗi dự án chạy một việc nặng một lúc.
- API `/api/...`:
  - `status` (cảnh báo API key, có Claude/Blender chưa, số lượt), `estimate`, `projects`.
  - Theo dự án: `ideas`, `idea`, `content/write`, `content` (lưu kèm lịch sử), `content/rewrite`, `history/<f>/restore`, `voice` (tải wav lên rồi `align.py`), `build` (plan_shots → thiết kế đồ thiếu → kiểm tra → xem trước), `preview`, `fix`, `render` (pct, đoạn khung vào `parts/`, tiến độ từ dòng `RENDER FRAME`, ffprobe), `open`, `file/...`.
  - Thư viện: `library`, `library/approve`, `library/design`.
- `ui/index.html`: 5 bước cộng tab thư viện.
  - Ước tính tức thì: số từ (190 từ/phút, sau khi tải giọng thì dùng tốc độ đo được), số chuỗi, số khung, thời gian render (1,4 s/khung).
  - Thẻ chuỗi sửa được mọi trường; thêm, xóa, kéo ☰ (pointer events, có tự cuộn) hoặc bấm ▲▼; nút "Viết lại đoạn này"; lịch sử phiên bản.
  - Tải giọng đọc lên và xem thời gian từng câu; ảnh xem trước bấm phóng to; ô "Nhờ Claude sửa"; thanh tiến độ render; xem hoặc tải mp4; duyệt hoặc góp ý đồ nháp.
- `align.py`: thuật toán của `align_vo.py` dạng hàm, kết quả trùng khớp `align_vo.py`.
- `builder.py --render --frames A-B` render một đoạn vào `parts/`.
- Đã gọi Claude thật qua trang: `ideas` (201 s, 10 ý), `write_content` 1 phút (195 s, 155 từ, 7 chuỗi), `rewrite_seq` (36 s). Kết quả nằm trong `projects/toast-butter-side`.
- Chưa chạy qua trang: `build`/`plan_shots`, `fix_from_preview`, thiết kế đồ trên trang (bước 5). Content bánh mì đòi 13 món mới, nên prompt viết content đã thêm luật "tối đa khoảng 5 món mới mỗi phút, ưu tiên dùng lại".
- `voice.wav` người dùng gửi dài 51,6 s, không khớp `WORDS` của video nắp cống (45 s). Có thể là một bản thu khác.

### Bước 5 — xong phần chạy thử trong container, chờ người dùng render bản đầy đủ (video "Why Does Toast Land Butter-Side Down?", `projects/toast-butter-side`)
- Đầu vào của người dùng: content 1,5 phút (222 từ, 10 chuỗi) và giọng OmniVoice 64,4 s, ra 1.966 khung.
- Chạy "Duyệt & dựng" qua server: `plan_shots` mất 12 phút (story có 10 seq camera v3, 32 thẻ, 10 track) → thiết kế 7 món
  (`sets/kitchen`, `props/{dining_table,toast,toast2d,tower_stack,diagram_toast_spin}`, `chars/gary_sneakers`; mỗi món 2–5 phút,
  đều 8/10 trừ toast 5/10) → dựng `CAMERA OK` ngay lần đầu, 1.599 object. Tổng cộng 36 phút.
- Lỗi gặp và đã sửa:
  1. Nút tải giọng gửi GET kèm dữ liệu → đổi sang POST. Thêm `wavfix.py` (wav float/24-bit/extensible → PCM 16-bit).
  2. `[beat]` không được phần mềm giọng hiểu → tab Giọng đọc xuất bản cho TTS (`...` / xuống dòng / SSML / bỏ).
  3. Claude CLI kiểm schema bằng Ajv draft-07 (không nhận `prefixItems`), còn API đòi draft 2020-12 → `cli_schema()` nới tuple
     thành `anyOf`; jsonval vẫn kiểm chặt.
  4. Content cần thẻ chữ trên màn hình → `core/cards.py` + `cards` trong story (title, label, stamp_x/check, bubble, iris).
  5. `size` của thẻ bị hiểu là hệ số nhân (1.3 → chữ khổng lồ) → tài liệu + schema 0,03–0,3 + tự nhận ra hệ số + tự xuống dòng/co cho vừa khung.
  6. Giày không đổi được (Gary sneaker vẽ trên thân) → `cfg.shoe` + extras `on: footL/footR`; gộp `chars.char_cfg/draw_extras`.
  7. Ánh trời xanh nhuộm mặt ngửa (ruột bánh xám xanh, bơ ô liu); Claude tự đoán sai là lỗi lưới, sửa 2 vòng không hết →
     ghi vào AUTHORING.md, gửi góp ý đúng hướng thì vòng 2 đạt 8/10.
  8. Bộ tách chữ cắt "brand-new" thành 2 chữ → giữ từ có gạch nối.
  9. Vòng tự sửa của build (lỗi Blender hoặc cam_report → Claude vá story); bỏ qua đồ đã có trong thư viện; prompt xem lại
     cho bối cảnh không đòi `scale.png`; log điểm "?/10".
- Đã thử: "Nhờ Claude sửa" (khung 886, 42 s), góp ý thư viện (toast, gary_sneakers) qua `/api/library/design`.
- Render: container chỉ có CPU, nên đã render đoạn 1–300 ở 25 % (46 phút, 9,2 s/khung): 300 khung + AAC, khoảng −20 dB, đỉnh −5,9 dB; thẻ, phụ đề, whip, bong bóng đều đúng. Cả video ở 100 % render trên máy người dùng (khoảng 1.966 × 1,4 s ≈ 46 phút).
- Còn để ý: chữ phụ đề đôi khi trùng với nhãn thẻ ("BRAND-NEW SHOES"); plan_shots nên tránh thẻ trùng chữ với phụ đề.

### Bước 6 — xong
- `skill/blender-why-shorts/SKILL.md` (v4, 98 dòng thay cho 1.563 dòng): không còn dạy viết tay script Blender; dạy Claude dùng tool.
  Gồm: tool nằm ở đâu, cách cập nhật (kể cả gỡ xung đột git đã gặp), bảng 5 bước với thời gian đo thật, điều khiển tool bằng
  computer use hoặc dòng lệnh (không gõ vào Blender), danh sách kiểm tra ảnh xem trước, sửa tay `story.json`, thư viện, bảng lỗi
  hay gặp, cách giao kết quả. Luật phong cách không chép lại mà trỏ tới `STYLE.md` (một nguồn duy nhất).
- `skill/blender-why-shorts.zip`: tải lên claude.ai để thay skill cũ. Đã thử: một phiên Claude chỉ có skill này trả lời đúng quy trình
  sửa một chuỗi đã render và lỗi "[beat]".
- Thêm `tools/splice.py` + nút "Ghép vào video đầy đủ" ở tab Render (cần ffmpeg): thay khung A-B bằng `parts/*_AAAA-BBBB.mp4`, giữ
  tiếng gốc, bản cũ lưu `*_before.mp4`. Đã thử khung 50-79, khung 1-30 và qua server với đoạn render thật.
- `README.md`: hướng dẫn nhanh cho người dùng.

## Video dài 16:9 (kế hoạch ở `docs/LONGFORM.md`)
Phân tích kênh mẫu, kế hoạch 8 bước, thiết kế nhiều quốc gia/phe với trang phục theo văn hóa (mục 3b), nhạc, tiếng động và hiệu ứng hình (bước 5).
Shorts giữ nguyên: mọi thay đổi kiểm bằng fingerprint (manhole-round, demo-v3, toast-butter-side đều giống hệt).

### Bước 1 — xong (khổ 16:9, chương, camera video dài)
- `meta.aspect` "16:9" → 1920x1080; `ctx.frame_half()` cho thẻ/phụ đề. Khổ 9:16 dùng nguyên hằng số cũ.
- Camera rig `long` (`camera.solve_long`, `long_report`): danh sách shot cắt thẳng, mỗi shot camera trôi; báo cắt/phút, shot ngắn/dài, shot đứng yên.
- Độ sâu trường ảnh `camera.dof` (v3 và long): phụ đề/thẻ chuyển sang cảnh "Overlay" (camera sinh đôi không DOF), compositor Alpha Over → vẫn nét (`core/overlay.py`).
- Phụ đề `captions.style`: pop (Shorts), bottom (16:9), off. Thẻ mới `fade`, `chapter`.
- `longform.py`: `split` cắt giọng + chữ vào `chapters/NN/` (mỗi chương là một dự án con), `status`, `concat` (ffmpeg -c copy).
- `align.py`: tìm theo dải khi kịch bản dài (> 3000 cặp dấu câu × khoảng lặng): 1.865 từ trong 8 s; 568 từ ra kết quả giống hệt cách tìm đầy đủ (0,8 s thay vì 141 s).
- Bridge: `write_content_long` (schema `content_long`: chapters, shots, factions), `PLAN_RULES_LONG`; `rewrite_seq` giữ chapter/shots.
- Server/UI: chọn khổ video, ước tính số chương/cú máy, thẻ chuỗi có chương + cú máy, dựng/xem trước/sửa theo chương, render lần lượt + ghép.
- `story.json` nhận `factions`, `chars[].faction/role` (chưa dùng khi dựng; bước 4).
- Mẫu: `projects/demo-long` (tay viết). Trên Windows: `tools\verify_long.bat`.
- Chạy thử thật qua server (`projects/why-manholes-round-long`, 3 phút, 2 chương; giọng espeak-ng chỉ để thử, không đưa lên git):
  write_content 202 s (568 từ, 6 nhịp, 48 cú máy dự kiến) → canh chữ + chia chương → Duyệt & dựng 33 phút: chương 1 có 30 shot,
  16,2 cắt/phút; chương 2 có 31 shot, 15,1 cắt/phút, thiết kế thêm `props/sewer_cutaway` (8/10); cả hai `CAMERA OK` ngay lần đầu.
  Ảnh: `docs/img/longform_step1.jpg`. Render + ghép thử 2 chương × 45 khung (dự án tạm, đã xóa); bấm Render lại thì bỏ qua chương đã có.
- Lỗi đã sửa khi chạy thử: phụ đề 16:9 bị nhân hệ số ống kính hai lần (mất ở lens ≠ 27); hai dòng phụ đề không bao giờ chồng nhau;
  tên hàm `target` trùng biến trong server; khung các chương trên trang bị bó hẹp.
- Còn để ý: Claude đặt máy cận mặt quá sát (cắt đầu) → đã thêm công thức khoảng cách theo lens vào `PLAN_RULES_LONG`, cần thử lại ở bước 2.
  Container: 16:9 ở 25 % khoảng 20 s/khung (DOF + lớp phủ chỉ thêm ~7 %); đo trên máy người dùng bằng `verify_long.bat`.

### Bước 2 — xong (mẫu kịch bản + bộ kiểu cảnh)
- `LONGFORM_RULES.md` (gửi kèm write_content/rewrite/plan_shots của video dài): khung kịch bản theo % thời lượng (mở giữa cao trào →
  "let's go back" → câu hỏi → cú mới mỗi 45-70 s → giải thích ~75 % → mở rộng → gọi lại tiêu đề), luật lời đọc, bảng lời → kiểu cảnh,
  nhịp hình, cách viết shot, màn hình chữ, nhiều phe.
- `core/framing.py`: shot `frame` (subject/type/angle/height/x/move) → keys đúng khoảng cách theo lens; builder video dài dựng camera
  sau tracks/blocking và lấy chủ thể ở khung giữa cú máy. Hết lỗi cận mặt cắt đầu.
- Thẻ `screen` (year/number/question/quote/name/place/fact). `long_report` in số shot theo kiểu.
- Kiểm tra: `check_long_content` (12-16 cắt/phút, ≥ 1 màn hình chữ mỗi 90 s, ≥ 6 kiểu cảnh), `check_long_story` (mọi card_text của
  content phải lên màn hình; không 3 shot giống hệt liền nhau). Thử trên bản cũ: bắt được 1 dòng chữ Claude quên đưa lên màn hình.
- Chạy thật:
  - write_content 5 phút "Why Were Roman Roads So Straight?" (`projects/why-roman-roads-straight`, 368 s): bám khung kịch bản
    (mở ở Britannia, "let's go back", câu hỏi ở ~30 s, "So here's the real answer" ở 74 %, gọi lại tiêu đề), 75 cú máy = 15,1 cắt/phút,
    9 kiểu cảnh (8 màn hình chữ, 7 bản đồ, 9 sơ đồ, 1 bàn chiến thuật), 4 phe. Cần 14 món mới (bản đồ giấy da, đồng quê La Mã,
    nhân vật La Mã/Briton…) → bước 3-4.
  - plan_shots lại chương 1 video nắp cống (13 phút): 26/29 shot dùng `frame`, 15,7 cắt/phút, 9 kiểu, 6 màn hình chữ, `CAMERA OK`,
    cận mặt thấy trọn đầu. Ảnh: `docs/img/longform_step2.jpg`.

### Bước 3 — xong (bản đồ giấy da, bàn chiến thuật, giấy sơ đồ)
- Ba bối cảnh dựng từ dữ liệu trong story (tôi viết tay, không để Claude thiết kế lại mỗi video), dùng `core/maps.py`:
  - `parchment_map`: bờ biển/hồ/sông thật Natural Earth 1:50m (`data/geo/`, public domain, `tools/ne_pack.py`) cho mọi khung kinh/vĩ độ;
    thành phố, vùng theo phe hiện dần, mũi tên hành quân vẽ dần (đầu mũi tên chạy theo), quân cờ di chuyển, núi, tên biển, tiêu đề, la bàn.
  - `tactical_board`: sa bàn (cỏ/cát/đất/tuyết, đồi, sông, rừng, đường, tường), khối quân 3D theo phe chia ô thành đội hình, có cờ, `moves`.
  - `paper_diagram`: giấy ô/kẻ dòng/trắng/blueprint, nét/vòng tròn/mũi tên vẽ dần, tô vùng, chữ viết tay, tay đeo găng cầm bút chạy theo nét.
- Màu theo `factions` của story (builder truyền `_factions` vào set khi story có phe). Anchor cho camera: `city_*`, `region_*`, `arrow<i>_*`, `unit_*`.
- Framing: nhìn từ trên thì máy và điểm nhìn trượt cùng nhau (không xoay khung), nghiêng 10° để không bị xoay ngẫu nhiên; map/board nhìn vào mặt bàn.
- Catalog gửi Claude có mô tả tham số, anchor, gợi ý camera. LONGFORM_RULES mục 6; content không đưa bản đồ/sơ đồ vào library_needs.
- Mẫu: `projects/demo-map` (Ý 312 TCN), `projects/demo-board` (sa bàn + giấy sơ đồ). Thumbnail lấy từ ảnh xem trước (tools/thumbs.py
  chưa khung được bối cảnh đặt xa gốc tọa độ).
- Chạy thật: plan_shots chương 1 video La Mã (giọng espeak để thử, 172 s, 14 phút Claude): dùng 2 bản đồ (đế chế thế kỷ 2, Ý 312 TCN),
  1 sa bàn, 5 tờ sơ đồ, 47 shot (46 dùng `frame`), 4 màn hình chữ, check_long_story sạch. Dựng riêng các shot dữ liệu: đúng địa lý,
  mũi tên/vùng/quân cờ đúng lúc (`docs/img/longform_step3.jpg`). Còn thiếu: nhân vật, bối cảnh, đạo cụ La Mã → bước 4.
- Còn để ý: một shot insert nhắm tâm tờ giấy trống (nên nhắm `label_*`); tay vẽ hơi nhòe do motion blur khi chạy nhanh.

### Bước 4 — xong (văn hóa, trang phục, đám đông)
- `library/cultures/<id>/culture.json` (bảng màu, kiểu tóc/râu, dải màu da, vai → trang phục, nguồn, điểm tranh cãi) và
  `library/outfits/<id>/outfit.json` (mảnh 2D gắn torso/head/foot/handL/handR, màu theo ô `$team $cloth $metal…`). Tài liệu: `library/OUTFITS.md`.
- `core/outfits.py`: look (tóc/râu theo văn hóa + seed), đồ cầm tay theo cánh tay, khăn cổ màu riêng cho nhân vật chính (`look.accent`),
  không vẽ râu hai lần khi trang phục đã có râu, đội hình (block/line/column/wedge/scatter/circle), đám đông bằng collection instance.
- Builder: `chars` type `person` + faction/role/outfit/look/outfit_changes; `crowds` (vài lính mẫu nhân bản, moves, march, biểu cảm khác nhau).
  `chars/person` (thân chuẩn), `sets/open_field`. Mẫu tay viết: `roman_empire_50ad` + `roman_legionary_50ad`; `projects/demo-legion`.
- `tools/lineup.py`: ảnh xếp hàng cạnh Joe + ảnh bóng đen nhỏ. Bridge `design_culture` (tra web, nguồn) và `design_outfit` (xem lineup,
  chấm sử liệu + bóng đen so với phe khác, sửa tối đa 2 vòng). Server: thiết kế văn hóa trước, rồi trang phục các vai story dùng.
- Chạy thật: văn hóa Briton (117 s, 6 vai có nguồn Caesar/Tacitus/Pliny), Cộng hòa La Mã 312 TCN, Samnite (81 s); trang phục
  briton_warrior (6→8/10), roman_surveyor 8, roman_centurion 7, briton_guide 7, appius_claudius 8, roman_hastatus_312bc 8, samnite_soldier 8.
  Chương 1 La Mã: plan_shots 5 phút → 13 món + 2 trang phục vai → dựng `CAMERA OK` (46 shot, 15,7 cắt/phút). Ảnh: `docs/img/longform_step4.jpg`.
- Lỗi đã sửa: thiếu tên file văn hóa/trang phục trong Library của builder; khăn bị tóc dài che; ria vẽ hai lần; ria che miệng;
  kiểm "che mắt" báo nhầm với mũ nửa elip. Story ghi `outcrop.size` dạng [5, 3] trong khi bối cảnh cần một số → sửa tay (vòng tự sửa của build sẽ làm việc này).
- Còn để ý: dựng chương 1 mất 434 s (6.398 object) → bước 6 tối ưu; nhãn "CENTURION" đè đầu nhân vật; tools/thumbs.py chụp hụt mặt
  nhân vật thấp (con dê).

### Bước 5 — xong (âm thanh và hiệu ứng hình video dài)
- `core/audio_long.py` (numpy, lọc bằng FFT, trộn chương 3 phút trong vài giây):
  - nhạc tự tổng hợp nhiều đoạn (intro → build → full → break, 8 ô nhịp/đoạn) theo mood epic, tense, mystery, march, calm, sad, triumph;
    `file` trong `library/music/` thay được (đọc wav, hoặc ogg/mp3/flac qua `aud` của Blender);
  - 23 tiếng video dài (march, war_drum, war_horn, sword_clash, shield_bash, arrows, gallop, crowd_roar, fire, rain, thunder, quill…),
    13 nền âm thanh; file CC0 `library/sfx/<tên>.wav`, `amb_<loại>.wav` được ưu tiên;
  - giọng: lọc 80 Hz + nén; nhạc/nền hạ dưới lời; đo độ lớn BS.1770 (biquad K đúng chuẩn, khớp ffmpeg ebur128 ~0,1-0,2 dB),
    chặn đỉnh + đo đỉnh thật (lấy mẫu ×4) → −14 LUFS, đỉnh thật ≤ −1 dB. Builder in `AUDIO … LUFS` và ghi `mix.wav`.
- Builder dùng đường này khi 16:9 hoặc có `sound.master`; đường Shorts giữ nguyên (fingerprint giống hệt). Whoosh chỉ ở whip và màn hình chữ.
- `core/fx_long.py`: smoke, dust, fire (lưỡi lửa + tàn + khói), arrows (đường cong, xoay theo hướng bay), sparks, banner (Wave modifier),
  light_shafts, rain/snow (lớp trước ống kính, driver `frame`), `grade` theo shot (day, dawn, dusk, night, cold, warm, desert, sepia, storm, fire;
  compositor Mix nhân màu + Bright/Contrast, giữ nguyên chữ vì lớp phủ nằm sau). Shot không ghi grade = day.
- Schema: music/ambience theo đoạn, tên tiếng video dài, `sound.master`, `vfx`, shot `grade`. LONGFORM_RULES mục 8-9.
- Chạy thật: Claude thêm âm thanh + hiệu ứng vào chương 1 La Mã qua "Nhờ Claude sửa" (38 s, 35 thay đổi): 9 đoạn nhạc đổi mood, 17 đoạn nền,
  53 tiếng động, 14 hiệu ứng, grade theo shot; dựng `CAMERA OK`, trộn −14,6 → sau khi sửa vòng bù −14,1..−14,3 LUFS. Ảnh: `docs/img/longform_step5.jpg`.
- Lỗi đã sửa: K-weighting xấp xỉ lệch 1 dB với nhạc nhiều trầm → dùng biquad chuẩn; limiter làm hụt độ lớn → vòng bù; đỉnh thật vượt −1 dB
  → đo ×4 và hạ trần; Bright/Contrast dùng thang −100..100 (grade gần như không thấy); `role` của nhân vật thư viện (Joe) không đòi trang phục.
- Còn để ý: cột khói trông như chồng đĩa (thêm biến thể); giọng espeak nhỏ nên phải tăng 9-15 dB khi chuẩn hóa.

### Bước 6 — xong (dựng và render nhanh)
- Đo bằng cProfile chương 1 La Mã (642 s, 6.542 object): 338 s là `keyframe_insert` (1,35 triệu lần, chủ yếu tư thế nhân vật),
  ~230 s là `bpy.ops` tạo khối (chậm dần theo số object; quả cầu khói 1,27 s/cái).
- Chế độ nhanh cho video dài (`meta.fast_build`, mặc định bật với 16:9; Shorts giữ đường cũ, fingerprint giống hệt):
  - `timing.KeyBuffer` + `timing.key()`: chars.py ghi keyframe vào bộ đệm, cuối cùng mỗi F-curve ghi một lần (foreach_set, BEZIER,
    AUTO_CLAMPED như keyframe_insert) — 3,47 triệu key trong 2,5 s;
  - `geo.FAST`: cube/cyl/sphere/cone bằng bmesh (không bpy.ops); fx_long tạo icosphere/lưới/mặt phẳng bằng bmesh.
  - Kết quả: demo-legion 40 s → 4 s, render giống từng điểm ảnh với chế độ cũ (lỗi đầu tiên: mã kiểu tay cầm 3 = ALIGNED, đúng là 4);
    chương 1 La Mã 642 s → 97 s.
- Render chuỗi ảnh (`builder.py --render --seq [--quality fast|normal|high] [--step 2]`): PNG vào `frames/`, `use_overwrite=False` +
  placeholder → bấm lại là render tiếp; xóa file rỗng của khung đang dở; đổi story/chất lượng thì xóa ảnh cũ; âm thanh = `mix.wav`
  (video dài) hoặc `sound.mixdown` (Shorts); `tools/encode.py` ghép bằng ffmpeg (concat có thời lượng, khung thiếu giữ ảnh trước).
  Chất lượng: fast = on twos + 12 mẫu (~30 % thời gian), normal = mẫu của story, high = 48 mẫu.
- Server/UI: chọn chất lượng ở tab Render (video dài render từng chương bằng chuỗi ảnh rồi ghép), tiến độ tính theo ảnh thật đã render
  (đúng cả khi render tiếp), nút "Đo tốc độ máy" (`--bench 3`, lưu s/khung ở 100 % vào `local_settings.json`, ước tính theo 3 mức chất lượng).
- Thử: demo-long 25 % fast, ngắt ở ảnh 29 (để lại placeholder rỗng khung 59), chạy lại → render nốt 151 ảnh, ghép 360 khung 12,0 s có tiếng.
  Container ~13 s/ảnh ở 25 % (CPU, đang chạy song song); số thật trên máy người dùng: bấm "Đo tốc độ máy".
- Âm thanh: vòng bù độ lớn 10 lần (giọng nhỏ cần tăng 13-15 dB vẫn ra −14,1 LUFS, đỉnh thật −1,1 dB).

### Bước 7 — xong (gói YouTube + thumbnail)
- `claude_bridge.youtube_package` (schema `youtube`, có tra web): 8-12 tiêu đề ≤ 70 ký tự (góc khác nhau, best_title), câu móc + tóm tắt,
  `beat_titles` (tên ngắn từng chuỗi), nguồn, 10-15 tag, 3 hashtag, bình luận ghim, 3 ý tưởng thumbnail (layout hero/vs/map/object,
  nhân vật + nét mặt + pose, chữ ≤ 4 từ). Kiểm: độ dài, tag ≤ 480 ký tự, nhân vật/bối cảnh/nét mặt có thật.
- `youtube.py`: mốc chương từ thời gian giọng đọc thật (đầu chuỗi, 00:00 đầu tiên, ≥ 10 s, ≥ 3 mốc, tên chương + tên đoạn không lặp chữ),
  mô tả hoàn chỉnh; `thumb_story`: bố cục cố định do tool đặt (hero = 1 người to một bên + chữ nửa kia; vs = 2 người hai phần ba + VS +
  chữ dải dưới; map = bản đồ "đã vẽ xong" + chữ dải trên; object = cận vật + mũi tên) — Claude chỉ chọn người/mặt/pose/chữ.
- Thẻ mới `thumb_text` (chữ khổng lồ, viền đen + viền trắng "đóng dấu" 12-16 bản sao, tự co vừa ô), `arrow` (khối mũi tên có viền),
  `circle`. `builder --preview N --size 1280x720`.
- Server `job_youtube` → `projects/<slug>/youtube/` (package.json, description.txt, titles.txt, thumb_1..3.png); Claude xem 3 ảnh,
  chấm, chọn và sửa cái tốt nhất 1 lần (bản cũ `thumb_k_v1.png`). Tab "6 YouTube": thumbnail, tiêu đề (chép), mô tả (chép), tag, bình luận ghim.
- Chạy thật video La Mã (~5 phút/lần): 10 tiêu đề (chọn "The Real Reason Roman Roads Were So Straight"), 9 mốc chương thật, 10 nguồn có link,
  15 tag. Thumbnail: lần 1 (Claude tự đặt tọa độ) chữ đè mặt, người chồng nhau, đầu nghiêng (độ hiểu thành radian) → chuyển sang bố cục cố định;
  lần 3 Claude chấm 5/7/4, chọn VS và sửa; Claude còn phát hiện chữ nhỏ dính nhau do viền dày → giãn chữ + viền mỏng cho chữ nhỏ.
  Mũi tên bản đồ thêm `smooth: false` (đường La Mã phải thẳng).


### Bước 8 — đang làm (video trọn 10 phút "Hadrian's Wall", `projects/why-hadrians-wall`)
- Content 1.868 từ, 3 chương, 17 chuỗi, 140 cú máy; giọng OmniVoice của người dùng 580 s → canh 1.855 từ (192 từ/phút) → chia chương ở đầu câu.
- Chương 1 (182 s): plan_shots 12 phút; thiết kế 3 trang phục (hadrian_122ad, roman_auxiliary_122ad, briton_farmer_50ad, đều 8/10),
  `sets/hadrians_wall` 7/10, `props/{wall_stone 7, emperor_bust 8, writing_tablet 8}`; dựng `CAMERA OK` ngay lần đầu. Ảnh: `docs/img/hadrian_ch1.jpg`.
- Lỗi đã sửa:
  1. Hết lượt 5 giờ của gói giữa lúc thiết kế → job vẫn thử hết các món (món nào cũng lỗi). Giờ dừng ngay, báo rõ; plan_shots ghi
     `missing.json`, bấm "Duyệt & dựng" lại thì dùng lại story (nếu mới hơn content/words) và chỉ thiết kế đồ còn thiếu; "Dựng lại chương này" mới lập lại (`replan`).
  2. Một trang phục bị xếp hàng thiết kế hai lần (library_needs + vai) → bỏ qua tên đã thử.
  3. Grade đêm/hoàng hôn/bão làm đen kịt vùng tối: compositor chạy ở không gian tuyến tính, Bright −22 là trừ 0,29 mỗi điểm ảnh
     → bóng tối lấy từ màu nhân (gain), Bright/Contrast giữ nhỏ (thử trước bằng numpy trên ảnh ban ngày).
  4. Ánh trời nhuộm xanh mặt ngửa lặp lại ở tường và đá → `look.warm_top(m)` (nhân sắc ấm theo pháp tuyến Z), ghi vào AUTHORING.md.
- `tools/bpy_run.py` bỏ `--` thừa (trước đây `bpy_run.py thumbs.py -- props/x` làm thumbs.py render lại cả thư viện).
- Chương 2 (172 s): `sets/barrack_room` (vòng chấm cuối bị cắt do hết lượt, tôi tự xem), `props/{centurial_stone 8, care_package 7}`; camera tự sửa 1 vòng.
  Chương 3 (227 s): `props/{ladder 8, cornu_horn 8, coins 8}`, `chars/cow` 7; tự sửa 2 vòng (neo `arrow0_mid` thiếu, 8 cú bị che). Ảnh: `docs/img/hadrian_ch{1,2,3}.jpg`.
  Tổng Claude: lập story 3 × 12-15 phút, 17 món mới × 3-5 phút; chạm giới hạn 5 giờ của gói hai lần.
- Lỗi đã sửa (tiếp):
  5. Camera nằm trong tường / sau tường (framing chỉ tính khoảng cách): `check_line_of_sight` bắn tia camera → điểm nhìn giữa mỗi shot,
     bị che thì WARN cho vòng tự sửa; `clear_angle` thử góc ±35/±70 rồi góc cao trước khi báo (NOTE trong log). Chương 3: 6/8 tự hết.
  6. Cận cảnh con vật thấp (dê, bò) nhìn vào tường: preset tính theo đầu người 1,85 → `subject_scale` co khung + điểm nhìn theo chiều cao đầu thật.
  7. Tay cầm bút của `paper_diagram` to và đứng đè hình vẽ → cỡ 1,2, nghỉ lâu thì rời tờ giấy; nhãn đè nhau → `label_overlaps` trong kiểm tra plan.
  8. `tactical_board` thiếu neo `arrow<i>_mid` như bản đồ; `tools/thumbs.py` chụp mặt theo đầu thật (con vật thấp bị hụt).
  9. Thumbnail dùng grade tối (lính màu xanh đêm) → schema và `thumb_story` bỏ night/storm/dusk/cold.
- Gói YouTube (252 s): 10 tiêu đề (chọn "Why Hadrian's Wall Had a Gate Every Mile"), 17 mốc chương, 14 nguồn, 3 thumbnail (Claude chấm 5/7/4, chọn VS).
  Ảnh: `docs/img/hadrian_thumbs.jpg`.
- Render thử trong container: chương 1 khung 1-300, fast 25 %, âm thanh −14,0 LUFS, 6 đoạn nhạc theo mood. Bản 10 phút đầy đủ render trên máy người dùng.

## Nhân vật 3D (yêu cầu của người dùng: cả Shorts lẫn video dài)
- `core/body3d.py`, chạy sau khi dựng nhân vật + trang phục + miệng nói: mặt/áo nền phồng thành khối tròn đặc (độ sâu theo khoảng cách tới
  mép, hình tròn → cầu, chữ nhật → viên thuốc); mảnh trên đầu/thân uốn ôm theo bề mặt theo thứ tự lớp z (z nhỏ hơn nền → phía sau);
  tay/giày/đồ cầm tay thành khối riêng, mảnh nhỏ vẽ lên mảnh lớn cùng nhóm (hoa văn khiên) ôm theo mảnh lớn; mọi góc bo tròn 0,035;
  viền: ống tròn dọc mép + vỏ mực mỏng; đổ bóng 2 tông theo hướng sáng cố định trong không gian camera (ánh sáng thật cho bóng loang lổ).
  Khung xương, tư thế, biểu cảm, chớp mắt, nhép miệng giữ nguyên.
- `meta.char_style` "3d" (mặc định) | "2d"; biến môi trường `WHYSHORTS_CHAR_STYLE=2d` cho fingerprint: 3 Shorts cũ ở 2D vẫn giống hệt.
- Lỗi đã sửa khi làm: trục Z camera của Blender hướng ra xa (ánh sáng đặt ngược → mặt xám); mảnh trang phục nằm trong thân (thiếu lệch
  base_z); lớp sát nhau đâm xuyên (bước lớp 0,012); hoa văn khiên chìm trong khiên; ống viền dày trồi qua nét màu (ép dẹt ống 0,25);
  tính lại cảnh cho mỗi nét (chương 1: 1.026 s → 118 s cho 21 nhân vật).
- Phụ đề video dài: viền = ống tròn dọc mép chữ (bevel) đặt sau chữ trắng; hết gai ở góc chữ.
- Ảnh: `docs/img/char3d_compare.jpg`, `char3d_shorts.jpg`, `hadrian3d_ch{1,2,3}.jpg`.

## Video dài liền mạch, hình đẹp, render nhanh hơn
- Video dài là MỘT mạch kể: "phần" (chapters/NN) chỉ để dựng/render. `longform.stitch`: `meta.part_offset/part_first/part_last`,
  bỏ thẻ `chapter`, bỏ fade ở chỗ nối, phần sau mở bằng mood nhạc phần trước kết thúc; builder tạo nhạc/nền theo thời gian chung
  của cả video (cắt từ cùng một bản, không fade ở chỗ nối). Đo chỗ nối phần 1→2: −12..−16 dB liền, không hụt. YouTube: "Timestamps"
  theo tên nhịp kể, không tên chương. UI/server gọi là "phần".
- Hình: mây hoạt hình trong shader trời (`look.add_clouds`, video dài, `world.clouds`), mảng màu + vân cỏ cho mặt đất/đồi lớn
  (`look.ground_variation`, `Builder.dress_ground`), viền sáng (rim) trên nhân vật 3D. LONGFORM_RULES mục 10 + STYLE "Hình đẹp, không
  đơn điệu"; `variety_problems` trong kiểm tra plan (≥ 1 vfx / 45 s, ≥ 2 grade khi phần ≥ 2 phút).
- Render (đo khung 4646 chương 1, 50 %, CPU): gốc 69 s → phụ đề 4 mẫu 50 s → cảnh 16 mẫu 43,5 s (−37 %, PSNR ≥ 47 dB so với gốc).
  Không đáng: vignette làm mờ nhanh (68,6 dB nhưng chỉ −2 s), giảm bước bóng (không nhanh hơn). Compositor chạy GPU trên Windows
  (`WHYSHORTS_GPU_COMPOSITOR`). Chất lượng: fast 8 mẫu + on twos, normal 16, high 32.

## Bộ công cụ "dễ viral" (6 việc)
- Soát giữ chân người xem (`retention_review`, tab Content): chấm câu móc, chỉ chỗ dễ bỏ đi, nút Áp dụng sửa từng chỗ.
- Học từ số liệu thật (`analytics.py`, `learn_retention`): tải CSV "Tỷ lệ giữ chân" của YouTube Studio → chỗ tụt + câu/cảnh lúc đó →
  bài học vào `library/LESSONS.md`; mọi lần viết content/soát sau đều đọc.
- Phụ đề nhiều thứ tiếng (`translate_subs`, 15 ngôn ngữ → `youtube/subs/*.srt`) + kịch bản lồng tiếng.
- Nhạc thật theo mood: `library/music/<mood>/*.wav|ogg|mp3` thay nhạc tổng hợp (AUDIO in tên bài).
- Nhận diện kênh (`library/channel.json`, tab YouTube): watermark, màn hình kết (end screen) ở phần cuối video dài, nhân vật dẫn chuyện cố định.
- Shorts cắt từ video dài (`clips.py`, `pick_clips`, tab Render): Claude chọn 3-5 đoạn 25-60 s trong một phần → `clips/NN/` dựng lại
  khổ 9:16 (cùng cảnh 3D, camera đóng khung lại, wide/establishing ×0,55), phụ đề pop, chữ móc 2,5 s đầu, "FULL VIDEO ON THE CHANNEL"
  2 s cuối (không thẻ nào đè), âm thanh lấy đúng đoạn mix của video dài + fade. Thử: 5 Short Hadrian, xem trước `docs/img/hadrian_shorts.jpg`,
  render thử Short 3 (3 s, −14 LUFS, có tiếng).

## Nhân vật không đứng trong tường / sau tường
- `Builder.unstick` (camera video dài): mỗi đoạn blocking có tọa độ cố định → thử thân người (3 độ cao × 5 điểm) với khối bối cảnh
  (BVH lúc đó); lọt vào tường/sàn/giàn giáo thì dời tới chỗ trống gần nhất cùng mặt sàn (NOTE trong log).
- `unstick_crowd` (đám đông đứng yên): người lọt vào khối → dời (ưu tiên vào phía trong đám đông); người bị tường ngăn với tâm đám đông
  (thấy mỗi cái đầu ló qua tường) → bỏ. Phần 2 Hadrian: 4 nhân vật dời, builders/garrison bỏ 2-9 người sau tường.
- `clear_angle` cho cả chủ thể là điểm: bắn tia tới điểm nhìn + nhân vật/đám đông trong 8 m, ở đầu/giữa/cuối chuyển động máy; chọn góc ít bị
  chắn nhất, vẫn chắn thì WARN. Cú garrison bị cây che → tự xoay 65°. Ảnh: `docs/img/walls_fix.jpg`.
- Server: sau MAX_FIX vòng sửa mà chỉ còn WARN (cảnh dựng được) thì vẫn giao ảnh xem trước + liệt kê cảnh báo, không báo dựng hỏng.
- Bụi (`dust`) bám đất, cao ~ngang hông; nhãn đè đầu không dời được chỉ là NOTE.

## Trang không "đứng im" khi Claude làm lâu (Windows)
- Mỗi phút trong lúc gọi Claude: dòng "… Claude vẫn đang làm (N phút)" (lập story thường 10-15 phút, trước đây không in gì).
- Đồng hồ việc chạy trên trang giữa các lần hỏi; hỏi tiến độ có giới hạn 8 s, hỏng ≥ 4 lần liền thì báo "Studio không trả lời"
  kèm cách gỡ; việc không còn (studio khởi động lại) thì báo bấm chạy lại.
- Server tắt QuickEdit của cửa sổ dòng lệnh (bấm chuột vào cửa sổ đen làm đóng băng chương trình); lỗi ghi `logs/server_errors.log`,
  không in ra cửa sổ; tiến trình con (Claude) không dùng bàn phím của cửa sổ (stdin DEVNULL) và không có cửa sổ riêng.
- `claude --help` hỏi một lần chạy nền lúc mở studio, tối đa 20 s, lỗi thì nhớ 5 phút; trang trạng thái không bao giờ chờ nó.
  Đọc ống dẫn bằng luồng riêng + `taskkill /T` cả cây tiến trình khi quá giờ (`subprocess.run(timeout=)` trên Windows có thể chờ mãi khi
  tiến trình cháu giữ ống dẫn: người dùng gặp "Studio không trả lời" 4 phút, không có dòng báo mỗi phút). Hủy việc cũng diệt cả cây.
- Hộp đen: `logs/threads.log` (faulthandler, mỗi 60 s ghi stack mọi luồng, chạy cả khi Python bị kẹt); `/api/ping` để thử studio còn sống.
- Nguyên nhân thật (threads.log của người dùng chỉ có luồng chờ, không có việc nào): một studio CŨ bị kẹt vẫn giữ cổng 8765; trên Windows
  SO_REUSEADDR cho studio mới mở cùng cổng không lỗi, trình duyệt vẫn nói chuyện với studio cũ. Giờ `StudioServer` bind độc quyền
  (SO_EXCLUSIVEADDRUSE), lúc mở hỏi `/api/ping` trước: có studio khác thì in pid + `taskkill /F /PID …` rồi thoát; tab trình duyệt ghi pid/giờ mở.
- Nguyên nhân THẬT (threads.log ở cổng mới cũng không có việc nào, ping `jobs: 0`): việc kết thúc với LỖI ngay ở bước 1, nhưng hàm `api()` của trang
  coi phản hồi có trường `error` là yêu cầu hỏng → hỏi lại mãi, không hiện lỗi (đồng hồ "0 giây", rồi "Studio không trả lời"). Giờ hỏi tiến độ
  dùng `keepError` → hiện "❌ Lỗi" + nội dung. (Đổi cổng 1111 và giữ cổng độc quyền vẫn giữ lại, vô hại.)
