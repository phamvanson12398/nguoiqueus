"""Word-by-word captions parented to the camera: grouping, highlight colours,
comic burst behind impact words, pop-in with wobble, lens-compensated distance."""
import math
import random
import re
import bpy
from . import ctx, geo
from .geo import empty, shape
from .look import flat
from .timing import ease_out_back, fcurves_of


def clean(w): return w.replace('"', '').replace('“', '').replace('”', '')


def group_words(WORDS, HIGHLIGHT):
    """merge a short word with the next one (<= 11 chars) unless it ends a phrase or the next is highlighted"""
    groups = []; i = 0
    while i < len(WORDS):
        t0, w = WORDS[i]; txt = clean(w); j = i + 1
        if j < len(WORDS) and len(re.sub(r"\W", "", txt)) <= 3 and not txt.endswith((".", ",", "?")) and len(txt + WORDS[j][1]) <= 11 \
                and re.sub(r"\W", "", WORDS[j][1]).lower() not in HIGHLIGHT:
            txt = txt + " " + clean(WORDS[j][1]); j += 1
        groups.append([t0, txt]); i = j
    return groups


def make_caps(WORDS, HIGHLIGHT, impact=("clang",)):
    """-> [(text, a, b[, rgb, size_mult])]: impact words orange + '!', highlight words yellow, upper case"""
    FPS = ctx.FPS
    groups = group_words(WORDS, HIGHLIGHT)
    CAPS = []
    for k, (t0, txt) in enumerate(groups):
        a = int(t0 * FPS) + 1
        b = (int(groups[k + 1][0] * FPS)) if k + 1 < len(groups) else a + 25
        b = max(b, a + 5); b = min(b, a + 40)
        key = re.sub(r"[^a-z]", "", txt.split()[-1].lower())
        if key in impact: CAPS.append((txt.upper().replace(".", "!"), a, b, (1.0, 0.55, 0.1), 1.7))
        elif key in HIGHLIGHT: CAPS.append((txt.upper(), a, b, (1.0, 0.85, 0.1), 1.3))
        else: CAPS.append((txt, a, b))
    return CAPS


def build_captions(CAPS, lens_by_frame, lift_ranges=(), y=-0.12, y_lift=-0.55, cap_d=1.0, ref_lens=28.0, burst_word="CLANG"):
    """caption root under the camera; lift_ranges = frames where captions move up (e.g. over a diagram)."""
    N = ctx.N
    CAP_D = cap_d
    font = bpy.data.fonts.load(ctx.FONT_PATH, check_existing=True) if ctx.FONT_PATH else None
    cap_root = empty("captions", ctx.cam, (0, y, -CAP_D))
    for f in range(1, N + 1):
        in_dg = any(a <= f <= b for a, b in lift_ranges)
        k_ = lens_by_frame[f] / ref_lens
        d_ = 1.0
        cap_root.location = (0, (y_lift if in_dg else y) * k_ * d_, -CAP_D * k_ * d_)
        cap_root.scale = (d_, d_, d_)
        cap_root.keyframe_insert("location", frame=f); cap_root.keyframe_insert("scale", frame=f)
    for i, c in enumerate(CAPS):
        txt, a, b = c[0], c[1], c[2]
        rgb = c[3] if len(c) > 3 else (1, 1, 1); size = 0.085 * (c[4] if len(c) > 4 else 1.0)
        holder = empty(f"cap{i}", cap_root)
        for layer, (m, off, z) in enumerate(((geo.INK, size * 0.11, -0.002), (flat(f"capc{rgb}", rgb), 0.0, 0.0))):
            cu = bpy.data.curves.new(f"cap{i}_{layer}", 'FONT'); cu.body = txt
            if font: cu.font = font
            cu.size = size; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.offset = off
            o = bpy.data.objects.new(f"cap{i}_{layer}", cu); ctx.col.objects.link(o)
            o.parent = holder; o.location = (0, 0, z); o.data.materials.append(m)
        if burst_word and burst_word in txt:                          # comic burst behind the impact word
            burst = empty(f"cap{i}_burst", holder, (0, 0, -0.006))
            pts = [((0.22 if k % 2 == 0 else 0.16) * math.cos(2 * math.pi * k / 18) * (1.0 + 0.12 * ((k * 7) % 3)),
                    (0.12 if k % 2 == 0 else 0.08) * math.sin(2 * math.pi * k / 18) * (1.0 + 0.12 * ((k * 5) % 3))) for k in range(18)]
            shape(burst, f"cap{i}_bst", pts, flat("burst_fill", (1.0, 0.82, 0.12)), 0, outline=0.012)
            burst2 = empty(f"cap{i}_burst2", holder, (0, 0, -0.008))
            shape(burst2, f"cap{i}_bst2", [(x * 1.18, y_ * 1.25) for x, y_ in pts], flat("burst_back", (0.92, 0.25, 0.08)), 0, outline=0.012)
        rnd_ = random.Random(i * 31)
        base_rot = rnd_.uniform(-0.06, 0.06) if len(c) > 3 else rnd_.uniform(-0.025, 0.025)
        holder.scale = (0, 0, 0); holder.keyframe_insert("scale", frame=1)
        for f in range(max(2, a - 1), min(N, b + 1) + 1):
            if f < a or f > b:
                s_ = 0.0; r_ = base_rot
            else:
                s_ = ease_out_back((f - a) / 5, 2.2)
                r_ = base_rot + (0.10 * math.sin((f - a) * 2.2) * (1 - (f - a) / 9) if len(c) > 3 and f - a < 9 else 0.0)
            holder.scale = (s_, s_, s_); holder.keyframe_insert("scale", frame=f)
            holder.rotation_euler = (0, 0, r_); holder.keyframe_insert("rotation_euler", frame=f)
    return cap_root


