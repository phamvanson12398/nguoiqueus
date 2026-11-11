# ---------------- camera v3: smooth one-take rig ----------------
# Replaces the v2 per-shot camera loop (SHOTS + ease + sin shake + ease_out_back punch/whip).
# Idea: a video is a few SEQUENCES (one continuous camera move each, on one set).
# Inside a sequence the camera never stops and never cuts: it glides along a C1 spline
# through key poses. Between sequences there is one motivated TRANSITION.
#
# SEQS = [
#   dict(a=1, b=210, keys=[  # (frame, cam_pos, look_pos, lens, roll_deg)
#        (1,   (-3.0, -1.0, 1.0), (0, 5, 1.4), 28, 0),
#        (90,  (-1.2,  1.5, 1.2), (0, 5, 1.5), 32, 0),
#        (210, ( 1.5,  2.2, 1.6), (0.6, 5.2, 1.6), 34, -4)],
#        follow=None,           # optional: fn(f) -> (x,y,z) subject the eye drifts toward
#        follow_w=0.35,         # 0..1 how much the look point leans toward the subject
#        ease_in=True, ease_out=False),   # ease only at video start/end or before a 'hold'
#   ...]
# TRANS = {cut_frame: ('whip', +1) | ('push',) | ('match',) | ('cut',)}   cut_frame = first frame of next seq
# PUNCH = [(frame, mult, dur, hold)]  smooth zoom in, hold (default 45 f), ease out over 24 f; no overshoot.
#   dur 6-10; a comic 'snap' zoom = dur 3 (max 3 per video)
# SHAKES = [(frame, strength, dur)]  strength 0.5-1.5, dur 8-14 frames

def _lerp(a, b, u): return tuple(a[i] + (b[i] - a[i]) * u for i in range(len(a)))
def smoother(u):                       # C2 ease (smootherstep), no overshoot
    u = max(0.0, min(1.0, u)); return u * u * u * (u * (u * 6 - 15) + 10)

def _hermite(p0, p1, m0, m1, t0, t1, t):
    h = t1 - t0; s = (t - t0) / h
    s2, s3 = s * s, s * s * s
    h00, h10, h01, h11 = 2*s3 - 3*s2 + 1, s3 - 2*s2 + s, -2*s3 + 3*s2, s3 - s2
    return tuple(h00*p0[i] + h10*h*m0[i] + h01*p1[i] + h11*h*m1[i] for i in range(len(p0)))

def spline_track(keys, frames, ease_in, ease_out):
    """keys: [(frame, vec)], returns {f: vec}. C1 Catmull-Rom on non-uniform times."""
    ts = [k[0] for k in keys]; ps = [tuple(k[1]) for k in keys]; n = len(ps); d = len(ps[0])
    if n == 1: return {f: ps[0] for f in frames}
    ms = []
    for i in range(n):
        if i == 0:
            m = (0.0,) * d if ease_in else tuple((ps[1][j] - ps[0][j]) / (ts[1] - ts[0]) for j in range(d))
        elif i == n - 1:
            m = (0.0,) * d if ease_out else tuple((ps[-1][j] - ps[-2][j]) / (ts[-1] - ts[-2]) for j in range(d))
        else:
            m = tuple((ps[i+1][j] - ps[i-1][j]) / (ts[i+1] - ts[i-1]) for j in range(d))
        ms.append(m)
    out = {}
    for f in frames:
        if f <= ts[0]:
            out[f] = tuple(ps[0][j] + ms[0][j] * (f - ts[0]) for j in range(d)); continue
        if f >= ts[-1]:
            out[f] = tuple(ps[-1][j] + ms[-1][j] * (f - ts[-1]) for j in range(d)); continue
        for i in range(n - 1):
            if ts[i] <= f <= ts[i+1]:
                out[f] = _hermite(ps[i], ps[i+1], ms[i], ms[i+1], ts[i], ts[i+1], f); break
    return out

def spring_follow(raw, frames, omega=7.0):
    """Critically damped spring: the eye lags softly behind a moving subject (no snap)."""
    dt = 1.0 / FPS; out = {}; x = list(raw[frames[0]]); v = [0.0] * len(x)
    for f in frames:
        tgt = raw[f]
        for j in range(len(x)):
            a = omega * omega * (tgt[j] - x[j]) - 2 * omega * v[j]
            v[j] += a * dt; x[j] += v[j] * dt
        out[f] = tuple(x)
    return out

