# ==========================================================
#  "Why Manhole Covers Are Round" (45 s, 1080x1920, 30 fps)
#  manhole_scene_v2.py rebuilt on top of core/ (same output, frame for frame).
#  Run:  blender -b -P projects/manhole-round/scene_v2_core.py            (build only)
#        blender -b -P projects/manhole-round/scene_v2_core.py -- --render (render mp4)
#  Or open in Blender's Text Editor and Run Script.
# ==========================================================
import bpy, math, os, sys, random

# ---- find the repo root (works with -P and from the Text Editor) ----
_here = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() and os.path.exists(__file__) else None
if _here is None and bpy.data.filepath:
    _here = os.path.dirname(bpy.data.filepath)
ROOT = os.environ.get("WHYSHORTS_ROOT") or os.path.abspath(os.path.join(_here, "..", ".."))
if ROOT not in sys.path: sys.path.insert(0, ROOT)
for _m in [m for m in sys.modules if m == "core" or m.startswith("core.")]:
    del sys.modules[_m]                                   # fresh module state on every run

import core
from core import ctx, look, geo, timing, camera, faces, chars, fx, captions, sfx, mixer
from core.look import flat, pbr, ramp_mat, setmat, window_mat, iron_mat
from core.geo import (cube, cyl, sphere, plane, ellipse, rrect, shape, stroke, disc, empty, text,
                      vis_track, key_loc, key_rot, key_scl)
from core.timing import ease, lerp, lerp3, pease, pop_scale, load_amplitude, add_teleport_holds
from core.chars import make_char, pose_char, apply_expressions, walk_legs, prop_round, prop_square

FPS, N = 30, 1350
PROJECT_DIR = os.path.join(ROOT, "projects", "manhole-round")
OUT_DIR = os.environ.get("WHYSHORTS_OUT") or PROJECT_DIR      # voice.wav is read from here, sfx_music.wav + mp4 written here
sc = core.start(N, FPS, OUT_DIR)
col = sc.collection
random.seed(7)

