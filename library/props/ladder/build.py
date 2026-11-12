"""3D rustic rope-lashed wooden ladder: two slightly bowed brown rails, round rungs lashed with hemp rope at both ends.

Origin at the foot (centre between the two rail feet, z = 0). The ladder stands up along +Z and its face lies in the
XZ plane, so a story leans it against a wall by rotating around X (rot x = +-0.41).

Hierarchy (names prefixed with the story id <name>):
  <name>                root empty
    <name>_rails        EMPTY holding the two rails
      <name>_rail_l     left rail  (x < 0), bowed lathe pole
      <name>_rail_r     right rail (x > 0)
    <name>_rungs        EMPTY holding every rung and its lashings
      <name>_rung<i>    rung i (0 = bottom)
      <name>_rope<i>_l  hemp lashing on the left end of rung i  (when lashing=True)
      <name>_rope<i>_r  hemp lashing on the right end of rung i
"""
import math
import random
from core.look import ramp_mat, warm_top
from core.geo import cyl, lathe, empty, group3d, attach, keep_hidden

DEFAULTS = dict(length=5.0, width=0.6, rungs=0, bow=0.07, rail_radius=0.05, rung_radius=0.034,
                wood_color=[0.34, 0.15, 0.05], rung_color=[0.44, 0.21, 0.07], rope_color=[0.66, 0.44, 0.18],
                lashing=True, broken_rung=-1, seed=7)


def _tag(rgb):
    return "_".join(str(int(round(c * 100))) for c in rgb)


def _shade(rgb, k):
    return tuple(max(0.0, min(1.0, c * k)) for c in rgb)


def _wood(name, rgb):
    # noise stretched along local Z -> long grain (rails and rungs both run along their local Z axis)
    m = ramp_mat(name, [(0.3, _shade(rgb, 0.62)), (0.55, tuple(rgb)), (0.8, _shade(rgb, 1.25))],
                 tex="noise", scale=3.0, mapping_scale=(9.0, 9.0, 0.5), bump=0.25, rough=0.8, detail=6.0)
    return warm_top(m)


def _rope(name, rgb):
    # bands across local Z -> wrapped coils on the short lashing cylinder
    m = ramp_mat(name, [(0.35, _shade(rgb, 0.55)), (0.65, tuple(rgb))],
                 tex="wave", wave_dir='Z', scale=9.0, distortion=1.0, detail=2.0, bump=0.5, rough=0.95)
    return warm_top(m)


def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    name = p["name"]
    L = max(1.0, float(p["length"]))
    W = max(0.25, float(p["width"]))
    rr = max(0.02, float(p["rail_radius"]))
    rg = max(0.015, min(float(p["rung_radius"]), rr * 0.95))
    bow = float(p["bow"])
    n = int(p["rungs"])
    if n <= 0:
        n = max(2, int(round(L / 0.5)) - 1)          # length 5 -> 9 rungs, ~0.5 apart
    rnd = random.Random(int(p["seed"]))

    m_rail = _wood(f"ladder_rail_{_tag(p['wood_color'])}", p["wood_color"])
    m_rung = _wood(f"ladder_rung_{_tag(p['rung_color'])}", p["rung_color"])
    m_rope = _rope(f"ladder_rope_{_tag(p['rope_color'])}", p["rope_color"])

    root = group3d(name)
    rails = empty(f"{name}_rails", root, (0, 0, 0))
    rungs = empty(f"{name}_rungs", root, (0, 0, 0))

    # ---- rails: tapered lathe poles, then bent sideways (hand-cut, slightly warped wood) ----
    # left rail bows outward, right rail bows the same way a bit less -> irregular, not mirror-perfect
    bows = {"l": -bow, "r": -bow * 0.55}
    xs = {"l": -W / 2, "r": W / 2}

    def rail_x(side, z):
        return xs[side] + bows[side] * math.sin(math.pi * min(max(z / L, 0.0), 1.0))

    steps = 16
    for side in ("l", "r"):
        prof = [(0.0, 0.0), (rr * 0.92, 0.0)]
        for k in range(1, steps):
            z = L * k / steps
            prof.append((rr * (1.0 - 0.18 * k / steps), z))   # slight taper toward the top
        prof += [(rr * 0.8, L - 0.015), (rr * 0.55, L), (0.0, L)]
        o = lathe(f"{name}_rail_{side}", (0, 0, 0), prof, m_rail, segments=14)
        for v in o.data.vertices:
            v.co.x += rail_x(side, v.co.z)
        o.data.update()
        o.location = (0, 0, 0)
        o.parent = rails

    # ---- rungs, lashed at both ends ----
    s = L / (n + 1)
    over = rr + 0.05                                  # rung pokes out past each rail
    for i in range(n):
        z = s * (i + 1) + rnd.uniform(-0.025, 0.025)
        xl, xr = rail_x("l", z), rail_x("r", z)
        span = (xr - xl) + 2 * over
        cx = (xl + xr) / 2
        tilt = rnd.uniform(-0.03, 0.03)               # barely-crooked rung: handmade look
        rung = cyl(f"{name}_rung{i}", (cx, 0, z), rg, span, m_rung, verts=14,
                   rot=(0, math.pi / 2 + tilt, 0))
        rung.parent = rungs
        if i == int(p["broken_rung"]):
            keep_hidden(rung, True)
            continue
        if p["lashing"]:
            for side, x in (("l", xl), ("r", xr)):
                rope = cyl(f"{name}_rope{i}_{side}", (x, 0, z), rr + 0.018, rg * 2 + 0.07, m_rope, verts=14)
                rope.parent = rungs

    return root
