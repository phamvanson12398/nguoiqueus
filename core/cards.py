"""On-screen cards parented to the camera (independent of lens, like captions):
title cards ("10 MINUTES EARLIER", "TEST 1"), labels ("30 IN"), red ✗ / green ✓ stamps,
thought bubbles, and an iris-out that closes to black.

Screen coordinates: pos = (x, y) with x, y in -1..1 (left..right, bottom..top of the 9:16 frame).
At the captions depth the visible frame is 36/28 units tall whatever the lens (the root is pushed
back by lens/28), so one screen unit = HALF_H vertically, HALF_W horizontally.
"""
import math
import bpy
from . import ctx, geo
from .geo import empty, shape, stroke, ellipse, rrect
from .look import flat
from .timing import ease, ease_out_back

HALF_H = 36 / 28 / 2            # 0.643: half the visible height at depth lens/28 (9:16; 16:9 -> ctx.frame_half())
HALF_W = HALF_H * 9 / 16
STYLES = ("title", "label", "stamp_x", "stamp_check", "bubble", "iris", "fade", "chapter", "screen")
# key-moment text screens (long-form): big text height + colour of the big text per variant
SCREEN = {"year": (0.17, None), "number": (0.15, None), "question": (0.085, (1, 1, 1)), "quote": (0.07, (1, 1, 1)),
          "name": (0.095, (1, 1, 1)), "place": (0.11, (1, 1, 1)), "fact": (0.08, (1, 1, 1))}
DEFAULT_COLOR = {"title": (0.98, 0.30, 0.02), "label": (1.0, 0.85, 0.1), "stamp_x": (0.9, 0.1, 0.08),
                 "stamp_check": (0.1, 0.75, 0.25), "bubble": (0.98, 0.98, 0.97), "iris": (0.0, 0.0, 0.0),
                 "fade": (0.0, 0.0, 0.0), "chapter": (0.80, 0.62, 0.30), "screen": (1.0, 0.80, 0.18)}


def _alpha_mat(name, rgb):
    """emission colour with a keyable opacity (node 'Mix Shader' factor 0 = invisible, 1 = solid)"""
    m = bpy.data.materials.new(name); m.use_nodes = True
    try: m.surface_render_method = 'BLENDED'
    except Exception: pass
    nt = m.node_tree; nt.nodes.clear()
    e = nt.nodes.new("ShaderNodeEmission"); e.inputs[0].default_value = (*rgb, 1)
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mx = nt.nodes.new("ShaderNodeMixShader"); mx.inputs[0].default_value = 0.0
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(e.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], o.inputs[0])
    return m, mx.inputs[0]


def _text(parent, name, body, size, rgb, z, outline=True):
    font = bpy.data.fonts.load(ctx.FONT_PATH, check_existing=True) if ctx.FONT_PATH else None
    layers = ((geo.INK, size * 0.11, z - 0.002), (flat(f"card_txt{tuple(round(c, 3) for c in rgb)}", rgb), 0.0, z)) if outline \
        else ((flat(f"card_txt{tuple(round(c, 3) for c in rgb)}", rgb), 0.0, z),)
    objs = []
    for i, (m, off, zz) in enumerate(layers):
        cu = bpy.data.curves.new(f"{name}_t{i}", 'FONT'); cu.body = body
        if font: cu.font = font
        cu.size = size; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.offset = off
        o = bpy.data.objects.new(f"{name}_t{i}", cu); ctx.col.objects.link(o); o.parent = parent; o.location = (0, 0, zz)
        o.data.materials.append(m); objs.append(o)
    return objs


def _text_width(body, size):
    return max(len(l) for l in body.split("\n")) * size * 0.56


