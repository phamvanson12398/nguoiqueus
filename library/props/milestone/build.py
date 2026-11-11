"""3D Roman milestone: slightly tapered stone column with a rounded worn top on a square plinth.
Inscription on the -Y face: dark letters bent around the column and following the worn surface,
sunk into the stone with only a hair standing proud, so they read as carved without a fragile boolean.
Origin = centre of the bottom (stands on the ground at z=0).  Parts: body (column), base (plinth),
text (group of inscription lines, can be hidden/revealed by a story).
Stone colour is warm on purpose: the blue sky gradient tints upward faces, neutral grey turns blue."""
import math
import random
from core.look import ramp_mat, pbr
from core.geo import group3d, attach, lathe, rbox, text3d

DEFAULTS = dict(text="VIA APPIA", subtext="MP XII", height=1.6, radius=0.3, base=True,
                text_size=0.15, text_z=1.12,
                stone_color=[0.62, 0.50, 0.34], base_color=[0.50, 0.40, 0.28],
                groove_color=[0.10, 0.07, 0.05], wear=0.012, seed=3)

SINK = 0.012     # letters reach this far inside the stone
PROUD = 0.003    # and stand this little above it (just enough to be visible)


def _clamp(c, k):
    return tuple(min(1.0, max(0.0, float(v) * k)) for v in c)


def _key(c):
    return "_".join(f"{float(v):.2f}" for v in c)


def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    name = p["name"]
    H = max(0.6, float(p["height"]))
    R = max(0.12, float(p["radius"]))
    k = H / 1.6
    has_base = bool(p["base"])
    wear = max(0.0, float(p["wear"]))
    rng = random.Random(int(p["seed"]))

    sc = p["stone_color"]; bc = p["base_color"]
    m_stone = ramp_mat(f"milestone_body_{_key(sc)}", [(0.3, _clamp(sc, 0.8)), (0.72, _clamp(sc, 1.12))],
                       scale=5.0, bump=0.2, rough=0.88)
    m_base = ramp_mat(f"milestone_base_{_key(bc)}", [(0.3, _clamp(bc, 0.78)), (0.72, _clamp(bc, 1.12))],
                      scale=6.0, bump=0.25, rough=0.9)
    m_groove = pbr(f"milestone_groove_{_key(p['groove_color'])}", tuple(float(v) for v in p["groove_color"]), rough=0.95)

    root = group3d(name)

    # ---- plinth ----
    z0 = 0.0
    if has_base:
        bh = 0.24 * k
        base = rbox(f"{name}_base", (0, 0, bh / 2), (R * 2.75, R * 2.75, bh), m_base, radius=0.045)
        attach(root, base)
        z0 = bh - 0.01

    # ---- column profile (r, z): flared foot, gentle taper, rounded worn dome ----
    top = H
    span = top - z0
    def zf(u): return z0 + span * u
    taper = 0.94
    prof = [(0.0, z0), (R * 1.10, z0), (R * 1.11, zf(0.025)), (R * 1.04, zf(0.05)), (R * 1.0, zf(0.08))]
    for i in range(1, 9):
        u = 0.08 + (0.86 - 0.08) * i / 8
        prof.append((R * (1.0 - (1.0 - taper) * (u - 0.08) / 0.78), zf(u)))
    rt = R * taper
    for a in (20, 40, 58, 72, 82, 90):
        t = math.radians(a)
        prof.append((rt * math.cos(t) * (1.0 if a < 90 else 0.0), zf(0.86) + span * 0.14 * math.sin(t)))
    prof[-1] = (0.0, top)

    def r_nom(z):
        for (ra, za), (rb, zb) in zip(prof, prof[1:]):
            if za <= z <= zb and zb > za:
                return ra + (rb - ra) * (z - za) / (zb - za)
        return R

    ph = [rng.uniform(0, 2 * math.pi) for _ in range(6)]

    def wear_off(th, z):
        """radial offset of the worn surface (same function for column and letters)"""
        if wear <= 0: return 0.0
        u = (z - z0) / span
        n = (0.55 * math.sin(3 * th + ph[0]) * math.sin(6.0 * z + ph[1])
             + 0.30 * math.sin(7 * th + ph[2] + 3.0 * z)
             + 0.15 * math.sin(13 * th + ph[3]))
        amp = wear * (1.0 + 1.5 * max(0.0, u - 0.8) / 0.2)
        if u < 0.06: amp *= 0.4
        return amp * n - amp * 0.5

    body = lathe(f"{name}_body", (0, 0, 0), prof, m_stone, segments=56)
    if wear > 0:
        for v in body.data.vertices:
            x, y, z = v.co
            r = math.hypot(x, y)
            if r < 1e-4: continue
            s = (r + wear_off(math.atan2(y, x), z)) / r
            v.co.x = x * s; v.co.y = y * s
    attach(root, body)

    # ---- inscription lines ----
    ts = max(0.04, float(p["text_size"])) * min(1.0, R / 0.3) ** 0.5
    text = str(p["text"] or "").strip()
    max_arc = R * 1.5                              # about 86 degrees of the front
    if "|" in text:
        lines = [s.strip() for s in text.split("|") if s.strip()]
    elif " " in text and len(text) * 0.62 * ts > max_arc:
        lines = text.split()
    else:
        lines = [text] if text else []
    rows = [(s, ts) for s in lines]
    sub = str(p["subtext"] or "").strip()
    if sub:
        rows.append((sub, ts * 0.72))

    if rows:
        g_text = group3d(f"{name}_text")
        attach(root, g_text)
        gaps = [s * 1.28 for _, s in rows]
        zc = float(p["text_z"]) * k + sum(gaps) / 2
        for i, (s, size) in enumerate(rows):
            zl = zc - gaps[i] / 2 - (0.12 * size if i == len(rows) - 1 and sub else 0.0)
            zc -= gaps[i]
            c = text3d(f"{name}_text{i}", (0, 0, 0), s, size, m_groove, depth=0.02)
            me = c.data
            if not len(me.vertices):
                continue
            for poly in me.polygons: poly.use_smooth = False
            xs = [v.co.x for v in me.vertices]; zs = [v.co.z for v in me.vertices]
            xmid = (min(xs) + max(xs)) / 2; w = max(xs) - min(xs)
            fx = min(1.0, max_arc / w) if w > 1e-6 else 1.0
            zmin, zmax = min(zs), max(zs); dz = (zmax - zmin) or 1.0
            for v in me.vertices:
                x, y, z = v.co
                th = (x - xmid) * fx / R             # angle away from -Y
                zw = zl + y
                ang = -math.pi / 2 + th              # world polar angle (−Y = −90°)
                rs = r_nom(zw) + wear_off(ang, zw)
                r = rs - SINK + (z - zmin) / dz * (SINK + PROUD)
                v.co = (r * math.sin(th), -r * math.cos(th), zw)
            me.update()
            c.location = (0, 0, 0); c.rotation_euler = (0, 0, 0)
            attach(g_text, c)

    return root
