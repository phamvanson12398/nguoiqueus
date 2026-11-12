"""Long-form audio (16:9 videos): music by mood, war/history SFX, ambience beds, voice processing, -14 LUFS master.

Pure numpy, vectorised (filters run in the frequency domain), so a 5-minute chapter mixes in seconds.
Every sound can be replaced by a real file: library/sfx/<name>.wav (or .ogg/.flac/.mp3 when Blender's `aud` is
available) and library/music/<file> for `sound.music.file`.  Royalty-free/CC0 files only.

The Shorts path (core/sfx.py, core/mixer.py) is untouched.
"""
import math, os, wave, zlib
import numpy as np

SR = 44100
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SFX_DIR = os.path.join(ROOT, "library", "sfx")
MUSIC_DIR = os.path.join(ROOT, "library", "music")


def _add(out, i, s, g=1.0):
    """out[i:i+len(s)] += g*s, clipped to out (i may be negative or past the end)"""
    if i < 0: s = s[-i:]; i = 0
    j = min(len(out), i + len(s))
    if j > i: out[i:j] += g * s[:j - i]


def _rng(tag): return np.random.default_rng(zlib.crc32(tag.encode()))
def _t(sec): return np.arange(int(SR * sec)) / SR


def _env(n, a=0.01, d=0.3, s=0.0, r=0.05, hold=None):
    """attack / exponential decay towards sustain s / release over the last r seconds"""
    t = np.arange(n) / SR
    e = np.minimum(1.0, t / max(a, 1e-4)) * (s + (1 - s) * np.exp(-np.maximum(0, t - a) / max(d, 1e-4)))
    if r: e *= np.clip((t[-1] - t) / r, 0, 1) if n > 1 else 1
    return e


def fft_filter(x, H):
    """apply a magnitude response H(freqs) (callable) to x; zero phase"""
    n = len(x)
    if n == 0: return x
    m = 1 << (n - 1).bit_length()
    X = np.fft.rfft(x, m); f = np.fft.rfftfreq(m, 1 / SR)
    return np.fft.irfft(X * H(f), m)[:n]


def band(lo=None, hi=None, order=2):
    def H(f):
        h = np.ones_like(f)
        if lo: h *= 1 / np.sqrt(1 + (lo / np.maximum(f, 1e-3)) ** (2 * order))
        if hi: h *= 1 / np.sqrt(1 + (f / hi) ** (2 * order))
        return h
    return H


def noise(sec, tag, lo=None, hi=None, order=2):
    x = _rng(tag).standard_normal(int(SR * sec))
    return fft_filter(x, band(lo, hi, order)) if (lo or hi) else x


def fit(x, n):
    """trim or zero-pad to exactly n samples"""
    if len(x) >= n: return x[:n]
    return np.concatenate([x, np.zeros(n - len(x))])


def norm(x, peak=1.0):
    m = np.abs(x).max() if len(x) else 0
    return x * (peak / m) if m > 1e-9 else x


# ---------------------------------------------------------------- instruments (additive, band-limited)
def tone(freq, dur, harm=((1, 1.0),), a=0.01, d=0.5, s=0.0, r=0.08, vib=0.0, detune=0.0):
    t = _t(dur); y = np.zeros(len(t))
    for k, amp in harm:
        f = freq * k
        if f > SR / 2.2: continue
        ph = 2 * np.pi * f * t + (vib * np.sin(2 * np.pi * 5.2 * t) * k)
        y += amp * np.sin(ph)
        if detune: y += amp * 0.6 * np.sin(2 * np.pi * f * (1 + detune) * t + 1.3)
    return y * _env(len(t), a, d, s, r)


SAW = tuple((k, 1.0 / k) for k in range(1, 14))
SQUARE = tuple((k, 1.0 / k) for k in range(1, 14, 2))
BRASS = tuple((k, 1.0 / (k ** 1.2)) for k in range(1, 12))
STR = tuple((k, 1.0 / (k ** 1.6)) for k in range(1, 10))


def pad(freqs, dur, bright=0.5):
    h = tuple((k, a * (bright ** (k - 1) if k > 1 else 1)) for k, a in SAW)
    return sum(tone(f, dur, h, a=min(1.2, dur * 0.3), d=50, s=1.0, r=min(1.0, dur * 0.3), detune=0.004) for f in freqs) / max(1, len(freqs))


