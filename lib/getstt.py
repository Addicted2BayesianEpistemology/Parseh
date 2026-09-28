#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Speech to text, optional and local: the program that runs Whisper, the two
models it reads, and what this computer can run them on (TO-DO §7.23, a0.4.1).

    python3 lib/getstt.py                       what is installed, and the processor
    python3 lib/getstt.py get large-v3-turbo    the program (if missing) and that model
    python3 lib/getstt.py get runtime           just the program
    python3 lib/getstt.py check                 look at the graphics card again

WHAT THIS IS.  A transcript made on the computer Parseh runs on, while a video
is being added: faster-whisper (CTranslate2) reading either of two models.  It
is optional in every sense.  Nothing here is imported, installed or started
until somebody presses *get it* on Settings -> Speech to text, Parseh's own
environment gains no package (environment.yml and lib/runtime.py do not name
it), and a person who never asks for it has the toolbox they had.

THE PROGRAM LIVES IN A FOLDER OF ITS OWN, `stt/runtime/<generation>-<python>/`,
made by `pip install --target` from lib/stt-requirements.txt -- 23 packages,
each pinned by the hash of every wheel that can be taken on the five computers
Parseh installs on, so what is installed is what the Parseh release names and
nothing PyPI says later.  It is never on THE SERVER'S sys.path: it brings its
own numpy, and two numpys in one process is fatal.  Everything that touches it
-- the transcription worker (lib/sttworker.py) and the hardware probe
(lib/sttprobe.py) -- is a CHILD PROCESS run with the Parseh python and
PYTHONPATH pointing there (worker_env()), so a graphics driver that aborts the
interpreter takes down a child, not the server, and this module stays standard
library only and importable with none of it installed.

THE FOLDER NAME IS THE RECORD.  The generation (PIN below, moved by hand
whenever the pin list moves) and the Python tag (cp312) are in the name, and
the versions are in the *.dist-info folders pip wrote, so "installed by an
older Parseh", "by a newer one" and "for another Python" are worked out from
the disk and there is no store, no format row and nothing for a step back to
a0.4.0 to mind.  A model's folder carries a meta.json in the manner of mt/'s.

THE MODELS are the two conversions of OpenAI's Whisper large-v3 and
large-v3-turbo that faster-whisper itself names, each at a pinned COMMIT of its
repository with the size and SHA-256 of all five files it needs.  They go
through lib/download.py like every other optional download -- resumed, stopped
between two blocks, checked before they are put in place -- into
`stt/models/<id>/`, and are loaded later from that path with the network
switched off.  All five files matter: without tokenizer.json faster-whisper
reaches for the network.

WHAT MAY BE FETCHED IS FIXED HERE.  A model is one of two names, a processing
mode one of three, and the only bytes that can arrive are the hash-checked
wheels and the pinned files -- so whoever presses the button, nothing a client
sends becomes a path, a repository, a device or a package.

