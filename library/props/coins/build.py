"""Roman silver denarius set (warm silver). Choose with item:

item='coin2d'  : hand-held 2D coin in the character plane, radius r2d = 0.14 (x scale2d). Silver rim on a thin ink disc,
                 bright field, generic laureate head in profile (NOT a real portrait) with ribbon ties, and a generic legend
                 ring (bars + small rings, no real letters) around the top; a white shine on the rim. Origin at the centre.
                 Part: {name}_coin (empty, scale = scale2d); head lives in {name}_coin_face (mirrored by facing=-1).
item='purse2d' : 2D leather money pouch ~0.4 wide x 0.36 tall, cinched neck with a cord, knot and two tails, ruffled mouth,
                 optional silver coin peeking out (peek). Origin at the bag centre. Part: {name}_purse.
item='coin3d'  : one 3D coin, radius r3d = 0.15, thickness 0.02, for falling / rolling. Origin at the centre.
                 Lathe body (raised rim, slightly sunken field) + raised head on both faces. Part: {name}_coin (group).
item='stack'   : n 3D coins stacked with small offsets and random spin. Origin at the bottom centre.
                 Part: {name}_stack (group) holding {name}_coin0..{name}_coin{n-2} and the top coin {name}_coin (with relief),
                 so a story can flick the top coin off.
2D items with a parent (torso) sit at `at` = [x right, y up, z forward]. 3D items ignore the parent.
Only the parts of the chosen item are created. 2D layers are spaced 0.02 in z (outline tubes have depth).
3D silver = metallic pbr wrapped in warm_top so the up-facing side is not tinted blue-grey by the sky."""
import math
import random
from core.look import flat, pbr, warm_top
from core.geo import empty, shape, stroke, disc, ellipse, arc, group3d, attach, lathe, extrude

DEFAULTS = dict(item="coin2d", n=6, at=[0.42, 0.45, 0.15], scale2d=1.0, r2d=0.14, r3d=0.15, thickness=0.02,
                silver_color=[0.80, 0.75, 0.66], leather_color=[0.45, 0.22, 0.08], cord_color=[0.90, 0.66, 0.28],
                facing=1, legend=True, shine=True, peek=True, relief=True, seed=3)

# generic laureate head in profile, facing +x, in coin-radius units (scaled by HS so it fits inside the legend ring)
HEAD = [(-0.32, -0.60), (-0.26, -0.46), (-0.19, -0.34), (-0.28, -0.18), (-0.34, 0.0), (-0.31, 0.20), (-0.20, 0.35),
        (-0.02, 0.43), (0.15, 0.39), (0.24, 0.28), (0.27, 0.15), (0.35, 0.04), (0.34, 0.0), (0.27, -0.03),
        (0.29, -0.09), (0.25, -0.13), (0.27, -0.20), (0.21, -0.26), (0.11, -0.29), (0.11, -0.40), (0.24, -0.50),
        (0.26, -0.60)]
HS = 0.82


def _clamp(c, k=1.0):
    return tuple(min(1.0, max(0.0, float(v) * k)) for v in c)


def _key(c):
    return "_".join(f"{float(v):.2f}" for v in c)


def _mat(tag, col, k=1.0):
    return flat(f"coins_{tag}_{_key(col)}_{k:.2f}", _clamp(col, k))


def _qbez(a, c, b, n=8):
    out = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        out.append((u * u * a[0] + 2 * u * t * c[0] + t * t * b[0], u * u * a[1] + 2 * u * t * c[1] + t * t * b[1]))
    return out


def _leaf(cx, cy, ang, L, W, n=10):
    ca, sa = math.cos(ang), math.sin(ang)
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x, y = L * math.cos(t), W * math.sin(t)
        pts.append((cx + ca * x - sa * y, cy + sa * x + ca * y))
    return pts


def _ostroke(par, nm, pts, w, z, m, ol=0.025):
    """coloured stroke with an ink rim: fat ink tube behind, coloured tube 0.02 in front"""
    stroke(par, nm + "_ink", pts, w + ol, z, m=None)
    stroke(par, nm, pts, w, z + 0.02, m=m)


def _sc(pts, k):
    return [(x * k, y * k) for x, y in pts]


