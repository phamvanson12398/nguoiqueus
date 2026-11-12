# Viết đồ cho thư viện

Mỗi món nằm trong thư mục riêng: `library/props/<tên>/` hoặc `library/sets/<tên>/`.

- `build.py` — code dựng, xem API bên dưới.
- `meta.json` — mô tả, tham số, các phần con. `claude_bridge` tự ghi file này từ kết quả của Claude.
- `thumb.png` và `_review/*.png` — ảnh render (`tools/thumbs.py`).

`<tên>` viết thường, nối bằng gạch dưới, tiếng Anh: `traffic_light`, `milk_carton`.

## API

```python
DEFAULTS = dict(kind="round", color=[0.9, 0.2, 0.1])      # mọi tham số đều có mặc định

def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    name = p["name"]                  # tên object gốc (story đặt = id), luôn có
    parent = p.get("parent")          # chỉ đạo cụ 2D dùng: torso/head của nhân vật hoặc 'plane' của bảng
    ...
    return root                       # props: MỘT object gốc; sets: dict(parts=..., anchors=..., noline=[...])
```

### Đạo cụ 3D (rơi, lăn, đặt trên đất, trang trí bối cảnh)
- **Gốc tọa độ** ở **tâm đáy** (đặt `loc` z=0 là đứng trên mặt đất). Vật dẹt nằm phẳng (nắp, đồng xu) thì gốc ở tâm.
- **Nhiều phần:** `root = group3d(name)` rồi dựng từng phần ở vị trí quanh (0, 0, 0) và `attach(root, a, b, c)`. Một phần duy nhất thì đặt tên phần đó là `name` và trả về luôn.
- **Tên phần con:** `f"{name}_<phần>"` (`traffic_light_red`) để story nhắm track hoặc visibility.
- **Đơn vị:** mét, nhân vật cao khoảng 2,5. Kích thước gợi ý: cột đèn 3-4; hộp sữa 0,5; đồng xu r 0,15 (đã phóng đại cho dễ nhìn).

### Đạo cụ 2D (cầm tay, đội đầu, sơ đồ trên bảng)
- Vẽ trong mặt phẳng XY (x sang phải, y lên trên), z nhỏ để xếp lớp (0, 0,02, 0,04…).
- Gốc là `empty(name, parent)`; vẽ bằng `shape`/`stroke`/`disc` lên gốc đó. Viền đen có sẵn trong `shape(..., outline=0.035)`.
- Kích thước cỡ bàn tay: 0,3-0,8. Nhân vật sẽ cầm ở khoảng (±0,4, 0,42) trong hệ tọa độ thân.

## Khối cơ bản (`from core.geo import ...`)
Mọi khối 3D trả về MESH (tự có viền mực), đặt tại `loc`:

| hàm | dùng cho |
|---|---|
| `cube(name, loc, size, m)` | hộp (size = kích thước x, y, z) |
| `rbox(name, loc, size, m, radius=0.03)` | hộp bo góc |
| `cyl(name, loc, r, depth, m, verts=32, rot=(0,0,0))` | trụ (trục Z, tâm ở giữa chiều cao) |
| `cone(name, loc, r1, r2, depth, m)` | nón, nón cụt |
| `sphere(name, loc, r, m, scale=(1,1,1))` | cầu, elip |
| `torus(name, loc, major, minor, m, rot)` | vòng, phao, quai |
| `lathe(name, loc, [(r, z), ...], m, segments=32)` | khối tiện: chai, cốc, cột, bình (r = 0 để bịt đầu) |
| `extrude(name, loc, pts, depth, m, bevel=0, rot)` | khối đùn từ hình 2D: biển báo, mặt nhà, ngôi sao |
| `text3d(name, loc, "TEXT", size, m, depth=0.02, rot)` | chữ 3D trên đồ vật |
| `group3d(name)`, `attach(root, *objs)` | gom nhiều phần |
| `keep_hidden(o, True)` | phần mặc định ẩn (trạng thái khác của đèn, mặt khác…): vẫn ẩn khi story bật hiện cả nhóm. **Đừng tự đặt `hide_render`** |
| `import_glb(path, name, size=1.0)` | nhập model CC0 .glb (đặt file trong thư mục đạo cụ) |

2D: `empty(name, parent, loc)`, `shape(parent, name, pts, m, z, outline=0.035)`, `stroke(parent, name, pts, width, z, m=None)`, `disc(parent, name, cx, cy, r, z, m)`, `arrow2d(...)`, `label(parent, name, text, (x, y), size, m)`.

Điểm 2D: `[(x, y), ...]`, `rrect(cx, cy, w, h, r)`, `ellipse(cx, cy, rx, ry, n, a0=0, a1=2π)`, `arc(cx, cy, rx, ry, độ0, độ1)`.

## Vật liệu (`from core.look import ...`)
Mọi vật liệu được lưu đệm theo **tên**: đặt tên riêng theo đạo cụ (`milk_carton_white`) trừ khi muốn dùng chung.

| hàm | dùng cho |
|---|---|
| `pbr(name, (r, g, b), rough=0.8, metal=0.0)` | vật liệu thật cho đồ 3D |
| `flat(name, (r, g, b))` | màu phẳng emission: đèn phát sáng, màn hình, đồ 2D |
| `ramp_mat(name, [(pos, rgb), ...], scale, bump)` | bề mặt có vân nhiễu (đá, gỗ, đất) |
| `iron_mat(name, "rings" hoặc "grid")` | gang |

Màu là linear: muốn màu tươi thì dùng giá trị đậm (đỏ (0.85, 0.1, 0.08), vàng (0.95, 0.7, 0.05)).

**Ánh trời nhuộm xanh mặt ngửa lên:** bầu trời là gradient xanh dương, nên mặt hướng lên trên (mặt bàn, lát bánh, sàn)
bị pha xanh. Màu nhạt hoặc vàng sẽ ngả xám xanh hay ô liu (đã gặp ở `toast`: ruột (0.95, 0.85, 0.6) thành xám xanh,
bơ vàng thành ô liu). Với mặt ngửa có màu nhận diện quan trọng:
- dùng màu ấm và đậm hơn hẳn, ví dụ ruột bánh (0.95, 0.62, 0.25), bơ (1.0, 0.72, 0.08), roughness ≥ 0.6;
- hoặc dùng `flat()` (emission, không bị nhuộm) cho mảng màu nhỏ như bơ, nhãn, đèn;
- hoặc bọc vật liệu bằng `warm_top(m)` (`from core.look import warm_top`): nhân màu với sắc ấm theo pháp tuyến hướng lên,
  mặt bên giữ nguyên. Dùng cho đá, gạch, gỗ, giấy, vải sáng màu có mặt trên lộ ra (đã dùng ở `hadrians_wall`, `wall_stone`).
Đây không phải lỗi pháp tuyến: dựng lại lưới sẽ không hết.

## Phong cách
- Hình khối to, đơn giản, đọc được trên màn hình điện thoại; 3-8 phần là đủ; tránh chi tiết nhỏ hơn 2 cm.
- Màu bão hòa, mỗi đồ vật 2-4 màu, có một màu nhận diện.
- Không dùng chữ hay logo thương hiệu thật.
- Chỉ được import `math`, `random`, `bpy`, `bmesh`, `mathutils`, `core.*`. Không đọc hay ghi file, không dùng `bpy.ops` ngoài `bpy.ops.mesh.primitive_*`/`bpy.ops.object.shade_*`.
