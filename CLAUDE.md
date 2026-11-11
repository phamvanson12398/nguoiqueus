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
  - Chỉ dùng thư viện chuẩn; Windows mở bằng `start_studio.bat` (Python đi kèm Blender), địa chỉ http://127.0.0.1:8765.
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
