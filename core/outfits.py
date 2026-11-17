"""Cultures, outfits, looks and crowds for long-form history videos.

library/cultures/<id>/culture.json   palette, hair/beard styles, skin tones, roles -> outfit ids, sources
library/outfits/<id>/outfit.json     2D pieces drawn on a character (same ops as char.json "extras"), colours by slot

Slots (resolved per character): $team $team_dark (faction colour), $cloth $cloth2 $metal $metal_dark $leather $trim
(culture palette, outfit may override), $hair, $accent (the protagonist's own colour), $skin, $ink, $white.
"on": torso | head | footL | footR | handL | handR  (hands: origin at the hand centre, so held items follow the arm).
Hair and beard come from the look (culture defaults + seed); outfits may force them ("hair": "none" under a full helmet).
"""
import json, math, os, random
import bpy
from . import ctx, geo
from .geo import shape, stroke, ellipse, arc
from .look import flat

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, "library")
INK = (0.04, 0.04, 0.05)
DEFAULT_PALETTE = {"cloth": (0.55, 0.45, 0.30), "cloth2": (0.40, 0.32, 0.20), "metal": (0.55, 0.56, 0.60), "metal_dark": (0.30, 0.31, 0.35),
                   "leather": (0.35, 0.20, 0.09), "trim": (0.85, 0.65, 0.15)}
HAIR_STYLES = ("none", "short", "long", "tied", "curly", "topknot", "braids", "bald_sides")
BEARDS = ("none", "mustache", "full", "goatee")


def load(kind, name):
    p = os.path.join(LIB, kind, name, {"cultures": "culture.json", "outfits": "outfit.json"}[kind])
    if not os.path.exists(p): raise ValueError(f"library {kind}/{name} not found")
    return json.load(open(p, encoding="utf-8"))


def exists(kind, name):
    return os.path.exists(os.path.join(LIB, kind, name, {"cultures": "culture.json", "outfits": "outfit.json"}[kind]))


def darker(rgb, k=0.6): return tuple(c * k for c in rgb)


def resolve_look(spec, faction, culture, outfit, seed_base=0):
    """-> dict of slot colours + hair/beard choice for one character"""
    import zlib                                   # stable seed (hash() of str changes between runs)
    rnd = random.Random(zlib.crc32(f"{spec.get('id', '')}|{seed_base}|{spec.get('look', {}).get('seed', 0)}".encode()))
    look = dict(spec.get("look", {}))
    pal = dict(DEFAULT_PALETTE)
    pal.update({k: tuple(v) for k, v in (culture or {}).get("palette", {}).items()})
    pal.update({k: tuple(v) for k, v in (outfit or {}).get("palette", {}).items()})
    pal.update({k: tuple(v) for k, v in look.get("palette", {}).items()})      # this character's own colours (dialogue videos)
    team = tuple((faction or {}).get("color") or pal.get("team") or (0.6, 0.1, 0.08))
    hairs = (culture or {}).get("hair_colors") or [(0.20, 0.12, 0.06), (0.10, 0.07, 0.05), (0.35, 0.20, 0.08)]
    skins = (culture or {}).get("skin_tones") or [(0.98, 0.98, 0.97)]
    slots = dict(pal, team=team, team_dark=darker(team), ink=INK, white=(0.98, 0.98, 0.97),
                 hair=tuple(look.get("hair_color") or rnd.choice(hairs)), accent=tuple(look.get("accent") or team),
                 skin=tuple(look.get("skin") or ((0.98, 0.98, 0.97) if look.get("skin_mode", "cartoon") == "cartoon" else rnd.choice(skins))))
    styles = (culture or {}).get("hair_styles") or ["short"]
    hair = look.get("hair") or (outfit or {}).get("hair") or rnd.choice(styles)
    beard_p = (culture or {}).get("beard_prob", 0.3)
    beard = look.get("beard") or (outfit or {}).get("beard")
    if not beard:
        beard = rnd.choice((culture or {}).get("beard_styles") or ["full"]) if rnd.random() < beard_p else "none"
    if look.get("signature"): slots["sig"] = tuple(look.get("sig_color") or (0.92, 0.2, 0.3))
    return {"slots": slots, "hair": hair, "beard": beard, "skin_mode": look.get("skin_mode", "cartoon"), "has_accent": bool(look.get("accent")),
            "signature": look.get("signature")}


def mat(name, slots, key):
    if isinstance(key, (list, tuple)): rgb = tuple(key)
    elif isinstance(key, str) and key.startswith("$"): rgb = slots.get(key[1:], (1, 0, 1))
    else: rgb = slots.get(key, (1, 0, 1))
    return flat(f"of_{name}_{'_'.join(f'{c:.3f}' for c in rgb)}", rgb)


