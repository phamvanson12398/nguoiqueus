"""Manhole opening in the road: dark disc/square + metal rim.  Root is an empty at the hole centre."""
import bpy
from core import ctx
from core.look import flat, pbr, setmat
from core.geo import cube, cyl

DEFAULTS = dict(kind="round", radius=0.45, side=0.80)


def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    hole_m = flat("hole_dark", (0.01, 0.01, 0.012))
    rim_m = pbr("rim", (0.25, 0.25, 0.27), rough=0.4, metal=0.8)
    g = bpy.data.objects.new(p["name"], None); ctx.col.objects.link(g)
    if p["kind"] == "round":
        r_ = p["radius"]
        d = cyl(p.get("dark_name", "hole_r_dark"), (0, 0, 0.004), r_ - 0.02, 0.006, hole_m, 48); d.parent = g; d.location = (0, 0, 0.004)
        bpy.ops.mesh.primitive_torus_add(major_radius=r_ + 0.02, minor_radius=0.035, major_segments=48, minor_segments=8)
        r = setmat(bpy.context.object, rim_m); r.parent = g; r.location = (0, 0, 0.01); r.scale = (1, 1, 0.4)
    else:
        s = p["side"]; pre = p.get("prefix", "hole_s")
        d = cube(f"{pre}_dark", (0, 0, 0), (s - 0.06, s - 0.06, 0.006), hole_m); d.parent = g; d.location = (0, 0, 0.004)
        k = s / 0.80; e = 0.42 * k; L = 0.9 * k
        for i, (dx, dy, sx, sy) in enumerate(((0, e, L, 0.06), (0, -e, L, 0.06), (e, 0, 0.06, L), (-e, 0, 0.06, L))):
            r = cube(f"{pre}_rim{i}", (0, 0, 0), (sx, sy, 0.025), rim_m); r.parent = g; r.location = (dx, dy, 0.012)
    return g
