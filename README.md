# WhyShorts Studio

Tool làm video hoạt hình dọc "Why…" bằng Blender trên Windows. Claude (qua Claude CLI, gói Pro/Max) lo phần nghĩ: ý tưởng, lời đọc, phân cảnh, thiết kế đạo cụ/bối cảnh/nhân vật mới. Tool lo phần làm: dựng cảnh, canh chữ theo giọng, âm thanh, render.

## Cần có
- Windows, Blender 5.2 ở `C:\Program Files\Blender Foundation\Blender 5.2\`, card NVIDIA.
- Claude Code (lệnh `claude`) đã đăng nhập gói Pro/Max.
- Tùy chọn: ffmpeg (`winget install ffmpeg`) để ghép đoạn render lại vào video đầy đủ.

## Mở tool
Bấm đúp `start_studio.bat` rồi mở http://127.0.0.1:1111 nếu trình duyệt không tự mở. Giữ cửa sổ đen mở trong lúc dùng.

## Làm một video
1. **Ý tưởng**: nhập chủ đề → "Gợi ý ý tưởng" → chọn 1 ý.
2. **Content**: chọn số phút → "Viết content" → sửa từng chuỗi, "Viết lại đoạn này" → Lưu.
3. **Giọng đọc**: sao chép lời đọc cho phần mềm giọng → tạo giọng → tải .wav lên.
4. **Duyệt & dựng**: chờ Claude dựng cảnh và thiết kế đồ còn thiếu → xem ảnh → "Nhờ Claude sửa" nếu thấy lỗi.
5. **Render**: chọn chất lượng (Nhanh = "on twos", khoảng 1/3 thời gian; Chuẩn; Cao) → Render → xem hoặc tải mp4.
   Bấm "Đo tốc độ máy" một lần để ước tính đúng thời gian. Bị ngắt (tắt máy, bấm Hủy) thì bấm Render lại: tool làm tiếp từ khung đang dở.

### Video dài YouTube 16:9
Bấm "+ Dự án mới" rồi chọn **OK = video dài** (hoặc đổi "Khổ video" ở bước 2). Các bước giống hệt Shorts, khác ở chỗ:
- Content chia **chương**; mỗi nhịp kể có danh sách cú máy (cận, toàn, bản đồ, sơ đồ, màn hình chữ…) sửa được.
- Tải giọng lên thì tool tự cắt giọng theo chương (`chapters/01`, `02`…).
- "Duyệt & dựng" dựng lần lượt từng chương; mỗi chương có ảnh xem trước, nút dựng lại và ô "Nhờ Claude sửa" chọn chương.
- Render lần lượt các chương chưa có video rồi ghép thành `out.mp4` (cần ffmpeg). Bị ngắt giữa chừng thì bấm Render lại để làm tiếp.

### Đối thoại hài (cặp đôi, vợ chồng, gia đình) 9:16
Bấm "+ Dự án mới" rồi gõ **3** (hoặc chọn "Đối thoại hài" ở ô Khổ video, bước 2). Ô "Nhân vật" ở bước 2 chọn 3D, 2D có màu, hoặc **2D xám** (bối cảnh có màu, người xám, mắt tròn trắng) cho từng video.
1. **Ý tưởng**: nhập chủ đề hài (hoặc để trống) → "Gợi ý ý tưởng" → chọn ý (có câu chữ trên đầu video, cú đảo, câu chốt).
2. **Content**: chọn số phút (0,5–3) → "Viết content". Claude viết lời thoại tiếng Anh + bản dịch, nhân vật (tóc, áo, màu, giọng) và cho từng câu:
   mặt người nói, mặt người nghe, cử chỉ, máy quay, khoảng nghỉ, tốc độ, tiếng động. Sửa thẳng trên trang, ▲▼ đổi thứ tự, đánh dấu ☑
   vài câu rồi "Viết lại câu đã chọn" → Lưu.
   **Tự viết kịch bản**: dán vào ô "Tự viết kịch bản" (mỗi câu một dòng `Tên: lời thoại`, ghi chú trong ngoặc như `(angry)`, `*laughs*`,
   `(nhún vai)`, `(long pause)`) → "Nhận diện ngay" (không tốn lượt Claude) hoặc "Nhận diện + Claude thêm diễn xuất" (giữ nguyên từng chữ,
   thêm mặt/cử chỉ/nhịp/bản dịch; viết tiếng Việt thì Claude dịch sang tiếng Anh Mỹ) hoặc "Dịch & làm hay hơn" (Claude gọt câu cho hài
   kiểu Mỹ, giữ nhân vật, tình huống và cú chốt). Dòng đầu trong ngoặc kép là tiêu đề, "Bối cảnh: …" là mô tả cảnh (chưa có thì Claude
   thiết kế), câu chỉ có hành động như "Jake: (nhìn chằm chằm)" thành một nhịp im lặng. Không cần bước Ý tưởng.
   **Đồ vật và đi lại**: mỗi câu có ô "Hành động" (lấy đồ ra, giơ cho xem, uống/ăn/xem điện thoại, đưa cho người kia, cất đi, bước tới,
   đi vào cảnh, nói xong bỏ đi) + "Đồ vật" (điện thoại, cà phê, khoai tây chiên, hoa, hộp quà… 21 món) + "Tới chỗ" (partner = lại gần,
   away = lùi ra, hoặc tên chỗ đứng của bối cảnh). Ô "Cầm sẵn từ đầu" ở thẻ nhân vật. Kịch bản tự viết nhận ra ghi chú kiểu
   `(uống cà phê)`, `(đưa điện thoại cho Emily)`, `(bỏ đi)`, `(bước lại gần)`, `*sips coffee*`, `(walks off)`.
   **Thẻ cảm xúc OmniVoice** (`[laughter]`, `[sigh]`, `[surprise-wa]`, `[question-ah]`, `[dissatisfaction-hnn]`… 13 thẻ, rê chuột vào
   nhãn câu thoại để xem): Claude tự đặt khoảng 1 thẻ mỗi 2-3 câu; kịch bản có sẵn thì bấm "😮 Thêm thẻ cảm xúc" rồi tạo lại giọng.
   **Ngồi / nằm**: ô "Tư thế lúc đầu" ở thẻ nhân vật (đứng / ngồi / nằm) và hành động "ngồi xuống / nằm xuống / đứng dậy" ở từng câu.
   Bối cảnh không có ghế/giường thì tool tự đặt ghế, sofa hoặc giường; ở bãi đỗ xe có chỗ ngồi trên capo (`car_hood`).
   **Đi làm việc rồi quay về**: hành động "đi tắt đèn / đi bật đèn rồi quay về" (đèn tắt thật, phòng tối; xong về giường nằm lại)
   và "đi tới chỗ… rồi quay về" (ghi chỗ ở ô "Tới chỗ"). Kịch bản tự viết: ghi `(đi tắt đèn)`, `(bật điện)`.
   **Claude tự dàn dựng**: khi bấm Duyệt & dựng, Claude đọc kịch bản và tự quyết định ai làm gì với đồ vật nào (dậy tắt đèn, mở tủ lạnh,
   bật TV, đưa đồ, về giường nằm…); đồ vật chưa có thì Claude vẽ thêm. Nút "🎬 Claude dàn dựng" để làm lại hoặc kèm yêu cầu riêng.
3. **Giọng đọc** (OmniVoice, cài một lần bằng `tools\install_omnivoice.bat`, cần card NVIDIA):
   "Tạo giọng thử" → nghe 3 giọng của mỗi nhân vật → **Chọn** (hoặc tải giọng thật của bạn 3-10 giây) → "Tạo giọng các câu & ghép".
   Câu nào chưa hay: ↻ đọc lại, hoặc tải bản tự thu của câu đó. Sửa chữ một câu thì chỉ câu đó được đọc lại.
   Giọng lưu ở `library/voices/`, video sau dùng lại được (nhân vật quen của kênh).
4. **Duyệt & dựng**: tool tự lập cảnh trong vài giây (không tốn lượt Claude): máy quay cắt giữa hai người / cận người nói / cận người nghe
   phản ứng / cận hai mặt ở câu chốt, mặt + miệng + cử chỉ theo từng câu, phụ đề (tiêu đề gợi ý ở bước 2 thì tự thêm khi chỉnh sửa video). Muốn đổi máy quay một câu thì sửa
   ô "Máy quay" của câu đó rồi dựng lại.
5. **Render** như Shorts.

Tab **YouTube**: "Tạo gói YouTube" → 10 tiêu đề, mô tả có mốc chương thật và nguồn, tag, bình luận ghim; video dài có thêm 3 thumbnail
1280x720 dựng từ chính nhân vật của video (Claude tự chấm và chọn). Bấm "Chép"/"Sao chép" rồi dán vào YouTube Studio.

Tab **Thư viện**: duyệt đồ Claude vừa thiết kế, gõ góp ý ("to hơn", "đổi màu"), hoặc nhờ thiết kế đồ mới.

## Cập nhật
```
git pull
```
Nếu báo xung đột file `thumb.png`: `git restore "library/**/thumb.png"` rồi pull lại.

## Tài liệu
- `CLAUDE.md`: thiết kế và tiến độ dự án.
- `STYLE.md`: luật phong cách gửi kèm mỗi lần gọi Claude.
- `STORY.md`: định dạng `story.json`.
- `library/AUTHORING.md`: cách viết đồ thư viện.
- `skill/blender-why-shorts/`: skill cho Claude (v4: dùng tool). Tải `skill/blender-why-shorts.zip` lên claude.ai để thay skill cũ.

## Dọn dẹp
Tab **5 Render** → khung "Dọn dẹp":
- **Dọn ảnh tạm**: xóa ảnh render tạm (`frames/`, `parts/`, ảnh dựng thumbnail) — video 10 phút có thể chiếm vài chục GB.
  Giữ story, giọng đọc, ảnh xem trước, video mp4 và gói YouTube.
- **Xóa dự án**: gõ đúng tên dự án để xác nhận; video mp4, gói YouTube, content và giọng đọc được chép ra
  `%USERPROFILE%\Videos\WhyShorts\<tên>` trước khi xóa (đổi chỗ bằng biến `WHYSHORTS_EXPORT`). Thư viện không bị xóa.
- Dự án mẫu có trên GitHub mà đã xóa: nếu `git pull` báo xung đột thì `git restore projects/<tên>` rồi pull lại.
