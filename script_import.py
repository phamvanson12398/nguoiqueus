"""The user's own dialogue script -> content.json (format "dialog").

Accepted (one line per sentence, blank lines ignored):

    Title: The Thermostat War          (optional headers: Title / Tiêu đề, Hook, Setting / Bối cảnh, Idle)
    Hook: Married couples be like
    Setting: kitchen

    Ben: Mia. Who touched the thermostat?
    Mia (innocent): Not me, babe.
    BEN: (angry) It was on seventy-four! [pause]
    Mia: *laughs* Weird.

- "Name:", "NAME -", "Name —", "[Name]" start a line; a line without a name continues the previous one.
- Cues in ( ), [ ] or * * are stage directions: emotions (angry / giận, shocked / sốc, sad / buồn, laughs / cười…),
  gestures (points / chỉ tay, shrugs / nhún vai, crosses arms / khoanh tay…), pauses ([pause], (beat), (im lặng)),
  speed (fast / nhanh, slow / chậm, whisper / thì thầm). Laughs and sighs become OmniVoice tags [laughter], [sigh].
- No names at all: lines alternate between two speakers A and B.

parse(text) -> {"title", "hook", "setting", "idle", "speakers": [...], "lines": [{speaker, text, face, gesture, pause, speed, cues}],
                 "warnings": [...], "vietnamese": bool}
to_content(parsed, voices=(), minutes=None) -> a complete content.json (defaults chosen by the tool, no Claude)
"""
import re, unicodedata
import vtags

HEADERS = {"title": "title", "tiêu đề": "title", "tieu de": "title", "hook": "hook", "tagline": "hook", "dòng chữ": "hook",
           "setting": "setting", "set": "setting", "bối cảnh": "setting", "boi canh": "setting", "location": "setting",
           "idle": "idle", "tư thế": "idle"}