def hand_noise(t, seed):              # t in SECONDS, 0.2-0.9 Hz: breathing operator, never per-frame jitter
    return (math.sin(2*math.pi*0.23*t + seed) * 0.55 + math.sin(2*math.pi*0.51*t + seed*1.7) * 0.30
            + math.sin(2*math.pi*0.87*t + seed*2.3) * 0.15)

def shake_at(f, shakes):              # impact shake: 5-9 Hz in seconds, exp decay, returns (dx, dy)
    dx = dy = 0.0
    for (s, k, dur) in shakes:
        if s <= f < s + dur:
            t = (f - s) / FPS; env = k * math.exp(-5.0 * (f - s) / dur) * smoother((f - s + 1) / 2)
            dx += env * (math.sin(2*math.pi*7.1*t) * 0.6 + math.sin(2*math.pi*4.3*t + 1.1) * 0.4)
            dy += env * (math.sin(2*math.pi*8.7*t + 0.5) * 0.6 + math.sin(2*math.pi*5.3*t + 2.0) * 0.4)
    return dx, dy

def solve_camera(SEQS, TRANS, PUNCH=(), SHAKES=(), hand=1.0):
    """Returns {f: (cam_pos, look_pos, lens, roll_rad)} for every frame. Pure python (testable outside Blender)."""
    res = {}
    for si, S in enumerate(SEQS):
        a, b = S["a"], S["b"]; frames = list(range(a, b + 1)); keys = S["keys"]
        ei, eo = S.get("ease_in", si == 0), S.get("ease_out", si == len(SEQS) - 1)
        cp = spline_track([(k[0], k[1]) for k in keys], frames, ei, eo)
        lp = spline_track([(k[0], k[2]) for k in keys], frames, ei, eo)
        ln = spline_track([(k[0], (k[3],)) for k in keys], frames, ei, eo)
        rl = spline_track([(k[0], (k[4] if len(k) > 4 else 0.0,)) for k in keys], frames, ei, eo)
        if S.get("follow"):
            w = S.get("follow_w", 0.35)
            raw = {f: _lerp(lp[f], S["follow"](f), w) for f in frames}
            lp = spring_follow(raw, frames, S.get("omega", 7.0))
        # transitions touching this sequence
        tin = TRANS.get(a); tout = TRANS.get(b + 1)
        for f in frames:
            c = list(cp[f]); l = list(lp[f]); lens = ln[f][0]; roll = math.radians(rl[f][0])
            d = [l[i] - c[i] for i in range(3)]; dist = math.sqrt(sum(x*x for x in d)) or 1.0
            fwd = [x / dist for x in d]
            right = [fwd[1], -fwd[0], 0.0]; rn = math.hypot(right[0], right[1]) or 1.0; right = [x/rn for x in right]
            # whip: same screen direction on both sides of the cut, accelerate out / decelerate in, NO bounce
            if tout and tout[0] == "whip" and f > b - 6:
                u = (f - (b - 6)) / 6.0; off = tout[1] * 1.1 * dist * u ** 3
                l = [l[i] + right[i] * off for i in range(3)]
            if tin and tin[0] == "whip" and f < a + 8:
                u = (f - a) / 8.0; off = -tin[1] * 0.9 * dist * (1 - u) ** 3
                l = [l[i] + right[i] * off for i in range(3)]
            # push-through: dolly hard into a dark object that fills frame (hole, door, mouth, pipe)
            if tout and tout[0] == "push" and f > b - 10:
                u = smoother((f - (b - 10)) / 10.0) ** 1.5
                c = [c[i] + fwd[i] * dist * 0.92 * u for i in range(3)]
            if tin and tin[0] == "push" and f < a + 12:
                u = (1 - (f - a) / 12.0) ** 3                             # fast out of the dark, settles into the spline
                c = [c[i] - fwd[i] * dist * 0.5 * u for i in range(3)]
            # punch: smooth lens push, held, no overshoot
            for P in PUNCH:                     # (frame, mult, dur[, hold]) push in, hold, ease back out
                p, m, dur = P[:3]; hold = P[3] if len(P) > 3 else 45
                if a <= p <= b and f >= p:
                    k_in = smoother((f - p) / dur); k_out = smoother((f - p - dur - hold) / 24.0)
                    lens *= 1 + (m - 1) * k_in * (1 - k_out)
            # handheld (scaled down on long lenses so it never looks like jitter)
            t = f / FPS; k = hand * 30.0 / lens
            c = [c[0] + 0.012 * k * hand_noise(t, 1.0), c[1], c[2] + 0.008 * k * hand_noise(t, 4.0)]
            sx, sy = shake_at(f, SHAKES)
            l = [l[0] + right[0] * (0.02*k*hand_noise(t, 7.0) + 0.045*sx), l[1] + right[1] * (0.02*k*hand_noise(t, 7.0) + 0.045*sx),
                 l[2] + 0.015*k*hand_noise(t, 9.0) + 0.035*sy]
            res[f] = (tuple(c), tuple(l), lens, roll)
    return res

