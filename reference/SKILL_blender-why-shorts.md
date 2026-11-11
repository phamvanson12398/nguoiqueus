---
name: "blender-why-shorts"
description: "Làm shorts dọc hoạt hình 'Why…' hài kiểu US: nhân vật 2D trong bối cảnh 3D, camera trôi liền mạch như phim ngắn, phụ đề từng chữ, âm thanh hiệu ứng theo hành động, dựng và render bằng Blender trên máy người dùng."
---

# Shorts hoạt hình "Why…" bằng Blender — v3 (camera liền mạch, điều khiển Blender trên máy người dùng)

Phong cách: video dọc 1080x1920, 30 fps, 45-75 giây. Một câu hỏi "Why…" được kể thành câu chuyện ngắn có nhân vật và xung đột; cú twist ở cuối chính là lời giải thích. Nhân vật 2D phẳng (đầu tròn to, viền đen, tay chân là nét) đứng trong bối cảnh 3D có ánh sáng thật và viền hoạt hình. **Camera trôi liên tục như một cú máy dài: ít cắt (4-7 chuỗi cho 45-60 giây), mỗi lần chuyển cảnh đều có động cơ (lia nối, chui qua vật, match cut), nên người xem thấy một bộ phim ngắn chứ không phải chuỗi slide.** Phụ đề từng chữ nảy lên giữa màn hình, nhạc nền vui và **tiếng động + hiệu ứng hình cho mọi hành động**.

Blender LUÔN chạy trên máy người dùng (Windows, Blender 5.2.3, card NVIDIA, EEVEE). Môi trường đám mây (`pip install bpy` cùng bản 5.2) chỉ để thử script và xem vài khung hình trước. Tốc độ đo thật với bộ công cụ v2: **khoảng 1,4 giây/khung** (45 giây video ≈ 32 phút render).

**Script tham chiếu v2 đầy đủ (đã render thật, 1.540 dòng):** `C:\Users\balha\Videos\claude_test\manhole_scene_v2.py` trên máy người dùng (video "Why Manhole Covers Are Round"). Khi làm video mới, việc đầu tiên là `device_stage_files` file này về rồi dùng làm khung, chỉ thay nội dung, **và thay toàn bộ phần camera của nó bằng camera v3** (mục 2c và module "Camera v3"). Nếu file không còn, ghép **template v1 ở cuối skill** với **module v2** (mục "Bộ công cụ v2") theo hướng dẫn tích hợp.

## Quy trình

### 1. Ý tưởng (dừng lại chờ chọn)
Mục tiêu: ý tưởng phải **xem được bằng mắt**, không phải bài giảng có hình minh họa. Làm theo thứ tự:

**a. Đào 25-30 ứng viên rồi lọc còn 10.** Nguồn câu hỏi thật của người Mỹ: "People also ask", r/explainlikeimfive, r/NoStupidQuestions, câu hỏi của trẻ con, đồ vật ai cũng thấy hằng ngày (nắp cống, ổ cắm, vạch kẻ đường, nút áo, hộp sữa…). Tránh chủ đề trừu tượng (kinh tế vĩ mô, lịch sử chính trị, hóa học phân tử) vì phải giải thích bằng bảng chữ.

**b. Chấm 5 tiêu chí, mỗi tiêu chí 0-2 điểm, chỉ giữ ý tưởng từ 8/10 trở lên:**
1. **Tò mò thật:** người Mỹ bình thường từng thắc mắc hoặc sẽ dừng lướt khi đọc tiêu đề.
2. **Câu trả lời nhìn thấy được:** lời giải thích diễn ra bằng một hành động vật lý trên vật thật (rơi, lăn, kẹt, vỡ, tràn) trong 1 cảnh, không cần đọc chữ.
3. **Có hành trình cho camera:** câu chuyện đi theo một vật, một nhân vật hoặc một con đường xuyên suốt (đồng xu rơi xuống cống, chiếc xe đi qua ngã tư, giọt nước chảy qua ống) để camera bám theo liên tục.
4. **Hài vật lý:** có ít nhất 3 tai nạn hoặc thất bại leo thang, mỗi cái có tiếng động rõ (thud, bonk, crash…).
5. **Kiểm chứng được:** sự thật có nguồn đáng tin; không dựa vào truyền thuyết mạng.

**c. Mỗi ý tưởng trình bày đúng mẫu:**
- Tiêu đề tiếng Anh (dạng "Why…", tối đa 8 chữ) + điểm (vd. 9/10)
- Logline 1 câu: nhân vật + mục tiêu + chuyện gì phá hỏng
- **3 nhịp:** Hook (2 giây đầu, hình gì) → Leo thang (3 lần thất bại, lần 3 lệch) → Twist (sự thật hiện ra bằng hành động gì)
- **Trục camera:** camera đi theo cái gì, từ đâu tới đâu, và 1-2 lần chuyển cảnh bằng cách nào (vd. "bám theo nắp cống lăn từ ngã tư xuống dốc → chui theo nó vào miệng cống → mặt cắt x-ray")
- **Bối cảnh:** 1 bối cảnh chính, tối đa 2 phụ
- **Cảnh ăn tiền** (dùng làm hook và thumbnail)
- Công thức câu chuyện (mục 2b)

10 ý tưởng dùng ít nhất 4 công thức khác nhau. **Không sao chép** câu chuyện hay nhân vật của kênh khác. Dừng lại chờ người dùng chọn, rồi tra web kiểm tra lại các ý chính của chủ đề được chọn (ghi nguồn). Nếu người dùng chê cả loạt, hỏi họ thích ý nào nhất trong số đã đưa và vì sao, rồi đào lại theo hướng đó.

