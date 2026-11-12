"""WhyShorts builder: story.json -> Blender scene (+ preview PNGs or mp4).

    blender -b -P builder.py -- projects/<slug>/story.json                      build + checks only
    blender -b -P builder.py -- projects/<slug>/story.json --preview 50,200,366  PNG previews (35 %)
    blender -b -P builder.py -- projects/<slug>/story.json --render              full mp4 (1080x1920, or 1920x1080 with meta.aspect 16:9)
    options: --pct 35  --samples 16  --out <dir>  --check (validate story.json only, no Blender scene)

The story format is described in STORY.md and story.schema.json.  Library items live in
library/{sets,props,chars,motions}.  voice.wav is read from the story's folder; sfx_music.wav,
preview/ and the mp4 are written there (or to --out).
"""
import bpy, os, sys, json, math, random, time, importlib.util
import numpy as np

# ---------------- paths, fresh core modules ----------------
_here = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() and os.path.exists(__file__) else os.getcwd()
ROOT = os.environ.get("WHYSHORTS_ROOT") or _here
if ROOT not in sys.path: sys.path.insert(0, ROOT)
for _m in [m for m in sys.modules if m == "core" or m.startswith("core.") or m.startswith("whylib_")]:
    del sys.modules[_m]

import core
from core import ctx, look, geo, timing, camera, faces, chars, fx, captions, sfx, mixer, cards, overlay, outfits, audio_long, fx_long
from core.expr import Env, ExprError
from core import framing, body3d
from mathutils import Vector
import storycheck
from storycheck import LibIndex

LIB_DIR = os.path.join(ROOT, "library")
ANIM_PROPS = ("location", "rotation_euler", "scale")
POSE_FIELDS = ("armL", "armR", "legs", "tilt", "body", "lean")


class StoryError(Exception):
    pass


# =====================================================================
#  library
# =====================================================================
class Library(LibIndex):
    """library/ index (storycheck.LibIndex) + loading and running build.py files"""

    def __init__(self, root=LIB_DIR):
        super().__init__(root); self._mods = {}

    def module(self, kind, name):
        key = (kind, name)
        if key not in self._mods:
            p = self.path(kind, name, "build.py")
            if not os.path.exists(p):
                raise StoryError(f"library {kind}/{name} not found (have: {', '.join(self.list(kind))})")
            spec = importlib.util.spec_from_file_location(f"whylib_{kind}_{name}", p)
            mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
            sys.modules[spec.name] = mod
            self._mods[key] = mod
        return self._mods[key]

    def json(self, kind, name):
        key = (kind, name)
        if key not in self._json:
            p = os.path.join(self.root, "motions", name + ".json") if kind == "motions" else \
                self.path(kind, name, {"cultures": "culture.json", "outfits": "outfit.json"}.get(kind, "char.json"))
            if not os.path.exists(p):
                raise StoryError(f"library {kind}/{name} not found (have: {', '.join(self.list(kind))})")
            self._json[key] = json.load(open(p, encoding="utf-8"))
        return self._json[key]

    def prop(self, type_, params):
        """build a prop; params must contain 'name' (object name) and may contain 'parent'"""
        return self.module("props", type_).build(params, self)

    def set(self, type_, params):
        return self.module("sets", type_).build(params, self) or {}


def check_story(st, lib):
    errs = storycheck.check_story(st, lib)
    assert set(storycheck.SFX_NAMES) == set(sfx.SFX), "storycheck.SFX_NAMES out of date"
    assert set(storycheck.FACES) == set(faces.KINDS), "storycheck.FACES out of date"
    return errs