# cue word -> (face, gesture, tag, extra pause, speed)
CUES = [
    (r"laugh|giggl|chuckl|cười lớn|cười to|bật cười|haha", ("laugh", None, "[laughter]", 0, None)),
    (r"sigh|deep breath|thở dài|hít sâu|hít một hơi", ("annoyed", None, "[sigh]", 0, 0.92)),
    (r"uh-huh|mm-hm|chiếu lệ|ừ ừ", (None, None, "[confirmation-en]", 0, None)),
    (r"huh\?|confused|hả\b|ngơ ngác", ("worried", None, "[question-ah]", 0, None)),
    (r"hmph|scoff|hừ|hứ", ("grumpy", None, "[dissatisfaction-hnn]", 0, None)),
    (r"stare|glare|deadpan look|nhìn chằm chằm|lườm|trừng", ("annoyed", None, None, 0, None)),
    (r"mutter|grumbl|lẩm bẩm|càu nhàu", ("grumpy", None, None, 0, 0.95)),
    (r"furious|angry|mad\b|yell|shout|giận|tức|hét|quát|cáu", ("angry", None, None, 0, 1.12)),
    (r"shock|surpris|gasp|stunned|sốc|ngạc nhiên|bất ngờ|há hốc", ("shock", None, "[surprise-oh]", 0, 1.05)),
    (r"\bsad\b|cry|sob|tear|buồn|khóc|tủi", ("sad", None, None, 0, 0.9)),
    (r"happy|excited|cheer|smil|innocent|sweet|vui|hào hứng|mỉm cười|cười|ngây thơ|ngọt", ("happy", None, None, 0, 1.05)),
    (r"love|dreamy|adoring|yêu|mê|say đắm", ("love", None, None, 0, None)),
    (r"shy|blush|embarrass|ngại|xấu hổ|đỏ mặt|ngượng", ("blush", None, None, 0, 0.95)),
    (r"nervous|worried|anxious|scared|\blo\b|lo lắng|sợ|hoảng|confus|khó hiểu|bối rối", ("worried", None, None, 0, 1.08)),
    (r"annoyed|irritat|bored|deadpan|flat|bực|chán|tỉnh bơ|cạn lời", ("annoyed", None, None, 0, 0.95)),
    (r"side.?eye|suspicious|glance|liếc|nghi ngờ|nghi", ("side_eye", None, None, 0, None)),
    (r"smug|proud|tự mãn|đắc ý|kiêu", ("smug_closed", None, None, 0, None)),
    (r"sarcas|smirk|mỉa|nhếch", ("smirk", None, None, 0, None)),
    (r"wink|nháy mắt", ("wink", None, None, 0, None)),
    (r"grump|pout|cau có|phụng phịu|dỗi", ("grumpy", None, None, 0, None)),
    (r"point|chỉ tay|chỉ vào", (None, "point", None, 0, None)),
    (r"shrug|nhún vai", (None, "shrug", None, 0, None)),
    (r"cross(es|ed)? (his |her |their )?arms|arms crossed|khoanh tay", (None, "cross_arms", None, 0, None)),
    (r"hands? on hips|chống nạnh", (None, "hands_hips", None, 0, None)),
    (r"facepalm|head in hands|ôm đầu|vỗ trán", (None, "facepalm", None, 0, None)),
    (r"wave|vẫy", (None, "wave", None, 0, None)),
    (r"hold(s|ing)? hands|nắm tay", (None, "hold_hands", None, 0, None)),
    (r"think|ponder|suy nghĩ|nghĩ ngợi|\bnghĩ\b", ("focus", "think", None, 0, None)),
    (r"fist|giơ nắm đấm", (None, "fist", None, 0, None)),
    (r"hands up|surrender|giơ tay", (None, "hands_up", None, 0, None)),
    (r"open arms|dang tay|ôm", (None, "open_arms", None, 0, None)),
    (r"long pause|silence|awkward|im lặng|ngượng ngùng|lặng thinh", (None, None, None, 1.2, None)),
    (r"pause|beat|ngừng|dừng|ngập ngừng", (None, None, None, 0.7, None)),
    (r"fast|quick|rapid|nhanh|vội", (None, None, None, 0, 1.15)),
    (r"slow|chậm", (None, None, None, 0, 0.88)),
    (r"whisper|thì thầm|nói nhỏ", (None, None, None, 0, 0.9)),
]
VI_CHARS = re.compile(r"[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]", re.I)
SPEAKER_RE = re.compile(r"^\s*(?:\[(?P<b>[^\]]{1,24})\]|(?P<n>[A-Za-zÀ-ỹ][\wÀ-ỹ.' ]{0,22}?))\s*(?P<cue>\([^)]*\))?\s*(?::|：|\s-\s|\s—\s|\s–\s)\s*(?P<t>.*)$")
FEMALE = {"mia", "emma", "olivia", "ava", "sophia", "isabella", "amelia", "lily", "chloe", "grace", "zoe", "ella", "anna", "kate", "sarah",
          "jessica", "jen", "jenny", "amy", "linda", "karen", "susan", "lisa", "nina", "rose", "lucy", "sophie", "hannah", "emily", "ashley",
          "mom", "mother", "mama", "wife", "girlfriend", "grandma", "granny", "daughter", "sister", "aunt", "she", "her", "lan", "mai", "hoa", "linh"}
ROLE_WORDS = {"mom": ("mom", "female", "middle-aged", "adult"), "mother": ("mom", "female", "middle-aged", "adult"),
              "mama": ("mom", "female", "middle-aged", "adult"), "dad": ("dad", "male", "middle-aged", "adult"),
              "father": ("dad", "male", "middle-aged", "adult"), "papa": ("dad", "male", "middle-aged", "adult"),
              "wife": ("wife", "female", "young adult", "adult"), "husband": ("husband", "male", "young adult", "adult"),
              "girlfriend": ("girlfriend", "female", "young adult", "adult"), "boyfriend": ("boyfriend", "male", "young adult", "adult"),
              "grandma": ("grandma", "female", "elderly", "adult"), "granny": ("grandma", "female", "elderly", "adult"),
              "grandpa": ("grandpa", "male", "elderly", "adult"), "son": ("son", "male", "child", "child"), "kid": ("son", "male", "child", "child"),
              "boy": ("son", "male", "child", "child"), "daughter": ("daughter", "female", "child", "child"), "girl": ("daughter", "female", "child", "child"),
              "boss": ("boss", "male", "middle-aged", "adult"), "neighbor": ("neighbor", "male", "middle-aged", "adult"),
              "mẹ": ("mom", "female", "middle-aged", "adult"), "bố": ("dad", "male", "middle-aged", "adult"), "vợ": ("wife", "female", "young adult", "adult"),
              "chồng": ("husband", "male", "young adult", "adult"), "con": ("son", "male", "child", "child"), "bà": ("grandma", "female", "elderly", "adult"),
              "ông": ("grandpa", "male", "elderly", "adult"), "sếp": ("boss", "male", "middle-aged", "adult")}


