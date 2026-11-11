"""Open field for armies and crowds: a wide gently rolling meadow (or dry plain / snow), rows of distant hills,
scattered trees and rocks, a dirt road.  Big enough for formations of 100+ people (default 160 x 120)."""
import math, random
from core import geo
from core.look import pbr, ramp_mat

DEFAULTS = dict(origin=[0.0, 0.0, 0.0], size=[160.0, 120.0], ground="meadow", hills=True, trees=18, rocks=10, road=None, seed=5)
GROUND = {"meadow": [(0.2, (0.22, 0.42, 0.10)), (0.6, (0.30, 0.50, 0.14)), (0.9, (0.36, 0.55, 0.18))],
          "dry": [(0.2, (0.55, 0.45, 0.22)), (0.6, (0.62, 0.52, 0.28)), (0.9, (0.70, 0.60, 0.34))],
          "snow": [(0.2, (0.80, 0.84, 0.88)), (0.6, (0.88, 0.90, 0.93)), (0.9, (0.95, 0.96, 0.98))]}


def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    rnd = random.Random(p["seed"])
    ox, oy, oz = (list(p["origin"]) + [0.0])[:3]; W, D = p["size"]
    g = ramp_mat(f"field_{p['ground']}", GROUND.get(p["ground"], GROUND["meadow"]), scale=0.08, bump=0.1)
    geo.cube("field_ground", (ox, oy + D / 2 - 20, oz - 0.05), (W, D, 0.1), g)
    hill = pbr(f"field_hill_{p['ground']}", GROUND.get(p["ground"], GROUND["meadow"])[1][1], rough=0.95)
    far = pbr(f"field_far_{p['ground']}", tuple(c * 0.8 + 0.12 for c in GROUND.get(p["ground"], GROUND["meadow"])[0][1]), rough=1.0)
    if p["hills"]:
        for i in range(9):
            x = ox + (i - 4) * W / 8 + rnd.uniform(-6, 6); r = rnd.uniform(14, 26)
            geo.sphere(f"field_hill{i}", (x, oy + D - 25 + rnd.uniform(-6, 6), oz - r * 0.55), r, far if i % 2 else hill, scale=(1.6, 1.0, 0.6))
    leaf = pbr("field_leaf", (0.10, 0.32, 0.08), rough=0.9); trunk = pbr("field_trunk", (0.30, 0.18, 0.08))
    for i in range(int(p["trees"])):
        x = ox + rnd.uniform(-W / 2.2, W / 2.2); y = oy + rnd.uniform(20, D - 30)
        if abs(x - ox) < 12 and y < oy + 40: continue          # keep the middle free for the action
        h = rnd.uniform(3.0, 5.0)
        geo.cyl(f"field_trunk{i}", (x, y, oz + h * 0.3), 0.18, h * 0.6, trunk, 10)
        geo.sphere(f"field_tree{i}", (x, y, oz + h * 0.75), h * 0.38, leaf, scale=(1.0, 1.0, 1.15))
    rock = pbr("field_rock", (0.45, 0.44, 0.42), rough=0.9)
    for i in range(int(p["rocks"])):
        x = ox + rnd.uniform(-W / 3, W / 3); y = oy + rnd.uniform(-8, 40); s = rnd.uniform(0.25, 0.7)
        if abs(x - ox) < 6 and -2 < y - oy < 20: continue
        geo.sphere(f"field_rock{i}", (x, y, oz + s * 0.2), s, rock, scale=(1.3, 1.0, 0.6))
    if p["road"]:
        dirt = pbr("field_dirt", (0.66, 0.46, 0.24), rough=0.95)
        (x0, y0), (x1, y1) = p["road"]["from"], p["road"]["to"]; L = math.dist((x0, y0), (x1, y1))
        o = geo.cube("field_road", (ox + (x0 + x1) / 2, oy + (y0 + y1) / 2, oz - 0.02), (p["road"].get("width", 3.0), L, 0.06), dirt)
        o.rotation_euler = (0, 0, math.atan2(x0 - x1, y1 - y0))
    return {"parts": {}, "anchors": {"center": [ox, oy, oz]}}