def parent_of(c, on):
    if on in ("handL", "handR"):
        lo = (c.armL if on == "handL" else c.armR)[1]
        return lo, (0.0, -c.aL[1] - 0.05)
    if on in ("footL", "footR"): return getattr(c, on), (0.04, c.foot_y - 0.02)
    return getattr(c, on), (0.0, 0.0)


def draw_ops(c, prefix, ops, slots, groups):
    """draw outfit ops; groups[on] = empty under that body part that holds this outfit (for outfit changes)"""
    for i, op in enumerate(ops):
        on = op.get("on", "torso"); par, (dx, dy) = parent_of(c, on)
        if on not in groups: groups[on] = geo.empty(f"{prefix}_{on}", par)
        g = groups[on]; nm = f"{prefix}_{op.get('name', i)}"
        m = mat(op.get("name", str(i)), slots, op.get("mat", "$cloth"))
        pts = geo.points(op["pts"]) if "pts" in op else None
        if pts and (dx or dy): pts = [(x + dx, y + dy) for x, y in pts]
        if op["op"] == "shape":
            shape(g, nm, pts, m, op.get("z", 0.18), **({"outline": op["outline"]} if "outline" in op else {}))
        elif op["op"] == "stroke":
            stroke(g, nm, pts, op.get("w", 0.04), op.get("z", 0.18), m=m)
        elif op["op"] == "disc":
            geo.disc(g, nm, op["c"][0] + dx, op["c"][1] + dy, op["r"], op.get("z", 0.18), m)
        else:
            raise ValueError(f"outfit op {op['op']!r} (shape, stroke, disc)")
    return groups


def hair_ops(style, r):
    """hair behind/around the white head disc (z < 0 behind, small z > 0 for fringes)"""
    H = "$hair"
    if style in ("none", None): return []
    if style == "bald_sides":
        return [{"op": "shape", "on": "head", "name": "hair_l", "pts": {"ellipse": [-r * 0.92, 0.0, r * 0.16, r * 0.3, 16]}, "mat": H, "z": -0.04},
                {"op": "shape", "on": "head", "name": "hair_r", "pts": {"ellipse": [r * 0.92, 0.0, r * 0.16, r * 0.3, 16]}, "mat": H, "z": -0.04}]
    ops = [{"op": "shape", "on": "head", "name": "hair_back", "pts": {"ellipse": [0, r * 0.12, r * 1.06, r * 0.98, 36]}, "mat": H, "z": -0.05}]
    if style == "short":
        ops.append({"op": "shape", "on": "head", "name": "hair_top", "pts": {"ellipse": [0, r * 0.55, r * 0.86, r * 0.42, 28, 0, math.pi]}, "mat": H, "z": 0.015})
    elif style == "long":
        ops += [{"op": "shape", "on": "head", "name": "hair_long", "pts": {"rrect": [0, -r * 0.35, r * 2.25, r * 1.5, r * 0.4]}, "mat": H, "z": -0.06},
                {"op": "shape", "on": "head", "name": "hair_top", "pts": {"ellipse": [0, r * 0.55, r * 0.88, r * 0.42, 28, 0, math.pi]}, "mat": H, "z": 0.015}]
    elif style == "tied":
        ops += [{"op": "shape", "on": "head", "name": "hair_top", "pts": {"ellipse": [0, r * 0.55, r * 0.86, r * 0.42, 28, 0, math.pi]}, "mat": H, "z": 0.015},
                {"op": "shape", "on": "head", "name": "hair_tail", "pts": {"ellipse": [-r * 1.05, -r * 0.2, r * 0.2, r * 0.5, 18]}, "mat": H, "z": -0.06}]
    elif style == "curly":
        for k in range(7):
            a = math.pi * (0.1 + 0.8 * k / 6)
            ops.append({"op": "disc", "on": "head", "name": f"hair_c{k}", "c": [r * 0.9 * math.cos(a), r * 0.9 * math.sin(a) + r * 0.1], "r": r * 0.24, "mat": H, "z": -0.045})
        ops.append({"op": "shape", "on": "head", "name": "hair_top", "pts": {"ellipse": [0, r * 0.58, r * 0.8, r * 0.36, 28, 0, math.pi]}, "mat": H, "z": 0.015})
    elif style == "topknot":
        ops += [{"op": "shape", "on": "head", "name": "hair_top", "pts": {"ellipse": [0, r * 0.55, r * 0.86, r * 0.42, 28, 0, math.pi]}, "mat": H, "z": 0.015},
                {"op": "shape", "on": "head", "name": "hair_knot", "pts": {"ellipse": [0, r * 1.12, r * 0.24, r * 0.2, 18]}, "mat": H, "z": -0.04}]
    elif style == "braids":
        ops += [{"op": "shape", "on": "head", "name": "hair_top", "pts": {"ellipse": [0, r * 0.55, r * 0.86, r * 0.42, 28, 0, math.pi]}, "mat": H, "z": 0.015},
                {"op": "stroke", "on": "head", "name": "braid_l", "pts": [[-r * 0.95, 0], [-r * 1.0, -r * 0.9], [-r * 0.9, -r * 1.4]], "w": r * 0.22, "mat": H, "z": -0.06},
                {"op": "stroke", "on": "head", "name": "braid_r", "pts": [[r * 0.95, 0], [r * 1.0, -r * 0.9], [r * 0.9, -r * 1.4]], "w": r * 0.22, "mat": H, "z": -0.06}]
    return ops


