"""Care package from home for a Roman soldier - 2D hand-held prop in the character plane (flat colours, ink outline 0.035).

item='box'        : canvas/leather bundle 0.6 x 0.4 tied with a cord cross (bow knot in the middle), open mouth with a pair of
                    red wool socks and a pair of strappy hobnailed leather sandals poking out.
                    Parts: {name}_bundle, {name}_socks, {name}_sandals.
item='underpants' : linen Roman subligaculum (ivory), rolled waistband, side ties, optional darned patch; 0.35 x 0.25,
                    origin at its centre (story flies it up and spins it around local Z). Part: {name}_underpants.
item='socks'      : the pair of socks alone. Part: {name}_socks.
item='sandals'    : the pair of sandals alone. Part: {name}_sandals.
With a parent (torso) the root sits at `at` = [0, 0.5, 0.42] (x right, y up, z forward).
Only the parts of the chosen item are created. Layers are spaced 0.02+ in z because outline tubes have depth."""
from core.look import flat
from core.geo import empty, shape, stroke, disc, rrect, ellipse, arc, label

DEFAULTS = dict(item="box", at=[0, 0.5, 0.42], scale2d=1.0,
                bag_color=[0.5, 0.29, 0.1], cord_color=[0.93, 0.74, 0.38],
                sock_color=[0.78, 0.04, 0.03], sock_cuff_color=[0.95, 0.85, 0.62],
                leather_color=[0.55, 0.26, 0.07], sole_color=[0.17, 0.08, 0.03],
                underpants_color=[0.93, 0.84, 0.62], patch=True, tag_text="")


def _clamp(c, k=1.0):
    return tuple(min(1.0, max(0.0, float(v) * k)) for v in c)


def _key(c):
    return "_".join(f"{float(v):.2f}" for v in c)


def _mat(tag, col, k=1.0):
    return flat(f"care_package_{tag}_{_key(col)}_{k:.2f}", _clamp(col, k))


def _qbez(a, c, b, n=8):
    out = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        out.append((u * u * a[0] + 2 * u * t * c[0] + t * t * b[0], u * u * a[1] + 2 * u * t * c[1] + t * t * b[1]))
    return out


def _ostroke(par, nm, pts, w, z, m, ol=0.035, cyclic=False):
    """coloured stroke with an ink rim: fat ink tube behind, coloured tube 0.02 in front"""
    stroke(par, nm + "_ink", pts, w + ol, z, m=None, cyclic=cyclic)
    stroke(par, nm, pts, w, z + 0.02, m=m, cyclic=cyclic)


# ---------------------------------------------------------------- pieces
def _sock(par, nm, z, M):
    """one wool sock, open cuff at (0, 0), leg up, foot pointing +x at the top"""
    body = ([(-0.04, 0.0), (0.04, 0.0), (0.04, 0.135), (0.12, 0.14)]
            + arc(0.12, 0.18, 0.045, 0.04, -90, 90)[1:]
            + arc(0.0, 0.175, 0.04, 0.045, 90, 180))
    shape(par, nm, body, M["sock"], z)
    toe = arc(0.12, 0.18, 0.032, 0.027, -90, 90) + [(0.095, 0.207), (0.095, 0.153)]
    shape(par, nm + "_toe", toe, M["sock_dark"], z + 0.015, outline=0)
    heel = arc(0.0, 0.175, 0.027, 0.032, 90, 180) + [(-0.027, 0.15), (0.02, 0.15), (0.02, 0.207)]
    shape(par, nm + "_heel", heel, M["sock_dark"], z + 0.015, outline=0)
    for i, x in enumerate((-0.015, 0.015)):
        stroke(par, f"{nm}_rib{i}", [(x, 0.06), (x, 0.12)], 0.008, z + 0.015, m=M["sock_dark"])
    shape(par, nm + "_cuff", rrect(0, 0.022, 0.094, 0.048, 0.014), M["cuff"], z + 0.025, outline=0.025)


def _sandal(par, nm, z, M):
    """one strappy hobnailed sandal in side view, origin at sole bottom centre, toe toward +x"""
    shape(par, nm + "_sole", rrect(0, 0.022, 0.30, 0.044, 0.02), M["sole"], z)
    straps = [
        [(-0.13, 0.04), (-0.137, 0.10), (-0.118, 0.165)],          # heel counter
        [(-0.128, 0.165), (-0.06, 0.172), (-0.015, 0.168)],        # ankle strap
        arc(0.03, 0.04, 0.07, 0.085, 0, 180),                      # vamp loop
        arc(0.105, 0.04, 0.035, 0.045, 0, 180),                    # toe loop
        [(-0.03, 0.165), (0.0, 0.14), (0.03, 0.125)],              # ankle -> vamp
    ]
    for i, pts in enumerate(straps):
        _ostroke(par, f"{nm}_s{i}", pts, 0.022, z + 0.02, M["leather"])
    _ostroke(par, nm + "_lace", [(-0.015, 0.168), (0.012, 0.145), (0.004, 0.11)], 0.012, z + 0.02, M["leather"], ol=0.022)
    for k in range(5):
        disc(par, f"{nm}_n{k}", -0.11 + 0.055 * k, 0.02, 0.011, z + 0.03, M["nail"])


