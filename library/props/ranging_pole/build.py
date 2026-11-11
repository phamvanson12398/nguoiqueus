"""3D surveyor's ranging pole: red/white striped staff with an iron spike at the bottom.

Hierarchy (names prefixed with the story id <name>):
  <name>              root empty, origin at the very spike tip (z = 0). Lower z in the story to sink it into mud.
    <name>_tip        iron spike (cone), bottom of the pole
    <name>_shaft      EMPTY holding the striped bands
      <name>_band<i>  coloured bands, i = 0 at the bottom (color_a, color_b, color_a, ...)
    <name>_cap        iron ferrule on top
    <name>_flag       small pennant at the top (only when flag=True)
"""
import math
from core.look import pbr
from core.geo import cyl, cone, extrude, empty, group3d, attach

DEFAULTS = dict(height=2.6, radius=0.05, bands=6, tip_length=0.24,
                color_a=[0.85, 0.08, 0.06], color_b=[0.92, 0.9, 0.86],
                flag=False, flag_color=[0.95, 0.7, 0.05])


def _tag(rgb):
    return "_".join(str(int(round(c * 100))) for c in rgb)


def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    name = p["name"]
    H = max(0.5, float(p["height"]))
    r = max(0.015, float(p["radius"]))
    n = max(1, int(p["bands"]))
    tip_h = min(max(0.05, float(p["tip_length"])), H * 0.3)
    rgb_a = tuple(p["color_a"]); rgb_b = tuple(p["color_b"]); rgb_f = tuple(p["flag_color"])

    m_a = pbr(f"ranging_pole_a_{_tag(rgb_a)}", rgb_a, rough=0.55)
    m_b = pbr(f"ranging_pole_b_{_tag(rgb_b)}", rgb_b, rough=0.6)
    m_iron = pbr("ranging_pole_iron", (0.12, 0.12, 0.13), rough=0.45, metal=0.75)

    root = group3d(name)

    # ---- iron spike: point at z = 0, widens to the shaft radius ----
    tip = cone(f"{name}_tip", (0, 0, tip_h / 2), 0.004, r * 1.02, tip_h, m_iron, verts=24)
    attach(root, tip)

    # ---- striped shaft ----
    cap_h = 0.05
    z0 = tip_h
    z1 = H - cap_h
    band_h = (z1 - z0) / n
    shaft = empty(f"{name}_shaft", root, (0, 0, 0))
    for i in range(n):
        zc = z0 + band_h * (i + 0.5)
        b = cyl(f"{name}_band{i}", (0, 0, zc), r, band_h, m_a if i % 2 == 0 else m_b, 24)
        b.parent = shaft

    # ---- iron ferrule on top ----
    cap = cyl(f"{name}_cap", (0, 0, H - cap_h / 2), r * 1.12, cap_h, m_iron, 24)
    attach(root, cap)

    # ---- optional pennant near the top (vertical XZ plane) ----
    if p["flag"]:
        m_f = pbr(f"ranging_pole_flag_{_tag(rgb_f)}", rgb_f, rough=0.6)
        fl, fh = 0.38, 0.24
        pts = [(0.0, 0.0), (fl, fh * 0.5), (0.0, fh)]
        top = H - cap_h - 0.04 - fh
        flag = extrude(f"{name}_flag", (r * 0.9, 0, top), pts, 0.02, m_f, rot=(math.pi / 2, 0, 0))
        attach(root, flag)

    return root
