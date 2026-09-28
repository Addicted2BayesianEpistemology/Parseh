#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""The child that listens: ONE transcription, reported on stdout as JSON lines.

    python3 sttworker.py <spec.json>          # made by lib/sttjobs.py, never by hand

Run by the server with Parseh's own Python and PYTHONPATH pointing at the
speech runtime (stt/runtime/...), where faster-whisper, CTranslate2, PyAV and
their own numpy live.  THE SERVER NEVER IMPORTS THEM: two numpys in one
process is fatal, and a broken GPU library can abort the interpreter it is
loaded into.  So the heavy work has a process of its own, which is also what
lets Stop kill it and lets a stopped server take it along.

WHAT IT SPEAKS -- one JSON object a line, ASCII only (a Windows console is
not UTF-8; the server's json.loads gives the Unicode back exactly):

    {"t":"device","device":"cpu"|"cuda","fell_back":false}
    {"t":"loading"}
    {"t":"progress","done":<media seconds>,"total":<media seconds>}
    {"t":"done","segments":[{"start","end","text"}],"duration":<s>,"language":"fa"}
    {"t":"error","code":"...","say":"a human sentence"}

THE SPEC is the only input: {source_path, audio_kind:"pcm16"|"media", lang,
model_path, device, cpu_threads, compute:{cpu:"int8", cuda:[...]}, mode,
film, parent}.  Every value was made by the server from inputs it had
checked, and is checked AGAIN here against short lists of what is allowed:
a value that is not on them never reaches CTranslate2 -- the precision
formats, the device and the model path are Parseh's to choose, never a
person's or a page's.

WHICH DEVICE.  `mode` is what the person chose:
    cpu   the CPU, int8, and CUDA is never so much as asked about;
    auto  the GPU when the server found one ready (`device`), and then, if it
          fails to load OR fails while the words are being made (the lazy
          "libcublas not found" and an out-of-memory both arrive that way),
          ONE more try on the CPU, from the start, said in `fell_back`;
    cuda  the GPU, and any failure is the person's to hear: no switching.

TEXT IS KEPT AS WHISPER GIVES IT: no transliteration, no translation
(task="transcribe"), Unicode and punctuation untouched.
"""
import gc
import json
import os
import re
import sys
import threading
import time
import traceback

MODES = ("auto", "cpu", "cuda")
CPU_COMPUTE = "int8"
GPU_COMPUTE = ("int8_float16", "float16")       # in this order: the lighter first
SAMPLE_RATE = 16000
BEAM_SIZE = 5
TICK = 0.25                                     # seconds between progress lines, at most
# \Z and not $: `$` also matches before a trailing newline, which is no letter
LANG_RE = re.compile(r"^[a-z]{2,3}\Z")

# what the person is told; the technical text goes to stderr, which the
# server keeps in its own log
SAYS = {
    "bad-spec": "The transcription could not be started.",
    "audio-gone": "The temporary recording disappeared.",
    "film-changed": "The film changed since you named it -- name it again.",
    "film-undecodable": "The local film could not be decoded.",
    "no-sound": "There is no sound in it to listen to.",
    "model-load": "The model could not be loaded.",
    "no-memory": "The computer ran out of memory for this model.",
    "gpu-error": "CUDA was requested but could not be initialized. "
                 "Choose Automatic or CPU to use the processor instead.",
    "gpu-memory": "The graphics card ran out of memory for this model. "
                  "Choose Automatic or CPU to use the processor instead.",
    "broken": "Speech to text could not start. Reinstall it in Settings, under Speech to text.",
    "failed": "Transcription failed.",
}


class Refused(Exception):
    def __init__(self, code, say=None):
        Exception.__init__(self, code)
        self.code = code
        self.say = say or SAYS.get(code) or SAYS["failed"]


def send(obj):
    """One line to the server.  A pipe nobody reads any more means the server
    has gone: there is nobody to work for."""
    try:
        sys.stdout.write(json.dumps(obj) + "\n")
        sys.stdout.flush()
    except (BrokenPipeError, OSError, ValueError):
        os._exit(3)


def log(where, exc=None):
    """The technical side, for the server's log (never the person's screen)."""
    sys.stderr.write("sttworker: %s\n" % where)
    if exc is not None:
        traceback.print_exception(type(exc), exc, exc.__traceback__, file=sys.stderr)
    sys.stderr.flush()


# ------------------------------------------------------------------- the spec
def read_spec(path):
    """The spec, checked value by value -> a dict this file may act on."""
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, ValueError, RecursionError):
        raise Refused("bad-spec")
    if not isinstance(raw, dict):
        raise Refused("bad-spec")
    spec = {}
    src = raw.get("source_path")
    if not isinstance(src, str) or not src or "\0" in src or not os.path.isabs(src):
        raise Refused("bad-spec")
    spec["source_path"] = src
    if raw.get("audio_kind") not in ("pcm16", "media"):
        raise Refused("bad-spec")
    spec["audio_kind"] = raw["audio_kind"]
    lang = raw.get("lang")
    if not isinstance(lang, str) or not LANG_RE.match(lang):
        raise Refused("bad-spec")
    spec["lang"] = lang
    model = raw.get("model_path")
    if not isinstance(model, str) or not model or "\0" in model or not os.path.isabs(model) \
            or not os.path.isdir(model):
        raise Refused("bad-spec")
    spec["model_path"] = model
    mode = raw.get("mode")
    device = raw.get("device")
    if mode not in MODES or device not in ("cpu", "cuda"):
        raise Refused("bad-spec")
    spec["mode"], spec["device"] = mode, device
    threads = raw.get("cpu_threads")
    if isinstance(threads, bool) or not isinstance(threads, int) or not 1 <= threads <= 64:
        raise Refused("bad-spec")
    spec["cpu_threads"] = threads
    comp = raw.get("compute")
    if not isinstance(comp, dict) or comp.get("cpu") != CPU_COMPUTE:
        raise Refused("bad-spec")
    gpu = comp.get("cuda")
    if not isinstance(gpu, list) or not gpu or any(c not in GPU_COMPUTE for c in gpu):
        raise Refused("bad-spec")
    spec["gpu_compute"] = [c for c in GPU_COMPUTE if c in gpu]
    film = raw.get("film")
    if film is not None:
        if not isinstance(film, list) or len(film) != 3 or not all(
                isinstance(x, int) and not isinstance(x, bool) for x in film):
            raise Refused("bad-spec")
    spec["film"] = film
    parent = raw.get("parent")
    spec["parent"] = parent if isinstance(parent, int) and not isinstance(parent, bool) else None
    return spec


# ---------------------------------------------------------------- the parent
def alive(pid):
    """Is a process still there?  (Not by signalling it: on Windows that would
    end it.  The same test lib/updater.py makes.)"""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        k = ctypes.windll.kernel32
        h = k.OpenProcess(0x00100000 | 0x1000, False, pid)   # SYNCHRONIZE | QUERY_LIMITED
        if not h:
            return False
        try:
            return k.WaitForSingleObject(h, 0) == 0x102        # WAIT_TIMEOUT: still running
        finally:
            k.CloseHandle(h)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    # a zombie is not a server: its own parent has not asked for its end yet
    try:
        with open("/proc/%d/stat" % pid, encoding="ascii", errors="replace") as f:
            return f.read().rsplit(")", 1)[-1].split()[0] != "Z"
    except OSError:
        return True


def watch_parent(pid):
    """A server killed outright cannot say goodbye, and on Windows and macOS
    nothing else ends this child: look for it, and go when it is gone.  (On
    Linux the kernel does it as well, PR_SET_PDEATHSIG, set by the server.)"""
    if not pid:
        return

    def loop():
        while True:
            time.sleep(1.5)
            if not alive(pid):
                os._exit(3)
    threading.Thread(target=loop, daemon=True).start()


# ---------------------------------------------------------------------- audio
def load_pcm(np, path):
    """The PCM16LE mono 16 kHz file a YouTube capture was written to -> float32,
    the array faster-whisper takes as it is.  Converted in blocks: a
    three-hour capture is 170 million samples, and one int16 copy beside one
    float64 copy would be a gigabyte and a half for nothing."""
    try:
        n = os.path.getsize(path) // 2
        out = np.empty(n, dtype=np.float32)
        pos, block = 0, 1 << 20
        with open(path, "rb") as f:
            while pos < n:
                raw = f.read(min(block, n - pos) * 2)
                if not raw:
                    break
                got = np.frombuffer(raw[:len(raw) - len(raw) % 2], dtype="<i2")
                out[pos:pos + len(got)] = got / 32768.0
                pos += len(got)
    except OSError:
        raise Refused("audio-gone")
    return out[:pos]


def load_media(np, spec):
    """A film on this machine -> float32 mono 16 kHz, decoded by PyAV (which
    faster-whisper brings): no system ffmpeg, and the film is only ever read."""
    path = spec["source_path"]
    if spec["film"]:
        try:
            st = os.stat(path)
        except OSError:
            raise Refused("film-undecodable")
        if [st.st_size, st.st_mtime_ns, st.st_ino] != spec["film"]:
            raise Refused("film-changed")
    if not os.path.isfile(path):
        raise Refused("film-undecodable")
    try:
        from faster_whisper.audio import decode_audio
        audio = decode_audio(path, sampling_rate=SAMPLE_RATE)
    except Exception as e:                                   # noqa: BLE001
        log("the film could not be decoded", e)
        raise Refused("film-undecodable")
    if getattr(audio, "ndim", 1) != 1:
        audio = np.asarray(audio, dtype=np.float32).reshape(-1)
    return audio


# ---------------------------------------------------------------- the failing
def is_memory(exc):
    """Did it fail for want of memory?  CTranslate2 says `CUDA failed with
    error out of memory` as a RuntimeError, and a CPU one is MemoryError."""
    said = str(exc).lower()
    return isinstance(exc, MemoryError) or "out of memory" in said \
        or "alloc_failed" in said or "bad_alloc" in said or "cannot allocate memory" in said


def gpu_refusal(exc):
    return Refused("gpu-memory" if is_memory(exc) else "gpu-error")


# ------------------------------------------------------------------ the model
def load_model(WhisperModel, spec, device):
    """The model on one device, with the precision Parseh chooses.  The CPU
    is int8 and nothing else.  The card is asked for int8_float16 first and
    float16 after it, because a card that cannot do the first says so with a
    ValueError at load and the second may still fit it; anything else that
    goes wrong is the card's, and is not tried again with another precision."""
    if device == "cpu":
        return WhisperModel(spec["model_path"], device="cpu", compute_type=CPU_COMPUTE,
                            cpu_threads=spec["cpu_threads"], local_files_only=True)
    last = None
    for compute in spec["gpu_compute"]:
        try:
            return WhisperModel(spec["model_path"], device="cuda", compute_type=compute,
                                local_files_only=True)
        except ValueError as e:
            last = e
            log("the graphics card does not do %s" % compute, e)
    raise last