def _bundle(g, name, M, tag_text):
    # back rim of the sack + dark open mouth
    shape(g, f"{name}_rim", ellipse(0, 0.14, 0.245, 0.07, 32), M["bag_back"], -0.04)
    shape(g, f"{name}_mouth", ellipse(0, 0.135, 0.215, 0.05, 32), M["mouth"], 0.0, outline=0)
    # front body (covers the lower half of everything poking out)
    lip = [(x, 0.13 - 0.02 * (1 - (x / 0.23) ** 2)) for x in [-0.23 + 0.46 * i / 10 for i in range(1, 10)]]
    body = ([(0.23, 0.13), (0.275, 0.07), (0.298, -0.02), (0.296, -0.10)]
            + arc(0, -0.11, 0.296, 0.095, 0, -180, n=14)
            + [(-0.298, -0.02), (-0.275, 0.07), (-0.23, 0.13)] + lip)
    zf = 0.27
    shape(g, f"{name}_body", body, M["bag"], zf)
    for i, x in enumerate((-0.15, -0.06, 0.07, 0.16)):
        stroke(g, f"{name}_fold{i}", [(x, 0.112), (x * 1.06, 0.06), (x * 1.1, 0.03)], 0.012, zf + 0.02, m=M["bag_dark"])
    # cord cross
    zc = zf + 0.03
    _ostroke(g, f"{name}_cordv", [(0.0, 0.112), (0.004, 0.03), (0.0, -0.04), (-0.004, -0.12), (0.0, -0.208)],
             0.028, zc, M["cord"])
    hpts = [(x, -0.045 - 0.018 * (1 - (x / 0.3) ** 2)) for x in [-0.3 + 0.6 * i / 12 for i in range(13)]]
    _ostroke(g, f"{name}_cordh", hpts, 0.028, zc, M["cord"])
    # bow knot
    _ostroke(g, f"{name}_bowL", ellipse(-0.05, -0.04, 0.04, 0.022, 20) + [ellipse(-0.05, -0.04, 0.04, 0.022, 20)[0]],
             0.02, zc + 0.02, M["cord"])
    _ostroke(g, f"{name}_bowR", ellipse(0.05, -0.04, 0.04, 0.022, 20) + [ellipse(0.05, -0.04, 0.04, 0.022, 20)[0]],
             0.02, zc + 0.02, M["cord"])
    _ostroke(g, f"{name}_tailL", [(-0.01, -0.07), (-0.022, -0.1), (-0.03, -0.125)], 0.02, zc + 0.02, M["cord"])
    _ostroke(g, f"{name}_tailR", [(0.01, -0.07), (0.028, -0.095), (0.04, -0.12)], 0.02, zc + 0.02, M["cord"])
    shape(g, f"{name}_knot", ellipse(0, -0.055, 0.032, 0.028, 20), M["cord"], zc + 0.07, outline=0.03)
    # optional hanging name tag
    if tag_text:
        tg = empty(f"{name}_tag", g, (0, 0, zc + 0.02))
        stroke(tg, f"{name}_tagstr", [(0.12, -0.08), (0.17, -0.11)], 0.01, 0.0, m=None)
        shape(tg, f"{name}_tagcard", rrect(0.21, -0.135, 0.14, 0.065, 0.012), M["cuff"], 0.03, outline=0.025)
        label(tg, f"{name}_tagtxt", str(tag_text)[:10], (0.21, -0.148), 0.034, M["ink_brown"])