def strings(freq, dur, short=False):
    return tone(freq, dur, STR, a=0.02 if short else 0.15, d=0.18 if short else 40, s=0.0 if short else 1.0, r=0.06 if short else 0.3, vib=0.0 if short else 0.004, detune=0.003)


def brass(freq, dur):
    return tone(freq, dur, BRASS, a=0.08, d=40, s=1.0, r=0.2, vib=0.003, detune=0.002)


def pluck(freq, dur=0.6):
    return tone(freq, dur, tuple((k, 1.0 / k ** 1.8) for k in range(1, 10)), a=0.003, d=0.25)


def bass(freq, dur):
    return tone(freq, dur, ((1, 1.0), (2, 0.35), (3, 0.12)), a=0.01, d=0.6, s=0.3, r=0.08)


def taiko(tag="t", big=1.0):
    t = _t(0.9); f = 45 + 55 * np.exp(-t * 14)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 4.5)
    hit = noise(0.9, "taiko" + tag, 200, 2000) * np.exp(-t * 40) * 0.5
    return norm(body + hit) * big


def snare(tag="s"):
    t = _t(0.25)
    return norm(noise(0.25, "snare" + tag, 900, 7000) * np.exp(-t * 18) + 0.4 * np.sin(2 * np.pi * 190 * t) * np.exp(-t * 25))


def hat(tag="h"):
    t = _t(0.08); return norm(noise(0.08, "hat" + tag, 6000, 14000) * np.exp(-t * 60)) * 0.5


# ---------------------------------------------------------------- music by mood
N0 = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def midi(n): return 440.0 * 2 ** ((n - 69) / 12)


def chord(root, kind):
    return [root + i for i in ({"m": (0, 3, 7), "M": (0, 4, 7), "sus": (0, 5, 7), "dim": (0, 3, 6)}[kind])]


MOODS = {   # bpm, key root (midi), progression [(semitones from key, kind)], layers
    "epic":    dict(bpm=92, key=50, prog=[(0, "m"), (-4, "M"), (3, "M"), (-2, "M")], layers=("pad", "ostinato", "brass", "taiko", "bass")),
    "tense":   dict(bpm=120, key=52, prog=[(0, "m"), (0, "m"), (1, "M"), (0, "m")], layers=("drone", "ostinato", "tick", "bass")),
    "mystery": dict(bpm=70, key=57, prog=[(0, "m"), (-4, "M"), (-7, "m"), (-5, "M")], layers=("pad", "pluck", "shimmer")),
    "march":   dict(bpm=104, key=55, prog=[(0, "M"), (5, "M"), (7, "M"), (0, "M")], layers=("snare", "taiko", "brass", "bass", "pad")),
    "calm":    dict(bpm=76, key=60, prog=[(0, "M"), (-3, "m"), (5, "M"), (7, "M")], layers=("pad", "pluck", "bass")),
    "sad":     dict(bpm=66, key=57, prog=[(0, "m"), (-4, "M"), (5, "m"), (-5, "M")], layers=("pad", "strings", "bass")),
    "triumph": dict(bpm=100, key=53, prog=[(0, "M"), (7, "M"), (9, "m"), (5, "M")], layers=("pad", "brass", "taiko", "bass", "ostinato")),
    "playful": dict(bpm=112, key=60, prog=[(0, "M"), (7, "M"), (9, "m"), (5, "M")], layers=("pluck", "bass", "hat")),
}


