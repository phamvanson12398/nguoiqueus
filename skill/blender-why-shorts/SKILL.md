---
name: "blender-why-shorts"
description: "Làm video hoạt hình 'Why…' bằng tool WhyShorts Studio trên máy người dùng: Shorts dọc hài kiểu US (45-75 s) hoặc video lịch sử dài 16:9 (10-20 phút, kiểu Squire Explains: chương, bản đồ, sa bàn, màn hình chữ, nhiều phe với trang phục theo văn hóa, nhạc + tiếng động + hiệu ứng). Nhân vật 2D trong bối cảnh 3D, dựng và render bằng Blender. Dùng khi người dùng muốn làm video 'Why…', sửa video đang làm, thêm đồ/văn hóa/trang phục vào thư viện, làm gói YouTube, hoặc gặp lỗi với tool."
---

# Shorts "Why…" bằng WhyShorts Studio (v4: dùng tool)

Video dọc 1080x1920, 30 fps, mặc định 45-75 giây (tối đa 10 phút). Một câu hỏi "Why…" được kể thành chuyện ngắn có xung đột; cú twist cuối chính là lời giải thích. Nhân vật 2D phẳng đứng trong bối cảnh 3D, camera trôi liên tục, phụ đề nảy từng chữ, mọi hành động đều có tiếng động.

**Không viết tay script Blender nữa.** Tool đã làm hết phần tay chân:

| Việc | Ai làm |
|---|---|
| Ý tưởng, content, phân cảnh theo khung hình, thiết kế đạo cụ/bối cảnh/nhân vật mới, sửa theo ảnh xem trước | Claude, qua `claude -p` do tool gọi (`claude_bridge.py`) |
| Lưu trữ, dựng cảnh từ `story.json` + thư viện, canh chữ, âm thanh, render | Tool (`server.py`, `builder.py`, `core/`) |
| Chọn ý, sửa content, làm giọng đọc, duyệt đồ mới, xem video | Người dùng |

Việc của Claude trong cuộc trò chuyện là: hướng dẫn hoặc tự điều khiển tool, đọc ảnh xem trước để tìm lỗi, sửa `story.json`/thư viện khi tool không tự sửa được, và chẩn đoán lỗi. Luật phong cách (ý tưởng, nhịp hài, camera v3, âm thanh, thiết kế) nằm ở **`STYLE.md` trong thư mục tool**: đó là nguồn duy nhất, đọc nó thay vì nhớ.

## Tool nằm ở đâu
- Máy người dùng: Windows, Blender 5.2.3, card NVIDIA, Claude CLI đăng nhập gói Pro/Max.
- Thư mục tool: bản clone của repo `phamvanson12398/nguoiqueus` (nhánh `claude/pensive-newton-618vli`), ví dụ `C:\Users\<user>\Downloads\tool_nguoique\nguoiqueus`. Hỏi người dùng nếu không chắc.
- Mở tool: bấm đúp `start_studio.bat` (chạy `server.py` bằng Python đi kèm Blender), trang ở http://127.0.0.1:8765. Giữ cửa sổ đen mở.
- Tài liệu trong thư mục tool: `CLAUDE.md` (thiết kế + tiến độ), `STYLE.md` (luật phong cách), `STORY.md` (định dạng `story.json`), `library/AUTHORING.md` (viết đồ thư viện).

## Cập nhật tool
```
git pull
```
Nếu git báo xung đột:
- `library/**/thumb.png` (ảnh thu nhỏ render lại trên máy): `git restore "library/**/thumb.png"` rồi pull lại.
- File trong `projects/<slug>/` (người dùng đã tải giọng/sửa content trên máy, trong khi bản đó cũng có trên GitHub): sao lưu thư mục (`Copy-Item -Recurse projects\<slug> projects\<slug>-cu`), `git restore projects/<slug>`, xóa các file chưa theo dõi bị báo trùng, rồi pull.
Sau khi pull: tắt cửa sổ đen, mở lại `start_studio.bat`, tải lại trang bằng Ctrl+F5.

