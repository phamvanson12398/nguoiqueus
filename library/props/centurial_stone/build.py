"""Roman centurial stone: a dressed sandstone building block whose front (-Y) face carries a recessed
rectangular panel with a carved Latin inscription naming the unit that built that stretch of wall.

dim '3d': chamfered block, corners nudged (hand-dressed), origin = centre of the bottom (stands on z=0).
          Parts: {name}_body (block), {name}_frame (raised border + darker recessed panel floor, one mesh),
          {name}_text (all letters merged into one dark mesh, sunk into the panel floor).
dim '2d': flat drawing with ink outline, hugged at the chest: parent = torso, placed at `at` ([0, 0.62, 0.42]).
          Parts: {name}_body, {name}_frame (empty with ring/floor/shadow shapes), {name}_text (flat mesh).
text:  '|' breaks the line, '>' is the centuria sign drawn as an angle/chevron glyph. Auto-fitted: condensed first
       (down to 72 %), then shrunk uniformly.  Cap height up to `letter_height` (0.075) -> readable in a 0.9-unit frame.
wonky: the 'Friday afternoon carving' gag: letters of random size and tilt, bouncing baseline, both lines sagging,
       the last three letters shrinking (ran out of room), one letter carved mirrored (a C if there is one) and the
       recessed panel rotated / off-centre with an uneven border.  The block itself is identical to the straight one
       (separate random stream) so the two compare side by side.
The letters skip the automatic ink hull (fake user -> counted as shared mesh): an outline would fatten small carved
letters until their counters close.  Stone colour matches wall_stone (warm and deep + warm_top): paler sand turned
olive on the top face under the blue sky gradient."""
import math
import random
import bpy
import bmesh
from core.look import ramp_mat, pbr, flat, warm_top
from core.geo import group3d, attach, rbox, cube, text3d, extrude, empty, shape, stroke

DEFAULTS = dict(text="> COH III | LEG II AVG", wonky=False, dim="3d",
                size=[0.5, 0.3, 0.32], letter_height=0.075, chamfer=0.03, rough=0.01, seed=5,
                stone_color=[0.70, 0.46, 0.22], groove_color=[0.10, 0.06, 0.035],
                at=[0, 0.62, 0.42], scale2d=1.0)

MARGIN = 0.034     # body edge -> outer edge of the frame
BORDER = 0.024     # width of the raised border
RING_OUT = 0.020   # border stands this far in front of the block face
FLOOR = 0.004      # recessed panel floor sits this far in front of the block face
SINK = 0.010       # letters reach this far behind the panel floor
PROUD = 0.003      # and stand this little in front of it
DEPTH = 0.02       # font extrusion used while building glyphs (remapped afterwards)
LINE_GAP = 0.42    # gap between lines, in cap heights


def _clamp(c, k):
    return tuple(min(1.0, max(0.0, float(v) * k)) for v in c)


def _key(c):
    return "_".join(f"{float(v):.2f}" for v in c)


def _rot(x, y, a):
    ca, sa = math.cos(a), math.sin(a)
    return x * ca - y * sa, x * sa + y * ca


# ---------------------------------------------------------------- glyphs
def _glyph(tmp, c, size, ch, m):
    """-> (verts [(x, y, z)], faces) of one character in font space (x right, y up, z toward viewer)"""
    if c == ">":                                   # centuria sign: a solid chevron pointing right
        h = ch; w = 0.62 * h; t = 0.22 * h
        pts = [(0.0, 0.0), (t, 0.0), (w, h / 2), (t, h), (0.0, h), (w - t * 1.15, h / 2)]
        o = extrude(tmp, (0, 0, 0), pts, DEPTH, m)
    else:
        o = text3d(tmp, (0, 0, 0), c, size, m, depth=DEPTH)
    me = o.data
    vs = [tuple(v.co) for v in me.vertices]
    fs = [tuple(pl.vertices) for pl in me.polygons]
    bpy.data.objects.remove(o)
    bpy.data.meshes.remove(me)
    return vs, fs


