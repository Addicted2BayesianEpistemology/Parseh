#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Audio files: what a recording is by its bytes, what it may be called, and
the three things ffmpeg does with one when the machine has it.

    import audiofile
    ext = audiofile.kind(data, "word.mp3")      # ".mp3", or None: not audio
    name = audiofile.clean_stem("Hello World!")  # "hello-world"
    audiofile.extract(src, 12.3, 13.1, "/tmp/clip")  # -> "/tmp/clip.mp3"
    audiofile.peaks(src, 10.0, 15.0, 400)        # [0.0 .. 1.0] * 400

Every door that takes audio in -- a studio document's `audio/` folder, an
exercise deck's, the clip tray the book reader and the video player cut into
-- asks this module, so the list of formats is written once:

    mp3  m4a  aac  ogg  oga  opus  wav  flac  webm

The EXTENSION FOLLOWS THE BYTES, as a picture's does (store._img_kind): a file
called `x.mp3` holding a WAV is stored as `x.wav`, because a browser and Anki
both believe the extension before the content.  The Ogg family is the one
place the name decides between equals: `.ogg`, `.oga` and `.opus` are all
`OggS`, so a name already in the family keeps its spelling, and otherwise an
Opus stream is `.opus` and anything else `.ogg`.

ffmpeg is optional (install.sh reports it).  Without it nothing is cut on the
server: `have_ffmpeg()` says so, and the pages record the clip in the browser
instead.  With it, `extract` cuts [start, end] out of any file ffmpeg reads --
a narration or a film -- into the best format the build can write (mp3, else
m4a, else wav), and `transcode` turns a browser's WAV or WebM into the same.

