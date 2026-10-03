#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""The transcription job: one at a time, on this computer, for the add page.

    started = sttjobs.start(source, lang, model, processing)   # -> {"job": token, ...}
    sttjobs.audio(token, offset, pcm, last)     # a YouTube capture, in pieces
    sttjobs.marks(token, marks); sttjobs.wave(token, rate, peaks)
    sttjobs.status(token); sttjobs.cancel(token); sttjobs.result(token)

NO HTTP HERE.  serve.py's /youtube/api/transcribe/* routes read the request,
call these, and send what they return; a refusal is a `Refusal`, which
becomes `{"ok": false, "error": "<a sentence>", "code": "<slug>"}` with its
status (`call`).  Nothing that reaches a person is ever a traceback: the
worker's own goes to the server's log.

WHAT A JOB IS.  It belongs to no video.  The add page names a source
(a YouTube video, or a film on this computer) through the add flow's own
validators, and gets back a TOKEN made here (secrets.token_urlsafe): the one
capability every other route takes.  No route takes a path, a device, a
precision or a temporary file's name from anybody; the model is one of two
words, the processing one of three, the language one Whisper knows.

ONE AT A TIME (a second start is 409 `busy`).  A multi-gigabyte model is
never loaded twice, a YouTube capture is real time and holds the person's
tab, and the slot is given up the moment a job ends or is cancelled.

THE MODEL IS HELD FROM start() TO THE END (getstt.using), the whole capture
included, so that Settings refuses to take the model or the program away under a
recording that has an hour of a person's time in it -- and says why.

ANY DEVICE THE NETWORK DOOR LET IN MAY START ONE (the owner): a phone, a
tablet, another computer.  Nothing here asks where the caller is, and
nothing may assume it is the machine the server runs on -- a remote
computer's Chromium can capture a tab and POST its sound, and a film is
named by a path on the SERVER's disk whoever names it.  The bound is the one
slot (409 `busy`) and Cancel.

THE STATES: awaiting-audio (a YouTube job, before its first piece) ->
receiving -> queued -> preparing -> loading -> transcribing -> done;
a film starts at `queued`.  failed and cancelled end it.  A finished job's
answer is kept for KEEP seconds and forgotten after; a cancelled one is
forgotten AT ONCE (only its token is remembered, so a page that asks is told
"cancelled" and not "no such job"), and an abandoned one -- a capture that
stopped arriving -- is let go after IDLE.

THE CHILD.  lib/sttworker.py, run with Parseh's own Python and the speech
runtime on its PYTHONPATH, in a process group of its own, registered with
getstt.track and with this module's own list: `cancel`, a stopped server
(atexit) and PR_SET_PDEATHSIG / the worker's own look for its parent all end
it.  The worker speaks JSON lines; `_message` is where each one lands.

