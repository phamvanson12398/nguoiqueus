"""Cartoon bed for dialogue videos: long side toward the camera (x), headboard at one end (head_side -1 = left,
+1 = right). Origin at the bottom centre; mattress top at z = top_h, front edge at y = -depth/2 (faces -Y)."""
from core.look import pbr
from core.geo import rbox, group3d, attach

DEFAULTS = dict(length=2.9, depth=1.3, top_h=0.62, head_side=-1, along="x", width=1.5, roll_y=0.95, frame_color=[0.55, 0.34, 0.18],
                sheet=[0.95, 0.95, 0.98], blanket=[0.35, 0.55, 0.85])


def _tag(rgb): return "_".join(str(int(round(c * 1000))) for c in rgb)


def _along_y(p, wood, sheet, blanket):
    """bed seen from its foot (dialogue lying shots): length along Y, headboard at +Y (far from the camera);
    the blanket covers it up to a soft rolled edge `roll_y` from the head end, where a sleeper's chin is"""
    name, L, W, H = p["name"], float(p["length"]), float(p["width"]), float(p["top_h"])
    root = group3d(name); parts = []
    parts.append(rbox(f"{name}_frame", (0, 0, 0.18), (W, L, 0.26), wood, radius=0.03))
    parts.append(rbox(f"{name}_mattress", (0, 0, (0.31 + H) / 2), (W - 0.08, L - 0.1, H - 0.31), sheet, radius=0.08))
    n = 2 if W >= 1.7 else 1
    for k in range(n):
        x = 0 if n == 1 else (k - 0.5) * W / 2
        parts.append(rbox(f"{name}_pillow{k}", (x, L / 2 - 0.36, H + 0.08), (W / n - 0.18, 0.42, 0.2), sheet, radius=0.08))
    ry = L / 2 - float(p["roll_y"])                       # rolled top edge of the blanket (under the chin)
    blen = ry + L / 2 - 0.02
    parts.append(rbox(f"{name}_blanket", (0, ry - blen / 2, H + 0.05), (W + 0.04, blen, 0.12), blanket, radius=0.05))
    parts.append(rbox(f"{name}_blanket_roll", (0, ry, H + 0.13), (W + 0.06, 0.24, 0.24), blanket, radius=0.11))
    parts.append(rbox(f"{name}_blanket_side", (0, ry - blen / 2, H - 0.12), (W + 0.08, blen, 0.36), blanket, radius=0.06))
    parts.append(rbox(f"{name}_headboard", (0, L / 2 + 0.05, 0.75), (W, 0.1, 1.5), wood, radius=0.04))
    parts.append(rbox(f"{name}_footboard", (0, -L / 2 - 0.05, 0.38), (W, 0.1, 0.76), wood, radius=0.04))
    for s in (-1, 1):
        for y in (-1, 1):
            parts.append(rbox(f"{name}_leg{s}{y}", (s * (W / 2 - 0.08), y * (L / 2 - 0.08), 0.03), (0.1, 0.1, 0.06), wood, radius=0.01))
    attach(root, *parts)
    return root


def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    if p.get("along", "x") == "y":
        return _along_y(p, pbr(f"bed_wood_{_tag(p['frame_color'])}", tuple(p["frame_color"]), rough=0.6),
                        pbr(f"bed_sheet_{_tag(p['sheet'])}", tuple(p["sheet"]), rough=0.9),
                        pbr(f"bed_blanket_{_tag(p['blanket'])}", tuple(p["blanket"]), rough=0.9))
    name, L, D, H, hs = p["name"], float(p["length"]), float(p["depth"]), float(p["top_h"]), (1 if float(p["head_side"]) > 0 else -1)
    wood = pbr(f"bed_wood_{_tag(p['frame_color'])}", tuple(p["frame_color"]), rough=0.6)
    sheet = pbr(f"bed_sheet_{_tag(p['sheet'])}", tuple(p["sheet"]), rough=0.9)
    blanket = pbr(f"bed_blanket_{_tag(p['blanket'])}", tuple(p["blanket"]), rough=0.9)
    root = group3d(name); parts = []
    parts.append(rbox(f"{name}_frame", (0, 0, 0.18), (L, D, 0.26), wood, radius=0.03))
    parts.append(rbox(f"{name}_mattress", (0, 0, (0.31 + H) / 2), (L - 0.1, D - 0.08, H - 0.31), sheet, radius=0.08))
    parts.append(rbox(f"{name}_blanket", (-hs * 0.3, -0.02, H - 0.04), (L - 0.75, D - 0.02, 0.1), blanket, radius=0.05))
    parts.append(rbox(f"{name}_pillow", (hs * (L / 2 - 0.42), 0.0, H + 0.06), (0.55, D * 0.6, 0.16), sheet, radius=0.07))
    parts.append(rbox(f"{name}_headboard", (hs * (L / 2 + 0.04), 0, 0.65), (0.1, D, 1.3), wood, radius=0.04))
    parts.append(rbox(f"{name}_footboard", (-hs * (L / 2 + 0.04), 0, 0.4), (0.1, D, 0.8), wood, radius=0.04))
    for s in (-1, 1):
        for y in (-1, 1):
            parts.append(rbox(f"{name}_leg{s}{y}", (s * (L / 2 - 0.08), y * (D / 2 - 0.08), 0.03), (0.1, 0.1, 0.06), wood, radius=0.01))
    attach(root, *parts)
    return root
