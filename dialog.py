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


def settings_of(slug):
    return _j(os.path.join(pdir(slug), "settings.json"), {}) or {}


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
    if l.get("beat") == "punchline": least = max(least, 1.0)            # comic pause before the punchline: let it land
    if p.get("face") in ("shock", "angry") and l["speaker"] != p["speaker"]: least = max(least, 0.45)
    if l.get("action") == "use": least = max(least, 0.9)                 # a sip / a bite before the line
    if l.get("action") == "enter": least = max(least, 1.2)               # they walk in first
    if p.get("action") == "exit": least = max(least, 1.0)                # the walk-off is seen
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
        x = tts.level(x) * (10 ** (tts.emotion_gain_db(calm_faces(l)[0]) / 20))      # same level for everyone, then emotion
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
    tail = 7.0 if c["lines"][-1].get("action") in ERRANDS else TAIL      # the errand (out of bed, light, back) finishes on screen
    pieces.append(np.zeros(int(round(tail * tts.SR)), np.float32)); t += tail
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
MIN_GAP = 1.6          # big soft heads (r ~0.61, a child's ~0.53) must not overlap, not even touch


def pair_gap(a, b):
    """how far apart two people stand, from who they are to each other"""
    ra, rb = a.get("role"), b.get("role")
    # heads look ~1.5 wide on screen (head_scale 1.22, the nearer one bigger) + a cap brim / bow: below ~1.6 they touch
    if "child" in (a.get("body"), b.get("body")): return 1.4                # a child's head is smaller: stand closer
    if ra in ROMANCE and rb in ROMANCE: return 1.6                       # a couple: close, a hand's width between the heads
    if ra in FAMILY and rb in FAMILY: return 1.62
    if "boss" in (ra, rb) or "neighbor" in (ra, rb): return 1.9          # work / not close: keep a polite distance
    return 1.7                                                           # friends


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



STRAIGHT_TWIST = True    # the twist / punchline / tag are played straight: no shocked face, no jump (user: natural is funnier)
CALM_ACTING = True       # whole dialogue videos: no 'shock' face (O mouth), no hop/flinch, no burst lines + '!' (user: "lố, cứ bình thường")


def calm_faces(l):
    """(speaker face, listener face) of a line. Twist / punchline / tag: a 'shock' becomes deadpan (neutral / side-eye);
    elsewhere a mild worried look (raised brows, small mouth) instead of the big O-mouth shock"""
    sp, li = l.get("face") or "neutral", l.get("listener_face") or "neutral"
    if STRAIGHT_TWIST and l.get("beat") in ("twist", "punchline", "tag"):
        if sp == "shock": sp = "neutral"
        if li == "shock": li = "side_eye"
    if CALM_ACTING:
        if sp == "shock": sp = "worried"
        if li == "shock": li = "worried"
    return sp, li


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


# ---------------------------------------------------------------------
#  props in hand + walking (line `action` / `prop` / `to_spot`, cast `holding`)
# ---------------------------------------------------------------------
PROP_KINDS = ["pillow", "phone", "coffee", "mug", "soda", "bottle", "fries", "burger", "pizza", "icecream", "bag", "keys", "book", "remote",
              "paper", "receipt", "money", "flowers", "gift", "card", "popcorn", "donut"]
USE = {"coffee": "drink", "mug": "drink", "soda": "drink", "bottle": "drink", "fries": "eat", "burger": "eat", "pizza": "eat",
       "icecream": "eat", "popcorn": "eat", "donut": "eat", "phone": "look", "book": "look", "paper": "look", "receipt": "look",
       "remote": "look", "card": "look", "money": "look"}
ACTIONS = ["none", "take_out", "show", "use", "give", "put_away", "walk_to", "enter", "exit", "sit_down", "lie_down", "stand_up",
           "lights_off", "lights_on", "errand", "hug", "high_five", "pinch_cheek", "throw", "fall_over"]
DUO = ("hug", "high_five", "pinch_cheek", "throw", "fall_over")   # moves with the other person (or a fall)
ERRANDS = ("lights_off", "lights_on", "errand")    # get up, walk there, do it, come back to the same place and posture
STAGING_DOC = """Động tác tool làm được (mỗi bước: who, do, + object/state/prop/to_spot, when = before|during|after, back):
- interact: đi tới đồ vật `object` (id trong objects), với tay, đổi nó sang `state` (bật/tắt TV, mở/đóng tủ lạnh, mở cửa, tắt đèn…),
  back = true (mặc định) thì quay về đúng chỗ và tư thế cũ (đang nằm giường → dậy, đi, làm, về nằm lại). Đồ vật có trạng thái
  `room: night/day` (đèn) làm cả phòng tối/sáng thật.
- lights_off / lights_on: như interact với đèn của phòng (không có đèn nào trong objects thì tool tự đặt đèn cây).
- errand + to_spot: đi tới chỗ đó, làm gì đó, quay về.
- walk_to + to_spot (spot của bối cảnh, partner = lại gần người đang nói chuyện, away = lùi ra, left/right); enter (đi vào cảnh);
  exit (bỏ đi khỏi cảnh).
- sit_down / lie_down / stand_up: ngồi xuống (ghế/sofa/mép giường), nằm xuống giường (đắp chăn), đứng dậy / ra khỏi giường.
- Nhiều chỗ: content.scenes [{start, set, posture, holding, spots}] — từ câu `start` câu chuyện chuyển sang bối cảnh khác (tool dựng
  từng cảnh riêng, ghép liền). Đồ vật (objects) có thể ghi `scene` (số cảnh, 1 = cảnh đầu); trống = cảnh nơi nó được dùng lần đầu.
  Đừng cho nhân vật đi bộ sang chỗ khác: đổi cảnh. Ở đầu cảnh mới mọi người đứng (trừ posture/holding khai báo cho cảnh đó).
- take_out / show / use / give / put_away + prop: lấy đồ ra, giơ cho xem, dùng (uống/ăn/xem màn hình), đưa cho người kia, cất đi.
- Hai người với nhau (`to` = id người kia, trống = người đang nói chuyện cùng): hug (lại gần ôm nhau ~1,3 s rồi về chỗ),
  high_five (đập tay), pinch_cheek (véo má, người kia giật mình), throw + prop (mặc định pillow: lấy đà ném trúng đầu người kia,
  họ giật mình), fall_over (ngã ngửa rồi tự dậy — vấp, sốc quá, giả chết).
Nguyên tắc: chỉ dàn dựng điều kịch bản ngụ ý hoặc làm cú hài rõ hơn bằng hình (người kia vừa đi tắt đèn vừa càu nhàu, mở tủ lạnh
đúng lúc nói "I'm not hungry"); không bày việc vô nghĩa; mỗi lúc thường chỉ MỘT người di chuyển; việc mất 4-8 s nên đặt ở câu
mà các câu sau vẫn nói tiếp được (người kia nói vọng theo); hành động của người NGHE là bước có who = người đó; giữ đúng logic
vị trí (ai đang nằm/ngồi/cầm gì sau mỗi bước). Đồ vật cần mà thư viện chưa có → đưa vào library_needs kèm danh sách trạng thái.
"""
LAMP_STATES = {"on": {"show": ["shade_on"], "hide": ["shade_off"], "room": "day"},
               "off": {"show": ["shade_off"], "hide": ["shade_on"], "room": "night"}}
WALK = 1.25            # units per second (a stroll; the soft body is ~2.7 tall)
OFF = 4.3              # entering / leaving people start / end this far from the stage centre (out of a 9:16 frame)
STEP = 0.32            # walk cycle: phase per frame (one step ~10 frames)


def _sgn(hand): return 1 if hand == "R" else -1


def hold_arm(kind, hand, ks):
    """the arm holding an item between actions: forearm forward at the waist (a bag simply hangs)"""
    if kind == "bag": return None
    s = _sgn(hand)
    return ["ik", [round(s * 0.3 * ks, 3), round(0.34 * ks, 3)], -s]


def action_arm(act, kind, hand, d, reach, ks):
    """(arm spec, prop tilt) for an item action; d = side of the partner, reach = how far the partner's hand is"""
    s = _sgn(hand); sc = lambda v: round(v * ks, 3)
    if act == "show":                        # held out toward the partner at face height
        return ["ik", [sc(d * 0.38), sc(0.8)], -s], 0.0
    if act == "give":                        # arm out toward the partner (meets their hand)
        return ["ik", [round(d * min(0.62 * ks, reach), 3), sc(0.5)], -s], 0.0
    if act == "take":
        return ["ik", [round(d * min(0.62 * ks, reach), 3), sc(0.5)], -s], 0.0
    if act == "put_away":                    # down to the pocket / bag
        return ["ik", [sc(s * 0.24), sc(0.1)], -s], 0.0
    use = USE.get(kind, "look")
    if use == "drink":                       # cup at the side of the mouth, tipped toward it
        return ["ik", [sc(s * 0.46), sc(0.78)], -s], round(s * 1.05, 2)
    if use == "eat":
        return ["ik", [sc(s * 0.4), sc(0.82)], -s], round(s * 0.6, 2)
    return ["ik", [sc(d * 0.2), sc(0.62)], -s], 0.0          # look at it (phone, letter…) in front of the chest


