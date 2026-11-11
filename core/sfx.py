"""Procedural SFX (numpy): 22 one-shots, Karplus-Strong music bed with ducking, ambience.

Every generator returns a mono float array at SR.  `SFX[name](**kw)` returns it peak-normalised.
Noise comes from one seeded generator, so the same calls in the same order give the same audio.
"""
import numpy as np

SR = 44100
_rng = np.random.default_rng(11)


def init(seed=11):
    """re-seed the noise generator; every generator below draws from it in call order"""
    global _rng
    _rng = np.random.default_rng(seed)

def _t(sec): return np.arange(int(SR * sec)) / SR
def _env(n, a=0.005, d=0.1):
    t = np.arange(n) / SR; return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / d)
def _fade(x, a=0.01, r=0.05):
    n = len(x); t = np.arange(n) / SR
    return x * np.minimum(1, t / a) * np.minimum(1, (t[-1] - t) / r)
def _lp(x, k):
    """one-pole low-pass; k may be a scalar or an array (sweeping filter)"""
    k = np.broadcast_to(np.asarray(k, dtype=float), x.shape)
    y = np.empty_like(x); acc = 0.0
    for i in range(len(x)):
        acc += k[i] * (x[i] - acc); y[i] = acc
    return y
def _noise(sec): return _rng.standard_normal(int(SR * sec))
def _sweep(f0, f1, sec, shape=1.0):
    t = _t(sec); f = f0 + (f1 - f0) * (t / t[-1]) ** shape
    return np.sin(2 * np.pi * np.cumsum(f) / SR)

# each generator returns a mono float array, peak about 1
def whoosh(sec=0.45):        # camera cut, fast move across frame
    n = int(SR * sec); k = 0.03 + 0.25 * np.sin(np.linspace(0, np.pi, n)) ** 2
    return _fade(_lp(_noise(sec), k) * np.sin(np.linspace(0, np.pi, n)) ** 2 * 3, 0.02, 0.1)
def swish(sec=0.18):          # arm swing, head turn, quick gesture
    n = int(SR * sec); k = np.linspace(0.08, 0.5, n)
    return _fade(_lp(_noise(sec), k) * np.sin(np.linspace(0, np.pi, n)) * 2.5, 0.01, 0.04)
def pop(sec=0.09):            # expression change, prop appears, caption pop
    t = _t(sec); return np.sin(2 * np.pi * (500 + 1400 * t / sec) * t) * _env(len(t), 0.001, 0.025)
def tick(sec=0.05):           # soft caption tick
    t = _t(sec); return np.sin(2 * np.pi * 1800 * t) * _env(len(t), 0.0005, 0.01)
def boing(sec=0.6):           # jump, spring, bounce
    t = _t(sec); f = 180 + 90 * np.sin(2 * np.pi * 9 * t) * np.exp(-t * 4) + 60 * t
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(len(t), 0.003, 0.22)
def thud(sec=0.45):           # body hits ground, heavy landing
    t = _t(sec); body = np.sin(2 * np.pi * (60 + 50 * np.exp(-t / 0.04)) * t) * _env(len(t), 0.002, 0.13)
    return body + _lp(_noise(sec), 0.06) * _env(len(t), 0.001, 0.03) * 4
def bonk(sec=0.35):           # something hits a head
    t = _t(sec); f = 380 * np.exp(-t / 0.12) + 170
    ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(ph) + 0.45 * np.sin(2.7 * ph)) * _env(len(t), 0.001, 0.1)
def step(sec=0.09):           # one footstep (call on every foot plant)
    return _lp(_noise(sec), 0.09) * _env(int(SR * sec), 0.002, 0.018) * 4
def slide_up(sec=0.5):        # slip, rising surprise
    return _fade(_sweep(450, 1900, sec, 1.5), 0.02, 0.05)
def slide_down(sec=0.6):      # falling, deflating
    return _fade(_sweep(1700, 300, sec, 0.8), 0.02, 0.08)
def steam(sec=1.1):           # angry kettle whistle
    t = _t(sec); f = 1100 + 120 * np.sin(2 * np.pi * 7 * t)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.6 * _lp(_noise(sec), 0.3)
    return _fade(s, 0.05, 0.2) * 0.8
def rumble(sec=0.6):          # anger build, impact low end
    t = _t(sec); return np.sin(2 * np.pi * 52 * t) * _env(len(t), 0.01, 0.25) + _lp(_noise(sec), 0.01) * 2 * _env(len(t), 0.01, 0.3)
def ding(sec=0.7):            # idea, wink, correct answer
    t = _t(sec); return (np.sin(2 * np.pi * 1568 * t) + 0.4 * np.sin(2 * np.pi * 3136 * t)) * _env(len(t), 0.002, 0.2)
def squeak(sec=0.16):         # small surprise, eyes widen
    return _fade(_sweep(900, 2400, sec, 0.6), 0.005, 0.03)
def zip_out(sec=0.25):        # character dashes out of frame
    return _fade(_sweep(300, 2600, sec, 2.0) * 0.6 + _lp(_noise(sec), 0.4) * 0.4, 0.005, 0.03)
def crash(sec=0.9):           # things break, train derails
    n = int(SR * sec); x = _noise(sec) * _env(n, 0.001, 0.25)
    for k in range(6):
        i = int(_rng.uniform(0, 0.5) * SR); m = int(0.05 * SR)
        x[i:i + m] += _noise(0.05)[:len(x[i:i + m])] * _env(m, 0.001, 0.015) * 2
    return x * 0.8
