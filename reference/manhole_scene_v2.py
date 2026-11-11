# ==========================================================
#  "Why Manhole Covers Are Round" (45 s, 1080x1920, 30 fps)
#  Original 2D characters in a stylised 3D city street.  [toolkit v2]
#  Run inside Blender 5.2: Scripting tab > Run Script.
#  Then render with Render > Render Animation (Ctrl+F12).
# ==========================================================
import bpy, math, os, wave, random, re
import numpy as np
from mathutils import Matrix

FPS, N = 30, 1350
CLOUD = bpy.app.background            # True when previewing headless
random.seed(7)

# ---------------- output / fonts ----------------
if os.name == "nt":
    OUT_DIR = os.path.join(os.path.expanduser("~"), "Videos", "claude_test")
    FONT_CANDIDATES = [r"C:\Windows\Fonts\ariblk.ttf", r"C:\Windows\Fonts\arialbd.ttf"]
else:
    OUT_DIR = "/home/claude/out/rail"
    FONT_CANDIDATES = ["/usr/share/fonts/opentype/inter/Inter-Black.otf",
                       "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"]
os.makedirs(OUT_DIR, exist_ok=True)
FONT_PATH = next((f for f in FONT_CANDIDATES if os.path.exists(f)), None)

# ---------------- reset ----------------
if CLOUD:
    bpy.ops.wm.read_factory_settings(use_empty=True)
else:
    for coll in (bpy.data.objects, bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras,
                 bpy.data.lights, bpy.data.textures, bpy.data.worlds, bpy.data.actions):
        for item in list(coll):
            coll.remove(item)
    if bpy.context.scene.sequence_editor:
        for st in list(bpy.context.scene.sequence_editor.strips):
            bpy.context.scene.sequence_editor.strips.remove(st)
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, N
sc.render.fps = FPS
sc.render.resolution_x, sc.render.resolution_y = 1080, 1920
sc.render.resolution_percentage = 100
sc.view_settings.view_transform = 'Standard'
sc.view_settings.look = 'None'
sc.render.engine = 'BLENDER_EEVEE'
try:
    sc.eevee.taa_render_samples = 32
    sc.eevee.use_shadows = True
    sc.eevee.use_raytracing = True
    sc.eevee.use_fast_gi = True
except Exception:
    pass
sc.render.use_motion_blur = False
col = sc.collection

# ---------------- materials ----------------
MATS = {}
def flat(name, rgb):
    if name in MATS: return MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    e = nt.nodes.new("ShaderNodeEmission"); e.inputs[0].default_value = (*rgb, 1)
    o = nt.nodes.new("ShaderNodeOutputMaterial"); nt.links.new(e.outputs[0], o.inputs[0])
    MATS[name] = m
    return m

def pbr(name, rgb, rough=0.8, metal=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m

def ramp_mat(name, stops, tex="noise", scale=1.0, coord="Object", bump=0.0, rough=0.9,
             wave_dir='Z', distortion=2.0, detail=4.0, mapping_scale=(1, 1, 1), voronoi=False):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; L = nt.links
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = rough
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = mapping_scale
    if coord == "Position":
        geo = nt.nodes.new("ShaderNodeNewGeometry"); L.new(geo.outputs["Position"], mp.inputs[0])
    else:
        L.new(tc.outputs[coord], mp.inputs[0])
    if tex == "wave":
        t = nt.nodes.new("ShaderNodeTexWave"); t.wave_type = 'BANDS'; t.bands_direction = wave_dir
        t.inputs["Scale"].default_value = scale; t.inputs["Distortion"].default_value = distortion
        t.inputs["Detail"].default_value = detail
        fac = t.outputs["Fac"]
    elif voronoi:
        t = nt.nodes.new("ShaderNodeTexVoronoi"); t.inputs["Scale"].default_value = scale
        fac = t.outputs["Color"]
    else:
        t = nt.nodes.new("ShaderNodeTexNoise"); t.inputs["Scale"].default_value = scale
        t.inputs["Detail"].default_value = detail
        fac = t.outputs["Fac"]
    L.new(mp.outputs[0], t.inputs["Vector"])
    cr = nt.nodes.new("ShaderNodeValToRGB")
    els = cr.color_ramp.elements
    els[0].position, els[0].color = stops[0][0], (*stops[0][1], 1)
    els[1].position, els[1].color = stops[-1][0], (*stops[-1][1], 1)
    for p, c in stops[1:-1]:
        e = els.new(p); e.color = (*c, 1)
    if voronoi:
        sep = nt.nodes.new("ShaderNodeRGBToBW"); L.new(fac, sep.inputs[0]); L.new(sep.outputs[0], cr.inputs[0])
    else:
        L.new(fac, cr.inputs[0])
    L.new(cr.outputs[0], b.inputs["Base Color"])
    if bump > 0:
        bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = bump
        src = t.outputs["Distance"] if voronoi else t.outputs["Fac"]
        L.new(src, bp.inputs["Height"]); L.new(bp.outputs[0], b.inputs["Normal"])
    return m

def setmat(o, m):
    o.data.materials.clear(); o.data.materials.append(m); return o


WORDS = [(0.0, 'Meet'), (0.19, 'Gary.'), (0.92, 'Gary'), (1.28, 'runs'), (1.47, 'the'), (1.65, 'city'), (2.02, 'budget,'), (2.58, 'and'), (2.79, 'Gary'), (3.21, 'hates'), (3.64, 'circles.'), (4.06, 'Circles'), (4.48, 'waste'), (4.69, 'metal,"'), (5.12, 'he'), (5.33, 'says.'), (5.72, 'Make'), (5.92, 'the'), (6.11, 'manhole'), (6.7, 'covers'), (7.09, 'square."'), (7.5, 'So'), (7.65, 'Joe'), (7.81, 'makes'), (8.11, 'them'), (8.27, 'square.'), (8.68, 'Day'), (8.89, 'one.'), (9.3, 'Joe'), (9.5, 'lifts'), (9.7, 'the'), (9.9, 'new'), (10.11, 'cover,'), (10.51, 'turns'), (10.71, 'it'), (10.91, 'just'), (11.11, 'a'), (11.31, 'little...'), (11.72, 'and'), (11.92, 'CLANG.'), (12.32, 'It'), (12.52, 'drops'), (12.71, 'straight'), (12.9, 'down'), (13.1, 'the'), (13.3, 'hole.'), (13.69, 'See,'), (14.16, 'a'), (14.34, 'square'), (14.53, 'is'), (14.71, 'wider'), (15.08, 'corner'), (15.44, 'to'), (15.63, 'corner'), (15.99, 'than'), (16.18, 'it'), (16.36, 'is'), (16.54, 'side'), (16.73, 'to'), (16.91, 'side.'), (17.09, 'Tilt'), (17.28, 'it,'), (17.84, 'and'), (18.04, 'it'), (18.24, 'slips'), (18.44, 'right'), (18.64, 'through.'), (18.84, 'Gary'), (19.24, 'orders'), (19.64, 'another'), (20.24, 'one.'), (21.02, 'CLANG.'), (21.21, 'And'), (21.4, 'another.'), (22.44, 'CLANG.'), (23.06, 'Now'), (23.23, 'the'), (23.4, 'city'), (23.74, 'is'), (23.92, 'out'), (24.09, 'three'), (24.26, 'covers,'), (24.86, 'and'), (25.02, 'a'), (25.18, 'guy'), (25.34, 'in'), (25.5, 'the'), (25.66, 'sewer'), (25.99, 'is'), (26.15, 'wearing'), (26.47, 'one'), (26.63, 'as'), (26.79, 'a'), (26.95, 'hat.'), (27.11, 'So'), (27.27, 'Joe'), (27.44, 'brings'), (27.6, 'back'), (27.76, 'the'), (27.92, 'circle.'), (28.64, 'A'), (28.81, 'circle'), (29.14, 'is'), (29.31, 'the'), (29.48, 'same'), (29.65, 'width'), (29.81, 'no'), (29.98, 'matter'), (30.32, 'how'), (30.48, 'you'), (30.65, 'turn'), (30.82, 'it,'), (30.99, 'so'), (31.15, 'it'), (31.32, 'can'), (31.49, 'never'), (31.82, 'fall'), (31.99, 'in.'), (32.38, 'You'), (32.57, 'never'), (32.94, 'have'), (33.13, 'to'), (33.32, 'line'), (33.51, 'it'), (33.69, 'up.'), (33.88, 'And'), (34.07, 'a'), (34.26, 'cover'), (34.63, 'that'), (34.82, 'weighs'), (35.01, 'over'), (35.38, 'a'), (35.57, 'hundred'), (35.94, 'pounds?'), (36.13, 'You'), (36.32, 'just'), (36.51, 'roll'), (36.69, 'it.'), (37.08, 'Gary'), (37.44, 'looks'), (37.62, 'at'), (37.8, 'the'), (37.98, 'bill.'), (38.44, 'Then'), (38.6, 'at'), (38.77, 'the'), (38.93, 'circle.'), (39.62, 'Fine,"'), (39.98, 'he'), (40.34, 'says.'), (40.98, 'But'), (41.19, "I'm"), (41.39, 'keeping'), (41.8, 'the'), (42.01, 'square'), (42.21, 'one."'), (42.74, 'As'), (42.87, 'a'), (43.01, 'coffee'), (43.27, 'table.')]


# ---------------- world / light ----------------
world = bpy.data.worlds.new("Sky"); sc.world = world; world.use_nodes = True
wn = world.node_tree; wl = wn.links
bgn = wn.nodes["Background"]
tco = wn.nodes.new("ShaderNodeTexCoord")
sxyz = wn.nodes.new("ShaderNodeSeparateXYZ"); wl.new(tco.outputs["Generated"], sxyz.inputs[0])
mr = wn.nodes.new("ShaderNodeMapRange")
mr.inputs[1].default_value, mr.inputs[2].default_value = -0.05, 0.75
wl.new(sxyz.outputs[2], mr.inputs[0])
skr = wn.nodes.new("ShaderNodeValToRGB"); el = skr.color_ramp.elements
el[0].position, el[0].color = 0.0, (0.98, 0.86, 0.72, 1)
el[1].position, el[1].color = 1.0, (0.16, 0.42, 0.90, 1)
e = el.new(0.25); e.color = (0.62, 0.80, 0.98, 1)
wl.new(mr.outputs[0], skr.inputs[0]); wl.new(skr.outputs[0], bgn.inputs[0])
bgn.inputs[1].default_value = 1.0

sun_d = bpy.data.lights.new("Sun", 'SUN'); sun_d.energy = 3.2; sun_d.color = (1.0, 0.93, 0.82); sun_d.angle = math.radians(4)
sun = bpy.data.objects.new("Sun", sun_d); col.objects.link(sun)
sun.rotation_euler = (math.radians(48), math.radians(-28), math.radians(-35))


# ---------------- helpers ----------------
def cube(name, loc, size, m):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object; o.name = name; o.scale = size
    return setmat(o, m)

def cyl(name, loc, r, depth, m, verts=32, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc, rotation=rot)
    o = bpy.context.object; o.name = name
    return setmat(o, m)

def sphere(name, loc, r, m, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=r, location=loc)
    o = bpy.context.object; o.name = name; o.scale = scale
    bpy.ops.object.shade_smooth()
    return setmat(o, m)

def window_mat(name, wall, glass, scale=(2.2, 1.0)):
    """building facade: brick texture used as a window grid"""
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; L = nt.links; b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.7
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1, 1, 1)
    L.new(geo.outputs["Position"], mp.inputs[0])
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); L.new(mp.outputs[0], sep.inputs[0])
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    add = nt.nodes.new("ShaderNodeMath"); add.operation = 'ADD'
    L.new(sep.outputs[0], add.inputs[0]); L.new(sep.outputs[1], add.inputs[1])
    L.new(add.outputs[0], comb.inputs[0]); L.new(sep.outputs[2], comb.inputs[1])
    br = nt.nodes.new("ShaderNodeTexBrick"); br.offset = 0.0; br.squash = 1.0
    br.inputs["Color1"].default_value = (*glass, 1); br.inputs["Color2"].default_value = (*glass, 1)
    br.inputs["Mortar"].default_value = (*wall, 1)
    br.inputs["Scale"].default_value = 1.0; br.inputs["Mortar Size"].default_value = 0.35
    br.inputs["Brick Width"].default_value = scale[0]; br.inputs["Row Height"].default_value = scale[1] * 1.4
    br.inputs["Mortar Smooth"].default_value = 0.0
    L.new(comb.outputs[0], br.inputs["Vector"])
    L.new(br.outputs["Color"], b.inputs["Base Color"])
    return m

def iron_mat(name, kind):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; L = nt.links; b = nt.nodes["Principled BSDF"]
    b.inputs["Metallic"].default_value = 0.6; b.inputs["Roughness"].default_value = 0.55
    tc = nt.nodes.new("ShaderNodeTexCoord")
    if kind == "rings":
        t = nt.nodes.new("ShaderNodeTexWave"); t.wave_type = 'RINGS'; t.inputs["Scale"].default_value = 3.0
        t.inputs["Distortion"].default_value = 0.0
        L.new(tc.outputs["Object"], t.inputs["Vector"])
    else:
        t = nt.nodes.new("ShaderNodeTexChecker"); t.inputs["Scale"].default_value = 6.0
        L.new(tc.outputs["Generated"], t.inputs["Vector"])
    cr = nt.nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = (0.10, 0.10, 0.11, 1); cr.color_ramp.elements[1].color = (0.22, 0.22, 0.23, 1)
    L.new(t.outputs["Fac"], cr.inputs[0]); L.new(cr.outputs[0], b.inputs["Base Color"])
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.5
    L.new(t.outputs["Fac"], bp.inputs["Height"]); L.new(bp.outputs[0], b.inputs["Normal"])
    return m

# ---------------- STREET SET (hole at origin of action: H) ----------------
H = (0.0, 4.0)
ASPHALT = ramp_mat("asphalt", [(0.3, (0.10, 0.10, 0.11)), (0.7, (0.16, 0.16, 0.17))], scale=40, bump=0.3, detail=8)
bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 60, 0)); setmat(bpy.context.object, ASPHALT)
CONC = ramp_mat("concrete", [(0.3, (0.55, 0.53, 0.50)), (0.7, (0.66, 0.64, 0.60))], scale=6, bump=0.2)
YELLOW_PAINT = pbr("paint_y", (0.95, 0.70, 0.05), rough=0.6)
WHITE_PAINT = pbr("paint_w", (0.9, 0.9, 0.88), rough=0.6)
for s_ in (-1, 1):
    cube(f"sidewalk{s_}", (s_ * 6.5, 60, 0.12), (3.0, 200, 0.24), CONC)
for i in range(30):                                       # centre line, dashed (road runs along Y)
    cube(f"dash{i}", (2.4, -6 + i * 4.0, 0.004), (0.12, 2.0, 0.01), YELLOW_PAINT)
for i in range(7):                                        # crosswalk behind the action
    cube(f"zebra{i}", (-4.2 + i * 1.4, 9.5, 0.004), (0.7, 2.2, 0.01), WHITE_PAINT)

