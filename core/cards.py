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

HALF_H = 36 / 28 / 2            # 0.643: half the visible height at depth lens/28
HALF_W = HALF_H * 9 / 16
STYLES = ("title", "label", "stamp_x", "stamp_check", "bubble", "iris")
DEFAULT_COLOR = {"title": (0.98, 0.30, 0.02), "label": (1.0, 0.85, 0.1), "stamp_x": (0.9, 0.1, 0.08),
                 "stamp_check": (0.1, 0.75, 0.25), "bubble": (0.98, 0.98, 0.97), "iris": (0.0, 0.0, 0.0)}


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
    default = {"title": 0.075, "label": 0.06, "bubble": 0.065}.get(style, 0.16)
    size = c.get("size") or default
    if size > 0.3:                    # written as a multiplier ("1.3x") instead of a height: treat it as one
        print(f"WARN card {i}: size {size} looks like a multiplier, using {round(default * size, 3)}")
        size = default * size
    body_ = c.get("text", "")
    if style in ("title", "label", "bubble") and body_:     # shrink to fit the frame width (9:16)
        extra = {"title": 1.2, "label": 0.2, "bubble": 2.2}[style]
        need = _text_width(body_, size) + size * extra
        if need > 1.9 * HALF_W: size *= 1.9 * HALF_W / need
    rgb = tuple(c.get("color") or DEFAULT_COLOR[style]); body = c.get("text", "")
    x, y = c.get("pos") or ((0, 0.55) if style == "title" else (0, -0.6) if style == "iris" else (0, 0))
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
    if not cards: return None
    root = empty("cards", ctx.cam, (0, 0, -1.0))
    for f in range(1, ctx.N + 1):
        k = lens_by_frame[f] / ref_lens
        root.location = (0, 0, -1.0 * k)          # no scale: at depth lens/28 the frame is always 2*HALF_H tall
        root.keyframe_insert("location", frame=f)
    for i, c in enumerate(cards):
        c = dict(c)
        bake_card(build_card(root, i, c), c)
    return root
