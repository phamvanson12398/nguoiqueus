"""American supermarket parking lot at dusk (7 pm, orange-to-purple sky, pole lamps just switched on).
Open toward -Y: the camera stands at -Y looking +Y.  All positions are relative to `origin` [x, y]; asphalt top z = 0.

Acting area: STAGE = (0, 4), kept clear x -2.4..2.4, y -3..4.9 (2-3 characters side by side facing -Y).
Hero hatchback right behind them: centre (0.6, 6.4), long axis along X, nose toward -X, so the DRIVER side faces the
camera; body side face at y ~5.2, roof z ~2.15, length 5.1 (x -1.95..3.15).  Driver door (part 'car_door') = hinge
empty at the door's front edge (x -0.45, y 5.16): rotation Z NEGATIVE swings it open toward the camera.
Dim glowing windows (part 'car_glass' = group of the side panes that are not on the door).
Painted stall lines (white) around the hero car (y 4.9 / 7.9) and two far rows of nose-in stalls (y 15, y 23) with
parked cars.  Planters with a tree at x -5.5 and x +6.0 (y 6.4) frame the shot.  Stray shopping cart (part 'cart') at
(-4.2, 9.2).  Six light poles (h 8.5) with warm spot lights (part 'lamps' = every glowing lamp face + its light:
hide/show it to switch the lot lights on).  Store facade front y 34 (entrance block front 32.7), lit glass doors
(part 'store_glass'), green awning, glowing 3D sign 'MARKET' (part 'sign') at z ~6.6, cart corral at x -10.
Sky backdrop: a vertical arc (radius 95 around the stage) with an emission gradient, low sun disc + tree silhouettes;
sky='night' adds stars + moon, sky='day' is blue.  The world/sun still come from the story's `world`.
Uses its own Random(seed), not the shared `random`."""
import math
import random
import bpy
import bmesh
from core import ctx
from core.look import flat, pbr, ramp_mat, warm_top, MATS
from core.geo import cube, rbox, cyl, sphere, extrude, text3d, group3d, attach

PFX = "parking_lot"
STAGE = (0.0, 4.0)
CAR_AT = (0.6, 6.4)
CAR_W = 2.3

DEFAULTS = dict(
    name="parking_lot",
    origin=[0.0, 0.0],
    car_color=[0.80, 0.06, 0.05],
    sky="dusk",
    lamps_on=True,
    lamp_light=900.0,
    door_open=0.0,
    window_glow=[0.34, 0.30, 0.46],
    sign_text="MARKET",
    store_color=[0.82, 0.66, 0.48],
    store_accent=[0.05, 0.40, 0.20],
    far_cars=True,
    seed=5,
)

SKIES = {
    "dusk": [(0.0, (1.0, 0.58, 0.18)), (0.05, (1.0, 0.38, 0.12)), (0.14, (0.88, 0.24, 0.36)),
             (0.30, (0.45, 0.15, 0.52)), (0.58, (0.16, 0.08, 0.36)), (1.0, (0.05, 0.04, 0.16))],
    "night": [(0.0, (0.12, 0.08, 0.22)), (0.15, (0.05, 0.05, 0.16)), (0.5, (0.02, 0.02, 0.08)), (1.0, (0.01, 0.01, 0.03))],
    "day": [(0.0, (0.98, 0.86, 0.72)), (0.2, (0.62, 0.80, 0.98)), (1.0, (0.16, 0.42, 0.90))],
}
SILHOUETTE = {"dusk": (0.10, 0.05, 0.13), "night": (0.015, 0.015, 0.03), "day": (0.18, 0.36, 0.20)}

# car side profiles (x, z), nose toward -X
BODY = [(-2.55, 0.62), (-2.45, 0.42), (2.45, 0.42), (2.55, 0.62), (2.55, 1.2), (2.35, 1.32),
        (-1.0, 1.34), (-2.3, 1.14), (-2.55, 0.92)]
CABIN = [(-1.15, 1.25), (2.25, 1.25), (2.2, 1.75), (1.9, 2.05), (-0.15, 2.08), (-1.15, 1.3)]
PANE_FRONT = [(-0.85, 1.4), (0.45, 1.4), (0.45, 1.93), (-0.12, 1.95)]
PANE_REAR = [(0.62, 1.4), (1.98, 1.4), (1.82, 1.9), (0.62, 1.93)]


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


