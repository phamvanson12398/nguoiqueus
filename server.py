"""WhyShorts Studio — local web server + control page.

    python server.py                 then open http://127.0.0.1:8765
    options: --port 8765  --host 127.0.0.1  --no-browser

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

PROJECTS = os.path.join(ROOT, "projects")
UI = os.path.join(ROOT, "ui")
WPM = 150                       # AI voice words per minute
SEC_PER_FRAME = 1.4             # measured render speed on the user's GPU (toolkit v2)
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
            try: p.kill()
            except Exception: pass

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
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,60}", slug or ""): raise ValueError("tên dự án không hợp lệ")
    return os.path.join(PROJECTS, slug)


def jload(path, default=None):
    try: return json.load(open(path, encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError): return default


def estimate(minutes):
    """numbers shown next to the minutes box"""
    words = int(round(minutes * WPM))
    seqs = max(4, min(7, int(round(minutes * 6)))) if minutes <= 1.25 else int(round(minutes * 5.5))
    frames = int(round(minutes * 60 * FPS))
    return {"minutes": minutes, "words": words, "sequences": seqs, "chapters": 0 if minutes <= 1.25 else max(2, round(seqs / 5.5)),
            "frames": frames, "render_seconds": round(frames * SEC_PER_FRAME)}


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
    st["estimate"] = estimate((st["settings"] or {}).get("minutes", 1.0))
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
    job.say(f"Claude đang viết content {minutes} phút (~{e['words']} từ, ~{e['sequences']} chuỗi)…")
    data = bridge.write_content(slug, idea, minutes)
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
    est = len(content["vo_en"].split()) / WPM * 60
    job.say(f"Giọng đọc {r['duration']} s ({r['frames']} khung), {r['word_count']} chữ, {len(r['segments'])} cụm. "
            f"Ước tính từ content: {est:.0f} s.")
    return {"duration": r["duration"], "frames": r["frames"]}


def run_builder(job, slug, args, progress_total=None):
    """run builder.py in Blender, stream its output into the job log, parse RENDER FRAME lines"""
    story = os.path.join(pdir(slug), "story.json")
    b = bridge.blender_cmd()
    if os.path.basename(b).lower().startswith("python"):
        cmd = [b, os.path.join(ROOT, "tools", "bpy_run.py"), os.path.join(ROOT, "builder.py"), story] + args
    else:
        cmd = [b, "-b", "--factory-startup", "-P", os.path.join(ROOT, "builder.py"), "--", story] + args
    job.say("$ " + " ".join(os.path.basename(c) if i < 2 else c for i, c in enumerate(cmd)))
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", cwd=ROOT)
    job.procs.append(p)
    a0 = None; t0 = time.time(); last = []
    for line in p.stdout:
        line = line.rstrip()
        if line.startswith("Fra:") or "EGL Error" in line or line.startswith("DeprecationWarning") or "Video append frame" in line: continue
        if line.startswith("RENDER START"):
            _, _, a, b_, *_ = line.split(); a0, b1 = int(a), int(b_); job.progress = {"done": 0, "total": b1 - a0 + 1, "eta": None}
        if line.startswith("RENDER FRAME"):
            f, a, b_, el = line.split()[2:6]; f, a, b_, el = int(f), int(a), int(b_), float(el)
            done = f - a + 1; total = b_ - a + 1; rate = el / max(1, done)
            job.progress = {"done": done, "total": total, "eta": round(rate * (total - done)), "sec_per_frame": round(rate, 2), "frame": f}
            if done % 10 and done != total: continue
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
    fr = []
    for a, b in spans[:8]: fr.append((a + b) // 2)
    for a, b in spans[1:4]: fr.append(a + 2)                      # just after a transition
    return sorted(set(fr))[:10] or [1]


def job_build(job, slug, design=True, preview=True):
    """'Duyệt & dựng': plan shots -> design missing library items -> check -> build + preview, with automatic fix rounds"""
    d = pdir(slug); lib = storycheck.LibIndex()
    if not os.path.exists(os.path.join(d, "words.json")): raise ValueError("chưa có giọng đọc đã canh chữ (tải voice.wav lên trước)")
    job.say("1/4 Claude chuyển content thành story.json (bảng khung hình, camera v3)…")
    res = bridge.plan_shots(slug)
    missing = res.get("missing", [])
    job.say(f"   story.json xong. Đồ mới cần thiết kế: {', '.join(m['kind'] + '/' + m['name'] for m in missing) or 'không'}")
    failed = []
    if missing and design:
        job.say("2/4 Thiết kế đồ còn thiếu (mỗi món vài phút)…")
        for k, m in enumerate(missing, 1):
            if lib.exists(m["kind"], m["name"]):
                job.say(f" - [{k}/{len(missing)}] {m['kind']}/{m['name']}: đã có trong thư viện, bỏ qua"); continue
            job.say(f" - [{k}/{len(missing)}] {m['kind']}/{m['name']}: {m['brief']}")
            try:
                r = bridge.design_char(m["name"], m["brief"]) if m["kind"] == "chars" else bridge.design_item(m["kind"], m["name"], m["brief"])
                last = ([x for x in r.get("rounds", []) if "score" in x] or [{}])[-1]
                job.say(f"   -> {last.get('score', '?')}/10 {last.get('summary_vi', '')}")
                if not r.get("ok", True): failed.append(m["name"])
            except Exception as e:
                if job.cancelled: raise
                failed.append(m["name"]); job.say(f"   -> LỖI: {e}")
    if failed: raise ValueError("thiết kế chưa xong: " + ", ".join(failed) + " (xem log; có thể thiết kế lại ở tab Thư viện rồi bấm 'Chỉ render lại xem trước')")
    errs = storycheck.check_story(jload(os.path.join(d, "story.json")))
    if errs: raise ValueError("story.json còn lỗi: " + "; ".join(errs[:5]))
    if not preview: return {"missing": missing}
    for attempt in range(bridge.MAX_FIX + 1):
        frames = default_preview_frames(slug)
        job.say(f"{3 if attempt == 0 else '3b'}/4 Dựng cảnh trong Blender và xem trước khung {frames} (35 %)…")
        problem = None
        try:
            out = job_preview(job, slug, frames)["log"]
            warns = [l for l in out.splitlines() if l.startswith("WARN") or "CAMERA NEEDS FIX" in l]
            if warns: problem = "Camera chưa đạt cam_report:\n" + "\n".join(warns)
        except ValueError as e:
            if job.cancelled: raise
            problem = f"Dựng trong Blender bị lỗi:\n{e}"
        if not problem:
            job.say("4/4 Xong: CAMERA OK, đã có ảnh xem trước. Xem ảnh rồi bấm Render, hoặc mô tả lỗi để Claude sửa.")
            return {"missing": missing, "fix_rounds": attempt}
        if attempt == bridge.MAX_FIX: raise ValueError(problem)
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


def job_render(job, slug, pct=100, frames=None, samples=None):
    args = ["--render"]
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


def job_design(job, kind, name, brief, dim, feedback):
    if kind == "chars": return bridge.design_char(name, brief, feedback=feedback)
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
        except Exception as e: traceback.print_exc(); self.send_json({"error": f"{type(e).__name__}: {e}"}, 500)

    def do_POST(self):
        try: self.route("POST")
        except ValueError as e: self.send_json({"error": str(e)}, 400)
        except Exception as e: traceback.print_exc(); self.send_json({"error": f"{type(e).__name__}: {e}"}, 500)

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
            return self.send_json(estimate(float(q.get("minutes", ["1"])[0])))
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
            os.makedirs(pdir(slug)); save_settings(slug, minutes=float(b.get("minutes", 1.0)), title=b.get("title", ""))
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
                errs = bridge.validate(c, bridge.load_schema("content"))
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
                return self.send_json(start_job("build", slug, job_build, slug, b.get("design", True), b.get("preview", True)).to_json())
            if act == ["preview"]:
                b = self.jbody(); frames = b.get("frames") or default_preview_frames(slug)
                return self.send_json(start_job("preview", slug, job_preview, slug, [int(f) for f in frames], int(b.get("pct", 35))).to_json())
            if act == ["fix"]:
                b = self.jbody()
                return self.send_json(start_job("fix", slug, job_fix, slug, b["problem"], [int(f) for f in b.get("frames", [])]).to_json())
            if act == ["render"]:
                b = self.jbody()
                return self.send_json(start_job("render", slug, job_render, slug, b.get("pct", 100), b.get("frames"), b.get("samples")).to_json())
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
            if kind not in ("props", "sets", "chars"): raise ValueError("kind phải là props/sets/chars")
            return self.send_json(start_job("design", f"lib:{kind}/{name}", job_design, kind, name, b.get("brief"), b.get("dim"),
                                            b.get("feedback")).to_json())
        return self.send_json({"error": "not found"}, 404)

    def status(self):
        h = None
        try: h = bridge.cli_help(); claude_ok = True
        except bridge.BridgeError as e: claude_ok = False; h = str(e)
        b = bridge.blender_cmd()
        return {"api_key_warning": bridge.api_key_warning(), "claude": claude_ok, "claude_note": None if claude_ok else h,
                "json_schema": bool(claude_ok and "--json-schema" in h), "blender": b,
                "blender_found": bool(shutil.which(b) or os.path.exists(b)), "usage": bridge.usage(),
                "wpm": WPM, "sec_per_frame": SEC_PER_FRAME,
                "jobs": [j.to_json(10 ** 9) for j in JOBS.values() if j.status == "running"]}

    def library(self):
        lib = storycheck.LibIndex(); out = {}
        for kind in ("sets", "props", "chars"):
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


def main(argv):
    port = int(argv[argv.index("--port") + 1]) if "--port" in argv else 8765
    host = argv[argv.index("--host") + 1] if "--host" in argv else "127.0.0.1"
    os.makedirs(PROJECTS, exist_ok=True)
    w = bridge.api_key_warning()
    if w: print(w)
    srv = ThreadingHTTPServer((host, port), Handler)
    url = f"http://{host}:{port}"
    print(f"WhyShorts Studio: {url}   (Ctrl+C để tắt)", flush=True)
    if "--no-browser" not in argv:
        try: webbrowser.open(url)
        except Exception: pass
    try: srv.serve_forever()
    except KeyboardInterrupt: pass


if __name__ == "__main__":
    main(sys.argv[1:])
