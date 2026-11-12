"""Render library thumbnails and review views.

    blender -b -P tools/thumbs.py                                    thumb.png for every item
    blender -b -P tools/thumbs.py -- props/milk_carton --views       thumb.png + _review/{front,side,top,iso_back,scale}.png
    options: --size 512  --samples 16  --params '{"kind":"square"}'  (build parameters for the render)

Prints 'THUMB <item> -> <path>' per image and 'THUMB FAILED <item>' + traceback on build errors
(claude_bridge.py reads these lines).
"""
import bpy, os, sys, math, json, time, traceback, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path: sys.path.insert(0, ROOT)


def load_library():
    """exec builder.py (it resets core modules) and return its Library class"""
    src = open(os.path.join(ROOT, "builder.py"), encoding="utf-8").read()
    g = {"__name__": "whybuilder", "__file__": os.path.join(ROOT, "builder.py")}
    exec(compile(src, "builder.py", "exec"), g)
    return g["Library"]


Library = load_library()
import core
from core import ctx, look, geo, fx, faces, chars
from mathutils import Vector

_argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
opt = {}; items = []; i = 0
while i < len(_argv):
    a = _argv[i]
    if a == "--views": opt["views"] = True; i += 1
    elif a.startswith("--"): opt[a[2:]] = _argv[i + 1]; i += 2
    else: items.append(a); i += 1
SIZE = int(opt.get("size", 512)); SAMPLES = int(opt.get("samples", 16))
PARAMS = json.loads(opt.get("params", "{}"))
TAG = opt.get("tag", "")          # review round: images go to _review/<tag>/ so every round has fresh file names

SET_VIEWS = {  # per-set cameras (pos, look, lens): a set is too big to auto-frame
    "street": [((-3.2, -1.5, 2.0), (0.4, 7.0, 1.4), 26), ((3.5, 0.0, 1.4), (-1.0, 9.0, 1.6), 24), ((0.0, -8.0, 9.0), (0.0, 8.0, 0.0), 24)],
    "office": [((299.6, -0.6, 1.6), (300.3, 4.0, 1.4), 26), ((302.5, 1.0, 1.8), (299.0, 4.5, 1.0), 24)],
    "diagram_board": [((500.0, -9.0, 1.5), (500.0, 0.3, 1.5), 26)],
}


def fresh():
    global _look_done
    core.start(1, 30, os.path.join(ROOT, "_thumbs_tmp"), SAMPLES)
    import random; random.seed(7)
    geo.init(); fx.init(); faces.init()
    look.sky_world(); look.sun_light()
    _look_done = False


def bounds(objs):
    dg = bpy.context.evaluated_depsgraph_get(); pts = []
    for o in objs:
        if o.hide_render: continue
        if o.type == 'CURVE':          # evaluated curve bound boxes are unreliable here: use the spline points
            pts += [o.matrix_world @ Vector(p.co[:3]) for sp in o.data.splines for p in sp.points]
        elif o.type == 'FONT':         # same for text: measure the evaluated mesh
            me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
            pts += [o.matrix_world @ v.co for v in me.vertices]; bpy.data.meshes.remove(me)
        elif o.type == 'MESH':
            oe = o.evaluated_get(dg); pts += [oe.matrix_world @ Vector(c) for c in oe.bound_box]
    if not pts: return Vector((0, 0, 0.5)), Vector((0.5, 0.5, 0.5))
    lo = Vector([min(p[k] for p in pts) for k in range(3)]); hi = Vector([max(p[k] for p in pts) for k in range(3)])
    return (lo + hi) / 2, (hi - lo) / 2


def camera(pos, look_at, lens=40):
    cam = ctx.cam
    if cam is None or cam.name != "ThumbCam":
        cam_d = bpy.data.cameras.new("ThumbCam"); cam_d.clip_end = 1000; cam_d.clip_start = 0.01
        cam = bpy.data.objects.new("ThumbCam", cam_d); ctx.col.objects.link(cam); ctx.sc.camera = cam
        ctx.set_camera(cam)
    cam.data.lens = lens; cam.location = pos
    cam.rotation_euler = (Vector(look_at) - Vector(pos)).to_track_quat('-Z', 'Y').to_euler()
    return cam


def frame_dir(center, half, direction, lens=50, margin=1.25):
    """camera position looking at `center` along `direction`, far enough for the box to fit"""
    r = max(half.length, 0.05)
    dist = r / math.tan(math.atan(18 / lens)) * margin
    d = Vector(direction).normalized()
    return tuple(center - d * dist), tuple(center)


_look_done = False


def shoot(path, noline):
    global _look_done
    sc = ctx.sc
    if not _look_done:
        look.setup_look(noline); _look_done = True
    sc.render.use_motion_blur = False
    sc.render.resolution_x = sc.render.resolution_y = SIZE; sc.render.resolution_percentage = 100
    sc.eevee.taa_render_samples = SAMPLES
    sc.render.image_settings.media_type = 'IMAGE'; sc.render.image_settings.file_format = 'PNG'
    sc.render.filepath = path; sc.frame_set(1)
    bpy.ops.render.render(write_still=True)
    print("THUMB", os.path.relpath(path, ROOT), "->", path, flush=True)


def build_char(lib, name, loc=(0, 0, 0), cid=None):
    L = lib.json("chars", name); cid = cid or name
    cfg = chars.char_cfg(L)
    cfg["extras"] = lambda c: chars.draw_extras(c, cid, L)
    return chars.make_char(cid, loc, cfg), L