THE GRAPHICS CARD IS DETECTED, NEVER INSTALLED.  The CPU always works (int8).
An NVIDIA card is used only when a probe run in a child has PROVED it can: the
driver sees it, this program's CUDA build lists a half-precision type for it,
and cuBLAS for CUDA 12 loads.  Counting devices is not proof -- with cuBLAS
missing the count is 1 and the model even loads, and the failure comes later
inside the first segment -- so the probe loads cuBLAS itself.  What the
pinned CTranslate2 needs is written once, in GPU_NEEDS, and every sentence
about it is made from that.
"""
import argparse
import contextlib
import functools
import io
import json
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.error

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import download       # noqa: E402  resumable, stoppable, and says how far
import version        # noqa: E402  who is asking: UA

STT_DIR = os.path.join(ROOT, "stt")
REQUIREMENTS = os.path.join(HERE, "stt-requirements.txt")
PROBE = os.path.join(HERE, "sttprobe.py")

# ---------------------------------------------------------------- the pin
# THE ONE PLACE.  Moving the program means moving these together, by hand:
# lib/stt-requirements.txt (hashes included), PIN below, MEASURED, and the
# generation.  tests/test_getstt.py holds them to one another.
#
# `generation` is the number in the runtime's folder name.  Raise it whenever
# the pin list changes: the folder a Parseh made under the old number is then
# "installed by an older Parseh", with one button to make the new one.
RUNTIME_PYTHON = "3.12"                     # the wheels are cp312
PYTAG = "cp%d%d" % sys.version_info[:2]     # the Python running this Parseh
PIN = {
    "generation": 1,
    "python": "cp312",
    "faster-whisper": "1.2.1",
    "ctranslate2": "4.8.2",
    "av": "18.1.0",
    "tokenizers": "0.23.2",
    "huggingface-hub": "1.33.0",
    "onnxruntime": "1.30.0",                # 1.23.2 on an Intel Mac: nothing newer is built for it
}
# what has to be in a finished program's folder: (distribution, exact version or
# None for "any").  The names are those of the *.dist-info folders pip writes.
REQUIRED = (("faster_whisper", PIN["faster-whisper"]), ("ctranslate2", PIN["ctranslate2"]),
            ("av", PIN["av"]), ("tokenizers", PIN["tokenizers"]),
            ("huggingface_hub", PIN["huggingface-hub"]), ("onnxruntime", None),
            ("numpy", None), ("tqdm", None), ("pyyaml", None))

# WHAT THE GRAPHICS CARD NEEDS, for the pinned CTranslate2 (4.8.2).  This is
# what a real GPU transcription needed on a machine with no cuDNN anywhere:
# an NVIDIA driver, and cuBLAS for CUDA 12.  cuDNN stopped being needed at
# CTranslate2 4.6.3 ("makes cuDNN an optional dependency"), though
# faster-whisper 1.2.1's own README still says "cuDNN 9".  Every sentence the
# pages say about it is made from this table, so a later pin changes one place.
GPU_NEEDS = {"driver": True, "cublas": "12", "cudnn": None}
# the only CTranslate2 wheels with CUDA code in them
GPU_PLATFORMS = ("linux x86_64", "windows amd64")
CUDA_LIBS = {"linux": "libcublas.so.12", "win32": "cublas64_12.dll"}
# where a person gets the two things (the archive, because "latest" is CUDA 13,
# whose cuBLAS this program cannot use)
GPU_LINKS = {"driver": "https://www.nvidia.com/Download/index.aspx",
             "cublas": "https://developer.nvidia.com/cuda-toolkit-archive"}
# THE COMPUTE TYPES, chosen for the person: never asked.  The CPU's is int8;
# the card's are tried in this order and the first its compute capability
# supports is used.
COMPUTE = {"cpu": "int8", "cuda": ("int8_float16", "float16")}
# where a computer may look for cuBLAS when the loader does not find it by
# name: a CUDA toolkit put in its usual place.  ONE SWITCH; off, only what the
# loader itself finds counts.
SCAN_FOR_CUBLAS = True

MODES = ("auto", "cpu", "cuda")
MODELS = ("large-v3-turbo", "large-v3")     # the ONLY two identifiers
ALLOWED_MODELS = frozenset(MODELS)
DEFAULT_MODEL = "large-v3-turbo"
PARTS = ("runtime",) + MODELS               # what a job may name
SETTINGS_PAGE = "/settings/speech/"
GUIDE = "/guide/site/lookup-and-languages/speech-to-text.html"

# THE MODELS, PINNED: the repository, the COMMIT of it (never `main`), and the
# size and SHA-256 of every file a model folder needs -- read from the
# repositories' own listings at those commits and re-hashed on 2026-09-28.
# The turbo conversion is `dropbox-dash/…` now; faster-whisper 1.2.1 still
# names the old `mobiuslabsgmbh/…`, which answers with a redirect to it.  The
# two repositories' tokenizer.json and config.json differ: nothing is shared.
MODEL_PINS = {
    "large-v3-turbo": {
        "repo": "dropbox-dash/faster-whisper-large-v3-turbo",
        "revision": "0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf",
        "files": {
            "config.json": ("b0253ea6c0d3bea6b1e19e91a02acfd3b53f4467362efcb5a3e6b16c9b3a9b7e", 2263),
            "model.bin": ("e76620f83d5f5b69efd3d87e3dc180c1bd21df9fbebacfd4335e5e1efcc018da", 1617884929),
            "preprocessor_config.json": ("7ccc62c6f2765af1f3b46c00c9b5894426835a05021c8b9c01eecb6dfb542711", 340),
            "tokenizer.json": ("297b13372ac43916285644fb9687add3cc62ee2a1adb60da3dc25cc94c1871fd", 2710337),
            "vocabulary.json": ("c69260f2ab26d659b7c398f9a2b2b48ed0df16c3b47d7326782fd9cba71690c1", 1068114),
        },
    },
    "large-v3": {
        "repo": "Systran/faster-whisper-large-v3",
        "revision": "edaa852ec7e145841d8ffdb056a99866b5f0a478",
        "files": {
            "config.json": ("a9306624f5ec14270a014b647e5c316b6e03a662c369758d1b90697a7b0655b9", 2394),
            "model.bin": ("69f74147e3334731bc3a76048724833325d2ec74642fb52620eda87352e3d4f1", 3087284237),
            "preprocessor_config.json": ("7ccc62c6f2765af1f3b46c00c9b5894426835a05021c8b9c01eecb6dfb542711", 340),
            "tokenizer.json": ("6d8cbd7cd0d8d5815e478dac67b85a26bbe77c1f5e0c6d76d1ce2abc0e5f21ca", 2480617),
            "vocabulary.json": ("c69260f2ab26d659b7c398f9a2b2b48ed0df16c3b47d7326782fd9cba71690c1", 1068114),
        },
    },
}
MODEL_URL = "https://huggingface.co/%(repo)s/resolve/%(revision)s/%(file)s"

# WHAT A PART SAYS ABOUT ITSELF on the page and to the add page: the label
# the two models are always shown by, the trade-off, and what they need.
MODEL_INFO = {
    "large-v3-turbo": {
        "label": "faster-whisper / large-v3-turbo",
        "tag": "Recommended · faster and lighter",
        "hint": "The one to start with: about half the download, and several times faster than "
                "large-v3 on a CPU. It needs about 2.2 GB of memory there.",
        "memory": "about 2.2 GB"},
    "large-v3": {
        "label": "faster-whisper / large-v3",
        "tag": "Higher accuracy · larger and slower",
        "hint": "The higher-accuracy option, for what the turbo model gets wrong: twice the "
                "download, about five times slower on a CPU, and it needs about 6 GB of memory "
                "there. A small graphics card may not hold it; Parseh then continues on the CPU.",
        "memory": "about 6 GB"},
}

# WHAT EACH COSTS, in bytes, MEASURED on 2026-09-28: the wheels pip takes on
# each kind of computer (every file re-hashed against PyPI's digest), what
# they occupy once installed, and the models' files.  Installed, on Linux
# x86_64, is a real install's tree (430,842,783 bytes, the .pyc pip writes
# included); the four other kinds' are their wheels' unpacked sizes taken from
# the wheels' own listings and scaled by what the real one grew (x1.0665), so
# they are "about".  Read by plan(), so the page says how big before anybody
# presses a button, and never asks a server.
MEASURED = {
    "runtime": {"linux x86_64": 127879938, "linux aarch64": 99698704, "macOS arm64": 63883459,
                "macOS x86_64": 88689754, "windows amd64": 84461419},
    "runtime kept": {"linux x86_64": 430842783, "linux aarch64": 332150000, "macOS arm64": 190416000,
                     "macOS x86_64": 338444000, "windows amd64": 260996000},
    "large-v3-turbo": sum(s for _h, s in MODEL_PINS["large-v3-turbo"]["files"].values()),
    "large-v3": sum(s for _h, s in MODEL_PINS["large-v3"]["files"].values()),
}
# below these, pip finds no wheel: the newest pins raise the floor of the two Macs
RUNTIME_FLOORS = {"macOS arm64": 14, "macOS x86_64": 13}
# THE LONGEST PATH INSIDE THE PROGRAM'S FOLDER, in characters, from the pinned wheels' own
# listings with the .pyc pip compiles beside them (onnxruntime/tools/ort_format_model/
# ort_flatbuffers_py/fbs/__pycache__/RuntimeOptimizationRecordContainerEntry.cpython-312.pyc).
# Windows makes no file whose whole path is longer than 259 characters unless it has been told
# to (LongPathsEnabled), so a Parseh folder deeper than that leaves no room for it.
LONGEST_TREE_PATH = 125
WINDOWS_PATH_LIMIT = 259

# who says what, for lib/notices.py: the program (one line naming what it is
# made of, and each licence its parts carry) and the models
SOURCE = ("faster-whisper %s, CTranslate2 %s, PyAV %s and onnxruntime %s, from PyPI"
          % (PIN["faster-whisper"], PIN["ctranslate2"], PIN["av"], PIN["onnxruntime"]))
LICENCE = "MIT"                              # faster-whisper, CTranslate2, onnxruntime
# and the ones that come with it, each said with what carries it
RUNTIME_LICENCES = (("PyAV", "BSD-3-Clause"),
                    ("the FFmpeg libraries inside PyAV", "LGPL-3.0-or-later"))
MODEL_SOURCE = ("OpenAI Whisper large-v3 and large-v3-turbo, converted to CTranslate2 "
                "(Systran; Mobius Labs)")
MODEL_LICENCE = "MIT"
UA = "Parseh/%s (+https://github.com/Addicted2BayesianEpistemology/Parseh)" % version.VERSION

# WHISPER'S LANGUAGES at the pinned program (faster_whisper/tokenizer.py,
# _LANGUAGE_CODES: 100 of them) -- kept here and not as a field of
# lib/languages.json, which a language a person adds does not carry.  A
# Parseh code IS the Whisper code, so there is nothing to translate.
WHISPER_LANGUAGES = frozenset(
    "af am ar as az ba be bg bn bo br bs ca cs cy da de el en es et eu fa fi fo fr gl gu ha haw he "
    "hi hr ht hu hy id is it ja jw ka kk km kn ko la lb ln lo lt lv mg mi mk ml mn mr ms mt my ne "
    "nl nn no oc pa pl ps pt ro ru sa sd si sk sl sn so sq sr su sv sw ta te tg th tk tl tr tt uk "
    "ur uz vi yi yo zh yue".split())


class SpeechError(Exception):
    """Something a person can be told, in a sentence: `code` for the program,
    `say` for the page.  Never a traceback."""

    def __init__(self, code, say):
        super().__init__(say)
        self.code = code
        self.say = say


# ------------------------------------------------------------ where things are
# EVERY PATH IS A FUNCTION OF STT_DIR, AT THE MOMENT OF THE CALL: a test that
# points STT_DIR at a temporary tree must never find this module holding the
# checkout's own stt/ (which may be a computer's 3 GB of models).
def tmp_dir():
    return os.path.join(STT_DIR, "tmp")


def __getattr__(name):
    """`getstt.TMP_DIR`, as the interface says it, but following STT_DIR."""
    if name == "TMP_DIR":
        return tmp_dir()
    raise AttributeError("module %r has no attribute %r" % (__name__, name))


def _runtimes_dir():
    return os.path.join(STT_DIR, "runtime")


def _models_dir():
    return os.path.join(STT_DIR, "models")


def runtime_folder():
    """Where THIS Parseh's program lives once it is installed."""
    return os.path.join(_runtimes_dir(), "%d-%s" % (PIN["generation"], PYTAG))


def _stage_folder():
    return os.path.join(STT_DIR, "runtime.part-%d" % os.getpid())


def _model_part(key):
    return model_dir(key) + ".part"


def model_dir(key):
    """The folder of a model -- raises ValueError for anything but the two
    identifiers.  The only door from a name to a path: what a client sends
    never gets here unless it is one of two exact strings."""
    if not isinstance(key, str) or key not in ALLOWED_MODELS:
        raise ValueError("%r is not one of the speech models (%s)" % (key, ", ".join(MODELS)))
    return os.path.join(_models_dir(), key)