def _text_data(p, name, m, box_w, box_h, wonky, rng):
    """lay out all lines inside a box centred at (0, 0).
    -> (verts [(u, v, t)], faces); t = 0 back of the letter, 1 front"""
    raw = str(p.get("text") or "").upper()
    lines = [s.strip() for s in raw.split("|")]
    lines = [s for s in lines if s]
    if not lines:
        return [], []
    n = len(lines)
    ch = min(max(0.02, float(p["letter_height"])), box_h * 0.9 / (n + (n - 1) * LINE_GAP))
    tmp = f"{name}_tmpglyph"
    ref, _ = _glyph(tmp, "H", 1.0, 1.0, m)
    ys = [v[1] for v in ref]
    cap = (max(ys) - min(ys)) if ys and max(ys) > min(ys) else 0.7
    size = ch / cap

    cache = {}
    rows = []
    for line in lines:
        items = []
        for c in line:
            if c == " ":
                items.append(dict(sp=True, w=0.38 * ch, gap=0.0)); continue
            if c not in cache:
                vs, fs = _glyph(tmp, c, size, ch, m)
                if not vs:
                    cache[c] = None
                else:
                    x0 = min(v[0] for v in vs); x1 = max(v[0] for v in vs)
                    y0 = min(v[1] for v in vs); y1 = max(v[1] for v in vs)
                    z0 = min(v[2] for v in vs); z1 = max(v[2] for v in vs)
                    dz = (z1 - z0) or 1.0
                    cache[c] = dict(v=[(x - x0, y - y0, (z - z0) / dz if z1 > z0 else 1.0) for x, y, z in vs],
                                    f=fs, w=x1 - x0, h=y1 - y0)
            g = cache[c]
            if g is None:
                items.append(dict(sp=True, w=0.3 * ch, gap=0.0)); continue
            items.append(dict(sp=False, g=g, c=c, s=1.0, r=0.0, dv=0.0, mir=False, gap=0.1 * ch))
        rows.append(items)

    tilts = [0.0] * n
    offs = [0.0] * n
    if wonky:
        for items in rows:
            for it in items:
                if it["sp"]:
                    continue
                it["gap"] = rng.uniform(0.0, 0.32) * ch
                it["s"] = rng.uniform(0.8, 1.25)
                it["r"] = math.radians(rng.uniform(-14, 14))
                it["dv"] = rng.uniform(-0.15, 0.15) * ch
        tail = [it for it in rows[-1] if not it["sp"]][-3:]
        for it, k in zip(tail, (0.86, 0.68, 0.52)[3 - len(tail):]):
            it["s"] = k                              # ran out of room at the end of the last line
            it["r"] = math.radians(rng.uniform(-8, 8))
        glyphs = [it for items in rows for it in items if not it["sp"]]
        pick = next((it for it in glyphs if it["c"] == "C"), None)
        if pick is None:
            pick = next((it for pref in "NSRGLEKBDPFJZ7" for it in glyphs if it["c"] == pref), None)
        if pick is not None:
            pick["mir"] = True
        sg = rng.choice((-1, 1))
        for r in range(n):                           # all lines sag the same way, by different amounts
            tilts[r] = math.radians(rng.uniform(3.5, 6.5)) * sg
            offs[r] = rng.uniform(-0.012, 0.012)

    def row_w(items):
        w = sum((it["w"] if it["sp"] else it["g"]["w"] * it["s"]) + it["gap"] for it in items)
        return w - (items[-1]["gap"] if items else 0.0)

    widths = [max(1e-6, row_w(items)) for items in rows]
    ks = [min(1.0, box_w * 0.94 / w) for w in widths]
    cxs = [max(k, 0.72) for k in ks]
    U = min(k / cx for k, cx in zip(ks, cxs))
    chs = ch * U
    pitch = chs * (1.0 + LINE_GAP)

    V, F = [], []
    for r, items in enumerate(rows):
        cx = cxs[r]
        vr = ((n - 1) / 2 - r) * pitch
        base = vr - chs / 2
        pen = -widths[r] * cx * U / 2 + offs[r]
        ct, st = math.cos(tilts[r]), math.sin(tilts[r])
        for it in items:
            if it["sp"]:
                pen += (it["w"] + it["gap"]) * cx * U
                continue
            g = it["g"]; s = it["s"]
            gw = g["w"] * s * cx * U; gh = g["h"] * s * U
            ca, sa = math.cos(it["r"]), math.sin(it["r"])
            i0 = len(V)
            for x, y, t in g["v"]:
                x = x * s * cx * U; y = y * s * U
                if it["mir"]:
                    x = gw - x
                dx, dy = x - gw / 2, y - gh / 2
                x = gw / 2 + dx * ca - dy * sa
                y = gh / 2 + dx * sa + dy * ca
                x += pen; y += base + it["dv"] * U - vr
                x, y = x * ct - y * st, x * st + y * ct
                V.append((x, y + vr, t))
            for f in g["f"]:
                f2 = [i0 + i for i in f]
                if it["mir"]:
                    f2.reverse()
                F.append(tuple(f2))
            pen += (g["w"] * s + it["gap"]) * cx * U
    return V, F


