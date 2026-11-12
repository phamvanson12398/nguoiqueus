"""YouTube package: chapter timestamps from the real voice timing, description text, thumbnail stories (1280x720).

    python youtube.py stamps <slug>                 print the chapter timestamps the description will use
    python youtube.py thumbstory <slug> <concept.json> <out_dir>   write a thumbnail story.json

Claude writes titles / description / tags / thumbnail concepts (claude_bridge.youtube_package); this module only does
the deterministic parts: real timestamps (YouTube needs 00:00 first, >= 3 marks, >= 10 s apart) and building a
thumbnail scene out of the video's own characters, outfits and sets.
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECTS = os.path.join(ROOT, "projects")
POSES = {   # thumbnail poses -> arm specs (torso coords)
    "stand": {}, "arms_up": {"armL": ["ik", [-0.55, 1.15], -1], "armR": ["ik", [0.55, 1.15], 1]},
    "point_right": {"armR": ["ik", [0.75, 0.62], 1]}, "point_left": {"armL": ["ik", [-0.75, 0.62], -1]},
    "hands_cheeks": {"armL": ["ik", [-0.42, 1.28], -1], "armR": ["ik", [0.42, 1.28], 1]},
    "cross_arms": {"armL": ["ik", [0.22, 0.45], -1], "armR": ["ik", [-0.22, 0.5], 1]},
    "fist_up": {"armR": ["ik", [0.42, 1.25], 1]}, "shrug": {"armL": ["ik", [-0.6, 0.62], 1], "armR": ["ik", [0.6, 0.62], -1]},
}


def _j(p, d=None):
    try: return json.load(open(p, encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError): return d


def fmt(sec):
    sec = int(round(sec)); h, r = divmod(sec, 3600); m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def sequence_starts(slug):
    """[(seconds, sequence)] from the full words.json: the time of each sequence's first word"""
    import longform
    d = os.path.join(PROJECTS, slug)
    content = _j(os.path.join(d, "content.json")); words = _j(os.path.join(d, "words.json"))
    if not content or not words: return []
    W = words["words"]; k = 0; out = []
    counts = [len(longform.tokens(s.get("vo_en", ""))) for s in content["sequences"]]
    total = sum(counts) or 1
    if total != len(W): counts = [round(c * len(W) / total) for c in counts]
    for s, c in zip(content["sequences"], counts):
        if k < len(W): out.append((W[k][0] if k else 0.0, s))
        k += c
    return out


def timestamps(slug, beat_titles=None, min_gap=10.0):
    """timestamp list [(sec, title)] from the sequence (beat) starts of the real voice; first at 0, >= min_gap apart"""
    content = _j(os.path.join(PROJECTS, slug, "content.json")) or {}
    beat_titles = {int(k): v for k, v in (beat_titles or {}).items()}
    marks = []
    for t, s in sequence_starts(slug):           # one seamless video: beat names only, no chapter names
        title = beat_titles.get(int(s.get("id", 0)))
        if title: marks.append((t, title))
    if not marks: return []
    marks[0] = (0.0, marks[0][1])
    out = [marks[0]]
    for t, title in marks[1:]:
        if t - out[-1][0] >= min_gap: out.append((t, title))
    return out if len(out) >= 3 else []


def description(pkg, stamps):
    lines = [pkg["description_hook"].strip(), "", pkg["description_body"].strip()]
    if stamps:
        lines += ["", "Timestamps:"] + [f"{fmt(t)} {title}" for t, title in stamps]
    if pkg.get("sources"):
        lines += ["", "Sources:"] + [f"- {s['source']}" + (f" ({s['url']})" if s.get("url") else "") for s in pkg["sources"]]
    if pkg.get("credits"): lines += ["", pkg["credits"].strip()]
    if pkg.get("hashtags"): lines += ["", " ".join("#" + h.lstrip("#") for h in pkg["hashtags"][:3])]
    return "\n".join(lines).strip() + "\n"


def source_story(slug):
    """the story to borrow characters/sets from: the project's story.json, or the first chapter that has one"""
    d = os.path.join(PROJECTS, slug)
    st = _j(os.path.join(d, "story.json"))
    if st: return st, d
    idx = _j(os.path.join(d, "chapters", "index.json"), {"chapters": []})
    for c in idx["chapters"]:
        cd = os.path.join(d, "chapters", f"{c['n']:02d}"); st = _j(os.path.join(cd, "story.json"))
        if st: return st, cd
    return None, d


def all_stories(slug):
    d = os.path.join(PROJECTS, slug); out = []
    st = _j(os.path.join(d, "story.json"))
    if st: out.append(st)
    idx = _j(os.path.join(d, "chapters", "index.json"), {"chapters": []})
    for c in idx["chapters"]:
        st = _j(os.path.join(d, "chapters", f"{c['n']:02d}", "story.json"))
        if st: out.append(st)
    return out