def _no_shadow(o):
    try:
        o.visible_shadow = False
    except AttributeError:
        pass
    return o


def _quads(name, rects, z, m):
    """many flat rectangles (x0, x1, y0, y1) in ONE mesh at height z (paint on the asphalt)"""
    bm = bmesh.new()
    for x0, x1, y0, y1 in rects:
        vs = [bm.verts.new((x, y, z)) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
        bm.faces.new(vs)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); ctx.col.objects.link(o)
    me.materials.append(m)
    return o


def _grad_mat(name, stops, zmax):
    """emission gradient by object-space height (sky backdrop)"""
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear(); L = nt.links
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Object"], sep.inputs[0])
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs[1].default_value = 0.0; mr.inputs[2].default_value = zmax
    L.new(sep.outputs[2], mr.inputs[0])
    cr = nt.nodes.new("ShaderNodeValToRGB"); els = cr.color_ramp.elements
    els[0].position, els[0].color = stops[0][0], (*stops[0][1], 1)
    els[1].position, els[1].color = stops[-1][0], (*stops[-1][1], 1)
    for ps, c in stops[1:-1]:
        e = els.new(ps); e.color = (*c, 1)
    L.new(mr.outputs[0], cr.inputs[0])
    em = nt.nodes.new("ShaderNodeEmission"); L.new(cr.outputs[0], em.inputs[0])
    out = nt.nodes.new("ShaderNodeOutputMaterial"); L.new(em.outputs[0], out.inputs[0])
    MATS[name] = m
    return m


def _sky_arc(name, loc, radius, z0, z1, a0, a1, m, seg=56):
    bm = bmesh.new()
    cols = []
    for i in range(seg + 1):
        a = math.radians(a0 + (a1 - a0) * i / seg)
        x, y = radius * math.cos(a), radius * math.sin(a)
        cols.append((bm.verts.new((x, y, z0)), bm.verts.new((x, y, z1))))
    for (b0, t0), (b1, t1) in zip(cols, cols[1:]):
        bm.faces.new((b0, b1, t1, t0))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); ctx.col.objects.link(o)
    me.materials.append(m); o.location = loc
    return _no_shadow(o)


def _light(name, kind, energy, color, loc, parent=None, size=None, blend=0.6, soft=0.4):
    ld = bpy.data.lights.new(name, kind)
    ld.energy = float(energy); ld.color = color; ld.shadow_soft_size = soft
    if kind == 'SPOT':
        ld.spot_size = math.radians(size or 110); ld.spot_blend = blend
    lo = bpy.data.objects.new(name, ld); ctx.col.objects.link(lo)
    lo.parent = parent; lo.location = loc
    return lo