def plan_actions(c, lt, xs, ys, stage, spots, N, fr, kids, addressee, log=print, beds=None, inbed0=(), objects=None):
    """turns `holding` / line actions into, per cast member: hand_props (items + when they are seen), blocking segments
    (standing + walking), pose segments that win over gestures (walking, item actions) and arm poses for holding.
    Returns (items, blocking, act_segs, hold_at, pos_at)."""
    cast = c["cast"]; L = c["lines"]; n = len(cast); ids = [m["id"] for m in cast]
    spots = spots or {}
    side = {i: (1 if xs[i] >= stage[0] else -1) for i in range(n)}
    way = {i: [] for i in range(n)}                  # (a, b, (x0, y0), (x1, y1)) walks, in time order
    items = {i: [] for i in range(n)}                # {"kind", "hand", "a", "b", "id"}
    act = {i: [] for i in range(n)}                  # pose segments with priority
    open_ = {i: {} for i in range(n)}                # hand -> item being held
    out = {i: False for i in range(n)}                # off the frame right now (not entered yet / left)
    beds = beds or {}; inbed = {i: i in inbed0 for i in range(n)}
    cur_post = {i: (cast[i].get("posture") or "stand") for i in range(n)}
    lights = []; extra_post = {i: [] for i in range(n)}; obj_states = []
    reacts_x = {i: [] for i in range(n)}; flights = []
    objs = {o["id"]: dict(o) for o in (objects or [])}       # things in the set people can use (placed by plan())
    state = {"posture": lambda i, f: "stand"}         # set by plan() once postures are planned (items held in bed)

    def pos(i, f):
        p = (xs[i], ys[i])
        for a, b, p0, p1 in way[i]:
            if f >= b: p = p1
            elif f >= a:
                u = (f - a) / max(1, b - a); u = u * u * (3 - 2 * u)
                return (p0[0] + (p1[0] - p0[0]) * u, p0[1] + (p1[1] - p0[1]) * u)
            else: break
        return p

    def near_hand(i, f):
        j = addressee_at(i, f)
        d = 1 if pos(j, f)[0] > pos(i, f)[0] else -1
        return ("R" if d > 0 else "L"), d

    def addressee_at(i, f):
        return min((j for j in range(n) if j != i), key=lambda j: abs(pos(j, f)[0] - pos(i, f)[0]))

    def give_item(i, kind, hand, a, color=None):
        it = {"kind": kind, "hand": hand, "a": a, "b": N, "id": f"{kind}{len(items[i])}"}
        if color: it["color"] = color
        items[i].append(it); open_[i][hand] = it; return it

    def hand_for(i, prefer, f):
        """the hand a new item goes to at frame f: `prefer` if free, else the other one if free, else `prefer` after the item
        already in it is put down (seen: two coffees drawn in one hand, a person ending up with an item in each hand + more)"""
        for h_, it_ in list(open_[i].items()):
            if it_["b"] < f: open_[i].pop(h_, None)          # already gone (put away / given)
        other = "L" if prefer == "R" else "R"
        if prefer not in open_[i]: return prefer
        if other not in open_[i]: return other
        old = open_[i].pop(prefer); old["b"] = max(old["a"], f - 1)
        return prefer

    def find(i, kind):
        for h, it in open_[i].items():
            if kind in (None, "", it["kind"]): return h, it
        return None, None

    busy = {i: 0 for i in range(n)}                 # frame until which someone is busy walking/doing (steps queue after it)
    moments = []                                     # (a, b, who, kind, where): cut to these (the camera shows them there)
    instant = {i: set() for i in range(n)}          # frames where someone's posture changes at a cut (no easing)

    def walk(i, a, to, speed=WALK):
        a = max(a, busy[i] + 1)
        p0 = pos(i, a); dist = math.hypot(to[0] - p0[0], to[1] - p0[1])
        if dist < 0.05: return a
        b = min(N + 40, a + max(int(0.8 * FPS), int(round(dist / speed * FPS))))
        way[i].append((a, b, p0, to)); busy[i] = b
        return b

    def jump(i, f, to):
        """be somewhere else from frame f on, hidden by a camera cut (no walking through beds and furniture)"""
        p0 = pos(i, f); way[i].append((f - 1, f - 1, p0, (round(to[0], 3), round(to[1], 3)))); busy[i] = max(busy[i], f)
        instant[i].add(f)

    for i, m in enumerate(cast):                    # items held from the start
        h = m.get("holding") or {}
        if h.get("kind") in PROP_KINDS:
            hand = h.get("hand") or ("R" if _dir(i, xs) > 0 else "L")
            if not h.get("hand") and i in inbed0: hand = "L" if hand == "R" else "R"     # in bed: the outer hand (not over the partner)
            give_item(i, h["kind"], hand, 1, h.get("color"))
    entering = {i for i in range(n) if any(l["speaker"] == ids[i] and l.get("action") == "enter" for l in L)}
    for i in entering:                               # out of the frame until their entrance
        first = next(k for k, l in enumerate(L) if l["speaker"] == ids[i] and l.get("action") == "enter")
        if any(l["speaker"] == ids[i] for l in L[:first]): continue    # they talk before: enter = walk back in later
        start = (stage[0] + side[i] * OFF, ys[i])
        way[i].append((0, 1, start, start)); out[i] = True

    def duo(k, l, i, acts, kind, a, b):
        """hug / high five / pinch a cheek / throw something at someone / fall over"""
        to = (l.get("to") or l.get("object") or "").strip()
        j = ids.index(to) if to in ids else addressee_at(i, a)
        t = min(N, max(a, busy[i] + 2))
        pi, pj = pos(i, t), pos(j, t); d = 1 if pj[0] > pi[0] else -1
        hi, hj = ("R" if d > 0 else "L"), ("L" if d > 0 else "R")
        ks, kj = (0.66 if kids[i] else 1.0), (0.66 if kids[j] else 1.0)
        bi, bj = -_sgn(hi), -_sgn(hj)
        if acts == "fall_over":                       # slips and falls on their back (away from the other), then gets up
            act[i].append({"from": t, "to": min(N, t + 56),
                           "rest": f"{d * 1.45:.2f} * ease((f - {t}) / 7) - ({d * 1.45:.2f}) * ease((f - {t + 42}) / 12)",
                           "armL": ["ang", -2.2, 0.4], "armR": ["ang", 2.2, -0.4], "legs": [[0.5 * d, -0.2], [0.8 * d, -0.4]]})
            busy[i] = max(busy[i], t + 56); moments.append((t, min(N, t + 56), i, "cut", None)); return
        if acts == "throw":                           # wind up, let go, it flies at the other one's head
            item = kind or "pillow"
            h, it = find(i, item)
            if it is None:
                h = hand_for(i, hi, max(1, t - 10)); it = give_item(i, item, h, max(1, t - 10))
            sh = _sgn(h)
            act[i].append({"from": t, "to": t + 10, "arm" + h: ["ik", [round(-d * 0.25 * ks, 3), round(1.35 * ks, 3)], -sh]})
            act[i].append({"from": t + 11, "to": t + 22, "arm" + h: ["ik", [round(d * 0.62 * ks, 3), round(1.05 * ks, 3)], -sh]})
            rel = t + 14; it["b"] = rel; open_[i].pop(h, None)
            hit = rel + max(8, int(abs(pj[0] - pi[0]) * 5))
            fy = round(min(pi[1], pj[1]) - 0.9, 3)        # in front of both (their flat layers stand ~0.5 toward the camera)
            flights.append({"kind": item, "a": rel, "b": hit, "from": [round(pi[0] + d * 0.5, 3), fy, 1.9 * ks],
                            "to": [round(pj[0] - d * 0.2, 3), fy, 2.05 * kj], "arc": 0.5})
            reacts_x[j].append([min(N, hit), "flinch"]); busy[i] = max(busy[i], t + 24)
            moments.append((t, min(N, hit + 16), j if abs(pj[0] - pi[0]) < 1.6 else i, "cut", None)); return
        gap = {"hug": 0.95, "high_five": 1.25, "pinch_cheek": 1.0}[acts]
        p_home = pi
        b1 = t
        if abs(pj[0] - pi[0]) > gap + 0.15:           # steps up to the other one first
            b1 = walk(i, t, (round(pj[0] - d * gap, 3), round(pj[1] - 0.05, 3)))
        if acts == "hug":                             # both hug for ~1.3 s
            act[i].append({"from": b1, "to": b1 + 40, "arm" + hi: ["ik", [round(d * 0.55 * ks, 3), round(0.8 * ks, 3)], bi],
                           "arm" + ("L" if hi == "R" else "R"): ["ik", [round(d * 0.3 * ks, 3), round(0.95 * ks, 3)], -bi]})
            act[j].append({"from": b1 + 2, "to": b1 + 40, "arm" + hj: ["ik", [round(-d * 0.55 * kj, 3), round(0.8 * kj, 3)], bj],
                           "arm" + ("L" if hj == "R" else "R"): ["ik", [round(-d * 0.3 * kj, 3), round(0.95 * kj, 3)], -bj]})
            end = b1 + 42
        elif acts == "high_five":                     # near hands meet between them at chest height (a raised hand hides behind the big head)
            half = round(max(0.45, min(0.7, abs(pos(j, b1)[0] - pos(i, b1)[0]) / 2)), 3)
            act[i].append({"from": b1, "to": b1 + 22, "arm" + hi: ["ik", [round(d * half * ks, 3), round(0.82 * ks, 3)], bi]})
            act[j].append({"from": b1 + 2, "to": b1 + 22, "arm" + hj: ["ik", [round(-d * half * kj, 3), round(0.82 * kj, 3)], bj]})
            end = b1 + 24
        else:                                         # pinch_cheek: reaches to the other one's face, they flinch
            act[i].append({"from": b1, "to": b1 + 30, "arm" + hi: ["ik", [round(d * 0.66 * ks, 3), round(1.15 * ks, 3)], bi]})
            reacts_x[j].append([min(N, b1 + 8), "flinch"])
            end = b1 + 32
        busy[i] = max(busy[i], end); busy[j] = max(busy[j], end)
        moments.append((max(1, b1 - 4), min(N, end), i, "cut", None))
        if abs(pos(i, end)[0] - p_home[0]) > 0.1: walk(i, end + 2, p_home)

    def do(k, l, i, acts, kind, a, b, is_step=False):
        """one action of cast member i at line k (a, b = the line's frames, or the step's moment)"""
        if is_step and acts in ("sit_down", "stand_up"):     # steps change posture here (line actions: plan_postures)
            extra_post[i].append((max(2, a - 18, busy[i] + 2), {"sit_down": "sit", "stand_up": "stand"}[acts]))
        ks = 0.66 if kids[i] else 1.0
        if out[i] or acts == "enter":               # entrance (also: someone who left and talks again walks back in)
            if out[i]:
                to = (xs[i], ys[i]); p0 = pos(i, a)
                t0 = max(2, a - int(round(math.hypot(to[0] - p0[0], to[1] - p0[1]) / WALK * FPS)) - 4)
                if way[i] and t0 <= way[i][-1][1]: t0 = way[i][-1][1] + 1
                walk(i, t0, to); out[i] = False
            if acts == "enter": acts = "none"
        if acts == "walk_to":
            ts = (l.get("to_spot") or "").strip()
            j = ids.index(addressee(k)) if addressee(k) in ids else addressee_at(i, a)
            if ts in spots: to = tuple(spots[ts]["xy"])
            elif ts in ("left", "right"): to = (stage[0] + (-1.6 if ts == "left" else 1.6), pos(i, a)[1])
            elif ts in ("away",): to = (pos(i, a)[0] + (1.4 if pos(i, a)[0] > pos(j, a)[0] else -1.4), pos(i, a)[1])
            else:                                   # "partner" / empty: step up close to the person they talk to
                pj = pos(j, a); sd = 1 if pos(i, a)[0] > pj[0] else -1
                to = (pj[0] + sd * 1.15, pj[1])
            for o in range(n):                      # never onto someone else
                if o != i and abs(pos(o, a)[0] - to[0]) < MIN_GAP and abs(pos(o, a)[1] - to[1]) < 0.8:
                    to = (pos(o, a)[0] + (MIN_GAP if to[0] >= pos(o, a)[0] else -MIN_GAP), to[1])
            walk(i, max(2, a - 4), (round(to[0], 3), round(to[1], 3)))
        if acts == "lie_down" and i in beds and not inbed[i]:      # cut: already in bed (lying, under the blanket)
            t = max(2, a - 18, busy[i] + 2)
            jump(i, t, (beds[i]["x"], beds[i]["y"])); moments.append((t, min(N, t + 40), i, "cut", None))
            if is_step: extra_post[i].append((t, "lie"))
        elif is_step and acts == "lie_down": extra_post[i].append((max(2, a - 18, busy[i] + 2), "lie"))
        if acts == "lie_down": inbed[i] = True
        if acts in ERRANDS or acts == "interact":  # walk to a thing, use it (it changes state: light off, TV on…), come back
            p_home = pos(i, a); was_in = inbed[i]; post = cur_post[i]
            others = [pos(o, a)[0] for o in range(n) if o != i]
            sd = 1 if not others or p_home[0] >= sum(others) / len(others) else -1
            ts = (l.get("to_spot") or "").strip(); oid = (l.get("object") or "").strip(); new_state = l.get("state")
            if acts in ("lights_off", "lights_on"):        # the room light: a thing whose state changes the room, else a floor lamp
                new_state = "off" if acts == "lights_off" else "on"
                oid = oid if oid in objs else next((k_ for k_, o_ in objs.items() if any(v.get("room") for v in o_["states"].values())), None)
                sw = None if oid else (ts if ts in spots else next((k_ for k_ in ("light_switch", "lamp", "switch") if k_ in spots), None))
                if not oid and not sw:
                    objs["lamp"] = {"type": "floor_lamp", "x": round(p_home[0] + sd * 2.5, 3), "y": round(p_home[1] + 0.25, 3),
                                    "states": LAMP_STATES, "use": {}, "state0": "off" if new_state == "on" else "on"}
                    oid = "lamp"
            else: sw = ts if ts in spots and not oid else None
            if oid and oid not in objs:
                log(f"   lưu ý: câu {k + 1}: không có đồ vật '{oid}' trong cảnh, bỏ qua"); return
            if oid:
                o = objs[oid]; use = o.get("use") or {}
                rs = 1 if o["x"] >= p_home[0] else -1
                if use.get("side") == "front":
                    target = (o["x"], round(o["y"] - float(use.get("dist", 0.9)), 3)); reach = [0.25 * rs, float(use.get("reach_h", 0.95))]
                else:
                    target = (round(o["x"] - rs * float(use.get("dist", 0.62)), 3), round(o["y"] - 0.35, 3)); reach = [0.6 * rs, float(use.get("reach_h", 0.95))]
            elif sw:
                target = tuple(spots[sw]["xy"]); rs = 1 if target[0] >= p_home[0] else -1; reach = [0.6 * rs, 0.95]
            else:                                          # errand somewhere off to the side
                target = (round(p_home[0] + sd * 2.4, 3), round(p_home[1] - 0.3, 3)); rs = sd; reach = [0.6 * rs, 0.95]
            t_cut = min(N, max(a + 6, busy[i] + 2))        # cut: already there (never walks through the bed)
            # never onto someone else (seen: the kitchen 'counter' spot was where the partner stood, so he appeared INSIDE her):
            # stand beside them, on the side away from them, and reach toward the thing
            aim = target
            for o in range(n):
                if o == i: continue
                po = pos(o, t_cut)
                if abs(po[0] - target[0]) < MIN_GAP and abs(po[1] - target[1]) < 0.8:
                    sd_o = 1 if (target[0] > po[0] or (target[0] == po[0] and p_home[0] > po[0])) else -1
                    target = (round(po[0] + sd_o * MIN_GAP, 3), target[1])
            if target != aim:
                rs = 1 if aim[0] >= target[0] else -1; reach = [0.6 * rs, reach[1]]
            jump(i, t_cut, target)
            if post != "stand": extra_post[i].append((t_cut, "stand"))
            hand = "R" if rs > 0 else "L"
            act[i].append({"from": t_cut, "to": min(N, t_cut + 22), "arm" + hand: ["ik", [round(reach[0], 3), round(reach[1], 3)], -rs]})
            press = min(N, t_cut + 12)
            if oid and new_state:
                if new_state not in objs[oid]["states"]: log(f"   lưu ý: câu {k + 1}: '{oid}' không có trạng thái '{new_state}' ({', '.join(objs[oid]['states'])})")
                else: obj_states.append((press, oid, new_state))
            elif sw and acts in ("lights_off", "lights_on"):
                lights.append((press, "off" if acts == "lights_off" else "on"))
            if l.get("back", True) is not False:            # cut back: already home, in bed / on the sofa again
                t_back = min(N, t_cut + 36)
                jump(i, t_back, p_home)
                if post != "stand": extra_post[i].append((t_back, post))
                inbed[i] = was_in
                moments.append((t_cut, t_back - 1, i, "away", target))
            else:
                inbed[i] = False; cur_post[i] = "stand"; busy[i] = max(busy[i], t_cut + 30)
                moments.append((t_cut, min(N, t_cut + 33), i, "away", target))
        if acts in DUO:
            duo(k, l, i, acts, kind, a, b)
            return
        if acts in ("sit_down", "lie_down", "stand_up"): cur_post[i] = {"sit_down": "sit", "lie_down": "lie", "stand_up": "stand"}[acts]
        if acts == "stand_up" and inbed[i]:         # cut: already up, standing beside the bed on the free side
            others = [pos(o, a)[0] for o in range(n) if o != i]
            sd = -1 if others and sum(others) / len(others) > pos(i, a)[0] else 1
            bx = beds[i]["x"] if i in beds else pos(i, a)[0]
            t = max(2, a - 18, busy[i] + 2)
            jump(i, t, (round(bx + sd * 1.6, 3), round(pos(i, a)[1] - 0.5, 3))); inbed[i] = False
            moments.append((t, min(N, t + 40), i, "cut", None))
            if is_step: extra_post[i].append((t, "stand"))
        if acts == "exit":                          # says the line, then walks off on their side
            others = [pos(o, b)[0] for o in range(n) if o != i and not out[o]]
            if others:                              # away from the others, never through them
                sd = 1 if pos(i, b)[0] >= sum(others) / len(others) else -1
            else: sd = side[i]
            walk(i, b + 4, (stage[0] + sd * OFF, pos(i, b)[1]), speed=WALK * 1.4); out[i] = True
        # items
        if acts in ("take_out", "show", "use", "give", "put_away"): busy[i] = max(busy[i], a + 16)
        hand, d = near_hand(i, a)
        if acts in ("take_out", "show", "use", "give") and kind and find(i, kind)[1] is None:
            h = hand_for(i, hand, max(1, a - 12))
            give_item(i, kind, h, max(1, a - 12))
        if acts in ("show", "use", "give", "put_away"):
            h, it = find(i, kind)
            if it is None:
                if acts != "put_away": log(f"   lưu ý: câu {k + 1} '{acts}' nhưng {l['speaker']} không cầm gì (ghi prop)")
                return
            j = addressee_at(i, a); dj = 1 if pos(j, a)[0] > pos(i, a)[0] else -1
            reach = max(0.2, abs(pos(j, a)[0] - pos(i, a)[0]) / 2 - 0.04)
            if acts == "use":
                arm, tilt = action_arm("use", it["kind"], h, dj, reach, ks)
                seg = {"from": max(1, a - 24), "to": min(N, a + 8), "arm" + h: arm, "prop_tilt": [tilt if h == "L" else 0, tilt if h == "R" else 0]}
                if USE.get(it["kind"]) == "look": seg = dict(seg, to=min(N, b), tilt=-0.06 * dj)
                act[i].append(seg)
            elif acts == "show":
                arm, _ = action_arm("show", it["kind"], h, dj, reach, ks)
                act[i].append({"from": max(1, a - 8), "to": min(N, b + 4), "arm" + h: arm})
            elif acts == "put_away":
                arm, _ = action_arm("put_away", it["kind"], h, dj, reach, ks)
                act[i].append({"from": max(1, a - 4), "to": min(N, a + 10), "arm" + h: arm})
                it["b"] = min(N, a + 8); open_[i].pop(h, None)
            elif acts == "give":                    # hand it over at the end of the line; the other one takes it
                arm, _ = action_arm("give", it["kind"], h, dj, reach, ks)
                act[i].append({"from": max(1, b - 14), "to": min(N, b + 10), "arm" + h: arm})
                kj = 0.66 if kids[j] else 1.0
                hs, same = find(j, it["kind"])             # already holding one of these: swap it, never two coffees
                if same is not None: same["b"] = min(N, b + 2); open_[j].pop(hs, None); hj = hs
                else: hj = hand_for(j, "R" if -dj > 0 else "L", min(N, b + 3))
                armj, _ = action_arm("take", it["kind"], hj, -dj, reach, kj)
                act[j].append({"from": max(1, b - 8), "to": min(N, b + 16), "arm" + hj: armj})
                it["b"] = min(N, b + 2); open_[i].pop(h, None)
                give_item(j, it["kind"], hj, min(N, b + 3), it.get("color"))
    for k, (x, l) in enumerate(zip(lt, L)):
        i = ids.index(l["speaker"]); a, b = fr(x["start"]), fr(x["end"])
        acts = l.get("action") or "none"; kind = (l.get("prop") or "").strip().lower() or None
        if kind and kind not in PROP_KINDS:
            log(f"   lưu ý: câu {k + 1} đạo cụ '{kind}' chưa có, bỏ qua (có: {', '.join(PROP_KINDS)})"); kind = None
        do(k, l, i, acts, kind, a, b)
        for s_ in l.get("steps") or []:              # staged steps (Claude's staging or the page): anyone, before/during/after the line
            who = s_.get("who") or l["speaker"]
            if who not in ids: log(f"   lưu ý: câu {k + 1}: bước của '{who}' không có trong cast, bỏ qua"); continue
            w = s_.get("when") or "during"
            a2 = {"before": max(2, a - 30), "during": a, "after": min(N, b + 6)}.get(w, a)
            a2 = min(N, max(a2, busy[ids.index(who)] + 4))               # one thing after another for the same person
            b2 = max(a2 + 20, b if w != "after" else a2 + 40)
            k2 = (s_.get("prop") or "").strip().lower() or None
            if k2 and k2 not in PROP_KINDS: k2 = None
            do(k, dict(s_, speaker=who), ids.index(who), s_.get("do") or "none", k2, a2, min(N, b2), True)
    # walking: legs step, arms swing (an item arm keeps holding), a little bob
    for i in range(n):
        ph = round(1.3 * i, 2)
        for a, b, p0, p1 in way[i]:
            if b - a < 2: continue
            seg = {"from": max(1, a), "to": min(N, b), "legs": f"walk_legs(f * {STEP} + {ph})",
                   "armL": ["ang", f"-0.12 - 0.32 * sin(f * {STEP} + {ph})", 0.15], "armR": ["ang", f"0.12 - 0.32 * sin(f * {STEP} + {ph})", -0.15],
                   "body": [0, f"0.03 * abs(sin(f * {STEP} + {ph}))"], "rest": 0}
            act[i].insert(0, seg)
    blocking = {}
    for i in range(n):
        segs = []; f0 = 1; p = (xs[i], ys[i])
        for a, b, p0, p1 in way[i]:
            if b <= 1: p = p1; continue
            if a > f0: segs.append({"from": f0, "to": a - 1, "location": [round(p[0], 3), round(p[1], 3), 0]})
            aa = max(1, a)
            segs.append({"from": aa, "to": min(N, b), "location": [
                f"lerp({p0[0]:.3f}, {p1[0]:.3f}, ease((f - {a}) / {max(1, b - a)}))",
                f"lerp({p0[1]:.3f}, {p1[1]:.3f}, ease((f - {a}) / {max(1, b - a)}))", 0]})
            f0 = b + 1; p = p1
            if f0 > N: break
        if f0 <= N: segs.append({"from": f0, "to": N, "location": [round(p[0], 3), round(p[1], 3), 0]})
        blocking[i] = {"default": {"location": [round(xs[i], 3), ys[i], 0]}, "segments": segs}

    def hold_at(i, f):
        """arm specs for the items cast member i holds at frame f"""
        out = {}
        for it in items[i]:
            if it["a"] <= f <= it["b"]:
                arm = hold_arm(it["kind"], it["hand"], 0.66 if kids[i] else 1.0)
                if state["posture"](i, f) == "lie" or (state["posture"](i, f) == "sit" and inbed_at(i, f)):
                    s_ = _sgn(it["hand"]); k_ = 0.66 if kids[i] else 1.0       # in bed: held up by the face, above the blanket
                    arm = ["ik", [round(s_ * 0.5 * k_, 3), round(1.18 * k_, 3)], -s_]   # by the chin, lifted in front of the face
                if arm: out["arm" + it["hand"]] = arm
                if state["posture"](i, f) == "lie" or (state["posture"](i, f) == "sit" and inbed_at(i, f)):
                    t_ = round(-_sgn(it["hand"]) * 0.35, 2)                   # a small tilt = drawn in front of the heads
                    out["prop_tilt"] = [t_, 0] if it["hand"] == "L" else [0, t_]
        return out
    def inbed_at(i, f):
        return state.get("inbed", lambda i, f: False)(i, f)
    hold_at.state = state
    hp = {i: [{"id": it["id"], "kind": it["kind"], "hand": it["hand"], "ranges": [[it["a"], it["b"]]], **({"color": it["color"]} if "color" in it else {})}
              for it in items[i]] for i in range(n)}
    for f_, oid, stt in sorted(obj_states):          # states that change the room (a light) also drive the night/day grade
        rm = objs[oid]["states"][stt].get("room")
        if rm: lights.append((f_, "off" if rm == "night" else "on"))
    lights.sort()
    if any(o_["states"].get(o_.get("state0") or "", {}).get("room") == "night" for o_ in objs.values()):
        lights.insert(0, (1, "off"))                     # a light that starts switched off: the room starts dark
    plan_actions.extras = {"objects": objs, "obj_states": sorted(obj_states), "lights": lights, "post": extra_post,
                           "moments": moments, "instant": instant, "reacts": reacts_x, "flights": flights, "busy_end": max([0] + list(busy.values()) + [f_ for e_ in extra_post.values() for f_, _q in e_])}
    return hp, blocking, act, hold_at, pos, way


