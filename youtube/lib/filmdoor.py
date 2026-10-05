#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""The three doors of a video's own media that are not "name it by its path".

    POST /youtube/api/film/look   {path}                 what a file is, before it is added
                                  {name, bytes}          or a file about to be sent: the kind and the room
    POST /youtube/api/film        ?name=<file>[&video=<id>]   the file itself, SENT as the body
    POST /youtube/api/film/wave   {video}                the shape of its sound, for the bar

THE PATH IS UNTOUCHED.  A film or a sound is still named by its path on this
machine (ytpages.check_film, attach_film, local_target and every route that takes
one), and hard-linked, which costs no copy for a two-hour film.  SENDING is one
more way to arrive at a path -- for another device, and for Windows, where there
is no path to type -- and not a second mechanism:

  * with no `video`, the file is written whole into youtube/videos/.incoming/
    <token>/ and the answer is the PATH it now has.  The page puts it in the
    path box, and from there every door is the one it always was: the prompt, the
    speech to text, "start it empty", the checked answer.  Adding the video
    links it into the video's folder and the waiting copy goes (ytpages.attach_film).
  * with `video`, the file replaces the media of a video that is a file on this
    machine -- the one whose film was moved away, which the player says is "not
    here any more" -- and is settled the way a film attached by path is.

WHOLE OR NOT AT ALL.  The body is streamed to disk in megabyte pieces and never
held, to a name ending `.part` that no page, no listing and no bundle reads as
media, and renamed only when the last byte is in and the file has been looked at.
There is no ceiling on its size but the disk's, which is said BEFORE it starts
(the page asks /api/film/look {name, bytes} first, and is told what is free; a
refusal that came after the body had begun would reach it as a broken connection
and not as words).  Every refusal is a sentence, and the body of a refused request
is never read.

Who may write, and from where, is not decided here: serve.py's dispatcher refuses
any write that does not come from a Parseh page (lib/crosssite.py) and any device
that has not been let in (lib/network.py) before a route is chosen.
"""
import math
import os
import re
import shutil
import sys
import threading
import traceback
import uuid

LIB = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(os.path.dirname(LIB))
for _p in (LIB, os.path.join(ROOT, "lib")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import activity     # noqa: E402  the list of what the computer is doing: bytes counted as they arrive
import audiofile    # noqa: E402  ffmpeg's door, for the picture of the sound
import bundle       # noqa: E402  which files may be a video's media
import filmkind     # noqa: E402  what a file is, and the playable copy
import ytpages      # noqa: E402  the video shelf, and the path door this is one more way into

# a client that goes away half way is ordinary traffic, not a fault (serve.GONE's list)
GONE = (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, TimeoutError)
PIECE = 1 << 20
# kept free on the disk beyond the file itself: a playable copy of a sound is
# made beside it, and the checks and the answer take a little too
RESERVE = 64 << 20
NAME_MAX = 80

_BUSY = set()           # the videos a file is being sent to now
_LOCK = threading.Lock()


def _say(h, ok, fields, status=200):
    return h.send_json(dict(fields, ok=ok), status)


def _refuse(h, why, status=400):
    """Refused BEFORE the body is read: the connection is not used again, or
    the unread body would be taken for the next request."""
    h.close_connection = True
    return _say(h, False, {"error": why}, status)


def _kinds_said():
    return ("a video (%s) or a sound (%s)"
            % (", ".join(bundle.VIDEO_EXTS),
               ", ".join(e for e in bundle.SOUND_EXTS if e not in bundle.VIDEO_EXTS)))


def _mb(n):
    return "%d MB" % max(1, round(n / 1e6)) if n >= 1e6 else "%d kB" % max(1, round(n / 1e3))


def _free(where):
    """The bytes free on the disk `where` lives on (the nearest directory that
    exists), or None where that cannot be said."""
    while not os.path.isdir(where) and os.path.dirname(where) != where:
        where = os.path.dirname(where)
    try:
        return shutil.disk_usage(where).free
    except OSError:
        return None


def _no_room(n, free):
    """The refusal, in words, when `n` bytes and a little more do not fit in
    `free`; "" when they do (or when it cannot be said, which is not a refusal)."""
    if free is not None and free < n + RESERVE:
        return ("there is no room on this computer's disk for it: it needs %s and %s is free"
                % (_mb(n + RESERVE), _mb(free)))
    return ""


# ----------------------------------------------------------------- what a file is
def look(h):
    """What a file is, before the video is added.  Writes nothing.

      {path}          a file on this machine, named the way every door names one:
                      its kind, its size, its length where ffprobe can say, and what
                      will be done if a browser cannot play it
      {name, bytes}   a file ABOUT TO BE SENT: whether this computer takes that kind
                      and has the room, asked before a byte is sent -- a refusal
                      that came after the body had begun would reach the page as a
                      broken connection and not as words
    """
    try:
        data = ytpages._json_in(h, 1 << 16)
    except ValueError as e:
        return _say(h, False, {"error": str(e)}, 400)
    if isinstance(data.get("name"), str) and "path" not in data:
        ext = os.path.splitext(os.path.basename(data["name"]))[1].lower()
        n = data.get("bytes")
        if ext not in bundle.MEDIA_EXTS:
            return _say(h, False, {"error": "name the file with its extension: %s" % _kinds_said()}, 400)
        if isinstance(n, bool) or not isinstance(n, int) or n <= 0:
            return _say(h, False, {"error": "that file is empty: nothing would be sent"}, 400)
        free = _free(ytpages.VIDEOS)
        why = _no_room(n, free)
        if why:
            return _say(h, False, {"error": why}, 507)
        return _say(h, True, {"kind": filmkind.kind_of(ext), "ext": ext, "bytes": n, "free": free or 0})
    try:
        path, ext = ytpages.check_film(data.get("path"))
    except ValueError as e:
        return _say(h, False, {"error": str(e)}, 400)
    return _say(h, True, dict(filmkind.look(path, ext), name=os.path.basename(path)))


# ---------------------------------------------------------------- the file, sent
def _stem(name):
    """The sent file's name made safe to be a file's and the video's own
    (ytpages.local_id is named after it): audiofile.clean_stem's rule."""
    return audiofile.clean_stem(name, "film", NAME_MAX)


