# Video dài YouTube 16:9 — mẫu kịch bản và bộ kiểu cảnh

Gửi kèm mỗi lần gọi Claude cho dự án `format: "long"` (viết content, viết lại đoạn, lên shot list). Phong cách nhân vật, bối cảnh, màu
vẫn theo `STYLE.md`; định dạng `story.json` theo `STORY.md`. Rút ra từ phân tích video mẫu ở `docs/LONGFORM.md` (chỉ học "ngữ pháp",
không chép nội dung, nhân vật hay khung hình của kênh khác).

## 1. Khung kịch bản (theo % thời lượng)

| Vị trí | Nhịp | Việc phải làm |
|---|---|---|
| 0–3 % (10–25 s) | **Mở giữa cao trào** | Thả người xem vào khoảnh khắc căng nhất hoặc vô lý nhất, ngôi "you" hoặc nhân vật dẫn dắt. Kết bằng một câu hỏi/điều bất thường ("But something is wrong."). |
| 3–5 % | **"Let's go back"** | Câu chuyển rõ ràng về điểm xuất phát ("Let's go back to this morning…"), kèm thẻ thời gian. |
| 5–15 % | **Gieo câu hỏi lớn** | Nói thẳng câu hỏi của tiêu đề bằng lời; vì sao nó lạ; hứa sẽ trả lời. Giới thiệu nhân vật dẫn dắt và thế giới (năm, nơi chốn → màn hình chữ, bản đồ). |
| 15–70 % | **Leo thang theo nhịp** | Mỗi 45–70 giây một **cú mới**: tiết lộ, đảo chiều, con số bất ngờ, thất bại lớn hơn. Mỗi cú mở bằng câu móc ("But here's the problem…", "And then it gets worse.") và kết bằng một câu ngắn treo lơ lửng. Cuối mỗi chương là một cú treo (cliffhanger). |
| 70–85 % | **Giải thích chính** | Trả lời câu hỏi bằng cơ chế nhìn thấy được: sơ đồ, bàn chiến thuật, mặt cắt, so sánh ✓/✗. Một ý mỗi câu. |
| 85–97 % | **Mở rộng** | Hệ quả: ngày nay còn thấy ở đâu, ai học theo, con số tổng kết. |
| 97–100 % | **Gọi lại tiêu đề** | Câu chốt lặp lại gần nguyên văn tiêu đề/câu hỏi, có cú lật nhỏ hoặc tag hài; mờ về đen. |

Chương: 2–4 phút, mỗi chương 3–6 nhịp kể (sequence 20–60 s). Tiêu đề chương ngắn (2–5 chữ), hiện trên thẻ chương.

## 2. Lời đọc
- Tiếng Anh Mỹ, câu ngắn (trung bình 9–14 từ), hiện tại đơn; ngôi "you" khi kể trải nghiệm ("You're a young soldier…"), hoặc ngôi ba với
  một nhân vật dẫn dắt xuyên suốt. Mỗi câu một ý; tránh liệt kê dài.
- Con số cụ thể, tên riêng, năm: mỗi cái là một cơ hội cho màn hình chữ/bản đồ.
- Hài thưa hơn Shorts: một câu tỉnh bơ hoặc gag hình mỗi 30–60 s, không phá nhịp căng.
- Không bịa: con số, năm, trích dẫn phải có nguồn (ghi trong `sources`); không chắc thì nói "about", "historians think".

## 3. Lời → kiểu cảnh (chọn theo từng câu)

| Câu lời đọc nói về… | Kiểu cảnh |
|---|---|
| năm, ngày, tên trận/sự kiện, con số lớn, câu hỏi then chốt, câu nói nổi tiếng, tên nhân vật lịch sử | **card** (màn hình chữ) |
| địa danh, hành quân, biên giới, "from X to Y" | **map** |
| đội hình, chiến thuật, "from above", vị trí các bên | **board** (bàn chiến thuật nhìn từ trên) |
| cơ chế, vì sao, so sánh kích thước/lực, "here's how it works" | **diagram** (hoặc mặt cắt) |
| cảm xúc, quyết định, phản ứng, câu thoại | **closeup** / **ecu** |
| hai người nói chuyện, hành động tay | **medium** |
| cả người hành động, đi, ngã | **full** |
| quy mô: đám đông, quân đội, thành phố, "everyone" | **wide** / **establishing** |
| một vật cụ thể (nắp, thư, đồng xu, vũ khí) | **insert** |
| trong nhà, lều, văn phòng | **interior** |
| "you see…", trải nghiệm ngôi thứ hai | **pov** |
| thời đại/nơi mới | establishing + màn hình chữ năm hoặc địa danh + bảng màu mới |