FACADES = [((0.62, 0.22, 0.14), "brick"), ((0.85, 0.75, 0.55), "beige"), ((0.20, 0.45, 0.48), "teal"),
           ((0.75, 0.55, 0.35), "sand"), ((0.45, 0.20, 0.25), "plum"), ((0.88, 0.85, 0.80), "cream")]
GLASS = (0.12, 0.18, 0.26)
fac_mats = [window_mat(f"fac_{n}", c, GLASS) for c, n in FACADES]
y = -8.0; k = 0
while y < 120:
    for s_ in (-1, 1):
        w = random.uniform(5, 8); h = random.uniform(7, 18)
        cube(f"bld{k}", (s_ * (8.0 + 2.5 + random.uniform(0, 1.5)), y + w / 2, h / 2), (5, w - 0.3, h), random.choice(fac_mats))
        cube(f"roof{k}", (s_ * 10.5, y + w / 2, h + 0.15), (5.4, w - 0.1, 0.3), CONC)
        k += 1
    y += random.uniform(5, 8)

POLE_M = pbr("lamp_pole", (0.15, 0.17, 0.2), rough=0.4, metal=0.8)
LAMP_M = flat("lamp_glow", (1.0, 0.92, 0.7))
for i in range(8):
    yy = -4 + i * 12
    for s_ in (-1, 1):
        cyl(f"lamp{i}{s_}", (s_ * 5.3, yy, 2.5), 0.07, 5.0, POLE_M, 12)
        cube(f"lamparm{i}{s_}", (s_ * 4.85, yy, 4.95), (0.9, 0.08, 0.08), POLE_M)
        sphere(f"lampbulb{i}{s_}", (s_ * 4.4, yy, 4.85), 0.16, LAMP_M)

TRUNK = pbr("trunk", (0.30, 0.18, 0.10)); LEAF = pbr("leaf", (0.15, 0.45, 0.15), rough=0.8)
for i in range(10):
    yy = 2 + i * 9
    for s_ in (-1, 1):
        cyl(f"trunk{i}{s_}", (s_ * 7.4, yy, 1.0), 0.12, 2.0, TRUNK, 10)
        sphere(f"crown{i}{s_}", (s_ * 7.4, yy, 2.6), 1.0, LEAF, (1, 1, 1.1))

CONE_O = pbr("cone_o", (0.98, 0.35, 0.03), rough=0.5); CONE_W = pbr("cone_w", (0.95, 0.95, 0.95), rough=0.5)
def cone(name, x, yy):
    bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=0.2, radius2=0.03, depth=0.65, location=(x, yy, 0.36))
    setmat(bpy.context.object, CONE_O)
    cyl(name + "_band", (x, yy, 0.42), 0.13, 0.08, CONE_W, 24)
    cube(name + "_base", (x, yy, 0.025), (0.45, 0.45, 0.05), CONE_O)
for i, (x, yy) in enumerate(((-2.1, 5.6), (2.3, 5.8), (-2.6, 3.0), (2.9, 2.6))):
    cone(f"cone{i}", x, yy)
HYD = pbr("hydrant", (0.85, 0.1, 0.08), rough=0.4)
cyl("hydrant", (5.4, 6.5, 0.6), 0.16, 0.6, HYD, 16); sphere("hydrant_top", (5.4, 6.5, 0.92), 0.16, HYD)

# holes and covers (street)
HOLE_M = flat("hole_dark", (0.01, 0.01, 0.012))
RIM_M = pbr("rim", (0.25, 0.25, 0.27), rough=0.4, metal=0.8)
ROUND_IRON = iron_mat("iron_round", "rings"); SQUARE_IRON = iron_mat("iron_square", "grid")
COVER_R = 0.45; COVER_S = 0.80

def hole_round():
    g = bpy.data.objects.new("HoleRound", None); col.objects.link(g); g.location = (H[0], H[1], 0)
    d = cyl("hole_r_dark", (H[0], H[1], 0.004), COVER_R - 0.02, 0.006, HOLE_M, 48); d.parent = g; d.location = (0, 0, 0.004)
    bpy.ops.mesh.primitive_torus_add(major_radius=COVER_R + 0.02, minor_radius=0.035, major_segments=48, minor_segments=8)
    r = setmat(bpy.context.object, RIM_M); r.parent = g; r.location = (0, 0, 0.01); r.scale = (1, 1, 0.4)
    return g
def hole_square():
    g = bpy.data.objects.new("HoleSquare", None); col.objects.link(g); g.location = (H[0], H[1], 0)
    d = cube("hole_s_dark", (0, 0, 0), (COVER_S - 0.06, COVER_S - 0.06, 0.006), HOLE_M); d.parent = g; d.location = (0, 0, 0.004)
    for i, (dx, dy, sx, sy) in enumerate(((0, 0.42, 0.9, 0.06), (0, -0.42, 0.9, 0.06), (0.42, 0, 0.06, 0.9), (-0.42, 0, 0.06, 0.9))):
        r = cube(f"hole_s_rim{i}", (0, 0, 0), (sx, sy, 0.025), RIM_M); r.parent = g; r.location = (dx, dy, 0.012)
    return g
HOLE_R = hole_round(); HOLE_S = hole_square()

def cover3d(name, kind):
    if kind == "round":
        o = cyl(name, (0, 0, 0), COVER_R, 0.06, ROUND_IRON, 48)
    else:
        o = cube(name, (0, 0, 0), (COVER_S, COVER_S, 0.06), SQUARE_IRON)
        bev = o.modifiers.new("bev", 'BEVEL'); bev.width = 0.015; bev.segments = 2
    return o
CV_ROUND_IN_HOLE = cover3d("cv_round_hole", "round")     # sits in the hole (opening shots + ending)
CV_DROP = [cover3d(f"cv_drop{i}", "square") for i in range(3)]   # the three that fall in
CV_DROP_ROUND = cover3d("cv_drop_round", "round")        # dropped in without looking
CV_ROLL = cover3d("cv_roll", "round")                    # rolled down the street

# ---------------- OFFICE SET ----------------
O = (300.0, 0.0)
WOODF = ramp_mat("woodfloor", [(0.2, (0.38, 0.22, 0.12)), (0.6, (0.50, 0.31, 0.17)), (0.9, (0.42, 0.25, 0.13))],
                 scale=4.0, mapping_scale=(8, 0.6, 0.6), bump=0.2)
WALL = pbr("office_wall", (0.78, 0.86, 0.74), rough=0.9)
cube("off_floor", (O[0], O[1] + 4, -0.05), (14, 14, 0.1), WOODF)
cube("off_wallB", (O[0], O[1] + 6.0, 3), (14, 0.2, 6), WALL)
cube("off_wallL", (O[0] - 3.6, O[1] + 3, 3), (0.2, 8, 6), WALL)
cube("off_window_frame", (O[0] + 1.6, O[1] + 5.88, 2.7), (2.4, 0.06, 1.8), pbr("frame", (0.95, 0.95, 0.95)))
cube("off_window", (O[0] + 1.6, O[1] + 5.84, 2.7), (2.1, 0.06, 1.5), flat("sky_win", (0.55, 0.78, 0.98)))
cube("off_picture", (O[0] - 1.4, O[1] + 5.88, 2.9), (1.0, 0.06, 0.75), pbr("pframe", (0.25, 0.15, 0.08)))
cube("off_picture_in", (O[0] - 1.4, O[1] + 5.84, 2.9), (0.85, 0.06, 0.6), flat("chart_bg", (0.95, 0.95, 0.92)))
for i, hh in enumerate((0.15, 0.3, 0.22, 0.42)):            # little bar chart in the frame
    cube(f"off_bar{i}", (O[0] - 1.7 + i * 0.2, O[1] + 5.80, 2.68 + hh / 2), (0.12, 0.02, hh), flat(f"bar{i}", (0.1, 0.5, 0.2)))
POT = pbr("pot", (0.75, 0.35, 0.2)); cyl("off_pot", (O[0] - 2.8, O[1] + 5.0, 0.3), 0.3, 0.6, POT, 24)
for i in range(5):
    sphere(f"off_leaf{i}", (O[0] - 2.8 + random.uniform(-0.3, 0.3), O[1] + 5.0 + random.uniform(-0.2, 0.2), 0.9 + i * 0.22), 0.32, LEAF)
TABLE_C = (O[0] + 0.3, O[1] + 3.0)
tbl_top = cover3d("table_top", "square"); tbl_top.location = (TABLE_C[0], TABLE_C[1], 0.5)
LEG = pbr("table_leg", (0.15, 0.15, 0.16), rough=0.3, metal=0.9)
for dx in (-0.32, 0.32):
    for dy in (-0.32, 0.32):
        cyl("tleg", (TABLE_C[0] + dx, TABLE_C[1] + dy, 0.24), 0.03, 0.48, LEG, 12)
MUG = pbr("mug", (0.95, 0.95, 0.95), rough=0.3); MUGR = pbr("mug_red", (0.85, 0.1, 0.1), rough=0.3)
cyl("mug", (TABLE_C[0] + 0.12, TABLE_C[1] - 0.05, 0.62), 0.08, 0.18, MUG, 24)
cyl("mug_band", (TABLE_C[0] + 0.12, TABLE_C[1] - 0.05, 0.64), 0.082, 0.04, MUGR, 24)
cyl("coffee", (TABLE_C[0] + 0.12, TABLE_C[1] - 0.05, 0.71), 0.07, 0.01, flat("coffee", (0.18, 0.09, 0.04)), 24)

# ---------------- DIAGRAM STAGE ----------------
D = (500.0, 0.0, 1.5)
cube("dg_back", (D[0], D[1] + 0.6, D[2]), (16, 0.1, 14), flat("dg_paper", (0.96, 0.93, 0.84)))
dg = bpy.data.objects.new("dg_plane", None); col.objects.link(dg)
dg.location = (D[0], D[1] + 0.3, D[2]); dg.rotation_euler = (math.pi / 2, 0, 0)

# ---------------- camera ----------------
cam_d = bpy.data.cameras.new("Cam"); cam_d.lens = 30; cam_d.clip_start = 0.05; cam_d.clip_end = 600
cam = bpy.data.objects.new("Cam", cam_d); col.objects.link(cam); sc.camera = cam
tgt = bpy.data.objects.new("CamTarget", None); col.objects.link(tgt)
tc = cam.constraints.new('TRACK_TO'); tc.target = tgt; tc.track_axis = 'TRACK_NEGATIVE_Z'; tc.up_axis = 'UP_Y'

# ---------------- 2D character toolkit ----------------
INK = flat("ink", (0.03, 0.03, 0.035))
WHITE = flat("white", (0.98, 0.98, 0.97))

def ellipse(cx, cy, rx, ry, n=40, a0=0.0, a1=2 * math.pi):
    return [(cx + rx * math.cos(a0 + (a1 - a0) * i / n), cy + ry * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + (0 if a1 - a0 >= 2 * math.pi - 1e-6 else 1))]

def rrect(cx, cy, w, h, r, n=8):
    pts = []
    for qx, qy, a in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        ccx, ccy = cx + qx * (w / 2 - r), cy + qy * (h / 2 - r)
        for i in range(n + 1):
            t = math.radians(a + 90 * i / n)
            pts.append((ccx + r * math.cos(t), ccy + r * math.sin(t)))
    return pts

def _curve(name, pts, cyclic, dims):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = dims
    sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
    for p, (x, y) in zip(sp.points, pts):
        p.co = (x, y, 0, 1)
    sp.use_cyclic_u = cyclic
    return cu

def add_obj(name, data, parent, z, m):
    o = bpy.data.objects.new(name, data); col.objects.link(o)
    o.parent = parent; o.location = (0, 0, z)
    o.data.materials.append(m)
    return o

def shape(parent, name, pts, m, z, outline=0.035):
    """filled 2D shape with black outline; returns list of objects"""
    cu = _curve(name, pts, True, '2D'); cu.fill_mode = 'BOTH'
    a = add_obj(name, cu, parent, z, m)
    out = []
    if outline:
        cu2 = _curve(name + "_ol", pts, True, '3D'); cu2.bevel_depth = outline / 2; cu2.bevel_resolution = 2
        out.append(add_obj(name + "_ol", cu2, parent, z, INK))
    return [a] + out

def stroke(parent, name, pts, w, z, m=None, cyclic=False):
    cu = _curve(name, pts, cyclic, '3D'); cu.bevel_depth = w / 2; cu.bevel_resolution = 2; cu.use_fill_caps = True
    return [add_obj(name, cu, parent, z, m or INK)]

def disc(parent, name, cx, cy, r, z, m=INK):
    return shape(parent, name, ellipse(cx, cy, r, r, 24), m, z, outline=0)

def empty(name, parent=None, loc=(0, 0, 0)):
    o = bpy.data.objects.new(name, None); col.objects.link(o)
    o.parent = parent; o.location = loc
    return o

def limb(parent, name, origin, L1, L2, w, z, hand=None):
    """two-segment stick limb. returns (upper, lower) pivots"""
    up = empty(name + "_up", parent, (origin[0], origin[1], z))
    stroke(up, name + "_s1", [(0, 0), (0, -L1)], w, 0)
    disc(up, name + "_j", 0, -L1, w / 2, 0)
    lo = empty(name + "_lo", up, (0, -L1, 0))
    stroke(lo, name + "_s2", [(0, 0), (0, -L2)], w, 0)
    if hand == "hand":
        shape(lo, name + "_hand", ellipse(0, -L2 - 0.05, 0.075, 0.075, 24), WHITE, 0.03, outline=0.03)
    elif hand == "shoe":
        shape(lo, name + "_shoe", ellipse(0.04, -L2 - 0.02, 0.13, 0.065, 24), INK, 0.0, outline=0)
    return up, lo

def char_root(name, loc):
    root = empty(name, None, loc)
    lt = root.constraints.new('LOCKED_TRACK'); lt.target = cam; lt.track_axis = 'TRACK_NEGATIVE_Y'; lt.lock_axis = 'LOCK_Z'
    plane = empty(name + "_plane", root); plane.rotation_euler = (math.pi / 2, 0, 0)
    return root, plane

def group(parent, name):
    return empty(name, parent)

def set_visible(grp, frame, vis):
    for o in [grp] + list(grp.children_recursive):
        o.hide_render = not vis; o.hide_viewport = not vis
        o.keyframe_insert("hide_render", frame=frame); o.keyframe_insert("hide_viewport", frame=frame)


# ==========================================================
#  V2 TOOLKIT: easing, character life, FX pools, camera polish, film look
# ==========================================================
# ---------------- easing ----------------
def clamp01(u): return max(0.0, min(1.0, u))
def ease(u): u = clamp01(u); return u * u * (3 - 2 * u)
def ease_out_back(u, s=1.4):                 # overshoot then settle: use for gestures, pops, punch-ins
    u = clamp01(u) - 1; return u * u * ((s + 1) * u + s) + 1
def ease_out_elastic(u):                     # wobble settle: hats, springy props
    u = clamp01(u)
    if u in (0.0, 1.0): return u
    return 2 ** (-10 * u) * math.sin((u * 10 - 0.75) * (2 * math.pi) / 3) + 1
