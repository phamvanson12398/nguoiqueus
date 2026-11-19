"""Floor lamp for dialogue videos (someone gets up to switch the light off). Base + pole + a drum shade with two
looks swapped by visibility: `<name>_shade_on` (glowing warm) and `<name>_shade_off` (dull). Origin at the bottom
centre; the switch (pull cord) at `<name>_cord`, about 1.45 high on the camera side."""
from core.look import pbr, flat
from core.geo import rbox, cyl, group3d, attach

DEFAULTS = dict(height=2.3, shade=[0.98, 0.86, 0.55], metal=[0.18, 0.18, 0.2], on=True)


def _tag(rgb): return "_".join(str(int(round(c * 1000))) for c in rgb)


def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    name, H = p["name"], float(p["height"])
    metal = pbr(f"lamp_metal_{_tag(p['metal'])}", tuple(p["metal"]), rough=0.4, metal=0.6)
    glow = flat(f"lamp_glow_{_tag(p['shade'])}", tuple(min(1.0, c * 1.25) for c in p["shade"]))
    dull = pbr(f"lamp_dull_{_tag(p['shade'])}", tuple(c * 0.55 for c in p["shade"]), rough=0.9)
    root = group3d(name); parts = []
    parts.append(cyl(f"{name}_base", (0, 0, 0.03), 0.28, 0.06, metal, 32))
    parts.append(cyl(f"{name}_pole", (0, 0, H / 2), 0.035, H - 0.1, metal, 12))
    on = cyl(f"{name}_shade_on", (0, 0, H - 0.18), 0.36, 0.5, glow, 32)
    off = cyl(f"{name}_shade_off", (0, 0, H - 0.18), 0.355, 0.495, dull, 32)
    parts += [on, off]
    parts.append(cyl(f"{name}_cord", (0.12, -0.2, H - 0.62), 0.012, 0.45, metal, 6))
    attach(root, *parts)
    (off if p.get("on", True) else on).hide_render = True
    return root
