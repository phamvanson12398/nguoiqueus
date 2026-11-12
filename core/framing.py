"""Shot presets for long-form (16:9) shot lists: "closeup of joe, push in" -> camera keys.

Pure python (no bpy), so storycheck/bridge can use it too.  A shot may give `frame` instead of `keys`:

    {"a": 120, "b": 210, "type": "closeup",
     "frame": {"subject": "joe", "move": "push_in", "angle": 15, "height": "low", "x": -0.3}}

subject   character id / object name (resolved by the builder at the shot's first frame) or [x, y, z] ground point
type      ecu closeup medium full wide establishing insert (board/map/diagram/card/pov/interior: like wide unless 'size')
angle     degrees around the subject; 0 = camera in front (on -Y), +90 = camera on +X (subject's left)
height    eye | low | high | top (straight down, for boards and maps)
x, y      where the subject sits in frame (-1..1; x = -0.33 puts it on the left third)
size      frame height in scene units (overrides the type), lens (overrides the type's lens)
move      push_in pull_out pan_left pan_right truck_left truck_right crane_up crane_down orbit_left orbit_right
          drift (default: slow push + a little truck)   amount 0..2 scales the move (default 1)
roll      degrees (constant), fstop  (also accepted on the shot itself)
"""
import math

SENSOR_H = 36.0 * 9 / 16             # 16:9, sensor fit on the 36 mm width -> 20.25 mm tall
# frame height (scene units), look height above the subject's ground point, default lens
PRESETS = {
    "ecu":          (0.95, 2.02, 70),
    "closeup":      (1.65, 1.85, 55),
    "medium":       (2.4, 1.55, 40),
    "full":         (3.5, 1.30, 32),
    "wide":         (7.0, 1.40, 28),
    "establishing": (14.0, 2.00, 24),
    "insert":       (0.9, 0.0, 50),       # look at the subject point itself
    "pov":          (2.4, 1.70, 30),
}
ALIAS = {"board": "wide", "map": "wide", "diagram": "full", "card": "medium", "interior": "wide"}
MOVES = ("push_in", "pull_out", "pan_left", "pan_right", "truck_left", "truck_right", "crane_up", "crane_down",
         "orbit_left", "orbit_right", "drift", "static_drift")


def preset(type_):
    t = type_ if type_ in PRESETS else ALIAS.get(type_, "medium")
    return t, PRESETS[t]