# =====================================================================
#  long-form subtitles (16:9): phrase lines at the bottom, no pop
# =====================================================================
def phrase_lines(WORDS, max_chars=42, max_sec=4.0):
    """[(t0, t1_or_None, text)]: break after . ? ! , ; : or when the line would pass max_chars / max_sec"""
    lines = []; cur = []; t0 = None
    for k, (t, w) in enumerate(WORDS):
        w = clean(w)
        if cur and (len(" ".join(cur + [w])) > max_chars or t - t0 > max_sec):
            lines.append([t0, t, " ".join(cur)]); cur = []
        if not cur: t0 = t
        cur.append(w)
        if w.endswith((".", "?", "!", ";", ":")) or (w.endswith(",") and len(" ".join(cur)) > max_chars * 0.5):
            nxt = WORDS[k + 1][0] if k + 1 < len(WORDS) else t + 1.5
            lines.append([t0, nxt, " ".join(cur)]); cur = []
    if cur: lines.append([t0, cur and WORDS[-1][0] + 1.5, " ".join(cur)])
    return lines


def build_subtitles(WORDS, lens_by_frame, y=-0.80, size=0.034, ref_lens=28.0, max_hold=4.5):
    """bottom subtitle lines under the camera (white, thin ink rim).  y in screen units (-1 bottom .. 1 top)."""
    N, FPS = ctx.N, ctx.FPS
    hw, hh = ctx.frame_half()
    font = bpy.data.fonts.load(ctx.FONT_PATH, check_existing=True) if ctx.FONT_PATH else None
    root = empty("captions", ctx.cam, (0, y * hh, -1.0))
    for f in range(1, N + 1):                 # at depth lens/28 the frame is always 2*hh tall: only the depth follows the lens
        k_ = lens_by_frame[f] / ref_lens
        root.location = (0, y * hh, -1.0 * k_); root.keyframe_insert("location", frame=f)
    white = flat("sub_white", (0.97, 0.97, 0.95))
    spans = []
    for t0, t1, txt in phrase_lines(WORDS):
        a = int(t0 * FPS) + 1; b = min(int(t1 * FPS), a + int(max_hold * FPS)) if t1 else a + 45
        spans.append([a, max(b, a + 12), txt])
    for k in range(len(spans) - 1):                       # never two lines at once: a line ends before the next starts
        spans[k][1] = min(spans[k][1], spans[k + 1][0] - 1)
    for i, (a, b, txt) in enumerate(spans):
        if b < a: continue
        holder = empty(f"sub{i}", root)
        for layer, (m, off, z) in enumerate(((geo.INK, size * 0.09, -0.002), (white, 0.0, 0.0))):
            cu = bpy.data.curves.new(f"sub{i}_{layer}", 'FONT'); cu.body = txt
            if font: cu.font = font
            cu.size = size; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'
            if layer == 0:        # rim = a round tube along the glyph edges (offset rims grew miter spikes at sharp corners)
                cu.bevel_depth = off; cu.bevel_resolution = 3
                z = -(off + 0.002)    # the tube is `off` thick towards the camera too: keep it behind the white text
            else:
                cu.offset = off
            o = bpy.data.objects.new(f"sub{i}_{layer}", cu); ctx.col.objects.link(o)
            o.parent = holder; o.location = (0, 0, z); o.data.materials.append(m)
        holder.scale = (0, 0, 0); holder.keyframe_insert("scale", frame=1)
        for f in (a - 1, a, b, b + 1):
            if 1 <= f <= N:
                s_ = 1.0 if a <= f <= b else 0.0
                holder.scale = (s_, s_, s_); holder.keyframe_insert("scale", frame=f)
        for fc in fcurves_of(holder):
            for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT'
    return root
