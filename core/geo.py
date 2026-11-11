"""Geometry helpers: 3D primitives (cube, cylinder, sphere) and the 2D toolkit
(filled shapes with ink outline, strokes, discs, empties, two-segment limbs,
camera-facing billboard roots, visibility keys)."""
import math
import bpy
from . import ctx
from .look import flat, setmat

INK = None
WHITE = None


def init():
    """Create the shared ink/white materials (call once after ctx.setup)."""
    global INK, WHITE
    INK = flat("ink", (0.03, 0.03, 0.035))
    WHITE = flat("white", (0.98, 0.98, 0.97))


# ---------------- 3D primitives ----------------
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


def plane(size, loc, m):
    bpy.ops.mesh.primitive_plane_add(size=size, location=loc)
    return setmat(bpy.context.object, m)


# ---------------- 2D outlines ----------------
def ellipse(cx, cy, rx, ry, n=40, a0=0.0, a1=2 * math.pi):
    return [(cx + rx * math.cos(a0 + (a1 - a0) * i / n), cy + ry * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + (0 if a1 - a0 >= 2 * math.pi - 1e-6 else 1))]


def arc(cx, cy, rx, ry, a0, a1, n=10):
    return ellipse(cx, cy, rx, ry, n, math.radians(a0), math.radians(a1))


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
    o = bpy.data.objects.new(name, data); ctx.col.objects.link(o)
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


def disc(parent, name, cx, cy, r, z, m=None):
    return shape(parent, name, ellipse(cx, cy, r, r, 24), m or INK, z, outline=0)


def empty(name, parent=None, loc=(0, 0, 0)):
    o = bpy.data.objects.new(name, None); ctx.col.objects.link(o)
    o.parent = parent; o.location = loc
    return o


def group(parent, name):
    return empty(name, parent)


def text(name, body, size, parent, loc, m, align_y=True, font_path="default", offset=None, rot=None):
    """3D text object (labels, '!'); font_path='default' uses ctx.FONT_PATH"""
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = body; cu.size = size
    if offset is not None: cu.offset = offset
    cu.align_x = 'CENTER'
    if align_y: cu.align_y = 'CENTER'
    fp = ctx.FONT_PATH if font_path == "default" else font_path
    if fp: cu.font = bpy.data.fonts.load(fp, check_existing=True)
    o = bpy.data.objects.new(name, cu); ctx.col.objects.link(o); o.parent = parent; o.location = loc
    if rot is not None: o.rotation_euler = rot
    o.data.materials.append(m)
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


def billboard_root(name, loc):
    """empty that turns around Z to face the camera, with an upright child plane for 2D art"""
    root = empty(name, None, loc)
    lt = root.constraints.new('LOCKED_TRACK'); lt.target = ctx.cam; lt.track_axis = 'TRACK_NEGATIVE_Y'; lt.lock_axis = 'LOCK_Z'
    plane_ = empty(name + "_plane", root); plane_.rotation_euler = (math.pi / 2, 0, 0)
    return root, plane_


char_root = billboard_root


def keep_hidden(o, hidden=True):
    """hide a part at build time and keep it hidden when a visibility track shows its parent group
    (e.g. the unlit states of a lamp); a story can still show it by targeting it directly"""
    o.hide_render = o.hide_viewport = hidden
    o["why_keep_hidden"] = hidden
    return o


def set_visible(grp, frame, vis):
    for o in [grp] + list(grp.children_recursive):
        if vis and o is not grp and o.get("why_keep_hidden"): continue
        o.hide_render = not vis; o.hide_viewport = not vis
        o.keyframe_insert("hide_render", frame=frame); o.keyframe_insert("hide_viewport", frame=frame)


def vis_track(obj, ranges):
    """ranges: list of (start, end) frames where obj is visible"""
    prev = None
    for f in range(1, ctx.N + 1):
        v = any(a <= f <= b for a, b in ranges)
        if v != prev:
            set_visible(obj, f, v); prev = v


def key_loc(o, f, loc): o.location = loc; o.keyframe_insert("location", frame=f)
def key_rot(o, f, rot): o.rotation_euler = rot; o.keyframe_insert("rotation_euler", frame=f)
def key_scl(o, f, s): o.scale = s; o.keyframe_insert("scale", frame=f)


def arrow2d(parent, name, p0, p1, w, m):
    """double-headed 2D arrow between p0 and p1 (diagrams); parts: name_s, name_h1, name_h-1"""
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
    """centred 3D text in a 2D plane (z = 0.2)"""
    return text(name, txt, size, parent, (loc[0], loc[1], 0.2), m)


def points(spec):
    """2D point list from JSON: [[x, y], ...] | {"rrect": [cx, cy, w, h, r]} | {"ellipse": [cx, cy, rx, ry, n(, a0, a1)]}
    | {"arc": [cx, cy, rx, ry, a0_deg, a1_deg(, n)]} | {"ring": [cx, cy, rx, ry, n]} (closed ellipse for strokes)"""
    if isinstance(spec, dict):
        (k, a), = spec.items()
        if k == "rrect": return rrect(*a)
        if k == "ellipse": return ellipse(*a)
        if k == "arc": return arc(*a)
        if k == "ring": e = ellipse(*a); return e + [e[0]]
        raise ValueError(f"unknown point generator {k!r}")
    return [tuple(p) for p in spec]


