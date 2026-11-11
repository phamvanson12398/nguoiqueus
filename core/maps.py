"""Maps, tactical boards and paper diagrams: shared drawing helpers for library/sets/{parchment_map,tactical_board,paper_diagram}.

Everything lies flat on the XY plane (seen from above: shot type map/board, height "top"), drawn with flat (emission)
colours so the sky never tints it, layered by small z offsets.  Lines can be *drawn progressively* between two frames
(bevel_factor_end keyed), arrow heads ride on the tip, tokens move along keyed paths, areas fade in.

Coastlines, lakes and rivers come from Natural Earth 1:50m (public domain, data/geo/*.json, tools/ne_pack.py).
"""
import json, math, os
import bpy
from . import ctx, geo
from .look import flat
from .timing import ease

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEO_DIR = os.path.join(ROOT, "data", "geo")
_GEO = {}
SERIF = [r"C:\Windows\Fonts\georgiab.ttf", r"C:\Windows\Fonts\timesbd.ttf", r"C:\Windows\Fonts\cambriab.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"]
SERIF_IT = [r"C:\Windows\Fonts\georgiaz.ttf", r"C:\Windows\Fonts\timesbi.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-BoldItalic.ttf", "/usr/share/fonts/truetype/liberation/LiberationSerif-BoldItalic.ttf"]


def font(kind="serif"):
    for p in (SERIF if kind == "serif" else SERIF_IT if kind == "italic" else []):
        if os.path.exists(p): return p
    return ctx.FONT_PATH


def geo_data(name):
    if name not in _GEO:
        _GEO[name] = json.load(open(os.path.join(GEO_DIR, name + ".json"), encoding="utf-8"))["items"]
    return _GEO[name]


# ---------------------------------------------------------------- projection
class Proj:
    """lon/lat -> local x/y (equirectangular, x scaled by cos(mid latitude)), centred on the map, width W units"""
    def __init__(self, bounds, width=16.0):
        self.lon0, self.lat0, self.lon1, self.lat1 = bounds
        self.k = math.cos(math.radians((self.lat0 + self.lat1) / 2))
        self.sx = width / ((self.lon1 - self.lon0) * self.k)
        self.W = width; self.H = (self.lat1 - self.lat0) * self.sx
        self.cx, self.cy = (self.lon0 + self.lon1) / 2, (self.lat0 + self.lat1) / 2

    def __call__(self, lon, lat):
        return ((lon - self.cx) * self.k * self.sx, (lat - self.cy) * self.sx)

    def pts(self, ll): return [self(p[0], p[1]) for p in ll]


class Flat:
    """board/paper coordinates are already local units"""
    def __init__(self, w, h): self.W, self.H = w, h
    def __call__(self, x, y): return (x, y)
    def pts(self, ll): return [tuple(p[:2]) for p in ll]


# ---------------------------------------------------------------- clipping / simplifying
def clip_poly(pts, x0, y0, x1, y1):
    """Sutherland-Hodgman against an axis-aligned rectangle"""
    def clip(P, inside, cross):
        out = []
        for i in range(len(P)):
            cur, prev = P[i], P[i - 1]
            if inside(cur):
                if not inside(prev): out.append(cross(prev, cur))
                out.append(cur)
            elif inside(prev): out.append(cross(prev, cur))
        return out
    def xcut(x):
        return lambda a, b: (x, a[1] + (b[1] - a[1]) * (x - a[0]) / ((b[0] - a[0]) or 1e-9))
    def ycut(y):
        return lambda a, b: (a[0] + (b[0] - a[0]) * (y - a[1]) / ((b[1] - a[1]) or 1e-9), y)
    for inside, cross in ((lambda p: p[0] >= x0, xcut(x0)), (lambda p: p[0] <= x1, xcut(x1)),
                          (lambda p: p[1] >= y0, ycut(y0)), (lambda p: p[1] <= y1, ycut(y1))):
        pts = clip(pts, inside, cross)
        if not pts: return []
    return pts


def clip_line(pts, x0, y0, x1, y1):
    """polyline -> list of runs inside the rectangle (cut at the border)"""
    ins = lambda p: x0 <= p[0] <= x1 and y0 <= p[1] <= y1
    runs, cur = [], []
    for i, p in enumerate(pts):
        if ins(p):
            if not cur and i > 0: cur.append(_edge_hit(pts[i - 1], p, x0, y0, x1, y1))
            cur.append(p)
        elif cur:
            cur.append(_edge_hit(p, pts[i - 1], x0, y0, x1, y1)); runs.append(cur); cur = []
    if len(cur) > 1: runs.append(cur)
    return [r for r in runs if len(r) > 1]


def _edge_hit(out_p, in_p, x0, y0, x1, y1):
    t = 1.0
    for a, b, lo, hi in ((out_p[0], in_p[0], x0, x1), (out_p[1], in_p[1], y0, y1)):
        if a < lo: t = min(t, (lo - b) / (a - b))
        if a > hi: t = min(t, (hi - b) / (a - b))
    return (in_p[0] + (out_p[0] - in_p[0]) * t, in_p[1] + (out_p[1] - in_p[1]) * t)


