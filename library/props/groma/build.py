"""3D Roman groma (surveying instrument) standing on the ground.

Hierarchy (all names prefixed with the story id <name>):
  <name>                      root empty, origin at the iron foot tip (z = 0 = ground)
    <name>_pole               wooden staff (+ children: _shoe iron tip, _collar, _arm bracket, _pin pivot)
    <name>_cross              EMPTY pivot at the end of the arm; rotate Z to turn the cross
      <name>_cross_a/_b       the two wooden bars, _cross_hub, _cross_cap<i> bronze end caps
      <name>_plumbs           EMPTY holding the four plumb lines (toggle visibility / animate as a group)
        <name>_plumb<i>       EMPTY swing pivot at each bar end (gentle looping sway keys + CYCLES)
          <name>_plumb<i>_cord, <name>_plumb<i>_bob
The cross sits on an offset arm so the plumb lines hang clear of the staff (true to the real tool)."""
import math
from core.look import pbr
from core.geo import cyl, cone, rbox, lathe, empty, group3d, attach
from core.timing import fcurves_of

DEFAULTS = dict(pole_height=2.2, arm_length=0.6, cross_radius=0.5, cross_angle=20,
                cord_length=0.85, sway=True, sway_deg=3.0, sway_period=54,
                wood_color=[0.42, 0.18, 0.05], bronze_color=[0.85, 0.45, 0.1],
                cord_color=[0.12, 0.07, 0.03])


def _tag(rgb):
    return "_".join(str(int(round(c * 100))) for c in rgb)


def _sway(o, axis, amp, period, phase):
    """sine-like swing on one rotation axis: 5 keys over one period, then loop forever"""
    f0 = 1 + phase
    for k, v in enumerate((0.0, amp, 0.0, -amp, 0.0)):
        rot = list(o.rotation_euler); rot[axis] = v; o.rotation_euler = rot
        o.keyframe_insert("rotation_euler", index=axis, frame=f0 + k * period / 4.0)
    o.rotation_euler = (0, 0, 0)


def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    name = p["name"]
    ph = float(p["pole_height"]); arm = float(p["arm_length"])
    R = float(p["cross_radius"]); L = float(p["cord_length"])
    wood_rgb = tuple(p["wood_color"]); bronze_rgb = tuple(p["bronze_color"]); cord_rgb = tuple(p["cord_color"])

    m_wood = pbr(f"groma_wood_{_tag(wood_rgb)}", wood_rgb, rough=0.7)
    m_bronze = pbr(f"groma_bronze_{_tag(bronze_rgb)}", bronze_rgb, rough=0.35, metal=0.85)
    m_iron = pbr("groma_iron", (0.12, 0.12, 0.13), rough=0.5, metal=0.7)
    m_cord = pbr(f"groma_cord_{_tag(cord_rgb)}", cord_rgb, rough=0.9)

    root = group3d(name)

    # ---- pole: staff with iron foot, collar, horizontal arm and pivot pin ----
    shoe_h = 0.16
    staff_r = 0.05
    pole = cyl(f"{name}_pole", (0, 0, (ph + shoe_h) / 2), staff_r, ph - shoe_h, m_wood, 24)
    attach(root, pole)
    pz = pole.location.z  # children of the pole use coords relative to its centre
    shoe = cone(f"{name}_shoe", (0, 0, shoe_h / 2 + 0.005 - pz), 0.012, staff_r * 1.05, shoe_h + 0.01, m_iron, 24)
    collar = cyl(f"{name}_collar", (0, 0, ph - 0.13 - pz), staff_r * 1.35, 0.06, m_bronze, 24)
    arm_z = ph - 0.04
    bracket = rbox(f"{name}_arm", (arm / 2, 0, arm_z - pz), (arm + 0.14, 0.09, 0.08), m_wood, radius=0.02)
    pin = cyl(f"{name}_pin", (arm, 0, arm_z + 0.06 - pz), 0.028, 0.08, m_iron, 16)
    for o in (shoe, collar, bracket, pin):
        o.parent = pole

    # ---- cross: pivot empty at arm end, rotate Z to turn ----
    cz = arm_z + 0.12
    cross = empty(f"{name}_cross", root, (arm, 0, cz))
    cross.rotation_euler = (0, 0, math.radians(float(p["cross_angle"])))
    bt = 0.065
    bar_a = rbox(f"{name}_cross_a", (0, 0, 0), (2 * R, 0.07, bt), m_wood, radius=0.015)
    bar_b = rbox(f"{name}_cross_b", (0, 0, 0), (0.07, 2 * R, bt), m_wood, radius=0.015)
    hub = cyl(f"{name}_cross_hub", (0, 0, 0.0), 0.075, bt + 0.04, m_bronze, 24)
    for o in (bar_a, bar_b, hub):
        o.parent = cross

    # ---- plumbs: four cords with bronze bobs, each swinging from a bar end ----
    plumbs = empty(f"{name}_plumbs", cross, (0, 0, 0))
    amp = math.radians(float(p["sway_deg"]))
    per = max(8.0, float(p["sway_period"]))
    bob_profile = [(0.0, -L - 0.18), (0.03, -L - 0.13), (0.068, -L - 0.06), (0.07, -L - 0.035),
                   (0.045, -L - 0.01), (0.018, -L + 0.005), (0.0, -L + 0.01)]
    for i in range(4):
        a = i * math.pi / 2
        ex, ey = R * math.cos(a), R * math.sin(a)
        cap = cyl(f"{name}_cross_cap{i}", (ex, ey, 0), 0.045, bt + 0.02, m_bronze, 20)
        cap.parent = cross
        piv = empty(f"{name}_plumb{i}", plumbs, (ex, ey, -bt / 2 - 0.01))
        cord = cyl(f"{name}_plumb{i}_cord", (0, 0, -L / 2), 0.012, L, m_cord, 8)
        bob = lathe(f"{name}_plumb{i}_bob", (0, 0, 0), bob_profile, m_bronze, segments=24)
        cord.parent = piv; bob.parent = piv
        if p["sway"] and amp > 0:
            _sway(piv, 0, amp, per, phase=int(i * per * 0.23))
            _sway(piv, 1, amp * 0.7, per * 1.37, phase=int(i * per * 0.41 + 7))
            for fc in fcurves_of(piv):
                if not any(md.type == 'CYCLES' for md in fc.modifiers):
                    fc.modifiers.new('CYCLES')

    return root