def _slug(name):
    s = unicodedata.normalize("NFKD", name.lower()).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return (s if s and s[0].isalpha() else "c_" + s)[:20] or "char"


# things in hand / walking, from the stage directions (English + Vietnamese) -> line action, prop, to_spot
PROP_WORDS = [
    (r"phone|điện thoại|đt\b|smartphone|iphone", "phone"), (r"coffee|cà phê|cafe|latte|starbucks", "coffee"),
    (r"\bmug\b|\btea\b|\btrà\b|cốc|tách", "mug"), (r"soda|\bcoke\b|\bcan\b|lon\b|nước ngọt", "soda"),
    (r"bottle|water|chai|nước suối|\bwine\b|rượu", "bottle"), (r"fries|khoai|chips", "fries"), (r"burger|bánh mì kẹp|hamburger", "burger"),
    (r"pizza", "pizza"), (r"ice ?cream|kem\b", "icecream"), (r"\bbag\b|túi|shopping", "bag"), (r"keys?\b|chìa khóa|chìa khoá", "keys"),
    (r"\bbook\b|sách|quyển", "book"), (r"remote|điều khiển|remote control", "remote"), (r"receipt|hóa đơn|hoá đơn|bill\b", "receipt"),
    (r"letter|paper|note\b|tờ giấy|lá thư|thư\b|giấy", "paper"), (r"money|cash|dollars?|tiền", "money"),
    (r"flowers?|bouquet|hoa\b|bó hoa", "flowers"), (r"gift|present|quà|hộp quà", "gift"), (r"credit card|\bcard\b|thẻ", "card"),
    (r"popcorn|bỏng ngô|bắp rang", "popcorn"), (r"donut|doughnut|bánh vòng|bánh donut", "donut")]
ACTION_WORDS = [
    (r"walks? (in|into)|enters?|comes? in|bước vào|đi vào|chạy vào|xuất hiện", "enter", None),
    (r"walks? (off|out|away)|leaves?|storms? off|exits?|bỏ đi|đi ra|đi mất|quay lưng đi|bước ra ngoài", "exit", None),
    (r"steps? (closer|forward|up)|walks? (over|up) to|moves? closer|approach|bước tới|bước lại gần|tiến lại|đi lại gần|lại gần", "walk_to", "partner"),
    (r"steps? back|backs? (off|away)|moves? away|lùi lại|lùi ra|bước ra xa|tránh ra", "walk_to", "away"),
    (r"hands? (it|him|her|over)|gives?|passes?|đưa cho|đưa|trao|chìa .* cho", "give", None),
    (r"shows?|holds? up|giơ|chìa ra|cho .* xem", "show", None),
    (r"sips?|drinks?|eats?|bites?|takes? a (sip|bite)|uống|nhấp|hớp|ăn|cắn|nhai|scroll|looks? at (his|her|the) (phone|screen)|lướt|xem điện thoại|nhìn điện thoại|bấm điện thoại", "use", None),
    (r"puts? (it|.*) away|pockets?|cất|bỏ vào túi", "put_away", None),
    (r"takes? out|pulls? out|picks? up|grabs?|holds?|lấy ra|rút ra|cầm|nhặt", "take_out", None)]


def _actions(text_cues):
    """(action, prop, to_spot) from stage directions"""
    low = " ".join(text_cues).lower()
    prop = next((k for pat, k in PROP_WORDS if re.search(pat, low)), "")
    for pat, a, ts in ACTION_WORDS:
        if re.search(pat, low):
            if a in ("give", "show", "take_out", "put_away") and not prop: continue     # "gives up", "holds on"…: no item, not an action
            if a == "use" and not prop: prop = "phone" if re.search(r"scroll|lướt|màn hình|screen", low) else ""
            return a, prop, ts or ""
    return ("take_out", prop, "") if prop else ("none", "", "")


def _apply_cues(text_cues):
    face = gesture = None; tags = []; pause = 0.0; speed = None
    for cue in text_cues:
        low = cue.lower()
        for pat, (f, g, tag, p, sp) in CUES:
            if re.search(pat, low):
                face = face or f; gesture = gesture or g; pause = max(pause, p)
                if tag and tag not in tags: tags.append(tag)
                if sp and speed is None: speed = sp
    return face, gesture, tags, pause, speed