# ---------------------------------------------------------------------
#  sitting / lying (cast `posture`, line actions sit_down / lie_down / stand_up, set spots with `seat` / `bed`)
# ---------------------------------------------------------------------
POSTURES = ["stand", "sit", "lie"]
BODY_DIMS = {False: {"hip": 0.82, "tall": 2.82, "head": 2.08}, True: {"hip": 0.52, "tall": 1.9, "head": 1.44}}   # soft / soft_child
BED_LEN = 3.4          # bed (along y) length; the sleeper's spot is BED_HEAD from its head end
BED_HEAD = 0.55
BED_GAP = 1.7         # two sleepers side by side: big round heads must not overlap
IN_BED = {"lie": 1.0, "sit": 1.3}    # head centre above the mattress: reclined on the propped pillow / sitting up
POSE_T = 14            # frames to sit down / lie down / get up
STAND_LEGS = ((-0.06, 0.02), (0.06, -0.02))
FURNITURE = {"chair": {"seat": 0.5, "depth": 0.58}, "sofa": {"seat": 0.52, "depth": 0.9}, "bed": {"seat": 0.62, "depth": 1.3}}


def _steps(base, events, T=POSE_T):
    """an expression: base + sum of eased steps (value changes at each event frame) -> smooth, no segments needed;
    an event (f, v, 1) changes at once from frame f (a camera cut)"""
    out = f"{base:.3f}"; prev = base; changed = False
    for e in events:
        f0, v = e[0], e[1]; t = e[2] if len(e) > 2 else T
        if abs(v - prev) > 1e-4:
            out += f" + ({v - prev:.3f}) * ease((f - {f0 - 1 if t <= 1 else f0}) / {max(1, t)})"; changed = True
        prev = v
    return out if changed else round(base, 3)


