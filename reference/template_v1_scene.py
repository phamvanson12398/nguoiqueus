# ==========================================================
#  "Meet Joe" - test scene (12 s, 1080x1920, 30 fps)
#  Original 2D characters in a stylised 3D desert railroad.
#  Run inside Blender 5.2: Scripting tab > Run Script.
#  Then render with Render > Render Animation (Ctrl+F12).
# ==========================================================
import bpy, math, os, wave, random
import numpy as np

FPS, N = 30, 360
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

# ---------------- environment ----------------
def cube(name, loc, size, m):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object; o.name = name; o.scale = size
    return setmat(o, m)

SAND = ramp_mat("sand", [(0.3, (0.78, 0.42, 0.20)), (0.5, (0.86, 0.52, 0.27)), (0.7, (0.72, 0.36, 0.18))],
                scale=0.15, bump=0.15, detail=6)
bpy.ops.mesh.primitive_plane_add(size=600, location=(0, 100, 0))
setmat(bpy.context.object, SAND)

BALLAST = ramp_mat("ballast", [(0.0, (0.30, 0.25, 0.22)), (0.35, (0.55, 0.45, 0.38)),
                               (0.65, (0.62, 0.38, 0.28)), (1.0, (0.80, 0.72, 0.65))],
                   scale=9.0, voronoi=True, bump=0.6, rough=0.95)
# trapezoid ballast bed
me = bpy.data.meshes.new("ballast")
Y0, Y1 = -20, 260
vs = [(-1.9, Y0, 0), (1.9, Y0, 0), (1.35, Y0, 0.3), (-1.35, Y0, 0.3),
      (-1.9, Y1, 0), (1.9, Y1, 0), (1.35, Y1, 0.3), (-1.35, Y1, 0.3)]
fs = [(0, 1, 2, 3), (4, 7, 6, 5), (3, 2, 6, 7), (0, 3, 7, 4), (1, 5, 6, 2)]
me.from_pydata(vs, [], fs); me.update()
bal = bpy.data.objects.new("ballast", me); col.objects.link(bal); setmat(bal, BALLAST)

WOOD = ramp_mat("wood", [(0.2, (0.22, 0.13, 0.08)), (0.6, (0.36, 0.22, 0.13)), (0.9, (0.28, 0.17, 0.10))],
                scale=3.0, mapping_scale=(6, 0.4, 0.4), bump=0.3)
sl = cube("sleeper", (0, Y0 + 0.5, 0.36), (2.5, 0.26, 0.12), WOOD)
am = sl.modifiers.new("arr", 'ARRAY'); am.use_relative_offset = False; am.use_constant_offset = True
am.constant_offset_displace = (0, 0.75 / 0.26, 0); am.count = 370

STEEL = pbr("steel", (0.42, 0.40, 0.40), rough=0.35, metal=1.0)
RUST = pbr("rust", (0.30, 0.16, 0.10), rough=0.9)
for x in (-0.72, 0.72):
    cube("rail_web", (x, (Y0 + Y1) / 2, 0.5), (0.05, Y1 - Y0, 0.16), RUST)
    cube("rail_head", (x, (Y0 + Y1) / 2, 0.59), (0.10, Y1 - Y0, 0.05), STEEL)

STRATA = ramp_mat("strata", [(0.0, (0.40, 0.09, 0.05)), (0.25, (0.70, 0.20, 0.08)), (0.45, (0.88, 0.42, 0.16)),
                             (0.6, (0.93, 0.62, 0.38)), (0.75, (0.66, 0.18, 0.08)), (1.0, (0.45, 0.11, 0.06))],
                  tex="wave", scale=0.045, distortion=1.6, detail=2, bump=0.25, coord="Position")

def cliff(name, loc, size, seed):
    o = cube(name, loc, size, STRATA)
    ss = o.modifiers.new("ss", 'SUBSURF'); ss.subdivision_type = 'SIMPLE'; ss.levels = ss.render_levels = 4
    tx = bpy.data.textures.new(name + "_t", 'CLOUDS'); tx.noise_scale = 2.5; tx.noise_depth = 2
    d = o.modifiers.new("disp", 'DISPLACE'); d.texture = tx; d.strength = 0.9; d.texture_coords = 'GLOBAL'
    sm = o.modifiers.new("sm", 'SMOOTH'); sm.iterations = 2
    return o

