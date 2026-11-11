"""2D characters on camera-facing planes: builder, IK posing with follow-through,
squash/stretch reactions, expressions with blinks, lip flap, walk cycle, hand props."""
import math
from . import ctx, geo, faces
from .geo import empty, shape, stroke, ellipse, rrect, limb, billboard_root, set_visible, vis_track
from .look import flat
from .timing import ease, ease_out_elastic, noise1


class Char:
    pass


# ---------------- IK ----------------
def ik(sh, tgt, L1, L2, bend=1):
    dx, dy = tgt[0] - sh[0], tgt[1] - sh[1]
    d = max(min(math.hypot(dx, dy), L1 + L2 - 1e-3), abs(L1 - L2) + 1e-3)
    base = math.atan2(dx, -dy)
    off = math.acos(max(-1, min(1, (L1 * L1 + d * d - L2 * L2) / (2 * L1 * d))))
    a1 = base + bend * off
    ex, ey_ = sh[0] + L1 * math.sin(a1), sh[1] - L1 * math.cos(a1)
    a_abs = math.atan2(tgt[0] - ex, -(tgt[1] - ey_))
    return a1, a_abs - a1


# ---------------- builder ----------------
def make_char(name, loc, cfg):
    """cfg: leg (hipY, L1, L2), torso (w, h, color), arm (shY, shX, L1, L2), head (y, r), skin, extras(fn), faces"""
    c = Char(); c.name = name
    c.root, c.plane = billboard_root(name, loc)
    c.body = empty(name + "_body", c.plane)
    hipY, lL1, lL2 = cfg["leg"]
    c.legL = limb(c.body, name + "_legL", (-0.15, hipY), lL1, lL2, 0.065, 0.05, "shoe")
    c.legR = limb(c.body, name + "_legR", (0.15, hipY), lL1, lL2, 0.065, 0.05, "shoe")
    c.torso = empty(name + "_torso", c.body, (0, hipY - 0.04, 0))
    tw, th, tcol = cfg["torso"]
    shape(c.torso, name + "_shirt", rrect(0, th / 2, tw, th, 0.3 if tw < 0.9 else 0.32), tcol, 0.12)
    shX, shY, aL1, aL2 = cfg["arm"]
    c.sh = {"L": (-shX, shY), "R": (shX, shY)}; c.aL = (aL1, aL2)
    c.armL = limb(c.torso, name + "_armL", (-shX, shY), aL1, aL2, 0.05, 0.30, "hand")
    c.armR = limb(c.torso, name + "_armR", (shX, shY), aL1, aL2, 0.05, 0.30, "hand")
    stroke(c.torso, name + "_neck", [(0, th - 0.04), (0, th + 0.08)], 0.06, 0.1)
    hy, hr = cfg["head"]
    c.head = empty(name + "_head", c.torso, (0, hy, 0.36))
    c.skin = flat(name + "_skin", (0.98, 0.98, 0.97))
    shape(c.head, name + "_face", ellipse(0, 0, hr, hr * 0.97, 48), c.skin, 0.0)
    cfg["extras"](c)
    c.F, c.blink = faces.build_faces(c.head, name, c.skin, cfg["faces"], ey=cfg.get("eye_y", -0.02))
    c.hist = {}; c.expr_table = []
    return c


