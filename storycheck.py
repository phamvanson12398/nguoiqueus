"""story.json checks that need no Blender: JSON Schema + library references + names.
Used by builder.py (before building) and claude_bridge.py (to validate plan_shots output)."""
import json, os

ROOT = os.path.dirname(os.path.abspath(__file__))
FACES = ("neutral", "happy", "smirk", "wink", "angry", "shock", "worried", "grumpy", "focus", "smug_closed")
REACTS = ("hop", "flinch", "shiver", "proud")
SFX_NAMES = ("whoosh", "swish", "pop", "tick", "boing", "thud", "bonk", "step", "slide_up", "slide_down", "steam", "rumble",
             "ding", "squeak", "zip_out", "crash", "scratch", "horn", "chug", "sad_trombone", "gulp", "cash")


class LibIndex:
    """read-only view of library/ (no Blender needed)"""

    def __init__(self, root=os.path.join(ROOT, "library")):
        self.root = root; self._json = {}

    def path(self, kind, name, fname):
        return os.path.join(self.root, kind, name, fname)

    def exists(self, kind, name):
        if kind == "motions": return os.path.exists(os.path.join(self.root, "motions", name + ".json"))
        if kind == "chars": return os.path.exists(self.path("chars", name, "char.json"))
        if kind == "cultures": return os.path.exists(self.path("cultures", name, "culture.json"))
        if kind == "outfits": return os.path.exists(self.path("outfits", name, "outfit.json"))
        return os.path.exists(self.path(kind, name, "build.py"))

    def list(self, kind):
        d = os.path.join(self.root, kind)
        if not os.path.isdir(d): return []
        if kind == "motions": return sorted(f[:-5] for f in os.listdir(d) if f.endswith(".json"))
        return sorted(n for n in os.listdir(d) if self.exists(kind, n))

    def json(self, kind, name):
        key = (kind, name)
        if key not in self._json:
            p = os.path.join(self.root, "motions", name + ".json") if kind == "motions" else \
                self.path(kind, name, {"cultures": "culture.json", "outfits": "outfit.json"}.get(kind, "char.json"))
            if not os.path.exists(p):
                raise KeyError(f"library {kind}/{name} not found (have: {', '.join(self.list(kind))})")
            self._json[key] = json.load(open(p, encoding="utf-8"))
        return self._json[key]

    def meta(self, kind, name):
        p = self.path(kind, name, {"chars": "char.json", "cultures": "culture.json", "outfits": "outfit.json"}.get(kind, "meta.json"))
        return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}

    def catalog(self):
        """compact listing for prompts: kind -> [{name, title, description, params}]"""
        out = {}
        for kind in ("sets", "props", "chars"):
            items = []
            for n in self.list(kind):
                m = self.meta(kind, n)
                d = {"name": n, "title_vi": m.get("title_vi", ""), "description_vi": m.get("description_vi", "")}
                if kind != "chars":
                    d["params"] = {k: ({"default": v.get("default"), "desc_vi": v["desc_vi"]} if v.get("desc_vi") else v.get("default"))
                                   for k, v in m.get("params", {}).items()}
                    if m.get("parts"): d["parts"] = m["parts"]
                    for extra in ("anchors", "space", "camera_vi"):
                        if m.get(extra): d[extra] = m[extra]
                    if m.get("dim"): d["dim"] = m["dim"]
                else:
                    d["faces"] = m.get("faces", [])
                if m.get("status") == "draft": d["status"] = "draft"
                items.append(d)
            out[kind] = items
        out["cultures"] = [{"name": n, "title_vi": self.json("cultures", n).get("title_vi", ""), "years": self.json("cultures", n).get("years"),
                             "roles": self.json("cultures", n).get("roles", {})} for n in self.list("cultures")]
        out["outfits"] = [{"name": n, "title_vi": self.json("outfits", n).get("title_vi", ""), "culture": self.json("outfits", n).get("culture"),
                            "role": self.json("outfits", n).get("role")} for n in self.list("outfits")]
        out["motions"] = [{"name": n, "params": self.json("motions", n).get("params", {}),
                           "description_vi": self.json("motions", n).get("description_vi", "")} for n in self.list("motions")]
        return out


