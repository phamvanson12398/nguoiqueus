"""Shorts cut from a long video.

Claude picks 3-5 moments (claude_bridge.pick_clips); for each one the tool makes a Short project under
projects/<slug>/clips/NN/: the story of the part that contains the moment, re-framed for 9:16 (the scene is 3D, so the camera
is solved again for a vertical frame instead of cropping), Shorts pop captions, a hook card for the first seconds and a
"full video" card at the end. `meta.clip` = the frames to render; the builder puts the matching slice of the part's mix under it.

    python clips.py make <slug>          (after claude_bridge.pick_clips wrote clips/index.json)
"""
import copy, json, os, shutil, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECTS = os.path.join(ROOT, "projects")
FPS = 30


def _j(p, default=None):
    try: return json.load(open(p, encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError): return default


def clips_dir(slug):
    return os.path.join(PROJECTS, slug, "clips")


def clip_slug(slug, k):
    return f"{slug}/clips/{int(k):02d}"


def parts(slug):
    idx = _j(os.path.join(PROJECTS, slug, "chapters", "index.json"), {"chapters": []})
    return idx["chapters"]


def part_of(slug, start, end):
    """the part that holds [start, end] seconds of the full video (None if it straddles a seam)"""
    for c in parts(slug):
        if c["start"] - 0.05 <= start and end <= c["end"] + 0.05: return c
    return None


def snap(slug, start, end):
    """move start to the first word at/after it and end to the end of the last word before it"""
    W = (_j(os.path.join(PROJECTS, slug, "words.json")) or {}).get("words") or []
    if not W: return start, end
    s = next((float(w[0]) for w in W if float(w[0]) >= start - 0.15), start)
    ends = [float(W[i + 1][0]) - 0.02 if i + 1 < len(W) else float(w[0]) + 0.6 for i, w in enumerate(W)]
    e = max((t for t, w in zip(ends, W) if float(w[0]) < end), default=end)
    return s, min(e + 0.35, end + 0.6)


def make_clip(slug, k, pick):
    """projects/<slug>/clips/NN/: story.json (9:16, meta.clip), voice.wav + words.json of the part"""
    c = part_of(slug, pick["start_sec"], pick["end_sec"])
    if c is None: raise ValueError(f"clip {k}: {pick['start_sec']}-{pick['end_sec']} s nằm vắt qua hai phần")
    pd = os.path.join(PROJECTS, slug, "chapters", f"{c['n']:02d}")
    st = _j(os.path.join(pd, "story.json"))
    if not st: raise ValueError(f"phần {c['n']} chưa có story.json")
    st = copy.deepcopy(st)
    A = max(1, int(round((pick["start_sec"] - c["start"]) * FPS)) + 1)
    B = min(st["meta"]["frames"], int(round((pick["end_sec"] - c["start"]) * FPS)) + 1)
    m = st["meta"]
    m["aspect"] = "9:16"; m["output"] = "short.mp4"; m["title"] = pick.get("title", m.get("title", ""))
    m["clip"] = {"from": A, "to": B, "source": f"{slug} phần {c['n']}", "title": pick.get("title", "")}
    m["part_first"] = m["part_last"] = False
    st["captions"] = {"style": "pop"}
    # a vertical frame shows the same HEIGHT as the wide one but a third of the width: wide/establishing shots would leave the
    # characters as dots, so a Short frames them tighter
    PRESET_H = {"establishing": 14.0, "wide": 7.0, "full": 3.5}
    for s in st["camera"].get("shots", []):
        fr = s.get("frame")
        if fr and s.get("type") in ("establishing", "wide", "full") and fr.get("height") != "top" and s.get("type") not in ("map", "board"):
            fr["size"] = round(float(fr.get("size", PRESET_H[s["type"]])) * (0.55 if s["type"] != "full" else 0.8), 2)
    keep = [cd for cd in st.get("cards", []) if cd.get("style") not in ("fade", "chapter", "endscreen", "watermark")
            and cd.get("to", 0) >= A and cd.get("from", 0) <= B]
    hook = (pick.get("hook_text") or "").upper()
    for cd in keep:                                   # nothing on top of the hook
        if hook and cd.get("from", 0) < A + 75: cd["from"] = max(cd.get("from", 0), A + 76)
        if cd.get("to", 0) > B - 61: cd["to"] = B - 61   # ... nor on top of the "full video" end label
    keep = [cd for cd in keep if cd.get("to", 0) >= cd.get("from", 1)]
    if hook: keep.append({"style": "title", "text": hook, "from": A, "to": A + 75, "pos": [0, 0.62], "size": 0.075})
    keep.append({"style": "label", "text": pick.get("end_text") or "FULL VIDEO ON THE CHANNEL", "from": max(A, B - 60), "to": B,
                 "pos": [0, 0.6], "size": 0.05})
    st["cards"] = keep
    d = os.path.join(clips_dir(slug), f"{int(k):02d}"); os.makedirs(d, exist_ok=True)
    for f in ("voice.wav", "words.json"):
        if os.path.exists(os.path.join(pd, f)): shutil.copy2(os.path.join(pd, f), os.path.join(d, f))
    json.dump(st, open(os.path.join(d, "story.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    info = dict(pick, k=int(k), part=c["n"], frames=[A, B], seconds=round((B - A + 1) / FPS, 1))
    json.dump(info, open(os.path.join(d, "clip.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return info


def make_all(slug, picks, log=print):
    out = []
    for k, p in enumerate(picks, 1):
        s, e = snap(slug, float(p["start_sec"]), float(p["end_sec"]))
        c0 = part_of(slug, float(p["start_sec"]), float(p["end_sec"]))
        if c0: s, e = max(s, c0["start"]), min(e, c0["end"] - 0.05)       # snapping must not push it over a seam
        p = dict(p, start_sec=round(s, 2), end_sec=round(e, 2))
        try:
            info = make_clip(slug, k, p); out.append(info)
            log(f"Short {k:02d} «{p.get('title', '')}»: phần {info['part']}, khung {info['frames'][0]}-{info['frames'][1]} ({info['seconds']} s)")
        except ValueError as e_:
            log(f"Short {k:02d}: bỏ qua ({e_})")
    json.dump({"clips": out}, open(os.path.join(clips_dir(slug), "index.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return out


def status(slug):
    d = clips_dir(slug); idx = _j(os.path.join(d, "index.json"), {"clips": []}); out = []
    for k0, c in enumerate(idx["clips"], 1):
        k = int(c.get("k", k0)); cd = os.path.join(d, f"{k:02d}"); pv = os.path.join(cd, "preview")
        out.append(dict(c, k=k, rendered=os.path.exists(os.path.join(cd, "short.mp4")),
                        previews=sorted(f for f in os.listdir(pv) if f.endswith(".png")) if os.path.isdir(pv) else []))
    return out


if __name__ == "__main__":
    if sys.argv[1] == "make":
        print(make_all(sys.argv[2], _j(os.path.join(clips_dir(sys.argv[2]), "picks.json"))["clips"]))