def build_card(root, i, c):
    style = c.get("style", "title")
    default = {"title": 0.075, "label": 0.06, "bubble": 0.065, "chapter": 0.07}.get(style, 0.16)
    if style == "screen":
        default = SCREEN.get(c.get("variant", "fact"), SCREEN["fact"])[0]
        if c.get("variant") == "quote" and c.get("text") and not c["text"].startswith(("“", '"')): c["text"] = "“" + c["text"] + "”"
    size = c.get("size") or default
    if size > 0.3:                    # written as a multiplier ("1.3x") instead of a height: treat it as one
        print(f"WARN card {i}: size {size} looks like a multiplier, using {round(default * size, 3)}")
        size = default * size
    body_ = c.get("text", "")
    if style in ("title", "label", "bubble", "chapter", "screen") and body_:     # fit the frame width: wrap to 2 lines, then shrink
        extra = {"title": 1.2, "label": 0.2, "bubble": 2.2, "chapter": 1.0, "screen": 1.6}[style]
        maxw = 1.9 * HALF_W
        if _text_width(body_, size) + size * extra > maxw and "\n" not in body_ and " " in body_:
            words = body_.split(" "); best = None
            for k in range(1, len(words)):
                a, b = " ".join(words[:k]), " ".join(words[k:])
                if best is None or max(len(a), len(b)) < max(len(x) for x in best): best = (a, b)
            body_ = "\n".join(best); c["text"] = body_
        need = _text_width(body_, size) + size * extra
        if need > maxw: size *= maxw / need
    rgb = tuple(c.get("color") or DEFAULT_COLOR[style]); body = c.get("text", "")   # (may have been wrapped above)
    x, y = c.get("pos") or ((0, 0.55) if style == "title" else (0, -0.6) if style == "iris" else (0, 0))
    if style == "fade": x, y = 0, 0
    h = empty(f"card{i}", root, (x * HALF_W, y * HALF_H, -0.02 - 0.0005 * i))
    h.rotation_euler = (0, 0, math.radians(c.get("rot", 0)))
    if style == "title":
        w = _text_width(body, size) + size * 1.2; hh = size * (1.6 + 1.1 * body.count("\n"))
        shape(h, f"card{i}_bg", rrect(0, 0, w, hh, size * 0.25), flat(f"card_bg{rgb}", rgb), -0.006, outline=0.012)
        _text(h, f"card{i}", body, size, (1, 1, 1), 0.0)
    elif style == "label":
        _text(h, f"card{i}", body, size, rgb, 0.0)
    elif style in ("stamp_x", "stamp_check"):
        m = flat(f"card_stamp{rgb}", rgb); s = size
        pts = [[(-s, -s), (s, s)], [(-s, s), (s, -s)]] if style == "stamp_x" else [[(-s, 0), (-s * 0.3, -s * 0.7), (s, s * 0.8)]]
        for k, p in enumerate(pts):
            # strokes are tubes (radius = width/2): keep the coloured one fully in front of the white rim
            stroke(h, f"card{i}_w{k}", p, s * 0.55, -s * 0.6, m=flat("card_white", (1, 1, 1)))
            stroke(h, f"card{i}_s{k}", p, s * 0.36, 0.0, m=m)
        if body: _text(h, f"card{i}", body, s * 0.45, (1, 1, 1), s * 0.25)
    elif style == "bubble":
        w = max(_text_width(body, size) + size * 2.2, size * 5); hh = size * (3.0 + 1.1 * body.count("\n"))
        m = flat(f"card_bubble{rgb}", rgb)
        blobs = [(dx * w * 0.6, dy * hh, w * 0.5 * r, hh * 0.55 * r) for dx, dy, r in
                 ((0, 0, 1.0), (-0.55, -0.15, 0.62), (0.55, -0.12, 0.66), (-0.25, 0.32, 0.6), (0.3, 0.3, 0.62))]
        dots = [(dx * w, dy * hh, r, r) for dx, dy, r in ((-0.35, -0.75, size * 0.7), (-0.5, -1.05, size * 0.42))]
        ol = size * 0.22
        for k, (cx, cy, rx, ry) in enumerate(blobs + dots):        # ink rims first (behind), then the fills on top
            shape(h, f"card{i}_o{k}", ellipse(cx, cy, rx + ol, ry + ol, 32), geo.INK, -0.012, outline=0)
        for k, (cx, cy, rx, ry) in enumerate(blobs + dots):
            shape(h, f"card{i}_c{k}", ellipse(cx, cy, rx, ry, 32), m, -0.008, outline=0)
        if body: _text(h, f"card{i}", body, size, (0.1, 0.1, 0.12), 0.0, outline=False)
    elif style == "iris":
        # black ring: outer square much bigger than the frame, inner circle = hole (keyed via scale of a pivot)
        R = 4000.0; cu = bpy.data.curves.new(f"card{i}_iris", 'CURVE'); cu.dimensions = '2D'; cu.fill_mode = 'BOTH'
        for pts in ([(-R, -R), (R, -R), (R, R), (-R, R)], ellipse(0, 0, 1.0, 1.0, 64)):
            sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
            for p, (px, py) in zip(sp.points, pts): p.co = (px, py, 0, 1)
            sp.use_cyclic_u = True
        o = bpy.data.objects.new(f"card{i}_iris", cu); ctx.col.objects.link(o); o.parent = h; o.location = (0, 0, 0.01)
        o.data.materials.append(flat("card_iris", rgb))
        c["_iris"] = o
    elif style == "screen":
        # dark see-through plate (the blurred scene shows behind), accent sub line, big text, caption, accent rule
        var = c.get("variant", "fact")
        m, fac = _alpha_mat(f"card{i}_plate", (0.02, 0.02, 0.03))
        shape(h, f"card{i}_plate", rrect(0, 0, HALF_W * 2.4, HALF_H * 2.4, 0.001), m, -0.01, outline=0)
        c["_fade"] = fac
        inner = empty(f"card{i}_in", h); c["_inner"] = inner
        big_rgb = SCREEN.get(var, SCREEN["fact"])[1] or rgb
        nl = body.count("\n")
        if c.get("sub"): _text(inner, f"card{i}_sub", c["sub"], max(0.032, size * 0.32), rgb, 0.0, outline=False)[0].location.y = size * (0.95 + 0.55 * nl)
        if body: _text(inner, f"card{i}", body, size, big_rgb, 0.0)
        cap = c.get("caption")
        yb = -size * (0.85 + 0.55 * nl)
        if cap: _text(inner, f"card{i}_cap", cap, max(0.03, min(0.05, size * 0.4)), (0.92, 0.92, 0.9), 0.0, outline=False)[0].location.y = yb - 0.02
        wl = min(_text_width(body or "x", size) * 0.45, HALF_W * 0.8)
        shape(inner, f"card{i}_line", rrect(0, yb + (0.035 if cap else 0.0) + size * 0.1, wl, max(0.004, size * 0.05), 0.0005),
              flat(f"card_line{rgb}", rgb), 0.0, outline=0)
    elif style in ("fade", "chapter"):
        # full-frame plate whose opacity is keyed; 'chapter' = dark plate + chapter label (small, colour) + title (big, white)
        m, fac = _alpha_mat(f"card{i}_plate", (0.0, 0.0, 0.0) if style == "chapter" else rgb)
        shape(h, f"card{i}_plate", rrect(0, 0, HALF_W * 2.4, HALF_H * 2.4, 0.001), m, -0.01, outline=0)
        c["_fade"] = fac
        if style == "chapter":
            sub = c.get("sub") or ""
            if sub: _text(h, f"card{i}_sub", sub, size * 0.55, rgb, 0.0, outline=False)[0].location.y = size * 1.25
            if body: _text(h, f"card{i}", body, size, (1, 1, 1), 0.0, outline=False)
            ln = flat(f"card_line{rgb}", rgb); wl = min(_text_width(body or "x", size) * 0.6, HALF_W)
            shape(h, f"card{i}_line", rrect(0, -size * 0.95, wl, size * 0.06, 0.0005), ln, 0.0, outline=0)
    h.scale = (0, 0, 0)
    return h


