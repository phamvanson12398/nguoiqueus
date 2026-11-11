"""claude_bridge: every call from the tool to Claude goes through here (`claude -p`).

Jobs (each returns validated JSON; schemas in schemas/):
    ideas            10 ideas for a topic (or open)                 -> projects/<slug>/ideas.json
    write_content    narration EN/VI + sequence table for an idea  -> projects/<slug>/content.json (+ history)
    rewrite_seq      rewrite one sequence on request               -> content.json (+ history)
    plan_shots       approved content + words -> story.json        -> projects/<slug>/story.json
    design_prop      new library prop: build.py -> render -> Claude looks at the renders and fixes (<= 2 rounds)
    design_set       same for a set
    design_char      new character (char.json)
    fix_from_preview preview PNGs + a problem -> JSON patch on story.json

Command line (run with any Python 3.10+, including Blender's bundled python.exe):
    python claude_bridge.py design_prop milk_carton "hộp sữa giấy kiểu Mỹ, mái nhọn..." --dim 3d
    python claude_bridge.py design_prop milk_carton --feedback "to hơn, đổi màu xanh"
    python claude_bridge.py approve props/milk_carton
    python claude_bridge.py ideas --topic "đồ vật trong bếp" --project kitchen
    python claude_bridge.py usage                      (calls, time, cost estimate from logs/)

Environment: WHYSHORTS_CLAUDE (claude command, default 'claude'), WHYSHORTS_BLENDER (blender.exe, or a
python that has the `bpy` module), WHYSHORTS_MODEL (optional model for every job),
WHYSHORTS_KEEP_API_KEY=1 to pass ANTHROPIC_API_KEY through (otherwise it is removed so the CLI uses
the Pro/Max subscription).
"""
import ast, datetime, json, os, re, shutil, subprocess, sys, threading, time

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path: sys.path.insert(0, ROOT)
from jsonval import validate
import storycheck

LOG_DIR = os.path.join(ROOT, "logs")
SCHEMAS = os.path.join(ROOT, "schemas")
LIB = os.path.join(ROOT, "library")
MAX_FIX = 2                       # schema / safety / build-error retries per call, and review rounds per design

READ_TOOLS = ["Read", "Glob", "Grep"]
WEB_TOOLS = ["WebSearch", "WebFetch"]
JOB_TOOLS = {"ideas": WEB_TOOLS, "write_content": WEB_TOOLS + ["Read"], "rewrite_seq": [], "plan_shots": READ_TOOLS,
             "design_prop": READ_TOOLS, "design_set": READ_TOOLS, "design_char": READ_TOOLS, "review": READ_TOOLS,
             "fix_from_preview": READ_TOOLS}


class BridgeError(Exception):
    pass


_tls = threading.local()          # server.py sets _tls.hook / _tls.procs per job thread


def say(msg):
    hook = getattr(_tls, "hook", None)
    (hook or (lambda m: print(m, flush=True)))(msg)


