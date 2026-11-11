# WhyShorts — luật phong cách (gửi kèm mỗi lần gọi Claude)

Bản rút gọn của skill `blender-why-shorts` v3. Định dạng dữ liệu nằm ở `STORY.md`; API viết đồ thư viện ở `library/AUTHORING.md`. Trả lời người dùng bằng tiếng Việt; lời đọc video bằng tiếng Anh.

## Video
- Dọc 1080x1920, 30 fps. Shorts mặc định 45-75 giây (tối đa 10 phút; video dài chia chương, mỗi chương 4-7 chuỗi máy, luật bên dưới giữ nguyên).
- Một câu hỏi "Why…" kể thành chuyện ngắn có nhân vật và xung đột; cú twist cuối chính là lời giải thích.
- Nhân vật 2D phẳng (đầu tròn to, viền đen, tay chân là nét) đứng trong bối cảnh 3D có ánh sáng thật và viền hoạt hình.
- Camera trôi liên tục như một cú máy dài; phụ đề từng chữ nảy lên; nhạc nền vui; mọi hành động đều có tiếng động.

## Ý tưởng
- Câu hỏi thật của người Mỹ (People also ask, r/explainlikeimfive, câu hỏi trẻ con, đồ vật hằng ngày). Tránh chủ đề trừu tượng phải giải thích bằng bảng chữ.
- Chấm 5 tiêu chí × 0-2 điểm, chỉ giữ ý từ 8/10:
  1. tò mò thật;
  2. câu trả lời nhìn thấy được bằng một hành động vật lý trên vật thật (rơi, lăn, kẹt, vỡ, tràn);
  3. có hành trình cho camera bám theo;
  4. hài vật lý: ít nhất 3 thất bại leo thang, mỗi cái có tiếng rõ;
  5. kiểm chứng được, có nguồn.
- Mỗi ý tưởng gồm: tiêu đề "Why…" (≤ 8 chữ) + điểm, logline 1 câu, 3 nhịp (Hook 2 giây đầu → Leo thang 3 lần, lần 3 lệch → Twist bằng hành động), trục camera, bối cảnh (1 chính, ≤ 2 phụ), cảnh ăn tiền, công thức.
- 10 ý tưởng dùng ít nhất 4 công thức khác nhau: leo thang · kế hoạch hoàn hảo đổ vỡ · đối đầu · thí nghiệm ngốc nghếch · thế giới nếu khác đi · điều tra hiện trường · tài liệu giả.
- Không sao chép câu chuyện hay nhân vật của kênh khác.

## Lời đọc
- Tiếng Anh, giọng kể chuyện Mỹ, khoảng 150 từ/phút (giọng AI). Câu ngắn, có punchline, twist, câu chốt hài.
- Lời thoại nhân vật đặt trong ngoặc kép (để nhép miệng). `[beat]` = ngắt 0,5-1 giây cho gag hình.
- Kèm bản dịch tiếng Việt và bảng chuỗi máy.

## Nhịp hài
- Hook 2 giây đầu bằng cảnh vô lý nhất, rồi lùi về ("3 DAYS EARLIER") bằng lia nối, không cắt cụt.
- Luật số 3: hai lần giống nhau, lần ba lệch.
- Sau mỗi nhịp lớn có cảnh phản ứng (cận mặt).
- Cặp nhân vật tương phản (nóng nảy và tỉnh bơ). Một gag chạy dọc video, có kết ở cuối. Callback + tag sau lời giải thích.
- Ít nhất một gag hình mỗi 4-5 giây; không cảnh nào chỉ có nhân vật đứng nói. Lời giải thích phải thấy qua hành động (bảng sơ đồ chỉ là phương án phụ).
- Thư viện gag:
  - freeze-frame + thẻ tên;
  - REPLAY slow-mo hoặc tua ngược;
  - POV từ trong hố;
  - mặt cắt x-ray;
  - chia đôi màn hình ✓/✗;
  - bong bóng tưởng tượng;
  - montage "DAY 2… DAY 47";
  - phóng đại (hóa đơn dài, đồng hồ thiệt hại);
  - vật lý hoạt hình (lơ lửng rồi mới rơi, nảy);
  - kể bằng biển hiệu hoặc bồ câu quay đầu nhìn hai lần;
  - iris-out, match cut, wipe.

