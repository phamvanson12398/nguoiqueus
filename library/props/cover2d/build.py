"""2D manhole cover held in a character's hands (or worn as a hat): round with rings or
square with a grid.  Hand props are 2D (skill rule); parent it to the torso or head."""
from core.chars import prop_round, prop_square

DEFAULTS = dict(kind="square", size=None)


def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    if p["kind"] == "round":
        return prop_round(p.get("parent"), p["name"], *( [p["size"]] if p["size"] else [] ))
    return prop_square(p.get("parent"), p["name"], *( [p["size"]] if p["size"] else [] ))
