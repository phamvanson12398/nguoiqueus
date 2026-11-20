"""OmniVoice inline non-verbal / emotion tags (the documented set, k2-fsa/OmniVoice README).

A tag is written straight into the line text, e.g. "[laughter] You really got me." OmniVoice turns it into the sound;
captions drop it (dialog.spoken). This module is plain Python (no bpy): the content checks, the script importer and
the page all use the same list.
"""
import re

# tag -> (what it sounds like, when to use it) — Vietnamese for the page and the prompts
TAGS = {
    "[laughter]": ("tiếng cười", "câu đùa của chính mình, chọc người kia, cười trừ khi bị bắt quả tang"),
    "[sigh]": ("thở dài", "chán, bất lực, chịu thua, mệt với người kia (\"[sigh] Fine. You pick.\")"),
    "[surprise-oh]": ("\"Oh!\" ngạc nhiên", "vừa hiểu ra / vừa nghe tin lạ (\"[surprise-oh] You're serious?\")"),
    "[surprise-ah]": ("\"Ah!\" giật mình", "giật mình, bị bắt quả tang, đau, hoảng"),
    "[surprise-wa]": ("\"Wa!\" sốc mạnh", "sốc to, choáng (\"[surprise-wa] Four hundred dollars?!\")"),
    "[surprise-yo]": ("\"Yo!\" thích thú", "hào hứng, khoái chí khi thấy thứ hay"),
    "[question-ah]": ("\"Hả?\" hỏi lại", "không tin tai mình, hỏi lại (\"[question-ah] Taco Bell?\")"),
    "[question-oh]": ("\"Ồ?\" nghi ngờ", "nghi ngờ, bắt bẻ nhẹ (\"[question-oh] Since when?\")"),
    "[question-en]": ("\"Hửm?\" ngơ ngác", "lơ đãng, không nghe rõ, giả vờ không hiểu"),
    "[question-ei]": ("\"Ê?\" ngạc nhiên hỏi", "ngạc nhiên kèm hỏi, thân mật"),
    "[question-yi]": ("\"Hử?\" khó hiểu", "khó hiểu, thấy lạ"),
    "[confirmation-en]": ("\"Ừm.\" xác nhận", "đồng ý chiếu lệ, tỉnh bơ, \"uh-huh\" kiểu không nghe"),
    "[dissatisfaction-hnn]": ("\"Hừm\" không vừa ý", "bực, dỗi, không chịu, càu nhàu"),
}
TAG_RE = re.compile(r"\[[^\]]+\]")
PHONEME_RE = re.compile(r"\[[A-Z]{1,3}[0-2]?( [A-Z]{1,3}[0-2]?)*\]")       # [B EY1 S]: pronunciation, not a tag


def tags_in(text):
    return [t for t in TAG_RE.findall(text or "") if not PHONEME_RE.fullmatch(t)]


def unknown(text):
    return [t for t in tags_in(text) if t not in TAGS]


def rules_text():
    """the list for prompts / docs"""
    return "\n".join(f"  - `{t}` = {s}: {u}" for t, (s, u) in TAGS.items())


def _words(text): return len(re.findall(r"[A-Za-z0-9'’]+", TAG_RE.sub(" ", text or "")))


def pick(line):
    """the tag that fits a line (from its face and wording), or None"""
    t = TAG_RE.sub(" ", line.get("text", "")).strip(); low = t.lower(); f = line.get("face") or "neutral"
    if f == "shock": f = "neutral" if line.get("beat") in ("twist", "punchline", "tag") else "worried"   # calm acting (dialog.calm_faces)
    n = _words(t)
    if re.search(r"\b(ha){2,}\b|\bhehe\b|\blol\b", low) or f == "laugh": return "[laughter]"
    if f in ("shock",):
        if "?!" in t or re.search(r"\$|\bhundred|thousand|\bdollars?\b", low): return "[surprise-wa]"
        if t.endswith("?"): return "[question-ah]"
        return "[surprise-oh]"
    if f == "sad" or re.match(r"(fine|okay|ok|whatever)\b[.,]", low) and f in ("annoyed", "grumpy", "sad", "worried"): return "[sigh]"
    if f in ("grumpy", "angry") and (n <= 5 or re.match(r"(ugh|no|nope|hmph|seriously)\b", low)): return "[dissatisfaction-hnn]"
    if f in ("annoyed",) and re.match(r"(ugh|seriously|really)\b", low): return "[dissatisfaction-hnn]"
    if f in ("side_eye", "side_eye_l", "side_eye_r", "smirk") and t.endswith("?") and n <= 6: return "[question-oh]"
    if re.match(r"(uh-huh|mm-hm|mhm|yeah|yep|sure)\b", low) and f in ("neutral", "smirk", "annoyed", "smug_closed"): return "[confirmation-en]"
    if f == "worried" and t.endswith("?") and n <= 5: return "[question-ah]"
    if f in ("happy", "love") and re.match(r"(oh|ooh|wow|yes)\b", low) and "!" in t: return "[surprise-yo]"
    if f == "happy" and re.search(r"\bjk\b|\bkidding\b|\bjoking\b", low): return "[laughter]"
    return None


def auto_tag(lines, share=0.4):
    """add a fitting OmniVoice tag to lines that have none (strongest moments first: punchline, twist, shock, laugh),
    at most `share` of the lines in all, never two tagged lines in a row by the same person. Returns the count added."""
    have = sum(1 for l in lines if tags_in(l.get("text")))
    cap = max(2, round(len(lines) * share)) - have
    order = sorted(range(len(lines)), key=lambda k: (lines[k].get("beat") not in ("punchline", "twist", "tag"),
                                                      lines[k].get("face") not in ("laugh", "shock", "sad"), k))
    added = 0
    for k in order:
        if added >= cap: break
        l = lines[k]
        if tags_in(l.get("text")): continue
        g = pick(l)
        if not g: continue
        prev = lines[k - 1] if k else None
        if prev and prev.get("speaker") == l.get("speaker") and tags_in(prev.get("text")): continue
        txt = re.sub(r"^\s*(ha(ha)+|hehe)[.!,]*\s*", "", l["text"], flags=re.I) if g == "[laughter]" else l["text"]
        l["text"] = f"{g} {txt}".strip(); added += 1
    return added
