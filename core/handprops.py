"""Hand-held props for dialogue videos: flat 2D drawings (like the characters) held in one hand.

Each recipe draws into a group whose origin is the grip point (the hand centre) and whose +Y is "up";
chars.pose_char turns the group every frame so the item stays upright (or at the tilt an action asks
for) whatever the forearm does. The hand is drawn over the item (items sit just behind it, z < 0).

`make(c, pid, kind, side, color=None)` -> the group (an empty under the forearm).
Kinds: see KINDS (phone, coffee, mug, soda, bottle, fries, burger, pizza, icecream, bag, keys, book,
remote, paper, receipt, money, flowers, gift, card, popcorn, donut).
"""
import math
from . import geo
from .geo import empty, shape, stroke, ellipse, rrect
from .look import flat

OL = 0.022
SCALE = 1.4


def _m(name, rgb): return flat(f"hp_{name}", tuple(rgb))


def _phone(g, n, col):
    shape(g, n + "_body", rrect(0, 0.1, 0.17, 0.3, 0.03), _m("phone", col or (0.12, 0.12, 0.14)), -0.03, OL)
    shape(g, n + "_scr", rrect(0, 0.105, 0.13, 0.24, 0.015), _m("screen", (0.45, 0.75, 0.98)), -0.025, 0)
    shape(g, n + "_glint", [(-0.05, 0.2), (-0.02, 0.2), (-0.05, 0.12)], _m("glint", (0.8, 0.93, 1.0)), -0.02, 0)


def _coffee(g, n, col):
    cup = [(-0.085, 0.24), (0.085, 0.24), (0.065, -0.04), (-0.065, -0.04)]
    shape(g, n + "_cup", cup, _m("paper_cup", (0.97, 0.96, 0.93)), -0.03, OL)
    shape(g, n + "_sleeve", [(-0.08, 0.15), (0.08, 0.15), (0.07, 0.04), (-0.07, 0.04)], _m("sleeve", col or (0.62, 0.42, 0.25)), -0.025, 0)
    shape(g, n + "_lid", rrect(0, 0.255, 0.2, 0.045, 0.015), _m("lid", (0.95, 0.95, 0.95)), -0.022, OL)


def _mug(g, n, col):
    shape(g, n + "_handle", ellipse(0.1, 0.1, 0.06, 0.07, 18), _m("mug", col or (0.9, 0.3, 0.3)), -0.035, OL)
    shape(g, n + "_hole", ellipse(0.1, 0.1, 0.03, 0.04, 14), _m("mug_hole", (0.6, 0.6, 0.6)), -0.033, 0)
    shape(g, n + "_body", rrect(0, 0.08, 0.2, 0.22, 0.03), _m("mug", col or (0.9, 0.3, 0.3)), -0.03, OL)


def _soda(g, n, col):
    shape(g, n + "_can", rrect(0, 0.08, 0.13, 0.25, 0.025), _m("can", col or (0.85, 0.1, 0.12)), -0.03, OL)
    shape(g, n + "_top", rrect(0, 0.2, 0.12, 0.03, 0.01), _m("alu", (0.82, 0.82, 0.85)), -0.025, 0)
    shape(g, n + "_band", rrect(0, 0.07, 0.13, 0.05, 0.0, 2), _m("can_band", (0.98, 0.98, 0.98)), -0.025, 0)


def _bottle(g, n, col):
    pts = [(-0.06, -0.06), (0.06, -0.06), (0.06, 0.16), (0.03, 0.22), (0.03, 0.3), (-0.03, 0.3), (-0.03, 0.22), (-0.06, 0.16)]
    shape(g, n + "_b", pts, _m("bottle", col or (0.55, 0.82, 0.95)), -0.03, OL)
    shape(g, n + "_cap", rrect(0, 0.31, 0.07, 0.04, 0.01), _m("cap", (0.2, 0.45, 0.9)), -0.025, OL)
    shape(g, n + "_label", rrect(0, 0.06, 0.12, 0.08, 0.0, 2), _m("label", (0.98, 0.98, 0.98)), -0.025, 0)


