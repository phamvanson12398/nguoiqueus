"""American kitchen, daytime, open toward -Y (camera stands inside, y -2.7..2).
Black/white checker floor (0.8 tiles), back wall face at y=6.5, cream cabinets, wood counter
along the back wall (front edge y~5.42, top z 1.35), sink under a sunny window on the left,
mint retro fridge on the right (x 3.5), ceiling at z 6.5.
Part 'lamp': pendant lamp, root empty at the ceiling (0, 3.6, 6.5) so rotating it swings the lamp;
round red shade with a glowing bottom at z~5.3; two buttered toast slices stuck right under it
(centre z 5.15, butter side up against the shade) as children `kitchen_lamp_toast1/2`.
The floor x -3.5..3, y 3..5 is left empty for a table / tower.  Uses no shared `random`."""
import math
import bpy
import bmesh
from core import ctx
from core.look import flat, pbr, ramp_mat
from core.geo import cube, cyl, sphere, rbox, lathe, extrude, torus, group3d, attach

DEFAULTS = dict(
    name="kitchen",
    origin=[0.0, 0.0],
    wall_color=[0.55, 0.74, 0.82],
    cabinet_color=[0.93, 0.84, 0.62],
    counter_color=[0.55, 0.32, 0.14],
    backsplash_color=[0.30, 0.62, 0.60],
    fridge_color=[0.40, 0.78, 0.66],
    lamp_color=[0.85, 0.10, 0.07],
    lamp_on=True,
    lamp_light=0.0,
    stuck_toast=True,
    side_walls=True,
    decor=True,
)

TILE = 0.8
WALL_Y = 6.5          # front face of the back wall
CEIL_Z = 6.5
LAMP_XY = (0.0, 3.6)


def _no_shadow(o):
    try:
        o.visible_shadow = False
    except AttributeError:
        pass
    return o


def _checker(name, x0, y0, nx, ny, t, z, m):
    """one mesh holding only the dark tiles (sits on a light slab)"""
    bm = bmesh.new()
    for i in range(nx):
        for j in range(ny):
            if (i + j) % 2 == 0:
                vs = [bm.verts.new((x0 + i * t + dx, y0 + j * t + dy, z)) for dx, dy in ((0, 0), (t, 0), (t, t), (0, t))]
                bm.faces.new(vs)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); ctx.col.objects.link(o)
    me.materials.append(m)
    return o


def _bread_pts(s=1.0):
    pts = [(-0.2 * s, -0.2 * s), (0.2 * s, -0.2 * s)]
    for i in range(15):
        a = math.radians(-20 + 220 * i / 14)
        pts.append((0.235 * s * math.cos(a), (0.06 + 0.16 * math.sin(a)) * s))
    return pts