cliff("wall_L", (-9.5, 40, 9), (5, 90, 22), 1)
cliff("wall_L2", (-14, 120, 12), (8, 80, 28), 2)
for i, (x, y, w, d, h) in enumerate([(26, 70, 22, 16, 10), (45, 120, 30, 20, 16), (12, 165, 18, 14, 13),
                                     (-30, 190, 26, 18, 20), (60, 60, 20, 30, 8)]):
    cliff(f"mesa{i}", (x, y, h / 2 - 0.5), (w, d, h), i)

# telegraph poles
POLE = pbr("pole", (0.25, 0.16, 0.10), rough=0.9)
for i in range(14):
    y = -6 + i * 14
    bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=0.09, depth=6, location=(3.4, y, 3))
    setmat(bpy.context.object, POLE)
    cube("bar", (3.4, y, 5.6), (1.4, 0.1, 0.1), POLE)

# cacti
CACT = pbr("cactus", (0.20, 0.45, 0.22), rough=0.7)
def cactus(x, y, h):
    bpy.ops.mesh.primitive_cylinder_add(vertices=14, radius=0.22, depth=h, location=(x, y, h / 2)); setmat(bpy.context.object, CACT)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.22, location=(x, y, h)); setmat(bpy.context.object, CACT)
    for s, hh in ((1, 0.55), (-1, 0.4)):
        bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.14, depth=0.5, location=(x + s * 0.32, y, h * hh),
                                            rotation=(0, math.pi / 2, 0)); setmat(bpy.context.object, CACT)
        bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.14, depth=0.7, location=(x + s * 0.55, y, h * hh + 0.33)); setmat(bpy.context.object, CACT)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.14, location=(x + s * 0.55, y, h * hh + 0.68)); setmat(bpy.context.object, CACT)
for x, y, h in ((5.5, 12, 2.6), (8, 30, 3.2), (-4.2, 22, 2.2), (6.5, 55, 3.0)):
    cactus(x, y, h)

# rocks
ROCK = ramp_mat("rock", [(0.3, (0.45, 0.20, 0.10)), (0.7, (0.65, 0.33, 0.16))], scale=2, bump=0.4)
for i in range(40):
    x = random.choice([-1, 1]) * random.uniform(2.3, 7); y = random.uniform(-4, 70)
    r = random.uniform(0.08, 0.35)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=r, location=(x, y, r * 0.3))
    o = bpy.context.object; o.scale = (1, random.uniform(0.7, 1.3), random.uniform(0.5, 0.8))
    o.rotation_euler = (0, 0, random.uniform(0, 6)); setmat(o, ROCK)

# soft clouds
CLOUDM = flat("cloud", (0.97, 0.97, 1.0))
for cx, cy, cz in ((-25, 160, 45), (30, 190, 55), (5, 220, 40), (60, 170, 35)):
    for k in range(6):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=random.uniform(4, 8),
                                             location=(cx + random.uniform(-9, 9), cy + random.uniform(-3, 3), cz + random.uniform(-2, 2)))
        o = bpy.context.object; o.scale = (1, 0.5, 0.55); setmat(o, CLOUDM)
        o.visible_shadow = False

# ---------------- camera ----------------
cam_d = bpy.data.cameras.new("Cam"); cam_d.lens = 32; cam_d.clip_start = 0.05; cam_d.clip_end = 600
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

# ---------------- JOE (worker) ----------------
SKIN = WHITE
BLUE = flat("joe_blue", (0.03, 0.22, 0.55))
HIVIS = flat("hivis", (0.95, 0.85, 0.05))
HAT = flat("hardhat", (0.98, 0.30, 0.02))
HAT_D = flat("hardhat_d", (0.75, 0.18, 0.01))
HAIR = flat("hair", (0.36, 0.22, 0.12))
MOUTH = flat("mouth", (0.55, 0.10, 0.10))
TONGUE = flat("tongue", (0.95, 0.45, 0.45))