def music(total_sec, mood="epic", seed=0, intensity=1.0):
    """multi-section underscore: intro (sparse) -> build -> full -> breakdown -> full ...; 8 bars per section"""
    M = MOODS.get(mood, MOODS["epic"]); rnd = np.random.default_rng(seed + zlib.crc32(mood.encode()))
    beat = 60 / M["bpm"]; bar = 4 * beat; n = int(SR * total_sec) + SR * 4
    out = np.zeros(n)

    def put(sig, t, g):
        i = int(t * SR); j = min(n, i + len(sig))
        if 0 <= i < n: out[i:j] += g * sig[:j - i]
    cache = {}

    def c(key, fn):
        if key not in cache: cache[key] = fn()
        return cache[key]
    bars = int(math.ceil(total_sec / bar)) + 1
    plan = ["intro", "build", "full", "break", "full", "build", "full", "break"]
    for b in range(bars):
        sec = plan[(b // 8) % len(plan)] if b >= 8 or b < 8 else "intro"
        if b < 4: sec = "intro"
        elif b < 8: sec = "build"
        dens = {"intro": 0.35, "build": 0.65, "full": 1.0, "break": 0.45}[sec] * intensity
        t0 = b * bar; deg, kind = M["prog"][b % len(M["prog"])]
        root = M["key"] + deg; notes = chord(root, kind)
        L = M["layers"]
        if "pad" in L: put(c(("pad", root, kind), lambda: pad([midi(x) for x in notes], bar * 1.05, 0.55)), t0, 0.22)
        if "drone" in L: put(c(("drone", M["key"]), lambda: pad([midi(M["key"] - 12), midi(M["key"] - 5)], bar * 1.05, 0.4)), t0, 0.25)
        if "bass" in L:
            for k in range(2): put(c(("bass", root), lambda: bass(midi(root - 12), beat * 1.9)), t0 + k * 2 * beat, 0.45)
        if "strings" in L and dens > 0.4: put(c(("str", root), lambda: strings(midi(notes[-1] + 12), bar)), t0, 0.16)
        if "ostinato" in L and dens > 0.5:
            pat = [notes[0], notes[1], notes[2], notes[1]] if mood != "tense" else [notes[0], notes[0] + 1, notes[0], notes[0] + 1]
            for k in range(8):
                p = pat[k % 4] + 12
                put(c(("ost", p), lambda: strings(midi(p), beat * 0.45, short=True)), t0 + k * beat / 2, 0.12)
        if "pluck" in L:
            for k in range(8 if dens > 0.6 else 4):
                if rnd.random() < 0.7 * dens + 0.2:
                    p = notes[int(rnd.integers(0, 3))] + 12 * int(rnd.integers(0, 2))
                    put(c(("pl", p), lambda: pluck(midi(p))), t0 + k * (bar / (8 if dens > 0.6 else 4)), 0.16)
        if "shimmer" in L and b % 2 == 0: put(c(("sh", root), lambda: pad([midi(notes[2] + 24)], bar * 2, 0.2)), t0, 0.06)
        if "brass" in L and dens >= 0.95 and b % 2 == 0:
            put(c(("br", root), lambda: sum(brass(midi(x), bar * 1.6) for x in notes) / 3), t0, 0.16)
        if "taiko" in L and dens > 0.4:
            hits = [0, 1.5, 2, 3] if dens > 0.9 else [0, 2]
            for k, h in enumerate(hits): put(c(("tk", k), lambda: taiko(str(k))), t0 + h * beat, 0.5 if h == 0 else 0.32)
        if "snare" in L and dens > 0.4:
            for k in range(8): put(c(("sn", k % 2), lambda: snare(str(k % 2))), t0 + k * beat / 2, 0.22 if k % 2 else 0.12)
        if "tick" in L:
            for k in range(8): put(c("hat", hat), t0 + k * beat / 2, 0.12)
        if "hat" in L and dens > 0.5:
            for k in range(8): put(c("hat", hat), t0 + k * beat / 2, 0.08)
    out = out[:int(SR * total_sec)]
    fade = np.ones(len(out)); fi = min(len(out), int(SR * 2.0)); fo = min(len(out), int(SR * 2.5))
    fade[:fi] = np.linspace(0, 1, fi); fade[len(out) - fo:] = np.linspace(1, 0, fo)
    return norm(out * fade, 0.9)


# ---------------------------------------------------------------- long-form SFX
def _march(sec=2.0, n_men=30, bpm=110):
    t = _t(sec); out = np.zeros(len(t)); rnd = _rng("march"); step = 60 / bpm
    for k in range(int(sec / step) + 1):
        for j in range(4):
            i = int((k * step + rnd.normal(0, 0.012)) * SR)
            s = noise(0.12, f"st{j}", 80, 900) * np.exp(-_t(0.12) * 35)
            _add(out, i, s, (1.0 if k % 2 == 0 else 0.8))
    return out + 0.15 * noise(sec, "march_bed", 100, 600)


def _clash():
    t = _t(0.9); f = [1220, 1987, 2650, 3540, 4410]
    ring = sum(np.sin(2 * np.pi * fr * t + k) * np.exp(-t * (6 + k * 2)) / (1 + k * 0.4) for k, fr in enumerate(f))
    return ring + noise(0.9, "clash", 1500, 9000) * np.exp(-t * 60) * 2


def _shield():
    t = _t(0.5); return noise(0.5, "shield", 120, 1600) * np.exp(-t * 14) + 0.6 * np.sin(2 * np.pi * 95 * t) * np.exp(-t * 10)


def _arrows(sec=1.6, n=40):
    t = _t(sec); out = np.zeros(len(t)); rnd = _rng("arrows")
    for k in range(n):
        st = rnd.uniform(0, sec * 0.5); d = rnd.uniform(0.35, 0.7); i = int(st * SR); m = int(d * SR)
        w = noise(d, f"ar{k % 6}", 1500 + 300 * (k % 5), 6000) * np.sin(np.pi * np.arange(m) / m) ** 2
        _add(out, i, w)
    return out


def _arrow_hit():
    t = _t(0.25); return noise(0.25, "arrowhit", 300, 3000) * np.exp(-t * 40) + 0.5 * np.sin(2 * np.pi * 160 * t) * np.exp(-t * 30)


def _gallop(sec=2.5, bpm=200):
    t = _t(sec); out = np.zeros(len(t)); step = 60 / bpm
    for k in range(int(sec / step / 1.5) + 1):
        for j, off in enumerate((0, 0.09, 0.2)):
            i = int((k * step * 1.5 + off) * SR); s = noise(0.1, f"hoof{j}", 60, 700) * np.exp(-_t(0.1) * 45)
            _add(out, i, s)
    return out


def _roar(sec=2.5):
    t = _t(sec); env = np.minimum(1, t / 0.4) * np.minimum(1, (t[-1] - t) / 0.8)
    return noise(sec, "roar", 250, 2200) * env * (1 + 0.3 * np.sin(2 * np.pi * 3.1 * t))


def _murmur(sec=3.0): return noise(sec, "murmur", 200, 1500) * (0.7 + 0.3 * np.sin(2 * np.pi * 0.7 * _t(sec)))


def _cornu(sec=1.8):
    t = _t(sec); f0 = 98 * (1 + 0.04 * np.minimum(1, t / 0.2))
    y = sum(np.sin(2 * np.pi * np.cumsum(f0 * k) / SR) / k ** 1.1 for k in range(1, 12))
    return y * _env(len(t), 0.12, 40, 1.0, 0.3)


def _war_drum(): return taiko("wd", 1.0)


def _fire(sec=3.0):
    t = _t(sec); out = 0.4 * noise(sec, "fire_bed", 100, 1500); rnd = _rng("crackle")
    for k in range(int(sec * 25)):
        i = int(rnd.uniform(0, sec) * SR); s = noise(0.02, f"cr{k % 8}", 2000, 9000) * np.exp(-_t(0.02) * 300) * rnd.uniform(0.3, 1.2)
        _add(out, i, s)
    return out


def _rain(sec=3.0): return noise(sec, "rain", 800, 10000) * 0.8 + 0.3 * noise(sec, "rain_lo", 100, 600)


def _thunder(sec=3.5):
    t = _t(sec); return noise(sec, "thunder", 25, 400) * (np.exp(-t * 1.2) * np.minimum(1, t / 0.05)) * (1 + 0.6 * np.sin(2 * np.pi * 1.7 * t))


def _bell(): return tone(523.25, 2.5, ((1, 1), (2.76, 0.5), (5.4, 0.3), (8.9, 0.15)), a=0.002, d=0.9)


def _quill(sec=1.2):
    t = _t(sec); return noise(sec, "quill", 2500, 9000) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 6 * t))) * 0.6