# ---------------------------------------------------------------- panel
def _panel(L, H, wonky, rng):
    """outer / inner quads of the frame (CCW, seen from the front), text box size and text offset"""
    fw, fh = L - 2 * MARGIN, H - 2 * MARGIN
    b = BORDER
    O = [(-fw / 2, -fh / 2), (fw / 2, -fh / 2), (fw / 2, fh / 2), (-fw / 2, fh / 2)]
    I = [(-fw / 2 + b, -fh / 2 + b), (fw / 2 - b, -fh / 2 + b), (fw / 2 - b, fh / 2 - b), (-fw / 2 + b, fh / 2 - b)]
    box_w, box_h = fw - 2 * b, fh - 2 * b
    toff = (0.0, 0.0)
    if wonky:
        sg = rng.choice((-1, 1))
        a = math.radians(rng.uniform(2.8, 4.0)) * sg
        du, dv = rng.uniform(0.006, 0.010) * -sg, rng.uniform(-0.006, 0.004)
        sx = rng.uniform(0.004, 0.008) * rng.choice((-1, 1))
        sy = rng.uniform(0.003, 0.006) * rng.choice((-1, 1))
        O2 = []
        for x, y in O:
            x, y = _rot(x * 0.95, y * 0.93, a)
            O2.append((x + du, y + dv))
        I2 = []
        for x, y in I:
            x = x * 0.95 + sx + rng.uniform(-0.005, 0.005)
            y = y * 0.93 + sy + rng.uniform(-0.005, 0.005)
            x, y = _rot(x, y, a)
            I2.append((x + du, y + dv))
        O, I = O2, I2
        box_w, box_h = box_w * 0.95, box_h * 0.93
        toff = (du + sx + rng.uniform(0.008, 0.016) * sg, dv - 0.005)
    return O, I, box_w, box_h, toff


def _mesh_obj(nm, verts, faces, m):
    """mesh object made from raw data (built on a core cube so it is registered like every other block)"""
    o = cube(nm, (0, 0, 0), (1, 1, 1), m)
    me = o.data
    me.clear_geometry()
    me.from_pydata(verts, [], faces)
    me.update()
    return o


def _frame_obj(nm, O, I, pu, pv, y0, m_ring, m_floor):
    yt = y0 - RING_OUT; yb = y0 + 0.006; yf = y0 - FLOOR
    o = cube(nm, (0, 0, 0), (1, 1, 1), m_ring)
    bm = bmesh.new()

    def vert(q, y):
        return bm.verts.new((pu + q[0], y, pv + q[1]))

    of = [vert(q, yt) for q in O]; inf = [vert(q, yt) for q in I]
    ob = [vert(q, yb) for q in O]; ib = [vert(q, yb) for q in I]
    ring = []
    for i in range(4):
        j = (i + 1) % 4
        ring.append(bm.faces.new((of[i], of[j], inf[j], inf[i])))
        ring.append(bm.faces.new((ob[i], ib[i], ib[j], ob[j])))
        ring.append(bm.faces.new((ob[i], ob[j], of[j], of[i])))
        ring.append(bm.faces.new((ib[i], inf[i], inf[j], ib[j])))
    bmesh.ops.recalc_face_normals(bm, faces=ring)
    fl = bm.faces.new([vert(q, yf) for q in I])
    fl.normal_update()
    if fl.normal.y > 0:
        fl.normal_flip()
    fl.material_index = 1
    bm.to_mesh(o.data)
    bm.free()
    o.data.materials.append(m_floor)
    o.data.update()
    return o


