"""Fridge for dialogue videos. States by visibility: <name>_door_closed / <name>_door_open (door swung toward +X, inside lit with
shelves and food). Origin at the bottom centre, front facing the camera (-Y)."""
import math
from core.look import pbr, flat
from core.geo import rbox, group3d, attach

DEFAULTS = dict(height=2.5, width=1.1, color=[0.85, 0.92, 0.95])


def _tag(rgb): return "_".join(str(int(round(c * 1000))) for c in rgb)


def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    name, H, W = p["name"], float(p["height"]), float(p["width"])
    body = pbr(f"fridge_body_{_tag(p['color'])}", tuple(p["color"]), rough=0.35)
    trim = pbr("fridge_trim", (0.55, 0.58, 0.6), rough=0.3, metal=0.5)
    root = group3d(name); parts = []
    parts.append(rbox(f"{name}_body", (0, 0.08, H / 2), (W, 0.7, H), body, radius=0.06))
    closed = rbox(f"{name}_door_closed", (0, -0.29, H / 2), (W - 0.02, 0.08, H - 0.04), body, radius=0.05)
    handle = rbox(f"{name}_door_closed_handle", (W / 2 - 0.12, -0.36, H * 0.6), (0.05, 0.05, 0.6), trim, radius=0.02)
    opn = group3d(f"{name}_door_open")
    inside = rbox(f"{name}_door_open_inside", (0, -0.26, H / 2), (W - 0.12, 0.02, H - 0.16), flat("fridge_light", (1.0, 0.98, 0.85)), radius=0.03)
    inside.parent = opn
    for k, z in enumerate((0.5, 0.95, 1.4, 1.85)):
        rbox(f"{name}_door_open_shelf{k}", (0, -0.28, z), (W - 0.16, 0.04, 0.03), trim, radius=0.01).parent = opn
    for k, (x, z, c) in enumerate(((-0.25, 0.62, (0.9, 0.3, 0.25)), (0.15, 0.62, (0.95, 0.85, 0.3)), (-0.1, 1.07, (0.4, 0.75, 0.35)), (0.25, 1.52, (0.95, 0.95, 0.95)))):
        rbox(f"{name}_door_open_food{k}", (x, -0.31, z), (0.22, 0.04, 0.22), flat(f"fridge_food{k}", c), radius=0.04).parent = opn
    door = rbox(f"{name}_door_open_door", (W / 2 + 0.02 + 0.04, -0.29 - W / 2, H / 2), (0.08, W - 0.02, H - 0.04), body, radius=0.05)
    door.parent = opn
    parts += [closed, handle, opn]
    attach(root, *parts)
    for o in [opn] + list(opn.children_recursive): o.hide_render = True
    return root