def _paper(): return noise(0.7, "paper", 1500, 8000) * _env(int(SR * 0.7), 0.05, 0.25)


def _stamp(): t = _t(0.3); return noise(0.3, "stamp", 80, 1200) * np.exp(-t * 25) + np.sin(2 * np.pi * 110 * t) * np.exp(-t * 20)


def _heartbeat(sec=1.6):
    t = _t(sec); out = np.zeros(len(t))
    for st in (0.0, 0.25, 0.8, 1.05):
        i = int(st * SR); s = np.sin(2 * np.pi * 55 * _t(0.15)) * np.exp(-_t(0.15) * 25)
        _add(out, i, s)
    return out


def _wind_gust(sec=2.5): t = _t(sec); return noise(sec, "gust", 150, 1800) * np.sin(np.pi * t / sec) ** 2


def _splash(): t = _t(0.8); return noise(0.8, "splash", 300, 6000) * np.exp(-t * 6) * np.minimum(1, t / 0.01)


def _dig(): t = _t(0.4); return noise(0.4, "dig", 100, 2500) * np.exp(-t * 12)


def _hammer(): t = _t(0.35); return noise(0.35, "hammer", 400, 5000) * np.exp(-t * 30) + 0.5 * np.sin(2 * np.pi * 700 * t) * np.exp(-t * 35)


