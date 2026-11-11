"""Easing curves, smooth noise, voice amplitude and keyframe utilities (pure timing math)."""
import math
import wave
import numpy as np


# ---------------- easing ----------------
def clamp01(u): return max(0.0, min(1.0, u))
def ease(u): u = clamp01(u); return u * u * (3 - 2 * u)
def ease_out_back(u, s=1.4):                 # overshoot then settle: use for gestures, pops, punch-ins
    u = clamp01(u) - 1; return u * u * ((s + 1) * u + s) + 1
def ease_out_elastic(u):                     # wobble settle: hats, springy props
    u = clamp01(u)
    if u in (0.0, 1.0): return u
    return 2 ** (-10 * u) * math.sin((u * 10 - 0.75) * (2 * math.pi) / 3) + 1
def ease_out_bounce(u):                      # things landing
    u = clamp01(u); n1, d1 = 7.5625, 2.75
    if u < 1 / d1: return n1 * u * u
    if u < 2 / d1: u -= 1.5 / d1; return n1 * u * u + 0.75
    if u < 2.5 / d1: u -= 2.25 / d1; return n1 * u * u + 0.9375
    u -= 2.625 / d1; return n1 * u * u + 0.984375
def pease(f, a, n=8): return ease_out_back((f - a) / n)     # pose transition with overshoot
def noise1(t, seed=0.0):                     # smooth pseudo-noise from summed sines, range ~[-1, 1]
    return (math.sin(t * 1.3 + seed) * 0.5 + math.sin(t * 2.7 + seed * 1.7) * 0.3 + math.sin(t * 5.1 + seed * 2.3) * 0.2)
def lerp(a, b, u): return a + (b - a) * u
def lerp3(a, b, u): return tuple(a[i] + (b[i] - a[i]) * u for i in range(len(a)))
def pop_scale(f, a, dur=5, over=1.25):
    if f < a: return 0.0
    u = (f - a) / dur
    if u >= 1: return 1.0
    return u * over / 0.7 if u < 0.7 else over + (1 - over) * (u - 0.7) / 0.3
def norm(v): l_ = math.sqrt(sum(x * x for x in v)) or 1.0; return tuple(x / l_ for x in v)
def in_ranges(f, ranges): return any(a <= f <= b for a, b in ranges)
def near(f, frames, d): return any(abs(f - x) <= d for x in frames)


# ---------------- voice amplitude (lip flap, head bobs) ----------------
def load_amplitude(path, n_frames, fps):
    amp = [0.0] * (n_frames + 2)
    try:
        with wave.open(path, "rb") as w:
            sr = w.getframerate(); ch = w.getnchannels(); sw = w.getsampwidth()
            raw = w.readframes(w.getnframes())
        x = np.frombuffer(raw, dtype=np.int16 if sw == 2 else np.int32).astype(np.float64)
        if ch > 1: x = x.reshape(-1, ch).mean(axis=1)
        x /= np.abs(x).max() + 1e-9
        hop = sr / fps
        for f in range(1, n_frames + 1):
            seg = x[int((f - 1) * hop):int(f * hop)]
            if len(seg):
                db = 20 * math.log10(math.sqrt(float(np.mean(seg ** 2))) + 1e-6)
                amp[f] = clamp01((db + 38) / 26)
    except Exception as e:
        print("amplitude: no voice file, using synthetic flap", e)
        for f in range(1, n_frames + 1):
            amp[f] = clamp01(0.5 + 0.5 * math.sin(f * 1.9) * math.sin(f * 0.7))
    return amp


# ---------------- keyframe access (Blender 5 layered actions) ----------------
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


def add_teleport_holds(objs, thr=0.6):
    """hold keys so motion blur never smears an object across a teleport (off-set -> on-set)"""
    for o in objs:
        for fc in fcurves_of(o):
            if fc.data_path != "location": continue
            pts = sorted((kp.co[0], kp.co[1]) for kp in fc.keyframe_points)
            for (f0, v0), (f1, v1) in zip(pts, pts[1:]):
                if f1 - f0 >= 0.99 and abs(v1 - v0) > thr:
                    fc.keyframe_points.insert(f0 + 0.98, v0, options={'FAST'})
            fc.update()