## 4. Nhịp hình
- Khoảng **12–16 cắt/phút** (video mẫu ~14); phần lớn cú máy 1,5–4 s; cứ 1–2 phút có một cú máy dài 8–25 s (toàn cảnh hé lộ, sơ đồ giải thích).
- Trong mỗi cú máy camera luôn chuyển động chậm (đẩy vào, kéo ra, lia, trượt ngang, nâng/hạ cần, vòng cung nhỏ). Hai cú liền nhau
  không cùng kiểu cảnh và cùng chuyển động; xen kẽ toàn – trung – cận – cận vật.
- Cắt theo câu: cắt ở đầu câu hoặc ở chữ nhấn, không cắt giữa một từ.
- Màn hình chữ: khoảng **1 cái mỗi 45–90 s**, ở mốc quan trọng, đổi kiểu (year, number, question, quote, name, place, fact); không dùng
  cho chữ đã có trong phụ đề cùng lúc nếu chỉ lặp lại y nguyên.
- Bản đồ/bàn chiến thuật/sơ đồ: dùng khi lời nói về chúng; mỗi lần 4–15 s, có chuyển động (mũi tên vẽ dần, đơn vị trượt, camera đẩy).

## 5. Viết shot trong `story.json` (rig `long`)
Ưu tiên **`frame`** (khung đặt sẵn) thay vì tự tính `keys`; tool tự đặt máy đúng khoảng cách nên không cắt đầu nhân vật:

```json
{"a": 301, "b": 372, "type": "closeup", "fstop": 2.0,
 "frame": {"subject": "joe", "move": "push_in", "angle": 20, "height": "low", "x": -0.3}}
```
- `subject`: id nhân vật, `"<id bối cảnh>.<anchor>"`, tên vật thể, hoặc `[x, y, z]` (điểm trên mặt đất / tâm vật). Vị trí lấy ở
  **khung giữa** cú máy (đã tính chuyển động của tracks/blocking); vật đang ẩn hoặc bay nhanh thì ghi thẳng `[x, y, z]`.
- `type`: `ecu closeup medium full wide establishing insert` (board/map → nhìn thẳng xuống, diagram → như full, card → như medium).
- `angle` (độ quanh chủ thể, 0 = trước mặt), `height` (`eye` hơi thấp, `low`, `high`, `top`), `x`/`y` (vị trí chủ thể trong khung,
  -0,33 = một phần ba trái), `size` (chiều cao khung, ghi đè), `lens`, `move` (`push_in pull_out pan_left pan_right truck_left truck_right
  crane_up crane_down orbit_left orbit_right drift`), `amount` (0–2), `roll`.
- Chỉ dùng `keys` khi cần đường máy đặc biệt (bám theo vật rơi, nhiều điểm).
- Độ sâu trường ảnh: `camera.dof.fstop` 2,8; cận 1,8–2,2; toàn cảnh 4–5,6.

Màn hình chữ ở mốc quan trọng (`cards`, style `screen`, nền tối trong suốt, cảnh mờ phía sau):
```json
{"style": "screen", "variant": "year",     "sub": "THE YEAR IS", "text": "340 BC", "caption": "Latium, central Italy", "from": 400, "to": 470}
{"style": "screen", "variant": "number",   "text": "500", "caption": "square covers ordered", "from": 1440, "to": 1500}
{"style": "screen", "variant": "question", "text": "WHY ARE MANHOLE COVERS ROUND?", "from": 548, "to": 610}
{"style": "screen", "variant": "quote",    "text": "Squares are the future!", "caption": "— Gary, budget manager", "from": 900, "to": 960}
{"style": "screen", "variant": "name",     "text": "PUBLIUS DECIUS MUS", "caption": "Roman consul", "from": 1200, "to": 1260}
```
Dài 45–90 khung; cú máy bên dưới vẫn trôi (thường type `card` hoặc một cảnh mờ fstop thấp). Thẻ `title`/`label`/dấu ✗✓ vẫn dùng cho nhãn
nhỏ. Mở chương bằng `chapter` + `fade`; kết video bằng `fade` có `hold`.

## 6. Nhiều quốc gia, phe, thời kỳ
- Liệt kê trong `factions` (content) với văn hóa + thời kỳ, trang phục, màu, vũ khí đúng sử liệu; nói rõ chương nào có phe nào.
- Hai phe giống nhau phải phân biệt được bằng màu, khiên, cờ. Không biếm họa sắc tộc; phe "địch" không bị vẽ xấu hơn.