def plan_postures(c, lt, xs, ys, way, spots, N, fr, kids, dirs, beds_list=(), log=print, extra=None, instant=None):
    """per cast member: pose-default fields (legs/body/rest as smooth expressions of f), the furniture to put in the set,
    posture_at(i, f) and the frame ranges spent sitting/lying."""
    cast = c["cast"]; L = c["lines"]; n = len(cast); ids = [m["id"] for m in cast]; spots = spots or {}
    ev = {i: [] for i in range(n)}                   # (frame, posture, seat spot name or None)
    for i, m in enumerate(cast):
        p0 = m.get("posture") or "stand"
        if p0 not in POSTURES: p0 = "stand"
        ev[i].append((1, p0, m.get("spot") if (m.get("spot") or "") in spots else None))
    for k, (x, l) in enumerate(zip(lt, L)):
        i = ids.index(l["speaker"]); a = fr(x["start"]); act = l.get("action") or "none"
        if act in ("sit_down", "lie_down", "stand_up"):
            ev[i].append((max(2, a - 18), {"sit_down": "sit", "lie_down": "lie", "stand_up": "stand"}[act], None))
        if act == "walk_to" and (l.get("to_spot") or "") in spots and (spots[l["to_spot"]].get("seat") or spots[l["to_spot"]].get("bed")):
            ev[i].append(("after_walk", "sit", l["to_spot"]))          # walks to the sofa / bed and sits on it
    for i, evs in (extra or {}).items():               # back from an errand: lies / sits down again
        for f0, q in evs: ev[i].append((f0, q, None))
    for i in range(n):                                # walking needs legs: get up first, sit again on arrival at a seat
        fixed = []
        walks = [w for w in way[i] if w[1] - w[0] >= 2]
        for e in ev[i]:
            if e[0] == "after_walk":
                w = next((w for w in walks if w[1] >= 2), None)
                if w: fixed.append((min(N, w[1] + 2), e[1], e[2]))
            else: fixed.append(e)
        fixed.sort(key=lambda e: e[0])
        for a, b, _p0, _p1 in walks:
            cur = sorted([e for e in fixed if e[0] <= a], key=lambda e: e[0])
            if cur and cur[-1][1] != "stand": fixed.append((max(2, a - POSE_T - 2), "stand", None))
        ev[i] = sorted(fixed, key=lambda e: e[0])

    def posture_at(i, f):
        p = "stand"
        for f0, q, _s in ev[i]:
            if f0 <= f: p = q
        return p

    furniture = []; out_ranges = {i: [] for i in range(n)}; fields = {}
    sitters0 = [i for i in range(n) if ev[i][0][1] == "sit" and not ev[i][0][2]]
    sofa_for = set()
    if len(sitters0) >= 2:                            # people sitting together from the start share a sofa
        xs_s = [xs[i] for i in sitters0]; w = max(xs_s) - min(xs_s) + 1.4
        furniture.append({"type": "sofa", "x": (max(xs_s) + min(xs_s)) / 2, "y": max(ys[i] for i in sitters0),
                          "params": {"width": round(max(2.2, w), 2)}})
        sofa_for = set(sitters0)
    for b in beds_list:                               # beds seen from their foot, head end at the sleeper's spot
        furniture.append({"type": "bed", "x": b["x"], "y": b["y"], "params": {"along": "y", "width": b["width"]}})
    for i in range(n):
        kd = BODY_DIMS[bool(kids[i])]; d = dirs[i]
        legs_L, legs_R, by = [], [], []
        inbed = False
        for f0, q, sp in ev[i]:
            seat = None
            if sp and sp in spots: seat = spots[sp].get("seat") or spots[sp].get("bed")
            if q == "lie": inbed = True
            elif q == "stand": inbed = False
            if q == "lie" or (q == "sit" and inbed):  # in bed: head on the pillow / sitting up, the blanket covers the rest
                top = seat if seat else FURNITURE["bed"]["seat"]
                lift = (IN_BED["lie"] if q == "lie" else IN_BED["sit"]) * (0.75 if kids[i] else 1.0)
                legs_L.append((f0, STAND_LEGS[0])); legs_R.append((f0, STAND_LEGS[1]))
                by.append((f0, round(top + lift - kd["head"], 3)))
                continue
            if q == "sit" and seat is None:
                if i not in sofa_for and not any(fu.get("owner") == (i, "sit") for fu in furniture):
                    furniture.append({"type": "chair", "x": xs[i], "y": ys[i], "owner": (i, "sit"), "params": {}})
                seat = FURNITURE["sofa" if i in sofa_for else "chair"]["seat"]
            if q == "sit":
                th = 1.45 * d
                legs_L.append((f0, (th, -th))); legs_R.append((f0, (th * 0.92, -th * 0.92)))
                by.append((f0, round(seat + 0.03 - kd["hip"], 3)))
            else:
                legs_L.append((f0, STAND_LEGS[0])); legs_R.append((f0, STAND_LEGS[1])); by.append((f0, 0.0))
        if all(q == "stand" for _f, q, _s in ev[i]): fields[i] = {}; continue
        inst = (instant or {}).get(i, set())
        T_ = lambda f: 1 if f in inst else POSE_T             # at a cut the pose is already there
        legs_L = [(f, v, T_(f)) for f, v in legs_L]; legs_R = [(f, v, T_(f)) for f, v in legs_R]; by = [(f, v, T_(f)) for f, v in by]
        b0 = lambda lst, j=None: (lst[0][1] if j is None else lst[0][1][j])
        fields[i] = {
            "legs": [[_steps(b0(legs_L, 0), [(f, v[0], t) for f, v, t in legs_L[1:]]), _steps(b0(legs_L, 1), [(f, v[1], t) for f, v, t in legs_L[1:]])],
                     [_steps(b0(legs_R, 0), [(f, v[0], t) for f, v, t in legs_R[1:]]), _steps(b0(legs_R, 1), [(f, v[1], t) for f, v, t in legs_R[1:]])]],
            "body": [0, _steps(b0(by), by[1:])]}
        cur = None
        for f0, q, _s in ev[i] + [(N + 1, "end", None)]:
            if cur and cur[1] != "stand": out_ranges[i].append((cur[0], f0 - 1))
            cur = (f0, q)
    for fu in furniture:
        if fu["type"] == "bed":                          # head end just behind the sleeper, the foot toward the camera
            fu["loc"] = [round(fu["x"], 3), round(fu["y"] + BED_HEAD - BED_LEN / 2, 3), 0]
        else:                                            # just behind the person (their legs show in front of the seat)
            fu["loc"] = [round(fu["x"], 3), round(fu["y"] + FURNITURE[fu["type"]]["depth"] / 2 + 0.05, 3), 0]
    return fields, furniture, posture_at, out_ranges


