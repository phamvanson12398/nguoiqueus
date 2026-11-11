"""Normalise any common WAV to 16-bit PCM (what Python's `wave` module, align.py and Blender read).

AI voice tools often export 32-bit float, 24-bit or WAVE_FORMAT_EXTENSIBLE files; `wave` refuses
those.  to_pcm16(data: bytes) -> (bytes, info) keeps the sample rate and channels, converts the samples.
A file that is already plain 16-bit PCM is returned unchanged.
"""
import io, struct, wave
import numpy as np


def _chunks(data):
    if data[:4] != b"RIFF" or data[8:12] != b"WAVE": raise ValueError("không phải file WAV")
    i = 12
    while i + 8 <= len(data):
        cid = data[i:i + 4]; size = struct.unpack("<I", data[i + 4:i + 8])[0]
        body = data[i + 8:i + 8 + size]
        yield cid, body
        i += 8 + size + (size & 1)


def to_pcm16(data):
    fmt = raw = None
    for cid, body in _chunks(data):
        if cid == b"fmt ": fmt = body
        elif cid == b"data": raw = body
    if fmt is None or raw is None: raise ValueError("file WAV thiếu phần fmt/data")
    tag, ch, sr, _, align, bits = struct.unpack("<HHIIHH", fmt[:16])
    if tag == 0xFFFE and len(fmt) >= 26:                       # WAVE_FORMAT_EXTENSIBLE: real format in the sub-GUID
        tag = struct.unpack("<H", fmt[24:26])[0]
    info = {"format": {1: "PCM", 3: "float"}.get(tag, str(tag)), "bits": bits, "channels": ch, "rate": sr}
    if tag == 1 and bits == 16 and data[20:22] == b"\x01\x00":
        return data, dict(info, converted=False)
    raw = raw[:len(raw) - len(raw) % max(1, align)]
    if tag == 3 and bits in (32, 64):
        x = np.frombuffer(raw, "<f4" if bits == 32 else "<f8").astype(np.float64)
    elif tag == 1 and bits == 8:
        x = (np.frombuffer(raw, np.uint8).astype(np.float64) - 128) / 128
    elif tag == 1 and bits == 16:
        x = np.frombuffer(raw, "<i2").astype(np.float64) / 32768
    elif tag == 1 and bits == 24:
        b = np.frombuffer(raw, np.uint8).reshape(-1, 3).astype(np.int32)
        v = b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16); v = np.where(v >= 1 << 23, v - (1 << 24), v)
        x = v.astype(np.float64) / (1 << 23)
    elif tag == 1 and bits == 32:
        x = np.frombuffer(raw, "<i4").astype(np.float64) / 2147483648
    else:
        raise ValueError(f"chưa hỗ trợ WAV kiểu {info['format']} {bits}-bit; hãy xuất WAV PCM 16-bit")
    peak = np.abs(x).max() if x.size else 0
    if peak > 1.0: x = x / peak                                 # float files can exceed full scale
    pcm = np.clip(np.round(x * 32767), -32768, 32767).astype("<i2")
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(ch); w.setsampwidth(2); w.setframerate(sr); w.writeframes(pcm.tobytes())
    return out.getvalue(), dict(info, converted=True)
