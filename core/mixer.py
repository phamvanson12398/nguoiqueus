"""Mixer: places SFX on frames, beds, auto sound rules (cuts, expression pops,
caption ticks, gesture swishes), writes the wav and wires the sequencer + mp4 output."""
import os
import wave
import numpy as np
from . import ctx
from .sfx import SR, SFX
from .timing import near

class Mix:
    def __init__(self, total_sec, fps=30):
        self.fps = fps; self.buf = np.zeros(int(SR * total_sec) + SR)
    def add(self, sig, frame, gain=1.0):
        i = int((frame - 1) / self.fps * SR); j = min(len(self.buf), i + len(sig))
        if i < len(self.buf): self.buf[i:j] += gain * sig[:j - i]
    def sfx(self, name, frame, gain=0.6, **kw):
        self.add(SFX[name](**kw), frame, gain)
    def bed(self, sig, gain=1.0):
        n = min(len(sig), len(self.buf)); self.buf[:n] += gain * sig[:n]
    def write(self, path, total_sec):
        x = self.buf[:int(SR * total_sec)]
        x = x / max(1.0, np.abs(x).max() / 0.89)
        with wave.open(path, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes((x * 32767).astype(np.int16).tobytes())
        return path


def auto_sfx(mix, cuts, chars, caps, avoid_cuts=(), gain=1.0, gesture_chars=None):
    """whoosh before each cut (not within 8 f of an avoid frame), pop on expression changes,
    tick on each caption, swish on gesture onsets.  Call order matters (shared noise generator)."""
    for c_ in cuts:
        if not near(c_, avoid_cuts, 8): mix.sfx("whoosh", c_ - 5, 0.22 * gain)
    pops = sorted({fr for ch in chars for fr, _ in ch.expr_table[1:]})
    last = -99
    for fr in pops:
        if fr - last > 4 and not near(fr, cuts, 2): mix.sfx("pop", fr, 0.2 * gain); last = fr
    for c in caps:
        mix.sfx("tick", c[1], 0.07 * gain)
    GESTURES = {}
    for ch in (gesture_chars if gesture_chars is not None else chars):
        for side, hist in ch.hist.items():
            sp = [0.0] + [abs(b_[1] - a_[1]) for a_, b_ in zip(hist, hist[1:])]
            for i in range(6, len(sp)):
                if sp[i] > 0.08 and max(sp[i - 6:i]) < 0.08:
                    GESTURES.setdefault(ch.name, set()).add(hist[i][0])
    for who, frames in GESTURES.items():
        last = -99
        for fr in sorted(frames):
            if fr - last > 8 and not near(fr, cuts, 2): mix.sfx("swish", fr - 2, 0.25 * gain); last = fr
    return GESTURES


def attach_audio(wav_path, vo_path=None, sfx_volume=None):
    """sfx/music strip on channel 1, voice on channel 2 (if the file exists)"""
    sc = ctx.sc
    has_vo = bool(vo_path) and os.path.exists(vo_path)
    sed = sc.sequence_editor_create()
    st_ = sed.strips.new_sound("sfx_music", wav_path, 1, 1)
    st_.volume = sfx_volume if sfx_volume is not None else (0.8 if has_vo else 1.0)
    if has_vo:
        sed.strips.new_sound("voice", vo_path, 2, 1)
    return sed


def set_video_output(path):
    sc = ctx.sc
    ims = sc.render.image_settings
    ims.media_type = 'VIDEO'
    ims.file_format = 'FFMPEG'
    sc.render.ffmpeg.format = 'MPEG4'
    sc.render.ffmpeg.codec = 'H264'
    sc.render.ffmpeg.constant_rate_factor = 'HIGH'
    sc.render.ffmpeg.audio_codec = 'AAC'
    sc.render.ffmpeg.audio_bitrate = 192
    sc.render.filepath = path