def cam_report(res, SEQS, TRANS, PUNCH=(), N=None):
    """Smoothness gate. Prints problems; returns True when the camera passes."""
    ok = True; cuts = sorted(TRANS)
    for S in SEQS:
        L = S["b"] - S["a"] + 1
        if L < 90: print(f"WARN seq {S['a']}-{S['b']} only {L/FPS:.1f}s (aim 4-10 s; max 2 short inserts)"); ok = False
    worst = 0.0
    for S in SEQS:
        fr = list(range(S["a"] + 1, S["b"]))
        for f in fr:
            if any(abs(f - c) < 12 for c in cuts) or f + 1 > S["b"] or f - 1 < S["a"]: continue
            if any(P[0] <= f < P[0] + 12 or P[0] + P[2] + (P[3] if len(P) > 3 else 45) <= f < P[0] + P[2] + (P[3] if len(P) > 3 else 45) + 26 for P in PUNCH): continue
            acc = math.dist([res[f+1][0][i] - 2*res[f][0][i] + res[f-1][0][i] for i in range(3)], (0, 0, 0))
            worst = max(worst, acc)
    print(f"cuts: {len(cuts)}  sequences: {len(SEQS)}  worst cam accel: {worst*1000:.2f} mm/frame^2")
    if worst * 1000 > 4.0: print("WARN camera accel spike > 4 mm/frame^2: add a key or move keys apart"); ok = False
    snaps = sum(1 for P in PUNCH if P[2] <= 4)
    if snaps > 3: print(f"WARN {snaps} snap zooms (max 3)"); ok = False
    print("CAMERA OK" if ok else "CAMERA NEEDS FIX")
    return ok

def bake_camera(cam, cam_d, res, cut_frames):
    """Blender side: keys every frame, LINEAR, rotation built from look+roll (no TRACK_TO), holds at cuts."""
    import bpy
    from mathutils import Vector, Quaternion
    for con in list(cam.constraints): cam.constraints.remove(con)
    cam.rotation_mode = 'XYZ'; prev = None; LENS_F = {}
    def put(fr, v):
        nonlocal prev
        c, l, lens, roll = v
        cam.location = c
        q = (Vector(l) - Vector(c)).to_track_quat('-Z', 'Y')
        q = q @ Quaternion((0, 0, 1), roll)
        e = q.to_euler('XYZ', prev) if prev else q.to_euler('XYZ'); prev = e
        cam.rotation_euler = e; cam_d.lens = lens
        cam.keyframe_insert("location", frame=fr); cam.keyframe_insert("rotation_euler", frame=fr)
        cam_d.keyframe_insert("lens", frame=fr)
    for f in sorted(res):
        put(f, res[f]); LENS_F[f] = res[f][2]
        if f + 1 in cut_frames: put(f + 0.98, res[f])       # motion-blur hold: no smear across a cut
    for idb in (cam, cam_d):
        for fc in fcurves_of(idb):
            for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
    return LENS_F

if "fcurves_of" not in globals():          # v1 template alone: copy from module v2
    def fcurves_of(idb):
        ad = idb.animation_data
        if not ad or not ad.action: return []
        act = ad.action
        if hasattr(act, "fcurves"): return list(act.fcurves)
        out_ = []
        for layer in act.layers:
            for strip in layer.strips:
                cb = strip.channelbag(ad.action_slot)
                if cb: out_ += list(cb.fcurves)
        return out_