THE WAVEFORM.  A YouTube job's peaks are the browser's own, from the same
capture (`wave`); they are HELD (youtube/lib/wavefile.py) for the video's
creation to adopt.  A FILM GETS NO WAVEFORM WRITTEN (the owner): the player
draws a film's from the film itself, so the worker only listens.
"""
import atexit
import contextlib
import json
import math
import os
import re
import secrets
import shutil
import signal
import subprocess
import sys
import threading
import time
import traceback

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
WORKER = os.path.join(HERE, "sttworker.py")
WIN = os.name == "nt"
for _p in (HERE, os.path.join(ROOT, "youtube", "lib")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ------------------------------------------------------------------ the limits
MODELS = ("large-v3-turbo", "large-v3")     # the ONLY two models, whatever getstt says
MODES = ("auto", "cpu", "cuda")             # and the only three ways to process
SAMPLE_RATE = 16000
CHUNK_MAX = 1 << 20                         # bytes of PCM16 in one audio request
MAX_SAMPLES = SAMPLE_RATE * 3600 * 12       # twelve hours of capture, 1.4 GB on disk
MIN_SAMPLES = SAMPLE_RATE // 2              # under half a second is no recording
FREE_TO_START = 256 << 20                   # bytes free before a capture may begin
FREE_TO_GO_ON = 64 << 20                    # and that must remain after each piece
IDLE = 600.0                                # seconds without a piece: abandoned
KEEP = 900.0                                # a finished job's answer, in seconds
KEEP_CANCELLED = 300.0                      # the token of a cancelled one
MAX_LINE = 64 << 20                         # a line of the worker's, at most
FELL_BACK = "The graphics card could not start this model, so Parseh continued on the CPU."
PAGE = "/youtube/add/"

AWAITING, RECEIVING, QUEUED, PREPARING, LOADING = \
    "awaiting-audio", "receiving", "queued", "preparing", "loading"
TRANSCRIBING, ALIGNING, DONE, FAILED, CANCELLED = "transcribing", "aligning", "done", "failed", "cancelled"
REVIEW_CHOICE, CORRECTING = "awaiting-review-choice", "correcting"
CHECKING = "checking-dictionary"
ACTIVE = (AWAITING, RECEIVING, QUEUED, PREPARING, LOADING, TRANSCRIBING, ALIGNING, CHECKING, CORRECTING)
RECORDING = (AWAITING, RECEIVING)           # a YouTube job still taking audio

TOKEN_BYTES = 12
# each ends in \Z and not $: `$` also matches before a trailing newline, and a
# token becomes part of a file name
TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{16}\Z")          # what token_urlsafe(12) makes
YT_ID = re.compile(r"^[A-Za-z0-9_-]{11}\Z")
LANG_RE = re.compile(r"^[a-z]{2,3}\Z")

JOBS = {}           # token -> the job, while it lives
TOMBS = {}          # token -> {"kind", "at"} for a job that was cancelled
LOCK = threading.RLock()
CHILDREN = set()    # every worker this module started, for stop_all


# ---------------------------------------------------------------- the refusals
class Refusal(Exception):
    """A sentence for the person and a slug for the page; `status` is the
    HTTP answer.  Anything else that goes wrong is turned into this by
    `call`, so that no answer ever carries a traceback."""

    def __init__(self, code, say, status=400, **extra):
        Exception.__init__(self, say)
        self.code, self.say, self.status, self.extra = code, say, status, extra

    def body(self):
        return dict(self.extra, ok=False, error=self.say, code=self.code)


def call(fn, *args, **kw):
    """fn's dict answer -> (dict with ok, HTTP status).  The one place a
    Refusal, or anything unforeseen, becomes an answer."""
    try:
        out = fn(*args, **kw)
        return dict(out, ok=True), 200
    except Refusal as e:
        return e.body(), e.status
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()
        return {"ok": False, "code": "failed", "error": "Transcription failed."}, 500


def _getstt():
    """The speech manager, imported when it is needed: a checkout without it
    (or a server that never installed speech to text) still runs, and
    every job says it is not installed."""
    try:
        import getstt
    except ImportError:
        raise Refusal("not-installed", "Speech to text is not installed.", 409)
    return getstt


def _speech(fn, *args):
    """A call into getstt, its SpeechError made a Refusal in its own words."""
    gs = _getstt()
    try:
        return fn(gs, *args)
    except getattr(gs, "SpeechError", ()) as e:
        raise Refusal(getattr(e, "code", "failed"), getattr(e, "say", "") or
                      "Speech to text could not do that.", 409)


# ------------------------------------------------------------- the add flow's own
def source_of(body):
    """The request's source and language, by the ADD FLOW'S OWN VALIDATORS
    (ytpages.one_source / video_id / local_target -> check_film /
    posted_lang) and their own sentences -> ({"kind", "id" | "path"}, code).

    What is stored is the NORMALISED source: the eleven-character id the
    server parsed, or the absolute path check_film made -- never the page's
    own spelling, which is never read again."""
    import ytpages
    for key in ("url", "path", "lang", "source"):
        if body.get(key) is not None and not isinstance(body.get(key), str):
            raise Refusal("bad-source" if key != "lang" else "bad-language",
                          "the %s has to be text, and that is a %s"
                          % (key, type(body.get(key)).__name__))
    kind = body.get("source")
    if kind not in ("youtube", "film"):
        raise Refusal("bad-source", "a transcription starts from a YouTube video "
                      "or from a film on this machine")
    try:
        ytpages.one_source(body)
    except ValueError as e:
        raise Refusal("bad-source", str(e))
    if kind == "youtube":
        if (body.get("path") or "").strip():
            raise Refusal("bad-source", "a YouTube video is named by its address, "
                          "not by a file on this machine")
        vid = ytpages.video_id(body.get("url"))
        if not vid:
            raise Refusal("bad-source", "that is not a YouTube URL (or id) -- or "
                          "name a film on this machine instead")
        source = {"kind": "youtube", "id": vid}
    else:
        if (body.get("url") or "").strip():
            raise Refusal("bad-source", "a film on this machine is named by its path, "
                          "not by an address")
        try:
            path, _ext, _id = ytpages.local_target({"path": body.get("path")}, [])
        except ValueError as e:
            raise Refusal("bad-source", str(e))
        source = {"kind": "film", "path": path}
    if not (body.get("lang") or "").strip():
        raise Refusal("bad-language", "name the language the video is spoken in")
    try:
        code = ytpages.posted_lang(body.get("lang")).code
    except KeyError as e:
        raise Refusal("bad-language", str(e.args[0] if e.args else e))
    return source, code


# --------------------------------------------------------------------- helpers
def _now():
    return time.time()


def _tmp():
    """The folder temporary audio lives in (stt/tmp/), made when first needed."""
    gs = _getstt()
    os.makedirs(gs.TMP_DIR, exist_ok=True)
    return gs.TMP_DIR


def _named(token, ext):
    """A temporary file's path: made by the server from a token it made
    itself, so nothing the client sends is ever part of it."""
    if not isinstance(token, str) or not TOKEN_RE.match(token):
        raise Refusal("no-such-job", "That transcription is not here any more "
                      "(Parseh may have been restarted).", 404)
    base = os.path.abspath(_tmp())
    path = os.path.abspath(os.path.join(base, "stt-%s%s" % (token, ext)))
    if os.path.dirname(path) != base:
        raise Refusal("no-such-job", "That transcription is not here any more.", 404)
    return path


def _free(path):
    try:
        return shutil.disk_usage(path).free
    except OSError:
        return None


def _clock(seconds):
    n = max(0, int(seconds))
    return "%d:%02d:%02d" % (n // 3600, n // 60 % 60, n % 60) if n >= 3600 \
        else "%d:%02d" % (n // 60, n % 60)


def _remove(*paths):
    for p in paths:
        if p:
            try:
                os.unlink(p)
            except OSError:
                pass


def _using(gs, key):
    """The model is in use for as long as the job lives, from start() to its
    end, so that Settings will not remove it under it (getstt.using)."""
    f = getattr(gs, "using", None)
    return f(key) if callable(f) else contextlib.nullcontext()


def _unhold(job):
    """The part start() took for the job, let go.  Every end of a job asks
    (done, failed, cancelled, abandoned, a stopping server) and the first
    one frees it: a second is nothing, so a part an install holds as well is
    not let go early, and one that is never let go could not be removed again."""
    with LOCK:
        hold = job.pop("hold", None)
    if hold is not None:
        hold.close()


def _job(token, missing=True):
    """A token -> its job.  A token that is not one is refused before any
    table is looked in; an unknown one is `no-such-job`, or None."""
    if not isinstance(token, str) or not TOKEN_RE.match(token):
        raise Refusal("no-such-job", "That transcription is not here any more "
                      "(Parseh may have been restarted).", 404)
    with LOCK:
        _expire()
        job = JOBS.get(token)
        cancelled = token in TOMBS
    if job is None and missing:
        if cancelled:
            raise Refusal("cancelled", "Recording was cancelled.", 409)
        raise Refusal("no-such-job", "That transcription is not here any more "
                      "(Parseh may have been restarted).", 404)
    return job


# ------------------------------------------------------------------------ files
def _files(job):
    return [job["pcm"], job["spec"], job["log"]]


def _clean_files(job):
    """Every temporary file of a job gone -- the audio above all."""
    _remove(*_files(job))


def _kill(proc):
    """The worker and anything it started, ended (as lib/latexdraw._kill)."""
    try:
        if WIN:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                           capture_output=True, timeout=10)
        else:
            os.killpg(proc.pid, signal.SIGKILL)
    except (OSError, subprocess.SubprocessError):
        try:
            proc.kill()
        except OSError:
            pass


def _preexec():
    # on Linux the worker dies with the server even when the server is
    # killed outright (PR_SET_PDEATHSIG); elsewhere the worker looks for its
    # parent itself, and the server's own stop ends it (stop_all)
    try:
        import ctypes
        ctypes.CDLL("libc.so.6", use_errno=True).prctl(1, signal.SIGKILL)
    except Exception:                                        # noqa: BLE001
        pass


def stop_all():
    """Every worker ended, and every temporary recording with it: the server
    is stopping (atexit, and serve.py's SIGTERM handler ends in it)."""
    with LOCK:
        procs = list(CHILDREN)
        jobs = list(JOBS.values())
    for proc in procs:
        _kill(proc)
    for job in jobs:
        job["cancelled"] = True
        if job.get("llm_cancel"):
            job["llm_cancel"].cancel()
        _clean_files(job)
        _unhold(job)


atexit.register(stop_all)


# -------------------------------------------------------------------- the table
def _expire():
    """Forget what is over, and abandon what stopped arriving.  Asked at
    every call, under LOCK: there is no timer thread to keep."""
    now = _now()
    for token, job in list(JOBS.items()):
        if job["state"] in (DONE, FAILED, REVIEW_CHOICE) and now - (job["finished"] or now) > KEEP:
            del JOBS[token]
        elif job["state"] in RECORDING and now - job.get("touched", now) > IDLE:
            _end(job, FAILED, "abandoned", "No sound arrived for %d minutes, so this "
                 "transcription was given up." % (IDLE // 60))
    for token, tomb in list(TOMBS.items()):
        if now - tomb["at"] > KEEP_CANCELLED:
            del TOMBS[token]


def _end(job, state, code=None, say=None):
    """A job over: its state, its reason, and nothing of it left on disk
    that it does not need (the answer of a done one is in memory)."""
    with LOCK:
        if job["state"] in (DONE, FAILED, CANCELLED):
            return
        job["state"] = state
        job["finished"] = _now()
        if state == FAILED:
            job["error"] = {"code": code or "failed", "say": say or "Transcription failed."}
        _unhold(job)                     # in the breath that says it is over
    _clean_files(job)
    if state == FAILED and job["kind"] == "youtube" and not job["sealed"]:
        # A PARTIAL CAPTURE HOLDS NOTHING: the waveform is the whole video's or
        # none (a capture that was complete and whose transcription then failed
        # keeps its peaks: an hour of the person's time, and half a megabyte)
        import wavefile
        wavefile.drop(job["id"])
    if state in (FAILED, CANCELLED):
        try:
            import wordtimes
            wordtimes.drop(job["id"])
        except Exception:  # noqa: BLE001
            pass


def busy():
    """Is a job holding the slot?  (For the Reading help page: an install
    and a transcription do not both load a model.)"""
    with LOCK:
        _expire()
        return any(j["state"] in ACTIVE for j in JOBS.values())


# ------------------------------------------------------------------------ start
def start(source, lang, model, processing, duration=None, exact=True):
    """A job, for a source the add flow's validators passed -> {"job", "state",
    "need", ...}.  `source` is what source_of() made; everything here is
    checked again, because this is the door tests and other code reach too."""
    if not isinstance(model, str) or model not in MODELS:
        raise Refusal("bad-model", "That is not one of the two speech models.")
    if not isinstance(processing, str) or processing not in MODES:
        raise Refusal("bad-processing", "Processing has to be Automatic, CPU or NVIDIA GPU.")
    if not isinstance(lang, str) or not LANG_RE.match(lang):
        raise Refusal("bad-language", "That is not a language code.")
    if not isinstance(exact, bool):
        raise Refusal("bad-exact", "Exact word times can only be on or off.")
    if not isinstance(source, dict):
        raise Refusal("bad-source", "There is no video to transcribe.")
    kind = source.get("kind")
    film = None
    if kind == "youtube":
        vid = source.get("id")
        if not isinstance(vid, str) or not YT_ID.match(vid):
            raise Refusal("bad-source", "That is not a YouTube video's id.")
        norm = {"kind": "youtube", "id": vid}
    elif kind == "film":
        path = source.get("path")
        if not isinstance(path, str) or not path or "\0" in path or not os.path.isabs(path):
            raise Refusal("bad-source", "A film is named by the full path of a file on "
                          "this machine.")
        # the add flow's own check again (a film is a file with a video's
        # extension), and the path must be the one it made: the same words
        # in, the same words out
        import ytpages
        try:
            real, _ext = ytpages.check_film(path)
        except ValueError as e:
            raise Refusal("bad-source", str(e))
        if real != path:
            raise Refusal("bad-source", "A film is named by the full path of a file on "
                          "this machine.")
        try:
            st = os.stat(path)
        except OSError:
            raise Refusal("film-unreadable", "The local film could not be read.", 422)
        if not os.path.isfile(path):
            raise Refusal("film-unreadable", "The local film could not be read.", 422)
        film = [st.st_size, st.st_mtime_ns, st.st_ino]
        norm = {"kind": "film", "path": path}
    else:
        raise Refusal("bad-source", "A transcription starts from a YouTube video or "
                      "from a film on this machine.")
    hint = None
    if duration is not None:
        # (one comparison refuses nan, inf and a 400-digit integer alike, without
        # ever turning the number into a float, which an integer that big cannot be)
        if isinstance(duration, bool) or not isinstance(duration, (int, float)) \
                or not 0 < duration <= MAX_SAMPLES / SAMPLE_RATE:
            raise Refusal("bad-duration", "That is not how long a video can be.")
        hint = float(duration)

    gs = _getstt()
    if not gs.runtime_ready():
        raise Refusal("not-installed", "Speech to text is not installed.", 409)
    if not gs.model_ready(model):
        raise Refusal("no-model", "The selected model is not installed.", 409)
    # the language Whisper listens for; a code it lacks is SpeechError
    wlang = _speech(lambda g, c: g.whisper_code(c), lang)
    if not isinstance(wlang, str) or not LANG_RE.match(wlang):
        raise Refusal("unsupported-language", "Speech to text cannot listen for that "
                      "language.", 409)
    # the device is resolved HERE, so an explicit NVIDIA GPU that is not ready
    # is refused at once, before anybody records an hour of sound for it
    device, _note = _speech(lambda g, m: g.resolve(m), processing)
    if device not in ("cpu", "cuda"):
        raise Refusal("failed", "Transcription failed.", 500)
    name = ""
    if device == "cuda":
        try:
            name = str(gs.hardware()["cuda"].get("name") or "")
        except Exception:                                    # noqa: BLE001
            name = ""
    threads = gs.cpu_threads()
    aligner = ""
    ready = getattr(gs, "aligner_ready", None)
    if exact and callable(ready):
        try:
            aligner = lang if ready(lang) else ""
        except Exception:  # noqa: BLE001
            aligner = ""
    tmp = _tmp()
    if kind == "youtube":
        need = FREE_TO_START + (int(hint * SAMPLE_RATE * 2) if hint else 0)
        free = _free(tmp)
        if free is not None and free < need:
            raise Refusal("no-room", "There was not enough disk space to finish the "
                          "capture.", 507)

    with LOCK:
        _expire()
        if any(j["state"] in ACTIVE for j in JOBS.values()):
            raise Refusal("busy", "Another transcription is running.", 409)
        token = secrets.token_urlsafe(TOKEN_BYTES)
        now = _now()
        job = {"id": token, "kind": kind, "source": norm, "film": film,
               "lang": lang, "wlang": wlang, "model": model, "mode": processing,
               "aligner": aligner,
               "planned": device, "device": None, "device_name": name, "threads": threads,
               "fell_back": False,
               "state": AWAITING if kind == "youtube" else QUEUED,
               "created": now, "touched": now, "started": None, "finished": None,
               "have": 0, "sealed": False, "hint": hint, "marks": [],
               "total": None, "done": 0.0, "segments": None, "text": "", "notes": [],
               "words": None,
               "facts": None, "warning": "", "error": None, "cancelled": False,
               "proc": None, "lock": threading.Lock(),
               "pcm": _named(token, ".pcm"), "spec": _named(token, ".spec.json"),
               "log": _named(token, ".log")}
        JOBS[token] = job
        # THE JOB HOLDS ITS MODEL, AND WITH IT THE PROGRAM, FROM HERE TO ITS END: a
        # capture is real time and takes as long as the video plays, and Settings
        # must not take the part away under a recording (nothing else notices it)
        job["hold"] = contextlib.ExitStack()
        job["hold"].enter_context(_using(gs, model))
        if aligner:
            job["hold"].enter_context(_using(gs, "align-" + aligner))
        # the answer is made BEFORE the worker's thread can move the state on
        answer = _started(job)
    if kind == "film":
        _launch(job)
    return answer


def _started(job):
    out = {"job": job["id"], "state": job["state"], "kind": job["kind"],
           "need": "audio" if job["kind"] == "youtube" else "",
           "lang": job["lang"], "model": job["model"], "processing": job["mode"],
           "exact": bool(job.get("aligner")),
           "say": _say(job)}
    if job.get("correction"):
        out["correction"] = dict(job["correction"])
    out.update(_who(job))
    return out


def _who(job):
    if job["kind"] == "youtube":
        return {"source": "youtube", "video_id": job["source"]["id"]}
    return {"source": "film", "film": os.path.basename(job["source"]["path"])}


def _launch(job):
    threading.Thread(target=_run, args=(job,), daemon=True).start()


# ------------------------------------------------------------------------ audio
def audio(token, offset, data, last=False):
    """One piece of a YouTube capture: 16 kHz mono PCM16LE, at a sample
    offset -> {"have": samples so far}.  Idempotent: a piece sent twice is
    written once; a piece that skips ahead is 409 `gap`, with `have`, and
    the browser sends again from there."""
    job = _job(token)
    if job["kind"] != "youtube":
        raise Refusal("wrong-state", "This transcription takes no recording: it reads a "
                      "film on this machine.", 409)
    if not isinstance(data, (bytes, bytearray)):
        raise Refusal("bad-audio", "The recording did not arrive as sound.")
    if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
        raise Refusal("bad-offset", "The recording says where its piece belongs, and that "
                      "is not a place.")
    if len(data) > CHUNK_MAX:
        raise Refusal("too-big", "That piece of the recording is bigger than one piece "
                      "may be.", 413)
    if len(data) % 2:
        raise Refusal("bad-audio", "The recording did not arrive as whole samples.")
    n = len(data) // 2
    if not n and not last:
        raise Refusal("bad-audio", "That piece of the recording was empty.")
    with job["lock"]:
        with LOCK:
            state, have, sealed = job["state"], job["have"], job["sealed"]
            if job["cancelled"] or state == CANCELLED:
                raise Refusal("cancelled", "Recording was cancelled.", 409)
            if state not in RECORDING:
                # THE LAST PIECE SENT AGAIN, because its answer was lost, is
                # not an error: the job has it and has gone on
                if sealed and last and offset + n == have:
                    return {"have": have, "state": state}
                raise Refusal("wrong-state", "This transcription is not taking sound "
                              "any more.", 409)
        if offset > have or (not n and offset != have):
            raise Refusal("gap", "A piece of the recording is missing.", 409, have=have)
        if offset + n > MAX_SAMPLES:
            raise Refusal("too-long", "A recording of more than 12 hours cannot be "
                          "transcribed here.", 413)
        if offset + n > have:
            free = _free(os.path.dirname(job["pcm"]))
            if free is not None and free - len(data) < FREE_TO_GO_ON:
                _end(job, FAILED, "no-room", "There was not enough disk space to finish "
                     "the capture.")
                raise Refusal("no-room", "There was not enough disk space to finish the "
                              "capture.", 507)
            try:
                mode = "r+b" if os.path.exists(job["pcm"]) else "wb"
                with open(job["pcm"], mode) as f:
                    f.seek(offset * 2)
                    f.write(data)
            except OSError:
                _end(job, FAILED, "no-room", "There was not enough disk space to finish "
                     "the capture.")
                raise Refusal("no-room", "There was not enough disk space to finish the "
                              "capture.", 507)
            have = offset + n
        with LOCK:
            job["have"] = have
            job["touched"] = _now()
            job["state"] = RECEIVING
            if last:
                if have < MIN_SAMPLES:
                    _end(job, FAILED, "no-sound", "No sound was recorded.")
                    raise Refusal("no-sound", "No sound was recorded.")
                job["sealed"] = True
                job["total"] = have / float(SAMPLE_RATE)
                job["state"] = QUEUED
            state = job["state"]      # said now: the worker's thread moves it on
        if last:
            _launch(job)
    return {"have": have, "state": state}


def marks(token, marks):
    """The pairs [frame, video seconds] that put the recording on the video's
    own clock (sttpanel.remap): REPLACE ALL, sent before the last piece."""
    import sttpanel
    job = _job(token)
    if job["kind"] != "youtube":
        raise Refusal("wrong-state", "A film needs no marks: it is read from its start.", 409)
    if not isinstance(marks, list):
        raise Refusal("bad-marks", "The marks have to be a list of pairs.")
    with LOCK:
        if job["state"] not in RECORDING:
            raise Refusal("wrong-state", "This transcription is not taking marks any "
                          "more.", 409)
        job["marks"] = sttpanel.clean_marks(marks, SAMPLE_RATE)
        job["touched"] = _now()
        return {"marks": len(job["marks"])}


def wave(token, rate, peaks):
    """The peaks the browser made from the same capture -> held for the video
    the person adds (youtube/lib/wavefile.py).  A partial capture holds
    nothing: cancel and a failure drop it."""
    import wavefile
    job = _job(token)
    if job["kind"] != "youtube":
        raise Refusal("wrong-state", "A film has no waveform to send: the player draws it "
                      "from the film itself.", 409)
    with LOCK:
        if job["state"] in (FAILED, CANCELLED):
            raise Refusal("wrong-state", "This transcription is over.", 409)
    try:
        kept = wavefile.hold(token, rate, peaks)
    except ValueError as e:
        raise Refusal("bad-wave", str(e))
    with LOCK:
        job["touched"] = _now()
    return {"buckets": kept}


# ----------------------------------------------------------------- status, etc.
def _say(job):
    s, model = job["state"], job["model"]
    if s == AWAITING:
        return "Waiting for the recording to start…"
    if s == RECEIVING:
        got = _clock(job["have"] / float(SAMPLE_RATE))
        return ("Recording %s / %s…" % (got, _clock(job["hint"])) if job["hint"]
                else "Recording %s…" % got)
    if s == QUEUED:
        return "Audio captured." if job["kind"] == "youtube" else "Getting ready…"
    if s == PREPARING:
        return "Preparing audio…"
    fell = FELL_BACK + " " if job["fell_back"] else ""
    if s == LOADING:
        on = (" Using %s." % job["device_name"]) if job["device"] == "cuda" \
            and job["device_name"] else ""
        return "%sLoading %s…%s" % (fell, model, on)
    if s == TRANSCRIBING:
        where = "GPU" if job["device"] == "cuda" else "CPU"
        pct = _pct(job)
        return "%sTranscribing on %s…%s" % (fell, where, " %d%%" % pct if pct is not None
                                                  else "")
    if s == ALIGNING:
        pct = _pct(job)
        return "Making exact word times…%s" % (" %d%%" % pct if pct is not None else "")
    if s == REVIEW_CHOICE:
        return "Whisper finished. Choose how to review its transcript."
    if s == CHECKING:
        return "Whisper finished. Checking words in the installed dictionary…"
    if s == CORRECTING:
        c = job.get("correction", {})
        if c.get("total", 0):
            if c.get("task") == "workspace":
                return "%s… %d / %d ASR words processed." % (c.get("phase", "Reviewing workspace"), c.get("done", 0), c["total"])
            return "Reviewing with the selected LLM… %d / %d ASR words reviewed." % (c.get("done", 0), c["total"])
        return "Reviewing with the selected LLM…"
    if s == DONE:
        n = (job["facts"] or {}).get("captions", 0)
        return "Done — %d caption%s." % (n, "" if n == 1 else "s")
    if s == FAILED:
        return (job["error"] or {}).get("say") or "Transcription failed."
    return "Recording was cancelled." if job["kind"] == "youtube" \
        else "Transcription was cancelled."


def _pct(job):
    if job["state"] == CORRECTING:
        c = job.get("correction", {})
        return int(100 * c.get("done", 0) / c["total"]) if c.get("total", 0) > 0 else None
    if job["state"] == DONE:
        return 100
    if job["state"] in (TRANSCRIBING, ALIGNING) and job["total"]:
        return max(0, min(99, int(100 * job["done"] / job["total"])))
    if job["state"] == RECEIVING and job["hint"]:
        return max(0, min(99, int(100 * job["have"] / float(SAMPLE_RATE) / job["hint"])))
    return None


def _report(job):
    """A job as status says it: the shape the add page draws from."""
    out = {"state": job["state"], "say": _say(job), "pct": _pct(job),
           "done": round(job["done"], 3), "total": round(job["total"], 3) if job["total"]
           else None, "device": job["device"], "fell_back": job["fell_back"],
           "model": job["model"], "lang": job["lang"], "kind": job["kind"],
           "exact": bool(job.get("aligner")),
           "have": job["have"], "stopped": job["state"] == CANCELLED}
    if job.get("correction"):
        out["correction"] = dict(job["correction"])
    out.update(_who(job))
    if job["fell_back"]:
        out["note"] = FELL_BACK
    if job["state"] == DONE:
        out["captions"] = (job["facts"] or {}).get("captions", 0)
    if job["state"] == FAILED and job["error"]:
        out["error"], out["code"] = job["error"]["say"], job["error"]["code"]
    return out


def status(token):
    job = _job(token, missing=False)
    if job is not None:
        with LOCK:
            return _report(job)
    with LOCK:
        tomb = TOMBS.get(token) if isinstance(token, str) else None
    if tomb is None:
        raise Refusal("no-such-job", "That transcription is not here any more "
                      "(Parseh may have been restarted).", 404)
    youtube = tomb["kind"] == "youtube"
    return {"state": CANCELLED, "say": "Recording was cancelled." if youtube
            else "Transcription was cancelled.", "pct": None, "done": 0, "total": None,
            "device": None, "fell_back": False, "model": None, "lang": None,
            "kind": tomb["kind"], "source": tomb["kind"], "stopped": True}


def cancel(token):
    """Stop it: the worker killed, the temporary audio deleted, the held
    waveform dropped, the slot free, and the job forgotten -- only its
    token stays (a little while), so that a page which asks is told so.
    A job that is over has nothing to stop (its answer stays)."""
    import wavefile
    import wordtimes
    job = _job(token, missing=False)
    if job is None:
        return {"cancelled": False}
    with LOCK:
        if job["state"] == CORRECTING or (job["state"] == DONE and job.get("review_choice") == "llm"):
            return cancel_review(token)
        if job["state"] == DONE and job.get("review_choice") == "external":
            # Discarding the browser review also forgets its unaccepted imports.
            job.pop("external_review", None)
            job["review_choice"] = None
            job["correction_result"] = None
            job["state"] = REVIEW_CHOICE
        if job["state"] not in ACTIVE + (REVIEW_CHOICE,):
            return {"cancelled": False}
        job["cancelled"] = True
        job["state"] = CANCELLED
        job["finished"] = _now()
        proc = job["proc"]
    if proc is not None:
        _kill(proc)
        try:
            proc.wait(10)                # its memory is free before the next job
        except (subprocess.TimeoutExpired, OSError):
            pass
    with job["lock"]:                    # after a piece being written, not in it
        _clean_files(job)
    _unhold(job)                         # with the worker dead, the part may go
    wavefile.drop(token)
    wordtimes.drop(token)
    with LOCK:
        JOBS.pop(token, None)
        TOMBS[token] = {"kind": job["kind"], "at": _now()}
    return {"cancelled": True}


def result(token):
    """The transcript, in the add page's own format, once the job is done;
    it may be read again until the job is forgotten."""
    import wavefile
    job = _job(token, missing=False)
    if job is None:
        with LOCK:
            if isinstance(token, str) and token in TOMBS:
                raise Refusal("cancelled", "Recording was cancelled.", 409)
        raise Refusal("no-such-job", "That transcription is not here any more "
                      "(Parseh may have been restarted).", 404)
    with LOCK:
        state = job["state"]
        if state == FAILED and job["error"]:
            raise Refusal(job["error"]["code"], job["error"]["say"], 409)
        if state not in (DONE, REVIEW_CHOICE, CORRECTING):
            raise Refusal("not-finished", "It has not finished yet.", 409)
        facts = dict(job["facts"] or {})
        return dict(facts, text=job["text"], lang=job["lang"], model=job["model"],
                    device=job["device"], fell_back=job["fell_back"],
                    notes=list(job["notes"]), warning=job["warning"],
                    words=dict(job["words"] or {"held": False, "count": 0}),
                    wave={"held": wavefile.held(token)},
                    review={"evidence": job.get("review_evidence"),
                            "choice": job.get("review_choice"),
                            "correction": dict(job.get("correction") or {}),
                            "result": job.get("correction_result"),
                            "external": _external_view(job),
                            "diagnostics": list(job.get("llm_diagnostics") or []),
                            "diagnostics_clipped": bool(job.get("llm_diagnostics_clipped"))})


def review_media(token):
    """The original local film for this job's browser review, never a caller's path.

    The normal admission gate still applies. The unpredictable job token grants
    access only to the already validated source, while its file identity matches.
    No copy of the film or ASR audio is created or retained.
    """
    job = _job(token)
    with LOCK:
        if job["kind"] != "film" or not job.get("film") or job["state"] in (FAILED, CANCELLED):
            raise Refusal("no-review-media", "There is no local video for this review.", 404)
        if not _review_source_current(job):
            raise Refusal("source-changed", "The local film changed. Transcribe it again.", 409)
        return job["source"]["path"]


def review_dictionary(token, source_sha256, word_id):
    """Read-only meanings for source words, native ASR and validated LLM candidates."""
    import asrcorrection
    import asrdictionary
    job = _job(token)
    with LOCK:
        evidence = job.get("review_evidence")
        if not evidence or source_sha256 != evidence["source_sha256"] or not _review_source_current(job):
            raise Refusal("stale-review", "That dictionary lookup no longer matches the review.", 409)
        word = asrcorrection.index(evidence).get(word_id) if isinstance(word_id, str) else None
        if word is None:
            raise Refusal("bad-word", "Choose a word from this Whisper result.")
        resolver = job.get("dictionary_resolver")
        if resolver is None:
            resolver = job["dictionary_resolver"] = asrdictionary.Resolver(job["lang"])
        segment = next(s for s in evidence["segments"] if s["segment_id"] == word["segment_id"])
        source_words = segment["words"]
        index = next(i for i, w in enumerate(source_words) if w["word_id"] == word_id)
        asr_before = source_words[index-1]["text"] if index else ""
        asr_after = source_words[index+1]["text"] if index+1 < len(source_words) else ""
        asr_candidates = [a["text"] for a in word["asr_alternatives"]]
        proposal = next((s for s in (job.get("correction_result") or {}).get("suggestions", [])
                         if word_id in s.get("word_ids", [s["word_id"]])), None)
        original = proposal["original"] if proposal else word["text"]
        members = proposal.get("word_ids", [proposal["word_id"]]) if proposal else [word_id]
        first = next(j for j, w in enumerate(source_words) if w["word_id"] == members[0])
        last = next(j for j, w in enumerate(source_words) if w["word_id"] == members[-1])
        before = source_words[first-1]["text"] if first else ""
        after = source_words[last+1]["text"] if last+1 < len(source_words) else ""
        candidates = [c["text"] for c in proposal["candidates"]] if proposal else []
    return {"word_id": word_id, "source_sha256": source_sha256,
            "original": dict(resolver.word(original, before, after), text=original),
            "asr_alternatives": [dict(resolver.word(text, asr_before, asr_after), text=text) for text in asr_candidates],
            "candidates": [dict(resolver.word(text, before, after), text=text) for text in candidates]}


def _review_source_current(job):
    if job["kind"] != "film" or not job.get("film"):
        return True
    try:
        st = os.stat(job["source"]["path"])
        return [st.st_size, st.st_mtime_ns, st.st_ino] == job["film"]
    except OSError:
        return False


def review(token, mode, source_sha256, connection_id=None, word_ids=None, instruction_mode="prompt", task="suspect"):
    """Explicit browser choice. Destination and model come only from host config."""
    import llmconfig
    import llmadapter
    job = _job(token)
    with LOCK:
        if job["state"] not in (REVIEW_CHOICE, DONE):
            raise Refusal("wrong-state", "Wait for Whisper or cancel the current LLM review.", 409)
        if not job.get("review_evidence") or source_sha256 != job["review_evidence"]["source_sha256"]:
            raise Refusal("stale-review", "That review no longer matches the Whisper result.", 409)
        if not _review_source_current(job):
            raise Refusal("source-changed", "The local film changed. Transcribe it again.", 409)
        if mode not in ("llm", "whisper"):
            raise Refusal("bad-review", "Choose LLM review or Whisper-only review.")
        if instruction_mode not in ("prompt", "skill"):
            raise Refusal("bad-review", "Choose the short prompt or installed correction skill.")
        if task not in ("suspect", "full", "workspace"):
            raise Refusal("bad-review", "Choose a saved transcript review method.")
        previous = job.get("correction_result")
        if word_ids is not None:
            import asrcorrection
            sources = asrcorrection.index(job["review_evidence"])
            if (mode != "llm" or not isinstance(word_ids, list) or not word_ids
                    or len(word_ids) > len(sources) or any(not isinstance(w, str) for w in word_ids)
                    or len(set(word_ids)) != len(word_ids)
                    or any(w not in sources or not sources[w]["reviewable"] or
                           (task == "suspect" and not asrcorrection.suspect(sources[w])) for w in word_ids)
                    or (previous and previous.get("task", "suspect") != task)):
                raise Refusal("bad-review", "Choose remaining words from this review task and Whisper result.")
        if mode == "whisper":
            job.pop("external_review", None)
            job["review_choice"] = "whisper"
            job["correction_result"] = None
            job["correction"] = {"state": "not-requested", "complete": False}
            job["state"], job["finished"] = DONE, _now()
            return _report(job)
        if any(j is not job and j["state"] in ACTIVE for j in JOBS.values()):
            raise Refusal("busy", "Another transcription or LLM review is running.", 409)
        config = llmconfig.load()
        if config is None:
            raise Refusal("llm-unconfigured", "Set up LLM Integration, or review the Whisper result without it.", 409)
        if instruction_mode == "skill" and task != "workspace" and config.get("adapter") != "unsloth-agent-skills":
            raise Refusal("skills-unavailable", "Select the Unsloth Agent Skills adapter in LLM Integration before using an installed skill.", 409)
        if connection_id != llmconfig.revision(config):
            raise Refusal("settings-changed", "The LLM settings changed. Inspect the current destination and choose review again.", 409)
        try:
            llmconfig.for_review(config, task)
            if task == "workspace":
                import asrworkspace
                if not asrworkspace.sandbox_status()["available"]:
                    raise llmconfig.LLMError("workspace-unavailable", asrworkspace.sandbox_status()["say"])
        except llmconfig.LLMError as e:
            raise Refusal(e.code, e.say, 409)
        if word_ids is not None and previous and job.get("llm_config_fingerprint") != llmconfig.fingerprint(config):
            raise Refusal("settings-changed", "The LLM settings changed. Start a new review before retrying words.", 409)
        cancel = llmadapter.Cancellation()
        job["llm_cancel"] = cancel
        job["llm_generation"] = job.get("llm_generation", 0) + 1
        generation = job["llm_generation"]
        job["review_choice"] = "llm"
        job.pop("external_review", None)
        job["llm_config_fingerprint"] = llmconfig.fingerprint(config)
        if word_ids is None:
            job["correction_result"] = None
            job["llm_diagnostics"] = []
            job["llm_diagnostics_bytes"] = 0
            job["llm_diagnostics_clipped"] = False
        job["correction"] = {"state": "running", "complete": False, "done": 0, "total": 0,
                             "unit": "words", "response_count": len(job.get("llm_diagnostics") or []),
                             "instruction_mode": instruction_mode,
                             "task": task,
                             "destination": config["base_url"], "model": llmconfig.for_review(config, task)["selected_model"],
                             "started": _now()}
        job["state"] = CORRECTING
        answer = _report(job)
    threading.Thread(target=_correct, args=(job, config, cancel, generation, word_ids, previous), daemon=True,
                     name="asr-correction").start()
    return answer


def _correct(job, config, cancel, generation, word_ids=None, previous=None):
    import asrcorrection
    import llmadapter
    import llmconfig
    stamp = llmconfig.fingerprint(config)
    task = job["correction"].get("task", "suspect")
    feature_config = llmconfig.for_review(config, task)

    def current():
        cancel.check()
        if not _review_source_current(job):
            raise llmconfig.LLMError("source-changed", "The local film changed during review. Transcribe it again.")
        if llmconfig.fingerprint(llmconfig.load()) != stamp:
            raise llmconfig.LLMError("settings-changed", "The LLM destination or model changed. Choose review again.")

    class SavedAdapter:
        def generate_text(self, *args, **kw):
            current()
            return llmadapter.adapter(feature_config).generate_text(*args, **kw)

        def agent_turn(self, *args, **kw):
            current()
            return llmadapter.adapter(feature_config).agent_turn(*args, **kw)

    def progress(done, total, phase=None):
        current()
        with LOCK:
            if generation == job.get("llm_generation") and job["state"] == CORRECTING:
                job["correction"].update(done=done, total=total)
                if phase:
                    job["correction"]["phase"] = phase

    def diagnostic(trace):
        # Explicitly inspectable feature data, kept only with this ephemeral
        # job. Never put prompts/replies in logs, prefs, sync or status.
        current()
        def redact(value):
            if isinstance(value, str):
                key = config.get("api_key")
                return value.replace(key, "[redacted credential]") if key else value
            if isinstance(value, list):
                return [redact(v) for v in value]
            if isinstance(value, dict):
                return {k: redact(v) for k, v in value.items()}
            return value
        trace = redact(trace)
        trace["run"] = generation
        size = len(json.dumps(trace, ensure_ascii=False).encode("utf-8"))
        with LOCK:
            if generation != job.get("llm_generation") or job["state"] != CORRECTING:
                return
            if size > 512 * 1024:
                job["llm_diagnostics_clipped"] = True
                return
            history = job.setdefault("llm_diagnostics", [])
            while history and (job.get("llm_diagnostics_bytes", 0) + size > 512 * 1024 or len(history) >= 100):
                old = history.pop(0)
                job["llm_diagnostics_bytes"] -= len(json.dumps(old, ensure_ascii=False).encode("utf-8"))
                job["llm_diagnostics_clipped"] = True
            history.append(trace)
            job["llm_diagnostics_bytes"] = job.get("llm_diagnostics_bytes", 0) + size
            job["correction"]["response_count"] = job["correction"].get("response_count", 0) + 1

    try:
        if task == "workspace":
            import asrworkspace
            out = asrworkspace.correct(job["review_evidence"], SavedAdapter(), cancel, progress,
                                       config.get("context_tokens", 8192), diagnostic, word_ids)
        else:
            out = asrcorrection.correct(job["review_evidence"], SavedAdapter(), cancel, progress,
                                        config.get("context_tokens", 8192), diagnostic, word_ids,
                                        job["correction"].get("instruction_mode") == "skill", task)
        current()
        with LOCK:
            if generation != job.get("llm_generation") or job["state"] != CORRECTING:
                return
            if word_ids is not None and previous:
                selected = set(out.get("reviewed_word_ids", word_ids))
                # A retry updates only its selected words. Other proposals and
                # the browser's accepted/manual draft remain available.
                out["suggestions"] = [s for s in previous["suggestions"] if not selected.intersection(s.get("word_ids", [s["word_id"]]))] + out["suggestions"]
                for key in ("failed_word_ids", "uncertain_word_ids"):
                    out[key] = [w for w in previous.get(key, []) if w not in selected] + out[key]
                out["assessment"] = "suggestions" if out["suggestions"] else out["assessment"]
            job["correction_result"] = out
            job["correction"].update(state="complete", complete=True,
                                     failed_words=len(out.get("failed_word_ids", [])))
            job["state"], job["finished"] = DONE, _now()
    except Exception as e:
        # No tracebacks here: an unexpected exception may contain model text.
        safe = e if isinstance(e, llmconfig.LLMError) else llmconfig.LLMError(
            "correction-failed", "LLM review could not finish. The Whisper result is intact.")
        with LOCK:
            if generation != job.get("llm_generation") or job["state"] != CORRECTING:
                return
            job["correction_result"] = None
            job["correction"].update(state="failed", complete=False, code=safe.code, error=safe.say)
            job["state"], job["finished"] = REVIEW_CHOICE, _now()


def cancel_review(token):
    job = _job(token)
    with LOCK:
        if job["state"] == CORRECTING or (job["state"] == DONE and job.get("review_choice") == "llm"):
            job["llm_generation"] = job.get("llm_generation", 0) + 1
            cancel = job.pop("llm_cancel", None)
            if cancel:
                cancel.cancel()
            job["correction_result"] = None
            job["correction"].update(state="cancelled", complete=False,
                                     error="LLM review was cancelled. The Whisper result is intact.")
            job["state"], job["finished"] = REVIEW_CHOICE, _now()
        return _report(job)


def _external_job(token, source_sha256, session=None):
    job = _job(token)
    if (job["state"] not in (DONE, REVIEW_CHOICE) or not job.get("review_evidence")
            or source_sha256 != job["review_evidence"]["source_sha256"]):
        raise Refusal("stale-review", "That external review no longer matches the pending Whisper result.", 409)
    if not _review_source_current(job):
        raise Refusal("source-changed", "The local film changed. Transcribe it again.", 409)
    if session is not None and (not isinstance(session, str) or not session or job.get("review_choice") != "external" or session != job.get("external_review", {}).get("id")):
        raise Refusal("stale-review", "This external prompt was replaced. Prepare a new prompt.", 409)
    job["touched"] = _now()
    return job


def _external_view(job):
    ext = job.get("external_review")
    if not ext or job.get("review_choice") != "external":
        return None
    import asrexternal
    index = ext["index"]
    return {"id": ext["id"], "task": ext["task"], "index": index, "batches": len(ext["batches"]),
            "finished": ext["finished"], "submitted": sorted(ext["answers"]),
            "words_done": sum(len(asrexternal.ids(ext["batches"][i])) for i in ext["answers"]),
            "words_total": sum(len(asrexternal.ids(batch)) for batch in ext["batches"]),
            "prompt": ext["prompt"] if not ext["finished"] else "", "prompt_error": ext.get("prompt_error", "")}


def external_start(token, source_sha256, task, word_ids=None):
    import asrexternal
    import asrcorrection
    with LOCK:
        job = _external_job(token, source_sha256)
        sources = asrcorrection.index(job["review_evidence"])
        if word_ids is not None and (not isinstance(word_ids, list) or not word_ids
                or any(not isinstance(ident, str) or ident not in sources or not sources[ident]["reviewable"] for ident in word_ids)
                or len(set(word_ids)) != len(word_ids) or len(word_ids) > len(sources)):
            raise Refusal("bad-review", "Choose mapped words from this Whisper result.")
        try:
            batches = asrexternal.batches(job["review_evidence"], task, word_ids)
            first = asrexternal.prompt(job["review_evidence"], task, batches[0]) if batches else ""
        except Exception as error:
            if hasattr(error, "say"):
                raise Refusal(error.code, error.say)
            raise Refusal("bad-review", "The external prompt could not be prepared.")
        previous = job.get("correction_result")
        base = previous if word_ids is not None and previous and previous.get("task") == task else None
        job["external_review"] = {"id": secrets.token_urlsafe(18), "task": task, "index": 0,
                                  "batches": batches, "answers": {}, "attempts": {}, "finished": not batches, "base": base, "prompt": first}
        job["review_choice"] = "external"
        job["state"], job["finished"] = DONE, _now()
        job["correction"] = {"state": "awaiting-paste" if batches else "complete", "complete": not batches,
                             "unit": "words", "task": task, "method": "external", "done": 0,
                             "total": sum(len(asrexternal.ids(batch)) for batch in batches)}
        _external_merge(job)
        return result(token)


def _external_merge(job):
    import asrexternal
    ext = job["external_review"]
    selected = set().union(*(asrexternal.ids(batch) for batch in ext["batches"]))
    base = ext["base"] or {}
    out = {"schema_version": 1, "task": ext["task"], "method": "external-" + ext["task"],
           "suggestions": [s for s in base.get("suggestions", []) if not selected.intersection(s.get("word_ids", [s["word_id"]]))]}
    for field in ("failed_word_ids", "uncertain_word_ids", "reviewed_word_ids"):
        out[field] = [ident for ident in base.get(field, []) if ident not in selected]
    for answer in ext["answers"].values():
        out["suggestions"].extend(answer["suggestions"])
        for field in ("failed_word_ids", "uncertain_word_ids", "reviewed_word_ids"):
            out[field].extend(answer[field])
    if ext["finished"]:
        unseen = selected - set(out["reviewed_word_ids"])
        out["failed_word_ids"].extend(sorted(unseen))
        out["uncertain_word_ids"].extend(sorted(unseen))
    out["assessment"] = ("no_flagged_words" if ext["task"] == "suspect" else "no_reviewable_words") if not selected else (
        "partial" if out["failed_word_ids"] else "suggestions" if out["suggestions"] else "kept_original")
    out["words_reviewed"] = sum(len(asrexternal.ids(ext["batches"][i])) for i in ext["answers"])
    out["words_total"] = sum(len(asrexternal.ids(batch)) for batch in ext["batches"])
    job["correction_result"] = out
    job["correction"].update(done=out["words_reviewed"], total=out["words_total"],
                             failed_words=len(out["failed_word_ids"]), complete=ext["finished"],
                             state="complete" if ext["finished"] else "awaiting-paste")


def external_action(token, source_sha256, session, action, index=None, answer=None):
    import asrexternal
    import llmconfig
    with LOCK:
        if not isinstance(session, str) or not session:
            raise Refusal("stale-review", "Prepare an external prompt before importing an answer.", 409)
        job = _external_job(token, source_sha256, session)
        ext = job["external_review"]
        if action == "cancel":
            job.pop("external_review", None); job["review_choice"] = None
            job["correction_result"] = None; job["correction"] = {"state": "not-requested", "complete": False}
            job["state"], job["finished"] = REVIEW_CHOICE, _now()
            return result(token)
        if ext["finished"]:
            raise Refusal("stale-review", "This external review is finished. Prepare another prompt to retry.", 409)
        # An open copy/paste review may take longer than ASR result retention.
        # Refresh only this in-memory review; it still occupies no job slot.
        if action == "keep-alive":
            job["finished"] = _now()
            return {"kept": True}
        if action in ("prompt", "answer"):
            if type(index) is not int or not 0 <= index < len(ext["batches"]):
                raise Refusal("bad-review", "Choose a prompt batch from this review.")
        if action == "answer":
            try:
                parsed = asrexternal.parse(job["review_evidence"], ext["task"], ext["batches"][index], answer)
                current_prompt = asrexternal.prompt(job["review_evidence"], ext["task"], ext["batches"][index])
            except llmconfig.LLMError as error:
                raise Refusal(error.code, error.say)
            ext["answers"][index] = parsed
            ext["attempts"][index] = ext["attempts"].get(index, 0) + 1
            ext.update(index=index, prompt=current_prompt, prompt_error="")
            config = llmconfig.load() or {}
            key = config.get("api_key")
            def safe(text):
                if key:
                    # Raw pasted CSV and JSON can escape quotes in a key.
                    variants = {key, key.replace('"', '""'), json.dumps(key, ensure_ascii=False)[1:-1]}
                    for value in sorted(variants, key=len, reverse=True):
                        text = text.replace(value, "[redacted credential]")
                return text
            trace = {"run": ext["id"], "sentence_id": "external-batch%d" % index, "attempt": ext["attempts"][index], "state": "complete",
                     "source": "\n".join(unit["text"] for unit in ext["batches"][index]),
                     "word_ids": parsed["reviewed_word_ids"], "answer": safe(answer)[:16000], "ignored_edits": parsed["ignored_edits"],
                     "prompt": [{"role": "user", "content": safe(current_prompt)[:32000]}]}
            # Redact strings before JSON encoding, including quoted keys in
            # pasted explanations. Never replace JSON syntax or numeric values.
            def redact(value):
                if isinstance(value, str):
                    return safe(value)
                if isinstance(value, list):
                    return [redact(item) for item in value]
                if isinstance(value, dict):
                    return {name: redact(item) for name, item in value.items()}
                return value
            trace = redact(trace)
            history = job.setdefault("llm_diagnostics", [])
            history.append(trace)
            while len(history) > 100 or len(json.dumps(history, ensure_ascii=False).encode("utf-8")) > 512 * 1024:
                history.pop(0); job["llm_diagnostics_clipped"] = True
            job["llm_diagnostics_bytes"] = len(json.dumps(history, ensure_ascii=False).encode("utf-8"))
            if len(ext["answers"]) == len(ext["batches"]):
                ext["finished"] = True
            else:
                following = next(i for i in range(len(ext["batches"])) if i not in ext["answers"])
                try:
                    text = asrexternal.prompt(job["review_evidence"], ext["task"], ext["batches"][following])
                    ext.update(index=following, prompt=text)
                except llmconfig.LLMError as error:
                    # A later prompt failure must preserve this imported batch.
                    ext["prompt_error"] = error.say
        elif action == "prompt":
            try:
                text = asrexternal.prompt(job["review_evidence"], ext["task"], ext["batches"][index])
            except llmconfig.LLMError as error:
                raise Refusal(error.code, error.say)
            ext.update(index=index, prompt=text, prompt_error="")
        elif action == "finish":
            ext["finished"] = True
        elif action != "prompt":
            raise Refusal("bad-review", "Choose prompt, import answer, finish or cancel.")
        _external_merge(job)
        job["finished"] = _now()
        return result(token)


def external_files(token, source_sha256, session, index):
    import asrexternal
    with LOCK:
        if not isinstance(session, str) or not session:
            raise Refusal("stale-review", "Prepare a workspace prompt before downloading its files.", 409)
        job = _external_job(token, source_sha256, session)
        ext = job["external_review"]
        if ext["task"] != "workspace" or type(index) is not int or not 0 <= index < len(ext["batches"]):
            raise Refusal("bad-review", "Choose this workspace review's prompt batch.")
        try:
            units = ext["batches"][index]
            return asrexternal.bundle(job["review_evidence"], units, asrexternal.prompt(job["review_evidence"], ext["task"], units))
        except Exception as error:
            if hasattr(error, "say"):
                raise Refusal(error.code, error.say)
            raise Refusal("external-download", "The text workspace could not be prepared.")


def use_review(token, source_sha256, decisions, manual_edits=None):
    """Apply only chosen validated spans. Caption clocks/boundaries stay put."""
    import asrcorrection
    import llmconfig
    import wordtimes
    import ytpages
    job = _job(token)
    with LOCK:
        if job["state"] != DONE or not job.get("review_choice"):
            raise Refusal("review-first", "Choose how to review the transcript first.", 409)
        if job.get("review_choice") == "external" and not job.get("external_review", {}).get("finished"):
            raise Refusal("review-first", "Finish importing answers or choose Review received suggestions first.", 409)
        if not _review_source_current(job):
            raise Refusal("source-changed", "The local film changed. Transcribe it again.", 409)
        if (job["review_choice"] == "llm" and
                job.get("llm_config_fingerprint") != llmconfig.fingerprint(llmconfig.load())):
            job["correction_result"] = None
            job["correction"].update(state="failed", complete=False,
                error="The LLM settings changed. Choose review again; the old suggestions were discarded.")
            job["state"], job["finished"] = REVIEW_CHOICE, _now()
            raise Refusal("stale-review", "The LLM settings changed. Choose review again.", 409)
        evidence = job["review_evidence"]
        if source_sha256 != evidence["source_sha256"]:
            raise Refusal("stale-review", "That review no longer matches the Whisper result.", 409)
        try:
            panel, changed = asrcorrection.apply(job["text"], evidence,
                job.get("correction_result") or {"suggestions": []}, decisions, manual_edits)
        except llmconfig.LLMError as e:
            raise Refusal(e.code, e.say)
        original = ytpages.parse_transcript_text(job["text"], job["lang"])
        caps = ytpages.parse_transcript_text(panel, job["lang"])
        if [c["start"] for c in caps] != [c["start"] for c in original]:
            raise Refusal("invalid-suggestions", "That edit would change the caption boundaries; it was not applied.")
        out = result(token)
        out["text"] = panel
        # Rebuild from the immutable capture tape so a retried Use with a
        # different decision set does not inherit an earlier pending edit.
        doc = wordtimes.load(token)
        if doc:
            import copy
            doc["atoms"] = copy.deepcopy(doc.get("raw_atoms") or doc["atoms"])
            doc = wordtimes.sync(doc, caps, job["lang"])
            doc["panel_sha256"] = wordtimes.panel_hash(panel)
            wordtimes.hold(token, doc)
            out["words"] = dict(out["words"], panel_sha256=doc["panel_sha256"],
                                count=len(doc.get("atoms") or []), timings_stale=changed)
        if changed:
            # Audio has been deleted, so no exact re-alignment can be claimed.
            out["notes"].append("Caption timings are unchanged. Changed word timings need review in Edit the transcript; the recording has been deleted.")
        return out


# -------------------------------------------------------------------- the child
def _spec(gs, job):
    """What the worker is told: all of it made HERE, from what was checked."""
    pcm = job["kind"] == "youtube"
    try:
        model_path = gs.model_dir(job["model"])
    except (ValueError, OSError):
        raise Refusal("no-model", "The selected model is not installed.", 409)
    if pcm:
        if not os.path.isfile(job["pcm"]):
            raise Refusal("audio-gone", "The temporary recording disappeared.", 410)
        source = job["pcm"]
    else:
        source = job["source"]["path"]
        try:
            st = os.stat(source)
        except OSError:
            raise Refusal("film-unreadable", "The local film could not be read.", 422)
        if [st.st_size, st.st_mtime_ns, st.st_ino] != job["film"]:
            raise Refusal("film-changed", "The film changed since you named it -- name "
                          "it again.", 409)
    return {"source_path": source, "audio_kind": "pcm16" if pcm else "media",
            "lang": job["wlang"], "model_path": model_path, "device": job["planned"],
            "cpu_threads": job["threads"],
            "compute": {"cpu": "int8", "cuda": ["int8_float16", "float16"]},
            "mode": job["mode"], "film": job["film"], "parent": os.getpid(),
            "aligner_path": (gs.aligner_path(job["aligner"]) if job.get("aligner") else None)}


def _spawn(gs, job, spec_path):
    """The worker, in a process group of its own, and registered wherever the
    server looks to end its children -> the process, or None if the job was
    cancelled in the meantime."""
    env = dict(os.environ)
    env.update(_speech(lambda g: g.worker_env()))
    # nothing of the user's site-packages, no bytecode written into the
    # runtime, and no script directory on the path in front of it
    env.update(PYTHONNOUSERSITE="1", PYTHONDONTWRITEBYTECODE="1",
               PYTHONSAFEPATH="1", PYTHONIOENCODING="utf-8")
    kw = {"stdin": subprocess.DEVNULL, "stdout": subprocess.PIPE, "env": env,
          "text": True, "encoding": "utf-8", "errors": "replace", "bufsize": 1,
          "cwd": os.path.dirname(spec_path)}
    if WIN:
        kw["creationflags"] = (getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                               | getattr(subprocess, "CREATE_NO_WINDOW", 0))
    else:
        kw["start_new_session"] = True
        if sys.platform.startswith("linux"):
            kw["preexec_fn"] = _preexec
    with LOCK:
        if job["cancelled"]:
            return None
        with open(job["log"], "ab") as errs:
            proc = subprocess.Popen([sys.executable, "-B", "-u", WORKER, spec_path],
                                    stderr=errs, **kw)
        job["proc"] = proc
        CHILDREN.add(proc)
    track = getattr(gs, "track", None)
    if callable(track):
        track(proc)
    return proc


def _run(job):
    """The whole life of one job after its audio is in: the spec, the child,
    what it says, and the tidying up whatever happens."""
    proc = None
    gs = None
    try:
        gs = _getstt()
        # (the model is held already: start() took it for the whole of the job)
        with LOCK:
            if job["cancelled"]:
                return
            job["state"], job["started"] = PREPARING, _now()
        spec = _spec(gs, job)
        with open(job["spec"], "w", encoding="utf-8") as f:
            json.dump(spec, f)
        proc = _spawn(gs, job, job["spec"])
        if proc is None:
            return
        got = _listen(job, proc)
        rc = proc.wait()
        # THE WORKER HAS ENDED: its own words go to the log, and the recording
        # -- which has done its work, and is not to be kept merely because
        # Whisper needed it -- is deleted BEFORE the job says it is done, so
        # that nobody who has been told "done" can find sound left on the disk
        _show_log(job)
        _clean_files(job)
        if job["cancelled"]:
            return
        if got.get("done") is not None:
            _finish(job, got["done"])
        elif got.get("error") is not None:
            _end(job, FAILED, got["error"]["code"], got["error"]["say"])
        elif rc in (-9, 137):
            _end(job, FAILED, "killed", "Transcription was stopped by the system, most "
                 "likely because the computer ran out of memory.")
        else:
            _end(job, FAILED, "failed", "Transcription failed.")
    except Refusal as e:
        _end(job, FAILED, e.code, e.say)
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()
        _end(job, FAILED, "failed", "Transcription failed.")
    finally:
        if proc is not None:
            if proc.poll() is None:
                _kill(proc)
            with LOCK:
                CHILDREN.discard(proc)
                job["proc"] = None
            untrack = getattr(gs, "untrack", None)
            if callable(untrack):
                untrack(proc)
        # (again, and harmless once it has been done: what is left of a job that
        # went wrong before its worker ended)
        _show_log(job)
        _clean_files(job)
        _unhold(job)                     # whatever way this thread ended, the part goes


def _show_log(job):
    """The worker's own stderr -- where the technical GPU error and any
    traceback are -- into the server's log, for whoever looks; never into an
    answer."""
    try:
        with open(job["log"], encoding="utf-8", errors="replace") as f:
            text = f.read().strip()
    except OSError:
        return
    if text:
        print("speech to text (%s):\n%s" % (job["kind"], text[-4000:]), file=sys.stderr,
              flush=True)


def _listen(job, proc):
    """Read the worker's lines until it is done -> {"done": msg, "error": msg}
    (whichever came).  Anything that is not a JSON object is ignored."""
    got = {"done": None, "error": None}
    while True:
        line = proc.stdout.readline(MAX_LINE)
        if not line:
            return got
        if len(line) >= MAX_LINE and not line.endswith("\n"):
            _kill(proc)
            got["error"] = {"code": "failed", "say": "Transcription failed."}
            return got
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        if isinstance(msg, dict):
            _message(job, msg, got)


def _num(v, low=0.0, high=1e9):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        return None
    return float(min(high, max(low, v)))


def _message(job, msg, got):
    """One line of the worker's, believed as far as it can be checked."""
    kind = msg.get("t")
    with LOCK:
        if job["cancelled"]:
            return
        if kind == "device":
            # a second `device` is the one fall back: it starts over
            if msg.get("device") in ("cpu", "cuda"):
                job["device"] = msg["device"]
                job["fell_back"] = bool(msg.get("fell_back"))
                job["state"], job["done"] = LOADING, 0.0
        elif kind == "loading":
            job["state"] = LOADING
        elif kind == "aligning":
            job["state"] = ALIGNING
            total, done = _num(msg.get("total")), _num(msg.get("done"))
            if total:
                job["total"] = total
            if done is not None:
                job["done"] = done
        elif kind == "progress":
            # the first line, before the model is even asked for, only says how
            # long the audio is (0 of the whole); a later one, with something
            # done, says the words are being made
            total, done = _num(msg.get("total")), _num(msg.get("done"))
            if total:
                job["total"] = total
            if done is not None:
                job["done"] = done
                if done > 0 and job["state"] in (PREPARING, LOADING):
                    job["state"] = TRANSCRIBING
    if kind == "done":
        got["done"] = msg
    elif kind == "error":
        code = msg.get("code") if isinstance(msg.get("code"), str) else "failed"
        say = msg.get("say") if isinstance(msg.get("say"), str) else ""
        got["error"] = {"code": re.sub(r"[^a-z-]", "", code)[:40] or "failed",
                        "say": " ".join(say.split())[:300] or "Transcription failed."}


def _evidence_words(raw):
    import asrcorrection
    words = []
    for w in raw:
        if not isinstance(w, dict) or not isinstance(w.get("text"), str):
            continue
        alt, available = asrcorrection.alternatives(w.get("asr_alternatives"))
        words.append({"text": w["text"][:400], "start": _num(w.get("start")),
                      "end": _num(w.get("end")), "score": asrcorrection.score(w.get("score")),
                      "asr_alternatives": alt,
                      "alternatives_available": w.get("alternatives_available", available) is True})
    return words


def _finish(job, msg):
    """The worker is done: its segments onto the video's clock, into the
    add page's panel, and counted by the add page's own parser."""
    import sttpanel
    segs = []
    raw = msg.get("segments")
    for s in raw[:200000] if isinstance(raw, list) else []:
        if not isinstance(s, dict) or not isinstance(s.get("text"), str):
            continue
        a, b = _num(s.get("start")), _num(s.get("end"))
        if a is None:
            continue
        row = {"start": a, "end": b if b is not None else a, "text": s["text"][:4000]}
        words = []
        raw_words = s.get("words", []) if isinstance(s.get("words"), list) else []
        for w in raw_words[:MAX_LINE // 32]:
            if not isinstance(w, dict) or not isinstance(w.get("text"), str):
                continue
            wa, wb = _num(w.get("start")), _num(w.get("end"))
            if wa is None:
                continue
            words.append({"start": wa, "end": wb if wb is not None else wa,
                          "text": w["text"][:400], "score": _num(w.get("score"), -1e6, 1e6)})
        if words:
            row["words"] = words
        # ASR evidence is independent of the optional CTC word timing tape.
        if isinstance(s.get("asr_words"), list):
            row["asr_words"] = _evidence_words(s["asr_words"])
        else:
            row["asr_words"] = _evidence_words(raw_words if msg.get("word_source") != "aligner" else [])
        segs.append(row)
    if job["kind"] == "youtube" and job["marks"]:
        segs = sttpanel.remap(segs, job["marks"], SAMPLE_RATE)
    text, notes = sttpanel.segments_to_panel(segs)
    facts = sttpanel.facts(text, job["lang"]) if text.strip() else {"captions": 0}
    if not facts["captions"]:
        _end(job, FAILED, "no-speech", "No speech was heard in it. Check that the language "
             "is the one spoken, and that the video has sound.")
        return
    warning = ""
    if not facts.get("want"):
        import languages
        L = languages.LANGS.get(job["lang"])
        warning = ("Every caption came out in another script than %s: is the language "
                   "the one spoken?" % (L.name if L else job["lang"]))
    word_info = {"held": False, "count": 0}
    all_words = [w for seg in segs for w in (seg.get("words") or [])]
    if all_words:
        try:
            import wordtimes
            import ytpages
            source = msg.get("word_source") if msg.get("word_source") in ("whisper", "aligner") else "whisper"
            doc = wordtimes.empty(job["id"], job["lang"], all_words, source, job["model"])
            doc = wordtimes.sync(doc, ytpages.parse_transcript_text(text, job["lang"]), job["lang"])
            panel = wordtimes.panel_hash(text)
            doc["panel_sha256"] = panel
            wordtimes.hold(job["id"], doc)
            word_info = {"held": True, "count": len(doc.get("atoms") or []), "source": source,
                         "panel_sha256": panel}
        except Exception:  # noqa: BLE001 - words must never discard a successful transcript
            traceback.print_exc()
            notes.append("Word timestamps could not be kept for this transcription.")
    if isinstance(msg.get("word_warning"), str) and msg.get("word_warning"):
        notes.append(msg["word_warning"])
    import asrcorrection
    review_evidence = asrcorrection.evidence(segs, text, job["lang"])
    import asrdictionary
    resolver = asrdictionary.Resolver(job["lang"])
    with LOCK:
        if job["cancelled"]:
            return
        job["state"] = CHECKING
    _unhold(job)                         # worker is dead; dictionary work holds no model
    if not resolver.enrich(review_evidence, lambda: job["cancelled"]):
        return
    with LOCK:
        if job["cancelled"]:
            return
        job["review_evidence"] = review_evidence
        job["dictionary_resolver"] = resolver
        job["review_choice"] = None
        job["correction"] = {"state": "not-requested", "complete": False}
        job["text"], job["notes"], job["facts"], job["warning"], job["words"] = \
            text, notes, facts, warning, word_info
        job["done"], job["segments"] = job["total"] or job["done"], None
        job["state"], job["finished"] = REVIEW_CHOICE, _now()
        _unhold(job)                     # in the breath that says it is done


# ------------------------------------------------------------------ the server
def activity_entries(entry, keep, now=None):
    """The jobs as the activity list has them (lib/activity.py entry()), so
    that every page's Working pill, and the stop button's question, know a
    transcription is going on.  Kind `narration`: what estimating by the
    sound is already; the id has no token in it (every page reads this)."""
    now = _now() if now is None else now
    out = []
    with LOCK:
        # every page asks this every few seconds: a capture that stopped
        # arriving is noticed here, and leaves the list, without anybody
        # having to start another job to find out
        _expire()
        for job in list(JOBS.values()):
            over = job["state"] in (DONE, FAILED, REVIEW_CHOICE)
            if over and now - (job["finished"] or now) > keep:
                continue
            what = "Transcribing a YouTube video" if job["kind"] == "youtube" \
                else "Transcribing a film on this machine"
            out.append(entry(
                "stt:%s@%.3f" % (job["kind"], job["created"]), "narration", what,
                job["created"], stage=None if over else _say(job), page=PAGE,
                finished=job["finished"] if over else None,
                ok=job["state"] in (DONE, REVIEW_CHOICE)))
    return out


def startup():
    """At every start of the server, on a thread of its own: the temporary
    recordings and half-written files of a server that was killed, and the
    held waveforms nobody adopted, let go.  Neither folder is made here."""
    try:
        gs = _getstt()
        sweep = getattr(gs, "sweep", None)
        if callable(sweep):
            sweep()
    except Refusal:
        pass
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()
    try:
        import wavefile
        wavefile.sweep()
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()
    try:
        import wordtimes
        wordtimes.sweep()
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()