# =====================================================================
#  builder
# =====================================================================
class Builder:
    def __init__(self, story_path, out_dir=None, lib=None):
        self.path = os.path.abspath(story_path)
        self.st = json.load(open(self.path, encoding="utf-8"))
        self.dir = os.path.dirname(self.path)
        self.out = out_dir or self.dir
        self.lib = lib or Library()
        self.chars = {}                 # id -> Char
        self.char_specs = []
        self.story_props = set()
        self.noline_roots = []
        self.anchors = {}
        self.report = {"warnings": []}
        self.dof_on = False
        self.outfit_vis = []          # (group empty, [(a, b)]) for outfit changes
        self.crowds = {}              # id -> crowd root
        self.crowd_tpl = []           # (collection, template char root, location)

    # ---------- helpers ----------
    def obj(self, name, where=""):
        o = bpy.data.objects.get(name)
        if o is None:
            raise StoryError(f"{where}: no object named '{name}'")
        return o

    def place(self, o, spec):
        for k in ("loc", "rot", "scale"):
            if k in spec:
                setattr(o, {"loc": "location", "rot": "rotation_euler", "scale": "scale"}[k], tuple(self.env.const(spec[k], f"{k}")))

    # ---------- tracks ----------
    def resolve_segments(self, segs, params, where):
        out = []
        for i, s in enumerate(segs):
            if "ranges" in s: rng = [tuple(self.env.const(r, f"{where}[{i}].ranges", params)) for r in s["ranges"]]
            elif "from" in s: rng = [(self.env.const(s["from"], where, params), self.env.const(s["to"], where, params))]
            else: rng = [(-10 ** 9, 10 ** 9)]
            out.append((rng, s))
        return out

    def run_track(self, tr, target=None, where="track"):
        o = target or self.obj(tr["target"], where)
        params = {}
        if "use" in tr:
            m = self.lib.json("motions", tr["use"])
            params = dict(m.get("params", {}))
            for k, v in tr.get("params", {}).items():
                params[k] = self.env.const(v, f"{where}.params.{k}")
            segs, default = m.get("segments", []), m.get("default")
        else:
            segs, default = tr.get("segments", []), tr.get("default")
        segs = self.resolve_segments(segs, params, where)
        a, b = tr.get("frames", [1, ctx.N])
        tlet = tr.get("let")
        for f in range(a, b + 1):
            spec = next((s for rng, s in segs if any(r0 <= f <= r1 for r0, r1 in rng)), default)
            if spec is None: continue
            ns = self.env.frame_ns(f, tlet, where, extra=params)
            for k, src in (spec.get("let") or {}).items():
                ns[k] = self.env.val(src, ns, where)
            for prop, v in spec.items():
                if prop in ("from", "to", "ranges", "let", "note"): continue
                val = self.env.val(v, ns, f"{where}.{prop}")
                setattr(o, prop, tuple(val) if isinstance(val, list) else val)
                o.keyframe_insert(prop, frame=f)
        return o

    # ---------- characters ----------
    def outfit_for(self, cs, ref=None, faction_id=None):
        """(outfit json, faction, culture) for a character spec; ref = outfit id or role name (outfit changes)"""
        fac = next((f for f in self.st.get("factions", []) if f["id"] == (faction_id or cs.get("faction"))), None)
        cul = outfits.load("cultures", fac["culture"]) if fac and fac.get("culture") and outfits.exists("cultures", fac["culture"]) else None
        oid = ref or cs.get("outfit")
        if oid and not outfits.exists("outfits", oid) and cul and oid in cul.get("roles", {}): oid = cul["roles"][oid]
        if not oid and cs.get("role"):
            oid = (cul or {}).get("roles", {}).get(cs["role"])
            if not oid: raise StoryError(f"chars.{cs['id']}: culture '{(fac or {}).get('culture')}' has no role '{cs['role']}'")
        return (outfits.load("outfits", oid) if oid else None), fac, cul

    def build_char(self, cs):
        L = self.lib.json("chars", cs["type"])
        cid = cs["id"]
        cfg = chars.char_cfg(L, cs.get("faces"))
        of, fac, cul = self.outfit_for(cs) if (cs.get("outfit") or (cs.get("role") and cs["type"] == "person")) else (None, None, None)
        changes = cs.get("outfit_changes", [])
        if of or changes:
            lk = outfits.resolve_look(cs, fac, cul, of, self.st["meta"].get("seed", 7))
            if of and of.get("torso"):
                tw, th, _ = cfg["torso"]; cfg["torso"] = (tw, th, outfits.mat("torso", lk["slots"], of["torso"]))
            hr = cfg["head"][1]
            variants = [(1, of, fac, cul, lk)]
            for ch in changes:
                o2, f2, c2 = self.outfit_for(cs, ch[1], ch[2] if len(ch) > 2 else None)
                variants.append((int(ch[0]), o2, f2, c2, outfits.resolve_look(cs, f2, c2, o2, self.st["meta"].get("seed", 7))))

            def extras(c):
                chars.draw_extras(c, cid, L)
                groups = []
                for k, (f0, o_, f_, c_, lk_) in enumerate(variants):
                    g = []
                    if len(variants) > 1 and o_ and o_.get("torso"):     # changed outfits repaint the shirt
                        tw, th, _ = cfg["torso"]
                        o_ = dict(o_, items=[{"op": "shape", "on": "torso", "name": "shirt_cover", "pts": {"rrect": [0, th / 2, tw, th, 0.3]},
                                              "mat": o_["torso"], "z": 0.125}] + list(o_.get("items", [])))
                    if o_: g = outfits.dress(c, cid, o_, lk_, hr, prefix=f"{cid}_of{k}")
                    groups.append((f0, g))
                if len(groups) > 1:
                    for k, (f0, g) in enumerate(groups):
                        f1 = groups[k + 1][0] - 1 if k + 1 < len(groups) else 10 ** 6
                        for e in g: self.outfit_vis.append((e, [(f0, f1)]))
                outfits.apply_skin(c, cid, lk)
            cfg["extras"] = extras
        else:
            cfg["extras"] = lambda c: chars.draw_extras(c, cid, L)
        c = chars.make_char(cid, tuple(self.env.const(cs.get("loc", [0, 0, 0]))), cfg)
        for hp in cs.get("props", []):
            parent = getattr(c, hp.get("on", "torso"))
            o = self.lib.prop(hp["type"], dict(hp.get("params", {}), name=hp["id"], parent=parent))
            self.place(o, hp)
            c.held = getattr(c, "held", []) + [o]
        for e in cs.get("fx", []):
            if e["type"] == "steam": fx.add_steam(c)
            elif e["type"] == "drips": fx.add_drips(c)
            else: raise StoryError(f"chars.{cid}.fx: unknown fx {e['type']!r} (steam, drips)")
        c.reacts = [tuple(r) for r in cs.get("reacts", [])]
        c.expr_table = [tuple(e) for e in cs.get("expressions", [])] or [(1, cfg["faces"][0])]
        self.chars[cid] = c
        self.char_specs.append(cs)
        return c

    def build_crowd(self, cr, k):
        """a formation of soldiers/people: a few template characters (variants) instanced at every member position"""
        cid = cr["id"]; rnd = random.Random(cr.get("seed", 11 + k))
        at = tuple(self.env.const(cr.get("at", [0, 0, 0]), f"crowds[{k}].at"))
        nv = max(1, min(6, int(cr.get("variants", 3))))
        march = [tuple(r) for r in cr.get("march", [])]
        tpls = []
        face_pool = cr.get("faces") or ([cr["face"]] if cr.get("face") else ["neutral", "focus", "grumpy", "neutral", "worried", "smirk"])
        for v in range(nv):
            spec = {"id": f"{cid}_t{v}", "type": cr.get("type", "person"), "loc": list(at), "look": dict(cr.get("look", {}), seed=v),
                    "expressions": [[1, face_pool[v % len(face_pool)]]], "blinks": [30 + 17 * v, 120 + 23 * v]}
            for key in ("faction", "role", "outfit"):
                if key in cr: spec[key] = cr[key]
            pose = {"default": dict(cr.get("pose", {}))}
            if march: pose["segments"] = [{"ranges": [list(r) for r in march], "legs": f"walk_legs(f * 0.30 + {v * 1.7:.2f})"}]
            spec["pose"] = pose
            c = self.build_char(spec)
            coll = bpy.data.collections.new(f"tpl_{cid}_{v}")
            self.crowd_tpl.append((coll, c.root, at)); tpls.append((coll, at))
        offs = outfits.formation_offsets(cr, rnd)
        root, members = outfits.instance_crowd(cid, tpls, offs, at, cr.get("rot", 0), rnd)
        if cr.get("moves"):
            for (f0, p0), (f1, p1) in zip(cr["moves"], cr["moves"][1:]):
                for f in range(int(f0), int(f1) + 1, 2):
                    u = timing.ease((f - f0) / max(1, f1 - f0)) if cr.get("ease", True) else (f - f0) / max(1, f1 - f0)
                    root.location = (p0[0] + (p1[0] - p0[0]) * u, p0[1] + (p1[1] - p0[1]) * u, at[2]); root.keyframe_insert("location", frame=f)
                root.location = (p1[0], p1[1], at[2]); root.keyframe_insert("location", frame=int(f1))
        if "from" in cr or "to" in cr:
            self.outfit_vis.append((root, [(int(cr.get("from", 1)), int(cr.get("to", 10 ** 6)))]))
        self.crowds[cid] = root
        return root

    def arm(self, spec, ns, where):
        if spec is None: return None
        kind = spec[0]
        if kind == "ik": return ("ik", tuple(self.env.val(spec[1], ns, where)), self.env.val(spec[2], ns, where))
        if kind == "ang": return ("ang", self.env.val(spec[1], ns, where), self.env.val(spec[2], ns, where))
        raise StoryError(f"{where}: arm spec must start with 'ik' or 'ang', got {kind!r}")

    def pose_frame(self, c, cs, segs, f, amp):
        talk = cs.get("talk", [])
        c.amp_now = amp[f] if any(a_ <= f <= b_ for a_, b_ in talk) else 0.0
        P = cs.get("pose", {})
        spec = dict(P.get("default", {}))
        seg = next((s for rng, s in segs if any(r0 <= f <= r1 for r0, r1 in rng)), None)
        let = dict(spec.pop("let", {}) or {})
        if seg:
            spec.update({k: v for k, v in seg.items() if k in POSE_FIELDS})
            let.update(seg.get("let") or {})
        w = f"chars.{cs['id']}.pose"
        ns = self.env.frame_ns(f, let, w)
        legs = self.env.val(spec["legs"], ns, w) if "legs" in spec else ((-0.06, 0.02), (0.06, -0.02))
        chars.pose_char(c, f, self.arm(spec.get("armL"), ns, w), self.arm(spec.get("armR"), ns, w),
                        legL=tuple(legs[0]), legR=tuple(legs[1]),
                        head_tilt=self.env.val(spec.get("tilt", 0.0), ns, w),
                        body=tuple(self.env.val(spec.get("body", [0, 0]), ns, w)),
                        lean=self.env.val(spec.get("lean", 0.0), ns, w))
        for e in cs.get("fx", []):
            if e["type"] == "steam": fx.bake_steam_frame(c, f, e.get("ranges", []))
            elif e["type"] == "drips": fx.bake_drips_frame(c, f, e.get("from", 1))

    # ---------- camera ----------
    def build_camera_object(self):
        cs = self.st["camera"]
        if cs.get("rig", "shots_v2") == "shots_v2":
            self.cam, self.cam_d, self.tgt = camera.make_shot_camera(lens=cs.get("lens", 30))
        else:
            cam_d = bpy.data.cameras.new("Cam"); cam_d.lens = cs.get("lens", 30); cam_d.clip_start = 0.05; cam_d.clip_end = 600
            cam = bpy.data.objects.new("Cam", cam_d); ctx.col.objects.link(cam); ctx.sc.camera = cam; ctx.set_camera(cam)
            self.cam, self.cam_d, self.tgt = cam, cam_d, None

    def bake_camera(self):
        cs = self.st["camera"]
        if cs.get("rig", "shots_v2") == "shots_v2":
            shots, whip, fstop, track = [], set(), {}, None
            tracks = {}
            for i, s in enumerate(cs["shots"]):
                if "track" in s:
                    tracks[s["a"]] = s["track"]
                    shots.append((s["a"], s["b"], None, None, None, None, s["lens"]))
                else:
                    c0, c1 = s["cam"]; l0, l1 = s["look"]
                    shots.append((s["a"], s["b"], tuple(c0), tuple(c1), tuple(l0), tuple(l1), s["lens"]))
                if s.get("whip"): whip.add(s["a"])
                if "fstop" in s: fstop[i] = s["fstop"]

            def track(f):
                a = max(k for k in tracks if k <= f); tr = tracks[a]; ns = self.env.frame_ns(f, tr.get("let"), "camera.track")
                return tuple(self.env.val(tr["cam"], ns)), tuple(self.env.val(tr["look"], ns))
            res = camera.bake_shots(self.cam, self.cam_d, self.tgt, shots,
                                    [tuple(x) for x in cs.get("shakes", [])], [tuple(x) for x in cs.get("punch", [])],
                                    whip, fstop, track=track, hand=cs.get("hand", 0.010))
            self.lens, self.cuts = res["lens"], res["cuts"]
        elif cs["rig"] == "long":
            shots = []
            for k, s in enumerate(cs["shots"]):
                if "frame" in s and "keys" not in s:       # shot preset -> two camera keys
                    sp = self.subject_pos(s["frame"].get("subject", [0, 0, 0]), (s["a"] + s["b"]) // 2, f"camera.shots[{k}].frame")
                    fr = self.subject_scale(s, s["frame"])
                    fr = self.clear_angle(dict(s, frame=fr), sp)
                    s = dict(s, frame=fr, keys=framing.frame_keys(fr, s.get("type", "medium"), s["a"], s["b"], sp))
                    self.report.setdefault("framed", []).append([s["a"], s["b"], s.get("type")])
                d = dict(a=s["a"], b=s["b"], keys=[tuple(k) for k in s["keys"]])
                for k in ("ease_in", "ease_out", "follow_w", "omega", "type"):
                    if k in s: d[k] = s[k]
                if "follow" in s:
                    src = s["follow"]; d["follow"] = (lambda src: (lambda f: tuple(self.env.val(src, self.env.frame_ns(f)))))(src)
                shots.append(d)
            trans = {int(k): tuple(v) for k, v in cs.get("trans", {}).items()}
            punch = [tuple(x) for x in cs.get("punch", [])]; shakes = [tuple(x) for x in cs.get("shakes", [])]
            res, shots, trans = camera.solve_long(shots, trans, punch, shakes, hand=cs.get("hand", 0.6))
            self.report["camera_ok"] = camera.long_report(res, shots, trans, punch)
            self.lens = camera.bake_camera(self.cam, self.cam_d, res, set(trans))
            self.cuts = sorted(trans)
            self.bake_dof(res, cs, cs["shots"])
            if not self.check_line_of_sight(res, cs["shots"]): self.report["camera_ok"] = False
        else:
            seqs = []
            for s in cs["seqs"]:
                d = dict(a=s["a"], b=s["b"], keys=[tuple(k) for k in s["keys"]])
                for k in ("ease_in", "ease_out", "follow_w", "omega"):
                    if k in s: d[k] = s[k]
                if "follow" in s:
                    src = s["follow"]; d["follow"] = (lambda src: (lambda f: tuple(self.env.val(src, self.env.frame_ns(f)))))(src)
                seqs.append(d)
            trans = {int(k): tuple(v) for k, v in cs.get("trans", {}).items()}
            punch = [tuple(x) for x in cs.get("punch", [])]; shakes = [tuple(x) for x in cs.get("shakes", [])]
            res = camera.solve_camera(seqs, trans, punch, shakes, hand=cs.get("hand", 1.0))
            self.report["camera_ok"] = camera.cam_report(res, seqs, trans, punch)
            self.lens = camera.bake_camera(self.cam, self.cam_d, res, set(trans))
            self.cuts = sorted(trans)
            self.bake_dof(res, cs, cs["seqs"])

    def _blocker(self, own, cam, look):
        """name of the first object between cam and look that is not part of `own` (None = clear)"""
        cam, look = Vector(cam), Vector(look); d = (look - cam).length
        if d < 0.3: return None
        dg = bpy.context.evaluated_depsgraph_get()
        mine = {own.name} | {c.name for c in own.children_recursive}
        hit, _loc, _n, _i, ob, _m = ctx.sc.ray_cast(dg, cam, (look - cam).normalized(), distance=d * 0.92)
        if hit and ob is not None and ob.name not in mine and not ob.name.startswith(("vfx_", "Overlay", "cap_", "card_")):
            return ob.name
        return None

    HEAD_REF = 1.85      # head height of a standard character (framing presets aim at it)

    def subject_scale(self, s, fr):
        """framing presets are sized for a person; a goat's or cow's head sits much lower, so a 'closeup' showed the wall
        behind it with the animal at the bottom edge. Scale frame size and look height by the real head height."""
        subj = fr.get("subject")
        if not isinstance(subj, str) or subj not in self.chars: return fr
        c = self.chars[subj]
        if getattr(c, "head", None) is None: return fr
        ctx.sc.frame_set((s["a"] + s["b"]) // 2)
        hz = c.head.matrix_world.translation.z - c.root.matrix_world.translation.z
        k = hz / self.HEAD_REF
        if abs(k - 1) <= 0.15: return fr
        print(f"NOTE shot {s['a']}-{s['b']}: '{subj}' head at {hz:.2f} -> framing scaled x{k:.2f}")
        return dict(fr, _scale=k)

    def clear_angle(self, s, sp):
        """the shot preset puts the camera at a fixed angle/distance from the subject; when a wall (or the inside of a
        building) is in the way at the start, middle or end of the shot, try other angles, then a high angle, and keep the
        first clear one. Leaves the frame unchanged when nothing helps (check_line_of_sight then warns)."""
        fr = s["frame"]; subj = fr.get("subject")
        if not isinstance(subj, str) or "." in subj or s.get("type") in ("board", "map") or fr.get("height") == "top": return fr
        own = self.chars[subj].root if subj in self.chars else self.crowds.get(subj) or bpy.data.objects.get(subj)
        if own is None: return fr
        a, b = s["a"], s["b"]; m = (a + b) // 2

        def blocked(f2):
            ks = framing.frame_keys(f2, s.get("type", "medium"), a, b, sp)
            ctx.sc.frame_set(m)
            for kk in (ks[0], ks[-1]):
                who = self._blocker(own, kk[1], kk[2])
                if who: return who
            return None
        who = blocked(fr)
        if not who: return fr
        base = float(fr.get("angle", 0.0))
        tries = [dict(fr, angle=base + da) for da in (35, -35, 70, -70)] + \
                [dict(fr, angle=base + da, height="high") for da in (0, 35, -35, 70, -70)]
        for f2 in tries:
            if not blocked(f2):
                print(f"NOTE shot {a}-{b}: view of '{subj}' blocked by '{who}' -> angle {f2['angle']:.0f}"
                      + (f", height {f2['height']}" if f2.get("height") != fr.get("height") else ""))
                self.report.setdefault("reframed", []).append([a, b, who, f2["angle"], f2.get("height")])
                return f2
        return fr

    def dress_ground(self):
        """long-form look: big ground and hill meshes get soft colour patches (fields, worn grass, sunlit slopes)"""
        done = set(); n = 0
        for o in ctx.sc.objects:
            if o.type != 'MESH' or o.hide_render: continue
            d = o.dimensions
            if d.x > 30 and d.y > 30 and d.z < 0.5 * max(d.x, d.y):
                for m in o.data.materials:
                    if m is not None and m.name not in done:
                        look.ground_variation(m); done.add(m.name); n += 1
        if n: print(f"GROUND {n} materials with colour patches")

    def check_line_of_sight(self, res, shots):
        """framing places the camera by distance only: a wall, a tree or the inside of a building can end up between the
        camera and the subject (seen: a low orbit around a centurion ended inside the milecastle wall). Cast a ray from the
        camera to the look point in the middle of every framed shot of a character/crowd/object and warn when it is blocked."""
        ok = True; dg = None
        for k, s in enumerate(shots):
            subj = (s.get("frame") or {}).get("subject")
            if not isinstance(subj, str) or "." in subj: continue
            own = self.chars[subj].root if subj in self.chars else self.crowds.get(subj) or bpy.data.objects.get(subj)
            if own is None: continue
            f = (s["a"] + s["b"]) // 2
            if f not in res: continue
            ctx.sc.frame_set(f); dg = bpy.context.evaluated_depsgraph_get()
            cam, look = Vector(res[f][0]), Vector(res[f][1]); d = (look - cam).length
            if d < 0.3: continue
            mine = {own.name} | {c.name for c in own.children_recursive}
            hit, loc, _n, _i, ob, _m = ctx.sc.ray_cast(dg, cam, (look - cam).normalized(), distance=d * 0.92)
            if hit and ob is not None and ob.name not in mine and not ob.name.startswith(("vfx_", "Overlay", "cap_", "card_")):
                ok = False
                print(f"WARN shot {s['a']}-{s['b']} (camera.shots[{k}]): view of '{subj}' blocked by '{ob.name}' at frame {f} "
                      f"({(loc - cam).length:.1f} of {d:.1f} from the camera): change frame.angle/height/x/move or move the subject")
        return ok

    def value_at(self, segs, default, f, prop, where):
        """value of one property of a track/blocking spec at frame f (None if nothing sets it)"""
        rs = self.resolve_segments(segs, {}, where)
        spec = next((sg for rng, sg in rs if any(r0 <= f <= r1 for r0, r1 in rng)), default)
        if not spec or prop not in spec: return None
        ns = self.env.frame_ns(f, None, where)
        for k, src in (spec.get("let") or {}).items(): ns[k] = self.env.val(src, ns, where)
        return tuple(self.env.val(spec[prop], ns, where))

    def subject_pos(self, subj, f, where):
        """ground point of a shot subject at frame f: [x,y,z], a character id, '<set id>.<anchor>' or an object name"""
        if isinstance(subj, (list, tuple)): return tuple(self.env.const(subj, where))
        if subj in self.anchors: return tuple((list(self.anchors[subj]) + [0.0, 0.0, 0.0])[:3])
        if subj in self.crowds:
            ctx.sc.frame_set(f); return tuple(self.crowds[subj].matrix_world.translation)
        if subj in self.chars or bpy.data.objects.get(subj) is not None:    # animated already: evaluate the scene at f
            ctx.sc.frame_set(f)
            o = self.chars[subj].root if subj in self.chars else bpy.data.objects[subj]
            return tuple(o.matrix_world.translation)
        for cs in self.char_specs:
            if cs["id"] == subj:
                b = cs.get("blocking")
                v = self.value_at(b.get("segments", []), b.get("default"), f, "location", where) if b else None
                return v or tuple(self.env.const(cs.get("loc", [0, 0, 0]), where))
        for tr in self.st.get("tracks", []):
            if tr.get("target") == subj and "use" not in tr:
                v = self.value_at(tr.get("segments", []), tr.get("default"), f, "location", where)
                if v: return v
        o = bpy.data.objects.get(subj)
        if o is None: raise StoryError(f"{where}: unknown subject '{subj}' (character id, '<set>.<anchor>', object name or [x,y,z])")
        return tuple(o.matrix_world.translation)

    def bake_dof(self, res, cs, spans):
        """camera.dof = {"fstop": 2.8} turns depth of field on (focus = look point); a shot/seq may set its own "fstop"."""
        dof = cs.get("dof")
        if not dof: return
        base = dof.get("fstop", 2.8); fs = {}
        for s in spans:
            for f in range(s["a"], s["b"] + 1): fs[f] = s.get("fstop", base)
        for f in res: fs.setdefault(f, base)
        camera.bake_dof(self.cam_d, res, fs)
        self.dof_on = True

    # ---------- main ----------
    def build(self):
        st = self.st; meta = st["meta"]
        errs = check_story(st, self.lib)
        if errs: raise StoryError("story.json has errors:\n  " + "\n  ".join(errs))
        N, FPS = meta["frames"], meta["fps"]
        t0 = time.time()
        self.aspect = meta.get("aspect", "9:16")
        sc = core.start(N, FPS, self.out, meta.get("samples", 32), aspect=self.aspect)
        fast = self.aspect != "9:16" and meta.get("fast_build", True)      # Shorts keep the exact original path
        geo.FAST = fast; timing.KEYBUF = timing.KeyBuffer() if fast else None
        random.seed(meta.get("seed", 7))
        geo.init(); fx.init(); faces.init()
        self.env = Env(FPS, N, st.get("defs"), st.get("consts"))

        w = st.get("world", {})
        wo = look.sky_world(tuple(tuple(c) for c in w["sky"]) if "sky" in w else look.SKY_DAY, w.get("sky_strength", 1.0))
        if self.aspect != "9:16" and w.get("clouds", 0.5) > 0:          # long-form: a sky with clouds, never an empty gradient
            look.add_clouds(wo, w.get("clouds", 0.5), seed=float(meta.get("seed", 7)))
        look.sun_light(**w.get("sun", {}))

        # sets, each followed by its props (creation order is part of the result)
        for s in st.get("sets", []):
            sp = s.get("params", {})
            if st.get("factions"): sp = dict(sp, _factions=st["factions"])    # maps/boards colour items by faction
            res = self.lib.set(s["type"], sp)
            parts = res.get("parts", {})
            self.noline_roots += res.get("noline", [])
            for k, v in res.get("anchors", {}).items(): self.anchors[f"{s.get('id', s['type'])}.{k}"] = v
            for p in s.get("props", []):
                parent = parts[p["on"]] if "on" in p else None
                o = self.lib.prop(p["type"], dict(p.get("params", {}), name=p["id"], parent=parent))
                self.place(o, p); self.story_props.add(p["id"])

        self.build_camera_object()
        for cs in st.get("chars", []):
            self.build_char(cs)
        for k, cr in enumerate(st.get("crowds", [])):
            self.build_crowd(cr, k)
        for c in self.chars.values():
            fx.add_reaction_fx(c)
        for cs in self.char_specs:
            if cs.get("talk"): chars.add_talk_mouth(self.chars[cs["id"]])
        self.char_style = body3d.style(meta)
        if self.char_style == "3d":
            t3 = time.time()
            for c in self.chars.values(): body3d.convert(c)
            print(f"CHARS 3D {len(self.chars)} characters in {time.time() - t3:.1f} s")

        long_rig = st["camera"].get("rig") == "long"
        if not long_rig: self.bake_camera()

        for e, rng in self.outfit_vis: geo.vis_track(e, rng)
        for name, ranges in st.get("visibility", {}).items():
            geo.vis_track(self.obj(name, f"visibility.{name}"), [tuple(r) for r in ranges])
        moved = set()
        for k, tr in enumerate(st.get("tracks", [])):
            o = self.run_track(tr, where=f"tracks[{k}]({tr['target']})")
            moved.add(o.name)
        for cs in self.char_specs:
            c = self.chars[cs["id"]]
            if "blocking" in cs: self.run_track(cs["blocking"], c.root, f"chars.{cs['id']}.blocking")
            if "skin_keys" in cs:
                sk = c.skin.node_tree.nodes["Emission"].inputs[0]
                for f_, col_ in cs["skin_keys"]:
                    sk.default_value = (*col_, 1); sk.keyframe_insert("default_value", frame=f_)
        if long_rig: self.bake_camera()       # after tracks/blocking: shot presets frame subjects where they really are

        amp = timing.load_amplitude(os.path.join(self.dir, meta.get("voice", "voice.wav")), N, FPS)
        segs = {cs["id"]: self.resolve_segments(cs.get("pose", {}).get("segments", []), {}, f"chars.{cs['id']}.pose") for cs in self.char_specs}
        for f in range(1, N + 1):
            for cs in self.char_specs:
                self.pose_frame(self.chars[cs["id"]], cs, segs[cs["id"]], f, amp)
        for cs in self.char_specs:
            chars.apply_expressions(self.chars[cs["id"]], blinks=tuple(cs.get("blinks", ())))
        if timing.KEYBUF is not None:
            t_k = time.time(); nk = timing.KEYBUF.flush(); print(f"KEYS {nk} buffered keys written in {time.time() - t_k:.1f} s")

        cp = st.get("captions", {})
        cstyle = cp.get("style", "pop" if self.aspect == "9:16" else "bottom")
        WORDS = [tuple(x) for x in st.get("words", [])]
        self.caps = captions.make_caps(WORDS, set(cp.get("highlight", [])), impact=tuple(cp.get("impact", []))) if cstyle == "pop" else []
        if cstyle == "pop":
            cap_root = captions.build_captions(self.caps, self.lens, lift_ranges=[tuple(r) for r in cp.get("lift", [])],
                                               burst_word=cp.get("burst_word", (cp.get("impact") or [""])[0].upper() or None))
        elif cstyle == "bottom":
            cap_root = captions.build_subtitles(WORDS, self.lens, y=cp.get("y", -0.80), size=cp.get("size", 0.034))
        else:
            cap_root = None

        cards_root = cards.build_cards(st.get("cards"), self.lens)
        vfx_noline = fx_long.build(st.get("vfx"), {f["id"]: f for f in st.get("factions", [])}, self.cam, meta.get("seed", 7)) if st.get("vfx") else []

        fxs = st.get("fx", {})
        for k, d in enumerate(fxs.get("dust", [])):
            d = dict(d); fr = d.pop("frame"); pos = tuple(self.env.const(d.pop("pos"), f"fx.dust[{k}].pos"))
            fx.dust_burst(fr, pos, **d)
        fx.bake_dust()
        for cs in self.char_specs:
            if cs.get("reaction_fx"): fx.bake_reaction_fx(self.chars[cs["id"]], cs["reaction_fx"])
        for cs in self.char_specs:
            if cs.get("talk"): chars.bake_talk(self.chars[cs["id"]], [tuple(r) for r in cs["talk"]], amp)

        if timing.KEYBUF is not None: timing.KEYBUF.flush()
        holds = st.get("teleport_holds")
        if holds is None:
            holds = [c.root.name for c in self.chars.values()] + sorted(n for n in moved if n in self.story_props)
        timing.add_teleport_holds([self.obj(n, "teleport_holds") for n in holds])

        if self.aspect != "9:16": self.dress_ground()
        noline = []
        for c in self.chars.values(): noline += look.descendants(c.root)
        if cap_root: noline += look.descendants(cap_root)
        if cards_root: noline += look.descendants(cards_root)
        for r in self.noline_roots: noline += look.descendants(r)
        for p_ in fx.PUFF_POOL: noline += look.descendants(p_)
        for o in vfx_noline: noline += [o] + look.descendants(o)
        look.setup_look(noline)
        for coll, troot, loc in self.crowd_tpl:          # crowd templates leave the scene: only their instances render
            outfits.to_template_collection(coll, troot, loc)
        if any("grade" in sh for sh in st["camera"].get("shots", [])):
            fx_long.grade(st["camera"]["shots"])
        if self.dof_on:                       # DOF would blur captions/cards near the lens: render them in an overlay scene
            overlay.make_overlay([cap_root, cards_root], samples=max(4, meta.get("samples", 32) // 4))

        self.build_sound()
        geo.FAST = False; timing.KEYBUF = None
        mixer.set_video_output(os.path.join(self.out, meta.get("output", "out.mp4")))
        sc.frame_set(1)
        self.report["build_seconds"] = round(time.time() - t0, 1)
        print(f"SCENE READY -> {sc.render.filepath}  ({self.report['build_seconds']} s, {len(bpy.data.objects)} objects)")
        return sc

    def build_sound_long(self):
        """long-form mix: compressed voice, music segments (mood or file) ducked under the voice, ambience beds,
        story events + long-form/real SFX, whooshes on whips only, normalised to -14 LUFS with a peak limiter"""
        A = audio_long; S = self.st.get("sound", {}); N, FPS = ctx.N, ctx.FPS
        n = int(round(N / FPS * A.SR)); seed = self.st["meta"].get("seed", 7)
        vo_p = os.path.join(self.dir, self.st["meta"].get("voice", "voice.wav"))
        M = S.get("master", {})
        voice = A.fit(A.load_audio(vo_p), n) if os.path.exists(vo_p) else None
        if voice is not None:
            voice = A.fft_filter(voice, A.band(lo=80))
            if M.get("compress_voice", True): voice = A.compress(voice)
        ref = A.lufs(voice) if voice is not None and np.abs(voice).max() > 1e-4 else -20.0
        duck = A.duck_gain(voice) if voice is not None else None

        def at_level(x, rel_db):                        # loudness relative to the voice
            L = A.lufs(x)
            return x * 10 ** ((ref + rel_db - L) / 20) if L > -69 else x

        def segs(spec, default):
            if not spec: return []
            items = spec if isinstance(spec, list) else [spec]
            return [dict(default, **it) for it in items]

        meta = self.st["meta"]
        part_off = meta.get("part_offset")            # seconds: this story is one part of a longer, seamless video
        first, last = meta.get("part_first", True), meta.get("part_last", True)

        def place(x, a, b, xf=2.0):
            """x laid from frame a to b with crossfades (none at a seam with the previous/next part)"""
            i, j = int((a - 1) / FPS * A.SR), min(n, int(b / FPS * A.SR))
            out = np.zeros(n); seg = A.fit(x, j - i); f = min(len(seg) // 2, int(xf * A.SR))
            if f > 0:
                seg = seg.copy()
                if a > 1 or first: seg[:f] *= np.linspace(0, 1, f)
                if b < N or last: seg[-f:] *= np.linspace(1, 0, f)
            out[i:j] = seg; return out
        gen_cache = {}

        def on_timeline(key, fn, a, sec):
            """music/ambience in the video's global time: parts of one video cut from the same piece, so it runs on
            across the seam instead of restarting at its intro"""
            if part_off is None: return fn(sec)
            off = float(part_off) + (a - 1) / FPS
            need = off + sec
            if key not in gen_cache or gen_cache[key][0] < need: gen_cache[key] = (need, fn(need))
            full = gen_cache[key][1]; i = int(off * A.SR)
            return full[i:i + int(sec * A.SR)]
        parts = [] if voice is None else [voice]
        rep = {}
        for k, mu in enumerate(segs(S.get("music"), {"mood": "epic", "from": 1, "to": N})):
            a, b = int(mu.get("from", 1)), int(mu.get("to", N)); sec = (b - a + 1) / FPS
            if mu.get("file"):
                x = A.load_audio(os.path.join(A.MUSIC_DIR, mu["file"])); x = np.tile(x, int(np.ceil(sec * A.SR / max(1, len(x)))))
            else:
                mood = mu.get("mood", "epic"); mood = {"sneaky": "mystery"}.get(mood, mood)
                x = on_timeline(("m", mood, mu.get("intensity", 1.0)), lambda L, mood=mood, k=k: A.music(
                    L, mood, seed=seed + (0 if part_off is not None else k), intensity=mu.get("intensity", 1.0)), a, sec)
            x = place(at_level(A.fit(x, int(sec * A.SR)), mu.get("gain_db", -4.0)), a, b)
            if duck is not None: x = x * duck ** (mu.get("duck_db", -10.0) / -13.0)
            parts.append(x); rep.setdefault("music", []).append(mu.get("file") or mu.get("mood"))
        for am in segs(S.get("ambience"), {"kind": "wind", "from": 1, "to": N}):
            if am["kind"] == "none": continue
            a, b = int(am.get("from", 1)), int(am.get("to", N)); sec = (b - a + 1) / FPS
            x = place(at_level(on_timeline(("a", am["kind"]), lambda L, kd=am["kind"]: A.ambience(L, kd), a, sec),
                               am.get("gain_db", -20.0)), a, b, 1.0)
            if duck is not None: x = x * duck ** (4.0 / 13.0)
            parts.append(x)
        fx_ = np.zeros(n); vpk = float(np.abs(voice).max()) if voice is not None else 0.5
        lvl = vpk * 10 ** (M.get("sfx_db", 0.0) / 20)

        def hit(name, frame, gain):
            x = A.get_sfx(name, sfx.SFX); i = int((frame - 1) / FPS * A.SR); A._add(fx_, i, x, gain * lvl)
        for fr, nm, g in S.get("events", []): hit(nm, fr, g)
        for r in S.get("repeat", []):
            for f in range(r["from"], r["to"] + 1, r["every"]): hit(r["name"], f, r["gain"])
        au = S.get("auto", {})
        if au.get("enabled", True):
            for k, v in self.st["camera"].get("trans", {}).items():
                if v[0] == "whip": hit("whoosh", int(k) - 5, 0.25)
            for c in self.st.get("cards", []):
                if c.get("style") in ("screen", "chapter"): hit("whoosh_big", int(c["from"]), 0.18)
        parts.append(fx_)
        mix, mrep = A.master(parts, M.get("lufs", -14.0))
        rep.update(mrep); self.report["audio"] = rep
        print(f"AUDIO {mrep['lufs']} LUFS (gain {mrep['gain_db']} dB) peak {mrep['peak_db']} dBFS  music={rep.get('music')}")
        wav = A.write_wav(os.path.join(self.out, "mix.wav"), mix)
        mixer.attach_audio(wav, None, sfx_volume=1.0)

    def build_sound(self):
        if self.aspect != "9:16" or "master" in self.st.get("sound", {}): return self.build_sound_long()
        S = self.st.get("sound", {}); N, FPS = ctx.N, ctx.FPS
        TOTAL = N / FPS
        vo = os.path.join(self.dir, self.st["meta"].get("voice", "voice.wav"))
        has_vo = os.path.exists(vo)
        g = S.get("sfx_gain_with_voice", 0.8) if has_vo else 1.0
        mix = mixer.Mix(TOTAL, FPS)
        mu = S.get("music")
        if mu:
            w0, w1 = mu.get("duck_window", [-4, 30])
            duck = [((c + w0) / FPS, (c + w1) / FPS) for c in mu.get("duck", [])]
            mix.bed(sfx.music_bed(TOTAL, mu.get("mood", "playful"), duck=duck), mu.get("gain_with_voice", 0.10) if has_vo else mu.get("gain", 0.16))
        am = S.get("ambience")
        if am: mix.bed(sfx.ambience(TOTAL, am.get("kind", "city")), am.get("gain", 0.04))
        au = S.get("auto", {})
        if au.get("enabled", True):
            gest = [self.chars[i] for i in au["gesture_chars"]] if "gesture_chars" in au else None
            cuts = self.cuts
            if self.st["camera"].get("rig") == "long":     # straight cuts are silent in long-form; whoosh only on whips
                cuts = sorted(int(k) for k, v in self.st["camera"].get("trans", {}).items() if v[0] == "whip")
            mixer.auto_sfx(mix, cuts, list(self.chars.values()), self.caps, avoid_cuts=tuple(au.get("avoid", ())), gain=g, gesture_chars=gest)
        for fr, nm, gain in S.get("events", []):
            mix.sfx(nm, fr, gain * g)
        for r in S.get("repeat", []):
            for f in range(r["from"], r["to"] + 1, r["every"]):
                mix.sfx(r["name"], f, r["gain"] * g)
        wav = mix.write(os.path.join(self.out, "sfx_music.wav"), TOTAL)
        mixer.attach_audio(wav, vo)


# =====================================================================
#  CLI
# =====================================================================
def gpu_name():
    """the graphics chip EEVEE renders on (a laptop may hand Blender the weak integrated chip instead of the NVIDIA card)"""
    try:
        import gpu
        return f"{gpu.platform.vendor_get()} | {gpu.platform.renderer_get()}"
    except Exception as e:
        return f"unknown ({e})"


QUALITY = {"fast": dict(samples=8, step=2), "normal": dict(samples=16, step=1), "high": dict(samples=32, step=1)}   # 16 vs 24 samples: PSNR 47 dB, -13 % time


def render_sequence(B, sc, opt):
    """render PNG frames into <out>/frames (skipping frames already there), mix the audio, encode the mp4 with ffmpeg.
    --step 2 renders every other frame and holds it for two ('on twos', half the render time); --quality fast|normal|high"""
    q = QUALITY.get(opt.get("quality", ""), {})
    step = int(opt.get("step", q.get("step", 1)))
    if "samples" not in opt and q.get("samples"): sc.eevee.taa_render_samples = q["samples"]
    overlay.sync(sc.render.resolution_percentage, sc.eevee.taa_render_samples)
    fdir = os.path.join(B.out, "frames"); os.makedirs(fdir, exist_ok=True)
    stamp = os.path.join(fdir, "_settings.json")
    want = {"pct": sc.render.resolution_percentage, "samples": sc.eevee.taa_render_samples, "step": step,
            "story_mtime": os.path.getmtime(B.path)}
    old = json.load(open(stamp)) if os.path.exists(stamp) else None
    if old and old != want:                              # settings or story changed: old frames are stale
        for f in os.listdir(fdir):
            if f.startswith("f_"): os.remove(os.path.join(fdir, f))
        print("RENDER frames cleared (settings or story changed)", flush=True)
    for f in os.listdir(fdir):                           # placeholders of a frame that was interrupted
        if f.startswith("f_") and os.path.getsize(os.path.join(fdir, f)) == 0: os.remove(os.path.join(fdir, f))
    json.dump(want, open(stamp, "w"))
    a, b = sc.frame_start, sc.frame_end
    if "frames" in opt:
        a, b = [int(x) for x in opt["frames"].replace("-", ",").split(",")]
    sc.frame_start, sc.frame_end, sc.frame_step = max(1, a), min(sc.frame_end, b), step
    ims = sc.render.image_settings; ims.media_type = 'IMAGE'; ims.file_format = 'PNG'; ims.color_mode = 'RGB'; ims.compression = 15
    sc.render.use_overwrite = False; sc.render.use_placeholder = True
    sc.render.filepath = os.path.join(fdir, "f_####")
    have = len([f for f in os.listdir(fdir) if f.startswith("f_")])
    T0 = time.time()

    def _progress(scene, *_):
        print(f"RENDER FRAME {scene.frame_current} {scene.frame_start} {scene.frame_end} {time.time() - T0:.1f}", flush=True)
    bpy.app.handlers.render_write.append(_progress)
    print(f"RENDER START {sc.frame_start} {sc.frame_end} step {step} (already {have} frames) -> {fdir}", flush=True)
    bpy.ops.render.render(animation=True)
    bpy.app.handlers.render_write.remove(_progress)
    audio = os.path.join(B.out, "mix.wav")
    if not os.path.exists(audio) or B.aspect == "9:16" and "master" not in B.st.get("sound", {}):
        audio = os.path.join(fdir, "audio.wav")
        sc.frame_start, sc.frame_end, sc.frame_step = 1, B.st["meta"]["frames"], 1
        bpy.ops.sound.mixdown(filepath=audio, container='WAV', codec='PCM', format='S16', mixrate=44100)
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import encode
    out = os.path.join(B.out, B.st["meta"].get("output", "out.mp4"))
    if "frames" in opt:
        base, ext = os.path.splitext(os.path.basename(out)); pdir = os.path.join(B.out, "parts"); os.makedirs(pdir, exist_ok=True)
        out = os.path.join(pdir, f"{base}_{a:04d}-{b:04d}{ext}")
    encode.encode(fdir, audio if "frames" not in opt else "-", out, fps=B.st["meta"]["fps"], first=max(1, a),
                  last=min(B.st["meta"]["frames"], b), log=lambda m: print(m, flush=True))
    print("RENDERED ->", out, flush=True)
    return 0


def main(argv):
    if not argv: print(__doc__); return 1
    story = argv[0]
    opt = {}; i = 1
    while i < len(argv):
        a = argv[i]
        if a in ("--render", "--check", "--seq", "--square"): opt[a[2:]] = True; i += 1
        else: opt[a[2:]] = argv[i + 1]; i += 2
    if opt.get("check"):
        errs = check_story(json.load(open(story, encoding="utf-8")), Library())
        print("STORY OK" if not errs else "STORY ERRORS:\n  " + "\n  ".join(errs)); return 0 if not errs else 2
    B = Builder(story, out_dir=opt.get("out"))
    try:
        sc = B.build()
    except (StoryError, ExprError) as e:
        print("BUILD FAILED:", e); return 2
    if "preview" in opt:
        pdir = os.path.join(B.out, "preview"); os.makedirs(pdir, exist_ok=True)
        sc.render.resolution_percentage = int(opt.get("pct", 35))
        if "size" in opt:                                    # exact pixel size (e.g. 1280x720 thumbnails)
            w_, h_ = [int(x) for x in opt["size"].lower().split("x")]
            for scn in [sc] + ([overlay.SCENE] if overlay.SCENE else []):
                scn.render.resolution_x, scn.render.resolution_y = w_, h_
            sc.render.resolution_percentage = 100
        sc.eevee.taa_render_samples = int(opt.get("samples", 16))
        overlay.sync(sc.render.resolution_percentage, sc.eevee.taa_render_samples)
        if opt.get("square"):                                # the centre square only (character reference pictures)
            w_, h_ = sc.render.resolution_x, sc.render.resolution_y; f_ = min(w_, h_) / max(w_, h_)
            sc.render.use_border = True; sc.render.use_crop_to_border = True
            if w_ >= h_: sc.render.border_min_x, sc.render.border_max_x, sc.render.border_min_y, sc.render.border_max_y = (1 - f_) / 2, (1 + f_) / 2, 0, 1
            else: sc.render.border_min_x, sc.render.border_max_x, sc.render.border_min_y, sc.render.border_max_y = 0, 1, (1 - f_) / 2, (1 + f_) / 2
        sc.render.image_settings.media_type = 'IMAGE'; sc.render.image_settings.file_format = 'PNG'
        for fr in [int(x) for x in opt["preview"].split(",")]:
            t1 = time.time(); sc.frame_set(fr); sc.render.filepath = os.path.join(pdir, f"p_{fr:04d}.png")
            bpy.ops.render.render(write_still=True); print("FRAME", fr, round(time.time() - t1, 1), "s")
    if "bench" in opt:                                 # measure seconds/frame on this machine (first frame compiles shaders)
        n = int(opt["bench"]); a = int(opt.get("at", max(1, sc.frame_end // 3)))
        sc.render.resolution_percentage = int(opt.get("pct", 100))
        sc.eevee.taa_render_samples = int(opt.get("samples", sc.eevee.taa_render_samples))
        overlay.sync(sc.render.resolution_percentage, sc.eevee.taa_render_samples)
        sc.render.image_settings.media_type = 'IMAGE'; sc.render.image_settings.file_format = 'PNG'
        bdir = os.path.join(B.out, "_bench"); os.makedirs(bdir, exist_ok=True); times = []
        for k in range(n + 1):
            t1 = time.time(); sc.frame_set(min(sc.frame_end, a + k)); sc.render.filepath = os.path.join(bdir, f"b_{k}.png")
            bpy.ops.render.render(write_still=True); times.append(time.time() - t1)
            print(f"BENCH FRAME {k} {times[-1]:.2f}", flush=True)
        spf = sum(times[1:]) / max(1, len(times) - 1)
        print(f"BENCH sec_per_frame {spf:.2f} first {times[0]:.1f} pct {sc.render.resolution_percentage} samples {sc.eevee.taa_render_samples} "
              f"res {sc.render.resolution_x}x{sc.render.resolution_y}", flush=True)
        print("GPU " + gpu_name() + "  compositor " + str(getattr(sc.render, "compositor_device", "?")), flush=True)
        return 0
    if opt.get("render"):
        if "pct" in opt: sc.render.resolution_percentage = int(opt["pct"])
        if "samples" in opt: sc.eevee.taa_render_samples = int(opt["samples"])
        if opt.get("seq"):                                 # image sequence: resumable, 'on twos', then ffmpeg
            return render_sequence(B, sc, opt)
        overlay.sync(sc.render.resolution_percentage, sc.eevee.taa_render_samples)
        if "frames" in opt:                      # partial render A-B into parts/ (re-render one sequence)
            a, b = [int(x) for x in opt["frames"].replace("-", ",").split(",")]
            sc.frame_start, sc.frame_end = max(1, a), min(sc.frame_end, b)
            base, ext = os.path.splitext(os.path.basename(sc.render.filepath))
            pdir = os.path.join(B.out, "parts"); os.makedirs(pdir, exist_ok=True)
            sc.render.filepath = os.path.join(pdir, f"{base}_{sc.frame_start:04d}-{sc.frame_end:04d}{ext}")
        T0 = time.time()

        def _progress(scene, *_):
            print(f"RENDER FRAME {scene.frame_current} {scene.frame_start} {scene.frame_end} {time.time() - T0:.1f}", flush=True)
        bpy.app.handlers.render_write.append(_progress)
        print(f"RENDER START {sc.frame_start} {sc.frame_end} -> {sc.render.filepath}", flush=True)
        bpy.ops.render.render(animation=True)
        bpy.app.handlers.render_write.remove(_progress)
        print("RENDERED ->", sc.render.filepath, flush=True)
    return 0


if __name__ == "__main__":
    _argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    _rc = main(_argv)
    if _rc and bpy.app.background: sys.exit(_rc)