### 2. Kịch bản
- Lời đọc tiếng Anh giọng kể chuyện Mỹ, 130-170 từ (giọng AI đọc nhanh: 160 từ chỉ còn khoảng 44 giây). Câu ngắn, punchline, twist, câu chốt hài. Lời thoại của nhân vật đặt trong ngoặc kép để nhép miệng.
- Bản dịch tiếng Việt và **bảng chuỗi máy** (mục 2c): mỗi chuỗi 4-10 giây là một cú máy liền, ghi các khóa camera bên trong (khung, vị trí, điểm nhìn, ống kính), cách chuyển sang chuỗi sau, cùng nhân vật, biểu cảm, hành động, chữ nhấn, **âm thanh** và **hiệu ứng hình** (bụi, tia sốc, khung nổ, punch-in).
- Người dùng tự làm giọng đọc rồi lưu `voice.wav` vào `%USERPROFILE%\Videos\claude_test\`. Đánh dấu `[beat]` ở chỗ cần ngắt 0,5-1 giây cho gag hình.

### 2b. Tình huống và hình ảnh (bắt buộc, trước khi chốt kịch bản)
**Công thức câu chuyện:**
1. **Leo thang:** lặp sai lầm 3 lần, lần sau to hơn, lần 3 biến tấu bất ngờ.
2. **Kế hoạch hoàn hảo đổ vỡ:** khoe thứ "hoàn hảo", rồi định luật khoa học phá hỏng nó.
3. **Đối đầu:** hai đối thủ hai cách làm, chia đôi màn hình xem kết quả.
4. **Thí nghiệm ngốc nghếch:** "What if we just…", 3-4 phương án, mỗi cái hỏng một kiểu, kèm dấu ✗.
5. **Thế giới nếu khác đi:** cho thấy thế giới vô lý khi thiếu điều đó.
6. **Điều tra hiện trường:** mở bằng thảm họa, thám tử truy tìm, flashback hé lộ.
7. **Tài liệu giả:** nhân vật nói với camera, cảnh xen vạch mặt họ.

**Luật nhịp hài:**
- Hook 2 giây đầu bằng cảnh thảm họa hoặc vô lý nhất, rồi thẻ "3 DAYS EARLIER" (chuyển bằng lia nối hoặc tua ngược, không cắt cụt).
- Luật số 3: hai lần giống nhau, lần thứ ba lệch.
- Sau mỗi nhịp lớn có cảnh phản ứng (cận mặt, nhìn thẳng camera).
- Cặp nhân vật tương phản: một người nóng nảy, một người tỉnh bơ.
- Một gag chạy dọc video (con bồ câu chứng kiến, đồng hồ đếm thiệt hại) có kết ở cuối.
- Câu chốt nhắc lại chi tiết đầu video (callback), thêm một gag nhỏ sau lời giải thích (tag).
- Mật độ: ít nhất một gag hình mỗi 4-5 giây. Không cảnh nào chỉ có nhân vật đứng nói.
- Lời giải thích phải được **thấy qua hành động** (nhãn hoặc phấn vẽ trên vật thật); bảng giấy riêng chỉ là phương án phụ.

**Thư viện gag hình:**
- **Freeze-frame + thẻ tên hài:** tính tư thế theo `story_t = time_map(f)` để giữ yên 20-30 khung, nháy trắng, thẻ 2D trong `cap_root`.
- **REPLAY slow-mo hoặc tua ngược:** `time_map` chậm 3-4 lần hoặc chạy lùi, góc máy mới, vòng tròn đỏ vẽ dần, tiếng `scratch`.
- **POV:** camera trong lòng hố nhìn lên, vật rơi vào ống kính rồi đen màn hình. Cần thành hố 3D (ống trụ hở, vật liệu gạch).
- **Mặt cắt x-ray:** bối cảnh riêng dựng mặt cắt, camera nhìn ngang thấy vật rơi suốt đường.
- **Chia đôi màn hình:** hai bối cảnh sát nhau, vách đen chéo, nhãn ✓/✗.
- **Bong bóng tưởng tượng 2D** chứa cảnh mini, vỡ bằng `pop`.
- **Montage "DAY 2… DAY 47":** cùng góc máy, hậu quả chồng chất dần.
- **Phóng đại:** hóa đơn lăn khắp phố, đồng hồ "$ 4,500" hoặc "LOST: 3" nhảy số, máy tính nổ.
- **Vật lý hoạt hình:** lơ lửng 10 khung trước khi rơi, nhìn camera trước khi rơi, nảy bằng `ease_out_bounce`.
- **Kể bằng bối cảnh:** biển hiệu chơi chữ, TV chạy tin, người qua đường hoặc bồ câu quay đầu nhìn hai lần (text 3D, nhân vật phụ đơn giản).
- **Chuyển cảnh:** iris-out để kết, match cut (nắp tròn → đồng xu → mặt trăng), wipe bằng vật lướt qua ống kính.

**Góc máy:** đa dạng góc máy đến từ việc camera **di chuyển bên trong một chuỗi** (đi từ toàn cảnh xuống góc thấp, vòng qua vai rồi đẩy vào cận mặt), không phải từ việc cắt liên tục. Xem mục 2c.

**Brainstorm:**
- Mỗi câu lời đọc nghĩ 3 phương án hình (sát nghĩa, phóng đại, vô lý), chọn cái bất ngờ nhất mà vẫn hiểu trong 1 giây.
- Bảng chuỗi máy có cột "gag", "đường đi camera" và "chuyển cảnh". Cho người dùng duyệt bảng này trước khi dựng.
- Mỗi video mới có ít nhất 2 gag hoặc góc máy chưa dùng ở video trước.

### 2c. Ngữ pháp máy quay v3 (bắt buộc: đây là thứ làm video mượt và liền mạch)
Lỗi của v2: mỗi cảnh 2-4 giây tự đứng yên → chạy → đứng yên, rồi cắt sang một góc không liên quan; rung máy tính theo khung hình nên nhiễu. Kết quả là video giật và rời rạc. v3 sửa như sau:

**1. Nghĩ theo chuỗi, không theo cảnh.** Video 45-60 giây chỉ có **4-7 chuỗi** (`SEQS`). Mỗi chuỗi 4-10 giây là **một cú máy liền** trên một bối cảnh, camera không bao giờ dừng hẳn. Bên trong chuỗi đặt 2-5 khóa camera; camera đi qua các khóa theo spline mượt (Catmull-Rom), tốc độ đổi dần chứ không giật. Tối đa 2 cảnh chèn ngắn (2-3 giây, ví dụ cận mặt phản ứng) cho cả video.

**2. Camera có động cơ.** Mỗi chuyển động camera phải đi theo một thứ: nhân vật đi, vật rơi, ánh nhìn của nhân vật, hoặc hé lộ một chi tiết. Dùng `follow` để điểm nhìn trôi theo chủ thể bằng lò xo (trễ khoảng 0,2 giây), giống người quay thật bị bất ngờ.

**3. Các kiểu di chuyển trong chuỗi (kết hợp, đừng dùng một kiểu suốt video):**
- *Dolly-in chậm* vào nhân vật khi căng thẳng tăng
- *Tracking ngang* đi cùng nhân vật hoặc vật đang lăn
- *Vòng cung* (arc) 20-60° quanh nhân vật ở khoảnh khắc lớn
- *Hạ cần* (crane down) từ toàn cảnh xuống góc thấp ở đầu chuỗi
- *Kéo lùi hé lộ* (pull-back reveal) để lộ hậu quả cho gag
- Nghiêng máy (roll) tối đa ±6°, đổi dần trong chuỗi

**4. Chuyển giữa các chuỗi phải có động cơ (`TRANS`):**
- `whip`: lia nhanh cùng một hướng ở cả hai phía cắt (tăng tốc ra, giảm tốc vào, **không nảy**). Dùng khi đổi nơi chốn hoặc nhảy thời gian.
- `push`: camera lao vào một vật tối che kín khung (miệng cống, cửa, miệng nhân vật, ống) rồi chuỗi sau bắt đầu từ bóng tối lùi ra. Đẹp nhất cho "chui vào bên trong", mặt cắt x-ray.
- `match`: hình dạng ở cùng vị trí trên màn hình (nắp tròn → đồng xu → mặt trăng). Đặt vật ở cùng vị trí màn hình ở khung cuối và khung đầu.
- `cut`: cắt thường, chỉ dùng khi **cắt theo hành động** (nhân vật đang quay người, vật đang bay) và camera giữ hướng trôi giống nhau ở hai bên.
- Giữ **luật 180°**: các chuỗi trên cùng một bối cảnh để camera cùng một phía trục nhìn giữa hai nhân vật. Hướng di chuyển trên màn hình nhất quán (đi trái sang phải thì chuỗi sau vẫn trái sang phải).

**5. Zoom và rung không bao giờ giật:**
- Punch-in (`PUNCH`): đẩy ống kính 12-25% trong 6-10 khung, giữ khoảng 1,5 giây rồi nhả ra trong 24 khung, không nảy. "Snap zoom" kiểu hài (3 khung) tối đa 3 lần mỗi video, chỉ ở punchline.
- Rung tay: dao động 0,2-0,9 Hz tính theo giây (như người cầm máy thở), giảm theo ống kính dài.
- Rung va chạm (`SHAKES`): 5-9 Hz, tắt dần theo hàm mũ trong 8-14 khung, chủ yếu xoay hướng nhìn chứ không dịch vị trí.

**6. Kiểm tra bằng số trước khi render:** `cam_report()` phải in `CAMERA OK` (không chuỗi nào ngắn hơn 3 giây, gia tốc camera trong chuỗi dưới 4 mm/khung², tối đa 3 snap zoom). Xem thêm 1 khung ở giữa mỗi lần chuyển cảnh.

### 3. Canh thời gian theo giọng
- Lấy `voice.wav` về bằng `device_stage_files`.
- Thử `faster-whisper` (`word_timestamps=True`). Mạng thường chặn tải model (403); khi đó dùng ngay `align_vo.py` (mục "Công cụ phụ"): nó dò khoảng lặng rồi chia từ theo âm tiết, sao cho chỗ ngắt rơi vào dấu câu và tốc độ đọc đều. Kết quả là `WORDS = [(giây, "từ"), …]` và số khung `N`.
- In các cụm câu với thời gian, kiểm tra độ to quanh các từ quan trọng rồi chỉnh tay nếu cần. Sai số chấp nhận được khoảng 0,3 giây.
- Đổi thời gian từ sang khung hình rồi dựng **bảng chuỗi theo khung hình**: ranh giới chuỗi rơi vào chỗ ngắt câu hoặc `[beat]`, khóa camera rơi vào từ nhấn và hành động.

### 4. Dựng script (đám mây)
- Lấy script tham chiếu v2 làm khung rồi thay: `WORDS`, `N`, bối cảnh, nhân vật, `SEQS`, `TRANS`, `PUNCH`, `SHAKES` (camera v3), vị trí nhân vật, khối tư thế, `expr_table`, `reacts`, đoạn nhép miệng, đạo cụ 3D, `HIGHLIGHT`, `dust_burst`, `bake_reaction_fx`, `EVENTS`. Các bối cảnh đặt cách xa nhau (đường phố ở gốc tọa độ, văn phòng ở x=300, bảng minh họa ở x=500) rồi cắt qua lại bằng camera.
- Xem trước bằng **EEVEE**, không dùng Cycles (Cycles bỏ qua backface culling nên viền inverted hull sẽ phủ đen vật thể). Dùng `preview.py` (mục "Công cụ phụ"): khoảng 15-30 giây/khung ở 35%. Mỗi chuỗi xem khung đầu, giữa, cuối và một khung giữa lần chuyển cảnh, ghép bằng `ffmpeg hstack` rồi xem.
- Danh sách kiểm tra: `cam_report` in `CAMERA OK`; nhân vật không bị cắt, phụ đề không che miệng, hình minh họa đủ to, tay không chui vào nhân vật khác, bụi không che chữ, khung nổ vừa với chữ. In `GESTURES` và `EVENTS` ra để chắc mọi hành động lớn đều có tiếng.

### 5. Chạy trên máy người dùng
1. Đọc skill `computer-use`. Nếu Blender chưa mở: `computer_resolve_access(["Blender 5.2"])` (launcher) → request → `computer_open_application("Blender 5.2")`, đợi 8 giây, rồi resolve + request thêm `c:\program files\blender foundation\blender 5.2\blender.exe` (cửa sổ thật) với `clipboardWrite: true`. Cửa sổ thường đen 3-8 giây: rê chuột vào rồi mới chụp.
2. **Gửi script bằng file, không dán cả nội dung:** chép vào `/mnt/user-data/outputs/scene.py` rồi `device_commit_files` sang `C:\Users\<user>\Videos\claude_test\scene.py`. **Sau đó gọi `device_list_dir` và so kích thước file**: lệnh commit có thể báo thành công mà vẫn giữ bản cũ; nếu sai thì commit lại với `force: true`.
3. Trong Blender: click ra ngoài để tắt màn hình chào → tab **Scripting** → click vào Python Console. `computer_write_clipboard` một dòng rồi `ctrl+v` và Enter (không gõ trực tiếp vì bộ gõ Unikey làm sai chữ):
   `exec(open(r"C:\Users\<user>\Videos\claude_test\scene.py", encoding="utf-8").read())`
   Đợi khoảng 50 giây, zoom vào console để thấy dòng `SCENE READY`.
4. **Đo tốc độ trước khi render cả video:** `import time; bpy.context.scene.frame_set(A); bpy.ops.render.render(); bpy.context.scene.frame_set(B); t0=time.time(); bpy.ops.render.render(); print(round(time.time()-t0,1))`. Lần đầu luôn chậm (khoảng 40 giây biên dịch shader), **lần thứ hai mới là tốc độ thật**. Mục tiêu dưới 2 giây/khung; nếu chậm hơn thì tắt từng tính năng để tìm thủ phạm (Freestyle từng làm mỗi khung mất 44 giây). Không dùng `write_still` khi output là video.
5. Rê chuột vào vùng 3D, nhấn `ctrl+f12`. Cửa sổ Render có thể đứng hình trống, đó là bình thường. Theo dõi bằng `device_list_dir` (file mp4 lớn dần, mtime mới), đợi bằng `Bash sleep … run_in_background` thay vì chuỗi `computer_wait`. Có thể `computer_release_lock` để người dùng dùng máy trong lúc render. Khi mtime đứng yên hơn 1 phút là render đã xong.
6. Nếu kết nối tới máy bị ngắt thì quyền truy cập ứng dụng mất nhưng Blender vẫn render; chỉ cần kiểm tra file. Đừng gọi `computer_open_application` khi cửa sổ Claude đang được focus, vì có thể mở thêm một Blender trống; nếu thấy Blender trống (có khối lập phương mặc định) thì rê chuột vào nó và nhấn `ctrl+q`.
7. Xong thì `device_stage_files` mp4 → ffprobe (đủ số khung, có audio, volumedetect) → ghép 10 khung xem → `SendUserFile` → `computer_release_lock`.
- Script không gọi `read_factory_settings` khi chạy trong giao diện (template xử lý qua biến `CLOUD`), và tự xóa cảnh cũ nên có thể chạy lại nhiều lần.

### 6. Bộ công cụ v2: dùng Blender để video đẹp và sống động hơn
**Hình ảnh (`setup_look`):**
- Viền hoạt hình cho bối cảnh 3D bằng **inverted hull**: modifier Solidify lật pháp tuyến, vật liệu đen có backface culling, chạy trên GPU. Template tự áp cho mọi mesh trừ collection `NOLINE` (nhân vật, phụ đề, hình minh họa, bụi). **Không dùng Freestyle** (chạy bằng CPU, chậm khoảng 30 lần).
- Compositor (Blender 5: `scene.compositing_node_group` cùng `NodeGroupOutput`, `ShaderNodeMix`, `ShaderNodeMath`):
  - Glare Bloom nhẹ
  - Sương xa (Mist pass) tạo chiều sâu cho phố
  - Saturation 1,1 và contrast nhẹ
  - Làm tối viền khung hình bằng EllipseMask + Blur
- Motion blur EEVEE `motion_blur_position = 'START'`, kèm **hold key** (keyframe phụ ở `f + 0.98`) ở cuối mỗi cảnh và mỗi lần nhân vật/đạo cụ dịch chuyển tức thời, để không bị vệt mờ xuyên cảnh.
- **Không bật DOF**, vì phụ đề nằm sát ống kính và sẽ bị nhòe.

**Chuyển động nhân vật:**
- `pease(f, start, n)` (ease-out-back) cho mọi động tác tay: có đà và nảy nhẹ. `ease` chỉ dùng cho camera.
- Cẳng tay tự trễ khi bắp tay quay nhanh (follow-through), đầu nghiêng trễ theo thân, thân đung đưa nhẹ khi đứng yên, thở. Tất cả có sẵn trong `pose_char` v2.
- Tay dùng IK: `('ik', (x, y), bend)` theo tọa độ thân để tay cầm đúng đạo cụ.
- Phản ứng có co giãn (`c.reacts`):
  - `hop`: giật mình bật lên, có lấy đà và co giãn khi rời đất và khi tiếp đất
  - `flinch`: giật lùi rồi lò xo về
  - `shiver`: run
  - `proud`: ưỡn ngực
- Mỗi lần sốc dùng thêm `bake_reaction_fx(c, [frames])`: tia sốc quanh đầu và dấu "!" bật lên.
- Nhép miệng: `add_talk_mouth(c)` + `bake_talk(c, ranges, AMP)`. Độ mở miệng lấy từ độ to của `voice.wav` (`load_amplitude`) trong các đoạn lời thoại; đầu gật theo giọng (`c.amp_now`).
- Chớp mắt keyframe **mọi khung** (nếu chỉ key lúc thay đổi, mắt sẽ từ từ híp lại).
- Đi bộ: `walk_legs(phase)`, thân nhún, bụi nhỏ dưới vật đang lăn.

**Camera (module "Camera v3", thay hoàn toàn camera v2):**
- `solve_camera(SEQS, TRANS, PUNCH, SHAKES)` tính mọi khung: spline C1 qua các khóa, lò xo cho điểm nhìn, chuyển cảnh whip/push/match/cut, punch-in mượt, rung tay theo Hz.
- `bake_camera(cam, cam_d, CAM, cuts)`: keyframe mọi khung kiểu LINEAR, tự tính hướng quay và roll (bỏ TRACK_TO), thêm hold key ở `f+0.98` trước mỗi lần cắt để motion blur không vệt xuyên cảnh. Trả về `LENS_F` cho phụ đề.
- Đã đo trên cùng một video 45 giây: v2 có gia tốc camera khoảng 114 mm/khung² (rung theo khung) và 67 khung camera đứng khựng; v3 dưới 1,5 mm/khung² trong chuỗi và chỉ khựng ở đầu video.
- Phụ đề vẫn bù theo tiêu cự từng khung (`LENS_F`) nên punch-in không làm chữ to ra.

**Hiệu ứng hình:**
- `dust_burst(frame, pos, …)` + `bake_dust()`: bụi hoạt hình dùng chung một bể đối tượng. Dùng mỗi khi có va chạm, tiếp đất, lăn, nhảy ra khỏi hố.
- Khung nổ truyện tranh tự động phía sau phụ đề có chữ CLANG (có thể thêm cho BAM, POW…).
- Phụ đề nảy vào (ease-out-back), nghiêng ngẫu nhiên; từ nhấn tô vàng, to 1,3 lần và lắc khi hiện.

**Luật chuyển động (bắt buộc kiểm tra trước khi render):**
1. Không có khung nào camera đứng yên giữa chuỗi; tốc độ camera chỉ đổi dần (spline), không dừng-chạy-dừng.
2. Mỗi từ nhấn phải có ít nhất một trong các thứ: punch-in, phản ứng hoặc động tác.
3. Mỗi va chạm phải có đủ: tiếng động, bụi, rung máy và biểu cảm của nhân vật gần đó.
4. Mỗi động tác tay phải có overshoot (`pease`) và tiếng `swish` (tự động).
5. Nhân vật nào nói lời thoại thì phải nhép miệng.
6. Mỗi lần chuyển chuỗi có một kiểu trong `TRANS` và lý do (đổi nơi, nhảy thời gian, chui vào trong, hình giống nhau); `cam_report` in `CAMERA OK`.

### 7. Âm thanh theo hành động (bắt buộc)
Có 22 hiệu ứng tổng hợp bằng numpy, không vướng bản quyền. Các tiếng tự động gắn vào:
- chuyển chuỗi `whip` hoặc `push` → `whoosh` canh vào khung giữa cú lia (bỏ qua nếu sát tiếng CLANG); `match` → `pop` nhẹ hoặc không tiếng
- đổi biểu cảm → `pop`
- mỗi chữ phụ đề → `tick`
- bắt đầu một động tác tay → `swish` (dò từ `c.hist`)

Khi có giọng đọc: nhạc nền khoảng 0,10, hiệu ứng nhân 0,8, strip `sfx_music` đặt volume 0,8. Kiểm tra bằng `volumedetect`: giọng đọc nên to hơn nền khoảng 8 dB.

Các tiếng theo câu chuyện thì đặt tay trong `EVENTS = [(frame, "tên", gain)]`:

| Hành động | Hiệu ứng |
|---|---|
| Bước đi, chạy (mỗi lần chân chạm đất) | `step` |
| Nhảy, bật lên, ngạc nhiên kiểu lò xo | `boing` |
| Trượt chân, bị hất lên | `slide_up` |
| Rơi, xì hơi, thất vọng | `slide_down` |
| Ngã xuống đất, vật nặng rơi | `thud` |
| Bị đập vào đầu | `bonk` |
| Tức giận, mặt đỏ | `rumble` + `steam` |
| Giật mình nhẹ, mắt mở to | `squeak` |
| Nuốt nước bọt, lo lắng | `gulp` |
| Lóe ý tưởng, nháy mắt, đúng rồi | `ding` |
| Chạy vụt ra khỏi khung | `zip_out` |
| Đổ vỡ, tàu trật bánh | `crash` |
| "Khoan đã…?" | `scratch` |
| Tàu hỏa | `horn`, `chug` (nền) |
| Tiền, lợi nhuận | `cash` |
| Thất bại ở cuối | `sad_trombone` |

Gain gợi ý: hiệu ứng chính 0,4-0,6; swish/pop 0,25-0,3; tick 0,1. Nhạc nền `music_bed(TOTAL, mood)` với mood là `playful`, `sneaky` hoặc `tense`, gain khoảng 0,16, và tự giảm âm lượng (`duck`) ở đoạn cao trào. Nếu có giọng đọc thì hạ nhạc xuống khoảng 0,10 và hiệu ứng khoảng 0,8 lần.

### 8. Quy tắc thiết kế
- Đạo cụ cầm tay là hình 2D trong mặt phẳng nhân vật (`prop_round`, `prop_square`); đạo cụ rơi, lăn, nằm đất là 3D; đổi qua lại ngay tại khung hành động.
- Hình minh họa: bảng giấy riêng (x=500) với hình 2D lớn, mũi tên, nhãn. Camera lens 45 ở khoảng cách 7,7; phụ đề dời thấp (y = -0,55) trong các cảnh này.
- Cảnh cận mặt: hạ điểm nhìn để mặt nằm cao hơn phụ đề.
- Thư viện biểu cảm v2 (`build_faces`): neutral, happy, smirk, wink, angry, shock, worried, grumpy, focus, smug_closed.
- Nhân vật: đầu tròn r khoảng 0,5, thân bo góc to gần bằng đầu, chân ngắn (0,36 + 0,34), tay mảnh, bàn tay tròn trắng, viền đen 0,035. Mỗi nhân vật có một món đồ nhận diện (mũ, cà vạt, kính…) và màu riêng. Màu emission phải đậm vì giá trị là linear: cam là (0.98, 0.30, 0.02), xanh là (0.03, 0.22, 0.55).
- Biểu cảm là các nhóm object bật/tắt bằng keyframe `hide_render`. Mỗi nhân vật nên có tối thiểu: bình thường, vui, nhếch mép hoặc nháy mắt, tức hoặc sốc. Có chớp mắt.
- Bối cảnh 3D dùng vật liệu thật (Principled) và ánh nắng; nhân vật dùng Emission để giữ màu phẳng nhưng vẫn đổ bóng.
- Camera: theo mục 2c. Mỗi chuỗi 4-10 giây, góc hơi thấp (ngang ngực nhân vật), luôn trôi; rung máy khi có va chạm hoặc nổi giận bằng `SHAKES`.
- Phụ đề: 1-2 chữ mỗi lần, chữ trắng viền đen, từ khóa tô vàng và to hơn 1,35 lần, đặt hơi dưới giữa màn hình.
- Không vẽ nhân vật có bản quyền, không chép thiết kế nhân vật của kênh mẫu.

### 9. Giao kết quả
Gửi mp4 kèm 1-2 câu: đã làm gì, render mất bao lâu, file nằm ở đâu trên máy, và một bước tiếp theo. Nói rõ nếu phụ đề được canh bằng dạng sóng (có thể lệch khoảng 0,3 giây).

## Công cụ phụ

### `align_vo.py` (canh phụ đề không cần model)
```python
# usage: python3 align_vo.py voice.wav script.txt > words_literal.py
import re, sys, wave, math
import numpy as np
from functools import lru_cache

