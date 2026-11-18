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
- **Ngắt nghỉ, không nói một mạch**: OmniVoice ngừng theo dấu câu, nên viết chỗ ngừng ngay trong câu: "So... I did a thing.",
  "Okay, but—", "Wait. Wait, wait, wait.", "You're telling me... it's fake?". Nhịp đổi theo cảm xúc:
  - cãi nhau, chối, hoảng: câu ngắn, đối đáp dồn (`pause_before` 0,15-0,3);
  - ngập ngừng, ngượng, sắp thú nhận: "..." trong câu, `pause_before` 0,6-1,0;
  - sau cú đảo/tiết lộ: người kia im 1-1,5 s rồi mới phản ứng (đặt ở `pause_before` của câu phản ứng);
  - trước câu chốt: khoảng lặng ngượng 0,8-1,5 s. Tool tự giữ khoảng lặng tối thiểu ở những chỗ này.
- **Giọng phải có biểu cảm** (OmniVoice đọc theo chữ và dấu câu, không có nút "cảm xúc"): viết sao cho chữ tự mang cảm xúc.
  - Dấu câu: "?!" khi sốc, "!" khi phấn khích/bực, "..." khi ngập ngừng/ngượng, "—" khi bị cắt ngang, câu cụt khi tỉnh bơ.
  - Thán từ ở đầu câu: "Oh my God.", "Wait—what?!", "Ugh.", "Okay, okay.", "Nope.", "Babe...", "Uh-huh.", "Wow." (đừng lạm dụng).
  - Kéo dài/nhấn: "Sooo…", "No. Way.", "I am NOT mad." (viết hoa MỘT chữ cần nhấn, không viết hoa cả câu).
  - Thẻ `[laughter]`, `[sigh]`, `[surprise-oh]`, `[dissatisfaction-hnn]` ở chỗ cảm xúc thật sự (3-5 cả video).
  - `face` của người nói cũng chỉnh âm lượng câu: angry/shock to hơn, sad/blush nhỏ hơn; tool đọc mỗi câu vài bản và giữ bản có ngữ điệu nhất.
- Hài lành mạnh, đáng yêu: đùa vào tình huống và thói quen (đồ ăn, điện thoại, tiền, mua sắm, remote TV, nhiệt độ điều hòa, ngủ nướng,
  mẹ chồng/mẹ vợ, bài tập về nhà, quên ngày kỷ niệm), không chê ngoại hình, không xúc phạm giới/dân tộc/tôn giáo, không bạo lực thật,
  không nội dung người lớn. Cả hai phía đều có lúc "thắng".
- Đề tài dễ viral: "relatable" (ai yêu/ai có bố mẹ cũng gặp), so sánh "lời nói vs ý thật", logic trẻ con, logic bố mẹ, hiểu lầm chữ nghĩa,
  lời hứa vs thực tế, kiểm tra tình yêu ("Would you still love me if I was a worm?").

## 2b. Hài kiểu Mỹ (bắt buộc)
Người xem chính là khán giả Mỹ: viết như sitcom/sketch Mỹ, người Mỹ đọc thấy tự nhiên và buồn cười.
- **Đời sống Mỹ hằng ngày** làm chất liệu: chạy Target "chỉ mua một món" rồi ra 200 đô, thẻ Costco, gọi DoorDash/Uber Eats khi
  "we have food at home", chia mật khẩu Netflix, group chat gia đình, Thanksgiving với nhà vợ/chồng, fantasy football, hóa đơn tiền điện,
  student loans, tiền thuê nhà, đơn Starbucks dài ngoằng, gym tháng Một, gói Amazon chất đống, HOA hàng xóm khó tính, therapy-speak
  ("I'm setting a boundary", "that's a red flag"), "per my last email", bố kể dad joke, mẹ nói "I'm not mad, I'm disappointed".
  Chỉ nhắc tên thương hiệu như người thật nói chuyện (không quảng cáo, không chê bai sản phẩm).
- **Kỹ thuật hài Mỹ**: deadpan (nói chuyện vô lý bằng giọng tỉnh bơ), sarcasm, understatement ("So that's… not great."),
  hyperbole, chữ nghĩa bị hiểu theo nghĩa đen, logic sai mà tự tin tuyệt đối, "yes-and" leo thang (mỗi câu chấp nhận rồi đẩy xa hơn),
  callback (câu cuối gọi lại một chi tiết đầu video), khoảng lặng ngượng (awkward pause) trước câu chốt, câu chốt thật ngắn (2-6 từ).
