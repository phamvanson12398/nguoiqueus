"""WhyShorts Studio — local web server + control page.

    python server.py                 then open http://127.0.0.1:1111
    options: --port 1111  --host 127.0.0.1  --no-browser

Standard library only (runs with Blender's bundled python.exe).  Long tasks (Claude calls,
Blender builds/renders) run as background jobs; the page polls /api/jobs/<id>.
Environment: see claude_bridge.py (WHYSHORTS_BLENDER, WHYSHORTS_CLAUDE, WHYSHORTS_MODEL).
"""
import json, os, re, shutil, subprocess, sys, threading, time, traceback, uuid, mimetypes, datetime, webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, unquote, parse_qs

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path: sys.path.insert(0, ROOT)
import claude_bridge as bridge
import storycheck
import longform

PROJECTS = os.path.join(ROOT, "projects")
UI = os.path.join(ROOT, "ui")
WPM = 190                       # AI voice words/minute: measured 198 (reference channel) and 201 (user's OmniVoice); 150 was too slow
SEC_PER_FRAME = 1.4             # measured render speed on the user's GPU (toolkit v2); replaced by "Đo tốc độ máy"
LOCAL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "local_settings.json")   # this machine only (not in git)
QUALITY_FACTOR = {"fast": 0.3, "normal": 1.0, "high": 1.45}   # fast = on twos + 12 samples (vs 32)


def local_settings():
    try: return json.load(open(LOCAL, encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError): return {}


def spf_for(fmt="short"):
    """seconds per frame at 100 %, quality normal: measured on this machine if available"""
    m = local_settings().get("spf", {})
    return m.get("long" if fmt == "long" else "short") or (SEC_PER_FRAME * 1.15 if fmt == "long" else SEC_PER_FRAME)
FPS = 30


# =====================================================================
#  jobs
# =====================================================================
class Job:
    def __init__(self, kind, project, fn, *args, **kw):
        self.id = uuid.uuid4().hex[:10]; self.kind = kind; self.project = project
        self.status = "running"; self.log = []; self.result = None; self.error = None
        self.progress = None; self.started = time.time(); self.ended = None
        self.procs = []; self.cancelled = False
        self.thread = threading.Thread(target=self._run, args=(fn, args, kw), daemon=True)

    def say(self, msg):
        for line in str(msg).splitlines():
            self.log.append(line)
        if len(self.log) > 4000: del self.log[:1000]

    def _run(self, fn, args, kw):
        bridge._tls.hook = self.say; bridge._tls.procs = self.procs; bridge._tls.cancelled = False
        self._tls_ref = bridge._tls
        try:
            self.result = fn(self, *args, **kw)
            self.status = "cancelled" if self.cancelled else "done"
        except Exception as e:
            self.status = "cancelled" if self.cancelled else "error"
            self.error = str(e)
            self.say("LỖI: " + str(e))
            if not isinstance(e, (bridge.BridgeError, ValueError)): self.say(traceback.format_exc())
        finally:
            self.ended = time.time()

    def cancel(self):
        self.cancelled = True
        try: self._tls_ref.cancelled = True
        except AttributeError: pass
        for p in list(self.procs):
            bridge._kill_tree(p)

    def to_json(self, since=0):
        return {"id": self.id, "kind": self.kind, "project": self.project, "status": self.status,
                "log": self.log[since:], "log_len": len(self.log), "result": self.result, "error": self.error,
                "progress": self.progress, "elapsed": round((self.ended or time.time()) - self.started, 1)}


JOBS = {}
BUSY = {}                         # project -> job id (one heavy job per project)
LOCK = threading.Lock()


def start_job(kind, project, fn, *args, **kw):
    with LOCK:
        cur = BUSY.get(project)
        if cur and JOBS[cur].status == "running":
            raise ValueError(f"Dự án đang chạy việc '{JOBS[cur].kind}', đợi xong hoặc bấm Hủy")
        j = Job(kind, project, fn, *args, **kw); JOBS[j.id] = j; BUSY[project] = j.id
    j.thread.start()
    return j


# =====================================================================
#  project files
# =====================================================================
def slugify(s):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:40] or "video"


def pdir(slug):
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,60}(/chapters/\d{2}|/clips/\d{2})?", slug or ""): raise ValueError("tên dự án không hợp lệ")
    return os.path.join(PROJECTS, slug)


TEMP_DIRS = ("frames", "parts", "_bench")          # render scratch inside a project or one of its parts


def _dir_size(p):
    n = 0
    for root, _dirs, files in os.walk(p):
        for f in files:
            try: n += os.path.getsize(os.path.join(root, f))
            except OSError: pass
    return n


def _inside_projects(p):
    p = os.path.realpath(p); base = os.path.realpath(PROJECTS)
    return p != base and os.path.commonpath([p, base]) == base


def temp_dirs(slug):
    """render scratch of a project: frames/, parts/, _bench/ (also in every part), thumbnail/reference build folders"""
    d = pdir(slug); out = []
    roots = [d]
    for sub in ("chapters", "clips"):                      # parts of a long video and Shorts cut from it
        sd = os.path.join(d, sub)
        if os.path.isdir(sd): roots += [os.path.join(sd, c) for c in sorted(os.listdir(sd)) if os.path.isdir(os.path.join(sd, c))]
    for r in roots:
        out += [os.path.join(r, t) for t in TEMP_DIRS if os.path.isdir(os.path.join(r, t))]
    yd = os.path.join(d, "youtube")
    if os.path.isdir(yd):
        out += [os.path.join(yd, f) for f in os.listdir(yd) if re.fullmatch(r"thumb_\d+", f) and os.path.isdir(os.path.join(yd, f))]
        rd = os.path.join(yd, "refs")
        if os.path.isdir(rd): out += [os.path.join(rd, f) for f in os.listdir(rd) if f.startswith("_") and os.path.isdir(os.path.join(rd, f))]
    return [p for p in out if _inside_projects(p)]


def clean_project(slug):
    """delete render scratch (frames, parts, bench, thumbnail builds); keep story, voice, content, previews, mp4, YouTube package"""
    if "/chapters/" in slug: raise ValueError("chọn dự án chính, không chọn một phần")
    cur = BUSY.get(slug)
    if cur and JOBS[cur].status == "running": raise ValueError("dự án đang chạy một việc: đợi xong hoặc bấm Hủy")
    freed = 0; removed = []
    for p in temp_dirs(slug):
        freed += _dir_size(p); shutil.rmtree(p, ignore_errors=True); removed.append(os.path.relpath(p, pdir(slug)).replace("\\", "/"))
    return {"freed_mb": round(freed / 1e6, 1), "removed": removed}


def export_dir():
    return os.environ.get("WHYSHORTS_EXPORT") or os.path.join(os.path.expanduser("~"), "Videos", "WhyShorts")


def delete_project(slug, confirm):
    """copy the finished video(s) and the YouTube package out of the project, then delete the project folder"""
    if "/chapters/" in slug: raise ValueError("chọn dự án chính, không chọn một phần")
    if confirm != slug: raise ValueError("gõ đúng tên dự án để xác nhận xóa")
    cur = BUSY.get(slug)
    if cur and JOBS[cur].status == "running": raise ValueError("dự án đang chạy một việc: đợi xong hoặc bấm Hủy")
    d = pdir(slug)
    if not os.path.isdir(d) or not _inside_projects(d): raise ValueError(f"không có dự án {slug}")
    dst = os.path.join(export_dir(), slug.replace("/", "_")); kept = []
    for f in os.listdir(d):                                   # finished videos at the project root
        if f.endswith(".mp4") and not f.endswith("_before.mp4"):
            os.makedirs(dst, exist_ok=True); shutil.copy2(os.path.join(d, f), os.path.join(dst, f)); kept.append(f)
    yd = os.path.join(d, "youtube")
    if os.path.isdir(yd):
        def skip(_dir, names): return [n for n in names if re.fullmatch(r"thumb_\d+", n) or n.startswith("_") or n.endswith(".wav")]
        shutil.copytree(yd, os.path.join(dst, "youtube"), ignore=skip, dirs_exist_ok=True); kept.append("youtube/")
    for f in ("content.json", "voice.wav"):
        if os.path.exists(os.path.join(d, f)):
            os.makedirs(dst, exist_ok=True); shutil.copy2(os.path.join(d, f), os.path.join(dst, f)); kept.append(f)
    shutil.rmtree(d)
    BUSY.pop(slug, None)
    return {"deleted": slug, "kept": kept, "kept_in": dst if kept else None}