def _whoosh_big(sec=0.9):
    t = _t(sec); env = np.sin(np.pi * t / sec) ** 2
    return noise(sec, "whoosh_big", 150, 3000) * env


LONG_SFX_FN = {"march": _march, "sword_clash": _clash, "shield_bash": _shield, "arrows": _arrows, "arrow_hit": _arrow_hit,
               "gallop": _gallop, "crowd_roar": _roar, "crowd_murmur": _murmur, "war_horn": _cornu, "war_drum": _war_drum,
               "fire": _fire, "rain": _rain, "thunder": _thunder, "bell": _bell, "quill": _quill, "paper": _paper,
               "stamp_hit": _stamp, "heartbeat": _heartbeat, "wind_gust": _wind_gust, "splash": _splash, "dig": _dig,
               "hammer": _hammer, "whoosh_big": _whoosh_big}
LONG_SFX_NAMES = tuple(sorted(LONG_SFX_FN))
_SFX_CACHE = {}


def load_audio(path):
    """mono float at SR from a wav (any width), or any format Blender's aud reads"""
    try:
        with wave.open(path, "rb") as w:
            sr, ch, sw = w.getframerate(), w.getnchannels(), w.getsampwidth(); raw = w.readframes(w.getnframes())
        if sw == 2: x = np.frombuffer(raw, np.int16).astype(float) / 32768
        elif sw == 4: x = np.frombuffer(raw, np.int32).astype(float) / 2 ** 31
        elif sw == 3:
            b = np.frombuffer(raw, np.uint8).reshape(-1, 3); x = (b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8) | (b[:, 2].astype(np.int32) << 16))
            x = np.where(x >= 2 ** 23, x - 2 ** 24, x).astype(float) / 2 ** 23
        else: x = (np.frombuffer(raw, np.uint8).astype(float) - 128) / 128
        if ch > 1: x = x.reshape(-1, ch).mean(axis=1)
    except (wave.Error, EOFError):
        import aud                                         # Blender's audio library: ogg, mp3, flac ...
        d = aud.Sound(path).resample(SR, False).data(); x = d.mean(axis=1) if d.ndim > 1 else d; sr = SR
    if sr != SR:
        idx = np.arange(0, len(x), sr / SR); x = np.interp(idx, np.arange(len(x)), x)
    return x


def user_sfx(name):
    for ext in (".wav", ".ogg", ".flac", ".mp3"):
        p = os.path.join(SFX_DIR, name + ext)
        if os.path.exists(p): return p
    return None


def get_sfx(name, shorts_sfx=None):
    """real file in library/sfx/<name>.* first, then the procedural long-form generator, then the Shorts one"""
    if name in _SFX_CACHE: return _SFX_CACHE[name]
    p = user_sfx(name)
    if p: x = norm(load_audio(p))
    elif name in LONG_SFX_FN: x = norm(LONG_SFX_FN[name]())
    elif shorts_sfx and name in shorts_sfx: x = shorts_sfx[name]()
    else: raise KeyError(f"unknown sound '{name}'")
    _SFX_CACHE[name] = x
    return x


