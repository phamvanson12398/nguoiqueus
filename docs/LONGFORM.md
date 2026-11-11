# Chế độ video dài 16:9 (10–20 phút): phân tích kênh mẫu và kế hoạch

## 1. Kênh mẫu: Squire Explains (@SquireExplains)
Nguồn: danh sách video công khai của kênh (lấy ngày 11/11/2026) và thumbnail. Trang video và phụ đề bị YouTube chặn từ máy chủ
đám mây, nên **chưa phân tích được lời đọc, nhịp cắt, chuyển động**. Các phần đó ghi rõ là "suy luận" bên dưới.

**Số liệu (đo được)**
- 6 video dài, dài 9:24–13:20 (trung bình 10,7 phút); tổng 2,6 triệu view, trung vị 69 nghìn:

  | Video | Dài | View |
  |---|---|---|
  | Why Knights Stopped Using Shields | 9:24 | 1,8 triệu |
  | Why Breaking the Roman Front Line Was a Death Trap | 9:25 | 621 nghìn |
  | The ENTIRE History of the Samurai | 11:41 | 100 nghìn |
  | Were War Elephants Actually Useful? | 9:56 | 39 nghìn |
  | Why Was the English Longbow So Deadly? | 13:20 | 36 nghìn |
  | What Was Hiding Under America's Base in Vietnam? | 10:40 | 7,6 nghìn |

- 48 shorts: tổng 18,1 triệu view, trung vị 130 nghìn, 3 video trên 1 triệu ("She Went to War Disguised as Her Brother" 5,3 triệu,
  "Why Sparta HATED This 300 Survivor" 1,9 triệu, "Why This Kamikaze Kept Coming Back..." 1,7 triệu).
- Mô tả kênh: "history's strangest why questions… hand-drawn animation, facts checked, new shorts every week".

**Đề tài và tiêu đề (đo được)**
- Lịch sử quân sự là chính: hiệp sĩ, La Mã, samurai, Sparta, Thế chiến 2, Việt Nam.
- Mẫu tiêu đề:
  - dài: "Why … ?", "Were … Actually Useful?", "The ENTIRE History of …", "What Was Hiding …";
  - shorts: "What Happened to …", "The X Who …", "Why … Kept …".
  - Viết hoa một chữ để nhấn (ENTIRE, HATED, NEVER, BANNED).
- Video dài trả lời **một câu hỏi về cơ chế** ("vì sao khiên bị bỏ"), không kể tiểu sử. Hai video đứng đầu đều thuộc kiểu này.

**Hình ảnh (nhìn từ thumbnail)**
- Nhân vật 2D vector: đầu tròn trắng to, viền đen dày, mắt chấm, lông mày biểu cảm, má hồng. Cùng họ phong cách với nhân vật của tool.
- Trang phục và vũ khí đúng thời kỳ, khá chi tiết (mũ, giáp, áo choàng, khiên có hoa văn, kimono, quân phục). Mỗi video là một bộ trang phục mới
  khoác lên cùng một khuôn nhân vật.
- Đám đông: hàng lính lặp lại, đứng theo đội hình, xếp lớp xa gần.
- Nền: phong cảnh vẽ phẳng (đồi, trời mây, lều trại, lâu đài) được làm mờ cho có chiều sâu. Có cả mặt cắt (đường hầm dưới căn cứ Việt Nam).
- Thumbnail 16:9:
  - 1–2 chữ rất to, trắng viền đen ("USELESS.", "DEADLIEST.", "IT'S A TRAP", "UNDER THEM?");
  - một nhân vật biểu cảm rõ;
  - hoặc chia đôi kiểu trước/sau ("1185 → 1877") hay đối đầu ("ROME VS ELEPHANTS"), có ký hiệu đỏ (biển cấm, mũi tên, dấu ?).
- Shorts: thumbnail dọc với chữ đỏ/trắng to ("THE KAMIKAZE WHO CAME BACK").

**Cách làm (suy luận, cần xác nhận bằng video thật)**
- Rất có thể là hoạt hình cắt rối 2D (Adobe Animate/After Effects, Moho hoặc Toon Boom). Có thư viện nhân vật và trang phục dùng lại, nền vẽ
  sẵn từng lớp cho parallax, camera pan/zoom trên tranh, có thể chạy 12–15 hình/giây theo kiểu hoạt hình.