## Quy trình làm một video (5 bước trên trang)
| Bước | Người dùng bấm | Tool/Claude làm | Thời gian (đo thật) |
|---|---|---|---|
| 1. Ý tưởng | nhập chủ đề → "Gợi ý ý tưởng", chọn 1 ý (hoặc "Dùng chủ đề này") | Claude đào 25-30 ứng viên, chấm 5 tiêu chí, trả 10 ý ≥ 8/10, có tra web | khoảng 3 phút |
| 2. Content | chọn số phút → "Viết content"; sửa thẻ chuỗi, "Viết lại đoạn này", Lưu | lời đọc EN + bản dịch VI + bảng chuỗi máy + nguồn + danh sách đồ cần thiết kế | khoảng 3 phút; viết lại 1 chuỗi khoảng 40 s |
| 3. Giọng đọc | sao chép "bản cho phần mềm giọng" ([beat] đã đổi), tự làm giọng (OmniVoice, ElevenLabs…), tải .wav lên | đổi wav float/24-bit sang PCM 16-bit, canh từng chữ theo khoảng lặng (sai số khoảng 0,3 s) | vài giây |
| 4. Duyệt & dựng | bấm "Duyệt & dựng"; xem ảnh; gõ lỗi vào "Nhờ Claude sửa" | Claude viết `story.json` (camera v3) → thiết kế đồ thiếu (tự render, tự xem, sửa ≤ 2 vòng) → dựng trong Blender, kiểm `CAMERA OK` (tự sửa ≤ 2 vòng) → 10 ảnh xem trước 35 % | 1,5 phút video: 12 phút story + 3-5 phút/món mới + 2-3 phút dựng |
| 5. Render | 100 % → Render; xem/tải mp4 | thanh tiến độ, ffprobe | khoảng 1,4 s/khung trên GPU (1 phút video ≈ 42 phút) |
| Thư viện | duyệt đồ nháp hoặc gõ góp ý ("to hơn, đổi màu"); thiết kế đồ mới | Claude sửa theo góp ý, render lại, tự xem | 2-4 phút/món |

Sửa một chuỗi sau khi đã render: sửa `story.json` hoặc "Nhờ Claude sửa" → tab Render nhập khung `A-B` của chuỗi đó → nút **"Ghép vào video đầy đủ"** (cần ffmpeg: `winget install ffmpeg`). Bản cũ giữ ở `*_before.mp4`.

## Video dài 16:9 (chọn "Khổ video: 16:9 dài" ở bước 2)
Luật riêng của video dài nằm ở `LONGFORM_RULES.md` (khung kịch bản theo % thời lượng, nhịp 12-16 cắt/phút, màn hình chữ ≥ 1 mỗi 90 s,
bảng lời → kiểu cảnh, âm thanh, hiệu ứng); định dạng ở `STORY.md`; trang phục ở `library/OUTFITS.md`. Khác với Shorts:
| Bước | Khác gì |
|---|---|
| 2. Content | `write_content_long`: chương → nhịp (beat) → cú máy dự kiến; khai báo phe (`factions`: văn hóa, màu). 10 phút ≈ 1.900 từ, ~140 cú máy, 4-6 phút Claude. Tool kiểm nhịp cắt, màn hình chữ, số kiểu cảnh. |
| 3. Giọng đọc | Tải một file wav cho cả video; tool canh chữ (tìm theo dải, vài giây cho 2.000 từ) rồi **chia chương** ở đầu câu vào `projects/<slug>/chapters/NN/` (mỗi chương là một dự án con có story riêng). |
| 4. Duyệt & dựng | Làm lần lượt từng chương: plan_shots (camera rig `long`, shot `frame` đặt máy theo chủ thể) → văn hóa mới (tra web, có nguồn) → trang phục từng vai (xem ảnh xếp hàng + bóng đen, chấm sử liệu) → đồ mới → dựng, `CAMERA OK`. Bấm lại thì **làm tiếp** từ chỗ dở (story đã lập được dùng lại, chỉ thiết kế đồ còn thiếu); "Dựng lại chương này" mới lập story lại. |
| 5. Render | Chọn chất lượng: fast (on twos, 12 mẫu, ~30 % thời gian, để duyệt), normal, high. Render chuỗi ảnh PNG từng chương rồi ghép; tắt giữa chừng bấm lại là render tiếp. Bấm **"Đo tốc độ máy"** một lần để ước tính đúng. |
| 6. YouTube | Claude viết 8-12 tiêu đề, mô tả có mốc chương (tool tính từ giọng thật), nguồn, tag, bình luận ghim; tool render 3 thumbnail bằng nhân vật/bối cảnh của video, Claude chấm và sửa cái tốt nhất. |
- Lượt Claude: video 10 phút tốn nhiều lượt (mỗi chương ~12 phút lập story + 3-10 món mới × 3-5 phút); đo thật ở video Tường Hadrian:
  chạm giới hạn 5 giờ của gói hai lần. Dựng từng chương ("Dựng chương này"), rải qua nhiều khung 5 giờ; hết lượt thì bấm lại sau giờ mở.
