# ---------------- easing ----------------
def clamp01(u): return max(0.0, min(1.0, u))
def ease(u): u = clamp01(u); return u * u * (3 - 2 * u)
def ease_out_back(u, s=1.4):                 # overshoot then settle: gestures, pops, punch-ins
    u = clamp01(u) - 1; return u * u * ((s + 1) * u + s) + 1
def ease_out_elastic(u):
    u = clamp01(u)
    if u in (0.0, 1.0): return u
    return 2 ** (-10 * u) * math.sin((u * 10 - 0.75) * (2 * math.pi) / 3) + 1
def pease(f, a, n=8): return ease_out_back((f - a) / n)     # pose transition with overshoot
def noise1(t, seed=0.0):
    return (math.sin(t * 1.3 + seed) * 0.5 + math.sin(t * 2.7 + seed * 1.7) * 0.3 + math.sin(t * 5.1 + seed * 2.3) * 0.2)

# ---------------- voice amplitude (lip flap, head bobs) ----------------
def load_amplitude(path, n_frames, fps):
    amp = [0.0] * (n_frames + 2)
    try:
        with wave.open(path, "rb") as w:
            sr = w.getframerate(); ch = w.getnchannels(); sw = w.getsampwidth()
            raw = w.readframes(w.getnframes())
        x = np.frombuffer(raw, dtype=np.int16 if sw == 2 else np.int32).astype(np.float64)
        if ch > 1: x = x.reshape(-1, ch).mean(axis=1)
        x /= np.abs(x).max() + 1e-9
        hop = sr / fps
        for f in range(1, n_frames + 1):
            seg = x[int((f - 1) * hop):int(f * hop)]
            if len(seg):
                db = 20 * math.log10(math.sqrt(float(np.mean(seg ** 2))) + 1e-6)
                amp[f] = clamp01((db + 38) / 26)
    except Exception as e:
        for f in range(1, n_frames + 1):
            amp[f] = clamp01(0.5 + 0.5 * math.sin(f * 1.9) * math.sin(f * 0.7))
    return amp

# ---------------- dust puffs (pooled billboards) ----------------
PUFF_M = flat("puff_fill", (0.93, 0.90, 0.85))
PUFF_POOL = []; PUFF_EVENTS = []
def _make_puff(i):
    root = empty(f"puff_root{i}", None, (0, 0, -20))
    lt = root.constraints.new('LOCKED_TRACK'); lt.target = cam; lt.track_axis = 'TRACK_NEGATIVE_Y'; lt.lock_axis = 'LOCK_Z'
    pl = empty(f"puff_pl{i}", root); pl.rotation_euler = (math.pi / 2, 0, 0)
    for k, (dx_, dy_, r) in enumerate(((0, 0, 0.12), (0.09, 0.05, 0.09), (-0.08, 0.06, 0.08))):
        shape(pl, f"puff{i}_{k}", ellipse(dx_, dy_, r, r, 18), PUFF_M, 0.01 * k, outline=0.022)
    root.scale = (0, 0, 0)
    return root
def dust_burst(frame, pos, n=8, radius=0.7, size=1.0, life=20, rise=0.35):
    rnd = random.Random(frame * 7 + int(pos[0] * 13))
    for k in range(n):
        a = 2 * math.pi * k / n + rnd.uniform(-0.3, 0.3)
        PUFF_EVENTS.append((frame + rnd.randint(0, 2), pos, (math.cos(a), math.sin(a)), radius * rnd.uniform(0.7, 1.2),
                            size * rnd.uniform(0.7, 1.3), life + rnd.randint(-3, 4), rise * rnd.uniform(0.6, 1.4)))