- Lời đọc kiểu "người dẫn tự mãn" (squire), hài khô, có kiểm chứng; khoảng 150 từ/phút → 1.400–2.000 từ cho 10–13 phút.
- Chiến lược kênh: shorts hằng tuần để kéo người đăng ký, video dài thưa hơn nhưng kiếm nhiều hơn (quảng cáo giữa video từ 8 phút).

## 2. So với tool hiện tại
| Cần cho video dài | Tool hiện có | Thiếu |
|---|---|---|
| 16:9 1920x1080 | cố định 1080x1920 | khổ hình theo `meta.aspect`; khung camera, thẻ, phụ đề theo khổ |
| 10–20 phút (18.000–36.000 khung) | `plan_shots` 1 lần cho cả video (12 phút Claude cho 1.966 khung) | chia **chương**: story theo chương, dựng/render từng chương, ghép |
| Canh chữ 1.500–3.000 từ | `align.py` quy hoạch động O((P·G)²) | canh theo đoạn/chương |
| Render | 1,4 s/khung → 20 phút ≈ 14 giờ | render "on twos" (15 hình/giây nhân đôi), hàng đợi render theo chương, render tiếp khi bị ngắt |
| Đám đông, đội hình quân | mỗi nhân vật khoảng 120 object | "lính phụ" nhẹ (collection instance), lệnh đội hình (hàng, khối, nêm) |
| Trang phục đúng thời kỳ | món đồ nhận diện vẽ lên thân/đầu | **bộ trang phục** ghép được (mũ, giáp, khiên, vũ khí, áo) như món thư viện, Claude thiết kế theo thời kỳ |
| Nền phẳng nhiều lớp, mờ xa | bối cảnh 3D | kiểu bối cảnh "diorama": các lớp tranh 2D phẳng xếp sâu, có parallax, mờ theo xa (mist có sẵn) |
| Bản đồ, mũi tên quân, dòng thời gian, mặt cắt | bảng sơ đồ + thẻ | bối cảnh `map` (vùng, sông, mũi tên di chuyển, quân cờ), `timeline`, `cutaway` |
| Phụ đề | to giữa màn hình kiểu shorts | kiểu video dài: phụ đề nhỏ phía dưới hoặc tắt (YouTube có CC) |
| Thumbnail | không có | tạo 3 phương án 1280x720 (chữ to + nhân vật + chia đôi/VS) |
| Đóng gói YouTube | không có | tiêu đề, mô tả có mốc chương, nguồn, thẻ tag |

## 3. Kế hoạch đề xuất (theo thứ tự, mỗi bước chạy thử thật như các bước trước)
1. **Khổ 16:9 + chương**: `meta.aspect` ("9:16" | "16:9"); project dài gồm `chapters/<n>/story.json`;
   content dài có chương (hook 30 giây → 4–8 chương → kết); canh chữ theo chương; render từng chương rồi ghép (dùng lại `tools/splice.py`).
   Video thử: 3 phút, 2 chương.
2. **Render nhanh**: tùy chọn on-twos, hàng đợi render chương, render tiếp từ khung đang dở, đo tốc độ thật trên máy người dùng.
3. **Trang phục và đám đông**: thư viện `outfits/<thời kỳ>/` (Claude thiết kế), lính phụ nhẹ + lệnh đội hình. Video thử: "Why Roman
   soldiers fought in lines" kiểu tương tự (đề tài và nhân vật của mình, không chép).
4. **Bối cảnh diorama 2D + bản đồ/timeline/cutaway**.
5. **Thumbnail + gói YouTube** (tiêu đề, mô tả có chương, nguồn).
6. Làm trọn một video 10 phút; ghi lỗi, sửa; cập nhật skill.

**Lưu ý bản quyền và khác biệt:** không chép nhân vật, thumbnail hay kịch bản của Squire Explains. Giữ nhân vật của tool (Joe, Gary…),
chọn một người dẫn riêng và bảng màu riêng.

## 4. Cần thêm để phân tích sâu hơn
- Bản chép lời (YouTube → "…" → Show transcript → copy) của 2 video dài, ví dụ "Why Knights Stopped Using Shields" và "Roman Front Line":
  để đo cấu trúc kịch bản, hook, nhịp, số từ.
- 1–2 phút video tải từ máy người dùng (hoặc quay màn hình): để đo độ dài mỗi cảnh, kiểu chuyển cảnh, chuyển động camera, số hình/giây.