def ease_out_bounce(u):                      # things landing
    u = clamp01(u); n1, d1 = 7.5625, 2.75
    if u < 1 / d1: return n1 * u * u
    if u < 2 / d1: u -= 1.5 / d1; return n1 * u * u + 0.75
    if u < 2.5 / d1: u -= 2.25 / d1; return n1 * u * u + 0.9375
    u -= 2.625 / d1; return n1 * u * u + 0.984375
def pease(f, a, n=8): return ease_out_back((f - a) / n)     # pose transition with overshoot
def noise1(t, seed=0.0):                     # smooth pseudo-noise from summed sines, range ~[-1, 1]
    return (math.sin(t * 1.3 + seed) * 0.5 + math.sin(t * 2.7 + seed * 1.7) * 0.3 + math.sin(t * 5.1 + seed * 2.3) * 0.2)

# ---------------- voice amplitude (lip flap, head bobs) ----------------
def load_amplitude(path, n_frames, fps):
    amp = [0.0] * (n_frames + 2)
    try:
        with wave.open(path, "rb") as w:
            sr = w.getframerate(); ch = w.getnchannels(); sw = w.getsampwidth()
            raw = w.readframes(w.getnframes())
        x = np.frombuffer(raw, dtype=np.int16 if sw == 2 else np.int32).astype(np.float64)
        if ch > 1: x = x.reshape(-1, ch).mean(axis=1)
        x /= np.abs(x).max() + 1e-9
        hop = sr / fps
        for f in range(1, n_frames + 1):
            seg = x[int((f - 1) * hop):int(f * hop)]
            if len(seg):
                db = 20 * math.log10(math.sqrt(float(np.mean(seg ** 2))) + 1e-6)
                amp[f] = clamp01((db + 38) / 26)
    except Exception as e:
        print("amplitude: no voice file, using synthetic flap", e)
        for f in range(1, n_frames + 1):
            amp[f] = clamp01(0.5 + 0.5 * math.sin(f * 1.9) * math.sin(f * 0.7))
    return amp

# ---------------- FX: dust puffs (pooled billboards) ----------------
PUFF_M = flat("puff_fill", (0.93, 0.90, 0.85))
PUFF_POOL = []; PUFF_EVENTS = []
def _make_puff(i):
    root = empty(f"puff_root{i}", None, (0, 0, -20))
    lt = root.constraints.new('LOCKED_TRACK'); lt.target = cam; lt.track_axis = 'TRACK_NEGATIVE_Y'; lt.lock_axis = 'LOCK_Z'
    pl = empty(f"puff_pl{i}", root); pl.rotation_euler = (math.pi / 2, 0, 0)
    for k, (dx_, dy_, r) in enumerate(((0, 0, 0.12), (0.09, 0.05, 0.09), (-0.08, 0.06, 0.08))):
        shape(pl, f"puff{i}_{k}", ellipse(dx_, dy_, r, r, 18), PUFF_M, 0.01 * k, outline=0.022)
    root.scale = (0, 0, 0)
    return root
def dust_burst(frame, pos, n=8, radius=0.7, size=1.0, life=20, rise=0.35):
    """schedule a ring of dust puffs at a 3D position (impacts, landings, skids)"""
    rnd = random.Random(frame * 7 + int(pos[0] * 13))
    for k in range(n):
        a = 2 * math.pi * k / n + rnd.uniform(-0.3, 0.3)
        PUFF_EVENTS.append((frame + rnd.randint(0, 2), pos, (math.cos(a), math.sin(a)), radius * rnd.uniform(0.7, 1.2),
                            size * rnd.uniform(0.7, 1.3), life + rnd.randint(-3, 4), rise * rnd.uniform(0.6, 1.4)))
def bake_dust():
    if not PUFF_EVENTS: return
    busy = []                                           # (pool index, free_after_frame)
    for ev in sorted(PUFF_EVENTS):
        f0, pos, d, rad, sz, life, rise = ev
        idx = next((i for i, (p, free) in enumerate(busy) if free < f0 - 2), None)
        if idx is None:
            PUFF_POOL.append(_make_puff(len(PUFF_POOL))); busy.append((len(PUFF_POOL) - 1, 0)); idx = len(busy) - 1
        pidx = busy[idx][0]; busy[idx] = (pidx, f0 + life + 1); o = PUFF_POOL[pidx]
        o.scale = (0, 0, 0); o.keyframe_insert("scale", frame=max(1, f0 - 1))
        for f in range(f0, min(N, f0 + life) + 1):
            u = (f - f0) / life; e = ease_out_back(u * 1.6, 1.0) if u < 0.62 else 1.0
            s = sz * (0.35 + 0.9 * e) * (1 - ease((u - 0.55) / 0.45))
            o.location = (pos[0] + d[0] * rad * ease(u * 1.3), pos[1] + d[1] * rad * ease(u * 1.3), pos[2] + 0.08 + rise * ease(u))
            o.scale = (s, s, s); o.keyframe_insert("scale", frame=f); o.keyframe_insert("location", frame=f)
        if f0 + life + 1 <= N:
            o.scale = (0, 0, 0); o.keyframe_insert("scale", frame=f0 + life + 1)

# ---------------- FX: shock lines + "!" above a character ----------------
def add_reaction_fx(c):
    sl = empty(c.name + "_speedlines", c.head, (0, 0, -0.3))
    for k in range(16):
        a = 2 * math.pi * k / 16; r0, r1 = 0.62, 0.95 + 0.12 * (k % 2)
        w_ = 0.035
        p0 = (r0 * math.cos(a), r0 * math.sin(a)); p1 = (r1 * math.cos(a), r1 * math.sin(a))
        nx, ny = -math.sin(a) * w_, math.cos(a) * w_
        shape(sl, f"{c.name}_sl{k}", [(p0[0] + nx * 0.3, p0[1] + ny * 0.3), (p1[0] + nx, p1[1] + ny), (p1[0] - nx, p1[1] - ny), (p0[0] - nx * 0.3, p0[1] - ny * 0.3)],
              INK, 0, outline=0)
    sl.scale = (0, 0, 0); c.speedlines = sl
    ex = empty(c.name + "_excl", c.head, (0.58, 0.62, 0.4))
    for layer, (m, off, z) in enumerate(((INK, 0.05, -0.01), (flat("excl_red", (0.92, 0.1, 0.08)), 0.0, 0.0))):
        cu = bpy.data.curves.new(f"{c.name}_ex{layer}", 'FONT'); cu.body = "!"; cu.size = 0.45; cu.offset = off
        cu.align_x = 'CENTER'; cu.align_y = 'CENTER'
        if FONT_PATH: cu.font = bpy.data.fonts.load(FONT_PATH, check_existing=True)
        o = bpy.data.objects.new(f"{c.name}_ex{layer}", cu); col.objects.link(o); o.parent = ex; o.location = (0, 0, z)
        o.rotation_euler = (0, 0, -0.2); o.data.materials.append(m)
    ex.scale = (0, 0, 0); c.excl = ex
def bake_reaction_fx(c, frames, dur=16):
    for o_ in (c.speedlines, c.excl):
        o_.scale = (0, 0, 0); o_.keyframe_insert("scale", frame=1)
    for f0 in frames:
        for f in range(f0, min(N, f0 + dur) + 1):
            u = (f - f0) / dur
            s_l = ease_out_back(u * 4, 2.0) * (1 - ease((u - 0.6) / 0.4))
            c.speedlines.scale = (s_l, s_l, 1); c.speedlines.rotation_euler = (0, 0, 0.15 * math.sin(f * 1.3))
            s_e = ease_out_back(u * 3, 2.2) * (1 - ease((u - 0.75) / 0.25))
            c.excl.scale = (s_e, s_e, 1); c.excl.location = (0.58, 0.62 + 0.08 * ease(u), 0.4)
            for o_ in (c.speedlines, c.excl):
                o_.keyframe_insert("scale", frame=f)
            c.speedlines.keyframe_insert("rotation_euler", frame=f); c.excl.keyframe_insert("location", frame=f)
        for o_ in (c.speedlines, c.excl):
            o_.scale = (0, 0, 0); o_.keyframe_insert("scale", frame=min(N, f0 + dur + 1))

# ---------------- talking mouth (lip flap from the voice) ----------------
def add_talk_mouth(c, ey=-0.02):
    g = empty(c.name + "_talk", c.head, (0, 0, 0.14))
    shape(g, c.name + "_talk_patch", ellipse(0, ey - 0.17, 0.22, 0.12, 24), c.skin, 0, outline=0)
    piv = empty(c.name + "_talk_piv", g, (0, ey - 0.17, 0.02))
    shape(piv, c.name + "_talk_m", ellipse(0, 0, 0.12, 0.10, 24), MOUTH, 0, outline=0.03)
    shape(piv, c.name + "_talk_t", ellipse(0, -0.05, 0.06, 0.035, 16), TONGUE, 0.02, outline=0)
    shape(piv, c.name + "_talk_teeth", rrect(0, 0.065, 0.14, 0.035, 0.01), TEETH, 0.02, outline=0)
    c.talk = g; c.talk_piv = piv
def bake_talk(c, ranges, amp):
    vis_track(c.talk, ranges)
    for f in range(1, N + 1):
        on = any(a <= f <= b for a, b in ranges)
        o = 0.18 + 0.82 * amp[f] if on else 0.2
        c.talk_piv.scale = (0.9 + 0.15 * o, o, 1); c.talk_piv.keyframe_insert("scale", frame=f)

# ---------------- reactions baked into the body (squash & stretch) ----------------
def react_offsets(c, f):
    """returns (dy, sy, lean) for hop / flinch / shiver reactions registered in c.reacts"""
    dy, sy, lean = 0.0, 1.0, 0.0
    for t0, kind in getattr(c, "reacts", []):
        if kind == "hop" and t0 - 4 <= f <= t0 + 16:
            if f < t0:                                       # anticipation: crouch
                sy -= 0.10 * ease((f - (t0 - 4)) / 4)
            else:
                u = (f - t0) / 16
                dy += 0.22 * math.sin(math.pi * min(1, u / 0.8)) if u < 0.8 else 0.0
                if u < 0.25: sy += 0.12 * (1 - u / 0.25)     # stretch on take-off
                elif u > 0.8: sy -= 0.12 * math.sin(math.pi * (u - 0.8) / 0.2)   # squash on landing
        elif kind == "flinch" and t0 <= f <= t0 + 20:
            u = (f - t0) / 20; lean += -0.18 * (1 - ease_out_elastic(u)); sy -= 0.05 * (1 - ease(u))
        elif kind == "shiver" and t0 <= f <= t0 + 30:
            lean += 0.04 * math.sin(f * 2.4) * (1 - (f - t0) / 30)
        elif kind == "proud" and t0 <= f <= t0 + 14:
            u = (f - t0) / 14; sy += 0.07 * math.sin(math.pi * u); dy += 0.04 * math.sin(math.pi * u)
    return dy, sy, lean

# ---------------- film look: outlines, bloom, mist, vignette, colour ----------------
def setup_look(noline_objs):
    vl = sc.view_layers[0]
    nol = bpy.data.collections.new("NOLINE"); sc.collection.children.link(nol)
    for o in noline_objs:
        if o.name not in nol.objects: nol.objects.link(o)
        if o.name in col.objects: col.objects.unlink(o)
    # Freestyle is CPU-bound (~40 s/frame on this scene) -> GPU inverted-hull outlines instead
    sc.render.use_freestyle = False
    add_ink_outlines([o for o in sc.objects if o.type == 'MESH' and o.name not in nol.objects])
    sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.45
    vl.use_pass_mist = True
    sc.world.mist_settings.start = 14; sc.world.mist_settings.depth = 110; sc.world.mist_settings.falloff = 'QUADRATIC'
    ng = bpy.data.node_groups.new("FilmLook", 'CompositorNodeTree')
    ng.interface.new_socket("Image", in_out='OUTPUT', socket_type='NodeSocketColor')
    n = ng.nodes; L = ng.links
    rl = n.new('CompositorNodeRLayers')
    gl = n.new('CompositorNodeGlare'); gl.inputs["Type"].default_value = 'Bloom'
    gl.inputs["Threshold"].default_value = 0.92; gl.inputs["Strength"].default_value = 0.35; gl.inputs["Size"].default_value = 0.6
    mist = n.new('ShaderNodeMix'); mist.data_type = 'RGBA'; mist.blend_type = 'MIX'
    mfac = n.new('ShaderNodeMath'); mfac.operation = 'MULTIPLY'; mfac.inputs[1].default_value = 0.45
    hs = n.new('CompositorNodeHueSat'); hs.inputs["Saturation"].default_value = 1.10
    bc = n.new('CompositorNodeBrightContrast'); bc.inputs["Contrast"].default_value = 6.0
    em = n.new('CompositorNodeEllipseMask'); em.inputs["Size"].default_value = (1.05, 1.15)
    bl = n.new('CompositorNodeBlur'); bl.inputs["Size"].default_value = (180, 180)
    inv = n.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
    vf = n.new('ShaderNodeMath'); vf.operation = 'MULTIPLY'; vf.inputs[1].default_value = 0.38
    vig = n.new('ShaderNodeMix'); vig.data_type = 'RGBA'; vig.blend_type = 'MULTIPLY'
    vig.inputs[7].default_value = (0.0, 0.0, 0.0, 1.0)
    out = n.new('NodeGroupOutput')
    L.new(rl.outputs["Image"], gl.inputs["Image"])
    L.new(rl.outputs["Mist"], mfac.inputs[0]); L.new(mfac.outputs[0], mist.inputs[0])
    L.new(gl.outputs["Image"], mist.inputs[6]); mist.inputs[7].default_value = (0.78, 0.86, 0.95, 1.0)
    L.new(mist.outputs[2], hs.inputs["Image"]); L.new(hs.outputs["Image"], bc.inputs["Image"])
    L.new(em.outputs["Mask"], bl.inputs["Image"]); L.new(bl.outputs["Image"], inv.inputs[1]); L.new(inv.outputs[0], vf.inputs[0])
    L.new(vf.outputs[0], vig.inputs[0]); L.new(bc.outputs["Image"], vig.inputs[6])
    L.new(vig.outputs[2], out.inputs[0])
    sc.compositing_node_group = ng
    return ng

INK_HULL = None
def add_ink_outlines(objs):
    """cartoon outlines that render on the GPU: solidify shell, normals flipped, back faces culled"""
    global INK_HULL
    if INK_HULL is None:
        INK_HULL = bpy.data.materials.new("ink_hull"); INK_HULL.use_nodes = True
        nt = INK_HULL.node_tree; nt.nodes.clear()
        e = nt.nodes.new("ShaderNodeEmission"); e.inputs[0].default_value = (0.05, 0.04, 0.04, 1)
        o_ = nt.nodes.new("ShaderNodeOutputMaterial"); nt.links.new(e.outputs[0], o_.inputs[0])
        INK_HULL.use_backface_culling = True
    done = set()
    for o in objs:
        dims = o.dimensions
        if max(dims) > 150 or min(dims) < 0.003 and max(dims) > 50:   # ground planes and the like
            continue
        if o.data.name in done or o.data.users > 1:
            continue
        if any(m.type in ('ARRAY', 'DISPLACE', 'SUBSURF') for m in o.modifiers):
            pass
        elif tuple(o.scale) != (1.0, 1.0, 1.0):                       # bake scale so the shell is even
            o.data.transform(Matrix.Diagonal((*o.scale, 1.0))); o.scale = (1, 1, 1)
        size = max(o.dimensions)
        t = 0.012 if size < 0.6 else 0.02 if size < 2.5 else 0.045 if size < 20 else 0.25
        o.data.materials.append(INK_HULL)
        sol = o.modifiers.new("ink", 'SOLIDIFY'); sol.thickness = t; sol.offset = 1.0
        sol.use_flip_normals = True; sol.material_offset = len(o.data.materials) - 1; sol.use_rim = False
        done.add(o.data.name)

