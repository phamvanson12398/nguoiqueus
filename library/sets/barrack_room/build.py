"""Roman barrack room (contubernium) at night, open toward -Y (camera stands at -Y looking +Y).
All positions are relative to `origin` [x, y] (default [0, 0]; the story passes [1300, 0]); floor z = 0.

Room: inner faces of the walls at x = -4 (left), x = +4 (right), y = 7 (back); side walls run from y = -2 to the back.
Ochre whitewashed stone walls with a dirty dado band up to z 0.9, dark beams along X at z 4.5, plank ceiling at 4.75,
rammed-earth floor.  Rough table 1.6 x 0.8 centred (0, 3.6), top z = 0.9, stool behind it at (0.3, 4.55).
On the table: terracotta oil lamp (-0.5, 3.7) with a flame + real warm point light, upside-down red cup (0.55, 3.75)
(part 'cup', origin at the rim centre on the table -> lift / flip it), jug (0.1, 3.95), stack of wax tablets (-0.05, 3.42).
Bunk beds along the right wall: back bunk x 3.0..3.8, y 5.0..6.8 (two tiers, plaid wool blankets); bunks=2 adds a
front bunk at y 0.4..2.2.  Weapon rack on the back wall: oval shield (x -1.7), two spears (x -0.55, -0.3), bronze helmet
(x 0.6).  Small stone-ring hearth with glowing embers at (2.6, 5.2) (story adds fire fx at z 0.35) + orange point light.
Wooden door in the left wall, centre (-4, 4.2), opening y 3.45..4.95, height 2.6.  Part 'door' = hinge empty on the back
jamb (y 4.95): rotation Z = 0 closed, positive swings the leaf into the room (default 70 deg).
Outside the door: moonlit yard (blue ground, opposite barrack block, glowing night sky) + blue moon point light.
Acting area kept clear around (0, 3): Atto at (-0.9, 2.9), centurion at (1.5, 3.3).
Uses its own Random(seed), not the shared `random`."""
import math
import random
import bpy
import bmesh
from core import ctx
from core.look import pbr, flat, ramp_mat, warm_top, MATS
from core.geo import cube, rbox, cyl, sphere, cone, torus, lathe, group3d, attach, keep_hidden

PFX = "barrack_room"
TABLE_Z = 0.9
BOX_F = ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))

DEFAULTS = dict(name="barrack", origin=[0.0, 0.0], wall_color=[0.70, 0.55, 0.32], door_open=70.0,
                lamp_on=True, lamp_light=60.0, embers=True, hearth_light=120.0, moon_light=500.0,
                moon_color=[0.06, 0.16, 0.42], bunks=2,
                blanket_colors=[[0.55, 0.08, 0.05], [0.85, 0.58, 0.12]],
                blanket2_colors=[[0.06, 0.20, 0.32], [0.80, 0.70, 0.45]],
                shield_color=[0.62, 0.06, 0.04], cup_color=[0.60, 0.13, 0.04], seed=3)


# ---------------- helpers ----------------
def _rgb(v, fb):
    try:
        c = [float(x) for x in list(v)[:3]]
        if len(c) == 3:
            return tuple(max(0.0, min(1.0, x)) for x in c)
    except Exception:
        pass
    return tuple(fb)


def _tag(c):
    return "%.2f_%.2f_%.2f" % tuple(c)


def _boxes(name, boxes, mats):
    """many axis-aligned boxes in ONE mesh: box = (x0, x1, y0, y1, z0, z1[, mat_idx])"""
    bm = bmesh.new()
    for bx in boxes:
        x0, x1, y0, y1, z0, z1 = bx[:6]
        mi = bx[6] if len(bx) > 6 else 0
        if x1 - x0 < 1e-4 or y1 - y0 < 1e-4 or z1 - z0 < 1e-4:
            continue
        vs = []
        for z in (z0, z1):
            for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
                vs.append(bm.verts.new((x, y, z)))
        for f in BOX_F:
            bm.faces.new([vs[i] for i in f]).material_index = mi
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for m in mats:
        me.materials.append(m)
    o = bpy.data.objects.new(name, me); ctx.col.objects.link(o)
    return o