## Camera v3
- Video 45-60 giây có 4-7 chuỗi; mỗi chuỗi 4-10 giây là một cú máy liền trên một bối cảnh, 2-5 khóa camera, không bao giờ dừng hẳn. Tối đa 2 cảnh chèn ngắn (2-3 giây).
- Mỗi chuyển động camera đi theo một thứ: nhân vật, vật rơi, ánh nhìn, hé lộ chi tiết.
- Các kiểu chuyển động (kết hợp): dolly-in chậm, tracking ngang, vòng cung 20-60°, hạ cần, kéo lùi hé lộ, roll tối đa ±6°.
- Chuyển chuỗi có động cơ: `whip` (đổi nơi, nhảy thời gian), `push` (lao vào vật tối: miệng cống, cửa), `match` (hình giống nhau ở cùng vị trí màn hình), `cut` (chỉ khi cắt theo hành động). Giữ luật 180° và hướng di chuyển trên màn hình.
- Punch-in 12-25% trong 6-10 khung, giữ khoảng 1,5 giây, nhả 24 khung. Snap zoom (3 khung) tối đa 3 lần mỗi video.
- Rung va chạm: strength 0,5-1,5, dur 8-14.
- Góc hơi thấp (ngang ngực nhân vật). Cảnh cận mặt: hạ điểm nhìn để mặt cao hơn phụ đề.
- Bối cảnh đặt xa nhau: phố ở gốc tọa độ, văn phòng ở x=300, bảng sơ đồ ở x=500 (camera lens 45, cách 7,7; phụ đề hạ thấp).
- Trước khi render, `cam_report` phải in `CAMERA OK`.

## Luật chuyển động (kiểm tra trước render)
1. Không khung nào camera đứng yên giữa chuỗi.
2. Mỗi từ nhấn có punch-in, phản ứng hoặc động tác.
3. Mỗi va chạm có đủ: tiếng động, bụi, rung máy, biểu cảm của nhân vật gần đó.
4. Mỗi động tác tay có overshoot (`pease`) và tiếng `swish` (tự động).
5. Nhân vật nói lời thoại thì nhép miệng (`talk`).
6. Mỗi lần chuyển chuỗi có một kiểu `trans` và lý do.

## Âm thanh
- Tự động: whoosh ở cắt cảnh, pop khi đổi biểu cảm, tick theo phụ đề, swish khi vung tay.
- Theo hành động (đặt trong `events`):

| Hành động | Hiệu ứng |
|---|---|
| bước chân | step |
| nhảy, lò xo | boing |
| trượt lên | slide_up |
| rơi, xì hơi | slide_down |
| vật nặng rơi | thud |
| đập đầu | bonk |
| tức giận | rumble + steam |
| giật mình | squeak |
| lo lắng | gulp |
| ý tưởng, đúng rồi | ding |
| chạy vụt | zip_out |
| đổ vỡ | crash |
| "khoan đã?" | scratch |
| tàu hỏa | horn, chug |
| tiền | cash |
| thất bại | sad_trombone |

- Gain: hiệu ứng chính 0,4-0,6; swish/pop 0,25-0,3; tick 0,1. Nhạc `playful`, `sneaky` hoặc `tense`, khoảng 0,16 (0,10 khi có giọng đọc), hạ nhạc (`duck`) ở cao trào.

## Thiết kế
- **Nhân vật:**
  - Hình dáng: đầu tròn r ≈ 0,5, thân bo góc gần bằng đầu, chân ngắn (0,36 + 0,34), tay mảnh, bàn tay tròn trắng, viền đen 0,035. Cao khoảng 2,5 đơn vị.
  - Mỗi nhân vật có một món đồ nhận diện (mũ, nơ, kính…) và màu riêng; tối thiểu 4 biểu cảm, có chớp mắt.
  - Màu emission là linear nên phải đậm: cam (0.98, 0.30, 0.02), xanh (0.03, 0.22, 0.55).
- **Đạo cụ:** đồ cầm tay là 2D trong mặt phẳng nhân vật; đồ rơi, lăn, nằm đất là 3D; đổi qua lại ngay tại khung hành động.
- **Bối cảnh:** vật liệu thật (Principled) + nắng; nhân vật dùng Emission (màu phẳng).
- **Tỉ lệ thế giới:** nhân vật cao khoảng 2,5; nắp cống r = 0,45; đồ cầm tay 0,3-0,8; cửa khoảng 3 × 1,5.
- **Hình khối:** to, rõ, ít chi tiết vụn (xem trên màn hình điện thoại); màu bão hòa, tương phản; viền mực tự động cho mesh 3D.
- **Phụ đề:** 1-2 chữ mỗi lần, trắng viền đen, từ khóa vàng to hơn khoảng 1,3 lần, đặt hơi dưới giữa màn hình. Không bật DOF.
- **Bản quyền:** không vẽ nhân vật có bản quyền, không chép thiết kế của kênh mẫu, không dùng logo thương hiệu thật.