def floor():
    return geo.plane(80, (0, 0, -0.001), look.flat("thumb_floor", (0.86, 0.88, 0.9)))


def render_item(kind, name, lib, views):
    d = os.path.join(lib.root, kind, name); rv = os.path.join(d, "_review", TAG) if TAG else os.path.join(d, "_review")
    if views: os.makedirs(rv, exist_ok=True)
    if kind == "sets":
        fresh()
        vs = SET_VIEWS.get(name, [((-6, -6, 4), (0, 2, 1), 24)])
        camera(*vs[0])
        res = lib.set(name, PARAMS)
        noline = [x for r in res.get("noline", []) for x in look.descendants(r)]
        if name == "diagram_board":
            pl = res["parts"]["plane"]
            a = lib.prop("diagram_square_hole", {"name": "sq", "parent": pl}); a.location = (-3.2, 0, 0)
            b = lib.prop("diagram_round_hole", {"name": "rd", "parent": pl}); b.location = (3.2, 0, 0)
            noline += look.descendants(pl)
        shoot(os.path.join(d, "thumb.png"), noline)
        if views:
            for k, v in enumerate(vs):
                camera(*v); shoot(os.path.join(rv, f"view{k}.png"), noline)
        return
    if kind == "chars":
        fresh()
        camera((0, -6.0, 1.15), (0, 0, 1.15), 50)
        ch, L = build_char(lib, name)
        ch.expr_table = [(1, L["faces"][0])]; chars.pose_char(ch, 1); chars.apply_expressions(ch)
        shoot(os.path.join(d, "thumb.png"), look.descendants(ch.root) + [floor()])
        if views:
            bpy.context.view_layer.update()
            hp = ch.head.matrix_world.translation                  # the real head: short characters (goat, cow) sit far below Joe's 1.85
            hr = float(((L.get("cfg") or {}).get("head") or [0, 0.4])[1]) * ch.head.matrix_world.to_scale()[0]
            dist = max(1.0, 6.5 * hr)
            for face in L["faces"]:
                for kf, g in ch.F.items(): geo.set_visible(g, 1, kf == face)
                camera((hp.x, hp.y - dist, hp.z), (hp.x, hp.y, hp.z), 50); shoot(os.path.join(rv, f"face_{face}.png"), [])
        return

    meta = lib.meta(kind, name); is2d = meta.get("dim") == "2d"
    # main thumbnail + views
    fresh()
    holder = geo.empty("thumb_holder")
    o = lib.prop(name, dict(PARAMS, name=name, parent=holder))
    if o.parent is None: o.parent = holder          # 3D props ignore 'parent'
    if is2d: holder.rotation_euler = (math.pi / 2, 0, 0); holder.location = (0, 0, 20)   # float above the floor
    bpy.context.view_layer.update()
    objs = look.descendants(holder)
    c, h = bounds(objs)
    noline = objs if is2d else []
    fl = [] if is2d else [floor()]
    dirs = [("thumb", (0, 1, 0) if is2d else (0.55, 1, -0.75))]
    if views:
        dirs += [("front", (0, 1, 0))] + ([] if is2d else [("side", (-1, 0, 0)), ("top", (0.0001, 0.0001, -1)), ("iso_back", (-0.6, -1, -0.6))])
    for tag, dvec in dirs:
        pos, at = frame_dir(c, h, dvec)
        camera(pos, at, 50)
        shoot(os.path.join(d, "thumb.png") if tag == "thumb" else os.path.join(rv, f"{tag}.png"), noline + fl)
        if tag == "thumb" and views: shutil.copy(os.path.join(d, "thumb.png"), os.path.join(rv, "thumb.png"))
    if not views: return
    # scale reference next to Joe (2D: held in Joe's hands)
    fresh()
    camera((0, -6.5, 1.3), (0, 0, 1.25), 40)
    joe, L = build_char(lib, "joe", (0.0 if is2d else -0.9, 0.2, 0))
    joe.expr_table = [(1, "neutral")]
    if is2d:
        o = lib.prop(name, dict(PARAMS, name=name, parent=joe.torso)); o.location = (0, 0.42, 0.45)
        chars.pose_char(joe, 1, ('ik', (-0.42, 0.42), -1), ('ik', (0.42, 0.42), 1))
    else:
        holder = geo.empty("thumb_holder"); o = lib.prop(name, dict(PARAMS, name=name, parent=holder))
        if o.parent is None: o.parent = holder
        bpy.context.view_layer.update()
        c2, h2 = bounds(look.descendants(holder))
        holder.location = (0.9 - c2.x + max(0.0, h2.x - 0.6), -c2.y, -(c2.z - h2.z))   # stand on the floor right of Joe
        chars.pose_char(joe, 1)
        tall = max(2.6, 2 * h2.z + 0.2)
        camera((0.4, -max(6.5, tall * 2.6), tall * 0.5), (0.4, 0, tall * 0.48), 40)
    chars.apply_expressions(joe)
    shoot(os.path.join(rv, "scale.png"), look.descendants(joe.root) + [floor()])


def main():
    lib = Library()
    todo = items or [f"{k}/{n}" for k in ("sets", "props", "chars") for n in lib.list(k)]
    for it in todo:
        k, n = it.split("/"); t0 = time.time()
        try:
            render_item(k, n, lib, opt.get("views", False))
            print("THUMB DONE", it, round(time.time() - t0, 1), "s", flush=True)
        except Exception as e:
            traceback.print_exc(); print("THUMB FAILED", it, f"{type(e).__name__}: {e}", flush=True)


main()
