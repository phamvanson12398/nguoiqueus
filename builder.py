"""WhyShorts builder: story.json -> Blender scene (+ preview PNGs or mp4).

    blender -b -P builder.py -- projects/<slug>/story.json                      build + checks only
    blender -b -P builder.py -- projects/<slug>/story.json --preview 50,200,366  PNG previews (35 %)
    blender -b -P builder.py -- projects/<slug>/story.json --render              full mp4 (1080x1920)
    options: --pct 35  --samples 16  --out <dir>  --check (validate story.json only, no Blender scene)

The story format is described in STORY.md and story.schema.json.  Library items live in
library/{sets,props,chars,motions}.  voice.wav is read from the story's folder; sfx_music.wav,
preview/ and the mp4 are written there (or to --out).
"""
import bpy, os, sys, json, math, random, time, importlib.util

# ---------------- paths, fresh core modules ----------------
_here = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() and os.path.exists(__file__) else os.getcwd()
ROOT = os.environ.get("WHYSHORTS_ROOT") or _here
if ROOT not in sys.path: sys.path.insert(0, ROOT)
for _m in [m for m in sys.modules if m == "core" or m.startswith("core.") or m.startswith("whylib_")]:
    del sys.modules[_m]

import core
from core import ctx, look, geo, timing, camera, faces, chars, fx, captions, sfx, mixer
from core.expr import Env, ExprError
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
            p = os.path.join(self.root, "motions", name + ".json") if kind == "motions" else self.path(kind, name, "char.json")
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
    def build_char(self, cs):
        L = self.lib.json("chars", cs["type"])
        for mname, rgb in L.get("materials", {}).items():
            look.flat(mname, tuple(rgb))
        cfg = dict(L["cfg"])
        tw, th, tmat = cfg["torso"]
        cfg["torso"] = (tw, th, look.flat(tmat, tuple(L["materials"][tmat])) if isinstance(tmat, str) else tmat)
        cfg["faces"] = cs.get("faces", L.get("faces", ["neutral"]))
        cid = cs["id"]

        def extras(c):
            for op in L.get("extras", []):
                parent = getattr(c, op["on"]); nm = f"{cid}_{op['name']}"
                m = look.MATS[op["mat"]] if op.get("mat") else None
                if op["op"] == "shape":
                    kw = {"outline": op["outline"]} if "outline" in op else {}
                    geo.shape(parent, nm, geo.points(op["pts"]), m, op["z"], **kw)
                elif op["op"] == "stroke":
                    geo.stroke(parent, nm, geo.points(op["pts"]), op["w"], op["z"], m=m)
                elif op["op"] == "disc":
                    geo.disc(parent, nm, op["c"][0], op["c"][1], op["r"], op["z"], m)
                else:
                    raise StoryError(f"char {cs['type']}: unknown extras op {op['op']!r}")
        cfg["extras"] = extras
        c = chars.make_char(cid, tuple(self.env.const(cs.get("loc", [0, 0, 0]))), cfg)
        for hp in cs.get("props", []):
            parent = getattr(c, hp.get("on", "torso"))
            o = self.lib.prop(hp["type"], dict(hp.get("params", {}), name=hp["id"], parent=parent))
            self.place(o, hp)
        for e in cs.get("fx", []):
            if e["type"] == "steam": fx.add_steam(c)
            elif e["type"] == "drips": fx.add_drips(c)
            else: raise StoryError(f"chars.{cid}.fx: unknown fx {e['type']!r} (steam, drips)")
        c.reacts = [tuple(r) for r in cs.get("reacts", [])]
        c.expr_table = [tuple(e) for e in cs.get("expressions", [])] or [(1, cfg["faces"][0])]
        self.chars[cid] = c
        self.char_specs.append(cs)
        return c

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

    # ---------- main ----------
    def build(self):
        st = self.st; meta = st["meta"]
        errs = check_story(st, self.lib)
        if errs: raise StoryError("story.json has errors:\n  " + "\n  ".join(errs))
        N, FPS = meta["frames"], meta["fps"]
        t0 = time.time()
        sc = core.start(N, FPS, self.out, meta.get("samples", 32))
        random.seed(meta.get("seed", 7))
        geo.init(); fx.init(); faces.init()
        self.env = Env(FPS, N, st.get("defs"), st.get("consts"))

        w = st.get("world", {})
        look.sky_world(tuple(tuple(c) for c in w["sky"]) if "sky" in w else look.SKY_DAY, w.get("sky_strength", 1.0))
        look.sun_light(**w.get("sun", {}))

        # sets, each followed by its props (creation order is part of the result)
        for s in st.get("sets", []):
            res = self.lib.set(s["type"], s.get("params", {}))
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
        for c in self.chars.values():
            fx.add_reaction_fx(c)
        for cs in self.char_specs:
            if cs.get("talk"): chars.add_talk_mouth(self.chars[cs["id"]])

        self.bake_camera()

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

        amp = timing.load_amplitude(os.path.join(self.dir, meta.get("voice", "voice.wav")), N, FPS)
        segs = {cs["id"]: self.resolve_segments(cs.get("pose", {}).get("segments", []), {}, f"chars.{cs['id']}.pose") for cs in self.char_specs}
        for f in range(1, N + 1):
            for cs in self.char_specs:
                self.pose_frame(self.chars[cs["id"]], cs, segs[cs["id"]], f, amp)
        for cs in self.char_specs:
            chars.apply_expressions(self.chars[cs["id"]], blinks=tuple(cs.get("blinks", ())))

        cp = st.get("captions", {})
        self.caps = captions.make_caps([tuple(x) for x in st.get("words", [])], set(cp.get("highlight", [])), impact=tuple(cp.get("impact", [])))
        cap_root = captions.build_captions(self.caps, self.lens, lift_ranges=[tuple(r) for r in cp.get("lift", [])],
                                           burst_word=cp.get("burst_word", (cp.get("impact") or [""])[0].upper() or None))

        fxs = st.get("fx", {})
        for k, d in enumerate(fxs.get("dust", [])):
            d = dict(d); fr = d.pop("frame"); pos = tuple(self.env.const(d.pop("pos"), f"fx.dust[{k}].pos"))
            fx.dust_burst(fr, pos, **d)
        fx.bake_dust()
        for cs in self.char_specs:
            if cs.get("reaction_fx"): fx.bake_reaction_fx(self.chars[cs["id"]], cs["reaction_fx"])
        for cs in self.char_specs:
            if cs.get("talk"): chars.bake_talk(self.chars[cs["id"]], [tuple(r) for r in cs["talk"]], amp)

        holds = st.get("teleport_holds")
        if holds is None:
            holds = [c.root.name for c in self.chars.values()] + sorted(n for n in moved if n in self.story_props)
        timing.add_teleport_holds([self.obj(n, "teleport_holds") for n in holds])

        noline = []
        for c in self.chars.values(): noline += look.descendants(c.root)
        noline += look.descendants(cap_root)
        for r in self.noline_roots: noline += look.descendants(r)
        for p_ in fx.PUFF_POOL: noline += look.descendants(p_)
        look.setup_look(noline)

        self.build_sound()
        mixer.set_video_output(os.path.join(self.out, meta.get("output", "out.mp4")))
        sc.frame_set(1)
        self.report["build_seconds"] = round(time.time() - t0, 1)
        print(f"SCENE READY -> {sc.render.filepath}  ({self.report['build_seconds']} s, {len(bpy.data.objects)} objects)")
        return sc

    def build_sound(self):
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
            mixer.auto_sfx(mix, self.cuts, list(self.chars.values()), self.caps, avoid_cuts=tuple(au.get("avoid", ())), gain=g, gesture_chars=gest)
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
def main(argv):
    if not argv: print(__doc__); return 1
    story = argv[0]
    opt = {}; i = 1
    while i < len(argv):
        a = argv[i]
        if a in ("--render", "--check"): opt[a[2:]] = True; i += 1
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
        sc.eevee.taa_render_samples = int(opt.get("samples", 16))
        sc.render.image_settings.media_type = 'IMAGE'; sc.render.image_settings.file_format = 'PNG'
        for fr in [int(x) for x in opt["preview"].split(",")]:
            t1 = time.time(); sc.frame_set(fr); sc.render.filepath = os.path.join(pdir, f"p_{fr:04d}.png")
            bpy.ops.render.render(write_still=True); print("FRAME", fr, round(time.time() - t1, 1), "s")
    if opt.get("render"):
        if "pct" in opt: sc.render.resolution_percentage = int(opt["pct"])
        bpy.ops.render.render(animation=True)
        print("RENDERED ->", sc.render.filepath)
    return 0


if __name__ == "__main__":
    _argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    _rc = main(_argv)
    if _rc and bpy.app.background: sys.exit(_rc)