# ---------------------------------------------------------------- ambience beds
AMBIENCE = ("battlefield", "camp", "market", "forest", "sea", "rain", "fire", "wind", "night", "river", "swamp", "city", "room")


def ambience(total_sec, kind="wind"):
    p = user_sfx("amb_" + kind)
    if p:
        x = load_audio(p); reps = int(math.ceil(total_sec * SR / max(1, len(x))))
        return norm(np.tile(x, reps)[:int(total_sec * SR)], 0.7)
    sec = total_sec; t = _t(sec)
    if kind == "wind": x = noise(sec, "amb_wind", 80, 900) * (0.7 + 0.3 * np.sin(2 * np.pi * 0.11 * t))
    elif kind == "rain": x = _rain(sec)
    elif kind == "fire": x = _fire(sec)
    elif kind in ("sea", "river"):
        x = noise(sec, "amb_" + kind, 100, 2500) * ((0.6 + 0.4 * np.sin(2 * np.pi * 0.12 * t) ** 2) if kind == "sea" else 0.8)
    elif kind == "forest":
        x = noise(sec, "amb_forest", 150, 1200) * 0.5; rnd = _rng("birds")
        for k in range(int(sec / 2.5)):
            i = int(rnd.uniform(0, sec) * SR); f = rnd.uniform(2500, 4200); d = 0.12
            s = np.sin(2 * np.pi * (f + 600 * np.sin(2 * np.pi * 18 * _t(d))) * _t(d)) * np.sin(np.pi * _t(d) / d)
            _add(x, i, 0.5 * s)
    elif kind == "night":
        x = noise(sec, "amb_night", 100, 800) * 0.3
        cr = np.sin(2 * np.pi * 4300 * t) * (np.sin(2 * np.pi * 28 * t) > 0.3) * (np.sin(2 * np.pi * 0.6 * t) > 0)
        x += 0.15 * cr
    elif kind in ("battlefield", "camp", "market", "city", "swamp", "room"):
        lo, hi, g = {"battlefield": (100, 2500, 1.0), "camp": (120, 1500, 0.6), "market": (200, 2500, 0.8), "city": (100, 2000, 0.7),
                     "swamp": (80, 900, 0.5), "room": (60, 400, 0.25)}[kind]
        x = noise(sec, "amb_" + kind, lo, hi) * g * (0.75 + 0.25 * np.sin(2 * np.pi * 0.23 * t))
        if kind == "battlefield":
            rnd = _rng("bf")
            for k in range(int(sec / 1.7)):
                i = int(rnd.uniform(0, sec) * SR); s = norm(_clash()) * 0.25 if k % 2 else norm(_shield()) * 0.3
                _add(x, i, s)
    else: x = np.zeros(int(sec * SR))
    return norm(x, 0.7)


# ---------------------------------------------------------------- voice + master
def envelope_follow(x, att=0.01, rel=0.25, hop=256):
    """RMS envelope (per sample) with attack/release, computed on hops"""
    n = len(x); m = int(math.ceil(n / hop))
    pad = np.zeros(m * hop); pad[:n] = x ** 2
    r = np.sqrt(pad.reshape(m, hop).mean(axis=1))
    ka = math.exp(-hop / (SR * att)); kr = math.exp(-hop / (SR * rel)); e = np.empty(m); acc = 0.0
    for i in range(m):
        k = ka if r[i] > acc else kr; acc = k * acc + (1 - k) * r[i]; e[i] = acc
    return np.repeat(e, hop)[:n]


def compress(x, thresh_db=-22, ratio=3.0, makeup_db=4.0):
    env = envelope_follow(x, 0.005, 0.12)
    lvl = 20 * np.log10(env + 1e-9); over = np.maximum(0, lvl - thresh_db)
    return x * 10 ** ((-over * (1 - 1 / ratio) + makeup_db) / 20)


