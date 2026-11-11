"""Minimal JSON Schema (draft 2020-12 subset) validator, standard library only.

Uses the `jsonschema` package when it is installed; otherwise checks: type, enum, const,
properties, required, additionalProperties, items, prefixItems, minItems, maxItems,
minimum, maximum, minLength, maxLength, pattern, oneOf, anyOf, $ref (#/$defs/...).
validate(instance, schema) -> list of "path: message" strings (empty = valid).
"""
import re

_TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


def _is_type(v, t):
    if t == "integer": return isinstance(v, int) and not isinstance(v, bool)
    if t == "number": return isinstance(v, (int, float)) and not isinstance(v, bool)
    return isinstance(v, _TYPES[t])


def _check(v, s, root, path, errs):
    if s is True or s == {}: return
    if s is False: errs.append(f"{path}: not allowed"); return
    if "$ref" in s:
        node = root
        for part in s["$ref"].lstrip("#/").split("/"): node = node[part]
        _check(v, node, root, path, errs)
    if "type" in s:
        ts = s["type"] if isinstance(s["type"], list) else [s["type"]]
        if not any(_is_type(v, t) for t in ts):
            errs.append(f"{path}: expected {'/'.join(ts)}, got {type(v).__name__}"); return
    if "enum" in s and v not in s["enum"]: errs.append(f"{path}: {v!r} not one of {s['enum']}")
    if "const" in s and v != s["const"]: errs.append(f"{path}: must be {s['const']!r}")
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        if "minimum" in s and v < s["minimum"]: errs.append(f"{path}: {v} < minimum {s['minimum']}")
        if "maximum" in s and v > s["maximum"]: errs.append(f"{path}: {v} > maximum {s['maximum']}")
    if isinstance(v, str):
        if "minLength" in s and len(v) < s["minLength"]: errs.append(f"{path}: shorter than {s['minLength']}")
        if "maxLength" in s and len(v) > s["maxLength"]: errs.append(f"{path}: longer than {s['maxLength']}")
        if "pattern" in s and not re.search(s["pattern"], v): errs.append(f"{path}: does not match {s['pattern']}")
    if isinstance(v, dict):
        for k in s.get("required", []):
            if k not in v: errs.append(f"{path}: missing '{k}'")
        props = s.get("properties", {})
        for k, x in v.items():
            if k in props: _check(x, props[k], root, f"{path}.{k}", errs)
            elif "additionalProperties" in s:
                ap = s["additionalProperties"]
                if ap is False: errs.append(f"{path}: unexpected key '{k}'")
                elif isinstance(ap, dict): _check(x, ap, root, f"{path}.{k}", errs)
    if isinstance(v, list):
        if "minItems" in s and len(v) < s["minItems"]: errs.append(f"{path}: fewer than {s['minItems']} items")
        if "maxItems" in s and len(v) > s["maxItems"]: errs.append(f"{path}: more than {s['maxItems']} items")
        pre = s.get("prefixItems", [])
        for i, x in enumerate(v):
            if i < len(pre): _check(x, pre[i], root, f"{path}[{i}]", errs)
            elif "items" in s: _check(x, s["items"], root, f"{path}[{i}]", errs)
    for key in ("oneOf", "anyOf"):
        if key in s:
            ok = 0; sub_errs = []
            for sub in s[key]:
                e = []; _check(v, sub, root, path, e)
                if not e: ok += 1
                else: sub_errs.append(e)
            if ok == 0:
                best = min(sub_errs, key=len)
                errs.append(f"{path}: matches none of {key} (closest: {'; '.join(best[:2])})")
            elif key == "oneOf" and ok > 1:
                errs.append(f"{path}: matches more than one of oneOf")


def validate(instance, schema):
    try:
        import jsonschema
        v = jsonschema.Draft202012Validator(schema)
        return [f"{'.'.join(str(p) for p in e.absolute_path) or '$'}: {e.message}" for e in v.iter_errors(instance)]
    except ImportError:
        errs = []; _check(instance, schema, schema, "$", errs); return errs