wav, txt_path = sys.argv[1], sys.argv[2]
w = wave.open(wav); sr = w.getframerate(); ch = w.getnchannels()
x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float)
if ch > 1: x = x.reshape(-1, ch).mean(axis=1)
x /= 32768; DUR = len(x) / sr
hop = int(sr * 0.02); n = len(x) // hop
db = np.array([20 * math.log10(math.sqrt(np.mean(x[i * hop:(i + 1) * hop] ** 2)) + 1e-6) for i in range(n)])
quiet = db < np.percentile(db, 20) + 6                        # pauses: quiet runs >= 0.18 s
gaps = []; i = 0
while i < n:
    if quiet[i]:
        j = i
        while j < n and quiet[j]: j += 1
        if (j - i) * 0.02 >= 0.18: gaps.append((i * 0.02, j * 0.02))
        i = j
    else: i += 1

text = open(txt_path).read().replace("\n", " ")
toks = re.findall(r"[A-Za-z0-9'’]+[^\sA-Za-z0-9]*", text)
def syl(t):
    t = re.sub(r"[^a-z]", "", t.lower())
    if not t: return 1
    s = len(re.findall(r"[aeiouy]+", t))
    if t.endswith("e") and not t.endswith(("le", "ee")) and s > 1: s -= 1
    return max(1, s)
words = [(t, syl(t), bool(re.search(r'[.,?!…"]', t))) for t in toks]
S = np.concatenate([[0], np.cumsum([w_[1] for w_ in words])])
segs = []; t0 = 0.0
for a, b in gaps:
    if a > t0: segs.append((t0, a))
    t0 = b
if t0 < DUR: segs.append((t0, DUR))
mean_rate = S[-1] / sum(b - a for a, b in segs)
P = [k for k, w_ in enumerate(words) if w_[2] and k < len(words) - 1]   # punctuation = candidate pause
G = gaps[:-1] if gaps and gaps[-1][1] > DUR - 0.1 else gaps
end_speech = gaps[-1][0] if gaps and gaps[-1][1] > DUR - 0.1 else DUR
def cost(k0, k1, a, b):
    s = S[k1 + 1] - S[k0]; return s * math.log((s / max(b - a, 0.05)) / mean_rate) ** 2
@lru_cache(None)
def best(pi, gi):                                             # even speaking rate, pauses land on punctuation
    k0 = P[pi] + 1 if pi >= 0 else 0; t_ = G[gi][1] if gi >= 0 else 0.0
    res = (cost(k0, len(words) - 1, t_, end_speech) + 0.6 * (len(G) - 1 - gi), None)
    for pj in range(pi + 1, len(P)):
        for gj in range(gi + 1, len(G)):
            c = cost(k0, P[pj], t_, G[gj][0]) + 0.6 * (gj - gi - 1)
            if c > res[0]: continue
            tot = best(pj, gj)[0] + c
            if tot < res[0]: res = (tot, (pj, gj))
    return res
chain = []; st = (-1, -1)
while best(*st)[1] is not None:
    st = best(*st)[1]; chain.append(st)
out = []; k0 = 0; ta = 0.0
for pj, gj in chain + [(None, None)]:
    k1 = P[pj] if pj is not None else len(words) - 1
    tb = G[gj][0] if gj is not None else end_speech
    s = S[k1 + 1] - S[k0]; t_ = ta
    for k in range(k0, k1 + 1):
        out.append((round(float(t_), 2), words[k][0])); t_ += (tb - ta) * words[k][1] / s
    print(f"# {ta:5.2f}-{tb:5.2f}  {' '.join(w_[0] for w_ in words[k0:k1 + 1])}", file=sys.stderr)
    if pj is None: break
    k0 = k1 + 1; ta = G[gj][1]
print("WORDS = " + repr(out))
print(f"# voice duration {DUR:.2f}s -> N = {int(math.ceil((DUR + 1.2) * 30))} frames", file=sys.stderr)
```

### `preview.py` (xem trước bằng EEVEE trong đám mây)
```python
import bpy, sys, time
exec(open('scene.py').read())
sc = bpy.context.scene
args = sys.argv[sys.argv.index('--') + 1:]
sc.render.resolution_percentage = int(args[1]) if len(args) > 1 else 35
sc.eevee.taa_render_samples = 16
sc.render.image_settings.media_type = 'IMAGE'; sc.render.image_settings.file_format = 'PNG'
for fr in [int(x) for x in args[0].split(',')]:
    t0 = time.time(); sc.frame_set(fr); sc.render.filepath = f'out/p_{fr:04d}.png'
    bpy.ops.render.render(write_still=True); print("FRAME", fr, round(time.time() - t0, 1), "s")
# python3 preview.py -- 50,200,366,640 35
```

## Module v2 (dán vào script sau phần camera và 2D toolkit, trước phần nhân vật)
Cần thêm `from mathutils import Matrix` và `re` vào phần import.

```python
# ---------------- easing ----------------
def clamp01(u): return max(0.0, min(1.0, u))
def ease(u): u = clamp01(u); return u * u * (3 - 2 * u)
def ease_out_back(u, s=1.4):                 # overshoot then settle: gestures, pops, punch-ins
    u = clamp01(u) - 1; return u * u * ((s + 1) * u + s) + 1
def ease_out_elastic(u):
    u = clamp01(u)
    if u in (0.0, 1.0): return u
    return 2 ** (-10 * u) * math.sin((u * 10 - 0.75) * (2 * math.pi) / 3) + 1
def pease(f, a, n=8): return ease_out_back((f - a) / n)     # pose transition with overshoot
def noise1(t, seed=0.0):
    return (math.sin(t * 1.3 + seed) * 0.5 + math.sin(t * 2.7 + seed * 1.7) * 0.3 + math.sin(t * 5.1 + seed * 2.3) * 0.2)

# ---------------- voice amplitude (lip flap, head bobs) ----------------
def load_amplitude(path, n_frames, fps):
    amp = [0.0] * (n_frames + 2)
    try:
        with wave.open(path, "rb") as w:
            sr = w.getframerate(); ch = w.getnchannels(); sw = w.getsampwidth()
            raw = w.readframes(w.getnframes())
        x = np.frombuffer(raw, dtype=np.int16 if sw == 2 else np.int32).astype(np.float64)
        if ch > 1: x = x.reshape(-1, ch).mean(axis=1)
        x /= np.abs(x).max() + 1e-9
        hop = sr / fps
        for f in range(1, n_frames + 1):
            seg = x[int((f - 1) * hop):int(f * hop)]
            if len(seg):
                db = 20 * math.log10(math.sqrt(float(np.mean(seg ** 2))) + 1e-6)
                amp[f] = clamp01((db + 38) / 26)
    except Exception as e:
        for f in range(1, n_frames + 1):
            amp[f] = clamp01(0.5 + 0.5 * math.sin(f * 1.9) * math.sin(f * 0.7))
    return amp

# ---------------- dust puffs (pooled billboards) ----------------
PUFF_M = flat("puff_fill", (0.93, 0.90, 0.85))
PUFF_POOL = []; PUFF_EVENTS = []
def _make_puff(i):
    root = empty(f"puff_root{i}", None, (0, 0, -20))
    lt = root.constraints.new('LOCKED_TRACK'); lt.target = cam; lt.track_axis = 'TRACK_NEGATIVE_Y'; lt.lock_axis = 'LOCK_Z'
    pl = empty(f"puff_pl{i}", root); pl.rotation_euler = (math.pi / 2, 0, 0)
    for k, (dx_, dy_, r) in enumerate(((0, 0, 0.12), (0.09, 0.05, 0.09), (-0.08, 0.06, 0.08))):
        shape(pl, f"puff{i}_{k}", ellipse(dx_, dy_, r, r, 18), PUFF_M, 0.01 * k, outline=0.022)
    root.scale = (0, 0, 0)
    return root
def dust_burst(frame, pos, n=8, radius=0.7, size=1.0, life=20, rise=0.35):
    rnd = random.Random(frame * 7 + int(pos[0] * 13))
    for k in range(n):
        a = 2 * math.pi * k / n + rnd.uniform(-0.3, 0.3)
        PUFF_EVENTS.append((frame + rnd.randint(0, 2), pos, (math.cos(a), math.sin(a)), radius * rnd.uniform(0.7, 1.2),
                            size * rnd.uniform(0.7, 1.3), life + rnd.randint(-3, 4), rise * rnd.uniform(0.6, 1.4)))
def bake_dust():
    busy = []
    for ev in sorted(PUFF_EVENTS):
        f0, pos, d, rad, sz, life, rise = ev
        idx = next((i for i, (p, free) in enumerate(busy) if free < f0 - 2), None)
        if idx is None:
            PUFF_POOL.append(_make_puff(len(PUFF_POOL))); busy.append((len(PUFF_POOL) - 1, 0)); idx = len(busy) - 1
        pidx = busy[idx][0]; busy[idx] = (pidx, f0 + life + 1); o = PUFF_POOL[pidx]
        o.scale = (0, 0, 0); o.keyframe_insert("scale", frame=max(1, f0 - 1))
        for f in range(f0, min(N, f0 + life) + 1):
            u = (f - f0) / life; e = ease_out_back(u * 1.6, 1.0) if u < 0.62 else 1.0
            s = sz * (0.35 + 0.9 * e) * (1 - ease((u - 0.55) / 0.45))
            o.location = (pos[0] + d[0] * rad * ease(u * 1.3), pos[1] + d[1] * rad * ease(u * 1.3), pos[2] + 0.08 + rise * ease(u))
            o.scale = (s, s, s); o.keyframe_insert("scale", frame=f); o.keyframe_insert("location", frame=f)
        if f0 + life + 1 <= N:
            o.scale = (0, 0, 0); o.keyframe_insert("scale", frame=f0 + life + 1)

# ---------------- shock lines + "!" ----------------
def add_reaction_fx(c):
    sl = empty(c.name + "_speedlines", c.head, (0, 0, -0.3))
    for k in range(16):
        a = 2 * math.pi * k / 16; r0, r1 = 0.62, 0.95 + 0.12 * (k % 2); w_ = 0.035
        p0 = (r0 * math.cos(a), r0 * math.sin(a)); p1 = (r1 * math.cos(a), r1 * math.sin(a))
        nx, ny = -math.sin(a) * w_, math.cos(a) * w_
        shape(sl, f"{c.name}_sl{k}", [(p0[0] + nx * 0.3, p0[1] + ny * 0.3), (p1[0] + nx, p1[1] + ny), (p1[0] - nx, p1[1] - ny), (p0[0] - nx * 0.3, p0[1] - ny * 0.3)], INK, 0, outline=0)
    sl.scale = (0, 0, 0); c.speedlines = sl
    ex = empty(c.name + "_excl", c.head, (0.58, 0.62, 0.4))
    for layer, (m, off, z) in enumerate(((INK, 0.05, -0.01), (flat("excl_red", (0.92, 0.1, 0.08)), 0.0, 0.0))):
        cu = bpy.data.curves.new(f"{c.name}_ex{layer}", 'FONT'); cu.body = "!"; cu.size = 0.45; cu.offset = off
        cu.align_x = 'CENTER'; cu.align_y = 'CENTER'
        if FONT_PATH: cu.font = bpy.data.fonts.load(FONT_PATH, check_existing=True)
        o = bpy.data.objects.new(f"{c.name}_ex{layer}", cu); col.objects.link(o); o.parent = ex; o.location = (0, 0, z)
        o.rotation_euler = (0, 0, -0.2); o.data.materials.append(m)
    ex.scale = (0, 0, 0); c.excl = ex
def bake_reaction_fx(c, frames, dur=16):
    for o_ in (c.speedlines, c.excl):
        o_.scale = (0, 0, 0); o_.keyframe_insert("scale", frame=1)
    for f0 in frames:
        for f in range(f0, min(N, f0 + dur) + 1):
            u = (f - f0) / dur
            s_l = ease_out_back(u * 4, 2.0) * (1 - ease((u - 0.6) / 0.4))
            c.speedlines.scale = (s_l, s_l, 1); c.speedlines.rotation_euler = (0, 0, 0.15 * math.sin(f * 1.3))
            s_e = ease_out_back(u * 3, 2.2) * (1 - ease((u - 0.75) / 0.25))
            c.excl.scale = (s_e, s_e, 1); c.excl.location = (0.58, 0.62 + 0.08 * ease(u), 0.4)
            for o_ in (c.speedlines, c.excl): o_.keyframe_insert("scale", frame=f)
            c.speedlines.keyframe_insert("rotation_euler", frame=f); c.excl.keyframe_insert("location", frame=f)
        for o_ in (c.speedlines, c.excl):
            o_.scale = (0, 0, 0); o_.keyframe_insert("scale", frame=min(N, f0 + dur + 1))

# ---------------- talking mouth ----------------
def add_talk_mouth(c, ey=-0.02):
    g = empty(c.name + "_talk", c.head, (0, 0, 0.14))
    shape(g, c.name + "_talk_patch", ellipse(0, ey - 0.17, 0.22, 0.12, 24), c.skin, 0, outline=0)
    piv = empty(c.name + "_talk_piv", g, (0, ey - 0.17, 0.02))
    shape(piv, c.name + "_talk_m", ellipse(0, 0, 0.12, 0.10, 24), MOUTH, 0, outline=0.03)
    shape(piv, c.name + "_talk_t", ellipse(0, -0.05, 0.06, 0.035, 16), TONGUE, 0.02, outline=0)
    shape(piv, c.name + "_talk_teeth", rrect(0, 0.065, 0.14, 0.035, 0.01), TEETH, 0.02, outline=0)
    c.talk = g; c.talk_piv = piv
def bake_talk(c, ranges, amp):            # needs vis_track() from the animation part
    vis_track(c.talk, ranges)
    for f in range(1, N + 1):
        on = any(a <= f <= b for a, b in ranges)
        o = 0.18 + 0.82 * amp[f] if on else 0.2
        c.talk_piv.scale = (0.9 + 0.15 * o, o, 1); c.talk_piv.keyframe_insert("scale", frame=f)

# ---------------- reactions (squash & stretch) ----------------
def react_offsets(c, f):
    dy, sy, lean = 0.0, 1.0, 0.0
    for t0, kind in getattr(c, "reacts", []):
        if kind == "hop" and t0 - 4 <= f <= t0 + 16:
            if f < t0: sy -= 0.10 * ease((f - (t0 - 4)) / 4)
            else:
                u = (f - t0) / 16
                dy += 0.22 * math.sin(math.pi * min(1, u / 0.8)) if u < 0.8 else 0.0
                if u < 0.25: sy += 0.12 * (1 - u / 0.25)
                elif u > 0.8: sy -= 0.12 * math.sin(math.pi * (u - 0.8) / 0.2)
        elif kind == "flinch" and t0 <= f <= t0 + 20:
            u = (f - t0) / 20; lean += -0.18 * (1 - ease_out_elastic(u)); sy -= 0.05 * (1 - ease(u))
        elif kind == "shiver" and t0 <= f <= t0 + 30:
            lean += 0.04 * math.sin(f * 2.4) * (1 - (f - t0) / 30)
        elif kind == "proud" and t0 <= f <= t0 + 14:
            u = (f - t0) / 14; sy += 0.07 * math.sin(math.pi * u); dy += 0.04 * math.sin(math.pi * u)
    return dy, sy, lean