def receive(h, n):
    """The body of a POST /youtube/api/film, `n` bytes of it, into a file."""
    q = lambda k: (h.query.get(k) or [""])[0]
    raw = re.sub(r"[\x00-\x1f]", "", os.path.basename(q("name")))
    ext = os.path.splitext(raw)[1].lower()
    if ext not in bundle.MEDIA_EXTS:
        return _refuse(h, "name the file with its extension: %s" % _kinds_said())
    if n <= 0:
        return _refuse(h, "that file is empty: nothing was sent")
    vid = q("video").strip()
    meta = d = None
    if vid:
        meta, d = ytpages.find_video(vid)
        if meta is None:
            return _refuse(h, "no such video", 404)
        if not (bundle.film_at(d) or (ytpages.is_local_id(meta.get("id", ""))
                                      and not (meta.get("url") or "").strip())):
            return _refuse(h, "this video is on YouTube: a film or a sound is attached only "
                              "to a video that is a file on this machine")
    filmkind.sweep(ytpages.VIDEOS)
    if d:
        where, held = d, os.path.join(d, bundle.MEDIA_STEM + ext + ".part")
        key = os.path.realpath(d)
    else:
        token = uuid.uuid4().hex[:12]
        where = os.path.join(filmkind.staging(ytpages.VIDEOS), token)
        final = os.path.join(where, _stem(raw) + ext)
        held = final + ".part"
        key = token
    # the room was said to the person before they pressed (look), and is asked
    # again here for whoever did not ask: the disk is the only ceiling there is
    why = _no_room(n, _free(d or ytpages.VIDEOS))
    if why:
        return _refuse(h, why, 507)
    with _LOCK:
        if key in _BUSY:
            return _refuse(h, "a file is already being sent to this video: wait for it", 409)
        _BUSY.add(key)
    got = 0
    try:
        os.makedirs(where, exist_ok=True)
        with open(held, "wb") as f:
            while got < n:
                chunk = h.rfile.read(min(PIECE, n - got))
                if not chunk:
                    break
                f.write(chunk)
                got += len(chunk)
                activity.progress(getattr(h, "_act", None), done=got)
        if got != n:
            raise IOError("the upload was cut short (%s of %s) and nothing was kept"
                          % (_mb(got), _mb(n)))
        h._received()
        # LOOKED AT BEFORE IT IS KEPT: where ffprobe is installed a file it cannot
        # read is not a video or a sound whatever its name says, and is refused
        # now and not when the player is opened on it
        if filmkind.ffprobe() and filmkind.probe(held) is None:
            raise ValueError("that is not a video or a sound ffmpeg can read: it may be "
                             "damaged, or not what its name says")
        if d:
            done = filmkind.settle(d, held)
            return _say(h, True, dict(done, video=meta["id"],
                                      where="%s/v/%s/" % (ytpages.BASE, meta["id"])))
        os.replace(held, final)
        return _say(h, True, dict(filmkind.look(final, ext), path=os.path.abspath(final),
                                  name=os.path.basename(final), bytes=got))
    except GONE:
        h.close_connection = True
        _clean(held, where, d)
    except (OSError, ValueError) as e:
        h.close_connection = True      # the body may be half read
        _clean(held, where, d)
        full = isinstance(e, OSError) and getattr(e, "errno", None) == 28
        return _say(h, False, {"error": "the disk filled up while it was being written, and "
                                        "nothing was kept" if full else str(e)}, 400)
    except Exception as e:             # noqa: BLE001 - a request must never die without an answer
        traceback.print_exc()
        h.close_connection = True
        _clean(held, where, d)
        try:
            return _say(h, False, {"error": "%s: %s" % (type(e).__name__, e)}, 500)
        except GONE:
            return None
    finally:
        with _LOCK:
            _BUSY.discard(key)


