"""3D oversized slice of sandwich bread (toast) with a glossy butter layer.

Normal mode: the slice lies flat in XY (thickness along Z), origin at the CENTRE of the slab so a story
can flip it around the Y axis.  Brown crust ring, pale-yellow crumb faces, domed "sandwich loaf" top
edge (toward +Y).  Butter on 'top' (+Z), 'bottom' (-Z), 'both' or 'none': wavy-edged 0.015 layer plus
a small butter pat.

splat=True: the slice has landed butter-side DOWN (crust/crumb face up), slightly squashed, a wavy
butter puddle oozes out around its rim on the floor, a few droplets, and the squashed pat peeks out on
one side.  Origin at the floor (z = 0).

Parts: <name>_bread (crumb faces <name>_bread_crumb are its child), <name>_butter (empty holding the
butter layers <name>_butter_top / _butter_bottom / _butter_puddle, pat <name>_butter_pat, droplets).
Flat slabs are built as clean bmesh prisms (recalculated normals) instead of curve extrusions: the
curve caps shaded wrong (grey crumb, green butter) and broke the ink hull into spikes.
Falls / flips / splats -> 3D."""
import math
import random
import bpy
import bmesh
from core import ctx
from core.look import pbr
from core.geo import rbox, sphere, group3d, attach, arc

DEFAULTS = dict(butter="top", splat=False, pat=True, squash=0.75,
                crust_color=[0.42, 0.17, 0.04], crumb_color=[0.98, 0.74, 0.32],
                butter_color=[0.98, 0.62, 0.03], scale=1.0)

W = 0.45        # slice width (x)
L = 0.45        # slice height (y), bottom edge to top of dome
T = 0.06        # thickness (z)
BT = 0.015      # butter thickness
SHOULDER = 0.06  # y where the straight sides end and the domed top begins


def _tag(rgb):
    return "_".join(str(int(round(c * 100))) for c in rgb)


def _prism(name, pts, z0, z1, m, bevel=0.0, loc=(0, 0, 0)):
    """closed slab: 2D outline (XY) from z0 to z1, outward normals, optional rounded edges"""
    area = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
               for i in range(len(pts)))
    if area < 0:
        pts = list(reversed(pts))
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bot = [bm.verts.new((x, y, z0)) for x, y in pts]
    top = [bm.verts.new((x, y, z1)) for x, y in pts]
    n = len(pts)
    bm.faces.new(top)
    bm.faces.new(list(reversed(bot)))
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bot[i], bot[j], top[j], top[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); ctx.col.objects.link(o)
    me.materials.append(m)
    o.location = loc
    if bevel > 0:
        b = o.modifiers.new("round", 'BEVEL'); b.width = bevel; b.segments = 2
        b.limit_method = 'ANGLE'; b.angle_limit = math.radians(60); b.use_clamp_overlap = True
    return o


def _slice_outline(inset):
    """sandwich-bread silhouette in XY: square bottom with rounded corners, slight shoulder
    overhang and a domed top"""
    hw = W / 2 - inset
    y0 = -L / 2 + inset
    rc = 0.035
    over = 0.014
    ry = L / 2 - SHOULDER - inset
    pts = []
    pts += arc(-hw + rc, y0 + rc, rc, rc, 180, 270, 4)
    pts += arc(hw - rc, y0 + rc, rc, rc, 270, 360, 4)
    pts.append((hw, SHOULDER - 0.025))
    pts += arc(0, SHOULDER, hw + over, ry, 0, 180, 28)
    pts.append((-hw, SHOULDER - 0.025))
    return pts


def _wavy(cx, cy, ax, ay, amp, lobes, n=72, phase=0.0):
    """wavy-edged rounded square (superellipse) blob: butter spread / puddle"""
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        c, s = math.cos(t), math.sin(t)
        x = ax * math.copysign(abs(c) ** 0.5, c)
        y = ay * math.copysign(abs(s) ** 0.5, s)
        k = 1.0 + amp * math.sin(lobes * t + phase)
        pts.append((cx + x * k, cy + y * k))
    return pts


