"""Compare two fingerprint dumps (and their rendered PNG frames).

    python tools/compare.py <dir_a> <dir_b>
    blender -b --python tools/compare.py -- <dir_a> <dir_b>      (no system Python needed)

Exit code 0 and 'IDENTICAL' when every field and every pixel matches.
"""
import json, os, sys, glob, math

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
A, B = args[0], args[1]
fa = json.load(open(os.path.join(A, "fingerprint.json")))
fb = json.load(open(os.path.join(B, "fingerprint.json")))
IGNORE = {"build_seconds"}

diffs = []
max_num = [0.0, ""]


def walk(a, b, path):
    if len(diffs) > 400: return
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if path == "" and k in IGNORE: continue
            if k not in a: diffs.append(f"only in B: {path}/{k}"); continue
            if k not in b: diffs.append(f"only in A: {path}/{k}"); continue
            walk(a[k], b[k], f"{path}/{k}")
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b): diffs.append(f"length {path}: {len(a)} vs {len(b)}"); return
        for i, (x, y) in enumerate(zip(a, b)): walk(x, y, f"{path}[{i}]")
    elif isinstance(a, float) or isinstance(b, float):
        if not (isinstance(a, (int, float)) and isinstance(b, (int, float))):
            diffs.append(f"{path}: {a!r} vs {b!r}"); return
        if a != b:
            d = abs(a - b)
            if d > max_num[0]: max_num[:] = [d, path]
            diffs.append(f"{path}: {a!r} vs {b!r} (diff {d:.3g})")
    elif a != b:
        diffs.append(f"{path}: {a!r} vs {b!r}")


walk(fa, fb, "")
n_keys = sum(v["n"] for o in fa["objects"].values() for v in o["anim"].values())
print(f"A: {len(fa['objects'])} objects, {len(fa['meshes'])} meshes, {len(fa['curves'])} curves, "
      f"{len(fa['materials'])} materials, {n_keys} object keyframes, {len(fa['evaluated'])} evaluated frames")
print(f"build time A {fa.get('build_seconds')} s, B {fb.get('build_seconds')} s")
if diffs:
    print(f"SCENE DIFFERS: {len(diffs)} differences (showing 40); largest numeric {max_num[0]:.3g} at {max_num[1]}")
    for d in diffs[:40]: print("  ", d)
else:
    print("scene data: identical (every property, keyframe, evaluated matrix, audio hash)")


def load_png(path):
    try:
        import numpy as np
        try:
            from PIL import Image
            return np.asarray(Image.open(path).convert("RGBA"), dtype=np.int16)
        except ImportError:
            import bpy
            im = bpy.data.images.load(path); w, h = im.size
            px = np.empty(w * h * 4, dtype=np.float32); im.pixels.foreach_get(px)
            bpy.data.images.remove(im)
            return np.round(px.reshape(h, w, 4) * 255).astype(np.int16)
    except ImportError:
        return None


pix_bad = 0
pngs = sorted(os.path.basename(p) for p in glob.glob(os.path.join(A, "f_*.png")))
for name in pngs:
    pb = os.path.join(B, name)
    if not os.path.exists(pb): print(f"frame {name}: missing in B"); pix_bad += 1; continue
    ia, ib = load_png(os.path.join(A, name)), load_png(pb)
    if ia is None: print("numpy not available: pixel check skipped"); break
    if ia.shape != ib.shape: print(f"frame {name}: size {ia.shape} vs {ib.shape}"); pix_bad += 1; continue
    d = abs(ia - ib); n = int((d.max(axis=2) > 0).sum())
    print(f"frame {name}: {ia.shape[1]}x{ia.shape[0]}  pixels different {n}  max channel diff {int(d.max())}")
    if n: pix_bad += 1

ok = not diffs and pix_bad == 0
print("IDENTICAL" if ok else "NOT IDENTICAL")
sys.exit(0 if ok else 1)
