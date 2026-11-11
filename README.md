# WhyShorts Studio

Tool làm video hoạt hình dọc "Why…" bằng Blender trên Windows. Claude (qua Claude CLI, gói Pro/Max) lo phần nghĩ: ý tưởng, lời đọc, phân cảnh, thiết kế đạo cụ/bối cảnh/nhân vật mới. Tool lo phần làm: dựng cảnh, canh chữ theo giọng, âm thanh, render.

## Cần có
- Windows, Blender 5.2 ở `C:\Program Files\Blender Foundation\Blender 5.2\`, card NVIDIA.
- Claude Code (lệnh `claude`) đã đăng nhập gói Pro/Max.
- Tùy chọn: ffmpeg (`winget install ffmpeg`) để ghép đoạn render lại vào video đầy đủ.

## Mở tool
Bấm đúp `start_studio.bat` rồi mở http://127.0.0.1:8765 nếu trình duyệt không tự mở. Giữ cửa sổ đen mở trong lúc dùng.

## Làm một video
1. **Ý tưởng**: nhập chủ đề → "Gợi ý ý tưởng" → chọn 1 ý.
2. **Content**: chọn số phút → "Viết content" → sửa từng chuỗi, "Viết lại đoạn này" → Lưu.
3. **Giọng đọc**: sao chép lời đọc cho phần mềm giọng → tạo giọng → tải .wav lên.
4. **Duyệt & dựng**: chờ Claude dựng cảnh và thiết kế đồ còn thiếu → xem ảnh → "Nhờ Claude sửa" nếu thấy lỗi.
5. **Render**: 100 % → Render (khoảng 1,4 giây/khung) → xem hoặc tải mp4.

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