def _fries(g, n, col):
    for k, x in enumerate((-0.06, -0.03, 0.0, 0.03, 0.06, -0.045, 0.045)):
        h = 0.25 + 0.04 * ((k * 37) % 5) / 4
        shape(g, f"{n}_f{k}", rrect(x, h - 0.08, 0.026, 0.2, 0.006), _m("fry", (0.98, 0.8, 0.2)), -0.035, 0.012)
    box = [(-0.1, 0.17), (-0.05, 0.13), (0.0, 0.15), (0.05, 0.13), (0.1, 0.17), (0.075, -0.04), (-0.075, -0.04)]
    shape(g, n + "_box", box, _m("fries_box", col or (0.88, 0.12, 0.12)), -0.03, OL)


def _burger(g, n, col):
    shape(g, n + "_bun_b", rrect(0, -0.0, 0.26, 0.06, 0.03), _m("bun", (0.9, 0.62, 0.3)), -0.03, OL)
    shape(g, n + "_patty", rrect(0, 0.045, 0.27, 0.05, 0.025), _m("patty", (0.42, 0.22, 0.12)), -0.029, OL)
    shape(g, n + "_lettuce", [(-0.14, 0.075), (-0.1, 0.06), (-0.05, 0.08), (0.0, 0.06), (0.05, 0.08), (0.1, 0.06), (0.14, 0.075), (0.13, 0.095), (-0.13, 0.095)],
          _m("lettuce", (0.45, 0.8, 0.25)), -0.028, 0)
    shape(g, n + "_bun_t", ellipse(0, 0.095, 0.135, 0.09, 24, 0, math.pi), _m("bun", (0.9, 0.62, 0.3)), -0.027, OL)


def _pizza(g, n, col):
    shape(g, n + "_slice", [(0.0, -0.06), (0.12, 0.24), (-0.12, 0.24)], _m("cheese", (0.99, 0.82, 0.3)), -0.03, OL)
    shape(g, n + "_crust", rrect(0, 0.25, 0.26, 0.05, 0.025), _m("crust", (0.85, 0.55, 0.25)), -0.028, OL)
    for k, (x, y) in enumerate(((0.0, 0.15), (-0.04, 0.07), (0.035, 0.05))):
        shape(g, f"{n}_pep{k}", ellipse(x, y, 0.025, 0.025, 12), _m("pepperoni", (0.8, 0.15, 0.12)), -0.025, 0)


def _icecream(g, n, col):
    shape(g, n + "_cone", [(-0.07, 0.12), (0.07, 0.12), (0.0, -0.08)], _m("cone", (0.9, 0.68, 0.38)), -0.03, OL)
    shape(g, n + "_scoop", ellipse(0, 0.17, 0.085, 0.075, 24), _m("scoop", col or (0.98, 0.7, 0.8)), -0.028, OL)


def _bag(g, n, col):
    stroke(g, n + "_handle", [(-0.06, 0.0), (-0.06, 0.06), (0.06, 0.06), (0.06, 0.0)], 0.018, -0.035, m=geo.INK)
    shape(g, n + "_bag", [(-0.13, -0.02), (0.13, -0.02), (0.15, -0.34), (-0.15, -0.34)], _m("bag", col or (0.85, 0.7, 0.45)), -0.03, OL)


def _keys(g, n, col):
    shape(g, n + "_ring", ellipse(0, 0.03, 0.04, 0.04, 16), _m("ring", (0.75, 0.75, 0.78)), -0.03, 0.015)
    shape(g, n + "_k1", [(-0.015, 0.0), (0.015, 0.0), (0.02, -0.14), (0.04, -0.15), (0.0, -0.17), (-0.02, -0.14)], _m("key", col or (0.92, 0.75, 0.25)), -0.028, 0.015)
    shape(g, n + "_fob", rrect(0.06, -0.06, 0.06, 0.1, 0.02), _m("fob", (0.15, 0.15, 0.18)), -0.029, 0.015)


def _book(g, n, col):
    shape(g, n + "_cover", rrect(0, 0.1, 0.24, 0.32, 0.015), _m("book", col or (0.2, 0.4, 0.8)), -0.03, OL)
    shape(g, n + "_spine", rrect(-0.1, 0.1, 0.03, 0.32, 0.0, 2), _m("spine", (0.1, 0.2, 0.45)), -0.025, 0)
    shape(g, n + "_title", rrect(0.015, 0.18, 0.13, 0.04, 0.005), _m("book_title", (0.98, 0.9, 0.5)), -0.025, 0)


