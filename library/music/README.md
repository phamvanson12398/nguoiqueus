# Nhạc nền (thư viện nhạc thật)
Nhạc thật nghe chuyên nghiệp hơn nhạc tool tự tổng hợp. Tải nhạc **miễn phí bản quyền** rồi xếp vào thư mục theo **tâm trạng**:

```
library/music/epic/      trận đánh, khoảnh khắc lớn
library/music/tense/     căng thẳng, nguy hiểm
library/music/mystery/   bí ẩn, mở đầu, câu hỏi
library/music/march/     hành quân, xây dựng, làm việc
library/music/calm/      giải thích, đời thường
library/music/sad/       mất mát
library/music/triumph/   chiến thắng, kết
library/music/playful/   đoạn hài, gag
```

- Nguồn gợi ý: YouTube Studio → Thư viện âm thanh (lọc "Không cần ghi công"), Pixabay Music, nhạc CC0. Bài CC-BY: ghi công trong mô tả video.
- Định dạng: `.wav`, `.mp3`, `.ogg`, `.flac`, `.m4a` (mp3/ogg/flac/m4a đọc qua Blender). Mỗi thư mục 2-5 bài là đủ; bài dài ≥ 1 phút.
- Tool tự chọn một bài cho mỗi tâm trạng (cố định theo video, các phần của video dài dùng cùng bài), lặp nối mềm cho đủ dài, hạ dưới giọng
  đọc và chuẩn độ lớn như nhạc tự tổng hợp. Thư mục nào trống thì tool vẫn tự tổng hợp nhạc cho tâm trạng đó.
- Muốn chỉ định đúng một bài cho một đoạn: trong story `"music": [{"file": "epic/ten_bai.mp3", "from": 1, "to": 900}]`.
- File nhạc không đưa lên git (dung lượng, bản quyền).