def check_story(st, lib=None, pending=()):
    """-> list of error strings.  pending = {(kind, name)} items that will be designed (allowed as references)."""
    lib = lib or LibIndex()
    from jsonval import validate
    schema = json.load(open(os.path.join(ROOT, "story.schema.json"), encoding="utf-8"))
    errs = validate(st, schema)
    if errs: return errs
    pend = set(pending)

    def known(kind, name): return lib.exists(kind, name) or (kind, name) in pend
    ids = set()

    def new_id(i, where):
        if i in ids: errs.append(f"{where}: duplicate id '{i}'")
        ids.add(i)
    for k, s in enumerate(st.get("sets", [])):
        w = f"sets[{k}]"
        if not known("sets", s["type"]): errs.append(f"{w}: unknown set '{s['type']}' (have {lib.list('sets')})")
        for j, p in enumerate(s.get("props", [])):
            if not known("props", p["type"]): errs.append(f"{w}.props[{j}]: unknown prop '{p['type']}' (have {lib.list('props')})")
            new_id(p["id"], f"{w}.props[{j}]")
    for k, c in enumerate(st.get("chars", [])):
        w = f"chars[{k}]"
        if not known("chars", c["type"]): errs.append(f"{w}: unknown character '{c['type']}' (have {lib.list('chars')})")
        new_id(c["id"], w)
        faces = c.get("faces")
        if faces is None and lib.exists("chars", c["type"]): faces = lib.json("chars", c["type"]).get("faces")
        for j, p in enumerate(c.get("props", [])):
            if not known("props", p["type"]): errs.append(f"{w}.props[{j}]: unknown prop '{p['type']}'")
            new_id(p["id"], f"{w}.props[{j}]")
        for j, e in enumerate(c.get("expressions", [])):
            if faces and e[1] not in faces: errs.append(f"{w}.expressions[{j}]: face '{e[1]}' is not built for this character (faces: {faces})")
    for k, t in enumerate(st.get("tracks", [])):
        if "use" in t and not lib.exists("motions", t["use"]): errs.append(f"tracks[{k}]: unknown motion '{t['use']}' (have {lib.list('motions')})")
    ch_ids = {c["id"] for c in st.get("chars", [])}
    for g in st.get("sound", {}).get("auto", {}).get("gesture_chars", []):
        if g not in ch_ids: errs.append(f"sound.auto.gesture_chars: no character '{g}'")
    fac_ids = {f["id"] for f in st.get("factions", [])}
    facs = {f["id"]: f for f in st.get("factions", [])}

    def check_outfit(w, ref, fid):
        cul = (facs.get(fid) or {}).get("culture")
        if known("outfits", ref): return
        if cul and lib.exists("cultures", cul) and ref in lib.json("cultures", cul).get("roles", {}):
            o = lib.json("cultures", cul)["roles"][ref]
            if not known("outfits", o): errs.append(f"{w}: role '{ref}' of culture '{cul}' uses outfit '{o}', which does not exist (add to missing)")
            return
        if cul and (("cultures", cul) in pend): return
        if cul and not lib.exists("cultures", cul):
            errs.append(f"{w}: faction culture '{cul}' is not in the library (have {lib.list('cultures')}; add it to missing as kind cultures)"); return
        errs.append(f"{w}: '{ref}' is neither an outfit (have {lib.list('outfits')}) nor a role of culture '{cul}'")
    for k, c in enumerate(st.get("chars", [])):
        if c.get("outfit"): check_outfit(f"chars[{k}].outfit", c["outfit"], c.get("faction"))
        elif c.get("role"): check_outfit(f"chars[{k}].role", c["role"], c.get("faction"))
        for j, ch in enumerate(c.get("outfit_changes", [])):
            check_outfit(f"chars[{k}].outfit_changes[{j}]", ch[1], ch[2] if len(ch) > 2 else c.get("faction"))
    for k, cr in enumerate(st.get("crowds", [])):
        if cr.get("faction") and cr["faction"] not in fac_ids: errs.append(f"crowds[{k}].faction: no faction '{cr['faction']}'")
        if cr.get("outfit") or cr.get("role"): check_outfit(f"crowds[{k}]", cr.get("outfit") or cr["role"], cr.get("faction"))
    for c in st.get("chars", []):
        if "faction" in c and c["faction"] not in fac_ids: errs.append(f"chars.{c['id']}.faction: no faction '{c['faction']}' (have {sorted(fac_ids)})")
    for k, cd in enumerate(st.get("cards", [])):
        if cd["to"] < cd["from"]: errs.append(f"cards[{k}]: 'to' ({cd['to']}) before 'from' ({cd['from']})")
    N = st["meta"]["frames"]
    cam = st["camera"]
    if cam.get("rig") == "long" and st["meta"].get("aspect", "9:16") != "16:9":
        errs.append("camera: rig 'long' is for long-form videos, set meta.aspect to '16:9'")
    spans = [(s["a"], s["b"]) for s in (cam.get("shots") or cam.get("seqs") or [])]
    if spans:
        spans.sort()
        if spans[0][0] != 1: errs.append(f"camera: first shot/sequence must start at frame 1 (starts at {spans[0][0]})")
        for (a0, b0), (a1, b1) in zip(spans, spans[1:]):
            if a1 != b0 + 1: errs.append(f"camera: gap or overlap between {a0}-{b0} and {a1}-{b1}")
        if spans[-1][1] != N: errs.append(f"camera: last shot/sequence ends at {spans[-1][1]}, video has {N} frames")
    return errs


if __name__ == "__main__":
    import sys
    e = check_story(json.load(open(sys.argv[1], encoding="utf-8")))
    print("STORY OK" if not e else "STORY ERRORS:\n  " + "\n  ".join(e)); sys.exit(1 if e else 0)
