"""Replace frames A-B of a full render with a re-rendered part (after fixing one sequence).

    python tools/splice.py full.mp4 part.mp4 A B [out.mp4]

The part must cover exactly frames A-B (builder.py --render --frames A-B writes parts/<name>_AAAA-BBBB.mp4,
A and B are read from that name when omitted).  Video is re-encoded once (H.264, CRF 16); the audio of the
full render is kept unchanged (sound does not depend on the picture).  Needs ffmpeg on PATH
(Windows: `winget install ffmpeg`).  Without out.mp4 the full file is replaced and the old one kept as *_before.mp4.
"""
import os, re, shutil, subprocess, sys


def find_ffmpeg():
    return shutil.which("ffmpeg")


def splice(full, part, a=None, b=None, out=None, fps=30):
    ff = find_ffmpeg()
    if not ff: raise RuntimeError("cần ffmpeg (Windows: winget install ffmpeg, rồi mở lại cửa sổ)")
    if a is None or b is None:
        m = re.search(r"_(\d{4,})-(\d{4,})\.mp4$", part)
        if not m: raise ValueError("không đọc được khung A-B từ tên file phần; truyền A B vào lệnh")
        a, b = int(m.group(1)), int(m.group(2))
    a, b = int(a), int(b)
    replace = out is None
    out = out or full[:-4] + "_spliced.mp4"
    t_a, t_b = (a - 1) / fps, b / fps
    flt = (f"[0:v]trim=end={t_a},setpts=PTS-STARTPTS[v0];"
           f"[1:v]setpts=PTS-STARTPTS[v1];"
           f"[0:v]trim=start={t_b},setpts=PTS-STARTPTS[v2];"
           + (f"[v0][v1][v2]concat=n=3:v=1:a=0[v]" if a > 1 else f"[v1][v2]concat=n=2:v=1:a=0[v]"))
    if a <= 1: flt = flt.replace(f"[0:v]trim=end={t_a},setpts=PTS-STARTPTS[v0];", "")
    cmd = [ff, "-v", "error", "-y", "-i", full, "-i", part, "-filter_complex", flt, "-map", "[v]", "-map", "0:a?",
           "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p", "-r", str(fps), "-c:a", "copy", out]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0: raise RuntimeError("ffmpeg lỗi: " + p.stderr[-800:])
    if replace:
        before = full[:-4] + "_before.mp4"
        if os.path.exists(before): os.remove(before)
        os.replace(full, before); os.replace(out, full); out = full
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) < 2: print(__doc__); sys.exit(1)
    full, part = args[0], args[1]
    a = int(args[2]) if len(args) > 2 else None; b = int(args[3]) if len(args) > 3 else None
    print("OK ->", splice(full, part, a, b, args[4] if len(args) > 4 else None))
