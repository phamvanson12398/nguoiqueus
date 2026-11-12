"""Long-form visual effects (story "vfx"): smoke, battle dust, fire + embers, rain/snow, arrow volleys, sparks,
waving banners, light shafts, and per-shot colour grades.  Cheap by design: keyed meshes and a few screen overlays,
no physics simulation, so previews of any frame are exact and fast.  No gore.
"""
import math, random
import bpy
from . import ctx, geo
from .look import flat, pbr
from .timing import ease

GRADES = {   # multiply colour, mix factor, brightness, contrast (Bright/Contrast node, -100..100)
    "day": ((1.0, 1.0, 1.0), 0.0, 0.0, 0.0), "dawn": ((1.0, 0.80, 0.66), 0.6, -3.0, 4.0),
    "dusk": ((1.0, 0.60, 0.40), 0.7, -8.0, 10.0), "night": ((0.35, 0.45, 0.85), 0.85, -22.0, 14.0),
    "cold": ((0.76, 0.86, 1.0), 0.6, -2.0, 6.0), "warm": ((1.0, 0.86, 0.66), 0.5, 2.0, 4.0),
    "desert": ((1.0, 0.84, 0.58), 0.6, 4.0, 8.0), "sepia": ((0.92, 0.74, 0.52), 0.85, -3.0, 6.0),
    "storm": ((0.58, 0.64, 0.76), 0.8, -12.0, 12.0), "fire": ((1.0, 0.52, 0.28), 0.65, 0.0, 10.0),
}


def _fade_mat(name, rgb, emission=True):
    m = bpy.data.materials.new(name); m.use_nodes = True
    try: m.surface_render_method = 'BLENDED'
    except Exception: pass
    nt = m.node_tree; nt.nodes.clear()
    sh = nt.nodes.new("ShaderNodeEmission" if emission else "ShaderNodeBsdfDiffuse"); sh.inputs[0].default_value = (*rgb, 1)
    tr = nt.nodes.new("ShaderNodeBsdfTransparent"); mx = nt.nodes.new("ShaderNodeMixShader"); mx.inputs[0].default_value = 1.0
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(sh.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], o.inputs[0])
    return m, mx.inputs[0]


def _ico(name, loc, r, m, sub=2):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub, radius=r, location=loc)
    o = bpy.context.active_object; o.name = name; o.data.materials.append(m)
    for p in o.data.polygons: p.use_smooth = True
    try: o.visible_shadow = False
    except Exception: pass
    return o


def _hide_outside(o, a, b):
    N = ctx.N
    o.scale = (0, 0, 0); o.keyframe_insert("scale", frame=1)
    if b < N: o.keyframe_insert("scale", frame=min(N, b + 1))


def smoke(k, spec, rnd, dust=False):
    """rising (smoke) or ground-hugging (dust) puffs that grow, drift and fade"""
    N = ctx.N; a, b = int(spec.get("from", 1)), int(spec.get("to", N))
    x0, y0, z0 = (list(spec["at"]) + [0.0])[:3]
    n = int(spec.get("n", 10)); size = spec.get("size", 1.5 if dust else 1.2); spread = spec.get("spread", 2.5 if dust else 1.0)
    rgb = tuple(spec.get("color") or ((0.42, 0.33, 0.22) if dust else (0.40, 0.40, 0.42)))
    life = int(spec.get("life", 90 if dust else 75)); rise = spec.get("rise", 0.15 if dust else 0.9)
    wind = spec.get("wind", [0.4, 0.1])
    objs = []
    for i in range(n):
        m, fac = _fade_mat(f"vfx_smoke{k}_{i}", tuple(c * rnd.uniform(0.9, 1.1) for c in rgb), emission=False)
        o = _ico(f"vfx_smoke{k}_{i}", (x0, y0, z0), size, m)
        t0 = a + int(i * max(1, (b - a - life * 0.3)) / max(1, n)) if b - a > life else a + int(rnd.uniform(0, 10))
        ox, oy = rnd.uniform(-spread, spread), rnd.uniform(-spread * 0.5, spread * 0.5)
        for f in sorted(set([1, max(1, t0 - 1)] + list(range(t0, min(N, t0 + life) + 1, 3)) + [min(N, t0 + life + 1)])):
            u = (f - t0) / life
            if f < t0 or u > 1:
                o.scale = (0, 0, 0); o.keyframe_insert("scale", frame=f); fac.default_value = 0.0; fac.keyframe_insert("default_value", frame=f); continue
            s = (0.35 + 0.9 * ease(min(1, u * 1.6))) * (1.4 if dust else 1.0)
            o.scale = (s, s, s * (0.6 if dust else 1.0))
            o.location = (x0 + ox + wind[0] * u * life / 30, y0 + oy + wind[1] * u * life / 30, z0 + size * 0.5 + rise * u * life / 30)
            fac.default_value = spec.get("opacity", 0.75) * (1 - u) ** 1.3 * min(1, u * 6)
            for p in ("scale", "location"): o.keyframe_insert(p, frame=f)
            fac.keyframe_insert("default_value", frame=f)
        objs.append(o)
    return objs