def jload(path, default=None):
    try: return json.load(open(path, encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError): return default


def is_long(slug):
    return (jload(os.path.join(pdir(slug), "settings.json")) or {}).get("format") == "long"


def sub_target(slug, chapter):
    """a long project's chapter is planned/built/rendered as the sub-project <slug>/chapters/NN"""
    return longform.chapter_slug(slug, int(chapter)) if chapter else slug


def estimate(minutes, wpm=None, fmt="short"):
    """numbers shown next to the minutes box (wpm: measured from the project's voice when known)"""
    wpm = wpm or WPM
    words = int(round(minutes * wpm))
    if fmt == "long":
        frames = int(round(minutes * 60 * FPS)); n_ch = max(2, round(minutes / 3))
        return {"minutes": minutes, "words": words, "sequences": max(n_ch * 3, round(minutes * 60 / 35)), "chapters": n_ch,
                "shots": round(minutes * 14), "frames": frames, "render_seconds": round(frames * spf_for("long")), "wpm": wpm, "format": "long",
                "render_by_quality": {q: round(frames * spf_for("long") * k) for q, k in QUALITY_FACTOR.items()}}
    seqs = max(4, min(7, int(round(minutes * 6)))) if minutes <= 1.25 else int(round(minutes * 5.5))
    frames = int(round(minutes * 60 * FPS))
    return {"minutes": minutes, "words": words, "sequences": seqs, "chapters": 0 if minutes <= 1.25 else max(2, round(seqs / 5.5)),
            "frames": frames, "render_seconds": round(frames * spf_for("short")), "wpm": wpm,
            "render_by_quality": {q: round(frames * spf_for("short") * k) for q, k in QUALITY_FACTOR.items()}}


def project_state(slug):
    d = pdir(slug)
    if not os.path.isdir(d): raise ValueError(f"không có dự án {slug}")
    st = {"slug": slug}
    for k in ("ideas", "idea", "content", "words", "settings"):
        st[k] = jload(os.path.join(d, k + ".json"))
    story = jload(os.path.join(d, "story.json"))
    st["story"] = {"frames": story["meta"]["frames"], "title": story["meta"].get("title"), "output": story["meta"].get("output"),
                   "camera": story["camera"].get("rig"), "sequences": len(story["camera"].get("seqs") or story["camera"].get("shots") or []),
                   "chars": [c["id"] for c in story.get("chars", [])]} if story else None
    st["has_voice"] = os.path.exists(os.path.join(d, "voice.wav"))
    prev = os.path.join(d, "preview")
    st["previews"] = sorted(f for f in os.listdir(prev) if f.endswith(".png")) if os.path.isdir(prev) else []
    outs = [f for f in os.listdir(d) if f.endswith(".mp4")]
    parts = os.path.join(d, "parts")
    outs += ["parts/" + f for f in sorted(os.listdir(parts)) if f.endswith(".mp4")] if os.path.isdir(parts) else []
    st["outputs"] = [{"file": f, "size": os.path.getsize(os.path.join(d, f)),
                      "time": datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(d, f))).isoformat(timespec="seconds")} for f in outs]
    hist = os.path.join(d, "history")
    st["history"] = sorted((f for f in os.listdir(hist) if f.endswith(".json")), reverse=True) if os.path.isdir(hist) else []
    st["estimate"] = estimate((st["settings"] or {}).get("minutes", 1.0), (st["settings"] or {}).get("wpm_measured"),
                              (st["settings"] or {}).get("format", "short"))
    st["format"] = (st["settings"] or {}).get("format", "short")
    yd = os.path.join(d, "youtube")
    st["youtube"] = dict(jload(os.path.join(yd, "package.json")) or {}, description=open(os.path.join(yd, "description.txt"), encoding="utf-8").read()
                         if os.path.exists(os.path.join(yd, "description.txt")) else None,
                         thumbs=sorted(f for f in os.listdir(yd) if re.fullmatch(r"thumb_\d(_v1)?\.png", f)),
                         ai_prompts=jload(os.path.join(yd, "ai_prompts.json")),
                         subs=sorted(os.listdir(os.path.join(yd, "subs"))) if os.path.isdir(os.path.join(yd, "subs")) else [],
                         refs=sorted(f for f in os.listdir(os.path.join(yd, "refs")) if f.endswith(".png")) if os.path.isdir(os.path.join(yd, "refs")) else []) if os.path.isdir(yd) else None
    st["chapters"] = longform.status(slug) if st["format"] == "long" else None
    st["retention"] = jload(os.path.join(d, "retention_review.json"))
    st["analytics"] = jload(os.path.join(d, "analytics", "report.json"))
    st["lessons"] = open(os.path.join(bridge.LIB, "LESSONS.md"), encoding="utf-8").read() if os.path.exists(os.path.join(bridge.LIB, "LESSONS.md")) else ""
    try:
        import clips as _clips
        st["clips"] = _clips.status(slug) if "/" not in slug else []
    except Exception:
        st["clips"] = []
    cur = BUSY.get(slug); st["job"] = JOBS[cur].to_json(10 ** 9) if cur and cur in JOBS else None
    return st


def save_settings(slug, **kw):
    p = os.path.join(pdir(slug), "settings.json"); s = jload(p, {}); s.update(kw)
    json.dump(s, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2); return s


# =====================================================================
#  job bodies
# =====================================================================
def job_ideas(job, slug, topic):
    job.say("Claude đang đào ý tưởng" + (f" về: {topic}" if topic else "") + " (có tra web, thường 1-4 phút)…")
    data = bridge.ideas(slug, topic or None)
    job.say(f"Xong: {len(data['ideas'])} ý tưởng.")
    return {"count": len(data["ideas"])}


def job_write(job, slug, minutes):
    idea = jload(os.path.join(pdir(slug), "idea.json"))
    if not idea: raise ValueError("chưa chọn ý tưởng (hoặc nhập chủ đề tự do)")
    e = estimate(minutes)
    wpm = (jload(os.path.join(pdir(slug), "settings.json")) or {}).get("wpm_measured") or WPM
    e = estimate(minutes, wpm)
    fmt = "long" if is_long(slug) else "short"
    e = estimate(minutes, wpm, fmt)
    job.say(f"Claude đang viết content {minutes} phút " + ("(video dài 16:9, " + f"{e['chapters']} phần, " if fmt == "long" else "(")
            + f"~{e['words']} từ ở {wpm} từ/phút, ~{e['sequences']} chuỗi)…")
    data = bridge.write_content(slug, idea, minutes, wpm=wpm, fmt=fmt)
    job.say(f"Xong: {data['word_count']} từ, {len(data['sequences'])} chuỗi.")
    return {"words": data["word_count"]}


def job_rewrite(job, slug, sid, request):
    job.say(f"Claude đang viết lại chuỗi {sid}: {request}")
    data = bridge.rewrite_seq(slug, sid, request)
    job.say("Xong. " + data.get("note_vi", ""))
    return {"id": sid}