# ---------------- pose_char v2 (replaces v1; arms accept ('ang', a1, a2) or ('ik', (x, y), bend)) ----------------
def ik(sh, tgt, L1, L2, bend=1):
    dx, dy = tgt[0] - sh[0], tgt[1] - sh[1]
    d = max(min(math.hypot(dx, dy), L1 + L2 - 1e-3), abs(L1 - L2) + 1e-3)
    base = math.atan2(dx, -dy)
    off = math.acos(max(-1, min(1, (L1 * L1 + d * d - L2 * L2) / (2 * L1 * d))))
    a1 = base + bend * off
    ex, ey_ = sh[0] + L1 * math.sin(a1), sh[1] - L1 * math.cos(a1)
    return a1, math.atan2(tgt[0] - ex, -(tgt[1] - ey_)) - a1
def pose_char(c, f, armL=None, armR=None, legL=(-0.06, 0.02), legR=(0.06, -0.02), head_tilt=0.0, body=(0, 0), breath=True, lean=0.0):
    if not hasattr(c, "prev"): c.prev = {}; c.vel = {}
    for side, spec, lp in (("L", armL, c.armL), ("R", armR, c.armR)):
        if spec is None: spec = ('ang', -0.25 if side == "L" else 0.25, 0.1 if side == "L" else -0.1)
        a1, a2 = ik(c.sh[side], spec[1], c.aL[0], c.aL[1], spec[2]) if spec[0] == 'ik' else (spec[1], spec[2])
        v = a1 - c.prev.get(side, a1); c.vel[side] = 0.55 * c.vel.get(side, 0.0) + 0.45 * v; c.prev[side] = a1
        a2 = a2 - max(-0.5, min(0.5, 1.6 * c.vel[side]))            # forearm drags behind
        lp[0].rotation_euler = (0, 0, a1); lp[1].rotation_euler = (0, 0, a2)
        lp[0].keyframe_insert("rotation_euler", frame=f); lp[1].keyframe_insert("rotation_euler", frame=f)
        c.hist.setdefault(side, []).append((f, a1 + 0.5 * a2))
    for spec, lp in ((legL, c.legL), (legR, c.legR)):
        lp[0].rotation_euler = (0, 0, spec[0]); lp[1].rotation_euler = (0, 0, spec[1])
        lp[0].keyframe_insert("rotation_euler", frame=f); lp[1].keyframe_insert("rotation_euler", frame=f)
    t = f / FPS
    dy, sy, rlean = react_offsets(c, f)
    b = (1 + (0.014 * math.sin(t * 2.4 + len(c.name)) if breath else 0)) * sy
    sway = 0.02 * noise1(t * 0.8, len(c.name))
    c.body.scale = (1 / math.sqrt(b), b, 1); c.body.location = (body[0], body[1] + dy, 0)
    c.body.rotation_euler = (0, 0, lean + rlean + sway)
    c.body.keyframe_insert("scale", frame=f); c.body.keyframe_insert("location", frame=f); c.body.keyframe_insert("rotation_euler", frame=f)
    lag = getattr(c, "lag_tilt", 0.0)
    c.lag_tilt = lag + 0.35 * (-(lean + rlean) * 0.6 - lag)
    talk = getattr(c, "amp_now", 0.0)
    c.head.rotation_euler = (0, 0, head_tilt + 0.03 * math.sin(t * 1.7) + c.lag_tilt + 0.05 * talk * math.sin(f * 0.9))
    c.head.keyframe_insert("rotation_euler", frame=f)

# ---------------- film look + GPU outlines ----------------
INK_HULL = None
def add_ink_outlines(objs):
    global INK_HULL
    if INK_HULL is None:
        INK_HULL = bpy.data.materials.new("ink_hull"); INK_HULL.use_nodes = True
        nt = INK_HULL.node_tree; nt.nodes.clear()
        e = nt.nodes.new("ShaderNodeEmission"); e.inputs[0].default_value = (0.05, 0.04, 0.04, 1)
        o_ = nt.nodes.new("ShaderNodeOutputMaterial"); nt.links.new(e.outputs[0], o_.inputs[0])
        INK_HULL.use_backface_culling = True
    done = set()
    for o in objs:
        dims = o.dimensions
        if max(dims) > 150 or min(dims) < 0.003 and max(dims) > 50: continue    # ground planes
        if o.data.name in done or o.data.users > 1: continue
        if not any(m.type in ('ARRAY', 'DISPLACE', 'SUBSURF') for m in o.modifiers) and tuple(o.scale) != (1.0, 1.0, 1.0):
            o.data.transform(Matrix.Diagonal((*o.scale, 1.0))); o.scale = (1, 1, 1)
        size = max(o.dimensions)
        t = 0.012 if size < 0.6 else 0.02 if size < 2.5 else 0.045 if size < 20 else 0.25
        o.data.materials.append(INK_HULL)
        sol = o.modifiers.new("ink", 'SOLIDIFY'); sol.thickness = t; sol.offset = 1.0
        sol.use_flip_normals = True; sol.material_offset = len(o.data.materials) - 1; sol.use_rim = False
        done.add(o.data.name)
def setup_look(noline_objs):
    vl = sc.view_layers[0]
    nol = bpy.data.collections.new("NOLINE"); sc.collection.children.link(nol)
    for o in noline_objs:
        if o.name not in nol.objects: nol.objects.link(o)
        if o.name in col.objects: col.objects.unlink(o)
    sc.render.use_freestyle = False
    add_ink_outlines([o for o in sc.objects if o.type == 'MESH' and o.name not in nol.objects])
    sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.45; sc.render.motion_blur_position = 'START'
    vl.use_pass_mist = True
    sc.world.mist_settings.start = 14; sc.world.mist_settings.depth = 110; sc.world.mist_settings.falloff = 'QUADRATIC'
    ng = bpy.data.node_groups.new("FilmLook", 'CompositorNodeTree')
    ng.interface.new_socket("Image", in_out='OUTPUT', socket_type='NodeSocketColor')
    n = ng.nodes; L = ng.links
    rl = n.new('CompositorNodeRLayers')
    gl = n.new('CompositorNodeGlare'); gl.inputs["Type"].default_value = 'Bloom'
    gl.inputs["Threshold"].default_value = 0.92; gl.inputs["Strength"].default_value = 0.35; gl.inputs["Size"].default_value = 0.6
    mist = n.new('ShaderNodeMix'); mist.data_type = 'RGBA'; mist.blend_type = 'MIX'
    mfac = n.new('ShaderNodeMath'); mfac.operation = 'MULTIPLY'; mfac.inputs[1].default_value = 0.45
    hs = n.new('CompositorNodeHueSat'); hs.inputs["Saturation"].default_value = 1.10
    bc = n.new('CompositorNodeBrightContrast'); bc.inputs["Contrast"].default_value = 6.0
    em = n.new('CompositorNodeEllipseMask'); em.inputs["Size"].default_value = (1.05, 1.15)
    bl = n.new('CompositorNodeBlur'); bl.inputs["Size"].default_value = (180, 180)
    inv = n.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
    vf = n.new('ShaderNodeMath'); vf.operation = 'MULTIPLY'; vf.inputs[1].default_value = 0.38
    vig = n.new('ShaderNodeMix'); vig.data_type = 'RGBA'; vig.blend_type = 'MULTIPLY'
    vig.inputs[7].default_value = (0.0, 0.0, 0.0, 1.0)
    out = n.new('NodeGroupOutput')
    L.new(rl.outputs["Image"], gl.inputs["Image"])
    L.new(rl.outputs["Mist"], mfac.inputs[0]); L.new(mfac.outputs[0], mist.inputs[0])
    L.new(gl.outputs["Image"], mist.inputs[6]); mist.inputs[7].default_value = (0.78, 0.86, 0.95, 1.0)
    L.new(mist.outputs[2], hs.inputs["Image"]); L.new(hs.outputs["Image"], bc.inputs["Image"])
    L.new(em.outputs["Mask"], bl.inputs["Image"]); L.new(bl.outputs["Image"], inv.inputs[1]); L.new(inv.outputs[0], vf.inputs[0])
    L.new(vf.outputs[0], vig.inputs[0]); L.new(bc.outputs["Image"], vig.inputs[6])
    L.new(vig.outputs[2], out.inputs[0])
    sc.compositing_node_group = ng
def descendants(o): return [o] + list(o.children_recursive)

# ---------------- motion-blur hold keys (Blender 5 layered actions) ----------------
def fcurves_of(idb):
    ad = idb.animation_data
    if not ad or not ad.action: return []
    act = ad.action
    if hasattr(act, "fcurves"): return list(act.fcurves)
    out_ = []
    for layer in act.layers:
        for strip in layer.strips:
            cb = strip.channelbag(ad.action_slot)
            if cb: out_ += list(cb.fcurves)
    return out_
def add_teleport_holds(objs, thr=0.6):
    for o in objs:
        for fc in fcurves_of(o):
            if fc.data_path != "location": continue
            pts = sorted((kp.co[0], kp.co[1]) for kp in fc.keyframe_points)
            for (f0, v0), (f1, v1) in zip(pts, pts[1:]):
                if f1 - f0 >= 0.99 and abs(v1 - v0) > thr:
                    fc.keyframe_points.insert(f0 + 0.98, v0, options={'FAST'})
            fc.update()
```

## Module camera v3 (dán sau module v2; đã chạy thật trên Blender 5.2.3 với template ở dưới)

```python
# ---------------- camera v3: smooth one-take rig ----------------
# Replaces the v2 per-shot camera loop (SHOTS + ease + sin shake + ease_out_back punch/whip).
# Idea: a video is a few SEQUENCES (one continuous camera move each, on one set).
# Inside a sequence the camera never stops and never cuts: it glides along a C1 spline
# through key poses. Between sequences there is one motivated TRANSITION.
#
# SEQS = [
#   dict(a=1, b=210, keys=[  # (frame, cam_pos, look_pos, lens, roll_deg)
#        (1,   (-3.0, -1.0, 1.0), (0, 5, 1.4), 28, 0),
#        (90,  (-1.2,  1.5, 1.2), (0, 5, 1.5), 32, 0),
#        (210, ( 1.5,  2.2, 1.6), (0.6, 5.2, 1.6), 34, -4)],
#        follow=None,           # optional: fn(f) -> (x,y,z) subject the eye drifts toward
#        follow_w=0.35,         # 0..1 how much the look point leans toward the subject
#        ease_in=True, ease_out=False),   # ease only at video start/end or before a 'hold'
#   ...]
# TRANS = {cut_frame: ('whip', +1) | ('push',) | ('match',) | ('cut',)}   cut_frame = first frame of next seq
# PUNCH = [(frame, mult, dur, hold)]  smooth zoom in, hold (default 45 f), ease out over 24 f; no overshoot.
#   dur 6-10; a comic 'snap' zoom = dur 3 (max 3 per video)
# SHAKES = [(frame, strength, dur)]  strength 0.5-1.5, dur 8-14 frames

def _lerp(a, b, u): return tuple(a[i] + (b[i] - a[i]) * u for i in range(len(a)))
def smoother(u):                       # C2 ease (smootherstep), no overshoot
    u = max(0.0, min(1.0, u)); return u * u * u * (u * (u * 6 - 15) + 10)

def _hermite(p0, p1, m0, m1, t0, t1, t):
    h = t1 - t0; s = (t - t0) / h
    s2, s3 = s * s, s * s * s
    h00, h10, h01, h11 = 2*s3 - 3*s2 + 1, s3 - 2*s2 + s, -2*s3 + 3*s2, s3 - s2
    return tuple(h00*p0[i] + h10*h*m0[i] + h01*p1[i] + h11*h*m1[i] for i in range(len(p0)))

def spline_track(keys, frames, ease_in, ease_out):
    """keys: [(frame, vec)], returns {f: vec}. C1 Catmull-Rom on non-uniform times."""
    ts = [k[0] for k in keys]; ps = [tuple(k[1]) for k in keys]; n = len(ps); d = len(ps[0])
    if n == 1: return {f: ps[0] for f in frames}
    ms = []
    for i in range(n):
        if i == 0:
            m = (0.0,) * d if ease_in else tuple((ps[1][j] - ps[0][j]) / (ts[1] - ts[0]) for j in range(d))
        elif i == n - 1:
            m = (0.0,) * d if ease_out else tuple((ps[-1][j] - ps[-2][j]) / (ts[-1] - ts[-2]) for j in range(d))
        else:
            m = tuple((ps[i+1][j] - ps[i-1][j]) / (ts[i+1] - ts[i-1]) for j in range(d))
        ms.append(m)
    out = {}
    for f in frames:
        if f <= ts[0]:
            out[f] = tuple(ps[0][j] + ms[0][j] * (f - ts[0]) for j in range(d)); continue
        if f >= ts[-1]:
            out[f] = tuple(ps[-1][j] + ms[-1][j] * (f - ts[-1]) for j in range(d)); continue
        for i in range(n - 1):
            if ts[i] <= f <= ts[i+1]:
                out[f] = _hermite(ps[i], ps[i+1], ms[i], ms[i+1], ts[i], ts[i+1], f); break
    return out

def spring_follow(raw, frames, omega=7.0):
    """Critically damped spring: the eye lags softly behind a moving subject (no snap)."""
    dt = 1.0 / FPS; out = {}; x = list(raw[frames[0]]); v = [0.0] * len(x)
    for f in frames:
        tgt = raw[f]
        for j in range(len(x)):
            a = omega * omega * (tgt[j] - x[j]) - 2 * omega * v[j]
            v[j] += a * dt; x[j] += v[j] * dt
        out[f] = tuple(x)
    return out

def hand_noise(t, seed):              # t in SECONDS, 0.2-0.9 Hz: breathing operator, never per-frame jitter
    return (math.sin(2*math.pi*0.23*t + seed) * 0.55 + math.sin(2*math.pi*0.51*t + seed*1.7) * 0.30
            + math.sin(2*math.pi*0.87*t + seed*2.3) * 0.15)

def shake_at(f, shakes):              # impact shake: 5-9 Hz in seconds, exp decay, returns (dx, dy)
    dx = dy = 0.0
    for (s, k, dur) in shakes:
        if s <= f < s + dur:
            t = (f - s) / FPS; env = k * math.exp(-5.0 * (f - s) / dur) * smoother((f - s + 1) / 2)
            dx += env * (math.sin(2*math.pi*7.1*t) * 0.6 + math.sin(2*math.pi*4.3*t + 1.1) * 0.4)
            dy += env * (math.sin(2*math.pi*8.7*t + 0.5) * 0.6 + math.sin(2*math.pi*5.3*t + 2.0) * 0.4)
    return dx, dy