def descendants(o):
    return [o] + list(o.children_recursive)

# ---------------- faces library ----------------
MOUTH = flat("mouth", (0.55, 0.10, 0.10)); TONGUE = flat("tongue", (0.95, 0.45, 0.45))
TEETH = flat("teeth", (1, 1, 1)); SWEAT = flat("sweat", (0.45, 0.75, 1.0)); RED_M = flat("vein", (0.85, 0.1, 0.1))

def eye(parent, name, x, y, z, rx=0.055, ry=0.085):
    g = empty(name, parent, (x, y, z)); disc(g, name + "_d", 0, 0, 1.0, 0, INK); g.scale = (rx, ry, 1); return g

def arc(cx, cy, rx, ry, a0, a1, n=10):
    return ellipse(cx, cy, rx, ry, n, math.radians(a0), math.radians(a1))

def build_faces(head, p, skin, kinds, ey=-0.02, dx=0.15):
    """returns dict kind -> group, plus 'blink' eye list for neutral"""
    F = {}; blink_eyes = []
    for kind in kinds:
        g = empty(f"{p}_{kind}", head); F[kind] = g; z = 0.06
        if kind == "neutral":
            blink_eyes += [eye(g, f"{p}nL", -dx, ey, z), eye(g, f"{p}nR", dx, ey, z)]
            stroke(g, f"{p}n_m", arc(0, ey - 0.11, 0.11, 0.06, 200, 340), 0.035, z)
            stroke(g, f"{p}n_bL", [(-dx - 0.07, ey + 0.14), (-dx + 0.06, ey + 0.16)], 0.03, z)
            stroke(g, f"{p}n_bR", [(dx - 0.06, ey + 0.16), (dx + 0.07, ey + 0.14)], 0.03, z)
        elif kind == "happy":
            for s in (-1, 1):
                stroke(g, f"{p}h_e{s}", arc(s * dx, ey - 0.03, 0.07, 0.07, 20, 160), 0.035, z)
            mp = [(-0.17, ey - 0.10)] + arc(0, ey - 0.10, 0.17, 0.17, 180, 360, 16)[1:]
            shape(g, f"{p}h_m", mp, MOUTH, z, outline=0.03)
            shape(g, f"{p}h_t", ellipse(0, ey - 0.22, 0.07, 0.04, 16), TONGUE, z + 0.02, outline=0)
        elif kind in ("smirk", "wink"):
            eye(g, f"{p}s_eL", -dx, ey - 0.01, z, 0.055, 0.065)
            shape(g, f"{p}s_lidL", rrect(-dx, ey + 0.04, 0.15, 0.06, 0.02), skin, z + 0.03, outline=0)
            stroke(g, f"{p}s_llL", [(-dx - 0.07, ey + 0.015), (-dx + 0.07, ey + 0.015)], 0.03, z + 0.04)
            if kind == "wink":
                stroke(g, f"{p}w_eR", arc(dx, ey - 0.04, 0.07, 0.06, 20, 160), 0.035, z)
            else:
                eye(g, f"{p}s_eR", dx, ey - 0.01, z, 0.055, 0.065)
                shape(g, f"{p}s_lidR", rrect(dx, ey + 0.04, 0.15, 0.06, 0.02), skin, z + 0.03, outline=0)
                stroke(g, f"{p}s_llR", [(dx - 0.07, ey + 0.015), (dx + 0.07, ey + 0.015)], 0.03, z + 0.04)
            stroke(g, f"{p}s_bL", [(-dx - 0.08, ey + 0.12), (-dx + 0.07, ey + 0.11)], 0.03, z)
            stroke(g, f"{p}s_bR", [(dx - 0.07, ey + 0.17), (dx + 0.01, ey + 0.21), (dx + 0.08, ey + 0.19)], 0.03, z)
            stroke(g, f"{p}s_m", [(-0.10, ey - 0.15), (0.02, ey - 0.16), (0.11, ey - 0.13), (0.15, ey - 0.09)], 0.035, z)
        elif kind == "angry":
            eye(g, f"{p}a_eL", -dx + 0.01, ey + 0.0, z, 0.05, 0.05); eye(g, f"{p}a_eR", dx - 0.01, ey, z, 0.05, 0.05)
            stroke(g, f"{p}a_bL", [(-dx - 0.12, ey + 0.16), (-dx + 0.10, ey + 0.05)], 0.05, z + 0.01)
            stroke(g, f"{p}a_bR", [(dx - 0.10, ey + 0.05), (dx + 0.12, ey + 0.16)], 0.05, z + 0.01)
            shape(g, f"{p}a_t", rrect(0, ey - 0.20, 0.26, 0.12, 0.03), TEETH, z, outline=0.03)
            for x in (-0.065, 0, 0.065):
                stroke(g, f"{p}a_tt{x}", [(x, ey - 0.25), (x, ey - 0.15)], 0.015, z + 0.03)
            stroke(g, f"{p}a_tm", [(-0.12, ey - 0.20), (0.12, ey - 0.20)], 0.015, z + 0.03)
            stroke(g, f"{p}a_v1", [(0.20, 0.33), (0.26, 0.28)], 0.03, z, m=RED_M); stroke(g, f"{p}a_v2", [(0.27, 0.36), (0.29, 0.29)], 0.03, z, m=RED_M)
        elif kind == "shock":
            for s in (-1, 1):
                shape(g, f"{p}k_w{s}", ellipse(s * dx, ey + 0.01, 0.085, 0.11, 24), WHITE, z, outline=0.03)
                disc(g, f"{p}k_p{s}", s * dx, ey + 0.0, 0.035, z + 0.03)
                stroke(g, f"{p}k_b{s}", arc(s * dx, ey + 0.13, 0.08, 0.05, 30, 150), 0.03, z)
            shape(g, f"{p}k_m", ellipse(0, ey - 0.20, 0.08, 0.10, 24), MOUTH, z, outline=0.03)
        elif kind == "worried":
            eye(g, f"{p}o_eL", -dx, ey, z, 0.05, 0.075); eye(g, f"{p}o_eR", dx, ey, z, 0.05, 0.075)
            stroke(g, f"{p}o_bL", [(-dx - 0.08, ey + 0.11), (-dx + 0.07, ey + 0.16)], 0.03, z)
            stroke(g, f"{p}o_bR", [(dx - 0.07, ey + 0.16), (dx + 0.08, ey + 0.11)], 0.03, z)
            stroke(g, f"{p}o_m", [(-0.10, ey - 0.17), (-0.05, ey - 0.14), (0, ey - 0.17), (0.05, ey - 0.14), (0.10, ey - 0.17)], 0.03, z)
            shape(g, f"{p}o_sw", [(0.33, 0.22), (0.37, 0.12), (0.37, 0.08), (0.33, 0.05), (0.29, 0.08), (0.29, 0.12)], SWEAT, z, outline=0.02)
        elif kind == "grumpy":
            for s in (-1, 1):
                eye(g, f"{p}g_e{s}", s * dx, ey - 0.02, z, 0.055, 0.04)
                stroke(g, f"{p}g_b{s}", [(s * (dx + 0.09), ey + 0.08), (s * (dx - 0.07), ey + 0.06)], 0.04, z)
            stroke(g, f"{p}g_m", arc(0, ey - 0.22, 0.10, 0.05, 20, 160), 0.035, z)
        elif kind == "focus":
            for s in (-1, 1):
                eye(g, f"{p}f_e{s}", s * dx, ey, z, 0.05, 0.05)
                stroke(g, f"{p}f_b{s}", [(s * (dx + 0.08), ey + 0.12), (s * (dx - 0.07), ey + 0.09)], 0.03, z)
            stroke(g, f"{p}f_m", [(-0.05, ey - 0.15), (0.06, ey - 0.15)], 0.03, z)
            shape(g, f"{p}f_tg", ellipse(0.09, ey - 0.17, 0.04, 0.03, 12), TONGUE, z, outline=0.015)
        elif kind == "smug_closed":
            for s in (-1, 1):
                stroke(g, f"{p}c_e{s}", arc(s * dx, ey + 0.02, 0.07, 0.05, 200, 340), 0.035, z)
            stroke(g, f"{p}c_m", [(-0.12, ey - 0.13), (0, ey - 0.17), (0.12, ey - 0.13), (0.16, ey - 0.10)], 0.035, z)
    return F, blink_eyes

# ---------------- IK + character builder ----------------
def ik(sh, tgt, L1, L2, bend=1):
    dx, dy = tgt[0] - sh[0], tgt[1] - sh[1]
    d = max(min(math.hypot(dx, dy), L1 + L2 - 1e-3), abs(L1 - L2) + 1e-3)
    base = math.atan2(dx, -dy)
    off = math.acos(max(-1, min(1, (L1 * L1 + d * d - L2 * L2) / (2 * L1 * d))))
    a1 = base + bend * off
    ex, ey_ = sh[0] + L1 * math.sin(a1), sh[1] - L1 * math.cos(a1)
    a_abs = math.atan2(tgt[0] - ex, -(tgt[1] - ey_))
    return a1, a_abs - a1

class Char:
    pass

def make_char(name, loc, cfg):
    """cfg: leg (hipY, L1, L2), torso (w, h, color), arm (shY, shX, L1, L2), head (y, r), skin, extras(fn), faces"""
    c = Char(); c.name = name
    c.root, c.plane = char_root(name, loc)
    c.body = empty(name + "_body", c.plane)
    hipY, lL1, lL2 = cfg["leg"]
    c.legL = limb(c.body, name + "_legL", (-0.15, hipY), lL1, lL2, 0.065, 0.05, "shoe")
    c.legR = limb(c.body, name + "_legR", (0.15, hipY), lL1, lL2, 0.065, 0.05, "shoe")
    c.torso = empty(name + "_torso", c.body, (0, hipY - 0.04, 0))
    tw, th, tcol = cfg["torso"]
    shape(c.torso, name + "_shirt", rrect(0, th / 2, tw, th, 0.3 if tw < 0.9 else 0.32), tcol, 0.12)
    shX, shY, aL1, aL2 = cfg["arm"]
    c.sh = {"L": (-shX, shY), "R": (shX, shY)}; c.aL = (aL1, aL2)
    c.armL = limb(c.torso, name + "_armL", (-shX, shY), aL1, aL2, 0.05, 0.30, "hand")
    c.armR = limb(c.torso, name + "_armR", (shX, shY), aL1, aL2, 0.05, 0.30, "hand")
    stroke(c.torso, name + "_neck", [(0, th - 0.04), (0, th + 0.08)], 0.06, 0.1)
    hy, hr = cfg["head"]
    c.head = empty(name + "_head", c.torso, (0, hy, 0.36))
    c.skin = flat(name + "_skin", (0.98, 0.98, 0.97))
    shape(c.head, name + "_face", ellipse(0, 0, hr, hr * 0.97, 48), c.skin, 0.0)
    cfg["extras"](c)
    c.F, c.blink = build_faces(c.head, name, c.skin, cfg["faces"], ey=cfg.get("eye_y", -0.02))
    c.hist = {}; c.expr_table = []
    return c

def pose_char(c, f, armL=None, armR=None, legL=(-0.06, 0.02), legR=(0.06, -0.02), head_tilt=0.0, body=(0, 0), breath=True, lean=0.0):
    """arm specs: ('ang', a1, a2) or ('ik', (x, y), bend) in torso coords.
    V2: forearms drag behind fast upper-arm moves (follow-through), reactions add squash/stretch, head lags the body."""
    if not hasattr(c, "prev"): c.prev = {}; c.vel = {}
    for side, spec, lp in (("L", armL, c.armL), ("R", armR, c.armR)):
        if spec is None: spec = ('ang', -0.25 if side == "L" else 0.25, 0.1 if side == "L" else -0.1)
        if spec[0] == 'ik':
            a1, a2 = ik(c.sh[side], spec[1], c.aL[0], c.aL[1], spec[2])
        else:
            a1, a2 = spec[1], spec[2]
        v = a1 - c.prev.get(side, a1); c.vel[side] = 0.55 * c.vel.get(side, 0.0) + 0.45 * v; c.prev[side] = a1
        a2 = a2 - max(-0.5, min(0.5, 1.6 * c.vel[side]))            # forearm drags behind
        lp[0].rotation_euler = (0, 0, a1); lp[1].rotation_euler = (0, 0, a2)
        lp[0].keyframe_insert("rotation_euler", frame=f); lp[1].keyframe_insert("rotation_euler", frame=f)
        c.hist.setdefault(side, []).append((f, a1 + 0.5 * a2))
    for spec, lp in ((legL, c.legL), (legR, c.legR)):
        lp[0].rotation_euler = (0, 0, spec[0]); lp[1].rotation_euler = (0, 0, spec[1])
        lp[0].keyframe_insert("rotation_euler", frame=f); lp[1].keyframe_insert("rotation_euler", frame=f)
    t = f / FPS
    dy, sy, rlean = react_offsets(c, f)
    b = (1 + (0.014 * math.sin(t * 2.4 + len(c.name)) if breath else 0)) * sy
    sway = 0.02 * noise1(t * 0.8, len(c.name))                      # idle weight shift
    c.body.scale = (1 / math.sqrt(b), b, 1); c.body.location = (body[0], body[1] + dy, 0)
    c.body.rotation_euler = (0, 0, lean + rlean + sway)
    c.body.keyframe_insert("scale", frame=f); c.body.keyframe_insert("location", frame=f); c.body.keyframe_insert("rotation_euler", frame=f)
    lag = getattr(c, "lag_tilt", 0.0)
    c.lag_tilt = lag + 0.35 * (-(lean + rlean) * 0.6 - lag)                # head follows the lean a few frames late
    talk = getattr(c, "amp_now", 0.0)
    c.head.rotation_euler = (0, 0, head_tilt + 0.03 * math.sin(t * 1.7) + c.lag_tilt + 0.05 * talk * math.sin(f * 0.9))
    c.head.location = (0, c.head.location[1], c.head.location[2]); c.head.keyframe_insert("rotation_euler", frame=f)

def expr_at(table, f):
    cur = table[0][1]
    for t_, e_ in table:
        if f >= t_: cur = e_
    return cur

def apply_expressions(c, blinks=()):
    for f in range(1, N + 1):
        for kind, g in c.F.items():
            vis = expr_at(c.expr_table, f) == kind
            if f == 1 or vis != (expr_at(c.expr_table, f - 1) == kind):
                set_visible(g, f, vis)
        bl = any(b_ <= f < b_ + 4 for b_ in blinks)
        for e_ in c.blink:
            e_.scale = (e_.scale[0], 0.012 if bl else 0.085, 1); e_.keyframe_insert("scale", frame=f)

