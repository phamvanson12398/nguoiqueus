"""Image sequence (+ audio) -> mp4 with ffmpeg.  Works with gaps (render 'on twos': every 2nd frame is held for 2).

    python tools/encode.py <frames_dir> <audio.wav|-> <out.mp4> [--fps 30] [--step 2] [--first 1] [--last N] [--crf 18]

The builder writes frames as f_0001.png ...; missing frames reuse the previous image, so a render with frame_step=2
(or an interrupted one that is resumed later) still gives a video of the exact length.
"""
import os, re, subprocess, sys, shutil


def encode(frames_dir, audio, out, fps=30, first=1, last=None, crf=18, log=print):
    if not shutil.which("ffmpeg"): raise RuntimeError("cần ffmpeg để ghép video")
    files = {int(m.group(1)): f for f in os.listdir(frames_dir) if (m := re.fullmatch(r"f_(\d{4,6})\.(png|jpg)", f))}
    if not files: raise RuntimeError(f"không có khung nào trong {frames_dir}")
    last = last or max(files)
    lst = os.path.join(frames_dir, "_concat.txt"); held = 0; prev = None
    with open(lst, "w", encoding="utf-8") as fh:
        runs = []
        for f in range(first, last + 1):
            if f in files: prev = files[f]
            elif prev is None:
                nxt = next((files[g] for g in range(f, last + 1) if g in files), None); prev = nxt
                held += 1
            else: held += 1
            if runs and runs[-1][0] == prev: runs[-1][1] += 1
            else: runs.append([prev, 1])
        for name, n in runs:
            fh.write(f"file '{name}'\nduration {n / fps:.6f}\n")
        fh.write(f"file '{runs[-1][0]}'\n")             # concat demuxer needs the last file twice
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst]
    if audio and audio != "-" and os.path.exists(audio): cmd += ["-i", audio]
    cmd += ["-r", str(fps), "-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p"]
    if audio and audio != "-" and os.path.exists(audio): cmd += ["-c:a", "aac", "-b:a", "192k", "-shortest"]
    cmd += ["-movflags", "+faststart", out]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=frames_dir)
    if r.returncode: raise RuntimeError("ffmpeg: " + r.stderr[-800:])
    log(f"ENCODED {last - first + 1} khung ({len(files)} ảnh, {held} khung giữ lại) -> {out}")
    return out


if __name__ == "__main__":
    a = sys.argv[1:]
    opt = {a[i][2:]: a[i + 1] for i in range(3, len(a) - 1) if a[i].startswith("--")}
    encode(a[0], a[1], a[2], fps=int(opt.get("fps", 30)), first=int(opt.get("first", 1)),
           last=int(opt["last"]) if "last" in opt else None, crf=int(opt.get("crf", 18)))
