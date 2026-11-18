"""Dialogue comedy Shorts: content.json (format "dialog", lines spoken by a cast) -> voices -> voice.wav -> story.json.

Unlike the narrated videos, nothing here needs Claude after the script: the tool knows who says what and when, so it
places the cast, keys every face/mouth/gesture to the line timings and cuts the camera between two-shots, close-ups
and reaction shots by itself (seconds instead of a 12-minute plan_shots).

    python dialog.py speak <slug> [--only 3,7] [--reseed]   OmniVoice: one wav per line (lines/NN_<speaker>.wav)
    python dialog.py assemble <slug>                        lines -> voice.wav + words.json (+ per-line timings)
    python dialog.py plan <slug> [--style 3d|2d|2d_grey]    -> story.json (9:16, rig long, pop captions)
                                                            (2d_grey: grey characters on a coloured set)
The `hook` line ("This is true love") is a title suggestion only: the user adds it in their editor, it is not drawn.

Line wavs are cached by text/voice/speed/seed: after editing two lines only those two are spoken again.
A line can also be the user's own recording (upload_line): it is kept until that line's text changes.
"""
import hashlib, json, math, os, random, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path: sys.path.insert(0, ROOT)
PROJECTS = os.path.join(ROOT, "projects")
FPS = 30
LEAD = 0.35            # seconds before the first line
TAIL = 1.5             # seconds after the last line (the reaction to the punchline)
GAP = 0.22             # default pause between lines
TAKES = 3              # OmniVoice takes per line; the most expressive one is kept (settings.voice_takes)
PRE = 3                # frames: cut a little before the speaker starts
MIN_SHOT = 28          # frames: shorter shots are merged into the previous one
MAX_SHOT = 150         # frames: longer shots get a reaction cutaway
ALL_FACES = ["neutral", "happy", "smirk", "wink", "angry", "shock", "worried", "grumpy", "focus", "smug_closed",
             "sad", "love", "laugh", "side_eye_l", "side_eye_r", "annoyed", "blush"]
SOFT_OUTFIT = {"casual_dress": "soft_dress", "casual_tee": "soft_tee", "hoodie": "soft_hoodie", "shirt_tie": "soft_shirt_tie",
               "home_apron": "soft_apron", "cardigan": "soft_cardigan", "kid_tee": "soft_kid_tee", "kid_dress": "soft_kid_dress"}
STAGES = {"kitchen": [0.0, 4.3], "street": [0.0, 4.0], "office": [0.0, 2.6]}     # where the cast stands (sets without "stage")