def place_objects(c, xs, ys, stage, spots, lib, ids, log=print):
    """things people use (content `objects`: TV, fridge, door, lamp…), placed by `near`: a set spot, a cast member, left/right/behind;
    their states (show/hide parts, room light) and use point come from the library meta"""
    out = []
    for o in c.get("objects") or []:
        typ = o.get("type")
        if not typ or not lib.exists("props", typ):
            log(f"   lưu ý: đồ vật '{o.get('id')}' ({typ}) chưa có trong thư viện: bỏ qua (thiết kế trước)"); continue
        meta = (lib.meta("props", typ) if hasattr(lib, "meta") else {}) or {}
        near = (o.get("near") or "right").strip()
        if near in spots: x, y = spots[near]["xy"]; y += 0.4
        elif near in ids:
            j = ids.index(near); sd = 1 if xs[j] >= stage[0] else -1; x, y = xs[j] + sd * 1.7, ys[j] + 0.3
        elif near == "left": x, y = stage[0] - 2.7, stage[1] + 0.3
        elif near == "behind": x, y = stage[0], stage[1] + 1.6
        else: x, y = stage[0] + 2.7, stage[1] + 0.3
        for j in range(len(xs)):                            # never on top of someone
            if abs(xs[j] - x) < 0.9 and abs(ys[j] - y) < 0.6: x = xs[j] + (0.9 if x >= xs[j] else -0.9)
        states = meta.get("states") or {}
        s0 = o.get("state") if o.get("state") in states else next(iter(states), None)
        out.append({"id": o["id"], "type": typ, "x": round(x, 3), "y": round(y, 3), "states": states, "use": meta.get("use") or {},
                    "state0": s0, "params": o.get("params") or {}, "rot": o.get("rot")})
    return out