def _remote(g, n, col):
    shape(g, n + "_body", rrect(0, 0.1, 0.08, 0.3, 0.03), _m("remote", col or (0.15, 0.15, 0.17)), -0.03, OL)
    shape(g, n + "_power", ellipse(0, 0.21, 0.018, 0.018, 12), _m("red_btn", (0.9, 0.15, 0.15)), -0.025, 0)
    for k in range(3):
        shape(g, f"{n}_btn{k}", ellipse(0, 0.14 - 0.05 * k, 0.02, 0.014, 10), _m("grey_btn", (0.6, 0.6, 0.62)), -0.025, 0)


def _paper(g, n, col):
    shape(g, n + "_sheet", rrect(0, 0.12, 0.24, 0.32, 0.01), _m("paper", col or (0.99, 0.99, 0.97)), -0.03, OL)
    for k in range(5):
        stroke(g, f"{n}_l{k}", [(-0.08, 0.22 - 0.045 * k), (0.08 - 0.03 * (k % 2), 0.22 - 0.045 * k)], 0.01, -0.025, m=_m("ink_line", (0.5, 0.5, 0.55)))


def _receipt(g, n, col):
    pts = [(-0.07, 0.36)] + [(-0.07 + 0.14 * k / 6, 0.36 + (0.012 if k % 2 else 0)) for k in range(7)] + [(0.07, -0.02), (-0.07, -0.02)]
    shape(g, n + "_r", pts, _m("receipt", col or (0.99, 0.99, 0.96)), -0.03, OL)
    for k in range(6):
        stroke(g, f"{n}_l{k}", [(-0.045, 0.3 - 0.05 * k), (0.045 - 0.02 * (k % 2), 0.3 - 0.05 * k)], 0.008, -0.025, m=_m("ink_line", (0.5, 0.5, 0.55)))


def _money(g, n, col):
    for k in range(3):
        shape(g, f"{n}_b{k}", rrect(0.015 * k, 0.06 + 0.012 * k, 0.26, 0.13, 0.01), _m("bill", col or (0.55, 0.8, 0.5)), -0.034 + 0.002 * k, 0.018)
    shape(g, n + "_c", ellipse(0.03, 0.084, 0.035, 0.035, 14), _m("bill_d", (0.3, 0.6, 0.3)), -0.026, 0)


def _flowers(g, n, col):
    c = col or (0.95, 0.3, 0.45)
    for k, (x, y) in enumerate(((-0.08, 0.3), (0.0, 0.34), (0.08, 0.3), (-0.04, 0.24), (0.05, 0.24))):
        stroke(g, f"{n}_st{k}", [(0.0, 0.0), (x * 0.9, y - 0.03)], 0.014, -0.036, m=_m("stem", (0.25, 0.6, 0.25)))
        shape(g, f"{n}_fl{k}", ellipse(x, y, 0.05, 0.05, 16), _m(f"petal{k % 2}", c if k % 2 == 0 else (0.98, 0.85, 0.3)), -0.033, 0.015)
        shape(g, f"{n}_ct{k}", ellipse(x, y, 0.018, 0.018, 10), _m("flower_ct", (0.98, 0.95, 0.75)), -0.03, 0)
    shape(g, n + "_wrap", [(-0.09, 0.14), (0.09, 0.14), (0.025, -0.08), (-0.025, -0.08)], _m("wrap", (0.98, 0.97, 0.9)), -0.029, OL)


def _gift(g, n, col):
    shape(g, n + "_box", rrect(0, 0.12, 0.28, 0.24, 0.015), _m("gift", col or (0.3, 0.55, 0.95)), -0.03, OL)
    shape(g, n + "_rv", rrect(0, 0.12, 0.05, 0.24, 0.0, 2), _m("ribbon", (0.98, 0.85, 0.25)), -0.025, 0)
    shape(g, n + "_rh", rrect(0, 0.12, 0.28, 0.05, 0.0, 2), _m("ribbon", (0.98, 0.85, 0.25)), -0.025, 0)
    for s in (-1, 1):
        shape(g, f"{n}_bow{s}", ellipse(0.05 * s, 0.27, 0.05, 0.03, 14), _m("ribbon", (0.98, 0.85, 0.25)), -0.024, 0.015)