def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    name = p["name"]
    mode = str(p["butter"]).lower()
    if mode not in ("top", "bottom", "both", "none"):
        mode = "top"
    splat = bool(p["splat"])
    want_pat = bool(p["pat"])

    crust_rgb = tuple(p["crust_color"]); crumb_rgb = tuple(p["crumb_color"]); butter_rgb = tuple(p["butter_color"])
    m_crust = pbr(f"toast_crust_{_tag(crust_rgb)}", crust_rgb, rough=0.85)
    m_crumb = pbr(f"toast_crumb_{_tag(crumb_rgb)}", crumb_rgb, rough=0.9)
    m_butter = pbr(f"toast_butter_{_tag(butter_rgb)}", butter_rgb, rough=0.2)

    root = group3d(name)

    # ---- bread: crust slab (rounded edge) + crumb faces standing 3 mm proud on both sides ----
    bread = _prism(f"{name}_bread", _slice_outline(0.0), -T / 2, T / 2, m_crust, bevel=0.012)
    crumb = _prism(f"{name}_bread_crumb", _slice_outline(0.032), -T / 2 - 0.003, T / 2 + 0.003, m_crumb)
    crumb.parent = bread

    # ---- butter group (empty) ----
    butter = group3d(f"{name}_butter")
    layers = []
    face = T / 2 + 0.003              # crumb face

    if not splat:
        sides = {"top": [1], "bottom": [-1], "both": [1, -1], "none": []}[mode]
        for sgn in sides:
            tag = "top" if sgn > 0 else "bottom"
            spread = _wavy(0.0, -0.015, 0.15, 0.14, 0.05, 9, phase=0.4 if sgn > 0 else 1.3)
            z0, z1 = sorted((sgn * (face - 0.001), sgn * (face + BT)))
            layers.append(_prism(f"{name}_butter_{tag}", spread, z0, z1, m_butter, bevel=0.005))
        if want_pat and sides:
            sgn = sides[0]
            pat = rbox(f"{name}_butter_pat", (0.03, -0.03, sgn * (face + BT + 0.021)), (0.10, 0.08, 0.045),
                       m_butter, radius=0.012)
            pat.rotation_euler = (0, 0, 0.35)
            layers.append(pat)
    else:
        sq = max(0.3, min(1.0, float(p["squash"])))
        th = 0.012                    # puddle thickness on the floor
        if mode != "none":
            layers.append(_prism(f"{name}_butter_puddle", _wavy(0.0, 0.0, 0.29, 0.29, 0.05, 11, phase=0.7),
                                 0.0, th, m_butter, bevel=0.005))
            rnd = random.Random(23)
            for k in range(5):
                a = 2 * math.pi * k / 5 + rnd.uniform(-0.3, 0.3)
                d = rnd.uniform(0.40, 0.48)
                r = rnd.uniform(0.022, 0.034)
                layers.append(sphere(f"{name}_butter_drop{k}", (d * math.cos(a), d * math.sin(a), r * 0.25), r,
                                     m_butter, scale=(1.0, 1.0, 0.3)))
            if want_pat:
                layers.append(sphere(f"{name}_butter_pat", (0.27, -0.17, 0.016), 0.06, m_butter,
                                     scale=(1.1, 0.85, 0.35)))
        # crust/crumb face up, squashed, sitting (slightly sunk) in the butter
        bread.scale = (1.04, 1.04, sq)
        bread.location = (0, 0, (th if mode != "none" else 0.0) - 0.004 + (T / 2 + 0.003) * sq)

    for lay in layers:
        lay.parent = butter
    attach(root, bread, butter)

    s = float(p["scale"])
    if s != 1.0:
        root.scale = (s, s, s)
    return root
