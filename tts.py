"""Text-to-speech for dialogue videos: OmniVoice (k2-fsa) run by tools/omnivoice_worker.py in its own Python.

Voices live in library/voices/<id>/ (reused by every video, so a recurring couple keeps their voices):
    voice.json   {"name", "instruct", "gender", "age", "ref_text", "status": "draft|approved", "source": "design|upload"}
    cand_1..3.wav  auditions made from `instruct` (voice design gives a new voice every call)
    ref.wav      the chosen audition (or the user's own recording, 3-10 s): every line is CLONED from it

Python for OmniVoice (torch + omnivoice, ~3 GB, needs an NVIDIA card to be quick), first that exists:
    WHYSHORTS_OMNIVOICE_PY, local_settings.json "omnivoice_python", the venv made by tools/install_omnivoice.bat
WHYSHORTS_TTS=fake makes a stand-in voice (tones, right syllable timing) for testing without OmniVoice.

    python tts.py status
    python tts.py audition <voice_id> "<instruct>"
    python tts.py pick <voice_id> <k>
"""
import json, math, os, re, shutil, subprocess, sys, tempfile, time, wave
import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
VOICES = os.path.join(ROOT, "library", "voices")
LOCAL = os.path.join(ROOT, "local_settings.json")
SR = 24000
SAMPLE_TEXT = "Hey! Did you just eat my last slice of pizza? It was right here, and now it's gone. Unbelievable."
INSTALL_DIR_WIN = os.path.join(os.environ.get("USERPROFILE", os.path.expanduser("~")), "WhyShortsVoice")


