"""3D signal beacon on a hilltop: teepee of logs on a stone ring, cartoon emission flames,
tall slender grey smoke column.  Origin at the bottom centre.
Parts: <name>_wood, <name>_fire, <name>_smoke.  <name>_smoke is an empty whose origin is the
BOTTOM of the smoke column, so a story can scale its Z from 0.05 to 1 to make the smoke rise.
Meant to be seen far away (scale ~3): big, readable shapes."""
import math
import random
from mathutils import Vector
from core.look import pbr, flat
from core.geo import cyl, sphere, lathe, group3d, attach, empty, keep_hidden

DEFAULTS = dict(lit=True, smoke_height=5.0, smoke_drift=0.6, smoke_color=[0.24, 0.24, 0.26],
                flame_color=[0.98, 0.30, 0.02], wood_color=[0.32, 0.15, 0.05], stones=True)

LOGS = 9          # logs in the teepee
BASE_R = 0.82     # teepee footprint radius
APEX_Z = 1.35     # where the logs cross
FLAME_TOP = 2.2   # tip of the main flame; smoke starts just below


def _log(name, a, b, r, m):
    """cylinder from point a to point b"""
    a, b = Vector(a), Vector(b)
    d = b - a
    o = cyl(name, tuple((a + b) * 0.5), r, d.length, m, verts=10)
    o.rotation_euler = Vector((0, 0, 1)).rotation_difference(d.normalized()).to_euler()
    return o


def _tongue(name, loc, w, h, m, lean=0.0, ang=0.0):
    """cartoon flame tongue (teardrop with a pointed tip), leaning outward toward angle `ang`"""
    prof = [(0.0, 0.0), (w * 0.85, 0.12 * h), (w, 0.32 * h), (w * 0.72, 0.58 * h), (w * 0.36, 0.82 * h), (0.0, h)]
    o = lathe(name, loc, prof, m, segments=20)
    o.rotation_euler = (-lean * math.sin(ang), lean * math.cos(ang), 0)
    return o


def _hide_all(o):
    keep_hidden(o, True)
    for c in o.children_recursive:
        keep_hidden(c, True)


def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    name = p["name"]
    rng = random.Random(7)
    root = group3d(name)

    # ---------------- wood: teepee of logs + stone ring ----------------
    wc = p["wood_color"]
    wood_a = pbr("beacon_fire_wood", tuple(wc), rough=0.9)
    wood_b = pbr("beacon_fire_wood_dark", (wc[0] * 0.6, wc[1] * 0.55, wc[2] * 0.55), rough=0.9)
    wood = empty(f"{name}_wood", root)
    for i in range(LOGS):
        ang = 2 * math.pi * i / LOGS + rng.uniform(-0.12, 0.12)
        bot = Vector((BASE_R * math.cos(ang), BASE_R * math.sin(ang), 0.07))
        top = Vector((0.08 * math.cos(ang + math.pi), 0.08 * math.sin(ang + math.pi), APEX_Z))
        top = bot + (top - bot) * 1.22          # logs poke past the crossing point
        o = _log(f"{name}_log{i}", bot, top, 0.10, wood_a if i % 2 == 0 else wood_b)
        o.parent = wood
    for k, ang in enumerate((0.4, 0.4 + math.pi / 2)):
        dx, dy = math.cos(ang) * 0.85, math.sin(ang) * 0.85
        o = _log(f"{name}_base{k}", (-dx, -dy, 0.11 + k * 0.16), (dx, dy, 0.11 + k * 0.16), 0.11, wood_b)
        o.parent = wood
    if p["stones"]:
        stone = pbr("beacon_fire_stone", (0.30, 0.28, 0.26), rough=0.95)
        n = 10
        for i in range(n):
            ang = 2 * math.pi * i / n
            r = 0.18 + rng.uniform(-0.03, 0.03)
            o = sphere(f"{name}_stone{i}", (1.05 * math.cos(ang), 1.05 * math.sin(ang), r * 0.55), r, stone,
                       scale=(1.25, 1.0, 0.75))
            o.rotation_euler = (0, 0, ang)
            o.parent = wood

    # ---------------- fire: cluster of cartoon tongues (emission) ----------------
    fc = p["flame_color"]
    m_out = flat("beacon_fire_flame", tuple(fc))
    m_mid = flat("beacon_fire_flame_mid", (1.0, 0.58, 0.03))
    m_core = flat("beacon_fire_flame_core", (1.0, 0.88, 0.25))
    fire = empty(f"{name}_fire", root)
    # main orange tongue, slimmer than the teepee so the logs show below it
    _tongue(f"{name}_flame_out", (0, 0, 0.25), 0.40, FLAME_TOP - 0.25, m_out).parent = fire
    # yellow-orange tongues poking out of the main one on three sides
    for i, ang in enumerate((0.5, 2.6, 4.6)):
        _tongue(f"{name}_flame_mid{i}", (0.24 * math.cos(ang), 0.24 * math.sin(ang), 0.35), 0.25, 1.45 - 0.12 * i,
                m_mid, lean=0.22, ang=ang).parent = fire
    # small pale-yellow tongues low between them
    for i, ang in enumerate((1.6, 3.6, 5.6)):
        _tongue(f"{name}_flame_core{i}", (0.32 * math.cos(ang), 0.32 * math.sin(ang), 0.35), 0.15, 0.8,
                m_core, lean=0.3, ang=ang).parent = fire
    # short orange side tongues leaning outward for a jagged silhouette
    for i, ang in enumerate((0.0, 1.1, 2.1, 3.2, 4.2, 5.3)):
        _tongue(f"{name}_tongue{i}", (0.38 * math.cos(ang), 0.38 * math.sin(ang), 0.3), 0.17, 0.95 + 0.2 * (i % 2),
                m_out, lean=0.45, ang=ang).parent = fire

    # ---------------- smoke: empty at the column base, puffs above it ----------------
    smoke_base = FLAME_TOP - 0.3
    smoke = empty(f"{name}_smoke", root, (0, 0, smoke_base))
    m_smoke = pbr("beacon_fire_smoke", tuple(p["smoke_color"]), rough=1.0)
    H = max(0.5, float(p["smoke_height"]))
    drift = float(p["smoke_drift"])
    n = max(3, int(round(H / 0.42)))
    for i in range(n):
        t = i / (n - 1)
        z = 0.3 + t * (H - 0.3)
        r = 0.36 + 0.30 * t
        x = drift * t * t + 0.10 * math.sin(i * 1.7)
        y = 0.08 * math.cos(i * 2.3)
        o = sphere(f"{name}_puff{i}", (x, y, z), r, m_smoke,
                   scale=(1.0 + rng.uniform(-0.08, 0.12), 1.0, 0.9 + rng.uniform(-0.05, 0.1)))
        o.parent = smoke
        if i % 2 == 1:
            side = 1 if (i // 2) % 2 == 0 else -1
            o2 = sphere(f"{name}_puffs{i}", (x + side * r * 0.75, y, z - 0.1), r * 0.62, m_smoke)
            o2.parent = smoke

    attach(root, wood, fire, smoke)
    if not p["lit"]:
        _hide_all(fire)
        _hide_all(smoke)
    return root