def solve_camera(SEQS, TRANS, PUNCH=(), SHAKES=(), hand=1.0):
    """Returns {f: (cam_pos, look_pos, lens, roll_rad)} for every frame. Pure python (testable outside Blender)."""
    res = {}
    for si, S in enumerate(SEQS):
        a, b = S["a"], S["b"]; frames = list(range(a, b + 1)); keys = S["keys"]
        ei, eo = S.get("ease_in", si == 0), S.get("ease_out", si == len(SEQS) - 1)
        cp = spline_track([(k[0], k[1]) for k in keys], frames, ei, eo)
        lp = spline_track([(k[0], k[2]) for k in keys], frames, ei, eo)
        ln = spline_track([(k[0], (k[3],)) for k in keys], frames, ei, eo)
        rl = spline_track([(k[0], (k[4] if len(k) > 4 else 0.0,)) for k in keys], frames, ei, eo)
        if S.get("follow"):
            w = S.get("follow_w", 0.35)
            raw = {f: _lerp(lp[f], S["follow"](f), w) for f in frames}
            lp = spring_follow(raw, frames, S.get("omega", 7.0))
        # transitions touching this sequence
        tin = TRANS.get(a); tout = TRANS.get(b + 1)
        for f in frames:
            c = list(cp[f]); l = list(lp[f]); lens = ln[f][0]; roll = math.radians(rl[f][0])
            d = [l[i] - c[i] for i in range(3)]; dist = math.sqrt(sum(x*x for x in d)) or 1.0
            fwd = [x / dist for x in d]
            right = [fwd[1], -fwd[0], 0.0]; rn = math.hypot(right[0], right[1]) or 1.0; right = [x/rn for x in right]
            # whip: same screen direction on both sides of the cut, accelerate out / decelerate in, NO bounce
            if tout and tout[0] == "whip" and f > b - 6:
                u = (f - (b - 6)) / 6.0; off = tout[1] * 1.1 * dist * u ** 3
                l = [l[i] + right[i] * off for i in range(3)]
            if tin and tin[0] == "whip" and f < a + 8:
                u = (f - a) / 8.0; off = -tin[1] * 0.9 * dist * (1 - u) ** 3
                l = [l[i] + right[i] * off for i in range(3)]
            # push-through: dolly hard into a dark object that fills frame (hole, door, mouth, pipe)
            if tout and tout[0] == "push" and f > b - 10:
                u = smoother((f - (b - 10)) / 10.0) ** 1.5
                c = [c[i] + fwd[i] * dist * 0.92 * u for i in range(3)]
            if tin and tin[0] == "push" and f < a + 12:
                u = (1 - (f - a) / 12.0) ** 3                             # fast out of the dark, settles into the spline
                c = [c[i] - fwd[i] * dist * 0.5 * u for i in range(3)]
            # punch: smooth lens push, held, no overshoot
            for P in PUNCH:                     # (frame, mult, dur[, hold]) push in, hold, ease back out
                p, m, dur = P[:3]; hold = P[3] if len(P) > 3 else 45
                if a <= p <= b and f >= p:
                    k_in = smoother((f - p) / dur); k_out = smoother((f - p - dur - hold) / 24.0)
                    lens *= 1 + (m - 1) * k_in * (1 - k_out)
            # handheld (scaled down on long lenses so it never looks like jitter)
            t = f / FPS; k = hand * 30.0 / lens
            c = [c[0] + 0.012 * k * hand_noise(t, 1.0), c[1], c[2] + 0.008 * k * hand_noise(t, 4.0)]
            sx, sy = shake_at(f, SHAKES)
            l = [l[0] + right[0] * (0.02*k*hand_noise(t, 7.0) + 0.045*sx), l[1] + right[1] * (0.02*k*hand_noise(t, 7.0) + 0.045*sx),
                 l[2] + 0.015*k*hand_noise(t, 9.0) + 0.035*sy]
            res[f] = (tuple(c), tuple(l), lens, roll)
    return res

def cam_report(res, SEQS, TRANS, PUNCH=(), N=None):
    """Smoothness gate. Prints problems; returns True when the camera passes."""
    ok = True; cuts = sorted(TRANS)
    for S in SEQS:
        L = S["b"] - S["a"] + 1
        if L < 90: print(f"WARN seq {S['a']}-{S['b']} only {L/FPS:.1f}s (aim 4-10 s; max 2 short inserts)"); ok = False
    worst = 0.0
    for S in SEQS:
        fr = list(range(S["a"] + 1, S["b"]))
        for f in fr:
            if any(abs(f - c) < 12 for c in cuts) or f + 1 > S["b"] or f - 1 < S["a"]: continue
            if any(P[0] <= f < P[0] + 12 or P[0] + P[2] + (P[3] if len(P) > 3 else 45) <= f < P[0] + P[2] + (P[3] if len(P) > 3 else 45) + 26 for P in PUNCH): continue
            acc = math.dist([res[f+1][0][i] - 2*res[f][0][i] + res[f-1][0][i] for i in range(3)], (0, 0, 0))
            worst = max(worst, acc)
    print(f"cuts: {len(cuts)}  sequences: {len(SEQS)}  worst cam accel: {worst*1000:.2f} mm/frame^2")
    if worst * 1000 > 4.0: print("WARN camera accel spike > 4 mm/frame^2: add a key or move keys apart"); ok = False
    snaps = sum(1 for P in PUNCH if P[2] <= 4)
    if snaps > 3: print(f"WARN {snaps} snap zooms (max 3)"); ok = False
    print("CAMERA OK" if ok else "CAMERA NEEDS FIX")
    return ok

def bake_camera(cam, cam_d, res, cut_frames):
    """Blender side: keys every frame, LINEAR, rotation built from look+roll (no TRACK_TO), holds at cuts."""
    import bpy
    from mathutils import Vector, Quaternion
    for con in list(cam.constraints): cam.constraints.remove(con)
    cam.rotation_mode = 'XYZ'; prev = None; LENS_F = {}
    def put(fr, v):
        nonlocal prev
        c, l, lens, roll = v
        cam.location = c
        q = (Vector(l) - Vector(c)).to_track_quat('-Z', 'Y')
        q = q @ Quaternion((0, 0, 1), roll)
        e = q.to_euler('XYZ', prev) if prev else q.to_euler('XYZ'); prev = e
        cam.rotation_euler = e; cam_d.lens = lens
        cam.keyframe_insert("location", frame=fr); cam.keyframe_insert("rotation_euler", frame=fr)
        cam_d.keyframe_insert("lens", frame=fr)
    for f in sorted(res):
        put(f, res[f]); LENS_F[f] = res[f][2]
        if f + 1 in cut_frames: put(f + 0.98, res[f])       # motion-blur hold: no smear across a cut
    for idb in (cam, cam_d):
        for fc in fcurves_of(idb):
            for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
    return LENS_F

if "fcurves_of" not in globals():          # v1 template alone: copy from module v2
    def fcurves_of(idb):
        ad = idb.animation_data
        if not ad or not ad.action: return []
        act = ad.action
        if hasattr(act, "fcurves"): return list(act.fcurves)
        out_ = []
        for layer in act.layers:
            for strip in layer.strips:
                cb = strip.channelbag(ad.action_slot)
                if cb: out_ += list(cb.fcurves)
        return out_
```

### Tích hợp module v2 + camera v3 vào template v1
1. Camera: dán module "Camera v3" (ngay sau module v2), **xóa** vòng lặp `SHOTS` cũ và TRACK_TO không còn cần, thay bằng khối `SEQS / TRANS / PUNCH / SHAKES` → `solve_camera` → `cam_report` → `bake_camera` (xem template, phần "timeline"). Không cộng thêm whip/punch/rung kiểu v2 nữa.
2. Phụ đề: mỗi khung đặt `cap_root.location = (0, y*k, -k)` với `k = LENS_F[f]/28` (`y` là -0,12, hoặc -0,55 trong cảnh minh họa). Chữ nảy bằng `ease_out_back((f-a)/5, 2.2)`, nghiêng ngẫu nhiên ±0,03 (từ nhấn ±0,06, lắc 9 khung đầu). Chữ có CLANG thì thêm hình sao 18 cánh (bán kính 0,22/0,16 × 0,12/0,08, vàng, kèm lớp cam lớn hơn 1,2 lần phía sau).
3. Sau khi bake xong mọi thứ: gọi các `dust_burst(...)`, `bake_dust()`, `bake_reaction_fx(...)`, `bake_talk(...)`, `add_teleport_holds([roots nhân vật, đạo cụ 3D])`, rồi `setup_look(NOLINE)`. `NOLINE` gồm descendants của root nhân vật, `cap_root`, mặt phẳng minh họa, các puff và `dg_back`.
4. Chớp mắt key mọi khung. Trong vòng lặp, gán `c.amp_now = AMP[f]` khi nhân vật đang nói, trước khi gọi `pose_char`.

## Template v1 nền `scene.py` (đã chạy thật trên Blender 5.2.3: cảnh "Meet Joe" 12 giây; nâng lên v2 bằng module ở trên)

Khối camera trong template đã dùng camera v3, nên **phải dán module "Camera v3" vào trước phần `2D character toolkit`** (module có sẵn `fcurves_of` dự phòng khi chưa ghép module v2).

Các phần cần sửa cho mỗi video: `environment`, nhân vật `JOE` / `BOSS` (đổi tên, vai, màu), `SEQS` / `TRANS` / `PUNCH` / `SHAKES`, `J_EXPR` / `B_EXPR`, khối animation, `CAPS`, `EVENTS`, `N` (số khung = giây × 30).

```python
# ==========================================================
#  "Meet Joe" - test scene (12 s, 1080x1920, 30 fps)
#  Original 2D characters in a stylised 3D desert railroad.
#  Run inside Blender 5.2: Scripting tab > Run Script.
#  Then render with Render > Render Animation (Ctrl+F12).
# ==========================================================
import bpy, math, os, wave, random
import numpy as np

FPS, N = 30, 360
CLOUD = bpy.app.background            # True when previewing headless
random.seed(7)

# ---------------- output / fonts ----------------
if os.name == "nt":
    OUT_DIR = os.path.join(os.path.expanduser("~"), "Videos", "claude_test")
    FONT_CANDIDATES = [r"C:\Windows\Fonts\ariblk.ttf", r"C:\Windows\Fonts\arialbd.ttf"]
else:
    OUT_DIR = "/home/claude/out/rail"
    FONT_CANDIDATES = ["/usr/share/fonts/opentype/inter/Inter-Black.otf",
                       "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"]
os.makedirs(OUT_DIR, exist_ok=True)
FONT_PATH = next((f for f in FONT_CANDIDATES if os.path.exists(f)), None)

# ---------------- reset ----------------
if CLOUD:
    bpy.ops.wm.read_factory_settings(use_empty=True)
else:
    for coll in (bpy.data.objects, bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras,
                 bpy.data.lights, bpy.data.textures, bpy.data.worlds, bpy.data.actions):
        for item in list(coll):
            coll.remove(item)
    if bpy.context.scene.sequence_editor:
        for st in list(bpy.context.scene.sequence_editor.strips):
            bpy.context.scene.sequence_editor.strips.remove(st)
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, N
sc.render.fps = FPS
sc.render.resolution_x, sc.render.resolution_y = 1080, 1920
sc.render.resolution_percentage = 100
sc.view_settings.view_transform = 'Standard'
sc.view_settings.look = 'None'
sc.render.engine = 'BLENDER_EEVEE'
try:
    sc.eevee.taa_render_samples = 32
    sc.eevee.use_shadows = True
    sc.eevee.use_raytracing = True
    sc.eevee.use_fast_gi = True
except Exception:
    pass
sc.render.use_motion_blur = False
col = sc.collection

# ---------------- materials ----------------
MATS = {}
def flat(name, rgb):
    if name in MATS: return MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    e = nt.nodes.new("ShaderNodeEmission"); e.inputs[0].default_value = (*rgb, 1)
    o = nt.nodes.new("ShaderNodeOutputMaterial"); nt.links.new(e.outputs[0], o.inputs[0])
    MATS[name] = m
    return m

