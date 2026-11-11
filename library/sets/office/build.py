"""Small office corner: wood floor, two walls, window, framed bar chart, potted plant,
low table with a coffee mug.  The table top is any library prop (default: square manhole cover).
Plant leaves draw from the shared `random`."""
import random
from core.look import flat, pbr, ramp_mat
from core.geo import cube, cyl, sphere

DEFAULTS = dict(origin=[300.0, 0.0], table_top={"type": "manhole_cover", "params": {"kind": "square"}})


def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    ox, oy = p["origin"]
    woodf = ramp_mat("woodfloor", [(0.2, (0.38, 0.22, 0.12)), (0.6, (0.50, 0.31, 0.17)), (0.9, (0.42, 0.25, 0.13))],
                     scale=4.0, mapping_scale=(8, 0.6, 0.6), bump=0.2)
    wall = pbr("office_wall", (0.78, 0.86, 0.74), rough=0.9)
    cube("off_floor", (ox, oy + 4, -0.05), (14, 14, 0.1), woodf)
    cube("off_wallB", (ox, oy + 6.0, 3), (14, 0.2, 6), wall)
    cube("off_wallL", (ox - 3.6, oy + 3, 3), (0.2, 8, 6), wall)
    cube("off_window_frame", (ox + 1.6, oy + 5.88, 2.7), (2.4, 0.06, 1.8), pbr("frame", (0.95, 0.95, 0.95)))
    cube("off_window", (ox + 1.6, oy + 5.84, 2.7), (2.1, 0.06, 1.5), flat("sky_win", (0.55, 0.78, 0.98)))
    cube("off_picture", (ox - 1.4, oy + 5.88, 2.9), (1.0, 0.06, 0.75), pbr("pframe", (0.25, 0.15, 0.08)))
    cube("off_picture_in", (ox - 1.4, oy + 5.84, 2.9), (0.85, 0.06, 0.6), flat("chart_bg", (0.95, 0.95, 0.92)))
    for i, hh in enumerate((0.15, 0.3, 0.22, 0.42)):            # little bar chart in the frame
        cube(f"off_bar{i}", (ox - 1.7 + i * 0.2, oy + 5.80, 2.68 + hh / 2), (0.12, 0.02, hh), flat(f"bar{i}", (0.1, 0.5, 0.2)))
    pot = pbr("pot", (0.75, 0.35, 0.2)); cyl("off_pot", (ox - 2.8, oy + 5.0, 0.3), 0.3, 0.6, pot, 24)
    leaf = pbr("leaf", (0.15, 0.45, 0.15), rough=0.8)
    for i in range(5):
        sphere(f"off_leaf{i}", (ox - 2.8 + random.uniform(-0.3, 0.3), oy + 5.0 + random.uniform(-0.2, 0.2), 0.9 + i * 0.22), 0.32, leaf)
    tc = (ox + 0.3, oy + 3.0)
    tt = p["table_top"]
    if tt:
        top = lib.prop(tt["type"], dict(tt.get("params", {}), name="table_top"))
    else:
        top = cube("table_top", (0, 0, 0), (0.8, 0.8, 0.06), pbr("table_wood", (0.45, 0.28, 0.15)))
    top.location = (tc[0], tc[1], 0.5)
    leg = pbr("table_leg", (0.15, 0.15, 0.16), rough=0.3, metal=0.9)
    for dx in (-0.32, 0.32):
        for dy in (-0.32, 0.32):
            cyl("tleg", (tc[0] + dx, tc[1] + dy, 0.24), 0.03, 0.48, leg, 12)
    mug = pbr("mug", (0.95, 0.95, 0.95), rough=0.3); mugr = pbr("mug_red", (0.85, 0.1, 0.1), rough=0.3)
    cyl("mug", (tc[0] + 0.12, tc[1] - 0.05, 0.62), 0.08, 0.18, mug, 24)
    cyl("mug_band", (tc[0] + 0.12, tc[1] - 0.05, 0.64), 0.082, 0.04, mugr, 24)
    cyl("coffee", (tc[0] + 0.12, tc[1] - 0.05, 0.71), 0.07, 0.01, flat("coffee", (0.18, 0.09, 0.04)), 24)
    return {"anchors": {"table": list(tc)}, "parts": {"table_top": top}}