def bake_card(h, c):
    """pop in (5 f, overshoot) with a small wobble, hold, pop out (3 f); iris closes from big to 0 and stays black"""
    N = ctx.N; a, b = int(c["from"]), int(c["to"]); style = c.get("style", "title")
    h.scale = (0, 0, 0); h.keyframe_insert("scale", frame=1)
    if style == "iris":
        o = c["_iris"]
        x, y = c.get("pos") or (0, -0.6)
        r0 = max(math.hypot(HALF_W * (sx - x), HALF_H * (sy - y)) for sx in (-1, 1) for sy in (-1, 1)) * 1.05   # hole just covers the frame
        for f in range(max(1, a - 1), N + 1):
            u = ease((f - a) / max(1, b - a)) if f >= a else 0.0
            r = r0 * (1 - u) + 0.002          # R * 0.002 = 8 units: the black square still covers the whole frame
            s = 1.0 if f >= a else 0.0
            h.scale = (s, s, s); h.keyframe_insert("scale", frame=f)
            o.scale = (r, r, 1); o.keyframe_insert("scale", frame=f)
        return
    if style == "screen":
        # plate fades in 6 f to opacity (default 0.86); text pops in, then grows slowly (never still); out in 6 f
        fac = c["_fade"]; inner = c["_inner"]; top = float(c.get("opacity", 0.86))
        inner.scale = (0, 0, 0); inner.keyframe_insert("scale", frame=1)
        for f in range(max(1, a - 1), min(N, b + 1) + 1):
            if f < a or f > b: u = 0.0
            elif f < a + 6: u = ease((f - a) / 6)
            elif f > b - 6: u = ease((b - f) / 6)
            else: u = 1.0
            fac.default_value = top * u; fac.keyframe_insert("default_value", frame=f)
            h.scale = (1, 1, 1) if a <= f <= b else (0, 0, 0); h.keyframe_insert("scale", frame=f)
            if f < a or f > b: si = 0.0
            elif f < a + 7: si = ease_out_back((f - a) / 7, 1.6)
            elif f > b - 4: si = ease((b - f) / 4) * (1 + 0.05 * (f - a) / max(1, b - a))
            else: si = 1 + 0.05 * (f - a) / max(1, b - a)
            inner.scale = (si, si, si); inner.keyframe_insert("scale", frame=f)
        return
    if style in ("fade", "chapter"):
        # fade: opacity 0 -> 1 over 'in' frames (default to-from), hold, 1 -> 0 over 'out' frames if given
        # chapter: plate 0.94 opaque; plate + text fade in 8 f, hold, fade out 8 f
        fac = c["_fade"]; fin = int(c.get("in", (b - a) if style == "fade" else 8)); fout = int(c.get("out", 0 if style == "fade" else 8))
        top = 1.0 if style == "fade" else float(c.get("opacity", 0.94))
        for f in range(max(1, a - 1), min(N, b + 1) + 1):
            if f < a or f > b: u = 0.0
            elif f < a + fin: u = ease((f - a) / max(1, fin))
            elif fout and f > b - fout: u = ease((b - f) / max(1, fout))
            else: u = 1.0
            if style == "fade" and not fout and f > b: u = 1.0 if c.get("hold", False) else 0.0
            fac.default_value = top * u; fac.keyframe_insert("default_value", frame=f)
            s = 1.0 if (a <= f <= b or (u > 0)) else 0.0
            if style == "chapter" and a <= f <= b: s = 0.96 + 0.04 * u      # text eases in with a tiny grow
            h.scale = (s, s, s); h.keyframe_insert("scale", frame=f)
        return
    base = h.rotation_euler[2]
    for f in range(max(2, a - 1), min(N, b + 1) + 1):
        if f < a or f > b: s = 0.0
        elif f > b - 3: s = ease((b + 1 - f) / 3)
        else: s = ease_out_back((f - a) / 5, 2.0)
        h.scale = (s, s, s); h.keyframe_insert("scale", frame=f)
        wob = 0.08 * math.sin((f - a) * 2.0) * (1 - (f - a) / 10) if a <= f < a + 10 and style != "iris" else 0.0
        h.rotation_euler = (0, 0, base + wob); h.keyframe_insert("rotation_euler", frame=f)


def build_cards(cards, lens_by_frame, ref_lens=28.0):
    """root under the camera at the captions depth; returns root (add its descendants to NOLINE)"""
    global HALF_W, HALF_H
    if not cards: return None
    if ctx.ASPECT != "9:16": HALF_W, HALF_H = ctx.frame_half()    # 9:16 keeps the original constants bit for bit
    root = empty("cards", ctx.cam, (0, 0, -1.0))
    for f in range(1, ctx.N + 1):
        k = lens_by_frame[f] / ref_lens
        root.location = (0, 0, -1.0 * k)          # no scale: at depth lens/28 the frame is always 2*HALF_H tall
        root.keyframe_insert("location", frame=f)
    for i, c in enumerate(cards):
        c = dict(c)
        bake_card(build_card(root, i, c), c)
    return root
