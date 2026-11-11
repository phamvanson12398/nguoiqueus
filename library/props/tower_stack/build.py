"""Tower stack for the dining table: a wooden plank crate and a kitchen chair, as two
independently animatable 3D parts under one root empty.

Root origin = centre of the table footprint on the floor. Each part's origin is at the
CENTRE of its own bounding box, so shakes / 90-degree topples about Y pivot naturally.
  <name>_crate : 1.2 x 1.2 x 1.0, rest at (0, 0, base_height + 0.5)
  <name>_chair : 0.6 x 0.6 x 1.8 (seat top 0.9 above the feet = local z 0),
                 rest at (offset_x, offset_y, base_height + 1.0 + 0.9)
The chair back is on +Y; the seat's -X edge is a straight crisp line and the front-left
area of the seat stays clear so a slice of toast can lie on / hang over it."""
import bpy
import bmesh
from core.look import pbr, ramp_mat
from core.geo import rbox, group3d, attach

DEFAULTS = dict(base_height=1.07, chair_offset=[0.2, -0.35],
                crate_color=[0.78, 0.50, 0.20], chair_color=[0.72, 0.10, 0.05],
                seat_color=[0.62, 0.32, 0.10], grain=True)


def _tag(rgb):
    return "_".join(str(int(round(c * 1000))) for c in rgb)


def _wood(name, rgb, grain, rough=0.6):
    rgb = tuple(float(c) for c in rgb)
    nm = f"{name}_{_tag(rgb)}"
    if not grain:
        return pbr(nm, rgb, rough=rough)
    dark = tuple(c * 0.72 for c in rgb)
    light = tuple(min(1.0, c * 1.18) for c in rgb)
    return ramp_mat(nm + "_g", [(0.30, dark), (0.50, rgb), (0.72, light)],
                    tex="noise", scale=3.0, mapping_scale=(0.25, 3.0, 3.0),
                    bump=0.05, rough=rough, detail=3.0)


def _boxes(name, boxes, m, radius=0.01):
    """several boxes merged into ONE mesh object whose origin is (0, 0, 0).
    boxes = [((cx, cy, cz), (sx, sy, sz)), ...]. Uses rbox for the standard
    ink outline + bevel, then swaps in the merged mesh."""
    bm = bmesh.new()
    for (cx, cy, cz), (sx, sy, sz) in boxes:
        r = bmesh.ops.create_cube(bm, size=1.0)
        for v in r["verts"]:
            v.co.x = v.co.x * sx + cx
            v.co.y = v.co.y * sy + cy
            v.co.z = v.co.z * sz + cz
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    o = rbox(name, (0, 0, 0), (1, 1, 1), m, radius=radius, segments=2)
    old = o.data
    o.data = me
    if not me.materials:
        me.materials.append(m)
    try:
        bpy.data.meshes.remove(old)
    except Exception:
        pass
    return o


def _crate(name, p):
    col = [float(c) for c in p["crate_color"]]
    m_plank = _wood("tower_stack_plank", col, p["grain"])
    m_post = _wood("tower_stack_post", [c * 0.62 for c in col], p["grain"])
    m_core = pbr("tower_stack_core", (0.10, 0.05, 0.02), rough=0.9)

    # horizontal planks on the four sides (outer face 0.59, recessed 1 cm behind the posts)
    planks = []
    zs = [-0.336, -0.112, 0.112, 0.336]          # 4 boards 0.20 tall, 2.4 cm gaps, inside z -0.46..0.46
    for z in zs:
        for s in (-1, 1):
            planks.append(((s * 0.57, 0, z), (0.04, 0.96, 0.20)))   # +/-X faces
            planks.append(((0, s * 0.57, z), (0.96, 0.04, 0.20)))   # +/-Y faces
    # lid and bottom: three boards running along X, slight overhang
    for y in (-0.40, 0.0, 0.40):
        planks.append(((0, y, 0.48), (1.22, 0.38, 0.04)))
        planks.append(((0, y, -0.48), (1.22, 0.38, 0.04)))
    crate = _boxes(f"{name}_crate", planks, m_plank, radius=0.008)

    posts = _boxes(f"{name}_crate_posts",
                   [((sx * 0.54, sy * 0.54, 0), (0.12, 0.12, 0.92)) for sx in (-1, 1) for sy in (-1, 1)],
                   m_post, radius=0.012)
    core = _boxes(f"{name}_crate_core", [((0, 0, 0), (1.08, 1.08, 0.92))], m_core, radius=0)
    attach(crate, posts, core)
    return crate


def _chair(name, p):
    m_frame = pbr(f"tower_stack_paint_{_tag(p['chair_color'])}",
                  tuple(float(c) for c in p["chair_color"]), rough=0.45)
    m_seat = _wood("tower_stack_seat", p["seat_color"], p["grain"], rough=0.5)

    # seat: top surface exactly at local z = 0, straight edges (tiny bevel) so toast can hang over -X
    seat = _boxes(f"{name}_chair", [((0, 0, -0.03), (0.60, 0.60, 0.06))], m_seat, radius=0.008)

    L = 0.255                                     # leg centre offset from the middle
    frame = [
        ((-L, -L, -0.48), (0.07, 0.07, 0.84)),    # front legs: floor (-0.9) up to under the seat
        ((L, -L, -0.48), (0.07, 0.07, 0.84)),
        ((-L, L, 0.0), (0.07, 0.07, 1.80)),       # back posts: floor up to the top of the back (+0.9)
        ((L, L, 0.0), (0.07, 0.07, 1.80)),
        ((-L, 0, -0.10), (0.04, 0.44, 0.08)),     # side aprons under the seat
        ((L, 0, -0.10), (0.04, 0.44, 0.08)),
        ((0, -L, -0.10), (0.44, 0.04, 0.08)),     # front / back aprons
        ((0, L, -0.10), (0.44, 0.04, 0.08)),
        ((-L, 0, -0.62), (0.04, 0.44, 0.04)),     # side rungs
        ((L, 0, -0.62), (0.04, 0.44, 0.04)),
        ((0, -L, -0.72), (0.44, 0.04, 0.04)),     # front / back rungs
        ((0, L, -0.72), (0.44, 0.04, 0.04)),
    ]
    fr = _boxes(f"{name}_chair_frame", frame, m_frame, radius=0.01)

    back = _boxes(f"{name}_chair_back", [
        ((0, L, 0.78), (0.58, 0.05, 0.18)),       # wide top rail (reads well on a phone)
        ((0, L, 0.42), (0.58, 0.04, 0.08)),       # middle rail
        ((-0.09, L, 0.60), (0.07, 0.03, 0.28)),   # two vertical slats
        ((0.09, L, 0.60), (0.07, 0.03, 0.28)),
    ], m_seat, radius=0.01)
    attach(seat, fr, back)
    return seat


def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    name = p["name"]
    base = float(p["base_height"])
    ox, oy = float(p["chair_offset"][0]), float(p["chair_offset"][1])

    root = group3d(name)
    crate = _crate(name, p)
    chair = _chair(name, p)
    attach(root, crate, chair)          # direct children of the root -> tracked separately

    crate.location = (0.0, 0.0, base + 0.5)            # resting on the table top
    chair.location = (ox, oy, base + 1.0 + 0.9)        # feet on the crate lid
    return root
