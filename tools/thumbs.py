"""Render library thumbnails (library/<kind>/<name>/thumb.png).

    blender -b -P tools/thumbs.py                       all items
    blender -b -P tools/thumbs.py -- props/manhole_cover chars/joe     selected items
    options: --size 512  --samples 16
"""
import bpy, os, sys, math, json, time

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

sys.argv_ = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
opt = {}; items = []
i = 0
while i < len(sys.argv_):
    a = sys.argv_[i]
    if a.startswith("--"): opt[a[2:]] = sys.argv_[i + 1]; i += 2
    else: items.append(a); i += 1
SIZE = int(opt.get("size", 512)); SAMPLES = int(opt.get("samples", 16))

VIEW = {  # per-set camera (pos, look) because a set is too big to auto-frame
    "street": ((-3.2, -1.5, 2.0), (0.4, 7.0, 1.4)),
    "office": ((299.6, -0.6, 1.6), (300.3, 4.0, 1.4)),
    "diagram_board": ((500.0, -9.0, 1.5), (500.0, 0.3, 1.5)),
}


def scene_bounds(objs):
    dg = bpy.context.evaluated_depsgraph_get(); pts = []
    for o in objs:
        if o.type not in ('MESH', 'CURVE', 'FONT'): continue
        oe = o.evaluated_get(dg)
        if o.type == 'CURVE':          # evaluated curve bound boxes are unreliable here: use the spline points
            pts += [o.matrix_world @ Vector(p.co[:3]) for sp in o.data.splines for p in sp.points]
        else:
            pts += [oe.matrix_world @ Vector(c) for c in oe.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return (lo + hi) / 2, (hi - lo).length / 2


def make_cam(pos, look_at, lens=40):
    cam_d = bpy.data.cameras.new("ThumbCam"); cam_d.lens = lens; cam_d.clip_end = 1000
    cam = bpy.data.objects.new("ThumbCam", cam_d); ctx.col.objects.link(cam); ctx.sc.camera = cam
    cam.location = pos
    cam.rotation_euler = (Vector(look_at) - Vector(pos)).to_track_quat('-Z', 'Y').to_euler()
    ctx.set_camera(cam)
    return cam


def render(path, noline):
    sc = ctx.sc
    look.setup_look(noline)
    sc.render.use_motion_blur = False
    sc.render.resolution_x = sc.render.resolution_y = SIZE; sc.render.resolution_percentage = 100
    sc.eevee.taa_render_samples = SAMPLES
    sc.render.image_settings.media_type = 'IMAGE'; sc.render.image_settings.file_format = 'PNG'
    sc.render.filepath = path; sc.frame_set(1)
    bpy.ops.render.render(write_still=True)


def thumb(kind, name, lib):
    core.start(1, 30, os.path.join(ROOT, "_thumbs_tmp"), SAMPLES)
    import random; random.seed(7)
    geo.init(); fx.init(); faces.init()
    look.sky_world(); look.sun_light()
    out = os.path.join(lib.root, kind, name, "thumb.png"); noline = []
    if kind == "sets":
        pos, at = VIEW.get(name, ((-4, -4, 3), (0, 0, 1)))
        cam = make_cam(pos, at, 26)          # camera first: some sets may use billboards
        res = lib.set(name, {})
        noline = [d for r in res.get("noline", []) for d in look.descendants(r)]
        if name == "diagram_board":           # show the two diagram props on the board
            pl = res["parts"]["plane"]
            a = lib.prop("diagram_square_hole", {"name": "sq", "parent": pl}); a.location = (-3.2, 0, 0)
            b = lib.prop("diagram_round_hole", {"name": "rd", "parent": pl}); b.location = (3.2, 0, 0)
            noline += look.descendants(pl)
    elif kind == "props":
        meta = json.load(open(os.path.join(lib.root, kind, name, "meta.json"), encoding="utf-8"))
        holder = geo.empty("thumb_holder")
        o = lib.prop(name, {"name": name, "parent": holder})
        if o.parent is None: o.parent = holder          # 3D props ignore 'parent'
        if meta.get("dim") == "2d":
            holder.rotation_euler = (math.pi / 2, 0, 0); holder.location = (0, 0, 20)   # float above the floor
            noline = look.descendants(holder)
        bpy.context.view_layer.update()
        c, r = scene_bounds(look.descendants(holder))
        d = Vector((0, -1, 0)) if meta.get("dim") == "2d" else Vector((-0.55, -1, 0.75)).normalized()
        dist = max(r, 0.1) / math.tan(math.radians(20)) * 1.15
        make_cam(tuple(c + d * dist), tuple(c), 50)
    elif kind == "chars":
        make_cam((0, -6.0, 1.15), (0, 0, 1.15), 50)
        L = json.load(open(os.path.join(lib.root, kind, name, "char.json"), encoding="utf-8"))
        for m, rgb in L["materials"].items(): look.flat(m, tuple(rgb))
        cfg = dict(L["cfg"]); tw, th, tm = cfg["torso"]; cfg["torso"] = (tw, th, look.MATS[tm]); cfg["faces"] = L["faces"]

        def extras(c):
            for op in L.get("extras", []):
                par = getattr(c, op["on"]); nm = f"{name}_{op['name']}"; m = look.MATS[op["mat"]] if op.get("mat") else None
                if op["op"] == "shape": geo.shape(par, nm, geo.points(op["pts"]), m, op["z"], **({"outline": op["outline"]} if "outline" in op else {}))
                elif op["op"] == "stroke": geo.stroke(par, nm, geo.points(op["pts"]), op["w"], op["z"], m=m)
                elif op["op"] == "disc": geo.disc(par, nm, op["c"][0], op["c"][1], op["r"], op["z"], m)
        cfg["extras"] = extras
        ch = chars.make_char(name, (0, 0, 0), cfg)
        ch.expr_table = [(1, L["faces"][0])]
        chars.pose_char(ch, 1); chars.apply_expressions(ch)
        noline = look.descendants(ch.root)
    plane = geo.plane(60, (0, 0, -0.001), look.flat("thumb_floor", (0.86, 0.88, 0.9))) if kind != "sets" else None
    render(out, noline + ([plane] if plane else []))
    return out


def main():
    lib = Library()
    todo = items or [f"{k}/{n}" for k in ("sets", "props", "chars") for n in lib.list(k)]
    for it in todo:
        k, n = it.split("/"); t0 = time.time()
        try:
            p = thumb(k, n, lib); print("THUMB", it, "->", p, round(time.time() - t0, 1), "s")
        except Exception as e:
            import traceback; traceback.print_exc(); print("THUMB FAILED", it, e)


main()
