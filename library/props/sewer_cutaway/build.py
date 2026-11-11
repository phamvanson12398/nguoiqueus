"""3D x-ray cutaway under a street: soil slice (cut face toward -Y), asphalt with a round hole + cast-iron lid,
half-cut concrete shaft with steel rungs, round sewer pipe in section (dark inside, water at the bottom) and
radial orange soil-pressure arrows grouped under <id>_arrows (origin at the pipe centre -> pop with scale).
Origin = centre of the road surface right above the shaft axis (z = 0)."""
import math
import bpy
import bmesh
from core import ctx
from core.look import pbr, flat, ramp_mat, iron_mat
from core.geo import cyl, sphere, group3d, attach, empty, _curve_to_mesh

DEFAULTS = dict(width=9.0, depth=1.0, soil_depth=5.5, road_t=0.25, hole_r=0.45, shaft_wall=0.12, rungs=4,
                tube_z=-3.2, tube_r=1.2, tube_wall=0.15, water_h=0.35, pebbles=True,
                n_arrows=8, arrow_len=0.9, arrow_gap=0.06, arrow_offset_deg=22.5, arrow_y=-0.55,
                soil_color=[0.42, 0.17, 0.04], road_color=[0.07, 0.07, 0.08], concrete_color=[0.55, 0.55, 0.56],
                water_color=[0.16, 0.30, 0.32], arrow_color=[0.98, 0.30, 0.02])

PRE = "sewer_cutaway"


def _prism(name, loops, depth, m, ycen=0.0):
    """section shape(s) drawn in (x, z) and pushed along Y (centred on ycen); several loops = holes/islands"""
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '2D'; cu.fill_mode = 'BOTH'; cu.extrude = depth / 2
    for pts in loops:
        sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
        for pt, (x, z) in zip(sp.points, pts):
            pt.co = (x, z, 0, 1)
        sp.use_cyclic_u = True
    tmp = bpy.data.objects.new(name + "_tmp", cu); ctx.col.objects.link(tmp)
    o = _curve_to_mesh(tmp, name, m)
    o.rotation_euler = (math.pi / 2, 0, 0)          # curve y -> world z, curve z -> world -y
    o.location = (0, ycen, 0)
    return o