# ---------------------------------------------------------------- 2D coin
def _coin2d(part, name, R, M, p, rng):
    k = R / 0.14                                       # line widths follow the coin size
    ol = 0.022 * k
    # ink disc behind, silver rim disc on top (no outline tube: it swallowed the rim colour), field, inner rim line
    shape(part, f"{name}_coin_ink", ellipse(0, 0, R + ol, R + ol, 48), M["ink"], -0.02, outline=0)
    shape(part, f"{name}_coin_rim", ellipse(0, 0, R, R, 48), M["rim"], 0.0, outline=0)
    shape(part, f"{name}_coin_field", ellipse(0, 0, 0.82 * R, 0.82 * R, 48), M["field"], 0.02, outline=0)
    ring = ellipse(0, 0, 0.82 * R, 0.82 * R, 48)
    stroke(part, f"{name}_coin_ring", ring + [ring[0]], 0.012 * k, 0.025, m=M["dark"])

    face = empty(f"{name}_coin_face", part)
    if int(p["facing"]) < 0:
        face.scale = (-1.0, 1.0, 1.0)
    u = R * HS
    # ribbon ties behind the nape
    for i, pts in enumerate(([(-0.30, -0.06), (-0.39, -0.22), (-0.35, -0.34)],
                             [(-0.27, -0.09), (-0.29, -0.26), (-0.22, -0.38)])):
        stroke(face, f"{name}_coin_tie{i}", _sc(pts, u), 0.045 * u, 0.03, m=M["relief_dark"])
    shape(face, f"{name}_coin_head", _sc(HEAD, u), M["relief"], 0.04, outline=0.014 * k)
    # laurel wreath: leaves along an arc over the head, pointing back
    for i in range(6):
        a = math.radians(78 + 24 * i)
        cx, cy = -0.02 + 0.33 * math.cos(a), 0.04 + 0.34 * math.sin(a)
        shape(face, f"{name}_coin_leaf{i}", _sc(_leaf(cx, cy, a + math.pi / 2 + 0.35, 0.085, 0.04), u),
              M["relief_dark"], 0.06, outline=0)
    stroke(face, f"{name}_coin_ear", _sc(arc(-0.05, 0.0, 0.055, 0.075, 100, 290), u), 0.035 * u, 0.06,
           m=M["relief_dark"])
    disc(face, f"{name}_coin_eye", 0.17 * u, 0.12 * u, 0.035 * u, 0.06, M["dark"])
    stroke(face, f"{name}_coin_brow", _sc([(0.11, 0.18), (0.18, 0.185), (0.24, 0.16)], u), 0.03 * u, 0.06,
           m=M["relief_dark"])
    stroke(face, f"{name}_coin_mouth", _sc([(0.22, -0.11), (0.27, -0.11)], u), 0.025 * u, 0.06, m=M["relief_dark"])

    if p["legend"]:
        lg = empty(f"{name}_coin_legend", part)
        r1, r2 = 0.60 * R, 0.74 * R
        a0, a1, slots = 215.0, -35.0, 26
        pattern = []
        while len(pattern) < slots:
            pattern += ["L"] * rng.randint(3, 5) + [" "]
        for i, c in enumerate(pattern[:slots]):
            if c == " ":
                continue
            a = math.radians(a0 + (a1 - a0) * (i + 0.5) / slots)
            ca, sa = math.cos(a), math.sin(a)
            if rng.random() < 0.15:
                rm = (r1 + r2) / 2
                e = ellipse(ca * rm, sa * rm, 0.05 * R, 0.05 * R, 12)
                stroke(lg, f"{name}_coin_lo{i}", e + [e[0]], 0.010 * k, 0.04, m=M["dark"])
            else:
                rs = r1 + (r2 - r1) * (0.25 if rng.random() < 0.2 else 0.0)
                stroke(lg, f"{name}_coin_lb{i}", [(ca * rs, sa * rs), (ca * r2, sa * r2)], 0.012 * k, 0.04, m=M["dark"])
    if p["shine"]:
        stroke(part, f"{name}_coin_shine", arc(0, 0, 0.91 * R, 0.91 * R, 112, 160), 0.07 * R, 0.08, m=M["shine"])
        disc(part, f"{name}_coin_glint", 0.91 * R * math.cos(math.radians(100)), 0.91 * R * math.sin(math.radians(100)),
             0.04 * R, 0.08, M["shine"])