def job_align(job, slug):
    import align
    d = pdir(slug); content = jload(os.path.join(d, "content.json"))
    if not content: raise ValueError("chưa có content (cần lời đọc tiếng Anh để canh chữ)")
    job.say("Đang canh từng chữ theo voice.wav…")
    r = align.align(os.path.join(d, "voice.wav"), content["vo_en"])
    json.dump(r, open(os.path.join(d, "words.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    wpm = round(r["word_count"] / max(1.0, r["duration"] - 0.5) * 60)
    save_settings(slug, wpm_measured=wpm)             # later estimates for this project use the real voice speed
    est = len(content["vo_en"].split()) / WPM * 60
    job.say(f"Giọng đọc {r['duration']} s ({r['frames']} khung), {r['word_count']} chữ, {len(r['segments'])} cụm. "
            f"Ước tính từ content: {est:.0f} s. Tốc độ giọng đo được: {wpm} từ/phút.")
    if longform.is_long(content):
        job.say("Chia giọng đọc theo phần…")
        longform.split(slug, log=job.say)
    return {"duration": r["duration"], "frames": r["frames"]}


def run_builder(job, slug, args, progress_total=None, story=None):
    """run builder.py in Blender, stream its output into the job log, parse RENDER FRAME lines"""
    story = story or os.path.join(pdir(slug), "story.json")
    b = bridge.blender_cmd()
    if os.path.basename(b).lower().startswith("python"):
        cmd = [b, os.path.join(ROOT, "tools", "bpy_run.py"), os.path.join(ROOT, "builder.py"), story] + args
    else:
        cmd = [b, "-b", "--factory-startup", "-P", os.path.join(ROOT, "builder.py"), "--", story] + args
    job.say("$ " + " ".join(os.path.basename(c) if i < 2 else c for i, c in enumerate(cmd)))
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", cwd=ROOT)
    job.procs.append(p)
    a0 = None; t0 = time.time(); last = []; n_img = 0; step = 1
    for line in p.stdout:
        line = line.rstrip()
        if line.startswith("Fra:") or "EGL Error" in line or line.startswith("DeprecationWarning") or "Video append frame" in line: continue
        if line.startswith("RENDER START"):
            w = line.split(); a0, b1 = int(w[2]), int(w[3]); step = int(w[5]) if len(w) > 5 and w[4] == "step" else 1
            n_img = 0; job.progress = {"done": 0, "total": b1 - a0 + 1, "eta": None}
        if line.startswith("RENDER FRAME"):
            f, a, b_, el = line.split()[2:6]; f, a, b_, el = int(f), int(a), int(b_), float(el)
            n_img += 1
            done = f - a + 1; total = b_ - a + 1; rate = el / n_img          # seconds per rendered image (resume-safe)
            job.progress = {"done": done, "total": total, "eta": round(rate * max(0, total - done) / step), "sec_per_frame": round(rate / step, 2),
                            "frame": f}
            if n_img % 10 and done < total - step: continue
        job.say(line); last.append(line)
    p.wait(); job.procs.remove(p)
    if job.cancelled: raise ValueError("đã hủy")
    out = "\n".join(last[-60:])
    if p.returncode != 0 or "BUILD FAILED" in out or "Traceback" in out:
        tail = [l for l in last[-30:] if l.strip()]
        key = next((l for l in reversed(tail) if "BUILD FAILED" in l or "Error" in l), tail[-1] if tail else "")
        raise ValueError("Blender báo lỗi: " + key + "\n" + "\n".join(tail[-12:]))
    return "\n".join(last)


def job_preview(job, slug, frames, pct=35):
    d = pdir(slug); prev = os.path.join(d, "preview")
    if os.path.isdir(prev):
        for f in os.listdir(prev):
            if f.endswith(".png"): os.remove(os.path.join(prev, f))
    out = run_builder(job, slug, ["--preview", ",".join(str(f) for f in frames), "--pct", str(pct)])
    return {"previews": sorted(f for f in os.listdir(prev) if f.endswith(".png")), "log": out}


def default_preview_frames(slug):
    story = jload(os.path.join(pdir(slug), "story.json"))
    cam = story["camera"]; spans = [(s["a"], s["b"]) for s in (cam.get("seqs") or cam.get("shots") or [])]
    if len(spans) > 10:                                           # long-form shot list: 8 shots spread over the chapter
        pick = [spans[round(i * (len(spans) - 1) / 7)] for i in range(8)]
        return sorted({(a + b) // 2 for a, b in pick})
    fr = []
    for a, b in spans[:8]: fr.append((a + b) // 2)
    for a, b in spans[1:4]: fr.append(a + 2)                      # just after a transition
    return sorted(set(fr))[:10] or [1]


def job_build_long(job, slug, design=True, preview=True, chapters=None, replan=False):
    """long video: split (if needed), then plan/design/check/preview chapter by chapter (skips chapters that have a story)"""
    if not os.path.exists(os.path.join(pdir(slug), "chapters", "index.json")): longform.split(slug, log=job.say)
    st = longform.status(slug); out = {}
    todo = [c for c in st if (int(c["n"]) in chapters if chapters else not c["story"] or pending_designs(longform.chapter_slug(slug, c["n"])) or not c["previews"])]
    if not todo: job.say("Mọi phần đã có story.json (chọn phần để dựng lại)."); return {"chapters": []}
    for c in todo:
        job.say(f"===== Phần {c['n']:02d}/{len(st)} «{c['title']}» ({c['frames']} khung) =====")
        out[c["n"]] = job_build(job, longform.chapter_slug(slug, c["n"]), design, preview, replan=replan)
    job.say(f"Xong {len(todo)} phần. Xem ảnh từng phần rồi bấm Render (render lần lượt từng phần rồi ghép).")
    return {"chapters": list(out)}


def _story_people(d):
    st = jload(os.path.join(d, "story.json")) or {}
    facs = {f["id"]: f for f in st.get("factions", [])}
    for x in st.get("chars", []) + st.get("crowds", []):
        cul = (facs.get(x.get("faction")) or {}).get("culture")
        role = x.get("role") if x.get("type", "person") == "person" else None      # library characters wear their own clothes
        refs = [x.get("outfit") or role] + [c[1] for c in x.get("outfit_changes", [])]
        for ref in refs:
            if ref: yield ref, cul


def _resolve_outfit(ref, cul):
    lib = storycheck.LibIndex()
    if lib.exists("outfits", ref): return ref, None
    if cul and lib.exists("cultures", cul):
        c = lib.json("cultures", cul); oid = c.get("roles", {}).get(ref)
        if oid: return oid, c.get("role_briefs_vi", {}).get(oid) or f"vai {ref} của {cul}"
    return None, None


def needed_outfits(d):
    """[(outfit id, culture, brief)] the story needs and the library does not have yet"""
    out, seen = [], set()
    lib = storycheck.LibIndex()
    for ref, cul in _story_people(d):
        oid, brief = _resolve_outfit(ref, cul)
        if oid and oid not in seen and not lib.exists("outfits", oid):
            seen.add(oid); out.append((oid, cul, brief))
    return out


def story_outfits(d, exclude=None):
    """outfits of the story (with faction colours) the new one must be told apart from, at most 3"""
    st = jload(os.path.join(d, "story.json")) or {}
    facs = {f["id"]: f for f in st.get("factions", [])}
    lib = storycheck.LibIndex(); out = []
    for x in st.get("chars", []) + st.get("crowds", []):
        cul = (facs.get(x.get("faction")) or {}).get("culture")
        ref = x.get("outfit") or (x.get("role") if x.get("type", "person") == "person" else None)
        if not ref: continue
        oid, _ = _resolve_outfit(ref, cul)
        col = (facs.get(x.get("faction")) or {}).get("color")
        if oid and oid != exclude and lib.exists("outfits", oid):
            tag = oid + (":" + ",".join(f"{c:.3f}" for c in col) if col else "")
            if tag not in out: out.append(tag)
    return out[:3]


def saved_plan(slug):
    """missing list of a story.json planned from the current content + words (None = plan again)"""
    d = pdir(slug); sp, mp = os.path.join(d, "story.json"), os.path.join(d, "missing.json")
    if not (os.path.exists(sp) and os.path.exists(mp)): return None
    if any(os.path.exists(os.path.join(d, f)) and os.path.getmtime(os.path.join(d, f)) > os.path.getmtime(sp) for f in ("content.json", "words.json")):
        return None
    return jload(mp)


def pending_designs(slug):
    lib = storycheck.LibIndex(); miss = saved_plan(slug) or []
    return [m for m in miss if not lib.exists(m["kind"], m["name"])] + [o for o in needed_outfits(pdir(slug))]


def job_build(job, slug, design=True, preview=True, chapters=None, replan=False):
    """'Duyệt & dựng': plan shots -> design missing library items -> check -> build + preview, with automatic fix rounds"""
    if "/chapters/" not in slug and is_long(slug): return job_build_long(job, slug, design, preview, chapters, replan)
    d = pdir(slug); lib = storycheck.LibIndex()
    if not os.path.exists(os.path.join(d, "words.json")): raise ValueError("chưa có giọng đọc đã canh chữ (tải voice.wav lên trước)")
    job.say("1/4 Claude chuyển content thành story.json (bảng khung hình, " + ("16:9, shot list" if "/chapters/" in slug else "camera v3") + ")…")
    missing = None if replan else saved_plan(slug)
    if missing is not None: job.say("   story.json đã có (lập từ content + giọng hiện tại): dùng lại, không lập lại.")
    else: missing = bridge.plan_shots(slug).get("missing", [])
    job.say(f"   story.json xong. Đồ mới cần thiết kế: {', '.join(m['kind'] + '/' + m['name'] for m in missing) or 'không'}")
    failed = []
    order = {"cultures": 0, "outfits": 1}
    missing = sorted(missing, key=lambda m: order.get(m["kind"], 2))
    if missing and design:
        job.say("2/4 Thiết kế đồ còn thiếu (mỗi món vài phút)…")
        for k, m in enumerate(missing, 1):
            if lib.exists(m["kind"], m["name"]) or m["name"] in failed:
                job.say(f" - [{k}/{len(missing)}] {m['kind']}/{m['name']}: đã có trong thư viện, bỏ qua"); continue
            job.say(f" - [{k}/{len(missing)}] {m['kind']}/{m['name']}: {m['brief']}")
            try:
                if m["kind"] == "cultures":
                    r = bridge.design_culture(m["name"], m["brief"])
                    job.say(f"   -> văn hóa xong ({r['seconds']} s), vai: {r['roles']}")
                    continue
                if m["kind"] == "outfits":
                    r = bridge.design_outfit(m["name"], m["brief"], culture=m.get("culture"), compare=story_outfits(d, m["name"]))
                elif m["kind"] == "chars": r = bridge.design_char(m["name"], m["brief"])
                else: r = bridge.design_item(m["kind"], m["name"], m["brief"])
                last = ([x for x in r.get("rounds", []) if "score" in x] or [{}])[-1]
                job.say(f"   -> {last.get('score', '?')}/10 {last.get('summary_vi', '')}")
                if not r.get("ok", True): failed.append(m["name"])
            except Exception as e:
                if job.cancelled or bridge.is_usage_limit(e): raise ValueError(f"Hết lượt Claude của gói: {e}. Khi lượt mở lại, bấm 'Duyệt & dựng' lần nữa: tool làm tiếp từ đồ còn thiếu, không lập lại story.")
                failed.append(m["name"]); job.say(f"   -> LỖI: {e}")
        # outfits of the roles the story uses (known only once the cultures exist)
        for oid, cul, brief in needed_outfits(d):
            if oid in failed: continue
            job.say(f" - trang phục {oid} (văn hóa {cul}): {brief[:160]}")
            try:
                r = bridge.design_outfit(oid, brief, culture=cul, compare=story_outfits(d, oid))
                last = (r.get("rounds") or [{}])[-1]
                job.say(f"   -> {last.get('score', '?')}/10 {last.get('summary_vi', '')} | sử liệu: {last.get('accuracy_vi', '')}")
                if not r.get("ok", True): failed.append(oid)
            except Exception as e:
                if job.cancelled or bridge.is_usage_limit(e): raise ValueError(f"Hết lượt Claude của gói: {e}. Khi lượt mở lại, bấm 'Duyệt & dựng' lần nữa.")
                failed.append(oid); job.say(f"   -> LỖI: {e}")
    if failed: raise ValueError("thiết kế chưa xong: " + ", ".join(failed) + " (xem log; có thể thiết kế lại ở tab Thư viện rồi bấm 'Chỉ render lại xem trước')")
    if "/chapters/" in slug: longform.stitch(slug.split("/chapters/")[0], log=job.say)   # parts of one seamless video
    errs = storycheck.check_story(jload(os.path.join(d, "story.json")))
    if errs: raise ValueError("story.json còn lỗi: " + "; ".join(errs[:5]))
    if not preview: return {"missing": missing}
    for attempt in range(bridge.MAX_FIX + 1):
        frames = default_preview_frames(slug)
        job.say(f"{3 if attempt == 0 else '3b'}/4 Dựng cảnh trong Blender và xem trước khung {frames} (35 %)…")
        problem = None; only_warns = False
        try:
            out = job_preview(job, slug, frames)["log"]
            warns = [l for l in out.splitlines() if l.startswith("WARN") or "CAMERA NEEDS FIX" in l]
            if warns: problem = "Camera chưa đạt cam_report:\n" + "\n".join(warns); only_warns = True
        except ValueError as e:
            if job.cancelled: raise
            problem = f"Dựng trong Blender bị lỗi:\n{e}"
        if not problem:
            job.say("4/4 Xong: CAMERA OK, đã có ảnh xem trước. Xem ảnh rồi bấm Render, hoặc mô tả lỗi để Claude sửa.")
            return {"missing": missing, "fix_rounds": attempt}
        if attempt == bridge.MAX_FIX:
            if only_warns:          # the scene builds and has previews: hand it over with the remaining warnings
                job.say("4/4 Xong, còn cảnh báo (xem ảnh các cú này, sửa tay hoặc bấm 'Nhờ Claude sửa'):")
                for l in warns[:12]: job.say("   " + l)
                return {"missing": missing, "fix_rounds": attempt, "warnings": warns}
            raise ValueError(problem)
        job.say(f"   {problem.splitlines()[0]} -> nhờ Claude sửa story.json ({attempt + 1}/{bridge.MAX_FIX})")
        data = bridge.fix_from_preview(slug, problem + "\n(Chưa có ảnh: sửa theo thông báo lỗi.)", [])
        job.say("   Đã sửa: " + data["explain_vi"])


def job_fix(job, slug, problem, frames):
    d = pdir(slug); imgs = [os.path.join(d, "preview", f"p_{f:04d}.png") for f in frames]
    imgs = [i for i in imgs if os.path.exists(i)] or [os.path.join(d, "preview", f) for f in project_state(slug)["previews"]]
    job.say(f"Claude xem {len(imgs)} ảnh và sửa story.json: {problem}")
    data = bridge.fix_from_preview(slug, problem, imgs)
    job.say("Đã sửa: " + data["explain_vi"])
    job_preview(job, slug, frames or default_preview_frames(slug))
    return {"changes": len(data["changes"])}


def job_render_long(job, slug, pct=100, samples=None, quality="normal"):
    """render every chapter whose mp4 is missing or older than its story.json, then join them"""
    st = longform.status(slug)
    if not st or not all(c["story"] for c in st): raise ValueError("chưa dựng đủ các phần (bấm Duyệt & dựng)")
    longform.stitch(slug, log=job.say)
    st = longform.status(slug)
    todo = [c for c in st if not c["rendered"]]
    job.say(f"Render {len(todo)}/{len(st)} phần" + (f" (đã có: {[c['n'] for c in st if c['rendered']]})" if len(todo) < len(st) else "") + "…")
    for c in todo:
        job.say(f"===== Render phần {c['n']:02d}/{len(st)} ({c['frames']} khung) =====")
        job_render(job, longform.chapter_slug(slug, c["n"]), pct, None, samples, quality)
    if int(pct or 100) != 100: job.say("(render thử dưới 100 %: vẫn ghép để xem)")
    out = longform.concat(slug, log=job.say)
    return {"file": os.path.basename(out)}


def job_youtube(job, slug, thumbs=True):
    """YouTube package: Claude writes titles/description/tags/thumbnail ideas; the tool adds real chapter timestamps,
    renders 3 thumbnails (1280x720) from the video's own characters and sets, and lets Claude pick/fix the best one"""
    import youtube
    yd = os.path.join(pdir(slug), "youtube"); os.makedirs(yd, exist_ok=True)
    job.say("Claude viết gói YouTube (tiêu đề, mô tả, tag, 3 ý tưởng thumbnail)…")
    pkg = bridge.youtube_package(slug)
    stamps = youtube.timestamps(slug, pkg.get("beat_titles"))
    desc = youtube.description(pkg, stamps)
    open(os.path.join(yd, "description.txt"), "w", encoding="utf-8").write(desc)
    open(os.path.join(yd, "titles.txt"), "w", encoding="utf-8").write("\n".join(t["title"] for t in pkg["titles"]) + "\n")
    pkg["timestamps"] = [[round(t, 2), title] for t, title in stamps]
    job.say(f"   {len(pkg['titles'])} tiêu đề, {len(stamps)} mốc thời gian, {len(pkg['tags'])} tag.")
    st0, _ = youtube.source_story(slug)
    if thumbs and st0 and st0["meta"].get("aspect") == "16:9":
        imgs = []
        for k, concept in enumerate(pkg["thumbnails"], 1):
            job.say(f"Render thumbnail {k}/3: {concept.get('idea_vi', '')}")
            try: imgs.append(render_thumb(job, slug, yd, k, concept))
            except ValueError as e:
                if job.cancelled: raise
                job.say(f"   thumbnail {k} lỗi: {str(e)[:200]}"); imgs.append(None)
        try:
            if not any(imgs): raise ValueError("không render được thumbnail nào")
            rv = bridge.review_thumbnails(slug, [i or "(lỗi, không có ảnh)" for i in imgs], pkg["thumbnails"])
            pkg["thumb_review"] = rv
            job.say(f"   Claude chấm: {rv['scores']}, chọn số {rv['best']}. {rv['summary_vi']}")
            if rv.get("revised"):
                b = rv["best"]; job.say(f"   Sửa thumbnail {b}: {'; '.join(rv['problems_vi'])[:300]}")
                old = os.path.join(yd, f"thumb_{b}.png")
                if os.path.exists(old): shutil.copy(old, os.path.join(yd, f"thumb_{b}_v1.png"))
                render_thumb(job, slug, yd, b, dict(rv["revised"], id=b)); pkg["thumbnails"][b - 1] = dict(rv["revised"], id=b)
        except Exception as e:
            if job.cancelled: raise
            job.say(f"   (không chấm được thumbnail: {e})")
    json.dump(pkg, open(os.path.join(yd, "package.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    try: job_thumb_prompts(job, slug)
    except Exception as e:
        if job.cancelled: raise
        job.say(f"   (chưa viết được prompt AI cho thumbnail: {e})")
    return {"titles": len(pkg["titles"]), "timestamps": len(stamps)}


def job_subs(job, slug, langs):
    """English SRT from the real word timing; translated SRT + dubbing script for each language (youtube/subs/)"""
    import youtube
    sd = os.path.join(pdir(slug), "youtube", "subs"); os.makedirs(sd, exist_ok=True)
    lines = youtube.sub_lines(slug)
    if not lines: raise ValueError("chưa có giọng đọc đã canh chữ (words.json)")
    youtube.write_srt(os.path.join(sd, "en.srt"), lines)
    job.say(f"Phụ đề tiếng Anh: {len(lines)} dòng -> youtube/subs/en.srt")
    for lang in langs:
        job.say(f"Claude dịch sang {bridge.LANG_NAMES.get(lang, lang)}…")
        try:
            r = bridge.translate_subs(slug, lang, lines)
        except Exception as e:
            if job.cancelled or bridge.is_usage_limit(e): raise
            job.say(f"   -> lỗi: {e}"); continue
        youtube.write_srt(os.path.join(sd, f"{lang}.srt"), [(a, b, t) for (a, b, _x), t in zip(lines, r["lines"])])
        with open(os.path.join(sd, f"dub_{lang}.txt"), "w", encoding="utf-8") as f:
            f.write(r["title"] + "\n\n" + "\n\n".join(x["text"] for x in sorted(r["dub"], key=lambda x: x["id"])) + "\n")
        job.say(f"   -> {lang}.srt + dub_{lang}.txt ({r['title']})")
    return {"files": sorted(os.listdir(sd))}


def job_clips(job, slug):
    """Claude picks 3-5 moments; each becomes a 9:16 Short project (clips/NN) with 3 preview frames"""
    import clips
    if not is_long(slug): raise ValueError("chỉ dùng cho video dài đã dựng")
    job.say("Claude chọn khoảnh khắc hay nhất để cắt thành Shorts…")
    picks = bridge.pick_clips(slug)["clips"]
    made = clips.make_all(slug, picks, log=job.say)
    for c in made:
        k = c["k"]; a, b = c["frames"]
        job.say(f"Xem trước Short {k:02d} (dựng lại khổ dọc)…")
        try:
            run_builder(job, clips.clip_slug(slug, k), ["--preview", f"{a + 40},{(a + b) // 2},{b - 30}", "--pct", "35"])
        except Exception as e:
            if job.cancelled: raise
            job.say(f"   (lỗi xem trước: {e})")
    return {"clips": len(made)}


def job_render_clip(job, slug, k, quality="normal"):
    import clips
    info = jload(os.path.join(clips.clips_dir(slug), f"{int(k):02d}", "clip.json"))
    if not info: raise ValueError("không có Short này")
    a, b = info["frames"]
    job.say(f"Render Short {int(k):02d} «{info.get('title', '')}» (khung {a}-{b}, 1080x1920)…")
    run_builder(job, clips.clip_slug(slug, k), ["--render", "--seq", "--quality", quality, "--frames", f"{a}-{b}", "--pct", "100"])
    return {"file": f"clips/{int(k):02d}/short.mp4"}


def job_learn(job, slug):
    job.say("Đọc số liệu giữ chân người xem, tìm chỗ tụt; Claude rút bài học cho các video sau…")
    r = bridge.learn_retention(slug)
    job.say(f"   {len(r['data']['drops'])} chỗ tụt; {len(r['lessons'])} bài học mới -> library/LESSONS.md")
    for x in r["lessons"]: job.say("   • " + x)
    return {"lessons": len(r["lessons"])}


def job_retention(job, slug):
    job.say("Claude soát giữ chân người xem (câu móc 15 giây đầu, đoạn dễ tụt người xem)…")
    r = bridge.retention_review(slug)
    job.say(f"   Câu móc: {r['hook_score']}/10. {len(r['issues'])} chỗ cần sửa (xem ở bước 2, bấm 'Áp dụng' từng chỗ).")
    return {"hook_score": r["hook_score"], "issues": len(r["issues"])}


def job_thumb_prompts(job, slug):
    """prompts for outside image AIs + reference pictures of the characters they show (youtube/ai_prompts.json, refs/<id>.png)"""
    import youtube
    yd = os.path.join(pdir(slug), "youtube"); os.makedirs(yd, exist_ok=True)
    job.say("Claude viết prompt tạo thumbnail bằng AI khác (ChatGPT, Gemini, Midjourney, Ideogram…)…")
    data = bridge.thumbnail_prompts(slug)
    json.dump(data, open(os.path.join(yd, "ai_prompts.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    lines = [f"STYLE: {data['style_en']}", ""]
    for k, p in enumerate(data["prompts"], 1):
        lines += [f"=== {k}. {p['title_vi']}  (ảnh tham chiếu: {', '.join('refs/' + c + '.png' for c in p['chars']) or '—'})",
                  "PROMPT:", p["prompt_en"], "NEGATIVE:", p["negative_en"], "MIDJOURNEY:", p["midjourney"],
                  "CÓ CHỮ (Ideogram / GPT image):", p["text_in_image_en"],
                  f"CHỮ TỰ THÊM: {p['text_overlay']['text']} — {p['text_overlay']['where']}, {p['text_overlay']['color']}, {p['text_overlay']['font']}",
                  f"MẸO: {p['tips_vi']}", ""]
    open(os.path.join(yd, "ai_prompts.txt"), "w", encoding="utf-8").write("\n".join(lines))
    rd = os.path.join(yd, "refs"); os.makedirs(rd, exist_ok=True)
    need = []
    for p in data["prompts"]:
        for c in p["chars"]:
            if c not in need: need.append(c)
    job.say(f"   {len(data['prompts'])} prompt; render ảnh tham chiếu cho {need}")
    for cid in need:
        try:
            td = os.path.join(rd, "_" + cid); os.makedirs(td, exist_ok=True); sp = os.path.join(td, "story.json")
            json.dump(youtube.ref_story(slug, cid), open(sp, "w", encoding="utf-8"), indent=1)
            run_builder(job, slug, ["--preview", "2", "--size", "1600x900", "--samples", "32", "--square"], story=sp)
            src = os.path.join(td, "preview", "p_0002.png")
            if os.path.exists(src): shutil.copy(src, os.path.join(rd, f"{cid}.png"))
        except Exception as e:
            if job.cancelled: raise
            job.say(f"   (không render được ảnh tham chiếu {cid}: {e})")
    return {"prompts": len(data["prompts"]), "refs": need}


def render_thumb(job, slug, yd, k, concept):
    import youtube
    td = os.path.join(yd, f"thumb_{k}"); os.makedirs(td, exist_ok=True)
    sp = os.path.join(td, "story.json"); json.dump(youtube.thumb_story(slug, concept), open(sp, "w", encoding="utf-8"), indent=1)
    errs = storycheck.check_story(jload(sp))
    if errs: job.say("   story thumbnail lỗi: " + "; ".join(errs[:3])); return None
    run_builder(job, slug, ["--preview", "2", "--size", "1280x720", "--samples", "48"], story=sp)
    src = os.path.join(td, "preview", "p_0002.png"); dst = os.path.join(yd, f"thumb_{k}.png")
    if os.path.exists(src): shutil.copy(src, dst); return dst
    return None


def job_bench(job, slug, pct=100, quality="normal"):
    """render a few frames of the current story and remember seconds/frame for estimates"""
    t = slug
    if is_long(slug):
        st = longform.status(slug); c = next((c for c in st if c["story"]), None)
        if not c: raise ValueError("chưa có phần nào dựng xong để đo")
        t = longform.chapter_slug(slug, c["n"])
    samples = {"fast": 8, "normal": 16, "high": 32}.get(quality, 32)
    out = run_builder(job, t, ["--bench", "3", "--pct", str(int(pct)), "--samples", str(samples)])
    m = re.search(r"BENCH sec_per_frame ([0-9.]+)", out)
    if not m: raise ValueError("không đo được tốc độ")
    g = re.search(r"^GPU (.+?)  compositor (\S+)", out, re.M)
    if g:
        name = g.group(1)
        job.say(f"Card đồ họa Blender đang dùng: {name} (compositor: {g.group(2)})")
        if not re.search(r"nvidia|geforce|rtx|gtx|radeon rx|quadro", name, re.I):
            job.say("   CẢNH BÁO: Blender không chạy bằng card NVIDIA. Windows → Cài đặt → Hệ thống → Màn hình → Đồ họa → thêm blender.exe → "
                    "Hiệu năng cao (hoặc NVIDIA Control Panel → Manage 3D settings → blender.exe → High-performance NVIDIA processor), rồi đo lại.")
        ls = local_settings(); ls["gpu"] = name; json.dump(ls, open(LOCAL, "w", encoding="utf-8"), indent=1)
    st = jload(os.path.join(pdir(t), "story.json")) or {}
    kind = "long" if st.get("meta", {}).get("aspect") == "16:9" else "short"
    if int(pct) == 100 and quality == "normal":                  # only a full-size, normal-quality measurement is stored
        ls = local_settings(); ls.setdefault("spf", {})[kind] = round(float(m.group(1)), 2)
        json.dump(ls, open(LOCAL, "w", encoding="utf-8"), indent=1)
        job.say(f"Tốc độ đo được: {m.group(1)} s/khung (video {'dài 16:9' if kind == 'long' else 'Shorts'}, 100 %, {samples} mẫu). Đã lưu để ước tính.")
    else:
        job.say(f"Tốc độ đo được: {m.group(1)} s/khung ở {pct} %, {samples} mẫu (chỉ lưu khi đo ở 100 %, chất lượng Chuẩn).")
    return {"sec_per_frame": float(m.group(1))}


def job_render(job, slug, pct=100, frames=None, samples=None, quality="normal"):
    if "/chapters/" not in slug and is_long(slug) and not frames: return job_render_long(job, slug, pct, samples, quality)
    args = ["--render"]
    if shutil.which("ffmpeg") and quality:                     # image sequence: resumable, 'on twos' in fast mode
        args += ["--seq", "--quality", quality]
    if pct and int(pct) != 100: args += ["--pct", str(int(pct))]
    if frames: args += ["--frames", frames]
    if samples: args += ["--samples", str(int(samples))]
    out = run_builder(job, slug, args)
    m = re.search(r"RENDERED -> (.+)", out)
    path = m.group(1).strip() if m else None
    if path and os.path.exists(path) and shutil.which("ffprobe"):
        pr = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,nb_frames,duration", "-of", "json", path],
                            capture_output=True, text=True)
        job.say("ffprobe: " + pr.stdout.replace("\n", " ")[:400])
    return {"file": os.path.relpath(path, pdir(slug)).replace("\\", "/") if path else None}


def job_splice(job, slug, part):
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import splice
    story = jload(os.path.join(pdir(slug), "story.json")) or {}
    full = os.path.join(pdir(slug), story.get("meta", {}).get("output", "out.mp4"))
    if not os.path.exists(full): raise ValueError(f"chưa có video đầy đủ {os.path.basename(full)} (render cả video trước)")
    job.say(f"Ghép {os.path.basename(part)} vào {os.path.basename(full)} (bản cũ giữ ở *_before.mp4)…")
    out = splice.splice(full, part)
    job.say("Xong: " + os.path.basename(out))
    return {"file": os.path.basename(out)}


def job_design(job, kind, name, brief, dim, feedback, culture=None):
    if kind == "chars": return bridge.design_char(name, brief, feedback=feedback)
    if kind == "cultures": return bridge.design_culture(name, brief, feedback=feedback)
    if kind == "outfits": return bridge.design_outfit(name, brief, culture=culture, feedback=feedback)
    return bridge.design_item(kind, name, brief, dim=dim, feedback=feedback)


# =====================================================================
#  HTTP
# =====================================================================
class Handler(BaseHTTPRequestHandler):
    server_version = "WhyShorts/1.0"

    def log_message(self, fmt, *args):       # quiet
        if os.environ.get("WHYSHORTS_HTTP_LOG"): super().log_message(fmt, *args)

    def send_json(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code); self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b))); self.send_header("Cache-Control", "no-store"); self.end_headers()
        self.wfile.write(b)

    def send_file(self, path):
        if not os.path.isfile(path): return self.send_json({"error": "not found"}, 404)
        ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
        size = os.path.getsize(path); rng = self.headers.get("Range")
        start, end = 0, size - 1
        if rng and rng.startswith("bytes="):
            a, _, b = rng[6:].partition("-"); start = int(a or 0); end = int(b) if b else size - 1
            self.send_response(206); self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        else:
            self.send_response(200)
        self.send_header("Content-Type", ctype); self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1)); self.send_header("Cache-Control", "no-cache"); self.end_headers()
        with open(path, "rb") as f:
            f.seek(start); left = end - start + 1
            while left > 0:
                chunk = f.read(min(1 << 16, left))
                if not chunk: break
                try: self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError): return
                left -= len(chunk)

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(n) if n else b""

    def jbody(self):
        b = self.body(); return json.loads(b.decode("utf-8")) if b else {}

    @staticmethod
    def safe_join(base, rel):
        p = os.path.realpath(os.path.join(base, rel))
        if not p.startswith(os.path.realpath(base) + os.sep): raise ValueError("bad path")
        return p

    def do_GET(self):
        try: self.route("GET")
        except ValueError as e: self.send_json({"error": str(e)}, 400)
        except Exception as e: log_error(); self.send_json({"error": f"{type(e).__name__}: {e}"}, 500)

    def do_POST(self):
        try: self.route("POST")
        except ValueError as e: self.send_json({"error": str(e)}, 400)
        except Exception as e: log_error(); self.send_json({"error": f"{type(e).__name__}: {e}"}, 500)

    do_PUT = do_POST

    def route(self, method):
        u = urlparse(self.path); path = unquote(u.path); q = parse_qs(u.query)
        parts = [p for p in path.split("/") if p]
        if method == "GET" and (path == "/" or path == "/index.html"):
            return self.send_file(os.path.join(UI, "index.html"))
        if method == "GET" and parts[:1] == ["ui"]:
            return self.send_file(self.safe_join(UI, "/".join(parts[1:])))
        if method == "GET" and parts[:1] == ["library"]:
            rel = "/".join(parts[1:])
            if not rel.endswith((".png", ".jpg", ".json")): raise ValueError("chỉ xem ảnh/json")
            return self.send_file(self.safe_join(bridge.LIB, rel))
        if parts[:1] != ["api"]: return self.send_json({"error": "not found"}, 404)
        api = parts[1:]

        if api == ["status"]:
            return self.send_json(self.status())
        if api == ["estimate"]:
            return self.send_json(estimate(float(q.get("minutes", ["1"])[0]), float(q["wpm"][0]) if q.get("wpm") else None,
                                           q.get("format", ["short"])[0]))
        if api == ["channel"]:
            p = os.path.join(bridge.LIB, "channel.json")
            if method == "POST":
                b = self.jbody(); ch = {k: b[k] for k in ("name", "tagline", "host", "host_note_vi", "watermark", "end_screen", "end_screen_sec", "color") if k in b}
                if ch.get("name"): json.dump(ch, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
                elif os.path.exists(p): os.remove(p)
            return self.send_json({"channel": jload(p), "chars": storycheck.LibIndex().list("chars")})
        if api == ["ping"]:
            return self.send_json({"ok": True, "pid": os.getpid(), "started": STARTED,
                                   "jobs": len([j for j in JOBS.values() if j.status == "running"])})
        if api == ["usage"]:
            return self.send_json(bridge.usage())
        if api[:1] == ["jobs"] and len(api) >= 2:
            j = JOBS.get(api[1])
            if not j: return self.send_json({"error": "no job"}, 404)
            if len(api) == 3 and api[2] == "cancel" and method == "POST":
                j.cancel(); return self.send_json({"ok": True})
            return self.send_json(j.to_json(int(q.get("since", ["0"])[0])))

        if api == ["projects"]:
            if method == "GET":
                os.makedirs(PROJECTS, exist_ok=True)
                rows = []
                for s in sorted(os.listdir(PROJECTS)):
                    d = os.path.join(PROJECTS, s)
                    if not os.path.isdir(d): continue
                    c = jload(os.path.join(d, "content.json")) or {}; st = jload(os.path.join(d, "story.json")) or {}
                    rows.append({"slug": s, "title": c.get("title") or st.get("meta", {}).get("title") or s,
                                 "mtime": os.path.getmtime(d), "has_story": bool(st), "has_voice": os.path.exists(os.path.join(d, "voice.wav"))})
                rows.sort(key=lambda r: -r["mtime"])
                return self.send_json(rows)
            b = self.jbody(); slug = slugify(b.get("slug") or b.get("title") or "video")
            base, k = slug, 2
            while os.path.exists(os.path.join(PROJECTS, slug)): slug = f"{base}-{k}"; k += 1
            os.makedirs(pdir(slug)); save_settings(slug, minutes=float(b.get("minutes", 1.0)), title=b.get("title", ""),
                                                   format="long" if b.get("format") == "long" else "short")
            return self.send_json({"slug": slug})

        if api[:1] == ["projects"] and len(api) >= 2:
            slug = api[1]; d = pdir(slug); act = api[2:]
            if not act:
                return self.send_json(project_state(slug))
            if act == ["settings"]:
                return self.send_json(save_settings(slug, **self.jbody()))
            if act == ["ideas"]:
                b = self.jbody(); return self.send_json(start_job("ideas", slug, job_ideas, slug, b.get("topic", "")).to_json())
            if act == ["idea"]:
                b = self.jbody()
                if "index" in b:
                    idea = (jload(os.path.join(d, "ideas.json")) or {})["ideas"][int(b["index"])]
                else:
                    idea = {"title": b["topic"], "logline": b.get("notes", ""), "free_topic": True}
                json.dump(idea, open(os.path.join(d, "idea.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
                return self.send_json({"idea": idea})
            if act == ["content", "write"]:
                b = self.jbody(); m = float(b.get("minutes", 1.0)); save_settings(slug, minutes=m)
                return self.send_json(start_job("write_content", slug, job_write, slug, m).to_json())
            if act == ["content", "rewrite"]:
                b = self.jbody()
                return self.send_json(start_job("rewrite_seq", slug, job_rewrite, slug, int(b["id"]), b["request"]).to_json())
            if act == ["content"] and method == "POST":
                c = self.jbody()["content"]
                errs = bridge.validate(c, bridge.load_schema("content_long" if longform.is_long(c) else "content"))
                if errs: raise ValueError("content sai cấu trúc: " + "; ".join(errs[:3]))
                for i, s in enumerate(c["sequences"]): s["id"] = i + 1          # keep ids in display order
                c["word_count"] = len(c["vo_en"].split())
                bridge._save_versioned(slug, "content.json", c)
                return self.send_json({"ok": True, "word_count": c["word_count"]})
            if act[:1] == ["history"]:
                if len(act) == 2 and method == "GET":
                    return self.send_file(self.safe_join(os.path.join(d, "history"), act[1]))
                if len(act) == 3 and act[2] == "restore":
                    src = self.safe_join(os.path.join(d, "history"), act[1])
                    target = re.sub(r"_\d{8}-\d{6}\.json$", ".json", act[1])
                    bridge._save_versioned(slug, target, jload(src))
                    return self.send_json({"ok": True, "restored": target})
            if act == ["voice"] and method == "POST":
                data = self.body()
                if data[:4] != b"RIFF" or data[8:12] != b"WAVE": raise ValueError("cần file .wav (không nhận mp3/m4a)")
                import wavfix
                pcm, info = wavfix.to_pcm16(data)
                if info["converted"]:                      # keep what the user uploaded, write 16-bit PCM for the tools
                    open(os.path.join(d, "voice_original.wav"), "wb").write(data)
                open(os.path.join(d, "voice.wav"), "wb").write(pcm)
                j = start_job("align", slug, job_align, slug)
                j.say(f"File tải lên: WAV {info['format']} {info['bits']}-bit, {info['channels']} kênh, {info['rate']} Hz"
                      + (" -> đã chuyển sang PCM 16-bit (bản gốc: voice_original.wav)" if info["converted"] else ""))
                return self.send_json(j.to_json())
            if act == ["align"]:
                return self.send_json(start_job("align", slug, job_align, slug).to_json())
            if act == ["build"]:
                b = self.jbody()
                return self.send_json(start_job("build", slug, job_build, slug, b.get("design", True), b.get("preview", True),
                                                [int(x) for x in b.get("chapters", [])] or None, bool(b.get("replan"))).to_json())
            if act == ["preview"]:
                b = self.jbody(); t = sub_target(slug, b.get("chapter")); frames = b.get("frames") or default_preview_frames(t)
                return self.send_json(start_job("preview", slug, job_preview, t, [int(f) for f in frames], int(b.get("pct", 35))).to_json())
            if act == ["fix"]:
                b = self.jbody(); t = sub_target(slug, b.get("chapter"))
                return self.send_json(start_job("fix", slug, job_fix, t, b["problem"], [int(f) for f in b.get("frames", [])]).to_json())
            if act == ["render"]:
                b = self.jbody(); t = sub_target(slug, b.get("chapter"))
                return self.send_json(start_job("render", slug, job_render, t, b.get("pct", 100), b.get("frames"), b.get("samples"),
                                                b.get("quality", "normal")).to_json())
            if act == ["youtube"] and method == "POST":
                b = self.jbody()
                return self.send_json(start_job("youtube", slug, job_youtube, slug, b.get("thumbs", True)).to_json())
            if act == ["youtube", "prompts"] and method == "POST":
                return self.send_json(start_job("thumb_prompts", slug, job_thumb_prompts, slug).to_json())
            if act == ["bench"]:
                b = self.jbody()
                return self.send_json(start_job("bench", slug, job_bench, slug, int(b.get("pct", 100)), b.get("quality", "normal")).to_json())
            if act == ["concat"]:
                return self.send_json(start_job("concat", slug, lambda job, s: {"file": os.path.basename(longform.concat(s, log=job.say))}, slug).to_json())
            if act == ["splice"]:                      # put a re-rendered part (parts/*_AAAA-BBBB.mp4) into the full video
                part = self.safe_join(d, self.jbody()["part"])
                return self.send_json(start_job("splice", slug, job_splice, slug, part).to_json())
            if act == ["analytics", "upload"] and method == "POST":
                n = int(self.headers.get("Content-Length", 0)); data = self.rfile.read(n)
                if n > 20_000_000: raise ValueError("file quá lớn")
                ad = os.path.join(d, "analytics"); os.makedirs(ad, exist_ok=True)
                open(os.path.join(ad, "retention.csv"), "wb").write(data)
                return self.send_json(start_job("learn", slug, job_learn, slug).to_json())
            if act == ["clips"] and method == "POST":
                return self.send_json(start_job("clips", slug, job_clips, slug).to_json())
            if act[:2] == ["clips", "render"] and method == "POST":
                b = self.jbody()
                return self.send_json(start_job("render_clip", slug, job_render_clip, slug, int(b["k"]), b.get("quality", "normal")).to_json())
            if act == ["youtube", "subs"] and method == "POST":
                langs = [x for x in self.jbody().get("langs", []) if x in bridge.LANG_NAMES]
                return self.send_json(start_job("subs", slug, job_subs, slug, langs).to_json())
            if act == ["content", "review"] and method == "POST":
                return self.send_json(start_job("review", slug, job_retention, slug).to_json())
            if act == ["clean"] and method == "POST":
                return self.send_json(clean_project(slug))
            if act == ["delete"] and method == "POST":
                return self.send_json(delete_project(slug, self.jbody().get("confirm")))
            if act == ["temp"]:
                ps = temp_dirs(slug)
                return self.send_json({"mb": round(sum(_dir_size(p) for p in ps) / 1e6, 1), "dirs": len(ps), "export": export_dir()})
            if act == ["open"]:
                f = self.safe_join(d, self.jbody()["file"])
                if hasattr(os, "startfile"): os.startfile(f); return self.send_json({"ok": True})
                return self.send_json({"ok": False, "url": f"/api/projects/{slug}/file/{self.jbody().get('file', '')}"})
            if act[:1] == ["file"]:
                return self.send_file(self.safe_join(d, "/".join(act[1:])))

        if api == ["library"]:
            return self.send_json(self.library())
        if api[:2] == ["library", "approve"]:
            return self.send_json(bridge.approve(self.jbody()["item"]))
        if api[:2] == ["library", "design"]:
            b = self.jbody(); kind = b["kind"]; name = b["name"]
            if kind not in ("props", "sets", "chars", "cultures", "outfits"): raise ValueError("kind phải là props/sets/chars/cultures/outfits")
            return self.send_json(start_job("design", f"lib:{kind}/{name}", job_design, kind, name, b.get("brief"), b.get("dim"),
                                            b.get("feedback"), b.get("culture")).to_json())
        return self.send_json({"error": "not found"}, 404)

    def status(self):
        h = None
        try:
            h = bridge.cli_help(block=False); claude_ok = bool(h)
            if h is None: h = "Đang kiểm tra Claude CLI…"; claude_ok = None
            elif not h: h = ("Claude CLI không trả lời 'claude --help' trong 20 giây (đang tự cập nhật hoặc chờ đăng nhập?). "
                           "Mở cmd, gõ claude để kiểm tra; tool thử lại sau 5 phút.")
        except bridge.BridgeError as e: claude_ok = False; h = str(e)
        b = bridge.blender_cmd()
        return {"api_key_warning": bridge.api_key_warning(), "claude": claude_ok, "claude_note": None if claude_ok else h,
                "json_schema": bool(claude_ok and "--json-schema" in (h or "")), "blender": b,
                "blender_found": bool(shutil.which(b) or os.path.exists(b)), "usage": bridge.usage(),
                "wpm": WPM, "sec_per_frame": spf_for("short"), "sec_per_frame_long": spf_for("long"), "ffmpeg": bool(shutil.which("ffmpeg")),
                "jobs": [j.to_json(10 ** 9) for j in JOBS.values() if j.status == "running"], "pid": os.getpid(), "started": STARTED}

    def library(self):
        lib = storycheck.LibIndex(); out = {}
        for kind in ("sets", "props", "chars", "cultures", "outfits"):
            rows = []
            for n in lib.list(kind):
                m = lib.meta(kind, n)
                rv = os.path.join(lib.root, kind, n, "_review")
                imgs = []
                if os.path.isdir(rv):
                    rounds = sorted([x for x in os.listdir(rv) if os.path.isdir(os.path.join(rv, x))])
                    sub = os.path.join(rv, rounds[-1]) if rounds else rv
                    imgs = [f"/library/{kind}/{n}/_review/{os.path.relpath(os.path.join(sub, f), rv)}".replace("\\", "/")
                            for f in sorted(os.listdir(sub)) if f.endswith(".png")]
                rows.append({"kind": kind, "name": n, "title_vi": m.get("title_vi", n), "description_vi": m.get("description_vi", ""),
                             "status": m.get("status", "approved"), "review": m.get("review"), "params": m.get("params"),
                             "dim": m.get("dim"), "thumb": f"/library/{kind}/{n}/thumb.png" if os.path.exists(os.path.join(lib.root, kind, n, "thumb.png")) else None,
                             "views": imgs})
            out[kind] = rows
        return out


def _quiet(fn):
    try: fn()
    except Exception: pass


def log_error():
    """errors go to logs/server_errors.log, not the console (a frozen Windows console would freeze the request too)"""
    try:
        os.makedirs(os.path.join(ROOT, "logs"), exist_ok=True)
        with open(os.path.join(ROOT, "logs", "server_errors.log"), "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + traceback.format_exc() + "\n")
    except Exception:
        pass


def no_quick_edit():
    """Windows console: a click in the black window starts a text selection (QuickEdit) and FREEZES every program
    writing to it until Esc - the studio then looks dead (timer stuck at 0). Turn QuickEdit off for this window."""
    if os.name != "nt": return
    try:
        import ctypes
        k = ctypes.windll.kernel32; h = k.GetStdHandle(-10)          # STD_INPUT_HANDLE
        mode = ctypes.c_uint32()
        if k.GetConsoleMode(h, ctypes.byref(mode)):
            k.SetConsoleMode(h, (mode.value & ~0x0040) | 0x0080)      # clear ENABLE_QUICK_EDIT_MODE, keep EXTENDED_FLAGS
    except Exception:
        pass


def black_box():
    """every 60 s, the stack of every thread -> logs/threads.log (written from C, so it works even if Python is stuck).
    If the studio ever freezes, this file says exactly where."""
    try:
        import faulthandler
        os.makedirs(os.path.join(ROOT, "logs"), exist_ok=True)
        global _BB
        _BB = open(os.path.join(ROOT, "logs", "threads.log"), "w", encoding="utf-8")
        faulthandler.dump_traceback_later(60, repeat=True, file=_BB)
    except Exception:
        pass


STARTED = time.strftime("%H:%M:%S")


class StudioServer(ThreadingHTTPServer):
    """one studio per port. Python's default (SO_REUSEADDR) lets a SECOND studio bind the same port on Windows without
    an error; the browser then keeps talking to the old one (seen: an old, stuck studio answered nothing while the new
    window sat idle). Windows: exclusive bind; everywhere: refuse to start when a studio already answers."""
    daemon_threads = True
    allow_reuse_address = os.name != "nt"

    def server_bind(self):
        if os.name == "nt":
            import socket
            try: self.socket.setsockopt(socket.SOL_SOCKET, getattr(socket, "SO_EXCLUSIVEADDRUSE", -5), 1)
            except OSError: pass
        super().server_bind()


def other_studio(host, port):
    """pid of a studio already answering on host:port, 0 if something else holds it, None if free"""
    import socket, urllib.request
    with socket.socket() as so:
        so.settimeout(1.0)
        if so.connect_ex((host, port)) != 0: return None
    try:
        with urllib.request.urlopen(f"http://{host}:{port}/api/ping", timeout=3) as r: return json.load(r).get("pid", 0)
    except Exception:
        return 0


def main(argv):
    no_quick_edit(); black_box()
    port = int(argv[argv.index("--port") + 1]) if "--port" in argv else 1111
    host = argv[argv.index("--host") + 1] if "--host" in argv else "127.0.0.1"
    os.makedirs(PROJECTS, exist_ok=True)
    w = bridge.api_key_warning()
    if w: print(w)
    threading.Thread(target=lambda: _quiet(bridge.cli_help), daemon=True).start()     # ask the CLI once, in the background
    old = other_studio(host, port)
    if old is not None:
        print(f"\n!!! Cổng {port} đang bị một studio khác chiếm" + (f" (tiến trình {old})" if old else " (không trả lời: có thể đang bị kẹt)") + ".")
        print("    Trình duyệt sẽ nói chuyện với studio cũ đó, không phải cửa sổ này. Hãy tắt nó rồi mở lại start_studio.bat:")
        print(f"      taskkill /F /PID {old}" if old else "      Task Manager -> Details -> python.exe (Blender) -> End task  (hoặc: taskkill /F /IM python.exe)")
        print(f"    (Hoặc mở studio ở cổng khác: start_studio.bat --port {port + 1})\n", flush=True)
        return 1
    try:
        srv = StudioServer((host, port), Handler)
    except OSError as e:
        print(f"\n!!! Không mở được cổng {port}: {e}. Tắt studio cũ (Task Manager -> python.exe) rồi mở lại.\n", flush=True)
        return 1
    srv.handle_error = lambda request, client_address: log_error()                  # (broken pipes etc.: not on the console)
    url = f"http://{host}:{port}"
    print(f"WhyShorts Studio: {url}   (Ctrl+C để tắt)", flush=True)
    if "--no-browser" not in argv:
        try: webbrowser.open(url)
        except Exception: pass
    try: srv.serve_forever()
    except KeyboardInterrupt: pass


if __name__ == "__main__":
    main(sys.argv[1:])