def _j(p, d=None):
    try: return json.load(open(p, encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError): return d


def _w(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"; json.dump(obj, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1); os.replace(tmp, p)


def pdir(slug): return os.path.join(PROJECTS, slug)


def is_dialog(content): return bool(content) and content.get("format") == "dialog"


def content_of(slug):
    c = _j(os.path.join(pdir(slug), "content.json"))
    if not is_dialog(c): raise ValueError("dự án này không phải video đối thoại (content.format != dialog)")
    return c


def spoken(text):
    """what the captions show: OmniVoice tags like [laughter] removed"""
    return re.sub(r"\s+", " ", re.sub(r"\[[^\]]*\]", " ", text)).strip()


# =====================================================================
#  voices: one wav per line
# =====================================================================
def line_file(slug, k, speaker): return os.path.join(pdir(slug), "lines", f"{k + 1:02d}_{speaker}.wav")


def _manifest(slug): return _j(os.path.join(pdir(slug), "lines", "manifest.json"), {}) or {}


def _ref(vid):
    import tts
    d = tts.vdir(vid); ref = os.path.join(d, "ref.wav")
    v = _j(os.path.join(d, "voice.json"), {}) or {}
    return (ref if os.path.exists(ref) else None), v


def _key(line, vid, ref_path, seed):
    st = os.stat(ref_path) if ref_path and os.path.exists(ref_path) else None
    raw = json.dumps([line["text"], round(float(line.get("speed") or 1.0), 3), vid, st.st_size if st else 0, int(st.st_mtime) if st else 0, seed])
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def voice_status(slug):
    """per line: has a wav, up to date, source (tts/upload); per cast member: voice chosen?"""
    c = content_of(slug); man = _manifest(slug); out = []
    cast = {m["id"]: m for m in c["cast"]}
    for k, l in enumerate(c["lines"]):
        vid = cast.get(l["speaker"], {}).get("voice_id")
        ref, _ = _ref(vid) if vid else (None, {})
        m = man.get(f"{k + 1:02d}") or {}
        f = line_file(slug, k, l["speaker"])
        fresh = os.path.exists(f) and (m.get("source") == "upload" and m.get("text") == l["text"]
                                       or m.get("key") == _key(l, vid, ref, m.get("seed", k + 1)))
        out.append({"n": k + 1, "speaker": l["speaker"], "text": l["text"], "file": os.path.relpath(f, pdir(slug)).replace("\\", "/"),
                    "exists": os.path.exists(f), "fresh": bool(fresh), "source": m.get("source"), "seconds": m.get("seconds"),
                    "take": m.get("take"), "scores": m.get("scores")})
    import tts
    voices = []
    for m in c["cast"]:
        v = tts.voice(m["voice_id"]) or {}
        voices.append({"id": m["id"], "name": m["name"], "voice_id": m["voice_id"], "instruct": v.get("instruct") or m["voice_instruct"],
                       "ready": bool(v.get("has_ref")), "candidates": v.get("candidates", []), "picked": v.get("picked"),
                       "source": v.get("source")})
    return {"lines": out, "voices": voices}


def speak(slug, only=None, reseed=False, log=print, procs=None, cancelled=lambda: False):
    """OmniVoice for every line that has no up-to-date wav (only = 1-based line numbers to force)"""
    import tts
    c = content_of(slug); man = _manifest(slug)
    cast = {m["id"]: m for m in c["cast"]}
    missing = [m["name"] for m in c["cast"] if not _ref(m["voice_id"])[0]]
    if missing: raise ValueError("chưa chọn giọng cho: " + ", ".join(missing) + " (tab Giọng đọc: Tạo giọng thử rồi bấm Chọn)")
    items = []; force = set(only or [])
    for k, l in enumerate(c["lines"]):
        n = f"{k + 1:02d}"; m = man.get(n) or {}
        vid = cast[l["speaker"]]["voice_id"]; ref, v = _ref(vid)
        seed = int(m.get("seed", k + 1)) + (97 if (reseed and (not force or k + 1 in force)) else 0)
        f = line_file(slug, k, l["speaker"])
        up_to_date = os.path.exists(f) and (m.get("source") == "upload" and m.get("text") == l["text"] or m.get("key") == _key(l, vid, ref, seed))
        if up_to_date and (k + 1) not in force: continue
        items.append({"id": n, "text": l["text"], "out": f, "ref_audio": ref, "ref_text": v.get("ref_text") or "",
                      "speed": float(l.get("speed") or 1.0), "seed": seed, "_key": _key(l, vid, ref, seed), "_line": k})
    if not items:
        log("Mọi câu đã có giọng (không câu nào đổi)."); return {"spoken": 0}
    takes = max(1, min(5, int((_j(os.path.join(pdir(slug), "settings.json"), {}) or {}).get("voice_takes", TAKES))))
    log(f"Tạo giọng {len(items)}/{len(c['lines'])} câu, mỗi câu {takes} bản, giữ bản có biểu cảm nhất…")
    for it in items:            # stale files of a line whose speaker changed
        for fn in os.listdir(os.path.dirname(it["out"])) if os.path.isdir(os.path.dirname(it["out"])) else []:
            if fn.startswith(it["id"] + "_") and fn.endswith(".wav") and os.path.join(os.path.dirname(it["out"]), fn) != it["out"]:
                os.remove(os.path.join(os.path.dirname(it["out"]), fn))
    tdir = os.path.join(pdir(slug), "lines", "takes"); os.makedirs(tdir, exist_ok=True)
    jobs = []
    for it in items:            # several takes per line (OmniVoice phrases each one differently)
        for t in range(1, takes + 1):
            jobs.append(dict({k: v for k, v in it.items() if not k.startswith("_")}, id=f"{it['id']}_t{t}",
                             out=os.path.join(tdir, f"{it['id']}_t{t}.wav"), seed=it["seed"] * 10 + t))
    okk, errs = tts.run_items(jobs, log, procs, cancelled=cancelled)
    import shutil
    failed = {}
    for it in items:
        cands = []
        for t in range(1, takes + 1):
            tid = f"{it['id']}_t{t}"
            if tid not in okk: continue
            x, sr = tts.read_wav(os.path.join(tdir, tid + ".wav"))
            cands.append((tts.expressiveness(tts.trim(x, sr), sr), t, len(x) / sr))
        if not cands:
            failed[it["id"]] = "; ".join(v for k, v in errs.items() if k.startswith(it["id"] + "_t"))[:300] or "không có bản nào"; continue
        med = sorted(d for _, _, d in cands)[len(cands) // 2]
        best = max(cands, key=lambda c_: c_[0] - (3.0 if c_[2] > 1.6 * med else 0.0))      # a much longer take is usually garbled
        shutil.copy(os.path.join(tdir, f"{it['id']}_t{best[1]}.wav"), it["out"])
        man[it["id"]] = {"source": "tts", "key": it["_key"], "seed": it["seed"], "text": c["lines"][it["_line"]]["text"],
                         "seconds": round(best[2], 2), "take": best[1], "scores": [round(s_, 2) for s_, _, _ in cands]}
        if takes > 1: log(f"   câu {int(it['id'])}: bản {best[1]}/{len(cands)} (biểu cảm {', '.join(f'{s_:.1f}' for s_, _, _ in cands)})")
        okk.append(it["id"])
    errs = failed
    _w(os.path.join(pdir(slug), "lines", "manifest.json"), man)
    if errs: raise ValueError(f"{len(errs)} câu chưa tạo được giọng: " + "; ".join(f"câu {k}: {v}" for k, v in list(errs.items())[:5]))
    return {"spoken": len([i for i in items if i["id"] in okk])}


def upload_line(slug, n, data):
    """the user's own recording for line n (1-based)"""
    import tts, wavfix
    c = content_of(slug); k = int(n) - 1
    if not 0 <= k < len(c["lines"]): raise ValueError(f"không có câu {n}")
    l = c["lines"][k]; f = line_file(slug, k, l["speaker"])
    data, _ = wavfix.to_pcm16(data)
    os.makedirs(os.path.dirname(f), exist_ok=True); open(f, "wb").write(data)
    x, sr = tts.read_wav(f)
    man = _manifest(slug); man[f"{k + 1:02d}"] = {"source": "upload", "text": l["text"], "seconds": round(len(x) / sr, 2)}
    _w(os.path.join(pdir(slug), "lines", "manifest.json"), man)
    return {"n": k + 1, "seconds": round(len(x) / sr, 2)}


# =====================================================================
#  lines -> voice.wav + words.json
# =====================================================================
def pause_for(L, k):
    """silence before line k: the script's pause, but never shorter than the beat needs (people react, breathe, let a joke land)"""
    l, p = L[k], L[k - 1]
    want = float(l.get("pause_before", GAP))
    least = 0.25
    if l["speaker"] == p["speaker"]: least = 0.4                       # same person, next sentence: a breath
    if p.get("beat") in ("twist", "punchline"): least = max(least, 0.8)  # the other one takes in the news
    if l.get("beat") == "punchline": least = max(least, 0.7)            # comic pause before the punchline
    if p.get("face") in ("shock", "angry") and l["speaker"] != p["speaker"]: least = max(least, 0.45)
    return min(2.5, max(want, least))


def assemble(slug, log=print):
    import numpy as np, tts, align
    c = content_of(slug); d = pdir(slug)
    st = voice_status(slug)
    miss = [x["n"] for x in st["lines"] if not x["exists"]]
    if miss: raise ValueError(f"câu {miss} chưa có giọng (bấm 'Tạo giọng các câu')")
    old = [x["n"] for x in st["lines"] if not x["fresh"]]
    if old: log(f"   lưu ý: câu {old} đã sửa chữ sau khi tạo giọng (giọng cũ) — bấm 'Tạo giọng các câu' để làm lại")
    pieces = []; t = 0.0; words = []; lines = []
    import tempfile
    tmpd = tempfile.mkdtemp(prefix="dlg_")
    for k, l in enumerate(c["lines"]):
        x, sr = tts.read_wav(line_file(slug, k, l["speaker"]))
        x = tts.resample(tts.trim(x, sr), sr, tts.SR)
        x = tts.level(x) * (10 ** (tts.emotion_gain_db(l.get("face")) / 20))      # same level for everyone, then emotion
        gap = LEAD if k == 0 else pause_for(c["lines"], k)
        pieces.append(np.zeros(int(round(gap * tts.SR)), np.float32)); t += gap
        a = t; dur = len(x) / tts.SR
        tmp = os.path.join(tmpd, f"{k}.wav"); tts.write_wav(tmp, x, tts.SR)
        txt = spoken(l["text"])
        try:
            r = align.align(tmp, txt, fps=FPS, tail=0.0)
            ws = [[round(a + float(w[0]), 3), w[1]] for w in r["words"]]
        except Exception:
            toks = txt.split(); ws = [[round(a + dur * i / max(1, len(toks)), 3), w] for i, w in enumerate(toks)]
        words += ws
        pieces.append(x); t += dur
        lines.append({"n": k + 1, "speaker": l["speaker"], "start": round(a, 3), "end": round(t, 3), "text": txt})
    pieces.append(np.zeros(int(round(TAIL * tts.SR)), np.float32)); t += TAIL
    y = np.concatenate(pieces)
    pk = float(np.abs(y).max()) or 1.0
    y = y * min(4.0, 0.89 / pk)                    # peaks at -1 dBFS (OmniVoice lines come out at different levels)
    tts.write_wav(os.path.join(d, "voice.wav"), y, tts.SR)
    frames = int(math.ceil(t * FPS))
    wj = {"words": words, "segments": [[x["start"], x["end"]] for x in lines], "duration": round(t, 3), "frames": frames,
          "word_count": len(words), "lines": lines}
    _w(os.path.join(d, "words.json"), wj)
    log(f"Ghép {len(lines)} câu: {t:.1f} s ({frames} khung), {len(words)} chữ.")
    return wj


# =====================================================================
#  story.json
# =====================================================================
def _dir(i, xs):
    """+1 when this character's partner (nearest other) stands to the screen right"""
    others = [x for j, x in enumerate(xs) if j != i]
    near = min(others, key=lambda x: abs(x - xs[i]))
    return 1 if near > xs[i] else -1


ROMANCE = {"husband", "wife", "boyfriend", "girlfriend"}
FAMILY = {"dad", "mom", "son", "daughter", "grandma", "grandpa"}
MIN_GAP = 1.1          # big soft heads (r ~0.61, a child's ~0.53) must not overlap


def pair_gap(a, b):
    """how far apart two people stand, from who they are to each other"""
    ra, rb = a.get("role"), b.get("role")
    if "child" in (a.get("body"), b.get("body")): return 1.12               # a child's head is smaller: stand closer
    if ra in ROMANCE and rb in ROMANCE: return 1.2                       # a couple: close (holding hands reaches)
    if ra in FAMILY and rb in FAMILY: return 1.28
    if "boss" in (ra, rb) or "neighbor" in (ra, rb): return 1.6          # work / not close: keep a polite distance
    return 1.35                                                          # friends


def place_cast(cast, lines, stage, spots=None, log=print):
    """floor spot (x, y) of every cast member, fitted to roles and to the set:
    - a cast member's `spot` = a named spot of the set (driver_door, stove, doorway…) -> exactly there
    - `spot` left / center / right -> that order; otherwise whoever speaks first stands on the left (the eye reads the exchange)
    - a child between two adults, a step forward; gaps from the relationship (couple close, boss far)
    - nobody closer than MIN_GAP to anyone else (pushed apart sideways)"""
    spots = spots or {}; n = len(cast)
    first = {m["id"]: next((k for k, l in enumerate(lines) if l["speaker"] == m["id"]), 999) for m in cast}
    fixed = {}; hint = {}
    for i, m in enumerate(cast):
        sp = (m.get("spot") or "").strip()
        if sp in spots: fixed[i] = list(spots[sp]["xy"])
        elif sp in ("left", "center", "right"): hint[i] = {"left": -1, "center": 0, "right": 1}[sp]
        elif sp: log(f"   lưu ý: {m['name']} chọn chỗ '{sp}' nhưng bối cảnh không có chỗ đó, tool tự xếp")
    free = [i for i in range(n) if i not in fixed]
    order = sorted(free, key=lambda i: (hint.get(i, 0), first[cast[i]["id"]]))
    kids = [i for i in order if cast[i]["body"] == "child"]
    if n == 3 and len(free) == 3 and len(kids) == 1 and not hint:       # the child stands between the grown-ups
        order.remove(kids[0]); order.insert(1, kids[0])
    pos = {}
    if free:
        if fixed:                                                        # line up beside the people on fixed spots
            fx = [fixed[i][0] for i in fixed]; side = 1 if sum(fx) / len(fx) <= stage[0] else -1
            x = (max(fx) if side > 0 else min(fx)); y = sum(fixed[i][1] for i in fixed) / len(fixed)
            seq = order if side > 0 else order[::-1]
            anchor = min(fixed, key=lambda i: abs(fixed[i][0] - x))
            prev = cast[anchor]
            for i in seq:
                x += side * pair_gap(prev, cast[i]); pos[i] = [x, y]; prev = cast[i]
        else:
            gaps = [pair_gap(cast[a], cast[b]) for a, b in zip(order, order[1:])]
            width = sum(gaps); x = stage[0] - width / 2
            for k, i in enumerate(order):
                pos[i] = [x, stage[1]]
                if k < len(gaps): x += gaps[k]
    pos.update(fixed)
    for i in range(n):
        if cast[i]["body"] == "child" and i not in fixed: pos[i][1] -= 0.25           # a child a step forward (not hidden)
    xs = [pos[i][0] for i in range(n)]; ys = [pos[i][1] for i in range(n)]
    for _ in range(3):                                                   # keep heads apart
        idx = sorted(range(n), key=lambda i: xs[i])
        for a, b in zip(idx, idx[1:]):
            if abs(ys[a] - ys[b]) < 0.8 and xs[b] - xs[a] < MIN_GAP:
                push = (MIN_GAP - (xs[b] - xs[a])) / 2
                if b in fixed and a not in fixed: xs[a] -= 2 * push
                elif a in fixed and b not in fixed: xs[b] += 2 * push
                else: xs[a] -= push; xs[b] += push
    return [round(x, 3) for x in xs], [round(y, 3) for y in ys]



def _face(f, d):
    if f == "side_eye": return "side_eye_r" if d > 0 else "side_eye_l"
    return f if f in ALL_FACES else "neutral"


def gesture_pose(g, d, gap, scale=1.0, slim=True):
    """arm specs (torso space: shoulders at (+-0.33, 0.66), arm reach 0.66) for a gesture; d = side of the partner"""
    near_arm, far_arm = ("armR", "armL") if d > 0 else ("armL", "armR")
    if g == "hold_hands" and scale != 1.0: gap = gap / scale      # still reach the partner's hand
    sgn = lambda side: 1 if side == "armR" else -1           # screen side of each arm
    P = {}
    if g == "point":
        P[near_arm] = ["ik", [d * 0.92, 0.82], -d]
    elif g == "hold_hands":
        P[near_arm] = ["ik", [d * max(0.45, gap / 2 - 0.03), 0.2], d]
    elif g == "hands_hips":
        hx = 0.3 if slim else 0.43
        P["armL"] = ["ik", [-hx, 0.22], 1]; P["armR"] = ["ik", [hx, 0.22], -1]
    elif g == "cross_arms":
        cx = 0.1 if slim else 0.16
        P["armL"] = ["ik", [cx, 0.44], -1]; P["armR"] = ["ik", [-cx, 0.48], 1]
    elif g == "shrug":
        P["armL"] = ["ik", [-0.66, 0.66], -1]; P["armR"] = ["ik", [0.66, 0.66], 1]; P["tilt"] = 0.1 * d
    elif g == "wave":
        P[far_arm] = ["ik", [f"{sgn(far_arm) * 0.55} + 0.07 * sin(f * 0.55)", 1.38], -sgn(far_arm)]
    elif g == "think":
        P["armR"] = ["ik", [0.13, 0.9], 1]; P["armL"] = ["ik", [0.12, 0.46], -1]; P["tilt"] = 0.08
    elif g == "fist":
        P[far_arm] = ["ik", [sgn(far_arm) * 0.45, "1.05 + 0.05 * sin(f * 1.4)"], -sgn(far_arm)]
    elif g == "hands_up":
        P["armL"] = ["ik", [-0.56, 1.42], 1]; P["armR"] = ["ik", [0.56, 1.42], -1]
    elif g == "open_arms":
        P["armL"] = ["ik", [-0.86, 0.86], -1]; P["armR"] = ["ik", [0.86, 0.86], 1]
    elif g == "facepalm":
        P[far_arm] = ["ik", [sgn(far_arm) * 0.42, 1.42], -sgn(far_arm)]; P["tilt"] = -0.12 * d
    if scale != 1.0:            # a child's body is smaller: same gesture, hand targets scaled to its torso
        sc = lambda v: round(v * scale, 3) if isinstance(v, (int, float)) else f"({v}) * {scale}"
        for k in ("armL", "armR"):
            if k in P: P[k] = [P[k][0], [sc(P[k][1][0]), sc(P[k][1][1])], P[k][2]]
    return P


SHOT = {   # type, frame overrides
    # sizes for the soft body (head top ~2.7-3.0 with a cap/bow): never tighter than chest-up, with headroom
    "two":        ("full",    {"size": 3.15, "look_dz": 0.27, "move": "still"}),
    "speaker":    ("medium",  {"size": 3.0, "look_dz": 0.3, "move": "still"}),
    "listener":   ("medium",  {"size": 2.65, "look_dz": 0.45, "move": "still"}),
    "both_close": ("medium",  {"size": 3.5, "look_dz": 0.3, "move": "still"}),
    "wide":       ("wide",    {"size": 4.6, "look_dz": 0.4, "move": "still"}),
}


def plan_shots(lines_t, content, N):
    """one shot per line (cut PRE frames before it starts), merged/split to keep 1-5 s shots"""
    L = content["lines"]; out = []
    for k, (lt, l) in enumerate(zip(lines_t, L)):
        kind = l.get("shot") or "auto"
        if kind == "auto":
            if k == 0: kind = "two"
            elif l["beat"] == "punchline": kind = "both_close"
            elif l["beat"] == "tag": kind = "listener" if l.get("listener_face") not in (None, "neutral") else "speaker"
            elif l.get("react", "none") != "none": kind = "listener"
            elif k % 4 == 3: kind = "two"                         # re-establish now and then
            else: kind = "speaker"
        a = 1 if k == 0 else max(2, int(round(lt["start"] * FPS)) + 1 - PRE)
        out.append({"a": a, "kind": kind, "line": k, "speaker": l["speaker"]})
    # a line too short for its own shot stays in the previous shot; the same framing twice in a row is one shot
    merged = []
    for i, s in enumerate(out):
        nxt = out[i + 1]["a"] if i + 1 < len(out) else N + 1
        if merged and nxt - s["a"] < MIN_SHOT and s["kind"] != "both_close": continue
        p = merged[-1] if merged else None
        if p and s["kind"] == p["kind"] and (s["kind"] in ("two", "wide", "both_close") or s["speaker"] == p["speaker"]): continue
        merged.append(s)
    shots = []
    for i, s in enumerate(merged):
        b = merged[i + 1]["a"] - 1 if i + 1 < len(merged) else N
        if b - s["a"] + 1 > MAX_SHOT and s["kind"] in ("speaker", "two") and i + 1 < len(merged):   # long line: cut to the listener
            m = s["a"] + (b - s["a"] + 1) // 2
            shots.append(dict(s, b=m - 1)); shots.append(dict(s, a=m, b=b, kind="listener"))
        else:
            shots.append(dict(s, b=b))
    return shots


def plan(slug, char_style=None, log=print):
    c = content_of(slug); d = pdir(slug)
    wj = _j(os.path.join(d, "words.json"))
    if not wj or "lines" not in wj: raise ValueError("chưa ghép giọng (bấm 'Ghép giọng' sau khi tạo giọng các câu)")
    lt = wj["lines"]
    if len(lt) != len(c["lines"]): raise ValueError("content đã đổi số câu sau khi ghép giọng: tạo giọng + ghép lại")
    N = int(wj["frames"]); fr = lambda t: max(1, min(N, int(round(t * FPS)) + 1))
    settings = _j(os.path.join(d, "settings.json"), {}) or {}
    style = char_style or settings.get("char_style") or "3d"
    import storycheck
    lib = storycheck.LibIndex()
    set_name = c["setting"]["set"]
    if not lib.exists("sets", set_name): raise ValueError(f"bối cảnh '{set_name}' chưa có trong thư viện (thiết kế trước)")
    smeta = lib.meta("sets", set_name) if hasattr(lib, "meta") else {}
    stage = (smeta or {}).get("stage") or STAGES.get(set_name, [0.0, 4.0])
    params = dict(c["setting"].get("params") or {})
    if set_name == "kitchen": params.setdefault("stuck_toast", False)
    cast = c["cast"]; n = len(cast)
    kids = [m["body"] == "child" for m in cast]
    xs, ys = place_cast(cast, c["lines"], stage, (smeta or {}).get("spots"), log=log)    # where each one stands, by role and set
    y0 = round(sum(ys) / n, 3)
    gap = max(MIN_GAP, (max(xs) - min(xs)) / max(1, n - 1))
    rnd = random.Random(sum(map(ord, slug)))
    ids = [m["id"] for m in cast]
    chars = []
    idle = c.get("idle", "relaxed")
    for i, m in enumerate(cast):
        dd = _dir(i, xs); ks = 0.66 if kids[i] else 1.0       # child torso 0.52 tall vs 0.78
        talk = [[fr(x["start"]), fr(x["end"])] for x in lt if x["speaker"] == m["id"]]
        # faces: speaker's face when their line starts, listener's reaction a few frames after the other starts
        ex = []
        for k, (x, l) in enumerate(zip(lt, c["lines"])):
            a = fr(x["start"])
            if l["speaker"] == m["id"]: ex.append([a, _face(l["face"], dd)])
            else: ex.append([min(N, a + 4), _face(l.get("listener_face") or "neutral", dd)])
        ex[0][0] = 1
        clean = []
        for f_, face in sorted(ex, key=lambda e: e[0]):
            if clean and clean[-1][1] == face: continue
            if clean and clean[-1][0] == f_: clean[-1][1] = face; continue
            clean.append([f_, face])
        blinks = []; t = 1.2 + rnd.random()
        while t < N / FPS - 0.5: blinks.append(int(t * FPS)); t += 2.4 + 2.2 * rnd.random()
        reacts, rfx, segs = [], [], []
        for k, (x, l) in enumerate(zip(lt, c["lines"])):
            a, b = fr(x["start"]), fr(x["end"])
            if l["speaker"] != m["id"]:
                if l.get("react", "none") != "none":
                    reacts.append([min(N, a + 3), l["react"]])
                    if l["react"] in ("hop", "flinch"): rfx.append(min(N, a + 3))
                g = l.get("listener_gesture", "none")
                if g and g != "none": segs.append({"from": a, "to": min(N, b + 8), **gesture_pose(g, dd, gap, ks)})
            else:
                g = l.get("gesture", "none")
                pose = gesture_pose(g, dd, gap, ks) if g and g != "none" else {}
                pose.setdefault("tilt", 0.05 * dd)               # a small lean of the head toward the partner while talking
                segs.append({"from": max(1, a - 10), "to": min(N, b + 6), **pose})      # starts early: smoothing glides into it
        default = gesture_pose(idle, dd, gap, ks) if idle != "relaxed" and (idle != "hold_hands" or i < 2) else {}
        if idle == "hold_hands" and n == 3 and i == 2: default = {}
        spec = {"id": m["id"], "gaze": dd, "type": "soft_child" if kids[i] else "soft", "outfit": SOFT_OUTFIT.get(m["outfit"], m["outfit"]), "loc": [round(xs[i], 3), ys[i], 0],
                "blocking": {"default": {"location": [round(xs[i], 3), ys[i], 0]},
                             "segments": [{"from": 1, "to": N, "location": [round(xs[i], 3), ys[i], 0]}]},
                "look": {"hair": m["hair"], "hair_color": m["hair_color"], "beard": "none", "seed": i + 1,
                         "palette": {"cloth": m["colors"]["cloth"], "cloth2": m["colors"]["cloth2"]},
                         **({"signature": m["signature"], "sig_color": m.get("sig_color") or [0.92, 0.2, 0.3]}
                            if m.get("signature", "none") != "none" else {})},
                "head_shape": m.get("head_shape", "round"),
                "faces": ALL_FACES, "expressions": clean, "blinks": blinks, "talk": talk,
                "pose": {"default": default, "segments": segs, "smooth": 0.2}}
        if reacts: spec["reacts"] = reacts
        if rfx: spec["reaction_fx"] = rfx
        chars.append(spec)

    mid = [round((min(xs) + max(xs)) / 2, 3), y0, 0]

    def addressee(k):
        """who line k is said to: the last other speaker before it, else the next one, else the nearest person"""
        sp = c["lines"][k]["speaker"]
        for j in list(range(k - 1, -1, -1)) + list(range(k + 1, len(c["lines"]))):
            if c["lines"][j]["speaker"] != sp: return c["lines"][j]["speaker"]
        return min((x for x in ids if x != sp), key=lambda o: abs(xs[ids.index(o)] - xs[ids.index(sp)]))
    shots = []
    for s in plan_shots(lt, c, N):
        kind = s["kind"]; typ, ov = SHOT[kind]
        line = c["lines"][s["line"]]
        if kind in ("two", "wide", "both_close"): subj = mid
        elif kind == "listener": subj = addressee(s["line"])
        else: subj = line["speaker"]
        frame = dict(ov, subject=subj)
        if n == 3 and kind in ("two", "wide"): frame["size"] = ov.get("size", 3.6) * 1.25
        if kind in ("two", "wide"):                     # everyone in: the frame is 9/16 as wide as it is tall
            frame["size"] = round(max(frame["size"], (max(xs) - min(xs) + 1.3) * 16 / 9), 2)
            if frame["size"] > 3.6: frame["y"] = -0.3          # a wider frame: keep the group low, less empty floor, more room above
        if kind == "both_close" and n == 3:              # two closest: the speaker and the one they talk to
            j = ids.index(line["speaker"]); o = ids.index(addressee(s["line"]))
            frame["subject"] = [round((xs[j] + xs[o]) / 2, 3), round((ys[j] + ys[o]) / 2, 3), 0]
        if kind == "both_close" and any(kids):
            frame["look_dz"] = 0.0
        shots.append({"a": s["a"], "b": s["b"], "type": typ, "frame": frame})
    words = [[w[0], w[1]] for w in wj["words"]]
    st = {
        "meta": {"title": c["title"], "slug": slug, "fps": FPS, "frames": N, "seed": 7, "voice": "voice.wav", "output": "out.mp4",
                 "samples": 32, "aspect": "9:16", "char_style": "2d" if style == "2d_grey" else style,
                 **({"char_tone": "grey"} if style == "2d_grey" else {}), "dialog": True, "fast_build": True},
        "sets": [{"id": "stage", "type": set_name, "params": params}],
        "camera": {"rig": "long", "shots": shots, "hand": 0.0},          # locked-off camera, no shake (cuts only)
        "chars": chars,
        "words": words,
        "captions": {"style": "word"},                    # one plain yellow word at a time, like the reference videos
        "sound": {"auto": {"enabled": False}},             # voices only: no music, no sound effects
    }
    errs = storycheck.check_story(st, lib)
    if errs: raise ValueError("story.json lỗi: " + "; ".join(errs[:6]))
    _w(os.path.join(d, "story.json"), st)
    log(f"story.json: {N} khung ({N / FPS:.1f} s), {len(shots)} cú máy, {len(chars)} nhân vật, bối cảnh {set_name}, nhân vật {style}.")
    return st


def main(argv):
    if len(argv) < 2: print(__doc__); return
    cmd, slug = argv[0], argv[1]
    if cmd == "speak":
        only = [int(x) for x in argv[argv.index("--only") + 1].split(",")] if "--only" in argv else None
        print(speak(slug, only=only, reseed="--reseed" in argv))
    elif cmd == "assemble": assemble(slug)
    elif cmd == "plan": plan(slug, argv[argv.index("--style") + 1] if "--style" in argv else None)
    else: print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
