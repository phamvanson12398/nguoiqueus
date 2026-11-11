"""Ancient (Roman-era) countryside, daytime, open toward -Y.  Acting area around origin + (0, 4), ground top at z = 0.
region 'britain': low green hills, oak woods, thatched roundhouses far away (huts), optional mist banks (mist).
region 'italy'  : dry golden hills, umbrella pines, the Apennines far away; sun='auto' makes the shared Sun harsher.
Story features (positions relative to origin):
  swamp {at, r}            mud with a glossy water rim and reeds, mud top z 0.08 (a character at z -0.5 is knee deep)
  hills [{at, h}]          distant peaks, each with a flat spot (r ~3) exactly at z = h for a beacon_fire
  steep_slope {at, h, width, legs}  big slope rising toward +Y with a paved zig-zag road
  trackway [[x,y], ...]    winding dirt path
  outcrop {at, h, size}    flat-topped rock, top at z = h
  cutting {at, h, gap, angle}  hill cut in two, the gap runs along Y, rubble heaps at both mouths
Roman roads are the separate prop roman_road.  Uses its own Random(seed), not the shared `random`."""
import math
import random
import bpy
import bmesh
from core import ctx
from core.look import pbr, ramp_mat, MATS
from core.geo import cube, cyl, sphere, cone, lathe, group3d, attach

PFX = "roman_countryside"
DEFAULTS = dict(name="roman_countryside", origin=[0.0, 0.0], region="britain", huts=True, mist=False, sun="auto",
                swamp=None, hills=[{"at": [-24.0, 48.0], "h": 9.0}, {"at": [22.0, 62.0], "h": 12.0}],
                steep_slope=None, trackway=None, outcrop=None, cutting=None, trees=24, seed=3)

GROUND = {"britain": [(0.2, (0.10, 0.30, 0.05)), (0.55, (0.17, 0.40, 0.08)), (0.9, (0.25, 0.47, 0.10))],
          "italy": [(0.2, (0.56, 0.36, 0.10)), (0.55, (0.70, 0.48, 0.14)), (0.9, (0.80, 0.58, 0.18))]}
HILLS = {"britain": ((0.15, 0.38, 0.07), (0.24, 0.44, 0.16)), "italy": ((0.74, 0.48, 0.13), (0.64, 0.46, 0.22))}


# ---------------- helpers ----------------
def _bm_obj(name, verts, faces, mats, mat_idx=None, recalc=True):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    vs = [bm.verts.new(v) for v in verts]
    for k, f in enumerate(faces):
        try:
            fc = bm.faces.new([vs[i] for i in f])
        except ValueError:
            continue
        fc.material_index = mat_idx[k] if mat_idx else 0
    if recalc:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    for m in mats:
        me.materials.append(m)
    o = bpy.data.objects.new(name, me); ctx.col.objects.link(o)
    return o


def _smooth(pts, k=6):
    pts = [tuple(q) for q in pts]
    if len(pts) < 3:
        return pts
    P = [pts[0]] + pts + [pts[-1]]; out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for s in range(k):
            t = s / k; t2 = t * t; t3 = t2 * t
            out.append(tuple(0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in (0, 1)))
    out.append(pts[-1])
    return out


