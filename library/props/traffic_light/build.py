"""3D US-style traffic light on a metal pole: deep-yellow signal head, three lamps
(red / yellow / green, top to bottom) each with a small arc visor.  Lamps face -Y.
Each lamp = an 'off' disc  <name>_<color>  plus a glowing disc  <name>_<color>_on  just in
front of it; only the active state's '_on' disc is visible.  For the 'light changes' gag,
animate visibility of the *_on parts.  Origin at the centre of the pole's base (z = 0 = ground)."""
import math
from core.look import pbr, flat
from core.geo import cyl, cone, rbox, extrude, ellipse, group3d, attach, keep_hidden

DEFAULTS = dict(state="red", pole_height=2.6, pole_radius=0.07,
                box_color=[0.95, 0.62, 0.02], pole_color=[0.32, 0.34, 0.37],
                glow=4.0, visors=True)

LAMPS = [  # (color key, lit colour, dark colour)
    ("red",    (0.95, 0.06, 0.03), (0.16, 0.03, 0.02)),
    ("yellow", (0.98, 0.62, 0.02), (0.18, 0.12, 0.02)),
    ("green",  (0.05, 0.85, 0.25), (0.02, 0.13, 0.05)),
]


def _tag(rgb):
    return "_".join(str(int(round(c * 100))) for c in rgb)


def _glow_mat(name, rgb, strength):
    m = flat(name, rgb)
    for n in m.node_tree.nodes:
        if n.type == 'EMISSION':
            n.inputs[1].default_value = strength
    return m


def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    name = p["name"]
    state = str(p["state"]).lower()
    ph = float(p["pole_height"]); pr = float(p["pole_radius"])
    box_rgb = tuple(p["box_color"]); pole_rgb = tuple(p["pole_color"])

    m_pole = pbr(f"traffic_light_pole_{_tag(pole_rgb)}", pole_rgb, rough=0.45, metal=0.7)
    m_box = pbr(f"traffic_light_body_{_tag(box_rgb)}", box_rgb, rough=0.55)
    m_visor = pbr("traffic_light_visor", (0.03, 0.03, 0.035), rough=0.6)

    root = group3d(name)
    parts = []

    # pole + base flange + bracket collar
    parts.append(cone(f"{name}_base", (0, 0, 0.06), pr * 2.6, pr * 1.3, 0.12, m_pole))
    parts.append(cyl(f"{name}_pole", (0, 0, ph / 2), pr, ph, m_pole, 24))
    parts.append(cyl(f"{name}_collar", (0, 0, ph - 0.04), pr * 1.6, 0.08, m_pole, 24))

    # signal head
    bw, bd, bh = 0.52, 0.36, 1.26
    bz = ph + bh / 2
    parts.append(rbox(f"{name}_box", (0, 0, bz), (bw, bd, bh), m_box, radius=0.06))
    parts.append(cyl(f"{name}_cap", (0, 0, ph + bh + 0.03), pr * 1.4, 0.06, m_pole, 24))

    front = -bd / 2
    lr = 0.15                        # lamp radius
    step = bh / 3
    rot_face = (math.pi / 2, 0, 0)   # cylinder axis -> Y (faces -Y)
    for i, (key, lit, dark) in enumerate(LAMPS):
        z = ph + bh - step * (i + 0.5)
        m_off = pbr(f"traffic_light_{key}_off", dark, rough=0.3)
        m_on = _glow_mat(f"traffic_light_{key}_on_g{int(round(float(p['glow']) * 10))}", lit, float(p["glow"]))
        off = cyl(f"{name}_{key}", (0, front - 0.015, z), lr, 0.03, m_off, 32, rot_face)
        on = cyl(f"{name}_{key}_on", (0, front - 0.025, z), lr * 0.97, 0.03, m_on, 32, rot_face)
        keep_hidden(on, key != state)        # unlit: stays hidden when a visibility track shows the whole light
        parts += [off, on]

        if p["visors"]:
            ro, ri = lr + 0.05, lr + 0.02
            outer = ellipse(0, 0, ro, ro, 16, -0.15, math.pi + 0.15)
            inner = ellipse(0, 0, ri, ri, 16, -0.15, math.pi + 0.15)[::-1]
            vd = 0.17
            # extrude along local Z; rot X +90 deg maps local Z -> world -Y, local Y -> world Z
            parts.append(extrude(f"{name}_visor_{key}", (0, front - vd / 2, z), outer + inner, vd,
                                 m_visor, rot=(math.pi / 2, 0, 0)))

    attach(root, *parts)
    return root
