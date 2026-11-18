"""Cartoon sofa / couch for dialogue videos (two or three people side by side). Origin at the bottom centre;
seat top at z = seat_h, front edge at y = -depth/2 (faces the camera, -Y)."""
from core.look import pbr
from core.geo import rbox, group3d, attach

DEFAULTS = dict(width=2.6, seat_h=0.52, depth=0.9, back_h=0.62, arm_h=0.28, color=[0.25, 0.45, 0.72], pillows=True)


def _tag(rgb): return "_".join(str(int(round(c * 1000))) for c in rgb)


def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    name, W, H, D = p["name"], float(p["width"]), float(p["seat_h"]), float(p["depth"])
    col = tuple(p["color"]); dark = tuple(c * 0.78 for c in col); light = tuple(min(1.0, c * 1.15) for c in col)
    m = pbr(f"sofa_body_{_tag(col)}", col, rough=0.85)
    md = pbr(f"sofa_dark_{_tag(col)}", dark, rough=0.85)
    ml = pbr(f"sofa_cush_{_tag(col)}", light, rough=0.85)
    foot = pbr("sofa_feet", (0.18, 0.12, 0.08), rough=0.6)
    root = group3d(name); parts = []
    base_h = H - 0.14
    parts.append(rbox(f"{name}_base", (0, 0, 0.08 + base_h / 2 - 0.04), (W, D, base_h - 0.08), md, radius=0.05))
    n = max(1, round((W - 0.4) / 0.9))
    cw = (W - 0.36) / n
    for k in range(n):                                       # seat cushions
        x = -W / 2 + 0.18 + cw * (k + 0.5)
        parts.append(rbox(f"{name}_seat{k}", (x, -0.04, H - 0.07), (cw - 0.03, D - 0.12, 0.14), ml, radius=0.06))
        parts.append(rbox(f"{name}_backc{k}", (x, D / 2 - 0.2, H + float(p["back_h"]) * 0.45), (cw - 0.05, 0.22, float(p["back_h"]) * 0.8), ml, radius=0.08))
    parts.append(rbox(f"{name}_back", (0, D / 2 - 0.08, (H + float(p["back_h"])) / 2 + 0.04), (W, 0.16, H + float(p["back_h"]) - 0.08), m, radius=0.07))
    for s in (-1, 1):                                        # arms
        parts.append(rbox(f"{name}_arm{s}", (s * (W / 2 - 0.1), 0, (H + float(p["arm_h"])) / 2 + 0.04), (0.2, D, H + float(p["arm_h"]) - 0.08), m, radius=0.08))
        for y in (-1, 1):
            parts.append(rbox(f"{name}_foot{s}{y}", (s * (W / 2 - 0.12), y * (D / 2 - 0.1), 0.04), (0.08, 0.08, 0.08), foot, radius=0.015))
    if p.get("pillows", True):
        parts.append(rbox(f"{name}_pillow", (-W / 2 + 0.42, D / 2 - 0.36, H + 0.2), (0.34, 0.12, 0.32), pbr("sofa_pillow", (0.98, 0.82, 0.35), rough=0.9), radius=0.06))
    attach(root, *parts)
    return root