def simplify(pts, eps):
    out = [pts[0]]
    for p in pts[1:]:
        if math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) >= eps: out.append(p)
    return out


def smooth(pts, n=6):
    """Catmull-Rom through the points (hand-drawn arrows look curved, not jagged)"""
    if len(pts) < 3: return list(pts)
    P = [pts[0]] + list(pts) + [pts[-1]]; out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n; t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in range(2)))
    out.append(tuple(pts[-1]))
    return out


# ---------------------------------------------------------------- materials
def paper_mat(name, c0, c1, scale=4.0, coord_scale=1.0):
    """emission 'paper' with soft noise blotches (no lighting, no sky tint)"""
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear(); L = nt.links
    tc = nt.nodes.new("ShaderNodeTexCoord"); nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = scale; nz.inputs["Detail"].default_value = 6.0
    mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (coord_scale,) * 3
    cr = nt.nodes.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].color = (*c0, 1); cr.color_ramp.elements[1].color = (*c1, 1)
    cr.color_ramp.elements[0].position = 0.35; cr.color_ramp.elements[1].position = 0.7
    e = nt.nodes.new("ShaderNodeEmission"); o = nt.nodes.new("ShaderNodeOutputMaterial")
    L.new(tc.outputs["Object"], mp.inputs[0]); L.new(mp.outputs[0], nz.inputs["Vector"]); L.new(nz.outputs["Fac"], cr.inputs[0])
    L.new(cr.outputs["Color"], e.inputs[0]); L.new(e.outputs[0], o.inputs[0])
    return m


def fade_mat(name, rgb, alpha=1.0):
    """emission with keyable opacity -> (material, factor socket)"""
    m = bpy.data.materials.new(name); m.use_nodes = True
    try: m.surface_render_method = 'BLENDED'
    except Exception: pass
    nt = m.node_tree; nt.nodes.clear()
    e = nt.nodes.new("ShaderNodeEmission"); e.inputs[0].default_value = (*rgb, 1)
    tr = nt.nodes.new("ShaderNodeBsdfTransparent"); mx = nt.nodes.new("ShaderNodeMixShader"); mx.inputs[0].default_value = alpha
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(e.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], o.inputs[0])
    return m, mx.inputs[0]


# ---------------------------------------------------------------- drawing
def _noshadow(objs):
    for o in objs:
        try: o.visible_shadow = False
        except Exception: pass
    return objs


def poly(parent, name, pts, m, z, outline=0.0, ink=None):
    objs = geo.shape(parent, name, pts, m, z, outline=0)
    if outline:
        cu = geo._curve(name + "_ol", pts, True, '3D'); cu.bevel_depth = outline / 2; cu.bevel_resolution = 1
        objs.append(geo.add_obj(name + "_ol", cu, parent, z + 0.0005, ink or geo.INK))
    return _noshadow(objs)


def line(parent, name, pts, w, z, m, cyclic=False):
    cu = geo._curve(name, pts, cyclic, '3D'); cu.bevel_depth = w / 2; cu.bevel_resolution = 1; cu.use_fill_caps = True
    return _noshadow([geo.add_obj(name, cu, parent, z, m)])


def label(parent, name, body, pos, size, m, z, kind="serif", rot=0.0, spacing=1.0, outline_m=None):
    fp = font(kind)
    objs = []
    for i, (mm, off, dz) in enumerate(((outline_m, size * 0.08, -0.0005), (m, 0.0, 0.0)) if outline_m else ((m, 0.0, 0.0),)):
        cu = bpy.data.curves.new(f"{name}_{i}", 'FONT'); cu.body = body; cu.size = size; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'
        cu.space_character = spacing; cu.offset = off
        if fp: cu.font = bpy.data.fonts.load(fp, check_existing=True)
        o = bpy.data.objects.new(f"{name}_{i}", cu); ctx.col.objects.link(o); o.parent = parent
        o.location = (pos[0], pos[1], z + dz); o.rotation_euler = (0, 0, math.radians(rot)); o.data.materials.append(mm)
        objs.append(o)
    return _noshadow(objs)


def path_len(pts):
    return [0.0] + [sum(math.dist(pts[i], pts[i + 1]) for i in range(k)) for k in range(1, len(pts))]


def point_at(pts, cum, u):
    """point + heading at fraction u of the length"""
    L = cum[-1] or 1e-9; s = max(0.0, min(1.0, u)) * L
    for i in range(len(pts) - 1):
        if cum[i + 1] >= s or i == len(pts) - 2:
            seg = (cum[i + 1] - cum[i]) or 1e-9; t = (s - cum[i]) / seg
            x = pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t; y = pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t
            return (x, y), math.atan2(pts[i + 1][1] - pts[i][1], pts[i + 1][0] - pts[i][0])
    return tuple(pts[-1]), 0.0


