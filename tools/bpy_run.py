"""Run a Blender script with a Python that has the `bpy` module (pip install bpy==5.2.3), e.g. in the cloud:
    python tools/bpy_run.py tools/thumbs.py props/milk_carton --views
Equivalent to: blender -b -P tools/thumbs.py -- props/milk_carton --views"""
import sys
script, args = sys.argv[1], sys.argv[2:]
if args[:1] == ["--"]: args = args[1:]          # "bpy_run.py x.py -- a b" means the same as "bpy_run.py x.py a b"
sys.argv = ["blender", "--"] + args
import bpy  # noqa: F401  (initialises Blender)
exec(compile(open(script, encoding="utf-8").read(), script, "exec"), {"__name__": "__main__", "__file__": script})
