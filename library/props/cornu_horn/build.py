"""Roman cornu (bronze war horn), 2D hand prop drawn in the character plane.

A big G-shaped brass tube: short lead pipe from the mouthpiece (origin), a near-full loop (diameter loop_d) that wraps
around the player's head, then a straight run forward that flares into a wide bell pointing ahead/slightly up.
A wooden cross bar spans the loop diagonally (brass clamps at both ends).

With a parent (torso) the root sits at `at` (mouthpiece next to the character's mouth).  facing=-1 mirrors it,
tilt (degrees, + raises the bell) rotates about the mouthpiece, scale2d scales everything except the ink line.
Parts (empties, each holding its own fills + outlines):
  {name}_horn  mouthpiece + tube (pivot at the mouthpiece)
  {name}_bar   wooden cross bar (pivot at the loop centre)
  {name}_bell  flared bell (pivot at the bell base)

Layering note: strokes are round bevelled curves, so a stroke of width W at z covers z +- W/2.  The ink tube
(width w+OL) must sit low enough that its top stays below the brass tube's top, and everything drawn over the
tube must sit above the brass top.  All z values are derived from the tube width.
"""
import math
from core.look import flat
from core.geo import empty, shape, stroke

DEFAULTS = dict(at=[0.2, 0.75, 0.45], scale2d=1.0, facing=1, tilt=0.0,
                loop_d=0.7, tube_w=0.05, bell_r=0.15, bell_len=0.26, reach=0.42,
                color=[0.85, 0.40, 0.04], wood_color=[0.42, 0.18, 0.05])

OL = 0.035


def _key(c):
    return "_".join(f"{float(v):.2f}" for v in c)


def _clamp(c, k=1.0):
    return tuple(min(1.0, max(0.0, float(v) * k)) for v in c)


def _mix(c, t, k):
    return tuple(min(1.0, max(0.0, float(a) * (1 - k) + b * k)) for a, b in zip(c, t))


