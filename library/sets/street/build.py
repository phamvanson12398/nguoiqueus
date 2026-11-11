"""City street: asphalt, sidewalks, dashed centre line, crosswalk, random building blocks
with window facades, street lamps, trees, traffic cones, hydrant.  Road runs along +Y.
Buildings draw from Python's shared `random` (the story seed), so set order matters."""
import random
import bpy
from core.look import flat, pbr, ramp_mat, window_mat, setmat
from core.geo import cube, cyl, sphere, plane

DEFAULTS = dict(
    length=120.0,                       # buildings are placed from y=-8 up to this
    crosswalk_y=9.5,
    cones=[[-2.1, 5.6], [2.3, 5.8], [-2.6, 3.0], [2.9, 2.6]],
    hydrant=[5.4, 6.5],
    lamps=8, trees=10,
    facades=[[[0.62, 0.22, 0.14], "brick"], [[0.85, 0.75, 0.55], "beige"], [[0.20, 0.45, 0.48], "teal"],
             [[0.75, 0.55, 0.35], "sand"], [[0.45, 0.20, 0.25], "plum"], [[0.88, 0.85, 0.80], "cream"]],
    glass=[0.12, 0.18, 0.26],
)


def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    asphalt = ramp_mat("asphalt", [(0.3, (0.10, 0.10, 0.11)), (0.7, (0.16, 0.16, 0.17))], scale=40, bump=0.3, detail=8)
    plane(400, (0, 60, 0), asphalt)
    conc = ramp_mat("concrete", [(0.3, (0.55, 0.53, 0.50)), (0.7, (0.66, 0.64, 0.60))], scale=6, bump=0.2)
    yellow = pbr("paint_y", (0.95, 0.70, 0.05), rough=0.6)
    white = pbr("paint_w", (0.9, 0.9, 0.88), rough=0.6)
    for s_ in (-1, 1):
        cube(f"sidewalk{s_}", (s_ * 6.5, 60, 0.12), (3.0, 200, 0.24), conc)
    for i in range(30):                                       # centre line, dashed
        cube(f"dash{i}", (2.4, -6 + i * 4.0, 0.004), (0.12, 2.0, 0.01), yellow)
    for i in range(7):                                        # crosswalk
        cube(f"zebra{i}", (-4.2 + i * 1.4, p["crosswalk_y"], 0.004), (0.7, 2.2, 0.01), white)

    glass = tuple(p["glass"])
    fac_mats = [window_mat(f"fac_{n}", tuple(c), glass) for c, n in p["facades"]]
    y = -8.0; k = 0
    while y < p["length"]:
        for s_ in (-1, 1):
            w = random.uniform(5, 8); h = random.uniform(7, 18)
            cube(f"bld{k}", (s_ * (8.0 + 2.5 + random.uniform(0, 1.5)), y + w / 2, h / 2), (5, w - 0.3, h), random.choice(fac_mats))
            cube(f"roof{k}", (s_ * 10.5, y + w / 2, h + 0.15), (5.4, w - 0.1, 0.3), conc)
            k += 1
        y += random.uniform(5, 8)

    pole = pbr("lamp_pole", (0.15, 0.17, 0.2), rough=0.4, metal=0.8)
    glow = flat("lamp_glow", (1.0, 0.92, 0.7))
    for i in range(p["lamps"]):
        yy = -4 + i * 12
        for s_ in (-1, 1):
            cyl(f"lamp{i}{s_}", (s_ * 5.3, yy, 2.5), 0.07, 5.0, pole, 12)
            cube(f"lamparm{i}{s_}", (s_ * 4.85, yy, 4.95), (0.9, 0.08, 0.08), pole)
            sphere(f"lampbulb{i}{s_}", (s_ * 4.4, yy, 4.85), 0.16, glow)

    trunk = pbr("trunk", (0.30, 0.18, 0.10)); leaf = pbr("leaf", (0.15, 0.45, 0.15), rough=0.8)
    for i in range(p["trees"]):
        yy = 2 + i * 9
        for s_ in (-1, 1):
            cyl(f"trunk{i}{s_}", (s_ * 7.4, yy, 1.0), 0.12, 2.0, trunk, 10)
            sphere(f"crown{i}{s_}", (s_ * 7.4, yy, 2.6), 1.0, leaf, (1, 1, 1.1))

    cone_o = pbr("cone_o", (0.98, 0.35, 0.03), rough=0.5); cone_w = pbr("cone_w", (0.95, 0.95, 0.95), rough=0.5)
    for i, (x, yy) in enumerate(p["cones"]):
        bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=0.2, radius2=0.03, depth=0.65, location=(x, yy, 0.36))
        setmat(bpy.context.object, cone_o)
        cyl(f"cone{i}_band", (x, yy, 0.42), 0.13, 0.08, cone_w, 24)
        cube(f"cone{i}_base", (x, yy, 0.025), (0.45, 0.45, 0.05), cone_o)
    if p["hydrant"]:
        hyd = pbr("hydrant", (0.85, 0.1, 0.08), rough=0.4)
        hx, hy = p["hydrant"]
        cyl("hydrant", (hx, hy, 0.6), 0.16, 0.6, hyd, 16); sphere("hydrant_top", (hx, hy, 0.92), 0.16, hyd)
    return {}
