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
- **Thẻ cảm xúc OmniVoice** (viết thẳng vào `text`, OmniVoice đọc thành tiếng thật; phụ đề tự bỏ thẻ). Chỉ dùng đúng 13 thẻ này:
  - `[laughter]` = tiếng cười: câu đùa của chính mình, chọc người kia, cười trừ khi bị bắt quả tang
  - `[sigh]` = thở dài: chán, bất lực, chịu thua, mệt với người kia ("[sigh] Fine. You pick.")
  - `[surprise-oh]` = "Oh!" ngạc nhiên: vừa hiểu ra / vừa nghe tin lạ ("[surprise-oh] You're serious?")
  - `[surprise-ah]` = "Ah!" giật mình: giật mình, bị bắt quả tang, đau, hoảng
  - `[surprise-wa]` = "Wa!" sốc mạnh: sốc to, choáng ("[surprise-wa] Four hundred dollars?!")
  - `[surprise-yo]` = "Yo!" thích thú: hào hứng, khoái chí khi thấy thứ hay
  - `[question-ah]` = "Hả?" hỏi lại: không tin tai mình, hỏi lại ("[question-ah] Taco Bell?")
  - `[question-oh]` = "Ồ?" nghi ngờ: nghi ngờ, bắt bẻ nhẹ ("[question-oh] Since when?")
  - `[question-en]` = "Hửm?" ngơ ngác: lơ đãng, không nghe rõ, giả vờ không hiểu
  - `[question-ei]` = "Ê?" ngạc nhiên hỏi: ngạc nhiên kèm hỏi, thân mật
  - `[question-yi]` = "Hử?" khó hiểu: khó hiểu, thấy lạ
  - `[confirmation-en]` = "Ừm." xác nhận: đồng ý chiếu lệ, tỉnh bơ, "uh-huh" kiểu không nghe
  - `[dissatisfaction-hnn]` = "Hừm" không vừa ý: bực, dỗi, không chịu, càu nhàu
  - Dùng ĐỀU cả video: khoảng 1 thẻ mỗi 2-3 câu (≈ 30-45 % số câu), dồn vào chỗ cảm xúc mạnh: phản ứng sau cú đảo, câu chốt, lúc
    bị bắt quả tang, lúc chịu thua. Không 2 câu liền của cùng một người đều có thẻ; không quá 1 thẻ mỗi câu (cùng lắm 2 khi câu dài).
  - Đặt đầu câu (cách dùng chuẩn của OmniVoice) hoặc giữa hai vế sau dấu câu: "No way. [laughter] You did NOT.".
  - Khớp với `face`: laugh → [laughter]; shock → [surprise-oh]/[surprise-wa]/[question-ah]; sad, chịu thua → [sigh];
    grumpy/angry → [dissatisfaction-hnn]; side_eye/smirk hỏi vặn → [question-oh]; "uh-huh" tỉnh bơ → [confirmation-en].
  - Không viết "haha", "*sigh*", "(laughs)", không bịa thẻ khác (`[angry]`, `[cry]`… sẽ bị đọc thành chữ).
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
  - Thẻ cảm xúc OmniVoice (danh sách ở trên) ở chỗ cảm xúc thật sự, khoảng 1 thẻ mỗi 2-3 câu.
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

## 4b. Vị trí đứng (`spot`)
- Mỗi nhân vật đứng ở chỗ hợp vai và tình huống: chọn trong `spots` của bối cảnh (xem danh sách bối cảnh), ví dụ người lái xe ở
  `driver_door`, người đang nấu ở `stove`, người vừa về nhà hay khách ở `doorway`, sếp ở chỗ "của mình" (bàn/cửa sổ văn phòng), người
  đang trốn việc ở mép cảnh. Không có chỗ hợp thì ghi `left`/`center`/`right` hoặc để trống.
- Tool tự xếp phần còn lại: người nói trước đứng bên trái, trẻ con đứng giữa bố mẹ và nhích lên trước, cặp đôi đứng sát (nắm tay được),
  gia đình gần, bạn bè vừa, sếp/hàng xóm xa hơn; không ai đứng chồng lên ai.