def bake_dust():
    busy = []
    for ev in sorted(PUFF_EVENTS):
        f0, pos, d, rad, sz, life, rise = ev
        idx = next((i for i, (p, free) in enumerate(busy) if free < f0 - 2), None)
        if idx is None:
            PUFF_POOL.append(_make_puff(len(PUFF_POOL))); busy.append((len(PUFF_POOL) - 1, 0)); idx = len(busy) - 1
        pidx = busy[idx][0]; busy[idx] = (pidx, f0 + life + 1); o = PUFF_POOL[pidx]
        o.scale = (0, 0, 0); o.keyframe_insert("scale", frame=max(1, f0 - 1))
        for f in range(f0, min(N, f0 + life) + 1):
            u = (f - f0) / life; e = ease_out_back(u * 1.6, 1.0) if u < 0.62 else 1.0
            s = sz * (0.35 + 0.9 * e) * (1 - ease((u - 0.55) / 0.45))
            o.location = (pos[0] + d[0] * rad * ease(u * 1.3), pos[1] + d[1] * rad * ease(u * 1.3), pos[2] + 0.08 + rise * ease(u))
            o.scale = (s, s, s); o.keyframe_insert("scale", frame=f); o.keyframe_insert("location", frame=f)
        if f0 + life + 1 <= N:
            o.scale = (0, 0, 0); o.keyframe_insert("scale", frame=f0 + life + 1)

# ---------------- shock lines + "!" ----------------
def add_reaction_fx(c):
    sl = empty(c.name + "_speedlines", c.head, (0, 0, -0.3))
    for k in range(16):
        a = 2 * math.pi * k / 16; r0, r1 = 0.62, 0.95 + 0.12 * (k % 2); w_ = 0.035
        p0 = (r0 * math.cos(a), r0 * math.sin(a)); p1 = (r1 * math.cos(a), r1 * math.sin(a))
        nx, ny = -math.sin(a) * w_, math.cos(a) * w_
        shape(sl, f"{c.name}_sl{k}", [(p0[0] + nx * 0.3, p0[1] + ny * 0.3), (p1[0] + nx, p1[1] + ny), (p1[0] - nx, p1[1] - ny), (p0[0] - nx * 0.3, p0[1] - ny * 0.3)], INK, 0, outline=0)
    sl.scale = (0, 0, 0); c.speedlines = sl
    ex = empty(c.name + "_excl", c.head, (0.58, 0.62, 0.4))
    for layer, (m, off, z) in enumerate(((INK, 0.05, -0.01), (flat("excl_red", (0.92, 0.1, 0.08)), 0.0, 0.0))):
        cu = bpy.data.curves.new(f"{c.name}_ex{layer}", 'FONT'); cu.body = "!"; cu.size = 0.45; cu.offset = off
        cu.align_x = 'CENTER'; cu.align_y = 'CENTER'
        if FONT_PATH: cu.font = bpy.data.fonts.load(FONT_PATH, check_existing=True)
        o = bpy.data.objects.new(f"{c.name}_ex{layer}", cu); col.objects.link(o); o.parent = ex; o.location = (0, 0, z)
        o.rotation_euler = (0, 0, -0.2); o.data.materials.append(m)
    ex.scale = (0, 0, 0); c.excl = ex
def bake_reaction_fx(c, frames, dur=16):
    for o_ in (c.speedlines, c.excl):
        o_.scale = (0, 0, 0); o_.keyframe_insert("scale", frame=1)
    for f0 in frames:
        for f in range(f0, min(N, f0 + dur) + 1):
            u = (f - f0) / dur
            s_l = ease_out_back(u * 4, 2.0) * (1 - ease((u - 0.6) / 0.4))
            c.speedlines.scale = (s_l, s_l, 1); c.speedlines.rotation_euler = (0, 0, 0.15 * math.sin(f * 1.3))
            s_e = ease_out_back(u * 3, 2.2) * (1 - ease((u - 0.75) / 0.25))
            c.excl.scale = (s_e, s_e, 1); c.excl.location = (0.58, 0.62 + 0.08 * ease(u), 0.4)
            for o_ in (c.speedlines, c.excl): o_.keyframe_insert("scale", frame=f)
            c.speedlines.keyframe_insert("rotation_euler", frame=f); c.excl.keyframe_insert("location", frame=f)
        for o_ in (c.speedlines, c.excl):
            o_.scale = (0, 0, 0); o_.keyframe_insert("scale", frame=min(N, f0 + dur + 1))

