"""2D clipboard with paper lines and a metal clip (held at the chest)."""
from core.look import flat
from core.geo import empty, shape, stroke, rrect

DEFAULTS = dict(prefix="clip")


def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    pre = p["prefix"]
    board = flat("clipboard", (0.55, 0.33, 0.15)); paper = flat("paper", (0.98, 0.98, 0.96)); line = flat("paperline", (0.6, 0.6, 0.62))
    g = empty(p["name"], p.get("parent"))
    shape(g, f"{pre}_b", rrect(0, 0, 0.34, 0.44, 0.03), board, 0, outline=0.03)
    shape(g, f"{pre}_p", rrect(0, -0.02, 0.27, 0.34, 0.01), paper, 0.02, outline=0)
    for k in range(4):
        stroke(g, f"{pre}_l{k}", [(-0.09, 0.08 - k * 0.07), (0.09, 0.08 - k * 0.07)], 0.015, 0.04, m=line)
    shape(g, f"{pre}_c", rrect(0, 0.21, 0.12, 0.05, 0.01), flat("clipmetal", (0.7, 0.7, 0.72)), 0.05, outline=0.015)
    return g