# ---------------------------------------------------------------- 2D purse
def _purse2d(part, name, M, p, R):
    # coin peeking out of the mouth (behind the ruffle)
    if p["peek"]:
        cg = empty(f"{name}_purse_coin", part, (0.035, 0.175, -0.04))
        cg.rotation_euler = (0.0, 0.0, -0.3)
        shape(cg, f"{name}_purse_coinink", ellipse(0, 0, 0.061, 0.061, 32), M["ink"], -0.02, outline=0)
        shape(cg, f"{name}_purse_coinrim", ellipse(0, 0, 0.05, 0.05, 32), M["rim"], 0.0, outline=0)
        shape(cg, f"{name}_purse_coinfield", ellipse(0, 0, 0.038, 0.038, 32), M["field"], 0.02, outline=0)
        stroke(cg, f"{name}_purse_coinshine", arc(0, 0, 0.044, 0.044, 110, 165), 0.008, 0.035, m=M["shine"])
    # ruffled mouth above the cinch
    ruffle = [(-0.055, 0.07), (-0.11, 0.145), (-0.085, 0.172), (-0.05, 0.148), (-0.02, 0.185), (0.015, 0.152),
              (0.05, 0.188), (0.08, 0.152), (0.115, 0.165), (0.06, 0.07)]
    shape(part, f"{name}_purse_ruffle", ruffle, M["leather_back"], 0.0)
    stroke(part, f"{name}_purse_rufflefold0", [(-0.04, 0.085), (-0.05, 0.14)], 0.008, 0.02, m=M["leather_dark"])
    stroke(part, f"{name}_purse_rufflefold1", [(0.035, 0.085), (0.048, 0.145)], 0.008, 0.02, m=M["leather_dark"])
    # body
    body = (_qbez((0.055, 0.07), (0.24, 0.03), (0.17, -0.15))
            + arc(0, -0.15, 0.17, 0.065, 0, -180, n=14)[1:]
            + _qbez((-0.17, -0.15), (-0.24, 0.03), (-0.055, 0.07))[1:-1])
    zb = 0.06
    shape(part, f"{name}_purse_body", body, M["leather"], zb)
    shade = (_qbez((0.07, 0.05), (0.205, 0.0), (0.15, -0.16)) + [(0.11, -0.19), (0.13, -0.12), (0.12, -0.02)])
    shape(part, f"{name}_purse_shade", shade, M["leather_dark"], zb + 0.02, outline=0)
    stroke(part, f"{name}_purse_hilite", _qbez((-0.12, 0.02), (-0.165, -0.05), (-0.13, -0.13)), 0.018, zb + 0.02,
           m=M["leather_lite"])
    for i, pts in enumerate(([(-0.03, 0.06), (-0.05, 0.0), (-0.06, -0.05)], [(0.03, 0.06), (0.045, 0.01)])):
        stroke(part, f"{name}_purse_fold{i}", pts, 0.01, zb + 0.02, m=M["leather_dark"])
    # cord: band round the neck, knot, two tails with end knots
    zc = zb + 0.04
    band = [(-0.075, 0.068), (-0.03, 0.06), (0.03, 0.06), (0.078, 0.068)]
    _ostroke(part, f"{name}_purse_cord", band, 0.024, zc, M["cord"])
    tails = ([(0.0, 0.058), (0.035, 0.0), (0.03, -0.055)], [(-0.006, 0.058), (-0.032, 0.005), (-0.05, -0.035)])
    for i, pts in enumerate(tails):
        _ostroke(part, f"{name}_purse_tail{i}", pts, 0.016, zc + 0.02, M["cord"], ol=0.02)
        shape(part, f"{name}_purse_tailknot{i}", ellipse(pts[-1][0], pts[-1][1], 0.016, 0.016, 14), M["cord"],
              zc + 0.06, outline=0.02)
    shape(part, f"{name}_purse_knot", ellipse(0.0, 0.064, 0.026, 0.022, 18), M["cord"], zc + 0.08, outline=0.025)


