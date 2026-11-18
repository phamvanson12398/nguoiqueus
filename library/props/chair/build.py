"""Simple cartoon chair for dialogue videos: seat + backrest + four legs. Origin at the bottom centre;
the seat top is at z = seat_h, the front edge at y = -depth/2 (faces the camera, -Y)."""
from core.look import pbr
from core.geo import rbox, group3d, attach

DEFAULTS = dict(seat_h=0.5, width=0.62, depth=0.58, back_h=0.62, color=[0.62, 0.36, 0.18], cushion=[0.85, 0.28, 0.25])


def _tag(rgb): return "_".join(str(int(round(c * 1000))) for c in rgb)


def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    name, H, W, D = p["name"], float(p["seat_h"]), float(p["width"]), float(p["depth"])
    wood = pbr(f"chair_wood_{_tag(p['color'])}", tuple(p["color"]), rough=0.6)
    soft = pbr(f"chair_cushion_{_tag(p['cushion'])}", tuple(p["cushion"]), rough=0.8)
    root = group3d(name); parts = []
    parts.append(rbox(f"{name}_seat", (0, 0, H - 0.04), (W, D, 0.08), wood, radius=0.02))
    parts.append(rbox(f"{name}_cushion", (0, -0.01, H + 0.015), (W - 0.06, D - 0.06, 0.05), soft, radius=0.025))
    parts.append(rbox(f"{name}_back", (0, D / 2 - 0.03, H + float(p["back_h"]) / 2), (W, 0.06, float(p["back_h"])), wood, radius=0.025))
    lw = 0.06
    for k, (x, y) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
        parts.append(rbox(f"{name}_leg{k}", (x * (W / 2 - lw), y * (D / 2 - lw), (H - 0.08) / 2), (lw, lw, H - 0.08), wood, radius=0.01))
    attach(root, *parts)
    return root