def pbr(name, rgb, rough=0.8, metal=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m

def ramp_mat(name, stops, tex="noise", scale=1.0, coord="Object", bump=0.0, rough=0.9,
             wave_dir='Z', distortion=2.0, detail=4.0, mapping_scale=(1, 1, 1), voronoi=False):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; L = nt.links
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = rough
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = mapping_scale
    if coord == "Position":
        geo = nt.nodes.new("ShaderNodeNewGeometry"); L.new(geo.outputs["Position"], mp.inputs[0])
    else:
        L.new(tc.outputs[coord], mp.inputs[0])
    if tex == "wave":
        t = nt.nodes.new("ShaderNodeTexWave"); t.wave_type = 'BANDS'; t.bands_direction = wave_dir
        t.inputs["Scale"].default_value = scale; t.inputs["Distortion"].default_value = distortion
        t.inputs["Detail"].default_value = detail
        fac = t.outputs["Fac"]
    elif voronoi:
        t = nt.nodes.new("ShaderNodeTexVoronoi"); t.inputs["Scale"].default_value = scale
        fac = t.outputs["Color"]
    else:
        t = nt.nodes.new("ShaderNodeTexNoise"); t.inputs["Scale"].default_value = scale
        t.inputs["Detail"].default_value = detail
        fac = t.outputs["Fac"]
    L.new(mp.outputs[0], t.inputs["Vector"])
    cr = nt.nodes.new("ShaderNodeValToRGB")
    els = cr.color_ramp.elements
    els[0].position, els[0].color = stops[0][0], (*stops[0][1], 1)
    els[1].position, els[1].color = stops[-1][0], (*stops[-1][1], 1)
    for p, c in stops[1:-1]:
        e = els.new(p); e.color = (*c, 1)
    if voronoi:
        sep = nt.nodes.new("ShaderNodeRGBToBW"); L.new(fac, sep.inputs[0]); L.new(sep.outputs[0], cr.inputs[0])
    else:
        L.new(fac, cr.inputs[0])
    L.new(cr.outputs[0], b.inputs["Base Color"])
    if bump > 0:
        bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = bump
        src = t.outputs["Distance"] if voronoi else t.outputs["Fac"]
        L.new(src, bp.inputs["Height"]); L.new(bp.outputs[0], b.inputs["Normal"])
    return m

def setmat(o, m):
    o.data.materials.clear(); o.data.materials.append(m); return o

# ---------------- world / light ----------------
world = bpy.data.worlds.new("Sky"); sc.world = world; world.use_nodes = True
wn = world.node_tree; wl = wn.links
bgn = wn.nodes["Background"]
tco = wn.nodes.new("ShaderNodeTexCoord")
sxyz = wn.nodes.new("ShaderNodeSeparateXYZ"); wl.new(tco.outputs["Generated"], sxyz.inputs[0])
mr = wn.nodes.new("ShaderNodeMapRange")
mr.inputs[1].default_value, mr.inputs[2].default_value = -0.05, 0.75
wl.new(sxyz.outputs[2], mr.inputs[0])
skr = wn.nodes.new("ShaderNodeValToRGB"); el = skr.color_ramp.elements
el[0].position, el[0].color = 0.0, (0.98, 0.86, 0.72, 1)
el[1].position, el[1].color = 1.0, (0.16, 0.42, 0.90, 1)
e = el.new(0.25); e.color = (0.62, 0.80, 0.98, 1)
wl.new(mr.outputs[0], skr.inputs[0]); wl.new(skr.outputs[0], bgn.inputs[0])
bgn.inputs[1].default_value = 1.0

sun_d = bpy.data.lights.new("Sun", 'SUN'); sun_d.energy = 3.2; sun_d.color = (1.0, 0.93, 0.82); sun_d.angle = math.radians(4)
sun = bpy.data.objects.new("Sun", sun_d); col.objects.link(sun)
sun.rotation_euler = (math.radians(48), math.radians(-28), math.radians(-35))

# ---------------- environment ----------------
def cube(name, loc, size, m):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object; o.name = name; o.scale = size
    return setmat(o, m)

SAND = ramp_mat("sand", [(0.3, (0.78, 0.42, 0.20)), (0.5, (0.86, 0.52, 0.27)), (0.7, (0.72, 0.36, 0.18))],
                scale=0.15, bump=0.15, detail=6)
bpy.ops.mesh.primitive_plane_add(size=600, location=(0, 100, 0))
setmat(bpy.context.object, SAND)

BALLAST = ramp_mat("ballast", [(0.0, (0.30, 0.25, 0.22)), (0.35, (0.55, 0.45, 0.38)),
                               (0.65, (0.62, 0.38, 0.28)), (1.0, (0.80, 0.72, 0.65))],
                   scale=9.0, voronoi=True, bump=0.6, rough=0.95)
# trapezoid ballast bed
me = bpy.data.meshes.new("ballast")
Y0, Y1 = -20, 260
vs = [(-1.9, Y0, 0), (1.9, Y0, 0), (1.35, Y0, 0.3), (-1.35, Y0, 0.3),
      (-1.9, Y1, 0), (1.9, Y1, 0), (1.35, Y1, 0.3), (-1.35, Y1, 0.3)]
fs = [(0, 1, 2, 3), (4, 7, 6, 5), (3, 2, 6, 7), (0, 3, 7, 4), (1, 5, 6, 2)]
me.from_pydata(vs, [], fs); me.update()
bal = bpy.data.objects.new("ballast", me); col.objects.link(bal); setmat(bal, BALLAST)

WOOD = ramp_mat("wood", [(0.2, (0.22, 0.13, 0.08)), (0.6, (0.36, 0.22, 0.13)), (0.9, (0.28, 0.17, 0.10))],
                scale=3.0, mapping_scale=(6, 0.4, 0.4), bump=0.3)
sl = cube("sleeper", (0, Y0 + 0.5, 0.36), (2.5, 0.26, 0.12), WOOD)
am = sl.modifiers.new("arr", 'ARRAY'); am.use_relative_offset = False; am.use_constant_offset = True
am.constant_offset_displace = (0, 0.75 / 0.26, 0); am.count = 370

STEEL = pbr("steel", (0.42, 0.40, 0.40), rough=0.35, metal=1.0)
RUST = pbr("rust", (0.30, 0.16, 0.10), rough=0.9)
for x in (-0.72, 0.72):
    cube("rail_web", (x, (Y0 + Y1) / 2, 0.5), (0.05, Y1 - Y0, 0.16), RUST)
    cube("rail_head", (x, (Y0 + Y1) / 2, 0.59), (0.10, Y1 - Y0, 0.05), STEEL)

STRATA = ramp_mat("strata", [(0.0, (0.40, 0.09, 0.05)), (0.25, (0.70, 0.20, 0.08)), (0.45, (0.88, 0.42, 0.16)),
                             (0.6, (0.93, 0.62, 0.38)), (0.75, (0.66, 0.18, 0.08)), (1.0, (0.45, 0.11, 0.06))],
                  tex="wave", scale=0.045, distortion=1.6, detail=2, bump=0.25, coord="Position")

def cliff(name, loc, size, seed):
    o = cube(name, loc, size, STRATA)
    ss = o.modifiers.new("ss", 'SUBSURF'); ss.subdivision_type = 'SIMPLE'; ss.levels = ss.render_levels = 4
    tx = bpy.data.textures.new(name + "_t", 'CLOUDS'); tx.noise_scale = 2.5; tx.noise_depth = 2
    d = o.modifiers.new("disp", 'DISPLACE'); d.texture = tx; d.strength = 0.9; d.texture_coords = 'GLOBAL'
    sm = o.modifiers.new("sm", 'SMOOTH'); sm.iterations = 2
    return o

cliff("wall_L", (-9.5, 40, 9), (5, 90, 22), 1)
cliff("wall_L2", (-14, 120, 12), (8, 80, 28), 2)
for i, (x, y, w, d, h) in enumerate([(26, 70, 22, 16, 10), (45, 120, 30, 20, 16), (12, 165, 18, 14, 13),
                                     (-30, 190, 26, 18, 20), (60, 60, 20, 30, 8)]):
    cliff(f"mesa{i}", (x, y, h / 2 - 0.5), (w, d, h), i)

# telegraph poles
POLE = pbr("pole", (0.25, 0.16, 0.10), rough=0.9)
for i in range(14):
    y = -6 + i * 14
    bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=0.09, depth=6, location=(3.4, y, 3))
    setmat(bpy.context.object, POLE)
    cube("bar", (3.4, y, 5.6), (1.4, 0.1, 0.1), POLE)

# cacti
CACT = pbr("cactus", (0.20, 0.45, 0.22), rough=0.7)
def cactus(x, y, h):
    bpy.ops.mesh.primitive_cylinder_add(vertices=14, radius=0.22, depth=h, location=(x, y, h / 2)); setmat(bpy.context.object, CACT)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.22, location=(x, y, h)); setmat(bpy.context.object, CACT)
    for s, hh in ((1, 0.55), (-1, 0.4)):
        bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.14, depth=0.5, location=(x + s * 0.32, y, h * hh),
                                            rotation=(0, math.pi / 2, 0)); setmat(bpy.context.object, CACT)
        bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.14, depth=0.7, location=(x + s * 0.55, y, h * hh + 0.33)); setmat(bpy.context.object, CACT)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.14, location=(x + s * 0.55, y, h * hh + 0.68)); setmat(bpy.context.object, CACT)
for x, y, h in ((5.5, 12, 2.6), (8, 30, 3.2), (-4.2, 22, 2.2), (6.5, 55, 3.0)):
    cactus(x, y, h)

# rocks
ROCK = ramp_mat("rock", [(0.3, (0.45, 0.20, 0.10)), (0.7, (0.65, 0.33, 0.16))], scale=2, bump=0.4)
for i in range(40):
    x = random.choice([-1, 1]) * random.uniform(2.3, 7); y = random.uniform(-4, 70)
    r = random.uniform(0.08, 0.35)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=r, location=(x, y, r * 0.3))
    o = bpy.context.object; o.scale = (1, random.uniform(0.7, 1.3), random.uniform(0.5, 0.8))
    o.rotation_euler = (0, 0, random.uniform(0, 6)); setmat(o, ROCK)

# soft clouds
CLOUDM = flat("cloud", (0.97, 0.97, 1.0))
for cx, cy, cz in ((-25, 160, 45), (30, 190, 55), (5, 220, 40), (60, 170, 35)):
    for k in range(6):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=random.uniform(4, 8),
                                             location=(cx + random.uniform(-9, 9), cy + random.uniform(-3, 3), cz + random.uniform(-2, 2)))
        o = bpy.context.object; o.scale = (1, 0.5, 0.55); setmat(o, CLOUDM)
        o.visible_shadow = False

# ---------------- camera ----------------
cam_d = bpy.data.cameras.new("Cam"); cam_d.lens = 32; cam_d.clip_start = 0.05; cam_d.clip_end = 600
cam = bpy.data.objects.new("Cam", cam_d); col.objects.link(cam); sc.camera = cam
tgt = bpy.data.objects.new("CamTarget", None); col.objects.link(tgt)
tc = cam.constraints.new('TRACK_TO'); tc.target = tgt; tc.track_axis = 'TRACK_NEGATIVE_Z'; tc.up_axis = 'UP_Y'

# ---------------- 2D character toolkit ----------------
INK = flat("ink", (0.03, 0.03, 0.035))
WHITE = flat("white", (0.98, 0.98, 0.97))

def ellipse(cx, cy, rx, ry, n=40, a0=0.0, a1=2 * math.pi):
    return [(cx + rx * math.cos(a0 + (a1 - a0) * i / n), cy + ry * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + (0 if a1 - a0 >= 2 * math.pi - 1e-6 else 1))]

def rrect(cx, cy, w, h, r, n=8):
    pts = []
    for qx, qy, a in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        ccx, ccy = cx + qx * (w / 2 - r), cy + qy * (h / 2 - r)
        for i in range(n + 1):
            t = math.radians(a + 90 * i / n)
            pts.append((ccx + r * math.cos(t), ccy + r * math.sin(t)))
    return pts

def _curve(name, pts, cyclic, dims):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = dims
    sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
    for p, (x, y) in zip(sp.points, pts):
        p.co = (x, y, 0, 1)
    sp.use_cyclic_u = cyclic
    return cu

def add_obj(name, data, parent, z, m):
    o = bpy.data.objects.new(name, data); col.objects.link(o)
    o.parent = parent; o.location = (0, 0, z)
    o.data.materials.append(m)
    return o

def shape(parent, name, pts, m, z, outline=0.035):
    """filled 2D shape with black outline; returns list of objects"""
    cu = _curve(name, pts, True, '2D'); cu.fill_mode = 'BOTH'
    a = add_obj(name, cu, parent, z, m)
    out = []
    if outline:
        cu2 = _curve(name + "_ol", pts, True, '3D'); cu2.bevel_depth = outline / 2; cu2.bevel_resolution = 2
        out.append(add_obj(name + "_ol", cu2, parent, z, INK))
    return [a] + out

def stroke(parent, name, pts, w, z, m=None, cyclic=False):
    cu = _curve(name, pts, cyclic, '3D'); cu.bevel_depth = w / 2; cu.bevel_resolution = 2; cu.use_fill_caps = True
    return [add_obj(name, cu, parent, z, m or INK)]

def disc(parent, name, cx, cy, r, z, m=INK):
    return shape(parent, name, ellipse(cx, cy, r, r, 24), m, z, outline=0)

def empty(name, parent=None, loc=(0, 0, 0)):
    o = bpy.data.objects.new(name, None); col.objects.link(o)
    o.parent = parent; o.location = loc
    return o

def limb(parent, name, origin, L1, L2, w, z, hand=None):
    """two-segment stick limb. returns (upper, lower) pivots"""
    up = empty(name + "_up", parent, (origin[0], origin[1], z))
    stroke(up, name + "_s1", [(0, 0), (0, -L1)], w, 0)
    disc(up, name + "_j", 0, -L1, w / 2, 0)
    lo = empty(name + "_lo", up, (0, -L1, 0))
    stroke(lo, name + "_s2", [(0, 0), (0, -L2)], w, 0)
    if hand == "hand":
        shape(lo, name + "_hand", ellipse(0, -L2 - 0.05, 0.075, 0.075, 24), WHITE, 0.03, outline=0.03)
    elif hand == "shoe":
        shape(lo, name + "_shoe", ellipse(0.04, -L2 - 0.02, 0.13, 0.065, 24), INK, 0.0, outline=0)
    return up, lo

def char_root(name, loc):
    root = empty(name, None, loc)
    lt = root.constraints.new('LOCKED_TRACK'); lt.target = cam; lt.track_axis = 'TRACK_NEGATIVE_Y'; lt.lock_axis = 'LOCK_Z'
    plane = empty(name + "_plane", root); plane.rotation_euler = (math.pi / 2, 0, 0)
    return root, plane

def group(parent, name):
    return empty(name, parent)

def set_visible(grp, frame, vis):
    for o in [grp] + list(grp.children_recursive):
        o.hide_render = not vis; o.hide_viewport = not vis
        o.keyframe_insert("hide_render", frame=frame); o.keyframe_insert("hide_viewport", frame=frame)

# ---------------- JOE (worker) ----------------
SKIN = WHITE
BLUE = flat("joe_blue", (0.03, 0.22, 0.55))
HIVIS = flat("hivis", (0.95, 0.85, 0.05))
HAT = flat("hardhat", (0.98, 0.30, 0.02))
HAT_D = flat("hardhat_d", (0.75, 0.18, 0.01))
HAIR = flat("hair", (0.36, 0.22, 0.12))
MOUTH = flat("mouth", (0.55, 0.10, 0.10))
TONGUE = flat("tongue", (0.95, 0.45, 0.45))

joe, jp = char_root("Joe", (-0.55, 5.0, 0.42))
j_body = empty("joe_body", jp)                                   # bob/breath pivot at feet
j_legL = limb(j_body, "joe_legL", (-0.15, 0.74), 0.36, 0.34, 0.065, 0.05, "shoe")
j_legR = limb(j_body, "joe_legR", (0.15, 0.74), 0.36, 0.34, 0.065, 0.05, "shoe")
j_torso = empty("joe_torso", j_body, (0, 0.70, 0))
shape(j_torso, "joe_shirt", rrect(0, 0.40, 0.80, 0.82, 0.30), BLUE, 0.12)
shape(j_torso, "joe_stripe", rrect(0, 0.32, 0.78, 0.12, 0.03), HIVIS, 0.17, outline=0.02)
shape(j_torso, "joe_pocket", rrect(0.18, 0.58, 0.18, 0.15, 0.03), BLUE, 0.17, outline=0.022)
stroke(j_torso, "joe_neck", [(0, 0.78), (0, 0.88)], 0.06, 0.1)
j_armL = limb(j_torso, "joe_armL", (-0.33, 0.66), 0.34, 0.32, 0.05, 0.24, "hand")
j_armR = limb(j_torso, "joe_armR", (0.33, 0.66), 0.34, 0.32, 0.05, 0.24, "hand")
j_head = empty("joe_head", j_torso, (0, 1.34, 0.3))
shape(j_head, "joe_hair", ellipse(-0.36, 0.06, 0.16, 0.22, 24), HAIR, -0.05)
shape(j_head, "joe_face", ellipse(0, 0, 0.5, 0.48, 48), SKIN, 0.0)
dome = ellipse(0, 0.2, 0.47, 0.40, 30, 0, math.pi)
shape(j_head, "joe_hat", dome, HAT, 0.08)
stroke(j_head, "joe_hat_ridge", [(0, 0.2), (0, 0.58)], 0.035, 0.12)
shape(j_head, "joe_brim", rrect(0.04, 0.2, 1.12, 0.12, 0.05), HAT_D, 0.13)

def eye(parent, name, x, y, z, rx=0.055, ry=0.085):
    g = empty(name, parent, (x, y, z)); disc(g, name + "_d", 0, 0, 1.0, 0, INK); g.scale = (rx, ry, 1); return g

J = {}
J["neutral"] = g = group(j_head, "joe_neutral")
J["eyes_n"] = [eye(g, "jeL", -0.15, -0.02, 0.06), eye(g, "jeR", 0.15, -0.02, 0.06)]
stroke(g, "j_mouth_n", ellipse(0.0, -0.13, 0.12, 0.07, 10, math.radians(200), math.radians(340)), 0.035, 0.06)
stroke(g, "j_brow_nL", [(-0.22, 0.12), (-0.09, 0.14)], 0.03, 0.06); stroke(g, "j_brow_nR", [(0.09, 0.14), (0.22, 0.12)], 0.03, 0.06)

