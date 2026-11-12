"""Parchment map lying on a dark table, seen from above (shot type 'map', height 'top').

Real coastlines, lakes and rivers (Natural Earth) for any lon/lat window, plus story data drawn on top:
cities, coloured territories that fade in, march arrows that draw themselves, moving army tokens,
mountain glyphs, sea/region labels, a title cartouche and a compass rose.  Colours can come from
story `factions` (pass "faction": "<id>").  Everything is flat colour (no sky tint), outlines are ink lines."""
import math
from core import ctx, geo, maps
from core.look import flat

DEFAULTS = dict(origin=[700.0, 0.0, 0.0], bounds=[6.0, 36.5, 19.5, 47.2], width=16.0, style="parchment",
                rivers=True, lakes=True, cities=[], regions=[], arrows=[], units=[], labels=[], mountains=[],
                title=None, compass=True)
STYLES = {   # paper (two tones), sea, land, coast ink, river, text ink
    "parchment": dict(paper=((0.80, 0.64, 0.40), (0.70, 0.52, 0.30)), sea=(0.56, 0.55, 0.42), land=(0.86, 0.72, 0.46),
                      land2=(0.78, 0.63, 0.38), coast=(0.20, 0.12, 0.06), river=(0.22, 0.30, 0.34), ink=(0.16, 0.09, 0.04)),
    "modern": dict(paper=((0.62, 0.78, 0.88), (0.55, 0.72, 0.84)), sea=(0.45, 0.66, 0.82), land=(0.93, 0.90, 0.80),
                   land2=(0.86, 0.83, 0.72), coast=(0.25, 0.35, 0.45), river=(0.30, 0.52, 0.75), ink=(0.12, 0.14, 0.18)),
}


