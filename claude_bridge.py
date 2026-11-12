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
import ast, datetime, json, math, os, re, shutil, subprocess, sys, threading, time

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
             "design_culture": WEB_TOOLS + ["Read"], "youtube_package": WEB_TOOLS + ["Read"], "review_thumbs": READ_TOOLS, "design_outfit": READ_TOOLS, "review_outfit": READ_TOOLS,
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


def cli_schema(schema):
    """Schema passed to `claude --json-schema`.  The CLI checks it with Ajv in draft-07 strict mode (no
    prefixItems) while the API behind it requires valid draft 2020-12 (no array-form items), so no tuple
    syntax satisfies both: tuples are relaxed to 'each item is one of these schemas'.  The exact tuple
    shape is still enforced by our own validation (jsonval) and fed back to Claude when wrong."""
    if isinstance(schema, list): return [cli_schema(x) for x in schema]
    if not isinstance(schema, dict): return schema
    out = {k: cli_schema(v) for k, v in schema.items() if k not in ("$schema", "$id")}
    if "prefixItems" in out:
        opts = out.pop("prefixItems") + ([out.pop("items")] if "items" in out else [])
        uniq = []
        for o in opts:
            if o not in uniq: uniq.append(o)
        out["items"] = uniq[0] if len(uniq) == 1 else {"anyOf": uniq}
    return out


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
    if use_schema: cmd += ["--json-schema", json.dumps(cli_schema(schema), ensure_ascii=False)]
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
        if kind == "sets":       # sets have view0..N camera shots, no scale.png
            rv_prompt = rv_prompt.replace("Ảnh 'scale.png' đặt đồ vật cạnh nhân vật Joe (cao khoảng 2,5) để so tỉ lệ.",
                                          "Bối cảnh không có ảnh scale.png; các ảnh view0, view1… là góc máy gợi ý (nhân vật cao khoảng 2,5).")
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
        if op.get("on") not in ("torso", "head", "footL", "footR"): probs.append(f"extras[{i}].on phải là torso, head, footL hoặc footR")
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
              "arm [shX, shY, L1, L2], head [y, r], tùy chọn eye_y, tùy chọn shoe {mat, rx, ry, dx, outline} để đổi giày "
              "(mặc định: elip đen 0,13 × 0,065)), faces (≥ 4, chọn trong danh sách 10 biểu cảm), extras "
              "(lệnh vẽ shape/stroke/disc lên torso/head/footL/footR — footL/footR đi theo chân, toạ độ tính từ tâm bàn chân; toạ độ 2D, z để xếp lớp; pts là danh sách điểm hoặc {rrect|ellipse|arc|ring: [...]}). "
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


# =====================================================================
#  cultures + outfits (long-form, several nations)
# =====================================================================
OUTFIT_ONS = {"torso", "head", "footL", "footR", "handL", "handR"}
SLOTS = {"team", "team_dark", "cloth", "cloth2", "metal", "metal_dark", "leather", "trim", "hair", "accent", "ink", "white", "skin"}


def _pts_ok(pts):
    if isinstance(pts, dict):
        if len(pts) != 1: return False
        (k, a), = pts.items()
        return k in ("rrect", "ellipse", "arc", "ring") and isinstance(a, list) and all(isinstance(x, (int, float)) for x in a) and len(a) >= 4
    return isinstance(pts, list) and len(pts) >= 2 and all(isinstance(q, list) and len(q) == 2 for q in pts)


def check_outfit_json(o):
    e = []
    if not re.fullmatch(r"[a-z][a-z0-9_]{1,50}", o.get("name", "")): e.append("name: chữ thường, số, gạch dưới")
    for i, op in enumerate(o.get("items", [])):
        w = f"items[{i}] ({op.get('name')})"
        if op.get("on") not in OUTFIT_ONS: e.append(f"{w}: on phải là {sorted(OUTFIT_ONS)}")
        m = op.get("mat", "$cloth")
        if isinstance(m, str) and (not m.startswith("$") or m[1:] not in SLOTS) and m[1:] not in (o.get("palette") or {}):
            e.append(f"{w}: mat '{m}' không phải ô màu ({', '.join('$' + x for x in sorted(SLOTS))}) hay [r,g,b]")
        if op["op"] in ("shape", "stroke") and not _pts_ok(op.get("pts")): e.append(f"{w}: pts sai dạng")
        if op["op"] == "stroke" and not op.get("w"): e.append(f"{w}: stroke cần w")
        if op["op"] == "disc" and not (isinstance(op.get("c"), list) and len(op["c"]) == 2 and op.get("r")): e.append(f"{w}: disc cần c [x,y] và r")
        if op.get("on") == "head" and op["op"] == "shape" and op.get("z", 0.18) > 0.0 and isinstance(op.get("pts"), dict):
            (k, a), = op["pts"].items()
            upper_half = k == "ellipse" and len(a) >= 7 and a[5] >= -0.01 and a[6] <= math.pi + 0.01
            lo = a[1] if upper_half else a[1] - (a[3] if k == "ellipse" else a[3] / 2)
            hi = a[1] + (a[3] if k == "ellipse" else a[3] / 2)
            if k in ("ellipse", "rrect") and abs(a[0]) < 0.25 and lo < -0.05 and hi > -0.35:
                e.append(f"{w}: che mắt/miệng (mắt y≈-0,02, miệng y≈-0,3); đặt mũ/mặt nạ cao hơn hoặc z âm")
    if o.get("torso") and (not o["torso"].startswith("$") or o["torso"][1:] not in SLOTS): e.append("torso: phải là ô màu $...")
    return e


