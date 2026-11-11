"""Safe math expressions for story.json.

A value in story.json is a number, a string expression, or a list of those.
Expressions are plain Python arithmetic restricted to a whitelist: numbers, names
from the namespace below (f, t, FPS, N, math + easing functions, story `defs`,
segment `let` names), + - * / // % **, comparisons, `a if c else b`, and/or/not,
calls of whitelisted names, tuples/lists, and `lambda` (for defs only).
No attributes, no imports, no subscripts on arbitrary objects.

    f      current frame (int)           t   f / FPS (seconds)
    sin cos tan atan2 sqrt exp log floor abs min max pi radians
    ease ease_out_back ease_out_elastic ease_out_bounce pease lerp clamp01 noise1 pop_scale walk_legs
"""
import ast
import math
from . import timing
from .chars import walk_legs

_ALLOWED = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.IfExp, ast.Call, ast.Name,
            ast.Constant, ast.Tuple, ast.List, ast.Lambda, ast.arguments, ast.arg, ast.Load, ast.Subscript,
            ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow, ast.USub, ast.UAdd, ast.Not,
            ast.And, ast.Or, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE)

BASE = dict(sin=math.sin, cos=math.cos, tan=math.tan, atan2=math.atan2, sqrt=math.sqrt, exp=math.exp, log=math.log,
            floor=math.floor, abs=abs, min=min, max=max, pi=math.pi, radians=math.radians,
            ease=timing.ease, ease_out_back=timing.ease_out_back, ease_out_elastic=timing.ease_out_elastic,
            ease_out_bounce=timing.ease_out_bounce, pease=timing.pease, lerp=timing.lerp, clamp01=timing.clamp01,
            noise1=timing.noise1, pop_scale=timing.pop_scale, walk_legs=walk_legs)


class ExprError(ValueError):
    pass


_cache = {}


def compile_expr(src, where=""):
    if src in _cache: return _cache[src]
    try:
        tree = ast.parse(src, mode="eval")
    except SyntaxError as e:
        raise ExprError(f"{where}: syntax error in expression {src!r}: {e.msg}")
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED):
            raise ExprError(f"{where}: '{type(node).__name__}' is not allowed in expression {src!r}")
        if isinstance(node, ast.Call) and not isinstance(node.func, ast.Name):
            raise ExprError(f"{where}: only plain function names can be called in {src!r}")
        if isinstance(node, ast.Subscript) and not isinstance(node.value, (ast.List, ast.Tuple, ast.Name)):
            raise ExprError(f"{where}: subscripts only on literal lists or names in {src!r}")
    code = compile(tree, "<story>", "eval")
    _cache[src] = code
    return code


def names_in(src):
    return {n.id for n in ast.walk(ast.parse(src, mode="eval")) if isinstance(n, ast.Name)}


class Env:
    """namespace for one story: base functions + FPS/N + constants + compiled defs (lambdas)"""

    def __init__(self, fps, n, defs=None, consts=None):
        self.ns = dict(BASE); self.ns.update(FPS=fps, N=n, __builtins__={})
        if consts: self.ns.update(consts)
        for name, src in (defs or {}).items():
            self.ns[name] = self.val(src, self.ns, where=f"defs.{name}")

    def frame_ns(self, f, let=None, where="", extra=None):
        """namespace for frame f (f, t) plus extra constants and `let` names evaluated in order"""
        ns = dict(self.ns)
        if extra: ns.update(extra)
        if f is not None: ns["f"] = f; ns["t"] = f / ns["FPS"]
        for k, src in (let or {}).items():
            ns[k] = self.val(src, ns, where)
        return ns

    def val(self, v, ns, where=""):
        """number -> itself, string -> expression value, list -> list of values (recursively)"""
        if isinstance(v, str):
            code = compile_expr(v, where)
            try:
                return eval(code, ns)
            except Exception as e:
                raise ExprError(f"{where}: {type(e).__name__} evaluating {v!r} (f={ns.get('f')}): {e}")
        if isinstance(v, (list, tuple)): return [self.val(x, ns, where) for x in v]
        return v

    def const(self, v, where="", extra=None):
        return self.val(v, self.frame_ns(None, extra=extra), where)
