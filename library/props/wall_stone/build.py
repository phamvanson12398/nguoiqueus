"""Roman rough-hewn wall stone (ashlar facing block) or turf block.

dim '3d': chamfered block with slightly skewed (hand-dressed) corners, warm sandstone ramp material.
          Single block: root empty at the CENTRE of the block (origin='center', for tumbling/flipping tracks)
          or at the bottom centre (origin='bottom').  Parts: {name}_body (+ {name}_top, {name}_tuftN for turf).
          pile N > 1: a messy pile of N blocks, root at the bottom centre of the pile; each block is a group
          {name}_s<i> (children {name}_s<i>_body / _top).  N >= 6 puts one block fallen on its side beside the pile.
dim '2d': flat drawing in the character plane (front face 0.45 x 0.28) with ink outline, to be hugged at the
          chest; with a parent it sits at `at` = [0, 0.66, 0.42] in torso space (story loc overrides).
          Parts: {name}_face, {name}_inner (stone) / {name}_grass (turf).
kind 'stone' | 'turf' (brown soil block with a thick green grass top).
Colours are warm and deep on purpose: the blue sky gradient tints upward faces, pale sand turns grey-blue."""
import math
import random
from core.look import ramp_mat, flat, warm_top
from core.geo import group3d, attach, rbox, cone, empty, shape, stroke

DEFAULTS = dict(dim="3d", kind="stone", pile=1, size=[0.45, 0.32, 0.28], chamfer=0.035, rough=0.02,
                seed=7, origin="center",
                stone_color=[0.70, 0.46, 0.22], soil_color=[0.30, 0.17, 0.08], grass_color=[0.16, 0.40, 0.05],
                tufts=True, at=[0, 0.66, 0.42], scale2d=1.0, marks=True)

GRASS_T = 0.08    # thickness of the turf grass layer


def _clamp(c, k):
    return tuple(min(1.0, max(0.0, float(v) * k)) for v in c)


def _key(c):
    return "_".join(f"{float(v):.2f}" for v in c)


def _mats(p):
    sc, so, gr = p["stone_color"], p["soil_color"], p["grass_color"]
    return dict(
        stone=warm_top(ramp_mat(f"wall_stone_body_{_key(sc)}", [(0.28, _clamp(sc, 0.72)), (0.72, _clamp(sc, 1.12))],
                       scale=7.0, bump=0.35, rough=0.9)),
        soil=ramp_mat(f"wall_stone_soil_{_key(so)}", [(0.3, _clamp(so, 0.75)), (0.7, _clamp(so, 1.2))],
                      scale=9.0, bump=0.35, rough=0.95),
        grass=ramp_mat(f"wall_stone_grass_{_key(gr)}", [(0.35, _clamp(gr, 0.8)), (0.7, _clamp(gr, 1.15))],
                       scale=14.0, bump=0.25, rough=0.85),
    )


def _rough_box(nm, loc, size, m, chamfer, rough, rng):
    """chamfered box whose corners are nudged a little (hand-dressed, not machine-square)"""
    o = rbox(nm, loc, size, m, radius=chamfer, segments=1)
    if rough > 0:
        for v in o.data.vertices:
            v.co.x += rng.uniform(-rough, rough)
            v.co.y += rng.uniform(-rough, rough)
            v.co.z += rng.uniform(-rough, rough) * 0.6
            if v.co.z > 0:                       # top slightly narrower: reads as a dressed block
                v.co.x *= 0.975; v.co.y *= 0.975
        o.data.update()
    return o


