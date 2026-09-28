#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""A video's waveform.json: the one cleaner, the one writer, and the hold.

    rate, peaks = wavefile.clean(rate, peaks)     # ValueError with a sentence
    wavefile.write(video_dir, rate, peaks)        # waveform.json, atomically
    wavefile.hold(job, rate, peaks)               # keep them until a video exists
    wavefile.adopt(job, video_dir)                # ... and put them beside it

WHY A HOLD.  A video that is being added has no directory yet, and a
waveform is only ever written into one (serve.py's /api/waveform answers 404
until video.json exists).  A transcription job, though, has its peaks the
moment it finishes -- the ones the browser made from the very capture the
words came from -- and the person may spend an hour on the prompt before the
video exists.  So the peaks wait in youtube/videos/.waveforms/<job>.json, in
the same shape waveform.json has, and the three doors that create a video
take the job's token and move them in beside the new video.

A DOT-DIRECTORY, LIKE .trash/ AND .staging-*: never listed as a video,
never served (static_ok refuses every dot component), never bundled and
never backed up.  It sits on the same filesystem as the videos, so the move
in is one os.replace.  Its path is worked out from ytpages.VIDEOS AT THE
MOMENT OF ASKING, so every harness that points VIDEOS at a temporary tree
points the hold there too.

NO NEW FORMAT.  What is held, and what is adopted, is `{"rate": 20.0,
"peaks": [...]}` written by the same code that /api/waveform runs, so the
FORMATS row of waveform.json, its number and its wording are untouched.

WHOSE PEAKS.  Only a YouTube job holds any: the browser's own, made from the
capture the words were made from.  A film has no waveform written (the
owner's decision): the player draws it from the film itself.

Standard library only.
"""
import io
import json
import os
import re
import time

HERE = os.path.dirname(os.path.realpath(__file__))
YT = os.path.dirname(HERE)                        # youtube/
HOLD = ".waveforms"
KEEP_DAYS = 30                                    # a hold nobody adopted goes after this
MAX_PEAKS = 2000000                               # 28 hours at 20 a second
# The job token sttjobs makes (secrets.token_urlsafe(12) is sixteen of these).
# Checked HERE as well, because it becomes part of a file name.
TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{16}\Z")     # \Z: `$` lets a newline follow


def clean(rate, peaks):
    """(rate, peaks) as they may be kept -> (float rate, peaks each 0..1 with
    three decimals).  The limits and the sentences are the ones serve.py's
    /api/waveform has always had: the door and the hold cannot disagree."""
    if not isinstance(peaks, list) or not peaks:
        raise ValueError("no waveform was sent")
    if len(peaks) > MAX_PEAKS:
        raise ValueError("that waveform is too fine to keep")
    try:
        rate = float(rate)
    except (TypeError, ValueError):
        raise ValueError("a waveform says how many numbers a second it has")
    if not 1 <= rate <= 200:
        raise ValueError("a waveform carries between 1 and 200 numbers a second")
    out = []
    for v in peaks:
        try:
            f = float(v)
        except (TypeError, ValueError):
            f = 0.0
        out.append(round(min(1.0, max(0.0, f)), 3))
    return rate, out


def write(directory, rate, peaks):
    """waveform.json beside a video, atomically (a half file is never read).
    `rate` and `peaks` come out of clean()."""
    path = os.path.join(directory, "waveform.json")
    tmp = path + ".tmp"
    with io.open(tmp, "w", encoding="utf-8") as f:
        json.dump({"rate": rate, "peaks": peaks}, f, ensure_ascii=False)
    os.replace(tmp, path)
    return path


def read(path):
    """A waveform file -> (rate, peaks) cleaned, or None when it is not one."""
    try:
        with io.open(path, encoding="utf-8") as f:
            doc = json.load(f)
        if not isinstance(doc, dict):
            return None
        return clean(doc.get("rate"), doc.get("peaks"))
    except (OSError, ValueError, TypeError, RecursionError):
        return None


# ---------------------------------------------------------------------- the hold
def _videos():
    """youtube/videos/, as the running server has it (a test moves it)."""
    try:
        import ytpages
        return ytpages.VIDEOS
    except Exception:                                        # noqa: BLE001
        return os.path.join(YT, "videos")


def hold_dir(videos=None):
    return os.path.join(videos or _videos(), HOLD)


def hold_path(token, videos=None):
    """Where a job's peaks wait -> the path, or None for anything that is
    not a token this toolbox made (it would become part of a file name)."""
    if not isinstance(token, str) or not TOKEN_RE.match(token):
        return None
    return os.path.join(hold_dir(videos), token + ".json")


def hold(token, rate, peaks, videos=None):
    """Keep a job's peaks for the video that will be made from it -> the
    number of numbers kept.  ValueError says why not (a bad token, or what
    clean() refuses)."""
    path = hold_path(token, videos)
    if path is None:
        raise ValueError("that is not a transcription job")
    rate, peaks = clean(rate, peaks)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with io.open(tmp, "w", encoding="utf-8") as f:
        json.dump({"rate": rate, "peaks": peaks}, f, ensure_ascii=False)
    os.replace(tmp, path)
    return len(peaks)


def held(token, videos=None):
    path = hold_path(token, videos)
    return bool(path) and os.path.isfile(path)


def drop(token, videos=None):
    """Let a job's peaks go (it was cancelled, or adopted)."""
    path = hold_path(token, videos)
    if not path:
        return False
    gone = False
    for p in (path, path + ".tmp"):
        try:
            os.unlink(p)
            gone = True
        except OSError:
            pass
    return gone


def adopt(token, video_dir, videos=None):
    """Move a job's held peaks in beside a video that now exists.

    -> {"kept": True, "buckets": n}, or None when there is nothing to
    adopt: no token, a token that is not one, a job that held nothing, or a
    file that is not a waveform.  NEVER RAISES for that: a door that made a
    video must not fail because the picture of its sound was not there, and
    the person can still draw it from the player.  The hold is deleted only
    after the copy beside the video is in place.
    """
    path = hold_path(token, videos)
    if path is None or not os.path.isfile(path):
        return None
    got = read(path)                # validated again: the file is a stranger
    if got is None:
        drop(token, videos)
        return None
    rate, peaks = got
    try:
        write(video_dir, rate, peaks)
    except OSError:
        return None
    drop(token, videos)
    return {"kept": True, "buckets": len(peaks)}


def sweep(days=KEEP_DAYS, videos=None, now=None):
    """Holds nobody adopted for `days` days, and any half-written one, let
    go -> how many.  Asked at every start (serve.main): the folder is not
    made here, and not looked into if it is not there."""
    where = hold_dir(videos)
    now = time.time() if now is None else now
    n = 0
    try:
        names = os.listdir(where)
    except OSError:
        return 0
    for name in names:
        p = os.path.join(where, name)
        try:
            if os.path.isfile(p) and (name.endswith(".tmp")
                                      or now - os.path.getmtime(p) > days * 86400):
                os.unlink(p)
                n += 1
        except OSError:
            pass
    return n