def object_visibility(objs, changes, N):
    """story visibility for the parts that show a thing's state (screen on/off, door open/shut, shade lit/dark)"""
    vis = {}
    for oid, o in objs.items():
        sts = o.get("states") or {}
        if not sts: continue
        tl = [(1, o.get("state0") or next(iter(sts)))] + [(f, s_) for f, i_, s_ in changes if i_ == oid]
        parts = sorted({p for v in sts.values() for p in (v.get("show", []) + v.get("hide", []))})
        for part in parts:
            rng = []
            for k, (f, s_) in enumerate(tl):
                end = tl[k + 1][0] - 1 if k + 1 < len(tl) else N
                if end < f: continue
                v = sts.get(s_, {}); shown = part in v.get("show", []) or (part not in v.get("hide", []) and not v.get("show"))
                if part in v.get("hide", []): shown = False
                if shown:
                    if rng and rng[-1][1] == f - 1: rng[-1][1] = end
                    else: rng.append([f, end])
            vis[f"{oid}_{part}"] = rng or [[0, 0]]
    return vis


def action_shots(shots, moments, ids, xs, N):
    """someone is somewhere else for a moment (switching the light off, at the fridge, getting into bed): a medium shot on them that
    starts EXACTLY at the cut where they appear there (they never walk across the room), and the line shots resume after it"""
    ins = []
    for a, b, i, kind, where in moments:
        if kind in ("away", "cut"):
            ins.append([a, min(N, max(b, a + 27)), {"type": "medium", "frame": dict(SHOT["speaker"][1], subject=ids[i]), "_lock": True}])
    if not ins: return shots
    ins.sort(key=lambda x: x[0])
    for k in range(len(ins) - 1):                            # back-to-back moments: each ends where the next one starts
        if ins[k][1] >= ins[k + 1][0]: ins[k][1] = ins[k + 1][0] - 1
    out = []
    for s in shots:                                          # cut the line shots around the inserts
        pieces = [(s["a"], s["b"])]
        for a, b, _sh in ins:
            nxt = []
            for p0, p1 in pieces:
                if b < p0 or a > p1: nxt.append((p0, p1)); continue
                if a > p0: nxt.append((p0, a - 1))
                if b < p1: nxt.append((b + 1, p1))
            pieces = nxt
        for p0, p1 in pieces: out.append(dict(s, a=p0, b=p1))
    for a, b, sh in ins: out.append(dict(sh, a=a, b=b))
    out.sort(key=lambda s: s["a"])
    final = []
    for s in out:                                            # no flash cuts: a short line-shot piece is absorbed by its neighbour,
        if not s.get("_lock") and s["b"] - s["a"] < 14:      # but an insert never moves (its first frame is the cut)
            if final and not final[-1].get("_lock"): final[-1]["b"] = s["b"]; continue
            if final: final[-1]["b"] = s["b"]; continue
        final.append(s)
    for k in range(len(final) - 1): final[k]["b"] = final[k + 1]["a"] - 1
    final[-1]["b"] = N
    for s in final: s.pop("_lock", None)
    return final


def plan_beds(c, xs, ys, dirs, kids, log=print):
    """who sleeps where: everyone lying at some point gets a bed seen from its foot (head end at their spot);
    people lying from the start share one double bed side by side. Changes xs of those sharing; returns
    (beds {i: {x, y}}, bed list, set of people in bed at the start)."""
    cast = c["cast"]; n = len(cast); ids = [m["id"] for m in cast]
    lie0 = [i for i, m in enumerate(cast) if m.get("posture") == "lie"]
    later = [i for i in range(n) if i not in lie0 and any(l["speaker"] == ids[i] and l.get("action") == "lie_down" for l in c["lines"])]
    beds, blist = {}, []
    if len(lie0) >= 2:                                # a couple in bed: one double bed, side by side
        cx = sum(xs[i] for i in lie0) / len(lie0); y = max(ys[i] for i in lie0)
        order = sorted(lie0, key=lambda i: xs[i]); w = BED_GAP * (len(order) - 1) + 1.75
        for k, i in enumerate(order):
            xs[i] = round(cx - BED_GAP * (len(order) - 1) / 2 + BED_GAP * k, 3); ys[i] = y; beds[i] = {"x": xs[i], "y": y}
        blist.append({"x": cx, "y": y, "width": round(w, 2)})
        others = [i for i in range(n) if i not in lie0]
        for i in others:                                 # the others stand clear of the bed
            sd = 1 if xs[i] >= cx else -1
            xs[i] = round(cx + sd * max(abs(xs[i] - cx), blist[-1]["width"] / 2 + 0.75), 3)
    elif lie0:
        i = lie0[0]; beds[i] = {"x": xs[i], "y": ys[i]}; blist.append({"x": xs[i], "y": ys[i], "width": 1.9})
    for i in later:                                    # lies down later: their bed is beside them, away from the others
        bx = round(xs[i] - dirs[i] * 1.9, 3)
        beds[i] = {"x": bx, "y": ys[i]}; blist.append({"x": bx, "y": ys[i], "width": 1.9})
    return beds, blist, set(lie0)


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
        out.append({"a": a, "kind": kind, "line": k, "speaker": l["speaker"], "auto": (l.get("shot") or "auto") == "auto"})
    # quick volleys (3+ short lines, speakers taking turns): one two-shot holds them, both faces react; no ping-pong of close-ups
    quick = [(lt["end"] - lt["start"]) < 1.7 for lt in lines_t]
    k = 0
    while k < len(out):
        j = k
        while j + 1 < len(out) and quick[j + 1] and quick[j] and L[j + 1]["speaker"] != L[j]["speaker"]: j += 1
        if j - k + 1 >= 3:
            for q in range(k, j + 1):
                if out[q]["auto"] and out[q]["kind"] == "speaker" and L[q].get("beat") not in ("twist", "punchline"): out[q]["kind"] = "two"
        k = j + 1
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


def scenes_of(c):
    """the video's scenes (content.scenes: [{start (1-based line), set, params, brief_vi, posture, holding}]), [] for one place"""
    sc = sorted([x for x in (c.get("scenes") or []) if int(x.get("start", 1)) >= 1], key=lambda x: int(x["start"]))
    if not sc: return []
    if int(sc[0]["start"]) != 1:
        sc = [{"start": 1, "set": c["setting"]["set"], "params": c["setting"].get("params") or {}, "brief_vi": c["setting"].get("brief_vi", "")}] + sc
    out = []
    for x in sc:                                         # one scene per start line
        if out and int(x["start"]) == int(out[-1]["start"]): out[-1] = x
        elif int(x["start"]) <= len(c["lines"]): out.append(x)
    return out if len(out) > 1 else []


def object_scene(c, oid, scenes):
    """the scene where a thing is first used (an object belongs to one place)"""
    starts = [int(x["start"]) for x in scenes]
    for k, l in enumerate(c["lines"]):
        if l.get("object") == oid or any(st.get("object") == oid for st in l.get("steps") or []):
            return max(i for i, s0 in enumerate(starts) if s0 <= k + 1)
    return 0


def split_scenes(slug, log=print):
    """several places in one video: every scene becomes a part (chapters/NN: its own content, words, voice slice, story);
    the parts are rendered one after the other and joined (same as the long-form parts)"""
    import tts
    c = content_of(slug); d = pdir(slug); wj = _j(os.path.join(d, "words.json"))
    scenes = scenes_of(c)
    if not scenes: return []
    x, sr = tts.read_wav(os.path.join(d, "voice.wav"))
    lt = wj["lines"]; n = len(c["lines"]); dur = float(wj["duration"])
    starts = [int(sc["start"]) - 1 for sc in scenes] + [n]
    settings = _j(os.path.join(d, "settings.json"), {}) or {}
    idx = []
    for k, sc in enumerate(scenes):
        a_l, b_l = starts[k], starts[k + 1]
        t0 = 0.0 if k == 0 else max(0.0, lt[a_l]["start"] - 0.45)
        t1 = dur if k + 1 == len(scenes) else max(t0 + 0.5, lt[b_l]["start"] - 0.45)
        sub = {kk: vv for kk, vv in c.items() if kk not in ("scenes", "lines", "objects", "setting")}
        sub["setting"] = {"set": sc["set"], "params": sc.get("params") or {}, "brief_vi": sc.get("brief_vi", "")}
        sub["lines"] = [dict(l) for l in c["lines"][a_l:b_l]]
        sub["cast"] = []
        for m in c["cast"]:                               # who is where at the start of this scene
            m2 = dict(m); m2.pop("spot", None)
            if (sc.get("spots") or {}).get(m["id"]): m2["spot"] = sc["spots"][m["id"]]
            if (sc.get("posture") or {}).get(m["id"]): m2["posture"] = sc["posture"][m["id"]]
            elif k > 0: m2.pop("posture", None)
            if (sc.get("holding") or {}).get(m["id"]): m2["holding"] = {"kind": sc["holding"][m["id"]]}
            elif k > 0: m2.pop("holding", None)
            sub["cast"].append(m2)
        sub["objects"] = [o for o in c.get("objects") or [] if int(o.get("scene", object_scene(c, o["id"], scenes) + 1)) == k + 1]
        sub["staged"] = True
        words = [[round(w[0] - t0, 3), w[1]] for w in wj["words"] if t0 <= w[0] < t1]
        lines = [dict(x_, n=i + 1, start=round(x_["start"] - t0, 3), end=round(x_["end"] - t0, 3)) for i, x_ in enumerate(lt[a_l:b_l])]
        cd = os.path.join(d, "chapters", f"{k + 1:02d}"); os.makedirs(cd, exist_ok=True)
        _w(os.path.join(cd, "content.json"), sub)
        _w(os.path.join(cd, "words.json"), {"words": words, "segments": [[l["start"], l["end"]] for l in lines], "duration": round(t1 - t0, 3),
                                            "frames": int(math.ceil((t1 - t0) * FPS)), "word_count": len(words), "lines": lines})
        _w(os.path.join(cd, "settings.json"), dict(settings, format="dialog"))
        tts.write_wav(os.path.join(cd, "voice.wav"), x[int(t0 * sr):int(t1 * sr)], sr)
        idx.append({"n": k + 1, "title": sc.get("brief_vi") or sc["set"], "set": sc["set"], "start_line": a_l + 1, "end_line": b_l,
                    "t0": round(t0, 3), "t1": round(t1, 3)})
    _w(os.path.join(d, "chapters", "index.json"), {"chapters": idx, "kind": "dialog_scenes"})
    log(f"{len(idx)} cảnh: " + "; ".join(f"{s_['n']}) {s_['set']} câu {s_['start_line']}-{s_['end_line']}" for s_ in idx))
    return idx


