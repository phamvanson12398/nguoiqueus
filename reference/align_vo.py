# usage: python3 align_vo.py voice.wav script.txt > words_literal.py
import re, sys, wave, math
import numpy as np
from functools import lru_cache

wav, txt_path = sys.argv[1], sys.argv[2]
w = wave.open(wav); sr = w.getframerate(); ch = w.getnchannels()
x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float)
if ch > 1: x = x.reshape(-1, ch).mean(axis=1)
x /= 32768; DUR = len(x) / sr
hop = int(sr * 0.02); n = len(x) // hop
db = np.array([20 * math.log10(math.sqrt(np.mean(x[i * hop:(i + 1) * hop] ** 2)) + 1e-6) for i in range(n)])
quiet = db < np.percentile(db, 20) + 6                        # pauses: quiet runs >= 0.18 s
gaps = []; i = 0
while i < n:
    if quiet[i]:
        j = i
        while j < n and quiet[j]: j += 1
        if (j - i) * 0.02 >= 0.18: gaps.append((i * 0.02, j * 0.02))
        i = j
    else: i += 1

text = open(txt_path).read().replace("\n", " ")
toks = re.findall(r"[A-Za-z0-9'’]+[^\sA-Za-z0-9]*", text)
def syl(t):
    t = re.sub(r"[^a-z]", "", t.lower())
    if not t: return 1
    s = len(re.findall(r"[aeiouy]+", t))
    if t.endswith("e") and not t.endswith(("le", "ee")) and s > 1: s -= 1
    return max(1, s)
words = [(t, syl(t), bool(re.search(r'[.,?!…"]', t))) for t in toks]
S = np.concatenate([[0], np.cumsum([w_[1] for w_ in words])])
segs = []; t0 = 0.0
for a, b in gaps:
    if a > t0: segs.append((t0, a))
    t0 = b
if t0 < DUR: segs.append((t0, DUR))
mean_rate = S[-1] / sum(b - a for a, b in segs)
P = [k for k, w_ in enumerate(words) if w_[2] and k < len(words) - 1]   # punctuation = candidate pause
G = gaps[:-1] if gaps and gaps[-1][1] > DUR - 0.1 else gaps
end_speech = gaps[-1][0] if gaps and gaps[-1][1] > DUR - 0.1 else DUR
def cost(k0, k1, a, b):
    s = S[k1 + 1] - S[k0]; return s * math.log((s / max(b - a, 0.05)) / mean_rate) ** 2
@lru_cache(None)
def best(pi, gi):                                             # even speaking rate, pauses land on punctuation
    k0 = P[pi] + 1 if pi >= 0 else 0; t_ = G[gi][1] if gi >= 0 else 0.0
    res = (cost(k0, len(words) - 1, t_, end_speech) + 0.6 * (len(G) - 1 - gi), None)
    for pj in range(pi + 1, len(P)):
        for gj in range(gi + 1, len(G)):
            c = cost(k0, P[pj], t_, G[gj][0]) + 0.6 * (gj - gi - 1)
            if c > res[0]: continue
            tot = best(pj, gj)[0] + c
            if tot < res[0]: res = (tot, (pj, gj))
    return res
chain = []; st = (-1, -1)
while best(*st)[1] is not None:
    st = best(*st)[1]; chain.append(st)
out = []; k0 = 0; ta = 0.0
for pj, gj in chain + [(None, None)]:
    k1 = P[pj] if pj is not None else len(words) - 1
    tb = G[gj][0] if gj is not None else end_speech
    s = S[k1 + 1] - S[k0]; t_ = ta
    for k in range(k0, k1 + 1):
        out.append((round(float(t_), 2), words[k][0])); t_ += (tb - ta) * words[k][1] / s
    print(f"# {ta:5.2f}-{tb:5.2f}  {' '.join(w_[0] for w_ in words[k0:k1 + 1])}", file=sys.stderr)
    if pj is None: break
    k0 = k1 + 1; ta = G[gj][1]
print("WORDS = " + repr(out))
print(f"# voice duration {DUR:.2f}s -> N = {int(math.ceil((DUR + 1.2) * 30))} frames", file=sys.stderr)