def _card(g, n, col):
    shape(g, n + "_card", rrect(0, 0.08, 0.24, 0.15, 0.015), _m("card", col or (0.2, 0.25, 0.35)), -0.03, OL)
    shape(g, n + "_chip", rrect(-0.06, 0.09, 0.04, 0.035, 0.006), _m("chip", (0.95, 0.8, 0.3)), -0.025, 0)
    stroke(g, n + "_num", [(-0.08, 0.04), (0.08, 0.04)], 0.012, -0.025, m=_m("card_num", (0.85, 0.85, 0.9)))


def _popcorn(g, n, col):
    for k in range(7):
        x = -0.08 + 0.027 * k
        shape(g, f"{n}_p{k}", ellipse(x, 0.26 + 0.02 * (k % 2), 0.035, 0.032, 12), _m("popcorn", (0.99, 0.95, 0.75)), -0.035, 0.012)
    shape(g, n + "_tub", [(-0.11, 0.26), (0.11, 0.26), (0.08, -0.05), (-0.08, -0.05)], _m("tub", (0.98, 0.98, 0.98)), -0.03, OL)
    for k in (-1, 0, 1):
        shape(g, f"{n}_s{k}", [(0.06 * k - 0.016, 0.26), (0.06 * k + 0.016, 0.26), (0.045 * k + 0.012, -0.05), (0.045 * k - 0.012, -0.05)],
              _m("tub_stripe", col or (0.9, 0.15, 0.15)), -0.025, 0)


def _donut(g, n, col):
    shape(g, n + "_d", ellipse(0, 0.1, 0.12, 0.11, 28), _m("dough", (0.9, 0.66, 0.38)), -0.03, OL)
    shape(g, n + "_icing", ellipse(0, 0.11, 0.1, 0.09, 28), _m("icing", col or (0.98, 0.55, 0.75)), -0.027, 0)
    shape(g, n + "_hole", ellipse(0, 0.1, 0.035, 0.03, 16), _m("donut_hole", (0.55, 0.55, 0.55)), -0.024, 0.015)


KINDS = {"phone": _phone, "coffee": _coffee, "mug": _mug, "soda": _soda, "bottle": _bottle, "fries": _fries, "burger": _burger,
         "pizza": _pizza, "icecream": _icecream, "bag": _bag, "keys": _keys, "book": _book, "remote": _remote, "paper": _paper,
         "receipt": _receipt, "money": _money, "flowers": _flowers, "gift": _gift, "card": _card, "popcorn": _popcorn, "donut": _donut}
# how an item is eaten/drunk/used (dialog.py picks the action pose from this)
USE = {"coffee": "drink", "mug": "drink", "soda": "drink", "bottle": "drink", "fries": "eat", "burger": "eat", "pizza": "eat",
       "icecream": "eat", "popcorn": "eat", "donut": "eat", "phone": "look_at", "book": "look_at", "paper": "look_at", "receipt": "look_at",
       "remote": "point_remote"}


def make(c, pid, kind, side, color=None):
    """an item in hand `side` ('L'/'R') of character c: a group at the hand centre, counter-rotated by pose_char"""
    if kind not in KINDS: raise ValueError(f"hand prop kind {kind!r} ({', '.join(sorted(KINDS))})")
    lo = (c.armL if side == "L" else c.armR)[1]
    g = empty(f"{c.name}_hp_{pid}", lo, (0.0, getattr(c, "hand_dy", -c.aL[1] - 0.05), 0.0))
    g.scale = (SCALE,) * 3                     # drawn at real size; a bit bigger reads better in a 9:16 frame
    KINDS[kind](g, f"{c.name}_hp_{pid}", tuple(color) if color else None)
    c.hand_items = getattr(c, "hand_items", []) + [(side, g)]
    c.held = getattr(c, "held", []) + [g]
    return g