def fire(k, spec, rnd):
    """flickering flame tongues (emission) + rising embers"""
    N = ctx.N; a, b = int(spec.get("from", 1)), int(spec.get("to", N))
    x0, y0, z0 = (list(spec["at"]) + [0.0])[:3]; sz = spec.get("size", 1.0)
    root = geo.empty(f"vfx_fire{k}", None, (x0, y0, z0)); objs = [root]
    cols = [(1.0, 0.25, 0.02), (1.0, 0.55, 0.05), (1.0, 0.85, 0.25)]
    for i in range(int(spec.get("tongues", 7))):
        m = flat(f"vfx_flame{i % 3}", cols[i % 3])
        r = sz * (0.35 - 0.08 * (i % 3)); dx = rnd.uniform(-0.35, 0.35) * sz
        o = geo.cone(f"vfx_fire{k}_{i}", (x0 + dx, y0 + rnd.uniform(-0.2, 0.2) * sz, z0 + r * 1.2), r, 0.0, r * 3.2, m, verts=10)
        o.parent = None; objs.append(o)
        ph = rnd.uniform(0, 6.28)
        for f in range(max(1, a - 1), min(N, b + 1) + 1, 2):
            on = a <= f <= b
            s = (1.0 + 0.22 * math.sin(f * 0.9 + ph) + 0.12 * math.sin(f * 2.3 + ph * 2)) if on else 0.0
            o.scale = (s * 0.9, s * 0.9, s * (1.0 + 0.15 * math.sin(f * 1.7 + ph))) if on else (0, 0, 0)
            o.keyframe_insert("scale", frame=f)
        if a > 1: o.scale = (0, 0, 0); o.keyframe_insert("scale", frame=1)
    em = flat("vfx_ember", (1.0, 0.6, 0.1))
    for i in range(int(spec.get("embers", 10))):
        o = _ico(f"vfx_ember{k}_{i}", (x0, y0, z0), 0.035 * sz, em, 1); objs.append(o)
        per = rnd.randint(40, 70); off = rnd.randint(0, per); dx = rnd.uniform(-0.6, 0.6) * sz
        for f in range(max(1, a), min(N, b) + 1, 2):
            u = ((f + off) % per) / per
            o.location = (x0 + dx + 0.3 * math.sin(u * 6 + i), y0, z0 + 0.3 * sz + u * 3.0 * sz)
            s = 1.0 if u < 0.85 else 0.0
            o.scale = (s, s, s); o.keyframe_insert("location", frame=f); o.keyframe_insert("scale", frame=f)
        _hide_outside(o, a, b)
    if spec.get("smoke", True):
        objs += smoke(f"{k}f", {"at": [x0, y0, z0 + sz * 2.5], "from": a, "to": b, "n": 6, "size": 0.6 * sz, "rise": 1.2, "opacity": 0.5}, rnd)
    return objs


