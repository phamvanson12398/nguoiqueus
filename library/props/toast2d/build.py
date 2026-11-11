"""2D hand-held slice of sandwich bread (toast) in the character plane, ~0.42 x 0.42, thick ink outline.

Origin at the slice centre.  Parent to the torso, e.g. loc [0.45, 0.5, 0.42] with the right hand IK at
(0.45, 0.45).  Layers (z): crust 0, crumb 0.02, butter 0.04-0.05, knife 0.07-0.10 (knife sits in front).

Parts (each an empty, so a story can animate / show / hide them separately):
  <name>_bread   crust + crumb
  <name>_butter  wavy butter spread + shine streak on the top face
  <name>_knife   butter knife, placed at knife_pos (default (-0.3, 0.1)) and tilted knife_angle;
                 drawn around its own centre so rotation tracks pivot on the knife.
butter='none' / knife=False still build the part but mark it keep_hidden (stays hidden when the whole
prop is shown).  Hand props are 2D (skill rule); the 3D falling slice is the 'toast' prop."""
import math
from core.look import flat
from core.geo import empty, shape, stroke, rrect, arc, keep_hidden

DEFAULTS = dict(butter="top", knife=True, knife_butter=True, knife_pos=[-0.3, 0.1], knife_angle=-40.0,
                outline=0.05,
                crust_color=[0.45, 0.16, 0.03], crumb_color=[0.92, 0.60, 0.26],
                butter_color=[1.0, 0.82, 0.08], handle_color=[0.80, 0.07, 0.04], scale=1.0)

W = 0.42          # slice width
H = 0.42          # slice height (bottom edge to top of dome)
SHOULDER = 0.06   # y where the straight sides end and the domed top starts


def _tag(rgb):
    return "_".join(str(int(round(c * 100))) for c in rgb)


def _slice(inset):
    """sandwich-bread silhouette centred on (0, 0): square bottom with rounded corners, domed top"""
    hw = W / 2 - inset
    y0 = -H / 2 + inset
    rc = 0.04
    over = 0.015
    ry = H / 2 - SHOULDER - inset
    pts = []
    pts += arc(-hw + rc, y0 + rc, rc, rc, 180, 270, 5)
    pts += arc(hw - rc, y0 + rc, rc, rc, 270, 360, 5)
    pts.append((hw, SHOULDER - 0.025))
    pts += arc(0, SHOULDER, hw + over, ry, 0, 180, 28)
    pts.append((-hw, SHOULDER - 0.025))
    return pts


def _wavy(cx, cy, rx, ry, amp, lobes, n=64, phase=0.0):
    """soft rounded blob with a wavy edge (butter spread)"""
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        c, s = math.cos(t), math.sin(t)
        x = rx * math.copysign(abs(c) ** 0.6, c)
        y = ry * math.copysign(abs(s) ** 0.6, s)
        k = 1.0 + amp * math.sin(lobes * t + phase)
        pts.append((cx + x * k, cy + y * k))
    return pts


def _hide_part(part):
    for o in [part] + list(part.children_recursive):
        keep_hidden(o, True)


def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    name = p["name"]
    ol = float(p["outline"])

    bmode = p["butter"]
    if isinstance(bmode, bool):
        bmode = "top" if bmode else "none"
    bmode = str(bmode).lower()
    if bmode not in ("top", "none"):
        bmode = "top"

    crust_rgb = tuple(p["crust_color"]); crumb_rgb = tuple(p["crumb_color"])
    butter_rgb = tuple(p["butter_color"]); handle_rgb = tuple(p["handle_color"])
    m_crust = flat(f"toast2d_crust_{_tag(crust_rgb)}", crust_rgb)
    m_crumb = flat(f"toast2d_crumb_{_tag(crumb_rgb)}", crumb_rgb)
    m_butter = flat(f"toast2d_butter_{_tag(butter_rgb)}", butter_rgb)
    m_shine = flat("toast2d_butter_shine", (1.0, 0.97, 0.70))
    m_handle = flat(f"toast2d_handle_{_tag(handle_rgb)}", handle_rgb)
    m_blade = flat("toast2d_blade", (0.70, 0.72, 0.76))
    m_bolster = flat("toast2d_bolster", (0.40, 0.41, 0.45))

    root = empty(name, p.get("parent"))

    # ---- bread: brown crust with a thick ink outline, lighter crumb inset ----
    bread = empty(f"{name}_bread", root)
    shape(bread, f"{name}_bread_crust", _slice(0.0), m_crust, 0.0, outline=ol)
    shape(bread, f"{name}_bread_crumb", _slice(0.035), m_crumb, 0.02, outline=0)

    # ---- butter: wavy spread on the top face + a shine streak ----
    butter = empty(f"{name}_butter", root)
    shape(butter, f"{name}_butter_spread", _wavy(0.0, -0.02, 0.13, 0.115, 0.06, 8, phase=0.5),
          m_butter, 0.04, outline=0.018)
    stroke(butter, f"{name}_butter_shine", [(-0.07, 0.04), (-0.03, 0.06), (0.01, 0.065)], 0.022, 0.05,
           m=m_shine)
    if bmode == "none":
        _hide_part(butter)

    # ---- knife: tilted butter knife above-left, pivot at its own centre ----
    kx, ky = p["knife_pos"]
    knife = empty(f"{name}_knife", root, (float(kx), float(ky), 0.0))
    knife.rotation_euler = (0.0, 0.0, math.radians(float(p["knife_angle"])))
    shape(knife, f"{name}_knife_handle", rrect(-0.115, 0.0, 0.17, 0.07, 0.033), m_handle, 0.07, outline=0.03)
    shape(knife, f"{name}_knife_blade", rrect(0.095, 0.0, 0.25, 0.055, 0.027), m_blade, 0.08, outline=0.03)
    shape(knife, f"{name}_knife_bolster", rrect(-0.03, 0.0, 0.03, 0.075, 0.01), m_bolster, 0.09, outline=0.02)
    if p["knife_butter"]:
        shape(knife, f"{name}_knife_dab", _wavy(0.16, 0.005, 0.05, 0.036, 0.08, 5, n=40, phase=1.1),
              m_butter, 0.10, outline=0.015)
    if not p["knife"]:
        _hide_part(knife)

    s = float(p["scale"])
    if s != 1.0:
        root.scale = (s, s, s)
    return root