# ---------------- talking mouth ----------------
def add_talk_mouth(c, ey=-0.02):
    g = empty(c.name + "_talk", c.head, (0, 0, 0.14))
    shape(g, c.name + "_talk_patch", ellipse(0, ey - 0.17, 0.22, 0.12, 24), c.skin, 0, outline=0)
    piv = empty(c.name + "_talk_piv", g, (0, ey - 0.17, 0.02))
    shape(piv, c.name + "_talk_m", ellipse(0, 0, 0.12, 0.10, 24), MOUTH, 0, outline=0.03)
    shape(piv, c.name + "_talk_t", ellipse(0, -0.05, 0.06, 0.035, 16), TONGUE, 0.02, outline=0)
    shape(piv, c.name + "_talk_teeth", rrect(0, 0.065, 0.14, 0.035, 0.01), TEETH, 0.02, outline=0)
    c.talk = g; c.talk_piv = piv
def bake_talk(c, ranges, amp):            # needs vis_track() from the animation part
    vis_track(c.talk, ranges)
    for f in range(1, N + 1):
        on = any(a <= f <= b for a, b in ranges)
        o = 0.18 + 0.82 * amp[f] if on else 0.2
        c.talk_piv.scale = (0.9 + 0.15 * o, o, 1); c.talk_piv.keyframe_insert("scale", frame=f)

# ---------------- reactions (squash & stretch) ----------------
def react_offsets(c, f):
    dy, sy, lean = 0.0, 1.0, 0.0
    for t0, kind in getattr(c, "reacts", []):
        if kind == "hop" and t0 - 4 <= f <= t0 + 16:
            if f < t0: sy -= 0.10 * ease((f - (t0 - 4)) / 4)
            else:
                u = (f - t0) / 16
                dy += 0.22 * math.sin(math.pi * min(1, u / 0.8)) if u < 0.8 else 0.0
                if u < 0.25: sy += 0.12 * (1 - u / 0.25)
                elif u > 0.8: sy -= 0.12 * math.sin(math.pi * (u - 0.8) / 0.2)
        elif kind == "flinch" and t0 <= f <= t0 + 20:
            u = (f - t0) / 20; lean += -0.18 * (1 - ease_out_elastic(u)); sy -= 0.05 * (1 - ease(u))
        elif kind == "shiver" and t0 <= f <= t0 + 30:
            lean += 0.04 * math.sin(f * 2.4) * (1 - (f - t0) / 30)
        elif kind == "proud" and t0 <= f <= t0 + 14:
            u = (f - t0) / 14; sy += 0.07 * math.sin(math.pi * u); dy += 0.04 * math.sin(math.pi * u)
    return dy, sy, lean

# ---------------- pose_char v2 (replaces v1; arms accept ('ang', a1, a2) or ('ik', (x, y), bend)) ----------------
def ik(sh, tgt, L1, L2, bend=1):
    dx, dy = tgt[0] - sh[0], tgt[1] - sh[1]
    d = max(min(math.hypot(dx, dy), L1 + L2 - 1e-3), abs(L1 - L2) + 1e-3)
    base = math.atan2(dx, -dy)
    off = math.acos(max(-1, min(1, (L1 * L1 + d * d - L2 * L2) / (2 * L1 * d))))
    a1 = base + bend * off
    ex, ey_ = sh[0] + L1 * math.sin(a1), sh[1] - L1 * math.cos(a1)
    return a1, math.atan2(tgt[0] - ex, -(tgt[1] - ey_)) - a1