def draw_on(curves, a, b, hide_before=True):
    """key bevel_factor_end 0 -> 1 between frames a and b (eased)"""
    N = ctx.N
    for cu in curves:
        cu.bevel_factor_mapping_end = 'SPLINE'
        for f in sorted({1, max(1, a - 1), a, b, min(N, b + 1)} | set(range(a, b + 1, 2))):
            u = 0.0 if f < a else 1.0 if f >= b else ease((f - a) / max(1, b - a))
            cu.bevel_factor_end = u if (u > 0 or not hide_before) else 0.0
            cu.keyframe_insert("bevel_factor_end", frame=f)


def show_between(o, a, b=None):
    """scale 0 before a (and after b); 5-frame pop in"""
    N = ctx.N
    o.scale = (0, 0, 0); o.keyframe_insert("scale", frame=1)
    for f in range(max(1, a - 1), min(N, a + 6) + 1):
        s = 0.0 if f < a else min(1.0, ease((f - a) / 5) * 1.0)
        o.scale = (s, s, s); o.keyframe_insert("scale", frame=f)
    if b is not None and b < N:
        for f in (b, b + 4):
            s = 1.0 if f == b else 0.0
            o.scale = (s, s, s); o.keyframe_insert("scale", frame=min(N, f))


def fade_between(fac, a, b=None, top=1.0, dur=10):
    N = ctx.N
    fac.default_value = 0.0; fac.keyframe_insert("default_value", frame=1)
    for f in (a, a + dur):
        fac.default_value = 0.0 if f == a else top; fac.keyframe_insert("default_value", frame=min(N, f))
    if b is not None and b < N:
        for f in (b, b + dur):
            fac.default_value = top if f == b else 0.0; fac.keyframe_insert("default_value", frame=min(N, f))


def arrow(parent, name, pts, w, z, rgb, a=None, b=None, ink_w=None, head=True, dashed=False):
    """thick arrow (colour over a dark rim), drawn on between a and b, head riding on the tip"""
    pts = smooth(pts) if len(pts) > 2 else list(pts)
    col = flat(f"map_arrow{tuple(round(c, 3) for c in rgb)}", rgb)
    ink = flat("map_ink", (0.10, 0.07, 0.05))
    rw = w + (ink_w or w * 0.45)
    rim = line(parent, name + "_rim", pts, rw, z, ink)
    body = line(parent, name, pts, w, z + (rw - w) / 2 + 0.002, col)     # tubes: lift the body above the rim's crown
    hd = None
    if head:
        hz = z + rw / 2 + 0.004
        hd = geo.empty(name + "_head", parent, (*pts[-1], hz))
        L = w * 2.6
        tri = [(L * 0.55, 0), (-L * 0.45, L * 0.55), (-L * 0.45, -L * 0.55)]
        poly(hd, name + "_hd", tri, col, 0.0, outline=w * 0.45, ink=ink)
        _, ang = point_at(pts, path_len(pts), 1.0); hd.rotation_euler = (0, 0, ang)
    if a is not None:
        draw_on([rim[0].data, body[0].data], a, b)
        if hd is not None:
            cum = path_len(pts); N = ctx.N
            hd.scale = (0, 0, 0); hd.keyframe_insert("scale", frame=1)
            for f in range(max(1, a), min(N, b + 1) + 1):
                u = 1.0 if f >= b else ease((f - a) / max(1, b - a))
                (x, y), ang = point_at(pts, cum, u)
                hd.location = (x, y, hz); hd.rotation_euler = (0, 0, ang)
                s = 1.0 if f > a else 0.0
                hd.scale = (s, s, s)
                for p in ("location", "rotation_euler", "scale"): hd.keyframe_insert(p, frame=f)
    return [rim[0], body[0]] + ([hd] if hd else [])


def move_keys(o, moves, proj, z):
    """moves = [[frame, [x, y]], ...] in map/board coordinates; eased between keys"""
    if not moves: return
    pts = [(int(f), proj(*p[:2])) for f, p in moves]
    o.location = (*pts[0][1], z); o.keyframe_insert("location", frame=1)
    for (f0, p0), (f1, p1) in zip(pts, pts[1:]):
        for f in range(f0, f1 + 1, 2):
            u = ease((f - f0) / max(1, f1 - f0))
            o.location = (p0[0] + (p1[0] - p0[0]) * u, p0[1] + (p1[1] - p0[1]) * u, z); o.keyframe_insert("location", frame=f)
        o.location = (*p1, z); o.keyframe_insert("location", frame=f1)


def faction_rgb(spec, factions, default=(0.75, 0.10, 0.08)):
    """colour of an item: its 'color', else its faction's colour"""
    if spec.get("color"): return tuple(spec["color"])
    f = (factions or {}).get(spec.get("faction"))
    return tuple(f["color"]) if f and f.get("color") else default


def factions_of(params):
    return {f["id"]: f for f in params.get("_factions", [])}


def keyname(s):
    import re
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")
