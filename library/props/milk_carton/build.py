"""3D American half-gallon milk carton: square white body, a coloured band wrapped around it,
big label text (default MILK) on the front face (-Y), gable (pointy) roof whose ridge runs along X,
with the glued top fin on the ridge.  Optional opened spout on the +X gable end and a milk stream.
Falls / tips over / pours -> 3D.  Origin at the centre of the bottom (z = 0 = ground).
Sized ~1.5x the first version (body 0.405 wide, ~0.87 tall overall) so it reads next to a 2.5 character.
Part names: <name>_body, _band, _label, _roof, _fin, _spout (only if open), _stream (only if pour).
The stream runs along the carton's local +X from the spout: it looks right when the carton is tilted
~90 deg toward +X (rotate the root around Y by about +90..+110 deg)."""
import math
from core.look import pbr
from core.geo import rbox, cube, cyl, cone, extrude, text3d, group3d, attach

DEFAULTS = dict(band_color=[0.85, 0.06, 0.05], label="MILK", label_color=None, roof_color=None,
                spout="closed", pour=False, pour_length=1.2, scale=1.0)

K = 1.5             # size factor vs. the first version (all dimensions below scale with it)
W = 0.27 * K        # body width (x) and depth (y)
BH = 0.40 * K       # body height
RH = 0.13 * K       # roof (gable) height
FH = 0.06 * K       # fin height
FT = 0.03 * K       # fin thickness


def _tag(rgb):
    return "_".join(str(int(round(c * 100))) for c in rgb)


def build(params, lib):
    p = dict(DEFAULTS); p.update(params or {})
    name = p["name"]
    band_rgb = tuple(p["band_color"])
    label_rgb = tuple(p["label_color"]) if p.get("label_color") else band_rgb
    white_rgb = (0.92, 0.92, 0.90)
    roof_rgb = tuple(p["roof_color"]) if p.get("roof_color") else white_rgb
    pour = bool(p["pour"])
    spout_open = pour or str(p["spout"]).lower() == "open"

    m_white = pbr("milk_carton_body", white_rgb, rough=0.55)
    m_band = pbr(f"milk_carton_band_{_tag(band_rgb)}", band_rgb, rough=0.5)
    m_label = pbr(f"milk_carton_label_{_tag(label_rgb)}", label_rgb, rough=0.5)
    m_roof = m_white if roof_rgb == white_rgb else pbr(f"milk_carton_roof_{_tag(roof_rgb)}", roof_rgb, rough=0.55)

    root = group3d(name)
    parts = []

    # body: square column standing on the ground
    parts.append(rbox(f"{name}_body", (0, 0, BH / 2), (W, W, BH), m_white, radius=0.012 * K))

    # coloured band wrapped around the lower body (slightly proud of the surface)
    band_h = 0.11 * K
    pad = 0.012 * K
    parts.append(rbox(f"{name}_band", (0, 0, 0.13 * K), (W + pad, W + pad, band_h), m_band, radius=0.008 * K))

    # label text on the front face (-Y), above the band
    label = str(p["label"]) or "MILK"
    size = min(0.105 * K, 0.42 * K / max(len(label), 1))      # keep long labels inside the face width
    lab = text3d(f"{name}_label", (0, -W / 2 - 0.009 * K, 0.28 * K), label, size, m_label,
                 depth=0.018 * K, rot=(math.pi / 2, 0, 0))
    # thin font meshes break the automatic ink hull into white jagged shards; the outline pass
    # skips meshes with more than one user, so a fake user opts the lettering out of the outline
    lab.data.use_fake_user = True
    parts.append(lab)

    # gable roof: triangle in the YZ plane, extruded along X (ridge along X)
    # rot (90, 0, 90 deg): local x -> world y, local y -> world z, local z (extrude) -> world x
    tri = [(-W / 2, 0.0), (W / 2, 0.0), (0.0, RH)]
    parts.append(extrude(f"{name}_roof", (0, 0, BH - 0.002 * K), tri, W, m_roof,
                         rot=(math.pi / 2, 0, math.pi / 2)))

    # glued top fin sitting on the ridge
    parts.append(rbox(f"{name}_fin", (0, 0, BH + RH + FH / 2 - 0.012 * K), (W, FT, FH), m_roof,
                      radius=0.006 * K))

    # opened spout: small 4-sided pyramid poking out of the +X gable end
    spout_tip_x = W / 2 + 0.07 * K
    spout_z = BH + 0.045 * K
    if spout_open:
        sp = cone(f"{name}_spout", (W / 2 + 0.035 * K, 0, spout_z), 0.065 * K, 0.0, 0.07 * K, m_roof,
                  verts=4, rot=(0, math.pi / 2, 0))
        sp.rotation_euler = (math.pi / 4, math.pi / 2, 0)   # diamond shape seen from the side
        parts.append(sp)

    # milk stream: thick white cylinder along local +X from the spout tip
    if pour:
        L = float(p["pour_length"])
        m_milk = pbr("milk_carton_milk", (0.95, 0.95, 0.93), rough=0.25)
        parts.append(cyl(f"{name}_stream", (spout_tip_x + L / 2 - 0.01 * K, 0, spout_z), 0.03 * K, L, m_milk,
                         16, rot=(0, math.pi / 2, 0)))

    attach(root, *parts)
    s = float(p["scale"])
    if s != 1.0:
        root.scale = (s, s, s)
    return root