def pose_char(c, f, armL=None, armR=None, legL=(-0.06, 0.02), legR=(0.06, -0.02), head_tilt=0.0, body=(0, 0), breath=True, lean=0.0):
    if not hasattr(c, "prev"): c.prev = {}; c.vel = {}
    for side, spec, lp in (("L", armL, c.armL), ("R", armR, c.armR)):
        if spec is None: spec = ('ang', -0.25 if side == "L" else 0.25, 0.1 if side == "L" else -0.1)
        a1, a2 = ik(c.sh[side], spec[1], c.aL[0], c.aL[1], spec[2]) if spec[0] == 'ik' else (spec[1], spec[2])
        v = a1 - c.prev.get(side, a1); c.vel[side] = 0.55 * c.vel.get(side, 0.0) + 0.45 * v; c.prev[side] = a1
        a2 = a2 - max(-0.5, min(0.5, 1.6 * c.vel[side]))            # forearm drags behind
        lp[0].rotation_euler = (0, 0, a1); lp[1].rotation_euler = (0, 0, a2)
        lp[0].keyframe_insert("rotation_euler", frame=f); lp[1].keyframe_insert("rotation_euler", frame=f)
        c.hist.setdefault(side, []).append((f, a1 + 0.5 * a2))
    for spec, lp in ((legL, c.legL), (legR, c.legR)):
        lp[0].rotation_euler = (0, 0, spec[0]); lp[1].rotation_euler = (0, 0, spec[1])
        lp[0].keyframe_insert("rotation_euler", frame=f); lp[1].keyframe_insert("rotation_euler", frame=f)
    t = f / FPS
    dy, sy, rlean = react_offsets(c, f)
    b = (1 + (0.014 * math.sin(t * 2.4 + len(c.name)) if breath else 0)) * sy
    sway = 0.02 * noise1(t * 0.8, len(c.name))
    c.body.scale = (1 / math.sqrt(b), b, 1); c.body.location = (body[0], body[1] + dy, 0)
    c.body.rotation_euler = (0, 0, lean + rlean + sway)
    c.body.keyframe_insert("scale", frame=f); c.body.keyframe_insert("location", frame=f); c.body.keyframe_insert("rotation_euler", frame=f)
    lag = getattr(c, "lag_tilt", 0.0)
    c.lag_tilt = lag + 0.35 * (-(lean + rlean) * 0.6 - lag)
    talk = getattr(c, "amp_now", 0.0)
    c.head.rotation_euler = (0, 0, head_tilt + 0.03 * math.sin(t * 1.7) + c.lag_tilt + 0.05 * talk * math.sin(f * 0.9))
    c.head.keyframe_insert("rotation_euler", frame=f)

# ---------------- film look + GPU outlines ----------------
INK_HULL = None
def add_ink_outlines(objs):
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
        if max(dims) > 150 or min(dims) < 0.003 and max(dims) > 50: continue    # ground planes
        if o.data.name in done or o.data.users > 1: continue
        if not any(m.type in ('ARRAY', 'DISPLACE', 'SUBSURF') for m in o.modifiers) and tuple(o.scale) != (1.0, 1.0, 1.0):
            o.data.transform(Matrix.Diagonal((*o.scale, 1.0))); o.scale = (1, 1, 1)
        size = max(o.dimensions)
        t = 0.012 if size < 0.6 else 0.02 if size < 2.5 else 0.045 if size < 20 else 0.25
        o.data.materials.append(INK_HULL)
        sol = o.modifiers.new("ink", 'SOLIDIFY'); sol.thickness = t; sol.offset = 1.0
        sol.use_flip_normals = True; sol.material_offset = len(o.data.materials) - 1; sol.use_rim = False
        done.add(o.data.name)
def setup_look(noline_objs):
    vl = sc.view_layers[0]
    nol = bpy.data.collections.new("NOLINE"); sc.collection.children.link(nol)
    for o in noline_objs:
        if o.name not in nol.objects: nol.objects.link(o)
        if o.name in col.objects: col.objects.unlink(o)
    sc.render.use_freestyle = False
    add_ink_outlines([o for o in sc.objects if o.type == 'MESH' and o.name not in nol.objects])
    sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.45; sc.render.motion_blur_position = 'START'
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
def descendants(o): return [o] + list(o.children_recursive)

# ---------------- motion-blur hold keys (Blender 5 layered actions) ----------------
def fcurves_of(idb):
    ad = idb.animation_data
    if not ad or not ad.action: return []
    act = ad.action
    if hasattr(act, "fcurves"): return list(act.fcurves)
    out_ = []
    for layer in act.layers:
        for strip in layer.strips:
            cb = strip.channelbag(ad.action_slot)
            if cb: out_ += list(cb.fcurves)
    return out_
def add_teleport_holds(objs, thr=0.6):
    for o in objs:
        for fc in fcurves_of(o):
            if fc.data_path != "location": continue
            pts = sorted((kp.co[0], kp.co[1]) for kp in fc.keyframe_points)
            for (f0, v0), (f1, v1) in zip(pts, pts[1:]):
                if f1 - f0 >= 0.99 and abs(v1 - v0) > thr:
                    fc.keyframe_points.insert(f0 + 0.98, v0, options={'FAST'})
            fc.update()