joe, jp = char_root("Joe", (-0.55, 5.0, 0.42))
j_body = empty("joe_body", jp)                                   # bob/breath pivot at feet
j_legL = limb(j_body, "joe_legL", (-0.15, 0.74), 0.36, 0.34, 0.065, 0.05, "shoe")
j_legR = limb(j_body, "joe_legR", (0.15, 0.74), 0.36, 0.34, 0.065, 0.05, "shoe")
j_torso = empty("joe_torso", j_body, (0, 0.70, 0))
shape(j_torso, "joe_shirt", rrect(0, 0.40, 0.80, 0.82, 0.30), BLUE, 0.12)
shape(j_torso, "joe_stripe", rrect(0, 0.32, 0.78, 0.12, 0.03), HIVIS, 0.17, outline=0.02)
shape(j_torso, "joe_pocket", rrect(0.18, 0.58, 0.18, 0.15, 0.03), BLUE, 0.17, outline=0.022)
stroke(j_torso, "joe_neck", [(0, 0.78), (0, 0.88)], 0.06, 0.1)
j_armL = limb(j_torso, "joe_armL", (-0.33, 0.66), 0.34, 0.32, 0.05, 0.24, "hand")
j_armR = limb(j_torso, "joe_armR", (0.33, 0.66), 0.34, 0.32, 0.05, 0.24, "hand")
j_head = empty("joe_head", j_torso, (0, 1.34, 0.3))
shape(j_head, "joe_hair", ellipse(-0.36, 0.06, 0.16, 0.22, 24), HAIR, -0.05)
shape(j_head, "joe_face", ellipse(0, 0, 0.5, 0.48, 48), SKIN, 0.0)
dome = ellipse(0, 0.2, 0.47, 0.40, 30, 0, math.pi)
shape(j_head, "joe_hat", dome, HAT, 0.08)
stroke(j_head, "joe_hat_ridge", [(0, 0.2), (0, 0.58)], 0.035, 0.12)
shape(j_head, "joe_brim", rrect(0.04, 0.2, 1.12, 0.12, 0.05), HAT_D, 0.13)

def eye(parent, name, x, y, z, rx=0.055, ry=0.085):
    g = empty(name, parent, (x, y, z)); disc(g, name + "_d", 0, 0, 1.0, 0, INK); g.scale = (rx, ry, 1); return g

J = {}
J["neutral"] = g = group(j_head, "joe_neutral")
J["eyes_n"] = [eye(g, "jeL", -0.15, -0.02, 0.06), eye(g, "jeR", 0.15, -0.02, 0.06)]
stroke(g, "j_mouth_n", ellipse(0.0, -0.13, 0.12, 0.07, 10, math.radians(200), math.radians(340)), 0.035, 0.06)
stroke(g, "j_brow_nL", [(-0.22, 0.12), (-0.09, 0.14)], 0.03, 0.06); stroke(g, "j_brow_nR", [(0.09, 0.14), (0.22, 0.12)], 0.03, 0.06)

J["happy"] = g = group(j_head, "joe_happy")
stroke(g, "j_eye_hL", ellipse(-0.15, -0.05, 0.07, 0.07, 10, math.radians(20), math.radians(160)), 0.035, 0.06)
stroke(g, "j_eye_hR", ellipse(0.15, -0.05, 0.07, 0.07, 10, math.radians(20), math.radians(160)), 0.035, 0.06)
mp = [(-0.17, -0.12)] + ellipse(0, -0.12, 0.17, 0.17, 16, math.pi, 2 * math.pi)[1:]
shape(g, "j_mouth_h", mp, MOUTH, 0.06, outline=0.03)
shape(g, "j_tongue", ellipse(0, -0.24, 0.07, 0.04, 16), TONGUE, 0.08, outline=0)

def smirk_face(name, wink=False):
    g = group(j_head, name)
    eL = eye(g, name + "eL", -0.15, -0.03, 0.06, 0.055, 0.065)
    shape(g, name + "lidL", rrect(-0.15, 0.02, 0.15, 0.06, 0.02), SKIN, 0.09, outline=0)
    stroke(g, name + "lidlineL", [(-0.22, -0.005), (-0.08, -0.005)], 0.03, 0.1)
    if wink:
        stroke(g, name + "winkR", ellipse(0.15, -0.06, 0.07, 0.06, 10, math.radians(20), math.radians(160)), 0.035, 0.06)
        eR = None
    else:
        eR = eye(g, name + "eR", 0.15, -0.03, 0.06, 0.055, 0.065)
        shape(g, name + "lidR", rrect(0.15, 0.02, 0.15, 0.06, 0.02), SKIN, 0.09, outline=0)
        stroke(g, name + "lidlineR", [(0.08, -0.005), (0.22, -0.005)], 0.03, 0.1)
    stroke(g, name + "browL", [(-0.23, 0.10), (-0.08, 0.09)], 0.03, 0.06)
    stroke(g, name + "browR", [(0.08, 0.15), (0.16, 0.19), (0.23, 0.17)], 0.03, 0.06)
    stroke(g, name + "mouth", [(-0.10, -0.17), (0.02, -0.18), (0.11, -0.15), (0.15, -0.11)], 0.035, 0.06)
    return g
