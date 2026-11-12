"""3D characters from the 2D character rig.

The rig (core/chars.py) draws every part as a flat 2D curve on an upright plane that turns to face the camera: the face
circle on the head, the shirt on the torso, outfit pieces, eyes and mouths, stick limbs, hands and shoes. `convert(c)`
runs after a character (and its outfit, talking mouth) is built and turns those flat pieces into 3D:

- the face and the shirt are "inflated" into closed round solids (depth from the distance to the outline, so a circle
  becomes a ball and a rounded rectangle a pill);
- pieces drawn on the head or the torso (hair, helmet, beard, eyes, mouth, armour, belts) are bent onto that surface,
  in front of it or, for pieces drawn behind the base (back hair, cloak), behind it;
- everything else (hands, shoes, hand-held shields and weapons, joints) is inflated into its own small solid;
- stick limbs get thicker; ink tubes along the outlines of pieces on the body follow the surface;
- colours keep their 2D value in the light and get a darker toon band in the shade; solids get an ink shell outline.

The skeleton, poses, expressions, blinks and lip flap are untouched: only geometry and materials change.
Style switch: story meta.char_style "3d" (default) or "2d"; env WHYSHORTS_CHAR_STYLE overrides (fingerprint checks)."""
import math
import os
import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector
from . import geo, look

STYLE_ENV = "WHYSHORTS_CHAR_STYLE"
HEAD_DEPTH = 0.62        # head solid depth / radius (a slightly flattened ball keeps the 2D face readable)
TORSO_DEPTH = 0.55       # torso depth / half its smaller side
FREE_DEPTH = 0.55        # hands, shoes, shields, props
LAYER = 0.35             # 2D layer gaps (z) are squeezed by this much on top of the surface
LIMB_W = 1.7             # stick limbs get this much thicker
CORNER = 0.035           # corner rounding radius (scene units) for every character piece
EDGE = 0.065             # target edge length when subdividing flat pieces
TUBE_FLAT = 0.25         # depth squash of stroke tubes lying on a surface
HULL = 0.010             # ink shell thickness around solids (the rim tube draws the main outline)
LIGHT = (-0.45, 0.6, -0.66)  # toon light direction in Blender camera space (x right, y up, -z towards the viewer)
RIM = (0.72, 0.86, 0.45)  # rim light: facing ratio start, full, strength
SHADE_AT = 0.52          # (dot + 1) / 2 below this is the shade band


def style(meta=None):
    s = os.environ.get(STYLE_ENV) or (meta or {}).get("char_style") or "3d"
    return "2d" if s == "2d" else "3d"


# ---------------- materials ----------------
def _rgb_of(m):
    if m is None or not m.use_nodes: return (0.8, 0.8, 0.8)
    for n in m.node_tree.nodes:
        if n.type == 'EMISSION': return tuple(n.inputs[0].default_value[:3])
        if n.type == 'BSDF_PRINCIPLED': return tuple(n.inputs["Base Color"].default_value[:3])
    return (0.8, 0.8, 0.8)


