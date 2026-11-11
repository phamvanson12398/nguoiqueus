"""A sheet of paper on a desk, seen from above (shot type 'diagram' with height 'top', or 'board'), on which a
cartoon hand with a pencil draws the explanation: strokes and circles that draw themselves, arrows, shaded areas
that fade in, handwritten labels that pop in.  Paper: grid, lined, blank or blueprint.
Sheet coordinates: x right, y up, in sheet units (default 14 x 8), centred on `origin`."""
import math
from core import ctx, geo, maps
from core.look import flat
from core.timing import ease

DEFAULTS = dict(origin=[1100.0, 0.0, 0.0], size=[14.0, 8.0], paper="grid", strokes=[], circles=[], arrows=[],
                fills=[], labels=[], hand=True)
PAPERS = {"grid": ((0.93, 0.92, 0.86), (0.88, 0.87, 0.80), (0.55, 0.70, 0.85)), "lined": ((0.93, 0.92, 0.86), (0.88, 0.87, 0.80), (0.55, 0.65, 0.85)),
          "blank": ((0.93, 0.91, 0.84), (0.87, 0.85, 0.78), None), "blueprint": ((0.05, 0.20, 0.45), (0.04, 0.16, 0.38), (0.35, 0.55, 0.85))}
INKS = {"ink": (0.05, 0.05, 0.08), "red": (0.75, 0.06, 0.04), "blue": (0.04, 0.18, 0.65), "green": (0.05, 0.45, 0.12),
        "white": (0.95, 0.95, 0.92), "orange": (0.98, 0.30, 0.02)}


def _rgb(c, default):
    if isinstance(c, str): return INKS.get(c, INKS["ink"])
    return tuple(c) if c else default