def parse(text):
    head = {}; lines = []; warnings = []; named = 0; canon = {}; pending = []
    raw = [l.rstrip() for l in (text or "").replace("\r", "").split("\n")]
    for ln in raw:
        s = ln.strip()
        if not s or s.startswith(("#", "//")): continue
        m = re.match(r"^\s*([A-Za-zÀ-ỹ ]{2,12})\s*:\s*(.+)$", s)
        if m and m.group(1).strip().lower() in HEADERS and not lines:
            head[HEADERS[m.group(1).strip().lower()]] = m.group(2).strip(); continue
        if not named and not lines and not head.get("title") and re.fullmatch(r"[“\"'«].{2,80}[”\"'»]", s):
            head["title"] = s.strip('“”"\'«» '); continue
        m = SPEAKER_RE.match(s)
        if m and (m.group("b") or m.group("n")) and len((m.group("b") or m.group("n")).split()) <= 3 and m.group("t") is not None:
            name = (m.group("b") or m.group("n")).strip()
            key = name.lower()                                 # "BEN" and "Ben" are the same person
            if key in canon: name = canon[key]
            else: canon[key] = name if not name.isupper() or len(name) <= 2 else name.title()
            name = canon[key]
            lines.append({"name": name, "raw": (" ".join(pending) + " " + (m.group("cue") or "") + " " + m.group("t")).strip()}); named += 1
            pending = []
        elif lines and named and re.fullmatch(r"(\([^)]*\)|\*[^*]+\*|\[[^\]]+\]|\s)+", s):
            pending.append(s)                                 # a stage direction on its own line: goes with the NEXT line
        elif lines and named:
            lines[-1]["raw"] += " " + s                       # continuation of the previous line
        elif not named and lines == [] and (len(s) > 60 or s.endswith((".", "!", "?"))) and ":" not in s[:25]:
            head["notes"] = (head.get("notes", "") + " " + s).strip()       # a paragraph before the dialogue: scene notes
        else:
            lines.append({"name": None, "raw": s})
    if lines and not named:                                    # no names: two people taking turns
        warnings.append("Không thấy tên người nói: coi như hai người A và B nói lần lượt (sửa tên ở thẻ nhân vật)")
        for k, l in enumerate(lines): l["name"] = "A" if k % 2 == 0 else "B"
    elif any(l["name"] is None for l in lines):
        first = next(l["name"] for l in lines if l["name"])
        for l in lines:
            if l["name"] is None: l["name"] = first; warnings.append(f"Dòng đầu không có tên người nói: gán cho {first}")
    out = []; names = []; silent = None
    for k, l in enumerate(lines):
        cues = re.findall(r"\(([^)]*)\)|\*([^*]+)\*|\[([^\]]+)\]", l["raw"])
        cue_txt = [a or b or c for a, b, c in cues]
        keep_tags = [c for c in cue_txt if "[" + c.strip() + "]" in vtags.TAGS]
        body = re.sub(r"\(([^)]*)\)|\*([^*]+)\*|\[([^\]]+)\]", " ", l["raw"])
        body = re.sub(r"\s+", " ", body).strip().strip('"“”')
        face, gesture, tags, pause, speed = _apply_cues(cue_txt)
        tags = [f"[{t.strip()}]" for t in keep_tags] + [t for t in tags if t.strip("[]") not in keep_tags]
        if not body:
            if cue_txt:                                               # silent beat: "Jake: (stares at her)"
                silent = {"who": l["name"], "cues": cue_txt, "face": face, "gesture": gesture, "act": _actions(cue_txt)}
                continue
            warnings.append(f"Dòng {k + 1} trống: bỏ qua"); continue
        if l["name"] not in names: names.append(l["name"])
        act, prop, to_spot = _actions(cue_txt)
        entry = {"speaker_name": l["name"], "text": (" ".join(tags) + " " + body).strip() if tags else body, "face": face,
                 "gesture": gesture, "pause": pause, "speed": speed, "cues": cue_txt, "action": act, "prop": prop, "to_spot": to_spot}
        if silent:                                                    # the silent beat before this line
            entry["pause"] = max(entry["pause"], 1.3)
            entry["silent_before"] = {"who": silent["who"], "action": "; ".join(silent["cues"])}
            if silent["who"] == l["name"] and silent["act"][0] != "none" and entry["action"] == "none":    # does it, then talks
                entry["action"], entry["prop"], entry["to_spot"] = silent["act"]
            if silent["who"] != l["name"]:
                entry["listener_face"] = silent["face"] or "annoyed"; entry["listener_gesture"] = silent["gesture"]
            silent = None
        out.append(entry)
    if len(names) > 3: warnings.append(f"Có {len(names)} người nói ({', '.join(names)}): video đối thoại chỉ nhận tối đa 3 người")
    if len(out) < 2: warnings.append("Kịch bản cần ít nhất 2 câu thoại")
    vi = bool(VI_CHARS.search(" ".join(l["text"] for l in out)))
    return {"title": head.get("title"), "hook": head.get("hook"), "setting": head.get("setting"), "idle": head.get("idle"), "notes": head.get("notes"),
            "speakers": names, "lines": out, "warnings": warnings, "vietnamese": vi}