def walk_legs(ph, amp=0.42):
    s = math.sin(ph)
    return ((amp * s, amp * s - 0.7 * max(0.0, math.sin(ph + 1.9))),
            (-amp * s, -amp * s - 0.7 * max(0.0, math.sin(ph + 1.9 + math.pi))))

# 2D props held in the character plane (child of torso, so they stay upright)
def prop_round(parent, name, r=0.42):
    g = empty(name, parent)
    shape(g, name + "_b", ellipse(0, 0, r, r, 40), flat("iron2d", (0.20, 0.20, 0.22)), 0.0, outline=0.035)
    for k in (0.72, 0.45, 0.2):
        stroke(g, f"{name}_r{k}", ellipse(0, 0, r * k, r * k, 32) + [ellipse(0, 0, r * k, r * k, 32)[0]], 0.022, 0.03, m=flat("iron2d_l", (0.36, 0.36, 0.38)))
    return g
def prop_square(parent, name, s=0.76):
    g = empty(name, parent)
    shape(g, name + "_b", rrect(0, 0, s, s, 0.04), flat("iron2d", (0.20, 0.20, 0.22)), 0.0, outline=0.035)
    for k in (-0.2, 0.0, 0.2):
        stroke(g, f"{name}_v{k}", [(k * s * 1.4, -s * 0.38), (k * s * 1.4, s * 0.38)], 0.022, 0.03, m=flat("iron2d_l", (0.36, 0.36, 0.38)))
        stroke(g, f"{name}_h{k}", [(-s * 0.38, k * s * 1.4), (s * 0.38, k * s * 1.4)], 0.022, 0.03, m=flat("iron2d_l", (0.36, 0.36, 0.38)))
    return g

# ---------------- JOE ----------------
BLUE = flat("joe_blue", (0.03, 0.22, 0.55)); HIVIS = flat("hivis", (0.95, 0.85, 0.05))
HAT = flat("hardhat", (0.98, 0.30, 0.02)); HAT_D = flat("hardhat_d", (0.75, 0.18, 0.01)); HAIR = flat("hair", (0.36, 0.22, 0.12))
def joe_extras(c):
    shape(c.torso, "joe_stripe", rrect(0, 0.32, 0.78, 0.12, 0.03), HIVIS, 0.17, outline=0.02)
    shape(c.torso, "joe_pocket", rrect(0.18, 0.58, 0.18, 0.15, 0.03), BLUE, 0.17, outline=0.022)
    shape(c.head, "joe_hair", ellipse(-0.36, 0.06, 0.16, 0.22, 24), HAIR, -0.05)
    shape(c.head, "joe_hat", ellipse(0, 0.2, 0.47, 0.40, 30, 0, math.pi), HAT, 0.08)
    stroke(c.head, "joe_hat_ridge", [(0, 0.2), (0, 0.58)], 0.035, 0.12)
    shape(c.head, "joe_brim", rrect(0.04, 0.2, 1.12, 0.12, 0.05), HAT_D, 0.13)
JOE = make_char("joe", (-0.85, 4.1, 0.0), dict(leg=(0.74, 0.36, 0.34), torso=(0.80, 0.82, BLUE), arm=(0.33, 0.66, 0.34, 0.32),
                head=(1.34, 0.5), extras=joe_extras, faces=["neutral", "happy", "smirk", "wink", "shock", "focus", "smug_closed"]))
JOE_SQ = prop_square(JOE.torso, "joe_sq"); JOE_SQ.location = (0, 0.42, 0.45)
JOE_RD = prop_round(JOE.torso, "joe_rd"); JOE_RD.location = (0, 0.42, 0.45)

# ---------------- GARY (budget manager) ----------------
SHIRT_W = flat("gary_shirt", (0.95, 0.95, 0.93)); VEST = flat("gary_vest", (0.08, 0.38, 0.14))
BOW = flat("bowtie", (0.85, 0.08, 0.10)); GHAIR = flat("gary_hair", (0.20, 0.12, 0.07))
CLIP = flat("clipboard", (0.55, 0.33, 0.15)); PAPER = flat("paper", (0.98, 0.98, 0.96)); LINE = flat("paperline", (0.6, 0.6, 0.62))
def gary_extras(c):
    shape(c.torso, "gary_vest", [(-0.40, 0.70), (-0.12, 0.84), (0, 0.55), (0.12, 0.84), (0.40, 0.70), (0.40, 0.18), (0.30, 0.05), (-0.30, 0.05), (-0.40, 0.18)],
          VEST, 0.15, outline=0.03)
    for k in range(3):
        disc(c.torso, f"gary_btn{k}", 0.0, 0.45 - k * 0.13, 0.03, 0.2, SHIRT_W)
    shape(c.torso, "gary_bowL", [(0, 0.86), (-0.13, 0.93), (-0.13, 0.79)], BOW, 0.22, outline=0.02)
    shape(c.torso, "gary_bowR", [(0, 0.86), (0.13, 0.93), (0.13, 0.79)], BOW, 0.22, outline=0.02)
    disc(c.torso, "gary_knot", 0, 0.86, 0.035, 0.25, BOW)
    shape(c.head, "gary_hair", [(-0.47, 0.12), (-0.40, 0.34), (-0.15, 0.48), (0.20, 0.47), (0.45, 0.30), (0.47, 0.12), (0.30, 0.30), (0.05, 0.32), (-0.10, 0.25), (-0.30, 0.28)],
          GHAIR, 0.05, outline=0.03)
    for s in (-1, 1):
        stroke(c.head, f"gary_glass{s}", ellipse(s * 0.15, -0.02, 0.12, 0.11, 24) + [ellipse(s * 0.15, -0.02, 0.12, 0.11, 24)[0]], 0.03, 0.2)
    stroke(c.head, "gary_bridge", [(-0.035, 0.0), (0.035, 0.0)], 0.03, 0.2)
GARY = make_char("gary", (1.0, 4.3, 0.0), dict(leg=(0.78, 0.38, 0.36), torso=(0.84, 0.90, SHIRT_W), arm=(0.36, 0.72, 0.35, 0.33),
                 head=(1.40, 0.48), extras=gary_extras, faces=["neutral", "angry", "shock", "worried", "grumpy", "smug_closed", "smirk"]))
GARY_CLIP = empty("gary_clip", GARY.torso, (-0.30, 0.38, 0.42))
shape(GARY_CLIP, "clip_b", rrect(0, 0, 0.34, 0.44, 0.03), CLIP, 0, outline=0.03)
shape(GARY_CLIP, "clip_p", rrect(0, -0.02, 0.27, 0.34, 0.01), PAPER, 0.02, outline=0)
for k in range(4):
    stroke(GARY_CLIP, f"clip_l{k}", [(-0.09, 0.08 - k * 0.07), (0.09, 0.08 - k * 0.07)], 0.015, 0.04, m=LINE)
shape(GARY_CLIP, "clip_c", rrect(0, 0.21, 0.12, 0.05, 0.01), flat("clipmetal", (0.7, 0.7, 0.72)), 0.05, outline=0.015)
GARY_BILL = empty("gary_bill", GARY.torso, (0.0, 0.62, 0.45))
bill_strip = empty("bill_strip", GARY_BILL)
shape(bill_strip, "bill_p", rrect(0, -0.5, 0.36, 1.0, 0.01), PAPER, 0, outline=0.02)
for k in range(12):
    stroke(bill_strip, f"bill_l{k}", [(-0.13, -0.08 - k * 0.075), (0.06 if k % 3 else 0.13, -0.08 - k * 0.075)], 0.012, 0.02, m=LINE)
txt_cu = bpy.data.curves.new("bill_total", 'FONT'); txt_cu.body = "$$$"; txt_cu.size = 0.09; txt_cu.align_x = 'CENTER'
bt = bpy.data.objects.new("bill_total", txt_cu); col.objects.link(bt); bt.parent = bill_strip; bt.location = (0, -0.98, 0.03)
bt.data.materials.append(RED_M)
shape(GARY_BILL, "bill_roll", ellipse(0, 0, 0.2, 0.06, 20), PAPER, 0.05, outline=0.02)
GARY_SQ = prop_square(GARY.torso, "gary_sq"); GARY_SQ.location = (0, 0.40, 0.46)

# steam puffs (Gary angry)
STEAM = flat("steam", (0.97, 0.97, 0.98)); puffs = []
for s in (-1, 1):
    pv = empty(f"puff{s}", GARY.head, (s * 0.52, 0.42, 0.2))
    for k, (dx_, dy_, r) in enumerate(((0, 0, 0.11), (0.1, 0.06, 0.09), (-0.08, 0.08, 0.08), (0.03, 0.13, 0.08))):
        shape(pv, f"puff{s}_{k}", ellipse(dx_ * s, dy_, r, r, 20), STEAM, 0.01 * k, outline=0.025)
    puffs.append(pv)

# ---------------- SAM (sewer worker) ----------------
ORANGE = flat("sam_vest", (0.98, 0.45, 0.05))
def sam_extras(c):
    for k in (-0.2, 0.2):
        stroke(c.torso, f"sam_ref{k}", [(k, 0.15), (k, 0.75)], 0.06, 0.17, m=flat("sam_refl", (0.9, 0.9, 0.9)))
    shape(c.head, "sam_beard", [(-0.36, -0.15), (-0.2, -0.38), (0, -0.46), (0.2, -0.38), (0.36, -0.15), (0.2, -0.28), (0, -0.30), (-0.2, -0.28)],
          flat("sam_beard", (0.45, 0.28, 0.15)), 0.04, outline=0.025)
SAM = make_char("sam", (H[0], H[1], -5.0), dict(leg=(0.74, 0.36, 0.34), torso=(0.82, 0.82, ORANGE), arm=(0.34, 0.66, 0.34, 0.32),
                head=(1.34, 0.48), extras=sam_extras, faces=["shock", "worried"], eye_y=0.02))
SAM_HAT = prop_square(SAM.head, "sam_hat", 0.78); SAM_HAT.location = (0, 0.50, 0.25); SAM_HAT.rotation_euler = (0, 0, 0.12)
DRIPS = []
for i, (dx_, dy_) in enumerate(((-0.45, 0.25), (0.48, 0.1), (0.3, 0.55))):
    d_ = empty(f"drip{i}", SAM.head, (dx_, dy_, 0.3))
    shape(d_, f"drip{i}s", [(0, 0.08), (0.04, -0.02), (0, -0.05), (-0.04, -0.02)], SWEAT, 0, outline=0.015)
    DRIPS.append(d_)

# ---------------- DIAGRAM SHAPES (in dg plane, x right / y up) ----------------
GREEN = flat("dg_green", (0.05, 0.6, 0.2)); REDA = flat("dg_red", (0.9, 0.12, 0.1)); IRON2 = flat("iron2d", (0.20, 0.20, 0.22))
def arrow(parent, name, p0, p1, w, m):
    g = empty(name, parent)
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0]); hl = 0.22
    a0 = (p0[0] + hl * 0.8 * math.cos(ang), p0[1] + hl * 0.8 * math.sin(ang)); a1 = (p1[0] - hl * 0.8 * math.cos(ang), p1[1] - hl * 0.8 * math.sin(ang))
    stroke(g, name + "_s", [a0, a1], w, 0.1, m=m)
    for P_, sgn in ((p1, 1), (p0, -1)):
        tip = P_; bx, by = P_[0] - sgn * hl * math.cos(ang), P_[1] - sgn * hl * math.sin(ang)
        nx, ny = -math.sin(ang) * hl * 0.55, math.cos(ang) * hl * 0.55
        shape(g, f"{name}_h{sgn}", [tip, (bx + nx, by + ny), (bx - nx, by - ny)], m, 0.1, outline=0)
    return g
def label(parent, name, text, loc, size, m):
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = text; cu.size = size; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'
    if FONT_PATH: cu.font = bpy.data.fonts.load(FONT_PATH, check_existing=True)
    o = bpy.data.objects.new(name, cu); col.objects.link(o); o.parent = parent; o.location = (loc[0], loc[1], 0.2)
    o.data.materials.append(m); return o

DG_SQ = empty("dg_square_set", dg)
HS = 1.8                                              # square hole side
shape(DG_SQ, "dg_sq_hole", rrect(0, 0, HS, HS, 0.02), HOLE_M, 0.0, outline=0.05)
DG_SQ_COVER = empty("dg_sq_cover", DG_SQ, (0, 0, 0.05))
shape(DG_SQ_COVER, "dg_sq_cov", rrect(0, 0, 2.05, 2.05, 0.05), IRON2, 0, outline=0.05)
DG_SIDE = arrow(DG_SQ, "dg_side", (-HS / 2, -HS / 2 - 0.45), (HS / 2, -HS / 2 - 0.45), 0.06, GREEN)
DG_DIAG = arrow(DG_SQ, "dg_diag", (-HS / 2 + 0.05, -HS / 2 + 0.05), (HS / 2 - 0.05, HS / 2 - 0.05), 0.07, REDA)
DG_L_SIDE = label(DG_SQ, "dg_l_side", "SIDE", (0, -HS / 2 - 0.85), 0.32, GREEN)
DG_L_DIAG = label(DG_SQ, "dg_l_diag", "1.4x LONGER", (0, HS / 2 + 0.55), 0.32, REDA)
DG_RD = empty("dg_round_set", dg)
shape(DG_RD, "dg_rd_hole", ellipse(0, 0, 0.9, 0.9, 48), HOLE_M, 0.0, outline=0.05)
DG_RD_COVER = empty("dg_rd_cover", DG_RD, (0, 0, 0.05))
shape(DG_RD_COVER, "dg_rd_cov", ellipse(0, 0, 1.03, 1.03, 48), IRON2, 0, outline=0.05)
DG_DIAM = empty("dg_diam_pivot", DG_RD, (0, 0, 0.2))
arrow(DG_DIAM, "dg_diam", (-1.03, 0), (1.03, 0), 0.07, GREEN)
DG_L_SAME = label(DG_RD, "dg_l_same", "SAME WIDTH", (0, 1.55), 0.34, GREEN)
DG_L_NEVER = label(DG_RD, "dg_l_never", "CAN'T FALL IN", (0, -1.55), 0.34, GREEN)

# V2: reaction FX rigs and a talking mouth for the character who speaks quoted lines
for ch_ in (JOE, GARY, SAM):
    add_reaction_fx(ch_)
add_talk_mouth(GARY)

# ---------------- utilities ----------------
def ease(u):
    u = max(0.0, min(1.0, u)); return u * u * (3 - 2 * u)
def lerp(a, b, u): return a + (b - a) * u
def lerp3(a, b, u): return tuple(a[i] + (b[i] - a[i]) * u for i in range(len(a)))
def pop_scale(f, a, dur=5, over=1.25):
    if f < a: return 0.0
    u = (f - a) / dur
    if u >= 1: return 1.0
    return u * over / 0.7 if u < 0.7 else over + (1 - over) * (u - 0.7) / 0.3
