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
- **Chọn số phút** (ô số, bước 0,5). Hiện ngay: số từ lời đọc dự kiến (~150 từ/phút giọng AI), số chuỗi máy, **thời gian render ước tính** (~1,4 giây/khung × 30 khung/giây).
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