def _light(name, kind, energy, color, soft, loc, parent=None):
    ld = bpy.data.lights.new(name, kind)
    ld.energy = float(energy); ld.color = color; ld.shadow_soft_size = soft
    lo = bpy.data.objects.new(name, ld); ctx.col.objects.link(lo)
    lo.parent = parent; lo.location = loc
    return lo


def _plaid(name, base, stripe, scale=4.0, width=0.28):
    """wool check: stripes along local X and Y (object coords), crossings darker"""
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; n = nt.nodes; L = nt.links
    b = n["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.95
    tc = n.new("ShaderNodeTexCoord")
    sep = n.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Object"], sep.inputs[0])
    masks = []
    for i in (0, 1):
        mul = n.new("ShaderNodeMath"); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = scale
        L.new(sep.outputs[i], mul.inputs[0])
        fr = n.new("ShaderNodeMath"); fr.operation = 'FRACT'; L.new(mul.outputs[0], fr.inputs[0])
        lt = n.new("ShaderNodeMath"); lt.operation = 'LESS_THAN'; lt.inputs[1].default_value = width
        L.new(fr.outputs[0], lt.inputs[0])
        masks.append(lt)
    add = n.new("ShaderNodeMath"); add.operation = 'ADD'
    L.new(masks[0].outputs[0], add.inputs[0]); L.new(masks[1].outputs[0], add.inputs[1])
    half = n.new("ShaderNodeMath"); half.operation = 'MULTIPLY'; half.inputs[1].default_value = 0.5
    L.new(add.outputs[0], half.inputs[0])
    cr = n.new("ShaderNodeValToRGB"); cr.color_ramp.interpolation = 'CONSTANT'
    els = cr.color_ramp.elements
    els[0].position, els[0].color = 0.0, (*base, 1)
    els[1].position, els[1].color = 0.4, (*stripe, 1)
    e = els.new(0.9); e.color = (base[0] * 0.45, base[1] * 0.45, base[2] * 0.45, 1)
    L.new(half.outputs[0], cr.inputs[0]); L.new(cr.outputs[0], b.inputs["Base Color"])
    MATS[name] = m
    return m


# ---------------- build ----------------
def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    N = str(p.get("name") or "barrack")
    rnd = random.Random(int(p.get("seed", 3)))
    org = list(p.get("origin") or [0.0, 0.0]) + [0.0, 0.0]
    ox, oy = float(org[0]), float(org[1])

    def P(x, y, z=0.0):
        return (ox + x, oy + y, z)

    def B(x0, x1, y0, y1, z0, z1, mi=0):
        return (ox + x0, ox + x1, oy + y0, oy + y1, z0, z1, mi)

    parts, anchors, noline = {}, {}, []

    # ---- materials ----
    wc = _rgb(p.get("wall_color"), DEFAULTS["wall_color"])
    wash = warm_top(ramp_mat(f"{PFX}_wash_{_tag(wc)}",
                             [(0.2, (wc[0] * 0.86, wc[1] * 0.84, wc[2] * 0.80)), (0.55, wc),
                              (0.85, (wc[0] * 0.94, wc[1] * 0.86, wc[2] * 0.70))],
                             scale=1.2, coord="Position", bump=0.15, rough=0.95))
    dado = pbr(f"{PFX}_dado_{_tag(wc)}", (wc[0] * 0.55, wc[1] * 0.47, wc[2] * 0.40), rough=0.95)
    dirt = warm_top(ramp_mat(f"{PFX}_floor", [(0.2, (0.30, 0.19, 0.09)), (0.6, (0.40, 0.27, 0.13)), (0.9, (0.46, 0.32, 0.16))],
                             scale=1.5, coord="Position", bump=0.2, rough=0.95))
    wood = warm_top(ramp_mat(f"{PFX}_wood", [(0.2, (0.30, 0.16, 0.06)), (0.6, (0.42, 0.24, 0.10)), (0.9, (0.50, 0.30, 0.13))],
                             tex="wave", wave_dir='X', scale=3.0, coord="Object", distortion=1.0, detail=2.0, bump=0.2))
    wood_dark = warm_top(ramp_mat(f"{PFX}_wood_dark", [(0.2, (0.16, 0.08, 0.03)), (0.6, (0.24, 0.13, 0.05)),
                                                      (0.9, (0.30, 0.17, 0.07))],
                                  tex="wave", wave_dir='X', scale=2.5, coord="Object", distortion=1.0, detail=2.0, bump=0.2))
    ceil = pbr(f"{PFX}_ceiling", (0.14, 0.08, 0.04), rough=0.95)
    terracotta = warm_top(pbr(f"{PFX}_terracotta", (0.62, 0.26, 0.10), rough=0.7))
    cc = _rgb(p.get("cup_color"), DEFAULTS["cup_color"])
    cupm = warm_top(pbr(f"{PFX}_cup_{_tag(cc)}", cc, rough=0.4))
    buff = warm_top(pbr(f"{PFX}_jug", (0.70, 0.46, 0.24), rough=0.75))
    iron = pbr(f"{PFX}_iron", (0.08, 0.08, 0.09), rough=0.45, metal=0.85)
    bronze = pbr(f"{PFX}_bronze", (0.80, 0.52, 0.20), rough=0.35, metal=0.85)
    stone = warm_top(ramp_mat(f"{PFX}_hearth_stone", [(0.2, (0.24, 0.21, 0.17)), (0.6, (0.36, 0.32, 0.26)),
                                                      (0.9, (0.46, 0.41, 0.33))],
                              scale=6.0, coord="Position", bump=0.3, voronoi=True))
    ash = pbr(f"{PFX}_ash", (0.10, 0.09, 0.08), rough=1.0)
    coal = pbr(f"{PFX}_coal", (0.05, 0.04, 0.035), rough=0.9)
    ember = flat(f"{PFX}_ember", (0.85, 0.18, 0.02))
    ember_hot = flat(f"{PFX}_ember_hot", (1.0, 0.42, 0.05))
    flame = flat(f"{PFX}_flame", (1.0, 0.62, 0.14))
    wax = pbr(f"{PFX}_wax", (0.10, 0.07, 0.03), rough=0.5)
    tablet_w = warm_top(pbr(f"{PFX}_tablet", (0.58, 0.38, 0.17), rough=0.8))
    mattress = warm_top(pbr(f"{PFX}_mattress", (0.62, 0.50, 0.32), rough=1.0))
    pillow = warm_top(pbr(f"{PFX}_pillow", (0.74, 0.63, 0.45), rough=1.0))
    bc1 = list(p.get("blanket_colors") or DEFAULTS["blanket_colors"]) + DEFAULTS["blanket_colors"]
    bc2 = list(p.get("blanket2_colors") or DEFAULTS["blanket2_colors"]) + DEFAULTS["blanket2_colors"]
    b1a, b1b = _rgb(bc1[0], DEFAULTS["blanket_colors"][0]), _rgb(bc1[1], DEFAULTS["blanket_colors"][1])
    b2a, b2b = _rgb(bc2[0], DEFAULTS["blanket2_colors"][0]), _rgb(bc2[1], DEFAULTS["blanket2_colors"][1])
    plaid1 = warm_top(_plaid(f"{PFX}_plaid_{_tag(b1a)}_{_tag(b1b)}", b1a, b1b))
    plaid2 = warm_top(_plaid(f"{PFX}_plaid_{_tag(b2a)}_{_tag(b2b)}", b2a, b2b))
    sc = _rgb(p.get("shield_color"), DEFAULTS["shield_color"])
    shield_face = pbr(f"{PFX}_shield_{_tag(sc)}", sc, rough=0.5)
    shield_rim = pbr(f"{PFX}_shield_rim", (0.85, 0.60, 0.08), rough=0.4, metal=0.6)
    mc = _rgb(p.get("moon_color"), DEFAULTS["moon_color"])
    moon_sky = flat(f"{PFX}_moon_sky_{_tag(mc)}", mc)
    moon_ground = pbr(f"{PFX}_moon_ground", (0.10, 0.13, 0.20), rough=1.0)
    moon_wall = pbr(f"{PFX}_moon_wall", (0.16, 0.18, 0.27), rough=0.95)
    moon_roof = pbr(f"{PFX}_moon_roof", (0.10, 0.07, 0.10), rough=0.8)

    # ---- PART walls: shell + floor + beams + door frame ----
    H = 4.8
    wb = [
        B(-4.3, 4.3, 7.0, 7.3, 0.0, H),                       # back wall
        B(4.0, 4.3, -2.0, 7.0, 0.0, H),                       # right wall
        B(-4.3, -4.0, -2.0, 3.45, 0.0, H),                    # left wall, front of the door
        B(-4.3, -4.0, 4.95, 7.0, 0.0, H),                     # left wall, behind the door
        B(-4.3, -4.0, 3.45, 4.95, 2.8, H),                    # above the lintel
        # dirty dado band (the "stained" lower wall)
        B(-4.0, 4.0, 6.97, 7.0, 0.0, 0.9, 1),
        B(3.97, 4.0, -2.0, 6.97, 0.0, 0.9, 1),
        B(-4.0, -3.97, -2.0, 3.33, 0.0, 0.9, 1),
        B(-4.0, -3.97, 5.07, 6.97, 0.0, 0.9, 1),
        B(-4.3, 4.3, -2.0, 7.3, 4.75, 4.9, 2),                # plank ceiling (above the beams)
    ]
    shell = _boxes(f"{N}_walls_shell", wb, [wash, dado, ceil])
    floor = _boxes(f"{N}_walls_floor", [B(-4.0, 4.0, -3.0, 7.0, -0.1, 0.0),
                                        B(-4.3, -4.0, 3.45, 4.95, -0.1, 0.0)], [dirt])
    noline.append(floor)
    bb = [B(-4.0, 4.0, yb - 0.13, yb + 0.13, 4.37, 4.63) for yb in (-1.0, 1.0, 3.0, 5.0, 6.85)]
    beams = _boxes(f"{N}_walls_beams", bb, [wood_dark])
    frame = _boxes(f"{N}_walls_doorframe", [B(-4.34, -3.95, 3.33, 3.45, 0.0, 2.6),
                                            B(-4.34, -3.95, 4.95, 5.07, 0.0, 2.6),
                                            B(-4.34, -3.95, 3.33, 5.07, 2.6, 2.8),
                                            B(-4.34, -3.95, 3.45, 4.95, 0.0, 0.04)], [wood_dark])
    walls = group3d(f"{N}_walls")
    attach(walls, shell, floor, beams, frame)
    parts["walls"] = walls

    # ---- PART outside: moonlit yard seen through the door ----
    out = group3d(f"{N}_outside")
    yard = _boxes(f"{N}_outside_yard", [B(-14.0, -4.3, -4.0, 26.0, -0.1, -0.01)], [moon_ground])
    block = _boxes(f"{N}_outside_block", [B(-9.0, -8.2, -4.0, 26.0, 0.0, 3.4, 0),
                                          B(-9.3, -7.9, -4.0, 26.0, 3.4, 3.65, 1)], [moon_wall, moon_roof])
    doors_far = _boxes(f"{N}_outside_doors", [B(-8.24, -8.19, yd - 0.6, yd + 0.6, 0.0, 2.3) for yd in (6.0, 11.0, 16.0)],
                       [moon_roof])
    sky = _boxes(f"{N}_outside_sky", [B(-12.2, -12.0, -6.0, 30.0, -1.0, 14.0)], [moon_sky])
    noline += [yard, sky]
    attach(out, yard, block, doors_far, sky)
    if p.get("moon_light", 0) and float(p["moon_light"]) > 0:
        _light(f"{N}_outside_moon", 'POINT', p["moon_light"], (0.45, 0.60, 1.0), 1.0, P(-6.5, 4.2, 3.0), None)
    parts["outside"] = out

    # ---- PART table (+ stool) : root at the table centre on the floor ----
    table = group3d(f"{N}_table", P(0.0, 3.6, 0.0))
    tk = [rbox(f"{N}_table_top", (0.0, 0.0, TABLE_Z - 0.04), (1.6, 0.8, 0.08), wood, radius=0.02)]
    for dx in (-0.68, 0.68):
        for dy in (-0.31, 0.31):
            tk.append(cube(f"{N}_table_leg", (dx, dy, (TABLE_Z - 0.08) / 2), (0.09, 0.09, TABLE_Z - 0.08), wood))
    tk.append(cube(f"{N}_table_stretcher", (0.0, 0.0, 0.22), (1.36, 0.06, 0.06), wood))
    tk.append(cyl(f"{N}_table_stool_seat", (0.3, 0.95, 0.5), 0.22, 0.06, wood, 20))
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.3
        tk.append(cyl(f"{N}_table_stool_leg{k}", (0.3 + 0.14 * math.cos(a), 0.95 + 0.14 * math.sin(a), 0.235),
                      0.03, 0.47, wood, 8))
    attach(table, *tk)
    parts["table"] = table

    # ---- PART lamp: terracotta oil lamp, nozzle toward +X, flame + warm point light ----
    lamp = group3d(f"{N}_lamp", P(-0.5, 3.7, TABLE_Z))
    lk = [lathe(f"{N}_lamp_body", (0, 0, 0), [(0.0, 0.0), (0.08, 0.0), (0.12, 0.03), (0.12, 0.06), (0.07, 0.085),
                                               (0.035, 0.09), (0.035, 0.105), (0.0, 0.105)], terracotta, segments=24),
          sphere(f"{N}_lamp_nozzle", (0.15, 0.0, 0.05), 0.06, terracotta, scale=(1.4, 0.8, 0.55)),
          torus(f"{N}_lamp_handle", (-0.13, 0.0, 0.08), 0.045, 0.02, terracotta, rot=(math.pi / 2, 0, 0),
                major_seg=16, minor_seg=8)]
    fl = sphere(f"{N}_lamp_flame", (0.22, 0.0, 0.12), 0.045, flame, scale=(0.8, 0.8, 1.7))
    noline.append(fl)
    attach(lamp, *lk, fl)
    if p.get("lamp_on", True):
        if p.get("lamp_light", 0) and float(p["lamp_light"]) > 0:
            _light(f"{N}_lamp_light", 'POINT', p["lamp_light"], (1.0, 0.72, 0.42), 0.1, (0.22, 0.0, 0.3), lamp)
    else:
        keep_hidden(fl, True)
    parts["lamp"] = lamp
    parts["lamp_flame"] = fl

    # ---- PART cup: upside-down cup, origin = rim centre on the table (lift / flip it) ----
    cup = lathe(f"{N}_cup", P(0.55, 3.75, TABLE_Z),
                [(0.0, 0.0), (0.11, 0.0), (0.115, 0.02), (0.10, 0.16), (0.075, 0.2), (0.08, 0.21), (0.08, 0.24),
                 (0.0, 0.24)], cupm, segments=28)
    parts["cup"] = cup

    # ---- PART jug ----
    jug = group3d(f"{N}_jug", P(0.1, 3.95, TABLE_Z))
    attach(jug,
           lathe(f"{N}_jug_body", (0, 0, 0), [(0.0, 0.0), (0.09, 0.0), (0.14, 0.08), (0.15, 0.18), (0.12, 0.28),
                                               (0.06, 0.34), (0.05, 0.40), (0.07, 0.43), (0.0, 0.43)], buff, segments=24),
           torus(f"{N}_jug_handle", (-0.11, 0.0, 0.30), 0.075, 0.022, buff, rot=(math.pi / 2, 0, 0),
                 major_seg=16, minor_seg=8))
    parts["jug"] = jug

    # ---- PART tablets: small stack of wooden writing tablets ----
    tabs = group3d(f"{N}_tablets", P(-0.05, 3.42, TABLE_Z))
    tl = []
    for k, rz in enumerate((0.0, 0.12, -0.08)):
        t = rbox(f"{N}_tablets_{k}", (0.0, 0.0, 0.015 + 0.032 * k), (0.30, 0.20, 0.03), tablet_w, radius=0.008)
        t.rotation_euler = (0.0, 0.0, rz)
        tl.append(t)
    w_ = cube(f"{N}_tablets_wax", (0.0, 0.0, 0.0805), (0.24, 0.14, 0.004), wax)
    w_.rotation_euler = (0.0, 0.0, -0.08)
    attach(tabs, *tl, w_)
    parts["tablets"] = tabs

    # ---- PART bunks: two-tier wooden bunk beds along the right wall ----
    bunks = group3d(f"{N}_bunks")

    def bunk(tag, cx, cy, plaid):
        g = group3d(f"{N}_bunk_{tag}", P(cx, cy, 0.0), parent=bunks)
        k = []
        for dx in (-0.36, 0.36):
            for dy in (-0.86, 0.86):
                k.append(cube(f"{N}_bunk_{tag}_post", (dx, dy, 1.05), (0.1, 0.1, 2.1), wood))
        for i, z in enumerate((0.42, 1.42)):
            for dx in (-0.36, 0.36):
                k.append(cube(f"{N}_bunk_{tag}_rail{i}", (dx, 0.0, z), (0.06, 1.8, 0.12), wood))
            for dy in (-0.86, 0.86):
                k.append(cube(f"{N}_bunk_{tag}_end{i}", (0.0, dy, z), (0.8, 0.06, 0.12), wood))
            k.append(cube(f"{N}_bunk_{tag}_deck{i}", (0.0, 0.0, z + 0.04), (0.66, 1.66, 0.04), wood))
            k.append(rbox(f"{N}_bunk_{tag}_mattress{i}", (0.0, 0.0, z + 0.13), (0.70, 1.68, 0.14), mattress, radius=0.05))
            k.append(rbox(f"{N}_bunk_{tag}_blanket{i}", (0.0, -0.27, z + 0.15), (0.78, 1.25, 0.2), plaid, radius=0.05))
            k.append(rbox(f"{N}_bunk_{tag}_pillow{i}", (0.0, 0.62, z + 0.26), (0.55, 0.30, 0.12), pillow, radius=0.05))
        k.append(cube(f"{N}_bunk_{tag}_guard", (-0.36, 0.0, 1.78), (0.06, 1.8, 0.08), wood))
        attach(g, *k)
        return g

    parts["bunk_back"] = bunk("back", 3.4, 5.9, plaid1)
    if int(p.get("bunks", 2)) >= 2:
        parts["bunk_front"] = bunk("front", 3.4, 1.3, plaid2)
    parts["bunks"] = bunks

    # ---- PART rack: weapon rack on the back wall ----
    rack = group3d(f"{N}_rack", P(-0.7, 6.92, 0.0))
    rk = [cube(f"{N}_rack_board", (-0.3, 0.0, 2.75), (3.4, 0.1, 0.18), wood_dark)]
    for k, px in enumerate((-1.0, 0.27, 1.3)):
        rk.append(cyl(f"{N}_rack_peg{k}", (px, -0.12, 2.72), 0.04, 0.25, wood, 10, rot=(math.pi / 2, 0, 0)))
    # oval shield (x -1.7 world)
    rk += [sphere(f"{N}_rack_shield_rim", (-1.0, -0.10, 1.75), 1.0, shield_rim, scale=(0.52, 0.06, 0.68)),
           sphere(f"{N}_rack_shield", (-1.0, -0.12, 1.75), 1.0, shield_face, scale=(0.47, 0.065, 0.63)),
           cube(f"{N}_rack_shield_spine", (-1.0, -0.17, 1.75), (0.08, 0.04, 1.05), shield_rim),
           sphere(f"{N}_rack_shield_boss", (-1.0, -0.19, 1.75), 0.14, bronze, scale=(1.0, 0.6, 1.0))]
    # two spears in a bracket (x -0.55, -0.3 world)
    rk.append(cube(f"{N}_rack_bracket", (0.27, -0.08, 2.0), (0.6, 0.12, 0.06), wood_dark))
    for k, sx in enumerate((0.15, 0.4)):
        rk += [cyl(f"{N}_rack_spear{k}", (sx, -0.16, 1.33), 0.03, 2.55, wood, 10),
               cone(f"{N}_rack_spear{k}_tip", (sx, -0.16, 2.75), 0.06, 0.0, 0.3, iron, 12),
               cone(f"{N}_rack_spear{k}_butt", (sx, -0.16, 0.08), 0.0, 0.035, 0.1, iron, 10)]
    # bronze helmet on a peg (x 0.6 world)
    rk += [sphere(f"{N}_rack_helmet", (1.3, -0.24, 2.42), 0.24, bronze, scale=(1.0, 1.0, 0.9)),
           torus(f"{N}_rack_helmet_brim", (1.3, -0.24, 2.27), 0.24, 0.035, bronze, major_seg=24, minor_seg=8),
           rbox(f"{N}_rack_helmet_cheekL", (1.1, -0.30, 2.15), (0.06, 0.18, 0.24), bronze, radius=0.02),
           rbox(f"{N}_rack_helmet_cheekR", (1.5, -0.30, 2.15), (0.06, 0.18, 0.24), bronze, radius=0.02),
           sphere(f"{N}_rack_helmet_knob", (1.3, -0.24, 2.66), 0.05, bronze)]
    attach(rack, *rk)
    parts["rack"] = rack

    # ---- PART hearth: stone ring + embers + orange light ----
    hearth = group3d(f"{N}_hearth", P(2.6, 5.2, 0.0))
    hk = []
    for k in range(9):
        a = 2 * math.pi * k / 9 + rnd.uniform(-0.1, 0.1)
        r = 0.30 + rnd.uniform(-0.02, 0.02)
        st = sphere(f"{N}_hearth_stone{k}", (r * math.cos(a), r * math.sin(a), 0.07), 0.11 + rnd.uniform(-0.01, 0.02),
                    stone, scale=(1.0, 0.85, 0.7))
        st.rotation_euler = (0.0, 0.0, a)
        hk.append(st)
    hk.append(cyl(f"{N}_hearth_ash", (0.0, 0.0, 0.03), 0.27, 0.06, ash, 20))
    glow = []
    on = bool(p.get("embers", True))
    for k in range(9):
        a = rnd.uniform(0, 2 * math.pi); r = rnd.uniform(0.0, 0.17)
        m = (ember_hot if k % 3 == 0 else ember) if on else coal
        e = sphere(f"{N}_hearth_ember{k}", (r * math.cos(a), r * math.sin(a), 0.09 + rnd.uniform(0.0, 0.04)),
                   rnd.uniform(0.05, 0.08), m, scale=(1.0, 1.0, 0.6))
        glow.append(e)
    for k in range(4):
        a = rnd.uniform(0, 2 * math.pi); r = rnd.uniform(0.05, 0.18)
        hk.append(sphere(f"{N}_hearth_coal{k}", (r * math.cos(a), r * math.sin(a), 0.1), 0.06, coal, scale=(1.2, 0.9, 0.6)))
    if on:
        noline.extend(glow)
    attach(hearth, *hk, *glow)
    if on and p.get("hearth_light", 0) and float(p["hearth_light"]) > 0:
        _light(f"{N}_hearth_light", 'POINT', p["hearth_light"], (1.0, 0.45, 0.15), 0.3, (0.0, 0.0, 0.6), hearth)
    parts["hearth"] = hearth

    # ---- PART door: hinge on the back jamb (y 4.95), leaf extends to -Y; rot Z + swings into the room ----
    door = group3d(f"{N}_door", P(-4.04, 4.94, 0.0))
    brace_len = math.hypot(1.2, 1.5)
    brace = cube(f"{N}_door_brace", (0.06, -0.73, 1.25), (0.04, 0.12, brace_len), wood)
    brace.rotation_euler = (math.atan2(1.2, 1.5), 0.0, 0.0)
    attach(door,
           cube(f"{N}_door_leaf", (0.0, -0.74, 1.28), (0.08, 1.44, 2.54), wood_dark),
           cube(f"{N}_door_batten0", (0.06, -0.74, 0.45), (0.04, 1.32, 0.14), wood),
           cube(f"{N}_door_batten1", (0.06, -0.74, 2.1), (0.04, 1.32, 0.14), wood),
           brace,
           torus(f"{N}_door_ring", (0.1, -1.25, 1.2), 0.07, 0.02, iron, rot=(0.0, math.pi / 2, 0.0),
                 major_seg=16, minor_seg=8))
    door.rotation_euler = (0.0, 0.0, math.radians(float(p.get("door_open", 70.0))))
    parts["door"] = door

    # ---- PART chest: iron-banded chest in the back-left corner ----
    chest = group3d(f"{N}_chest", P(-3.4, 6.3, 0.0))
    attach(chest,
           rbox(f"{N}_chest_box", (0.0, 0.0, 0.25), (0.55, 1.0, 0.5), wood, radius=0.03),
           rbox(f"{N}_chest_lid", (0.0, 0.0, 0.54), (0.6, 1.05, 0.1), wood_dark, radius=0.03),
           cube(f"{N}_chest_band0", (0.0, -0.3, 0.3), (0.6, 0.05, 0.62), iron),
           cube(f"{N}_chest_band1", (0.0, 0.3, 0.3), (0.6, 0.05, 0.62), iron))
    parts["chest"] = chest

    # ---- anchors ----
    anchors["table"] = [ox, oy + 3.6, TABLE_Z]
    anchors["cup"] = [ox + 0.55, oy + 3.75, TABLE_Z]
    anchors["lamp"] = [ox - 0.5, oy + 3.7, TABLE_Z + 0.12]
    anchors["bunk"] = [ox + 3.4, oy + 5.9, 0.62]
    anchors["hearth"] = [ox + 2.6, oy + 5.2, 0.35]
    anchors["door"] = [ox - 4.0, oy + 4.2, 0.0]
    anchors["center"] = [ox, oy + 3.0, 0.0]
    anchors["rack"] = [ox - 0.7, oy + 6.8, 2.0]
    anchors["shield"] = [ox - 1.7, oy + 6.75, 1.75]
    anchors["atto"] = [ox - 0.9, oy + 2.9, 0.0]
    anchors["centurion"] = [ox + 1.5, oy + 3.3, 0.0]
    if "bunk_front" in parts:
        anchors["bunk_front"] = [ox + 3.4, oy + 1.3, 0.62]

    return {"parts": parts, "anchors": anchors, "noline": noline}