def _half_pipe(name, ri, ro, z0, z1, m_out, m_in, n=16):
    """back half of a vertical tube (y >= 0): concrete cut faces/outside, dark inner wall"""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    rows = []
    for i in range(n + 1):
        a = math.pi * i / n; c, s = math.cos(a), math.sin(a)
        rows.append([bm.verts.new((ri * c, ri * s, z0)), bm.verts.new((ro * c, ro * s, z0)),
                     bm.verts.new((ro * c, ro * s, z1)), bm.verts.new((ri * c, ri * s, z1))])
    for A, B in zip(rows, rows[1:]):
        f = bm.faces.new((A[0], A[3], B[3], B[0])); f.material_index = 1; f.smooth = True
        f = bm.faces.new((A[1], B[1], B[2], A[2])); f.smooth = True
        bm.faces.new((A[2], B[2], B[3], A[3]))
        bm.faces.new((A[0], B[0], B[1], A[1]))
    bm.faces.new(rows[0]); bm.faces.new(list(reversed(rows[-1])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); ctx.col.objects.link(o)
    me.materials.append(m_out); me.materials.append(m_in)
    return o


def _child(o, parent):
    """parent keeping the current world placement (parents are unparented-at-origin or under root at origin)"""
    o.parent = parent
    o.matrix_parent_inverse = parent.matrix_basis.inverted()
    return o


def _arrow_pts(theta, r_tip, L, pad=0.0, hl=0.32, hw=0.24, sw=0.10):
    """arrow in (x, z) relative to the pipe centre, tip at radius r_tip pointing inward along -direction(theta)"""
    dx, dz = math.cos(theta), math.sin(theta)
    nx, nz = -dz, dx
    tx, tz = r_tip * dx, r_tip * dz
    st = [(-2.0 * pad, 0), (hl, hw + pad), (hl, sw + pad), (L + pad, sw + pad),
          (L + pad, -sw - pad), (hl, -sw - pad), (hl, -hw - pad)]
    return [(tx + s * dx + t * nx, tz + s * dz + t * nz) for s, t in st]


def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    name = p["name"]
    W, D = p["width"] / 2, p["depth"]
    rt, zb = p["road_t"], -p["soil_depth"]
    ri = p["hole_r"]; ro = ri + p["shaft_wall"]
    zc, r_in = p["tube_z"], p["tube_r"]; r_out = r_in + p["tube_wall"]

    m_soil = ramp_mat(f"{PRE}_soil", [(0.3, tuple(p["soil_color"])),
                                      (0.7, tuple(c * 0.7 for c in p["soil_color"]))], scale=1.6, bump=0.15)
    m_peb = pbr(f"{PRE}_pebble", (0.36, 0.32, 0.28), rough=0.7)
    m_road = pbr(f"{PRE}_road", tuple(p["road_color"]), rough=0.85)
    m_conc = pbr(f"{PRE}_concrete", tuple(p["concrete_color"]), rough=0.9)
    m_dark = pbr(f"{PRE}_dark", (0.03, 0.03, 0.035), rough=1.0)
    m_steel = pbr(f"{PRE}_steel", (0.72, 0.72, 0.74), rough=0.35, metal=0.8)
    m_water = pbr(f"{PRE}_water", tuple(p["water_color"]), rough=0.25)
    m_iron = iron_mat(f"{PRE}_iron", "rings")
    m_arrow = flat(f"{PRE}_arrow", tuple(p["arrow_color"]))
    m_ink = flat(f"{PRE}_ink", (0.02, 0.02, 0.025))

    root = group3d(name)

    # ---- soil: section with a notch for the shaft that opens into the pipe's outer circle ----
    zj = zc + math.sqrt(max(r_out ** 2 - ro ** 2, 0.0))
    a0 = math.atan2(zj - zc, ro); a1 = math.pi - a0           # shaft/pipe junction angles (right, left)
    n = 40
    arc_pts = [(r_out * math.cos(a0 - (2 * math.pi - (a1 - a0)) * i / n),
                zc + r_out * math.sin(a0 - (2 * math.pi - (a1 - a0)) * i / n)) for i in range(n + 1)]
    soil_loop = [(-W, -rt), (-ro, -rt), (-ro, zj)] + list(reversed(arc_pts))[1:-1] + [(ro, zj), (ro, -rt), (W, -rt), (W, zb), (-W, zb)]
    soil = _prism(f"{name}_soil", [soil_loop], D, m_soil)
    attach(root, soil)
    if p["pebbles"]:
        for k, (x, z, r) in enumerate([(-3.6, -1.0, 0.28), (3.3, -0.9, 0.24), (-2.9, -4.7, 0.30), (3.7, -4.4, 0.26),
                                       (-3.9, -3.0, 0.22), (3.1, -2.6, 0.20), (1.5, -0.8, 0.18), (-1.5, -5.05, 0.22),
                                       (1.9, -5.0, 0.25)]):
            if abs(x) > W - r or z < zb + r: continue
            pb = sphere(f"{name}_soil_peb{k}", (x, -D / 2 + 0.03, z), r, m_peb, scale=(1, 0.45, 0.85))
            _child(pb, soil)

    # ---- road: asphalt slab with the round hole seen in section ----
    road = _prism(f"{name}_road", [[(-W, 0), (-W, -rt), (-ri, -rt), (-ri, 0)],
                                   [(ri, 0), (ri, -rt), (W, -rt), (W, 0)]], D, m_road)
    attach(root, road)

    # ---- lid: cast-iron disc sitting flush in the hole ----
    lid = cyl(f"{name}_lid", (0, 0, -0.04), ri - 0.005, 0.08, m_iron, 48)
    attach(root, lid)

    # ---- shaft: half-cut concrete tube (back half), dark inside, steel rungs ----
    z_bot = zc + math.sqrt(max(r_in ** 2 - ro ** 2, 0.0)) - 0.01
    shaft = _half_pipe(f"{name}_shaft", ri, ro, z_bot, -0.08, m_conc, m_dark)
    attach(root, shaft)
    nr = max(0, int(p["rungs"]))
    for k in range(nr):
        z = -0.5 - k * (abs(z_bot) - 0.9) / max(nr - 1, 1)
        rg = cyl(f"{name}_shaft_rung{k}", (0, ri - 0.1, z), 0.035, ri * 0.9, m_steel, 12, rot=(0, math.pi / 2, 0))
        _child(rg, shaft)

    # ---- tube: concrete ring in section, open at the top into the shaft; dark back + water ----
    di = math.asin(min(ri / r_in, 0.999)); do = math.asin(min(ri / r_out, 0.999))
    oa0, oa1 = math.pi / 2 - do, -1.5 * math.pi + do
    ia0, ia1 = -1.5 * math.pi + di, math.pi / 2 - di
    ring = [(r_out * math.cos(oa0 + (oa1 - oa0) * i / 48), zc + r_out * math.sin(oa0 + (oa1 - oa0) * i / 48)) for i in range(49)]
    ring += [(r_in * math.cos(ia0 + (ia1 - ia0) * i / 48), zc + r_in * math.sin(ia0 + (ia1 - ia0) * i / 48)) for i in range(49)]
    tube = _prism(f"{name}_tube", [ring], D, m_conc)
    attach(root, tube)
    back = _prism(f"{name}_tube_back", [[(r_in * math.cos(2 * math.pi * i / 40), zc + r_in * math.sin(2 * math.pi * i / 40))
                                         for i in range(40)]], 0.03, m_dark, ycen=D / 2 - 0.05)
    _child(back, tube)
    if p["water_h"] > 0:
        rw = r_in - 0.01
        phi = math.acos(max(-1.0, min(1.0, (rw - p["water_h"]) / rw)))
        wpts = [(rw * math.cos(1.5 * math.pi - phi + 2 * phi * i / 24), zc + rw * math.sin(1.5 * math.pi - phi + 2 * phi * i / 24))
                for i in range(25)]
        water = _prism(f"{name}_tube_water", [wpts], D - 0.08, m_water, ycen=-0.02)
        _child(water, tube)

    # ---- arrows: radial soil pressure, tips at the pipe ring, origin at the pipe centre ----
    arrows = empty(f"{name}_arrows", root, (0, 0, zc))
    ay = p["arrow_y"]; r_tip = r_out + p["arrow_gap"]; L = p["arrow_len"]
    for k in range(max(0, int(p["n_arrows"]))):
        th = math.radians(p["arrow_offset_deg"]) + 2 * math.pi * k / max(1, int(p["n_arrows"]))
        a = _prism(f"{name}_arrows_a{k}", [_arrow_pts(th, r_tip, L)], 0.05, m_arrow, ycen=ay + 0.005)
        a.parent = arrows
        ink = _prism(f"{name}_arrows_a{k}_ol", [_arrow_pts(th, r_tip, L, pad=0.045)], 0.025, m_ink, ycen=ay + 0.0425)
        ink.parent = arrows
    return root
