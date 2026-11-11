"""Shared scene state for every core module.

All core functions read the current scene, collection, camera, frame count
and paths from here instead of from script globals.  `setup()` resets
Blender and fills these in; `set_camera()` registers the camera that
billboards (characters, dust puffs) turn toward.
"""
import os
import bpy

FPS = 30
N = 1
OUT_DIR = ""
FONT_PATH = None
CLOUD = False
ASPECT = "9:16"        # "9:16" shorts (1080x1920) or "16:9" long-form YouTube (1920x1080)
RES = (1080, 1920)
sc = None
col = None
cam = None
cam_d = None

if os.name == "nt":
    FONT_CANDIDATES = [r"C:\Windows\Fonts\ariblk.ttf", r"C:\Windows\Fonts\arialbd.ttf"]
else:
    FONT_CANDIDATES = ["/usr/share/fonts/opentype/inter/Inter-Black.otf",
                       "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"]


def default_out_dir():
    if os.name == "nt":
        return os.path.join(os.path.expanduser("~"), "Videos", "claude_test")
    return "/home/claude/out/rail"


ASPECTS = {"9:16": (1080, 1920), "16:9": (1920, 1080)}


def frame_half():
    """(half width, half height) of the visible frame at depth lens/28 in front of a 36 mm-sensor camera
    (sensor fit AUTO: the 36 mm cover the longer side) -- the depth captions and cards are kept at"""
    long_ = 36 / 28 / 2
    w, h = RES
    return (long_, long_ * h / w) if w >= h else (long_ * w / h, long_)


def setup(n_frames, fps=30, out_dir=None, samples=32, aspect="9:16"):
    """Reset Blender and apply the standard EEVEE settings (v2 script, lines 11-53); 1080x1920 or 1920x1080."""
    global FPS, N, OUT_DIR, FONT_PATH, CLOUD, sc, col, cam, cam_d, ASPECT, RES
    if aspect not in ASPECTS: raise ValueError(f"aspect must be one of {list(ASPECTS)}")
    FPS, N, ASPECT, RES = fps, n_frames, aspect, ASPECTS[aspect]
    CLOUD = bpy.app.background
    OUT_DIR = out_dir or default_out_dir()
    os.makedirs(OUT_DIR, exist_ok=True)
    FONT_PATH = next((f for f in FONT_CANDIDATES if os.path.exists(f)), None)
    cam = cam_d = None

    if CLOUD:
        bpy.ops.wm.read_factory_settings(use_empty=True)
    else:
        for coll in (bpy.data.objects, bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras,
                     bpy.data.lights, bpy.data.textures, bpy.data.worlds, bpy.data.actions):
            for item in list(coll):
                coll.remove(item)
        if bpy.context.scene.sequence_editor:
            for st in list(bpy.context.scene.sequence_editor.strips):
                bpy.context.scene.sequence_editor.strips.remove(st)
    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = 1, N
    sc.render.fps = FPS
    sc.render.resolution_x, sc.render.resolution_y = RES
    sc.render.resolution_percentage = 100
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.render.engine = 'BLENDER_EEVEE'
    try:
        sc.eevee.taa_render_samples = samples
        sc.eevee.use_shadows = True
        sc.eevee.use_raytracing = True
        sc.eevee.use_fast_gi = True
    except Exception:
        pass
    sc.render.use_motion_blur = False
    col = sc.collection
    return sc


def set_camera(camera_obj):
    global cam, cam_d
    cam = camera_obj; cam_d = camera_obj.data