def preview_context(slug):
    """every preview image of the video (all scenes) with what should be on it: time, line (number in the whole script),
    who speaks, the shot, actions going on -> for Claude's self-review"""
    c = content_of(slug); d = pdir(slug); out = []
    parts = []
    if scenes_of(c) and os.path.exists(os.path.join(d, "chapters", "index.json")):
        for p_ in _j(os.path.join(d, "chapters", "index.json"))["chapters"]:
            parts.append((os.path.join(d, "chapters", f"{p_['n']:02d}"), p_["start_line"] - 1, p_["n"], p_["set"]))
    else:
        parts.append((d, 0, 1, c["setting"]["set"]))
    for pd, off, sn, set_name in parts:
        st = _j(os.path.join(pd, "story.json")); wj = _j(os.path.join(pd, "words.json")); prev = os.path.join(pd, "preview")
        if not st or not wj or not os.path.isdir(prev): continue
        shots = st["camera"].get("shots") or []
        for f_ in sorted(x for x in os.listdir(prev) if x.endswith(".png")):
            fr = int(f_[2:6]); t = fr / FPS
            cur = [l for l in wj["lines"] if l["start"] - 0.2 <= t <= l["end"] + 0.4]
            prv = [l for l in wj["lines"] if l["start"] <= t]
            l = cur[0] if cur else (prv[-1] if prv else wj["lines"][0])
            n_ = off + l["n"]; line = c["lines"][n_ - 1]
            sh = next((s for s in shots if s["a"] <= fr <= s["b"]), {})
            subj = (sh.get("frame") or {}).get("subject")
            info = {"image": os.path.join(prev, f_), "scene": sn, "set": set_name, "frame": fr, "t": round(t, 2), "line": n_,
                    "speaking": bool(cur), "speaker": line["speaker"], "text": line["text"], "face": line.get("face"),
                    "listener_face": line.get("listener_face"), "gesture": line.get("gesture"), "shot": line.get("shot", "auto"),
                    "camera": f"{sh.get('type', '?')} on {subj if isinstance(subj, str) else 'group'}"}
            acts = [line.get("action")] if line.get("action", "none") != "none" else []
            acts += [f"{s_['who']} {s_['do']}" + (f" {s_.get('object')}" if s_.get("object") else "") for s_ in line.get("steps") or []]
            if acts: info["actions"] = acts
            out.append(info)
    return out


REVIEW_FIELDS = {"line": ("shot", "face", "listener_face", "gesture", "listener_gesture", "react", "pause_before", "action"),
                 "cast": ("spot", "posture", "holding"), "object": ("near",)}


def apply_review_fixes(c, fixes):
    """Claude's fixes from the preview review -> content (only acting/staging fields; words never change)"""
    done = []
    for fx in fixes:
        t, f_, v = fx["target"], fx["field"], fx.get("value")
        if t == "line":
            l = c["lines"][int(fx["n"]) - 1]
            if f_ == "action" and v in ("", "none", None):
                for k in ("action", "prop", "to_spot"): l.pop(k, None)
            elif f_ == "pause_before": l[f_] = round(max(0.0, min(2.5, float(v))), 2)
            else: l[f_] = v
        elif t == "cast":
            m = next(m for m in c["cast"] if m["id"] == fx["id"])
            if v in ("", None, "none") or (f_ == "posture" and v == "stand"): m.pop(f_, None)
            elif f_ == "holding": m["holding"] = {"kind": v}
            else: m[f_] = v
        elif t == "object":
            o = next(o for o in c.get("objects") or [] if o["id"] == fx["id"])
            o[f_] = v
        done.append(fx)
    return done