# ---------------- reactions baked into the body (squash & stretch) ----------------
def react_offsets(c, f):
    """returns (dy, sy, lean) for hop / flinch / shiver / proud reactions registered in c.reacts"""
    dy, sy, lean = 0.0, 1.0, 0.0
    for t0, kind in getattr(c, "reacts", []):
        if kind == "hop" and t0 - 4 <= f <= t0 + 16:
            if f < t0:                                       # anticipation: crouch
                sy -= 0.10 * ease((f - (t0 - 4)) / 4)
            else:
                u = (f - t0) / 16
                dy += 0.22 * math.sin(math.pi * min(1, u / 0.8)) if u < 0.8 else 0.0
                if u < 0.25: sy += 0.12 * (1 - u / 0.25)     # stretch on take-off
                elif u > 0.8: sy -= 0.12 * math.sin(math.pi * (u - 0.8) / 0.2)   # squash on landing
        elif kind == "flinch" and t0 <= f <= t0 + 20:
            u = (f - t0) / 20; lean += -0.18 * (1 - ease_out_elastic(u)); sy -= 0.05 * (1 - ease(u))
        elif kind == "shiver" and t0 <= f <= t0 + 30:
            lean += 0.04 * math.sin(f * 2.4) * (1 - (f - t0) / 30)
        elif kind == "proud" and t0 <= f <= t0 + 14:
            u = (f - t0) / 14; sy += 0.07 * math.sin(math.pi * u); dy += 0.04 * math.sin(math.pi * u)
    return dy, sy, lean


# ---------------- posing ----------------
def pose_char(c, f, armL=None, armR=None, legL=(-0.06, 0.02), legR=(0.06, -0.02), head_tilt=0.0, body=(0, 0), breath=True, lean=0.0):
    """arm specs: ('ang', a1, a2) or ('ik', (x, y), bend) in torso coords.
    V2: forearms drag behind fast upper-arm moves (follow-through), reactions add squash/stretch, head lags the body."""
    if not hasattr(c, "prev"): c.prev = {}; c.vel = {}
    for side, spec, lp in (("L", armL, c.armL), ("R", armR, c.armR)):
        if spec is None: spec = ('ang', -0.25 if side == "L" else 0.25, 0.1 if side == "L" else -0.1)
        if spec[0] == 'ik':
            a1, a2 = ik(c.sh[side], spec[1], c.aL[0], c.aL[1], spec[2])
        else:
            a1, a2 = spec[1], spec[2]
        v = a1 - c.prev.get(side, a1); c.vel[side] = 0.55 * c.vel.get(side, 0.0) + 0.45 * v; c.prev[side] = a1
        a2 = a2 - max(-0.5, min(0.5, 1.6 * c.vel[side]))            # forearm drags behind
        lp[0].rotation_euler = (0, 0, a1); lp[1].rotation_euler = (0, 0, a2)
        lp[0].keyframe_insert("rotation_euler", frame=f); lp[1].keyframe_insert("rotation_euler", frame=f)
        c.hist.setdefault(side, []).append((f, a1 + 0.5 * a2))
    for spec, lp in ((legL, c.legL), (legR, c.legR)):
        lp[0].rotation_euler = (0, 0, spec[0]); lp[1].rotation_euler = (0, 0, spec[1])
        lp[0].keyframe_insert("rotation_euler", frame=f); lp[1].keyframe_insert("rotation_euler", frame=f)
    t = f / ctx.FPS
    dy, sy, rlean = react_offsets(c, f)
    b = (1 + (0.014 * math.sin(t * 2.4 + len(c.name)) if breath else 0)) * sy
    sway = 0.02 * noise1(t * 0.8, len(c.name))                      # idle weight shift
    c.body.scale = (1 / math.sqrt(b), b, 1); c.body.location = (body[0], body[1] + dy, 0)
    c.body.rotation_euler = (0, 0, lean + rlean + sway)
    c.body.keyframe_insert("scale", frame=f); c.body.keyframe_insert("location", frame=f); c.body.keyframe_insert("rotation_euler", frame=f)
    lag = getattr(c, "lag_tilt", 0.0)
    c.lag_tilt = lag + 0.35 * (-(lean + rlean) * 0.6 - lag)                # head follows the lean a few frames late
    talk = getattr(c, "amp_now", 0.0)
    c.head.rotation_euler = (0, 0, head_tilt + 0.03 * math.sin(t * 1.7) + c.lag_tilt + 0.05 * talk * math.sin(f * 0.9))
    c.head.location = (0, c.head.location[1], c.head.location[2]); c.head.keyframe_insert("rotation_euler", frame=f)


