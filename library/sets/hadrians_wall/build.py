"""Hadrian's Wall: a 60-long stretch along X (x = -30..30 from origin), north face toward +Y, wall centre line y = 0.

Finished stone wall: squared yellow-grey ashlar, faces at y = +-width/2, flat paved walk on top at z = 4.5
(a character stands at (-3, -0.2, 4.5)), low crenellated parapet with coping on the north edge up to z = 5.4.
Milecastle at x = 0 on the south side: yard ~6 x 7 (y -1.5 .. -8.5), walls 3 high, south gate between two piers
at y = -8.5, small barrack with a red tile roof.  North gate = arched passage through the wall at x = 0 (2.4 wide, 3 high).
Gate leaves are separate objects '<name>_gate_north' / '<name>_gate_south' with the origin on the WEST hinge edge,
at rest rotation (0, 0, 0): rotate Z negative = swings toward -Y (north gate: into the milecastle, south gate: out to
the south); a small X rotation makes the leaf shudder when knocked.  Iron ring knocker on the outer face.
Turrets (square, windows, top ~6) at x = +-20.
Options: kind stone|turf, width 3|2.4, build 0-1 (scaffold, stone piles, exposed rubble core, stepped east end),
ruin 0-1, ditch (V ditch north, y 6..10), causeway, crag (black whinstone cliff dropping north), vallum, fort,
road_on_top (18th-century Military Road built over the levelled wall), beacon_slots, gates, lit_windows.
Anchors: gate_north, gate_south, milecastle, turret_1, turret_2, walk, ditch (+ north_approach, south_approach,
center, crag_edge, vallum, fort, beacon_<slot> when present).  Night: story uses grade 'night' + vfx mist.
Uses its own Random(seed), not the shared `random`."""
import math
import random
import bpy
import bmesh
from mathutils import Matrix
from core import ctx
from core.look import pbr, flat, ramp_mat, MATS, warm_top
from core.geo import cube, cyl, sphere, cone, lathe, extrude, torus, group3d, attach, keep_hidden

PFX = "hadrians_wall"
WALK = 4.5          # top of the finished walkway
HALF = 30.0         # wall runs x = -30 .. 30
GATE_HW = 1.2       # half width of both gate passages
SPRING = 1.8        # arch springing height (arch crown = 3.0)
LEAF_W = 2.3        # gate leaf width (hinge on the west edge)

DEFAULTS = dict(name="wall", origin=[0.0, 0.0], kind="stone", width=3.0, build=1.0, ruin=0.0,
                ditch=True, causeway=True, crag=False, vallum=False, fort=False, road_on_top=False,
                beacon_slots=[], gates=True, lit_windows=False, stone_color=[0.50, 0.40, 0.22],
                hills=True, seed=7)

BOX_F = ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))


# ---------------- helpers ----------------
def _mk(name, bm, mats, recalc=False):
    if recalc:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for m in mats:
        me.materials.append(m)
    o = bpy.data.objects.new(name, me); ctx.col.objects.link(o)
    return o


def _boxes(name, boxes, mats):
    """many boxes in ONE mesh (one object, one outline).  box = (x0, x1, y0, y1, z0, z1[, mat_idx[, rot_z[, batter]]]);
    batter widens the bottom in Y (sloped turf faces)."""
    bm = bmesh.new()
    for bx in boxes:
        x0, x1, y0, y1, z0, z1 = bx[:6]
        mi = bx[6] if len(bx) > 6 else 0
        rz = bx[7] if len(bx) > 7 else 0.0
        bt = bx[8] if len(bx) > 8 else 0.0
        if x1 - x0 < 1e-4 or y1 - y0 < 1e-4 or z1 - z0 < 1e-4:
            continue
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        c, s = math.cos(rz), math.sin(rz)
        vs = []
        for z, e in ((z0, bt), (z1, 0.0)):
            for x, y in ((x0, y0 - e), (x1, y0 - e), (x1, y1 + e), (x0, y1 + e)):
                dx, dy = x - cx, y - cy
                vs.append(bm.verts.new((cx + dx * c - dy * s, cy + dx * s + dy * c, z)))
        for f in BOX_F:
            bm.faces.new([vs[i] for i in f]).material_index = mi
    return _mk(name, bm, mats)


def _gables(name, items, m):
    """gable roofs in one mesh: item = (x0, x1, y0, y1, eave_z, rise, ridge_axis 'x'|'y')"""
    bm = bmesh.new()
    for x0, x1, y0, y1, z0, rise, ax in items:
        if ax == 'x':
            yc = (y0 + y1) / 2
            P = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, yc, z0 + rise), (x1, yc, z0 + rise)]
        else:
            xc = (x0 + x1) / 2
            P = [(x0, y0, z0), (x0, y1, z0), (x1, y1, z0), (x1, y0, z0), (xc, y0, z0 + rise), (xc, y1, z0 + rise)]
        v = [bm.verts.new(q) for q in P]
        for f in ((0, 3, 2, 1), (0, 1, 5, 4), (2, 3, 4, 5), (3, 0, 4), (1, 2, 5)):
            bm.faces.new([v[i] for i in f])
    return _mk(name, bm, [m], recalc=True)


def _arc(cx, cz, r, a0, a1, n=14):
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cz + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def _xz(name, pts, depth, m, loc):
    """outline drawn in (x, z), thickness along Y (centred); mesh baked upright so rotation stays (0, 0, 0)"""
    o = extrude(name, (0.0, 0.0, 0.0), pts, depth, m)
    o.data.transform(Matrix.Rotation(math.pi / 2, 4, 'X'))
    o.location = loc
    return o