def check_model(key):
    """`key` if it is a model, else a SpeechError a route answers with."""
    if not isinstance(key, str) or key not in ALLOWED_MODELS:
        raise SpeechError("bad-model", "Choose one of the two speech models: %s."
                          % " or ".join(MODELS))
    return key


def check_mode(mode):
    if not isinstance(mode, str) or mode not in MODES:
        raise SpeechError("bad-processing", "Processing is Automatic, CPU or NVIDIA GPU.")
    return mode


# --------------------------------------------------- this computer, and the pin
def _mb(n):
    return ("%.1f GB" % (n / 1e9)) if n >= 1e9 else ("%d MB" % max(1, round(n / 1e6)))


@functools.lru_cache(maxsize=1)
def platform_key():
    """The kind of computer this is, as MEASURED names it -- or None where no
    wheel of the program exists (Linux on another processor, or without glibc)."""
    machine = platform.machine().lower()
    arch = {"x86_64": "x86_64", "amd64": "x86_64", "arm64": "arm64", "aarch64": "aarch64"}.get(machine)
    if sys.platform.startswith("linux"):
        if arch not in ("x86_64", "aarch64"):
            return None
        return "linux " + arch
    if sys.platform == "darwin":
        return {"arm64": "macOS arm64", "x86_64": "macOS x86_64"}.get(arch)
    if sys.platform == "win32":
        return "windows amd64" if arch == "x86_64" else None
    return None


def _mac_major():
    try:
        return int((platform.mac_ver()[0] or "0").split(".")[0])
    except ValueError:
        return 0


@functools.lru_cache(maxsize=1)
def _glibc():
    """(name, version) of this Linux's C library, from platform.libc_ver()
    -- which reads the interpreter's own binary, so once."""
    try:
        return platform.libc_ver()
    except OSError:
        return ("", "")


def has_pip():
    import importlib.util
    try:
        return importlib.util.find_spec("pip") is not None
    except (ImportError, ValueError):
        return False


def cannot_run():
    """Why the program cannot RUN on this computer, in a sentence -- or "".
    Python and the kind of computer are fixed by the wheels: they are cp312
    and built for five kinds of computer."""
    if sys.version_info[:2] != tuple(int(n) for n in RUNTIME_PYTHON.split(".")):
        return ("This Parseh runs on Python %d.%d, and the speech program is built for Python "
                "%s only." % (sys.version_info[0], sys.version_info[1], RUNTIME_PYTHON))
    key = platform_key()
    if key is None:
        return ("There is no speech program for this kind of computer (%s, %s)."
                % (sys.platform, platform.machine() or "unknown"))
    if key.startswith("linux"):
        libc, ver = _glibc()
        if libc != "glibc":
            return "The speech program needs the GNU C library, and this Linux uses another."
        try:
            major, minor = (int(n) for n in (ver.split(".") + ["0"])[:2])
        except ValueError:
            major, minor = 2, 28
        if (major, minor) < (2, 28):
            return "The speech program needs glibc 2.28 or newer; this computer has %s." % ver
    floor = RUNTIME_FLOORS.get(key)
    if floor and _mac_major() and _mac_major() < floor:
        return ("Speech to text needs macOS %d or newer on this kind of Mac; this one is macOS %d."
                % (floor, _mac_major()))
    return ""


def _long_paths_on():
    """Has this Windows been told to make files at paths over 259 characters?"""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"SYSTEM\CurrentControlSet\Control\FileSystem") as k:
            return winreg.QueryValueEx(k, "LongPathsEnabled")[0] == 1
    except (ImportError, OSError):
        return False


def _too_deep():
    """A sentence where Parseh's folder is too deep on Windows for the program's longest
    file name to fit under the 259-character limit, else "".  It is measured, not
    guessed: LONGEST_TREE_PATH is the longest path in the pinned wheels."""
    if os.name != "nt":
        return ""
    room = len(os.path.abspath(os.path.join(STT_DIR, "runtime.part-99999"))) + 1 + LONGEST_TREE_PATH
    if room <= WINDOWS_PATH_LIMIT or _long_paths_on():
        return ""
    return ("Parseh's folder is too deep for Windows: some of the speech program's files "
            "have names %d characters long, and with Parseh where it is they would pass "
            "the %d Windows allows. Move Parseh's folder nearer the top of a drive, or turn "
            "on long paths in Windows, then come back." % (LONGEST_TREE_PATH, WINDOWS_PATH_LIMIT))


def unavailable_reason():
    """Why the program cannot be INSTALLED here -- what stops it running, or
    no pip to install it with -- in a sentence, or "".  The page offers no
    button where this speaks."""
    return cannot_run() or ("" if has_pip() else
                            "This Python has no pip, and pip is what installs the speech "
                            "program. Parseh's own environment has it.") or _too_deep()


def _dists(folder):
    """{distribution: version} of the *.dist-info folders in a program folder,
    names lower-cased with '-' and '.' as '_'."""
    out = {}
    try:
        names = os.listdir(folder)
    except OSError:
        return out
    for n in names:
        if n.endswith(".dist-info"):
            name, _, ver = n[:-len(".dist-info")].partition("-")
            out[re.sub(r"[-.]+", "_", name).lower()] = ver
    return out


def _tree_size(folder):
    total = 0
    for here, _dirs, files in os.walk(folder):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(here, f))
            except OSError:
                pass
    return total


_SIZES = {}                                  # folder -> (when, bytes): a walk of 400 MB is not for every poll


def _kept(folder, ttl=30):
    now = time.time()
    got = _SIZES.get(folder)
    if got and now - got[0] < ttl:
        return got[1]
    size = _tree_size(folder)
    _SIZES[folder] = (now, size)
    return size


def _runtime_folders():
    """[(generation, python tag, folder name)] of what is under stt/runtime/."""
    out = []
    try:
        names = os.listdir(_runtimes_dir())
    except OSError:
        return out
    for n in sorted(names):
        m = re.match(r"^(\d+)-(cp\d+)$", n)
        if m and os.path.isdir(os.path.join(_runtimes_dir(), n)):
            out.append((int(m.group(1)), m.group(2), n))
    return out


def runtime():
    """What is installed of the program, from the folder's name and the
    dist-info folders inside it -> a dict:

        state    absent | ready | older | newer | other_python | unavailable | broken
        have     something is there (any generation, any Python)
        ready    a job can run now
        why      in words, for every state but ready and absent
        version, ctranslate2, generation, python, size, can_install

    `older`/`newer` are the generation in the folder's name against PIN's;
    `other_python` is a folder made for a different Python; `broken` is a
    folder of this generation and Python that lacks what the pin names.
    """
    reason = cannot_run()
    folders = _runtime_folders()
    mine = "%d-%s" % (PIN["generation"], PYTAG)
    stuck = unavailable_reason()
    row = {"state": "absent", "have": False, "ready": False, "why": "", "version": "",
           "ctranslate2": "", "generation": None, "python": "", "python_running": PYTAG,
           "size": 0, "can_install": not stuck, "unavailable": stuck}
    here = [f for f in folders if f[2] == mine]
    if here:
        path = os.path.join(_runtimes_dir(), mine)
        got = _dists(path)
        missing = [d for d, v in REQUIRED if d not in got or (v and got[d] != v)]
        row.update(have=True, generation=PIN["generation"], python=PYTAG,
                   version=got.get("faster_whisper", ""), ctranslate2=got.get("ctranslate2", ""))
        if missing:
            row.update(state="broken", size=_kept(path),
                       why="The speech program's folder is incomplete (%s is missing or is not the "
                           "version this Parseh names). Install it again." % missing[0].replace("_", "-"))
        elif reason:
            row.update(state="unavailable", why=reason)
        else:
            row.update(state="ready", ready=True, size=_kept(path))
        return row
    if folders:
        gen, tag, name = sorted(folders, key=lambda f: (f[1] == PYTAG, f[0]))[-1]
        path = os.path.join(_runtimes_dir(), name)
        got = _dists(path)
        row.update(have=True, generation=gen, python=tag, size=_kept(path),
                   version=got.get("faster_whisper", ""), ctranslate2=got.get("ctranslate2", ""))
        if tag != PYTAG:
            row.update(state="other_python",
                       why="It was installed for Python %s.%s; this Parseh runs Python %d.%d."
                           % (tag[2], tag[3:], sys.version_info[0], sys.version_info[1]))
        elif gen < PIN["generation"]:
            row.update(state="older",
                       why="It was installed by an older Parseh. It is made again, once, and "
                           "the old one is taken away when the new one is whole.")
        else:
            row.update(state="newer",
                       why="It was installed by a newer Parseh than this one, so this one "
                           "will not run it.")
        if reason:
            row.update(state="unavailable", why=reason)
        return row
    if stuck:
        row.update(state="unavailable", why=stuck)
    return row


