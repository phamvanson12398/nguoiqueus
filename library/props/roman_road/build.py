"""3D Roman road segment running along +X from the origin.
Crowned bed, polygonal grey paving stones, raised kerb stones on both sides, drainage ditches.
Origin = centre of the road start (x=0, y=0) on the ground (z=0); paving top z ~= 0.15.
Parts are group empties (bed, paving, kerb_l, kerb_r, ditch_l, ditch_r, optional water) so a story can
reveal the layers one by one.  Long pieces are split in ~2 m chunks so the ink outline stays thin.
Stone colour is deliberately warm: the blue sky gradient tints upward faces, neutral grey turns blue."""
import math
import random
import bpy
import bmesh
from core import ctx
from core.look import ramp_mat, pbr
from core.geo import group3d, attach

DEFAULTS = dict(length=20.0, width=4.0, stone_size=0.55,
                stone_color=[0.47, 0.41, 0.34], kerb_color=[0.62, 0.50, 0.34],
                bed_color=[0.16, 0.13, 0.10], ditch_color=[0.30, 0.19, 0.09],
                kerb_height=0.25, kerb_width=0.28, crown=0.035,
                ditch=True, ditch_width=0.45, water=False, seed=7)

BASE_Z = 0.09      # bed height at the paving edge
STONE_H = 0.03     # paving stone proud of the bed
SEG_MAX = 2.2      # chunk length (outline thickness depends on object size)


def _key(c):
    return "_".join(f"{v:.2f}" for v in c)


def _clamp(c, k):
    return tuple(min(1.0, max(0.0, v * k)) for v in c)


def _stone_mat(name, c):
    return ramp_mat(f"{name}_{_key(c)}", [(0.25, _clamp(c, 0.78)), (0.75, _clamp(c, 1.12))], scale=4.0, bump=0.15, rough=0.85)


def _new_obj(name, bm, mats, bevel=0.0):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    for m in mats:
        me.materials.append(m)
    o = bpy.data.objects.new(name, me)
    ctx.col.objects.link(o)
    if bevel > 0:
        b = o.modifiers.new("round", 'BEVEL'); b.width = bevel; b.segments = 2
        b.limit_method = 'ANGLE'; b.use_clamp_overlap = True
    return o


def _prism(bm, ring, ztop, zbot, mi=0):
    """ring = [(x, y), ...] CCW; ztop/zbot = f(x, y)"""
    t = [bm.verts.new((x, y, ztop(x, y))) for x, y in ring]
    b = [bm.verts.new((x, y, zbot(x, y))) for x, y in ring]
    n = len(ring)
    fs = [bm.faces.new(t), bm.faces.new(list(reversed(b)))]
    for i in range(n):
        j = (i + 1) % n
        fs.append(bm.faces.new((b[i], b[j], t[j], t[i])))
    for f in fs:
        f.material_index = mi


def _sweep(bm, prof, x0, x1):
    """closed cross-section prof = [(y, z), ...] swept along X from x0 to x1"""
    a = [bm.verts.new((x0, y, z)) for y, z in prof]
    b = [bm.verts.new((x1, y, z)) for y, z in prof]
    n = len(prof)
    bm.faces.new(a); bm.faces.new(list(reversed(b)))
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((a[i], a[j], b[j], b[i]))