def toon(m):
    """2-band toon version of a flat colour: lit = the 2D colour, shade = darker and a little warmer/bluer"""
    if m is None or m is geo.INK or m.name.startswith(("ink", "INK")): return m
    if m.name.endswith("__toon"): return m
    key = m.name + "__toon"
    if key in look.MATS: return look.MATS[key]
    rgb = _rgb_of(m)
    if max(rgb) < 0.06: look.MATS[key] = m; return m          # near-black: keep flat ink
    t = bpy.data.materials.new(key); t.use_nodes = True
    nt = t.node_tree; nt.nodes.clear(); L = nt.links
    # shading from a fixed light in CAMERA space (upper left, in front): the shade band is always a clean crescent on the
    # lower right, whatever the scene lights, shadows or sky do (real lights gave blotchy, noisy bands)
    geo_n = nt.nodes.new("ShaderNodeNewGeometry")
    vt = nt.nodes.new("ShaderNodeVectorTransform"); vt.vector_type = 'NORMAL'; vt.convert_from = 'WORLD'; vt.convert_to = 'CAMERA'
    L.new(geo_n.outputs["Normal"], vt.inputs[0])
    dot = nt.nodes.new("ShaderNodeVectorMath"); dot.operation = 'DOT_PRODUCT'
    dot.inputs[1].default_value = tuple(Vector(LIGHT).normalized())
    L.new(vt.outputs[0], dot.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB"); ramp.color_ramp.interpolation = 'LINEAR'
    el = ramp.color_ramp.elements
    shade = (0.66, 0.66, 0.74)                                     # shade band: darker, slightly cool
    el[0].position, el[0].color = SHADE_AT - 0.025, (*shade, 1)      # a narrow soft edge: crisp but not jagged
    el[1].position, el[1].color = SHADE_AT + 0.025, (1, 1, 1, 1)
    sc = nt.nodes.new("ShaderNodeMath"); sc.operation = 'MULTIPLY_ADD'; sc.inputs[1].default_value = 0.5; sc.inputs[2].default_value = 0.5
    L.new(dot.outputs["Value"], sc.inputs[0]); L.new(sc.outputs[0], ramp.inputs[0])
    mul = nt.nodes.new("ShaderNodeMix"); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'
    mul.inputs[0].default_value = 1.0; mul.inputs[6].default_value = (*rgb, 1)
    L.new(ramp.outputs[0], mul.inputs[7])
    # rim light: a thin brighter band on the silhouette, on the lit side only -> characters pop off the background
    lw = nt.nodes.new("ShaderNodeLayerWeight"); lw.inputs[0].default_value = 0.5
    rim = nt.nodes.new("ShaderNodeMapRange"); rim.inputs[1].default_value, rim.inputs[2].default_value = RIM[0], RIM[1]
    L.new(lw.outputs["Facing"], rim.inputs[0])
    lit = nt.nodes.new("ShaderNodeMapRange"); lit.inputs[1].default_value, lit.inputs[2].default_value = SHADE_AT, SHADE_AT + 0.2
    L.new(sc.outputs[0], lit.inputs[0])
    rk = nt.nodes.new("ShaderNodeMath"); rk.operation = 'MULTIPLY'; L.new(rim.outputs[0], rk.inputs[0]); L.new(lit.outputs[0], rk.inputs[1])
    rk2 = nt.nodes.new("ShaderNodeMath"); rk2.operation = 'MULTIPLY'; rk2.inputs[1].default_value = RIM[2]; L.new(rk.outputs[0], rk2.inputs[0])
    hi = nt.nodes.new("ShaderNodeMix"); hi.data_type = 'RGBA'; hi.blend_type = 'SCREEN'
    L.new(rk2.outputs[0], hi.inputs[0]); L.new(mul.outputs[2], hi.inputs[6]); hi.inputs[7].default_value = (1.0, 0.97, 0.9, 1)
    em = nt.nodes.new("ShaderNodeEmission"); L.new(hi.outputs[2], em.inputs[0])
    out = nt.nodes.new("ShaderNodeOutputMaterial"); L.new(em.outputs[0], out.inputs[0])
    look.MATS[key] = t
    return t


# ---------------- 2D polygon helpers ----------------
def _seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay; L2 = dx * dx + dy * dy
    t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def _inside(px, py, poly):
    c = False; n = len(poly)
    for i in range(n):
        ax, ay = poly[i]; bx, by = poly[(i + 1) % n]
        if (ay > py) != (by > py) and px < (bx - ax) * (py - ay) / (by - ay + 1e-15) + ax: c = not c
    return c


class Pillow:
    """height field of an inflated 2D outline: 0 on the outline, round towards the inside, flat beyond the inscribed radius"""
    def __init__(self, poly, ratio):
        self.poly = poly; self.ratio = ratio
        xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
        self.box = (min(xs), max(xs), min(ys), max(ys))
        R = 1e-4
        for i in range(13):
            for j in range(13):
                x = self.box[0] + (self.box[1] - self.box[0]) * (i + 0.5) / 13
                y = self.box[2] + (self.box[3] - self.box[2]) * (j + 0.5) / 13
                if _inside(x, y, poly): R = max(R, self.dist(x, y))
        self.R = R

    def dist(self, x, y):
        n = len(self.poly)
        return min(_seg_dist(x, y, *self.poly[i], *self.poly[(i + 1) % n]) for i in range(n))

    def many(self, xs, ys):
        """vectorised depth for arrays of points"""
        P = np.asarray(self.poly, dtype=np.float64); A = P; Bp = np.roll(P, -1, axis=0)
        x = np.asarray(xs, dtype=np.float64)[:, None]; y = np.asarray(ys, dtype=np.float64)[:, None]
        ax, ay, bx, by = A[:, 0][None], A[:, 1][None], Bp[:, 0][None], Bp[:, 1][None]
        dx, dy = bx - ax, by - ay; L2 = np.maximum(dx * dx + dy * dy, 1e-12)
        t = np.clip(((x - ax) * dx + (y - ay) * dy) / L2, 0, 1)
        d = np.hypot(x - ax - t * dx, y - ay - t * dy).min(axis=1)
        cross = ((ay > y) != (by > y)) & (x < dx * (y - ay) / np.where(np.abs(dy) < 1e-15, 1e-15, dy) + ax)
        inside = (cross.sum(axis=1) % 2) == 1
        d = np.minimum(d, self.R)
        return np.where(inside, self.ratio * np.sqrt(np.maximum(0.0, d * (2 * self.R - d))), 0.0)

    def __call__(self, x, y):
        if not (self.box[0] <= x <= self.box[1] and self.box[2] <= y <= self.box[3]) or not _inside(x, y, self.poly): return 0.0
        d = min(self.dist(x, y), self.R)
        return self.ratio * math.sqrt(max(0.0, d * (2 * self.R - d)))


def round_corners(pts, r, steps=4, max_angle=150.0):
    """replace every corner sharper than max_angle by a small arc (quadratic Bezier) of radius ~r: angular cloaks,
    belts and plates read soft and round instead of spiky"""
    n = len(pts)
    if n < 3 or r <= 0: return pts
    out = []
    for i in range(n):
        p0, p1, p2 = Vector(pts[i - 1]), Vector(pts[i]), Vector(pts[(i + 1) % n])
        a, b = p0 - p1, p2 - p1
        la, lb = a.length, b.length
        if la < 1e-9 or lb < 1e-9: continue
        ang = math.degrees(a.angle(b))
        if ang > max_angle: out.append(tuple(p1)); continue
        d = min(r, 0.45 * la, 0.45 * lb)
        q0, q2 = p1 + a / la * d, p1 + b / lb * d
        for k in range(steps + 1):
            t = k / steps
            q = (1 - t) ** 2 * q0 + 2 * (1 - t) * t * p1 + t * t * q2
            out.append((q.x, q.y))
    return out


def _set_poly(ob, pts):
    """rewrite a curve object's first spline as a POLY spline through pts (keeps cyclic / 2D-3D / bevel settings)"""
    cu = ob.data; cyc = cu.splines[0].use_cyclic_u
    cu.splines.clear(); sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
    for q, (x, y) in zip(sp.points, pts): q.co = (x, y, 0, 1)
    sp.use_cyclic_u = cyc


def _curve_poly(ob):
    """first spline of a curve object as 2D points (object-local)"""
    sp = ob.data.splines[0]
    pts = sp.bezier_points if sp.type == 'BEZIER' else sp.points
    return [(p.co[0], p.co[1]) for p in pts]


# ---------------- mesh building ----------------
def _fill_bm(poly, edge=EDGE):
    """triangulated flat polygon with interior vertices (so it can bend)"""
    bm = bmesh.new()
    vs = [bm.verts.new((x, y, 0.0)) for x, y in poly]
    if len(vs) < 3: return bm
    es = [bm.edges.new((vs[i], vs[(i + 1) % len(vs)])) for i in range(len(vs))]
    bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=False, edges=es)
    for _ in range(6):
        longs = [e for e in bm.edges if e.calc_length() > edge]
        if not longs: break
        bmesh.ops.subdivide_edges(bm, edges=longs, cuts=1, use_grid_fill=False)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        bmesh.ops.beautify_fill(bm, faces=bm.faces[:], edges=[e for e in bm.edges if not e.is_boundary])
    return bm