def listen(WhisperModel, spec, audio, device, fell_back):
    """One try on one device -> (segments, language).  The generator that
    transcribe() returns does the actual work as it is consumed, so this is
    where a GPU that loaded and cannot compute shows itself."""
    send({"t": "device", "device": device, "fell_back": fell_back})
    send({"t": "loading"})
    model = found = info = None
    try:
        try:
            model = load_model(WhisperModel, spec, device)
        except Exception as e:                               # noqa: BLE001
            log("the model did not load on the %s" % device, e)
            if device == "cuda":
                raise gpu_refusal(e)
            raise Refused("no-memory" if is_memory(e) else "model-load")
        seconds = len(audio) / float(SAMPLE_RATE)
        try:
            found, info = model.transcribe(audio, language=spec["lang"], beam_size=BEAM_SIZE,
                                           vad_filter=True, task="transcribe")
            total = float(getattr(info, "duration", 0) or 0) or seconds
            out, last = [], 0.0
            for s in found:
                out.append({"start": round(float(s.start), 3), "end": round(float(s.end), 3),
                            "text": str(s.text)})
                now = time.time()
                if now - last >= TICK:
                    last = now
                    send({"t": "progress", "done": min(float(s.end), total), "total": total})
        except Exception as e:                               # noqa: BLE001
            log("the transcription stopped on the %s" % device, e)
            if device == "cuda":
                raise gpu_refusal(e)
            raise Refused("no-memory" if is_memory(e) else "failed")
        send({"t": "progress", "done": total, "total": total})
        return out, getattr(info, "language", None) or spec["lang"]
    finally:
        # the generator holds the model, and a failure's traceback holds the
        # generator: let all three go before anything else is loaded, so two
        # copies of a multi-gigabyte model are never alive together
        model = found = info = None
        gc.collect()


