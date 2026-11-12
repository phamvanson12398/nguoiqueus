"""Learn from real YouTube audience-retention data.

Export from YouTube Studio: the video -> Analytics -> Engagement -> "Audience retention" -> Export (CSV). Columns differ a little
by language/version; this reader looks for a position column (percent, 0-1 or mm:ss) and a retention column (absolute retention
preferred). `drops(slug)` finds where viewers leave and what was on screen and said at that moment; claude_bridge.learn_retention
turns that into short rules kept in library/LESSONS.md, which every later content/plan prompt includes.

    python analytics.py <slug>       print the drops found in projects/<slug>/analytics/retention.csv
"""
import csv, io, json, os, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECTS = os.path.join(ROOT, "projects")
LESSONS = os.path.join(ROOT, "library", "LESSONS.md")


def _j(p, default=None):
    try: return json.load(open(p, encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError): return default


def _num(s):
    s = str(s).strip().replace(" ", "").replace(" ", "")
    if re.fullmatch(r"\d+:\d{1,2}(:\d{1,2})?", s):
        parts = [int(x) for x in s.split(":")]; t = 0
        for p in parts: t = t * 60 + p
        return ("t", float(t))
    pct = s.endswith("%"); s = s.rstrip("%").replace(",", ".")
    try: v = float(s)
    except ValueError: return None
    return ("p", v) if pct else ("n", v)


def read_csv(path, duration):
    """[(seconds, retention 0..1+)] sorted by time"""
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "utf-16", "cp1252", "latin-1"):
        try: text = raw.decode(enc); break
        except UnicodeDecodeError: continue
    rows = list(csv.reader(io.StringIO(text), delimiter=";" if text.count(";") > text.count(",") else ","))
    rows = [r for r in rows if any(c.strip() for c in r)]
    if len(rows) < 3: raise ValueError("file CSV không có dữ liệu")
    head = [h.strip().lower() for h in rows[0]]

    def col(*keys, avoid=()):
        for k in keys:
            for i, h in enumerate(head):
                if k in h and not any(a in h for a in avoid): return i
        return None
    ip = col("position", "vị trí", "time", "thời gian", "moment")
    ir = col("absolute audience retention", "absolute", "tuyệt đối", "audience retention", "retention", "giữ chân", avoid=("relative", "tương đối"))
    if ip is None: ip = 0
    if ir is None: ir = 1 if len(head) > 1 else None
    if ir is None: raise ValueError(f"không thấy cột tỉ lệ giữ chân trong {rows[0]}")
    pts = []
    for r in rows[1:]:
        if len(r) <= max(ip, ir): continue
        a, b = _num(r[ip]), _num(r[ir])
        if not a or not b: continue
        if a[0] == "t": t = a[1]
        elif a[0] == "p" or a[1] > 1.0: t = a[1] / 100 * duration
        else: t = a[1] * duration
        v = b[1] / 100 if (b[0] == "p" or b[1] > 1.5) else b[1]
        pts.append((t, v))
    pts.sort()
    if len(pts) < 5: raise ValueError("quá ít điểm dữ liệu")
    return pts


def video_duration(slug):
    W = (_j(os.path.join(PROJECTS, slug, "words.json")) or {})
    if W.get("duration"): return float(W["duration"])
    w = W.get("words") or []
    return float(w[-1][0]) + 1.0 if w else 60.0


def _said_at(slug, t, span=4.0):
    W = (_j(os.path.join(PROJECTS, slug, "words.json")) or {}).get("words") or []
    return " ".join(str(w[1]) for w in W if t - span <= float(w[0]) <= t + span)


def _shot_at(slug, t):
    """shot type/subject on screen at second t (long video: the part story; Short: the story)"""
    d = os.path.join(PROJECTS, slug)
    idx = _j(os.path.join(d, "chapters", "index.json"))
    if idx:
        for c in idx["chapters"]:
            if c["start"] <= t <= c["end"]:
                st = _j(os.path.join(d, "chapters", f"{c['n']:02d}", "story.json")) or {}
                f = int((t - c["start"]) * 30) + 1; break
        else: return None
    else:
        st = _j(os.path.join(d, "story.json")) or {}; f = int(t * 30) + 1
    cam = st.get("camera", {})
    for s in cam.get("shots") or cam.get("seqs") or []:
        if s["a"] <= f <= s["b"]:
            fr = s.get("frame") or {}
            return {"type": s.get("type"), "subject": fr.get("subject") if isinstance(fr.get("subject"), str) else None,
                    "seconds": round((s["b"] - s["a"] + 1) / 30, 1), "grade": s.get("grade"), "note": s.get("note")}
    return None


def drops(slug, path=None, top=6):
    """the intro drop and the steepest losses after it, each with what was said and shown"""
    import youtube
    path = path or os.path.join(PROJECTS, slug, "analytics", "retention.csv")
    dur = video_duration(slug); pts = read_csv(path, dur)
    def at(t):
        for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
            if t0 <= t <= t1: return v0 + (v1 - v0) * (t - t0) / max(1e-6, t1 - t0)
        return pts[-1][1] if t > pts[-1][0] else pts[0][1]
    win = max(4.0, dur / 60)
    cands = []
    t = max(30.0, win)
    while t + win <= dur - 10:
        cands.append((at(t) - at(t + win), t)); t += win / 2
    cands.sort(reverse=True)
    chosen = []
    for loss, t in cands:
        if loss <= 0.004: break
        if all(abs(t - c) > win * 2 for _l, c in chosen): chosen.append((loss, t))
        if len(chosen) >= top: break
    seqs = youtube.sequence_starts(slug)

    def seq_at(t):
        cur = None
        for s0, s in seqs:
            if s0 <= t: cur = s
        return cur
    out = {"duration": round(dur, 1), "at_30s": round(at(30), 3), "at_end": round(pts[-1][1], 3),
           "average": round(sum(v for _t, v in pts) / len(pts), 3), "intro_loss": round(at(0) - at(30), 3), "drops": []}
    for loss, t in sorted(chosen, key=lambda x: x[1]):
        s = seq_at(t + win / 2)
        out["drops"].append({"at_sec": round(t, 1), "window_sec": round(win, 1), "loss": round(loss, 3),
                             "seq_id": s.get("id") if s else None, "said": _said_at(slug, t + win / 2),
                             "shot": _shot_at(slug, t + win / 2)})
    return out


def lessons_text():
    return open(LESSONS, encoding="utf-8").read() if os.path.exists(LESSONS) else ""


def add_lessons(video_title, lessons):
    head = "# Bài học từ số liệu giữ chân người xem của kênh\nMỗi lần tải file retention lên, Claude thêm bài học ở đây; mọi lần viết content/lập cảnh sau đều đọc file này.\n"
    old = lessons_text() or head
    block = f"\n## {video_title}\n" + "\n".join(f"- {x}" for x in lessons) + "\n"
    open(LESSONS, "w", encoding="utf-8").write(old.rstrip("\n") + "\n" + block)


if __name__ == "__main__":
    print(json.dumps(drops(sys.argv[1]), ensure_ascii=False, indent=1))