def _lintel(top):
    g = GATE_HW
    return [(-g, top)] + _arc(0.0, SPRING, g, 180, 0) + [(g, top)]


def _ring():
    return _arc(0.0, SPRING, 1.45, 180, 0) + _arc(0.0, SPRING, 1.18, 0, 180)


def _leaf():
    return [(0.0, 0.0), (LEAF_W, 0.0)] + _arc(LEAF_W / 2, SPRING, LEAF_W / 2, 0, 180)


def _ashlar(name, c1, c2, mortar, bw=0.62, rh=0.31):
    """squared stone courses from world position (x+y along the course, z up): continuous across separate meshes"""
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; L = nt.links; n = nt.nodes
    b = n["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.88
    geo = n.new("ShaderNodeNewGeometry")
    sep = n.new("ShaderNodeSeparateXYZ"); L.new(geo.outputs["Position"], sep.inputs[0])
    add = n.new("ShaderNodeMath"); add.operation = 'ADD'
    L.new(sep.outputs[0], add.inputs[0]); L.new(sep.outputs[1], add.inputs[1])
    comb = n.new("ShaderNodeCombineXYZ")
    L.new(add.outputs[0], comb.inputs[0]); L.new(sep.outputs[2], comb.inputs[1])
    br = n.new("ShaderNodeTexBrick"); br.offset = 0.5; br.squash = 1.0
    br.inputs["Color1"].default_value = (*c1, 1); br.inputs["Color2"].default_value = (*c2, 1)
    br.inputs["Mortar"].default_value = (*mortar, 1)
    br.inputs["Scale"].default_value = 1.0; br.inputs["Mortar Size"].default_value = 0.03
    br.inputs["Brick Width"].default_value = bw; br.inputs["Row Height"].default_value = rh
    L.new(comb.outputs[0], br.inputs["Vector"])
    L.new(br.outputs["Color"], b.inputs["Base Color"])
    bp = n.new("ShaderNodeBump"); bp.invert = True; bp.inputs["Strength"].default_value = 0.35
    L.new(br.outputs["Fac"], bp.inputs["Height"]); L.new(bp.outputs["Normal"], b.inputs["Normal"])
    MATS[name] = m
    return m


# ---------------- build ----------------
def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    N = str(p.get("name") or "wall")
    rnd = random.Random(int(p.get("seed", 7)))
    org = list(p.get("origin") or [0.0, 0.0]) + [0.0, 0.0]
    ox, oy = float(org[0]), float(org[1])
    turf = str(p.get("kind", "stone")).lower() == "turf"
    wv = p.get("width", 3.0)
    if isinstance(wv, str):
        w = 2.4 if wv.lower().startswith("n") else 3.0
    else:
        w = min(5.0, max(1.8, float(wv)))
    hw = w / 2
    b = min(1.0, max(0.05, float(p.get("build", 1.0))))
    ruin = min(1.0, max(0.0, float(p.get("ruin", 0.0))))
    road = bool(p.get("road_on_top"))
    crag = bool(p.get("crag"))
    ditch = bool(p.get("ditch")) and not crag
    vallum = bool(p.get("vallum"))
    finished = b >= 0.999 and ruin <= 1e-3 and not road
    building = b < 0.999 and ruin <= 1e-3 and not road
    H = WALK * b
    bat = 0.6 if turf else 0.0
    E = hw + 1.0                                        # crag edge (relative y)

    parts, anchors, noline = {}, {}, []

    # ---- materials ----
    sc = [float(c) for c in (list(p.get("stone_color") or DEFAULTS["stone_color"]) + [0.5, 0.5, 0.5])[:3]]
    tag = "%.2f_%.2f_%.2f" % tuple(sc)
    ashlar = _ashlar(f"{PFX}_ashlar_{tag}", sc, (sc[0] * 0.82, sc[1] * 0.84, sc[2] * 0.9),
                     (sc[0] * 0.45, sc[1] * 0.45, sc[2] * 0.45))
    warm_top(ashlar)
    turfm = ramp_mat(f"{PFX}_turf", [(0.2, (0.20, 0.14, 0.05)), (0.5, (0.29, 0.23, 0.09)), (0.8, (0.17, 0.24, 0.07))],
                     tex="wave", wave_dir='Z', scale=1.6, coord="Position", distortion=1.5, bump=0.25)
    grass = ramp_mat(f"{PFX}_grass", [(0.2, (0.09, 0.26, 0.04)), (0.55, (0.14, 0.34, 0.06)), (0.9, (0.22, 0.42, 0.08))],
                     scale=0.15, coord="Position", bump=0.08, rough=0.95)
    grass_d = ramp_mat(f"{PFX}_ditch", [(0.2, (0.05, 0.17, 0.03)), (0.6, (0.09, 0.24, 0.04)), (0.9, (0.16, 0.28, 0.06))],
                       scale=0.3, coord="Position", bump=0.1, rough=0.95)
    if turf:
        core = ramp_mat(f"{PFX}_soil", [(0.2, (0.18, 0.11, 0.05)), (0.6, (0.28, 0.18, 0.08)), (0.9, (0.34, 0.24, 0.11))],
                        scale=2.0, coord="Position", bump=0.3)
    else:
        core = ramp_mat(f"{PFX}_core", [(0.2, (0.22, 0.20, 0.16)), (0.6, (0.36, 0.32, 0.25)), (0.9, (0.46, 0.41, 0.32))],
                        scale=3.0, coord="Position", bump=0.45, voronoi=True)
    wood = ramp_mat(f"{PFX}_gate_wood", [(0.2, (0.24, 0.12, 0.05)), (0.6, (0.36, 0.20, 0.08)), (0.9, (0.44, 0.26, 0.11))],
                    tex="wave", wave_dir='X', scale=3.0, coord="Object", distortion=1.0, detail=2.0, bump=0.2)
    planks = ramp_mat(f"{PFX}_planks", [(0.2, (0.36, 0.20, 0.08)), (0.6, (0.50, 0.30, 0.12)), (0.9, (0.58, 0.36, 0.15))],
                      tex="wave", wave_dir='X', scale=2.5, coord="Position", distortion=0.8, detail=2.0, bump=0.2)
    flags = ramp_mat(f"{PFX}_flags", [(0.2, (0.52, 0.40, 0.24)), (0.6, (0.66, 0.50, 0.28)), (0.9, (0.74, 0.56, 0.30))],
                     scale=1.2, coord="Position", bump=0.3, voronoi=True)
    walkm = planks if turf else flags
    body = turfm if turf else ashlar
    tower = planks if turf else ashlar
    vous = pbr(f"{PFX}_voussoir", (0.40, 0.34, 0.24), rough=0.85) if not turf else wood
    pole = pbr(f"{PFX}_scaffold_pole", (0.45, 0.28, 0.12), rough=0.9)
    deck = pbr(f"{PFX}_scaffold_plank", (0.60, 0.40, 0.18), rough=0.85)
    iron = pbr(f"{PFX}_iron", (0.07, 0.07, 0.08), rough=0.45, metal=0.85)
    dark = flat(f"{PFX}_opening", (0.015, 0.012, 0.01))
    lit = flat(f"{PFX}_window_lit", (1.0, 0.55, 0.12))
    tile = pbr(f"{PFX}_roof_tile", (0.72, 0.20, 0.07), rough=0.7)
    block = warm_top(pbr(f"{PFX}_block", (0.58, 0.48, 0.32), rough=0.85))
    rock = ramp_mat(f"{PFX}_whinstone", [(0.2, (0.03, 0.03, 0.035)), (0.6, (0.07, 0.07, 0.075)), (0.9, (0.13, 0.13, 0.13))],
                    scale=0.5, coord="Position", bump=0.4, voronoi=True)
    dirt = ramp_mat(f"{PFX}_dirt", [(0.2, (0.36, 0.23, 0.10)), (0.6, (0.48, 0.32, 0.14)), (0.9, (0.56, 0.40, 0.18))],
                    scale=0.8, coord="Position", bump=0.1)
    gravel = ramp_mat(f"{PFX}_gravel", [(0.2, (0.42, 0.36, 0.28)), (0.6, (0.56, 0.48, 0.36)), (0.9, (0.64, 0.56, 0.42))],
                      scale=4.0, coord="Position", bump=0.2)
    for m in (flags, gravel, core, block): warm_top(m)

    # ---- ground profile (relative y, z) ----
    prof = [(-140.0, 0.0)]
    if vallum:
        prof += [(-35.0, 0.0), (-33.6, 1.3), (-31.4, 1.3), (-30.0, 0.0), (-28.4, -2.8), (-25.6, -2.8), (-24.0, 0.0),
                 (-22.6, 1.3), (-20.4, 1.3), (-19.0, 0.0)]
    if crag:
        prof += [(E, 0.0), (E + 0.7, -0.9), (E + 1.8, -4.0), (E + 3.0, -8.0), (E + 4.4, -11.2), (E + 6.0, -12.8),
                 (E + 9.0, -13.2), (140.0, -13.2)]
    elif ditch:
        prof += [(6.0, 0.0), (8.0, -2.6), (10.0, 0.0), (11.5, 0.6), (14.5, 0.6), (16.5, 0.0), (140.0, 0.0)]
    else:
        prof += [(140.0, 0.0)]

    def zprof(y):
        if y <= prof[0][0]:
            return prof[0][1]
        for (ya, za), (yb, zb) in zip(prof, prof[1:]):
            if ya <= y <= yb:
                return za + (zb - za) * (y - ya) / max(1e-6, yb - ya)
        return prof[-1][1]

    def gmi(yr):
        if crag and E < yr < E + 6.0:
            return 2
        if ditch and 6.0 < yr < 10.0:
            return 1
        if vallum and -30.0 < yr < -24.0:
            return 1
        return 0

    gbm = bmesh.new(); grid = []
    xs = [ox - 140.0 + 5.0 * i for i in range(57)]
    for x in xs:
        col = []
        for yr, z in prof:
            dx = dy = dz = 0.0
            if crag and E + 0.1 < yr < E + 5.9:
                dx, dy, dz = rnd.uniform(-0.6, 0.6), rnd.uniform(-0.4, 0.4), rnd.uniform(-0.5, 0.5)
            col.append(gbm.verts.new((x + dx, oy + yr + dy, z + dz)))
        grid.append(col)
    for i in range(len(xs) - 1):
        for j in range(len(prof) - 1):
            f = gbm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
            f.material_index = gmi(0.5 * (prof[j][0] + prof[j + 1][0]))
    parts["ground"] = _mk(f"{N}_ground", gbm, [grass, grass_d, rock])

    if crag:                                             # whinstone columns stepping down the cliff
        cb = []
        for k in range(3):
            yk = E + 1.0 + 1.4 * k
            x = -80.0
            while x < 80.0:
                wd = rnd.uniform(0.9, 1.5)
                top = min(zprof(yk - 0.7) + rnd.uniform(0.2, 1.0), -0.25)
                cb.append((ox + x, ox + x + wd, oy + yk - rnd.uniform(0.5, 0.7), oy + yk + rnd.uniform(0.5, 0.7),
                           -14.0, top, 0, rnd.uniform(-0.15, 0.15)))
                x += wd + rnd.uniform(0.1, 0.6)
        parts["crag"] = _boxes(f"{N}_crag", cb, [rock])
        anchors["crag_edge"] = [ox, oy + E, 0.0]

    if ditch and p.get("causeway", True):
        parts["causeway"] = _boxes(f"{N}_causeway", [(ox - 1.6, ox + 1.6, oy + 6.0, oy + 10.0, -2.6, 0.0)], [dirt])
    if vallum:
        _boxes(f"{N}_vallum_crossing", [(ox - 2.0, ox + 2.0, oy - 30.0, oy - 24.0, -2.8, 0.0)], [dirt])
        anchors["vallum"] = [ox, oy - 27.0, -2.8]

    # ---- wall segments ----
    def segs(a, z):
        n = max(1, int(round((z - a) / 2.4)))
        L = (z - a) / n
        return [(a + i * L, a + (i + 1) * L) for i in range(n)]

    def heights(sg):
        us = [rnd.uniform(0.2, 1.0) for _ in sg]
        hs = []
        for i, (x0, x1) in enumerate(sg):
            if road:
                h = 0.5 if x1 <= 12.01 else rnd.uniform(0.7, 1.6)
            else:
                h = H
                if building and x0 >= 22.9:              # construction front: stepped east end
                    h = H * (0.72, 0.5, 0.3, 0.2)[min(3, int((x0 - 22.9) // 2.4))]
                if ruin > 0:
                    u = 0.5 * us[i] + 0.25 * (us[max(0, i - 1)] + us[min(len(us) - 1, i + 1)])
                    h *= 1.0 - ruin * u
                h = max(0.35, h)
            hs.append(h)
        return hs

    def top(x0, x1, h):
        """-> (body top, standing height, extra boxes) for one wall segment"""
        X0, X1, Y0, Y1 = ox + x0, ox + x1, oy - hw, oy + hw
        out = []
        if finished:
            bt = h - 0.06
            out.append((X0, X1, Y0, Y1 - (0.3 if turf else 0.4), bt, h, 2))
            return bt, h, out
        if road and x1 <= 12.01:
            return h, h, out
        if building:
            if turf:
                out.append((X0, X1, Y0 + 0.05, Y1 - 0.05, h - 0.02, h + 0.06, 1))
                return h, h + 0.06, out
            bt = h - 0.22
            out += [(X0, X1, Y0, Y0 + 0.32, bt, h, 0), (X0, X1, Y1 - 0.32, Y1, bt, h, 0),
                    (X0, X1, Y0 + 0.32, Y1 - 0.32, h - 0.3, h - 0.12, 1)]
            return bt, h - 0.12, out
        cap = 3 if (turf or road or ruin >= 0.3) else 1
        out.append((X0, X1, Y0 + 0.05, Y1 - 0.05, h - 0.12, h + 0.05, cap))
        return h - 0.1, h + 0.05, out

    wb, tops = [], []

    def add_seg(x0, x1, h):
        bt, sz, out = top(x0, x1, h)
        wb.append((ox + x0, ox + x1, oy - hw, oy + hw, 0.0, bt, 0, 0.0, bat))
        if not turf and not road and bt > 0.4:
            wb.append((ox + x0, ox + x1, oy - hw - 0.12, oy + hw + 0.12, 0.0, 0.32, 0))
        wb.extend(out)
        tops.append((x0, x1, sz))

    def merged(sg, hs):
        out = []
        for (x0, x1), h in zip(sg, hs):
            if out and abs(out[-1][2] - h) < 1e-6:
                out[-1][1] = x1
            else:
                out.append([x0, x1, h])
        return out

    L_s, R_s = segs(-HALF, -GATE_HW), segs(GATE_HW, HALF)
    L_h, R_h = heights(L_s), heights(R_s)
    for x0, x1, h in merged(L_s, L_h) + merged(R_s, R_h):
        add_seg(x0, x1, h)

    arch_objs = []
    if road:
        add_seg(-GATE_HW, GATE_HW, 0.5)
    else:
        wb.append((ox - GATE_HW, ox + GATE_HW, oy - hw, oy + hw, 0.0, 0.05, 0))       # threshold
        bt_g, sz_g, out_g = top(-GATE_HW, GATE_HW, min(L_h[-1], R_h[0]))
        if bt_g >= 3.3:
            wb.extend(out_g)
            tops.append((-GATE_HW, GATE_HW, sz_g))
            arch_objs.append(_xz(f"{N}_arch_lintel", _lintel(bt_g), w, body, (ox, oy, 0.0)))
            arch_objs.append(_xz(f"{N}_arch_ring", _ring(), w + 0.08, vous, (ox, oy, 0.0)))

    def top_at(xr):
        best = None
        for x0, x1, sz in tops:
            if x0 - 1e-6 <= xr <= x1 + 1e-6:
                best = sz if best is None else max(best, sz)
        return best if best is not None else H

    wall_grp = group3d(f"{N}_wall")
    wall_body = _boxes(f"{N}_wall_body", wb, [body, core, walkm, grass])
    attach(wall_grp, wall_body)
    parts["wall"] = wall_grp
    if arch_objs:
        ag = group3d(f"{N}_arch", parent=wall_grp)
        attach(ag, *arch_objs)
        parts["arch"] = ag

    # ---- parapet ----
    if finished:
        pb = []
        if turf:
            x, k = -HALF + 0.12, 0
            while x < HALF - 0.1:
                pb.append((ox + x - 0.1, ox + x + 0.1, oy + hw - 0.28, oy + hw - 0.06, WALK - 0.06,
                           WALK + (1.0 if k % 2 == 0 else 0.86), 0))
                x += 0.26; k += 1
            pb.append((ox - HALF, ox + HALF, oy + hw - 0.36, oy + hw - 0.28, WALK + 0.55, WALK + 0.7, 0))
            parts["parapet"] = _boxes(f"{N}_parapet", pb, [planks])
        else:
            # breastwork + coping slab (coping keeps the top face off the mortar line), merlons with caps
            pb.append((ox - HALF, ox + HALF, oy + hw - 0.4, oy + hw, WALK - 0.06, 4.96, 0))
            pb.append((ox - HALF, ox + HALF, oy + hw - 0.44, oy + hw + 0.04, 4.96, 5.04, 1))
            x = -HALF + 0.5
            while x + 0.8 <= HALF - 0.2 + 1e-6:
                pb.append((ox + x, ox + x + 0.8, oy + hw - 0.4, oy + hw, 5.04, 5.34, 0))
                pb.append((ox + x - 0.03, ox + x + 0.83, oy + hw - 0.43, oy + hw + 0.03, 5.34, 5.42, 1))
                x += 1.7
            parts["parapet"] = _boxes(f"{N}_parapet", pb, [ashlar, flags])
        attach(wall_grp, parts["parapet"])

    # ---- turrets ----
    win = lit if p.get("lit_windows") else dark
    for i, txr in enumerate((-20.0, 20.0)):
        if road:
            Ht = 0.4 if txr <= 12.0 else 1.0
        else:
            Ht = 5.6 * b
            if ruin > 0:
                Ht *= 1.0 - 0.65 * ruin * rnd.uniform(0.7, 1.0)
        tx = ox + txr; y0 = oy - hw - 2.6; y1 = oy + hw + 0.06
        tb = []
        if finished:
            tb.append((tx - 2.0, tx + 2.0, y0, y1, 0.0, Ht - 0.05, 0))
            tb.append((tx - 1.7, tx + 1.7, y0 + 0.3, y1 - 0.3, Ht - 0.06, Ht, 1))
            for cx in (-1.65, -0.55, 0.55, 1.65):
                tb.append((tx + cx - 0.3, tx + cx + 0.3, y0, y0 + 0.35, Ht, Ht + 0.5, 0))
                tb.append((tx + cx - 0.3, tx + cx + 0.3, y1 - 0.35, y1, Ht, Ht + 0.5, 0))
            Lt = y1 - y0; n = max(2, int(Lt / 1.1))
            for k in range(1, n - 1):
                cy = y0 + (k + 0.5) * Lt / n
                for sx in (-1, 1):
                    xa = tx + sx * 2.0
                    tb.append((min(xa, xa - sx * 0.35), max(xa, xa - sx * 0.35), cy - 0.3, cy + 0.3, Ht, Ht + 0.5, 0))
        else:
            tb.append((tx - 2.0, tx + 2.0, y0, y1, 0.0, Ht, 0))
            if ruin >= 0.3 or road:
                tb.append((tx - 1.95, tx + 1.95, y0 + 0.05, y1 - 0.05, Ht - 0.05, Ht + 0.05, 3))
        if Ht > 5.3:
            for sx in (-1, 1):
                tb.append((tx + sx * 0.72 - 0.22, tx + sx * 0.72 + 0.22, y0 - 0.03, y0 + 0.01, 4.55, 5.25, 2))
            tb.append((tx - 0.18, tx + 0.18, y1 - 0.01, y1 + 0.03, 4.6, 5.25, 2))
        if Ht > 2.1:
            tb.append((tx - 0.5, tx + 0.5, y0 - 0.03, y0 + 0.01, 0.0, 1.9, 2))
        tg = group3d(f"{N}_turret_{i + 1}")
        attach(tg, _boxes(f"{N}_turret_{i + 1}_body", tb, [tower, walkm, win, grass]))
        parts[f"turret_{i + 1}"] = tg
        anchors[f"turret_{i + 1}"] = [tx, (y0 + y1) / 2, Ht]

    # ---- milecastle ----
    def mh(base):
        if road:
            return 0.5
        h = base * b
        if ruin > 0:
            h *= 1.0 - ruin * rnd.uniform(0.35, 0.9)
        return max(0.3, h)

    hp_l, hp_r = mh(3.6), mh(3.6)
    pieces = [(-4.0, -3.0, -9.0, -hw, mh(3.0)), (3.0, 4.0, -9.0, -hw, mh(3.0)),
              (-3.0, -1.9, -9.0, -8.0, mh(3.0)), (1.9, 3.0, -9.0, -8.0, mh(3.0)),
              (-1.9, -GATE_HW, -9.0, -8.0, hp_l), (GATE_HW, 1.9, -9.0, -8.0, hp_r)]
    if road:
        pieces.append((-GATE_HW, GATE_HW, -9.0, -8.0, 0.5))
    capped = not road and ruin < 0.3 and not (building and turf)
    mb = []
    for x0, x1, y0, y1, h in pieces:
        mb.append((ox + x0, ox + x1, oy + y0, oy + y1, 0.0, h, 0))
        if ruin >= 0.3 or road:
            mb.append((ox + x0 + 0.05, ox + x1 - 0.05, oy + y0 + 0.05, oy + y1 - 0.05, h - 0.05, h + 0.05, 1))
        elif capped:                                     # warm coping slab (stops the sky tinting the top blue)
            mb.append((ox + x0 - 0.04, ox + x1 + 0.04, oy + y0 - 0.04, oy + y1 + 0.04, h, h + 0.08, 2))
    if not road:
        mb.append((ox - GATE_HW, ox + GATE_HW, oy - 9.0, oy - 8.0, 0.0, 0.05, 0))
    top_s = min(hp_l, hp_r)
    if capped and top_s >= 3.3:
        mb.append((ox - GATE_HW, ox + GATE_HW, oy - 9.04, oy - 7.96, top_s, top_s + 0.08, 2))
    mc = group3d(f"{N}_milecastle")
    mc_objs = [_boxes(f"{N}_milecastle_walls", mb, [body, grass, walkm])]
    if not road and top_s >= 3.3:
        mc_objs.append(_xz(f"{N}_milecastle_lintel", _lintel(top_s), 1.0, body, (ox, oy - 8.5, 0.0)))
        mc_objs.append(_xz(f"{N}_milecastle_ring", _ring(), 1.08, vous, (ox, oy - 8.5, 0.0)))
    yard = _boxes(f"{N}_milecastle_yard", [(ox - 3.0, ox + 3.0, oy - 8.0, oy - hw, 0.0, 0.02)], [gravel])
    mc_objs.append(yard); noline.append(yard)
    if not road:
        bk = group3d(f"{N}_barrack", parent=mc)
        if ruin >= 0.3:
            attach(bk, _boxes(f"{N}_barrack_walls", [(ox - 2.9, ox - 1.4, oy - 7.6, oy - 2.4, 0.0, 0.4)], [body]))
        else:
            hb = 2.0 * max(0.5, b) if building else 2.0
            attach(bk, _boxes(f"{N}_barrack_walls", [(ox - 2.9, ox - 1.4, oy - 7.6, oy - 2.4, 0.0, hb, 0),
                                                       (ox - 1.41, ox - 1.37, oy - 5.45, oy - 4.55, 0.0, 1.6, 1)],
                              [body, dark]))
            if not building:
                attach(bk, _gables(f"{N}_barrack_roof", [(ox - 3.1, ox - 1.2, oy - 7.8, oy - 2.2, hb, 0.8, 'y')], tile))
            attach(bk, lathe(f"{N}_barrack_barrel", (ox + 2.3, oy - 3.0, 0.0),
                             [(0.0, 0.0), (0.3, 0.0), (0.36, 0.4), (0.3, 0.8), (0.0, 0.8)], wood, segments=16))
        parts["barrack"] = bk
    attach(mc, *mc_objs)
    parts["milecastle"] = mc

    # ---- gate leaves (origin on the west hinge, rotation 0; Z negative swings toward -Y) ----
    hidden = (not p.get("gates", True)) or road

    def gate(tag_, hx, hy, out_sign):
        nm = f"{N}_gate_{tag_}"
        o = _xz(nm, _leaf(), 0.18, wood, (hx, hy, 0.0))
        kids = []
        for k, z in enumerate((0.5, 2.05)):
            for s in (-1, 1):
                kids.append(cube(f"{nm}_strap{k}{'n' if s > 0 else 's'}", (LEAF_W / 2, s * 0.105, z), (2.2, 0.03, 0.14), iron))
        kids.append(cyl(f"{nm}_boss", (1.85, out_sign * 0.12, 1.36), 0.07, 0.06, iron, 12, rot=(math.pi / 2, 0, 0)))
        kids.append(torus(f"{nm}_knocker", (1.85, out_sign * 0.15, 1.2), 0.15, 0.032, iron,
                          rot=(math.pi / 2, 0, 0), major_seg=20, minor_seg=8))
        for c in kids:
            c.parent = o
        if hidden:
            for c in [o] + kids:
                keep_hidden(c, True)
        return o

    parts["gate_north"] = gate("north", ox - LEAF_W / 2, oy - hw + 0.35, 1)
    parts["gate_south"] = gate("south", ox - LEAF_W / 2, oy - 8.8, -1)

    # ---- construction: scaffold, stone piles, rubble heaps ----
    if building:
        yf = oy - hw - (0.6 if turf else 0.12)
        rows = (yf - 0.25, yf - 1.45)
        sb = []
        for xa, xb in ((-15.0, -5.0), (5.0, 16.0)):
            n = max(2, int(round((xb - xa) / 2.4)))
            pxs = [ox + xa + (xb - xa) * k / n for k in range(n + 1)]
            for x in pxs:
                for y in rows:
                    sb.append((x - 0.07, x + 0.07, y - 0.07, y + 0.07, 0.0, H + 1.3, 0))
            z = 1.5
            while z < H + 0.2:
                for y in rows:
                    sb.append((ox + xa - 0.15, ox + xb + 0.15, y - 0.06, y + 0.06, z - 0.06, z + 0.06, 0))
                for x in pxs:
                    sb.append((x - 0.05, x + 0.05, rows[1] - 0.1, oy - hw + 0.3, z + 0.06, z + 0.16, 0))
                sb.append((ox + xa, ox + xb, rows[1] - 0.12, rows[0] + 0.12, z + 0.16, z + 0.22, 1))
                z += 1.5
        parts["scaffold"] = _boxes(f"{N}_scaffold", sb, [pole, deck])
        st = []
        for px, py in ((-9.0, -hw - 4.2), (10.0, -hw - 4.0), (16.5, -hw - 3.6)):
            for lv, (nx, ny) in enumerate(((3, 2), (2, 2), (1, 1))):
                for ix in range(nx):
                    for iy in range(ny):
                        cx = ox + px + (ix - (nx - 1) / 2) * 0.64; cy = oy + py + (iy - (ny - 1) / 2) * 0.44
                        st.append((cx - 0.3, cx + 0.3, cy - 0.2, cy + 0.2, lv * 0.32, lv * 0.32 + 0.31, 0,
                                   rnd.uniform(-0.06, 0.06)))
        sg = group3d(f"{N}_stones")
        attach(sg, _boxes(f"{N}_stones_piles", st, [block]),
               cone(f"{N}_stones_rubble1", (ox - 12.5, oy - hw - 3.8, 0.4), 1.1, 0.2, 0.8, core, 12),
               cone(f"{N}_stones_rubble2", (ox + 13.0, oy - hw - 4.6, 0.35), 0.9, 0.15, 0.7, core, 12))
        parts["stones"] = sg

    # ---- ruin: fallen blocks ----
    if ruin > 0 and not building:
        fb = []
        for k in range(int(45 * ruin)):
            x = rnd.uniform(-HALF, HALF)
            north = (not crag) and rnd.random() < 0.45
            y = (hw + 0.5 + rnd.uniform(0.0, 3.0)) if north else (-hw - 0.5 - rnd.uniform(0.0, 3.5))
            if -4.5 < x < 4.5 and -9.5 < y < -hw:
                continue
            if -1.8 < x < 1.8:
                continue
            sx, sy, sz = rnd.uniform(0.55, 0.7), rnd.uniform(0.35, 0.45), rnd.uniform(0.28, 0.34)
            fb.append((ox + x - sx / 2, ox + x + sx / 2, oy + y - sy / 2, oy + y + sy / 2, 0.0, sz, 0,
                       rnd.uniform(0, math.pi)))
        if fb:
            parts["stones"] = _boxes(f"{N}_stones", fb, [block])

    # ---- road on top (Military Road over the levelled wall) ----
    if road:
        rg = group3d(f"{N}_road")
        agger = _boxes(f"{N}_road_agger", [(ox - 140.0, ox + 12.0, oy - 3.0, oy + 3.0, 0.0, 0.62)], [dirt])
        surf = _boxes(f"{N}_road_surface", [(ox - 140.0, ox + 12.0, oy - 2.5, oy + 2.5, 0.62, 0.67)], [gravel])
        attach(rg, agger, surf); noline.append(surf)
        parts["road"] = rg

    # ---- beacon braziers ----
    bs = p.get("beacon_slots")
    names = ["turret_1", "turret_2", "milecastle"]
    if bs is True:
        slots = names[:2]
    elif isinstance(bs, (int, float)) and not isinstance(bs, bool):
        slots = names[:max(0, min(3, int(bs)))]
    elif isinstance(bs, (list, tuple)):
        slots = [str(s) for s in bs if str(s) in names]
    else:
        slots = []
    logw = pbr(f"{PFX}_log", (0.34, 0.20, 0.09), rough=0.9)
    for slot in slots:
        if slot == "milecastle":
            x, y, z = ox + 2.2, oy - 0.3, top_at(2.2)
        else:
            a = anchors[slot]; x, y, z = a[0], a[1], a[2]
        g = group3d(f"{N}_beacon_{slot}")
        attach(g, cyl(f"{N}_beacon_{slot}_stand", (x, y, z + 0.32), 0.1, 0.64, iron, 10),
               lathe(f"{N}_beacon_{slot}_bowl", (x, y, z), [(0.0, 0.6), (0.22, 0.6), (0.6, 1.05), (0.54, 1.1), (0.0, 0.92)],
                     iron, segments=16, smooth=False),
               _boxes(f"{N}_beacon_{slot}_logs", [(x - 0.45, x + 0.45, y - 0.08, y + 0.08, z + 0.95, z + 1.1, 0, rz)
                                                  for rz in (0.0, 1.05, 2.1)], [logw]))
        parts[f"beacon_{slot}"] = g
        anchors[f"beacon_{slot}"] = [x, y, z + 1.15]

    # ---- distant fort ----
    fp = p.get("fort")
    if fp:
        fd = fp if isinstance(fp, dict) else {}
        at = list(fd.get("at", [-22.0, -52.0])) + [0.0, 0.0]; sz = list(fd.get("size", [36.0, 26.0])) + [30.0, 20.0]
        cx, cy = ox + float(at[0]), oy + float(at[1]); sx, sy = max(16.0, float(sz[0])), max(14.0, float(sz[1]))
        x0, x1, y0, y1 = cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2
        t, hfw, g = 1.2, 3.2 * (b if building else 1.0) * (1.0 - 0.7 * ruin), 1.6
        fb = [(x0, cx - g, y0, y0 + t, 0, hfw, 0), (cx + g, x1, y0, y0 + t, 0, hfw, 0),
              (x0, cx - g, y1 - t, y1, 0, hfw, 0), (cx + g, x1, y1 - t, y1, 0, hfw, 0),
              (x0, x0 + t, y0, y1, 0, hfw, 0), (x1 - t, x1, y0, y1, 0, hfw, 0)]
        for qx in (x0, x1):
            for qy in (y0, y1):
                fb.append((qx - 1.2, qx + 1.2, qy - 1.2, qy + 1.2, 0, hfw + 1.0, 0))
        for gy in (y0 + t / 2, y1 - t / 2):
            fb.append((cx + g, cx + g + 2.2, gy - 1.4, gy + 1.4, 0, hfw + 1.4, 0))
            fb.append((cx - g - 2.2, cx - g, gy - 1.4, gy + 1.4, 0, hfw + 1.4, 0))
            fb.append((cx - g, cx + g, gy - 0.1, gy + 0.1, 0, 2.6, 1))
        roofs = []
        if ruin < 0.3:
            for j in range(3):
                for yb in (y0 + 3.5 + j * 3.4, y1 - 3.5 - j * 3.4):
                    for xa, xb in ((x0 + 2.5, cx - 3.5), (cx + 3.5, x1 - 2.5)):
                        fb.append((xa, xb, yb - 1.0, yb + 1.0, 0, 2.0, 0))
                        roofs.append((xa - 0.2, xb + 0.2, yb - 1.25, yb + 1.25, 2.0, 0.8, 'x'))
            fb.append((cx - 3.0, cx + 3.0, cy - 3.0, cy + 3.0, 0, 3.0, 0))
            roofs.append((cx - 3.3, cx + 3.3, cy - 3.3, cy + 3.3, 3.0, 1.2, 'y'))
        fg = group3d(f"{N}_fort")
        attach(fg, _boxes(f"{N}_fort_walls", fb, [ashlar, dark]))
        if roofs:
            attach(fg, _gables(f"{N}_fort_roofs", roofs, tile))
        parts["fort"] = fg
        anchors["fort"] = [cx, cy, 0.0]

    # ---- paths (thin, no outline) ----
    pb = []
    if crag:
        pb.append((ox - 0.8, ox + 0.8, oy + hw, oy + E, 0.0, 0.02))
    elif ditch:
        pb += [(ox - 0.8, ox + 0.8, oy + hw, oy + 6.0, 0.0, 0.02), (ox - 0.8, ox + 0.8, oy + 16.5, oy + 45.0, 0.0, 0.02)]
    else:
        pb.append((ox - 0.8, ox + 0.8, oy + hw, oy + 45.0, 0.0, 0.02))
    pb.append((ox - 0.8, ox + 0.8, oy - 60.0, oy - 9.0, 0.0, 0.02))
    paths = _boxes(f"{N}_paths", pb, [dirt]); noline.append(paths)

    # ---- distant hills and a few hawthorns ----
    if p.get("hills", True):
        hg = group3d(f"{N}_hills"); hobj = []
        hA = pbr(f"{PFX}_hill", (0.16, 0.36, 0.08), rough=0.95)
        hB = pbr(f"{PFX}_hill_far", (0.24, 0.40, 0.18), rough=1.0)
        for i in range(10):
            for sgn, ya, yb in ((1, 70.0, 110.0), (-1, 80.0, 120.0)):
                yr = sgn * rnd.uniform(ya, yb); r = rnd.uniform(18, 30)
                x = ox - 120 + i * 26 + rnd.uniform(-6, 6)
                hobj.append(sphere(f"{N}_hill{'n' if sgn > 0 else 's'}{i}", (x, oy + yr, zprof(yr) - r * 0.06), r,
                                   hB if i % 2 else hA, scale=(1.8, 1.0, 0.30)))
        trunk = pbr(f"{PFX}_tree_trunk", (0.28, 0.17, 0.08), rough=0.9)
        leaf = pbr(f"{PFX}_tree_leaf", (0.07, 0.22, 0.04), rough=0.9)
        for i in range(8):
            yr = rnd.uniform(24.0, 60.0) if i % 2 == 0 else -rnd.uniform(14.0, 60.0)
            xr = rnd.choice((-1, 1)) * rnd.uniform(8.0, 45.0)
            if fp and yr < -30.0 and -45.0 < xr < 5.0:
                continue
            z0 = zprof(yr); s = rnd.uniform(0.8, 1.2)
            hobj.append(cyl(f"{N}_tree{i}_trunk", (ox + xr, oy + yr, z0 + 1.1 * s), 0.25 * s, 2.2 * s, trunk, 8))
            hobj.append(sphere(f"{N}_tree{i}", (ox + xr + 0.4, oy + yr, z0 + 2.6 * s), 1.6 * s, leaf, scale=(1.4, 1.1, 0.8)))
        attach(hg, *hobj)
        parts["hills"] = hg

    # ---- anchors ----
    anchors["center"] = [ox, oy, 0.0]
    anchors["gate_north"] = [ox, oy, 0.0]
    anchors["gate_south"] = [ox, oy - 8.5, 0.0]
    anchors["milecastle"] = [ox, oy - 5.0, 0.0]
    anchors["walk"] = [ox - 3.0, oy - 0.2, WALK if finished else (0.67 if road else top_at(-3.0))]
    anchors["ditch"] = [ox, oy + 8.0, -2.6 if ditch else zprof(8.0)]
    anchors["north_approach"] = [ox, oy + (E if crag else 14.0), 0.0 if crag else zprof(14.0)]
    anchors["south_approach"] = [ox, oy - 14.0, 0.0]

    return {"parts": parts, "anchors": anchors, "noline": noline}
