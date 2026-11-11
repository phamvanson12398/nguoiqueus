"""3D cast-iron manhole cover: round (rings texture) or square (checker grid, bevelled).
Falls, rolls, tumbles -> 3D (skill rule: props that fall/roll are 3D)."""
from core.look import iron_mat
from core.geo import cube, cyl

DEFAULTS = dict(kind="round", radius=0.45, side=0.80, thickness=0.06)


def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    name = p["name"]
    if p["kind"] == "round":
        o = cyl(name, (0, 0, 0), p["radius"], p["thickness"], iron_mat("iron_round", "rings"), 48)
    else:
        o = cube(name, (0, 0, 0), (p["side"], p["side"], p["thickness"]), iron_mat("iron_square", "grid"))
        bev = o.modifiers.new("bev", 'BEVEL'); bev.width = 0.015; bev.segments = 2
    return o