def _mirror_back(bm):
    """close a front shell with its mirror image (same outline at z = 0)"""
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    dup = bmesh.ops.duplicate(bm, geom=geom)
    nv = [g for g in dup["geom"] if isinstance(g, bmesh.types.BMVert)]
    for v in nv: v.co.z = -v.co.z
    nf = [g for g in dup["geom"] if isinstance(g, bmesh.types.BMFace)]
    bmesh.ops.reverse_faces(bm, faces=nf)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)


def _swap_to_mesh(ob, me):
    """replace a curve object by a mesh object with the same name, parent, transform and materials"""
    name = ob.name; mats = [s.material for s in ob.material_slots]
    new = bpy.data.objects.new(name + "__m", me)
    for col in ob.users_collection: col.objects.link(new)
    new.parent = ob.parent; new.matrix_parent_inverse = ob.matrix_parent_inverse.copy()
    new.location, new.rotation_euler, new.scale = ob.location.copy(), ob.rotation_euler.copy(), ob.scale.copy()
    new.hide_render, new.hide_viewport = ob.hide_render, ob.hide_viewport
    for k in ob.keys():
        try: new[k] = ob[k]
        except Exception: pass
    for ch in list(ob.children):
        mw = ch.matrix_world.copy(); ch.parent = new; ch.matrix_world = mw
    bpy.data.objects.remove(ob, do_unlink=True)
    new.name = name
    me.materials.clear()
    for m in mats: me.materials.append(toon(m))
    for p in me.polygons: p.use_smooth = True
    return new