# ---------------- hatchback ----------------
def _car(nm, color, loc, rz, glass_m, mats, detail=True, door_open=0.0):
    """hatchback, root at the centre of its footprint on the ground, nose toward local -X.
    Returns (root, door_hinge or None, glass_group or None)."""
    W = CAR_W
    paint = pbr(f"{PFX}_paint_{_tag(color)}", color, rough=0.32)
    root = group3d(nm, loc)
    up = (math.pi / 2, 0, 0)
    objs = [extrude(f"{nm}_body", (0, 0, 0), BODY, W, paint, bevel=0.06, rot=up),
            extrude(f"{nm}_cabin", (0, 0, 0), CABIN, W - 0.3, paint, bevel=0.06, rot=up)]
    ws = rbox(f"{nm}_windshield", (-0.65 - 0.615 * 0.07, 0, 1.69 + 0.789 * 0.07), (1.15, W - 0.55, 0.03), mats["glass_dark"], radius=0.01)
    ws.rotation_euler = (0, -0.661, 0)
    objs.append(ws)
    objs.append(rbox(f"{nm}_rear_glass", (2.30, 0, 1.56), (0.03, W - 0.6, 0.42), mats["glass_dark"], radius=0.01))
    yp = (W - 0.3) / 2 + 0.08                                  # cabin side face (+bevel)
    yb = W / 2 + 0.06                                          # body side face (+bevel)
    for s in (-1, 1):
        for x in (-1.6, 1.6):
            objs.append(cyl(f"{nm}_arch{'LR'[s > 0]}{'FB'[x > 0]}", (x, s * (yb - 0.005), 0.45), 0.56, 0.02, mats["arch"], 32, rot=up))
            objs.append(cyl(f"{nm}_tyre{'LR'[s > 0]}{'FB'[x > 0]}", (x, s * (yb - 0.1), 0.44), 0.44, 0.24, mats["tyre"], 32, rot=up))
            objs.append(cyl(f"{nm}_hub{'LR'[s > 0]}{'FB'[x > 0]}", (x, s * (yb + 0.025), 0.44), 0.22, 0.02, mats["hub"], 24, rot=up))
        objs.append(rbox(f"{nm}_head{'LR'[s > 0]}", (-2.6, s * 0.72, 0.95), (0.14, 0.45, 0.17), mats["headlight"], radius=0.03))
        objs.append(rbox(f"{nm}_tail{'LR'[s > 0]}", (2.6, s * 0.85, 1.02), (0.1, 0.3, 0.32), mats["taillight"], radius=0.03))
    objs.append(rbox(f"{nm}_bumper_front", (-2.58, 0, 0.55), (0.26, W + 0.1, 0.28), mats["trim"], radius=0.06))
    objs.append(rbox(f"{nm}_bumper_rear", (2.6, 0, 0.55), (0.26, W + 0.1, 0.28), mats["trim"], radius=0.06))
    attach(root, *objs)

    glass = group3d(f"{nm}_glass")
    panes = [extrude(f"{nm}_pane_far_front", (0, yp, 0), PANE_FRONT, 0.02, glass_m, rot=up),
             extrude(f"{nm}_pane_far_rear", (0, yp, 0), PANE_REAR, 0.02, glass_m, rot=up),
             extrude(f"{nm}_pane_rear", (0, -yp, 0), PANE_REAR, 0.02, glass_m, rot=up)]
    attach(glass, *panes); attach(root, glass)

    hinge = None
    if detail:
        hinge = group3d(f"{nm}_door", (-1.05, -(yb + 0.03), 0))
        dx = 1.05                                               # door-local x = car x + 1.05
        door = [rbox(f"{nm}_door_panel", (0.75, 0, 0.87), (1.5, 0.05, 0.8), paint, radius=0.03),
                extrude(f"{nm}_door_pane", (0, -(yp - yb - 0.03) + 0.0, 0), [(x + dx, z) for x, z in PANE_FRONT], 0.02, glass_m, rot=up),
                rbox(f"{nm}_door_handle", (1.25, -0.05, 1.12), (0.3, 0.06, 0.07), mats["trim"], radius=0.02)]
        # pane sits on the cabin side face (y = -yp) which is behind the hinge line (y = -yb - 0.03)
        door[1].location.y = (yb + 0.03) - yp - 0.012
        attach(hinge, *door)
        hinge.rotation_euler = (0, 0, -math.radians(float(door_open)))
        attach(root, hinge)
        extra = [cube(f"{nm}_seam_rear", (1.98, -(yb + 0.005), 0.86), (0.035, 0.02, 0.8), mats["arch"]),
                 rbox(f"{nm}_handle_rear", (1.7, -(yb + 0.03), 1.12), (0.3, 0.06, 0.07), mats["trim"], radius=0.02),
                 rbox(f"{nm}_mirrorL", (-0.95, -(yp + 0.18), 1.45), (0.26, 0.24, 0.17), paint, radius=0.05),
                 rbox(f"{nm}_mirrorR", (-0.95, (yp + 0.18), 1.45), (0.26, 0.24, 0.17), paint, radius=0.05)]
        attach(root, *extra)
    else:
        attach(glass, extrude(f"{nm}_pane_front", (0, -yp, 0), PANE_FRONT, 0.02, glass_m, rot=up))
    root.rotation_euler = (0, 0, math.radians(rz))
    return root, hinge, glass


# ---------------- shopping cart ----------------
def _cart(nm, loc, rz, mats):
    root = group3d(nm, loc)
    up = (math.pi / 2, 0, 0)
    objs = [extrude(f"{nm}_basket", (0, 0, 0), [(-0.55, 0.55), (0.55, 0.55), (0.72, 1.3), (-0.62, 1.3)], 0.75, mats["wire"], bevel=0.02, rot=up),
            cube(f"{nm}_inside", (0.05, 0, 1.3), (1.2, 0.66, 0.02), mats["trim"]),
            cyl(f"{nm}_handle", (0.82, 0, 1.36), 0.05, 0.86, mats["cart_red"], 16, rot=up)]
    for x in (-0.42, 0.42):
        objs.append(cube(f"{nm}_leg{'FB'[x > 0]}", (x, 0, 0.36), (0.06, 0.6, 0.38), mats["wire"]))
        for y in (-0.3, 0.3):
            objs.append(cyl(f"{nm}_wheel{'FB'[x > 0]}{'LR'[y > 0]}", (x, y, 0.09), 0.09, 0.06, mats["tyre"], 16, rot=up))
    attach(root, *objs)
    root.rotation_euler = (0, 0, math.radians(rz))
    return root


