"""3D marble bust of a generic (non-portrait) Roman emperor on a tall square stone pedestal.
Origin = centre of the bottom of the pedestal; face looks toward -Y.  Pedestal 1.2 high, total about 2.1.
Parts: pedestal (group: plinth, shaft, cap), plaque (blank front plate), bust (group: socle, chest, drape,
neck, head), head (group pivoting at the neck, z=1.72: skull, jaw, hair, nose, ears, brow, eyes, mouth, beard),
hair, nose, beard (only when beard='full': ONE mesh '<name>_beard' with its origin at the chin so a story can
scale it 0 -> 1 for a 'beard pops out' gag).
seed varies hair style (3 lock patterns), hairline, nose, ears, brow and head width so a row of busts differs.
Marble is warm ivory on purpose: the blue sky gradient tints upward faces, neutral white turns grey-blue."""
import math
import random
import bmesh
from mathutils import Matrix, Euler, Vector
from core.look import ramp_mat, pbr
from core.geo import group3d, attach, rbox, lathe, cyl, sphere

DEFAULTS = dict(beard="none", seed=1, eyes="drilled", plaque=True,
                marble_color=[0.90, 0.76, 0.56], pedestal_color=[0.50, 0.38, 0.27],
                pupil_color=[0.36, 0.25, 0.15])

HZ = 1.72          # head pivot (top of neck)


def _clamp(c, k):
    return tuple(min(1.0, max(0.0, float(v) * k)) for v in c)


def _key(c):
    return "_".join(f"{float(v):.2f}" for v in c)


def _ell(name, loc, rad, m, rot=None):
    """ellipsoid with the radii baked into the mesh (object scale stays 1 so stories can animate scale)"""
    o = sphere(name, loc, 1.0, m)
    o.data.transform(Matrix.Diagonal((rad[0], rad[1], rad[2], 1.0)))
    if rot:
        o.data.transform(Euler(rot).to_matrix().to_4x4())
    o.scale = (1, 1, 1)
    return o


def _ell_front(cx, cy, cz, rx, ry, rz):
    """front (-Y) surface of an ellipsoid as y(x, z); returns None outside the silhouette"""
    def f(x, z):
        q = 1.0 - ((x - cx) / rx) ** 2 - ((z - cz) / rz) ** 2
        if q <= 0: return None
        return cy - ry * math.sqrt(q)
    return f


def _hug(o, surf, out=0.0, fallback=0.0):
    """bend a small feature built around its own centre so it sits on a curved front surface"""
    x0, y0, z0 = o.location
    for v in o.data.vertices:
        xw = x0 + v.co.x; zw = z0 + v.co.z
        s = surf(xw, zw)
        if s is None: s = fallback
        v.co.y = s - out + v.co.y - y0
    o.data.update()


def _add_balls(o, balls, segs=(12, 8)):
    """merge extra small spheres/ellipsoids (local coords) into the mesh of o"""
    bm = bmesh.new(); bm.from_mesh(o.data)
    for (p, rad) in balls:
        M = Matrix.Translation(Vector(p)) @ Matrix.Diagonal((rad[0], rad[1], rad[2], 1.0))
        bmesh.ops.create_uvsphere(bm, u_segments=segs[0], v_segments=segs[1], radius=1.0, matrix=M)
    bm.to_mesh(o.data); bm.free()
    for poly in o.data.polygons: poly.use_smooth = True
    o.data.update()


def _to_head(o, head):
    """re-parent a part built in world coordinates under the head group (pivot at z=HZ)"""
    o.location = (o.location[0], o.location[1], o.location[2] - HZ)
    o.parent = head
    return o