def arrows(k, spec, rnd):
    """a volley: n arrows fly from 'from_at' to 'to_at' on parabolic arcs (start spread over 'stagger' frames)"""
    N = ctx.N; f0 = int(spec["from"]); dur = int(spec.get("dur", 30)); n = int(spec.get("n", 30))
    p0 = (list(spec["from_at"]) + [1.5])[:3]; p1 = (list(spec["to_at"]) + [0.0])[:3]
    sp = spec.get("spread", 3.0); hgt = spec.get("arc", 6.0); stag = int(spec.get("stagger", 8))
    shaft = flat("vfx_arrow", (0.12, 0.08, 0.05)); fl = flat("vfx_fletch", (0.9, 0.88, 0.8))
    objs = []
    for i in range(n):
        o = geo.empty(f"vfx_arrow{k}_{i}", None, tuple(p0))
        sh = geo.cyl(f"vfx_arrow{k}_{i}_s", (0, 0, 0), 0.025, 0.9, shaft, 6, rot=(0, math.pi / 2, 0)); sh.parent = o
        tp = geo.cone(f"vfx_arrow{k}_{i}_t", (0.5, 0, 0), 0.05, 0.0, 0.12, shaft, verts=6, rot=(0, math.pi / 2, 0)); tp.parent = o
        fe = geo.cube(f"vfx_arrow{k}_{i}_f", (-0.42, 0, 0), (0.14, 0.01, 0.08), fl); fe.parent = o
        objs += [o, sh, tp, fe]
        s0 = f0 + rnd.randint(0, stag); a0 = [p0[0] + rnd.uniform(-sp, sp) * 0.3, p0[1] + rnd.uniform(-sp, sp) * 0.3, p0[2]]
        a1 = [p1[0] + rnd.uniform(-sp, sp), p1[1] + rnd.uniform(-sp, sp), p1[2]]
        prev = None
        o.scale = (0, 0, 0); o.keyframe_insert("scale", frame=1)
        for f in range(max(1, s0 - 1), min(N, s0 + dur + 2) + 1):
            u = min(1.0, max(0.0, (f - s0) / dur))
            pos = [a0[j] + (a1[j] - a0[j]) * u for j in range(3)]; pos[2] += hgt * 4 * u * (1 - u)
            o.location = pos
            du = 0.02; q = [a0[j] + (a1[j] - a0[j]) * min(1, u + du) for j in range(3)]; q[2] += hgt * 4 * min(1, u + du) * (1 - min(1, u + du))
            dx, dy, dz = q[0] - pos[0], q[1] - pos[1], q[2] - pos[2]
            if u < 1: o.rotation_euler = (0, -math.atan2(dz, math.hypot(dx, dy)), math.atan2(dy, dx))
            s = 1.0 if s0 <= f else 0.0
            o.scale = (s, s, s)
            for p in ("location", "rotation_euler", "scale"): o.keyframe_insert(p, frame=f)
        if spec.get("stick", True) is False:
            o.scale = (0, 0, 0); o.keyframe_insert("scale", frame=min(N, s0 + dur + 3))
    return objs


def sparks(k, spec, rnd):
    N = ctx.N; f0 = int(spec["frame"]); x0, y0, z0 = (list(spec["at"]) + [1.2])[:3]
    m = flat("vfx_spark", (1.0, 0.85, 0.35)); objs = []
    for i in range(int(spec.get("n", 14))):
        o = _ico(f"vfx_spark{k}_{i}", (x0, y0, z0), 0.03, m, 1); objs.append(o)
        v = [rnd.uniform(-1, 1), rnd.uniform(-0.6, 0.2), rnd.uniform(0.2, 1.2)]; life = rnd.randint(6, 12)
        o.scale = (0, 0, 0); o.keyframe_insert("scale", frame=1)
        for f in range(max(1, f0 - 1), min(N, f0 + life + 1) + 1):
            t = (f - f0) / 30
            o.location = (x0 + v[0] * t * 4, y0 + v[1] * t * 4, z0 + v[2] * t * 4 - 4.9 * t * t)
            s = 1.0 if f0 <= f <= f0 + life else 0.0
            o.scale = (s, s * 0.6, s * 0.6); o.keyframe_insert("location", frame=f); o.keyframe_insert("scale", frame=f)
    return objs


def banner(k, spec, rnd, factions):
    """pole + flag that waves (Wave modifier, no keys); colour from 'faction' or 'color'; optional 2D emblem disc"""
    x0, y0, z0 = (list(spec["at"]) + [0.0])[:3]; h = spec.get("h", 3.2); w = spec.get("w", 1.4); fh = spec.get("fh", 0.9)
    f = (factions or {}).get(spec.get("faction")) or {}
    rgb = tuple(spec.get("color") or f.get("color") or (0.7, 0.06, 0.04))
    pole = geo.cyl(f"vfx_banner{k}_pole", (x0, y0, z0 + h / 2), 0.04, h, pbr("vfx_pole", (0.32, 0.18, 0.08)), 10)
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=24, y_subdivisions=8, size=1.0, location=(0, 0, 0))
    fl = bpy.context.active_object; fl.name = f"vfx_banner{k}_flag"
    fl.scale = (w, fh, 1); fl.rotation_euler = (math.pi / 2, 0, math.radians(spec.get("rot", 0)))
    fl.location = (x0 + w / 2 * math.cos(math.radians(spec.get("rot", 0))), y0 + w / 2 * math.sin(math.radians(spec.get("rot", 0))), z0 + h - fh / 2)
    fl.data.materials.append(pbr(f"vfx_flag{tuple(round(c, 3) for c in rgb)}", rgb, rough=0.8))
    wv = fl.modifiers.new("wave", 'WAVE'); wv.use_normal = False; wv.use_x = True; wv.use_y = False
    wv.height = 0.12 * spec.get("wind", 1.0); wv.width = 0.35; wv.narrowness = 1.2; wv.speed = 0.06 * spec.get("wind", 1.0)
    wv.start_position_x = -0.5; wv.falloff_radius = 0.0
    sol = fl.modifiers.new("thick", 'SOLIDIFY'); sol.thickness = 0.02
    return [pole, fl]