Standard library only; lib/ imports nothing outside itself.
"""
import os
import re
import shutil
import subprocess
import unicodedata

EXTS = ("mp3", "m4a", "aac", "ogg", "oga", "opus", "wav", "flac", "webm")

# a stored audio file's name: lower case, like a picture's (store.IMG_NAME_RE)
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._\-]*\.(?:%s)$" % "|".join(EXTS))

# a path the dialect may name.  mdparser keeps its own copy (exlex is usable
# on its own), and tests/test_audiofile.py holds the two together.
PATH_RE = re.compile(r"^audio/[A-Za-z0-9][A-Za-z0-9._\-]*\.(?:%s)$" % "|".join(EXTS), re.I)

# under the servers' 32 MB body ceiling, so an upload never needs spooling
MAX_BYTES = 30 * 1024 * 1024

# fixed here, not left to the platform's mimetypes: Windows' registry and
# Python's own table disagree about .opus, .wav and .webm
MIME = {
    "mp3": "audio/mpeg", "m4a": "audio/mp4", "aac": "audio/aac",
    "ogg": "audio/ogg", "oga": "audio/ogg", "opus": "audio/ogg",
    "wav": "audio/wav", "flac": "audio/flac", "webm": "audio/webm",
}

# what the file picker offers (an <input accept>)
ACCEPT = "audio/*," + ",".join("." + e for e in EXTS)

HUMAN = "MP3, M4A, AAC, Ogg, Opus, WAV, FLAC and WebM"

_OGG = (".ogg", ".oga", ".opus")

# MPEG audio frame headers (ISO 11172-3 / 13818-3): kbit/s by (MPEG-1?, layer)
# and bitrate index 1..14, sample rates by version bits and index 0..2
_MPEG_KBPS = {
    (True, 1): (32, 64, 96, 128, 160, 192, 224, 256, 288, 320, 352, 384, 416, 448),
    (True, 2): (32, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384),
    (True, 3): (32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320),
    (False, 1): (32, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224, 256),
    (False, 2): (8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160),
    (False, 3): (8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160),
}
_MPEG_RATES = {3: (44100, 48000, 32000), 2: (22050, 24000, 16000), 0: (11025, 12000, 8000)}
# ADTS sampling_frequency_index 0..12
_ADTS_RATES = 13


def _mpeg_frame(head, at):
    """((version, layer, rate), frame length) of an MPEG audio frame header at
    `at`, or None: the sync, a version and a layer that exist, a bitrate that
    is neither "free" nor the forbidden 15, a sample rate that is not the
    reserved 3, an emphasis that is not the reserved 2."""
    if at + 4 > len(head) or head[at] != 0xFF or (head[at + 1] & 0xE0) != 0xE0:
        return None
    version = (head[at + 1] >> 3) & 3          # 3 MPEG-1, 2 MPEG-2, 0 MPEG-2.5
    layer = 4 - ((head[at + 1] >> 1) & 3)      # bits 11 -> I, 10 -> II, 01 -> III
    bitrate, rate = head[at + 2] >> 4, (head[at + 2] >> 2) & 3
    if version == 1 or layer == 4 or bitrate in (0, 15) or rate == 3 \
            or (head[at + 3] & 3) == 2:
        return None
    kbps = _MPEG_KBPS[(version == 3, layer)][bitrate - 1]
    hz = _MPEG_RATES[version][rate]
    pad = (head[at + 2] >> 1) & 1
    if layer == 1:
        size = (12 * kbps * 1000 // hz + pad) * 4
    else:
        per = 144 if version == 3 or layer == 2 else 72
        size = per * kbps * 1000 // hz + pad
    return (version, layer, rate), size


def _adts_frame(head, at):
    """((profile, rate, channels), frame length) of an ADTS header at `at`,
    or None: the sync, layer 00, a sample rate index that exists, a frame
    longer than its own header."""
    if at + 7 > len(head) or head[at] != 0xFF or (head[at + 1] & 0xF6) != 0xF0:
        return None
    rate = (head[at + 2] >> 2) & 0xF
    size = ((head[at + 3] & 3) << 11) | (head[at + 4] << 3) | (head[at + 5] >> 5)
    if rate >= _ADTS_RATES or size < (7 if head[at + 1] & 1 else 9):
        return None
    return ((head[at + 2] >> 6), rate, ((head[at + 2] & 1) << 2) | (head[at + 3] >> 6)), size


def _two_frames(head, frame):
    """Whether `head` starts with a frame header (`frame(head, at)`) that is
    followed, where its length says, by a second one of the same stream.  A
    header alone is four bytes any file may start with -- a UTF-16 text's
    byte-order mark FF FE reads as one -- and a stream of frames is what a
    recording is."""
    first = frame(head, 0)
    if first is None:
        return False
    second = frame(head, first[1])
    return second is not None and second[0] == first[0]


def kind(data, name=""):
    """The extension (with its dot) the bytes are, or None when they are not
    audio this toolbox stores.

    The bytes looked at are the first 4096 (all a caller holding a large file
    has to read): enough for every container's signature, and for the two
    first frames of an MPEG or ADTS stream with no tag in front, which is how
    those are known.  What the head cannot show -- an MP4 holding no sound
    track, a stream broken further on -- takes decoding (clips.plays)."""
    head = bytes(data[:4096]) if data else b""
    if len(head) < 12:
        return None
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return ".wav"
    if head[:4] == b"fLaC":
        return ".flac"
    if head[:4] == b"OggS":
        ext = os.path.splitext((name or "").lower())[1]
        if ext in _OGG:
            return ext
        return ".opus" if b"OpusHead" in head[:512] else ".ogg"
    if head[:4] == b"\x1a\x45\xdf\xa3":
        # Matroska; only its WebM profile is a format browsers promise
        return ".webm" if b"webm" in head[:64] else None
    if head[4:8] == b"ftyp":
        return ".m4a"
    if head[:3] == b"ID3":
        return ".mp3"
    if head[0] == 0xFF and (head[1] & 0xE0) == 0xE0:
        if (head[1] & 0xF6) == 0xF0:          # ADTS: sync + layer 00
            return ".aac" if _two_frames(head, _adts_frame) else None
        if _two_frames(head, _mpeg_frame):    # MPEG audio layer I-III
            return ".mp3"
    return None


def mime_for(name):
    """The Content-Type of a stored audio name, or None."""
    ext = os.path.splitext(name or "")[1].lower().lstrip(".")
    return MIME.get(ext)


def clean_stem(name, fallback="audio", limit=80):
    """A file name's stem made safe to store: NFKD-folded to ASCII, lower
    case, runs of anything else become one '-'.  The extension is dropped;
    `kind` decides it."""
    stem = os.path.splitext(os.path.basename(name or ""))[0]
    stem = unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode()
    stem = re.sub(r"[^a-z0-9._\-]+", "-", stem.lower()).strip("-._")
    stem = stem[:limit].strip("-._")
    return stem or fallback


def free_name(dest, stem, ext, data=None):
    """The first of `stem.ext`, `stem-2.ext`, ... that is free in `dest`, or
    that already holds exactly `data` (so the same file uploaded twice is
    stored once)."""
    n = 1
    while True:
        cand = "%s%s%s" % (stem, "" if n == 1 else "-%d" % n, ext)
        path = os.path.join(dest, cand)
        if not os.path.exists(path):
            return cand
        if data is not None and os.path.isfile(path):
            try:
                if os.path.getsize(path) == len(data):
                    with open(path, "rb") as f:
                        if f.read() == bytes(data):
                            return cand
            except OSError:
                pass
        n += 1


# ------------------------------------------------------------------ ffmpeg

def ffmpeg():
    """The ffmpeg executable, or None."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    for p in ("/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg"):
        if os.path.exists(p):
            return p
    return None