def vis_track(obj, ranges):
    """ranges: list of (start, end) frames where obj is visible"""
    prev = None
    for f in range(1, N + 1):
        v = any(a <= f <= b for a, b in ranges)
        if v != prev:
            set_visible(obj, f, v); prev = v
def key_loc(o, f, loc): o.location = loc; o.keyframe_insert("location", frame=f)
def key_rot(o, f, rot): o.rotation_euler = rot; o.keyframe_insert("rotation_euler", frame=f)
def key_scl(o, f, s): o.scale = s; o.keyframe_insert("scale", frame=f)

# ---------------- shots ----------------
DX = D[0]
SHOTS = [  # (start, end, cam_from, cam_to, look_from, look_to, lens)
    (1, 75,      (-2.0, -1.0, 1.4), (-1.6, -0.2, 1.4), (0.6, 4.3, 1.2), (0.8, 4.3, 1.3), 26),
    (76, 170,    (2.9, 1.8, 1.25), (2.6, 2.2, 1.3), (0.6, 4.2, 1.1), (0.7, 4.2, 1.25), 30),
    (171, 224,   (1.6, 2.4, 1.9), (1.5, 2.65, 1.95), (1.0, 4.3, 1.88), (1.0, 4.3, 1.93), 34),
    (225, 278,   (-1.9, 1.5, 1.2), (-1.7, 1.9, 1.25), (-0.85, 4.1, 1.5), (-0.85, 4.1, 1.55), 32),
    (279, 357,   (-2.4, 1.0, 1.1), (-2.0, 1.6, 1.1), (-0.45, 4.0, 1.05), (-0.4, 4.0, 1.05), 28),
    (358, 410,   (1.4, 1.9, 1.9), (1.3, 2.1, 1.85), (-0.15, 4.0, 0.45), (-0.15, 4.0, 0.45), 28),
    (411, 565,   (DX, -7.7, 1.3), (DX, -7.3, 1.3), (DX, 0.3, 1.3), (DX, 0.3, 1.3), 45),
    (566, 690,   (0.3, -0.5, 1.2), (0.25, 0.3, 1.2), (0.05, 4.2, 1.15), (0.05, 4.2, 1.2), 28),
    (691, 813,   (0.6, 0.5, 0.75), (0.5, 0.9, 0.8), (0.0, 4.0, 0.72), (0.0, 4.0, 0.8), 28),
    (814, 858,   (-1.9, 1.4, 1.3), (-1.7, 1.8, 1.3), (-0.85, 4.1, 1.5), (-0.85, 4.1, 1.55), 32),
    (859, 970,   (DX, -7.7, 1.3), (DX, -7.3, 1.3), (DX, 0.3, 1.3), (DX, 0.3, 1.3), 45),
    (971, 1016,  (1.3, 2.0, 1.6), (1.2, 2.2, 1.55), (-0.15, 4.0, 0.5), (-0.15, 4.0, 0.5), 28),
    (1017, 1110, None, None, None, None, 26),                       # tracking shot (rolling)
    (1111, 1188, (1.8, 2.2, 1.6), (1.7, 2.5, 1.65), (1.0, 4.3, 1.6), (1.0, 4.3, 1.75), 30),
    (1189, 1280, (2.2, 1.6, 1.4), (2.0, 2.0, 1.45), (1.0, 4.3, 1.45), (1.0, 4.3, 1.5), 30),
    (1281, N,    (O[0] + 0.45, 0.0, 1.2), (O[0] + 0.45, 0.3, 1.15), (O[0] + 0.7, 3.1, 0.95), (O[0] + 0.7, 3.1, 0.95), 28),
]
ROLL = (1017, 1105)
def roll_x(f): return lerp(0.6, 3.6, ease((f - ROLL[0]) / (ROLL[1] - ROLL[0])) * 0.3 + 0.7 * max(0, min(1, (f - ROLL[0]) / (ROLL[1] - ROLL[0]))))
SHAKES = [(360, 0.06), (171, 0.03), (631, 0.05), (674, 0.05), (760, 0.03), (1005, 0.02)]
PUNCH = [(213, 1.22), (360, 1.18), (631, 1.12), (674, 1.18), (838, 1.15), (1068, 1.2), (1291, 1.12)]   # zoom punch-ins on beats
WHIP_IN = {225, 411, 566, 814, 859, 971, 1111, 1281}                                                    # cuts that use a whip pan
SHOT_FSTOP = {0: 8.0, 6: 64, 10: 64, 12: 5.6, 2: 2.8, 13: 2.8}                                         # default 4 = gently soft background
cam_d.dof.use_dof = False; cam_d.dof.focus_object = tgt     # DOF off: it would blur the captions, which sit close to the lens
def norm(v): l_ = math.sqrt(sum(x * x for x in v)) or 1.0; return tuple(x / l_ for x in v)
HOLDS = {}; LENS_F = {}; FOCUS_D = {}
for f in range(1, N + 1):
    t = f / FPS
    for si, (a, b, c0, c1, l0, l1, lens) in enumerate(SHOTS):
        if a <= f <= b:
            if c0 is None:
                x = roll_x(f); cp = (x - 0.6, 0.0, 1.15); tp = (x - 0.3, 3.0, 0.85)
            else:
                u = ease((f - a) / max(1, b - a)); cp = lerp3(c0, c1, u); tp = lerp3(l0, l1, u)
            d_ = norm(tuple(tp[i] - cp[i] for i in range(3))); right = norm((d_[1], -d_[0], 0.0))
            dist = math.sqrt(sum((tp[i] - cp[i]) ** 2 for i in range(3)))
            off = 0.0
            if b + 1 in WHIP_IN and f > b - 4: off += 0.9 * dist * ((f - (b - 4)) / 4) ** 2        # whip out
            if a in WHIP_IN and f < a + 4: off -= 0.55 * dist * (1 - ease_out_back((f - a) / 4, 1.0))   # whip in, settle
            tp = tuple(tp[i] + right[i] * off for i in range(3))
            lens_f = lens
            for p_, m_ in PUNCH:
                if a <= p_ <= f <= b: lens_f = lens * (1 + (m_ - 1) * ease_out_back((f - p_) / 5, 1.8))
            fstop = SHOT_FSTOP.get(si, 4.0)
            cur_b = b
    sh = sum(amp * max(0, 1 - (f - t0) / 14) for t0, amp in SHAKES if t0 <= f < t0 + 14)
    hand = 0.010
    cam.location = (cp[0] + sh * math.sin(f * 3.1) + hand * noise1(t * 0.9, 1.0), cp[1], cp[2] + sh * math.cos(f * 2.3) + hand * noise1(t * 0.8, 2.0))
    tgt.location = (tp[0] + 0.02 * noise1(t * 0.7, 3.0), tp[1], tp[2] + 0.015 * noise1(t * 0.6, 4.0))
    cam_d.lens = lens_f; cam_d.dof.aperture_fstop = fstop
    LENS_F[f] = lens_f; FOCUS_D[f] = math.sqrt(sum((tgt.location[i] - cam.location[i]) ** 2 for i in range(3)))
    cam.keyframe_insert("location", frame=f); tgt.keyframe_insert("location", frame=f)
    cam_d.keyframe_insert("lens", frame=f); cam_d.dof.keyframe_insert("aperture_fstop", frame=f)
    if f == cur_b:
        HOLDS[f] = (tuple(cam.location), tuple(tgt.location), lens_f, fstop)
for f, (cl, tl, ln, fs_) in HOLDS.items():                                   # hold until the cut (clean motion blur)
    if f >= N: continue
    cam.location = cl; tgt.location = tl; cam_d.lens = ln; cam_d.dof.aperture_fstop = fs_
    cam.keyframe_insert("location", frame=f + 0.98); tgt.keyframe_insert("location", frame=f + 0.98)
    cam_d.keyframe_insert("lens", frame=f + 0.98); cam_d.dof.keyframe_insert("aperture_fstop", frame=f + 0.98)
CUTS = [s[0] for s in SHOTS[1:]]

# ---------------- set dressing visibility ----------------
vis_track(HOLE_R, [(1, 224), (860, N)])
vis_track(HOLE_S, [(225, 859)])
vis_track(CV_ROUND_IN_HOLE, [(1, 224), (1005, N)])
vis_track(DG_SQ, [(411, 565)]); vis_track(DG_RD, [(859, 970)])
vis_track(JOE_SQ, [(225, 357), (600, 627), (643, 670)])
vis_track(JOE_RD, [(814, 990)])
vis_track(GARY_CLIP, [(1, 1110)]); vis_track(GARY_BILL, [(1111, 1188)]); vis_track(GARY_SQ, [(1230, 1280)])
CV_ROUND_IN_HOLE.location = (H[0], H[1], 0.02)

# ---------------- 3D cover motion ----------------
def drop_square(o, t0):
    for f in range(1, N + 1):
        if f < t0 or f > t0 + 22:
            key_loc(o, f, (H[0], H[1], -6)); key_rot(o, f, (0, 0, 0)); continue
        t = (f - t0) / FPS
        z = 0.95 - 0.5 * 9.8 * 1.4 * t * t
        key_loc(o, f, (H[0] + 0.02 * math.sin(f), H[1], z))
        key_rot(o, f, (math.radians(80) + t * 1.2, 0.0, math.radians(45) + t * 2.0))
for o, t0 in zip(CV_DROP, (356, 628, 671)):
    drop_square(o, t0)
for f in range(1, N + 1):                                            # round one: dropped flat into its seat
    o = CV_DROP_ROUND
    if 990 <= f <= 1005:
        u = (f - 990) / 15.0
        key_loc(o, f, (H[0] - 0.1 * (1 - u), H[1] - 0.15 * (1 - u), lerp(0.95, 0.02, u * u)))
        key_rot(o, f, (math.radians(90) * (1 - ease(u)), 0, 0))
    else:
        key_loc(o, f, (H[0], H[1], -6)); key_rot(o, f, (0, 0, 0))
for f in range(1, N + 1):                                            # rolling one
    o = CV_ROLL
    if ROLL[0] <= f <= 1110:
        x = roll_x(f)
        key_loc(o, f, (x, 3.0, COVER_R + 0.005 * abs(math.sin(f * 0.9))))
        key_rot(o, f, (math.pi / 2, (x - 0.6) / COVER_R, 0))
    else:
        key_loc(o, f, (0, 0, -6)); key_rot(o, f, (math.pi / 2, 0, 0))

# ---------------- character locations ----------------
JP = (-0.85, 4.1, 0.0); GP = (1.0, 4.3, 0.0); OFF = (-40, 40, 0)
GARY_OFFICE = (TABLE_C[0] + 0.8, TABLE_C[1] + 0.3, 0.0)
for f in range(1, N + 1):
    # Joe
    if f < 225: jl = OFF
    elif 279 <= f <= 357: jl = (-0.6, 4.0, 0)
    elif ROLL[0] <= f <= 1110: jl = (roll_x(f) - 0.95, 3.05, 0.03 * abs(math.sin(f * 0.42)))
    elif f > 1110: jl = (-1.4, 4.4, 0)
    else: jl = JP
    key_loc(JOE.root, f, jl)
    # Gary
    if ROLL[0] <= f <= 1110: gl = OFF
    elif f >= 1281: gl = GARY_OFFICE
    else: gl = GP
    key_loc(GARY.root, f, gl)
    # Sam pops out of the hole in shot 9
    if 746 <= f <= 813:
        u = (f - 746) / 12.0
        z = lerp(-2.7, -1.12, min(1, u)) + (0.12 * math.sin(min(1, u) * math.pi) if u < 1.6 else 0) + 0.02 * math.sin(f * 0.3)
    else:
        z = -6
    key_loc(SAM.root, f, (H[0], H[1], z))

# ---------------- character poses ----------------
GARY_RED = (0.92, 0.28, 0.25)
gsk = GARY.skin.node_tree.nodes["Emission"].inputs[0]
for f_, col_ in ((170, (0.98, 0.98, 0.97)), (180, GARY_RED), (224, GARY_RED), (225, (0.98, 0.98, 0.97))):
    gsk.default_value = (*col_, 1); gsk.keyframe_insert("default_value", frame=f_)