def scratch(sec=0.35):        # record scratch, "wait what?"
    t = _t(sec); f = 300 + 900 * np.abs(np.sin(2 * np.pi * 3 * t))
    return _fade(np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * 0.3 + _lp(_noise(sec), 0.5) * 0.5, 0.005, 0.05)
def horn(sec=1.2):            # train horn (two-note chord)
    t = _t(sec); s = sum(np.sign(np.sin(2 * np.pi * f * t)) for f in (277, 349, 415)) / 3
    return _fade(_lp(s, 0.12), 0.06, 0.15) * 1.5
def chug(sec=2.0, bpm=200):   # steam train chugging bed
    out = np.zeros(int(SR * sec)); per = int(SR * 60 / bpm)
    for i in range(0, len(out), per):
        b = _lp(_noise(0.12), 0.25) * _env(int(0.12 * SR), 0.003, 0.04) * (1.4 if (i // per) % 2 == 0 else 0.8)
        out[i:i + len(b)] += b[:len(out[i:i + len(b)])]
    return out
def sad_trombone(sec=2.4):    # fail ending
    out = []
    for f, d, vib in ((392, 0.42, 0), (370, 0.42, 0), (349, 0.42, 0), (330, 1.1, 0.03)):
        t = _t(d); fr = f * (1 + vib * np.sin(2 * np.pi * 6 * t))
        ph = 2 * np.pi * np.cumsum(fr) / SR
        out.append(_fade(_lp(sum(np.sin(h * ph) / h for h in range(1, 8)), 0.25), 0.03, 0.1))
    return np.concatenate(out)
def gulp(sec=0.3):            # nervous swallow
    t = _t(sec); return np.sin(2 * np.pi * (300 - 200 * t / sec) * t) * _env(len(t), 0.01, 0.06) * 1.2
def cash(sec=0.5):            # money / profit
    return np.concatenate([ding(0.12) * 0.6, ding(0.4)])

def _norm(fn):
    def g(**kw):
        x = fn(**kw); return x / max(1e-6, np.abs(x).max())
    return g
SFX = {fn.__name__: _norm(fn) for fn in (whoosh, swish, pop, tick, boing, thud, bonk, step, slide_up, slide_down,
       steam, rumble, ding, squeak, zip_out, crash, scratch, horn, chug, sad_trombone, gulp, cash)}

# ---------------- music bed: plucky loop (Karplus-Strong) ----------------
def pluck(freq, dur=0.5, decay=0.996):
    n = int(SR * dur); per = max(2, int(SR / freq))
    buf = _rng.uniform(-1, 1, per); out = np.empty(n)
    for i in range(n):
        j = i % per; out[i] = buf[j]; buf[j] = 0.5 * (buf[j] + buf[(j + 1) % per]) * decay
    return out
NOTES = {"G3": 196.0, "A3": 220.0, "B3": 246.9, "C4": 261.6, "D4": 293.7, "E4": 329.6, "F4": 349.2,
         "G4": 392.0, "A4": 440.0, "B4": 493.9, "C5": 523.3, "C3": 130.8}
MOODS = {  # pattern of 16 eighth notes, bass notes every half bar, bpm
    "playful": (["C4", "G4", "E4", "G4", "A4", "G4", "E4", "G4", "F4", "C5", "A4", "C5", "G4", "D4", "B3", "D4"], ["C3", "G3"], 112),
    "sneaky":  (["A3", "C4", "E4", "C4", "B3", "D4", "F4", "D4", "A3", "C4", "E4", "A4", "G4", "E4", "D4", "B3"], ["A3", "E4"], 96),
    "tense":   (["E4", "F4", "E4", "F4", "E4", "F4", "G4", "F4", "E4", "F4", "E4", "F4", "B3", "C4", "B3", "C4"], ["E4", "B3"], 130),
}
def music_bed(total_sec, mood="playful", duck=()):
    """duck = list of (start_sec, end_sec) where music drops to 40%"""
    pat, bass, bpm = MOODS[mood]; beat = 60 / bpm / 2
    out = np.zeros(int(SR * total_sec)); cache = {}; t = 0.0; k = 0
    while t < total_sec - 0.3:
        for nm, g, d in ((pat[k % 16], 1.0, 0.5),) + (((bass[(k // 8) % 2], 0.9, 0.7),) if k % 4 == 0 else ()):
            if (nm, d) not in cache: cache[(nm, d)] = pluck(NOTES[nm], d)
            s = cache[(nm, d)]; i = int(t * SR); j = min(len(out), i + len(s)); out[i:j] += g * s[:j - i]
        t += beat; k += 1
    gain = np.ones(len(out))
    for a, b in duck:
        gain[int(a * SR):int(b * SR)] = 0.4
    return out * _lp(gain, 0.0005)

def ambience(total_sec, kind="wind"):
    n = int(SR * total_sec)
    if kind == "wind":
        return _lp(_rng.standard_normal(n), 0.01) * (0.6 + 0.4 * np.sin(np.arange(n) / SR * 0.7)) * 2
    if kind == "city":
        return _lp(_rng.standard_normal(n), 0.04) * 0.8
    return np.zeros(n)