J["smirk"] = smirk_face("joe_smirk")
J["wink"] = smirk_face("joe_wink", wink=True)

# ---------------- BOSS ----------------
SUIT = flat("suit", (0.07, 0.08, 0.14))
SHIRT = flat("shirt", (0.95, 0.95, 0.93))
TIE = flat("tie", (0.80, 0.10, 0.12))
GOLD = flat("gold", (0.95, 0.72, 0.15))
GREY = flat("grey_hair", (0.62, 0.62, 0.64))
BOSS_SKIN = flat("boss_skin", (0.98, 0.98, 0.97))
TEETH = flat("teeth", (1, 1, 1))
STEAM = flat("steam", (0.97, 0.97, 0.98))

boss, bp = char_root("Boss", (0.75, 5.2, 0.42))
b_body = empty("boss_body", bp)
b_legL = limb(b_body, "boss_legL", (-0.17, 0.80), 0.40, 0.38, 0.065, 0.05, "shoe")
b_legR = limb(b_body, "boss_legR", (0.17, 0.80), 0.40, 0.38, 0.065, 0.05, "shoe")
b_torso = empty("boss_torso", b_body, (0, 0.76, 0))
shape(b_torso, "boss_suit", rrect(0, 0.46, 0.94, 0.96, 0.32), SUIT, 0.12)
shape(b_torso, "boss_shirtV", [(-0.17, 0.92), (0.17, 0.92), (0, 0.55)], SHIRT, 0.16, outline=0.025)
shape(b_torso, "boss_tie", [(-0.045, 0.88), (0.045, 0.88), (0.07, 0.56), (0, 0.46), (-0.07, 0.56)], TIE, 0.2, outline=0.022)
for k in range(2):
    disc(b_torso, f"boss_btn{k}", 0.13, 0.28 - k * 0.14, 0.035, 0.18, GOLD)
stroke(b_torso, "boss_neck", [(0, 0.92), (0, 0.98)], 0.06, 0.1)
b_armL = limb(b_torso, "boss_armL", (-0.40, 0.74), 0.36, 0.34, 0.05, 0.24, "hand")
b_armR = limb(b_torso, "boss_armR", (0.40, 0.74), 0.36, 0.34, 0.05, 0.24, "hand")
b_head = empty("boss_head", b_torso, (0, 1.44, 0.3))
for s in (-1, 1):
    shape(b_head, f"boss_tuft{s}", ellipse(s * 0.42, 0.02, 0.14, 0.2, 24), GREY, -0.05)
shape(b_head, "boss_face", ellipse(0, 0, 0.48, 0.5, 48), BOSS_SKIN, 0.0)
must = [(0, -0.1), (0.07, -0.08), (0.17, -0.10), (0.24, -0.18), (0.16, -0.16), (0.06, -0.17), (0, -0.14),
        (-0.06, -0.17), (-0.16, -0.16), (-0.24, -0.18), (-0.17, -0.10), (-0.07, -0.08)]
shape(b_head, "boss_must", must, INK, 0.1, outline=0)
stroke(b_head, "boss_wrinkle", [(-0.08, 0.30), (0.08, 0.30)], 0.02, 0.06)

B = {}
B["stern"] = g = group(b_head, "boss_stern")
B["eyes_s"] = [eye(g, "beL", -0.15, 0.04, 0.06, 0.05, 0.07), eye(g, "beR", 0.15, 0.04, 0.06, 0.05, 0.07)]
stroke(g, "b_brow_sL", [(-0.25, 0.17), (-0.07, 0.13)], 0.04, 0.06); stroke(g, "b_brow_sR", [(0.07, 0.13), (0.25, 0.17)], 0.04, 0.06)
stroke(g, "b_mouth_s", [(-0.08, -0.25), (0.08, -0.25)], 0.03, 0.06)