def have_ffmpeg():
    return ffmpeg() is not None


_ENCODERS = {}


def encoders():
    """The audio encoders this machine's ffmpeg has (a set of names)."""
    exe = ffmpeg()
    if not exe:
        return set()
    if exe not in _ENCODERS:
        names = set()
        try:
            out = subprocess.run([exe, "-hide_banner", "-encoders"],
                                 capture_output=True, text=True, timeout=30).stdout
            for line in out.splitlines():
                m = re.match(r"^\s*A\S*\s+(\S+)", line)
                if m:
                    names.add(m.group(1))
        except (OSError, subprocess.SubprocessError):
            pass
        _ENCODERS[exe] = names
    return _ENCODERS[exe]


def best_output():
    """(extension, codec arguments) of the best format ffmpeg can write here:
    mp3 plays in every browser and in Anki on every device; m4a is the
    fallback every ffmpeg build has; wav needs no encoder at all."""
    enc = encoders()
    if "libmp3lame" in enc:
        return ".mp3", ["-c:a", "libmp3lame", "-q:a", "4"]
    if "aac" in enc:
        return ".m4a", ["-c:a", "aac", "-b:a", "128k"]
    return ".wav", ["-c:a", "pcm_s16le"]


class AudioError(Exception):
    """ffmpeg is missing or refused the file; the message says which."""


