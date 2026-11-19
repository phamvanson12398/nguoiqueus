"""TV on a low cabinet for dialogue videos. States by visibility: <name>_screen_on (bright picture) / <name>_screen_off (dark glass).
Origin at the bottom centre, screen facing the camera (-Y)."""
from core.look import pbr, flat
from core.geo import rbox, group3d, attach

DEFAULTS = dict(width=1.9, cabinet=[0.45, 0.3, 0.2], frame=[0.08, 0.08, 0.09])


def _tag(rgb): return "_".join(str(int(round(c * 1000))) for c in rgb)


def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    name, W = p["name"], float(p["width"])
    wood = pbr(f"tv_cab_{_tag(p['cabinet'])}", tuple(p["cabinet"]), rough=0.6)
    frm = pbr(f"tv_frame_{_tag(p['frame'])}", tuple(p["frame"]), rough=0.3)
    root = group3d(name); parts = []
    parts.append(rbox(f"{name}_cabinet", (0, 0, 0.3), (W + 0.4, 0.55, 0.6), wood, radius=0.03))
    parts.append(rbox(f"{name}_stand", (0, 0, 0.66), (0.4, 0.2, 0.12), frm, radius=0.02))
    h = W * 9 / 16
    parts.append(rbox(f"{name}_frame", (0, 0, 0.72 + h / 2 + 0.05), (W, 0.08, h + 0.1), frm, radius=0.03))
    on = rbox(f"{name}_screen_on", (0, -0.045, 0.77 + h / 2), (W - 0.1, 0.01, h - 0.02), flat("tv_screen_on", (0.45, 0.75, 1.0)), radius=0.005)
    pic = rbox(f"{name}_screen_on_pic", (-W * 0.15, -0.052, 0.77 + h * 0.45), (W * 0.35, 0.01, h * 0.4), flat("tv_pic", (1.0, 0.82, 0.35)), radius=0.005)
    off = rbox(f"{name}_screen_off", (0, -0.045, 0.77 + h / 2), (W - 0.1, 0.01, h - 0.02), pbr("tv_screen_off", (0.04, 0.05, 0.07), rough=0.15), radius=0.005)
    parts += [on, pic, off]
    attach(root, *parts)
    off.hide_render = True
    return root
