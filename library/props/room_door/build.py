"""Room door in a wall section for dialogue videos (someone answers the door, slams it). States by visibility:
<name>_closed / <name>_open (door swung in, dark doorway). Origin at the bottom centre, facing the camera (-Y)."""
from core.look import pbr, flat
from core.geo import rbox, group3d, attach

DEFAULTS = dict(wall=[0.86, 0.82, 0.74], door=[0.55, 0.33, 0.18], wall_width=2.4)


def _tag(rgb): return "_".join(str(int(round(c * 1000))) for c in rgb)


def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    name, WW = p["name"], float(p["wall_width"])
    wall = pbr(f"rdoor_wall_{_tag(p['wall'])}", tuple(p["wall"]), rough=0.9)
    wood = pbr(f"rdoor_wood_{_tag(p['door'])}", tuple(p["door"]), rough=0.6)
    knob = pbr("rdoor_knob", (0.85, 0.7, 0.3), rough=0.3, metal=0.8)
    root = group3d(name); parts = []
    for s in (-1, 1):
        parts.append(rbox(f"{name}_wall{s}", (s * (0.5 + (WW - 1.0) / 4), 0.1, 1.5), ((WW - 1.0) / 2, 0.16, 3.0), wall, radius=0.01))
    parts.append(rbox(f"{name}_lintel", (0, 0.1, 2.75), (1.0, 0.16, 0.5), wall, radius=0.01))
    parts.append(rbox(f"{name}_frame", (0, 0.0, 1.27), (1.08, 0.06, 2.54), wood, radius=0.01))
    closed = rbox(f"{name}_closed", (0, -0.02, 1.24), (0.92, 0.06, 2.46), wood, radius=0.02)
    kb = rbox(f"{name}_closed_knob", (0.34, -0.08, 1.2), (0.08, 0.06, 0.08), knob, radius=0.03)
    opn = group3d(f"{name}_open")
    rbox(f"{name}_open_dark", (0, 0.06, 1.24), (0.92, 0.02, 2.46), flat("rdoor_dark", (0.06, 0.06, 0.09)), radius=0.01).parent = opn
    rbox(f"{name}_open_door", (-0.42, 0.5, 1.24), (0.06, 0.88, 2.46), wood, radius=0.02).parent = opn
    parts += [closed, kb, opn]
    attach(root, *parts)
    for o in [opn] + list(opn.children_recursive): o.hide_render = True
    return root