# ---------------------------------------------------------------- build
def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    name = p["name"]
    L, D, H = (float(v) for v in p["size"])
    seed = int(p["seed"])
    rng_body = random.Random(seed)
    rng_w = random.Random(seed * 7 + 3)
    wonky = bool(p["wonky"])
    sc = p["stone_color"]; gc = tuple(float(v) for v in p["groove_color"])

    O, I, box_w, box_h, toff = _panel(L, H, wonky, rng_w)

    if str(p["dim"]).lower() == "2d":
        return _build_2d(p, name, L, H, sc, gc, O, I, box_w, box_h, toff, wonky, rng_body, rng_w)

    m_stone = warm_top(ramp_mat(f"centurial_stone_body_{_key(sc)}",
                                [(0.28, _clamp(sc, 0.74)), (0.72, _clamp(sc, 1.10))], scale=7.0, bump=0.35, rough=0.9))
    m_floor = warm_top(ramp_mat(f"centurial_stone_floor_{_key(sc)}",
                                [(0.30, _clamp(sc, 0.55)), (0.72, _clamp(sc, 0.80))], scale=9.0, bump=0.25, rough=0.95))
    m_text = pbr(f"centurial_stone_text_{_key(gc)}", gc, rough=0.95)

    root = group3d(name)

    # ---- body: chamfered block, corners nudged; the front face stays one flat plane for the panel ----
    ch_ = max(0.0, float(p["chamfer"])); r = max(0.0, float(p["rough"]))
    body = rbox(f"{name}_body", (0, 0, H / 2), (L, D, H), m_stone, radius=ch_, segments=1)
    for v in body.data.vertices:
        x, y, z = v.co
        v.co.x = x + rng_body.uniform(-r, r)
        if y > 0:
            v.co.y = y + rng_body.uniform(-r, r)
        if z > 0:
            v.co.z = z + rng_body.uniform(-r, r) * 0.8
            v.co.x *= 0.98
            if y > 0:
                v.co.y *= 0.97
    body.data.update()
    y0 = -D / 2
    pv = H / 2

    # ---- frame: raised border + darker recessed floor ----
    frame = _frame_obj(f"{name}_frame", O, I, 0.0, pv, y0, m_stone, m_floor)

    # ---- text: carved letters, back sunk behind the floor, front a hair proud ----
    V, F = _text_data(p, name, m_text, box_w, box_h, wonky, rng_w)
    yf = y0 - FLOOR
    if V:
        verts = [(toff[0] + u, yf - PROUD + (1.0 - t) * (SINK + PROUD), pv + toff[1] + v) for u, v, t in V]
        text = _mesh_obj(f"{name}_text", verts, F, m_text)
        text.data.use_fake_user = True          # shared-mesh path: no ink hull on small carved letters
    else:
        text = group3d(f"{name}_text")
    attach(root, body, frame, text)
    return root


def _build_2d(p, name, L, H, sc, gc, O, I, box_w, box_h, toff, wonky, rng_body, rng_w):
    s = max(0.2, float(p["scale2d"]))
    w, h = L * s, H * s
    parent = p.get("parent")
    g = empty(name, parent)
    if parent is not None:
        g.location = tuple(float(v) for v in p["at"])

    m_face = flat(f"centurial_stone_2d_face_{_key(sc)}", _clamp(sc, 1.05))
    m_ring = flat(f"centurial_stone_2d_ring_{_key(sc)}", _clamp(sc, 1.2))
    m_floor = flat(f"centurial_stone_2d_floor_{_key(sc)}", _clamp(sc, 0.74))
    m_shadow = flat(f"centurial_stone_2d_shadow_{_key(sc)}", _clamp(sc, 0.42))
    m_text = flat(f"centurial_stone_2d_text_{_key(gc)}", gc)

    def j(v):
        return v + rng_body.uniform(-0.006, 0.006) * s

    c = max(0.02, float(p["chamfer"]) * 1.3) * s
    outer = [(-w / 2 + c, -h / 2), (w / 2 - c, -h / 2), (w / 2, -h / 2 + c), (w / 2, h / 2 - c),
             (w / 2 - c, h / 2), (-w / 2 + c, h / 2), (-w / 2, h / 2 - c), (-w / 2, -h / 2 + c)]
    shape(g, f"{name}_body", [(j(x), j(y)) for x, y in outer], m_face, 0, outline=0.035)

    fr = empty(f"{name}_frame", g)
    shape(fr, f"{name}_frame_ring", [(x * s, y * s) for x, y in O], m_ring, 0.02, outline=0.02)
    shape(fr, f"{name}_frame_floor", [(x * s, y * s) for x, y in I], m_floor, 0.04, outline=0.012)
    # shadow along the inner top and left edges: reads as a recess
    cxm = sum(q[0] for q in I) / 4; cym = sum(q[1] for q in I) / 4
    sh = []
    for q in (I[0], I[3], I[2]):
        dx, dy = cxm - q[0], cym - q[1]
        dl = math.hypot(dx, dy) or 1.0
        sh.append(((q[0] + dx / dl * 0.009) * s, (q[1] + dy / dl * 0.009) * s))
    stroke(fr, f"{name}_frame_shadow", sh, 0.014 * s, 0.05, m=m_shadow)

    V, F = _text_data(p, name, m_text, box_w, box_h, wonky, rng_w)
    if V:
        verts = [((toff[0] + u) * s, (toff[1] + v) * s, 0.07 + t * 0.01) for u, v, t in V]
        text = _mesh_obj(f"{name}_text", verts, F, m_text)
        text.data.use_fake_user = True          # no ink hull: keeps small letters crisp
        text.parent = g
        text.location = (0, 0, 0)
    else:
        empty(f"{name}_text", g)
    return g
