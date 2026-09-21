#!/usr/bin/env python3
"""The HTML guide, served and compiled from its own front page.

    guidebuild.file_for("site/showcase.html")  the file behind /guide/<path>, or None
    guidebuild.status()                        {"parseh", "built", "stale", "state", "log", "ok", ...}
    guidebuild.start()                         compile it, as a job the page polls
    guidebuild.job()                           the compile alone, cheap: for serve.py's activity list

WHAT IS SERVED.  /guide/ is html-guide/index.html, the guide's front page,
written by hand; /guide/<path> is a file of html-guide/ -- but only of the
three things a reader needs, index.html, assets/ and the compiled site/.
The engine, the Markdown sources and anything whose name starts with a dot
are not on the web.

WHY A JOB, AND WHY A CHILD PROCESS.  The front page offers "Compile the
guide" when the compiled pages are missing or older than their sources (the
GUI-first rule: no command to copy).  The compile runs html-guide/build.py
as a child process, never inside the server: the guide's engine lends the
studio's renderer its own inline Markdown for the length of a compile by
replacing htmlgen.inline (html-guide/engine/studio.py), which inside the
server would reach the studio's own pages rendered at the same moment.  It
takes a second or two; the page polls status() and reloads when it is done.
Every other page hears of it from serve.py's activity list (/__activity),
which reads job() -- the hub above all, where a person goes to do the next
thing.

WHETHER IT IS UP TO DATE.  A compile writes site/build.json with a hash of
everything it read (html-guide/engine/fingerprint.py); status() computes the
hash again and compares.  That module is loaded here by its path, alone: it
imports nothing of the studio.
"""
import importlib.util
import json
import os
import subprocess
import sys
import threading
import time

LIB = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.realpath(os.path.join(LIB, ".."))
GUIDE = os.path.join(ROOT, "html-guide")
KEEP = 200                       # lines of a compile's output a job keeps
SERVED = ("assets", "site")      # besides index.html, what /guide/ may answer
LOCK = threading.Lock()
JOB = {}


def file_for(rel, guide=None):
    """The path under /guide/ (already unquoted, no leading slash) -> the file
    to send, or None.  A directory answers with its index.html, as a static
    host does."""
    guide = os.path.realpath(guide or GUIDE)
    parts = [p for p in rel.split("/") if p]
    if not parts:
        parts = ["index.html"]
    if any(p.startswith(".") or p == "__pycache__" or "\\" in p or "\0" in p for p in parts):
        return None
    if parts == ["index.html"]:
        full = os.path.join(guide, "index.html")
        return full if os.path.isfile(full) else None
    if parts[0] not in SERVED:
        return None
    top = os.path.realpath(os.path.join(guide, parts[0]))
    full = os.path.realpath(os.path.join(guide, *parts))
    if full != top and not full.startswith(top + os.sep):
        return None
    if os.path.isdir(full):
        full = os.path.join(full, "index.html")
    return full if os.path.isfile(full) else None


def _fingerprint(guide):
    """The hash of what a compile of `guide` would read, by the engine's own
    rule -- or None when there is no engine to ask."""
    path = os.path.join(guide, "engine", "fingerprint.py")
    manifest = os.path.join(guide, "engine", "manifest.py")
    if not (os.path.isfile(path) and os.path.isfile(manifest)):
        return None
    # a package of two modules, loaded under a name of its own: nothing else
    # of the engine (and nothing of the studio) comes with it
    pkg = "parseh_guide_fingerprint"
    if pkg not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            pkg, os.path.join(guide, "engine", "__init__.py"),
            submodule_search_locations=[os.path.join(guide, "engine")])
        mod = importlib.util.module_from_spec(spec)
        sys.modules[pkg] = mod          # the package itself: its __init__ is never run
    fp = importlib.import_module(pkg + ".fingerprint")
    return fp.fingerprint(guide)


def built(guide=None):
    """(is there a compiled site, the build.json it wrote or {})."""
    guide = guide or GUIDE
    site = os.path.join(guide, "site")
    info = {}
    try:
        with open(os.path.join(site, "build.json"), encoding="utf-8") as f:
            info = json.load(f)
    except (OSError, ValueError):
        pass
    return os.path.isfile(os.path.join(site, "nav.js")), info


def job():
    """The compile, running or last run, as a copy: {} before the first.
    No hashing of the sources, which status() does: /__activity asks this
    every second and a half from every page open."""
    with LOCK:
        return dict(JOB, log=list(JOB.get("log", [])))


def status(guide=None):
    guide = guide or GUIDE
    have, info = built(guide)
    try:
        now = _fingerprint(guide)
    except Exception:                        # an engine too broken to hash
        now = None
    stale = None if not have or now is None else info.get("fingerprint") != now
    run = job()
    return {"parseh": True, "built": have, "stale": stale,
            "errors": info.get("errors"), "warnings": info.get("warnings"),
            "pages": info.get("pages"),
            "state": run.get("state", "idle"), "log": run.get("log", []),
            "ok": run.get("ok"), "code": run.get("code"),
            "started": run.get("started"), "finished": run.get("finished")}


def command(guide=None):
    """html-guide/build.py, with the Python this server runs: the engine
    needs nothing but the standard library."""
    return [sys.executable, os.path.join(guide or GUIDE, "build.py")]


def _run(cmd, runner):
    def say(line):
        line = line.rstrip()
        if line.strip():
            with LOCK:
                JOB["log"].append(line)
                del JOB["log"][:-KEEP]
    try:
        if runner is not None:
            code = runner(cmd, say)
        else:
            p = subprocess.Popen(cmd, cwd=ROOT, stdin=subprocess.DEVNULL,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 text=True, encoding="utf-8", errors="replace", bufsize=1,
                                 env=dict(os.environ, PYTHONUNBUFFERED="1"))
            for line in p.stdout:
                say(line)
            code = p.wait()
    except Exception as e:                   # no Python to run, no build.py
        say("the compile could not run: %s" % e)
        code = 127
    with LOCK:
        JOB.update(state="done" if code == 0 else "failed", ok=code == 0, code=code,
                   finished=time.time())


def start(guide=None, runner=None):
    """Compile the guide -> (the job, True), or (the compile already running,
    False).  `runner(cmd, say) -> exit status` stands in for the child
    process, for a test."""
    with LOCK:
        if JOB.get("state") == "running":
            return dict(JOB, log=list(JOB["log"])), False
        JOB.clear()
        JOB.update(state="running", log=[], ok=None, code=None,
                   started=time.time(), finished=None)
        view = dict(JOB, log=[])
    threading.Thread(target=_run, args=(command(guide), runner), daemon=True).start()
    return view, True