def _hull(ob, t=HULL):
    look.add_ink_outlines([])                                     # creates INK_HULL once
    me = ob.data; me.materials.append(look.INK_HULL)
    sol = ob.modifiers.new("ink", 'SOLIDIFY'); sol.thickness = t; sol.offset = 1.0
    sol.use_flip_normals = True; sol.material_offset = len(me.materials) - 1; sol.use_rim = False


# ---------------- conversion ----------------
class _Ref:
    """a surface to bend pieces onto: head or torso, in its own local space"""
    def __init__(self, empty, base_obj, ratio, base_z):
        self.e = empty; self.inv = empty.matrix_world.inverted()
        M = self.inv @ base_obj.matrix_world
        poly = [(M @ Vector((x, y, 0)))[:2] for x, y in _curve_poly(base_obj)]
        self.depth = Pillow(poly, ratio); self.base_z = base_z; self.layers = []

    def gap(self, zc):
        """distance above (or below) the surface for a piece drawn at 2D layer zc: one step per distinct layer, so
        pieces that were 0.001 apart in 2D (and z-fought once bent onto the surface) stay apart"""
        side = [z for z in self.layers if (z >= self.base_z) == (zc >= self.base_z)]
        side = sorted(set(round(z, 4) for z in side), key=lambda z: abs(z - self.base_z))
        k = side.index(round(zc, 4)) if round(zc, 4) in side else len(side)
        return 0.008 + 0.012 * k


def _apply(M, co):
    """4x4 matrix applied to an (n, 3) array"""
    A = np.array(M); co = np.asarray(co, dtype=np.float64)
    if not len(co): return co.reshape(0, 3)
    return co @ A[:3, :3].T + A[:3, 3]


def _ancestors(ob):
    a = []; p = ob.parent
    while p is not None: a.append(p); p = p.parent
    return a