def _run(args, timeout=300):
    try:
        r = subprocess.run(args, capture_output=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as e:
        raise AudioError("ffmpeg could not run: %s" % e)
    if r.returncode != 0:
        tail = (r.stderr or b"").decode("utf-8", "replace").strip().splitlines()[-3:]
        raise AudioError("ffmpeg failed: %s" % (" ".join(tail) or "exit %d" % r.returncode))
    return r.stdout


# ffmpeg's MP3 decoder gives SILENCE for the first frames after a seek -- 50
# to 140 ms, the first consonant of a word cut tight.  So a job seeks fast to
# this far before the start and decodes the rest of the way; the samples at
# `start` are then the file's own, in every format.
PREROLL = 1.0


def _seek(src, start):
    """ffmpeg's input arguments for reading `src` from `start` seconds, and
    how far into the decoded stream `start` lies (the filters count from
    there: the output seek trims after them)."""
    start = round(start, 3)
    pre = round(min(start, PREROLL), 3)
    fast = round(start - pre, 3)
    args = (["-ss", "%.3f" % fast] if fast > 0 else []) + ["-i", src]
    return args + ["-ss", "%.3f" % pre], pre


def extract(src, start, end, out_base, fade=0.008):
    """Cut [start, end] seconds out of `src` (any file ffmpeg reads: a
    narration, a film) into `out_base` + the best extension; returns the
    written path.  A few milliseconds of fade at both edges keep the cut from
    clicking."""
    exe = ffmpeg()
    if not exe:
        raise AudioError("ffmpeg is not installed")
    start, end = float(start), float(end)
    if not (end > start >= 0):
        raise AudioError("the end must come after the start")
    dur = end - start
    ext, codec = best_output()
    out = out_base + ext
    f = min(fade, dur / 4)
    seek, at = _seek(src, start)
    af = "afade=t=in:st=%.3f:d=%.3f,afade=t=out:st=%.3f:d=%.3f" % (
        at, f, at + max(0.0, dur - f), f)
    _run([exe, "-nostdin", "-v", "error", "-y"] + seek +
         ["-t", "%.3f" % dur, "-vn", "-sn", "-dn", "-map_metadata", "-1",
          "-af", af] + codec + [out])
    if not os.path.isfile(out) or os.path.getsize(out) == 0:
        raise AudioError("ffmpeg wrote nothing: is there sound at %.2f s?" % start)
    return out


def transcode(src, out_base):
    """Re-encode a whole file (a browser's WAV or WebM recording) into the
    best format; returns the written path."""
    exe = ffmpeg()
    if not exe:
        raise AudioError("ffmpeg is not installed")
    ext, codec = best_output()
    out = out_base + ext
    _run([exe, "-nostdin", "-v", "error", "-y", "-i", src, "-vn", "-sn", "-dn",
          "-map_metadata", "-1"] + codec + [out])
    if not os.path.isfile(out) or os.path.getsize(out) == 0:
        raise AudioError("ffmpeg wrote nothing")
    return out


def duration(src):
    """Seconds, from ffprobe when there is one, else from a WAV header, else
    None."""
    exe = ffmpeg()
    probe = os.path.join(os.path.dirname(exe), "ffprobe") if exe else None
    if probe and (os.path.exists(probe) or os.path.exists(probe + ".exe")):
        try:
            out = subprocess.run([probe, "-v", "error", "-show_entries", "format=duration",
                                  "-of", "default=noprint_wrappers=1:nokey=1", src],
                                 capture_output=True, text=True, timeout=60).stdout.strip()
            return float(out)
        except (OSError, subprocess.SubprocessError, ValueError):
            pass
    try:
        import wave
        with wave.open(src, "rb") as w:
            return w.getnframes() / float(w.getframerate())
    except Exception:
        return None


def peaks(src, start, end, buckets=400, rate=8000):
    """The loudness of [start, end] in `buckets` equal slices, each 0..1 (the
    peak of the slice over the peak of the window), for drawing a waveform.
    Decoded by ffmpeg at a low rate, so a five-second window costs 80 KB."""
    exe = ffmpeg()
    if not exe:
        raise AudioError("ffmpeg is not installed")
    start, end = max(0.0, float(start)), float(end)
    if not end > start:
        raise AudioError("the end must come after the start")
    buckets = max(1, min(4000, int(buckets)))
    raw = _run([exe, "-nostdin", "-v", "error"] + _seek(src, start)[0] +
               ["-t", "%.3f" % (end - start), "-vn", "-ac", "1", "-ar", str(rate),
                "-f", "s16le", "-"], timeout=120)
    n = len(raw) // 2
    if n == 0:
        return [0.0] * buckets
    import array
    samples = array.array("h")
    samples.frombytes(raw[:n * 2])
    if os.sys.byteorder == "big":
        samples.byteswap()
    total = int(round((end - start) * rate)) or n
    out = []
    for b in range(buckets):
        lo = int(b * total / buckets)
        hi = max(lo + 1, int((b + 1) * total / buckets))
        seg = samples[lo:min(hi, n)]
        out.append(max((abs(s) for s in seg), default=0))
    top = max(out) or 1
    return [round(v / top, 3) for v in out]