def _popen_run(cmd, timeout, **kw):
    """subprocess.run that registers the process so a job can be cancelled from server.py"""
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE if kw.get("input") is not None else None,
                         text=True, encoding="utf-8", errors="replace", cwd=kw.get("cwd"), env=kw.get("env"))
    procs = getattr(_tls, "procs", None)
    if procs is not None: procs.append(p)
    try:
        out, err = p.communicate(kw.get("input"), timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill(); p.communicate(); raise
    finally:
        if procs is not None and p in procs: procs.remove(p)
    if getattr(_tls, "cancelled", False): raise BridgeError("đã hủy")
    return subprocess.CompletedProcess(cmd, p.returncode, out, err)


# =====================================================================
#  environment
# =====================================================================
def claude_cmd():
    """command list for the Claude CLI.  On Windows an npm install gives claude.cmd; running it would pass our
    JSON arguments through cmd.exe (quotes, <, >, | break), so call node + cli.js directly when possible."""
    c = os.environ.get("WHYSHORTS_CLAUDE", "claude")
    path = shutil.which(c) or c
    if os.name == "nt" and path.lower().endswith((".cmd", ".bat")):
        base = os.path.dirname(path)
        for cand in (os.path.join(base, "node_modules", "@anthropic-ai", "claude-code", "cli.js"),
                     os.path.join(os.environ.get("APPDATA", ""), "npm", "node_modules", "@anthropic-ai", "claude-code", "cli.js")):
            node = shutil.which("node") or os.path.join(base, "node.exe")
            if os.path.exists(cand) and node and os.path.exists(node):
                return [node, cand]
    return [path]


def blender_cmd():
    b = os.environ.get("WHYSHORTS_BLENDER")
    if b: return b
    win = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
    return win if os.path.exists(win) else "blender"


def api_key_warning():
    if os.environ.get("ANTHROPIC_API_KEY"):
        keep = os.environ.get("WHYSHORTS_KEEP_API_KEY") == "1"
        return ("CẢNH BÁO: máy có biến ANTHROPIC_API_KEY. Claude CLI sẽ tính phí API thay vì dùng gói Pro/Max. "
                + ("Đang giữ biến này vì WHYSHORTS_KEEP_API_KEY=1." if keep else "Tool đã bỏ biến này khi gọi Claude."))
    return None


_help_cache = None


def cli_help():
    global _help_cache
    if _help_cache is None:
        try:
            _help_cache = subprocess.run(claude_cmd() + ["--help"], capture_output=True, text=True, timeout=60,
                                         encoding="utf-8", errors="replace").stdout
        except FileNotFoundError:
            raise BridgeError(f"Không tìm thấy Claude CLI ('{' '.join(claude_cmd())}'). Cài Claude Code rồi đăng nhập bằng gói Pro/Max.")
    return _help_cache


def load_schema(name):
    return json.load(open(os.path.join(SCHEMAS, name + ".json"), encoding="utf-8"))


# =====================================================================
#  logging
# =====================================================================
def log_call(rec):
    os.makedirs(os.path.join(LOG_DIR, "calls"), exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    full = os.path.join(LOG_DIR, "calls", f"{stamp}_{rec['job']}.json")
    json.dump(rec, open(full, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    line = {k: rec.get(k) for k in ("time", "job", "project", "attempt", "ok", "seconds", "cost_usd", "turns", "model", "session", "error")}
    line["prompt_chars"] = len(rec.get("prompt", "")); line["file"] = os.path.relpath(full, ROOT)
    with open(os.path.join(LOG_DIR, "claude_calls.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")


def usage():
    p = os.path.join(LOG_DIR, "claude_calls.jsonl")
    if not os.path.exists(p): return {"calls": 0}
    rows = [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
    by = {}
    for r in rows:
        b = by.setdefault(r["job"], {"calls": 0, "seconds": 0.0, "cost_usd": 0.0, "failed": 0})
        b["calls"] += 1; b["seconds"] += r.get("seconds") or 0; b["cost_usd"] += r.get("cost_usd") or 0
        b["failed"] += 0 if r.get("ok") else 1
    return {"calls": len(rows), "seconds": round(sum(b["seconds"] for b in by.values()), 1),
            "cost_usd_list_price": round(sum(b["cost_usd"] for b in by.values()), 3),
            "by_job": {k: {kk: round(vv, 3) if isinstance(vv, float) else vv for kk, vv in v.items()} for k, v in by.items()}}


# =====================================================================
#  one Claude call (+ automatic fix rounds)
# =====================================================================
def _extract_json(text):
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    s = m.group(1) if m else text[text.find("{"):text.rfind("}") + 1]
    return json.loads(s)


def _run(prompt, schema, tools, model, resume, cwd, timeout):
    h = cli_help()
    cmd = claude_cmd() + ["-p", "--output-format", "json"]
    if resume: cmd += ["--resume", resume]
    style = os.path.join(ROOT, "STYLE.md")
    if "--append-system-prompt-file" in h: cmd += ["--append-system-prompt-file", style]
    else: cmd += ["--append-system-prompt", open(style, encoding="utf-8").read()]
    if "--tools" in h: cmd += ["--tools", ",".join(tools)]
    if tools: cmd += ["--allowedTools", ",".join(tools)]
    use_schema = "--json-schema" in h
    if use_schema: cmd += ["--json-schema", json.dumps(schema, ensure_ascii=False)]
    else: prompt += "\n\nTrả lời DUY NHẤT một khối ```json theo đúng JSON Schema sau:\n" + json.dumps(schema, ensure_ascii=False)
    model = model or os.environ.get("WHYSHORTS_MODEL")
    if model: cmd += ["--model", model]
    env = dict(os.environ)
    if env.get("ANTHROPIC_API_KEY") and env.get("WHYSHORTS_KEEP_API_KEY") != "1": env.pop("ANTHROPIC_API_KEY")
    t0 = time.time()
    p = _popen_run(cmd, timeout, input=prompt, cwd=cwd, env=env)
    secs = round(time.time() - t0, 1)
    try:
        out = json.loads(p.stdout)
    except json.JSONDecodeError:
        raise BridgeError(f"Claude CLI không trả JSON (exit {p.returncode}): {(p.stderr or p.stdout)[-800:]}")
    data = out.get("structured_output")
    if data is None and not out.get("is_error"):
        try: data = _extract_json(out.get("result", ""))
        except Exception: data = None
    return out, data, secs


def call(job, prompt, schema, *, project=None, model=None, tools=None, cwd=ROOT, check=None, timeout=1800, resume=None):
    """Run one job.  check(data) -> list of extra problems (safety, story refs...).
    Schema/check problems are sent back to the same session (--resume) up to MAX_FIX times.
    Returns (data, info) where info has session, cost, seconds, attempts."""
    w = api_key_warning()
    if w: say(w)
    tools = JOB_TOOLS.get(job, []) if tools is None else tools
    info = {"session": resume, "cost_usd": 0.0, "seconds": 0.0, "attempts": 0}
    msg = prompt
    for attempt in range(MAX_FIX + 1):
        info["attempts"] = attempt + 1
        rec = {"time": datetime.datetime.now().isoformat(timespec="seconds"), "job": job, "project": project,
               "attempt": attempt + 1, "prompt": msg, "tools": tools, "model": model or os.environ.get("WHYSHORTS_MODEL")}
        try:
            out, data, secs = _run(msg, schema, tools, model, info["session"], cwd, timeout)
        except subprocess.TimeoutExpired:
            rec.update(ok=False, error="timeout"); log_call(rec); raise BridgeError(f"{job}: Claude không trả lời trong {timeout} s")
        except BridgeError as e:
            rec.update(ok=False, error=str(e)); log_call(rec); raise
        info["session"] = out.get("session_id") or info["session"]
        info["cost_usd"] += out.get("total_cost_usd") or 0; info["seconds"] += secs
        rec.update(seconds=secs, cost_usd=out.get("total_cost_usd"), turns=out.get("num_turns"), session=info["session"],
                   result=data if data is not None else out.get("result"))
        if out.get("is_error"):
            rec.update(ok=False, error=out.get("result") or out.get("subtype")); log_call(rec)
            raise BridgeError(f"{job}: Claude báo lỗi: {rec['error']}")
        problems = ["không đọc được JSON trong câu trả lời"] if data is None else validate(data, schema)
        if not problems and check: problems = check(data)
        rec.update(ok=not problems, problems=problems); log_call(rec)
        if not problems:
            return data, info
        say(f"  [{job}] lần {attempt + 1}: {len(problems)} lỗi -> gửi lại cho Claude sửa")
        msg = ("Câu trả lời trước có lỗi sau, hãy sửa và trả lại TOÀN BỘ JSON đúng schema:\n- "
               + "\n- ".join(str(p) for p in problems[:30]))
    raise BridgeError(f"{job}: vẫn còn lỗi sau {MAX_FIX} lần sửa: {problems[:5]}")


# =====================================================================
#  safety check for Claude-written build.py
# =====================================================================
ALLOWED_IMPORTS = {"math", "random", "bpy", "bmesh", "mathutils"}
BANNED_NAMES = {"open", "exec", "eval", "compile", "__import__", "globals", "locals", "vars", "input", "breakpoint",
                "getattr", "setattr", "delattr", "os", "sys", "subprocess", "shutil", "socket", "importlib"}
BANNED_ATTRS = {"write", "save", "save_as_mainfile", "save_mainfile", "handlers", "driver_namespace", "texts", "libraries",
                "filepath_raw", "system", "popen", "remove_file", "unlink"}
ALLOWED_OPS = ("bpy.ops.mesh.primitive_", "bpy.ops.object.shade_smooth", "bpy.ops.object.shade_flat",
               "bpy.ops.object.shade_auto_smooth", "bpy.ops.curve.primitive_", "bpy.ops.import_scene.gltf")


def _dotted(node):
    parts = []
    while isinstance(node, ast.Attribute): parts.append(node.attr); node = node.value
    if isinstance(node, ast.Name): parts.append(node.id)
    return ".".join(reversed(parts))


def check_build_py(src, kind="props"):
    """-> list of problems (empty = acceptable)"""
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return [f"SyntaxError dòng {e.lineno}: {e.msg}"]
    probs = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                if a.name.split(".")[0] not in ALLOWED_IMPORTS and a.name.split(".")[0] != "core":
                    probs.append(f"dòng {n.lineno}: không được import '{a.name}'")
        elif isinstance(n, ast.ImportFrom):
            mod = (n.module or "").split(".")[0]
            if mod not in ALLOWED_IMPORTS and mod != "core" or n.level:
                probs.append(f"dòng {n.lineno}: không được import từ '{n.module}'")
        elif isinstance(n, ast.Name) and n.id in BANNED_NAMES:
            probs.append(f"dòng {n.lineno}: không được dùng '{n.id}'")
        elif isinstance(n, ast.Attribute):
            if n.attr.startswith("__"): probs.append(f"dòng {n.lineno}: không được dùng thuộc tính '{n.attr}'")
            if n.attr in BANNED_ATTRS: probs.append(f"dòng {n.lineno}: không được dùng '.{n.attr}'")
            d = _dotted(n)
            if d.startswith("bpy.ops.") and d.count(".") >= 3 and not d.startswith(ALLOWED_OPS):
                probs.append(f"dòng {n.lineno}: không được gọi '{d}' (chỉ bpy.ops.mesh.primitive_*, object.shade_*)")
            if d.startswith(("bpy.app", "bpy.utils", "bpy.context.preferences", "bpy.context.window")):
                probs.append(f"dòng {n.lineno}: không được dùng '{d}'")
    if not any(isinstance(n, ast.FunctionDef) and n.name == "build" for n in tree.body):
        probs.append("thiếu hàm build(params, lib) ở cấp module")
    return sorted(set(probs))


# =====================================================================
#  Blender runs (thumbnails / review renders / builder previews)
# =====================================================================
def run_blender(script, args, timeout=1800):
    b = blender_cmd()
    if os.path.basename(b).lower().startswith("python"):       # a python with the bpy module (cloud tests)
        cmd = [b, os.path.join(ROOT, "tools", "bpy_run.py"), script] + list(args)
    else:
        cmd = [b, "-b", "--factory-startup", "-P", script, "--"] + list(args)
    p = _popen_run(cmd, timeout, cwd=ROOT)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def render_views(kind, name, params=None, tag=""):
    """-> (image paths, error text or None); tag puts review images in _review/<tag>/ (fresh names each round)"""
    args = [f"{kind}/{name}", "--views", "--size", "512"] + (["--tag", tag] if tag else [])
    if params: args += ["--params", json.dumps(params)]
    code, log = run_blender(os.path.join(ROOT, "tools", "thumbs.py"), args)
    imgs = [l.split(" -> ", 1)[1].strip() for l in log.splitlines() if l.startswith("THUMB ") and " -> " in l]
    failed = [l for l in log.splitlines() if l.startswith("THUMB FAILED")]
    if failed or not imgs:
        tb = log[log.rfind("Traceback"):] if "Traceback" in log else log[-2500:]
        return imgs, (failed[0] if failed else "no images") + "\n" + tb[-2500:]
    return imgs, None


# =====================================================================
#  prompts
# =====================================================================
def _read(p):
    return open(os.path.join(ROOT, p), encoding="utf-8").read()


def _catalog_text():
    return json.dumps(storycheck.LibIndex().catalog(), ensure_ascii=False, indent=0)


def design_prompt(kind, name, brief, dim=None, feedback=None, current=None):
    lib = storycheck.LibIndex()
    ex = ["library/props/manhole_cover/build.py", "library/props/clipboard/build.py"] if kind == "props" else ["library/sets/office/build.py"]
    examples = "\n\n".join(f"# ---- {p} ----\n{_read(p)}" for p in ex)
    existing = ", ".join(lib.list(kind))
    task = f"""Nhiệm vụ: thiết kế {'đạo cụ' if kind == 'props' else 'bối cảnh'} mới cho thư viện WhyShorts.

Tên thư mục: library/{kind}/{name}/
Mô tả từ người dùng: {brief}
{('Loại: ' + dim + (' (rơi/lăn/đặt trên đất: dựng 3D bằng khối cơ bản)' if dim == '3d' else ' (cầm tay/đội đầu/sơ đồ: vẽ 2D trong mặt phẳng XY)')) if dim else ''}
Đồ đã có trong thư viện (đừng làm trùng): {existing}

Viết build.py theo đúng API dưới đây. Dùng khối cơ bản và vật liệu của core; đặt tên vật liệu theo tên đồ vật
(ví dụ "{name}_body") để không đụng vật liệu sẵn có. Gốc tọa độ ở tâm đáy (3D). Tỉ lệ: nhân vật cao khoảng 2,5 đơn vị.
Đưa các lựa chọn hữu ích ra params (màu, trạng thái, nhãn chữ...) kèm mặc định. parts = tên các object con mà story
có thể muốn animate; object con tên đúng f"{{name}}_<phần>". Nếu mô tả có "parts: a, b" thì PHẢI tạo đúng các phần đó. Có thể đọc core/geo.py, core/look.py hoặc đồ khác trong library/ nếu cần.

=== library/AUTHORING.md ===
{_read('library/AUTHORING.md')}

=== Ví dụ ===
{examples}
"""
    if current:
        task += f"\n=== build.py hiện tại ===\n{current}\n"
    if feedback:
        task += f"\nNgười dùng muốn sửa: {feedback}\nGiữ những gì đang tốt, chỉ đổi theo yêu cầu. Trả lại build.py đầy đủ.\n"
    return task


REVIEW_PROMPT = """Đây là ảnh render của {what} bạn vừa viết (build.py ở trên). Dùng công cụ Read để XEM từng ảnh:
{images}

Ảnh 'scale.png' đặt đồ vật cạnh nhân vật Joe (cao khoảng 2,5) để so tỉ lệ{scale_note}. Kiểm tra:
1. Nhìn một giây có nhận ra đúng là "{brief_short}" không? Hình khối có rõ trên màn hình điện thoại không?
2. Tỉ lệ so với nhân vật có hợp lý (theo phong cách hoạt hình, hơi phóng đại cho dễ nhìn)?
3. Các phần có ghép đúng chỗ không (không lơ lửng, không xuyên nhau sai, không lật ngược, không thiếu mặt)?
4. Màu sắc bão hòa, tương phản, hợp phong cách; viền mực rõ; không có chữ hay logo thương hiệu thật.
5. Đứng đúng trên mặt đất (3D: đáy ở z=0)?

Nếu đã tốt: ok=true, build_py=null. Nếu có lỗi đáng sửa: ok=false, liệt kê problems và trả build_py ĐẦY ĐỦ đã sửa.
Đừng sửa vụn vặt chỉ để sửa. summary_vi: 1-2 câu tiếng Việt mô tả kết quả cho người dùng."""


# =====================================================================
#  design jobs
# =====================================================================
def _write_item(kind, name, data, brief, status="draft", review=None):
    d = os.path.join(LIB, kind, name); os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "build.py"), "w", encoding="utf-8").write(data["build_py"].rstrip() + "\n")
    meta = {"kind": kind[:-1], "name": name, "title_vi": data["title_vi"], "description_vi": data["description_vi"]}
    for k in ("dim", "params", "parts", "space", "anchors", "views", "tags", "notes_vi"):
        if k in data: meta[k] = data[k]
    meta.update(status=status, brief_vi=brief, designed_by="claude_bridge",
                updated=datetime.datetime.now().isoformat(timespec="seconds"))
    if review: meta["review"] = review
    json.dump(meta, open(os.path.join(d, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return d


def design_item(kind, name, brief=None, dim=None, feedback=None, model=None):
    """design (or revise with feedback) a prop or set; returns a report dict"""
    if not re.fullmatch(r"[a-z][a-z0-9_]{1,40}", name): raise BridgeError("tên chỉ gồm chữ thường, số, gạch dưới")
    d = os.path.join(LIB, kind, name)
    current = open(os.path.join(d, "build.py"), encoding="utf-8").read() if feedback and os.path.exists(os.path.join(d, "build.py")) else None
    old_meta = storycheck.LibIndex().meta(kind, name) if current else {}
    brief = brief or old_meta.get("brief_vi") or old_meta.get("description_vi") or name
    dim = dim or old_meta.get("dim")
    if not feedback and os.path.exists(os.path.join(d, "build.py")) and old_meta.get("designed_by") != "claude_bridge":
        raise BridgeError(f"library/{kind}/{name} đã có (không phải do bridge tạo); chọn tên khác")
    job = "design_prop" if kind == "props" else "design_set"
    schema = load_schema(job)
    report = {"item": f"{kind}/{name}", "rounds": []}
    t0 = time.time()
    data, info = call(job, design_prompt(kind, name, brief, dim, feedback, current), schema, project=f"{kind}/{name}",
                      model=model, check=lambda x: check_build_py(x["build_py"], kind))
    session = info["session"]; cost = info["cost_usd"]
    if kind == "props" and dim: data["dim"] = dim
    _write_item(kind, name, data, brief)
    for rnd in range(MAX_FIX + 1):
        # 1) render; build errors go back to Claude
        tag = f"r{rnd + 1}"
        imgs, err = render_views(kind, name, tag=tag)
        fix_build = 0
        while err and fix_build < MAX_FIX:
            fix_build += 1
            say(f"  [{job}] lỗi khi dựng trong Blender -> gửi lại cho Claude sửa ({fix_build}/{MAX_FIX})")
            data2, info2 = call(job, f"build.py chạy lỗi trong Blender:\n{err}\nSửa lỗi và trả lại JSON đầy đủ.", schema,
                                project=f"{kind}/{name}", model=model, resume=session,
                                check=lambda x: check_build_py(x["build_py"], kind))
            cost += info2["cost_usd"]; data = data2
            if kind == "props" and dim: data["dim"] = dim
            _write_item(kind, name, data, brief)
            tag = f"r{rnd + 1}b{fix_build}"; imgs, err = render_views(kind, name, tag=tag)
        if err:
            report.update(ok=False, error=err[-1500:]); break
        report["images"] = [os.path.relpath(p, ROOT) for p in imgs]
        if rnd == MAX_FIX:
            report["rounds"].append({"note": "hết số vòng xem lại"}); break
        # 2) Claude looks at its own renders
        rel = "\n".join(f"- {p}" for p in imgs if os.sep + "_review" + os.sep in p)
        rv_prompt = REVIEW_PROMPT.format(what="đạo cụ" if kind == "props" else "bối cảnh", images=rel,
                                         brief_short=brief[:80], scale_note=" (đạo cụ 2D: Joe cầm trên tay)" if data.get("dim") == "2d" else "")
        rv, info3 = call("review", rv_prompt, load_schema("review"), project=f"{kind}/{name}", model=model, resume=session,
                         check=lambda x: check_build_py(x["build_py"], kind) if x.get("build_py") else [])
        cost += info3["cost_usd"]
        report["rounds"].append({"score": rv["score"], "ok": rv["ok"], "problems": rv["problems"], "summary_vi": rv["summary_vi"]})
        say(f"  [review {rnd + 1}] {rv['score']}/10 ok={rv['ok']}: {rv['summary_vi']}")
        if rv["ok"] or not rv.get("build_py"):
            break
        data = dict(data, build_py=rv["build_py"])
        _write_item(kind, name, data, brief)
    scored = [r for r in report["rounds"] if "score" in r]
    final = scored[-1] if scored else {}
    report.update(ok=report.get("ok", True), seconds=round(time.time() - t0, 1), cost_usd_list_price=round(cost, 3), session=session)
    _write_item(kind, name, data, brief, review={"score": final.get("score"), "summary_vi": final.get("summary_vi"),
                                                 "problems": final.get("problems", [])})
    json.dump(report, open(os.path.join(d, "_review", "report.json") if os.path.isdir(os.path.join(d, "_review")) else os.path.join(d, "report.json"),
                           "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return report


def check_char_json(cj):
    """structure check for a character config -> problems"""
    probs = []
    mats = cj.get("materials", {})
    for k, v in mats.items():
        if not (isinstance(v, list) and len(v) == 3 and all(isinstance(c, (int, float)) and 0 <= c <= 1 for c in v)):
            probs.append(f"materials.{k}: cần [r, g, b] trong khoảng 0-1")
    cfg = cj.get("cfg", {})
    for key, n in (("leg", 3), ("torso", 3), ("arm", 4), ("head", 2)):
        if not (isinstance(cfg.get(key), list) and len(cfg[key]) == n): probs.append(f"cfg.{key}: cần {n} phần tử")
    if isinstance(cfg.get("torso"), list) and len(cfg["torso"]) == 3 and cfg["torso"][2] not in mats:
        probs.append("cfg.torso[2] phải là tên một vật liệu trong materials")
    faces = cj.get("faces", [])
    bad = [f for f in faces if f not in storycheck.FACES]
    if bad: probs.append(f"faces không hợp lệ {bad}; chọn trong {list(storycheck.FACES)}")
    if len(faces) < 4: probs.append("cần ít nhất 4 biểu cảm (bình thường, vui, nhếch mép/nháy mắt, tức/sốc)")
    for i, op in enumerate(cj.get("extras", [])):
        if op.get("op") not in ("shape", "stroke", "disc"): probs.append(f"extras[{i}].op phải là shape/stroke/disc")
        if op.get("on") not in ("torso", "head"): probs.append(f"extras[{i}].on phải là torso hoặc head")
        if op.get("mat") and op["mat"] not in mats: probs.append(f"extras[{i}].mat '{op['mat']}' không có trong materials")
        for k in ("name", "z"):
            if k not in op: probs.append(f"extras[{i}]: thiếu '{k}'")
        if op.get("op") in ("shape", "stroke") and "pts" not in op: probs.append(f"extras[{i}]: thiếu 'pts'")
        if op.get("op") == "stroke" and "w" not in op: probs.append(f"extras[{i}]: thiếu 'w'")
        if op.get("op") == "disc" and not ("c" in op and "r" in op): probs.append(f"extras[{i}]: disc cần 'c' và 'r'")
        if isinstance(op.get("pts"), dict) and list(op["pts"])[0] not in ("rrect", "ellipse", "arc", "ring"):
            probs.append(f"extras[{i}].pts: chỉ dùng rrect/ellipse/arc/ring hoặc danh sách điểm")
    return probs


def _write_char(name, data, brief, status="draft", review=None):
    d = os.path.join(LIB, "chars", name); os.makedirs(d, exist_ok=True)
    cj = dict(data["char_json"])
    cj = {"kind": "char", "name": name, "title_vi": data["title_vi"], "description_vi": data["description_vi"], **cj,
          "tags": data.get("tags", []), "status": status, "brief_vi": brief, "designed_by": "claude_bridge",
          "updated": datetime.datetime.now().isoformat(timespec="seconds")}
    if review: cj["review"] = review
    json.dump(cj, open(os.path.join(d, "char.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def design_char(name, brief=None, feedback=None, model=None):
    if not re.fullmatch(r"[a-z][a-z0-9_]{1,40}", name): raise BridgeError("tên chỉ gồm chữ thường, số, gạch dưới")
    p = os.path.join(LIB, "chars", name, "char.json")
    old = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None
    if old and not feedback and old.get("designed_by") != "claude_bridge":
        raise BridgeError(f"library/chars/{name} đã có; chọn tên khác")
    brief = brief or (old or {}).get("brief_vi") or name
    ex = "\n\n".join(f"# ---- library/chars/{n}/char.json ----\n{_read(f'library/chars/{n}/char.json')}" for n in ("joe", "gary"))
    prompt = (f"Thiết kế nhân vật 2D mới cho WhyShorts, tên '{name}'. Mô tả: {brief}\n"
              "Theo luật thiết kế nhân vật trong STYLE.md (đầu tròn, thân bo góc, một món đồ nhận diện, màu riêng đậm). "
              "char_json gồm materials (tên duy nhất có tiền tố tên nhân vật), cfg (leg [hipY, L1, L2], torso [w, h, tên vật liệu], "
              "arm [shX, shY, L1, L2], head [y, r], tùy chọn eye_y), faces (≥ 4, chọn trong danh sách 10 biểu cảm), extras "
              "(lệnh vẽ shape/stroke/disc lên torso/head, toạ độ 2D, z để xếp lớp; pts là danh sách điểm hoặc {rrect|ellipse|arc|ring: [...]}). "
              f"Nhân vật đã có: {', '.join(storycheck.LibIndex().list('chars'))} — phải khác hẳn về màu và món đồ.\n\n{ex}")
    if old and feedback:
        prompt += f"\n\n=== char.json hiện tại ===\n{json.dumps(old, ensure_ascii=False)}\nNgười dùng muốn sửa: {feedback}"
    report = {"item": f"chars/{name}", "rounds": []}; t0 = time.time()
    data, info = call("design_char", prompt, load_schema("design_char"), project=f"chars/{name}", model=model,
                      check=lambda x: check_char_json(x["char_json"]))
    session, cost = info["session"], info["cost_usd"]
    _write_char(name, data, brief)
    for rnd in range(MAX_FIX + 1):
        imgs, err = render_views("chars", name, tag=f"r{rnd + 1}")
        if err:
            data2, info2 = call("design_char", f"Dựng nhân vật lỗi trong Blender:\n{err}\nSửa và trả lại JSON đầy đủ.", load_schema("design_char"),
                                project=f"chars/{name}", model=model, resume=session, check=lambda x: check_char_json(x["char_json"]))
            cost += info2["cost_usd"]; data = data2; _write_char(name, data, brief); continue
        report["images"] = [os.path.relpath(x, ROOT) for x in imgs]
        if rnd == MAX_FIX: break
        rel = "\n".join(f"- {x}" for x in imgs if os.sep + "_review" + os.sep in x)
        rv, info3 = call("review", f"Đây là ảnh render nhân vật bạn vừa thiết kế (dáng đứng và từng biểu cảm). Dùng Read để xem:\n{rel}\n"
                         "Kiểm tra: dễ nhận ra, đúng phong cách, món đồ nhận diện rõ, các phần ghép đúng chỗ, mỗi biểu cảm đọc được. "
                         "Nếu cần sửa: ok=false, problems, và char_json ĐẦY ĐỦ đã sửa (build_py=null). summary_vi 1-2 câu.",
                         load_schema("review"), project=f"chars/{name}", model=model, resume=session,
                         check=lambda x: check_char_json(x["char_json"]) if x.get("char_json") else [])
        cost += info3["cost_usd"]
        report["rounds"].append({"score": rv["score"], "ok": rv["ok"], "problems": rv["problems"], "summary_vi": rv["summary_vi"]})
        say(f"  [review {rnd + 1}] {rv['score']}/10 ok={rv['ok']}: {rv['summary_vi']}")
        if rv["ok"] or not rv.get("char_json"): break
        data = dict(data, char_json=rv["char_json"]); _write_char(name, data, brief)
    final = ([r for r in report["rounds"] if "score" in r] or [{}])[-1]
    _write_char(name, data, brief, review={"score": final.get("score"), "summary_vi": final.get("summary_vi"), "problems": final.get("problems", [])})
    report.update(ok="images" in report, seconds=round(time.time() - t0, 1), cost_usd_list_price=round(cost, 3))
    return report


def approve(item):
    kind, name = item.split("/")
    p = os.path.join(LIB, kind, name, "char.json" if kind == "chars" else "meta.json")
    m = json.load(open(p, encoding="utf-8")); m["status"] = "approved"
    m["approved"] = datetime.datetime.now().isoformat(timespec="seconds")
    json.dump(m, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return m


# =====================================================================
#  content jobs (used by the control page in step 4)
# =====================================================================
def _project_dir(slug):
    d = os.path.join(ROOT, "projects", slug); os.makedirs(d, exist_ok=True); return d


def _save_versioned(slug, fname, data):
    d = _project_dir(slug); p = os.path.join(d, fname)
    if os.path.exists(p):
        hist = os.path.join(d, "history"); os.makedirs(hist, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        shutil.copy(p, os.path.join(hist, f"{fname[:-5]}_{stamp}.json"))
    json.dump(data, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return p


def ideas(slug, topic=None, count=10, model=None):
    prompt = (f"Đề xuất {count} ý tưởng video 'Why…' theo mục Ý tưởng trong STYLE.md"
              + (f" xoay quanh chủ đề: {topic}." if topic else ".")
              + " Đào 25-30 ứng viên rồi lọc; chỉ giữ ý từ 8/10. Tra web để kiểm chứng sự thật chính (ghi nguồn trong facts)."
              + f"\nThư viện hiện có (ưu tiên ý dùng lại được):\n{_catalog_text()}")
    data, info = call("ideas", prompt, load_schema("ideas"), project=slug, model=model)
    _save_versioned(slug, "ideas.json", data)
    return data


def write_content(slug, idea, minutes=1.0, model=None):
    words = int(round(minutes * 150))
    n_seq = max(4, min(7, int(round(minutes * 6)))) if minutes <= 1.25 else int(round(minutes * 5.5))
    prompt = (f"Viết content cho ý tưởng sau (JSON):\n{json.dumps(idea, ensure_ascii=False)}\n\n"
              f"Độ dài: {minutes} phút ≈ {words} từ lời đọc tiếng Anh (±10 %), khoảng {n_seq} chuỗi máy"
              + (" chia thành chương, mỗi chương 4-7 chuỗi" if minutes > 1.25 else "") + ".\n"
              "Theo STYLE.md: lời đọc, bản dịch Việt, bảng chuỗi máy (mỗi chuỗi: lời đọc của chuỗi, hành động, bối cảnh, đạo cụ, "
              "nhân vật, biểu cảm, gag, tiếng động, hiệu ứng, cách chuyển cảnh, đường đi camera, chữ nhấn). "
              "Kiểm chứng sự thật bằng web, ghi nguồn. library_needs: đồ chưa có trong thư viện cần thiết kế. "
              "Mỗi món mới tốn vài phút và một lượt Claude: ưu tiên dùng lại thư viện (tham số, đổi màu), gộp đồ trang trí vào "
              "bối cảnh, bỏ đồ phụ không cần cho gag; tối đa khoảng 5 món mới cho 1 phút video.\n"
              f"Thư viện hiện có:\n{_catalog_text()}")
    data, info = call("write_content", prompt, load_schema("content"), project=slug, model=model,
                      check=lambda x: [] if abs(len(x["vo_en"].split()) - words) <= max(25, words * 0.2)
                      else [f"lời đọc có {len(x['vo_en'].split())} từ, cần khoảng {words}"])
    _save_versioned(slug, "content.json", data)
    return data


def rewrite_seq(slug, index, request, model=None):
    d = _project_dir(slug); content = json.load(open(os.path.join(d, "content.json"), encoding="utf-8"))
    prompt = (f"Content hiện tại:\n{json.dumps(content, ensure_ascii=False)}\n\nViết lại CHỈ chuỗi id={index} theo yêu cầu: {request}\n"
              "Giữ mạch truyện và độ dài tổng gần như cũ. Trả chuỗi mới và toàn bộ lời đọc EN/VI sau khi thay.")
    data, info = call("rewrite_seq", prompt, load_schema("sequence"), project=slug, model=model)
    for i, s in enumerate(content["sequences"]):
        if s["id"] == index: content["sequences"][i] = data["sequence"]
    content["vo_en"], content["vo_vi"] = data["vo_en"], data["vo_vi"]
    content["word_count"] = len(data["vo_en"].split())
    _save_versioned(slug, "content.json", content)
    return data


PLAN_RULES = """
Luật khi viết story.json:
- Phủ trọn meta.frames: camera v3 gồm các seqs liền nhau từ khung 1 tới khung cuối. Mỗi seq dài ít nhất 90 khung
  (cam_report báo lỗi nếu ngắn hơn); khóa camera cách nhau ít nhất 20 khung, đi chậm và đều (gia tốc < 4 mm/khung²);
  trans có kiểu whip/push/match/cut tại khung đầu seq sau. Punch [khung, hệ số, dur, hold]; shakes [khung, 0.5-1.5, 8-14].
- Mốc thời gian lấy từ words (giây × 30 + 1 = khung). Hành động, biểu cảm, tiếng động rơi đúng vào chữ nhấn.
- Nhân vật cao khoảng 2,5 đơn vị và đứng trên mặt đất z = 0. Bối cảnh chính ở gốc tọa độ, bảng sơ đồ ở x = 500
  (camera cách bảng 7,7, lens 45, đặt captions.lift khi đang chiếu bảng).
- Thẻ chữ trên màn hình (thẻ tên, "10 MINUTES EARLIER", "TEST 1", thẻ chương, "REPLAY", nhãn số đo, dấu ✗/✓,
  bong bóng tưởng tượng, iris-out kết video) đặt trong `cards` (xem STORY.md); tránh vùng phụ đề y ≈ -0,2.
- Hiệu ứng builder chưa có thì làm xấp xỉ:
  - slow-mo/REPLAY/tua ngược: track chạy chậm hoặc ngược trên cùng vật, kèm thẻ "REPLAY";
  - freeze-frame: giữ nguyên tư thế và vị trí, camera vẫn trôi nhẹ;
  - chia đôi màn hình: hai sơ đồ đặt cạnh nhau trên diagram_board;
  - vệt mờ, VHS, lấp lánh: bỏ qua, hoặc thay bằng thẻ hoặc bụi.
  Đừng bịa thêm trường ngoài schema.
- Đồ cầm tay 2D gắn vào nhân vật (props của char, on torso/head). Đồ 3D rơi/lăn/nằm đất nằm trong props của set,
  chuyển động bằng tracks (có thể dùng motions có sẵn) và visibility để đổi 2D↔3D đúng khung hành động.
- Tên object: id của đồ là tên gốc; phần con của đồ là "<id>_<phần>". Với đồ của thư viện, chỉ nhắm các phần có trong
  'parts' của nó. Với đồ mới, ghi rõ trong brief của missing: "parts: crate, chair", để lúc thiết kế đặt đúng tên.
- missing chỉ gồm tên CHƯA có trong thư viện. Muốn biến thể của đồ có sẵn thì dùng params của nó; nếu không đủ
  thì đặt một tên mới (ví dụ gary_sneakers) rồi đưa vào missing. Không đưa tên đã có vào missing.
  Giữ số món mới ít nhất có thể: gộp đồ trang trí vào bối cảnh, bỏ đồ phụ không cần cho gag.
- Biểu cảm chỉ dùng mặt có trong faces của nhân vật đó (xem catalog).
"""


def plan_shots(slug, model=None):
    d = _project_dir(slug)
    content = json.load(open(os.path.join(d, "content.json"), encoding="utf-8"))
    words = json.load(open(os.path.join(d, "words.json"), encoding="utf-8"))
    story_schema = json.load(open(os.path.join(ROOT, "story.schema.json"), encoding="utf-8"))
    defs = story_schema.pop("$defs"); [story_schema.pop(k, None) for k in ("$schema", "$id")]
    schema = {"type": "object", "$defs": defs, "additionalProperties": False, "required": ["story", "missing"],
              "properties": {"story": story_schema, "missing": {"type": "array", "items": {
                  "type": "object", "required": ["kind", "name", "brief"], "additionalProperties": False,
                  "properties": {"kind": {"enum": ["sets", "props", "chars"]}, "name": {"type": "string"}, "brief": {"type": "string"}}}}}}
    frames = int(round((words["duration"] + 1.2) * 30)) if "duration" in words else None
    prompt = (f"Chuyển content đã duyệt thành story.json (đọc STORY.md; mẫu: projects/demo-v3/story.json và projects/manhole-round/story.json).\n"
              f"Dùng camera rig 'v3'. Thời gian từ (words, giây): {json.dumps(words['words'], ensure_ascii=False)}\n"
              + (f"meta.frames = {frames}.\n" if frames else "")
              + f"Content:\n{json.dumps(content, ensure_ascii=False)}\n\nThư viện:\n{_catalog_text()}\n"
              + PLAN_RULES)

    def check(x):
        pend = {(m["kind"], m["name"]) for m in x["missing"]}
        return storycheck.check_story(x["story"], pending=pend)
    data, info = call("plan_shots", prompt, schema, project=slug, model=model, check=check)
    _save_versioned(slug, "story.json", data["story"])
    return data


def _pointer(doc, path):
    parts = [p.replace("~1", "/").replace("~0", "~") for p in path.lstrip("/").split("/")]
    cur = doc
    for p in parts[:-1]: cur = cur[int(p)] if isinstance(cur, list) else cur[p]
    return cur, parts[-1]


def apply_patch(doc, changes):
    doc = json.loads(json.dumps(doc))
    for c in changes:
        parent, key = _pointer(doc, c["path"])
        if isinstance(parent, list):
            i = len(parent) if key == "-" else int(key)
            if c["op"] == "delete": parent.pop(i)
            elif c["op"] == "insert": parent.insert(i, c["value"])
            else: parent[i] = c["value"]
        else:
            if c["op"] == "delete": parent.pop(key, None)
            else: parent[key] = c["value"]
    return doc


def fix_from_preview(slug, problem, images, model=None):
    d = _project_dir(slug); story = json.load(open(os.path.join(d, "story.json"), encoding="utf-8"))
    prompt = (f"Ảnh xem trước (dùng Read để xem): \n" + "\n".join(f"- {p}" for p in images)
              + f"\nVấn đề người dùng thấy: {problem}\n\nstory.json hiện tại:\n{json.dumps(story, ensure_ascii=False)}\n"
              "Trả về các thay đổi nhỏ nhất (JSON pointer) để sửa.")

    def check(x):
        try: return storycheck.check_story(apply_patch(story, x["changes"]))
        except Exception as e: return [f"không áp được patch: {e}"]
    data, info = call("fix_from_preview", prompt, load_schema("patch"), project=slug, model=model, check=check)
    _save_versioned(slug, "story.json", apply_patch(story, data["changes"]))
    return data


# =====================================================================
#  CLI
# =====================================================================
def main(argv):
    if not argv or argv[0] in ("-h", "--help"): print(__doc__); return 0
    job, rest = argv[0], argv[1:]
    opt = {}; i = 0
    while i < len(rest):
        if rest[i].startswith("--"): opt[rest[i][2:]] = rest[i + 1] if i + 1 < len(rest) else ""; i += 2
        else: i += 1
    pos = []; i = 0
    while i < len(rest):
        if rest[i].startswith("--"): i += 2
        else: pos.append(rest[i]); i += 1
    try:
        if job in ("design_prop", "design_set"):
            kind = "props" if job == "design_prop" else "sets"
            r = design_item(kind, pos[0], pos[1] if len(pos) > 1 else opt.get("brief"), dim=opt.get("dim"),
                            feedback=opt.get("feedback"), model=opt.get("model"))
            print(json.dumps(r, ensure_ascii=False, indent=1))
        elif job == "design_char":
            print(json.dumps(design_char(pos[0], pos[1] if len(pos) > 1 else opt.get("brief"), feedback=opt.get("feedback"),
                                         model=opt.get("model")), ensure_ascii=False, indent=1))
        elif job == "approve": print(json.dumps(approve(pos[0]), ensure_ascii=False, indent=1))
        elif job == "usage": print(json.dumps(usage(), ensure_ascii=False, indent=1))
        elif job == "ideas": print(json.dumps(ideas(opt.get("project", "ideas"), opt.get("topic"), model=opt.get("model")), ensure_ascii=False, indent=1))
        elif job == "check_build": print(check_build_py(open(pos[0], encoding="utf-8").read()) or "OK")
        else: print(f"chưa hỗ trợ từ dòng lệnh: {job} (dùng qua server.py ở bước 4)"); return 2
    except BridgeError as e:
        print("LỖI:", e); return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