def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    ox, oy, oz = (list(p["origin"]) + [0.0])[:3]
    W, H = p["size"]; N = ctx.N
    root = geo.empty("paper_root", None, (ox, oy, oz))
    c0, c1, lines = PAPERS.get(p["paper"], PAPERS["grid"])
    default_ink = INKS["white"] if p["paper"] == "blueprint" else INKS["ink"]
    maps.poly(root, "paper_desk", geo.rrect(0, 0, W * 6, H * 6, 0.1), maps.paper_mat("paper_desk", (0.30, 0.17, 0.08), (0.40, 0.24, 0.12), 1.2), -0.02)
    maps.poly(root, "paper_shadow", geo.rrect(0.12, -0.12, W, H, 0.05), flat("paper_shadow", (0.12, 0.07, 0.03)), -0.01)
    maps.poly(root, "paper_sheet", geo.rrect(0, 0, W, H, 0.05), maps.paper_mat(f"paper_{p['paper']}", c0, c1, 3.0), 0.0)
    if lines:
        lm = flat(f"paper_lines_{p['paper']}", lines)
        if p["paper"] in ("grid", "blueprint"):
            step = 0.5
            for i in range(1, int(W / step)):
                maps.line(root, f"paper_gx{i}", [(-W / 2 + i * step, -H / 2 + 0.05), (-W / 2 + i * step, H / 2 - 0.05)], 0.008, 0.001, lm)
            for j in range(1, int(H / step)):
                maps.line(root, f"paper_gy{j}", [(-W / 2 + 0.05, -H / 2 + j * step), (W / 2 - 0.05, -H / 2 + j * step)], 0.008, 0.001, lm)
        else:
            for j in range(1, int(H / 0.6)):
                maps.line(root, f"paper_ly{j}", [(-W / 2 + 0.05, -H / 2 + j * 0.6), (W / 2 - 0.05, -H / 2 + j * 0.6)], 0.01, 0.001, lm)
            maps.line(root, "paper_margin", [(-W / 2 + 1.2, -H / 2 + 0.05), (-W / 2 + 1.2, H / 2 - 0.05)], 0.014, 0.0012, flat("paper_margin", (0.85, 0.3, 0.3)))
    tips = []                                  # (a, b, pts) of everything that is drawn, for the hand
    for k, fl in enumerate(p["fills"]):
        mat, fac = maps.fade_mat(f"paper_fill{k}", _rgb(fl.get("color"), (0.98, 0.80, 0.20)), fl.get("opacity", 0.5))
        maps.poly(root, f"paper_fill{k}", [tuple(q) for q in fl["poly"]], mat, 0.002)
        if "from" in fl: maps.fade_between(fac, int(fl["from"]), fl.get("to"), fl.get("opacity", 0.5))
    strokes = list(p["strokes"])
    for c in p["circles"]:
        r = c.get("r", 1.0); x, y = c["at"]
        strokes.append(dict(c, path=[(x + r * math.cos(t), y + r * math.sin(t)) for t in [math.pi / 2 + 2 * math.pi * i / 48 for i in range(49)]], smooth=False))
    for k, st in enumerate(strokes):
        pts = [tuple(q) for q in st["path"]]
        if st.get("smooth", True) and len(pts) > 2: pts = maps.smooth(pts)
        o = maps.line(root, f"paper_stroke{k}", pts, st.get("width", 0.07), 0.004 + 0.0002 * k, flat(f"paper_ink{_rgb(st.get('color'), default_ink)}", _rgb(st.get("color"), default_ink)))
        if "from" in st:
            a, b = int(st["from"]), int(st.get("to", int(st["from"]) + 20)); maps.draw_on([o[0].data], a, b); tips.append((a, b, pts))
    for k, ar in enumerate(p["arrows"]):
        pts = [tuple(q) for q in ar["path"]]
        maps.arrow(root, f"paper_arrow{k}", pts, ar.get("width", 0.08), 0.006 + 0.0003 * k, _rgb(ar.get("color"), INKS["red"]),
                   int(ar["from"]) if "from" in ar else None, int(ar.get("to", ar.get("from", 1) + 20)), ink_w=0.0001)
        if "from" in ar: tips.append((int(ar["from"]), int(ar.get("to", int(ar["from"]) + 20)), maps.smooth(pts) if len(pts) > 2 else pts))
    anchors = {"center": [ox, oy, oz]}
    for k, lb in enumerate(p["labels"]):
        rgb = _rgb(lb.get("color"), default_ink)
        objs = maps.label(root, f"paper_lbl{k}", lb["text"], lb["at"], lb.get("size", 0.42), flat(f"paper_ink{rgb}", rgb), 0.008,
                          kind="italic", rot=lb.get("rot", 0))
        if "from" in lb:
            a = int(lb["from"])
            for o in objs: maps.show_between(o, a, lb.get("to"))
            n = max(1, len(lb["text"])); tips.append((a - min(18, 2 * n), a, [(lb["at"][0] - 0.25 * n * lb.get("size", 0.42) * 0.55, lb["at"][1]),
                                                                            (lb["at"][0] + 0.25 * n * lb.get("size", 0.42) * 0.55, lb["at"][1])]))
        anchors["label_" + maps.keyname(lb["text"])[:24]] = [ox + lb["at"][0], oy + lb["at"][1], oz]
    if p["hand"] and tips:
        tips.sort()
        hand = geo.empty("paper_hand", root, (W * 0.6, -H * 0.6, 0.35)); hs = p.get("hand_scale", 1.8); hand.scale = (hs, hs, hs)
        pencil = geo.empty("paper_pencil", hand, (0, 0, 0)); pencil.rotation_euler = (0, 0, math.radians(-35))
        L = 1.6; w = 0.16
        maps.poly(pencil, "paper_pen_body", [(0.18, -w / 2), (L, -w / 2), (L, w / 2), (0.18, w / 2)], flat("paper_pen", (0.98, 0.72, 0.05)), 0.02, outline=0.03)
        maps.poly(pencil, "paper_pen_wood", [(0.0, 0.0), (0.18, -w / 2), (0.18, w / 2)], flat("paper_pen_wood", (0.92, 0.75, 0.55)), 0.021, outline=0.03)
        maps.poly(pencil, "paper_pen_tip", [(0.0, 0.0), (0.06, -0.02), (0.06, 0.02)], flat("paper_pen_tip", (0.1, 0.1, 0.1)), 0.022)
        maps.poly(pencil, "paper_pen_eraser", [(L, -w / 2), (L + 0.18, -w / 2), (L + 0.18, w / 2), (L, w / 2)], flat("paper_pen_eraser", (0.95, 0.45, 0.55)), 0.02, outline=0.03)
        skin = flat("paper_hand", (0.98, 0.98, 0.97)); sleeve = flat("paper_sleeve", (0.03, 0.22, 0.55))
        # cartoon glove hand gripping the pencil near the tip: sleeve, palm, three curled fingers, thumb on top
        maps.poly(hand, "paper_hand_sleeve", geo.rrect(1.25, -0.95, 0.75, 0.55, 0.12), sleeve, 0.025, outline=0.04)
        maps.poly(hand, "paper_hand_palm", geo.ellipse(0.78, -0.55, 0.42, 0.36, 28), skin, 0.03, outline=0.04)
        for i, (fx, fy) in enumerate(((0.30, -0.42), (0.38, -0.62), (0.52, -0.80))):
            maps.poly(hand, f"paper_hand_f{i}", geo.ellipse(fx, fy, 0.16, 0.11, 18), skin, 0.032 + 0.001 * i, outline=0.035)
        maps.poly(hand, "paper_hand_thumb", geo.ellipse(0.42, -0.10, 0.20, 0.11, 20), skin, 0.04, outline=0.035)
        rest = (W * 0.62, -H * 0.62)
        cum = {i: maps.path_len(t[2]) for i, t in enumerate(tips)}
        last = rest
        for f in range(1, N + 1, 2):
            act = next((i for i, t in enumerate(tips) if t[0] <= f <= t[1]), None)
            if act is not None:
                a, b, pts = tips[act]; u = ease((f - a) / max(1, b - a)); (x, y), _ = maps.point_at(pts, cum[act], u); last = (x, y); zz = 0.25
            else:
                nxt = next((t for t in tips if t[0] > f), None)
                if nxt and nxt[0] - f < 20:               # glide to the next start
                    u = ease(1 - (nxt[0] - f) / 20); tx, ty = nxt[2][0]
                    x, y = last[0] + (tx - last[0]) * u, last[1] + (ty - last[1]) * u; zz = 0.25 + 0.35 * math.sin(math.pi * u)
                elif any(t[1] < f for t in tips) and not nxt:   # done: drift away
                    u = min(1.0, (f - max(t[1] for t in tips)) / 30); x, y = last[0] + (rest[0] - last[0]) * ease(u), last[1] + (rest[1] - last[1]) * ease(u); zz = 0.4
                else:
                    x, y = last; zz = 0.3
            hand.location = (x, y, zz + 0.01 * math.sin(f * 0.9)); hand.keyframe_insert("location", frame=f)
    return {"parts": {"root": root}, "anchors": anchors, "noline": [root]}