def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    name = p["name"]
    rng = random.Random(p["seed"])
    L = max(1.0, float(p["length"]))
    W = max(1.0, float(p["width"]))
    kw = min(float(p["kerb_width"]), W * 0.2)
    hw = W / 2.0
    hp = hw - kw                       # paved half width
    crown = float(p["crown"])
    kh = float(p["kerb_height"])
    s = max(0.2, float(p["stone_size"]))

    nseg = max(1, int(math.ceil(L / SEG_MAX)))
    seg = L / nseg

    def zb(y):                         # crowned bed surface
        u = min(1.0, abs(y) / hp)
        return BASE_Z + crown * (1.0 - u * u)

    m_bed = ramp_mat(f"roman_road_bed_{_key(p['bed_color'])}", [(0.3, _clamp(p["bed_color"], 0.7)), (0.7, _clamp(p["bed_color"], 1.25))], scale=9.0, bump=0.3)
    m_stone = [_stone_mat(f"roman_road_stone{i}", _clamp(p["stone_color"], k)) for i, k in enumerate((0.8, 1.0, 1.2))]
    m_kerb = [_stone_mat(f"roman_road_kerb{i}", _clamp(p["kerb_color"], k)) for i, k in enumerate((0.9, 1.08))]
    m_ditch = ramp_mat(f"roman_road_ditch_{_key(p['ditch_color'])}", [(0.3, _clamp(p["ditch_color"], 0.75)), (0.7, _clamp(p["ditch_color"], 1.2))], scale=6.0, bump=0.25)

    root = group3d(name)
    g_bed = group3d(f"{name}_bed"); g_pav = group3d(f"{name}_paving")
    g_kerb = [group3d(f"{name}_kerb_l"), group3d(f"{name}_kerb_r")]
    attach(root, g_bed, g_pav, *g_kerb)
    sides = ((0, -1.0, "l"), (1, 1.0, "r"))

    # ---- bed: crowned road body, one chunk per segment and side ----
    for k in range(nseg):
        for si, sg, tag in sides:
            prof = [(0.0, -0.02), (hw, -0.02), (hw, zb(hp))]
            for i in range(10, -1, -1):
                y = hp * i / 10.0
                prof.append((y, zb(y)))
            prof = [(sg * y, z) for y, z in prof]
            if sg < 0: prof.reverse()
            bm = bmesh.new(); _sweep(bm, prof, k * seg, (k + 1) * seg)
            attach(g_bed, _new_obj(f"{name}_bed_{k}{tag}", bm, [m_bed]))

    # ---- paving: staggered rows of irregular polygon stones ----
    nr = max(2, int(round(2 * hp / s)))
    ch = 2 * hp / nr
    gap = 0.05
    bms = {}
    for r in range(nr):
        yc0 = -hp + ch * (r + 0.5)
        x = 0.0
        first = True
        while x < L - 1e-4:
            ln = s * (rng.uniform(0.45, 0.9) if (first and r % 2) else rng.uniform(0.8, 1.3))
            first = False
            x1 = min(L, x + ln)
            if L - x1 < 0.3 * s: x1 = L
            a = (x1 - x) / 2 - gap / 2; b = ch / 2 - gap / 2
            xc = (x + x1) / 2; yc = yc0
            n = rng.randint(6, 8); off = rng.uniform(0, 2 * math.pi)
            ring = []
            for i in range(n):
                th = off + 2 * math.pi * (i + rng.uniform(-0.2, 0.2)) / n
                c, sn = math.cos(th), math.sin(th)
                mm = max(abs(c), abs(sn))
                f = rng.uniform(0.86, 1.0)
                ring.append((xc + a * c / mm * f, yc + b * sn / mm * f))
            dz = rng.uniform(-0.006, 0.006); tx = rng.uniform(-0.012, 0.012); ty = rng.uniform(-0.012, 0.012)
            ztop = (lambda xc, yc, dz, tx, ty: (lambda X, Y: zb(Y) + STONE_H + dz + tx * (X - xc) + ty * (Y - yc)))(xc, yc, dz, tx, ty)
            kseg = min(nseg - 1, int(xc / seg)); si = 0 if yc < 0 else 1
            if (kseg, si) not in bms: bms[(kseg, si)] = bmesh.new()
            _prism(bms[(kseg, si)], ring, ztop, lambda X, Y: zb(Y) - 0.03, rng.randrange(3))
            x = x1
    for (kseg, si), bm in sorted(bms.items()):
        attach(g_pav, _new_obj(f"{name}_paving_{kseg}{'lr'[si]}", bm, m_stone, bevel=0.015))

    # ---- kerbs: block stones on both edges ----
    for si, sg, tag in sides:
        y0, y1 = sorted((sg * (hp + 0.005), sg * hw))
        kb = {}
        x = 0.0
        while x < L - 1e-4:
            x1 = min(L, x + rng.uniform(0.8, 1.25))
            if L - x1 < 0.35: x1 = L
            h = kh + rng.uniform(-0.012, 0.012)
            xa, xb = x + 0.015, x1 - 0.015
            kseg = min(nseg - 1, int((x + x1) / 2 / seg))
            if kseg not in kb: kb[kseg] = bmesh.new()
            _prism(kb[kseg], [(xa, y0), (xb, y0), (xb, y1), (xa, y1)],
                   (lambda h: (lambda X, Y: h))(h), lambda X, Y: 0.0, rng.randrange(2))
            x = x1
        for kseg, bm in sorted(kb.items()):
            attach(g_kerb[si], _new_obj(f"{name}_kerb_{tag}{kseg}", bm, m_kerb, bevel=0.03))

    # ---- drainage ditches outside the kerbs ----
    if p["ditch"]:
        dw = max(0.15, float(p["ditch_width"]))
        g_d = [group3d(f"{name}_ditch_l"), group3d(f"{name}_ditch_r")]
        attach(root, *g_d)
        m_water = pbr(f"roman_road_water", (0.04, 0.22, 0.45), rough=0.12)
        g_w = group3d(f"{name}_water") if p["water"] else None
        if g_w: attach(root, g_w)
        for si, sg, tag in sides:
            prof = [(0.0, -0.02), (dw + 0.2, -0.02), (dw, 0.09), (dw * 0.75, 0.025), (0.0, 0.025)]
            prof = [(sg * (hw + u), z) for u, z in prof]
            if sg < 0: prof.reverse()
            for k in range(nseg):
                bm = bmesh.new(); _sweep(bm, prof, k * seg, (k + 1) * seg)
                attach(g_d[si], _new_obj(f"{name}_ditch_{tag}{k}", bm, [m_ditch]))
                if g_w:
                    ya, yb = sorted((sg * (hw + 0.02), sg * (hw + dw * 0.7)))
                    bm = bmesh.new()
                    _prism(bm, [(k * seg, ya), ((k + 1) * seg, ya), ((k + 1) * seg, yb), (k * seg, yb)],
                           lambda X, Y: 0.045, lambda X, Y: 0.02)
                    attach(g_w, _new_obj(f"{name}_water_{tag}{k}", bm, [m_water]))
    return root