B["angry"] = g = group(b_head, "boss_angry")
eye(g, "baL", -0.14, 0.02, 0.06, 0.05, 0.05); eye(g, "baR", 0.14, 0.02, 0.06, 0.05, 0.05)
stroke(g, "b_brow_aL", [(-0.27, 0.18), (-0.05, 0.07)], 0.05, 0.07); stroke(g, "b_brow_aR", [(0.05, 0.07), (0.27, 0.18)], 0.05, 0.07)
shape(g, "b_teeth", rrect(0, -0.28, 0.26, 0.12, 0.03), TEETH, 0.06, outline=0.03)
for x in (-0.065, 0, 0.065):
    stroke(g, f"b_tooth{x}", [(x, -0.33), (x, -0.23)], 0.015, 0.09)
stroke(g, "b_toothmid", [(-0.12, -0.28), (0.12, -0.28)], 0.015, 0.09)
stroke(g, "b_vein1", [(0.20, 0.33), (0.26, 0.28)], 0.03, 0.07, m=TIE); stroke(g, "b_vein2", [(0.27, 0.36), (0.29, 0.29)], 0.03, 0.07, m=TIE)

puffs = []
for s in (-1, 1):
    pv = empty(f"puff{s}", b_head, (s * 0.52, 0.42, 0.2))
    for k, (dx, dy, r) in enumerate(((0, 0, 0.11), (0.1, 0.06, 0.09), (-0.08, 0.08, 0.08), (0.03, 0.13, 0.08))):
        shape(pv, f"puff{s}_{k}", ellipse(dx * s, dy, r, r, 20), STEAM, 0.01 * k, outline=0.025)
    puffs.append(pv)

# ---------------- timeline: shots ----------------
S1, S2, S3 = (1, 105), (106, 215), (216, 360)

def ease(u):
    u = max(0.0, min(1.0, u)); return u * u * (3 - 2 * u)

def lerp3(a, b, u):
    return tuple(a[i] + (b[i] - a[i]) * u for i in range(3))

# camera v3: one continuous move per sequence + motivated transitions (module "Camera v3")
SEQS = [
    dict(a=S1[0], b=S1[1], keys=[(S1[0], (-2.8, 0.2, 0.95), (-0.55, 5.0, 1.5), 28, 0),
                                  (S1[1], (-1.9, 2.0, 1.1), (-0.5, 5.0, 1.65), 31, -2)]),
    dict(a=S2[0], b=S2[1], keys=[(S2[0], (2.8, 2.0, 1.4), (0.75, 5.2, 2.15), 33, 0),
                                  (S2[1], (2.1, 3.0, 1.6), (0.75, 5.2, 2.3), 35, 3)]),
    dict(a=S3[0], b=S3[1], keys=[(S3[0], (0.3, -0.6, 0.9), (0.1, 5.1, 1.5), 29, 0),
                                  (S3[1], (0.1, 0.8, 1.1), (0.1, 5.1, 1.7), 31, 0)]),
]
TRANS = {S2[0]: ('whip', 1), S3[0]: ('cut',)}      # cut on action: boss turns, camera keeps its drift
PUNCH = [(146, 1.15, 8)]                             # "PERFECT."
SHAKES = [(150, 1.2, 30)]                            # boss outburst
CAM = solve_camera(SEQS, TRANS, PUNCH, SHAKES)
cam_report(CAM, SEQS, TRANS, PUNCH)
LENS_F = bake_camera(cam, cam_d, CAM, set(TRANS))

# boss is off set during shot 1, steps in for shot 2
boss.location = (6, 8, 0.42); boss.keyframe_insert("location", frame=1); boss.keyframe_insert("location", frame=S1[1])
boss.location = (0.75, 5.2, 0.42); boss.keyframe_insert("location", frame=S2[0])
for fc in boss.animation_data.action.fcurves if hasattr(boss.animation_data.action, "fcurves") else []:
    for k in fc.keyframe_points: k.interpolation = 'CONSTANT'

# ---------------- character animation ----------------
LIMB_HIST = {}
def pose_limb(lp, a1, a2, f):
    up, lo = lp
    LIMB_HIST.setdefault(up.name, []).append((f, a1 + 0.5 * a2))
    up.rotation_euler = (0, 0, a1); lo.rotation_euler = (0, 0, a2)
    up.keyframe_insert("rotation_euler", frame=f); lo.keyframe_insert("rotation_euler", frame=f)

def angle_mix(a, b, u):
    return a + (b - a) * u

