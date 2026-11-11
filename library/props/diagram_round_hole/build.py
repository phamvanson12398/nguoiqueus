"""2D explainer: round hole, round cover, a diameter arrow that can spin, two labels.
Parts: <prefix>_rd_cover, <prefix>_diam_pivot, <prefix>_l_same, <prefix>_l_never."""
from core.look import flat
from core.geo import empty, shape, ellipse, arrow2d, label

DEFAULTS = dict(prefix="dg", radius=0.9, cover=1.03, label_top="SAME WIDTH", label_bottom="CAN'T FALL IN")


def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    pre = p["prefix"]
    hole_m = flat("hole_dark", (0.01, 0.01, 0.012)); iron = flat("iron2d", (0.20, 0.20, 0.22))
    green = flat("dg_green", (0.05, 0.6, 0.2))
    g = empty(p["name"], p.get("parent"))
    shape(g, f"{pre}_rd_hole", ellipse(0, 0, p["radius"], p["radius"], 48), hole_m, 0.0, outline=0.05)
    cov = empty(f"{pre}_rd_cover", g, (0, 0, 0.05))
    shape(cov, f"{pre}_rd_cov", ellipse(0, 0, p["cover"], p["cover"], 48), iron, 0, outline=0.05)
    piv = empty(f"{pre}_diam_pivot", g, (0, 0, 0.2))
    arrow2d(piv, f"{pre}_diam", (-p["cover"], 0), (p["cover"], 0), 0.07, green)
    label(g, f"{pre}_l_same", p["label_top"], (0, 1.55), 0.34, green)
    label(g, f"{pre}_l_never", p["label_bottom"], (0, -1.55), 0.34, green)
    return g