def light_shafts(k, spec, rnd):
    """soft god rays: a few long transparent emissive cones from 'at' along 'dir'"""
    N = ctx.N; a, b = int(spec.get("from", 1)), int(spec.get("to", N))
    x0, y0, z0 = (list(spec["at"]) + [12.0])[:3]; d = spec.get("dir", [0.3, 0.2, -1.0])
    L = math.sqrt(sum(c * c for c in d)); d = [c / L for c in d]
    objs = []
    for i in range(int(spec.get("n", 4))):
        m, fac = _fade_mat(f"vfx_ray{k}_{i}", tuple(spec.get("color") or (1.0, 0.92, 0.7)))
        ln = spec.get("length", 16.0)
        from mathutils import Vector
        sx, sy = x0 + rnd.uniform(-3, 3), y0 + rnd.uniform(-2, 2)
        c = (sx + d[0] * ln / 2, sy + d[1] * ln / 2, z0 + d[2] * ln / 2)       # cone centre: half-way along the ray
        o = geo.cone(f"vfx_ray{k}_{i}", c, 1.2 + rnd.uniform(0, 0.8), 0.2, ln, m, verts=16)   # wide end (-Z) far from the source
        o.rotation_euler = Vector((-d[0], -d[1], -d[2])).to_track_quat('Z', 'Y').to_euler()
        try: o.visible_shadow = False
        except Exception: pass
        for f in (1, max(1, a), min(N, a + 30), max(1, b - 30), min(N, b)):
            fac.default_value = 0.0 if f in (1, a, b) and not (a <= f < b and f not in (a, b)) else spec.get("opacity", 0.12)
            fac.keyframe_insert("default_value", frame=f)
        objs.append(o)
    return objs


