"""Render a line-up of outfits (with Joe for scale) + a small black silhouette version.

    blender -b -P tools/lineup.py -- <out_dir> <outfit>[:r,g,b] [<outfit>[:r,g,b] ...] [--pct 50]
    python tools/bpy_run.py tools/lineup.py <out_dir> roman_legionary_50ad briton_warrior_50ad:0.1,0.4,0.1

Writes <out_dir>/lineup.png (colour) and <out_dir>/silhouette.png (all black on white, 1/3 size: can you still tell
the sides apart?).  The colour after ':' is the faction colour ($team); default = the culture's map_color.
"""
import bpy, json, os, sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
out_dir = os.path.abspath(argv[0]); os.makedirs(out_dir, exist_ok=True)
pct = int(argv[argv.index("--pct") + 1]) if "--pct" in argv else 50
specs = [a for i, a in enumerate(argv[1:], 1) if not a.startswith("--") and (i < 2 or argv[i - 1] != "--pct")]

from core import outfits as _of  # noqa: E402
factions, chars = [], [{"id": "joe", "type": "joe", "loc": [0, 0, 0], "expressions": [[1, "happy"]]}]
GAP = 1.45
for k, sp in enumerate(specs):
    name, _, col = sp.partition(":")
    o = _of.load("outfits", name)
    cul = _of.load("cultures", o["culture"]) if o.get("culture") and _of.exists("cultures", o["culture"]) else {}
    rgb = [float(x) for x in col.split(",")] if col else (cul.get("map_color") or [0.6, 0.1, 0.08])
    fid = f"f{k}"
    factions.append({"id": fid, "culture": o.get("culture") or "", "color": rgb, "label": name})
    chars.append({"id": f"c{k}", "type": "person", "faction": fid, "outfit": name, "loc": [GAP * (k + 1), 0, 0],
                  "look": {"seed": k + 1}, "expressions": [[1, "neutral"]],
                  "pose": {"default": {"armL": ["ang", -0.35, 0.6], "armR": ["ang", 0.25, -0.25]}}})
n = len(chars); cx = GAP * (n - 1) / 2
size = max(3.6, (GAP * (n - 1) + 1.6) / 1.70)
story = {"meta": {"title": "lineup", "fps": 30, "frames": 3, "aspect": "16:9", "samples": 24, "output": "lineup.mp4"},
         "factions": [f for f in factions if f["culture"]] or [], "sets": [],
         "camera": {"rig": "long", "shots": [{"a": 1, "b": 3, "type": "full", "frame": {"subject": [cx, 0, 0], "size": size, "move": "static_drift"}}]},
         "chars": chars, "captions": {"style": "off"}, "sound": {}}
for f in story["factions"]:
    if not _of.exists("cultures", f["culture"]): f.pop("culture")
sp = os.path.join(out_dir, "lineup_story.json"); json.dump(story, open(sp, "w"), indent=1)

g = {"__name__": "lineup", "__file__": os.path.join(ROOT, "builder.py")}
sys.argv = ["blender", "--", sp]
exec(compile(open(os.path.join(ROOT, "builder.py"), encoding="utf-8").read(), os.path.join(ROOT, "builder.py"), "exec"), g)
B = g["Builder"](sp, out_dir=out_dir); sc = B.build()
# plain light-grey floor so feet read
floor = bpy.data.objects.new("lineup_floor", bpy.data.meshes.new("lineup_floor"))
import bmesh
bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=40); bm.to_mesh(floor.data); bm.free()
sc.collection.objects.link(floor); floor.data.materials.append(g["look"].flat("lineup_floor", (0.80, 0.78, 0.72)))
sc.render.image_settings.media_type = 'IMAGE'; sc.render.image_settings.file_format = 'PNG'
sc.render.resolution_percentage = pct; sc.eevee.taa_render_samples = 16; g["overlay"].sync(pct, 16)
sc.frame_set(2); sc.render.filepath = os.path.join(out_dir, "lineup.png"); bpy.ops.render.render(write_still=True)
# silhouette: every character black, world and floor white, small
black = g["look"].flat("lineup_black", (0.0, 0.0, 0.0)); white = g["look"].flat("lineup_white", (1.0, 1.0, 1.0))
for o in bpy.data.objects:
    if o.type in ('MESH', 'CURVE', 'FONT') and o.data and hasattr(o.data, "materials") and len(o.data.materials):
        for i in range(len(o.data.materials)): o.data.materials[i] = white if o.name == "lineup_floor" else black
w = sc.world.node_tree.nodes
for nd in w:
    if nd.type == 'BACKGROUND': nd.inputs[0].default_value = (1, 1, 1, 1)
for nd in list(w):
    if nd.type == 'VALTORGB':
        for e in nd.color_ramp.elements: e.color = (1, 1, 1, 1)
sc.compositing_node_group = None
sc.render.resolution_percentage = max(12, pct // 3); sc.render.filepath = os.path.join(out_dir, "silhouette.png")
bpy.ops.render.render(write_still=True)
print("LINEUP ->", os.path.join(out_dir, "lineup.png"), os.path.join(out_dir, "silhouette.png"))
