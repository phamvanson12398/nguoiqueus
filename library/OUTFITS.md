# Văn hóa và trang phục (video dài, nhiều phe)

## Văn hóa — `library/cultures/<id>/culture.json`
Một văn hóa = một dân tộc/nhà nước ở một thời kỳ (`roman_empire_50ad`, `iron_age_britons_50ad`, `samnite_312bc`, `dai_viet_1280`…).
```json
{"kind": "culture", "name": "roman_empire_50ad", "title_vi": "La Mã thời Đế chế (~năm 50)", "years": [-27, 200], "region": "Mediterranean",
 "description_vi": "...", "sources": [{"claim": "...", "source": "..."}], "uncertain_vi": "điểm còn tranh cãi",
 "palette": {"cloth": [r,g,b], "cloth2": [...], "metal": [...], "metal_dark": [...], "leather": [...], "trim": [...]},
 "hair_styles": ["short"], "hair_colors": [[...], ...], "beard_prob": 0.2, "beard_styles": ["full", "mustache"],
 "skin_tones": [[...], ...],
 "roles": {"soldier": "roman_legionary_50ad", "officer": "roman_centurion_50ad", "commoner": "roman_tunic_50ad"},
 "emblem_vi": "khiên đỏ, tia sét vàng", "architecture_vi": "...", "map_color": [r,g,b], "music_vi": "kèn đồng, trống"}
```
Màu là **emission tuyến tính**, phải đậm, bão hòa (STYLE.md). Không biếm họa sắc tộc: mặt mọi người vẫn là đĩa trắng của tool;
khác nhau ở tóc, râu, trang phục (skin_tones chỉ dùng khi story bật `look.skin_mode: "tones"`).

## Trang phục — `library/outfits/<id>/outfit.json`
Các mảnh 2D vẽ lên nhân vật `person` (cùng cú pháp `extras` của char.json):
```json
{"kind": "outfit", "name": "roman_legionary_50ad", "culture": "roman_empire_50ad", "role": "soldier", "title_vi": "...",
 "description_vi": "...", "silhouette_vi": "nhận ra ngay nhờ: mũ có gờ che gáy, khiên chữ nhật cong",
 "sources": [...], "torso": "$team", "hair": "none", "beard": null, "palette": {},
 "items": [{"op": "shape", "on": "torso", "name": "armor", "pts": {"rrect": [0, 0.45, 0.82, 0.5, 0.08]}, "mat": "$metal", "z": 0.17, "outline": 0.025}, ...]}
```
- `op`: `shape` (đa giác tô màu + viền), `stroke` (nét, `w` = độ dày), `disc` (`c`, `r`). `pts`: `[[x, y], ...]` hoặc `{"rrect": [cx, cy, w, h, r]}`,
  `{"ellipse": [cx, cy, rx, ry, n(, a0, a1 rad)]}`, `{"arc": [...]}`, `{"ring": [...]}`.
- `mat`: ô màu `$team $team_dark $cloth $cloth2 $metal $metal_dark $leather $trim $hair $accent $ink $white` hoặc `[r, g, b]`.
  Dùng `$team` cho phần nhận diện phe (áo, khiên, cờ, lông mào) để hai phe cùng văn hóa khác màu.
- `torso`: màu áo nền (ô màu). `hair`: `none` khi đội mũ kín, `auto` = theo văn hóa. `beard`: `none` để cấm râu. Râu/ria vẽ trong items thì
  đặt tên có chữ `beard`/`mustache` (tool sẽ không thêm râu tự động nữa).
- Tọa độ (thân `person`, đơn vị cảnh; nhân vật cao ~2,5):
  - `torso`: gốc ở đáy thân, thân rộng 0,8 (x −0,4…0,4), cao 0,82 (y 0…0,82); vai ở (±0,33; 0,66). Áo nền z 0,12; đồ trên thân z 0,13–0,25;
    tay nằm ở z 0,30 (đồ trên thân không che tay). Áo choàng sau lưng: z âm (−0,05).
  - `head`: gốc ở tâm đầu, bán kính 0,5; mắt ở y ≈ −0,02, miệng y ≈ −0,3 (**đừng che mắt, miệng**). Tóc sau đầu z −0,05; mũ z 0,06–0,12
    (vành mũ thấp nhất ở y ≈ 0,22). Mũ kín mặt chỉ được để hở mắt và miệng.
  - `handL`/`handR`: gốc ở tâm bàn tay (bàn tay tròn r 0,075, z 0,03); đồ cầm z −0,02 (sau tay) hoặc 0,05 (trước tay). Tay trái ở bên
    trái màn hình. Giáo dài ~2,2–2,6 theo trục y, khiên ~0,7–0,9.
  - `footL`/`footR`: gốc ở tâm bàn chân (giày oval rộng 0,26).
- Hình khối to, rõ, ít chi tiết vụn (STYLE.md). **Bóng đen** phải nhận ra phe ở cỡ nhỏ: dáng mũ, khiên, vũ khí khác nhau rõ.
- Đúng sử liệu: không lẫn đồ của thời kỳ/nước khác (không mũ sừng cho Viking, không giáp samurai cho lính Trung Hoa…). Ghi nguồn.

## Dùng trong story
```json
"factions": [{"id": "rome", "culture": "roman_empire_50ad", "color": [0.7, 0.06, 0.04], "label": "ROME"}],
"chars": [{"id": "marcus", "type": "person", "faction": "rome", "role": "surveyor", "look": {"hair": "short", "accent": [0.9, 0.6, 0.1], "seed": 3},
           "outfit_changes": [[900, "roman_legionary_50ad"]], "loc": [0, 4, 0]}],
"crowds": [{"id": "legion", "faction": "rome", "role": "soldier", "count": 40, "formation": "block", "cols": 10, "spacing": [0.9, 0.8],
            "at": [0, 12, 0], "rot": 0, "variants": 4, "moves": [[100, [0, 12]], [220, [0, 8]]], "march": [[100, 220]]}]
```
`outfit` ghi thẳng id trang phục; không có thì lấy `roles[role]` của văn hóa của phe.