## 4c. Đồ vật trong tay và đi lại (`holding`, `action`, `prop`, `to_spot`)
Đồ cầm tay là hình 2D phẳng (như nhân vật): phone, coffee, mug, soda, bottle, fries, burger, pizza, icecream, bag, keys, book,
remote, paper, receipt, money, flowers, gift, card, popcorn, donut. Chỉ dùng khi đồ vật có ích cho cái hài (callback, cú đảo,
gài từ trước) — tối đa khoảng 1/3 số câu có action.
- `cast[].holding` = đồ cầm sẵn từ đầu (cốc cà phê, túi đồ…). Tool tự chọn tay phía người kia.
- `action` của người nói ở câu đó:
  - `take_out` (lấy ra: điện thoại, chìa khóa…), `show` (giơ cho người kia xem, cả câu), `put_away` (cất đi);
  - `use` = uống/ăn/xem màn hình, làm ngay TRƯỚC câu (tool tự chừa ~1 s): hợp với câu bình thản kiểu "*sip* ...I don't care.";
  - `give` = đưa cho người đang nói chuyện, cuối câu; người kia cầm luôn (dùng cho cú chốt: "They're YOUR fries.");
  - `walk_to` + `to_spot` = vừa nói vừa bước tới: `partner` (lại gần, dỗ dành/đối chất), `away` (lùi ra, giận dỗi), `left`/`right`,
    hoặc tên một spot của bối cảnh (fridge, driver_door…);
  - `enter` = đi vào cảnh rồi mới nói (người thứ ba xuất hiện, bố về nhà…); trước đó người này không có trên hình;
  - `exit` = nói xong bỏ đi (câu chốt kiểu "I'm getting two." rồi quay đi). Nói câu sau thì tự đi vào lại.
- Không bắt hai người cùng đi một lúc; đi lại tối đa 2-3 lần mỗi video (máy quay đứng yên, đi nhiều sẽ ra khỏi khung).
- **Ngồi / nằm**: `cast[].posture` = tư thế lúc mở đầu (`stand`, `sit`, `lie`); đổi giữa chừng bằng `action` `sit_down`, `lie_down`,
  `stand_up` (làm ngay trước câu). Ngồi ở spot có `seat` của bối cảnh (sofa, mép capo xe…) — chọn spot đó trong `cast[].spot`;
  bối cảnh không có thì tool tự đặt ghế (hai người cùng ngồi từ đầu → một sofa), nằm thì tool tự đặt giường (nhìn từ cuối giường,
  đắp chăn tới cổ; hai người nằm từ đầu → chung giường đôi). Người đang nằm ngồi dậy thì ngồi dựa đầu giường, vẫn đắp chăn. Đi (`walk_to`, `exit`) thì tool tự cho đứng dậy trước; `walk_to` tới spot có ghế thì tự ngồi xuống.
  Dùng khi tư thế làm nên cái hài: nằm lướt điện thoại hỏi câu ngớ ngẩn lúc nửa đêm, ngồi sofa giành remote, ngồi phịch xuống khi
  chịu thua, bật dậy khi sốc. Cảnh "trong xe" vẫn dựng đứng/ngồi cạnh xe (`car_hood` ở bãi đỗ).

## 5. Bối cảnh
- Một bối cảnh cho cả video, chọn trong thư viện (bếp `kitchen` với `stuck_toast: false`, `office`, `street`…). Nếu không hợp thì đặt
  tên mới (living_room, bedroom, restaurant, car_front_seats, supermarket…) và đưa vào `library_needs` (tối đa 1 món mới).
- Nhân vật đứng giữa bối cảnh, quay mặt về camera như phim hoạt hình 2D; không đi lại, không ngồi. Cảnh trong xe → đứng cạnh xe ở bãi đỗ;
  bàn ăn → đứng cạnh bàn; giường/sofa → đứng trước giường/sofa.