def duck_gain(voice, duck_db=-13.0, floor=-55.0):
    """gain curve for music/ambience: duck_db while the voice speaks, back to 0 dB in the gaps"""
    if voice is None or not len(voice): return None
    env = envelope_follow(voice, 0.04, 0.45)
    lvl = 20 * np.log10(env + 1e-9); act = np.clip((lvl - floor) / 25, 0, 1)
    return 10 ** (duck_db * act / 20)


def lufs(x):
    """integrated loudness (ITU-R BS.1770-4, mono): K-weighting + 400 ms blocks with absolute and relative gating"""
    def biquad_mag(b, a, f):
        z = np.exp(-1j * 2 * np.pi * f / SR)
        return np.abs((b[0] + b[1] * z + b[2] * z * z) / (a[0] + a[1] * z + a[2] * z * z))

    def K(f):                                      # exact BS.1770 stages (coefficients for any sample rate)
        G, Q, fc = 3.99984385397, 0.7071752369554193, 1681.9744509555319
        A = 10 ** (G / 40); w = 2 * np.pi * fc / SR; al = np.sin(w) / (2 * Q); c = np.cos(w); sA = 2 * np.sqrt(A) * al
        shelf = biquad_mag((A * ((A + 1) + (A - 1) * c + sA), -2 * A * ((A - 1) + (A + 1) * c), A * ((A + 1) + (A - 1) * c - sA)),
                           ((A + 1) - (A - 1) * c + sA, 2 * ((A - 1) - (A + 1) * c), (A + 1) - (A - 1) * c - sA), f)
        Q2, fc2 = 0.5003270373253953, 38.13547087613982
        w2 = 2 * np.pi * fc2 / SR; al2 = np.sin(w2) / (2 * Q2); c2 = np.cos(w2)
        hp = biquad_mag(((1 + c2) / 2, -(1 + c2), (1 + c2) / 2), (1 + al2, -2 * c2, 1 - al2), f)
        return shelf * hp
    y = fft_filter(x, K); blk = int(0.4 * SR); hop = int(0.1 * SR)
    if len(y) < blk: return -70.0
    ms = np.array([np.mean(y[i:i + blk] ** 2) for i in range(0, len(y) - blk + 1, hop)])
    L = -0.691 + 10 * np.log10(ms + 1e-12)
    g = ms[L > -70]
    if not len(g): return -70.0
    rel = -0.691 + 10 * np.log10(g.mean()) - 10
    g2 = ms[(L > -70) & (L > rel)]
    return float(-0.691 + 10 * np.log10(g2.mean())) if len(g2) else -70.0


def limit(x, ceiling_db=-1.0, look=0.005, rel=0.08):
    c = 10 ** (ceiling_db / 20); a = np.abs(x); hop = 64; n = len(x); m = int(math.ceil(n / hop))
    p = np.zeros(m * hop); p[:n] = a; pk = p.reshape(m, hop).max(axis=1)
    la = max(1, int(look * SR / hop)); pk = np.array([pk[i:i + la + 1].max() for i in range(m)])
    g = np.minimum(1.0, c / np.maximum(pk, 1e-9)); kr = math.exp(-hop / (SR * rel)); out = np.empty(m); acc = 1.0
    for i in range(m):
        acc = g[i] if g[i] < acc else kr * acc + (1 - kr) * g[i]; out[i] = acc
    return x * np.repeat(out, hop)[:n]


def master(parts, target_lufs=-14.0, ceiling_db=-1.5):
    """sum, normalise to target LUFS, peak-limit -> (signal, report)"""
    n = max(len(p) for p in parts); mix = np.zeros(n)
    for p in parts: mix[:len(p)] += p
    before = lufs(mix); g = 10 ** ((target_lufs - before) / 20) if before > -69 else 1.0
    out = limit(mix * g, ceiling_db)
    for _ in range(2):                             # the limiter shaves loudness: correct and limit again
        err = target_lufs - lufs(out)
        if abs(err) < 0.1 or before <= -69: break
        g *= 10 ** (err / 20); out = limit(mix * g, ceiling_db)
    return out, {"lufs_before": round(before, 1), "gain_db": round(20 * math.log10(g), 1), "lufs": round(lufs(out), 1),
                 "peak_db": round(20 * math.log10(np.abs(out).max() + 1e-9), 1)}


def write_wav(path, x):
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
    return path
