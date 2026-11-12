"""Long-form (16:9, 10-20 min) projects: chapters.

A long project keeps the usual files at the top (content.json with `format: "long"` and `chapters`,
voice.wav, words.json from align.py) and gets one sub-project per chapter:

    projects/<slug>/chapters/01/  content.json  (this chapter's sequences + context)
                                  voice.wav     (this chapter's slice of the full voice)
                                  words.json    (times relative to the chapter start)
                                  story.json    (plan_shots, camera rig "long", meta.aspect 16:9)
                                  preview/ out.mp4
    projects/<slug>/out.mp4      = chapters joined with ffmpeg

Each chapter is planned, built, previewed and rendered exactly like a short project (the builder and
bridge see `<slug>/chapters/NN` as a project), so a fix touches one chapter only and an interrupted
render resumes at the first chapter whose mp4 is missing or older than its story.json.

    python longform.py split <slug>      cut voice + words into chapters/NN
    python longform.py status <slug>
    python longform.py concat <slug>     join chapters/NN/<output> into <slug>/out.mp4
"""
import json, math, os, re, shutil, subprocess, sys, wave

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECTS = os.path.join(ROOT, "projects")
FPS = 30
TAIL = 1.0           # seconds of room after the last word of the video


def _j(p, default=None):
    try: return json.load(open(p, encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError): return default


def _w(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(obj, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def is_long(content):
    return bool(content) and (content.get("format") == "long" or bool(content.get("chapters")))


def tokens(text):
    """same word split as align.py"""
    import align
    return re.findall(r"[A-Za-z0-9'’]+(?:[-–][A-Za-z0-9'’]+)*[^\sA-Za-z0-9]*", align.clean_script(text))


def chapter_of(seq, default=1):
    return int(seq.get("chapter") or default)


def chapter_list(content):
    """[(n, title, [sequences])] in order; sequences without 'chapter' stay in the current one"""
    titles = {int(c["n"]): c for c in content.get("chapters", [])}
    out = {}; cur = 1
    for s in content["sequences"]:
        cur = chapter_of(s, cur); out.setdefault(cur, []).append(s)
    return [(n, titles.get(n, {}).get("title", f"Chapter {n}"), out[n]) for n in sorted(out)]


def chapter_dir(slug, n):
    return os.path.join(PROJECTS, slug, "chapters", f"{n:02d}")


def chapter_slug(slug, n):
    return f"{slug}/chapters/{n:02d}"


def split(slug, log=print):
    """cut the full voice + words into chapters; returns [{n, title, start, end, frames, words}]"""
    d = os.path.join(PROJECTS, slug)
    content = _j(os.path.join(d, "content.json")); words = _j(os.path.join(d, "words.json"))
    if not content: raise ValueError("chưa có content.json")
    if not words: raise ValueError("chưa có words.json (tải voice.wav lên để canh chữ trước)")
    chs = chapter_list(content)
    W = words["words"]
    counts = [sum(len(tokens(s.get("vo_en", ""))) for s in seqs) for _, _, seqs in chs]
    total = sum(counts)
    if total != len(W):
        log(f"cảnh báo: content có {total} chữ, words.json có {len(W)} — chia theo tỉ lệ")
        counts = [round(c * len(W) / max(1, total)) for c in counts]; counts[-1] = len(W) - sum(counts[:-1])
    dur = words["duration"]
    # cut just before the first word of each chapter (in the pause before it when there is one)
    starts = [0]; k = 0
    for c in counts[:-1]:
        k += c; starts.append(k)
    cuts = [0.0]
    for k in starts[1:]:
        t_next = W[k][0]; t_prev = W[k - 1][0]
        cuts.append(round(max(t_prev + 0.25, t_next - 0.2), 3))
    cuts.append(dur + TAIL)
    wav = os.path.join(d, "voice.wav")
    res = []
    with wave.open(wav, "rb") as src:
        sr = src.getframerate(); nch = src.getnchannels(); sw = src.getsampwidth()
        raw = src.readframes(src.getnframes())
    bpf = nch * sw
    for i, (n, title, seqs) in enumerate(chs):
        a, b = cuts[i], cuts[i + 1]
        cd = chapter_dir(slug, n); os.makedirs(cd, exist_ok=True)
        seg = raw[int(a * sr) * bpf:int(min(b, dur) * sr) * bpf]
        with wave.open(os.path.join(cd, "voice.wav"), "wb") as dst:
            dst.setnchannels(nch); dst.setsampwidth(sw); dst.setframerate(sr); dst.writeframes(seg)
        cw = W[starts[i]:starts[i] + counts[i]]
        rel = [[round(t - a, 2), w] for t, w in cw]
        frames = int(math.ceil((b - a) * FPS))
        segs = [dict(s, start=round(s["start"] - a, 2), end=round(s["end"] - a, 2)) for s in words.get("segments", [])
                if a - 0.05 <= s["start"] < b]
        _w(os.path.join(cd, "words.json"), {"words": rel, "segments": segs, "duration": round(b - a - (TAIL if i == len(chs) - 1 else 0), 2),
                                            "frames": frames, "word_count": len(rel), "start_sec": a, "chapter": n})
        prev_c = chs[i - 1] if i else None; next_c = chs[i + 1] if i + 1 < len(chs) else None
        sub = {k: v for k, v in content.items() if k not in ("sequences", "vo_en", "vo_vi", "chapters", "word_count")}
        sub.update(format="long", chapter={"n": n, "title": title, "of": len(chs), "start_sec": a, "frames": frames,
                                           "previous": {"n": prev_c[0], "title": prev_c[1]} if prev_c else None,
                                           "next": {"n": next_c[0], "title": next_c[1]} if next_c else None},
                   chapters=content.get("chapters", []), sequences=seqs,
                   vo_en=" ".join(s.get("vo_en", "") for s in seqs), vo_vi=" ".join(s.get("vo_vi", "") for s in seqs))
        sub["word_count"] = len(sub["vo_en"].split())
        _w(os.path.join(cd, "content.json"), sub)
        _w(os.path.join(cd, "settings.json"), {"format": "long", "chapter": n, "parent": slug})
        res.append({"n": n, "title": title, "start": a, "end": b, "frames": frames, "words": len(rel)})
        log(f"phần {n:02d} «{title}»: {a:.1f}–{b:.1f} s, {frames} khung, {len(rel)} chữ, {len(seqs)} chuỗi")
    _w(os.path.join(d, "chapters", "index.json"), {"chapters": res})
    return res


def stitch(slug, log=print):
    """make the parts read as ONE continuous video (the viewer never sees chapters; parts only exist to build and render):
    each part's story gets its place in the full timeline (music/ambience run on across the seams, no fades there),
    'chapter' title cards are dropped, and a part opens on the music mood the previous part ended with."""
    idx = _j(os.path.join(PROJECTS, slug, "chapters", "index.json"), {"chapters": []})
    chs = idx["chapters"]; prev_mood = None; changed = []
    for k, c in enumerate(chs):
        sp = os.path.join(chapter_dir(slug, c["n"]), "story.json")
        st = _j(sp)
        if not st: prev_mood = None; continue
        before = json.dumps(st, sort_keys=True)
        m = st["meta"]
        m["part_offset"] = round(float(c["start"]), 3); m["part_first"] = k == 0; m["part_last"] = k == len(chs) - 1
        N = int(m.get("frames", 0) or 0)

        def seam_fade(cd):           # fade from/to black at a seam would flash black in the middle of the video
            if cd.get("style") != "fade": return False
            return (k > 0 and cd.get("from", 1) <= 2) or (k < len(chs) - 1 and N and cd.get("to", 0) >= N - 2)
        st["cards"] = [cd for cd in st.get("cards", []) if cd.get("style") != "chapter" and not seam_fade(cd)]
        mus = st.get("sound", {}).get("music")
        if isinstance(mus, dict): mus = st["sound"]["music"] = [mus]
        if mus:
            mus.sort(key=lambda x: x.get("from", 1))
            if prev_mood and not mus[0].get("file") and mus[0].get("from", 1) <= 1 and mus[0].get("mood") != prev_mood:
                mus[0]["mood"] = prev_mood
            last = mus[-1]; prev_mood = None if last.get("file") else last.get("mood")
        if json.dumps(st, sort_keys=True) != before:
            _w(sp, st); changed.append(c["n"])
    if changed: log(f"Nối liền các phần: cập nhật phần {changed} (vị trí trong video, bỏ thẻ chương, nhạc chạy tiếp)")
    return changed


def chapter_output(slug, n):
    st = _j(os.path.join(chapter_dir(slug, n), "story.json"))
    if not st: return None
    return os.path.join(chapter_dir(slug, n), st["meta"].get("output", "out.mp4"))


def status(slug):
    idx = _j(os.path.join(PROJECTS, slug, "chapters", "index.json"), {"chapters": []})
    out = []
    for c in idx["chapters"]:
        cd = chapter_dir(slug, c["n"]); sp = os.path.join(cd, "story.json"); mp = chapter_output(slug, c["n"])
        has_story = os.path.exists(sp)
        rendered = bool(mp and os.path.exists(mp) and os.path.getmtime(mp) >= os.path.getmtime(sp))
        prev = os.path.join(cd, "preview")
        out.append(dict(c, story=has_story, rendered=rendered, output=os.path.relpath(mp, os.path.join(PROJECTS, slug)).replace("\\", "/") if rendered else None,
                        previews=sorted(f for f in os.listdir(prev) if f.endswith(".png")) if os.path.isdir(prev) else []))
    return out


def concat(slug, out_name="out.mp4", log=print):
    """join the chapter mp4s (same codec settings) without re-encoding"""
    if not shutil.which("ffmpeg"): raise ValueError("cần ffmpeg để ghép các phần")
    st = status(slug)
    if not st: raise ValueError("chưa chia phần")
    miss = [c["n"] for c in st if not c["rendered"]]
    if miss: raise ValueError(f"phần chưa render (hoặc story mới hơn video): {miss}")
    d = os.path.join(PROJECTS, slug)
    lst = os.path.join(d, "chapters", "concat.txt")
    with open(lst, "w", encoding="utf-8") as f:
        for c in st: f.write("file '" + os.path.join(d, c["output"]).replace("\\", "/").replace("'", "'\\''") + "'\n")
    out = os.path.join(d, out_name)
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
                        "-movflags", "+faststart", out], capture_output=True, text=True)
    if r.returncode: raise ValueError("ffmpeg: " + r.stderr[-800:])
    log(f"đã ghép {len(st)} phần -> {out}")
    return out


if __name__ == "__main__":
    cmd, slug = sys.argv[1], sys.argv[2]
    if cmd == "split": split(slug)
    elif cmd == "status": print(json.dumps(status(slug), ensure_ascii=False, indent=1))
    elif cmd == "concat": concat(slug)
    else: print(__doc__)
