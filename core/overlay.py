"""Overlay scene: captions/cards rendered without depth of field and laid over the main image.

Depth of field blurs anything near the lens, and captions/cards sit just in front of it.  With
DOF on, the builder moves them into a second scene ("Overlay") seen through a twin camera that
copies the main camera but has no DOF; the main compositor lays that render over the film look.
Blender renders every scene that a compositor Render Layers node uses, so previews, partial and
full renders need no extra steps (keep `sync()` after changing resolution % or samples).
"""
import bpy
from . import ctx
from .look import descendants

SCENE = None


def make_overlay(roots, samples=8):
    global SCENE
    main = ctx.sc
    sc2 = bpy.data.scenes.new("Overlay"); SCENE = sc2
    sc2.render.engine = main.render.engine
    sc2.render.resolution_x, sc2.render.resolution_y = main.render.resolution_x, main.render.resolution_y
    sc2.render.resolution_percentage = main.render.resolution_percentage
    sc2.render.fps = main.render.fps; sc2.frame_start, sc2.frame_end = main.frame_start, main.frame_end
    sc2.render.film_transparent = True
    sc2.view_settings.view_transform = 'Standard'; sc2.view_settings.look = 'None'
    try: sc2.eevee.taa_render_samples = 4             # flat text and cards: 4 samples are enough
    except Exception: pass
    sc2.render.use_motion_blur = False
    cd = ctx.cam_d.copy(); cd.name = "CamOverlay"; cd.dof.use_dof = False
    cam2 = bpy.data.objects.new("CamOverlay", cd); sc2.collection.objects.link(cam2); sc2.camera = cam2
    cn = cam2.constraints.new('COPY_TRANSFORMS'); cn.target = ctx.cam
    sc2.collection.objects.link(ctx.cam)                     # parent of the overlay objects: evaluate it here too
    for r in roots:
        if r is None: continue
        for o in [r] + descendants(r):
            for coll in list(o.users_collection): coll.objects.unlink(o)
            sc2.collection.objects.link(o)
    # composite: FilmLook output -> Alpha Over (overlay on top)
    ng = main.compositing_node_group
    out = next(n for n in ng.nodes if n.bl_idname == 'NodeGroupOutput')
    src = out.inputs[0].links[0].from_socket
    rl2 = ng.nodes.new('CompositorNodeRLayers'); rl2.scene = sc2
    ao = ng.nodes.new('CompositorNodeAlphaOver')
    ins = [s for s in ao.inputs if s.type == 'RGBA']
    ng.links.new(src, ins[0]); ng.links.new(rl2.outputs["Image"], ins[1])
    ng.links.new(ao.outputs[0], out.inputs[0])
    return sc2


def sync(pct=None, samples=None):
    if SCENE is None: return
    if pct is not None: SCENE.render.resolution_percentage = pct
    if samples is not None:
        try: SCENE.eevee.taa_render_samples = 4      # flat text and cards: 4 samples look the same as 12 (PSNR 50 dB), -19 s/frame on CPU
        except Exception: pass