def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    name = p.get("name") or "kitchen"
    ox, oy = p["origin"]

    def P(x, y, z):
        return (ox + x, oy + y, z)

    # ---------------- materials ----------------
    tile_w = pbr(f"{name}_tile_white", (0.88, 0.88, 0.85), rough=0.35)
    tile_k = pbr(f"{name}_tile_black", (0.03, 0.03, 0.035), rough=0.35)
    wall = pbr(f"{name}_wall", tuple(p["wall_color"]), rough=0.9)
    ceil_m = pbr(f"{name}_ceiling", (0.92, 0.91, 0.88), rough=0.9)
    cab = pbr(f"{name}_cabinet", tuple(p["cabinet_color"]), rough=0.6)
    cab_dark = pbr(f"{name}_cabinet_shadow", tuple(c * 0.55 for c in p["cabinet_color"]), rough=0.7)
    cc = p["counter_color"]
    counter = ramp_mat(f"{name}_counter", [(0.2, tuple(c * 0.8 for c in cc)), (0.55, tuple(cc)), (0.9, tuple(c * 0.9 for c in cc))],
                       scale=3.0, mapping_scale=(6, 0.6, 0.6), bump=0.1, rough=0.5)
    knob = pbr(f"{name}_knob", (0.75, 0.55, 0.15), rough=0.3, metal=0.9)
    chrome = pbr(f"{name}_chrome", (0.8, 0.82, 0.85), rough=0.2, metal=1.0)
    steel = pbr(f"{name}_steel", (0.45, 0.47, 0.5), rough=0.35, metal=0.9)
    splash = pbr(f"{name}_backsplash", tuple(p["backsplash_color"]), rough=0.3)
    frame_m = pbr(f"{name}_window_frame", (0.95, 0.95, 0.93), rough=0.5)
    sky = flat(f"{name}_window_sky", (0.50, 0.78, 1.0))
    sun_m = flat(f"{name}_window_sun", (1.0, 0.82, 0.25))
    cloud = flat(f"{name}_window_cloud", (0.98, 0.98, 0.98))
    valance = pbr(f"{name}_valance", (0.95, 0.62, 0.06), rough=0.7)
    fridge = pbr(f"{name}_fridge", tuple(p["fridge_color"]), rough=0.35)

    noline = []

    # ---------------- floor ----------------
    nx, ny = 16, 14
    x0, y0 = -nx * TILE / 2, -4.0
    cube(f"{name}_floor", P(0, (y0 + y0 + ny * TILE) / 2, -0.05), (nx * TILE, ny * TILE, 0.1), tile_w)
    tiles = _checker(f"{name}_floor_tiles", ox + x0, oy + y0, nx, ny, TILE, 0.003, tile_k)
    noline.append(tiles)

    # ---------------- walls & ceiling (no shadows so the sun still lights the room) ----------------
    _no_shadow(cube(f"{name}_wall_back", P(-0.8, WALL_Y + 0.1, CEIL_Z / 2), (11.4, 0.2, CEIL_Z), wall))
    if p["side_walls"]:
        _no_shadow(cube(f"{name}_wall_left", P(-6.5, 1.25, CEIL_Z / 2), (0.2, 10.5, CEIL_Z), wall))
        _no_shadow(cube(f"{name}_wall_right", P(4.9, 1.25, CEIL_Z / 2), (0.2, 10.5, CEIL_Z), wall))
        _no_shadow(cube(f"{name}_ceiling", P(-0.8, 1.25, CEIL_Z + 0.05), (11.4, 10.5, 0.1), ceil_m))
    # baseboard along the back wall behind nothing visible -> skip; backsplash band
    cube(f"{name}_backsplash", P(-1.4, WALL_Y - 0.01, 1.775), (8.4, 0.02, 0.85), splash)

    # ---------------- base cabinets + counter ----------------
    bx0, bx1 = -5.6, 2.8
    bw = bx1 - bx0; bcx = (bx0 + bx1) / 2
    cube(f"{name}_toekick", P(bcx, 6.0, 0.06), (bw, 0.9, 0.12), cab_dark)
    rbox(f"{name}_base", P(bcx, 5.98, 0.68), (bw, 1.0, 1.12), cab, radius=0.02)
    ndoor = 8; dw = bw / ndoor
    for i in range(ndoor):
        cx = bx0 + dw * (i + 0.5)
        rbox(f"{name}_door{i}", P(cx, 5.46, 0.53), (dw - 0.08, 0.05, 0.7), cab, radius=0.02)
        rbox(f"{name}_drawer{i}", P(cx, 5.46, 1.06), (dw - 0.08, 0.05, 0.24), cab, radius=0.02)
        kx = cx + (dw / 2 - 0.16) * (1 if i % 2 == 0 else -1)
        sphere(f"{name}_knob{i}", P(kx, 5.41, 0.78), 0.045, knob)
        rbox(f"{name}_pull{i}", P(cx, 5.415, 1.06), (0.3, 0.035, 0.04), knob, radius=0.01)
    rbox(f"{name}_counter", P(bcx - 0.05, 5.96, 1.30), (bw + 0.1, 1.08, 0.1), counter, radius=0.02)

    # sink + faucet under the window
    sx = -2.6
    cube(f"{name}_sink", P(sx, 5.95, 1.352), (1.2, 0.68, 0.012), steel)
    cyl(f"{name}_faucet", P(sx, 6.3, 1.56), 0.05, 0.42, chrome, 16)
    cyl(f"{name}_faucet_spout", P(sx, 6.15, 1.76), 0.045, 0.34, chrome, 16, rot=(math.pi / 2, 0, 0))
    sphere(f"{name}_faucet_knob", P(sx + 0.22, 6.3, 1.42), 0.06, chrome)

    # ---------------- upper cabinets ----------------
    def uppers(tag, x0_, x1_, z0, z1, depth):
        w = x1_ - x0_; cx_ = (x0_ + x1_) / 2; zc = (z0 + z1) / 2; h = z1 - z0
        yc = WALL_Y - depth / 2
        rbox(f"{name}_upper_{tag}", P(cx_, yc, zc), (w, depth, h), cab, radius=0.02)
        n = max(1, round(w / 0.95)); d = w / n
        for i in range(n):
            dx = x0_ + d * (i + 0.5)
            rbox(f"{name}_upper_{tag}_door{i}", P(dx, WALL_Y - depth - 0.02, zc), (d - 0.08, 0.05, h - 0.1), cab, radius=0.02)
            kx = dx + (d / 2 - 0.15) * (1 if i % 2 == 0 else -1)
            sphere(f"{name}_upper_{tag}_knob{i}", P(kx, WALL_Y - depth - 0.07, z0 + 0.22), 0.045, knob)

    uppers("mid", -1.2, 2.7, 3.0, 4.8, 0.6)
    uppers("left", -5.6, -4.0, 3.0, 4.8, 0.6)
    uppers("fridge", 2.8, 4.2, 4.3, 5.2, 0.9)

    # ---------------- sunny window (left of the back wall) ----------------
    wz = 3.45
    rbox(f"{name}_window_frame", P(sx, WALL_Y - 0.03, wz), (2.4, 0.08, 2.0), frame_m, radius=0.02)
    cube(f"{name}_window_glass", P(sx, WALL_Y - 0.08, wz), (2.1, 0.02, 1.7), sky)
    cyl(f"{name}_window_sun", P(sx - 0.55, WALL_Y - 0.095, wz + 0.45), 0.24, 0.006, sun_m, 32, rot=(math.pi / 2, 0, 0))
    for k, (cx_, cz, s) in enumerate(((sx + 0.45, wz + 0.5, 1.0), (sx + 0.7, wz + 0.42, 0.8), (sx + 0.2, wz + 0.42, 0.7))):
        sphere(f"{name}_window_cloud{k}", P(cx_, WALL_Y - 0.095, cz), 0.2 * s, cloud, (1.4, 0.03, 0.8))
    cube(f"{name}_window_bar_v", P(sx, WALL_Y - 0.11, wz), (0.08, 0.04, 1.7), frame_m)
    cube(f"{name}_window_bar_h", P(sx, WALL_Y - 0.11, wz), (2.1, 0.04, 0.08), frame_m)
    rbox(f"{name}_window_sill", P(sx, WALL_Y - 0.15, wz - 1.05), (2.7, 0.3, 0.1), frame_m, radius=0.02)
    rbox(f"{name}_valance", P(sx, WALL_Y - 0.12, wz + 1.12), (2.7, 0.2, 0.36), valance, radius=0.04)

    # ---------------- retro fridge (right) ----------------
    fx_ = 3.5
    rbox(f"{name}_fridge", P(fx_, 5.8, 1.9), (1.4, 1.2, 3.8), fridge, radius=0.1)
    rbox(f"{name}_fridge_door_low", P(fx_, 5.18, 1.35), (1.3, 0.06, 2.5), fridge, radius=0.05)
    rbox(f"{name}_fridge_door_top", P(fx_, 5.18, 3.19), (1.3, 0.06, 1.02), fridge, radius=0.05)
    rbox(f"{name}_fridge_handle_low", P(fx_ - 0.52, 5.1, 1.9), (0.08, 0.1, 0.9), chrome, radius=0.03)
    rbox(f"{name}_fridge_handle_top", P(fx_ - 0.52, 5.1, 3.0), (0.08, 0.1, 0.45), chrome, radius=0.03)
    for k, (mx, mz, col) in enumerate(((3.3, 2.2, (0.95, 0.75, 0.05)), (3.85, 2.0, (0.85, 0.1, 0.08)), (3.6, 1.4, (0.1, 0.35, 0.85)))):
        cyl(f"{name}_fridge_magnet{k}", P(mx, 5.14, mz), 0.08, 0.03, pbr(f"{name}_magnet{k}", col, rough=0.4), 20, rot=(math.pi / 2, 0, 0))
    note = rbox(f"{name}_fridge_note", P(3.75, 5.145, 1.75), (0.4, 0.01, 0.5), pbr(f"{name}_note", (0.97, 0.95, 0.85), rough=0.9), radius=0.0)
    note.rotation_euler = (0, math.radians(8), 0)

    # ---------------- counter decor ----------------
    if p["decor"]:
        crock = pbr(f"{name}_crock", (0.1, 0.3, 0.75), rough=0.4)
        cyl(f"{name}_crock", P(1.7, 6.1, 1.53), 0.15, 0.36, crock, 24)
        spoon = pbr(f"{name}_spoon", (0.65, 0.42, 0.2), rough=0.6)
        for k, (dx, tilt) in enumerate(((-0.06, -0.2), (0.0, 0.05), (0.07, 0.25))):
            cyl(f"{name}_spoon{k}", P(1.7 + dx, 6.1, 1.85), 0.025, 0.45, spoon, 10, rot=(0, tilt, 0))
        bowl = pbr(f"{name}_bowl", (0.95, 0.95, 0.93), rough=0.3)
        lathe(f"{name}_bowl", P(-0.6, 6.0, 1.35), [(0.0, 0.0), (0.18, 0.0), (0.32, 0.1), (0.36, 0.2), (0.33, 0.2), (0.0, 0.08)], bowl)
        for k, (dx, dy, dz, col) in enumerate(((-0.12, 0.0, 1.6, (0.95, 0.45, 0.03)), (0.12, 0.03, 1.6, (0.8, 0.08, 0.06)),
                                               (0.0, -0.05, 1.72, (0.98, 0.78, 0.1)))):
            sphere(f"{name}_fruit{k}", P(-0.6 + dx, 6.0 + dy, dz), 0.13, pbr(f"{name}_fruit{k}", col, rough=0.5))
        pot = pbr(f"{name}_pot", (0.8, 0.38, 0.2), rough=0.7)
        leaf = pbr(f"{name}_leaf", (0.15, 0.5, 0.15), rough=0.8)
        cyl(f"{name}_sill_pot", P(sx + 0.85, WALL_Y - 0.17, wz - 0.85), 0.12, 0.22, pot, 20)
        for k, (dx, dz) in enumerate(((-0.06, 0.18), (0.07, 0.22), (0.0, 0.32))):
            sphere(f"{name}_sill_leaf{k}", P(sx + 0.85 + dx, WALL_Y - 0.17, wz - 0.85 + dz), 0.12, leaf)

    # ---------------- PART: pendant lamp (root at the ceiling -> rotate to swing) ----------------
    lamp = group3d(f"{name}_lamp", P(LAMP_XY[0], LAMP_XY[1], CEIL_Z))
    metal_dark = pbr(f"{name}_lamp_metal", (0.08, 0.08, 0.09), rough=0.4, metal=0.8)
    shade_m = pbr(f"{name}_lamp_shade", tuple(p["lamp_color"]), rough=0.4)
    rim_m = pbr(f"{name}_lamp_rim", (0.85, 0.62, 0.12), rough=0.3, metal=0.9)
    glow = flat(f"{name}_lamp_glow", (1.0, 0.86, 0.55)) if p["lamp_on"] else pbr(f"{name}_lamp_off", (0.9, 0.88, 0.82), rough=0.3)
    parts_l = [
        cyl(f"{name}_lamp_canopy", (0, 0, -0.04), 0.18, 0.08, metal_dark, 24),
        cyl(f"{name}_lamp_cord", (0, 0, -0.45), 0.025, 0.8, metal_dark, 10),
        lathe(f"{name}_lamp_shade", (0, 0, 0), [(0.0, -0.82), (0.14, -0.82), (0.2, -0.88), (0.36, -1.0),
                                                 (0.52, -1.12), (0.6, -1.2), (0.0, -1.2)], shade_m, segments=40),
        torus(f"{name}_lamp_rim", (0, 0, -1.2), 0.6, 0.03, rim_m),
        cyl(f"{name}_lamp_bulb", (0, 0, -1.225), 0.5, 0.05, glow, 40),     # glowing bottom, z 5.25..5.30
    ]
    attach(lamp, *parts_l)
    if p["lamp_light"] and p["lamp_light"] > 0:
        ld = bpy.data.lights.new(f"{name}_lamp_light", 'POINT')
        ld.energy = float(p["lamp_light"]); ld.color = (1.0, 0.85, 0.6); ld.shadow_soft_size = 0.3
        lo = bpy.data.objects.new(f"{name}_lamp_light", ld); ctx.col.objects.link(lo)
        lo.location = (0, 0, -1.5); lo.parent = lamp

    parts = {"lamp": lamp}
    if p["stuck_toast"]:
        crust = pbr(f"{name}_toast_crust", (0.42, 0.20, 0.05), rough=0.8)
        crumb = pbr(f"{name}_toast_face", (0.85, 0.52, 0.16), rough=0.8)
        butter = pbr(f"{name}_toast_butter", (0.98, 0.82, 0.18), rough=0.3)
        tz = 5.15 - CEIL_Z                                   # toast centre, local to the lamp root
        for k, (dx, dy, rz) in enumerate(((-0.23, 0.02, 12.0), (0.24, -0.03, -18.0))):
            n = f"{name}_lamp_toast{k + 1}"
            t = extrude(n, (dx, dy, tz), _bread_pts(1.0), 0.1, crust, rot=(0, 0, math.radians(rz)))
            face = extrude(f"{n}_face", (0, 0, 0), _bread_pts(0.84), 0.104, crumb)
            pat = rbox(f"{n}_butter", (0.0, -0.02, 0.075), (0.15, 0.15, 0.05), butter, radius=0.015)
            drip = sphere(f"{n}_drip", (0.12, -0.19, -0.06), 0.035, butter, (1, 1, 1.8))
            attach(t, face, pat, drip)
            attach(lamp, t)
            parts[f"lamp_toast{k + 1}"] = t

    anchors = {
        "joe": [ox + 2.3, oy + 4.6],
        "table": [ox - 0.25, oy + 4.0],
        "lamp": [ox + LAMP_XY[0], oy + LAMP_XY[1], 5.3],
        "toast": [ox + LAMP_XY[0], oy + LAMP_XY[1], 5.15],
        "counter": [ox - 1.4, oy + 5.42, 1.35],
        "fridge": [ox + fx_, oy + 5.15],
        "window": [ox + sx, oy + WALL_Y, wz],
    }
    return {"parts": parts, "anchors": anchors, "noline": noline}
