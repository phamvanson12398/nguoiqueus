"""Vindolanda-style wooden leaf tablet: thin pale wood leaf (enlarged to 0.6 x 0.25), black ink cursive in two columns
(one per half), a vertical fold crease in the middle, chipped edges.

dim '2d': flat drawing in the character plane with ink outline, held in both hands at the chest; with a parent it
          sits at `at` = [0, 0.6, 0.42] in torso space.  Origin at the centre of the (visible) leaf.
          Parts: {name}_leaf, {name}_fold, {name}_text (empty holding all ink strokes), {name}_grain<i>;
          folded: half leaf + {name}_back (second leaf peeking out behind) and the address in {name}_text.
dim '3d': lying on a table, origin at the bottom centre of the open leaf (z = 0 rests on the surface).
          Parts: {name}_leaf (left half), {name}_flap (hinge empty at the fold, x = 0, top surface) holding
          {name}_leaf2 (right half) + {name}_text2 + {name}_address (outside face, mirrored so it reads once folded),
          {name}_text (left column), {name}_fold (crease groove).
          Fold animation: rotate {name}_flap rotation_euler.y from 0 to -pi (lifts up and over onto the left half).
folded=True builds it already folded (2d: half leaf; 3d: flap at -pi).
3d wood is warmer/deeper than the 2d colour + warm_top so the blue sky does not turn the pale top grey-green."""
import math
import random
from core.look import flat, ramp_mat, warm_top
from core.geo import empty, shape, stroke, group3d, attach, extrude, keep_hidden

DEFAULTS = dict(dim="2d", folded=False, text_lines=4, size=[0.6, 0.25], thickness=0.02, chip=1.0,
                wood_color=[0.93, 0.70, 0.40], ink_color=[0.03, 0.025, 0.02], address=True, seed=11,
                at=[0, 0.6, 0.42], scale2d=1.0)


def _clamp(c, k):
    return tuple(min(1.0, max(0.0, float(v) * k)) for v in c)


def _key(c):
    return "_".join(f"{float(v):.2f}" for v in c)


def _toward(a, b, d):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy) or 1.0
    return (a[0] + dx / L * d, a[1] + dy / L * d)


def _chipped(x0, y0, x1, y1, rng, chip, straight=(False, False, False, False), u=1.0):
    """rectangle outline (CCW) with chipped corners and small V bites; straight[i] keeps edge i clean
    (edges: 0 bottom, 1 right, 2 top, 3 left) - used for the fold edge"""
    cs = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    step = 0.045 * u
    pts = []
    for i in range(4):
        a, b, prev = cs[i], cs[(i + 1) % 4], cs[i - 1]
        if not straight[(i - 1) % 4] and not straight[i] and rng.random() < 0.55 * chip:
            pts.append(_toward(a, prev, rng.uniform(0.012, 0.028) * u))
            pts.append(_toward(a, b, rng.uniform(0.012, 0.028) * u))
        else:
            pts.append(a)
        if straight[i]:
            continue
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        ux, uy = dx / L, dy / L
        nx, ny = -uy, ux                                  # inward normal for a CCW outline
        n = max(2, int(round(L / step)))
        for k in range(1, n):
            t = (k + rng.uniform(-0.25, 0.25)) / n
            d = rng.uniform(0.008, 0.022) * u if rng.random() < 0.3 * chip else rng.uniform(0.0, 0.003) * u
            pts.append((a[0] + ux * L * t + nx * d, a[1] + uy * L * t + ny * d))
    return pts


def _word(rng, x, y, nlet, lw, h, slant):
    """one cursive 'word': slanted zigzag of up/down strokes with the odd ascender/descender"""
    y += rng.uniform(-0.12, 0.12) * h
    pts = [(x, y + h * 0.2)]
    for _ in range(nlet):
        r = rng.random()
        ht = h * 1.9 if r < 0.2 else h * rng.uniform(0.85, 1.1)
        bot = y - h * 0.8 if 0.2 <= r < 0.3 else y
        pts.append((x + lw * 0.45 + slant * ht, y + ht))
        pts.append((x + lw, bot))
        x += lw
    return pts