def _unit(pre, p, mats, rng, z0, tufts):
    """one block built around (0, 0, z0) as a group named `pre`; returns the group"""
    L, D, H = (float(v) for v in p["size"])
    ch = max(0.0, float(p["chamfer"])); r = max(0.0, float(p["rough"]))
    g = group3d(pre)
    if p["kind"] == "turf":
        gt = min(GRASS_T, H * 0.4)
        body = _rough_box(f"{pre}_body", (0, 0, z0 - gt / 2), (L, D, H - gt), mats["soil"], ch, r, rng)
        top = _rough_box(f"{pre}_top", (0, 0, z0 + H / 2 - gt / 2), (L + 0.025, D + 0.025, gt),
                         mats["grass"], min(ch, gt * 0.4), r * 0.5, rng)
        attach(g, body, top)
        if tufts:
            for i in range(5):
                x = rng.uniform(-L * 0.38, L * 0.38); y = rng.uniform(-D * 0.35, D * 0.35)
                hgt = rng.uniform(0.07, 0.11)
                t = cone(f"{pre}_tuft{i}", (x, y, z0 + H / 2 + hgt / 2 - 0.01), 0.035, 0.0, hgt, mats["grass"], verts=6)
                t.rotation_euler = (rng.uniform(-0.25, 0.25), rng.uniform(-0.25, 0.25), 0)
                attach(g, t)
    else:
        body = _rough_box(f"{pre}_body", (0, 0, z0), (L, D, H), mats["stone"], ch, r, rng)
        attach(g, body)
    return g


def _build_2d(p, name):
    L, _, H = (float(v) for v in p["size"])
    s = max(0.2, float(p["scale2d"]))
    w, h = L * s, H * s
    rng = random.Random(int(p["seed"]))
    parent = p.get("parent")
    g = empty(name, parent)
    if parent is not None:
        g.location = tuple(float(v) for v in p["at"])

    def j(v):
        return v + rng.uniform(-0.007, 0.007) * s

    if p["kind"] == "turf":
        so, gr = p["soil_color"], p["grass_color"]
        m_soil = flat(f"wall_stone_2d_soil_{_key(so)}", _clamp(so, 1.1))
        m_grass = flat(f"wall_stone_2d_grass_{_key(gr)}", _clamp(gr, 1.15))
        m_dark = flat(f"wall_stone_2d_soildark_{_key(so)}", _clamp(so, 0.6))
        c = 0.03 * s
        body = [(-w / 2 + c, -h / 2), (w / 2 - c, -h / 2), (w / 2, -h / 2 + c), (w / 2, h / 2 - c),
                (w / 2 - c, h / 2), (-w / 2 + c, h / 2), (-w / 2, h / 2 - c), (-w / 2, -h / 2 + c)]
        shape(g, f"{name}_face", [(j(x), j(y)) for x, y in body], m_soil, 0, outline=0.035)
        # grass band with a zigzag lower edge (blades hanging over the soil)
        top = h / 2 + 0.01 * s; bot = h / 2 - 0.30 * h
        n = 7
        pts = [(-w / 2 - 0.01 * s, top), (w / 2 + 0.01 * s, top), (w / 2 + 0.01 * s, bot)]
        for i in range(1, n * 2):
            x = w / 2 - w * i / (n * 2)
            y = bot - (0.035 * s if i % 2 else 0.0)
            pts.append((x, y))
        pts.append((-w / 2 - 0.01 * s, bot))
        shape(g, f"{name}_grass", pts, m_grass, 0.02, outline=0.025)
        for i in range(3):                     # a few dark soil streaks
            x = -w * 0.3 + i * w * 0.3 + rng.uniform(-0.03, 0.03) * s
            y = -h * 0.15 + rng.uniform(-0.04, 0.02) * s
            stroke(g, f"{name}_mark{i}", [(x - 0.035 * s, y), (x + 0.035 * s, y + 0.01 * s)], 0.016 * s, 0.04, m=m_dark)
        return g

    sc = p["stone_color"]
    m_edge = flat(f"wall_stone_2d_edge_{_key(sc)}", _clamp(sc, 0.72))
    m_face = flat(f"wall_stone_2d_face_{_key(sc)}", _clamp(sc, 1.05))
    m_mark = flat(f"wall_stone_2d_mark_{_key(sc)}", _clamp(sc, 0.42))
    c = max(0.02, float(p["chamfer"]) * 1.3) * s
    outer = [(-w / 2 + c, -h / 2), (w / 2 - c, -h / 2), (w / 2, -h / 2 + c), (w / 2, h / 2 - c),
             (w / 2 - c, h / 2), (-w / 2 + c, h / 2), (-w / 2, h / 2 - c), (-w / 2, -h / 2 + c)]
    shape(g, f"{name}_face", [(j(x), j(y)) for x, y in outer], m_edge, 0, outline=0.035)
    inset = 0.045 * s
    inner = [(-w / 2 + inset, -h / 2 + inset), (w / 2 - inset, -h / 2 + inset),
             (w / 2 - inset, h / 2 - inset), (-w / 2 + inset, h / 2 - inset)]
    shape(g, f"{name}_inner", [(j(x), j(y)) for x, y in inner], m_face, 0.02, outline=0)
    if p["marks"]:
        for i, (fx, fy) in enumerate(((-0.22, 0.12), (0.05, -0.15), (0.24, 0.10))):
            x, y = fx * w, fy * h
            stroke(g, f"{name}_mark{i}", [(x - 0.03 * s, y - 0.012 * s), (x + 0.03 * s, y + 0.012 * s)],
                   0.014 * s, 0.04, m=m_mark)
    return g


