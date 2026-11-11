# Định dạng `story.json`

Một file `story.json` mô tả trọn một video theo **khung hình** (30 khung = 1 giây). `builder.py` đọc file này, lấy bối cảnh, đạo cụ, nhân vật trong `library/` rồi dựng cảnh trong Blender. Schema dùng để kiểm tra nằm ở `story.schema.json`. Hai file mẫu:

- `projects/manhole-round/story.json` — video nắp cống, dựng ra giống hệt bản v2 gốc (camera kiểu cũ `shots_v2`).
- `projects/demo-v3/story.json` — ví dụ ngắn dùng camera v3 trôi liền mạch. Video mới nên dùng kiểu này.

```bash
blender -b -P builder.py -- projects/<slug>/story.json --check                 # chỉ kiểm tra file
blender -b -P builder.py -- projects/<slug>/story.json --preview 50,200,366    # ảnh xem trước 35 % vào preview/
blender -b -P builder.py -- projects/<slug>/story.json --render                # mp4 1080x1920
```

## Giá trị và biểu thức

Mọi chỗ cần con số đều nhận được **số** hoặc **chuỗi biểu thức** (tính lại ở từng khung). Biểu thức là phép toán Python rút gọn, chỉ dùng được các tên sau:

| tên | ý nghĩa |
|---|---|
| `f`, `t` | khung hiện tại, và `f / FPS` (giây) |
| `FPS`, `N` | số khung/giây, tổng số khung |
| `sin cos tan atan2 sqrt exp log floor abs min max pi radians` | toán |
| `ease(u)` `ease_out_back(u, s)` `ease_out_elastic` `ease_out_bounce` `pease(f, a, n)` `lerp(a, b, u)` `clamp01` `noise1(t, seed)` `pop_scale(f, a)` `walk_legs(ph)` | easing và chuyển động |
| tên trong `defs`, `consts`, `let` của segment, `params` của motion | do story tự định nghĩa |

Được dùng `a if điều_kiện else b`, so sánh, `and/or/not`, và `lambda` (chỉ trong `defs`). Không có thuộc tính, import hay hàm nào khác. Biểu thức sai sẽ báo lỗi kèm vị trí, ví dụ `tracks[3].location: NameError evaluating 'sinn(f)'`.

## Các phần

### `meta`
`fps`, `frames` (bắt buộc), `seed` (bộ sinh ngẫu nhiên chung, dùng cho dãy nhà và lá cây), `voice` (file giọng đọc trong thư mục dự án), `output` (tên mp4), `samples` (mẫu EEVEE).

### `defs`, `consts`
Hàm và hằng dùng lại nhiều lần, ví dụ:
`"roll_x": "lambda f: lerp(0.6, 3.6, ...)"` — đường lăn của nắp cống, dùng chung cho camera, nhân vật, đạo cụ và bụi.

### `sets` — bối cảnh và đạo cụ trong bối cảnh
```json
{"type": "street", "params": {"length": 60}, "props": [
  {"id": "hole", "type": "manhole_hole", "params": {"kind": "round"}, "loc": [0, 4, 0]},
  {"id": "lid",  "type": "manhole_cover", "params": {"kind": "round"}}]}
```
`id` là tên vật thể trong Blender, dùng làm mục tiêu cho `tracks` và `visibility`. `on` gắn đạo cụ vào một phần của bối cảnh, ví dụ `"on": "plane"` của `diagram_board`. Thứ tự bối cảnh và đạo cụ chính là thứ tự tạo vật thể, ảnh hưởng tới số ngẫu nhiên và tên lưới.

### `camera`
- `"rig": "v3"` (dùng cho video mới): `seqs` gồm các chuỗi máy liền mạch, mỗi chuỗi có `keys` = `[khung, [vị trí máy], [điểm nhìn], lens, roll_độ]`. `trans` là chuyển cảnh tại khung đầu chuỗi sau: `{"101": ["whip", 1]}`, `push`, `match`, `cut`. `punch` = `[khung, hệ số, dur, hold]`, `shakes` = `[khung, độ mạnh, dur]`. Builder in `CAMERA OK` hoặc cảnh báo (luật skill mục 6).
- `"rig": "shots_v2"` (kiểu cũ của video nắp cống): `shots` gồm từng cảnh quay với `cam`/`look` (từ, tới), `lens`, `whip`, `fstop`, hoặc `track` (camera bám theo biểu thức). `shakes` = `[khung, biên độ]`, `punch` = `[khung, hệ số]`.

