"""Build a scene script and dump a complete fingerprint of the result.

    blender -b -P tools/fingerprint.py -- <scene.py> <out_dir> [--frames 1,200,360] [--render 50,360,700] [--pct 25] [--samples 16]

Writes <out_dir>/fingerprint.json (objects, meshes, curves, modifiers, constraints, materials,
every keyframe, evaluated world matrices on --frames, compositor, sequencer, sfx wav hash) and,
with --render, PNG frames <out_dir>/f_XXXX.png.  Compare two dumps with tools/compare.py.
"""
import bpy, sys, os, json, hashlib, time, struct

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
scene_path, out_dir = os.path.abspath(argv[0]), os.path.abspath(argv[1])
opt = {argv[i][2:]: argv[i + 1] for i in range(2, len(argv) - 1) if argv[i].startswith("--")}
FRAMES = [int(x) for x in opt.get("frames", "1,100,200,300,360,450,600,640,700,760,900,1000,1060,1150,1250,1320").split(",")]
RENDER = [int(x) for x in opt["render"].split(",")] if "render" in opt else []
os.makedirs(out_dir, exist_ok=True)

t0 = time.time()
g = {"__file__": scene_path, "__name__": "__main__"}
if scene_path.endswith(".json"):                # story.json -> run builder.py on it
    _builder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "builder.py")
    g["__file__"] = _builder; sys.argv = [sys.argv[0], "--", scene_path]
    exec(compile(open(_builder, encoding="utf-8").read(), _builder, "exec"), g)
else:
    sys.argv = [sys.argv[0]]                   # the scene must not see our arguments
    exec(compile(open(scene_path, encoding="utf-8").read(), scene_path, "exec"), g)
BUILD_S = time.time() - t0
sc = bpy.context.scene


def f2(x): return float(x)   # keep full precision; json writes repr


def hsh(b): return hashlib.sha256(b).hexdigest()[:16]


SIMPLE = ('BOOLEAN', 'INT', 'FLOAT', 'STRING', 'ENUM')


def rna(o, skip=()):
    out = {}
    for p in o.bl_rna.properties:
        k = p.identifier
        if k in ("rna_type", "name_full", "session_uid", "is_evaluated", "original", "users", "is_runtime_data",
                 "is_override_data", "is_missing", "is_embedded_data", "is_library_indirect", "tag", "is_editmode",
                 "filepath", "filepath_raw", "persistent_uid", "use_extra_user") or k in skip:
            continue
        try:
            v = getattr(o, k)
        except Exception:
            continue
        if p.type in SIMPLE:
            if p.type == 'ENUM' and p.is_enum_flag: v = sorted(v)
            elif p.type in ('FLOAT', 'INT', 'BOOLEAN') and getattr(p, "array_length", 0):
                v = [x for x in (v if not hasattr(v, "__len__") or not len(v) or not hasattr(v[0], "__len__") else [y for r in v for y in r])]
            out[k] = v if not isinstance(v, float) else f2(v)
        elif p.type == 'POINTER' and not p.is_never_none and v is not None and hasattr(v, "name") and isinstance(getattr(v, "name", None), str) and isinstance(v, bpy.types.ID):
            out[k] = "ID:" + v.name
    return out


def fcurves_of(idb):
    ad = getattr(idb, "animation_data", None)
    if not ad or not ad.action: return []
    act = ad.action
    if hasattr(act, "fcurves"): return list(act.fcurves)
    res = []
    for layer in act.layers:
        for strip in layer.strips:
            cb = strip.channelbag(ad.action_slot)
            if cb: res += list(cb.fcurves)
    return res


def anim(idb):
    res = {}
    for fc in fcurves_of(idb):
        n = len(fc.keyframe_points)
        co = [0.0] * (2 * n); fc.keyframe_points.foreach_get("co", co)
        interp = [kp.interpolation for kp in fc.keyframe_points]
        res[f"{fc.data_path}[{fc.array_index}]"] = {"n": n, "co": co, "interp": hsh("".join(interp).encode())}
    return res


def node_tree(nt):
    if nt is None: return None
    nodes = {}
    for n in nt.nodes:
        ins = {}
        for i, s in enumerate(n.inputs):
            if hasattr(s, "default_value"):
                v = s.default_value
                if isinstance(v, (str, bool, int, float)): pass
                elif isinstance(v, bpy.types.ID): v = "ID:" + v.name
                else:
                    try: v = [f2(x) for x in v]
                    except (TypeError, ValueError): v = str(v)
                ins[f"{i}:{s.identifier}"] = v
        d = rna(n, skip=("location", "location_absolute", "width", "height", "dimensions", "select", "show_options", "show_preview", "hide", "mute", "show_texture", "warning_propagation", "color", "use_custom_color", "label"))
        if n.bl_idname == "ShaderNodeValToRGB":
            d["ramp"] = [(f2(e.position), [f2(c) for c in e.color]) for e in n.color_ramp.elements]
        nodes[n.name] = {"type": n.bl_idname, "props": d, "inputs": ins}
    links = sorted(f"{l.from_node.name}.{l.from_socket.identifier}>{l.to_node.name}.{l.to_socket.identifier}" for l in nt.links)
    return {"nodes": nodes, "links": links, "anim": anim(nt)}


FP = {"objects": {}, "meshes": {}, "curves": {}, "materials": {}, "cameras": {}, "lights": {}, "worlds": {},
      "fonts": sorted(f.name for f in bpy.data.fonts), "collections": {}}