def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    name = p.get("name") or PFX
    ox, oy = [float(v) for v in p["origin"]]
    sky = p.get("sky") if p.get("sky") in SKIES else "dusk"
    lit = bool(p.get("lamps_on", True))
    rng = random.Random(int(p.get("seed", 5)))

    def P(x, y, z=0.0):
        return (ox + x, oy + y, z)

    noline = []

    # ---------------- materials ----------------
    asphalt = ramp_mat(f"{name}_asphalt", [(0.3, (0.05, 0.05, 0.06)), (0.55, (0.075, 0.075, 0.085)), (0.8, (0.11, 0.105, 0.11))],
                       scale=5.0, bump=0.15, rough=0.85)
    paint_line = pbr(f"{name}_line", (0.85, 0.84, 0.78), rough=0.7)
    concrete = warm_top(pbr(f"{name}_concrete", (0.55, 0.52, 0.48), rough=0.85))
    wall = warm_top(pbr(f"{name}_store_wall", _rgb(p["store_color"], DEFAULTS["store_color"]), rough=0.85))
    accent = pbr(f"{name}_store_accent", _rgb(p["store_accent"], DEFAULTS["store_accent"]), rough=0.6)
    trim_dark = pbr(f"{name}_trim", (0.08, 0.08, 0.09), rough=0.5)
    pole_m = pbr(f"{name}_pole", (0.22, 0.23, 0.25), rough=0.4, metal=0.7)
    lamp_off = pbr(f"{name}_lamp_off", (0.55, 0.55, 0.52), rough=0.3)
    soil = pbr(f"{name}_soil", (0.18, 0.10, 0.05), rough=1.0)
    leaf = pbr(f"{name}_leaf", (0.10, 0.36, 0.12), rough=0.8)
    leaf2 = pbr(f"{name}_leaf_light", (0.20, 0.50, 0.14), rough=0.8)
    bark = pbr(f"{name}_bark", (0.25, 0.14, 0.07), rough=0.9)
    if sky == "day":
        shop_glass = pbr(f"{name}_shop_glass_day", (0.35, 0.50, 0.58), rough=0.1)
        car_glass = pbr(f"{name}_car_glass_day", (0.30, 0.42, 0.52), rough=0.1)
    else:
        shop_glass = flat(f"{name}_shop_glass", (1.0, 0.72, 0.30) if lit else (0.45, 0.30, 0.12))
        car_glass = flat(f"{name}_car_glass_{_tag(_rgb(p['window_glow'], DEFAULTS['window_glow']))}",
                         _rgb(p["window_glow"], DEFAULTS["window_glow"]))
    far_glass = flat(f"{name}_far_glass_{sky}", {"dusk": (0.20, 0.14, 0.28), "night": (0.05, 0.05, 0.10),
                                                 "day": (0.30, 0.42, 0.52)}[sky])
    mats = dict(
        glass_dark=pbr(f"{name}_glass_dark", (0.04, 0.05, 0.08), rough=0.12),
        arch=pbr(f"{name}_arch", (0.02, 0.02, 0.025), rough=0.8),
        tyre=pbr(f"{name}_tyre", (0.03, 0.03, 0.035), rough=0.8),
        hub=pbr(f"{name}_hub", (0.70, 0.72, 0.75), rough=0.25, metal=0.9),
        headlight=flat(f"{name}_headlight", (1.0, 0.92, 0.70)) if sky != "day" else pbr(f"{name}_headlight_day", (0.9, 0.9, 0.85), rough=0.1),
        taillight=pbr(f"{name}_taillight", (0.75, 0.04, 0.03), rough=0.25),
        trim=pbr(f"{name}_car_trim", (0.10, 0.10, 0.11), rough=0.5),
        wire=pbr(f"{name}_cart_wire", (0.62, 0.64, 0.68), rough=0.3, metal=0.85),
        cart_red=pbr(f"{name}_cart_red", (0.80, 0.08, 0.05), rough=0.4),
    )

    # ---------------- ground + paint ----------------
    g = cube(f"{name}_ground", P(0, 40, -0.1), (220, 140, 0.2), asphalt); noline.append(g)
    rects = []
    # hero stall around the car (lines along X) + its neighbours' end lines
    for y in (4.9, 7.9):
        rects.append((-9.2, 10.0, y - 0.06, y + 0.06))
    for x in (-2.6, 3.8, -8.9, 9.7):
        rects.append((x - 0.06, x + 0.06, 4.9, 7.9))
    # two far rows of nose-in stalls (lines along Y)
    for yc in (15.0, 23.0):
        for k in range(12):
            x = -17.6 + 3.2 * k
            rects.append((x - 0.06, x + 0.06, yc - 2.8, yc + 2.8))
        rects.append((-17.6, 17.6, yc - 0.06 + (2.8 if yc == 15.0 else -2.8), yc + 0.06 + (2.8 if yc == 15.0 else -2.8)))
    lines = _quads(f"{name}_lines", [(ox + a, ox + b, oy + c, oy + d) for a, b, c, d in rects], 0.006, paint_line)
    noline.append(lines)
    zebra = _quads(f"{name}_crosswalk", [(ox + x - 0.35, ox + x + 0.35, oy + 27.2, oy + 30.4) for x in [-4.8 + 1.2 * i for i in range(9)]],
                   0.006, paint_line)
    noline.append(zebra)

    # ---------------- sky backdrop ----------------
    skym = _grad_mat(f"{name}_sky_{sky}", SKIES[sky], 60.0)
    arc = _sky_arc(f"{name}_sky", P(0, STAGE[1], 0), 95.0, -4.0, 75.0, 2.0, 178.0, skym)
    noline.append(arc)
    sil = flat(f"{name}_silhouette_{sky}", SILHOUETTE[sky])
    for k in range(22):
        a = math.radians(rng.uniform(8, 172))
        r = rng.uniform(70, 84); s = rng.uniform(3.0, 6.0)
        o = sphere(f"{name}_treeline{k}", P(r * math.cos(a), STAGE[1] + r * math.sin(a), s * 0.35), s, sil, (1.0, 1.0, rng.uniform(0.8, 1.3)))
        noline.append(_no_shadow(o))
    if sky == "dusk":
        sun = sphere(f"{name}_sunset", P(90 * math.cos(math.radians(140)), STAGE[1] + 90 * math.sin(math.radians(140)), 1.5),
                     5.0, flat(f"{name}_sunset", (1.0, 0.78, 0.38)))
        noline.append(_no_shadow(sun))
    elif sky == "night":
        star = flat(f"{name}_star", (1.0, 0.97, 0.88))
        for k in range(55):
            a = math.radians(rng.uniform(10, 170))
            o = sphere(f"{name}_star{k}", P(92 * math.cos(a), STAGE[1] + 92 * math.sin(a), rng.uniform(18, 70)), rng.uniform(0.12, 0.3), star)
            noline.append(_no_shadow(o))
        moon = sphere(f"{name}_moon", P(90 * math.cos(math.radians(55)), STAGE[1] + 90 * math.sin(math.radians(55)), 34), 3.2,
                      flat(f"{name}_moon", (0.95, 0.92, 0.80)))
        noline.append(_no_shadow(moon))

    # ---------------- store ----------------
    cube(f"{name}_store", P(0, 38.5, 4.0), (46, 9, 8), wall)
    cube(f"{name}_store_base", P(0, 33.97, 0.35), (46, 0.1, 0.7), trim_dark)
    cube(f"{name}_store_parapet", P(0, 38.5, 8.2), (46.4, 9.4, 0.45), trim_dark)
    rbox(f"{name}_entrance", P(0, 33.4, 4.6), (14, 1.4, 9.2), accent, radius=0.08)
    cube(f"{name}_entrance_cap", P(0, 33.4, 9.3), (14.4, 1.6, 0.3), trim_dark)
    sidewalk = rbox(f"{name}_sidewalk", P(0, 32.5, 0.1), (48, 3.4, 0.2), concrete, radius=0.03)
    store_glass = group3d(f"{name}_store_glass", P(0, 32.66, 0))
    sg = [cube(f"{name}_store_glass_door", (0, 0, 1.95), (11.0, 0.06, 3.5), shop_glass)]
    for k in range(7):
        sg.append(cube(f"{name}_store_mullion{k}", (-5.5 + k * 11 / 6, -0.04, 1.95), (0.12, 0.06, 3.5), trim_dark))
    sg.append(cube(f"{name}_store_glass_head", (0, -0.04, 3.75), (11.2, 0.06, 0.14), trim_dark))
    attach(store_glass, *sg)
    for s in (-1, 1):
        cube(f"{name}_store_window{'LR'[s > 0]}", P(s * 14.5, 33.93, 1.9), (9.0, 0.06, 2.4), shop_glass)
        for k in range(4):
            cube(f"{name}_store_window{'LR'[s > 0]}_bar{k}", P(s * 14.5 - 4.5 + k * 3.0, 33.89, 1.9), (0.1, 0.06, 2.4), trim_dark)
    awning = rbox(f"{name}_awning", P(0, 31.6, 4.15), (12.4, 2.4, 0.35), accent, radius=0.06)
    cyl(f"{name}_awning_postL", P(-5.8, 30.7, 2.0), 0.1, 4.0, trim_dark, 12)
    cyl(f"{name}_awning_postR", P(5.8, 30.7, 2.0), 0.1, 4.0, trim_dark, 12)
    sign_m = flat(f"{name}_sign_glow", (1.0, 0.88, 0.52)) if (lit and sky != "day") else pbr(f"{name}_sign_paint", (0.98, 0.92, 0.75), rough=0.4)
    sign_txt = str(p.get("sign_text") or "MARKET")[:14]
    sign = text3d(f"{name}_sign", P(0, 32.55, 6.75), sign_txt, 2.2 if len(sign_txt) <= 7 else 2.2 * 7 / len(sign_txt), sign_m,
                  depth=0.3, rot=(math.pi / 2, 0, 0))
    if lit and sky != "day":
        _light(f"{name}_store_light", 'POINT', 600.0, (1.0, 0.72, 0.38), P(0, 30.0, 2.6), soft=2.0)

    # cart corral + carts by the store
    corral = []
    for y in (28.6, 30.2):
        corral.append(cyl(f"{name}_corral_rail{int(y)}", P(-10.5, y, 0.95), 0.06, 4.6, pole_m, 12, rot=(0, math.pi / 2, 0)))
    for x in (-12.8, -8.2):
        for y in (28.6, 30.2):
            corral.append(cyl(f"{name}_corral_post{int(x)}{int(y)}", P(x, y, 0.48), 0.06, 0.96, pole_m, 12))
    for k in range(4):
        _cart(f"{name}_corral_cart{k}", P(-12.0 + k * 0.55, 29.4, 0), 0, mats)

    # ---------------- planters with trees (frame the hero car) ----------------
    for tag, cx in (("L", -5.5), ("R", 6.0)):
        rbox(f"{name}_planter{tag}", P(cx, 6.4, 0.2), (3.4, 2.0, 0.4), concrete, radius=0.05)
        cube(f"{name}_planter{tag}_soil", P(cx, 6.4, 0.41), (3.1, 1.7, 0.04), soil)
        cyl(f"{name}_tree{tag}_trunk", P(cx + 0.3, 6.5, 1.8), 0.16, 2.9, bark, 12)
        sphere(f"{name}_tree{tag}_crown", P(cx + 0.3, 6.5, 3.9), 1.35, leaf, (1.0, 1.0, 0.9))
        sphere(f"{name}_tree{tag}_crown2", P(cx - 0.35, 6.3, 3.4), 0.85, leaf2)
        for k, dx in enumerate((-1.0, -0.2, 0.9)):
            sphere(f"{name}_planter{tag}_bush{k}", P(cx + dx, 6.2, 0.62), 0.42, leaf2 if k % 2 else leaf)

    # ---------------- hero hatchback ----------------
    car_color = _rgb(p["car_color"], DEFAULTS["car_color"])
    car, door, glass = _car(f"{name}_car", car_color, P(CAR_AT[0], CAR_AT[1], 0), 0.0, car_glass, mats,
                            detail=True, door_open=p.get("door_open", 0.0))

    # ---------------- far parked cars ----------------
    if p.get("far_cars", True):
        palette = [(0.85, 0.85, 0.83), (0.35, 0.36, 0.38), (0.04, 0.09, 0.28), (0.45, 0.05, 0.05),
                   (0.05, 0.05, 0.06), (0.62, 0.62, 0.60), (0.08, 0.22, 0.18)]
        spots = [(15.0, 0, 90), (15.0, 1, -90), (15.0, 3, 90), (15.0, 6, 90), (15.0, 8, -90), (15.0, 10, 90),
                 (23.0, 1, 90), (23.0, 4, -90), (23.0, 5, 90), (23.0, 8, 90), (23.0, 9, -90)]
        for k, (yc, i, rz) in enumerate(spots):
            x = -17.6 + 3.2 * i + 1.6
            _car(f"{name}_far_car{k}", palette[k % len(palette)], P(x, yc, 0), rz, far_glass, mats, detail=False)
        _car(f"{name}_side_carR", (0.85, 0.85, 0.83), P(13.0, 6.4, 0), 0.0, far_glass, mats, detail=False)
        _car(f"{name}_side_carL", (0.04, 0.09, 0.28), P(-12.6, 6.4, 0), 180.0, far_glass, mats, detail=False)

    # stray cart in the lot
    cart = _cart(f"{name}_cart", P(-4.2, 9.2, 0), 28.0, mats)

    # ---------------- light poles ----------------
    lamps = group3d(f"{name}_lamps", P(0, 0, 0))
    glow_m = flat(f"{name}_lamp_glow", (1.0, 0.80, 0.48))
    poles = [(-7.5, 10.5), (8.0, 12.0), (-14.0, 20.5), (14.5, 21.5), (3.0, 19.0), (-3.5, 26.5)]
    H = 8.5
    for k, (x, y) in enumerate(poles):
        cyl(f"{name}_pole{k}_base", P(x, y, 0.3), 0.35, 0.6, concrete, 16)
        cyl(f"{name}_pole{k}", P(x, y, H / 2), 0.13, H, pole_m, 16)
        rbox(f"{name}_pole{k}_arm", P(x + 0.55, y, H - 0.05), (1.2, 0.14, 0.12), pole_m, radius=0.03)
        rbox(f"{name}_pole{k}_head", P(x + 1.15, y, H - 0.05), (1.3, 0.6, 0.28), pole_m, radius=0.06)
        cube(f"{name}_pole{k}_lens", P(x + 1.15, y, H - 0.2), (1.1, 0.45, 0.02), lamp_off)
        if lit:
            gl = cube(f"{name}_lamp{k}_glow", (x + 1.15, y, H - 0.215), (1.12, 0.47, 0.02), glow_m)
            attach(lamps, gl)
            if float(p.get("lamp_light", 0) or 0) > 0:
                _light(f"{name}_lamp{k}_light", 'SPOT', float(p["lamp_light"]), (1.0, 0.74, 0.42), (x + 1.15, y, H - 0.4),
                       parent=lamps, size=120, blend=0.7, soft=0.5)

    parts = {"car": car, "car_door": door, "car_glass": glass, "lamps": lamps, "sign": sign,
             "cart": cart, "store_glass": store_glass}
    anchors = {
        "stage": [ox + STAGE[0], oy + STAGE[1]],
        "left": [ox - 0.9, oy + STAGE[1]],
        "right": [ox + 0.9, oy + STAGE[1]],
        "left3": [ox - 1.4, oy + STAGE[1]],
        "right3": [ox + 1.4, oy + STAGE[1]],
        "car": [ox + CAR_AT[0], oy + CAR_AT[1] - CAR_W / 2, 1.2],
        "car_door": [ox + CAR_AT[0] - 0.45, oy + CAR_AT[1] - CAR_W / 2 - 0.1, 1.1],
        "car_window": [ox + CAR_AT[0] - 0.2, oy + CAR_AT[1] - CAR_W / 2, 1.65],
        "cart": [ox - 4.2, oy + 9.2, 0.8],
        "lamp": [ox - 6.35, oy + 10.5, H - 0.2],
        "store_door": [ox, oy + 32.7, 1.9],
        "sign": [ox, oy + 32.55, 6.75],
        "store": [ox, oy + 34.0, 4.0],
        "tree_left": [ox - 5.2, oy + 6.5, 3.9],
        "tree_right": [ox + 6.3, oy + 6.5, 3.9],
    }
    return {"parts": parts, "anchors": anchors, "noline": noline}
