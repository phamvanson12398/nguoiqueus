"""2D explainer: a slice of toast spinning off a table edge (diagram on diagram_board 'plane').
Origin = empty on the floor line right below the table edge; x right, y up, z toward camera.
Parts: <name>_toast (pivot at slice centre, track it from (0, table_h+0.04) to (land_x, 0.05) + rot z),
       <name>_ghosts (faded slices along the parabola), <name>_arc (dashed spin arc), <name>_mark (big X / check)."""
import math
from core.look import flat
from core.geo import empty, shape, stroke, rrect, arrow2d, label

DEFAULTS = dict(table_h=1.2, turns=0.5, ghosts=4, mark="x", height_label="30 IN", land_x=0.0,
                table_color=[0.42, 0.2, 0.06], accent=[0.03, 0.22, 0.55])

TW, TH = 0.4, 0.07          # toast silhouette
BUTTER_H = 0.024            # butter strip on the top edge


def _rot(pts, a, cx=0.0, cy=0.0):
    c, s = math.cos(a), math.sin(a)
    return [(cx + x * c - y * s, cy + x * s + y * c) for x, y in pts]


def _slice(parent, nm, cx, cy, ang, bread, butter, z, ol):
    """toast slice centred at (cx, cy), rotated ang; butter on local +y edge"""
    body = rrect(0, 0, TW, TH, 0.018, 4)
    but = rrect(0, TH / 2 - BUTTER_H / 2, TW - 0.03, BUTTER_H, 0.01, 3)
    shape(parent, nm + "_b", _rot(body, ang, cx, cy), bread, z, outline=ol)
    shape(parent, nm + "_y", _rot(but, ang, cx, cy), butter, z + 0.01, outline=0)


def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    name = p["name"]
    H = float(p["table_h"]); turns = float(p["turns"])
    LX = float(p["land_x"]) or (0.6 if turns >= 0.75 else 0.45)
    big = H > 2.0
    k = 1.0 + 0.6 * min(1.0, max(0.0, (H - 1.2) / 2.84))     # line/label scale for the tall version
    lw = 0.05 * k

    ink = flat("diagram_toast_spin_ink", (0.02, 0.02, 0.025))
    wood = flat("diagram_toast_spin_table", tuple(p["table_color"]))
    bread = flat("diagram_toast_spin_bread", (0.78, 0.42, 0.10))
    butter = flat("diagram_toast_spin_butter", (0.98, 0.78, 0.05))
    g_bread = flat("diagram_toast_spin_ghost", (0.88, 0.78, 0.62))
    g_butter = flat("diagram_toast_spin_ghost_butter", (0.97, 0.90, 0.55))
    accent = flat("diagram_toast_spin_accent", tuple(p["accent"]))
    red = flat("diagram_toast_spin_red", (0.85, 0.08, 0.06))
    green = flat("diagram_toast_spin_green", (0.05, 0.6, 0.18))

    g = empty(name, p.get("parent"))

    # floor line (~1.8 long, slightly past the landing spot)
    stroke(g, f"{name}_floor", [(-0.95, 0), (LX + 0.35, 0)], lw * 1.2, 0.0, m=ink)

    # table: top slab + two legs, edge at (0, H)
    slab = 0.12 * k; leg = 0.09 * k
    shape(g, f"{name}_tabletop", rrect(-0.45, H - slab / 2, 0.9, slab, 0.02), wood, 0.0, outline=0.035 * k)
    for i, x in enumerate((-0.82, -0.08)):
        shape(g, f"{name}_leg{i}", rrect(x, (H - slab) / 2, leg, H - slab, 0.01), wood, -0.01, outline=0.035 * k)

    # height arrow + label (left of the table)
    ax = -1.12
    arrow2d(g, f"{name}_harrow", (ax, 0.02), (ax, H), 0.05 * k, accent)
    lsz = 0.22 * k
    label(g, f"{name}_hlabel", str(p["height_label"]), (ax - 0.22 - 0.55 * lsz * 1.4, H / 2), lsz, accent)

    def path(u):
        return LX * u, H * (1 - u * u), -math.pi * turns * u

    # ghosts along the parabola (u in (0, 1), endpoints excluded: real toast sits there)
    gh = empty(f"{name}_ghosts", g, (0, 0, 0.02))
    n = max(0, int(p["ghosts"]))
    for i in range(n):
        u = (i + 1) / (n + 1)
        x, y, a = path(u)
        _slice(gh, f"{name}_gh{i}", x, y, a, g_bread, g_butter, 0.0, 0.02 * k)

    # dashed spin arc around the upper part of the fall (kept clear of the mark), clockwise, with arrow head
    arcg = empty(f"{name}_arc", g, (0, 0, 0.06))
    mx, my, _ = path(0.4)
    r = (0.42 if big else 0.3) * (1.0 + 0.3 * (k - 1))
    cx, cy = mx + 0.08, my
    sweep = min(320.0, 180.0 * turns / 0.5 * (1 if turns < 0.75 else 0.89))
    a0 = 100.0; a1 = a0 - sweep
    ndash = max(5, int(sweep / 26))
    for i in range(ndash):
        t0 = a0 + (a1 - a0) * (i / ndash); t1 = a0 + (a1 - a0) * ((i + 0.55) / ndash)
        seg = [(cx + r * math.cos(math.radians(t0 + (t1 - t0) * j / 4)),
                cy + r * math.sin(math.radians(t0 + (t1 - t0) * j / 4))) for j in range(5)]
        stroke(arcg, f"{name}_arc_d{i}", seg, lw, 0.0, m=accent)
    ea = math.radians(a1)
    tip = (cx + r * math.cos(ea), cy + r * math.sin(ea))
    tx, ty = math.sin(ea), -math.cos(ea)               # clockwise tangent
    nx, ny = math.cos(ea), math.sin(ea)
    hl = 0.16 * k
    head = [(tip[0] + tx * hl * 0.6, tip[1] + ty * hl * 0.6),
            (tip[0] - tx * hl * 0.6 + nx * hl * 0.6, tip[1] - ty * hl * 0.6 + ny * hl * 0.6),
            (tip[0] - tx * hl * 0.6 - nx * hl * 0.6, tip[1] - ty * hl * 0.6 - ny * hl * 0.6)]
    shape(arcg, f"{name}_arc_head", head, accent, 0.0, outline=0)

    # big mark on the floor at the landing spot; coloured core sits clearly in front of its ink tube
    mk = empty(f"{name}_mark", g, (LX, 0.0, 0.12))
    s = 0.22 * k; base = 0.12 + s
    ow, cw = 0.15 * k, 0.095 * k
    cz = ow / 2 + 0.01                                   # core in front of the whole ink tube
    if p["mark"] == "check":
        pts = [(-s, base), (-s * 0.25, base - s * 0.8), (s * 1.05, base + s * 0.95)]
        stroke(mk, f"{name}_mark_ol", pts, ow, 0.0, m=ink)
        stroke(mk, f"{name}_mark_c", pts, cw, cz, m=green)
    else:
        for j, (p0, p1) in enumerate((((-s, base - s), (s, base + s)), ((-s, base + s), (s, base - s)))):
            stroke(mk, f"{name}_mark_ol{j}", [p0, p1], ow, 0.0, m=ink)
            stroke(mk, f"{name}_mark_x{j}", [p0, p1], cw, cz, m=red)

    # the real toast: pivot at slice centre, starts on the table edge, butter up
    toast = empty(f"{name}_toast", g, (0.0, H + 0.04, 0.24))
    _slice(toast, f"{name}_tst", 0.0, 0.0, 0.0, bread, butter, 0.0, 0.03)
    return g