def convert(c):
    """turn character c (built by chars.make_char + outfit + talk mouth) into a 3D character; idempotent"""
    if getattr(c, "is3d", False): return c
    name = c.name
    face = bpy.data.objects.get(name + "_face"); shirt = bpy.data.objects.get(name + "_shirt")
    if face is None or shirt is None or face.type != 'CURVE' or shirt.type != 'CURVE': return c
    bpy.context.view_layer.update()
    head = _Ref(c.head, face, HEAD_DEPTH, (c.head.matrix_world.inverted() @ face.matrix_world).translation.z)
    tz = (c.torso.matrix_world.inverted() @ shirt.matrix_world).translation.z
    torso = _Ref(c.torso, shirt, TORSO_DEPTH, tz)
    free_roots = set()
    for limb in (getattr(c, "armL", None), getattr(c, "armR", None), getattr(c, "legL", None), getattr(c, "legR", None)):
        if limb: free_roots.add(limb[0])
    for o in getattr(c, "held", []):           # props the story puts in the character's hands: their own solids, not bent onto the body
        free_roots.add(o)
    skip = set()
    for attr in ("speedlines", "excl", "steam", "drips"):
        v = getattr(c, attr, None)
        for o in (v if isinstance(v, (list, tuple)) else [v]):
            if o is not None and hasattr(o, "children_recursive"): skip |= {o} | set(o.children_recursive)
    objs = [o for o in c.root.children_recursive if o.type == 'CURVE' and o not in skip]
    # soft corners: every filled piece and its outline tube get the same rounded outline
    for o in objs:
        if o.data.dimensions != '2D' or not o.data.splines: continue
        sc = max(1e-6, (abs(o.matrix_world.to_scale().x) + abs(o.matrix_world.to_scale().y)) / 2)
        pts = round_corners(_curve_poly(o), CORNER / sc)
        _set_poly(o, pts)
        ol = bpy.data.objects.get(o.name + "_ol")
        if ol is not None and ol.type == 'CURVE': _set_poly(ol, pts)
    # thicker stick limbs (bevel tubes on the limb pivots)
    for o in objs:
        if o.name.endswith(("_s1", "_s2")) and any(a in free_roots for a in _ancestors(o)):
            o.data.bevel_depth *= LIMB_W
    solids = {face.name, shirt.name}
    fills = {o.name for o in objs if o.data.dimensions == '2D'}
    for o in objs:                                             # 2D layers used on each surface
        anc = _ancestors(o)
        if o is face or o is shirt: continue
        if c.head in anc: head.layers.append((head.inv @ o.matrix_world).translation.z)
        elif c.torso in anc and not any(a in free_roots for a in anc): torso.layers.append((torso.inv @ o.matrix_world).translation.z)
    # free pieces (shield, shoe, held items): the biggest fill of a group is a solid, the smaller ones drawn on it
    # (shield boss and emblem, shoe straps) are bent onto its surface instead of being buried inside it
    free_ref = {}
    groups = {}
    for o in objs:
        if o.data.dimensions != '2D' or o is face or o is shirt: continue
        anc = _ancestors(o)
        if c.head in anc or (c.torso in anc and not any(a in free_roots for a in anc)): continue
        groups.setdefault(o.parent, []).append(o)
    for par, mem in groups.items():
        if len(mem) < 2 or par is None: continue
        inv = par.matrix_world.inverted()

        def poly_in_par(o):
            Mo = inv @ o.matrix_world
            return [tuple((Mo @ Vector((x, y, 0)))[:2]) for x, y in _curve_poly(o)]
        polys = {o: poly_in_par(o) for o in mem}
        area = {o: (max(p[0] for p in P) - min(p[0] for p in P)) * (max(p[1] for p in P) - min(p[1] for p in P)) for o, P in polys.items() if len(P) >= 3}
        if not area: continue
        base = max(area, key=area.get)
        bz = (inv @ base.matrix_world).translation.z
        r = _Ref(par, base, FREE_DEPTH, bz); free_ref[base] = r; solids.add(base.name)
        for o in mem:
            if o is base or o not in area: continue
            P = polys[o]; cx = sum(p[0] for p in P) / len(P); cy = sum(p[1] for p in P) / len(P)
            if _inside(cx, cy, polys[base]):
                free_ref[o] = r; r.layers.append((inv @ o.matrix_world).translation.z)
        for o in objs:                                           # strokes drawn on it (emblems, straps)
            if o.parent is not par or o.data.dimensions == '2D' or o.name.endswith("_ol") or o in free_ref: continue
            P = poly_in_par(o)
            if P and _inside(sum(p[0] for p in P) / len(P), sum(p[1] for p in P) / len(P), polys[base]):
                free_ref[o] = r; r.layers.append((inv @ o.matrix_world).translation.z)
    # all bevel tubes to meshes with ONE scene evaluation (one per tube took ~1 s each in a 6,000-object chapter)
    dg = bpy.context.evaluated_depsgraph_get()
    tube_mesh = {o.name: bpy.data.meshes.new_from_object(o.evaluated_get(dg)) for o in objs if o.data.dimensions != '2D'}
    for o in objs:
        nm = o.name
        anc = _ancestors(o)
        on_limb = any(a in free_roots for a in anc)
        ref = head if (c.head in anc or o is face) else torso if ((c.torso in anc and not on_limb) or o is shirt) else free_ref.get(o)
        is_fill = o.data.dimensions == '2D'
        # outlines of solids stay as round tubes on the rim (an even, smooth line); the thin shell only adds the
        # silhouette seen from above/below
        if nm.endswith("_ol") and (nm[:-3] in solids or nm[:-3] in fills) and (nm[:-3] in solids or ref is None):
            pass
        M = (ref.inv @ o.matrix_world) if ref is not None else Matrix.Identity(4)
        if is_fill:
            poly = _curve_poly(o)
            if len(poly) < 3: continue
            bm = _fill_bm(poly)
            co = np.array([v.co[:] for v in bm.verts]) if bm.verts else np.zeros((0, 3))
            if ref is not None:
                P = _apply(M, co)
                if nm in solids:                                   # the base solid itself: front shell = the surface
                    P[:, 2] = ref.base_z + ref.depth.many(P[:, 0], P[:, 1])
                    behind, solid = False, True
                else:
                    zc = M.translation.z; behind = zc < ref.base_z - 1e-6
                    own = Pillow([tuple(q[:2]) for q in _apply(M, np.array([(x, y, 0.0) for x, y in poly]))], 0.08)
                    h = ref.depth.many(P[:, 0], P[:, 1]) + ref.gap(zc)
                    P[:, 2] = ref.base_z + (-h if behind else h)
                    solid = False
                co = _apply(M.inverted(), P)
            else:                                                  # free piece: its own pillow, both sides
                own = Pillow(poly, FREE_DEPTH)
                co[:, 2] = own.many(co[:, 0], co[:, 1]); behind, solid = False, True
            for v, q in zip(bm.verts, co): v.co = q
            bm.normal_update()
            if solid:
                _mirror_back(bm)
                bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
            else:                                                  # open shell: face the viewer (or away, behind)
                nz = sum(f.normal.z * f.calc_area() for f in bm.faces)
                if (nz < 0) != behind: bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
            me = bpy.data.meshes.new(nm + "_3d"); bm.to_mesh(me); bm.free()
            new = _swap_to_mesh(o, me)
            if solid and max(new.dimensions) > 0.05: _hull(new)
        else:                                                      # bevel tube (stroke, outline): convert, then bend
            me = tube_mesh[nm]
            if ref is not None and len(me.vertices):
                co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
                P = _apply(M, co); zc = M.translation.z; behind = zc < ref.base_z - 1e-6
                # tubes are flattened in depth: a thick ink stroke under a thinner coloured one (horns, outlines) must
                # not poke through it once both sit on the surface one layer gap apart
                h = ref.depth.many(P[:, 0], P[:, 1]) + ref.gap(zc) + 0.002 + (P[:, 2] - zc) * TUBE_FLAT
                P[:, 2] = ref.base_z + (-h if behind else h)
                me.vertices.foreach_set("co", _apply(M.inverted(), P).ravel()); me.update()
            _swap_to_mesh(o, me)
    c.is3d = True
    return c