- Bản đồ (`parchment_map`, bờ biển thật), sa bàn (`tactical_board`) và giấy sơ đồ (`paper_diagram`) dựng từ dữ liệu trong story, không thiết kế lại mỗi video.
- Đám đông (`crowds`) nhân bản vài lính mẫu theo đội hình; nhân vật `type: person` mặc trang phục theo `faction` + `role`.
- Âm thanh tự trộn ra −14 LUFS, đỉnh thật ≤ −1 dB (`mix.wav`); nhạc/tiếng động/nền tự tổng hợp, file CC0 trong `library/music|sfx/` được ưu tiên.

## Khi Claude tự điều khiển tool
- Có quyền dùng máy người dùng (computer use): đọc skill `computer-use` trước. Mở `start_studio.bat` (Explorer → thư mục tool → bấm đúp), rồi thao tác trên trang như bảng trên. **Không gõ phím vào cửa sổ Blender** (bộ gõ Unikey làm sai chữ); tool luôn chạy Blender bằng dòng lệnh nên không cần mở Blender.
- Có thể chạy thẳng bằng dòng lệnh trong thư mục tool:
  ```
  python claude_bridge.py design_prop <ten> "<mô tả>" --dim 3d      (hoặc design_set, design_char, --feedback "…", approve props/<ten>, usage)
  blender -b -P builder.py -- projects/<slug>/story.json --check
  blender -b -P builder.py -- projects/<slug>/story.json --preview 75,300,620 --pct 35
  blender -b -P builder.py -- projects/<slug>/story.json --render [--frames A-B] [--pct 50]
  python tools/splice.py projects/<slug>/<out>.mp4 projects/<slug>/parts/<out>_AAAA-BBBB.mp4
  ```
- Lấy ảnh xem trước (`projects/<slug>/preview/p_XXXX.png`) hoặc mp4 về để xem, sửa file rồi đưa lại máy: dùng công cụ chuyển file của môi trường, và **kiểm tra lại kích thước/thời gian file sau khi chép** (lệnh chép có thể báo thành công mà vẫn giữ bản cũ).
- Theo dõi việc dài (dựng, render) bằng log trên trang hoặc file mp4 lớn dần; đợi bằng lệnh chạy nền thay vì chụp màn hình liên tục.

## Xem ảnh xem trước: danh sách kiểm tra
Với mỗi ảnh (bấm để phóng to), kiểm tra:
1. Nhân vật không bị cắt mất đầu/tay ở chỗ quan trọng; mặt nằm trên vùng phụ đề trong cảnh cận.
2. Phụ đề không che miệng; thẻ chữ (`cards`) không tràn khung, không trùng chữ với phụ đề cùng lúc, không che hành động chính.
3. Đạo cụ đúng lúc: cầm tay là 2D, rơi/lăn là 3D, đổi đúng khung hành động; không lơ lửng hay xuyên vào nhân vật khác.
4. Mỗi va chạm có tiếng + bụi + rung + biểu cảm; mỗi chữ nhấn có punch-in, phản ứng hoặc động tác.
5. Màu: mặt ngửa lên (sàn, mặt bàn, lát bánh) không bị xám xanh/ô liu (ánh trời xanh nhuộm; xem AUTHORING.md).
6. Khung ngay sau mỗi lần chuyển chuỗi: lia (whip) có hướng nhất quán, không lộ khoảng trống ngoài bối cảnh.
Gõ lỗi vào "Nhờ Claude sửa" kèm số khung ("khung 886: …"); tool gửi ảnh + story cho Claude và trả patch nhỏ nhất.