def beard_ops(style, r):
    H = "$hair"
    if style == "mustache":
        return [{"op": "shape", "on": "head", "name": "mustache", "pts": {"ellipse": [0, -r * 0.17, r * 0.28, r * 0.065, 20]}, "mat": H, "z": 0.06}]
    if style == "goatee":
        return [{"op": "shape", "on": "head", "name": "goatee", "pts": {"ellipse": [0, -r * 0.86, r * 0.2, r * 0.16, 18]}, "mat": H, "z": 0.06},
                {"op": "shape", "on": "head", "name": "mustache", "pts": {"ellipse": [0, -r * 0.17, r * 0.26, r * 0.06, 20]}, "mat": H, "z": 0.06}]
    if style == "full":
        jaw = arc(0, -r * 0.05, r * 0.98, r * 0.98, math.radians(200), math.radians(340), 18)
        inner = list(reversed(arc(0, -r * 0.12, r * 0.62, r * 0.62, math.radians(215), math.radians(325), 14)))
        return [{"op": "shape", "on": "head", "name": "beard", "pts": [list(p) for p in jaw + inner], "mat": H, "z": 0.05, "outline": 0.025},
                {"op": "shape", "on": "head", "name": "mustache", "pts": {"ellipse": [0, -r * 0.17, r * 0.26, r * 0.06, 20]}, "mat": H, "z": 0.06}]
    return []


def dress(c, cid, outfit, look, head_r, prefix=None):
    """draw one outfit (+ the look's hair/beard) on character c; -> list of group empties (for outfit changes)"""
    prefix = prefix or f"{cid}_of"
    slots = look["slots"]
    groups = {}
    hair = outfit.get("hair", look["hair"]) if outfit.get("hair") != "auto" else look["hair"]
    own_face_hair = any(op.get("on") == "head" and any(k in op.get("name", "").lower() for k in ("beard", "mustache", "moustache", "goatee"))
                        for op in outfit.get("items", []))
    draw_ops(c, prefix + "_hair", hair_ops(hair, head_r) + ([] if own_face_hair else beard_ops(look["beard"], head_r)), slots, groups)
    draw_ops(c, prefix, outfit.get("items", []), slots, groups)
    if look.get("has_accent") and outfit.get("accent_item", True):
        # the protagonist's own colour: a neck scarf (works with every culture; outfits can opt out with accent_item: false)
        th = getattr(c, "torso_h", 0.82)
        draw_ops(c, prefix + "_acc", [
            {"op": "shape", "on": "torso", "name": "scarf", "pts": {"rrect": [0, th - 0.02, 0.46, 0.15, 0.06]}, "mat": "$accent", "z": 0.335, "outline": 0.025},
            {"op": "shape", "on": "torso", "name": "scarf_tail", "pts": [[0.06, th - 0.06], [0.2, th - 0.06], [0.16, th - 0.32], [0.04, th - 0.28]],
             "mat": "$accent", "z": 0.34, "outline": 0.022}], slots, groups)
    if look.get("signature") and look["signature"] != "none":            # dialogue: one memorable item per character
        draw_ops(c, prefix + "_sig", signature_ops(look["signature"], head_r), slots, groups)
    return list(groups.values())


# ---------------------------------------------------------------- signature items (dialogue characters)
SIGNATURES = ("none", "bow", "glasses", "ahoge", "cap", "freckles", "earrings", "headband", "beanie", "flower", "lashes")