def _clean(held, where, d):
    """What a refused or a broken send leaves goes: the part, and the waiting
    folder it was in -- never a video's own folder."""
    try:
        os.unlink(held)
    except OSError:
        pass
    if not d:
        try:
            os.rmdir(where)
        except OSError:
            pass


def sweep():
    """What was sent and never used, and what a stopped server left half
    written: cleared off the way in."""
    filmkind.sweep(ytpages.VIDEOS)


# ----------------------------------------------------------- the picture of the sound
_WAVES = {}             # (path, size, mtime, buckets) -> the answer; a few at most
_WAVES_MAX = 16
BUCKETS_MAX = 1500


def wave(h):
    """The shape of a video's own sound, whole, for the bar a sound is shown as.

    One loudness each, as many as asked for (the page's width): the file is read
    by ffmpeg once (audiofile.envelope, streamed, a long recording in parts at
    once), scaled so the loudest is 1 -- a quiet lesson still fills the bar --
    and remembered while the file is unchanged.  Without ffmpeg there is no
    picture to give, and the answer says so: the page draws a plain strip."""
    try:
        data = ytpages._json_in(h, 1 << 16)
    except ValueError as e:
        return _say(h, False, {"error": str(e)}, 400)
    meta, d = ytpages.find_video(data.get("video") if isinstance(data.get("video"), str) else "")
    if meta is None:
        return _say(h, False, {"error": "no such video"}, 404)
    film = bundle.film_at(d)
    if not film:
        return _say(h, False, {"error": "this video has no film or sound here"}, 400)
    if not audiofile.have_ffmpeg():
        return _say(h, False, {"error": "ffmpeg is not installed on this computer, so there "
                                        "is no picture of the sound to draw", "record": False}, 409)
    try:
        buckets = int(data.get("buckets") or 600)
    except (TypeError, ValueError):
        buckets = 600
    buckets = max(50, min(BUCKETS_MAX, buckets))
    src = os.path.join(d, film)
    try:
        st = os.stat(src)
    except OSError as e:
        return _say(h, False, {"error": "the film could not be read (%s)" % e}, 400)
    key = (src, st.st_size, st.st_mtime_ns, buckets)
    if key in _WAVES:
        return _say(h, True, _WAVES[key])
    seconds = audiofile.duration(src)
    if not seconds or not math.isfinite(seconds) or seconds <= 0:
        return _say(h, False, {"error": "ffmpeg could not tell how long this sound is"}, 400)
    rate = max(1, min(100, int(math.ceil(buckets / seconds))))
    try:
        values = audiofile.envelope(src, 0, seconds, rate)
    except audiofile.AudioError as e:
        return _say(h, False, {"error": str(e)}, 400)
    top = max(values) if values else 0
    peaks = [round(v / top, 3) if top > 0 else 0.0 for v in values]
    answer = {"rate": rate, "seconds": round(seconds, 3), "peaks": peaks}
    if len(_WAVES) >= _WAVES_MAX:
        _WAVES.pop(next(iter(_WAVES)))
    _WAVES[key] = answer
    return _say(h, True, answer)