AMP = load_amplitude(os.path.join(OUT_DIR, "voice.wav"), N, FPS)
GARY_TALK = [(122, 153), (172, 224), (1189, 1199), (1230, 1282)]
JOE.reacts = [(248, "proud"), (358, "hop"), (631, "flinch"), (674, "hop"), (838, "proud"), (1300, "proud")]
GARY.reacts = [(171, "shiver"), (631, "flinch"), (674, "hop"), (1140, "shiver"), (1230, "proud")]
SAM.reacts = [(785, "hop")]
CLIP_HAND = ('ik', (-0.47, 0.30), -1)
for f in range(1, N + 1):
    t = f / FPS
    # ----- GARY -----
    GARY.amp_now = AMP[f] if any(a_ <= f <= b_ for a_, b_ in GARY_TALK) else 0.0
    aL, aR, tilt, body = CLIP_HAND, None, 0.0, (0, 0)
    if 120 <= f <= 168:                                          # taps clipboard with his pen hand
        aR = ('ik', (-0.20, 0.42 + 0.05 * abs(math.sin((f - 120) * 0.35))), 1)
    elif 171 <= f <= 224:                                        # outburst: pointing, shaking
        aR = ('ang', lerp(0.25, 2.0, pease(f, 171, 6)) + 0.15 * math.sin(f * 1.6), 0.25)
        body = (0.012 * math.sin(f * 2.9), 0)
    elif 566 <= f <= 600:                                        # "here, take another one"
        u = pease(f, 566, 8); aR = ('ang', lerp(0.25, -1.3, u), lerp(-0.1, -0.2, u))
    elif 600 < f <= 690 or 691 <= f <= 813:
        aR = ('ang', -0.35, 0.6) if f < 631 or f > 640 else ('ang', 2.3, 0.6)
    elif 1111 <= f <= 1188:                                      # holding the bill
        aL = ('ik', (-0.20, 0.60), -1); aR = ('ik', (0.20, 0.60), 1)
        tilt = -0.18 * pease(f, 1154, 8)
    elif 1189 <= f <= 1229:                                      # arms crossed
        u = pease(f, 1189, 7)
        aL = ('ik', (lerp(-0.47, 0.22, u), lerp(0.30, 0.48, u)), 1); aR = ('ik', (lerp(0.36, -0.22, u), lerp(0.1, 0.42, u)), -1)
    elif 1230 <= f <= 1280:                                      # hugging the square cover
        aL = ('ik', (-0.40, 0.40), -1); aR = ('ik', (0.40, 0.40), 1); tilt = 0.08 * math.sin(f * 0.25)
    elif f >= 1281:                                              # office: hands on hips
        aL = ('ik', (-0.44, 0.12), 1); aR = ('ik', (0.44, 0.12), -1)
    pose_char(GARY, f, aL, aR, head_tilt=tilt, body=body)
    # ----- JOE -----
    aL = aR = None; legs = ((-0.06, 0.02), (0.06, -0.02)); tilt = 0.0; body = (0, 0)
    holding_sq = any(a <= f <= b for a, b in ((225, 357), (600, 627), (643, 670)))
    if holding_sq:
        lift = 0.04 * math.sin(t * 3)
        sqx = 1.0
        if 316 <= f <= 357: sqx = lerp(1.0, 0.55, ease((f - 316) / 30))
        if 225 <= f <= 240: lift += 0.12 * math.sin(math.pi * (f - 225) / 15)      # turning it on edge
        JOE_SQ.scale = (sqx, 1, 1); JOE_SQ.keyframe_insert("scale", frame=f)
        JOE_SQ.location = (0, 0.42 + lift, 0.45); JOE_SQ.keyframe_insert("location", frame=f)
        aL = ('ik', (-0.38 * sqx - 0.02, 0.42 + lift), -1); aR = ('ik', (0.38 * sqx + 0.02, 0.42 + lift), 1)
    elif 358 <= f <= 410 or 628 <= f <= 642 or 671 <= f <= 690:   # empty hands after the drop
        aL = ('ik', (-0.36, 0.42), -1); aR = ('ik', (0.36, 0.42), 1); body = (0.0, -0.02)
    elif 814 <= f <= 990:                                          # proudly holding the round one
        hy = 0.55 if f < 971 else 0.42
        JOE_RD.location = (0, hy, 0.45); JOE_RD.keyframe_insert("location", frame=f)
        aL = ('ik', (-0.43, hy), -1); aR = ('ik', (0.43, hy), 1)
    elif ROLL[0] <= f <= 1110:                                      # walking, hand on the rolling cover
        ph = (f - ROLL[0]) * 0.42; legs = walk_legs(ph)
        aR = ('ik', (0.62, 0.15), 1); aL = ('ang', -0.35 * math.sin(ph), 0.2)
    elif 991 <= f <= 1016:                                          # dusting hands off
        aL = ('ik', (-0.10, 0.25 + 0.04 * math.sin(f)), -1); aR = ('ik', (0.10, 0.25 - 0.04 * math.sin(f)), 1)
    if 230 <= f <= 246:                                            # quick salute-like lift of the cover
        pass
    if not holding_sq:
        JOE_SQ.scale = (1, 1, 1); JOE_SQ.keyframe_insert("scale", frame=f)
    pose_char(JOE, f, aL, aR, legL=legs[0], legR=legs[1], head_tilt=tilt, body=body)
    # ----- SAM -----
    pose_char(SAM, f, ('ik', (-0.58, 0.47), -1), ('ik', (0.58, 0.47), 1), head_tilt=0.05 * math.sin(f * 0.2))
    for i, d_ in enumerate(DRIPS):
        ph = ((f - 746) / 20.0 + i * 0.33) % 1.0
        d_.location = (d_.location[0], [0.25, 0.1, 0.55][i] - 0.5 * ph, 0.3); d_.keyframe_insert("location", frame=f)
    # Gary's steam
    for k_, pv in enumerate(puffs):
        if 171 <= f <= 224:
            ph = ((f - 171) / 16.0 + k_ * 0.5) % 1.0; s_ = math.sin(math.pi * ph) * 1.2
            pv.scale = (s_, s_, 1); pv.location = (pv.location[0], 0.42 + 0.35 * ph, 0.2)
        else:
            pv.scale = (0, 0, 1)
        pv.keyframe_insert("scale", frame=f); pv.keyframe_insert("location", frame=f)
    # Gary's bill unrolls
    if 1111 <= f <= 1188:
        u = ease((f - 1113) / 27); bill_strip.scale = (1, max(0.03, u * 1.9), 1)
    else:
        bill_strip.scale = (1, 0.03, 1)
    bill_strip.keyframe_insert("scale", frame=f)

JOE.expr_table = [(1, "neutral"), (248, "happy"), (262, "focus"), (345, "shock"), (411, "neutral"), (566, "neutral"),
                  (631, "shock"), (643, "focus"), (674, "shock"), (691, "shock"), (814, "smirk"), (971, "smug_closed"),
                  (1017, "happy"), (1111, "neutral"), (1300, "wink")]
GARY.expr_table = [(1, "neutral"), (97, "grumpy"), (171, "angry"), (225, "grumpy"), (566, "grumpy"), (631, "shock"),
                   (645, "grumpy"), (674, "shock"), (700, "shock"), (1111, "neutral"), (1140, "worried"),
                   (1189, "grumpy"), (1230, "smug_closed"), (1281, "smirk")]
SAM.expr_table = [(1, "worried"), (785, "shock")]
apply_expressions(JOE, blinks=(60, 300, 520, 900, 1150))
apply_expressions(GARY, blinks=(40, 140, 260, 600, 1120))
apply_expressions(SAM)

# ---------------- diagram animation ----------------
for f in range(1, N + 1):
    # square
    if f < 425: s_cov = (1, 1, 1); r_cov = 0.0; y_cov = 0.0
    elif f < 513:
        u = ease((f - 425) / 10); s_cov = (1 - u, 1 - u, 1); r_cov = 0.0; y_cov = 2.0 * u
    elif f < 548:
        u = ease((f - 513) / 10); s_cov = (1, lerp(1, 0.12, u), 1); r_cov = math.radians(45) * u; y_cov = lerp(1.5, 0, u)
    else:
        u = ease((f - 548) / 12); s_cov = (1 - u * 0.9, 0.12 * (1 - u), 1); r_cov = math.radians(45); y_cov = -0.3 * u
    DG_SQ_COVER.scale = s_cov; DG_SQ_COVER.rotation_euler = (0, 0, r_cov); DG_SQ_COVER.location = (0, y_cov, 0.35 if f >= 513 else 0.05)
    for p_ in ("scale", "rotation_euler", "location"): DG_SQ_COVER.keyframe_insert(p_, frame=f)
    for obj, a in ((DG_DIAG, 453), (DG_L_DIAG, 456), (DG_SIDE, 497), (DG_L_SIDE, 500)):
        s_ = pop_scale(f, a); obj.scale = (s_, s_, 1); obj.keyframe_insert("scale", frame=f)
    # round
    if f < 870: rs = (1, 1, 1)
    elif f < 930: u = ease((f - 870) / 8); rs = (1 - u, 1 - u, 1)
    else: u = ease((f - 930) / 8); rs = (1, lerp(0.001, 0.12, u), 1)
    DG_RD_COVER.scale = rs
    DG_RD_COVER.location = (0, 0, 0.35 if f >= 930 else 0.05); DG_RD_COVER.keyframe_insert("location", frame=f)
    DG_RD_COVER.rotation_euler = (0, 0, (f - 930) * 0.07 if f >= 930 else 0)
    DG_RD_COVER.keyframe_insert("scale", frame=f); DG_RD_COVER.keyframe_insert("rotation_euler", frame=f)
    ds = pop_scale(f, 872); DG_DIAM.scale = (ds, ds, 1); DG_DIAM.rotation_euler = (0, 0, (f - 872) * 0.07)
    DG_DIAM.keyframe_insert("scale", frame=f); DG_DIAM.keyframe_insert("rotation_euler", frame=f)
    for obj, a in ((DG_L_SAME, 885), (DG_L_NEVER, 945)):
        s_ = pop_scale(f, a); obj.scale = (s_, s_, 1); obj.keyframe_insert("scale", frame=f)

# ---------------- captions (word by word, synced to the voice) ----------------
HIGHLIGHT = {"square", "clang", "corner", "side", "three", "hat", "circle", "same", "width", "never", "hundred",
             "pounds", "roll", "bill", "fine", "coffee", "table", "budget", "circles"}
def clean(w): return w.replace('"', '').replace('“', '').replace('”', '')
groups = []; i = 0
while i < len(WORDS):
    t0, w = WORDS[i]; txt = clean(w); j = i + 1
    if j < len(WORDS) and len(re.sub(r"\W", "", txt)) <= 3 and not txt.endswith((".", ",", "?")) and len(txt + WORDS[j][1]) <= 11 \
            and re.sub(r"\W", "", WORDS[j][1]).lower() not in HIGHLIGHT:
        txt = txt + " " + clean(WORDS[j][1]); j += 1
    groups.append([t0, txt]); i = j
CAPS = []
for k, (t0, txt) in enumerate(groups):
    a = int(t0 * FPS) + 1
    b = (int(groups[k + 1][0] * FPS)) if k + 1 < len(groups) else a + 25
    b = max(b, a + 5); b = min(b, a + 40)
    key = re.sub(r"[^a-z]", "", txt.split()[-1].lower())
    if key == "clang": CAPS.append((txt.upper().replace(".", "!"), a, b, (1.0, 0.55, 0.1), 1.7))
    elif key in HIGHLIGHT: CAPS.append((txt.upper(), a, b, (1.0, 0.85, 0.1), 1.3))
    else: CAPS.append((txt, a, b))
CAP_D = 1.0
font = bpy.data.fonts.load(FONT_PATH, check_existing=True) if FONT_PATH else None
cap_root = empty("captions", cam, (0, -0.12, -CAP_D))
for f in range(1, N + 1):
    in_dg = 411 <= f <= 565 or 859 <= f <= 970
    k_ = LENS_F[f] / 28.0
    d_ = 1.0
    cap_root.location = (0, (-0.55 if in_dg else -0.12) * k_ * d_, -CAP_D * k_ * d_)
    cap_root.scale = (d_, d_, d_)
    cap_root.keyframe_insert("location", frame=f); cap_root.keyframe_insert("scale", frame=f)
for i, c in enumerate(CAPS):
    txt, a, b = c[0], c[1], c[2]
    rgb = c[3] if len(c) > 3 else (1, 1, 1); size = 0.085 * (c[4] if len(c) > 4 else 1.0)
    holder = empty(f"cap{i}", cap_root)
    for layer, (m, off, z) in enumerate(((INK, size * 0.11, -0.002), (flat(f"capc{rgb}", rgb), 0.0, 0.0))):
        cu = bpy.data.curves.new(f"cap{i}_{layer}", 'FONT'); cu.body = txt
        if font: cu.font = font
        cu.size = size; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.offset = off
        o = bpy.data.objects.new(f"cap{i}_{layer}", cu); col.objects.link(o)
        o.parent = holder; o.location = (0, 0, z); o.data.materials.append(m)
    if "CLANG" in txt:                                            # comic burst behind the impact word
        burst = empty(f"cap{i}_burst", holder, (0, 0, -0.006))
        pts = [((0.22 if k % 2 == 0 else 0.16) * math.cos(2 * math.pi * k / 18) * (1.0 + 0.12 * ((k * 7) % 3)),
                (0.12 if k % 2 == 0 else 0.08) * math.sin(2 * math.pi * k / 18) * (1.0 + 0.12 * ((k * 5) % 3))) for k in range(18)]
        shape(burst, f"cap{i}_bst", pts, flat("burst_fill", (1.0, 0.82, 0.12)), 0, outline=0.012)
        burst2 = empty(f"cap{i}_burst2", holder, (0, 0, -0.008))
        shape(burst2, f"cap{i}_bst2", [(x * 1.18, y * 1.25) for x, y in pts], flat("burst_back", (0.92, 0.25, 0.08)), 0, outline=0.012)
    rnd_ = random.Random(i * 31)
    base_rot = rnd_.uniform(-0.06, 0.06) if len(c) > 3 else rnd_.uniform(-0.025, 0.025)
    holder.scale = (0, 0, 0); holder.keyframe_insert("scale", frame=1)
    for f in range(max(2, a - 1), min(N, b + 1) + 1):
        if f < a or f > b:
            s_ = 0.0; r_ = base_rot
        else:
            s_ = ease_out_back((f - a) / 5, 2.2)
            r_ = base_rot + (0.10 * math.sin((f - a) * 2.2) * (1 - (f - a) / 9) if len(c) > 3 and f - a < 9 else 0.0)
        holder.scale = (s_, s_, s_); holder.keyframe_insert("scale", frame=f)
        holder.rotation_euler = (0, 0, r_); holder.keyframe_insert("rotation_euler", frame=f)


# ---------------- V2: dust, reaction FX, lip flap ----------------
for fr in (360, 631, 674):
    dust_burst(fr, (H[0], H[1], 0.0), n=10, radius=0.85, size=1.0, life=22, rise=0.5)
dust_burst(750, (H[0], H[1], 0.0), n=6, radius=0.6, size=0.7)
dust_burst(1005, (H[0], H[1], 0.0), n=6, radius=0.75, size=0.45, life=16, rise=0.12)
for fr in range(ROLL[0] + 6, 1106, 9):
    dust_burst(fr, (roll_x(fr), 3.0, 0.0), n=2, radius=0.25, size=0.35, life=14, rise=0.15)
bake_dust()
bake_reaction_fx(JOE, [358, 674]); bake_reaction_fx(GARY, [631, 674, 1140]); bake_reaction_fx(SAM, [785])
bake_talk(GARY, GARY_TALK, AMP)

# hold keys so motion blur never smears an object across a teleport (off-set -> on-set)
def fcurves_of(idb):
    ad = idb.animation_data
    if not ad or not ad.action: return []
    act = ad.action
    if hasattr(act, "fcurves"): return list(act.fcurves)
    out_ = []
    for layer in act.layers:
        for strip in layer.strips:
            cb = strip.channelbag(ad.action_slot)
            if cb: out_ += list(cb.fcurves)
    return out_
def add_teleport_holds(objs, thr=0.6):
    for o in objs:
        for fc in fcurves_of(o):
            if fc.data_path != "location": continue
            pts = sorted((kp.co[0], kp.co[1]) for kp in fc.keyframe_points)
            for (f0, v0), (f1, v1) in zip(pts, pts[1:]):
                if f1 - f0 >= 0.99 and abs(v1 - v0) > thr:
                    fc.keyframe_points.insert(f0 + 0.98, v0, options={'FAST'})
            fc.update()
add_teleport_holds([JOE.root, GARY.root, SAM.root, CV_ROLL, CV_DROP_ROUND] + CV_DROP)

# film look: freestyle outlines on the 3D set only, bloom, mist, vignette, motion blur
NOLINE = []
for root_ in (JOE.root, GARY.root, SAM.root, cap_root, dg):
    NOLINE += descendants(root_)
for p_ in PUFF_POOL: NOLINE += descendants(p_)
NOLINE += [o for o in bpy.data.objects if o.name.startswith(("dg_", "cloud", "Sphere")) and o.type == 'MESH' and o.location.z > 30]
NOLINE.append(bpy.data.objects["dg_back"])
setup_look(NOLINE)
sc.render.motion_blur_position = 'START'

# ---------------- SOUND: action SFX + music bed ----------------

SR = 44100
_rng = np.random.default_rng(11)

def _t(sec): return np.arange(int(SR * sec)) / SR
def _env(n, a=0.005, d=0.1):
    t = np.arange(n) / SR; return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / d)
def _fade(x, a=0.01, r=0.05):
    n = len(x); t = np.arange(n) / SR
    return x * np.minimum(1, t / a) * np.minimum(1, (t[-1] - t) / r)
def _lp(x, k):
    """one-pole low-pass; k may be a scalar or an array (sweeping filter)"""
    k = np.broadcast_to(np.asarray(k, dtype=float), x.shape)
    y = np.empty_like(x); acc = 0.0
    for i in range(len(x)):
        acc += k[i] * (x[i] - acc); y[i] = acc
    return y