J["happy"] = g = group(j_head, "joe_happy")
stroke(g, "j_eye_hL", ellipse(-0.15, -0.05, 0.07, 0.07, 10, math.radians(20), math.radians(160)), 0.035, 0.06)
stroke(g, "j_eye_hR", ellipse(0.15, -0.05, 0.07, 0.07, 10, math.radians(20), math.radians(160)), 0.035, 0.06)
mp = [(-0.17, -0.12)] + ellipse(0, -0.12, 0.17, 0.17, 16, math.pi, 2 * math.pi)[1:]
shape(g, "j_mouth_h", mp, MOUTH, 0.06, outline=0.03)
shape(g, "j_tongue", ellipse(0, -0.24, 0.07, 0.04, 16), TONGUE, 0.08, outline=0)

def smirk_face(name, wink=False):
    g = group(j_head, name)
    eL = eye(g, name + "eL", -0.15, -0.03, 0.06, 0.055, 0.065)
    shape(g, name + "lidL", rrect(-0.15, 0.02, 0.15, 0.06, 0.02), SKIN, 0.09, outline=0)
    stroke(g, name + "lidlineL", [(-0.22, -0.005), (-0.08, -0.005)], 0.03, 0.1)
    if wink:
        stroke(g, name + "winkR", ellipse(0.15, -0.06, 0.07, 0.06, 10, math.radians(20), math.radians(160)), 0.035, 0.06)
        eR = None
    else:
        eR = eye(g, name + "eR", 0.15, -0.03, 0.06, 0.055, 0.065)
        shape(g, name + "lidR", rrect(0.15, 0.02, 0.15, 0.06, 0.02), SKIN, 0.09, outline=0)
        stroke(g, name + "lidlineR", [(0.08, -0.005), (0.22, -0.005)], 0.03, 0.1)
    stroke(g, name + "browL", [(-0.23, 0.10), (-0.08, 0.09)], 0.03, 0.06)
    stroke(g, name + "browR", [(0.08, 0.15), (0.16, 0.19), (0.23, 0.17)], 0.03, 0.06)
    stroke(g, name + "mouth", [(-0.10, -0.17), (0.02, -0.18), (0.11, -0.15), (0.15, -0.11)], 0.035, 0.06)
    return g
J["smirk"] = smirk_face("joe_smirk")
J["wink"] = smirk_face("joe_wink", wink=True)

# ---------------- BOSS ----------------
SUIT = flat("suit", (0.07, 0.08, 0.14))
SHIRT = flat("shirt", (0.95, 0.95, 0.93))
TIE = flat("tie", (0.80, 0.10, 0.12))
GOLD = flat("gold", (0.95, 0.72, 0.15))
GREY = flat("grey_hair", (0.62, 0.62, 0.64))
BOSS_SKIN = flat("boss_skin", (0.98, 0.98, 0.97))
TEETH = flat("teeth", (1, 1, 1))
STEAM = flat("steam", (0.97, 0.97, 0.98))

boss, bp = char_root("Boss", (0.75, 5.2, 0.42))
b_body = empty("boss_body", bp)
b_legL = limb(b_body, "boss_legL", (-0.17, 0.80), 0.40, 0.38, 0.065, 0.05, "shoe")
b_legR = limb(b_body, "boss_legR", (0.17, 0.80), 0.40, 0.38, 0.065, 0.05, "shoe")
b_torso = empty("boss_torso", b_body, (0, 0.76, 0))
shape(b_torso, "boss_suit", rrect(0, 0.46, 0.94, 0.96, 0.32), SUIT, 0.12)
shape(b_torso, "boss_shirtV", [(-0.17, 0.92), (0.17, 0.92), (0, 0.55)], SHIRT, 0.16, outline=0.025)
shape(b_torso, "boss_tie", [(-0.045, 0.88), (0.045, 0.88), (0.07, 0.56), (0, 0.46), (-0.07, 0.56)], TIE, 0.2, outline=0.022)
for k in range(2):
    disc(b_torso, f"boss_btn{k}", 0.13, 0.28 - k * 0.14, 0.035, 0.18, GOLD)
stroke(b_torso, "boss_neck", [(0, 0.92), (0, 0.98)], 0.06, 0.1)
b_armL = limb(b_torso, "boss_armL", (-0.40, 0.74), 0.36, 0.34, 0.05, 0.24, "hand")
b_armR = limb(b_torso, "boss_armR", (0.40, 0.74), 0.36, 0.34, 0.05, 0.24, "hand")
b_head = empty("boss_head", b_torso, (0, 1.44, 0.3))
for s in (-1, 1):
    shape(b_head, f"boss_tuft{s}", ellipse(s * 0.42, 0.02, 0.14, 0.2, 24), GREY, -0.05)
shape(b_head, "boss_face", ellipse(0, 0, 0.48, 0.5, 48), BOSS_SKIN, 0.0)
must = [(0, -0.1), (0.07, -0.08), (0.17, -0.10), (0.24, -0.18), (0.16, -0.16), (0.06, -0.17), (0, -0.14),
        (-0.06, -0.17), (-0.16, -0.16), (-0.24, -0.18), (-0.17, -0.10), (-0.07, -0.08)]
shape(b_head, "boss_must", must, INK, 0.1, outline=0)
stroke(b_head, "boss_wrinkle", [(-0.08, 0.30), (0.08, 0.30)], 0.02, 0.06)

B = {}
B["stern"] = g = group(b_head, "boss_stern")
B["eyes_s"] = [eye(g, "beL", -0.15, 0.04, 0.06, 0.05, 0.07), eye(g, "beR", 0.15, 0.04, 0.06, 0.05, 0.07)]
stroke(g, "b_brow_sL", [(-0.25, 0.17), (-0.07, 0.13)], 0.04, 0.06); stroke(g, "b_brow_sR", [(0.07, 0.13), (0.25, 0.17)], 0.04, 0.06)
stroke(g, "b_mouth_s", [(-0.08, -0.25), (0.08, -0.25)], 0.03, 0.06)

B["angry"] = g = group(b_head, "boss_angry")
eye(g, "baL", -0.14, 0.02, 0.06, 0.05, 0.05); eye(g, "baR", 0.14, 0.02, 0.06, 0.05, 0.05)
stroke(g, "b_brow_aL", [(-0.27, 0.18), (-0.05, 0.07)], 0.05, 0.07); stroke(g, "b_brow_aR", [(0.05, 0.07), (0.27, 0.18)], 0.05, 0.07)
shape(g, "b_teeth", rrect(0, -0.28, 0.26, 0.12, 0.03), TEETH, 0.06, outline=0.03)
for x in (-0.065, 0, 0.065):
    stroke(g, f"b_tooth{x}", [(x, -0.33), (x, -0.23)], 0.015, 0.09)
stroke(g, "b_toothmid", [(-0.12, -0.28), (0.12, -0.28)], 0.015, 0.09)
stroke(g, "b_vein1", [(0.20, 0.33), (0.26, 0.28)], 0.03, 0.07, m=TIE); stroke(g, "b_vein2", [(0.27, 0.36), (0.29, 0.29)], 0.03, 0.07, m=TIE)

puffs = []
for s in (-1, 1):
    pv = empty(f"puff{s}", b_head, (s * 0.52, 0.42, 0.2))
    for k, (dx, dy, r) in enumerate(((0, 0, 0.11), (0.1, 0.06, 0.09), (-0.08, 0.08, 0.08), (0.03, 0.13, 0.08))):
        shape(pv, f"puff{s}_{k}", ellipse(dx * s, dy, r, r, 20), STEAM, 0.01 * k, outline=0.025)
    puffs.append(pv)

# ---------------- timeline: shots ----------------
S1, S2, S3 = (1, 105), (106, 215), (216, 360)

def ease(u):
    u = max(0.0, min(1.0, u)); return u * u * (3 - 2 * u)

def lerp3(a, b, u):
    return tuple(a[i] + (b[i] - a[i]) * u for i in range(3))

# camera v3: one continuous move per sequence + motivated transitions (module "Camera v3")
SEQS = [
    dict(a=S1[0], b=S1[1], keys=[(S1[0], (-2.8, 0.2, 0.95), (-0.55, 5.0, 1.5), 28, 0),
                                  (S1[1], (-1.9, 2.0, 1.1), (-0.5, 5.0, 1.65), 31, -2)]),
    dict(a=S2[0], b=S2[1], keys=[(S2[0], (2.8, 2.0, 1.4), (0.75, 5.2, 2.15), 33, 0),
                                  (S2[1], (2.1, 3.0, 1.6), (0.75, 5.2, 2.3), 35, 3)]),
    dict(a=S3[0], b=S3[1], keys=[(S3[0], (0.3, -0.6, 0.9), (0.1, 5.1, 1.5), 29, 0),
                                  (S3[1], (0.1, 0.8, 1.1), (0.1, 5.1, 1.7), 31, 0)]),
]
TRANS = {S2[0]: ('whip', 1), S3[0]: ('cut',)}      # cut on action: boss turns, camera keeps its drift
PUNCH = [(146, 1.15, 8)]                             # "PERFECT."
SHAKES = [(150, 1.2, 30)]                            # boss outburst
CAM = solve_camera(SEQS, TRANS, PUNCH, SHAKES)
cam_report(CAM, SEQS, TRANS, PUNCH)
LENS_F = bake_camera(cam, cam_d, CAM, set(TRANS))

# boss is off set during shot 1, steps in for shot 2
boss.location = (6, 8, 0.42); boss.keyframe_insert("location", frame=1); boss.keyframe_insert("location", frame=S1[1])
boss.location = (0.75, 5.2, 0.42); boss.keyframe_insert("location", frame=S2[0])
for fc in boss.animation_data.action.fcurves if hasattr(boss.animation_data.action, "fcurves") else []:
    for k in fc.keyframe_points: k.interpolation = 'CONSTANT'

# ---------------- character animation ----------------
LIMB_HIST = {}
def pose_limb(lp, a1, a2, f):
    up, lo = lp
    LIMB_HIST.setdefault(up.name, []).append((f, a1 + 0.5 * a2))
    up.rotation_euler = (0, 0, a1); lo.rotation_euler = (0, 0, a2)
    up.keyframe_insert("rotation_euler", frame=f); lo.keyframe_insert("rotation_euler", frame=f)

def angle_mix(a, b, u):
    return a + (b - a) * u

J_EXPR = [(1, "neutral"), (24, "happy"), (70, "neutral"), (226, "smirk"), (300, "wink"), (318, "smirk")]
B_EXPR = [(1, "stern"), (146, "angry")]
BOSS_RED = (0.92, 0.28, 0.25)

def expr_at(table, f):
    cur = table[0][1]
    for t, e in table:
        if f >= t: cur = e
    return cur

for f in range(1, N + 1):
    t = f / FPS
    # --- Joe ---
    breath = 1 + 0.015 * math.sin(t * 2.4)
    j_body.scale = (1 / math.sqrt(breath), breath, 1); j_body.keyframe_insert("scale", frame=f)
    j_head.rotation_euler = (0, 0, 0.04 * math.sin(t * 1.7)); j_head.keyframe_insert("rotation_euler", frame=f)
    pose_limb(j_legL, -0.06, 0.02, f); pose_limb(j_legR, 0.06, -0.02, f)
    if f <= 105:
        w = ease((f - 18) / 10) * (1 - ease((f - 80) / 12))      # wave hello
        pose_limb(j_armR, angle_mix(0.25, 2.6, w), angle_mix(-0.15, 0.25 + 0.45 * math.sin(t * 14) * w, w), f)
        pose_limb(j_armL, -0.25, 0.1, f)
    else:
        # hands on hips -> right hand points up for "other plans"
        hip_u = ease((f - 220) / 10)
        up_u = ease((f - 262) / 8)
        pose_limb(j_armL, angle_mix(angle_mix(-0.25, -0.75, hip_u), -2.75, up_u),
                  angle_mix(angle_mix(0.1, 1.9, hip_u), -0.25, up_u), f)
        pose_limb(j_armR, angle_mix(0.25, 0.75, hip_u), angle_mix(-0.15, -1.9, hip_u), f)
    for name, g in J.items():
        if name.startswith("eyes"): continue
        vis = expr_at(J_EXPR, f) == name
        prev = expr_at(J_EXPR, f - 1) if f > 1 else None
        if f == 1 or vis != (prev == name): set_visible(g, f, vis)
    blink = any(b <= f < b + 4 for b in (45, 140, 250))
    for e_ in J["eyes_n"]:
        e_.scale = (0.055, 0.012 if blink else 0.085, 1); e_.keyframe_insert("scale", frame=f)

    # --- Boss ---
    angry = f >= 146
    jit = 0.012 * math.sin(f * 2.9) if angry else 0
    b_body.location = (jit, 0, 0); b_body.keyframe_insert("location", frame=f)
    bb = 1 + 0.012 * math.sin(t * 2.0 + 1)
    b_body.scale = (1 / math.sqrt(bb), bb, 1); b_body.keyframe_insert("scale", frame=f)
    pose_limb(b_legL, -0.07, 0.02, f); pose_limb(b_legR, 0.07, -0.02, f)
    if not angry:
        pose_limb(b_armL, -0.15, -0.6, f); pose_limb(b_armR, 0.15, 0.6, f)      # hands behind back-ish
    else:
        u = ease((f - 146) / 6)
        shake = 0.18 * math.sin(f * 1.7)
        pose_limb(b_armL, angle_mix(-0.15, -2.0 + shake, u), angle_mix(-0.6, -1.0, u), f)
        pose_limb(b_armR, angle_mix(0.15, 2.0 - shake, u), angle_mix(0.6, 1.0, u), f)
    for name in ("stern", "angry"):
        vis = expr_at(B_EXPR, f) == name
        prev = expr_at(B_EXPR, f - 1) if f > 1 else None
        if f == 1 or vis != (prev == name): set_visible(B[name], f, vis)
    for k, pv in enumerate(puffs):
        if angry:
            ph = ((f - 146) / 18.0 + k * 0.5) % 1.0
            s = math.sin(math.pi * ph) * 1.2
            pv.scale = (s, s, 1); pv.location = (pv.location[0], 0.42 + 0.35 * ph, 0.2)
        else:
            pv.scale = (0, 0, 1)
        pv.keyframe_insert("scale", frame=f); pv.keyframe_insert("location", frame=f)

# boss face turns red
emit = BOSS_SKIN.node_tree.nodes["Emission"].inputs[0]
emit.default_value = (0.98, 0.98, 0.97, 1); emit.keyframe_insert("default_value", frame=144)
emit.default_value = (*BOSS_RED, 1); emit.keyframe_insert("default_value", frame=156)

