"""3D wooden dining table: thick top (crisp straight edges so a slice of toast can hang
over the -X edge), four square legs and an optional apron frame under the top.
Origin at the bottom centre (floor); the top surface sits at z = height."""
from core.look import pbr, ramp_mat
from core.geo import rbox, group3d, attach

DEFAULTS = dict(height=1.07, top_size=[1.6, 0.9], top_thick=0.08,
                color=[0.42, 0.16, 0.05], leg_color=None,
                leg_inset=0.10, leg_width=0.09, apron=True, grain=True)


def _tag(rgb):
    return "_".join(str(int(round(c * 1000))) for c in rgb)


def _wood(name, rgb, grain):
    rgb = tuple(float(c) for c in rgb)
    nm = f"{name}_{_tag(rgb)}"          # cache key follows the colour so a new colour is not swallowed
    if not grain:
        return pbr(nm, rgb, rough=0.55)
    dark = tuple(c * 0.72 for c in rgb)
    light = tuple(min(1.0, c * 1.18) for c in rgb)
    # noise stretched along X -> long soft streaks like wood grain
    return ramp_mat(nm + "_g", [(0.30, dark), (0.50, rgb), (0.72, light)],
                    tex="noise", scale=3.0, mapping_scale=(0.25, 3.0, 3.0),
                    bump=0.05, rough=0.55, detail=3.0)


def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    name = p["name"]
    H = float(p["height"])
    sx, sy = float(p["top_size"][0]), float(p["top_size"][1])
    th = float(p["top_thick"])
    lw = float(p["leg_width"])
    ins = float(p["leg_inset"])
    col = p["color"]
    lcol = p["leg_color"] if p["leg_color"] is not None else [c * 0.7 for c in col]

    m_top = _wood("dining_table_body", col, p["grain"])
    m_leg = _wood("dining_table_leg", lcol, p["grain"])

    root = group3d(name)

    # top: very small bevel so the -X edge reads as a straight, sharp line
    top = rbox(f"{name}_top", (0, 0, H - th / 2), (sx, sy, th), m_top, radius=0.008, segments=2)
    parts = [top]

    # legs: square, from the floor up to the underside of the top
    leg_h = H - th
    lx = sx / 2 - ins - lw / 2
    ly = sy / 2 - ins - lw / 2
    for tag, (x, y) in (("fl", (-lx, -ly)), ("fr", (lx, -ly)), ("bl", (-lx, ly)), ("br", (lx, ly))):
        parts.append(rbox(f"{name}_leg_{tag}", (x, y, leg_h / 2), (lw, lw, leg_h), m_leg, radius=0.012))

    # apron: one hollow frame between the legs (single object, easy to hide)
    if p["apron"]:
        import bmesh
        import bpy
        ah = min(0.12, leg_h * 0.2)
        at = 0.035
        ox, oy = lx + lw / 2 - 0.01, ly + lw / 2 - 0.01      # outer half-sizes (just inside leg faces)
        z0, z1 = H - th - ah, H - th
        bm = bmesh.new()

        def box(x0, x1, y0, y1):
            vs = [bm.verts.new((x, y, z)) for z in (z0, z1) for y in (y0, y1) for x in (x0, x1)]
            for f in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
                bm.faces.new([vs[i] for i in f])

        box(-ox, ox, -oy, -oy + at)          # front rail
        box(-ox, ox, oy - at, oy)            # back rail
        box(-ox, -ox + at, -oy + at, oy - at)  # -X rail
        box(ox - at, ox, -oy + at, oy - at)    # +X rail
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new(f"{name}_apron")
        bm.to_mesh(me); bm.free()
        # reuse rbox to get an object with the standard ink outline, then swap in the frame mesh
        ap = rbox(f"{name}_apron", (0, 0, 0), (0.1, 0.1, 0.1), m_leg, radius=0)
        old = ap.data
        ap.data = me
        if not me.materials:
            me.materials.append(m_leg)
        try:
            bpy.data.meshes.remove(old)
        except Exception:
            pass
        parts.append(ap)

    attach(root, *parts)
    return root
