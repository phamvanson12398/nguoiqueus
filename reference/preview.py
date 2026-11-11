import bpy, sys, time
exec(open('scene.py').read())
sc = bpy.context.scene
args = sys.argv[sys.argv.index('--') + 1:]
sc.render.resolution_percentage = int(args[1]) if len(args) > 1 else 35
sc.eevee.taa_render_samples = 16
sc.render.image_settings.media_type = 'IMAGE'; sc.render.image_settings.file_format = 'PNG'
for fr in [int(x) for x in args[0].split(',')]:
    t0 = time.time(); sc.frame_set(fr); sc.render.filepath = f'out/p_{fr:04d}.png'
    bpy.ops.render.render(write_still=True); print("FRAME", fr, round(time.time() - t0, 1), "s")
# python3 preview.py -- 50,200,366,640 35