def cast(slug):
    """characters and sets available for thumbnails: {chars: {id: spec}, sets: {id: spec}, factions: {...}}"""
    chars, sets, facs = {}, {}, {}
    for st in all_stories(slug):
        for c in st.get("chars", []): chars.setdefault(c["id"], c)
        for s in st.get("sets", []): sets.setdefault(s.get("id", s["type"]), s)
        for f in st.get("factions", []): facs.setdefault(f["id"], f)
    return {"chars": chars, "sets": sets, "factions": facs}


def _char_spec(cs, ch, loc):
    src = cs["chars"][ch["id"]]
    spec = {key: src[key] for key in ("id", "type", "faction", "role", "outfit", "look", "props") if key in src}
    spec["loc"] = loc
    spec["expressions"] = [[1, ch.get("expression", "shock")]]
    tilt = max(-0.2, min(0.2, float(ch.get("tilt", 0.0)) * (0.0175 if abs(ch.get("tilt", 0.0)) > 1 else 1)))   # degrees by mistake -> radians
    spec["pose"] = {"default": dict(POSES.get(ch.get("pose", "stand"), {}), tilt=tilt)}
    return spec


def _home(cs, ch_id):
    src = cs["chars"][ch_id]
    loc = src.get("loc") or src.get("blocking", {}).get("default", {}).get("location") or [0, 0, 0]
    return [float(x) if not isinstance(x, str) else 0.0 for x in loc]


def _finished(set_spec):
    """a data set (map/board/paper) as it looks at the end: everything drawn from frame 1 (a thumbnail is frame 2)"""
    sp = json.loads(json.dumps(set_spec)); p = sp.get("params", {})
    for key in ("arrows", "strokes", "circles"):
        for it in p.get(key, []):
            if "from" in it: it["from"], it["to"] = 1, 2
    for key in ("regions", "cities", "labels", "units", "fills"):
        for it in p.get(key, []):
            it.pop("to", None)
            if "from" in it: it["from"] = 1
            if it.get("moves"): it["at"] = it["moves"][-1][1]; it.pop("moves")
    return sp


def thumb_story(slug, concept):
    """concept (from Claude) -> story.json of a 16:9 thumbnail scene.  Fixed layouts place people and text so they never collide:
    hero: one person big on a third, headline on the other half | vs: two people on the thirds, VS in the middle, headline in the
    bottom band | map: the map fills the frame, headline in the top band | object: like hero, framed on 'subject'"""
    cs = cast(slug); layout = concept.get("layout", "hero")
    set_id = concept.get("set") if concept.get("set") in cs["sets"] else None
    people = [c for c in concept.get("chars", []) if c.get("id") in cs["chars"]]
    sets = [_finished(cs["sets"][set_id])] if set_id else []
    chars = []; cards = []; txt = concept.get("text", "").upper().strip()
    yel = concept.get("text_color", [1.0, 0.86, 0.05])
    side = 1 if (people and people[0].get("x", 0.3) >= 0) else -1            # which third the hero stands on
    if layout == "map" and set_id:
        a = concept.get("subject") or "center"
        subject = a if (isinstance(a, list) or "." in str(a)) else f"{set_id}.{a}"
        shot = {"type": "map", "frame": {"subject": subject, "size": concept.get("size", 6.0), "move": "static_drift", "height": "top"}}
        if txt: cards.append({"style": "thumb_text", "text": txt, "pos": [0, 0.62], "size": 0.16, "max_w": 0.9, "max_h": 0.34, "color": yel, "rot": 0})
    elif layout == "vs" and len(people) >= 2:
        home = _home(cs, people[0]["id"]); H = 2.6; W = H * 16 / 9; dx = 0.25 * W
        chars = [_char_spec(cs, people[0], [home[0] - dx, home[1], home[2]]), _char_spec(cs, people[1], [home[0] + dx, home[1], home[2]])]
        shot = {"type": "medium", "frame": {"subject": [home[0], home[1], home[2]], "size": H, "move": "static_drift", "y": -0.18}}
        cards.append({"style": "thumb_text", "text": "VS", "pos": [0, 0.1], "size": 0.2, "color": [0.95, 0.12, 0.05], "rot": -4})
        if txt: cards.append({"style": "thumb_text", "text": txt.replace("\n", " "), "pos": [0, -0.74], "size": 0.13, "max_w": 0.94, "max_h": 0.24, "color": yel, "rot": 0})
    else:                                                                        # hero / object
        if people:
            home = _home(cs, people[0]["id"]); chars = [_char_spec(cs, people[0], home)]      # hero: ONE face, big
            subj = home
        else:
            subj = concept.get("subject") or (f"{set_id}.center" if set_id else [0, 0, 0])
            if isinstance(subj, str) and "." not in subj and set_id: subj = f"{set_id}.{subj}"
        shot = {"type": "closeup" if people else concept.get("shot", "insert"),
                "frame": {"subject": subj, "move": "static_drift", "x": 0.33 * side, "angle": -12 * side,
                          **({"size": concept["size"]} if concept.get("size") else ({"size": 2.0} if people else {}))}}
        if txt: cards.append({"style": "thumb_text", "text": txt, "pos": [-0.47 * side, 0.12], "size": 0.17, "max_w": 0.46, "max_h": 0.8,
                              "color": yel, "rot": 4 * side})
        if concept.get("arrow") and layout == "object":                         # arrow from the headline to the object
            cards.append({"style": "arrow", "pos": [0.12 * side, -0.05], "tail": [-0.3 * side, -0.35]})
    if concept.get("text2") and layout != "vs":
        cards.append({"style": "thumb_text", "text": concept["text2"].upper(), "pos": [0, -0.78], "size": 0.08, "max_w": 0.8, "max_h": 0.18,
                      "color": [1, 1, 1], "rot": 0})
    for c in cards: c.update({"from": 1, "to": 3})
    shot.update({"a": 1, "b": 3})
    # a thumbnail must read at phone size: dark grades (night, storm, dusk, cold) kill the contrast (seen: a night-blue hero)
    if concept.get("grade") and concept["grade"] not in ("night", "storm", "dusk", "cold"): shot["grade"] = concept["grade"]
    st = {"meta": {"title": f"thumbnail {concept.get('id', 1)}", "fps": 30, "frames": 3, "aspect": "16:9", "samples": 48, "output": "thumb.mp4"},
          "factions": list(cs["factions"].values()), "sets": sets, "chars": chars,
          "camera": {"rig": "long", "dof": {"fstop": concept.get("fstop", 1.8 if layout != "map" else 5.6)}, "shots": [shot]},
          "captions": {"style": "off"}, "cards": cards, "sound": {"master": {"lufs": -14}}}
    if not st["factions"]: st.pop("factions")
    return st


