"""WhyShorts core: Blender library split from the manhole v2 script (toolkit v2) + camera v3.

    ctx      scene reset/settings and shared state (scene, collection, camera, N, FPS, paths)
    look     materials, sky, sun, ink outlines, compositor film look
    geo      3D primitives + 2D toolkit (shape, stroke, disc, limb, billboard, visibility keys)
    timing   easing, noise, voice amplitude, keyframe helpers
    camera   v2 shot camera (bake_shots) and v3 one-take spline rig (solve_camera)
    faces    expression library
    chars    character builder, IK posing, reactions, expressions, lip flap, hand props
    fx       dust puffs, shock lines + '!'
    captions word-by-word captions
    sfx      procedural sound effects + music bed
    mixer    Mix, auto sound rules, sequencer + mp4 output

Run a scene with `blender -b -P <scene.py>`.  Call `start()` first so a re-run in the
Blender UI does not keep stale module state.
"""


def start(n_frames, fps=30, out_dir=None, samples=32, sfx_seed=11):
    """reset Blender + all module state, create shared ink/white/face/puff materials lazily"""
    from . import ctx, look, sfx
    sc = ctx.setup(n_frames, fps, out_dir, samples)
    look.reset()
    sfx.init(sfx_seed)
    return sc