J_EXPR = [(1, "neutral"), (24, "happy"), (70, "neutral"), (226, "smirk"), (300, "wink"), (318, "smirk")]
B_EXPR = [(1, "stern"), (146, "angry")]
BOSS_RED = (0.92, 0.28, 0.25)

def expr_at(table, f):
    cur = table[0][1]
    for t, e in table:
        if f >= t: cur = e
    return cur

for f in range(1, N + 1):
    t = f / FPS
    # --- Joe ---
    breath = 1 + 0.015 * math.sin(t * 2.4)
    j_body.scale = (1 / math.sqrt(breath), breath, 1); j_body.keyframe_insert("scale", frame=f)
    j_head.rotation_euler = (0, 0, 0.04 * math.sin(t * 1.7)); j_head.keyframe_insert("rotation_euler", frame=f)
    pose_limb(j_legL, -0.06, 0.02, f); pose_limb(j_legR, 0.06, -0.02, f)
    if f <= 105:
        w = ease((f - 18) / 10) * (1 - ease((f - 80) / 12))      # wave hello
        pose_limb(j_armR, angle_mix(0.25, 2.6, w), angle_mix(-0.15, 0.25 + 0.45 * math.sin(t * 14) * w, w), f)
        pose_limb(j_armL, -0.25, 0.1, f)
    else:
        # hands on hips -> right hand points up for "other plans"
        hip_u = ease((f - 220) / 10)
        up_u = ease((f - 262) / 8)
        pose_limb(j_armL, angle_mix(angle_mix(-0.25, -0.75, hip_u), -2.75, up_u),
                  angle_mix(angle_mix(0.1, 1.9, hip_u), -0.25, up_u), f)
        pose_limb(j_armR, angle_mix(0.25, 0.75, hip_u), angle_mix(-0.15, -1.9, hip_u), f)
    for name, g in J.items():
        if name.startswith("eyes"): continue
        vis = expr_at(J_EXPR, f) == name
        prev = expr_at(J_EXPR, f - 1) if f > 1 else None
        if f == 1 or vis != (prev == name): set_visible(g, f, vis)
    blink = any(b <= f < b + 4 for b in (45, 140, 250))
    for e_ in J["eyes_n"]:
        e_.scale = (0.055, 0.012 if blink else 0.085, 1); e_.keyframe_insert("scale", frame=f)

    # --- Boss ---
    angry = f >= 146
    jit = 0.012 * math.sin(f * 2.9) if angry else 0
    b_body.location = (jit, 0, 0); b_body.keyframe_insert("location", frame=f)
    bb = 1 + 0.012 * math.sin(t * 2.0 + 1)
    b_body.scale = (1 / math.sqrt(bb), bb, 1); b_body.keyframe_insert("scale", frame=f)
    pose_limb(b_legL, -0.07, 0.02, f); pose_limb(b_legR, 0.07, -0.02, f)
    if not angry:
        pose_limb(b_armL, -0.15, -0.6, f); pose_limb(b_armR, 0.15, 0.6, f)      # hands behind back-ish
    else:
        u = ease((f - 146) / 6)
        shake = 0.18 * math.sin(f * 1.7)
        pose_limb(b_armL, angle_mix(-0.15, -2.0 + shake, u), angle_mix(-0.6, -1.0, u), f)
        pose_limb(b_armR, angle_mix(0.15, 2.0 - shake, u), angle_mix(0.6, 1.0, u), f)
    for name in ("stern", "angry"):
        vis = expr_at(B_EXPR, f) == name
        prev = expr_at(B_EXPR, f - 1) if f > 1 else None
        if f == 1 or vis != (prev == name): set_visible(B[name], f, vis)
    for k, pv in enumerate(puffs):
        if angry:
            ph = ((f - 146) / 18.0 + k * 0.5) % 1.0
            s = math.sin(math.pi * ph) * 1.2
            pv.scale = (s, s, 1); pv.location = (pv.location[0], 0.42 + 0.35 * ph, 0.2)
        else:
            pv.scale = (0, 0, 1)
        pv.keyframe_insert("scale", frame=f); pv.keyframe_insert("location", frame=f)

# boss face turns red
emit = BOSS_SKIN.node_tree.nodes["Emission"].inputs[0]
emit.default_value = (0.98, 0.98, 0.97, 1); emit.keyframe_insert("default_value", frame=144)
emit.default_value = (*BOSS_RED, 1); emit.keyframe_insert("default_value", frame=156)

