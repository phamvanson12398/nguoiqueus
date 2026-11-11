"""2D paper bill on a roll; the strip '<prefix>_strip' unrolls downward when its Y scale grows
(0.03 = rolled, ~1.9 = fully open).  Red total at the bottom."""
import bpy
from core import ctx
from core.look import flat
from core.geo import empty, shape, stroke, rrect, ellipse, text

DEFAULTS = dict(prefix="bill", total="$$$")


def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    pre = p["prefix"]
    paper = flat("paper", (0.98, 0.98, 0.96)); line = flat("paperline", (0.6, 0.6, 0.62)); red = flat("vein", (0.85, 0.1, 0.1))
    g = empty(p["name"], p.get("parent"))
    strip = empty(f"{pre}_strip", g)
    shape(strip, f"{pre}_p", rrect(0, -0.5, 0.36, 1.0, 0.01), paper, 0, outline=0.02)
    for k in range(12):
        stroke(strip, f"{pre}_l{k}", [(-0.13, -0.08 - k * 0.075), (0.06 if k % 3 else 0.13, -0.08 - k * 0.075)], 0.012, 0.02, m=line)
    text(f"{pre}_total", p["total"], 0.09, strip, (0, -0.98, 0.03), red, align_y=False, font_path=None)
    shape(g, f"{pre}_roll", ellipse(0, 0, 0.2, 0.06, 20), paper, 0.05, outline=0.02)
    return g
