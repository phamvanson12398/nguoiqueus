"""2D explainer: square hole with a bigger square cover above it, side arrow (green)
and diagonal arrow (red) with labels.  Parts for animation (prefix 'dg' by default):
<prefix>_sq_cover, <prefix>_side, <prefix>_diag, <prefix>_l_side, <prefix>_l_diag."""
from core.look import flat
from core.geo import empty, shape, rrect, arrow2d, label

DEFAULTS = dict(prefix="dg", side=1.8, cover=2.05, label_side="SIDE", label_diag="1.4x LONGER")


def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    pre, HS = p["prefix"], p["side"]
    hole_m = flat("hole_dark", (0.01, 0.01, 0.012)); iron = flat("iron2d", (0.20, 0.20, 0.22))
    green = flat("dg_green", (0.05, 0.6, 0.2)); red = flat("dg_red", (0.9, 0.12, 0.1))
    g = empty(p["name"], p.get("parent"))
    shape(g, f"{pre}_sq_hole", rrect(0, 0, HS, HS, 0.02), hole_m, 0.0, outline=0.05)
    cov = empty(f"{pre}_sq_cover", g, (0, 0, 0.05))
    shape(cov, f"{pre}_sq_cov", rrect(0, 0, p["cover"], p["cover"], 0.05), iron, 0, outline=0.05)
    arrow2d(g, f"{pre}_side", (-HS / 2, -HS / 2 - 0.45), (HS / 2, -HS / 2 - 0.45), 0.06, green)
    arrow2d(g, f"{pre}_diag", (-HS / 2 + 0.05, -HS / 2 + 0.05), (HS / 2 - 0.05, HS / 2 - 0.05), 0.07, red)
    label(g, f"{pre}_l_side", p["label_side"], (0, -HS / 2 - 0.85), 0.32, green)
    label(g, f"{pre}_l_diag", p["label_diag"], (0, HS / 2 + 0.55), 0.32, red)
    return g