WORDS = [(0.0, 'Meet'), (0.19, 'Gary.'), (0.92, 'Gary'), (1.28, 'runs'), (1.47, 'the'), (1.65, 'city'), (2.02, 'budget,'), (2.58, 'and'), (2.79, 'Gary'), (3.21, 'hates'), (3.64, 'circles.'), (4.06, 'Circles'), (4.48, 'waste'), (4.69, 'metal,"'), (5.12, 'he'), (5.33, 'says.'), (5.72, 'Make'), (5.92, 'the'), (6.11, 'manhole'), (6.7, 'covers'), (7.09, 'square."'), (7.5, 'So'), (7.65, 'Joe'), (7.81, 'makes'), (8.11, 'them'), (8.27, 'square.'), (8.68, 'Day'), (8.89, 'one.'), (9.3, 'Joe'), (9.5, 'lifts'), (9.7, 'the'), (9.9, 'new'), (10.11, 'cover,'), (10.51, 'turns'), (10.71, 'it'), (10.91, 'just'), (11.11, 'a'), (11.31, 'little...'), (11.72, 'and'), (11.92, 'CLANG.'), (12.32, 'It'), (12.52, 'drops'), (12.71, 'straight'), (12.9, 'down'), (13.1, 'the'), (13.3, 'hole.'), (13.69, 'See,'), (14.16, 'a'), (14.34, 'square'), (14.53, 'is'), (14.71, 'wider'), (15.08, 'corner'), (15.44, 'to'), (15.63, 'corner'), (15.99, 'than'), (16.18, 'it'), (16.36, 'is'), (16.54, 'side'), (16.73, 'to'), (16.91, 'side.'), (17.09, 'Tilt'), (17.28, 'it,'), (17.84, 'and'), (18.04, 'it'), (18.24, 'slips'), (18.44, 'right'), (18.64, 'through.'), (18.84, 'Gary'), (19.24, 'orders'), (19.64, 'another'), (20.24, 'one.'), (21.02, 'CLANG.'), (21.21, 'And'), (21.4, 'another.'), (22.44, 'CLANG.'), (23.06, 'Now'), (23.23, 'the'), (23.4, 'city'), (23.74, 'is'), (23.92, 'out'), (24.09, 'three'), (24.26, 'covers,'), (24.86, 'and'), (25.02, 'a'), (25.18, 'guy'), (25.34, 'in'), (25.5, 'the'), (25.66, 'sewer'), (25.99, 'is'), (26.15, 'wearing'), (26.47, 'one'), (26.63, 'as'), (26.79, 'a'), (26.95, 'hat.'), (27.11, 'So'), (27.27, 'Joe'), (27.44, 'brings'), (27.6, 'back'), (27.76, 'the'), (27.92, 'circle.'), (28.64, 'A'), (28.81, 'circle'), (29.14, 'is'), (29.31, 'the'), (29.48, 'same'), (29.65, 'width'), (29.81, 'no'), (29.98, 'matter'), (30.32, 'how'), (30.48, 'you'), (30.65, 'turn'), (30.82, 'it,'), (30.99, 'so'), (31.15, 'it'), (31.32, 'can'), (31.49, 'never'), (31.82, 'fall'), (31.99, 'in.'), (32.38, 'You'), (32.57, 'never'), (32.94, 'have'), (33.13, 'to'), (33.32, 'line'), (33.51, 'it'), (33.69, 'up.'), (33.88, 'And'), (34.07, 'a'), (34.26, 'cover'), (34.63, 'that'), (34.82, 'weighs'), (35.01, 'over'), (35.38, 'a'), (35.57, 'hundred'), (35.94, 'pounds?'), (36.13, 'You'), (36.32, 'just'), (36.51, 'roll'), (36.69, 'it.'), (37.08, 'Gary'), (37.44, 'looks'), (37.62, 'at'), (37.8, 'the'), (37.98, 'bill.'), (38.44, 'Then'), (38.6, 'at'), (38.77, 'the'), (38.93, 'circle.'), (39.62, 'Fine,"'), (39.98, 'he'), (40.34, 'says.'), (40.98, 'But'), (41.19, "I'm"), (41.39, 'keeping'), (41.8, 'the'), (42.01, 'square'), (42.21, 'one."'), (42.74, 'As'), (42.87, 'a'), (43.01, 'coffee'), (43.27, 'table.')]

# ---------------- world / light ----------------
look.sky_world()
look.sun_light()

# ---------------- STREET SET (hole at origin of action: H) ----------------
H = (0.0, 4.0)
ASPHALT = ramp_mat("asphalt", [(0.3, (0.10, 0.10, 0.11)), (0.7, (0.16, 0.16, 0.17))], scale=40, bump=0.3, detail=8)
plane(400, (0, 60, 0), ASPHALT)
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
cam, cam_d, tgt = camera.make_shot_camera(lens=30)

# ---------------- shared 2D materials, FX pool, faces ----------------
geo.init(); INK = geo.INK; WHITE = geo.WHITE
fx.init()
faces.init(); RED_M = faces.RED_M; SWEAT = faces.SWEAT

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
text("bill_total", "$$$", 0.09, bill_strip, (0, -0.98, 0.03), RED_M, align_y=False, font_path=None)
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
def label(parent, name, txt, loc, size, m):
    return text(name, txt, size, parent, (loc[0], loc[1], 0.2), m)

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

# reaction FX rigs and a talking mouth for the character who speaks quoted lines
for ch_ in (JOE, GARY, SAM):
    fx.add_reaction_fx(ch_)
chars.add_talk_mouth(GARY)

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
def roll_track(f):
    x = roll_x(f); return (x - 0.6, 0.0, 1.15), (x - 0.3, 3.0, 0.85)