def _underpants(g, name, M, patch):
    body = ([(-0.13, 0.115), (0.13, 0.115), (0.14, 0.06)]
            + _qbez((0.14, 0.06), (0.06, 0.02), (0.045, -0.125))[1:]
            + _qbez((-0.045, -0.125), (-0.06, 0.02), (-0.14, 0.06))[:-1])
    shape(g, f"{name}_body", body, M["linen"], 0.0)
    stroke(g, f"{name}_crease0", [(-0.03, 0.06), (-0.02, -0.02), (-0.028, -0.08)], 0.01, 0.02, m=M["linen_dark"])
    stroke(g, f"{name}_crease1", [(0.045, 0.05), (0.034, -0.03)], 0.01, 0.02, m=M["linen_dark"])
    if patch:
        shape(g, f"{name}_patch", rrect(-0.06, 0.025, 0.05, 0.045, 0.006), M["patch"], 0.03, outline=0.02)
        stroke(g, f"{name}_stitch0", [(-0.075, 0.035), (-0.045, 0.015)], 0.007, 0.05, m=None)
        stroke(g, f"{name}_stitch1", [(-0.075, 0.015), (-0.045, 0.035)], 0.007, 0.05, m=None)
    shape(g, f"{name}_band", rrect(0, 0.097, 0.272, 0.042, 0.014), M["linen_band"], 0.06, outline=0.025)
    for sx, sd in ((1, "R"), (-1, "L")):
        _ostroke(g, f"{name}_tie{sd}0", [(sx * 0.135, 0.095), (sx * 0.158, 0.07), (sx * 0.168, 0.03)], 0.014, 0.08,
                 M["linen_band"], ol=0.025)
        _ostroke(g, f"{name}_tie{sd}1", [(sx * 0.135, 0.097), (sx * 0.162, 0.104), (sx * 0.175, 0.082)], 0.014, 0.08,
                 M["linen_band"], ol=0.025)
        shape(g, f"{name}_knot{sd}", ellipse(sx * 0.135, 0.096, 0.02, 0.018, 16), M["linen_band"], 0.13, outline=0.025)


# ---------------------------------------------------------------- build
def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    name = p["name"]
    item = str(p["item"]).lower()
    if item not in ("box", "underpants", "socks", "sandals"):
        raise ValueError(f"care_package: unknown item {item!r} (box | underpants | socks | sandals)")
    s = max(0.2, float(p["scale2d"]))

    M = dict(
        bag=_mat("bag", p["bag_color"]), bag_back=_mat("bag", p["bag_color"], 0.72),
        bag_dark=_mat("bag", p["bag_color"], 0.55), mouth=_mat("bag", p["bag_color"], 0.25),
        cord=_mat("cord", p["cord_color"]),
        sock=_mat("sock", p["sock_color"]), sock_dark=_mat("sock", p["sock_color"], 0.6),
        cuff=_mat("cuff", p["sock_cuff_color"]),
        leather=_mat("leather", p["leather_color"]), sole=_mat("sole", p["sole_color"]),
        nail=flat("care_package_nail", (0.55, 0.55, 0.58)),
        linen=_mat("linen", p["underpants_color"]), linen_dark=_mat("linen", p["underpants_color"], 0.72),
        linen_band=_mat("linen", p["underpants_color"], 0.88), patch=_mat("patch", (0.62, 0.42, 0.2)),
        ink_brown=flat("care_package_ink", (0.12, 0.05, 0.02)),
    )

    parent = p.get("parent")
    g = empty(name, parent)
    if parent is not None:
        g.location = tuple(float(v) for v in p["at"])

    def part(nm):
        e = empty(f"{name}_{nm}", g)
        e.scale = (s, s, s)
        return e

    def sub(par, nm, loc, rot=0.0, mirror=False):
        e = empty(f"{name}_{nm}", par, loc)
        e.rotation_euler = (0.0, 0.0, rot)
        if mirror:
            e.scale = (-1.0, 1.0, 1.0)
        return e

    if item == "box":
        bundle = part("bundle")
        socks = part("socks")
        sandals = part("sandals")
        _bundle(bundle, name, M, p["tag_text"])
        _sock(sub(socks, "sock1", (-0.07, 0.06, 0.03), -0.05), f"{name}_sk1", 0.0, M)
        _sock(sub(socks, "sock0", (-0.15, 0.05, 0.07), 0.35, mirror=True), f"{name}_sk0", 0.0, M)
        _sandal(sub(sandals, "sandal1", (0.06, 0.09, 0.12), 1.45), f"{name}_sd1", 0.0, M)
        _sandal(sub(sandals, "sandal0", (0.14, 0.07, 0.18), 1.05), f"{name}_sd0", 0.0, M)
    elif item == "socks":
        socks = part("socks")
        _sock(sub(socks, "sock0", (-0.11, -0.11, 0.0)), f"{name}_sk0", 0.0, M)
        _sock(sub(socks, "sock1", (-0.02, -0.125, 0.06), -0.06), f"{name}_sk1", 0.0, M)
    elif item == "sandals":
        sandals = part("sandals")
        _sandal(sub(sandals, "sandal0", (-0.02, -0.05, 0.0)), f"{name}_sd0", 0.0, M)
        _sandal(sub(sandals, "sandal1", (0.03, -0.13, 0.08)), f"{name}_sd1", 0.0, M)
    else:
        up = part("underpants")
        _underpants(up, name, M, bool(p["patch"]))
    return g
