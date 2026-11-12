"""Materials, sky, sun, GPU ink outlines and the compositor film look (v2 toolkit).

Every material constructor caches by name: the name is the key, so a set and a prop
asking for "leaf" share one material (first caller's colour wins)."""
import math
import bpy
from mathutils import Matrix
from . import ctx

MATS = {}
INK_HULL = None


def reset():
    global INK_HULL
    MATS.clear(); INK_HULL = None


# ---------------- materials ----------------
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
    if name in MATS: return MATS[name]
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    MATS[name] = m
    return m


def warm_top(m, tint=(1.34, 1.0, 0.58)):
    """cancel the blue sky tint on faces that look up (stone tops, table tops, bread): multiply the base colour by a warm
    tint weighted by the world normal's Z. Works on pbr/ramp_mat materials; safe to call twice. Shorts never call it."""
    if m is None or not m.use_nodes or m.get("warm_top"): return m
    nt = m.node_tree; L = nt.links
    b = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if b is None: return m
    inp = b.inputs["Base Color"]
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.clamp_result = True
    if inp.links: L.new(inp.links[0].from_socket, mix.inputs[6])
    else: mix.inputs[6].default_value = inp.default_value[:]
    mix.inputs[7].default_value = (*tint, 1)
    geo = nt.nodes.new("ShaderNodeNewGeometry"); sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    L.new(geo.outputs["Normal"], sep.inputs[0])
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs[1].default_value, mr.inputs[2].default_value = 0.2, 0.95
    L.new(sep.outputs[2], mr.inputs[0]); L.new(mr.outputs[0], mix.inputs[0])
    L.new(mix.outputs[2], inp)
    m["warm_top"] = 1
    return m


def ramp_mat(name, stops, tex="noise", scale=1.0, coord="Object", bump=0.0, rough=0.9,
             wave_dir='Z', distortion=2.0, detail=4.0, mapping_scale=(1, 1, 1), voronoi=False):
    if name in MATS: return MATS[name]
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
    MATS[name] = m
    return m


def setmat(o, m):
    o.data.materials.clear(); o.data.materials.append(m); return o


def window_mat(name, wall, glass, scale=(2.2, 1.0)):
    """building facade: brick texture used as a window grid"""
    if name in MATS: return MATS[name]
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; L = nt.links; b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.7
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1, 1, 1)
    L.new(geo.outputs["Position"], mp.inputs[0])
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); L.new(mp.outputs[0], sep.inputs[0])
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    add = nt.nodes.new("ShaderNodeMath"); add.operation = 'ADD'
    L.new(sep.outputs[0], add.inputs[0]); L.new(sep.outputs[1], add.inputs[1])
    L.new(add.outputs[0], comb.inputs[0]); L.new(sep.outputs[2], comb.inputs[1])
    br = nt.nodes.new("ShaderNodeTexBrick"); br.offset = 0.0; br.squash = 1.0
    br.inputs["Color1"].default_value = (*glass, 1); br.inputs["Color2"].default_value = (*glass, 1)
    br.inputs["Mortar"].default_value = (*wall, 1)
    br.inputs["Scale"].default_value = 1.0; br.inputs["Mortar Size"].default_value = 0.35
    br.inputs["Brick Width"].default_value = scale[0]; br.inputs["Row Height"].default_value = scale[1] * 1.4
    br.inputs["Mortar Smooth"].default_value = 0.0
    L.new(comb.outputs[0], br.inputs["Vector"])
    L.new(br.outputs["Color"], b.inputs["Base Color"])
    MATS[name] = m
    return m


def iron_mat(name, kind):
    if name in MATS: return MATS[name]
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; L = nt.links; b = nt.nodes["Principled BSDF"]
    b.inputs["Metallic"].default_value = 0.6; b.inputs["Roughness"].default_value = 0.55
    tc = nt.nodes.new("ShaderNodeTexCoord")
    if kind == "rings":
        t = nt.nodes.new("ShaderNodeTexWave"); t.wave_type = 'RINGS'; t.inputs["Scale"].default_value = 3.0
        t.inputs["Distortion"].default_value = 0.0
        L.new(tc.outputs["Object"], t.inputs["Vector"])
    else:
        t = nt.nodes.new("ShaderNodeTexChecker"); t.inputs["Scale"].default_value = 6.0
        L.new(tc.outputs["Generated"], t.inputs["Vector"])
    cr = nt.nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = (0.10, 0.10, 0.11, 1); cr.color_ramp.elements[1].color = (0.22, 0.22, 0.23, 1)
    L.new(t.outputs["Fac"], cr.inputs[0]); L.new(cr.outputs[0], b.inputs["Base Color"])
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.5
    L.new(t.outputs["Fac"], bp.inputs["Height"]); L.new(bp.outputs[0], b.inputs["Normal"])
    MATS[name] = m
    return m