def runtime_ready():
    return runtime()["ready"]


def runtime_dir():
    """The folder that goes on a child's PYTHONPATH, or None while the program
    is not there (ready means complete for this Parseh's pin and Python)."""
    return runtime_folder() if runtime()["ready"] else None


# -------------------------------------------------------------------- models
def model_info(key):
    """One model: state absent | ready | older | newer | broken, size, built,
    why -- from its folder and its meta.json, by presence and size (a
    3 GB file is hashed when it is fetched, never at every status)."""
    pin = MODEL_PINS[key]
    path = model_dir(key)
    row = {"state": "absent", "have": False, "ready": False, "size": 0, "built": "",
           "revision": "", "why": ""}
    if not os.path.isdir(path):
        return row
    meta = {}
    try:
        with io.open(os.path.join(path, "meta.json"), encoding="utf-8") as f:
            meta = json.load(f)
    except (OSError, ValueError):
        meta = {}
    if not isinstance(meta, dict):
        meta = {}                       # a meta.json somebody wrote by hand: not a record
    sizes = {}
    for name in pin["files"]:
        try:
            sizes[name] = os.path.getsize(os.path.join(path, name))
        except OSError:
            sizes[name] = None
    row.update(have=True, size=sum(s for s in sizes.values() if s), built=meta.get("built", ""),
               revision=meta.get("revision", ""))
    revision = meta.get("revision")
    if revision and revision != pin["revision"]:
        try:
            newer = int(meta.get("pin") or 0) > PIN["generation"]
        except (TypeError, ValueError):
            newer = False
        row.update(state="newer" if newer else "older",
                   why="It was fetched by %s Parseh, at another version of the model."
                       % ("a newer" if newer else "an older"))
        return row
    bad = [n for n, (_h, want) in pin["files"].items() if sizes[n] != want]
    if bad or revision != pin["revision"]:
        row.update(state="broken",
                   why="The model's folder is incomplete (%s). Get it again."
                       % (bad[0] if bad else "meta.json"))
        return row
    row.update(state="ready", ready=True)
    return row


def model_ready(key):
    """Is this model's folder complete and the one this Parseh pins?  A name
    that is not a model is not ready (and never a path)."""
    if not isinstance(key, str) or key not in ALLOWED_MODELS:
        return False
    return model_info(key)["ready"]


def installed():
    """The models that are ready to be used: the program is, and so are they."""
    if not runtime_ready():
        return []
    return [k for k in MODELS if model_ready(k)]


# -------------------------------------------------------------- the children
# THE REGISTRY OF EVERYTHING THIS MODULE, AND LANE C'S WORKER, START: a pip
# that is installing, a transcription that is running, the hardware probe.
# The updater's helper waits only for the server's own process, so what a
# server leaves behind when it stops is the next update's trouble -- stop_all()
# is what serve.py calls as it goes (with the drawings), and sweep() is what
# it does on the way in after a stop nothing could hook (kill -9, a crash, a
# closed console).
_LOCK = threading.RLock()
_CHILDREN = set()
_USES = {}


def popen_kwargs():
    """How a child is started, so that it can be stopped as a group and dies
    with the server where the system allows it: its own session (its own
    process group on Windows, with no console window), and on Linux a death
    signal for when the server is killed outright."""
    kw = {}
    if os.name == "nt":
        kw["creationflags"] = (getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                               | getattr(subprocess, "CREATE_NO_WINDOW", 0))
    else:
        kw["start_new_session"] = True
        if sys.platform.startswith("linux"):
            kw["preexec_fn"] = _die_with_the_server
    return kw


def _die_with_the_server():
    # PR_SET_PDEATHSIG (1) with SIGKILL, as lib/latexdraw.py does it
    try:
        import ctypes
        ctypes.CDLL("libc.so.6", use_errno=True).prctl(1, signal.SIGKILL)
    except Exception:                                        # noqa: BLE001
        pass


def track(proc):
    with _LOCK:
        _CHILDREN.add(proc)
    return proc


def untrack(proc):
    with _LOCK:
        _CHILDREN.discard(proc)


def _terminate(proc, hard=False):
    """Ask a child and all of its own children to stop."""
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                           capture_output=True, timeout=15)
        else:
            os.killpg(proc.pid, signal.SIGKILL if hard else signal.SIGTERM)
    except (OSError, subprocess.SubprocessError):
        pass


def stop_all(wait=2.0):
    """Every child ended: the server is stopping.  Asked to stop first, and
    killed if it has not gone in `wait` seconds."""
    with _LOCK:
        procs = list(_CHILDREN)
    for p in procs:
        _terminate(p)
    end = time.time() + wait
    for p in procs:
        while p.poll() is None and time.time() < end:
            time.sleep(0.05)
        if p.poll() is None:
            _terminate(p, hard=True)


@contextlib.contextmanager
def using(key):
    """`with getstt.using("large-v3-turbo"):` around anything that holds a part
    -- a transcription, an install -- so that removing it is refused meanwhile.
    The program is held by every use of any part."""
    with _LOCK:
        _USES[key] = _USES.get(key, 0) + 1
    try:
        yield
    finally:
        with _LOCK:
            _USES[key] -= 1
            if _USES[key] <= 0:
                del _USES[key]


def in_use(key=None):
    """Is `key` held?  With no key, is anything?  The program is held by any use."""
    with _LOCK:
        if key is None or key == "runtime":
            return bool(_USES)
        return _USES.get(key, 0) > 0


def sweep():
    """What a stopped server left half-done, cleared: the temporary audio, a
    program's staging folder, a pip's scratch folder, a folder being taken
    away.  A model's `.part` folder is NOT half-done -- it is the download the
    next press resumes.  Never makes stt/ where there is none, and never
    called at import (a test that imports serve must not sweep a real one)."""
    if not os.path.isdir(STT_DIR):
        return
    def clear(folder, only=lambda n: True):
        try:
            names = os.listdir(folder)
        except OSError:
            return
        for n in names:
            if only(n):
                _rmtree(os.path.join(folder, n))
    clear(tmp_dir())
    clear(STT_DIR, only=lambda n: n.startswith(("runtime.part-", ".trash")))
    clear(_runtimes_dir(), only=lambda n: n.startswith((".trash", ".old")))
    clear(_models_dir(), only=lambda n: n.startswith((".trash", ".old")))


def _rmtree(path):
    """Remove a file or a folder, and never stop at a stubborn file (Windows
    holds one that a process still has open): a folder that will not go
    is left for the next sweep."""
    try:
        if os.path.isdir(path) and not os.path.islink(path):
            shutil.rmtree(path, ignore_errors=True)
        else:
            os.unlink(path)
    except OSError:
        pass


def _take_away(path):
    """A folder gone at once from where it was known: renamed beside itself
    first, so that a status never sees it half-deleted, then deleted."""
    if not os.path.exists(path):
        return 0
    freed = _tree_size(path) if os.path.isdir(path) else os.path.getsize(path)
    trash = os.path.join(os.path.dirname(path), ".trash-%d-%s" % (os.getpid(), os.path.basename(path)))
    try:
        os.replace(path, trash)
    except OSError:
        trash = path
    _rmtree(trash)
    _SIZES.pop(path, None)
    return freed