- **Giọng văn**: tiếng Anh Mỹ thông tục, rút gọn (gonna, wanna, y'know, literally, low-key, no way, are you serious?, okay but…),
  câu ngắn, ngắt nhịp tự nhiên; tránh từ cổ, tránh kiểu Anh-Anh, tránh dịch từ tiếng Việt.
- Hài ấm áp, không cay độc: không chính trị, không tôn giáo, không chê ngoại hình/giới/sắc tộc; cặp đôi vẫn thương nhau ở cuối.

## 3. Diễn xuất (mỗi câu)
- `face` người nói và `listener_face` người nghe đổi theo nghĩa câu; người nghe PHẢN ỨNG là nửa cái hài (side_eye, annoyed, shock, sad).
  Mặt có sẵn: neutral happy smirk wink angry shock worried grumpy focus smug_closed sad love laugh side_eye annoyed blush.
- `gesture`/`listener_gesture`: point, hands_hips, cross_arms, shrug, wave, hold_hands, think, fist, hands_up, open_arms, facepalm, none.
  Ít thôi: cử chỉ ở câu quan trọng, còn lại none (tư thế `idle`). `hold_hands` cần cả hai người cùng làm.
- `react` (người nghe giật mình/nảy lên): ở cú đảo hoặc câu chốt, 1-3 lần cả video.
- `shot`: để `auto` phần lớn (tool tự cắt: hai người, cận người nói, cận người nghe phản ứng). Đặt `both_close` cho cú chốt,
  `listener` khi phản ứng mới là trò cười, `wide` cho câu đầu nếu cần thấy bối cảnh.
- `sfx` và `end_sfx`: luôn `none`. Video đối thoại KHÔNG có nhạc nền và tiếng động, chỉ có giọng; cái hài nằm ở lời, ngữ điệu, mặt và khoảng lặng.

## 4. Nhân vật và giọng
- Mỗi nhân vật: tên, vai, giới tính, tuổi, `body` (child cho trẻ con), tóc + màu tóc, trang phục đời thường (casual_tee, casual_dress, hoodie,
  shirt_tie, home_apron, cardigan, kid_tee, kid_dress), hai màu áo đậm và tươi, mỗi người khác nhau rõ (không cùng tông).
- **Đơn giản nhưng lạ mắt**: thân và mặt vẫn tối giản (đầu tròn to, thân thon, tay chân que), mỗi nhân vật có:
  - `head_shape` riêng: `round` (tròn), `egg` (quả trứng, cao), `wide` (bè ngang), `tall` (dài). Hai người trong video khác dáng đầu.
  - đúng MỘT `signature` (món nhận diện trên đầu): `bow` nơ, `glasses` kính, `ahoge` một sợi tóc dựng xoắn, `cap` mũ lưỡi trai,
    `freckles` tàn nhang, `earrings` bông tai, `headband` băng đô, `beanie` mũ len có quả bông, `flower` hoa cài, `lashes` mi cong.
    Hợp tính cách (mọt sách → glasses, bố → cap, cô nàng lém lỉnh → bow/flower, người lười → beanie, đứa trẻ tinh nghịch → ahoge/freckles).
  - `sig_color`: một màu rực cho món đó (đỏ, vàng, xanh ngọc, hồng, cam), hai người khác màu. Ở kiểu nhân vật xám, đây là điểm màu duy nhất
    trên người nên rất nổi.
- `voice_instruct` cho OmniVoice: tiếng Anh, thuộc tính cách nhau dấu phẩy: `male`/`female`, tuổi (`child`, `teenager`, `young adult`,
  `middle-aged`, `elderly`), độ cao (`very low pitch`, `low pitch`, `moderate pitch`, `high pitch`, `very high pitch`), giọng vùng
  (`american accent`, `british accent`…). Hai giọng trong một video phải khác nhau rõ (giới tính hoặc độ cao).
- `voice_id`: nếu library/voices đã có giọng hợp vai (nhân vật quen của kênh) thì dùng lại id đó (giữ tên nhân vật cũ); không thì đặt id mới.

## 5. Bối cảnh
- Một bối cảnh cho cả video, chọn trong thư viện (bếp `kitchen` với `stuck_toast: false`, `office`, `street`…). Nếu không hợp thì đặt
  tên mới (living_room, bedroom, restaurant, car_front_seats, supermarket…) và đưa vào `library_needs` (tối đa 1 món mới).
- Nhân vật đứng giữa bối cảnh, quay mặt về camera như phim hoạt hình 2D; không đi lại, không ngồi. Cảnh trong xe → đứng cạnh xe ở bãi đỗ;
  bàn ăn → đứng cạnh bàn; giường/sofa → đứng trước giường/sofa.
