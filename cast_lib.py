"""Channel characters: the recurring cast of the dialogue videos (Jake, Emily…), saved once and reused in every video so viewers
recognise them. library/cast/<id>.json holds the look, voice and personality; a script or a Claude-written dialogue that names
one of them gets exactly that look and voice (`apply`). Plain Python (no bpy)."""
import json, os, re, unicodedata

ROOT = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(ROOT, "library", "cast")
KEEP = ("name", "role", "gender", "age", "body", "hair", "hair_color", "outfit", "colors", "head_shape", "signature", "sig_color",
        "voice_id", "voice_instruct", "personality_vi", "aliases")
LOOK = ("role", "gender", "age", "body", "hair", "hair_color", "outfit", "colors", "head_shape", "signature", "sig_color",
        "voice_id", "voice_instruct")


def slug(name):
    s = unicodedata.normalize("NFKD", (name or "").lower()).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return (s if s and s[0].isalpha() else "c_" + s)[:20] or "char"


def list_cast():
    out = []
    if os.path.isdir(DIR):
        for f in sorted(os.listdir(DIR)):
            if f.endswith(".json"):
                try: out.append(dict(json.load(open(os.path.join(DIR, f), encoding="utf-8")), id=f[:-5]))
                except Exception: pass
    return out


def get(name):
    """a channel character by name, alias or id (case-insensitive), else None"""
    key = (name or "").strip().lower()
    if not key: return None
    for m in list_cast():
        names = {m["id"], (m.get("name") or "").lower()} | {a.lower() for a in m.get("aliases", [])}
        if key in names or slug(key) == m["id"]: return m
    return None


def save(member):
    os.makedirs(DIR, exist_ok=True)
    m = {k: member[k] for k in KEEP if k in member}
    if not m.get("name"): raise ValueError("nhân vật cần tên")
    cid = slug(m["name"])
    json.dump(m, open(os.path.join(DIR, cid + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return dict(m, id=cid)


def delete(cid):
    p = os.path.join(DIR, slug(cid) + ".json")
    if os.path.exists(p): os.remove(p); return True
    return False


def apply(content):
    """cast members named like a channel character take its look, voice and personality (the id stays the video's).
    Returns the names that were matched."""
    hit = []
    for m in content.get("cast", []):
        s = get(m.get("name")) or get(m.get("id"))
        if not s: continue
        for k in LOOK:
            if k in s: m[k] = json.loads(json.dumps(s[k]))
        if s.get("personality_vi") and not m.get("personality_vi"): m["personality_vi"] = s["personality_vi"]
        hit.append(m.get("name"))
    return hit


def prompt_text():
    cs = list_cast()
    if not cs: return ""
    rows = [{k: m.get(k) for k in ("name", "role", "gender", "age", "body", "personality_vi") if m.get(k)} for m in cs]
    return ("Nhân vật quen của kênh (người xem đã biết họ; ưu tiên dùng lại đúng tên, vai và tính cách khi hợp ý tưởng; "
            "tool tự lấy ngoại hình và giọng đã lưu): " + json.dumps(rows, ensure_ascii=False) + "\n")