def _lines(rng, x0, x1, ys, h, last_short=True):
    """list of word polylines filling the column [x0, x1] on the baselines ys"""
    words = []
    for li, y in enumerate(ys):
        end = x1 if (li < len(ys) - 1 or not last_short) else x0 + (x1 - x0) * rng.uniform(0.4, 0.7)
        x = x0 + rng.uniform(0.0, 0.25) * h + (0.9 * h if li == 0 else 0.0)
        placed = 0
        while True:
            nlet = rng.randint(2, 5); lw = h * rng.uniform(0.7, 0.9)
            if x + nlet * lw > end:
                if placed == 0 and end - x > 1.5 * lw:
                    nlet = max(1, int((end - x) / lw))
                else:
                    break
            words.append(_word(rng, x, y, nlet, lw, h, 0.35))
            placed += 1
            x += nlet * lw + h * rng.uniform(0.9, 1.4)
    return words


def _baselines(n, H, m, h):
    top = H / 2 - m - 1.9 * h
    bot = -H / 2 + m + 0.8 * h
    if n == 1:
        return [(top + bot) / 2]
    return [top - (top - bot) * i / (n - 1) for i in range(n)]


def _letter_h(n, H, m):
    return min(0.022, (H - 2 * m) / max(n, 1) * 0.4)


# ---------------------------------------------------------------- 2D
def _build_2d(p, name, rng):
    s = max(0.2, float(p["scale2d"]))
    W, H = float(p["size"][0]) * s, float(p["size"][1]) * s
    chip = max(0.0, float(p["chip"]))
    n = max(1, min(12, int(p["text_lines"])))
    wc = p["wood_color"]
    m_wood = flat(f"writing_tablet_wood2d_{_key(wc)}", _clamp(wc, 1.0))
    m_back = flat(f"writing_tablet_back2d_{_key(wc)}", _clamp(wc, 0.72))
    m_grain = flat(f"writing_tablet_grain2d_{_key(wc)}", _clamp(wc, 0.84))
    m_fold = flat(f"writing_tablet_fold2d_{_key(wc)}", _clamp(wc, 0.45))
    m_shade = flat(f"writing_tablet_shade2d_{_key(wc)}", _clamp(wc, 0.88))
    m_ink = flat(f"writing_tablet_ink_{_key(p['ink_color'])}", _clamp(p["ink_color"], 1.0))

    parent = p.get("parent")
    g = empty(name, parent)
    if parent is not None:
        g.location = tuple(float(v) for v in p["at"])
    tg = empty(f"{name}_text", g)
    m = 0.04 * s
    wink = 0.009 * s

    def grain(x0, x1):
        for i in range(3):
            y = H * (-0.3 + 0.3 * i) + rng.uniform(-0.02, 0.02) * s
            a = x0 + rng.uniform(0.0, 0.3) * (x1 - x0)
            b = a + rng.uniform(0.3, 0.55) * (x1 - x0)
            pts = [(a + (b - a) * t / 4, y + math.sin(t * 1.7 + i) * 0.004 * s) for t in range(5)]
            stroke(g, f"{name}_grain{i}", pts, 0.006 * s, 0.01, m=m_grain)

    if not p["folded"]:
        shape(g, f"{name}_leaf", _chipped(-W / 2, -H / 2, W / 2, H / 2, rng, chip, u=s), m_wood, 0, outline=0.035)
        grain(-W / 2 + 0.03 * s, W / 2 - 0.03 * s)
        shade = [(-0.016 * s, -H / 2 + 0.006 * s), (0, -H / 2 + 0.006 * s), (0, H / 2 - 0.006 * s), (-0.016 * s, H / 2 - 0.006 * s)]
        shape(g, f"{name}_foldshade", shade, m_shade, 0.012, outline=0)
        stroke(g, f"{name}_fold", [(0, -H / 2 + 0.005 * s), (0, H / 2 - 0.005 * s)], 0.012 * s, 0.02, m=m_fold)
        h = _letter_h(n, H, m)
        ys = _baselines(n, H, m, h)
        words = _lines(rng, -W / 2 + m, -0.035 * s, ys, h) + _lines(rng, 0.035 * s, W / 2 - m, ys, h)
    else:
        hw = W / 2
        dx, dy = 0.016 * s, -0.012 * s
        shape(g, f"{name}_back", _chipped(-hw / 2 + dx, -H / 2 + dy, hw / 2 + dx, H / 2 + dy, rng, chip,
                                          straight=(False, True, False, False), u=s), m_back, -0.02, outline=0.035)
        shape(g, f"{name}_leaf", _chipped(-hw / 2, -H / 2, hw / 2, H / 2, rng, chip,
                                          straight=(False, True, False, False), u=s), m_wood, 0, outline=0.035)
        grain(-hw / 2 + 0.03 * s, hw / 2 - 0.03 * s)
        stroke(g, f"{name}_fold", [(hw / 2 - 0.012 * s, -H / 2 + 0.006 * s), (hw / 2 - 0.012 * s, H / 2 - 0.006 * s)],
               0.01 * s, 0.02, m=m_fold)
        words = []
        if p["address"]:
            h = 0.02 * s
            words = _lines(rng, -hw * 0.32, hw * 0.3, [0.035 * s, -0.035 * s], h, last_short=False)
    for i, pts in enumerate(words):
        stroke(tg, f"{name}_w{i}", pts, wink, 0.03, m=m_ink)
    return g


