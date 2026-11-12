"""Tactical sand table seen from above (shot type 'board', height 'top' or 'high').

A wooden table with a terrain board (grass / sand / earth / snow): hills, rivers, forests, roads, walls/camps,
plus army units as coloured 3D blocks (optionally split into a grid of small blocks = a formation) with a banner,
that slide along keyed paths, and march arrows painted on the ground that draw themselves.
Board coordinates: x right, y up (north), units of the board itself (default 16 x 9), centred on `origin`.
Colours come from story `factions` ("faction": "<id>") or "color"."""
import math, random
from core import ctx, geo, maps
from core.look import flat, pbr

DEFAULTS = dict(origin=[900.0, 0.0, 0.0], size=[16.0, 9.0], ground="grass", grid=False,
                hills=[], rivers=[], forests=[], roads=[], walls=[], units=[], arrows=[], labels=[])
GROUNDS = {"grass": ((0.20, 0.36, 0.10), (0.30, 0.45, 0.14)), "sand": ((0.72, 0.58, 0.34), (0.82, 0.68, 0.42)),
           "earth": ((0.36, 0.24, 0.12), (0.48, 0.33, 0.17)), "snow": ((0.80, 0.84, 0.88), (0.92, 0.94, 0.96))}


def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    fac = maps.factions_of(p); rnd = random.Random(p.get("seed", 3))
    ox, oy, oz = (list(p["origin"]) + [0.0])[:3]
    W, H = p["size"]
    root = geo.empty("board_root", None, (ox, oy, oz))
    world = lambda xy, z=0.0: [ox + xy[0], oy + xy[1], oz + z]
    # table: dark wood frame around the terrain
    wood = pbr("board_wood", (0.30, 0.16, 0.07), rough=0.6)
    geo.rbox("board_table", (ox, oy, oz - 0.25), (W + 1.2, H + 1.2, 0.5), wood, radius=0.08)
    geo.cube("board_floor", (ox, oy, oz - 1.2), (W * 20, H * 20, 0.1), pbr("board_floor", (0.10, 0.07, 0.05), rough=0.9))
    g0, g1 = GROUNDS.get(p["ground"], GROUNDS["grass"])
    gm = maps.paper_mat(f"board_ground_{p['ground']}", g0, g1, 2.2)
    maps.poly(root, "board_ground", [(-W / 2, -H / 2), (W / 2, -H / 2), (W / 2, H / 2), (-W / 2, H / 2)], gm, 0.002)
    if p["grid"]:
        gl = flat("board_grid", tuple(c * 0.75 for c in g0))
        for i in range(1, int(W)):
            maps.line(root, f"board_gx{i}", [(-W / 2 + i, -H / 2), (-W / 2 + i, H / 2)], 0.012, 0.004, gl)
        for j in range(1, int(H)):
            maps.line(root, f"board_gy{j}", [(-W / 2, -H / 2 + j), (W / 2, -H / 2 + j)], 0.012, 0.004, gl)
    hillm = pbr(f"board_hill_{p['ground']}", tuple(c * 1.1 for c in g1), rough=0.95)
    for k, h in enumerate(p["hills"]):
        r = h.get("r", 1.2); ht = h.get("h", 0.35)
        o = geo.sphere(f"board_hill{k}", tuple(world(h["at"], 0.0)), r, hillm, scale=(1.0, h.get("stretch", 0.8), ht / r))
        if h.get("label"): maps.label(root, f"board_hill{k}_lbl", h["label"], (h["at"][0], h["at"][1] - r * 0.9), 0.28, flat("board_lbl", (0.95, 0.93, 0.85)), ht + 0.02)
    water = flat("board_water", (0.12, 0.38, 0.62)); waterR = flat("board_bank", (0.30, 0.25, 0.14))
    for k, rv in enumerate(p["rivers"]):
        pts = maps.smooth(rv["path"]); w = rv.get("width", 0.45)
        maps.line(root, f"board_bank{k}", pts, w * 1.35, 0.003, waterR); maps.line(root, f"board_river{k}", pts, w, 0.004 + w * 0.2, water)
    roadm = flat("board_road", (0.62, 0.52, 0.36))
    for k, rd in enumerate(p["roads"]):
        maps.line(root, f"board_road{k}", maps.smooth(rd["path"]) if len(rd["path"]) > 2 else rd["path"], rd.get("width", 0.22), 0.0035, roadm)
    leaf = pbr("board_tree", (0.08, 0.26, 0.07), rough=0.9); trunk = pbr("board_trunk", (0.25, 0.15, 0.07))
    for k, fo in enumerate(p["forests"]):
        n = fo.get("n", 9); r = fo.get("r", 1.0)
        for i in range(n):
            a = rnd.uniform(0, 2 * math.pi); d = r * math.sqrt(rnd.random())
            x, y = fo["at"][0] + d * math.cos(a), fo["at"][1] + d * math.sin(a); s = rnd.uniform(0.18, 0.28)
            geo.cone(f"board_tree{k}_{i}", tuple(world((x, y), s * 1.4)), s, 0.0, s * 2.6, leaf, verts=10)
            geo.cyl(f"board_trunk{k}_{i}", tuple(world((x, y), s * 0.15)), s * 0.18, s * 0.35, trunk, 8)
    wallm = pbr("board_wall", (0.62, 0.58, 0.52), rough=0.8)
    for k, wl in enumerate(p["walls"]):
        pts = wl["path"]
        for i in range(len(pts) - 1):
            (x0, y0), (x1, y1) = pts[i], pts[i + 1]; L = math.dist((x0, y0), (x1, y1))
            o = geo.rbox(f"board_wall{k}_{i}", tuple(world(((x0 + x1) / 2, (y0 + y1) / 2), wl.get("h", 0.3) / 2)), (L, wl.get("t", 0.16), wl.get("h", 0.3)), wallm, radius=0.02)
            o.rotation_euler = (0, 0, math.atan2(y1 - y0, x1 - x0))
    anchors = {"center": [ox, oy, oz]}
    parts = {"root": root}
    ink = flat("board_ink", (0.06, 0.05, 0.04))
    uroot = geo.empty("board_units", None, (ox, oy, oz))          # not in noline: the 3D blocks get ink outlines
    for k, u in enumerate(p["units"]):
        rgb = maps.faction_rgb(u, fac); uid = str(u.get("id", f"u{k}"))
        w, d = u.get("size", [1.6, 0.7]); rows, cols = u.get("rows", 1), u.get("cols", 1)
        g = geo.empty(f"board_unit_{uid}", uroot, (u["at"][0], u["at"][1], 0.0))
        g.rotation_euler = (0, 0, math.radians(u.get("rot", 0)))
        body = pbr(f"board_unit{tuple(round(c, 3) for c in rgb)}", rgb, rough=0.55)
        hgt = u.get("h", 0.22)
        if rows * cols == 1:
            b = geo.rbox(f"board_unit{k}_b", (0, 0, hgt / 2), (w, d, hgt), body, radius=0.04); b.parent = g
        else:                                          # formation: grid of small blocks with gaps
            bw, bd = w / cols, d / rows
            for i in range(rows):
                for j in range(cols):
                    b = geo.rbox(f"board_unit{k}_{i}_{j}", (-w / 2 + bw * (j + 0.5), -d / 2 + bd * (i + 0.5), hgt / 2), (bw * 0.8, bd * 0.8, hgt), body, radius=0.02)
                    b.parent = g
        pole = geo.cyl(f"board_unit{k}_pole", (-w / 2 + 0.08, d / 2 - 0.05, hgt + 0.22), 0.015, 0.44, ink, 8); pole.parent = g
        flag = geo.rbox(f"board_unit{k}_flag", (-w / 2 + 0.08 + 0.13, d / 2 - 0.05, hgt + 0.36), (0.24, 0.015, 0.15), body, radius=0.008); flag.parent = g
        if u.get("label"):
            maps.label(g, f"board_unit{k}_lbl", u["label"], (0, -d / 2 - 0.3), 0.26, flat("board_lbl", (0.95, 0.93, 0.85)), 0.01, outline_m=ink)
        if u.get("moves"): maps.move_keys(g, u["moves"], maps.Flat(W, H), 0.0)
        if "from" in u: maps.show_between(g, int(u["from"]), u.get("to"))
        parts[uid] = g; anchors["unit_" + maps.keyname(uid)] = world(u["at"])
    for k, ar in enumerate(p["arrows"]):
        rgb = maps.faction_rgb(ar, fac)
        maps.arrow(root, f"board_arrow{k}", [tuple(q) for q in ar["path"]], ar.get("width", 0.22), 0.006 + k * 0.0005, rgb,
                   int(ar["from"]) if "from" in ar else None, int(ar.get("to", ar.get("from", 1) + 45)), smooth_path=ar.get("smooth", True))
        anchors[f"arrow{k}_end"] = world(ar["path"][-1]); anchors[f"arrow{k}_start"] = world(ar["path"][0])
        _pts = [tuple(q) for q in ar["path"]]; anchors[f"arrow{k}_mid"] = world(maps.point_at(_pts, maps.path_len(_pts), 0.5)[0])
    for k, lb in enumerate(p["labels"]):
        objs = maps.label(root, f"board_lbl{k}", lb["text"], lb["at"], lb.get("size", 0.35), flat("board_lbl", (0.95, 0.93, 0.85)), 0.012,
                          rot=lb.get("rot", 0), outline_m=ink)
        if "from" in lb:
            for o in objs: maps.show_between(o, int(lb["from"]), lb.get("to"))
    flat_noline = [root]
    return {"parts": parts, "anchors": anchors, "noline": flat_noline}