### `chars` — nhân vật
```json
{"id": "gary", "type": "gary", "loc": [1.0, 4.3, 0],
 "props": [{"id": "gary_clip", "type": "clipboard", "loc": [-0.30, 0.38, 0.42]}],
 "fx": [{"type": "steam", "ranges": [[171, 224]]}],
 "talk": [[122, 153]], "reacts": [[171, "shiver"]], "reaction_fx": [631],
 "expressions": [[1, "neutral"], [171, "angry"]], "blinks": [40, 140],
 "skin_keys": [[170, [0.98, 0.98, 0.97]], [180, [0.92, 0.28, 0.25]]],
 "blocking": {"segments": [{"from": 1281, "to": 1350, "location": [301.1, 3.3, 0]}], "default": {"location": [1.0, 4.3, 0]}},
 "pose": {"default": {"armL": ["ik", [-0.47, 0.30], -1]},
          "segments": [{"from": 171, "to": 224, "armR": ["ang", "lerp(0.25, 2.0, pease(f, 171, 6))", 0.25]}]}}
```
- `props`: đồ cầm tay 2D, gắn vào `torso` (mặc định) hoặc `head`.
- `fx`: `steam` (bốc hơi khi tức, theo khoảng khung) và `drips` (mồ hôi chảy, bắt đầu từ `from`).
- `talk`: các khoảng nhép miệng theo `voice.wav`. `reacts`: `hop`, `flinch`, `shiver`, `proud` (co giãn thân). `reaction_fx`: tia sốc và dấu "!" đỏ.
- `expressions`: `[khung, mặt]`, với mặt là một trong `neutral happy smirk wink angry shock worried grumpy focus smug_closed`. Mặt dùng phải có trong `faces` của nhân vật.
- `blocking`: vị trí gốc nhân vật theo thời gian, cùng cú pháp với track.
- `pose`: tư thế theo đoạn. `default` áp dụng khi không đoạn nào khớp; đoạn khớp chỉ ghi đè những trường nó có. Các trường:
  - `armL`/`armR`: `["ik", [x, y], bend]` đặt bàn tay tại (x, y) trong hệ toạ độ thân, `bend` ±1 là hướng gập khuỷu; `["ang", vai, khuỷu]` là góc; `null` là tay buông.
  - `legs`: `[[đùi, cẳng], [đùi, cẳng]]` hoặc `"walk_legs(ph)"`.
  - `tilt` (nghiêng đầu), `body` [dx, dy], `lean`.

### `visibility`
`{"tên vật thể": [[a, b], ...]}`: vật thể và mọi con của nó chỉ hiện trong các khoảng đã cho.

### `tracks` — chuyển động theo khung
```json
{"target": "dg_sq_cover", "segments": [
   {"from": 425, "to": 512, "let": {"u": "ease((f - 425) / 10)"}, "scale": ["1 - u", "1 - u", 1]}],
 "default": {"scale": [1, 1, 1]}}
```
Mỗi khung trong `frames` (mặc định cả video): lấy đoạn **đầu tiên** có khung nằm trong `from`–`to` hoặc trong `ranges`; nếu không có đoạn nào thì dùng `default`; nếu không có cả `default` thì bỏ qua khung đó. Mọi thuộc tính trong đoạn (`location`, `rotation_euler`, `scale`) đều được đặt keyframe.

Mẫu chuyển động có sẵn: `{"target": "cv_drop0", "use": "drop_tumble", "params": {"t0": 356, "x": 0, "y": 4}}`, với `drop_tumble` và `drop_seat` nằm trong `library/motions/`.

### `words`, `captions`
`words` = `[[giây, "chữ"], ...]` lấy từ `align_vo.py`. Trong `captions`: `highlight` là chữ tô vàng phóng to, `impact` là chữ nổ cam kèm khung burst (ví dụ `clang`), `lift` là các khoảng khung đẩy phụ đề lên cao (khi đang chiếu sơ đồ).

### `fx`
`dust`: `[{"frame", "pos", "n", "radius", "size", "life", "rise"}]`, các cụm bụi dùng chung một pool.

### `sound`
`music` (`mood`: playful, sneaky, tense; `duck` = các khung hạ nhỏ nhạc), `ambience` (city, wind), `auto` (whoosh ở mỗi cắt cảnh trừ gần các khung `avoid`, pop khi đổi mặt, tick khi hiện phụ đề, swish khi vung tay của `gesture_chars`), `events` = `[khung, tên, gain]`, `repeat` (âm lặp đều, ví dụ bước chân). Khi có `voice.wav`, gain hiệu ứng nhân với `sfx_gain_with_voice` (0.8).

### `teleport_holds`
Danh sách vật thể được giữ khung để motion blur không kéo vệt khi dịch chuyển tức thời. Mặc định gồm gốc các nhân vật và các đạo cụ có track `location`.

## Thư viện `library/`

| loại | file | API |
|---|---|---|
| `sets/<tên>/` | `build.py`, `meta.json` | `build(params, lib) -> {"parts": {...}, "anchors": {...}, "noline": [...]}` |
| `props/<tên>/` | `build.py`, `meta.json` | `build(params, lib) -> object gốc`. `params["name"]` là tên, `params["parent"]` là vật thể cha (đạo cụ 2D) |
| `chars/<tên>/` | `char.json` | `materials`, `cfg` (chân, thân, tay, đầu), `faces`, `extras` (các lệnh vẽ `shape`/`stroke`/`disc` lên `torso`/`head`) |
| `motions/<tên>.json` | | `params`, `segments`, `default` giống track; tham số dùng được trong biểu thức |

Vật liệu được lưu đệm theo tên (`core/look.py`): hai món cùng gọi `pbr("leaf", ...)` sẽ dùng chung một vật liệu.
