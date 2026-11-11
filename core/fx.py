"""Comic FX: pooled dust puffs (billboards) and shock lines + red '!' above a character."""
import math
import random
from . import ctx, geo
from .geo import empty, shape, ellipse
from .look import flat
from .timing import ease, ease_out_back

PUFF_M = None
PUFF_POOL = []
PUFF_EVENTS = []


def init():
    global PUFF_M
    PUFF_M = flat("puff_fill", (0.93, 0.90, 0.85))
    PUFF_POOL.clear(); PUFF_EVENTS.clear()


# ---------------- dust puffs (pooled billboards) ----------------
def _make_puff(i):
    root = empty(f"puff_root{i}", None, (0, 0, -20))
    lt = root.constraints.new('LOCKED_TRACK'); lt.target = ctx.cam; lt.track_axis = 'TRACK_NEGATIVE_Y'; lt.lock_axis = 'LOCK_Z'
    pl = empty(f"puff_pl{i}", root); pl.rotation_euler = (math.pi / 2, 0, 0)
    for k, (dx_, dy_, r) in enumerate(((0, 0, 0.12), (0.09, 0.05, 0.09), (-0.08, 0.06, 0.08))):
        shape(pl, f"puff{i}_{k}", ellipse(dx_, dy_, r, r, 18), PUFF_M, 0.01 * k, outline=0.022)
    root.scale = (0, 0, 0)
    return root


def dust_burst(frame, pos, n=8, radius=0.7, size=1.0, life=20, rise=0.35):
    """schedule a ring of dust puffs at a 3D position (impacts, landings, skids)"""
    rnd = random.Random(frame * 7 + int(pos[0] * 13))
    for k in range(n):
        a = 2 * math.pi * k / n + rnd.uniform(-0.3, 0.3)
        PUFF_EVENTS.append((frame + rnd.randint(0, 2), pos, (math.cos(a), math.sin(a)), radius * rnd.uniform(0.7, 1.2),
                            size * rnd.uniform(0.7, 1.3), life + rnd.randint(-3, 4), rise * rnd.uniform(0.6, 1.4)))


def bake_dust():
    N = ctx.N
    if not PUFF_EVENTS: return
    busy = []                                           # (pool index, free_after_frame)
    for ev in sorted(PUFF_EVENTS):
        f0, pos, d, rad, sz, life, rise = ev
        idx = next((i for i, (p, free) in enumerate(busy) if free < f0 - 2), None)
        if idx is None:
            PUFF_POOL.append(_make_puff(len(PUFF_POOL))); busy.append((len(PUFF_POOL) - 1, 0)); idx = len(busy) - 1
        pidx = busy[idx][0]; busy[idx] = (pidx, f0 + life + 1); o = PUFF_POOL[pidx]
        o.scale = (0, 0, 0); o.keyframe_insert("scale", frame=max(1, f0 - 1))
        for f in range(f0, min(N, f0 + life) + 1):
            u = (f - f0) / life; e = ease_out_back(u * 1.6, 1.0) if u < 0.62 else 1.0
            s = sz * (0.35 + 0.9 * e) * (1 - ease((u - 0.55) / 0.45))
            o.location = (pos[0] + d[0] * rad * ease(u * 1.3), pos[1] + d[1] * rad * ease(u * 1.3), pos[2] + 0.08 + rise * ease(u))
            o.scale = (s, s, s); o.keyframe_insert("scale", frame=f); o.keyframe_insert("location", frame=f)
        if f0 + life + 1 <= N:
            o.scale = (0, 0, 0); o.keyframe_insert("scale", frame=f0 + life + 1)


# ---------------- shock lines + "!" above a character ----------------
def add_reaction_fx(c):
    sl = empty(c.name + "_speedlines", c.head, (0, 0, -0.3))
    for k in range(16):
        a = 2 * math.pi * k / 16; r0, r1 = 0.62, 0.95 + 0.12 * (k % 2)
        w_ = 0.035
        p0 = (r0 * math.cos(a), r0 * math.sin(a)); p1 = (r1 * math.cos(a), r1 * math.sin(a))
        nx, ny = -math.sin(a) * w_, math.cos(a) * w_
        shape(sl, f"{c.name}_sl{k}", [(p0[0] + nx * 0.3, p0[1] + ny * 0.3), (p1[0] + nx, p1[1] + ny), (p1[0] - nx, p1[1] - ny), (p0[0] - nx * 0.3, p0[1] - ny * 0.3)],
              geo.INK, 0, outline=0)
    sl.scale = (0, 0, 0); c.speedlines = sl
    ex = empty(c.name + "_excl", c.head, (0.58, 0.62, 0.4))
    for layer, (m, off, z) in enumerate(((geo.INK, 0.05, -0.01), (flat("excl_red", (0.92, 0.1, 0.08)), 0.0, 0.0))):
        geo.text(f"{c.name}_ex{layer}", "!", 0.45, ex, (0, 0, z), m, offset=off, rot=(0, 0, -0.2))
    ex.scale = (0, 0, 0); c.excl = ex


def bake_reaction_fx(c, frames, dur=16):
    N = ctx.N
    for o_ in (c.speedlines, c.excl):
        o_.scale = (0, 0, 0); o_.keyframe_insert("scale", frame=1)
    for f0 in frames:
        for f in range(f0, min(N, f0 + dur) + 1):
            u = (f - f0) / dur
            s_l = ease_out_back(u * 4, 2.0) * (1 - ease((u - 0.6) / 0.4))
            c.speedlines.scale = (s_l, s_l, 1); c.speedlines.rotation_euler = (0, 0, 0.15 * math.sin(f * 1.3))
            s_e = ease_out_back(u * 3, 2.2) * (1 - ease((u - 0.75) / 0.25))
            c.excl.scale = (s_e, s_e, 1); c.excl.location = (0.58, 0.62 + 0.08 * ease(u), 0.4)
            for o_ in (c.speedlines, c.excl):
                o_.keyframe_insert("scale", frame=f)
            c.speedlines.keyframe_insert("rotation_euler", frame=f); c.excl.keyframe_insert("location", frame=f)
        for o_ in (c.speedlines, c.excl):
            o_.scale = (0, 0, 0); o_.keyframe_insert("scale", frame=min(N, f0 + dur + 1))