def signature_ops(kind, r=0.5):
    """one memorable item per character, drawn on the head (r = head radius, eyes at y -0.02, x +-0.15).
    Colour slot $sig (stays coloured in the grey look: a single spot of colour on a grey character)."""
    k = r / 0.5; S = "$sig"
    def P(pts): return [[round(x * k, 4), round(y * k, 4)] for x, y in pts]
    if kind == "bow":
        return [{"op": "shape", "on": "head", "name": "sig_bow_l", "pts": P([[0.3, 0.44], [0.1, 0.6], [0.08, 0.32]]), "mat": S, "z": 0.02, "outline": 0.022},
                {"op": "shape", "on": "head", "name": "sig_bow_r", "pts": P([[0.3, 0.44], [0.5, 0.62], [0.52, 0.34]]), "mat": S, "z": 0.02, "outline": 0.022},
                {"op": "disc", "on": "head", "name": "sig_bow_k", "c": P([[0.3, 0.44]])[0], "r": 0.055 * k, "mat": S, "z": 0.025}]
    if kind == "glasses":
        return [{"op": "stroke", "on": "head", "name": f"sig_glass{s_}", "pts": {"ring": [s_ * 0.16 * k, -0.02 * k, 0.135 * k, 0.13 * k, 28]},
                 "w": 0.032 * k, "mat": S, "z": 0.1} for s_ in (-1, 1)] +                [{"op": "stroke", "on": "head", "name": "sig_glass_bridge", "pts": P([[-0.03, 0.0], [0.0, 0.02], [0.03, 0.0]]), "w": 0.028 * k, "mat": S, "z": 0.1}]
    if kind == "ahoge":           # one stubborn curl of hair standing up
        return [{"op": "stroke", "on": "head", "name": "sig_hair_curl", "pts": P([[0.02, 0.46], [-0.01, 0.6], [0.06, 0.72], [0.15, 0.7], [0.14, 0.61], [0.07, 0.62]]),
                 "w": 0.04 * k, "mat": "$hair", "z": -0.04}]
    if kind == "cap":
        return [{"op": "shape", "on": "head", "name": "sig_cap", "pts": {"ellipse": [0, 0.26 * k, 0.53 * k, 0.32 * k, 28, 0, 3.14159]}, "mat": S, "z": 0.02, "outline": 0.025},
                {"op": "shape", "on": "head", "name": "sig_cap_brim", "pts": P([[0.05, 0.3], [0.72, 0.3], [0.7, 0.22], [0.05, 0.22]]), "mat": S, "z": 0.025, "outline": 0.022},
                {"op": "disc", "on": "head", "name": "sig_cap_btn", "c": [0, 0.59 * k], "r": 0.035 * k, "mat": S, "z": 0.022}]
    if kind == "freckles":
        return [{"op": "disc", "on": "head", "name": f"sig_frk{s_}{j}", "c": [round(s_ * (0.24 + 0.05 * (j % 2)) * k, 4), round((-0.11 - 0.04 * (j // 2)) * k, 4)],
                 "r": 0.016 * k, "mat": [0.45, 0.22, 0.1], "z": 0.07} for s_ in (-1, 1) for j in range(3)]
    if kind == "earrings":
        return [{"op": "stroke", "on": "head", "name": f"sig_ear{s_}", "pts": {"ring": [s_ * 0.5 * k, -0.24 * k, 0.05 * k, 0.06 * k, 18]},
                 "w": 0.022 * k, "mat": S, "z": -0.03} for s_ in (-1, 1)]
    if kind == "headband":
        return [{"op": "stroke", "on": "head", "name": "sig_band", "pts": {"arc": [0, 0.1 * k, 0.5 * k, 0.4 * k, 20, 160, 20]}, "w": 0.075 * k, "mat": S, "z": 0.02}]
    if kind == "beanie":
        return [{"op": "shape", "on": "head", "name": "sig_beanie", "pts": {"ellipse": [0, 0.3 * k, 0.53 * k, 0.33 * k, 28, 0, 3.14159]}, "mat": S, "z": 0.02, "outline": 0.025},
                {"op": "shape", "on": "head", "name": "sig_beanie_rim", "pts": {"rrect": [0, 0.3 * k, 1.1 * k, 0.12 * k, 0.05 * k]}, "mat": S, "z": 0.025, "outline": 0.022},
                {"op": "disc", "on": "head", "name": "sig_beanie_pom", "c": [0, 0.66 * k], "r": 0.085 * k, "mat": S, "z": 0.015}]
    if kind == "flower":
        cx, cy = 0.33 * k, 0.4 * k
        import math as _m
        return [{"op": "disc", "on": "head", "name": f"sig_petal{j}", "c": [round(cx + 0.07 * k * _m.cos(j * 1.2566), 4), round(cy + 0.07 * k * _m.sin(j * 1.2566), 4)],
                 "r": 0.055 * k, "mat": S, "z": 0.02} for j in range(5)] +                [{"op": "disc", "on": "head", "name": "sig_petal_c", "c": [cx, cy], "r": 0.04 * k, "mat": [1.0, 0.82, 0.15], "z": 0.025}]
    if kind == "lashes":          # three lashes flicking out of each eye
        return [{"op": "stroke", "on": "head", "name": f"sig_lash{s_}{j}", "pts": P([[s_ * (0.2 + 0.035 * j), 0.07 - 0.02 * j], [s_ * (0.25 + 0.05 * j), 0.13 - 0.035 * j]]),
                 "w": 0.02 * k, "mat": "$ink", "z": 0.09} for s_ in (-1, 1) for j in range(3)]
    return []


def apply_skin(c, cid, look):
    """skin tones mode: tint face and hands of this character (default cartoon white keeps the house style)"""
    if look["skin_mode"] == "cartoon": return
    rgb = look["slots"]["skin"]
    c.skin.node_tree.nodes["Emission"].inputs[0].default_value = (*rgb, 1)
    hand_m = flat(f"{cid}_hand_skin", rgb)
    for arm in (c.armL, c.armR):
        for o in arm[1].children:
            if o.name.endswith("_hand"): o.data.materials[0] = hand_m


# ---------------------------------------------------------------- crowds
FORMATIONS = ("block", "line", "column", "wedge", "scatter", "circle")


def formation_offsets(spec, rnd):
    """local (x, y) offsets of the members; x across the front, y = depth (+y away from the camera side)"""
    kind = spec.get("formation", "block"); n = int(spec.get("count", 24))
    dx, dy = spec.get("spacing", [0.9, 0.9]); jit = spec.get("jitter", 0.12)
    pts = []
    if kind in ("block", "line", "column"):
        cols = int(spec.get("cols") or (n if kind == "line" else max(1, int(round(math.sqrt(n * 2))) if kind == "block" else 2)))
        rows = int(math.ceil(n / cols))
        for i in range(n):
            r, k = divmod(i, cols)
            pts.append(((k - (cols - 1) / 2) * dx + (dx * 0.5 if r % 2 and spec.get("stagger") else 0), r * dy))
    elif kind == "wedge":
        r = 0; placed = 0
        while placed < n:
            for k in range(r + 1):
                if placed >= n: break
                pts.append(((k - r / 2) * dx, r * dy)); placed += 1
            r += 1
    elif kind == "circle":
        R = spec.get("radius", max(1.0, n * dx / (2 * math.pi)))
        pts = [(R * math.cos(2 * math.pi * i / n), R * math.sin(2 * math.pi * i / n)) for i in range(n)]
    else:   # scatter
        w, d = spec.get("area", [n ** 0.5 * dx * 1.5, n ** 0.5 * dy * 1.5])
        pts = [(rnd.uniform(-w / 2, w / 2), rnd.uniform(0, d)) for _ in range(n)]
    return [(x + rnd.uniform(-jit, jit), y + rnd.uniform(-jit, jit)) for x, y in pts]


def instance_crowd(name, templates, offsets, root_loc, rot_deg, rnd, scale_jitter=0.04):
    """templates: [(collection, template_root_location)]; -> crowd root empty with one collection instance per member"""
    root = geo.empty(f"crowd_{name}", None, root_loc)
    root.rotation_euler = (0, 0, math.radians(rot_deg))
    members = []
    for i, (x, y) in enumerate(offsets):
        coll, _ = templates[rnd.randrange(len(templates))]
        e = bpy.data.objects.new(f"crowd_{name}_{i}", None); ctx.col.objects.link(e)
        e.instance_type = 'COLLECTION'; e.instance_collection = coll
        e.parent = root; e.location = (x, y, 0.0)
        s = 1.0 + rnd.uniform(-scale_jitter, scale_jitter); e.scale = (s, s, s)
        members.append(e)
    return root, members


def to_template_collection(coll, root_obj, loc):
    """move a built character out of the scene into its (unlinked) collection used by instances"""
    objs = [root_obj] + list(root_obj.children_recursive)
    for o in objs:
        for uc in list(o.users_collection): uc.objects.unlink(o)
        coll.objects.link(o)
    coll.instance_offset = tuple(loc)
    return coll