# =====================================================================
#  modelling blocks for library authors (design_prop / design_set)
#  Every block returns a MESH object (so it gets ink outlines) at `loc`.
# =====================================================================
def rbox(name, loc, size, m, radius=0.03, segments=3):
    """rounded box: size = full (x, y, z) dimensions, radius = bevel width"""
    from mathutils import Matrix
    o = cube(name, loc, (1, 1, 1), m)
    o.data.transform(Matrix.Diagonal((size[0], size[1], size[2], 1.0)))   # real size in the mesh: even bevel
    if radius > 0:
        b = o.modifiers.new("round", 'BEVEL'); b.width = radius; b.segments = segments; b.limit_method = 'ANGLE'
        b.use_clamp_overlap = True
    return o


def cone(name, loc, r1, r2, depth, m, verts=32, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r1, radius2=r2, depth=depth, location=loc, rotation=rot)
    o = bpy.context.object; o.name = name
    return setmat(o, m)


def torus(name, loc, major, minor, m, rot=(0, 0, 0), major_seg=48, minor_seg=12):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, major_segments=major_seg,
                                     minor_segments=minor_seg, location=loc, rotation=rot)
    o = bpy.context.object; o.name = name
    return setmat(o, m)


def lathe(name, loc, profile, m, segments=32, smooth=True):
    """solid of revolution around local Z: profile = [(radius, z), ...] from bottom to top.
    Points with radius 0 close the ends.  E.g. a vase, bottle, bollard, cup, lamp."""
    import bmesh
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    rings = []
    for r, z in profile:
        if r <= 1e-6:
            rings.append([bm.verts.new((0.0, 0.0, z))])
        else:
            rings.append([bm.verts.new((r * math.cos(2 * math.pi * i / segments), r * math.sin(2 * math.pi * i / segments), z))
                          for i in range(segments)])
    for a, b in zip(rings, rings[1:]):
        if len(a) == 1 and len(b) == 1: continue
        if len(a) == 1:
            for i in range(segments): bm.faces.new((a[0], b[i], b[(i + 1) % segments]))
        elif len(b) == 1:
            for i in range(segments): bm.faces.new((a[i], b[0], a[(i + 1) % segments]))
        else:
            for i in range(segments): bm.faces.new((a[i], a[(i + 1) % segments], b[(i + 1) % segments], b[i]))
    if len(rings[0]) > 1: bm.faces.new(list(reversed(rings[0])))
    if len(rings[-1]) > 1: bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    if smooth:
        for p in me.polygons: p.use_smooth = True
    o = bpy.data.objects.new(name, me); ctx.col.objects.link(o); o.location = loc
    me.materials.append(m)
    return o


def _curve_to_mesh(o, name, m):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
    curve = o.data
    bpy.data.objects.remove(o); bpy.data.curves.remove(curve)
    me.name = name; me.materials.clear(); me.materials.append(m)
    ob = bpy.data.objects.new(name, me); ctx.col.objects.link(ob)
    return ob


def extrude(name, loc, pts, depth, m, bevel=0.0, rot=(0, 0, 0)):
    """2D outline (points in XY, see points()) pushed out along Z by `depth` (centred), optional rounded edge.
    E.g. a sign, a star, a gable house front, a fish, a tooth."""
    cu = _curve(name, points(pts), True, '2D')
    cu.fill_mode = 'BOTH'; cu.extrude = depth / 2
    if bevel > 0: cu.bevel_depth = bevel; cu.bevel_resolution = 2
    tmp = bpy.data.objects.new(name + "_tmp", cu); ctx.col.objects.link(tmp)
    o = _curve_to_mesh(tmp, name, m); o.location = loc; o.rotation_euler = rot
    return o


def text3d(name, loc, body, size, m, depth=0.02, rot=(0, 0, 0), font_path="default"):
    """3D lettering (signs, labels on props) as a mesh, centred"""
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = body; cu.size = size; cu.extrude = depth / 2
    cu.align_x = 'CENTER'; cu.align_y = 'CENTER'
    fp = ctx.FONT_PATH if font_path == "default" else font_path
    if fp: cu.font = bpy.data.fonts.load(fp, check_existing=True)
    tmp = bpy.data.objects.new(name + "_tmp", cu); ctx.col.objects.link(tmp)
    o = _curve_to_mesh(tmp, name, m); o.location = loc; o.rotation_euler = rot
    return o


def group3d(name, loc=(0, 0, 0), parent=None):
    """empty used as the root of a multi-part prop"""
    return empty(name, parent, loc)


def attach(root, *objs):
    """parent objects to root keeping their current world placement (root at origin when building)"""
    for o in objs:
        o.parent = root
    return root


def import_glb(path, name, m_override=None, size=None):
    """import a CC0 .glb (Kenney, Quaternius, Poly Haven): parent everything to one root empty,
    optionally scale so the largest dimension is `size`, and soften materials toward the cartoon look"""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    root = empty(name, None)
    for o in new:
        if o.parent is None: o.parent = root
        for c in o.users_collection:
            if c is not ctx.col: c.objects.unlink(o)
        if o.name not in ctx.col.objects: ctx.col.objects.link(o)
        if o.type == 'MESH':
            for slot in o.material_slots:
                mt = slot.material
                if m_override is not None: slot.material = m_override
                elif mt and mt.use_nodes and "Principled BSDF" in mt.node_tree.nodes:
                    b = mt.node_tree.nodes["Principled BSDF"]
                    b.inputs["Roughness"].default_value = max(0.6, b.inputs["Roughness"].default_value)
                    b.inputs["Metallic"].default_value = min(0.3, b.inputs["Metallic"].default_value)
    if size:
        from mathutils import Vector
        bpy.context.view_layer.update()
        pts = [o.matrix_world @ Vector(c) for o in new if o.type == 'MESH' for c in o.bound_box]
        if pts:
            ext = max(max(p[i] for p in pts) - min(p[i] for p in pts) for i in range(3))
            if ext > 0: root.scale = (size / ext,) * 3
    return root