def run(spec):
    try:
        import numpy as np
        from faster_whisper import WhisperModel
    except (ImportError, OSError) as e:
        # (OSError too: on Windows a library that cannot be loaded -- a DLL the
        # program needs and the computer lacks -- is the loader's own error, not
        # an ImportError; the person is told the same, the log has the words)
        log("the speech runtime could not be imported", e)
        raise Refused("broken")

    audio = load_pcm(np, spec["source_path"]) if spec["audio_kind"] == "pcm16" \
        else load_media(np, spec)
    if len(audio) < 1:
        raise Refused("no-sound")
    seconds = len(audio) / float(SAMPLE_RATE)
    send({"t": "progress", "done": 0.0, "total": seconds})
    mode = spec["mode"]
    # `cpu` never reaches for the card, whatever else the spec says
    first = "cuda" if mode == "cuda" or (mode == "auto" and spec["device"] == "cuda") else "cpu"
    fell = None
    try:
        segments, language = listen(WhisperModel, spec, audio, first, False)
    except Refused as e:
        # ONE fall back, and only for `auto` on a card: an explicit choice of
        # the card is answered with the card's own error and not hidden
        if first != "cuda" or mode != "auto":
            raise
        fell = e.code
    if fell:
        # OUTSIDE the except block, so the failed try's frames are let go
        # before the second one loads a model of its own
        log("falling back to the CPU once (%s)" % fell)
        gc.collect()
        segments, language = listen(WhisperModel, spec, audio, "cpu", True)
    send({"t": "done", "segments": segments, "duration": round(seconds, 3),
          "language": language})


def main(argv):
    if len(argv) != 2:
        send({"t": "error", "code": "bad-spec", "say": SAYS["bad-spec"]})
        return 2
    try:
        spec = read_spec(argv[1])
        watch_parent(spec["parent"])
        run(spec)
    except Refused as e:
        send({"t": "error", "code": e.code, "say": e.say})
        return 2
    except BaseException as e:                               # noqa: BLE001
        if isinstance(e, (KeyboardInterrupt, SystemExit)):
            raise
        log("it stopped unexpectedly", e)
        send({"t": "error", "code": "no-memory" if is_memory(e) else "failed",
              "say": SAYS["no-memory" if is_memory(e) else "failed"]})
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