def ref_story(slug, char_id, expression="happy"):
    """reference picture of ONE character for outside image AIs (attach it so they draw the same person): full body,
    front, plain bright background, no text, 3D style of the video"""
    cs = cast(slug)
    spec = _char_spec(cs, {"id": char_id, "expression": expression, "pose": "stand"}, [0, 0, 0])
    spec.pop("props", None)
    shot = {"a": 1, "b": 3, "type": "full", "frame": {"subject": [0, 0, 0], "size": 2.9, "move": "static_drift", "y": -0.02}}
    st = {"meta": {"title": f"ref {char_id}", "fps": 30, "frames": 3, "aspect": "16:9", "samples": 32, "output": "ref.mp4"},
          "factions": list(cs["factions"].values()), "sets": [], "chars": [spec],
          "world": {"clouds": 0},
          "camera": {"rig": "long", "shots": [shot]}, "captions": {"style": "off"}, "cards": [], "sound": {"master": {"lufs": -14}}}
    if not st["factions"]: st.pop("factions")
    return st


def cast_descriptions(slug):
    """plain-language description of every character (look, outfit, colours) for image prompts"""
    import storycheck
    lib = storycheck.LibIndex(); cs = cast(slug); out = {}
    facs = cs["factions"]
    for cid, c in cs["chars"].items():
        d = {"id": cid, "type": c.get("type")}
        fac = facs.get(c.get("faction")) or {}
        if fac: d["faction"] = {"label": fac.get("label"), "color_rgb": fac.get("color"), "culture": fac.get("culture")}
        of = c.get("outfit")
        if not of and c.get("role") and fac.get("culture") and lib.exists("cultures", fac["culture"]):
            of = lib.json("cultures", fac["culture"]).get("roles", {}).get(c["role"])
        if of and lib.exists("outfits", of):
            o = lib.json("outfits", of); d["outfit"] = {"id": of, "title": o.get("title_vi"), "description": o.get("description_vi"),
                                                       "silhouette": o.get("silhouette_vi")}
        elif lib.exists("chars", c.get("type", "")):
            L = lib.json("chars", c["type"]); d["character"] = {"title": L.get("title_vi"), "description": L.get("description_vi")}
        if c.get("look"): d["look"] = c["look"]
        out[cid] = d
    return out


if __name__ == "__main__":
    if sys.argv[1] == "stamps":
        for t, title in timestamps(sys.argv[2]): print(fmt(t), title)
    elif sys.argv[1] == "thumbstory":
        st = thumb_story(sys.argv[2], json.load(open(sys.argv[3], encoding="utf-8")))
        os.makedirs(sys.argv[4], exist_ok=True); json.dump(st, open(os.path.join(sys.argv[4], "story.json"), "w"), indent=1)