# ---------------- world / light ----------------
SKY_DAY = ((0.98, 0.86, 0.72), (0.62, 0.80, 0.98), (0.16, 0.42, 0.90))   # horizon, 25 %, zenith


def sky_world(colors=SKY_DAY, strength=1.0):
    sc = ctx.sc
    world = bpy.data.worlds.new("Sky"); sc.world = world; world.use_nodes = True
    wn = world.node_tree; wl = wn.links
    bgn = wn.nodes["Background"]
    tco = wn.nodes.new("ShaderNodeTexCoord")
    sxyz = wn.nodes.new("ShaderNodeSeparateXYZ"); wl.new(tco.outputs["Generated"], sxyz.inputs[0])
    mr = wn.nodes.new("ShaderNodeMapRange")
    mr.inputs[1].default_value, mr.inputs[2].default_value = -0.05, 0.75
    wl.new(sxyz.outputs[2], mr.inputs[0])
    skr = wn.nodes.new("ShaderNodeValToRGB"); el = skr.color_ramp.elements
    el[0].position, el[0].color = 0.0, (*colors[0], 1)
    el[1].position, el[1].color = 1.0, (*colors[2], 1)
    e = el.new(0.25); e.color = (*colors[1], 1)
    wl.new(mr.outputs[0], skr.inputs[0]); wl.new(skr.outputs[0], bgn.inputs[0])
    bgn.inputs[1].default_value = strength
    return world


def add_clouds(world, cover=0.5, tint=(0.99, 0.98, 1.0), scale=2.2, seed=0.0):
    """soft cartoon clouds in the world shader (no objects, no render cost): stretched 3D noise on the view direction,
    only in a band above the horizon, soft-edged, slightly shaded underneath. cover 0..1 = how much sky they take"""
    if world is None or not world.use_nodes: return world
    wn = world.node_tree; L = wn.links
    bgn = wn.nodes["Background"]
    if not bgn.inputs[0].links: return world
    sky = bgn.inputs[0].links[0].from_socket
    tco = wn.nodes.new("ShaderNodeTexCoord")
    mp = wn.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (scale, scale, scale * 3.2)
    mp.inputs["Location"].default_value = (seed, seed * 0.7, 0.0)
    L.new(tco.outputs["Generated"], mp.inputs[0])
    nz = wn.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 1.6; nz.inputs["Detail"].default_value = 3.0
    nz.inputs["Roughness"].default_value = 0.55
    L.new(mp.outputs[0], nz.inputs["Vector"])
    thr = 0.62 - 0.14 * cover
    cr = wn.nodes.new("ShaderNodeValToRGB"); el = cr.color_ramp.elements
    el[0].position, el[0].color = thr, (0, 0, 0, 1); el[1].position, el[1].color = thr + 0.06, (1, 1, 1, 1)
    L.new(nz.outputs["Fac"], cr.inputs[0])
    sep = wn.nodes.new("ShaderNodeSeparateXYZ"); L.new(tco.outputs["Generated"], sep.inputs[0])
    band = wn.nodes.new("ShaderNodeMapRange"); band.inputs[1].default_value, band.inputs[2].default_value = 0.02, 0.14
    L.new(sep.outputs[2], band.inputs[0])
    top = wn.nodes.new("ShaderNodeMapRange"); top.inputs[1].default_value, top.inputs[2].default_value = 0.75, 0.45
    L.new(sep.outputs[2], top.inputs[0])
    m1 = wn.nodes.new("ShaderNodeMath"); m1.operation = 'MULTIPLY'; L.new(cr.outputs[0], m1.inputs[0]); L.new(band.outputs[0], m1.inputs[1])
    m2 = wn.nodes.new("ShaderNodeMath"); m2.operation = 'MULTIPLY'; L.new(m1.outputs[0], m2.inputs[0]); L.new(top.outputs[0], m2.inputs[1])
    shade = wn.nodes.new("ShaderNodeMix"); shade.data_type = 'RGBA'          # greyer, bluer underside near the horizon
    shade.inputs[6].default_value = (tint[0] * 0.80, tint[1] * 0.83, tint[2] * 0.92, 1); shade.inputs[7].default_value = (*tint, 1)
    L.new(band.outputs[0], shade.inputs[0])
    mix = wn.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'
    L.new(m2.outputs[0], mix.inputs[0]); L.new(sky, mix.inputs[6]); L.new(shade.outputs[2], mix.inputs[7])
    L.new(mix.outputs[2], bgn.inputs[0])
    return world


