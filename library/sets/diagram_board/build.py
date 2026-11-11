"""Explainer board: a paper wall facing -Y and an upright 2D plane in front of it.
Put 2D diagram props on the part 'plane' (x right, y up).  The board is excluded from ink outlines."""
import math
import bpy
from core import ctx
from core.look import flat
from core.geo import cube

DEFAULTS = dict(origin=[500.0, 0.0, 1.5], paper=[0.96, 0.93, 0.84], size=[16, 14])


def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    D = p["origin"]
    back = cube("dg_back", (D[0], D[1] + 0.6, D[2]), (p["size"][0], 0.1, p["size"][1]), flat("dg_paper", tuple(p["paper"])))
    dg = bpy.data.objects.new("dg_plane", None); ctx.col.objects.link(dg)
    dg.location = (D[0], D[1] + 0.3, D[2]); dg.rotation_euler = (math.pi / 2, 0, 0)
    return {"parts": {"plane": dg, "back": back}, "noline": [dg, back], "anchors": {"center": list(D)}}