def _write_lib_json(kind, name, fname, data, brief, review=None):
    d = os.path.join(LIB, kind, name); os.makedirs(d, exist_ok=True)
    p = os.path.join(d, fname); old = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
    data = dict(data, kind=kind[:-1], name=name, status="draft", designed_by="claude_bridge", brief_vi=brief,
                created=old.get("created") or datetime.datetime.now().isoformat(timespec="seconds"))
    if review: data["review"] = review
    json.dump(data, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return p


def design_culture(name, brief=None, feedback=None, model=None):
    """research + write library/cultures/<name>/culture.json (draft); -> report with the outfits its roles need"""
    if not re.fullmatch(r"[a-z][a-z0-9_]{1,50}", name): raise BridgeError("tên chỉ gồm chữ thường, số, gạch dưới")
    p = os.path.join(LIB, "cultures", name, "culture.json")
    old = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None
    brief = brief or (old or {}).get("brief_vi") or name
    doc = _read("library/OUTFITS.md")
    prompt = (f"Nghiên cứu (dùng web, ưu tiên nguồn học thuật/bảo tàng) và viết hồ sơ VĂN HÓA '{name}' cho thư viện WhyShorts: {brief}\n"
              "Mục đích: vẽ trang phục, màu, cờ, kiến trúc đúng sử liệu cho video hoạt hình 2D. Ghi nguồn cho các điểm chính và nói rõ điểm còn tranh cãi.\n"
              "roles: các vai sẽ xuất hiện (soldier, officer, commoner, noble, priest... chỉ các vai có thật ở văn hóa này) → id trang phục dạng "
              f"'<tên ngắn>_<vai>_<thời kỳ>' (ví dụ roman_legionary_50ad); role_briefs_vi: mỗi id một mô tả trang phục chi tiết, đúng sử liệu, đủ để vẽ.\n"
              "Màu là emission tuyến tính: phải đậm, bão hòa. skin_tones là dải màu da thật (chỉ dùng khi story bật), hair_colors thật.\n"
              f"Văn hóa đã có: {', '.join(storycheck.LibIndex().list('cultures'))}\n\n=== library/OUTFITS.md ===\n{doc}\n\n"
              f"=== Ví dụ: library/cultures/roman_empire_50ad/culture.json ===\n{_read('library/cultures/roman_empire_50ad/culture.json')}")
    if old and feedback: prompt += f"\n\n=== culture.json hiện tại ===\n{json.dumps(old, ensure_ascii=False)}\nNgười dùng muốn sửa: {feedback}"
    t0 = time.time()
    data, info = call("design_culture", prompt, load_schema("design_culture"), project=f"cultures/{name}", model=model)
    cj = dict(data["culture_json"], name=name)
    _write_lib_json("cultures", name, "culture.json", cj, brief)
    need = [o for o in cj["roles"].values() if not os.path.exists(os.path.join(LIB, "outfits", o, "outfit.json"))]
    return {"item": f"cultures/{name}", "ok": True, "roles": cj["roles"], "outfits_needed": need,
            "role_briefs_vi": cj.get("role_briefs_vi", {}), "seconds": round(time.time() - t0, 1), "cost_usd_list_price": info["cost_usd"]}


def render_lineup(name, compare=(), tag="r1"):
    out = os.path.join(LIB, "outfits", name, "_review", tag)
    code, log = run_blender(os.path.join(ROOT, "tools", "lineup.py"), [out, name] + list(compare))
    imgs = [os.path.join(out, f) for f in ("lineup.png", "silhouette.png") if os.path.exists(os.path.join(out, f))]
    if "LINEUP ->" not in log or len(imgs) < 2:
        tb = log[log.rfind("Traceback"):] if "Traceback" in log else log[-2500:]
        return imgs, tb[-2500:]
    return imgs, None


def design_outfit(name, brief=None, culture=None, compare=(), feedback=None, model=None):
    """write library/outfits/<name>/outfit.json, render a line-up next to Joe and the outfits it must differ from
    (compare = other outfit ids in the video), let Claude look and fix (max MAX_FIX rounds)"""
    if not re.fullmatch(r"[a-z][a-z0-9_]{1,50}", name): raise BridgeError("tên chỉ gồm chữ thường, số, gạch dưới")
    p = os.path.join(LIB, "outfits", name, "outfit.json")
    old = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None
    culture = culture or (old or {}).get("culture")
    if not culture: raise BridgeError("cần culture (văn hóa) cho trang phục")
    cul_p = os.path.join(LIB, "cultures", culture, "culture.json")
    if not os.path.exists(cul_p): raise BridgeError(f"chưa có văn hóa {culture} (thiết kế văn hóa trước)")
    cul = json.load(open(cul_p, encoding="utf-8"))
    brief = brief or (old or {}).get("brief_vi") or cul.get("role_briefs_vi", {}).get(name) or name
    role = next((r for r, o in cul.get("roles", {}).items() if o == name), (old or {}).get("role") or "soldier")
    compare = [c for c in compare if c != name and os.path.exists(os.path.join(LIB, "outfits", c.split(":")[0], "outfit.json"))]
    prompt = (f"Thiết kế TRANG PHỤC '{name}' (vai '{role}' của văn hóa '{culture}') cho nhân vật 2D WhyShorts: {brief}\n"
              "Đúng sử liệu theo culture.json bên dưới (không lẫn đồ thời kỳ/nước khác); khối to rõ, ít chi tiết vụn; phần nhận diện phe dùng $team. "
              + (f"Phải khác rõ (bóng đen, dáng mũ/khiên/vũ khí) với: {', '.join(compare)}.\n" if compare else "\n")
              + f"=== library/OUTFITS.md ===\n{_read('library/OUTFITS.md')}\n\n=== culture.json ===\n{json.dumps(cul, ensure_ascii=False)}\n\n"
              f"=== Ví dụ: library/outfits/roman_legionary_50ad/outfit.json ===\n{_read('library/outfits/roman_legionary_50ad/outfit.json')}")
    if old and feedback: prompt += f"\n\n=== outfit.json hiện tại ===\n{json.dumps(old, ensure_ascii=False)}\nNgười dùng muốn sửa: {feedback}"
    report = {"item": f"outfits/{name}", "rounds": []}; t0 = time.time()
    chk = lambda x: check_outfit_json(dict(x["outfit_json"], name=name))
    data, info = call("design_outfit", prompt, load_schema("design_outfit"), project=f"outfits/{name}", model=model, check=chk)
    session, cost = info["session"], info["cost_usd"]
    oj = dict(data["outfit_json"], name=name, culture=culture, role=role)
    _write_lib_json("outfits", name, "outfit.json", oj, brief)
    for rnd in range(MAX_FIX + 1):
        imgs, err = render_lineup(name, compare, tag=f"r{rnd + 1}")
        if err:
            d2, i2 = call("design_outfit", f"Dựng trang phục lỗi trong Blender:\n{err}\nSửa và trả lại JSON đầy đủ.", load_schema("design_outfit"),
                          project=f"outfits/{name}", model=model, resume=session, check=chk)
            cost += i2["cost_usd"]; oj = dict(d2["outfit_json"], name=name, culture=culture, role=role)
            _write_lib_json("outfits", name, "outfit.json", oj, brief); continue
        report["images"] = [os.path.relpath(x, ROOT) for x in imgs]
        if rnd == MAX_FIX: break
        rv, i3 = call("review_outfit", "Ảnh render trang phục bạn vừa thiết kế (dùng Read để xem):\n"
                      + "\n".join(f"- {x}" for x in imgs)
                      + "\nlineup.png: Joe (thước đo) rồi trang phục này" + (", rồi " + ", ".join(compare) if compare else "")
                      + ". silhouette.png: bóng đen cỡ nhỏ.\nKiểm tra: (1) đúng sử liệu, (2) bóng đen phân biệt được với các trang phục khác, "
                      "(3) đúng phong cách (khối to, rõ), (4) các mảnh đúng chỗ, không che mắt/miệng, đồ cầm theo tay. Nếu cần sửa: ok=false và "
                      "outfit_json ĐẦY ĐỦ đã sửa; nếu đạt: outfit_json=null.", load_schema("review_outfit"), project=f"outfits/{name}",
                      model=model, resume=session, check=lambda x: check_outfit_json(dict(x["outfit_json"], name=name)) if x.get("outfit_json") else [])
        cost += i3["cost_usd"]
        report["rounds"].append({k: rv[k] for k in ("score", "ok", "problems", "summary_vi", "accuracy_vi", "silhouette_ok")})
        say(f"  [review {rnd + 1}] {rv['score']}/10 ok={rv['ok']} silhouette={rv['silhouette_ok']}: {rv['summary_vi']}")
        if rv["ok"] or not rv.get("outfit_json"): break
        oj = dict(rv["outfit_json"], name=name, culture=culture, role=role); _write_lib_json("outfits", name, "outfit.json", oj, brief)
    final = (report["rounds"] or [{}])[-1]
    _write_lib_json("outfits", name, "outfit.json", oj, brief, review={k: final.get(k) for k in ("score", "summary_vi", "accuracy_vi", "problems")})
    if report.get("images"):
        try:
            from PIL import Image  # optional: square thumbnail from the line-up
            im = Image.open(os.path.join(ROOT, report["images"][0])); w, h = im.size; x = int(w * (1.5 / (2 + len(compare))))
            im.crop((max(0, x - h // 2), 0, max(0, x - h // 2) + h, h)).resize((512, 512)).save(os.path.join(LIB, "outfits", name, "thumb.png"))
        except Exception:
            shutil.copy(os.path.join(ROOT, report["images"][0]), os.path.join(LIB, "outfits", name, "thumb.png"))
    report.update(ok="images" in report, seconds=round(time.time() - t0, 1), cost_usd_list_price=round(cost, 3))
    return report


# =====================================================================
#  YouTube package (titles, description, tags, thumbnails)
# =====================================================================
YT_RULES = """
Gói YouTube cho video "Why…" (khán giả Mỹ, tiếng Anh):
- titles: 8-12 phương án ≤ 60 ký tự (tối đa 70), mỗi cái một góc khác (câu hỏi Why…, con số, bí ẩn, phản trực giác, 'the real reason');
  không clickbait sai sự thật, không VIẾT HOA cả câu. best_title = chỉ số cái tốt nhất.
- description_hook: 1-2 câu đầu (hiện trên nút 'more'), móc tò mò, có từ khóa chính. description_body: 2-4 câu tóm nội dung, không spoil hết.
  KHÔNG tự viết mốc thời gian: tool tự chèn từ thời gian giọng đọc thật; chỉ trả beat_titles = tên ngắn cho từng chuỗi (id → ≤ 6 từ).
- sources: nguồn đã dùng (giữ từ content, thêm url nếu có). tags: 10-15 tag tiếng Anh (tổng ≤ 450 ký tự), hashtags: 3.
- pinned_comment: một câu hỏi gợi bình luận.
- thumbnails: 3 ý tưởng KHÁC NHAU (layout hero / vs / map / object), dựng bằng chính nhân vật và bối cảnh của video (cast bên dưới):
  - text ≤ 4 từ, chữ to (không lặp nguyên tiêu đề; bổ sung tò mò), đặt ở vùng trống (text_pos), màu vàng/trắng nổi;
  - mặt nhân vật cường điệu (shock, angry, worried, smug_closed…) và pose (arms_up, point_right/left, hands_cheeks, cross_arms, fist_up, shrug);
  - bố cục do tool tự đặt (không cần tọa độ): hero = MỘT nhân vật to ở một bên (x > 0: bên phải), chữ ở nửa kia;
    vs = đúng 2 nhân vật hai phe (tool thêm chữ VS, chữ của bạn nằm dải dưới); map = set bản đồ làm nền (subject = anchor như
    city_roma / arrow0_mid / center), chữ ở dải trên, không nhân vật; object = cận một vật (subject = tên vật/anchor) + arrow: true;
  - grade để đổi không khí; text2 (tùy chọn) = dòng nhỏ ở dưới.
"""


def youtube_package(slug, model=None):
    import youtube
    d = _project_dir(slug); content = json.load(open(os.path.join(d, "content.json"), encoding="utf-8"))
    cs = youtube.cast(slug)
    lib = storycheck.LibIndex()
    cast_txt = {"chars": {k: {"type": v["type"], "faction": v.get("faction"), "outfit": v.get("outfit") or v.get("role"),
                              "faces": (lib.json("chars", v["type"]).get("faces") if lib.exists("chars", v["type"]) else None)} for k, v in cs["chars"].items()},
                "sets": {k: {"type": v["type"], "anchors_hint": "center" + (", city_*/arrow*_mid (map)" if v["type"] == "parchment_map" else "")} for k, v in cs["sets"].items()}}
    seqs = [{"id": q.get("id"), "chapter": q.get("chapter"), "vo_en": q.get("vo_en", "")[:300]} for q in content["sequences"]]
    prompt = (f"Viết gói YouTube cho video '{content.get('title')}'.\n{YT_RULES}\nContent (rút gọn): "
              + json.dumps({"title": content.get("title"), "question": content.get("question"), "chapters": content.get("chapters"),
                            "sequences": seqs, "sources": content.get("sources")}, ensure_ascii=False)
              + f"\n\nCast cho thumbnail (id dùng được):\n{json.dumps(cast_txt, ensure_ascii=False)}")

    def check(x):
        e = []
        for i, t in enumerate(x["titles"]):
            if len(t["title"]) > 70: e.append(f"titles[{i}] dài {len(t['title'])} ký tự (≤ 70)")
        if x["best_title"] >= len(x["titles"]): e.append("best_title ngoài danh sách")
        if sum(len(t) for t in x["tags"]) > 480: e.append("tags quá 480 ký tự")
        for i, th in enumerate(x["thumbnails"]):
            if len(th["text"].replace("\n", " ").split()) > 5: e.append(f"thumbnails[{i}].text quá 5 từ")
            if th.get("set") and th["set"] not in cs["sets"]: e.append(f"thumbnails[{i}].set '{th['set']}' không có (có: {sorted(cs['sets'])})")
            for c in th["chars"]:
                if c["id"] not in cs["chars"]: e.append(f"thumbnails[{i}]: không có nhân vật '{c['id']}'"); continue
                faces = cast_txt["chars"][c["id"]]["faces"]
                if faces and c["expression"] not in faces: e.append(f"thumbnails[{i}]: {c['id']} không có mặt '{c['expression']}' (có {faces})")
        return e
    data, info = call("youtube_package", prompt, load_schema("youtube"), project=slug, model=model, check=check)
    return data


def review_thumbnails(slug, images, concepts, model=None):
    prompt = ("Ba thumbnail 1280x720 tool vừa render cho video (dùng Read để xem):\n" + "\n".join(f"{k + 1}. {p}" for k, p in enumerate(images))
              + f"\nÝ tưởng gốc: {json.dumps(concepts, ensure_ascii=False)}\n"
              "Chấm từng cái (1-10) theo: đọc được ở cỡ nhỏ (điện thoại), chữ không che mặt, mặt cường điệu rõ, bố cục một điểm nhấn, tương phản màu, "
              "gây tò mò. best = cái tốt nhất. Nếu cái tốt nhất còn lỗi dễ sửa (chữ đè mặt, nhân vật bị cắt, mũi tên chỉ sai), trả revised = ý tưởng đã sửa "
              "(cùng dạng), không thì null.")
    data, info = call("review_thumbs", prompt, load_schema("review_thumbs"), project=slug, model=model)
    return data


def approve(item):
    kind, name = item.split("/")
    p = os.path.join(LIB, kind, name, {"chars": "char.json", "cultures": "culture.json", "outfits": "outfit.json"}.get(kind, "meta.json"))
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


def long_rules():
    """LONGFORM_RULES.md: script template + shot vocabulary for long-form jobs"""
    return "\n\n" + open(os.path.join(ROOT, "LONGFORM_RULES.md"), encoding="utf-8").read() + "\n"


LONG_CONTENT_RULES = """
Đây là VIDEO DÀI YouTube 16:9 (không phải Shorts): theo LONGFORM_RULES.md bên dưới (khung kịch bản, lời → kiểu cảnh, nhịp hình).
- Chia chương (chapters); mỗi chuỗi (sequence) là một nhịp kể 20-60 giây, ghi `chapter` và `shots` = danh sách cú máy dự kiến
  (12-16 cắt/phút theo `seconds`), mỗi cú có `type` chọn theo câu lời đọc tương ứng, `what_vi`, và `card_text` khi là màn hình chữ/bản đồ/nhãn.
- Màn hình chữ ở mốc quan trọng khoảng 1 cái mỗi 45-90 giây (shot type card có card_text), đổi kiểu: năm, con số, câu hỏi, trích dẫn, tên, địa danh.
- vo_en tổng phải đúng bằng các vo_en của chuỗi nối lại theo thứ tự.
- Bản đồ (bờ biển thật), sa bàn chiến thuật và giấy sơ đồ tay vẽ đã có sẵn (parchment_map, tactical_board, paper_diagram): dùng chúng cho
  shot map/board/diagram, KHÔNG đưa bản đồ/sa bàn/sơ đồ vào library_needs.
""" + "{RULES}"


def write_content(slug, idea, minutes=1.0, model=None, wpm=190, fmt="short"):
    if fmt == "long": return write_content_long(slug, idea, minutes, model=model, wpm=wpm)
    words = int(round(minutes * wpm))
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


def check_long_content(x, minutes):
    """rhythm of the planned shots: cuts/min, key-moment text screens, variety of shot types"""
    e = []
    secs = sum(q.get("seconds", 0) for q in x["sequences"]) or minutes * 60
    shots = [sh for q in x["sequences"] for sh in q.get("shots", [])]
    cpm = len(shots) / max(secs / 60, 0.1)
    if not 10 <= cpm <= 19: e.append(f"có {len(shots)} cú máy cho {secs:.0f} giây = {cpm:.1f} cắt/phút, cần 12-16 (thêm/bớt shots)")
    cards = [sh for sh in shots if sh["type"] == "card"]
    need = max(2, int(secs / 90))
    if len(cards) < need: e.append(f"chỉ có {len(cards)} màn hình chữ (type card), cần ít nhất {need} (1 cái mỗi 45-90 giây ở mốc quan trọng)")
    if any(not sh.get("card_text") for sh in cards): e.append("mỗi shot type card phải có card_text (chữ hiện trên màn hình)")
    types = {sh["type"] for sh in shots}
    if len(types) < 6: e.append(f"chỉ dùng {len(types)} kiểu cảnh ({sorted(types)}), cần đa dạng hơn (ít nhất 6)")
    return e


def write_content_long(slug, idea, minutes, model=None, wpm=190):
    words = int(round(minutes * wpm)); n_ch = max(2, round(minutes / 3)); n_seq = max(n_ch * 3, round(minutes * 60 / 35))
    prompt = (f"Viết content cho ý tưởng sau (JSON):\n{json.dumps(idea, ensure_ascii=False)}\n\n"
              f"Độ dài: {minutes} phút ≈ {words} từ lời đọc tiếng Anh (±8 %), khoảng {n_ch} chương, {n_seq} chuỗi.\n"
              + LONG_CONTENT_RULES.replace("{RULES}", long_rules()) +
              "Theo STYLE.md cho phong cách nhân vật/bối cảnh. Mỗi chuỗi: lời đọc, bản dịch Việt, hành động, bối cảnh, đạo cụ, nhân vật, "
              "biểu cảm, gag (nếu có), tiếng động, hiệu ứng, chuyển cảnh, đường đi camera, chữ nhấn, shots. Kiểm chứng sự thật bằng web, ghi nguồn. "
              "library_needs: đồ chưa có trong thư viện; ưu tiên dùng lại (tham số, đổi màu), tối đa khoảng 3 món mới mỗi phút.\n"
              f"Thư viện hiện có:\n{_catalog_text()}")

    def check(x):
        e = []
        n = len(x["vo_en"].split())
        if abs(n - words) > max(40, words * 0.12): e.append(f"lời đọc có {n} từ, cần khoảng {words}")
        joined = " ".join(q["vo_en"] for q in x["sequences"]).split()
        if abs(len(joined) - n) > 3: e.append(f"vo_en tổng ({n} từ) khác các vo_en chuỗi nối lại ({len(joined)} từ)")
        chs = {c["n"] for c in x["chapters"]}
        bad = sorted({q["chapter"] for q in x["sequences"]} - chs)
        if bad: e.append(f"chuỗi tham chiếu chương không có: {bad}")
        if [q["chapter"] for q in x["sequences"]] != sorted(q["chapter"] for q in x["sequences"]): e.append("chương của các chuỗi phải tăng dần")
        e += check_long_content(x, minutes)
        return e
    data, info = call("write_content", prompt, load_schema("content_long"), project=slug, model=model, check=check)
    _save_versioned(slug, "content.json", data)
    return data


def rewrite_seq(slug, index, request, model=None):
    d = _project_dir(slug); content = json.load(open(os.path.join(d, "content.json"), encoding="utf-8"))
    prompt = (f"Content hiện tại:\n{json.dumps(content, ensure_ascii=False)}\n\nViết lại CHỈ chuỗi id={index} theo yêu cầu: {request}\n"
              "Giữ mạch truyện và độ dài tổng gần như cũ. Trả chuỗi mới và toàn bộ lời đọc EN/VI sau khi thay."
              + (long_rules() if content.get("format") == "long" else ""))
    schema = load_schema("sequence")
    if content.get("format") == "long":              # long-form sequences also carry chapter + shots
        schema = json.loads(json.dumps(schema)); schema["properties"]["sequence"] = load_schema("content_long")["properties"]["sequences"]["items"]
    data, info = call("rewrite_seq", prompt, schema, project=slug, model=model)
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
- Người của các dân tộc/thời kỳ (lính, dân, nhân vật lịch sử): chars type "person" + faction + role (hoặc outfit), look (hair, beard,
  accent cho nhân vật chính, seed); đổi trang phục bằng outfit_changes. Đám đông, đội hình quân: `crowds` (formation block/line/column/
  wedge/scatter/circle, count, cols, spacing, moves, march). Văn hóa chưa có → missing kind "cultures" (brief: dân tộc, nơi, năm, các vai);
  trang phục của vai sẽ được thiết kế sau văn hóa (không cần liệt kê). Trang phục lẻ (nhân vật lịch sử riêng) → kind "outfits" + culture.
  Xem library/OUTFITS.md.
"""


PLAN_RULES_LONG = """
Luật riêng cho VIDEO DÀI (story này là MỘT CHƯƠNG; đọc LONGFORM_RULES.md bên dưới). Luật camera v3/seqs ở trên KHÔNG áp dụng:
dùng rig "long" với shots (shot ngắn được).
- meta.aspect = "16:9", meta.chapter = {n, title, start_sec}. `shots` liền nhau phủ khung 1..meta.frames, mỗi shot 0,5-25 giây
  (phần lớn 1,5-4 s, 12-16 cắt/phút, thỉnh thoảng 1 cảnh dài 8-25 s); mỗi shot có `type`. Bám theo `shots` dự kiến trong content.
- Viết shot bằng `frame` (khung đặt sẵn: subject, move, angle, height, x) — tool tự tính máy, không cắt đầu nhân vật. Chỉ dùng `keys`
  khi cần đường máy đặc biệt. Camera luôn chuyển động; hai shot liền nhau đổi kiểu cảnh hoặc góc/chuyển động. Cắt ở đầu câu/chữ nhấn.
- camera.dof = {"fstop": 2.8}; cận/cận vật đặt shot.fstop 1.8-2.2; toàn cảnh 4-5.6.
- Phụ đề: captions.style "bottom" (mặc định của 16:9); không dùng highlight/impact kiểu Shorts.
- Mở chương: {"style":"chapter","sub":"CHAPTER n","text": tiêu đề IN HOA, from 1, to ~75} + {"style":"fade","from":1,"to":20,"in":0,"out":20}.
  Chương cuối kết bằng {"style":"fade","hold":true} trong 30 khung cuối.
- MỌI card_text trong shots của content phải hiện trên màn hình: shot type card → thẻ style "screen" (variant year/number/question/
  quote/name/place/fact) trùng thời gian shot đó; map/diagram/board/label → thẻ label/title hoặc chữ trên bối cảnh. pos x,y trong -1..1
  theo khung 16:9; phụ đề ở y ≈ -0,8, tránh đặt thẻ nhỏ ở đó.
- Âm thanh: sound.music theo đoạn (mood epic/tense/mystery/march/calm/sad/triumph), sound.ambience theo bối cảnh, events tiếng video dài
  (LONGFORM_RULES mục 8); tool tự nén giọng, hạ nhạc dưới lời và chuẩn −14 LUFS. Hiệu ứng vfx + grade theo shot (mục 9).
- Các bối cảnh đặt xa nhau (gốc tọa độ, x = 300, x = 500 …). Shot map/board/diagram dùng bối cảnh dữ liệu có sẵn: parchment_map (bờ biển
  thật theo kinh/vĩ độ), tactical_board (sa bàn, khối quân theo phe), paper_diagram (tay vẽ lên giấy) — xem LONGFORM_RULES mục 6;
  không đưa bản đồ/sa bàn/sơ đồ mới vào missing. Có phe thì khai báo `factions` (id, culture, color, label) ở đầu story.
"""


def _norm_txt(t): return re.sub(r"[^A-Z0-9]+", " ", (t or "").upper()).strip()


def check_long_story(st, content):
    """long-form chapter: rhythm and every planned on-screen text present"""
    e = []
    cam = st.get("camera", {}); shots = cam.get("shots") or []
    N = st["meta"]["frames"]
    if shots:
        cpm = (len(shots) - 1) / max(N / 30 / 60, 0.1)
        if N > 1800 and not 9 <= cpm <= 20: e.append(f"{cpm:.1f} cắt/phút, cần 12-16 (chia hoặc gộp shot)")
        run = 1
        for p, q in zip(shots, shots[1:]):
            same = p.get("type") == q.get("type") and (p.get("frame") or {}).get("subject") == (q.get("frame") or {}).get("subject") \
                and (p.get("frame") or {}).get("move") == (q.get("frame") or {}).get("move") and "frame" in p and "frame" in q
            run = run + 1 if same else 1
            if run >= 3: e.append(f"shot {q['a']}-{q['b']}: 3 shot liền nhau cùng kiểu, cùng chủ thể, cùng chuyển động (đổi góc/kiểu)"); break
    card_words = [set((_norm_txt(c.get("text", "")) + " " + _norm_txt(c.get("sub", "")) + " " + _norm_txt(c.get("caption", ""))).split())
                  for c in st.get("cards", [])]
    for q in content.get("sequences", []):
        for sh in q.get("shots", []):
            want = set(_norm_txt(sh.get("card_text")).split())
            if sh["type"] == "card" and want and not any(len(want & cw) >= 0.8 * len(want) for cw in card_words):
                e.append(f"màn hình chữ '{sh['card_text']}' (chuỗi {q.get('id')}) chưa có trong cards")
    e += label_overlaps(st)
    return e


def label_overlaps(st):
    """handwritten labels of a paper_diagram are centred on 'at'; estimate their boxes and report pairs that overlap"""
    out = []
    for s in st.get("sets", []):
        if s.get("type") != "paper_diagram": continue
        boxes = []
        for lb in (s.get("params") or {}).get("labels", []):
            try:
                sz = float(lb.get("size", 0.42)); x, y = float(lb["at"][0]), float(lb["at"][1])
            except (TypeError, ValueError, KeyError, IndexError): continue
            if lb.get("rot"): continue
            w, h = 0.55 * sz * len(str(lb.get("text", ""))), 1.1 * sz
            boxes.append((lb.get("text", ""), x - w / 2, x + w / 2, y - h / 2, y + h / 2))
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                a, b = boxes[i], boxes[j]
                if a[1] < b[2] and b[1] < a[2] and a[3] < b[4] and b[3] < a[4]:
                    out.append(f"sets '{s['id']}': nhãn '{a[0]}' và '{b[0]}' đè nhau (nhãn canh giữa tại 'at', rộng ≈ 0,55 × size × số ký tự): dời một nhãn")
    return out


def plan_shots(slug, model=None):
    d = _project_dir(slug)
    content = json.load(open(os.path.join(d, "content.json"), encoding="utf-8"))
    long_ = content.get("format") == "long"
    words = json.load(open(os.path.join(d, "words.json"), encoding="utf-8"))
    story_schema = json.load(open(os.path.join(ROOT, "story.schema.json"), encoding="utf-8"))
    defs = story_schema.pop("$defs"); [story_schema.pop(k, None) for k in ("$schema", "$id")]
    schema = {"type": "object", "$defs": defs, "additionalProperties": False, "required": ["story", "missing"],
              "properties": {"story": story_schema, "missing": {"type": "array", "items": {
                  "type": "object", "required": ["kind", "name", "brief"], "additionalProperties": False,
                  "properties": {"kind": {"enum": ["sets", "props", "chars", "cultures", "outfits"]}, "name": {"type": "string"}, "brief": {"type": "string"},
                                 "culture": {"type": "string", "description": "outfits: the culture it belongs to"}}}}}}
    frames = int(round((words["duration"] + 1.2) * 30)) if "duration" in words else None
    if long_ and "frames" in words: frames = words["frames"]
    prompt = (f"Chuyển content đã duyệt thành story.json (đọc STORY.md; mẫu: "
              + ("projects/demo-long/story.json (video dài 16:9) và projects/demo-v3/story.json" if long_ else
                 "projects/demo-v3/story.json và projects/manhole-round/story.json") + ").\n"
              + ("Dùng camera rig 'long'. " if long_ else "Dùng camera rig 'v3'. ")
              + f"Thời gian từ (words, giây): {json.dumps(words['words'], ensure_ascii=False)}\n"
              + (f"meta.frames = {frames}.\n" if frames else "")
              + f"Content:\n{json.dumps(content, ensure_ascii=False)}\n\nThư viện:\n{_catalog_text()}\n"
              + PLAN_RULES + (PLAN_RULES_LONG + long_rules() if long_ else ""))

    def check(x):
        pend = {(m["kind"], m["name"]) for m in x["missing"]}
        e = storycheck.check_story(x["story"], pending=pend)
        if long_ and x["story"]["camera"].get("rig") != "long": e.append("video dài: camera.rig phải là 'long' (shots)")
        if long_ and x["story"]["meta"].get("aspect") != "16:9": e.append("video dài: meta.aspect phải là '16:9'")
        if frames and x["story"]["meta"]["frames"] != frames: e.append(f"meta.frames phải là {frames}")
        if long_: e += check_long_story(x["story"], content)
        return e
    data, info = call("plan_shots", prompt, schema, project=slug, model=model, check=check)
    _save_versioned(slug, "story.json", data["story"])
    json.dump(data["missing"], open(os.path.join(d, "missing.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return data


def is_usage_limit(err):
    """the Pro/Max plan's usage window is used up: every further call fails until it resets"""
    s = str(err).lower()
    return "hit your" in s and "limit" in s or "usage limit" in s


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