def walk_legs(ph, amp=0.42):
    s = math.sin(ph)
    return ((amp * s, amp * s - 0.7 * max(0.0, math.sin(ph + 1.9))),
            (-amp * s, -amp * s - 0.7 * max(0.0, math.sin(ph + 1.9 + math.pi))))


# ---------------- expressions ----------------
def expr_at(table, f):
    cur = table[0][1]
    for t_, e_ in table:
        if f >= t_: cur = e_
    return cur


def apply_expressions(c, blinks=()):
    for f in range(1, ctx.N + 1):
        for kind, g in c.F.items():
            vis = expr_at(c.expr_table, f) == kind
            if f == 1 or vis != (expr_at(c.expr_table, f - 1) == kind):
                set_visible(g, f, vis)
        bl = any(b_ <= f < b_ + 4 for b_ in blinks)
        for e_ in c.blink:
            e_.scale = (e_.scale[0], 0.012 if bl else 0.085, 1); e_.keyframe_insert("scale", frame=f)


# ---------------- talking mouth (lip flap from the voice) ----------------
def add_talk_mouth(c, ey=-0.02):
    g = empty(c.name + "_talk", c.head, (0, 0, 0.14))
    shape(g, c.name + "_talk_patch", ellipse(0, ey - 0.17, 0.22, 0.12, 24), c.skin, 0, outline=0)
    piv = empty(c.name + "_talk_piv", g, (0, ey - 0.17, 0.02))
    shape(piv, c.name + "_talk_m", ellipse(0, 0, 0.12, 0.10, 24), faces.MOUTH, 0, outline=0.03)
    shape(piv, c.name + "_talk_t", ellipse(0, -0.05, 0.06, 0.035, 16), faces.TONGUE, 0.02, outline=0)
    shape(piv, c.name + "_talk_teeth", rrect(0, 0.065, 0.14, 0.035, 0.01), faces.TEETH, 0.02, outline=0)
    c.talk = g; c.talk_piv = piv


def bake_talk(c, ranges, amp):
    vis_track(c.talk, ranges)
    for f in range(1, ctx.N + 1):
        on = any(a <= f <= b for a, b in ranges)
        o = 0.18 + 0.82 * amp[f] if on else 0.2
        c.talk_piv.scale = (0.9 + 0.15 * o, o, 1); c.talk_piv.keyframe_insert("scale", frame=f)


# ---------------- 2D hand props (child of the torso so they stay upright) ----------------
def prop_round(parent, name, r=0.42):
    g = empty(name, parent)
    shape(g, name + "_b", ellipse(0, 0, r, r, 40), flat("iron2d", (0.20, 0.20, 0.22)), 0.0, outline=0.035)
    for k in (0.72, 0.45, 0.2):
        stroke(g, f"{name}_r{k}", ellipse(0, 0, r * k, r * k, 32) + [ellipse(0, 0, r * k, r * k, 32)[0]], 0.022, 0.03, m=flat("iron2d_l", (0.36, 0.36, 0.38)))
    return g


def prop_square(parent, name, s=0.76):
    g = empty(name, parent)
    shape(g, name + "_b", rrect(0, 0, s, s, 0.04), flat("iron2d", (0.20, 0.20, 0.22)), 0.0, outline=0.035)
    for k in (-0.2, 0.0, 0.2):
        stroke(g, f"{name}_v{k}", [(k * s * 1.4, -s * 0.38), (k * s * 1.4, s * 0.38)], 0.022, 0.03, m=flat("iron2d_l", (0.36, 0.36, 0.38)))
        stroke(g, f"{name}_h{k}", [(-s * 0.38, k * s * 1.4), (s * 0.38, k * s * 1.4)], 0.022, 0.03, m=flat("iron2d_l", (0.36, 0.36, 0.38)))
    return g