## Sửa tay `story.json` (khi cần)
- Định dạng đầy đủ: `STORY.md`; kiểm tra nhanh: `python storycheck.py projects/<slug>/story.json` (không cần Blender).
- Số khung = giây × 30 + 1. Camera v3: seq ≥ 90 khung, khóa cách nhau ≥ 20 khung, `CAMERA OK` bắt buộc.
- Giá trị có thể là biểu thức (`"lerp(0.25, 2.0, pease(f, 171, 6))"`); chỉ dùng tên trong danh sách của STORY.md.
- Tên object: id của đồ; phần con là `<id>_<phần>` (xem `parts` trong `meta.json` của đồ).
- `cards.size` là chiều cao chữ (0,03-0,3), không phải hệ số nhân.
- Lịch sử mọi bản `story.json`/`content.json` nằm trong `projects/<slug>/history/`; khôi phục được trên trang.

## Thư viện
- `library/sets|props/<tên>/build.py + meta.json + thumb.png`, `library/chars/<tên>/char.json`, `library/motions/*.json`.
- Đồ do Claude thiết kế có `status: draft` cho tới khi người dùng duyệt. Góp ý cụ thể và đúng nguyên nhân sẽ sửa nhanh hơn (ví dụ "màu xám do ánh trời, dùng màu ấm đậm hoặc flat()").
- Viết đồ mới bằng tay: theo `library/AUTHORING.md` (khối cơ bản `rbox/cyl/lathe/extrude/text3d…`, vật liệu theo tên, gốc ở tâm đáy, chỉ import math/random/bpy/bmesh/mathutils/core). Nhân vật: `cfg.shoe` đổi giày, extras `on: torso|head|footL|footR`.
- Model CC0 .glb (Kenney, Quaternius, Poly Haven): `geo.import_glb(path, name, size=…)` trong `build.py`, đặt file .glb trong thư mục đồ.

## Lỗi hay gặp
| Triệu chứng | Nguyên nhân và cách xử lý |
|---|---|
| Thanh vàng "ANTHROPIC_API_KEY" | CLI sẽ tính phí API. Tool tự bỏ biến khi gọi; muốn giữ thì đặt `WHYSHORTS_KEEP_API_KEY=1`. |
| "Không thấy Blender" | Đặt `WHYSHORTS_BLENDER=<đường dẫn blender.exe>` rồi chạy `start_studio.bat` trong cùng cửa sổ. |
| Tải giọng lên báo lỗi | Chỉ nhận .wav (không mp3/m4a). Wav float/24-bit tự được chuyển. |
| Phần mềm giọng đọc chữ "beat" | Dùng ô "bản cho phần mềm giọng" ở tab Giọng đọc (đổi [beat] thành `...`/xuống dòng/SSML). |
| Phụ đề lệch giọng | Canh lại ở tab Giọng đọc; nếu content đã sửa sau khi làm giọng, phải làm lại giọng. |
| `CAMERA NEEDS FIX` | Tool tự gửi Claude sửa 2 lần; nếu vẫn lỗi: giãn khóa camera, seq ≥ 90 khung. |
| Thiết kế đồ "chưa xong" | Xem log; thiết kế lại ở tab Thư viện (thêm góp ý), rồi "Chỉ render lại xem trước". |
| Render chậm hơn 2 s/khung | Khung đầu luôn chậm (biên dịch shader khoảng 40 s); nếu vẫn chậm, kiểm tra đang dùng GPU NVIDIA trong Blender. |
| Video dài: "Hết lượt Claude của gói" khi đang dựng | Đợi lượt mở lại (giờ trong thông báo), bấm "Duyệt & dựng" lần nữa: tool làm tiếp, không lập story lại. |
| Video dài: bóng đen hai phe giống nhau / sai sử liệu | Tab Thư viện → trang phục → góp ý ("khiên bầu dục phẳng, không mào"), Claude sửa và xếp hàng lại. |
| Lượt dùng | `python claude_bridge.py usage` hoặc góc trên phải của trang; chi tiết từng lần gọi ở `logs/`. |

## Giao kết quả
Gửi mp4 (hoặc vài khung xem trước) kèm 1-2 câu: đã làm gì, render bao lâu, file nằm ở đâu (`projects/<slug>/<output>.mp4`), và bước tiếp theo. Nói rõ phụ đề canh bằng dạng sóng (có thể lệch khoảng 0,3 s) và các đồ mới còn đang là nháp.