def _noise(sec): return _rng.standard_normal(int(SR * sec))
def _sweep(f0, f1, sec, shape=1.0):
    t = _t(sec); f = f0 + (f1 - f0) * (t / t[-1]) ** shape
    return np.sin(2 * np.pi * np.cumsum(f) / SR)

# each generator returns a mono float array, peak about 1
def whoosh(sec=0.45):        # camera cut, fast move across frame
    n = int(SR * sec); k = 0.03 + 0.25 * np.sin(np.linspace(0, np.pi, n)) ** 2
    return _fade(_lp(_noise(sec), k) * np.sin(np.linspace(0, np.pi, n)) ** 2 * 3, 0.02, 0.1)
def swish(sec=0.18):          # arm swing, head turn, quick gesture
    n = int(SR * sec); k = np.linspace(0.08, 0.5, n)
    return _fade(_lp(_noise(sec), k) * np.sin(np.linspace(0, np.pi, n)) * 2.5, 0.01, 0.04)
def pop(sec=0.09):            # expression change, prop appears, caption pop
    t = _t(sec); return np.sin(2 * np.pi * (500 + 1400 * t / sec) * t) * _env(len(t), 0.001, 0.025)
def tick(sec=0.05):           # soft caption tick
    t = _t(sec); return np.sin(2 * np.pi * 1800 * t) * _env(len(t), 0.0005, 0.01)
def boing(sec=0.6):           # jump, spring, bounce
    t = _t(sec); f = 180 + 90 * np.sin(2 * np.pi * 9 * t) * np.exp(-t * 4) + 60 * t
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(len(t), 0.003, 0.22)
def thud(sec=0.45):           # body hits ground, heavy landing
    t = _t(sec); body = np.sin(2 * np.pi * (60 + 50 * np.exp(-t / 0.04)) * t) * _env(len(t), 0.002, 0.13)
    return body + _lp(_noise(sec), 0.06) * _env(len(t), 0.001, 0.03) * 4
def bonk(sec=0.35):           # something hits a head
    t = _t(sec); f = 380 * np.exp(-t / 0.12) + 170
    ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(ph) + 0.45 * np.sin(2.7 * ph)) * _env(len(t), 0.001, 0.1)
def step(sec=0.09):           # one footstep (call on every foot plant)
    return _lp(_noise(sec), 0.09) * _env(int(SR * sec), 0.002, 0.018) * 4
def slide_up(sec=0.5):        # slip, rising surprise
    return _fade(_sweep(450, 1900, sec, 1.5), 0.02, 0.05)
def slide_down(sec=0.6):      # falling, deflating
    return _fade(_sweep(1700, 300, sec, 0.8), 0.02, 0.08)
def steam(sec=1.1):           # angry kettle whistle
    t = _t(sec); f = 1100 + 120 * np.sin(2 * np.pi * 7 * t)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.6 * _lp(_noise(sec), 0.3)
    return _fade(s, 0.05, 0.2) * 0.8
def rumble(sec=0.6):          # anger build, impact low end
    t = _t(sec); return np.sin(2 * np.pi * 52 * t) * _env(len(t), 0.01, 0.25) + _lp(_noise(sec), 0.01) * 2 * _env(len(t), 0.01, 0.3)
def ding(sec=0.7):            # idea, wink, correct answer
    t = _t(sec); return (np.sin(2 * np.pi * 1568 * t) + 0.4 * np.sin(2 * np.pi * 3136 * t)) * _env(len(t), 0.002, 0.2)
def squeak(sec=0.16):         # small surprise, eyes widen
    return _fade(_sweep(900, 2400, sec, 0.6), 0.005, 0.03)
def zip_out(sec=0.25):        # character dashes out of frame
    return _fade(_sweep(300, 2600, sec, 2.0) * 0.6 + _lp(_noise(sec), 0.4) * 0.4, 0.005, 0.03)
def crash(sec=0.9):           # things break, train derails
    n = int(SR * sec); x = _noise(sec) * _env(n, 0.001, 0.25)
    for k in range(6):
        i = int(_rng.uniform(0, 0.5) * SR); m = int(0.05 * SR)
        x[i:i + m] += _noise(0.05)[:len(x[i:i + m])] * _env(m, 0.001, 0.015) * 2
    return x * 0.8
def scratch(sec=0.35):        # record scratch, "wait what?"
    t = _t(sec); f = 300 + 900 * np.abs(np.sin(2 * np.pi * 3 * t))
    return _fade(np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * 0.3 + _lp(_noise(sec), 0.5) * 0.5, 0.005, 0.05)
def horn(sec=1.2):            # train horn (two-note chord)
    t = _t(sec); s = sum(np.sign(np.sin(2 * np.pi * f * t)) for f in (277, 349, 415)) / 3
    return _fade(_lp(s, 0.12), 0.06, 0.15) * 1.5
def chug(sec=2.0, bpm=200):   # steam train chugging bed
    out = np.zeros(int(SR * sec)); per = int(SR * 60 / bpm)
    for i in range(0, len(out), per):
        b = _lp(_noise(0.12), 0.25) * _env(int(0.12 * SR), 0.003, 0.04) * (1.4 if (i // per) % 2 == 0 else 0.8)
        out[i:i + len(b)] += b[:len(out[i:i + len(b)])]
    return out
def sad_trombone(sec=2.4):    # fail ending
    out = []
    for f, d, vib in ((392, 0.42, 0), (370, 0.42, 0), (349, 0.42, 0), (330, 1.1, 0.03)):
        t = _t(d); fr = f * (1 + vib * np.sin(2 * np.pi * 6 * t))
        ph = 2 * np.pi * np.cumsum(fr) / SR
        out.append(_fade(_lp(sum(np.sin(h * ph) / h for h in range(1, 8)), 0.25), 0.03, 0.1))
    return np.concatenate(out)
def gulp(sec=0.3):            # nervous swallow
    t = _t(sec); return np.sin(2 * np.pi * (300 - 200 * t / sec) * t) * _env(len(t), 0.01, 0.06) * 1.2
def cash(sec=0.5):            # money / profit
    return np.concatenate([ding(0.12) * 0.6, ding(0.4)])

def _norm(fn):
    def g(**kw):
        x = fn(**kw); return x / max(1e-6, np.abs(x).max())
    return g
SFX = {fn.__name__: _norm(fn) for fn in (whoosh, swish, pop, tick, boing, thud, bonk, step, slide_up, slide_down,
       steam, rumble, ding, squeak, zip_out, crash, scratch, horn, chug, sad_trombone, gulp, cash)}

# ---------------- music bed: plucky loop (Karplus-Strong) ----------------
def pluck(freq, dur=0.5, decay=0.996):
    n = int(SR * dur); per = max(2, int(SR / freq))
    buf = _rng.uniform(-1, 1, per); out = np.empty(n)
    for i in range(n):
        j = i % per; out[i] = buf[j]; buf[j] = 0.5 * (buf[j] + buf[(j + 1) % per]) * decay
    return out
NOTES = {"G3": 196.0, "A3": 220.0, "B3": 246.9, "C4": 261.6, "D4": 293.7, "E4": 329.6, "F4": 349.2,
         "G4": 392.0, "A4": 440.0, "B4": 493.9, "C5": 523.3, "C3": 130.8}
MOODS = {  # pattern of 16 eighth notes, bass notes every half bar, bpm
    "playful": (["C4", "G4", "E4", "G4", "A4", "G4", "E4", "G4", "F4", "C5", "A4", "C5", "G4", "D4", "B3", "D4"], ["C3", "G3"], 112),
    "sneaky":  (["A3", "C4", "E4", "C4", "B3", "D4", "F4", "D4", "A3", "C4", "E4", "A4", "G4", "E4", "D4", "B3"], ["A3", "E4"], 96),
    "tense":   (["E4", "F4", "E4", "F4", "E4", "F4", "G4", "F4", "E4", "F4", "E4", "F4", "B3", "C4", "B3", "C4"], ["E4", "B3"], 130),
}
def music_bed(total_sec, mood="playful", duck=()):
    """duck = list of (start_sec, end_sec) where music drops to 40%"""
    pat, bass, bpm = MOODS[mood]; beat = 60 / bpm / 2
    out = np.zeros(int(SR * total_sec)); cache = {}; t = 0.0; k = 0
    while t < total_sec - 0.3:
        for nm, g, d in ((pat[k % 16], 1.0, 0.5),) + (((bass[(k // 8) % 2], 0.9, 0.7),) if k % 4 == 0 else ()):
            if (nm, d) not in cache: cache[(nm, d)] = pluck(NOTES[nm], d)
            s = cache[(nm, d)]; i = int(t * SR); j = min(len(out), i + len(s)); out[i:j] += g * s[:j - i]
        t += beat; k += 1
    gain = np.ones(len(out))
    for a, b in duck:
        gain[int(a * SR):int(b * SR)] = 0.4
    return out * _lp(gain, 0.0005)

def ambience(total_sec, kind="wind"):
    n = int(SR * total_sec)
    if kind == "wind":
        return _lp(_rng.standard_normal(n), 0.01) * (0.6 + 0.4 * np.sin(np.arange(n) / SR * 0.7)) * 2
    if kind == "city":
        return _lp(_rng.standard_normal(n), 0.04) * 0.8
    return np.zeros(n)

# ---------------- mixer ----------------
class Mix:
    def __init__(self, total_sec, fps=30):
        self.fps = fps; self.buf = np.zeros(int(SR * total_sec) + SR)
    def add(self, sig, frame, gain=1.0):
        i = int((frame - 1) / self.fps * SR); j = min(len(self.buf), i + len(sig))
        if i < len(self.buf): self.buf[i:j] += gain * sig[:j - i]
    def sfx(self, name, frame, gain=0.6, **kw):
        self.add(SFX[name](**kw), frame, gain)
    def bed(self, sig, gain=1.0):
        n = min(len(sig), len(self.buf)); self.buf[:n] += gain * sig[:n]
    def write(self, path, total_sec):
        x = self.buf[:int(SR * total_sec)]
        x = x / max(1.0, np.abs(x).max() / 0.89)
        with wave.open(path, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes((x * 32767).astype(np.int16).tobytes())
        return path




# ---------------- MIX ----------------
TOTAL = N / FPS
VO = os.path.join(OUT_DIR, "voice.wav")
HAS_VO = os.path.exists(VO)
SFXG = 0.8 if HAS_VO else 1.0
mix = Mix(TOTAL, FPS)
CLANGS = (360, 631, 674)
duck = [((c - 4) / FPS, (c + 30) / FPS) for c in CLANGS]
mix.bed(music_bed(TOTAL, "playful", duck=duck), 0.10 if HAS_VO else 0.16)
mix.bed(ambience(TOTAL, "city"), 0.04)

def near(f, frames, d): return any(abs(f - x) <= d for x in frames)
# automatic: cuts, expression pops, caption ticks, gesture swishes
for c_ in CUTS:
    if not near(c_, CLANGS, 8): mix.sfx("whoosh", c_ - 5, 0.22 * SFXG)
pops = sorted({fr for ch in (JOE, GARY, SAM) for fr, _ in ch.expr_table[1:]})
last = -99
for fr in pops:
    if fr - last > 4 and not near(fr, CUTS, 2): mix.sfx("pop", fr, 0.2 * SFXG); last = fr
for c in CAPS:
    mix.sfx("tick", c[1], 0.07 * SFXG)
GESTURES = {}
for ch in (JOE, GARY):
    for side, hist in ch.hist.items():
        sp = [0.0] + [abs(b_[1] - a_[1]) for a_, b_ in zip(hist, hist[1:])]
        for i in range(6, len(sp)):
            if sp[i] > 0.08 and max(sp[i - 6:i]) < 0.08:
                GESTURES.setdefault(ch.name, set()).add(hist[i][0])
for who, frames in GESTURES.items():
    last = -99
    for fr in sorted(frames):
        if fr - last > 8 and not near(fr, CUTS, 2): mix.sfx("swish", fr - 2, 0.25 * SFXG); last = fr

# story sounds (frame, name, gain)
EVENTS = [
    (125, "tick", 0.25), (136, "tick", 0.25), (147, "tick", 0.25), (158, "tick", 0.25),       # pen taps clipboard
    (171, "rumble", 0.5), (174, "steam", 0.3),                                                  # Gary blows up
    (250, "ding", 0.18),                                                                        # proud square cover
    (330, "squeak", 0.2),                                                                       # turning it on edge
    (356, "slide_down", 0.3), (360, "crash", 0.55), (361, "thud", 0.5), (392, "thud", 0.18),     # CLANG 1 + echo below
    (440, "swish", 0.25), (453, "pop", 0.3), (497, "pop", 0.3), (513, "squeak", 0.25),          # diagram
    (548, "slide_down", 0.35), (562, "thud", 0.2),
    (600, "pop", 0.3), (626, "slide_down", 0.25), (631, "crash", 0.5), (632, "thud", 0.45),     # CLANG 2
    (643, "pop", 0.3), (669, "slide_down", 0.25), (674, "crash", 0.5), (675, "thud", 0.45),     # CLANG 3
    (690, "scratch", 0.3), (728, "slide_down", 0.25),                                            # out three covers
    (748, "boing", 0.5), (790, "gulp", 0.35), (808, "squeak", 0.2),                             # sewer guy + hat
    (838, "ding", 0.4),                                                                          # the circle is back
    (872, "swish", 0.25), (885, "pop", 0.3), (931, "swish", 0.2), (945, "ding", 0.3),           # circle diagram
    (990, "swish", 0.25), (1005, "thud", 0.35), (1006, "pop", 0.3),                             # drops in, fits
    (1068, "boing", 0.25),                                                                       # 100+ lbs
    (1113, "zip_out", 0.3), (1140, "gulp", 0.4), (1146, "cash", 0.3), (1168, "squeak", 0.2),     # the bill
    (1195, "slide_down", 0.3), (1236, "pop", 0.3),
    (1291, "ding", 0.35), (1300, "pop", 0.25),
]
for fr, nm, g in EVENTS:
    mix.sfx(nm, fr, g * SFXG)
for f in range(ROLL[0] + 4, 1106, 11):                                                           # footsteps while rolling
    mix.sfx("step", f, 0.35 * SFXG)

wav_path = mix.write(os.path.join(OUT_DIR, "sfx_music.wav"), TOTAL)
sed = sc.sequence_editor_create()
st_ = sed.strips.new_sound("sfx_music", wav_path, 1, 1); st_.volume = 0.8 if HAS_VO else 1.0
if HAS_VO:
    sed.strips.new_sound("voice", VO, 2, 1)


# ---------------- render output ----------------
ims = sc.render.image_settings
ims.media_type = 'VIDEO'
ims.file_format = 'FFMPEG'
sc.render.ffmpeg.format = 'MPEG4'
sc.render.ffmpeg.codec = 'H264'
sc.render.ffmpeg.constant_rate_factor = 'HIGH'
sc.render.ffmpeg.audio_codec = 'AAC'
sc.render.ffmpeg.audio_bitrate = 192
sc.render.filepath = os.path.join(OUT_DIR, "manhole_round_v2.mp4")
sc.frame_set(1)
print("SCENE READY ->", sc.render.filepath)