def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    name = p["name"]
    s = max(0.2, float(p["scale2d"]))
    f = -1.0 if float(p["facing"]) < 0 else 1.0
    R = 0.5 * max(0.2, float(p["loop_d"]))
    w = max(0.02, float(p["tube_w"]))
    Rb = max(w, float(p["bell_r"]))
    Lb = max(0.08, float(p["bell_len"]))
    reach = max(0.05, float(p["reach"]))
    col = p["color"]; wc = p["wood_color"]

    m_brass = flat(f"cornu_horn_brass_{_key(col)}", _clamp(col))
    m_hi = flat(f"cornu_horn_hi_{_key(col)}", _mix(col, (1.0, 0.85, 0.45), 0.55))
    m_rim = flat(f"cornu_horn_rim_{_key(col)}", _mix(col, (1.0, 0.75, 0.3), 0.3))
    m_dark = flat(f"cornu_horn_dark_{_key(col)}", _clamp(col, 0.28))
    m_clamp = flat(f"cornu_horn_clamp_{_key(col)}", _clamp(col, 0.7))
    m_wood = flat(f"cornu_horn_wood_{_key(wc)}", _clamp(wc))
    m_grain = flat(f"cornu_horn_grain_{_key(wc)}", _clamp(wc, 0.6))

    # ---- z layers (round bevel strokes occupy z +- width/2)
    ws = w * s
    z_ink = 0.0                                   # ink tube, top at (ws + OL)/2
    z_tube = (ws + OL) / 2 - ws / 2 + 0.012       # brass tube top clearly above the ink top
    top = z_tube + ws / 2                         # top of the brass tube
    z_hi = top + 0.004
    z_mouth = top + OL / 2 + 0.01                 # flat shapes: their outline bevel spans +-OL/2
    z_bell = z_mouth
    z_rim = z_bell + 0.012
    z_throat = z_rim + OL / 2 + 0.005
    z_bar = -(ws + OL) / 2 - OL / 2 - 0.01        # bar fully behind the tube

    def P(x, y):
        return (f * x * s, y * s)

    def Ps(pts):
        return [P(x, y) for x, y in pts]

    def frame(o, u, pts):
        """local (a along u, b along normal) -> xy around origin o"""
        n = (-u[1], u[0])
        return [(o[0] + u[0] * a + n[0] * b, o[1] + u[1] * a + n[1] * b) for a, b in pts]

    # ---- centre line of the tube (unscaled, facing right, mouthpiece at origin)
    a0, a1 = math.radians(-30.0), math.radians(-260.0)          # clockwise sweep
    t0 = (math.sin(a0), -math.cos(a0))                            # travel direction at loop start
    Llead = 0.12
    P0 = (Llead * t0[0], Llead * t0[1])
    C = (P0[0] - R * math.cos(a0), P0[1] - R * math.sin(a0))
    n_arc = 64
    arc_pts = []
    for i in range(n_arc + 1):
        a = a0 + (a1 - a0) * i / n_arc
        arc_pts.append((C[0] + R * math.cos(a), C[1] + R * math.sin(a)))
    u = (math.sin(a1), -math.cos(a1))                             # exit direction (forward, slightly up)
    Ex = arc_pts[-1]
    B = (Ex[0] + u[0] * reach, Ex[1] + u[1] * reach)              # bell base
    line = [(0.0, 0.0)] + arc_pts + [(B[0] + u[0] * 0.03, B[1] + u[1] * 0.03)]

    g = empty(name, p.get("parent"))
    if p.get("parent") is not None:
        g.location = tuple(float(v) for v in p["at"])
    g.rotation_euler = (0.0, 0.0, math.radians(float(p["tilt"])) * f)

    # ---- bar (behind the tube; ends tucked under it)
    bar = empty(f"{name}_bar", g, (P(*C)[0], P(*C)[1], z_bar))
    d = (math.cos(math.radians(135.0)), math.sin(math.radians(135.0)))
    Lh = R + 0.15 * w
    hb = 0.028
    rect = frame((0.0, 0.0), d, [(-Lh, -hb), (Lh, -hb), (Lh, hb), (-Lh, hb)])
    shape(bar, f"{name}_bar_wood", Ps(rect), m_wood, 0.0, outline=OL)
    stroke(bar, f"{name}_bar_grain", Ps(frame((0.0, 0.0), d, [(-0.55 * Lh, 0.006), (0.45 * Lh, 0.006)])),
           0.008 * s, 0.006, m=m_grain)
    clamp_at = max(0.05, R - w / 2 - 0.05)
    for k, sg in enumerate((-1.0, 1.0)):
        c0 = sg * clamp_at
        band = frame((0.0, 0.0), d, [(c0 - 0.018, -hb - 0.01), (c0 + 0.018, -hb - 0.01),
                                     (c0 + 0.018, hb + 0.01), (c0 - 0.018, hb + 0.01)])
        shape(bar, f"{name}_bar_clamp{k}", Ps(band), m_clamp, 0.014, outline=0.025)

    # ---- horn: tube + mouthpiece
    horn = empty(f"{name}_horn", g)
    stroke(horn, f"{name}_tube_ink", Ps(line), ws + OL, z_ink)
    stroke(horn, f"{name}_tube", Ps(line), ws, z_tube, m=m_brass)
    # highlight on the outer top-left of the loop and along the top of the straight run
    hi = []
    for i in range(25):
        a = math.radians(-150.0 - 100.0 * i / 24)
        rr = R + 0.18 * w
        hi.append((C[0] + rr * math.cos(a), C[1] + rr * math.sin(a)))
    stroke(horn, f"{name}_tube_hi", Ps(hi), 0.012 * s, z_hi, m=m_hi)
    stroke(horn, f"{name}_tube_hi2",
           Ps(frame(Ex, u, [(0.05, 0.18 * w), (reach - 0.02, 0.18 * w)])), 0.012 * s, z_hi, m=m_hi)
    # mouthpiece cup: rim at the origin, narrowing along the lead pipe
    cup = frame((0.0, 0.0), t0, [(0.0, 0.04), (0.075, 0.021), (0.075, -0.021), (0.0, -0.04)])
    shape(horn, f"{name}_mouthpiece", Ps(cup), m_rim, z_mouth, outline=OL)

    # ---- bell
    bell = empty(f"{name}_bell", g, (P(*B)[0], P(*B)[1], 0.0))
    up, lo = [], []
    nb = 18
    for i in range(nb + 1):
        t = i / nb
        hw = w / 2 + (Rb - w / 2) * t ** 2.6
        up.append((Lb * t, hw)); lo.append((Lb * t, -hw))
    bell_poly = frame((0.0, 0.0), u, up + lo[::-1])
    shape(bell, f"{name}_bell_body", Ps(bell_poly), m_brass, z_bell, outline=OL)
    hl = []
    for i in range(2, 16):
        t = i / nb
        hw = w / 2 + (Rb - w / 2) * t ** 2.6
        hl.append((Lb * t, hw * 0.55))
    stroke(bell, f"{name}_bell_hi", Ps(frame((0.0, 0.0), u, hl)), 0.012 * s, z_bell + 0.008, m=m_hi)
    # mouth of the bell: bright rim + dark throat, seen slightly from the front
    rim = [(Lb + 0.04 * math.cos(2 * math.pi * i / 32), Rb * 1.02 * math.sin(2 * math.pi * i / 32)) for i in range(32)]
    shape(bell, f"{name}_bell_rim", Ps(frame((0.0, 0.0), u, rim)), m_rim, z_rim, outline=OL)
    throat = [(Lb + 0.024 * math.cos(2 * math.pi * i / 28), Rb * 0.78 * math.sin(2 * math.pi * i / 28)) for i in range(28)]
    shape(bell, f"{name}_bell_throat", Ps(frame((0.0, 0.0), u, throat)), m_dark, z_throat, outline=0)
    return g