def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    name = p["name"]
    rng = random.Random(int(p["seed"]))
    beard = str(p["beard"]).lower() == "full"

    mc = p["marble_color"]; pc = p["pedestal_color"]
    m_marble = ramp_mat(f"emperor_bust_body_{_key(mc)}", [(0.35, _clamp(mc, 0.94)), (0.75, _clamp(mc, 1.04))],
                        scale=3.0, bump=0.04, rough=0.6)
    m_hair = ramp_mat(f"emperor_bust_hair_{_key(mc)}", [(0.35, _clamp(mc, 0.86)), (0.75, _clamp(mc, 0.97))],
                      scale=6.0, bump=0.08, rough=0.65)
    m_ped = ramp_mat(f"emperor_bust_pedestal_{_key(pc)}", [(0.3, _clamp(pc, 0.82)), (0.72, _clamp(pc, 1.12))],
                     scale=5.0, bump=0.18, rough=0.85)
    m_plaque = pbr(f"emperor_bust_plaque_{_key(pc)}", _clamp(pc, 1.3), rough=0.7)
    m_dark = pbr(f"emperor_bust_pupil_{_key(p['pupil_color'])}", tuple(float(v) for v in p["pupil_color"]), rough=0.9)

    root = group3d(name)

    # ---------------- pedestal (0 .. 1.2) ----------------
    ped = group3d(f"{name}_pedestal"); attach(root, ped)
    plinth = rbox(f"{name}_plinth", (0, 0, 0.07), (0.86, 0.86, 0.14), m_ped, radius=0.03)
    shaft = rbox(f"{name}_shaft", (0, 0, 0.60), (0.66, 0.66, 0.94), m_ped, radius=0.025)
    cap = rbox(f"{name}_cap", (0, 0, 1.13), (0.84, 0.84, 0.14), m_ped, radius=0.03)
    attach(ped, plinth, shaft, cap)
    if p["plaque"]:
        plq = rbox(f"{name}_plaque", (0, -0.335, 0.66), (0.42, 0.03, 0.26), m_plaque, radius=0.012)
        attach(root, plq)

    # ---------------- bust ----------------
    bust = group3d(f"{name}_bust"); attach(root, bust)
    socle = lathe(f"{name}_socle", (0, 0, 0),
                  [(0.0, 1.2), (0.20, 1.2), (0.20, 1.235), (0.16, 1.26), (0.11, 1.30), (0.13, 1.32), (0.0, 1.335)],
                  m_marble, segments=40)
    CH = (0.0, 0.0, 1.52); CR = (0.40, 0.22, 0.24)
    chest = _ell(f"{name}_chest", CH, CR, m_marble)
    zcut = 1.33 - CH[2]
    for v in chest.data.vertices:            # flat bottom like a real bust
        if v.co.z < zcut: v.co.z = zcut
    chest.data.update()
    chest_front = _ell_front(CH[0], CH[1], CH[2], *CR)
    drape = _ell(f"{name}_drape", (0.04, 0.0, 1.50), (0.26, 0.04, 0.065), m_marble, rot=(0, math.radians(-35), 0))
    _hug(drape, chest_front, out=0.015, fallback=0.0)
    neck = cyl(f"{name}_neck", (0, 0, 1.70), 0.085, 0.20, m_marble, verts=28)
    attach(bust, socle, chest, drape, neck)

    # ---------------- head (group pivots at the neck) ----------------
    head = group3d(f"{name}_head", (0, 0, HZ)); attach(bust, head)
    hw = rng.uniform(0.97, 1.03)
    HC = (0.0, 0.0, 1.90); HR = (0.15 * hw, 0.165, 0.19)
    JC = (0.0, -0.05, 1.77); JR = (0.12 * hw, 0.12, 0.09)
    head_front = _ell_front(HC[0], HC[1], HC[2], *HR)
    jaw_front = _ell_front(JC[0], JC[1], JC[2], *JR)

    def face_front(x, z):
        a = head_front(x, z); b = jaw_front(x, z)
        if a is None: return b
        if b is None: return a
        return min(a, b)

    skull = _ell(f"{name}_skull", HC, HR, m_marble)
    jaw = _ell(f"{name}_jaw", JC, JR, m_marble)

    # hair cap + locks (one mesh)
    hstyle = rng.randrange(3)
    hz = rng.uniform(0.92, 1.02); hy = rng.uniform(0.012, 0.03)
    hcz = 1.955 + rng.uniform(-0.008, 0.008)
    hair = _ell(f"{name}_hair", (0, hy, hcz), (0.158 * hw, 0.168, 0.155 * hz), m_hair)
    line_z = 2.0 + rng.uniform(-0.01, 0.008)
    balls = []
    if hstyle == 0:      # comma locks across the forehead
        angs = [-72, -50, -28, -8, 12, 32, 54, 74]; rr = (0.036, 0.03, 0.044); dz = 0.0
    elif hstyle == 1:    # small tight curls, two staggered rows
        angs = [-78, -60, -42, -24, -6, 12, 30, 48, 66, 82]; rr = (0.03, 0.028, 0.034); dz = 0.0
    else:                # broad swept locks, slightly lower hairline
        angs = [-70, -40, -12, 16, 46, 74]; rr = (0.05, 0.03, 0.036); dz = -0.012
    shift = rng.uniform(-8, 8)
    for i, a in enumerate(angs):
        a = math.radians(a + shift + rng.uniform(-4, 4))
        z = line_z + dz + rng.uniform(-0.008, 0.008)
        if hstyle == 1 and i % 2: z += 0.035
        s = math.sqrt(max(0.0, 1 - ((z - HC[2]) / HR[2]) ** 2))
        x = (HR[0] * s + 0.008) * math.sin(a); y = -(HR[1] * s + 0.008) * math.cos(a)
        k = rng.uniform(0.9, 1.12)
        balls.append(((x, y - hy, z - hcz), (rr[0] * k, rr[1] * k, rr[2] * k)))
    # a few locks on the crown and the back so the silhouette is not a plain egg
    for a in (110, 150, 180, 210, 250):
        a = math.radians(a + rng.uniform(-10, 10))
        z = hcz + 0.05 + rng.uniform(-0.02, 0.02)
        s = math.sqrt(max(0.0, 1 - ((z - hcz) / (0.155 * hz)) ** 2))
        x = 0.158 * hw * s * math.sin(a); y = hy - 0.168 * s * math.cos(a)
        balls.append(((x, y - hy, z - hcz), (0.04, 0.04, 0.035)))
    _add_balls(hair, balls)

    # nose
    nl = rng.uniform(0.85, 1.2); nw = rng.uniform(0.9, 1.15)
    nose = _ell(f"{name}_nose", (0, -0.168, 1.862), (0.028 * nw, 0.04 * nl, 0.062), m_marble,
                rot=(math.radians(-12), 0, 0))
    # ears
    es = rng.uniform(0.85, 1.15)
    ear_l = _ell(f"{name}_ear_l", (0.152 * hw + 0.006, 0.0, 1.868), (0.022, 0.042 * es, 0.06 * es), m_marble)
    ear_r = _ell(f"{name}_ear_r", (-0.152 * hw - 0.006, 0.0, 1.868), (0.022, 0.042 * es, 0.06 * es), m_marble)
    # brow ridge bent around the face
    bz = 1.928 + rng.uniform(-0.008, 0.008)
    brow = _ell(f"{name}_brow", (0, 0, bz), (0.115 * hw, 0.022, 0.022), m_marble)
    _hug(brow, face_front, out=0.008, fallback=-0.12)
    # eyelids + optional drilled pupils
    parts_face = [brow]
    for sx, side in ((1, "l"), (-1, "r")):
        ex = 0.058 * hw * sx
        lid = _ell(f"{name}_eye_{side}", (ex, 0, 1.893), (0.034, 0.016, 0.02), m_marble)
        _hug(lid, face_front, out=0.002, fallback=-0.14)
        parts_face.append(lid)
        if str(p["eyes"]) == "drilled":
            pu = _ell(f"{name}_pupil_{side}", (ex, 0, 1.893), (0.013, 0.008, 0.015), m_dark)
            _hug(pu, face_front, out=0.017, fallback=-0.15)
            parts_face.append(pu)
    # mouth (a short dark line on the face; the beard leaves a window for it)
    mouth = _ell(f"{name}_mouth", (0, 0, 1.79), (0.042, 0.008, 0.009), m_dark)
    _hug(mouth, face_front, out=0.002, fallback=-0.16)
    parts_face.append(mouth)

    for o in [skull, jaw, hair, nose, ear_l, ear_r] + parts_face:
        _to_head(o, head)

    # ---------------- beard (one mesh, origin at the chin) ----------------
    if beard:
        chin = (0.0, -0.15, 1.72)
        bc = (0.0, -0.06, 1.765); br = (0.17 * hw, 0.14, 0.115)
        bo = _ell(f"{name}_beard", chin, br, m_hair)
        bo.data.transform(Matrix.Translation((bc[0] - chin[0], bc[1] - chin[1], bc[2] - chin[2])))
        # window for the mouth: pull front vertices near the lips back behind the face
        for v in bo.data.vertices:
            xw = chin[0] + v.co.x; yw = chin[1] + v.co.y; zw = chin[2] + v.co.z
            wx = min(1.0, max(0.0, (0.07 - abs(xw)) / 0.03))
            wz = min(1.0, max(0.0, (zw - 1.765) / 0.025))
            w = wx * wz
            target = -0.152
            if w > 0 and yw < target:
                v.co.y = (yw + (target - yw) * w) - chin[1]
        bo.data.update()
        curls = []
        for i in range(8):
            a = math.radians(-75 + 150 * (i + rng.uniform(0.2, 0.8)) / 8)
            b = math.radians(rng.uniform(-62, -12))
            x = bc[0] + br[0] * math.cos(b) * math.sin(a)
            y = bc[1] - br[1] * math.cos(b) * math.cos(a)
            z = bc[2] + br[2] * math.sin(b)
            r = rng.uniform(0.032, 0.044)
            curls.append(((x - chin[0], y - chin[1], z - chin[2]), (r, r * 0.85, r)))
        _add_balls(bo, curls)
        _to_head(bo, head)

    return root