# ---------------------------------------------------------------- 3D
def _body3d(nm, loc, R, T, m, segments=48):
    h = T / 2
    f = h - 0.0025
    prof = [(0.0, -f), (0.80 * R, -f), (0.86 * R, -h), (R - 0.004, -h), (R, -h + 0.004),
            (R, h - 0.004), (R - 0.004, h), (0.86 * R, h), (0.80 * R, f), (0.0, f)]
    o = lathe(nm, loc, prof, m, segments=segments, smooth=False)
    for poly in o.data.polygons:                      # smooth only the milled edge; faces stay crisp
        poly.use_smooth = abs(poly.normal.z) < 0.3
    return o


def _coin3d(nm, loc, rot_z, R, T, M, relief):
    g = group3d(nm)
    body = _body3d(f"{nm}_body", (0, 0, 0), R, T, M["silver3d"])
    attach(g, body)
    if relief:
        h = T / 2
        pts = _sc(HEAD, R * HS)
        top = extrude(f"{nm}_head", (0, 0, h - 0.0015), pts, 0.003, M["relief3d"])
        bot = extrude(f"{nm}_headb", (0, 0, -(h - 0.0015)), pts, 0.003, M["relief3d"], rot=(math.pi, 0.0, 0.0))
        attach(g, top, bot)
    g.location = loc
    g.rotation_euler = (0.0, 0.0, rot_z)
    return g


# ---------------------------------------------------------------- build
def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    name = p["name"]
    item = str(p["item"]).lower()
    if item not in ("coin2d", "purse2d", "coin3d", "stack"):
        raise ValueError(f"coins: unknown item {item!r} (coin2d | purse2d | coin3d | stack)")
    rng = random.Random(int(p["seed"]))
    sil = p["silver_color"]

    if item in ("coin2d", "purse2d"):
        s = max(0.2, float(p["scale2d"]))
        M = dict(rim=_mat("rim", sil, 0.78), field=_mat("field", sil, 1.0), relief=_mat("relief", sil, 0.86),
                 relief_dark=_mat("reliefdark", sil, 0.55), dark=_mat("dark", sil, 0.38),
                 ink=flat("coins_ink", (0.03, 0.03, 0.035)),
                 shine=flat("coins_shine", (0.98, 0.97, 0.93)),
                 leather=_mat("leather", p["leather_color"]), leather_back=_mat("leather", p["leather_color"], 0.72),
                 leather_dark=_mat("leather", p["leather_color"], 0.55),
                 leather_lite=_mat("leather", p["leather_color"], 1.5), cord=_mat("cord", p["cord_color"]))
        parent = p.get("parent")
        g = empty(name, parent)
        if parent is not None:
            g.location = tuple(float(v) for v in p["at"])
        if item == "coin2d":
            part = empty(f"{name}_coin", g)
            part.scale = (s, s, s)
            _coin2d(part, name, max(0.03, float(p["r2d"])), M, p, rng)
        else:
            part = empty(f"{name}_purse", g)
            part.scale = (s, s, s)
            _purse2d(part, name, M, p, float(p["r2d"]))
        return g

    # 3D: ignore any parent (story places it)
    R = max(0.03, float(p["r3d"]))
    T = max(0.008, float(p["thickness"]))
    base = _clamp(sil, 0.92)
    M = dict(silver3d=warm_top(pbr(f"coins_silver3d_{_key(base)}", base, rough=0.38, metal=0.9)),
             relief3d=warm_top(pbr(f"coins_relief3d_{_key(base)}", _clamp(base, 0.78), rough=0.5, metal=0.85)))
    root = group3d(name)
    if item == "coin3d":
        c = _coin3d(f"{name}_coin", (0, 0, 0), 0.0, R, T, M, bool(p["relief"]))
        attach(root, c)
        return root

    n = max(1, min(40, int(p["n"])))
    st = group3d(f"{name}_stack")
    attach(root, st)
    j = 0.06 * R
    for i in range(n):
        z = T / 2 + i * T
        x, y = rng.uniform(-j, j), rng.uniform(-j, j)
        rz = rng.uniform(0, 2 * math.pi)
        if i == n - 1:
            c = _coin3d(f"{name}_coin", (x, y, z), rz, R, T, M, bool(p["relief"]))
        else:
            c = _body3d(f"{name}_coin{i}", (x, y, z), R, T, M["silver3d"], segments=40)
            c.rotation_euler = (0.0, 0.0, rz)
        attach(st, c)
    return root
