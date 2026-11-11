"""Face library: expressions built as swappable 2D groups on a character head.

Kinds: neutral (blinks), happy, smirk, wink, angry, shock, worried, grumpy, focus, smug_closed.
"""
import math
from . import geo
from .geo import empty, disc, stroke, shape, ellipse, rrect, arc
from .look import flat

MOUTH = TONGUE = TEETH = SWEAT = RED_M = None
KINDS = ("neutral", "happy", "smirk", "wink", "angry", "shock", "worried", "grumpy", "focus", "smug_closed")


def init():
    global MOUTH, TONGUE, TEETH, SWEAT, RED_M
    MOUTH = flat("mouth", (0.55, 0.10, 0.10)); TONGUE = flat("tongue", (0.95, 0.45, 0.45))
    TEETH = flat("teeth", (1, 1, 1)); SWEAT = flat("sweat", (0.45, 0.75, 1.0)); RED_M = flat("vein", (0.85, 0.1, 0.1))


def eye(parent, name, x, y, z, rx=0.055, ry=0.085):
    g = empty(name, parent, (x, y, z)); disc(g, name + "_d", 0, 0, 1.0, 0, geo.INK); g.scale = (rx, ry, 1); return g

def build_faces(head, p, skin, kinds, ey=-0.02, dx=0.15):
    """returns dict kind -> group, plus 'blink' eye list for neutral"""
    F = {}; blink_eyes = []
    for kind in kinds:
        g = empty(f"{p}_{kind}", head); F[kind] = g; z = 0.06
        if kind == "neutral":
            blink_eyes += [eye(g, f"{p}nL", -dx, ey, z), eye(g, f"{p}nR", dx, ey, z)]
            stroke(g, f"{p}n_m", arc(0, ey - 0.11, 0.11, 0.06, 200, 340), 0.035, z)
            stroke(g, f"{p}n_bL", [(-dx - 0.07, ey + 0.14), (-dx + 0.06, ey + 0.16)], 0.03, z)
            stroke(g, f"{p}n_bR", [(dx - 0.06, ey + 0.16), (dx + 0.07, ey + 0.14)], 0.03, z)
        elif kind == "happy":
            for s in (-1, 1):
                stroke(g, f"{p}h_e{s}", arc(s * dx, ey - 0.03, 0.07, 0.07, 20, 160), 0.035, z)
            mp = [(-0.17, ey - 0.10)] + arc(0, ey - 0.10, 0.17, 0.17, 180, 360, 16)[1:]
            shape(g, f"{p}h_m", mp, MOUTH, z, outline=0.03)
            shape(g, f"{p}h_t", ellipse(0, ey - 0.22, 0.07, 0.04, 16), TONGUE, z + 0.02, outline=0)
        elif kind in ("smirk", "wink"):
            eye(g, f"{p}s_eL", -dx, ey - 0.01, z, 0.055, 0.065)
            shape(g, f"{p}s_lidL", rrect(-dx, ey + 0.04, 0.15, 0.06, 0.02), skin, z + 0.03, outline=0)
            stroke(g, f"{p}s_llL", [(-dx - 0.07, ey + 0.015), (-dx + 0.07, ey + 0.015)], 0.03, z + 0.04)
            if kind == "wink":
                stroke(g, f"{p}w_eR", arc(dx, ey - 0.04, 0.07, 0.06, 20, 160), 0.035, z)
            else:
                eye(g, f"{p}s_eR", dx, ey - 0.01, z, 0.055, 0.065)
                shape(g, f"{p}s_lidR", rrect(dx, ey + 0.04, 0.15, 0.06, 0.02), skin, z + 0.03, outline=0)
                stroke(g, f"{p}s_llR", [(dx - 0.07, ey + 0.015), (dx + 0.07, ey + 0.015)], 0.03, z + 0.04)
            stroke(g, f"{p}s_bL", [(-dx - 0.08, ey + 0.12), (-dx + 0.07, ey + 0.11)], 0.03, z)
            stroke(g, f"{p}s_bR", [(dx - 0.07, ey + 0.17), (dx + 0.01, ey + 0.21), (dx + 0.08, ey + 0.19)], 0.03, z)
            stroke(g, f"{p}s_m", [(-0.10, ey - 0.15), (0.02, ey - 0.16), (0.11, ey - 0.13), (0.15, ey - 0.09)], 0.035, z)
        elif kind == "angry":
            eye(g, f"{p}a_eL", -dx + 0.01, ey + 0.0, z, 0.05, 0.05); eye(g, f"{p}a_eR", dx - 0.01, ey, z, 0.05, 0.05)
            stroke(g, f"{p}a_bL", [(-dx - 0.12, ey + 0.16), (-dx + 0.10, ey + 0.05)], 0.05, z + 0.01)
            stroke(g, f"{p}a_bR", [(dx - 0.10, ey + 0.05), (dx + 0.12, ey + 0.16)], 0.05, z + 0.01)
            shape(g, f"{p}a_t", rrect(0, ey - 0.20, 0.26, 0.12, 0.03), TEETH, z, outline=0.03)
            for x in (-0.065, 0, 0.065):
                stroke(g, f"{p}a_tt{x}", [(x, ey - 0.25), (x, ey - 0.15)], 0.015, z + 0.03)
            stroke(g, f"{p}a_tm", [(-0.12, ey - 0.20), (0.12, ey - 0.20)], 0.015, z + 0.03)
            stroke(g, f"{p}a_v1", [(0.20, 0.33), (0.26, 0.28)], 0.03, z, m=RED_M); stroke(g, f"{p}a_v2", [(0.27, 0.36), (0.29, 0.29)], 0.03, z, m=RED_M)
        elif kind == "shock":
            for s in (-1, 1):
                shape(g, f"{p}k_w{s}", ellipse(s * dx, ey + 0.01, 0.085, 0.11, 24), geo.WHITE, z, outline=0.03)
                disc(g, f"{p}k_p{s}", s * dx, ey + 0.0, 0.035, z + 0.03)
                stroke(g, f"{p}k_b{s}", arc(s * dx, ey + 0.13, 0.08, 0.05, 30, 150), 0.03, z)
            shape(g, f"{p}k_m", ellipse(0, ey - 0.20, 0.08, 0.10, 24), MOUTH, z, outline=0.03)
        elif kind == "worried":
            eye(g, f"{p}o_eL", -dx, ey, z, 0.05, 0.075); eye(g, f"{p}o_eR", dx, ey, z, 0.05, 0.075)
            stroke(g, f"{p}o_bL", [(-dx - 0.08, ey + 0.11), (-dx + 0.07, ey + 0.16)], 0.03, z)
            stroke(g, f"{p}o_bR", [(dx - 0.07, ey + 0.16), (dx + 0.08, ey + 0.11)], 0.03, z)
            stroke(g, f"{p}o_m", [(-0.10, ey - 0.17), (-0.05, ey - 0.14), (0, ey - 0.17), (0.05, ey - 0.14), (0.10, ey - 0.17)], 0.03, z)
            shape(g, f"{p}o_sw", [(0.33, 0.22), (0.37, 0.12), (0.37, 0.08), (0.33, 0.05), (0.29, 0.08), (0.29, 0.12)], SWEAT, z, outline=0.02)
        elif kind == "grumpy":
            for s in (-1, 1):
                eye(g, f"{p}g_e{s}", s * dx, ey - 0.02, z, 0.055, 0.04)
                stroke(g, f"{p}g_b{s}", [(s * (dx + 0.09), ey + 0.08), (s * (dx - 0.07), ey + 0.06)], 0.04, z)
            stroke(g, f"{p}g_m", arc(0, ey - 0.22, 0.10, 0.05, 20, 160), 0.035, z)
        elif kind == "focus":
            for s in (-1, 1):
                eye(g, f"{p}f_e{s}", s * dx, ey, z, 0.05, 0.05)
                stroke(g, f"{p}f_b{s}", [(s * (dx + 0.08), ey + 0.12), (s * (dx - 0.07), ey + 0.09)], 0.03, z)
            stroke(g, f"{p}f_m", [(-0.05, ey - 0.15), (0.06, ey - 0.15)], 0.03, z)
            shape(g, f"{p}f_tg", ellipse(0.09, ey - 0.17, 0.04, 0.03, 12), TONGUE, z, outline=0.015)
        elif kind == "smug_closed":
            for s in (-1, 1):
                stroke(g, f"{p}c_e{s}", arc(s * dx, ey + 0.02, 0.07, 0.05, 200, 340), 0.035, z)
            stroke(g, f"{p}c_m", [(-0.12, ey - 0.13), (0, ey - 0.17), (0.12, ey - 0.13), (0.16, ey - 0.10)], 0.035, z)
    return F, blink_eyes