# ---------------------------------------------------------------- 3D
def _build_3d(p, name, rng):
    W, H = float(p["size"][0]), float(p["size"][1])
    T = max(0.006, float(p["thickness"]))
    chip = max(0.0, float(p["chip"]))
    n = max(1, min(12, int(p["text_lines"])))
    wc = p["wood_color"]
    base = (wc[0] * 0.86, wc[1] * 0.74, wc[2] * 0.58)          # warmer + deeper against the blue sky tint
    wood = warm_top(ramp_mat(f"writing_tablet_wood_{_key(wc)}", [(0.3, _clamp(base, 0.85)), (0.7, _clamp(base, 1.08))],
                             scale=6.0, bump=0.2, rough=0.75, mapping_scale=(1, 8, 1)))
    m_fold = flat(f"writing_tablet_fold_{_key(wc)}", _clamp(wc, 0.4))
    m_ink = flat(f"writing_tablet_ink_{_key(p['ink_color'])}", _clamp(p["ink_color"], 1.0))
    wink = 0.01
    m = 0.04

    root = group3d(name)
    left = extrude(f"{name}_leaf", (0, 0, T / 2),
                   _chipped(-W / 2, -H / 2, 0, H / 2, rng, chip, straight=(False, True, False, False)), T, wood)
    attach(root, left)
    flap = group3d(f"{name}_flap", (0, 0, T))
    attach(root, flap)
    right = extrude(f"{name}_leaf2", (0, 0, -T / 2),
                    _chipped(0, -H / 2, W / 2, H / 2, rng, chip, straight=(False, False, False, True)), T, wood)
    attach(flap, right)

    crease = stroke(root, f"{name}_fold", [(0, -H / 2 + 0.01), (0, H / 2 - 0.01)], 0.006, T + 0.001, m=m_fold)

    h = _letter_h(n, H, m)
    ys = _baselines(n, H, m, h)
    tl = empty(f"{name}_text", root, (0, 0, T))
    for i, pts in enumerate(_lines(rng, -W / 2 + m, -0.035, ys, h)):
        stroke(tl, f"{name}_wa{i}", pts, wink, 0.003, m=m_ink)
    tr = empty(f"{name}_text2", flap, (0, 0, 0))
    for i, pts in enumerate(_lines(rng, 0.035, W / 2 - m, ys, h)):
        stroke(tr, f"{name}_wb{i}", pts, wink, 0.003, m=m_ink)
    if p["address"]:
        ta = empty(f"{name}_address", flap, (0, 0, -T))
        hw = W / 2
        for i, pts in enumerate(_lines(rng, -hw * 0.32, hw * 0.3, [0.035, -0.035], 0.02, last_short=False)):
            # centred on the right half and mirrored in x so it reads correctly after the flap turns over
            stroke(ta, f"{name}_wc{i}", [(hw / 2 - x, y) for x, y in pts], wink, -0.003, m=m_ink)

    if p["folded"]:
        flap.rotation_euler = (0.0, -math.pi, 0.0)
        for o in crease:
            keep_hidden(o, True)
    return root


def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    name = p["name"]
    rng = random.Random(int(p["seed"]))
    if str(p["dim"]).lower() == "3d":
        return _build_3d(p, name, rng)
    return _build_2d(p, name, rng)