def _j(p, d=None):
    try: return json.load(open(p, encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError): return d


def _w(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"; json.dump(obj, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1); os.replace(tmp, p)


def say_default(m): print(m, flush=True)


# =====================================================================
#  engine
# =====================================================================
def engine():
    return "fake" if os.environ.get("WHYSHORTS_TTS", "").lower() == "fake" else "omnivoice"


def omnivoice_python():
    cands = [os.environ.get("WHYSHORTS_OMNIVOICE_PY"), (_j(LOCAL, {}) or {}).get("omnivoice_python"),
             os.path.join(INSTALL_DIR_WIN, "venv", "Scripts", "python.exe"),
             os.path.join(os.path.expanduser("~"), "WhyShortsVoice", "venv", "bin", "python")]
    for c in cands:
        if c and os.path.exists(c): return c
    return None


def status():
    e = engine(); py = omnivoice_python()
    ok = e == "fake" or bool(py)
    msg = ("giọng thử (WHYSHORTS_TTS=fake), không phải OmniVoice" if e == "fake" else
           f"OmniVoice: {py}" if py else
           "chưa cài OmniVoice: chạy tools\\install_omnivoice.bat một lần (cần card NVIDIA, ~3 GB), hoặc ghi đường dẫn python.exe có OmniVoice vào ô Cài đặt")
    return {"engine": e, "python": py, "ready": ok, "message": msg}


def run_items(items, log=say_default, procs=None, num_step=32, cancelled=lambda: False):
    """synthesise every item {id, text, out, ref_audio/ref_text | instruct, speed, seed}; -> (ok ids, {id: error})"""
    if not items: return [], {}
    if engine() == "fake":
        okk = []
        for k, it in enumerate(items, 1):
            if cancelled(): raise ValueError("đã hủy")
            x = fake_voice(it["text"], it.get("instruct") or _voice_hint(it), float(it.get("speed") or 1.0), int(it.get("seed") or 0))
            write_wav(it["out"], x, SR); okk.append(it["id"])
            log(f"   giọng thử {k}/{len(items)} {it['id']}: {len(x) / SR:.1f} s")
        return okk, {}
    py = omnivoice_python()
    if not py: raise ValueError(status()["message"])
    os.makedirs(os.path.join(ROOT, "logs"), exist_ok=True)
    jp = os.path.join(ROOT, "logs", f"tts_job_{int(time.time() * 1000)}.json")
    _w(jp, {"model": os.environ.get("WHYSHORTS_OMNIVOICE_MODEL", "k2-fsa/OmniVoice"), "device": os.environ.get("WHYSHORTS_OMNIVOICE_DEVICE", "auto"),
            "num_step": num_step, "sample_rate": SR, "items": items})
    cmd = [py, os.path.join(ROOT, "tools", "omnivoice_worker.py"), jp]
    log(f"   OmniVoice: {len(items)} câu (lần đầu tải model ~2-3 GB từ Hugging Face, sau đó nạp model ~20-40 s)…")
    kw = {}
    if os.name == "nt": kw["creationflags"] = 0x08000000          # CREATE_NO_WINDOW
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, text=True,
                         encoding="utf-8", errors="replace", cwd=ROOT, env=env, **kw)
    if procs is not None: procs.append(p)
    okk, errs, tail = [], {}, []
    try:
        for line in p.stdout:
            line = line.rstrip(); tail.append(line); tail = tail[-40:]
            if line.startswith("TTS ERROR"):
                _, _, rest = line.partition("TTS ERROR "); iid, _, msg = rest.partition(" "); errs[iid] = msg; log("   LỖI " + rest)
            elif line.startswith("TTS ") and "/" in line.split()[1]:
                okk.append(line.split()[2]); log("   " + line[4:])
            elif line.startswith(("TTS LOAD", "TTS READY")):
                log("   " + line[4:])
        p.wait()
    finally:
        if procs is not None and p in procs: procs.remove(p)
    if cancelled(): raise ValueError("đã hủy")
    if p.returncode not in (0, 2) and not okk:
        raise ValueError("OmniVoice không chạy được:\n" + "\n".join(l for l in tail[-12:] if l.strip()))
    try: os.remove(jp)
    except OSError: pass
    return okk, errs


def _voice_hint(it):
    v = _j(os.path.join(os.path.dirname(it.get("ref_audio") or ""), "voice.json"), {}) or {}
    return v.get("instruct") or ""


# =====================================================================
#  stand-in voice (testing without OmniVoice): right syllable rhythm and pauses, pitch from the instruct
# =====================================================================
def _syl(w):
    t = re.sub(r"[^a-z]", "", w.lower())
    if not t: return 1
    s = len(re.findall(r"[aeiouy]+", t))
    if t.endswith("e") and not t.endswith(("le", "ee")) and s > 1: s -= 1
    return max(1, s)


def fake_voice(text, instruct="", speed=1.0, seed=0):
    ins = (instruct or "").lower()
    f0 = 125.0
    if "female" in ins or "woman" in ins: f0 = 215.0
    if "child" in ins or "kid" in ins: f0 = 290.0
    if "elderly" in ins or "old" in ins: f0 *= 0.9
    if "high pitch" in ins: f0 *= 1.15
    if "low pitch" in ins: f0 *= 0.85
    rnd = np.random.default_rng(seed + len(text))
    parts = [np.zeros(int(SR * 0.08))]
    for tok in re.findall(r"\[[^\]]*\]|[A-Za-z0-9'’-]+[^\sA-Za-z0-9\[]*", text):
        if tok.startswith("["):                                   # [laughter], [sigh]…: a breathy burst
            n = int(SR * 0.45); env = np.abs(np.sin(np.linspace(0, 5 * math.pi, n))) * np.hanning(n)
            parts.append(0.12 * env * rnd.standard_normal(n)); parts.append(np.zeros(int(SR * 0.12))); continue
        for s in range(_syl(tok)):
            dur = (0.15 + 0.05 * rnd.random()) / speed; n = int(SR * dur); t = np.arange(n) / SR
            f = f0 * (1 + 0.08 * math.sin(len(parts))) * (1 + 0.05 * rnd.standard_normal())
            v = sum(np.sin(2 * math.pi * f * h * t) / h for h in (1, 2, 3, 4))
            env = np.sin(np.linspace(0, math.pi, n)) ** 0.6
            parts.append(0.22 * env * v + 0.01 * rnd.standard_normal(n))
        gap = 0.07
        if re.search(r"[,;:—–]$", tok): gap = 0.28
        elif re.search(r"[.?!…]$", tok): gap = 0.42
        parts.append(np.zeros(int(SR * gap / speed)))
    parts.append(np.zeros(int(SR * 0.1)))
    return np.concatenate(parts).astype(np.float32)


# =====================================================================
#  wav helpers (numpy, 16-bit PCM)
# =====================================================================
def read_wav(path):
    """-> (float32 mono samples, rate); accepts float/24-bit/extensible (wavfix)"""
    import wavfix
    data = open(path, "rb").read()
    data, _ = wavfix.to_pcm16(data)
    import io
    w = wave.open(io.BytesIO(data)); sr = w.getframerate(); ch = w.getnchannels()
    x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    if ch > 1: x = x.reshape(-1, ch).mean(axis=1)
    return x, sr


def write_wav(path, x, sr=SR):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    y = np.clip(np.asarray(x, np.float32), -1, 1)
    w = wave.open(path, "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes((y * 32767).astype("<i2").tobytes()); w.close()


def resample(x, sr, to=SR):
    if sr == to or len(x) == 0: return x
    n = int(round(len(x) * to / sr))
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)


def trim(x, sr, db=-42.0, keep=0.04):
    """cut silence at both ends (keep a few ms so consonants are not clipped)"""
    if len(x) == 0: return x
    hop = int(sr * 0.01); n = len(x) // hop
    if n < 3: return x
    rms = np.array([math.sqrt(float(np.mean(x[i * hop:(i + 1) * hop] ** 2)) + 1e-12) for i in range(n)])
    loud = np.where(20 * np.log10(rms + 1e-9) > max(db, 20 * math.log10(rms.max() + 1e-9) - 38))[0]
    if len(loud) == 0: return x
    a = max(0, loud[0] * hop - int(sr * keep)); b = min(len(x), (loud[-1] + 1) * hop + int(sr * keep))
    return x[a:b]


# =====================================================================
#  voice library
# =====================================================================
def vdir(vid):
    if not re.fullmatch(r"[a-z0-9][a-z0-9_]{0,40}", vid or ""): raise ValueError(f"tên giọng không hợp lệ: {vid!r}")
    return os.path.join(VOICES, vid)


def voice(vid):
    v = _j(os.path.join(vdir(vid), "voice.json"))
    if v is None: return None
    v = dict(v, id=vid, has_ref=os.path.exists(os.path.join(vdir(vid), "ref.wav")),
             candidates=sorted(int(m.group(1)) for f in os.listdir(vdir(vid)) for m in [re.fullmatch(r"cand_(\d+)\.wav", f)] if m))
    return v


def list_voices():
    if not os.path.isdir(VOICES): return []
    return [v for v in (voice(n) for n in sorted(os.listdir(VOICES)) if os.path.isdir(os.path.join(VOICES, n))) if v]


def save_voice(vid, **fields):
    p = os.path.join(vdir(vid), "voice.json")
    v = _j(p, {}) or {}
    v.update({k: x for k, x in fields.items() if x is not None})
    v.setdefault("status", "draft"); v.setdefault("created", time.strftime("%Y-%m-%d"))
    _w(p, v); return voice(vid)


def audition(vid, instruct, n=3, text=SAMPLE_TEXT, log=say_default, procs=None, cancelled=lambda: False, **meta):
    """n candidate voices from an OmniVoice voice-design instruct ('female, young adult, high pitch, american accent')"""
    d = vdir(vid); os.makedirs(d, exist_ok=True)
    save_voice(vid, instruct=instruct, sample_text=text, source="design", **meta)
    base = int(time.time()) % 100000
    items = [{"id": f"cand_{k}", "text": text, "out": os.path.join(d, f"cand_{k}.wav"), "instruct": instruct, "seed": base + k}
             for k in range(1, n + 1)]
    okk, errs = run_items(items, log, procs, cancelled=cancelled)
    if not okk: raise ValueError("không tạo được giọng thử: " + "; ".join(f"{k}: {v}" for k, v in errs.items()))
    return voice(vid)


def pick(vid, k):
    """use audition k as the voice of this character (every line is cloned from it)"""
    d = vdir(vid); src = os.path.join(d, f"cand_{int(k)}.wav")
    if not os.path.exists(src): raise ValueError(f"không có giọng thử số {k}")
    x, sr = read_wav(src); x = trim(x, sr)
    write_wav(os.path.join(d, "ref.wav"), resample(x, sr), SR)
    v = _j(os.path.join(d, "voice.json"), {}) or {}
    return save_voice(vid, ref_text=v.get("sample_text") or SAMPLE_TEXT, picked=int(k), status="approved")


def upload_ref(vid, data, ref_text, **meta):
    """the user's own recording (3-10 s) + what it says -> this character's voice"""
    import wavfix
    d = vdir(vid); os.makedirs(d, exist_ok=True)
    data, _ = wavfix.to_pcm16(data)
    tmp = os.path.join(d, "upload.wav"); open(tmp, "wb").write(data)
    x, sr = read_wav(tmp); os.remove(tmp)
    x = trim(x, sr)
    if len(x) / sr < 2.0: raise ValueError("đoạn ghi âm quá ngắn (cần 3-10 giây)")
    if len(x) / sr > 15: x = x[:int(sr * 12)]
    write_wav(os.path.join(d, "ref.wav"), resample(x, sr), SR)
    return save_voice(vid, ref_text=ref_text.strip() or None, source="upload", status="approved", **meta)


def main(argv):
    if not argv or argv[0] == "status": print(json.dumps(status(), ensure_ascii=False, indent=1)); return
    if argv[0] == "audition": print(json.dumps(audition(argv[1], argv[2]), ensure_ascii=False, indent=1)); return
    if argv[0] == "pick": print(json.dumps(pick(argv[1], argv[2]), ensure_ascii=False, indent=1)); return
    if argv[0] == "voices": print(json.dumps(list_voices(), ensure_ascii=False, indent=1)); return
    print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