def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    name = p["name"]
    if str(p["dim"]).lower() == "2d":
        return _build_2d(p, name)

    mats = _mats(p)
    rng = random.Random(int(p["seed"]))
    L, D, H = (float(v) for v in p["size"])
    N = max(1, int(p["pile"]))

    if N == 1:
        z0 = H / 2 if p["origin"] == "bottom" else 0.0
        return _unit(name, p, mats, rng, z0, bool(p["tufts"]))

    # ---- messy pile, root at the bottom centre ----
    root = group3d(name)
    spare = 1 if N >= 6 else 0
    M = N - spare
    ny = 1 if M <= 4 else 2

    def cap(nx):
        return sum((nx - k) * ny for k in range(nx))

    nx = 1
    while cap(nx) < M:
        nx += 1
    gap = 0.015
    slots = []                               # (layer, x, y)
    left = M
    for k in range(nx):
        row = nx - k
        layer = [((i - (row - 1) / 2) * (L + gap), (jj - (ny - 1) / 2) * (D + gap))
                 for i in range(row) for jj in range(ny)]
        if left < len(layer):
            layer = sorted(rng.sample(layer, left))
        slots += [(k, x, y) for x, y in layer]
        left -= len(layer)
        if left <= 0:
            break

    i = 0
    for k, x, y in slots:
        u = _unit(f"{name}_s{i}", p, mats, rng, 0.0, False)
        tilt = math.radians(4.0) if k > 0 else math.radians(1.5)
        rx = rng.uniform(-tilt, tilt); ry = rng.uniform(-tilt, tilt)
        u.location = (x + rng.uniform(-0.03, 0.03), y + rng.uniform(-0.03, 0.03),
                      H / 2 + k * (H - 0.004) + abs(ry) * L / 2 + abs(rx) * D / 2)
        u.rotation_euler = (rx, ry, rng.uniform(-math.radians(10), math.radians(10)))
        attach(root, u)
        i += 1
    if spare:                                # one block tumbled off, lying on its side
        u = _unit(f"{name}_s{i}", p, mats, rng, 0.0, False)
        side = 1 if rng.random() < 0.5 else -1
        u.location = (side * ((nx / 2) * (L + gap) + L * 0.55), rng.uniform(-0.12, 0.12) + D * 0.3, D / 2)
        u.rotation_euler = (math.radians(90), 0, math.radians(rng.uniform(20, 40)) * side)
        attach(root, u)
    return root