def plan(slug, char_style=None, log=print):
    c0 = content_of(slug)
    if scenes_of(c0):                                    # several places: one story per scene
        parts = split_scenes(slug, log)
        for f_ in ["story.json"] + [os.path.join("preview", x) for x in (os.listdir(os.path.join(pdir(slug), "preview"))
                                                                        if os.path.isdir(os.path.join(pdir(slug), "preview")) else [])]:
            if os.path.isfile(os.path.join(pdir(slug), f_)): os.remove(os.path.join(pdir(slug), f_))   # the parts replace the one-place story
        return [plan(f"{slug}/chapters/{p_['n']:02d}", char_style, log) for p_ in parts]
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

    def addressee(k):
        """who line k is said to: the last other speaker before it, else the next one, else the nearest person"""
        sp = c["lines"][k]["speaker"]
        for j in list(range(k - 1, -1, -1)) + list(range(k + 1, len(c["lines"]))):
            if c["lines"][j]["speaker"] != sp: return c["lines"][j]["speaker"]
        return min((x for x in ids if x != sp), key=lambda o: abs(xs[ids.index(o)] - xs[ids.index(sp)]))
    dirs = [_dir(i, xs) for i in range(n)]
    beds, bed_list, inbed0 = plan_beds(c, xs, ys, dirs, kids, log)
    dirs = [_dir(i, xs) for i in range(n)]
    objects = place_objects(c, xs, ys, stage, (smeta or {}).get("spots") or {}, lib, ids, log)
    N0 = N
    for _pass in range(6):                               # the errands may outlast the last line: then the video runs on until they finish
        hprops, blocking, act_segs, hold_at, pos_at, ways = plan_actions(c, lt, xs, ys, stage, (smeta or {}).get("spots"), N, fr, kids, addressee,
                                                                         log if _pass == 0 else (lambda *_: None), beds=beds, inbed0=inbed0, objects=objects)
        need = plan_actions.extras["busy_end"] + int(1.5 * FPS)
        if need <= N: break
        N = need
    if N > N0: log(f"   hành động kéo dài: video dài thêm {(N - N0) / FPS:.1f} s sau câu cuối (lặng, để thấy việc làm xong)")
    pex = plan_actions.extras
    pfields, furniture, posture_at, seated = plan_postures(c, lt, xs, ys, ways, (smeta or {}).get("spots"), N, fr, kids, dirs, bed_list, log,
                                                           extra=pex["post"], instant=pex["instant"])
    objs, lights = pex["objects"], pex["lights"]

    def inbed_at(i, f):
        """lying, or sitting up after lying (the last non-stand posture before f started in bed)"""
        q = posture_at(i, f)
        if q == "lie": return True
        if q != "sit": return False
        g = f
        while g > 1 and posture_at(i, g) == "sit": g -= 8
        return posture_at(i, g) == "lie"
    hold_at.state["posture"] = posture_at; hold_at.state["inbed"] = inbed_at
    for i in range(n):                                   # sitting / lying on purpose: the builder must not "unstick" them from the seat
        for sg in blocking[i]["segments"]:
            loc = sg["location"]
            if all(isinstance(v, (int, float)) for v in loc) and any(a_ <= sg["to"] and b_ >= sg["from"] for a_, b_ in seated[i]):
                sg["note"] = "seated"
    chars = []
    idle = c.get("idle", "relaxed")
    for i, m in enumerate(cast):
        dd = _dir(i, xs); ks = 0.66 if kids[i] else 1.0       # child torso 0.52 tall vs 0.78
        talk = [[fr(x["start"]), fr(x["end"])] for x in lt if x["speaker"] == m["id"]]
        # faces: speaker's face when their line starts, listener's reaction a few frames after the other starts
        ex = []
        for k, (x, l) in enumerate(zip(lt, c["lines"])):
            a = fr(x["start"]); sp_f, li_f = calm_faces(l)
            if l["speaker"] == m["id"]: ex.append([a, _face(sp_f, dd)])
            else: ex.append([min(N, a + 4), _face(li_f, dd)])
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
                if l.get("react", "none") != "none" and not CALM_ACTING:   # (calm: no jumps/flinches from the script at all)
                    reacts.append([min(N, a + 3), l["react"]])
                    if l["react"] in ("hop", "flinch"): rfx.append(min(N, a + 3))
                g = l.get("listener_gesture", "none")
                if g and g != "none": segs.append({"from": a, "to": min(N, b + 8), **gesture_pose(g, dd, gap, ks)})
            else:
                g = l.get("gesture", "none")
                pose = gesture_pose(g, dd, gap, ks) if g and g != "none" else {}
                segs.append({"from": max(1, a - 10), "to": min(N, b + 6), **pose})      # starts early: smoothing glides into it
        for sg in segs:                                   # a gesture keeps the item in the hand that holds it
            for arm, spec_ in hold_at(i, (sg["from"] + sg["to"]) // 2).items(): sg.setdefault(arm, spec_)
        holds = []
        for it in hprops[i]:
            for a_, b_ in it["ranges"]:                    # split where the holding pose changes (lying in bed holds it up by the face)
                f_ = a_
                while f_ <= b_:
                    arm = hold_at(i, f_); g_ = f_
                    while g_ + 1 <= b_ and hold_at(i, g_ + 1) == arm: g_ += 1
                    if arm: holds.append({"from": f_, "to": g_, **arm})
                    f_ = g_ + 1
        segs = act_segs[i] + segs + holds                 # the first segment that covers a frame wins
        default = gesture_pose(idle, dd, gap, ks) if idle != "relaxed" and (idle != "hold_hands" or i < 2) else {}
        if idle == "hold_hands" and n == 3 and i == 2: default = {}
        default = dict(default, **pfields[i])              # sitting / lying: legs, body height, lying rotation as smooth f-expressions
        spec = {"id": m["id"], "gaze": dd, "type": "soft_child" if kids[i] else "soft", "outfit": SOFT_OUTFIT.get(m["outfit"], m["outfit"]), "loc": [round(xs[i], 3), ys[i], 0],
                "blocking": blocking[i], "mouth": "soft",
                "look": {"hair": m["hair"], "hair_color": m["hair_color"], "beard": "none", "seed": i + 1,
                         "palette": {"cloth": m["colors"]["cloth"], "cloth2": m["colors"]["cloth2"]},
                         **({"signature": m["signature"], "sig_color": m.get("sig_color") or [0.92, 0.2, 0.3]}
                            if m.get("signature", "none") != "none" else {})},
                "head_shape": m.get("head_shape", "round"),
                "faces": ALL_FACES, "expressions": clean, "blinks": blinks, "talk": talk,
                "pose": {"default": default, "segments": segs, "smooth": 0.2, "calm": True}}
        if hprops[i]: spec["hand_props"] = hprops[i]
        for r_ in pex["reacts"].get(i, []):                  # hugged / pinched / hit by a pillow: a small flinch, no burst lines
            reacts.append(r_)
            if not CALM_ACTING: rfx.append(r_[0])
        if reacts: spec["reacts"] = reacts
        if rfx: spec["reaction_fx"] = rfx
        chars.append(spec)

    def group_at(f):
        """middle of the people in the frame at f (someone who has not come in yet / has left is not counted)"""
        ps = [pos_at(i, f) for i in range(n)]
        on = [p for p in ps if abs(p[0] - stage[0]) < OFF - 0.6] or ps
        return [round((min(p[0] for p in on) + max(p[0] for p in on)) / 2, 3), round(sum(p[1] for p in on) / len(on), 3), 0], \
            max(p[0] for p in on) - min(p[0] for p in on)
    shots = []
    for s in plan_shots(lt, c, N):
        kind = s["kind"]; typ, ov = SHOT[kind]
        line = c["lines"][s["line"]]
        fm = (s["a"] + s["b"]) // 2
        mid, spread = group_at(fm)
        on = [i for i in range(n) if abs(pos_at(i, fm)[0] - stage[0]) < OFF - 0.6]
        pst = {i: posture_at(i, fm) for i in on}
        lying = any(q == "lie" for q in pst.values())
        if kind in ("two", "wide", "both_close"): subj = mid
        elif kind == "listener": subj = addressee(s["line"])
        else: subj = line["speaker"]
        frame = dict(ov, subject=subj)
        if n == 3 and kind in ("two", "wide"): frame["size"] = ov.get("size", 3.6) * 1.25
        if kind in ("two", "wide"):                     # everyone in: the frame is 9/16 as wide as it is tall
            frame["size"] = round(max(frame["size"], (spread + 1.3) * 16 / 9), 2)
            if frame["size"] > 3.6: frame["y"] = -0.3          # a wider frame: keep the group low, less empty floor, more room above
        if kind == "both_close":                         # both heads whole, a little room at the sides
            frame["size"] = round(max(frame["size"], (min(spread, 2.2) + 1.15) * 16 / 9), 2)
        if kind == "both_close" and n == 3:              # two closest: the speaker and the one they talk to
            j = ids.index(line["speaker"]); o = ids.index(addressee(s["line"])); fm = (s["a"] + s["b"]) // 2
            pj, po = pos_at(j, fm), pos_at(o, fm)
            frame["subject"] = [round((pj[0] + po[0]) / 2, 3), round((pj[1] + po[1]) / 2, 3), 0]
        if kind == "both_close" and any(kids):
            frame["look_dz"] = 0.0
        if isinstance(subj, str) and kind in ("speaker", "listener"):      # clean single: whoever is beside them is pushed out
            j = ids.index(subj); pj = pos_at(j, fm)
            near = [pos_at(o, fm)[0] - pj[0] for o in on if o != j and abs(pos_at(o, fm)[0] - pj[0]) < 2.6]
            if near and (all(dx > 0 for dx in near) or all(dx < 0 for dx in near)):
                side = 1 if near[0] > 0 else -1; gap = min(abs(dx) for dx in near)
                half = frame["size"] * 9 / 16 / 2                     # half the frame width at the subject
                # subject slides toward the neighbour's side until the neighbour's head (seen r ~0.85 with head_scale + perspective) is out
                need = (half - (gap - 0.85)) / half + 0.36
                if need > 0: frame["x"] = round(side * min(0.5, need), 3)     # framing x > 0 = subject right of centre
        if isinstance(subj, str):                         # one person: frame them where their head really is
            j = ids.index(subj); q = posture_at(j, fm); kd = BODY_DIMS[bool(kids[j])]
            inb = inbed_at(j, fm)
            if q == "lie" or (q == "sit" and inb):          # in bed: from the foot of the bed, a little above, on the face on the pillow
                head = FURNITURE["bed"]["seat"] + (IN_BED["lie"] if q == "lie" else IN_BED["sit"]) * (0.75 if kids[j] else 1.0)
                frame["look_dz"] = round(frame.get("look_dz", 0) - (kd["head"] - head) + 0.3, 3); frame["height"] = "high"
                frame["size"] = 3.2
            elif q == "sit": frame["look_dz"] = round(frame.get("look_dz", 0) - (kd["hip"] - FURNITURE["chair"]["seat"]), 3)
        elif pst:
            if lying: frame["look_dz"] = round(frame.get("look_dz", 0) - 0.45, 3); frame["height"] = "high"
            elif any(q == "sit" for q in pst.values()): frame["look_dz"] = round(frame.get("look_dz", 0) - 0.15, 3)
        shots.append({"a": s["a"], "b": s["b"], "type": typ, "frame": frame})
    shots = action_shots(shots, pex["moments"], ids, xs, N)        # someone doing something: the camera goes to them
    words = [[w[0], w[1]] for w in wj["words"]]
    st = {
        "meta": {"title": c["title"], "slug": slug, "fps": FPS, "frames": N, "seed": 7, "voice": "voice.wav", "output": "out.mp4",
                 "samples": 32, "aspect": "9:16", "char_style": "2d" if style == "2d_grey" else style,
                 **({"char_tone": "grey"} if style == "2d_grey" else {}), "dialog": True, "fast_build": True},
        "sets": [{"id": "stage", "type": set_name, "params": params,
                  **({"props": [{"id": f"furn{k}_{fu['type']}", "type": fu["type"], "params": fu["params"], "loc": fu["loc"]}
                                for k, fu in enumerate(furniture)]
                                + [{"id": oid, "type": o["type"], "params": o.get("params") or {}, "loc": [o["x"], o["y"], 0],
                                    **({"rot": [0, 0, o["rot"]]} if o.get("rot") else {})} for oid, o in objs.items()]}
                               if (furniture or objs) else {})}],
        "camera": {"rig": "long", "shots": shots, "hand": 0.0},          # locked-off camera, no shake (cuts only)
        "chars": chars,
        "words": words,
        "captions": {"style": "word", "y": float(settings_of(slug).get("caption_y", -0.3))},   # one yellow word at a time, ~65 % down: clear of app UI
        "sound": {"auto": {"enabled": False}},             # voices only: no music, no sound effects
    }
    if lights: st["lights"] = [[int(f), v] for f, v in lights]
    if pex["flights"]: st["flights"] = pex["flights"]
    vis = object_visibility(objs, pex["obj_states"], N)
    if vis: st["visibility"] = vis
    errs = storycheck.check_story(st, lib)
    if errs: raise ValueError("story.json lỗi: " + "; ".join(errs[:6]))
    _w(os.path.join(d, "story.json"), st)
    log(f"story.json: {N} khung ({N / FPS:.1f} s), {len(shots)} cú máy, {len(chars)} nhân vật, bối cảnh {set_name}, nhân vật {style}."
        + (f" Đồ nội thất thêm: {', '.join(fu['type'] for fu in furniture)}." if furniture else ""))
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