PALETTE = [((0.85, 0.2, 0.35), (0.98, 0.8, 0.2)), ((0.15, 0.45, 0.85), (0.12, 0.2, 0.45)), ((0.2, 0.65, 0.4), (0.95, 0.6, 0.15))]
SIG = {"female": ["bow", "earrings", "flower"], "male": ["cap", "glasses", "beanie"]}
SIG_COLOR = [(0.95, 0.15, 0.3), (0.1, 0.55, 0.95), (1.0, 0.7, 0.1)]
SHAPES = ["egg", "wide", "round"]
SETS = {"kitchen", "office", "street"}
# place words in a scene description -> set name (used if the library has it, otherwise Claude designs it at build time)
PLACES = [
    (r"\bcar\b|parking|xe hơi|ô tô|trong xe|bãi đỗ|bãi xe", "parking_lot"),
    (r"living room|couch|sofa|phòng khách|ghế sofa|tivi|\btv\b", "living_room"),
    (r"bedroom|\bbed\b|phòng ngủ|giường", "bedroom"),
    (r"restaurant|diner|dinner table|nhà hàng|quán ăn|bàn ăn", "restaurant"),
    (r"caf[eé]|coffee|starbucks|quán cà phê|cà phê", "cafe"),
    (r"supermarket|grocery|target|costco|walmart|siêu thị|cửa hàng|tạp hóa", "supermarket"),
    (r"\bpark\b|công viên", "park"),
    (r"classroom|school|lớp học|trường", "classroom"),
    (r"beach|bãi biển|biển", "beach"),
    (r"office|work|văn phòng|công ty", "office"),
    (r"street|sidewalk|đường phố|vỉa hè|ngoài đường", "street"),
    (r"kitchen|bếp|nấu ăn", "kitchen"),
    (r"bathroom|phòng tắm|nhà vệ sinh", "bathroom"),
    (r"gym|phòng tập", "gym"),
    (r"backyard|garden|sân sau|vườn", "backyard"),
]
STAND = (" Bối cảnh cho video đối thoại: 2-3 người ĐỨNG cạnh nhau quay mặt về camera (phía -Y), chừa khoảng trống x -1,5..1,5 quanh "
         "điểm diễn; nếu cảnh gốc là ngồi (trong xe, bàn ăn, sofa) thì dựng chỗ đứng cạnh xe/bàn/sofa. Khai báo 'stage' (x, y) và 'spots': 4-6 chỗ "
         "đứng có tên theo đồ vật/vai trò (vd driver_door, counter, doorway, sofa_left), tọa độ sàn x, y thật trong bối cảnh, mô tả ngắn.")


def pick_set(desc, have=()):
    """-> (set name, library_need or None) from the user's scene description"""
    if not desc: return "kitchen", None
    low = desc.strip().lower()
    if low in have or low in SETS: return low, None
    name = next((n for pat, n in PLACES if re.search(pat, low)), None)
    if name and (name in have or name in SETS): return name, None
    if not name:
        name = "scene_" + re.sub(r"[^a-z0-9]+", "_", unicodedata.normalize("NFKD", low).encode("ascii", "ignore").decode())[:24].strip("_")
    return name, {"kind": "sets", "name": name, "brief": desc.strip().rstrip(".") + "." + STAND}