def ground_variation(m, scale=0.035, amount=1.6):
    """big soft patches on a ground/hill material (darker cool, lighter warm), so a meadow reads like real fields
    instead of one flat green; safe to call twice"""
    if m is None or not m.use_nodes or m.get("ground_var"): return m
    nt = m.node_tree; L = nt.links
    b = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if b is None: return m
    inp = b.inputs["Base Color"]
    geo_ = nt.nodes.new("ShaderNodeNewGeometry")
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = scale; nz.inputs["Detail"].default_value = 2.0
    L.new(geo_.outputs["Position"], nz.inputs["Vector"])
    cr = nt.nodes.new("ShaderNodeValToRGB"); el = cr.color_ramp.elements
    lo = 1 - 0.16 * amount; hi = 1 + 0.14 * amount
    el[0].position, el[0].color = 0.32, (lo * 0.95, lo, lo * 0.98, 1)
    el[1].position, el[1].color = 0.68, (hi * 1.06, hi * 1.03, hi * 0.86, 1)
    mid = el.new(0.5); mid.color = (1, 1, 1, 1)
    L.new(nz.outputs["Fac"], cr.inputs[0])
    fine = nt.nodes.new("ShaderNodeTexNoise"); fine.inputs["Scale"].default_value = scale * 28; fine.inputs["Detail"].default_value = 4.0
    L.new(geo_.outputs["Position"], fine.inputs["Vector"])
    fr = nt.nodes.new("ShaderNodeValToRGB"); fe = fr.color_ramp.elements                   # a grassy grain, +-6 %
    fe[0].position, fe[0].color = 0.35, (0.94, 0.94, 0.94, 1); fe[1].position, fe[1].color = 0.65, (1.06, 1.06, 1.02, 1)
    L.new(fine.outputs["Fac"], fr.inputs[0])
    both = nt.nodes.new("ShaderNodeMix"); both.data_type = 'RGBA'; both.blend_type = 'MULTIPLY'; both.inputs[0].default_value = 1.0
    L.new(cr.outputs[0], both.inputs[6]); L.new(fr.outputs[0], both.inputs[7])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs[0].default_value = 1.0
    if inp.links: L.new(inp.links[0].from_socket, mix.inputs[6])
    else: mix.inputs[6].default_value = inp.default_value[:]
    L.new(both.outputs[2], mix.inputs[7]); L.new(mix.outputs[2], inp)
    m["ground_var"] = 1
    return m


def sun_light(energy=3.2, color=(1.0, 0.93, 0.82), angle_deg=4, rot_deg=(48, -28, -35)):
    sun_d = bpy.data.lights.new("Sun", 'SUN'); sun_d.energy = energy; sun_d.color = color; sun_d.angle = math.radians(angle_deg)
    sun = bpy.data.objects.new("Sun", sun_d); ctx.col.objects.link(sun)
    sun.rotation_euler = tuple(math.radians(a) for a in rot_deg)
    return sun