def frame_keys(fr, type_, a, b, subject_pos, aspect=16 / 9):
    """-> [(a, cam, look, lens, roll), (b, cam, look, lens, roll)]"""
    t, (H, look_h, lens) = preset(fr.get("type", type_))
    k = max(0.35, min(2.0, float(fr.get("_scale", 1.0))))   # subject head height / a person's (goat, cow, child, giant)
    if t in ("ecu", "closeup", "medium", "full", "pov") and "size" not in fr: H *= max(k, 0.6)
    look_h *= k
    H = float(fr.get("size", H)); lens = float(fr.get("lens", lens))
    sx, sy, sz = subject_pos
    if t == "insert" and "size" not in fr: H = 0.9
    flat_top = type_ in ("board", "map") or fr.get("type") in ("board", "map")        # maps/boards lie on the table
    look = [sx, sy, sz + (look_h if t != "insert" and not flat_top else 0.0) + float(fr.get("look_dz", 0.0))]
    d = H * lens / SENSOR_H                                   # distance that shows H units of height
    ang = math.radians(float(fr.get("angle", 0.0)))
    height = fr.get("height", {"insert": "high"}.get(t, "top" if type_ in ("board", "map") else "eye"))
    W = H * aspect
    # subject placement in frame: move the look point the other way
    fx, fy = float(fr.get("x", 0.0)), float(fr.get("y", 0.0))
    right = (math.cos(ang), math.sin(ang), 0.0)               # screen right when looking from angle 0 (from -Y)
    look = [look[0] - right[0] * fx * W / 2, look[1] - right[1] * fx * W / 2, look[2] - fy * H / 2]
    if height == "top":
        look[2] = sz + float(fr.get("look_dz", 0.0))
        tilt = math.radians(10)                                  # nearly straight down; 10 deg keeps 'up' = +Y (no random roll)
        cam = [look[0] + math.sin(ang) * d * math.sin(tilt), look[1] - math.cos(ang) * d * math.sin(tilt), look[2] + d * math.cos(tilt)]
    else:
        elev = {"eye": -0.04, "low": -0.20, "high": 0.38}.get(height, -0.04)   # slightly low by default (STYLE)
        horiz = d * math.cos(elev)
        cam = [look[0] + math.sin(ang) * horiz, look[1] - math.cos(ang) * horiz, look[2] + d * math.sin(elev)]
    cam[2] = max(cam[2], sz + 0.12)                         # never under the ground the subject stands on
    roll = float(fr.get("roll", 0.0))
    move = fr.get("move", "drift"); k = float(fr.get("amount", 1.0))
    c0, l0, c1, l1 = list(cam), list(look), list(cam), list(look)
    fwd = [l0[i] - c0[i] for i in range(3)]; n = math.sqrt(sum(x * x for x in fwd)) or 1; fwd = [x / n for x in fwd]
    side = [right[0], right[1], 0.0]

    def add(v, u, s): return [v[i] + u[i] * s for i in range(3)]
    lens0 = lens1 = lens
    if height == "top":
        # seen from above every move is a slide of camera AND look (no yaw), a push along the view, or a slow roll
        if move in ("push_in", "pull_out", "crane_down", "crane_up"):
            sgn = 1 if move in ("push_in", "crane_down") else -1
            c0 = add(cam, fwd, -0.07 * d * k * sgn); c1 = add(cam, fwd, 0.07 * d * k * sgn)
        elif move in ("orbit_left", "orbit_right"):
            r0 = roll - 3 * k if move == "orbit_left" else roll + 3 * k
            r1 = roll + 3 * k if move == "orbit_left" else roll - 3 * k
            r = lambda v: [round(x, 4) for x in v]
            return [(a, r(cam), r(look), round(lens, 2), r0), (b, r(cam), r(look), round(lens, 2), r1)]
        elif move == "static_drift":
            c0 = add(cam, fwd, -0.015 * d); c1 = add(cam, fwd, 0.015 * d)
        else:
            sx_ = {"pan_left": -1, "truck_left": -1, "pan_right": 1, "truck_right": 1}.get(move, 0.4)
            s_ = sx_ * 0.12 * W * k; up = (0.0, 1.0, 0.0) if move == "drift" else (0.0, 0.0, 0.0)
            c0 = add(add(cam, side, -s_ / 2), up, -0.02 * H * k); c1 = add(add(cam, side, s_ / 2), up, 0.02 * H * k)
            l0 = add(add(look, side, -s_ / 2), up, -0.02 * H * k); l1 = add(add(look, side, s_ / 2), up, 0.02 * H * k)
            if move == "drift": c0 = add(c0, fwd, -0.03 * d * k); c1 = add(c1, fwd, 0.03 * d * k)
        r = lambda v: [round(x, 4) for x in v]
        return [(a, r(c0), r(l0), round(lens, 2), roll), (b, r(c1), r(l1), round(lens, 2), roll)]
    if move == "push_in": c0 = add(cam, fwd, -0.07 * d * k); c1 = add(cam, fwd, 0.07 * d * k)
    elif move == "pull_out": c0 = add(cam, fwd, 0.07 * d * k); c1 = add(cam, fwd, -0.07 * d * k)
    elif move in ("pan_left", "pan_right"):
        s = (-1 if move == "pan_left" else 1) * 0.16 * W * k
        l0 = add(look, side, -s / 2); l1 = add(look, side, s / 2)
    elif move in ("truck_left", "truck_right"):
        s = (-1 if move == "truck_left" else 1) * 0.14 * W * k
        c0 = add(cam, side, -s / 2); c1 = add(cam, side, s / 2); l0 = add(look, side, -s / 2); l1 = add(look, side, s / 2)
    elif move in ("crane_up", "crane_down"):
        s = (1 if move == "crane_up" else -1) * 0.22 * H * k
        c0 = add(cam, (0, 0, 1), -s / 2); c1 = add(cam, (0, 0, 1), s / 2)
        l0 = add(look, (0, 0, 1), -s / 6); l1 = add(look, (0, 0, 1), s / 6)
    elif move in ("orbit_left", "orbit_right"):
        da = math.radians((1 if move == "orbit_left" else -1) * 9 * k)
        def orb(t):
            dx, dy = cam[0] - look[0], cam[1] - look[1]
            return [look[0] + dx * math.cos(t) - dy * math.sin(t), look[1] + dx * math.sin(t) + dy * math.cos(t), cam[2]]
        c0, c1 = orb(-da / 2), orb(da / 2)
    elif move == "static_drift":
        c0 = add(cam, fwd, -0.015 * d); c1 = add(cam, fwd, 0.015 * d)
    else:                                                     # drift: slow push + a little truck
        c0 = add(add(cam, fwd, -0.04 * d * k), side, -0.03 * W * k)
        c1 = add(add(cam, fwd, 0.04 * d * k), side, 0.03 * W * k)
    r = lambda v: [round(x, 4) for x in v]
    return [(a, r(c0), r(l0), round(lens0, 2), roll), (b, r(c1), r(l1), round(lens1, 2), roll)]


def describe(type_, fr):
    t, (H, _, lens) = preset(fr.get("type", type_))
    return f"{t}: frame {fr.get('size', H)} tall, lens {fr.get('lens', lens)}, distance {float(fr.get('size', H)) * float(fr.get('lens', lens)) / SENSOR_H:.2f}"