# ---------------- captions (word by word) ----------------
CAPS = [  # text, start, end, color, size
    ("Meet", 12, 24), ("Joe.", 24, 54),
    ("He builds", 58, 76), ("railroads.", 76, 104),
    ("His boss", 112, 128), ("wants them", 128, 144), ("PERFECT.", 146, 182, (1.0, 0.85, 0.1), 1.35),
    ("No gaps.", 184, 212),
    ("But Joe", 222, 244), ("has", 248, 258), ("other", 258, 272), ("plans.", 272, 312),
]
CAP_D = 1.0
font = bpy.data.fonts.load(FONT_PATH) if FONT_PATH else None
cap_root = empty("captions", cam, (0, -0.12, -CAP_D))
for i, c in enumerate(CAPS):
    txt, a, b = c[0], c[1], c[2]
    rgb = c[3] if len(c) > 3 else (1, 1, 1)
    size = 0.085 * (c[4] if len(c) > 4 else 1.0)
    holder = empty(f"cap{i}", cap_root)
    for layer, (m, off, z) in enumerate(((INK, size * 0.11, -0.002), (flat(f"capc{i}", rgb), 0.0, 0.0))):
        cu = bpy.data.curves.new(f"cap{i}_{layer}", 'FONT'); cu.body = txt
        if font: cu.font = font
        cu.size = size; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.offset = off
        o = bpy.data.objects.new(f"cap{i}_{layer}", cu); col.objects.link(o)
        o.parent = holder; o.location = (0, 0, z); o.data.materials.append(m)
    for f in range(max(1, a - 1), min(N, b + 1) + 1):
        if f < a or f > b:
            s = 0.0
        else:
            u = (f - a) / 4.0
            s = 1.0 if u >= 1 else (u * 1.25 if u < 0.8 else 1.0 + (1 - u) * 0.25 / 0.2 * 0.2)
            s = min(s, 1.15)
        holder.scale = (s, s, s); holder.keyframe_insert("scale", frame=f)
    holder.scale = (0, 0, 0); holder.keyframe_insert("scale", frame=1) if a > 2 else None

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


TOTAL = N / FPS
mix = Mix(TOTAL, FPS)
mix.bed(music_bed(TOTAL, "playful", duck=[(S2[0] / FPS, S2[1] / FPS)]), 0.16)
mix.bed(ambience(TOTAL, "wind"), 0.05)
# VO: if a voice file exists next to the output, it is added on its own strip below

# --- automatic action sounds ---
for a_ in (S2[0], S3[0]):                                   # every camera cut
    mix.sfx("whoosh", a_ - 6, 0.35)
for table in (J_EXPR, B_EXPR):                               # every expression change
    for fr, _ in table[1:]:
        mix.sfx("pop", fr, 0.25)
for c in CAPS:                                               # every caption word
    mix.sfx("tick", c[1], 0.10)
GESTURES = {}                                                # every gesture onset (still -> moving)
for name, hist in LIMB_HIST.items():
    if "leg" in name: continue
    who = name.split("_")[0]
    sp = [0.0] + [abs(b_[1] - a_[1]) for a_, b_ in zip(hist, hist[1:])]
    for i in range(6, len(sp)):
        if sp[i] > 0.08 and max(sp[i - 6:i]) < 0.08:
            GESTURES.setdefault(who, set()).add(hist[i][0])
for who, frames in GESTURES.items():
    last = -99
    for fr in sorted(frames):
        if fr - last > 8:
            mix.sfx("swish", fr - 2, 0.30); last = fr

# --- hand-placed story sounds (frame, name, gain) ---
EVENTS = [
    (146, "rumble", 0.55), (147, "steam", 0.30), (148, "squeak", 0.25),
    (300, "ding", 0.35),
]
for fr, nm, g in EVENTS:
    mix.sfx(nm, fr, g)

wav_path = mix.write(os.path.join(OUT_DIR, "sfx_music.wav"), TOTAL)
sed = sc.sequence_editor_create()
sed.strips.new_sound("sfx_music", wav_path, 1, 1)
VO = os.path.join(OUT_DIR, "voice.wav")
if os.path.exists(VO):
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
sc.render.filepath = os.path.join(OUT_DIR, "joe_test.mp4")
sc.frame_set(1)
print("SCENE READY ->", sc.render.filepath)