def cast_member(name, k, voices=()):
    low = name.lower(); key = low.split()[0]
    role, gender, age, body = ROLE_WORDS.get(key, (None, None, "young adult", "adult"))
    if gender is None: gender = "female" if key in FEMALE or key.endswith(("a", "ie", "y")) and key not in {"tony", "andy", "jay", "ray"} else "male"
    if role is None: role = "girlfriend" if gender == "female" else "boyfriend"
    vid = next((v["id"] for v in voices if (v.get("name") or "").lower() == low and v.get("has_ref")), None) or _slug(name) + "_voice"
    pitch = {"female": "high pitch", "male": "low pitch"}[gender] if age != "child" else "very high pitch"
    cloth, cloth2 = PALETTE[k % len(PALETTE)]
    return {"id": _slug(name), "name": name if not name.isupper() else name.title(), "role": role, "gender": gender, "age": age, "body": body,
            "voice_id": vid, "voice_instruct": f"{gender}, {age}, {pitch}, american accent",
            "hair": ("tied" if gender == "female" else "short"), "hair_color": [0.06, 0.05, 0.04],
            "outfit": ("kid_dress" if gender == "female" else "kid_tee") if body == "child" else ("casual_dress" if gender == "female" else "casual_tee"),
            "colors": {"cloth": list(cloth), "cloth2": list(cloth2)}, "personality_vi": "",
            "head_shape": SHAPES[k % len(SHAPES)], "signature": SIG[gender][k % 3], "sig_color": list(SIG_COLOR[k % 3])}


def to_content(p, voices=(), minutes=None, have_sets=()):
    """a complete dialogue content from the parsed script, every acting choice defaulted by the tool (no Claude)"""
    if len(p["lines"]) < 2: raise ValueError("kịch bản cần ít nhất 2 câu thoại")
    if len(p["speakers"]) > 3: raise ValueError(f"tối đa 3 người nói (đang có {len(p['speakers'])}: {', '.join(p['speakers'])})")
    if len(p["speakers"]) < 2: raise ValueError("cần ít nhất 2 người nói (dạng 'Tên: lời thoại')")
    cast = [cast_member(n, k, voices) for k, n in enumerate(p["speakers"])]
    ids = {n: c["id"] for n, c in zip(p["speakers"], cast)}
    if len(set(ids.values())) < len(ids): raise ValueError("hai người nói có tên quá giống nhau, đặt tên khác hẳn")
    lines = []; n = len(p["lines"])
    for k, l in enumerate(p["lines"]):
        beat = "punchline" if k == n - 1 else "twist" if k == n - 2 and n > 4 else "setup" if k < 2 else "build"
        face = l["face"] or ("smirk" if beat == "punchline" else "neutral")
        nxt = p["lines"][k + 1] if k + 1 < n else None
        listener = l.get("listener_face") or ("shock" if face in ("angry",) or beat in ("twist", "punchline") else "side_eye" if face in ("smirk", "smug_closed") else "neutral")
        lines.append({"speaker": ids[l["speaker_name"]], "text": l["text"], "text_vi": "", "face": face, "listener_face": listener,
                      "gesture": l["gesture"] or "none", "listener_gesture": l.get("listener_gesture") or "none",
                      "shot": "listener" if l.get("silent_before") else "auto",
                      "pause_before": round(max(0.25, l["pause"] or 0.25), 2), "speed": l["speed"] or 1.0, "sfx": "none",
                      "react": "flinch" if beat == "twist" else "none", "beat": beat,
                      **({"action": l["action"], "prop": l.get("prop") or "", "to_spot": l.get("to_spot") or ""} if l.get("action", "none") != "none" else {})})
    vtags.auto_tag(lines)                       # OmniVoice emotion tags at the strong moments (~40 % of lines at most)
    words = sum(len(re.sub(r"\[[^\]]*\]", " ", l["text"]).split()) for l in lines)
    st, need = pick_set(p.get("setting") or p.get("notes"), have_sets)
    return {"format": "dialog", "title": p.get("title") or lines[0]["text"][:40], "title_vi": "", "hook": (p.get("hook") or "")[:32],
            "premise_vi": p.get("notes") or "Kịch bản do bạn tự viết.", "minutes": minutes or round(words / 2.3 / 60, 2),
            "cast": cast, "setting": {"set": st, "params": {"stuck_toast": False} if st == "kitchen" else {}, "brief_vi": p.get("setting") or ""},
            "idle": p.get("idle") if p.get("idle") in ("relaxed", "hold_hands", "hands_hips", "cross_arms") else "relaxed",
            "lines": lines, "highlight": [], "end_sfx": "none", "library_needs": [need] if need else []}