# ---------------------------------------------------------------- the processor
def physical_cores():
    """Physical cores where the system says (Linux's cpuinfo, macOS's sysctl),
    else None.  Never guessed from the logical count here."""
    try:
        if sys.platform.startswith("linux"):
            pairs, cur = set(), {}
            with io.open("/proc/cpuinfo", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if not line.strip():
                        if "core id" in cur:
                            pairs.add((cur.get("physical id"), cur["core id"]))
                        cur = {}
                        continue
                    k, _, v = line.partition(":")
                    cur[k.strip()] = v.strip()
            if "core id" in cur:
                pairs.add((cur.get("physical id"), cur["core id"]))
            return len(pairs) or None
        if sys.platform == "darwin":
            out = subprocess.run(["sysctl", "-n", "hw.physicalcpu"], capture_output=True,
                                 text=True, timeout=5).stdout.strip()
            return int(out) if out.isdigit() else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    return None


def _logical_cores():
    try:
        return len(os.sched_getaffinity(0))
    except (AttributeError, OSError):
        return os.cpu_count() or 1


def cpu_threads():
    """How many threads a transcription on the CPU uses: the physical cores,
    at most eight.  Measured with the turbo model on 24 threads' worth of
    CPU: 4 threads took 25.5 s, 8 took 23.9, 16 took 25.6 and all 24 took
    34.3 -- more is not faster, and CTranslate2 itself advises no more
    than the physical cores.  Where they cannot be read, half the logical
    ones (two threads to a core is the usual case)."""
    logical = _logical_cores()
    phys = physical_cores() or max(1, logical // 2)
    return max(1, min(8, phys, logical))


def _cpu():
    logical = _logical_cores()
    phys = physical_cores()
    cores = phys or logical
    return {"available": True, "cores": cores, "logical": logical, "threads": cpu_threads(),
            "compute": COMPUTE["cpu"],
            "said": "%d core%s available. Speech to text will work here. Long videos may take "
                    "some time." % (cores, "" if cores == 1 else "s")}


_HW = {"at": None, "data": None}
_HW_LOCK = threading.Lock()        # the cache: held for an instant, never across a look
_HW_RUN = threading.Lock()         # one look at a time (a look is a child process)
HARDWARE_TTL = 300          # seconds a look at the card is believed before a job asks again


def gpu_needs_text():
    """The requirements of GPU_NEEDS, as the list a page shows, made from the
    table and from nothing else: [(what, where to get it or None)]."""
    out = []
    if GPU_NEEDS.get("driver"):
        out.append(("an NVIDIA graphics driver that runs CUDA %s programs" % (GPU_NEEDS.get("cublas") or ""),
                    GPU_LINKS["driver"]))
    if GPU_NEEDS.get("cublas"):
        libs = " on Linux, ".join([CUDA_LIBS["linux"]]) + " on Linux, " + CUDA_LIBS["win32"] + " on Windows"
        out.append(("cuBLAS for CUDA %s (%s)" % (GPU_NEEDS["cublas"], libs), GPU_LINKS["cublas"]))
    if GPU_NEEDS.get("cudnn"):
        out.append(("cuDNN %s for CUDA %s" % (GPU_NEEDS["cudnn"], GPU_NEEDS.get("cublas") or ""), GPU_LINKS["cublas"]))
    return out


def gpu_note():
    """One sentence that says what is NOT needed where the table says so."""
    if not GPU_NEEDS.get("cudnn"):
        return "cuDNN is not needed with this version of the speech program."
    return ""


def _run_probe(timeout=30):
    """lib/sttprobe.py, run as a child with the Parseh python and, when the
    program is installed, PYTHONPATH on it.  The child NEVER loads a model
    (0.2 s).  -> the JSON it printed, or {"error": sentence}."""
    env = dict(os.environ, PYTHONNOUSERSITE="1", PYTHONDONTWRITEBYTECODE="1", PYTHONSAFEPATH="1",
               PYTHONIOENCODING="utf-8")
    where = runtime_dir()
    if where:
        env["PYTHONPATH"] = where
    else:
        env.pop("PYTHONPATH", None)
    try:
        proc = subprocess.Popen([sys.executable, "-B", PROBE] + ([] if SCAN_FOR_CUBLAS else ["--no-scan"]),
                                stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
                                text=True, encoding="utf-8", errors="replace", **popen_kwargs())
    except OSError as e:
        return {"error": "could not look at the graphics card (%s)" % e}
    track(proc)
    try:
        out, _err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _terminate(proc, hard=True)
        proc.communicate()
        return {"error": "looking at the graphics card took more than %d seconds" % timeout}
    finally:
        untrack(proc)
    for line in reversed((out or "").splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except ValueError:
                break
    return {"error": "looking at the graphics card gave no answer (the program stopped with "
                     "code %s)" % proc.returncode}


def _cuda_from(probe):
    """What a probe's answer means, as the four things a page says: state
    none | found-not-ready | ready, whether a card was seen, the name, and the
    pieces still missing -- each one a sentence."""
    smi = probe.get("smi") or None
    cublas = probe.get("cublas") or {}
    devices = probe.get("cuda_devices") or 0
    name = (smi or {}).get("name") or None
    memory = (smi or {}).get("memory") or None
    out = {"state": "none", "supported_build": True, "detected": False, "ready": False,
           "name": name, "memory": memory, "driver": (smi or {}).get("driver"),
           "missing": [], "why": "", "compute": None, "cublas_dir": None,
           "requirements": dict(GPU_NEEDS)}
    if probe.get("error") and not smi and not probe.get("ct2"):
        out["why"] = probe["error"]
        return out
    if not smi and not devices:
        out["why"] = "No NVIDIA graphics card was found on this computer."
        return out
    out["detected"] = True
    missing = []
    if not probe.get("ct2"):
        missing.append("the speech program itself, which is what checks the card: get it above "
                       "and then check again")
    else:
        if not devices:
            missing.append("the NVIDIA driver's CUDA support: the driver lists a card, but the "
                           "speech program finds no CUDA device")
        types = list(probe.get("cuda_types") or [])
        if devices and not [t for t in COMPUTE["cuda"] if t in types]:
            missing.append("a graphics card that can do half-precision maths (compute "
                           "capability 7.0 or newer): this one supports %s"
                           % (", ".join(types) or "nothing the program uses"))
        else:
            out["compute"] = next((t for t in COMPUTE["cuda"] if t in types), None)
    if not cublas.get("loads"):
        lib = cublas.get("name") or CUDA_LIBS.get(sys.platform, CUDA_LIBS["linux"])
        missing.append("cuBLAS for CUDA %s (%s was not found)" % (GPU_NEEDS.get("cublas") or "", lib))
    else:
        out["cublas_dir"] = cublas.get("dir")
    if missing:
        out["state"] = "found-not-ready"
        out["missing"] = missing
        out["why"] = "; ".join(missing[:1] if len(missing) == 1 else missing)
    else:
        out["state"] = "ready"
        out["ready"] = True
    return out


def _hardware_record(cuda, seen):
    cpu = _cpu()
    return {"checked": seen is not None, "at": seen, "cpu": cpu, "cuda": cuda,
            "auto": "cuda" if cuda.get("ready") else "cpu"}


def _unchecked_cuda():
    return {"state": "unchecked", "supported_build": platform_key() in GPU_PLATFORMS,
            "detected": False, "ready": False, "name": None, "memory": None, "driver": None,
            "missing": [], "why": "", "compute": None, "cublas_dir": None,
            "requirements": dict(GPU_NEEDS)}


def _no_gpu_build():
    cuda = _unchecked_cuda()
    cuda.update(state="none", supported_build=False,
                why="The speech program for this kind of computer (%s) has no graphics-card "
                    "support, so it runs on the CPU." % (platform_key() or sys.platform))
    return cuda


def cached_hardware():
    """The last look at the processor -- never a new one, so a page that is
    only being drawn (or a status polled every second) spawns nothing.  The
    CPU is read fresh; the card is what the last check found, or "unchecked"."""
    with _HW_LOCK:
        cuda, seen = _HW["data"], _HW["at"]
    if cuda is None:
        cuda = _unchecked_cuda() if platform_key() in GPU_PLATFORMS else _no_gpu_build()
    return _hardware_record(cuda, seen)


def hardware(refresh=False):
    """The processor, and whether a graphics card is PROVEN usable -- a look
    is taken when there is none yet, when `refresh` says so, or when the last
    one is older than HARDWARE_TTL; otherwise the last is returned.  The look
    is a child process and never loads a model."""
    with _HW_RUN:
        with _HW_LOCK:
            cuda, seen = _HW["data"], _HW["at"]
        stale = seen is None or time.time() - seen > HARDWARE_TTL
        if not refresh and not stale and cuda is not None:
            return _hardware_record(cuda, seen)
        if platform_key() not in GPU_PLATFORMS:
            cuda = _no_gpu_build()
        else:
            cuda = _cuda_from(_run_probe())
        at = time.time()
        with _HW_LOCK:
            _HW["data"], _HW["at"] = cuda, at
        return _hardware_record(cuda, at)


def forget_hardware():
    """Throw the last look away (a test's, or an install's that changes it)."""
    with _HW_LOCK:
        _HW["data"] = None
        _HW["at"] = None


def resolve(mode):
    """What a job runs on -> ("cpu" | "cuda", a sentence).  Automatic is the
    card ONLY when it is proven, and silently the CPU otherwise; a person who
    chose the card and has none is told why, and nothing runs."""
    check_mode(mode)
    if mode == "cpu":
        return "cpu", "On the CPU, as you chose."
    hw = hardware()["cuda"]
    if mode == "cuda":
        if not hw["ready"]:
            raise SpeechError("gpu-unavailable", gpu_unready_sentence(hw))
        return "cuda", "On %s, as you chose." % (hw["name"] or "the NVIDIA graphics card")
    if hw["ready"]:
        return "cuda", "Automatic: on %s." % (hw["name"] or "the NVIDIA graphics card")
    return "cpu", "Automatic: on the CPU."


def gpu_unready_sentence(cuda):
    """Why the NVIDIA option is not one, for the person who chose it."""
    if cuda.get("state") == "found-not-ready":
        return ("The graphics card is not ready for speech to text: it needs %s. CPU "
                "transcription still works." % (cuda["why"] or "something it does not have yet"))
    return ("%s CPU transcription works without one." % (cuda.get("why") or
                                                        "There is no NVIDIA graphics card to use.")
            ).strip()


# ---------------------------------------------------------------- languages
def whisper_code(lang):
    """Whisper's name for a Parseh language -- the same string, when it knows
    the language; a SpeechError(code="unsupported-language") when it does not."""
    code = (lang or "").strip().lower() if isinstance(lang, str) else ""
    if code in WHISPER_LANGUAGES:
        return code
    raise SpeechError("unsupported-language",
                      "Whisper does not list this language (%s), so speech to text is not "
                      "offered for it." % (code or "none given"))


def speech_languages():
    """{code: True/False} for every language Parseh has, a person's own included."""
    import languages
    return {code: code in WHISPER_LANGUAGES for code in languages.LANGS}


# ------------------------------------------------------------------ the plan
def _runtime_plan():
    key = platform_key()
    dl = MEASURED["runtime"].get(key)
    kept = MEASURED["runtime kept"].get(key)
    return dl, kept


def _part_bytes(part):
    try:
        return sum(os.path.getsize(os.path.join(part, n))
                   for n in os.listdir(part) if not n.endswith(".part.json"))
    except OSError:
        return 0


def plan(key, *, probe=True):
    """What getting this part will cost, before anything is fetched: lib/download.py's
    plan() shape, for the same argument as build().  Nothing is asked of any server
    (the sizes are measured); `probe` is accepted for the interface and unused.

    A model's plan INCLUDES the program when it is not installed -- getting
    the model gets everything speech to text needs, under one bar.  The
    program cannot be resumed (pip starts a wheel again), so its `have` is
    always 0; a model's is the bytes of a download that was stopped.  The
    room needed at once is the larger of the program's own peak (its wheels
    and what they unpack to) and what stays plus the model still to come."""
    if key not in PARTS:
        raise ValueError("%r is not a part of speech to text" % (key,))
    rt_dl, rt_kept = _runtime_plan()
    need_rt = not runtime_ready()
    if key == "runtime":
        if rt_dl is None:
            return download.plan(None)
        return download.plan(rt_dl, measured=True, kept=rt_kept, have=0, peak=rt_dl + rt_kept)
    model = MEASURED[key]
    have = _part_bytes(_model_part(key))
    if not need_rt:
        return download.plan(model, measured=True, kept=model, have=have,
                             peak=max(model - have, 0))
    if rt_dl is None:
        return download.plan(None)
    dl = rt_dl + model
    peak = max(rt_dl + rt_kept, rt_kept + max(model - have, 0))
    return download.plan(dl, measured=True, kept=model + rt_kept, have=have, peak=peak)


def part_name(key):
    """What a part is called in a sentence."""
    if key == "runtime":
        return "the speech-to-text program"
    return "the %s speech model" % key


# ------------------------------------------------------------ the runtime step
_INSTALL = threading.RLock()        # one program install at a time; a model's Get waits for it

_PIP_DOWNLOADING = re.compile(r"^\s*Downloading\s+(\S+\.whl)")
_PIP_PROGRESS = re.compile(r"^Progress\s+(\d+)\s+of\s+(\d+)")
_PIP_COLLECTING = re.compile(r"^Collecting\s+(\S+)")
_PIP_INSTALLING = re.compile(r"^Installing collected packages")


def pip_command(stage, requirements=None):
    """The command that makes the program's folder: hash-checked, no
    dependency resolution (the list IS the closure), wheels only, into
    `stage`, with pip's own settings and cache out of it."""
    return [sys.executable, "-u", "-m", "pip", "install", "--isolated", "--require-hashes",
            "--no-deps", "--only-binary=:all:", "--target", stage, "-r",
            requirements or REQUIREMENTS, "--progress-bar", "raw", "--no-cache-dir",
            "--disable-pip-version-check", "--no-input", "--no-color"]


def _pip_env(scratch):
    """pip's environment: scratch space INSIDE stt/ (the volume the room was
    counted on, swept at every start), Parseh named in the User-Agent, and
    nothing of the person's site packages."""
    env = dict(os.environ, PYTHONNOUSERSITE="1", PYTHONIOENCODING="utf-8",
               PIP_USER_AGENT_USER_DATA=UA, PIP_DISABLE_PIP_VERSION_CHECK="1", PIP_NO_INPUT="1")
    for k in ("TMPDIR", "TEMP", "TMP"):
        env[k] = scratch
    env.pop("PYTHONPATH", None)
    return env


def _pip_words(lines):
    """Why pip stopped, in a sentence a person can act on, from the lines it
    printed."""
    text = "\n".join(lines)
    if "DO NOT MATCH THE HASHES" in text:
        return ("A downloaded file is not the one Parseh expects, so nothing was installed. "
                "Try again; if it keeps happening the connection is altering the download.")
    if "No matching distribution" in text or "Could not find a version" in text:
        which = re.search(r"requirement ([A-Za-z0-9_.\-]+==[\w.]+)", text)
        floor = RUNTIME_FLOORS.get(platform_key() or "")
        if floor:
            return ("This Mac's system is too old for the speech program (macOS %d or newer is "
                    "needed on this kind of Mac): %s has no build for it." % (floor, which.group(1)
                                                                            if which else "a package"))
        return ("There is no build of %s for this kind of computer, so the speech program "
                "cannot be installed here." % (which.group(1) if which else "a package it needs"))
    if re.search(r"(Connection|Temporary failure|Network is unreachable|Name or service|"
                 r"timed out|Max retries|SSLError|ProxyError|Could not fetch URL)", text):
        return ("Parseh could not reach the package server (pypi.org). Check the connection "
                "and press it again; nothing was installed.")
    if "No module named pip" in text:
        return "This Python has no pip, which is what installs the speech program."
    if re.search(r"(No space left|OSError: \[Errno 28\])", text):
        return "The disk filled up while the speech program was being installed. Make room and try again."
    if re.search(r"(Errno 13|PermissionError|Access is denied)", text):
        return "Parseh may not write in its own stt/ folder, so the speech program could not be installed."
    errors = [l for l in lines if l.startswith("ERROR")]
    if errors:
        return "pip stopped: %s" % errors[-1][:300]
    return "pip stopped without saying why (its last line: %s)" % ((lines[-1][:200]) if lines else "none")


def _install_runtime(say, progress, cancel, base=0, whole=None):
    """Make stt/runtime/<generation>-<python>/, ONE PIP, its bytes counted on
    the bar `base` bytes in (a model's Get counts the program first).

    Staged: pip installs into `runtime.part-<pid>` and the folder is renamed
    into place only when it is whole and holds what the pin names, so no
    half-installed program is ever taken for one; another generation's folder
    is deleted only after that.  Stop ends pip and everything it started,
    and removes the stage; pip cannot resume a wheel, so a stopped install
    starts its wheels again.  `whole` is the bar's total."""
    dl, _kept = _runtime_plan()
    whole = whole or dl
    stage = _stage_folder()
    scratch = os.path.join(tmp_dir(), "pip-%d" % os.getpid())
    final = runtime_folder()
    lines = []
    proc = None
    ended = threading.Event()
    try:
        for d in (stage, scratch):
            _rmtree(d)
        os.makedirs(scratch, exist_ok=True)
        os.makedirs(_runtimes_dir(), exist_ok=True)
        say("  the speech program, every file checked against the list Parseh ships")
        download.check(cancel)
        try:
            proc = subprocess.Popen(pip_command(stage), stdin=subprocess.DEVNULL,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    env=_pip_env(scratch), text=True, encoding="utf-8",
                                    errors="replace", **popen_kwargs())
        except OSError as e:
            raise SystemExit("getstt: could not start pip (%s)" % e)
        track(proc)

        def watcher():
            # STOP MUST END PIP AT ONCE, not when it next prints a line: the
            # runner only sets an Event, and knows nothing of children
            while not ended.is_set():
                if download.stopped(cancel):
                    _terminate(proc)
                    return
                ended.wait(0.2)
        threading.Thread(target=watcher, daemon=True).start()
        if progress:
            progress(base, whole, "download")
        finished, current = 0, 0
        for raw in proc.stdout:
            line = raw.rstrip("\r\n")
            m = _PIP_PROGRESS.match(line)
            if m:
                current = int(m.group(1))
                if progress:
                    progress(min(base + finished + current, base + (dl or whole)), whole, "download")
                continue
            lines.append(line)
            del lines[:-60]
            m = _PIP_COLLECTING.match(line)
            if m:
                finished += current
                current = 0
                say("    %s" % m.group(1))
            elif _PIP_INSTALLING.match(line):
                finished += current
                current = 0
                if progress:
                    progress(base + (dl or 0), whole, "build")
                say("  putting the program in place")
        proc.wait()
        if download.stopped(cancel):
            raise download.Cancelled()
        if proc.returncode != 0:
            raise SystemExit("getstt: %s" % _pip_words(lines))
        got = _dists(stage)
        missing = [d for d, v in REQUIRED if d not in got or (v and got[d] != v)]
        if missing:
            raise SystemExit("getstt: the program installed but %s is not there, so it was not "
                             "kept. Try again." % missing[0].replace("_", "-"))
        if os.path.isdir(final):
            _take_away(final)
        os.replace(stage, final)
        # the other generations' and Pythons' folders go only now
        for _g, _t, name in _runtime_folders():
            if os.path.join(_runtimes_dir(), name) != final:
                _take_away(os.path.join(_runtimes_dir(), name))
    finally:
        ended.set()
        if proc is not None:
            if proc.poll() is None:
                _terminate(proc, hard=True)
                proc.wait()
            proc.stdout.close()
            untrack(proc)
        _rmtree(stage)
        _rmtree(scratch)
    _SIZES.pop(final, None)
    if progress and whole:
        progress(base + (dl or 0), whole, "download")
    say("  the speech program is installed (%s)" % _mb(_tree_size(final)))
    # the card is looked at again with the program that can vouch for it
    try:
        hardware(refresh=True)
    except Exception:                                          # noqa: BLE001
        forget_hardware()


# --------------------------------------------------------------- the model step
def _fetch_all(files, say, progress, cancel, base=0, whole=None):
    """The files of a model as ONE bar: [(url, dest, sha256, size)].  A file
    already here, whole and matching its digest, is not fetched again --
    which is how a model stopped after its second file carries on at its
    third."""
    whole = whole or sum(f[3] for f in files)
    before = 0
    for url, dest, sha, size in files:
        say("    %s" % os.path.basename(dest))
        if os.path.isfile(dest) and download.digest(dest) == sha.lower():
            say("    already here: %s" % os.path.basename(dest))
        else:
            try:
                download.fetch(url, dest, say=say, progress=download.shifted(progress, base + before, whole),
                               cancel=cancel, sha256=sha, size=size, headers={"User-Agent": UA},
                               timeout=180)
            except download.Mismatch as e:
                raise SystemExit("getstt: %s" % e)
            except urllib.error.HTTPError as e:
                raise SystemExit("getstt: could not download %s (%s)" % (url, e))
            except OSError as e:
                raise SystemExit("getstt: could not download (%s). What came is kept: the next "
                                 "try carries on from there." % e)
        before += size


def _tidy(part, names):
    """Everything in a model's .part folder that is not one of its files or
    a download of one goes."""
    keep = set()
    for n in names:
        keep.update((n, n + ".part", n + ".part.json"))
    try:
        for n in os.listdir(part):
            if n not in keep:
                _rmtree(os.path.join(part, n))
    except OSError:
        pass


def _install_model(key, say, progress, cancel, base=0, whole=None):
    pin = MODEL_PINS[key]
    part = _model_part(key)
    final = model_dir(key)
    os.makedirs(_models_dir(), exist_ok=True)
    os.makedirs(part, exist_ok=True)
    _tidy(part, list(pin["files"]))
    say("  %s, from %s at a fixed version" % (MODEL_INFO[key]["label"], pin["repo"]))
    files = [(MODEL_URL % {"repo": pin["repo"], "revision": pin["revision"], "file": name},
              os.path.join(part, name), sha, size) for name, (sha, size) in pin["files"].items()]
    _fetch_all(files, say, progress, cancel, base=base, whole=whole)
    # every one of the five, in place, before it is called installed: with
    # tokenizer.json missing faster-whisper would reach for the network
    for name, (_sha, size) in pin["files"].items():
        p = os.path.join(part, name)
        if not os.path.isfile(p) or os.path.getsize(p) != size:
            raise SystemExit("getstt: %s did not arrive whole. Try again." % name)
    meta = {"model": key, "repo": pin["repo"], "revision": pin["revision"],
            "files": {n: s for n, (_h, s) in pin["files"].items()},
            "source": MODEL_SOURCE, "licence": MODEL_LICENCE, "pin": PIN["generation"],
            "built": time.strftime("%Y-%m-%d")}
    with io.open(os.path.join(part, "meta.json"), "w", encoding="utf-8") as f:
        f.write(json.dumps(meta, indent=1))
    # beside the old one and moved over it, closed first: Windows will not
    # move a folder holding an open file
    if os.path.isdir(final):
        _take_away(final)
    os.replace(part, final)
    say("  %s: %s" % (key, _mb(model_info(key)["size"])))


def build(key, say=print, progress=None, cancel=None):
    """Get one part: the program (`runtime`), or a model -- which gets the
    program first if it is not there, under ONE bar.  `progress(done,
    total, phase)`, `cancel` as lib/download.py has them; a part that cannot
    be got says why in a SystemExit (the runner prints it), Stop is
    download.Cancelled.  Returns the bytes it now takes."""
    if key not in PARTS:
        raise ValueError("%r is not a part of speech to text" % (key,))
    reason = unavailable_reason()
    if reason:
        raise SystemExit("getstt: %s" % reason)
    rt_dl, _kept = _runtime_plan()
    with using(key):
        if key == "runtime":
            with _INSTALL:
                if runtime_ready():
                    say("  the speech program is already installed")
                    return runtime()["size"]
                _install_runtime(say, progress, cancel)
            return runtime()["size"]
        total = MEASURED[key]
        with _INSTALL:
            # another job may have installed it while this one waited
            base = 0
            if not runtime_ready():
                total += rt_dl
                _install_runtime(say, progress, cancel, base=0, whole=total)
                base = rt_dl
        _install_model(key, say, progress, cancel, base=base, whole=total)
        return model_info(key)["size"]


def discard(key):
    """Throw away what a stopped download left (a model's .part folder).
    The installed part, if any, is untouched.  Returns the bytes freed."""
    if key == "runtime":
        freed = _tree_size(_stage_folder()) if os.path.isdir(_stage_folder()) else 0
        _rmtree(_stage_folder())
        return freed
    part = _model_part(check_model(key))
    freed = _part_bytes(part)
    _rmtree(part)
    return freed


def remove(key):
    """Take a part away: the program's folder, or one model's -- and nothing
    else of Parseh.  Refused (SpeechError, "in-use") while an install or a
    transcription holds it."""
    if key not in PARTS:
        raise SpeechError("bad-part", "There is no such part of speech to text.")
    if in_use(key):
        raise SpeechError("in-use", "It is being used right now: an install or a transcription "
                                    "is running. Stop that first.")
    if key == "runtime":
        freed = _take_away(_runtimes_dir())
        _rmtree(_stage_folder())
        forget_hardware()
    else:
        freed = _take_away(model_dir(key))
        _rmtree(_model_part(key))
    return freed


# ------------------------------------------------------------- what is said
def worker_env():
    """The environment additions for a child that runs the program: the
    program's folder on its path and nothing else of Python's (no user
    site, no bytecode written, the script's folder not put first), the
    network switched off for the model hub, and -- where the last look
    found cuBLAS off the loader's path -- its folder, so the child finds the
    same library the probe did.  Merge into os.environ; a SpeechError while
    there is no program."""
    where = runtime_dir()
    if not where:
        raise SpeechError("not-installed", "Speech to text is not installed yet: get it from "
                                           "Settings, then Speech to text.")
    env = {"PYTHONPATH": where, "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1",
           "PYTHONSAFEPATH": "1", "PYTHONIOENCODING": "utf-8", "HF_HUB_OFFLINE": "1",
           "TRANSFORMERS_OFFLINE": "1", "HF_HOME": os.path.join(tmp_dir(), "hf"),
           "HF_HUB_DISABLE_TELEMETRY": "1", "TOKENIZERS_PARALLELISM": "false"}
    with _HW_LOCK:
        found = (_HW["data"] or {}).get("cublas_dir")
    if found:
        var = "PATH" if os.name == "nt" else "LD_LIBRARY_PATH"
        env[var] = os.pathsep.join([found] + [p for p in os.environ.get(var, "").split(os.pathsep) if p])
    return env


def _what_now(cuda):
    if cuda["ready"]:
        return "cuda"
    return "cpu"


def processing(hw=None):
    """The three ways to choose the processor, as the add page draws them."""
    hw = hw or cached_hardware()
    cuda = hw["cuda"]
    cpu = hw["cpu"]
    now = "cuda" if cuda["ready"] else "cpu"
    auto_say = ("Automatic — recommended. It uses %s when it can prove the card is usable, and "
                "the CPU otherwise. Right now: %s." % (
                    cuda["name"] or "an NVIDIA graphics card",
                    (cuda["name"] or "the NVIDIA graphics card") if now == "cuda" else "the CPU"))
    return [{"id": "auto", "ready": True, "now": now, "say": auto_say},
            {"id": "cpu", "ready": True,
             "say": "CPU. Always works, on every computer (%d cores here, int8)." % cpu["cores"]},
            {"id": "cuda", "ready": bool(cuda["ready"]), "name": cuda["name"],
             "memory": cuda["memory"],
             "why": "" if cuda["ready"] else gpu_unready_sentence(cuda)}]


def _models_status():
    rt = runtime()
    out = {}
    for key in MODELS:
        m = model_info(key)
        info = MODEL_INFO[key]
        out[key] = dict(m, id=key, label=info["label"], tag=info["tag"], hint=info["hint"],
                        memory=info["memory"], repo=MODEL_PINS[key]["repo"],
                        pinned=MODEL_PINS[key]["revision"], download=MEASURED[key],
                        ready=bool(m["ready"] and rt["ready"]), files_ready=m["ready"])
    return out


def status():
    """The whole `speech` object of /lookup/api/status and of Settings -> Speech
    to text: the pin, the program, each model, the processor, the languages.
    Cheap and offline -- it reads folder names and sizes, never runs a child
    and never imports the program."""
    hw = cached_hardware()
    rt = runtime()
    needs = gpu_needs_text()
    return {
        "dir": "stt/",
        "pin": {"generation": PIN["generation"], "python": PIN["python"],
                "faster_whisper": PIN["faster-whisper"], "ctranslate2": PIN["ctranslate2"],
                "gpu": dict(GPU_NEEDS), "help": GUIDE + "#how-to-enable-gpu-acceleration"},
        "runtime": dict(rt, download=_runtime_plan()[0]),
        "models": _models_status(),
        "hardware": hw,
        "requirements": [{"what": w, "link": l} for w, l in needs],
        "requirements_note": gpu_note(),
        "languages": speech_languages(),
        "modes": list(MODES),
        "default_model": DEFAULT_MODEL,
        "platform": platform_key(),
        "busy": in_use(),
    }


def summary(where=None):
    """The slim slice the add page reads (POST /lookup/api/speech): is
    speech to text usable, which models, how it may be run, in which
    languages.  `where` is the device class of the caller; nothing here is
    locked (the owner, 2026-09-28: any device let in may use speech to text), so
    it is not used -- it is the interface's argument, and stays."""
    rt = runtime()
    models = _models_status()
    hw = hardware()
    ready = [k for k in MODELS if models[k]["ready"]]
    return {"ok": True,
            "installed": bool(rt["ready"] and ready),
            "runtime": {"state": rt["state"], "version": rt["version"], "why": rt["why"]},
            "models": [{"id": k, "label": models[k]["label"], "tag": models[k]["tag"],
                        "hint": models[k]["hint"], "have": models[k]["have"],
                        "ready": models[k]["ready"], "size": models[k]["size"],
                        "download": models[k]["download"]} for k in MODELS],
            "default_model": next((k for k in MODELS if models[k]["ready"]), None),
            "processing": processing(hw),
            "languages": speech_languages(),
            "busy": in_use(),
            "settings": SETTINGS_PAGE}


# ------------------------------------------------------------- the command line
def _print_status(say=print):
    st = status()
    say("Speech to text, in %s/" % os.path.relpath(STT_DIR, ROOT))
    say("")
    rt = st["runtime"]
    say("  program: %s%s" % (rt["state"], (" - " + rt["why"]) if rt["why"] else
                             (" (faster-whisper %s, ctranslate2 %s)" % (rt["version"], rt["ctranslate2"])
                              if rt["ready"] else "")))
    for key in MODELS:
        m = st["models"][key]
        say("  %-15s %s%s" % (key, m["state"], (" - %s" % _mb(m["size"])) if m["have"] else ""))
    hw = st["hardware"]
    say("  processor: %s" % hw["cpu"]["said"])
    say("  graphics card: %s%s" % (hw["cuda"]["state"], (" - " + hw["cuda"]["why"]) if hw["cuda"]["why"] else ""))


def main():
    p = argparse.ArgumentParser(prog="getstt", description=__doc__.splitlines()[0])
    p.add_argument("action", nargs="?", choices=("get", "check", "remove"), help="what to do")
    p.add_argument("part", nargs="?", help="runtime, large-v3-turbo or large-v3")
    a = p.parse_args()
    if a.action == "check":
        hardware(refresh=True)
        _print_status()
        return 0
    if a.action in ("get", "remove"):
        if a.part not in PARTS:
            raise SystemExit("getstt: name one of %s" % ", ".join(PARTS))
        if a.action == "remove":
            print("freed %s" % _mb(remove(a.part)))
            return 0
        last = [0.0]

        def progress(done, total, phase):
            if time.time() - last[0] > 2 and total:
                last[0] = time.time()
                print("  %s %s of %s" % (phase, _mb(done), _mb(total)), flush=True)
        try:
            build(a.part, say=lambda m: print(m, flush=True), progress=progress)
        except download.Cancelled:
            raise SystemExit("stopped")
        return 0
    _print_status()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
