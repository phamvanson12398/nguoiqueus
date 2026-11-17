"""OmniVoice text-to-speech worker (runs in the Python that has OmniVoice installed, not in the studio's Python).

    <omnivoice python> tools/omnivoice_worker.py job.json

job.json:
    {"model": "k2-fsa/OmniVoice", "device": "auto", "num_step": 32,
     "items": [{"id": "07", "text": "Baby, I don't care about money.", "out": "C:/.../lines/07_mia.wav",
                "ref_audio": "C:/.../library/voices/mia/ref.wav", "ref_text": "...",     # voice clone (a cast voice)
                "instruct": "female, young adult, moderate pitch, american accent",       # or voice design (auditions)
                "speed": 1.0, "seed": 7}]}

Prints one line per item ("TTS 3/12 07 2.41s") so the studio can show progress; "TTS ERROR <id> <message>" when one fails
(the others still run); "TTS DONE <n ok> <n failed>" at the end. The model loads once for the whole job.
The same voice clone prompt is reused for every line of a speaker, so a character sounds the same all video long.
"""
import json, os, sys, time, traceback


def main(path):
    job = json.load(open(path, encoding="utf-8"))
    items = job.get("items", [])
    t0 = time.time()
    import torch
    import soundfile as sf
    from omnivoice import OmniVoice
    dev = job.get("device", "auto")
    if dev == "auto":
        dev = "cuda:0" if torch.cuda.is_available() else ("mps" if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available() else "cpu")
    dtype = torch.float16 if dev.startswith("cuda") else torch.float32
    print(f"TTS LOAD {job.get('model', 'k2-fsa/OmniVoice')} on {dev}", flush=True)
    model = OmniVoice.from_pretrained(job.get("model", "k2-fsa/OmniVoice"), device_map=dev, dtype=dtype)
    print(f"TTS READY {time.time() - t0:.1f}s", flush=True)
    prompts = {}                     # (ref_audio, ref_text) -> voice clone prompt, built once per speaker
    ok = bad = 0
    for k, it in enumerate(items, 1):
        t1 = time.time()
        try:
            kw = {"text": it["text"], "num_step": int(it.get("num_step", job.get("num_step", 32)))}
            if it.get("speed") and abs(float(it["speed"]) - 1.0) > 1e-3: kw["speed"] = float(it["speed"])
            if it.get("duration"): kw["duration"] = float(it["duration"])
            if it.get("ref_audio"):
                key = (it["ref_audio"], it.get("ref_text") or "")
                if key not in prompts:
                    prompts[key] = model.create_voice_clone_prompt(ref_audio=it["ref_audio"], ref_text=it.get("ref_text") or None)
                kw["voice_clone_prompt"] = prompts[key]
            elif it.get("instruct"):
                kw["instruct"] = it["instruct"]
            if it.get("seed") is not None:
                torch.manual_seed(int(it["seed"]))
            audio = model.generate(**kw)
            a = audio[0] if isinstance(audio, (list, tuple)) else audio
            if hasattr(a, "detach"): a = a.detach().float().cpu().numpy()
            a = a.reshape(-1)
            os.makedirs(os.path.dirname(os.path.abspath(it["out"])), exist_ok=True)
            sf.write(it["out"], a, int(job.get("sample_rate", 24000)), subtype="PCM_16")
            ok += 1
            print(f"TTS {k}/{len(items)} {it.get('id', k)} {len(a) / 24000:.2f}s ({time.time() - t1:.1f}s)", flush=True)
        except Exception as e:      # one bad line must not lose the others
            bad += 1
            msg = str(e).replace("\n", " ")[:300]
            print(f"TTS ERROR {it.get('id', k)} {msg}", flush=True)
            traceback.print_exc(file=sys.stderr)
    print(f"TTS DONE {ok} {bad}", flush=True)
    return 0 if bad == 0 else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
