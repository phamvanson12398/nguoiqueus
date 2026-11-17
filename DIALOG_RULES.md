# Video đối thoại hài (Shorts 9:16) — luật viết

Kiểu video: 2 (tối đa 3) nhân vật đứng cạnh nhau trong MỘT bối cảnh đời thường, nói qua nói lại, kết bằng một cú đảo bất ngờ.
Đối tượng: cặp đôi yêu nhau, vợ chồng, gia đình (bố mẹ – con, ông bà – cháu, anh chị em), bạn bè, sếp – nhân viên.
Lời thoại tiếng Anh (giọng OmniVoice, mỗi nhân vật một giọng), bản dịch tiếng Việt để người dùng duyệt.

## 1. Cấu trúc (30-75 giây, 8-22 câu)
1. **Câu móc (0-3 s)**: câu đầu đặt ngay xung đột hoặc một câu lạ ("Baby, I have to tell you something… I ate your fries.").
   Không chào hỏi, không giới thiệu.
2. **Tiêu đề gợi ý (`hook`)**, người dùng tự thêm lên đầu video khi chỉnh sửa (tool không vẽ): đặt kỳ vọng mà video sẽ lật ngược ("This is true love", "When she says 'I'm fine'",
   "Dad logic"). ≤ 32 ký tự, không emoji (font không có emoji).
3. **Đẩy lên (setup → build)**: mỗi câu tăng một nấc; luật ba (hai lần như dự đoán, lần thứ ba lệch); người kia phản ứng ngày càng
   nghi ngờ/bực/sốc. Đừng giải thích, để người xem tự đoán.
4. **Cú đảo (twist)**: thông tin mới làm đổi nghĩa mọi câu trước (hóa ra là vì tiền, vì đồ ăn, vì con mèo…). Gài trước bằng một chi tiết nhỏ
   ở phần đầu để cú đảo "hợp lý mà bất ngờ".
5. **Câu chốt (punchline)**: câu ngắn nhất, rõ nhất, đặt gần cuối; trước nó có khoảng lặng hài `pause_before` 0,6-1,2 s.
6. **Câu đuôi (tag, tùy chọn)**: một phản ứng/một câu 1-4 chữ sau cú chốt ("…Worth it.", "[sigh] Every time.") + `end_sfx`.

## 2. Lời thoại
- Văn nói tự nhiên, ngắn: phần lớn 3-12 từ, tối đa ~16; không ai nói quá 2 câu liền. Hỏi – đáp nhanh.
- Tốc độ ~2,3 từ/giây tính cả khoảng nghỉ: 45 s ≈ 100 từ, 60 s ≈ 135 từ.
- Gọi nhau bằng tên/biệt danh ("babe", "honey", "Mom") để người xem biết ai với ai.
- Thẻ OmniVoice cho tiếng cười/thở dài: `[laughter]`, `[sigh]`, `[surprise-oh]`, `[surprise-wa]`, `[dissatisfaction-hnn]`,
  `[question-ah]`. Dùng ít (2-4 cả video), đặt đầu câu. Không viết "haha", "*sigh*".
- `speed`: 1.1-1.2 khi cuống, cãi nhau, nói nhanh để chối; 0.9 khi buồn, ngập ngừng, nghiêm giả vờ.
- Hài lành mạnh, đáng yêu: đùa vào tình huống và thói quen (đồ ăn, điện thoại, tiền, mua sắm, remote TV, nhiệt độ điều hòa, ngủ nướng,
  mẹ chồng/mẹ vợ, bài tập về nhà, quên ngày kỷ niệm), không chê ngoại hình, không xúc phạm giới/dân tộc/tôn giáo, không bạo lực thật,
  không nội dung người lớn. Cả hai phía đều có lúc "thắng".
- Đề tài dễ viral: "relatable" (ai yêu/ai có bố mẹ cũng gặp), so sánh "lời nói vs ý thật", logic trẻ con, logic bố mẹ, hiểu lầm chữ nghĩa,
  lời hứa vs thực tế, kiểm tra tình yêu ("Would you still love me if I was a worm?").

## 3. Diễn xuất (mỗi câu)
- `face` người nói và `listener_face` người nghe đổi theo nghĩa câu; người nghe PHẢN ỨNG là nửa cái hài (side_eye, annoyed, shock, sad).
  Mặt có sẵn: neutral happy smirk wink angry shock worried grumpy focus smug_closed sad love laugh side_eye annoyed blush.
- `gesture`/`listener_gesture`: point, hands_hips, cross_arms, shrug, wave, hold_hands, think, fist, hands_up, open_arms, facepalm, none.
  Ít thôi: cử chỉ ở câu quan trọng, còn lại none (tư thế `idle`). `hold_hands` cần cả hai người cùng làm.
- `react` (người nghe giật mình/nảy lên): ở cú đảo hoặc câu chốt, 1-3 lần cả video.
- `shot`: để `auto` phần lớn (tool tự cắt: hai người, cận người nói, cận người nghe phản ứng). Đặt `both_close` cho cú chốt,
  `listener` khi phản ứng mới là trò cười, `wide` cho câu đầu nếu cần thấy bối cảnh.
- `sfx`: tiếng hài ở đầu câu, chỉ chỗ đắt (≤ 1 mỗi 10 giây): scratch (khựng lại "wait what?"), boing, gulp (nuốt khan), ding (ý hay),
  squeak, cash (tiền), bonk, slide_down (xẹp), sad_trombone (thua). `end_sfx` cho cú chốt cuối.

## 4. Nhân vật và giọng
- Mỗi nhân vật: tên, vai, giới tính, tuổi, `body` (child cho trẻ con), tóc + màu tóc, trang phục đời thường (casual_tee, casual_dress, hoodie,
  shirt_tie, home_apron, cardigan, kid_tee, kid_dress), hai màu áo đậm và tươi, mỗi người khác nhau rõ (không cùng tông).
- `voice_instruct` cho OmniVoice: tiếng Anh, thuộc tính cách nhau dấu phẩy: `male`/`female`, tuổi (`child`, `teenager`, `young adult`,
  `middle-aged`, `elderly`), độ cao (`very low pitch`, `low pitch`, `moderate pitch`, `high pitch`, `very high pitch`), giọng vùng
  (`american accent`, `british accent`…). Hai giọng trong một video phải khác nhau rõ (giới tính hoặc độ cao).
- `voice_id`: nếu library/voices đã có giọng hợp vai (nhân vật quen của kênh) thì dùng lại id đó (giữ tên nhân vật cũ); không thì đặt id mới.

## 5. Bối cảnh
- Một bối cảnh cho cả video, chọn trong thư viện (bếp `kitchen` với `stuck_toast: false`, `office`, `street`…). Nếu không hợp thì đặt
  tên mới (living_room, bedroom, restaurant, car_front_seats, supermarket…) và đưa vào `library_needs` (tối đa 1 món mới).
- Nhân vật đứng giữa bối cảnh, quay mặt về camera như phim hoạt hình 2D; không đi lại.
