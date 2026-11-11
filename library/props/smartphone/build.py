"""2D handheld smartphone: black rounded body, glowing light-blue screen, small front camera.
Screen content: 'blank' | 'apps' (icon grid + dock) | 'chat' (header + alternating bubbles).
Held at the chest (hand-held props are 2D, skill rule 8). Origin = centre of the phone."""
from core.look import flat
from core.geo import empty, shape, stroke, disc, label, rrect

DEFAULTS = dict(
    body_color=[0.02, 0.02, 0.025],
    screen_color=[0.55, 0.85, 0.98],
    content="apps",          # blank | apps | chat
    screen_on=True,
    accent=[0.05, 0.6, 0.25],
    notify=False,
    size=1.0,
    prefix="",
)

W, H = 0.34, 0.62            # body
SW, SH, SY = 0.29, 0.50, -0.01   # screen width/height/centre-y (top 0.24, bottom -0.26)

APP_COLORS = [
    (0.85, 0.10, 0.08), (0.95, 0.70, 0.05), (0.05, 0.55, 0.20),
    (0.98, 0.35, 0.02), (0.45, 0.10, 0.70), (0.03, 0.30, 0.80),
    (0.90, 0.20, 0.50), (0.02, 0.60, 0.60), (0.60, 0.35, 0.10),
]
DOCK_COLORS = [(0.05, 0.55, 0.20), (0.03, 0.30, 0.80), (0.85, 0.10, 0.08)]


def _tag(rgb):
    return "".join("%02x" % max(0, min(255, int(round(c * 255)))) for c in rgb)


def _m(base, rgb):
    """material cached by name -> include colour in the name so custom colours don't collide"""
    return flat(f"smartphone_{base}_{_tag(rgb)}", tuple(rgb))


def _apps(g, pre):
    ic = 0.07
    k = 0
    for row, y in enumerate((0.15, 0.06, -0.03)):
        for col, x in enumerate((-0.09, 0.0, 0.09)):
            shape(g, f"{pre}_app{k}", rrect(x, y, ic, ic, 0.018), _m(f"app{k}", APP_COLORS[k]), 0.04, outline=0.012)
            k += 1
    # dock strip + 3 icons
    shape(g, f"{pre}_dock", rrect(0, -0.19, 0.26, 0.10, 0.03), _m("dock", (0.85, 0.95, 1.0)), 0.04, outline=0)
    for j, x in enumerate((-0.08, 0.0, 0.08)):
        shape(g, f"{pre}_dock{j}", rrect(x, -0.19, ic, ic, 0.018), _m(f"dockapp{j}", DOCK_COLORS[j]), 0.06, outline=0.012)


def _chat(g, pre, accent):
    # header bar with avatar
    shape(g, f"{pre}_head", rrect(0, 0.205, SW - 0.01, 0.07, 0.02), _m("chathead", accent), 0.04, outline=0)
    disc(g, f"{pre}_avatar", -0.10, 0.205, 0.025, 0.06, _m("avatar", (0.98, 0.98, 0.96)))
    stroke(g, f"{pre}_hname", [(-0.06, 0.205), (0.04, 0.205)], 0.02, 0.06, m=_m("hname", (0.98, 0.98, 0.96)))
    gray = _m("bub_them", (0.92, 0.92, 0.94)); txt_g = _m("txt_them", (0.45, 0.45, 0.5))
    mine = _m("bub_me", accent); txt_m = _m("txt_me", (0.98, 0.98, 0.96))
    bubbles = [(-1, 0.10, 0.19), (1, 0.0, 0.17), (-1, -0.11, 0.21)]
    for k, (side, y, w) in enumerate(bubbles):
        x = side * (SW / 2 - 0.02 - w / 2)
        shape(g, f"{pre}_bub{k}", rrect(x, y, w, 0.075, 0.03), mine if side > 0 else gray, 0.04, outline=0.012)
        stroke(g, f"{pre}_txt{k}", [(x - w / 2 + 0.035, y), (x + w / 2 - 0.035, y)], 0.02, 0.06,
               m=txt_m if side > 0 else txt_g)
    # typing field at the bottom
    shape(g, f"{pre}_field", rrect(0, -0.215, 0.25, 0.055, 0.025), _m("field", (0.98, 0.98, 0.96)), 0.04, outline=0.012)


def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    name = p["name"]
    pre = p["prefix"] or name
    g = empty(name, p.get("parent"))
    s = float(p["size"]); g.scale = (s, s, s)

    shape(g, f"{pre}_body", rrect(0, 0, W, H, 0.06), _m("body", p["body_color"]), 0, outline=0.035)
    scr_rgb = p["screen_color"] if p["screen_on"] else (0.01, 0.012, 0.02)
    shape(g, f"{pre}_screen", rrect(0, SY, SW, SH, 0.035), _m("screen", scr_rgb), 0.02, outline=0.012)
    disc(g, f"{pre}_camera", 0, H / 2 - 0.035, 0.02, 0.02, _m("camera", (0.25, 0.25, 0.3)))

    content = empty(f"{pre}_content", g)
    if p["screen_on"]:
        if p["content"] == "apps":
            _apps(content, pre)
        elif p["content"] == "chat":
            _chat(content, pre, p["accent"])

    badge = empty(f"{pre}_badge", g, (W / 2 - 0.01, H / 2 - 0.01, 0))
    disc(badge, f"{pre}_badge_dot", 0, 0, 0.055, 0.08, _m("badge", (0.9, 0.05, 0.05)))
    shape(badge, f"{pre}_badge_ring", rrect(0, 0, 0.11, 0.11, 0.055), _m("badge", (0.9, 0.05, 0.05)), 0.08, outline=0.02)
    label(badge, f"{pre}_badge_txt", "!", (0, -0.03), 0.09, _m("badgetxt", (0.98, 0.98, 0.96)))
    if not p["notify"]:
        for o in [badge] + list(badge.children_recursive):
            o.hide_render = True; o.hide_viewport = True
    return g