SHAKES = [(360, 0.06), (171, 0.03), (631, 0.05), (674, 0.05), (760, 0.03), (1005, 0.02)]
PUNCH = [(213, 1.22), (360, 1.18), (631, 1.12), (674, 1.18), (838, 1.15), (1068, 1.2), (1291, 1.12)]   # zoom punch-ins on beats
WHIP_IN = {225, 411, 566, 814, 859, 971, 1111, 1281}                                                    # cuts that use a whip pan
SHOT_FSTOP = {0: 8.0, 6: 64, 10: 64, 12: 5.6, 2: 2.8, 13: 2.8}                                         # default 4 = gently soft background
CAMRES = camera.bake_shots(cam, cam_d, tgt, SHOTS, SHAKES, PUNCH, WHIP_IN, SHOT_FSTOP, track=roll_track)
LENS_F = CAMRES["lens"]; CUTS = CAMRES["cuts"]

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
CAPS = captions.make_caps(WORDS, HIGHLIGHT, impact=("clang",))
cap_root = captions.build_captions(CAPS, LENS_F, lift_ranges=[(411, 565), (859, 970)])

# ---------------- dust, reaction FX, lip flap ----------------
for fr in (360, 631, 674):
    fx.dust_burst(fr, (H[0], H[1], 0.0), n=10, radius=0.85, size=1.0, life=22, rise=0.5)
fx.dust_burst(750, (H[0], H[1], 0.0), n=6, radius=0.6, size=0.7)
fx.dust_burst(1005, (H[0], H[1], 0.0), n=6, radius=0.75, size=0.45, life=16, rise=0.12)
for fr in range(ROLL[0] + 6, 1106, 9):
    fx.dust_burst(fr, (roll_x(fr), 3.0, 0.0), n=2, radius=0.25, size=0.35, life=14, rise=0.15)
fx.bake_dust()
fx.bake_reaction_fx(JOE, [358, 674]); fx.bake_reaction_fx(GARY, [631, 674, 1140]); fx.bake_reaction_fx(SAM, [785])
chars.bake_talk(GARY, GARY_TALK, AMP)

add_teleport_holds([JOE.root, GARY.root, SAM.root, CV_ROLL, CV_DROP_ROUND] + CV_DROP)

# film look: outlines on the 3D set only, bloom, mist, vignette, motion blur
NOLINE = []
for root_ in (JOE.root, GARY.root, SAM.root, cap_root, dg):
    NOLINE += look.descendants(root_)
for p_ in fx.PUFF_POOL: NOLINE += look.descendants(p_)
NOLINE += [o for o in bpy.data.objects if o.name.startswith(("dg_", "cloud", "Sphere")) and o.type == 'MESH' and o.location.z > 30]
NOLINE.append(bpy.data.objects["dg_back"])
look.setup_look(NOLINE)

# ---------------- SOUND: action SFX + music bed ----------------
TOTAL = N / FPS
VO = os.path.join(OUT_DIR, "voice.wav")
HAS_VO = os.path.exists(VO)
SFXG = 0.8 if HAS_VO else 1.0
mix = mixer.Mix(TOTAL, FPS)
CLANGS = (360, 631, 674)
duck = [((c - 4) / FPS, (c + 30) / FPS) for c in CLANGS]
mix.bed(sfx.music_bed(TOTAL, "playful", duck=duck), 0.10 if HAS_VO else 0.16)
mix.bed(sfx.ambience(TOTAL, "city"), 0.04)
mixer.auto_sfx(mix, CUTS, (JOE, GARY, SAM), CAPS, avoid_cuts=CLANGS, gain=SFXG, gesture_chars=(JOE, GARY))

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
mixer.attach_audio(wav_path, VO)

# ---------------- render output ----------------
mixer.set_video_output(os.path.join(OUT_DIR, "manhole_round_v2.mp4"))
sc.frame_set(1)
print("SCENE READY ->", sc.render.filepath)

if "--render" in sys.argv:
    bpy.ops.render.render(animation=True)