def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    S = STYLES.get(p["style"], STYLES["parchment"]); fac = maps.factions_of(p)
    ox, oy, oz = (list(p["origin"]) + [0.0])[:3]
    pr = maps.Proj(p["bounds"], p["width"]); W, H = pr.W, pr.H
    root = geo.empty("map_root", None, (ox, oy, oz))
    x0, y0, x1, y1 = -W / 2, -H / 2, W / 2, H / 2
    eps = W / 900.0
    # table + paper sheet with an ink frame
    geo.shape(root, "map_table", geo.rrect(0, 0, W * 8, H * 8, 0.2), maps.paper_mat("map_table", (0.12, 0.07, 0.04), (0.20, 0.12, 0.07), 1.5), -0.03, outline=0)
    pad = W * 0.035
    maps.poly(root, "map_paper", geo.rrect(0, 0, W + 2 * pad, H + 2 * pad, pad * 0.4), maps.paper_mat(f"map_paper_{p['style']}", *S["paper"], 2.5), -0.02)
    maps.poly(root, "map_sea", [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], maps.paper_mat(f"map_sea_{p['style']}", S["sea"], tuple(c * 0.92 for c in S["sea"]), 3.0), -0.01)
    ink = flat(f"map_ink_{p['style']}", S["ink"]); coast = flat(f"map_coast_{p['style']}", S["coast"])
    for k, w in ((0, W / 260), (1, W / 700)):
        e = pad * (0.55 if k == 0 else 0.25)
        maps.line(root, f"map_frame{k}", [(x0 - e, y0 - e), (x1 + e, y0 - e), (x1 + e, y1 + e), (x0 - e, y1 + e)], w, 0.02, ink, cyclic=True)
    lon0, lat0, lon1, lat1 = p["bounds"]
    m = 2.0
    inbox = lambda b: not (b[2] < lon0 - m or b[0] > lon1 + m or b[3] < lat0 - m or b[1] > lat1 + m)
    landm = maps.paper_mat(f"map_land_{p['style']}", S["land"], S["land2"], 3.5)
    n = 0
    for it in maps.geo_data("land"):
        if not inbox(it["b"]): continue
        pts = maps.clip_poly(pr.pts(it["c"]), x0, y0, x1, y1)
        if len(pts) < 3: continue
        pts = maps.simplify(pts, eps)
        if len(pts) < 3: continue
        maps.poly(root, f"map_land{n}", pts, landm, 0.0)
        for r_i, run in enumerate(maps.clip_line(maps.simplify(pr.pts(it["c"] + it["c"][:1]), eps), x0 + 1e-4, y0 + 1e-4, x1 - 1e-4, y1 - 1e-4)):
            maps.line(root, f"map_coast{n}_{r_i}", run, W / 420, 0.004, coast)
        n += 1
    if p["lakes"]:
        lake = flat(f"map_lake_{p['style']}", S["sea"])
        for k, it in enumerate(x for x in maps.geo_data("lakes") if inbox(x["b"])):
            pts = maps.clip_poly(pr.pts(it["c"]), x0, y0, x1, y1)
            if len(pts) >= 3: maps.poly(root, f"map_lake{k}", maps.simplify(pts, eps), lake, 0.003, outline=W / 600, ink=coast)
    if p["rivers"]:
        names = None if p["rivers"] is True else {x.lower() for x in p["rivers"]}
        riv = flat(f"map_river_{p['style']}", S["river"])
        for k, it in enumerate(x for x in maps.geo_data("rivers") if inbox(x["b"])):
            if names is not None and it["n"].lower() not in names: continue
            for r_i, run in enumerate(maps.clip_line(pr.pts(it["c"]), x0, y0, x1, y1)):
                maps.line(root, f"map_river{k}_{r_i}", maps.simplify(run, eps), W / 500, 0.005, riv)
    anchors = {"center": [ox, oy, oz]}
    world = lambda xy: [ox + xy[0], oy + xy[1], oz]
    # territories (fade in), drawn under rivers/coast so the coast still reads
    for k, rg in enumerate(p["regions"]):
        rgb = maps.faction_rgb(rg, fac)
        mat, f_ = maps.fade_mat(f"map_region{k}", rgb, rg.get("opacity", 0.45))
        pts = maps.clip_poly(pr.pts(rg["poly"]), x0, y0, x1, y1)
        if len(pts) < 3: continue
        objs = maps.poly(root, f"map_region{k}", pts, mat, 0.0035)
        edge = maps.line(root, f"map_region{k}_edge", pts, W / 380, 0.0036, flat(f"map_edge{k}", tuple(c * 0.6 for c in rgb)), cyclic=True)
        top = rg.get("opacity", 0.45)
        if "from" in rg:
            maps.fade_between(f_, int(rg["from"]), rg.get("to"), top)
            maps.draw_on([edge[0].data], int(rg["from"]), int(rg["from"]) + 20)
        cx = sum(q[0] for q in pts) / len(pts); cy = sum(q[1] for q in pts) / len(pts)
        anchors["region_" + maps.keyname(rg.get("name", str(k)))] = world((cx, cy))
        if rg.get("label") or rg.get("name"):
            lb = maps.label(root, f"map_region{k}_lbl", (rg.get("label") or rg["name"]).upper(), (cx, cy), rg.get("size", W / 45),
                            flat(f"map_rlbl{k}", tuple(c * 0.45 for c in rgb)), 0.013, spacing=1.25)
            if "from" in rg:
                for o in lb: maps.show_between(o, int(rg["from"]) + 6, rg.get("to"))
    for k, mt in enumerate(p["mountains"]):
        pts = [pr(*mt["at"][:2])] if "at" in mt else [pr(*q) for q in mt["line"]]
        if "line" in mt and len(pts) > 1:
            cum = maps.path_len(pts); nn = max(2, int(cum[-1] / (W / 40)))
            pts = [maps.point_at(pts, cum, i / (nn - 1))[0] for i in range(nn)]
        s = mt.get("size", W / 70)
        for i, (x, y) in enumerate(pts):
            x += ((i * 7) % 3 - 1) * s * 0.25; y += ((i * 5) % 3 - 1) * s * 0.2
            maps.line(root, f"map_mtn{k}_{i}", [(x - s, y - s * 0.4), (x, y + s * 0.6), (x + s, y - s * 0.4)], W / 500, 0.007, ink)
            maps.line(root, f"map_mtns{k}_{i}", [(x, y + s * 0.6), (x + s * 0.35, y - s * 0.1)], W / 900, 0.007, ink)
    for k, ar in enumerate(p["arrows"]):
        pts = pr.pts(ar["path"]); rgb = maps.faction_rgb(ar, fac)
        maps.arrow(root, f"map_arrow{k}", pts, ar.get("width", W / 110), 0.010 + k * 0.0004, rgb,
                   int(ar["from"]) if "from" in ar else None, int(ar.get("to", ar.get("from", 1) + 45)), smooth_path=ar.get("smooth", True))
        anchors[f"arrow{k}_start"] = world(pts[0]); anchors[f"arrow{k}_end"] = world(pts[-1])
        anchors[f"arrow{k}_mid"] = world(maps.point_at(pts, maps.path_len(pts), 0.5)[0])
    for k, c in enumerate(p["cities"]):
        x, y = pr(*c["at"][:2]); sz = c.get("size", 1)
        g = geo.empty(f"map_city{k}", root, (x, y, 0.012))
        r = W / 160 * (1 + 0.35 * (sz - 1))
        if sz >= 3:                                   # capital: red star
            star = [((r * 1.5 if i % 2 == 0 else r * 0.6) * math.cos(i * math.pi / 5 + math.pi / 2),
                     (r * 1.5 if i % 2 == 0 else r * 0.6) * math.sin(i * math.pi / 5 + math.pi / 2)) for i in range(10)]
            maps.poly(g, f"map_city{k}_d", star, flat("map_city_red", (0.62, 0.08, 0.05)), 0.0, outline=W / 900, ink=ink)
        else:
            maps.poly(g, f"map_city{k}_d", geo.ellipse(0, 0, r, r, 20), ink, 0.0)
            maps.poly(g, f"map_city{k}_i", geo.ellipse(0, 0, r * 0.5, r * 0.5, 16), flat("map_city_in", S["land"]), 0.0005)
        dx, dy = c.get("label_offset", [0, -1])
        maps.label(g, f"map_city{k}_lbl", c["name"], (dx * r * 3.2, dy * r * 3.0), c.get("label_size", W / 60 * (1 + 0.15 * (sz - 1))), ink, 0.001)
        if "from" in c: maps.show_between(g, int(c["from"]), c.get("to"))
        anchors["city_" + maps.keyname(c["name"])] = world((x, y))
    for k, lb in enumerate(p["labels"]):
        kind = lb.get("kind", "region")
        mat = flat(f"map_lbl_{kind}_{p['style']}", tuple(c * (1.4 if kind == "sea" else 1.0) for c in S["ink"]) if kind != "sea" else tuple(c * 0.55 for c in S["sea"]))
        objs = maps.label(root, f"map_lbl{k}", lb["text"], pr(*lb["at"][:2]), lb.get("size", W / (40 if kind != "sea" else 50)), mat, 0.013,
                          kind="italic" if kind == "sea" else "serif", rot=lb.get("rot", 0), spacing=1.35 if kind in ("sea", "region") else 1.0)
        if "from" in lb:
            for o in objs: maps.show_between(o, int(lb["from"]), lb.get("to"))
    units = {}
    for k, u in enumerate(p["units"]):
        rgb = maps.faction_rgb(u, fac); x, y = pr(*u["at"][:2]); s = u.get("size", W / 55)
        g = geo.empty(f"map_unit_{u.get('id', k)}", root, (x, y, 0.02))
        maps.poly(g, f"map_unit{k}_b", geo.rrect(0, 0, s * 2.2, s * 1.3, s * 0.25), flat(f"map_unitc{rgb}", rgb), 0.0, outline=W / 450, ink=ink)
        maps.line(g, f"map_unit{k}_x1", [(-s * 0.8, -s * 0.45), (s * 0.8, s * 0.45)], W / 700, 0.001, ink)
        maps.line(g, f"map_unit{k}_x2", [(-s * 0.8, s * 0.45), (s * 0.8, -s * 0.45)], W / 700, 0.001, ink)
        if u.get("label"): maps.label(g, f"map_unit{k}_lbl", u["label"], (0, -s * 1.3), s * 0.8, ink, 0.001)
        if u.get("moves"): maps.move_keys(g, u["moves"], pr, 0.02)
        if "from" in u: maps.show_between(g, int(u["from"]), u.get("to"))
        units[u.get("id", f"u{k}")] = g; anchors["unit_" + maps.keyname(str(u.get("id", k)))] = world((x, y))
    if p["title"]:
        tw = min(W * 0.45, len(p["title"]) * W / 75 + W * 0.06); th = W / 22
        cx, cy = x0 + tw / 2 + W * 0.03, y1 - th / 2 - W * 0.03
        maps.poly(root, "map_title_bg", geo.rrect(cx, cy, tw, th, th * 0.2), maps.paper_mat(f"map_paper_{p['style']}", *S["paper"], 2.5), 0.015, outline=W / 450, ink=ink)
        maps.label(root, "map_title", p["title"], (cx, cy), W / 62, ink, 0.016, spacing=1.1)
    if p["compass"]:
        r = W / 30; cx, cy = x1 - r * 1.6, y0 + r * 1.6
        maps.line(root, "map_comp_ring", geo.ellipse(cx, cy, r, r, 48), W / 700, 0.015, ink, cyclic=True)
        for i in range(4):
            a = i * math.pi / 2
            tip = (cx + math.cos(a + math.pi / 2) * r * 1.25, cy + math.sin(a + math.pi / 2) * r * 1.25)
            side1 = (cx + math.cos(a) * r * 0.22, cy + math.sin(a) * r * 0.22); side2 = (cx - math.cos(a) * r * 0.22, cy - math.sin(a) * r * 0.22)
            maps.poly(root, f"map_comp{i}", [tip, side1, (cx, cy), side2], ink if i == 0 else flat("map_comp_l", S["land"]), 0.0155, outline=W / 900, ink=ink)
        maps.label(root, "map_comp_n", "N", (cx, cy + r * 1.6), W / 60, ink, 0.016)
    return {"parts": {"root": root, **units}, "anchors": anchors, "noline": [root],
            "info": {"width": W, "height": H}}