for o in bpy.data.objects:
    FP["objects"][o.name] = {
        "type": o.type, "data": o.data.name if o.data else None, "parent": o.parent.name if o.parent else None,
        "loc": [f2(x) for x in o.location], "rot": [f2(x) for x in o.rotation_euler], "scl": [f2(x) for x in o.scale],
        "mpi": [f2(x) for r in o.matrix_parent_inverse for x in r],
        "hide_render": o.hide_render, "hide_viewport": o.hide_viewport,
        "slots": [s.material.name if s.material else None for s in o.material_slots],
        "constraints": [rna(c) for c in o.constraints], "modifiers": [rna(m) for m in o.modifiers],
        "collections": sorted(c.name for c in o.users_collection), "anim": anim(o)}
for m in bpy.data.meshes:
    v = [0.0] * (3 * len(m.vertices)); m.vertices.foreach_get("co", v)
    lv = [0] * len(m.loops); m.loops.foreach_get("vertex_index", lv)
    sm = [False] * len(m.polygons); m.polygons.foreach_get("use_smooth", sm)
    # topology independent of face/loop order (Blender's uv-sphere primitive orders loops differently run to run)
    faces_ = []
    for p in m.polygons:
        vs = list(p.vertices); i0 = vs.index(min(vs)); faces_.append(tuple(vs[i0:] + vs[:i0]))
    FP["meshes"][m.name] = {"nv": len(m.vertices), "np": len(m.polygons), "co": hsh(struct.pack(f"{len(v)}f", *v)),
                            "topology": hsh(repr(sorted(faces_)).encode()), "smooth": sum(sm),
                            "mats": [x.name if x else None for x in m.materials]}
for c in bpy.data.curves:
    d = rna(c, skip=("bevel_factor_start", "bevel_factor_end"))
    if c.splines:
        pts = []
        for sp in c.splines:
            for p in sp.points: pts += [f2(x) for x in p.co]
            pts.append(1e9 if sp.use_cyclic_u else -1e9)
        d["points"] = hsh(struct.pack(f"{len(pts)}d", *pts))
    d["mats"] = [x.name if x else None for x in c.materials]
    if hasattr(c, "body"): d["body"] = c.body; d["font"] = c.font.name if c.font else None
    FP["curves"][c.name] = d
for m in bpy.data.materials:
    FP["materials"][m.name] = {"props": rna(m), "tree": node_tree(m.node_tree)}
for c in bpy.data.cameras:
    FP["cameras"][c.name] = {"props": rna(c), "dof": rna(c.dof), "anim": anim(c)}
for l in bpy.data.lights:
    FP["lights"][l.name] = rna(l)
for w in bpy.data.worlds:
    FP["worlds"][w.name] = {"tree": node_tree(w.node_tree), "mist": rna(w.mist_settings)}
for c in bpy.data.collections:
    FP["collections"][c.name] = sorted(o.name for o in c.objects)
FP["scene"] = {"render": rna(sc.render), "eevee": rna(sc.eevee), "view": rna(sc.view_settings),
               "ffmpeg": rna(sc.render.ffmpeg), "image": rna(sc.render.image_settings),
               "frame": [sc.frame_start, sc.frame_end, sc.render.fps], "camera": sc.camera.name if sc.camera else None,
               "mist_pass": sc.view_layers[0].use_pass_mist,
               "compositor": node_tree(sc.compositing_node_group) if getattr(sc, "compositing_node_group", None) else None}
seq = []
if sc.sequence_editor:
    for st in sc.sequence_editor.strips:
        fp_ = bpy.path.abspath(st.sound.filepath) if getattr(st, "sound", None) else None
        seq.append({"name": st.name, "channel": st.channel, "start": st.frame_start, "volume": f2(getattr(st, "volume", 1.0)),
                    "file": os.path.basename(fp_) if fp_ else None,
                    "sha": hsh(open(fp_, "rb").read()) if fp_ and os.path.exists(fp_) else None})
FP["sequencer"] = sorted(seq, key=lambda s: s["name"])
FP["render_path_basename"] = os.path.basename(sc.render.filepath)

# evaluated state (constraints, parenting, visibility keys) on sample frames
ev = {}
for f in FRAMES:
    sc.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    ev[f] = {o.name: [[f2(x) for r in o.evaluated_get(dg).matrix_world for x in r], o.evaluated_get(dg).hide_render]
             for o in bpy.data.objects}
    ev[f]["__lens__"] = f2(sc.camera.data.lens) if sc.camera else None
FP["evaluated"] = ev
FP["build_seconds"] = round(BUILD_S, 1)

with open(os.path.join(out_dir, "fingerprint.json"), "w") as fh:
    json.dump(FP, fh, sort_keys=True)
print(f"FINGERPRINT {out_dir}  objects={len(FP['objects'])} meshes={len(FP['meshes'])} curves={len(FP['curves'])} build={BUILD_S:.1f}s")

if RENDER:
    sc.render.resolution_percentage = int(opt.get("pct", 25))
    sc.eevee.taa_render_samples = int(opt.get("samples", 16))
    sc.render.image_settings.media_type = 'IMAGE'; sc.render.image_settings.file_format = 'PNG'
    for f in RENDER:
        t1 = time.time(); sc.frame_set(f); sc.render.filepath = os.path.join(out_dir, f"f_{f:04d}.png")
        bpy.ops.render.render(write_still=True); print("FRAME", f, round(time.time() - t1, 1), "s")