# ---------------- film look: outlines, bloom, mist, vignette, colour ----------------
def setup_look(noline_objs):
    sc, col = ctx.sc, ctx.col
    vl = sc.view_layers[0]
    nol = bpy.data.collections.new("NOLINE"); sc.collection.children.link(nol)
    for o in noline_objs:
        if o.name not in nol.objects: nol.objects.link(o)
        if o.name in col.objects: col.objects.unlink(o)
    # Freestyle is CPU-bound (~40 s/frame on this scene) -> GPU inverted-hull outlines instead
    sc.render.use_freestyle = False
    add_ink_outlines([o for o in sc.objects if o.type == 'MESH' and o.name not in nol.objects])
    sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.45
    vl.use_pass_mist = True
    sc.world.mist_settings.start = 14; sc.world.mist_settings.depth = 110; sc.world.mist_settings.falloff = 'QUADRATIC'
    ng = bpy.data.node_groups.new("FilmLook", 'CompositorNodeTree')
    ng.interface.new_socket("Image", in_out='OUTPUT', socket_type='NodeSocketColor')
    n = ng.nodes; L = ng.links
    rl = n.new('CompositorNodeRLayers')
    gl = n.new('CompositorNodeGlare'); gl.inputs["Type"].default_value = 'Bloom'
    gl.inputs["Threshold"].default_value = 0.92; gl.inputs["Strength"].default_value = 0.35; gl.inputs["Size"].default_value = 0.6
    mist = n.new('ShaderNodeMix'); mist.data_type = 'RGBA'; mist.blend_type = 'MIX'
    mfac = n.new('ShaderNodeMath'); mfac.operation = 'MULTIPLY'; mfac.inputs[1].default_value = 0.45
    hs = n.new('CompositorNodeHueSat'); hs.inputs["Saturation"].default_value = 1.10
    bc = n.new('CompositorNodeBrightContrast'); bc.inputs["Contrast"].default_value = 6.0
    em = n.new('CompositorNodeEllipseMask'); em.inputs["Size"].default_value = (1.05, 1.15)
    bl = n.new('CompositorNodeBlur'); bl.inputs["Size"].default_value = (180, 180)
    inv = n.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
    vf = n.new('ShaderNodeMath'); vf.operation = 'MULTIPLY'; vf.inputs[1].default_value = 0.38
    vig = n.new('ShaderNodeMix'); vig.data_type = 'RGBA'; vig.blend_type = 'MULTIPLY'
    vig.inputs[7].default_value = (0.0, 0.0, 0.0, 1.0)
    out = n.new('NodeGroupOutput')
    L.new(rl.outputs["Image"], gl.inputs["Image"])
    L.new(rl.outputs["Mist"], mfac.inputs[0]); L.new(mfac.outputs[0], mist.inputs[0])
    L.new(gl.outputs["Image"], mist.inputs[6]); mist.inputs[7].default_value = (0.78, 0.86, 0.95, 1.0)
    L.new(mist.outputs[2], hs.inputs["Image"]); L.new(hs.outputs["Image"], bc.inputs["Image"])
    L.new(em.outputs["Mask"], bl.inputs["Image"]); L.new(bl.outputs["Image"], inv.inputs[1]); L.new(inv.outputs[0], vf.inputs[0])
    L.new(vf.outputs[0], vig.inputs[0]); L.new(bc.outputs["Image"], vig.inputs[6])
    L.new(vig.outputs[2], out.inputs[0])
    sc.compositing_node_group = ng
    gpu_compositor(sc)
    sc.render.motion_blur_position = 'START'
    return ng


def gpu_compositor(sc):
    """run the compositor (bloom, vignette blur, grade, caption overlay) on the graphics card: on the user's NVIDIA
    machine this was ~1/4 of the frame time on the CPU. Windows only by default (the cloud container has no GPU);
    WHYSHORTS_GPU_COMPOSITOR=1/0 forces it."""
    import os
    want = os.environ.get("WHYSHORTS_GPU_COMPOSITOR")
    on = want == "1" if want in ("0", "1") else os.name == "nt"
    if not on: return
    try: sc.render.compositor_device = 'GPU'
    except Exception: pass


def add_ink_outlines(objs):
    """cartoon outlines that render on the GPU: solidify shell, normals flipped, back faces culled"""
    global INK_HULL
    if INK_HULL is None:
        INK_HULL = bpy.data.materials.new("ink_hull"); INK_HULL.use_nodes = True
        nt = INK_HULL.node_tree; nt.nodes.clear()
        e = nt.nodes.new("ShaderNodeEmission"); e.inputs[0].default_value = (0.05, 0.04, 0.04, 1)
        o_ = nt.nodes.new("ShaderNodeOutputMaterial"); nt.links.new(e.outputs[0], o_.inputs[0])
        INK_HULL.use_backface_culling = True
    done = set()
    for o in objs:
        dims = o.dimensions
        if max(dims) > 150 or min(dims) < 0.003 and max(dims) > 50:   # ground planes and the like
            continue
        if o.data.name in done or o.data.users > 1:
            continue
        if any(m.type in ('ARRAY', 'DISPLACE', 'SUBSURF') for m in o.modifiers):
            pass
        elif tuple(o.scale) != (1.0, 1.0, 1.0):                       # bake scale so the shell is even
            o.data.transform(Matrix.Diagonal((*o.scale, 1.0))); o.scale = (1, 1, 1)
        size = max(o.dimensions)
        t = 0.012 if size < 0.6 else 0.02 if size < 2.5 else 0.045 if size < 20 else 0.25
        o.data.materials.append(INK_HULL)
        sol = o.modifiers.new("ink", 'SOLIDIFY'); sol.thickness = t; sol.offset = 1.0
        sol.use_flip_normals = True; sol.material_offset = len(o.data.materials) - 1; sol.use_rim = False
        done.add(o.data.name)


def descendants(o):
    return [o] + list(o.children_recursive)