def _ribbon(name, pts, w, z, m):
    """flat strip along a polyline (mitred joints), counter-clockwise seen from above"""
    verts, faces = [], []
    n = len(pts)
    for i in range(n):
        a = pts[max(i - 1, 0)]; b = pts[min(i + 1, n - 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / L, dx / L
        verts.append((pts[i][0] - nx * w / 2, pts[i][1] - ny * w / 2, z))
        verts.append((pts[i][0] + nx * w / 2, pts[i][1] + ny * w / 2, z))
    for i in range(n - 1):
        faces.append((2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1))
    return _bm_obj(name, verts, faces, [m], recalc=False)


def _segments(name, segs, w, zf, lift, m):
    """separate quads per segment (extended by w/2 so hairpins overlap), heights from zf(x, y)"""
    verts, faces = [], []
    for (ax, ay), (bx, by) in segs:
        dx, dy = bx - ax, by - ay; L = math.hypot(dx, dy) or 1.0; ux, uy = dx / L, dy / L
        nx, ny = -uy, ux; e = w / 2
        A = (ax - ux * e, ay - uy * e); B = (bx + ux * e, by + uy * e)
        k = len(verts)
        for (px, py) in ((A[0] - nx * e, A[1] - ny * e), (B[0] - nx * e, B[1] - ny * e),
                         (B[0] + nx * e, B[1] + ny * e), (A[0] + nx * e, A[1] + ny * e)):
            verts.append((px, py, zf(px, py) + lift))
        faces.append((k, k + 1, k + 2, k + 3))
    return _bm_obj(name, verts, faces, [m], recalc=False)


def _blob(rnd, rx, ry, n=28, jit=0.1):
    return [((rx * (1 + rnd.uniform(-jit, jit))) * math.cos(2 * math.pi * i / n),
             (ry * (1 + rnd.uniform(-jit, jit))) * math.sin(2 * math.pi * i / n)) for i in range(n)]


def _slab(name, pts, cx, cy, z0, z1, m):
    """flat prism from an XY outline (top cap fanned from the centre so concave outlines stay clean)"""
    n = len(pts)
    verts = [(cx + x, cy + y, z0) for x, y in pts] + [(cx + x, cy + y, z1) for x, y in pts] + [(cx, cy, z1), (cx, cy, z0)]
    faces = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    faces += [(n + i, n + (i + 1) % n, 2 * n) for i in range(n)]
    faces += [((i + 1) % n, i, 2 * n + 1) for i in range(n)]
    return _bm_obj(name, verts, faces, [m])


def _mist_mat(name, alpha):
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear(); n = nt.nodes; L = nt.links
    tc = n.new("ShaderNodeTexCoord"); sp = n.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Generated"], sp.inputs[0])
    rx = n.new("ShaderNodeValToRGB"); e = rx.color_ramp.elements
    e[0].position, e[0].color = 0.0, (0, 0, 0, 1); e[1].position, e[1].color = 1.0, (0, 0, 0, 1)
    e.new(0.18).color = (1, 1, 1, 1); e.new(0.82).color = (1, 1, 1, 1)
    L.new(sp.outputs[0], rx.inputs[0])
    rz = n.new("ShaderNodeValToRGB"); e = rz.color_ramp.elements
    e[0].position, e[0].color = 0.0, (0.7, 0.7, 0.7, 1); e[1].position, e[1].color = 1.0, (0, 0, 0, 1)
    e.new(0.3).color = (1, 1, 1, 1)
    L.new(sp.outputs[2], rz.inputs[0])
    mul = n.new("ShaderNodeMath"); mul.operation = 'MULTIPLY'
    L.new(rx.outputs[0], mul.inputs[0]); L.new(rz.outputs[0], mul.inputs[1])
    mul2 = n.new("ShaderNodeMath"); mul2.operation = 'MULTIPLY'; mul2.inputs[1].default_value = alpha
    L.new(mul.outputs[0], mul2.inputs[0])
    tr = n.new("ShaderNodeBsdfTransparent")
    em = n.new("ShaderNodeEmission"); em.inputs[0].default_value = (0.82, 0.87, 0.90, 1)
    mix = n.new("ShaderNodeMixShader")
    L.new(mul2.outputs[0], mix.inputs[0]); L.new(tr.outputs[0], mix.inputs[1]); L.new(em.outputs[0], mix.inputs[2])
    out = n.new("ShaderNodeOutputMaterial"); L.new(mix.outputs[0], out.inputs[0])
    if hasattr(m, "surface_render_method"):
        m.surface_render_method = 'BLENDED'
    MATS[name] = m
    return m


def _free(zones, x, y, pad=0.0):
    return all(math.hypot(x - zx, y - zy) > zr + pad for zx, zy, zr in zones)


def _find_spot(rnd, zones, x, y, pad, spread=14.0, tries=40):
    """the requested spot if free, else the nearest free random spot around it (never closer to the camera than y+8)"""
    if _free(zones, x, y, pad):
        return x, y
    best = None
    for _ in range(tries):
        qx = x + rnd.uniform(-spread, spread); qy = y + rnd.uniform(-spread, spread)
        if _free(zones, qx, qy, pad):
            d = math.hypot(qx - x, qy - y)
            if best is None or d < best[0]:
                best = (d, qx, qy)
    return (best[1], best[2]) if best else None


# ---------------- build ----------------
def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    N = p.get("name") or PFX
    rnd = random.Random(p["seed"])
    ox, oy = (list(p["origin"]) + [0.0, 0.0])[:2]
    region = p["region"] if p["region"] in GROUND else "britain"
    italy = region == "italy"

    def rel(q):
        return ox + float(q[0]), oy + float(q[1])

    parts, anchors, noline = {}, {}, []
    anchors["center"] = [ox, oy + 4.0, 0.0]

    gmat = ramp_mat(f"{PFX}_ground_{region}", GROUND[region], scale=0.12, coord="Position", bump=0.08, rough=0.95)
    hillA = pbr(f"{PFX}_hill_{region}", HILLS[region][0], rough=0.95)
    hillB = pbr(f"{PFX}_far_{region}", HILLS[region][1], rough=1.0)
    rock = ramp_mat(f"{PFX}_rock_{region}",
                    [(0.2, (0.36, 0.34, 0.31)), (0.6, (0.50, 0.47, 0.42)), (0.9, (0.62, 0.58, 0.52))] if not italy else
                    [(0.2, (0.55, 0.50, 0.42)), (0.6, (0.70, 0.64, 0.54)), (0.9, (0.80, 0.74, 0.62))],
                    scale=0.6, coord="Position", bump=0.3, voronoi=True)
    dirt = ramp_mat(f"{PFX}_dirt", [(0.2, (0.38, 0.24, 0.10)), (0.6, (0.50, 0.32, 0.14)), (0.9, (0.58, 0.40, 0.18))],
                    scale=0.8, coord="Position", bump=0.1)

    if italy and p.get("sun", "auto") == "auto":
        sun = bpy.data.objects.get("Sun")
        if sun is not None and sun.type == 'LIGHT':
            sun.data.energy = max(sun.data.energy, 4.6)
            sun.data.color = (1.0, 0.90, 0.74)
            sun.data.angle = math.radians(1.5)

    parts["ground"] = cube(f"{N}_ground", (ox, oy + 75.0, -0.05), (260.0, 250.0, 0.1), gmat)

    zones = [(ox, oy + 4.0, 10.0)]

    # ---- swamp ----
    sw = p.get("swamp")
    if sw:
        sx, sy = rel(sw.get("at", [0.0, 4.0])); r = float(sw.get("r", 4.0))
        zones.append((sx, sy, r * 1.25 + 1.0))
        grp = group3d(f"{N}_swamp")
        bank = pbr(f"{PFX}_swamp_bank", (0.26, 0.30, 0.08), rough=0.9)
        water = pbr(f"{PFX}_swamp_water", (0.07, 0.15, 0.11), rough=0.05)
        mud = ramp_mat(f"{PFX}_swamp_mud", [(0.2, (0.20, 0.14, 0.05)), (0.6, (0.30, 0.22, 0.08)), (0.9, (0.34, 0.30, 0.10))],
                       scale=0.9, coord="Position", bump=0.25, rough=0.45)
        outline = _blob(rnd, r, r * 0.8, 30, 0.08)
        objs = [_slab(f"{N}_swamp_bank", [(x * 1.18, y * 1.18) for x, y in outline], sx, sy, -0.02, 0.04, bank),
                _slab(f"{N}_swamp_water", [(x * 0.97, y * 0.97) for x, y in outline], sx, sy, 0.0, 0.06, water),
                _slab(f"{N}_swamp_mud", [(x * rnd.uniform(0.74, 0.84), y * rnd.uniform(0.74, 0.84)) for x, y in outline],
                      sx, sy, 0.0, 0.08, mud)]
        for i in range(3):
            a = rnd.uniform(0, 2 * math.pi); d = rnd.uniform(0.15, 0.45) * r
            pr = rnd.uniform(0.35, 0.6) * r * 0.35
            objs.append(_slab(f"{N}_swamp_puddle{i}", _blob(rnd, pr * 1.4, pr, 16, 0.12),
                              sx + d * math.cos(a), sy + d * 0.8 * math.sin(a), 0.0, 0.09, water))
        reed = pbr(f"{PFX}_reed", (0.32, 0.42, 0.08), rough=0.8)
        head = pbr(f"{PFX}_reed_head", (0.30, 0.16, 0.06), rough=0.8)
        for c in range(7):
            a = 2 * math.pi * c / 7 + rnd.uniform(-0.3, 0.3)
            bx, by = sx + r * 1.08 * math.cos(a), sy + r * 0.86 * math.sin(a)
            if math.sin(a) < -0.6:                           # keep the camera side of the swamp open
                continue
            for k in range(5):
                x = bx + rnd.uniform(-0.45, 0.45); y = by + rnd.uniform(-0.35, 0.35); Lr = rnd.uniform(1.1, 1.8)
                objs.append(cone(f"{N}_reed{c}_{k}", (x, y, Lr / 2), 0.07, 0.015, Lr, reed, 8))
                if k % 2 == 0:
                    objs.append(cyl(f"{N}_reedhead{c}_{k}", (x, y, Lr * 0.82), 0.08, 0.3, head, 10))
        attach(grp, *objs)
        parts["swamp"] = grp
        anchors["swamp_center"] = [sx, sy, 0.0]

    # ---- beacon hills ----
    patch = pbr(f"{PFX}_hilltop_patch", (0.45, 0.30, 0.13), rough=0.95)
    for i, h in enumerate(p.get("hills") or []):
        hx, hy = rel(h.get("at", [0.0, 50.0])); H = float(h.get("h", 8.0)); R = max(10.0, H * 2.4)
        prof = [(R, 0.0), (R * 0.78, H * 0.3), (R * 0.5, H * 0.66), (R * 0.28, H * 0.9), (3.4, H * 0.985), (3.0, H), (0.0, H)]
        o = lathe(f"{N}_hill_{i + 1}", (hx, hy, 0.0), prof, gmat, segments=40, smooth=True)
        top = cyl(f"{N}_hill_{i + 1}_top", (hx, hy, H + 0.005), 2.6, 0.02, patch, 24)
        top.parent = o; top.location = (0.0, 0.0, H + 0.005)
        parts[f"hill_{i + 1}"] = o
        anchors[f"hill_{i + 1}"] = [hx, hy, H]
        zones.append((hx, hy, R))

    # ---- steep slope with a zig-zag paved road ----
    ss = p.get("steep_slope")
    if ss:
        cx, cy = rel(ss.get("at", [0.0, 30.0])); H = float(ss.get("h", 10.0)); W = float(ss.get("width", 20.0))
        legs = max(2, int(ss.get("legs", 4)))
        L = H / math.tan(math.radians(35)); y0 = cy - L / 2; y1 = cy + L / 2; y2 = y1 + 6.0; y3 = y2 + H * 1.3
        Wb, Wt = W / 2 + 6.0, W / 2
        verts = [(cx - Wb, y0, 0), (cx + Wb, y0, 0), (cx + Wb, y3, 0), (cx - Wb, y3, 0),
                 (cx - Wt, y1, H), (cx + Wt, y1, H), (cx + Wt, y2, H), (cx - Wt, y2, H)]
        faces = [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (4, 5, 6, 7), (3, 2, 1, 0)]
        parts["slope"] = _bm_obj(f"{N}_slope", verts, faces, [gmat])

        def zf(x, y):
            return H * min(1.0, max(0.0, (y - y0) / L))

        a = W / 2 - 2.0
        path = [(cx - a, y0 - 5.0)]
        for k in range(legs + 1):
            path.append((cx + (-a if k % 2 == 0 else a), y0 + 0.6 + (L - 1.2) * k / legs))
        path.append((path[-1][0], y1 + 3.0))
        segs = list(zip(path, path[1:]))
        pave = ramp_mat(f"{PFX}_paving", [(0.2, (0.40, 0.38, 0.35)), (0.6, (0.58, 0.55, 0.50)), (0.9, (0.66, 0.62, 0.56))],
                        scale=1.4, coord="Position", bump=0.35, voronoi=True)
        kerb = pbr(f"{PFX}_kerb", (0.28, 0.26, 0.24), rough=0.9)
        road = _segments(f"{N}_slope_road", segs, 2.0, zf, 0.07, pave)
        kb = _segments(f"{N}_slope_kerb", segs, 2.6, zf, 0.04, kerb)
        parts["slope_road"] = road; noline += [road, kb]
        anchors["slope"] = [cx, cy, H / 2]
        anchors["slope_foot"] = [path[0][0], path[0][1], 0.0]
        anchors["slope_top"] = [path[-1][0], path[-1][1], H]
        for zx in (-1, 1):
            zones.append((cx + zx * W * 0.35, cy + 3.0, W * 0.5 + 6.0))

    # ---- dirt trackway ----
    tw = p.get("trackway")
    if tw and len(tw) >= 2:
        pts = _smooth([rel(q) for q in tw], 8)
        tr = _ribbon(f"{N}_trackway", pts, 1.4, 0.015, dirt)
        parts["trackway"] = tr; noline.append(tr)
        anchors["trackway_start"] = [pts[0][0], pts[0][1], 0.0]
        for q in pts[::3]:
            zones.append((q[0], q[1], 2.0))

    # ---- flat-topped outcrop ----
    oc = p.get("outcrop")
    if oc:
        qx, qy = rel(oc.get("at", [6.0, 8.0])); H = float(oc.get("h", 3.0)); S = float(oc.get("size", 4.0))
        prof = [(S * 0.78, 0.0), (S * 0.72, H * 0.4), (S * 0.6, H * 0.85), (S * 0.53, H * 0.97), (S * 0.5, H), (0.0, H)]
        o = lathe(f"{N}_outcrop", (qx, qy, 0.0), prof, rock, segments=9, smooth=False)
        for v in o.data.vertices:
            if v.co.z < H - 1e-3:
                k = rnd.uniform(0.86, 1.14); v.co.x *= k; v.co.y *= k
        o.rotation_euler = (0.0, 0.0, rnd.uniform(0, math.pi))
        for i in range(3):
            a = rnd.uniform(0, 2 * math.pi); d = S * 0.85; s = rnd.uniform(0.35, 0.7)
            b = sphere(f"{N}_outcrop_boulder{i}", (qx + d * math.cos(a), qy + d * math.sin(a), s * 0.35), s, rock,
                       scale=(1.3, 1.0, 0.75))
            b.parent = o; b.matrix_parent_inverse = o.matrix_world.inverted()
        parts["outcrop"] = o
        anchors["outcrop"] = [qx, qy, H]
        zones.append((qx, qy, S + 2.0))

    # ---- road cutting through a hill ----
    cu = p.get("cutting")
    if cu:
        cx, cy = rel(cu.get("at", [0.0, 30.0])); Hc = float(cu.get("h", 7.0)); g = float(cu.get("gap", 7.0)) / 2
        an = math.radians(float(cu.get("angle", 0.0))); ca, sa = math.cos(an), math.sin(an)

        def R(lx, ly):
            return cx + lx * ca - ly * sa, cy + lx * sa + ly * ca

        cutface = ramp_mat(f"{PFX}_cutface", [(0.2, (0.48, 0.30, 0.14)), (0.55, (0.62, 0.44, 0.24)), (0.9, (0.46, 0.40, 0.34))],
                           tex="wave", wave_dir='Z', scale=0.35, coord="Position", distortion=3.0, bump=0.2)
        grp = group3d(f"{N}_cutting"); objs = []
        ys = [-9.0, -5.0, 0.0, 5.0, 9.0]; fs = [0.12, 0.8, 1.0, 0.8, 0.12]
        for side, s in (("left", -1), ("right", 1)):
            verts = []
            for yk, f in zip(ys, fs):
                for lx, z in ((g, 0.0), (g + 0.9, Hc * f), (g + 4.5, Hc * f), (g + 10.0, Hc * f * 0.6), (g + 13.0 + 7.0 * f, 0.0)):
                    X, Y = R(s * lx, yk); verts.append((X, Y, z))
            faces, mi = [], []
            for k in range(4):
                for j in range(4):
                    b = k * 5 + j; faces.append((b, b + 5, b + 6, b + 1)); mi.append(1 if j == 0 else 0)
            faces.append(tuple(range(5))); mi.append(0)
            faces.append(tuple(range(20, 25))); mi.append(0)
            faces.append(tuple([k * 5 for k in range(5)] + [k * 5 + 4 for k in reversed(range(5))])); mi.append(0)
            objs.append(_bm_obj(f"{N}_cutting_{side}", verts, faces, [gmat, cutface], mi))
            for end in (-1, 1):
                hx, hy = R(s * (g + 1.8), end * 10.6)
                objs.append(cone(f"{N}_cutting_heap_{side}{end}", (hx, hy, 0.55), 1.8, 0.3, 1.1, dirt, 12))
                for k in range(6):
                    rx, ry = R(s * (g + 1.8 + rnd.uniform(-1.6, 1.6)), end * (10.6 + rnd.uniform(-1.8, 1.8)))
                    rs = rnd.uniform(0.25, 0.6)
                    objs.append(sphere(f"{N}_cutting_rock_{side}{end}_{k}", (rx, ry, rs * 0.4), rs, rock, scale=(1.3, 1.0, 0.7)))
            for k in range(4):
                rx, ry = R(s * (g - 0.1), rnd.uniform(-6.0, 6.0)); rs = rnd.uniform(0.25, 0.45)
                objs.append(sphere(f"{N}_cutting_stone_{side}{k}", (rx, ry, rs * 0.4), rs, rock, scale=(1.2, 1.0, 0.7)))
        attach(grp, *objs)
        parts["cutting"] = grp
        anchors["cutting"] = [cx, cy, 0.0]
        zones.append((cx, cy, g + 22.0))

    # ---- thatched roundhouses (britain): placed before trees so they always get their spot ----
    if not italy and p.get("huts", True):
        hgrp = group3d(f"{N}_huts"); hobjs = []
        wall = pbr(f"{PFX}_hut_wall", (0.58, 0.42, 0.24), rough=0.95)
        thatch = ramp_mat(f"{PFX}_thatch", [(0.2, (0.48, 0.30, 0.08)), (0.6, (0.62, 0.40, 0.11)), (0.9, (0.70, 0.48, 0.14))],
                          tex="wave", wave_dir='Z', scale=2.0, coord="Position", distortion=4.0, bump=0.3)
        door = pbr(f"{PFX}_hut_door", (0.12, 0.07, 0.04), rough=0.9)
        fence = pbr(f"{PFX}_fence", (0.36, 0.22, 0.10), rough=0.9)
        for i, (hx, hy, s) in enumerate(((-15, 21, 1.0), (-21, 25, 0.85), (-9, 27, 0.9), (16, 24, 0.95))):
            spot = _find_spot(rnd, zones, ox + hx, oy + hy, 3.6 * s)
            if spot is None:
                continue
            x, y = spot
            hobjs.append(cyl(f"{N}_hut{i}_wall", (x, y, 0.9 * s), 2.4 * s, 1.8 * s, wall, 24))
            hobjs.append(cone(f"{N}_hut{i}_roof", (x, y, 1.8 * s + 1.4 * s), 3.1 * s, 0.12 * s, 2.8 * s, thatch, 24))
            hobjs.append(cube(f"{N}_hut{i}_door", (x, y - 2.36 * s, 0.7 * s), (1.0 * s, 0.14, 1.4 * s), door))
            for k in range(5):                               # a few wattle-fence posts in front
                fx = x + (k - 2) * 1.3 * s + 0.4; fy = y - 4.2 * s
                hobjs.append(cyl(f"{N}_hut{i}_post{k}", (fx, fy, 0.55), 0.09, 1.1, fence, 8))
            hobjs.append(cube(f"{N}_hut{i}_rail", (x + 0.4, y - 4.2 * s, 0.75), (5.4 * s, 0.1, 0.12), fence))
            zones.append((x, y, 4.6 * s))
        attach(hgrp, *hobjs)
        parts["huts"] = hgrp

    # ---- background hills (and the Apennines) ----
    for i in range(11):
        x = ox - 120 + i * 24 + rnd.uniform(-6, 6); y = oy + rnd.uniform(85, 118); r = rnd.uniform(18, 30)
        sphere(f"{N}_bghill{i}", (x, y, -r * 0.06), r, hillB if i % 2 else hillA, scale=(1.8, 1.0, 0.30))
    for i in range(6):
        side = -1 if i % 2 == 0 else 1
        x = ox + side * rnd.uniform(28, 70); y = oy + rnd.uniform(45, 70); r = rnd.uniform(10, 15)
        if _free(zones, x, y, r * 0.8):
            sphere(f"{N}_midhill{i}", (x, y, -r * 0.05), r, hillA, scale=(1.6, 1.0, 0.28))
    if italy:
        mrock = pbr(f"{PFX}_apennine", (0.36, 0.36, 0.44), rough=0.95)
        mcap = pbr(f"{PFX}_apennine_cap", (0.80, 0.74, 0.66), rough=0.95)
        for i in range(8):
            x = ox - 140 + i * 40 + rnd.uniform(-10, 10); y = oy + rnd.uniform(150, 178)
            Rm = rnd.uniform(30, 44); Hm = rnd.uniform(22, 34)
            o = lathe(f"{N}_apennine{i}", (x, y, 0.0), [(Rm, 0.0), (Rm * 0.62, Hm * 0.45), (Rm * 0.3, Hm * 0.78),
                                                        (Rm * 0.08, Hm * 0.97), (0.0, Hm)], mrock, segments=7, smooth=False)
            c = lathe(f"{N}_apennine{i}_cap", (x, y, 0.0), [(Rm * 0.33, Hm * 0.74), (Rm * 0.09, Hm * 0.975), (0.0, Hm + 0.3)],
                      mcap, segments=7, smooth=False)
            rz = rnd.uniform(0, math.pi); o.rotation_euler = (0, 0, rz); c.rotation_euler = (0, 0, rz)

    # ---- trees ----
    tgrp = group3d(f"{N}_trees"); tobjs = []
    ntree = int(p.get("trees", 24))
    if italy:
        trunk = pbr(f"{PFX}_pine_trunk", (0.42, 0.22, 0.11), rough=0.9)
        crown = pbr(f"{PFX}_pine_crown", (0.10, 0.26, 0.06), rough=0.9)
        shrub = pbr(f"{PFX}_shrub", (0.30, 0.34, 0.10), rough=0.9)
        placed = 0; tries = 0
        while placed < ntree and tries < ntree * 20:
            tries += 1
            x = ox + rnd.choice((-1, 1)) * rnd.uniform(9, 48); y = oy + rnd.uniform(10, 75)
            if not _free(zones, x, y, 2.5):
                continue
            Ht = rnd.uniform(5.0, 7.5); cr = rnd.uniform(2.0, 2.8)
            tobjs.append(cyl(f"{N}_pine_trunk{placed}", (x, y, Ht / 2), 0.22, Ht, trunk, 10))
            tobjs.append(sphere(f"{N}_pine{placed}", (x, y, Ht + 0.3), cr, crown, scale=(1.5, 1.5, 0.42)))
            zones.append((x, y, 2.5)); placed += 1
        for i in range(14):
            x = ox + rnd.uniform(-40, 40); y = oy + rnd.uniform(8, 50)
            if not _free(zones, x, y, 1.2):
                continue
            s = rnd.uniform(0.6, 1.1)
            tobjs.append(sphere(f"{N}_shrub{i}", (x, y, s * 0.35), s, shrub, scale=(1.3, 1.3, 0.7)))
    else:
        trunk = pbr(f"{PFX}_oak_trunk", (0.30, 0.18, 0.08), rough=0.9)
        leafA = pbr(f"{PFX}_oak_leaf", (0.07, 0.24, 0.04), rough=0.9)
        leafB = pbr(f"{PFX}_oak_leaf2", (0.12, 0.31, 0.05), rough=0.9)
        clusters = []                                        # wood clusters on free ground, both sides of the frame
        for want in ((-26, 18), (24, 16), (-40, 34), (38, 34), (-6, 40), (50, 60), (-55, 60)):
            spot = _find_spot(rnd, zones, ox + want[0], oy + want[1], 6.0, spread=16.0)
            if spot:
                clusters.append(spot)
        if not clusters:
            clusters = [(ox - 30, oy + 20), (ox + 30, oy + 20)]
        placed = 0; tries = 0
        while placed < ntree and tries < ntree * 20:
            tries += 1
            ccx, ccy = clusters[tries % len(clusters)]
            x = ccx + rnd.uniform(-7, 7); y = ccy + rnd.uniform(-5, 5)
            if y < oy + 10 or not _free(zones, x, y, 2.6):
                continue
            s = rnd.uniform(0.85, 1.25); th = 2.6 * s
            leaf = leafA if placed % 2 else leafB
            tobjs.append(cyl(f"{N}_oak_trunk{placed}", (x, y, th / 2), 0.35 * s, th, trunk, 10))
            tobjs.append(sphere(f"{N}_oak{placed}", (x, y, th + 1.3 * s), 2.2 * s, leaf, scale=(1.1, 1.0, 0.9)))
            for sd in (-1, 1):
                tobjs.append(sphere(f"{N}_oak{placed}_{sd}", (x + sd * 1.5 * s, y + rnd.uniform(-0.5, 0.5), th + 0.7 * s),
                                    1.55 * s, leaf))
            zones.append((x, y, 2.6 * s)); placed += 1
    for i in range(10):                                      # loose boulders
        x = ox + rnd.uniform(-30, 30); y = oy + rnd.uniform(9, 40); s = rnd.uniform(0.3, 0.75)
        if _free(zones, x, y, 1.0):
            tobjs.append(sphere(f"{N}_boulder{i}", (x, y, s * 0.25), s, rock, scale=(1.3, 1.0, 0.6)))
    # foreground grass tufts / bracken so the near ground is not an empty lawn (kept off the centre of the stage)
    tuft = pbr(f"{PFX}_tuft_{region}", (0.06, 0.20, 0.03) if not italy else (0.48, 0.34, 0.08), rough=0.9)
    nt_ = 0
    for i in range(60):
        x = ox + rnd.uniform(-16, 16); y = oy + rnd.uniform(-6, 18)
        if math.hypot(x - ox, y - oy - 4.0) < 5.5:
            continue
        if not _free(zones[1:], x, y, 0.6):
            continue
        for k in range(3):
            Lt = rnd.uniform(0.35, 0.6)
            o = cone(f"{N}_tuft{nt_}_{k}", (x + rnd.uniform(-0.15, 0.15), y + rnd.uniform(-0.15, 0.15), Lt / 2),
                     0.1, 0.0, Lt, tuft, 6)
            o.rotation_euler = (rnd.uniform(-0.35, 0.35), rnd.uniform(-0.35, 0.35), 0.0)
            tobjs.append(o)
        nt_ += 1
        if nt_ >= 26:
            break
    attach(tgrp, *tobjs)
    parts["trees"] = tgrp

    # ---- mist banks (transparent, no outlines, no shadows) ----
    if p.get("mist"):
        mgrp = group3d(f"{N}_mist"); mobjs = []
        for k, (dy, hh, al) in enumerate(((16.0, 2.2, 0.35), (30.0, 4.0, 0.5), (48.0, 6.0, 0.55), (75.0, 9.0, 0.6))):
            y = oy + dy; x0, x1 = ox - 110.0, ox + 110.0
            o = _bm_obj(f"{N}_mist{k}", [(x0, y, 0.0), (x1, y, 0.0), (x1, y, hh), (x0, y, hh)], [(0, 1, 2, 3)],
                        [_mist_mat(f"{PFX}_mist{k}", al)], recalc=False)
            if hasattr(o, "visible_shadow"):
                o.visible_shadow = False
            mobjs.append(o)
        attach(mgrp, *mobjs)
        parts["mist"] = mgrp; noline.append(mgrp)

    return {"parts": parts, "anchors": anchors, "noline": noline}