# ---------------- captions (word by word) ----------------
CAPS = [  # text, start, end, color, size
    ("Meet", 12, 24), ("Joe.", 24, 54),
    ("He builds", 58, 76), ("railroads.", 76, 104),
    ("His boss", 112, 128), ("wants them", 128, 144), ("PERFECT.", 146, 182, (1.0, 0.85, 0.1), 1.35),
    ("No gaps.", 184, 212),
    ("But Joe", 222, 244), ("has", 248, 258), ("other", 258, 272), ("plans.", 272, 312),
]
CAP_D = 1.0
font = bpy.data.fonts.load(FONT_PATH) if FONT_PATH else None
cap_root = empty("captions", cam, (0, -0.12, -CAP_D))
for i, c in enumerate(CAPS):
    txt, a, b = c[0], c[1], c[2]
    rgb = c[3] if len(c) > 3 else (1, 1, 1)
    size = 0.085 * (c[4] if len(c) > 4 else 1.0)
    holder = empty(f"cap{i}", cap_root)
    for layer, (m, off, z) in enumerate(((INK, size * 0.11, -0.002), (flat(f"capc{i}", rgb), 0.0, 0.0))):
        cu = bpy.data.curves.new(f"cap{i}_{layer}", 'FONT'); cu.body = txt
        if font: cu.font = font
        cu.size = size; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.offset = off
        o = bpy.data.objects.new(f"cap{i}_{layer}", cu); col.objects.link(o)
        o.parent = holder; o.location = (0, 0, z); o.data.materials.append(m)
    for f in range(max(1, a - 1), min(N, b + 1) + 1):
        if f < a or f > b:
            s = 0.0
        else:
            u = (f - a) / 4.0
            s = 1.0 if u >= 1 else (u * 1.25 if u < 0.8 else 1.0 + (1 - u) * 0.25 / 0.2 * 0.2)
            s = min(s, 1.15)
        holder.scale = (s, s, s); holder.keyframe_insert("scale", frame=f)
    holder.scale = (0, 0, 0); holder.keyframe_insert("scale", frame=1) if a > 2 else None

# ---------------- SOUND: action SFX + music bed ----------------

SR = 44100
_rng = np.random.default_rng(11)

def _t(sec): return np.arange(int(SR * sec)) / SR
def _env(n, a=0.005, d=0.1):
    t = np.arange(n) / SR; return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / d)
def _fade(x, a=0.01, r=0.05):
    n = len(x); t = np.arange(n) / SR
    return x * np.minimum(1, t / a) * np.minimum(1, (t[-1] - t) / r)
def _lp(x, k):
    """one-pole low-pass; k may be a scalar or an array (sweeping filter)"""
    k = np.broadcast_to(np.asarray(k, dtype=float), x.shape)
    y = np.empty_like(x); acc = 0.0
    for i in range(len(x)):
        acc += k[i] * (x[i] - acc); y[i] = acc
    return y
def _noise(sec): return _rng.standard_normal(int(SR * sec))
def _sweep(f0, f1, sec, shape=1.0):
    t = _t(sec); f = f0 + (f1 - f0) * (t / t[-1]) ** shape
    return np.sin(2 * np.pi * np.cumsum(f) / SR)

# each generator returns a mono float array, peak about 1
def whoosh(sec=0.45):        # camera cut, fast move across frame
    n = int(SR * sec); k = 0.03 + 0.25 * np.sin(np.linspace(0, np.pi, n)) ** 2
    return _fade(_lp(_noise(sec), k) * np.sin(np.linspace(0, np.pi, n)) ** 2 * 3, 0.02, 0.1)
def swish(sec=0.18):          # arm swing, head turn, quick gesture
    n = int(SR * sec); k = np.linspace(0.08, 0.5, n)
    return _fade(_lp(_noise(sec), k) * np.sin(np.linspace(0, np.pi, n)) * 2.5, 0.01, 0.04)
def pop(sec=0.09):            # expression change, prop appears, caption pop
    t = _t(sec); return np.sin(2 * np.pi * (500 + 1400 * t / sec) * t) * _env(len(t), 0.001, 0.025)
def tick(sec=0.05):           # soft caption tick
    t = _t(sec); return np.sin(2 * np.pi * 1800 * t) * _env(len(t), 0.0005, 0.01)
def boing(sec=0.6):           # jump, spring, bounce
    t = _t(sec); f = 180 + 90 * np.sin(2 * np.pi * 9 * t) * np.exp(-t * 4) + 60 * t
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(len(t), 0.003, 0.22)
def thud(sec=0.45):           # body hits ground, heavy landing
    t = _t(sec); body = np.sin(2 * np.pi * (60 + 50 * np.exp(-t / 0.04)) * t) * _env(len(t), 0.002, 0.13)
    return body + _lp(_noise(sec), 0.06) * _env(len(t), 0.001, 0.03) * 4
def bonk(sec=0.35):           # something hits a head
    t = _t(sec); f = 380 * np.exp(-t / 0.12) + 170
    ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(ph) + 0.45 * np.sin(2.7 * ph)) * _env(len(t), 0.001, 0.1)
def step(sec=0.09):           # one footstep (call on every foot plant)
    return _lp(_noise(sec), 0.09) * _env(int(SR * sec), 0.002, 0.018) * 4
def slide_up(sec=0.5):        # slip, rising surprise
    return _fade(_sweep(450, 1900, sec, 1.5), 0.02, 0.05)
def slide_down(sec=0.6):      # falling, deflating
    return _fade(_sweep(1700, 300, sec, 0.8), 0.02, 0.08)
def steam(sec=1.1):           # angry kettle whistle
    t = _t(sec); f = 1100 + 120 * np.sin(2 * np.pi * 7 * t)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.6 * _lp(_noise(sec), 0.3)
    return _fade(s, 0.05, 0.2) * 0.8
def rumble(sec=0.6):          # anger build, impact low end
    t = _t(sec); return np.sin(2 * np.pi * 52 * t) * _env(len(t), 0.01, 0.25) + _lp(_noise(sec), 0.01) * 2 * _env(len(t), 0.01, 0.3)
def ding(sec=0.7):            # idea, wink, correct answer
    t = _t(sec); return (np.sin(2 * np.pi * 1568 * t) + 0.4 * np.sin(2 * np.pi * 3136 * t)) * _env(len(t), 0.002, 0.2)
def squeak(sec=0.16):         # small surprise, eyes widen
    return _fade(_sweep(900, 2400, sec, 0.6), 0.005, 0.03)
def zip_out(sec=0.25):        # character dashes out of frame
    return _fade(_sweep(300, 2600, sec, 2.0) * 0.6 + _lp(_noise(sec), 0.4) * 0.4, 0.005, 0.03)
def crash(sec=0.9):           # things break, train derails
    n = int(SR * sec); x = _noise(sec) * _env(n, 0.001, 0.25)
    for k in range(6):
        i = int(_rng.uniform(0, 0.5) * SR); m = int(0.05 * SR)
        x[i:i + m] += _noise(0.05)[:len(x[i:i + m])] * _env(m, 0.001, 0.015) * 2
    return x * 0.8
def scratch(sec=0.35):        # record scratch, "wait what?"
    t = _t(sec); f = 300 + 900 * np.abs(np.sin(2 * np.pi * 3 * t))
    return _fade(np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * 0.3 + _lp(_noise(sec), 0.5) * 0.5, 0.005, 0.05)
def horn(sec=1.2):            # train horn (two-note chord)
    t = _t(sec); s = sum(np.sign(np.sin(2 * np.pi * f * t)) for f in (277, 349, 415)) / 3
    return _fade(_lp(s, 0.12), 0.06, 0.15) * 1.5
def chug(sec=2.0, bpm=200):   # steam train chugging bed
    out = np.zeros(int(SR * sec)); per = int(SR * 60 / bpm)
    for i in range(0, len(out), per):
        b = _lp(_noise(0.12), 0.25) * _env(int(0.12 * SR), 0.003, 0.04) * (1.4 if (i // per) % 2 == 0 else 0.8)
        out[i:i + len(b)] += b[:len(out[i:i + len(b)])]
    return out
def sad_trombone(sec=2.4):    # fail ending
    out = []
    for f, d, vib in ((392, 0.42, 0), (370, 0.42, 0), (349, 0.42, 0), (330, 1.1, 0.03)):
        t = _t(d); fr = f * (1 + vib * np.sin(2 * np.pi * 6 * t))
        ph = 2 * np.pi * np.cumsum(fr) / SR
        out.append(_fade(_lp(sum(np.sin(h * ph) / h for h in range(1, 8)), 0.25), 0.03, 0.1))
    return np.concatenate(out)
def gulp(sec=0.3):            # nervous swallow
    t = _t(sec); return np.sin(2 * np.pi * (300 - 200 * t / sec) * t) * _env(len(t), 0.01, 0.06) * 1.2
def cash(sec=0.5):            # money / profit
    return np.concatenate([ding(0.12) * 0.6, ding(0.4)])

def _norm(fn):
    def g(**kw):
        x = fn(**kw); return x / max(1e-6, np.abs(x).max())
    return g
SFX = {fn.__name__: _norm(fn) for fn in (whoosh, swish, pop, tick, boing, thud, bonk, step, slide_up, slide_down,
       steam, rumble, ding, squeak, zip_out, crash, scratch, horn, chug, sad_trombone, gulp, cash)}

# ---------------- music bed: plucky loop (Karplus-Strong) ----------------
def pluck(freq, dur=0.5, decay=0.996):
    n = int(SR * dur); per = max(2, int(SR / freq))
    buf = _rng.uniform(-1, 1, per); out = np.empty(n)
    for i in range(n):
        j = i % per; out[i] = buf[j]; buf[j] = 0.5 * (buf[j] + buf[(j + 1) % per]) * decay
    return out
NOTES = {"G3": 196.0, "A3": 220.0, "B3": 246.9, "C4": 261.6, "D4": 293.7, "E4": 329.6, "F4": 349.2,
         "G4": 392.0, "A4": 440.0, "B4": 493.9, "C5": 523.3, "C3": 130.8}
MOODS = {  # pattern of 16 eighth notes, bass notes every half bar, bpm
    "playful": (["C4", "G4", "E4", "G4", "A4", "G4", "E4", "G4", "F4", "C5", "A4", "C5", "G4", "D4", "B3", "D4"], ["C3", "G3"], 112),
    "sneaky":  (["A3", "C4", "E4", "C4", "B3", "D4", "F4", "D4", "A3", "C4", "E4", "A4", "G4", "E4", "D4", "B3"], ["A3", "E4"], 96),
    "tense":   (["E4", "F4", "E4", "F4", "E4", "F4", "G4", "F4", "E4", "F4", "E4", "F4", "B3", "C4", "B3", "C4"], ["E4", "B3"], 130),
}
def music_bed(total_sec, mood="playful", duck=()):
    """duck = list of (start_sec, end_sec) where music drops to 40%"""
    pat, bass, bpm = MOODS[mood]; beat = 60 / bpm / 2
    out = np.zeros(int(SR * total_sec)); cache = {}; t = 0.0; k = 0
    while t < total_sec - 0.3:
        for nm, g, d in ((pat[k % 16], 1.0, 0.5),) + (((bass[(k // 8) % 2], 0.9, 0.7),) if k % 4 == 0 else ()):
            if (nm, d) not in cache: cache[(nm, d)] = pluck(NOTES[nm], d)
            s = cache[(nm, d)]; i = int(t * SR); j = min(len(out), i + len(s)); out[i:j] += g * s[:j - i]
        t += beat; k += 1
    gain = np.ones(len(out))
    for a, b in duck:
        gain[int(a * SR):int(b * SR)] = 0.4
    return out * _lp(gain, 0.0005)

def ambience(total_sec, kind="wind"):
    n = int(SR * total_sec)
    if kind == "wind":
        return _lp(_rng.standard_normal(n), 0.01) * (0.6 + 0.4 * np.sin(np.arange(n) / SR * 0.7)) * 2
    if kind == "city":
        return _lp(_rng.standard_normal(n), 0.04) * 0.8
    return np.zeros(n)

# ---------------- mixer ----------------
class Mix:
    def __init__(self, total_sec, fps=30):
        self.fps = fps; self.buf = np.zeros(int(SR * total_sec) + SR)
    def add(self, sig, frame, gain=1.0):
        i = int((frame - 1) / self.fps * SR); j = min(len(self.buf), i + len(sig))
        if i < len(self.buf): self.buf[i:j] += gain * sig[:j - i]
    def sfx(self, name, frame, gain=0.6, **kw):
        self.add(SFX[name](**kw), frame, gain)
    def bed(self, sig, gain=1.0):
        n = min(len(sig), len(self.buf)); self.buf[:n] += gain * sig[:n]
    def write(self, path, total_sec):
        x = self.buf[:int(SR * total_sec)]
        x = x / max(1.0, np.abs(x).max() / 0.89)
        with wave.open(path, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes((x * 32767).astype(np.int16).tobytes())
        return path


TOTAL = N / FPS
mix = Mix(TOTAL, FPS)
mix.bed(music_bed(TOTAL, "playful", duck=[(S2[0] / FPS, S2[1] / FPS)]), 0.16)
mix.bed(ambience(TOTAL, "wind"), 0.05)
# VO: if a voice file exists next to the output, it is added on its own strip below

# --- automatic action sounds ---
for a_ in (S2[0], S3[0]):                                   # every camera cut
    mix.sfx("whoosh", a_ - 6, 0.35)
for table in (J_EXPR, B_EXPR):                               # every expression change
    for fr, _ in table[1:]:
        mix.sfx("pop", fr, 0.25)
for c in CAPS:                                               # every caption word
    mix.sfx("tick", c[1], 0.10)
GESTURES = {}                                                # every gesture onset (still -> moving)
for name, hist in LIMB_HIST.items():
    if "leg" in name: continue
    who = name.split("_")[0]
    sp = [0.0] + [abs(b_[1] - a_[1]) for a_, b_ in zip(hist, hist[1:])]
    for i in range(6, len(sp)):
        if sp[i] > 0.08 and max(sp[i - 6:i]) < 0.08:
            GESTURES.setdefault(who, set()).add(hist[i][0])
for who, frames in GESTURES.items():
    last = -99
    for fr in sorted(frames):
        if fr - last > 8:
            mix.sfx("swish", fr - 2, 0.30); last = fr

# --- hand-placed story sounds (frame, name, gain) ---
EVENTS = [
    (146, "rumble", 0.55), (147, "steam", 0.30), (148, "squeak", 0.25),
    (300, "ding", 0.35),
]
for fr, nm, g in EVENTS:
    mix.sfx(nm, fr, g)

wav_path = mix.write(os.path.join(OUT_DIR, "sfx_music.wav"), TOTAL)
sed = sc.sequence_editor_create()
sed.strips.new_sound("sfx_music", wav_path, 1, 1)
VO = os.path.join(OUT_DIR, "voice.wav")
if os.path.exists(VO):
    sed.strips.new_sound("voice", VO, 2, 1)

# ---------------- render output ----------------
ims = sc.render.image_settings
ims.media_type = 'VIDEO'
ims.file_format = 'FFMPEG'
sc.render.ffmpeg.format = 'MPEG4'
sc.render.ffmpeg.codec = 'H264'
sc.render.ffmpeg.constant_rate_factor = 'HIGH'
sc.render.ffmpeg.audio_codec = 'AAC'
sc.render.ffmpeg.audio_bitrate = 192
sc.render.filepath = os.path.join(OUT_DIR, "joe_test.mp4")
sc.frame_set(1)
print("SCENE READY ->", sc.render.filepath)
```