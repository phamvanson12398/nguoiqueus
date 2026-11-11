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


def set_visible(grp, frame, vis):
    for o in [grp] + list(grp.children_recursive):
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