def weather_overlay(k, spec, cam):
    """rain streaks or snow flakes on a plane just in front of the lens (scrolls with the frame: a driver on #frame)"""
    kind = spec["type"]; a, b = int(spec.get("from", 1)), int(spec.get("to", ctx.N))
    hw, hh = ctx.frame_half()
    m = bpy.data.materials.new(f"vfx_{kind}{k}"); m.use_nodes = True
    try: m.surface_render_method = 'BLENDED'
    except Exception: pass
    nt = m.node_tree; nt.nodes.clear(); Ln = nt.links
    tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping")
    if kind == "rain":
        mp.inputs["Scale"].default_value = (180.0, 7.0, 1.0); mp.inputs["Rotation"].default_value = (0, 0, math.radians(8))
        tex = nt.nodes.new("ShaderNodeTexNoise"); tex.inputs["Scale"].default_value = 3.0; tex.inputs["Detail"].default_value = 1.0
        ramp = nt.nodes.new("ShaderNodeValToRGB"); ramp.color_ramp.elements[0].position = 0.68; ramp.color_ramp.elements[1].position = 0.74
        rgb = (0.85, 0.9, 1.0); speed = 0.9 * spec.get("intensity", 1.0)
    else:
        mp.inputs["Scale"].default_value = (40.0, 40.0, 1.0)
        tex = nt.nodes.new("ShaderNodeTexVoronoi"); tex.inputs["Scale"].default_value = 4.0; tex.feature = 'F1'
        ramp = nt.nodes.new("ShaderNodeValToRGB"); ramp.color_ramp.elements[0].position = 0.0; ramp.color_ramp.elements[1].position = 0.06
        ramp.color_ramp.elements[0].color = (1, 1, 1, 1); ramp.color_ramp.elements[1].color = (0, 0, 0, 1)
        rgb = (1.0, 1.0, 1.0); speed = 0.05 * spec.get("intensity", 1.0)
    e = nt.nodes.new("ShaderNodeEmission"); e.inputs[0].default_value = (*rgb, 1)
    tr = nt.nodes.new("ShaderNodeBsdfTransparent"); mx = nt.nodes.new("ShaderNodeMixShader"); mul = nt.nodes.new("ShaderNodeMath"); mul.operation = 'MULTIPLY'
    mul.inputs[1].default_value = spec.get("opacity", 0.35 if kind == "rain" else 0.8)
    o_ = nt.nodes.new("ShaderNodeOutputMaterial")
    Ln.new(tc.outputs["UV"], mp.inputs[0]); Ln.new(mp.outputs[0], tex.inputs["Vector"])
    Ln.new(tex.outputs[0] if kind == "rain" else tex.outputs["Distance"], ramp.inputs[0]); Ln.new(ramp.outputs["Color"], mul.inputs[0])
    Ln.new(mul.outputs[0], mx.inputs[0]); Ln.new(tr.outputs[0], mx.inputs[1]); Ln.new(e.outputs[0], mx.inputs[2]); Ln.new(mx.outputs[0], o_.inputs[0])
    fc = mp.inputs["Location"].driver_add("default_value", 1); fc.driver.expression = f"frame*{speed:.4f}"
    fcx = mp.inputs["Location"].driver_add("default_value", 0); fcx.driver.expression = f"frame*{speed * (0.1 if kind == 'rain' else 0.15):.4f}"
    bpy.ops.mesh.primitive_plane_add(size=1.0); pl = bpy.context.active_object; pl.name = f"vfx_{kind}{k}_plane"
    pl.data.materials.append(m); pl.parent = cam; pl.location = (0, 0, -0.9); pl.scale = (6.0, 6.0 * hh / hw, 1)   # covers any lens >= 10 mm
    geo.vis_track(pl, [(a, b)])
    return [pl]


def grade(shots, cuts_default="day"):
    """per-shot colour grade: insert a Mix (multiply) + Bright/Contrast into the film look, keyed at every shot start"""
    sc = ctx.sc; ng = sc.compositing_node_group
    if ng is None: return
    out = next(n for n in ng.nodes if n.bl_idname == 'NodeGroupOutput'); src = out.inputs[0].links[0].from_socket
    mix = ng.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'
    bc = ng.nodes.new('CompositorNodeBrightContrast')
    ng.links.new(src, mix.inputs[6]); ng.links.new(mix.outputs[2], bc.inputs["Image"]); ng.links.new(bc.outputs["Image"], out.inputs[0])
    for s in shots:
        g = GRADES.get(s.get("grade", cuts_default), GRADES["day"])
        for f in (s["a"],):
            mix.inputs[0].default_value = g[1]; mix.inputs[7].default_value = (*g[0], 1)
            bc.inputs["Bright"].default_value = g[2]; bc.inputs["Contrast"].default_value = g[3]
            for sock in (mix.inputs[0], mix.inputs[7], bc.inputs["Bright"], bc.inputs["Contrast"]):
                sock.keyframe_insert("default_value", frame=f)
    try:
        ad = ng.animation_data
        if ad and ad.action:
            from .timing import fcurves_of
            for fcv in fcurves_of(ng):
                for kp in fcv.keyframe_points: kp.interpolation = 'CONSTANT'
    except Exception:
        pass


def build(vfx, factions=None, cam=None, seed=17):
    """-> list of objects to keep out of ink outlines (noline)"""
    rnd = random.Random(seed); noline = []
    for k, sp in enumerate(vfx or []):
        t = sp["type"]
        if t == "smoke": noline += smoke(k, sp, rnd)
        elif t == "dust": noline += smoke(k, sp, rnd, dust=True)
        elif t == "fire": noline += fire(k, sp, rnd)
        elif t == "arrows": noline += arrows(k, sp, rnd)
        elif t == "sparks": noline += sparks(k, sp, rnd)
        elif t == "banner": banner(k, sp, rnd, factions)              # 3D cloth keeps its ink outline
        elif t == "light_shafts": noline += light_shafts(k, sp, rnd)
        elif t in ("rain", "snow"): noline += weather_overlay(k, sp, cam or ctx.cam)
        else: raise ValueError(f"vfx[{k}]: unknown type {t!r}")
    return noline
