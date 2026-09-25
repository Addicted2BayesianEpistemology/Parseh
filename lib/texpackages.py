# SPDX-License-Identifier: GPL-3.0-or-later
"""TeX packages got for the LaTeX drawings, from Settings (TO-DO §8.39, a0.4.0).

WHERE THEY GO (the owner, 2026-09-25).  Into a folder of Parseh's own,
texmf/, through tlmgr's user mode -- which works on a TeX Live installed by
its own installer and on one a Linux distribution packaged alike, where a
plain `tlmgr install` refuses ("running on Debian, switching to user mode!"),
and needs no administrator -- from the repository of the installed TeX
Live's own year (a TeX Live of an earlier year is served by the historic
archive: a repository newer than the installation is refused by tlmgr).
Every drawing is pointed at the folder (TEXMFAUXTREES, lib/latexdraw.py).
On Windows with MiKTeX, MiKTeX's own package manager, which puts a package
in MiKTeX's own tree.  Removing only ever touches what Parseh itself put
there -- never a package of the system's TeX, and so never what Parseh's
own PDFs need (install.sh --pdf's list).

texmf/ IS CONTENT, like dict/: an update keeps it, a release ships it empty,
a backup copies it (lib/release.py CONTENT, lib/updater.py PERSONAL).  What
is in it is listed in texmf/parseh-packages.json, with each package's size
and licence as TeX Live gave them: the rows of Settings -> LaTeX drawings
and /licences/ read that list, and so does a drawing's key (state()), so a
package installed or removed draws afresh.

Getting a package is a job like a dictionary's download (lib/lookuppage.py):
what it costs said before it starts, its progress, Stop.
"""
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time

LIB = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(LIB)
if LIB not in sys.path:
    sys.path.insert(0, LIB)
import latexthemes                                           # noqa: E402

TREE = os.path.join(ROOT, "texmf")
MANIFEST_NAME = "parseh-packages.json"
# the shape of the list, as a number (lib/version.py FORMATS)
MANIFEST_FORMAT = 1
MAIN_REPO = "https://mirror.ctan.org/systems/texlive/tlnet"
HISTORIC_REPO = "https://ftp.math.utah.edu/pub/tex/historic/systems/texlive/%d/tlnet-final"
WIN = os.name == "nt"

_LOCK = threading.Lock()
JOBS = {}           # package name -> the job
_PROCS = {}         # package name -> the running process


def tree():
    return TREE


def manifest_path():
    return os.path.join(TREE, MANIFEST_NAME)


def manifest():
    """{"format", "packages": {name: {"at", "licence", "size", "via"}}}"""
    try:
        with open(manifest_path(), encoding="utf-8") as fh:
            doc = json.load(fh)
        if isinstance(doc, dict) and isinstance(doc.get("packages"), dict):
            return doc
    except (OSError, ValueError):
        pass
    return {"format": MANIFEST_FORMAT, "packages": {}}


def _save_manifest(doc):
    doc = dict(doc, format=MANIFEST_FORMAT)
    os.makedirs(TREE, exist_ok=True)
    tmp = manifest_path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, manifest_path())


def state():
    """A drawing's key's share of the packages: what Parseh has installed,
    and when."""
    pk = manifest()["packages"]
    if not pk:
        return ""
    blob = json.dumps({k: v.get("at") for k, v in sorted(pk.items())})
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------- the TeX
def distribution():
    """Which TeX this computer has -> {"kind": "texlive"|"miktex"|None,
    "year", "tool", "said"}."""
    for c in latexthemes.COMPILERS + ("tex",):
        path = shutil.which(c)
        if not path:
            continue
        try:
            out = subprocess.run([path, "--version"], capture_output=True, text=True,
                                 timeout=20, stdin=subprocess.DEVNULL).stdout
        except (OSError, subprocess.SubprocessError):
            continue
        if "miktex" in out.lower():
            tool = shutil.which("miktex") or shutil.which("mpm")
            return {"kind": "miktex", "year": None, "tool": tool,
                    "said": out.splitlines()[0].strip() if out else "MiKTeX"}
        m = re.search(r"TeX Live (\d{4})", out)
        tlmgr = shutil.which("tlmgr")
        return {"kind": "texlive", "year": int(m.group(1)) if m else None, "tool": tlmgr,
                "said": ("TeX Live %s" % m.group(1)) if m else out.splitlines()[0].strip()}
    return {"kind": None, "year": None, "tool": None, "said": "no TeX on this computer"}


def env():
    e = dict(os.environ)
    if os.path.isdir(TREE):
        e["TEXMFAUXTREES"] = TREE.replace("\\", "/") + ","
    return e


def installed(file):
    """Is a TeX file reachable, in the system's TeX or in texmf/?"""
    k = shutil.which("kpsewhich")
    if not k:
        return None
    try:
        r = subprocess.run([k, file], capture_output=True, text=True, timeout=20, env=env(),
                           stdin=subprocess.DEVNULL)
        return bool(r.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        return None


def licence_of(tl_name):
    """The TeX Catalogue's licence of a TeX Live package, as the checkboxes know it."""
    for row in latexthemes.PACKAGES.values():
        if tl_name in row["tl"]:
            return row["licence"]
    for tl, _f, lic in latexthemes.ALWAYS.values():
        if tl_name in tl:
            return lic
    return ""


def _tlmgr(args, repo=None):
    d = distribution()
    tool = d.get("tool")
    if not tool:
        return None
    cmd = [tool, "--usermode", "--usertree", TREE]
    if repo:
        cmd += ["--repository", repo]
    return cmd + list(args)


def _repositories():
    d = distribution()
    out = [MAIN_REPO]
    if d.get("year"):
        out.append(HISTORIC_REPO % d["year"])
    return out


def plan(names):
    """What getting these TeX Live packages costs, before anything starts ->
    {"packages": [{"name", "size", "licence"}], "can", "why"}."""
    d = distribution()
    rows = [{"name": n, "size": None, "licence": licence_of(n)} for n in names]
    if d["kind"] is None:
        return {"packages": rows, "can": False,
                "why": "This computer has no TeX. Install TeX Live or MiKTeX first: the "
                       "guide's Installing page says how."}
    if d["kind"] == "miktex" and not d.get("tool"):
        return {"packages": rows, "can": False, "why": "MiKTeX's package manager was not found."}
    if d["kind"] == "texlive" and not d.get("tool"):
        return {"packages": rows, "can": False,
                "why": "This TeX Live has no tlmgr, so Parseh cannot add packages to it."}
    if d["kind"] == "texlive":
        for repo in _repositories():
            cmd = _tlmgr(["info", "--json"] + list(names), repo)
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=60,
                                   stdin=subprocess.DEVNULL)
                info = json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else None
            except (OSError, subprocess.SubprocessError, ValueError):
                info = None
            if not info:
                continue
            by = {x.get("name"): x for x in info if isinstance(x, dict)}
            for row in rows:
                x = by.get(row["name"]) or {}
                try:
                    row["size"] = int(x.get("containersize") or 0) or None
                except (TypeError, ValueError):
                    row["size"] = None
                lic = ((x.get("cataloguedata") or {}).get("license")) or row["licence"]
                row["licence"] = lic
            break
    return {"packages": rows, "can": True, "why": "", "tex": d["said"]}


def _progress(job, line):
    m = re.search(r"\[(\d+)/(\d+)", line)
    if m:
        job["done"], job["total"] = int(m.group(1)), int(m.group(2))
    if line.strip():
        job["say"] = line.strip()[:200]


def _run(job, name):
    d = distribution()
    try:
        if d["kind"] == "texlive":
            os.makedirs(TREE, exist_ok=True)
            if not os.path.exists(os.path.join(TREE, "tlpkg", "texlive.tlpdb")):
                init = _tlmgr(["init-usertree"])
                subprocess.run(init, capture_output=True, text=True, timeout=120,
                               stdin=subprocess.DEVNULL)
            ok = False
            for repo in _repositories():
                if job.get("stopped"):
                    break
                cmd = _tlmgr(["install", name], repo)
                ok = _stream(job, name, cmd)
                if ok or job.get("stopped"):
                    break
                job["tried"] = job.get("tried", []) + [repo]
            via = "tlmgr"
        elif d["kind"] == "miktex":
            tool = d["tool"]
            if os.path.basename(tool).lower().startswith("miktex"):
                cmd = [tool, "packages", "install", name]
            else:
                cmd = [tool, "--install=%s" % name]
            ok = _stream(job, name, cmd)
            via = "miktex"
        else:
            ok, via = False, ""
            job["error"] = "This computer has no TeX."
        if job.get("stopped"):
            job["error"] = "Stopped."
        elif ok:
            doc = manifest()
            doc["packages"][name] = {"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "via": via,
                                     "licence": licence_of(name),
                                     "size": _tree_size() if via == "tlmgr" else None}
            _save_manifest(doc)
            import latexdraw
            latexdraw.forget_failures()
        elif not job.get("error"):
            job["error"] = ("%s could not be installed: %s" % (name, job.get("say") or "it failed"))
    except Exception as e:                                   # noqa: BLE001
        job["error"] = "%s could not be installed: %s" % (name, e)
    finally:
        job["running"] = False
        job["finished"] = time.time()


def _stream(job, name, cmd):
    kw = {"stdout": subprocess.PIPE, "stderr": subprocess.STDOUT, "stdin": subprocess.DEVNULL,
          "text": True, "env": env()}
    if WIN:
        kw["creationflags"] = (getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                               | getattr(subprocess, "CREATE_NO_WINDOW", 0))
    else:
        kw["start_new_session"] = True
    proc = subprocess.Popen(cmd, **kw)
    with _LOCK:
        _PROCS[name] = proc
    try:
        for line in proc.stdout:
            _progress(job, line)
        proc.wait()
    finally:
        with _LOCK:
            _PROCS.pop(name, None)
    return proc.returncode == 0


def _tree_size():
    total = 0
    for here, _d, files in os.walk(TREE):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(here, f))
            except OSError:
                pass
    return total


def start(name):
    """Get one TeX package, in the background -> the job."""
    if not re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,60}$", name or ""):
        raise ValueError("%r is not a package's name" % name)
    with _LOCK:
        job = JOBS.get(name)
        if job and job.get("running"):
            return job
        job = JOBS[name] = {"name": name, "running": True, "done": 0, "total": 0,
                            "say": "starting", "error": None, "started": time.time()}
    threading.Thread(target=_run, args=(job, name), daemon=True).start()
    return job


def stop(name=None):
    with _LOCK:
        names = [name] if name else list(_PROCS)
        procs = [(n, _PROCS.get(n)) for n in names]
    for n, p in procs:
        if n in JOBS:
            JOBS[n]["stopped"] = True
        if p is None:
            continue
        try:
            if WIN:
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
            else:
                os.killpg(p.pid, signal.SIGTERM)
        except OSError:
            pass


def remove(name):
    """Remove a package Parseh installed -- and only one it did."""
    doc = manifest()
    got = doc["packages"].get(name)
    if not got:
        raise ValueError("%s was not installed by Parseh, so Parseh does not remove it" % name)
    if got.get("via") == "tlmgr":
        cmd = _tlmgr(["remove", name])
    else:
        d = distribution()
        tool = d.get("tool") or ""
        cmd = ([tool, "packages", "remove", name] if os.path.basename(tool).lower().startswith("miktex")
               else [tool, "--uninstall=%s" % name])
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300, stdin=subprocess.DEVNULL,
                       env=env())
    if r.returncode != 0:
        raise ValueError("%s could not be removed: %s" % (name, (r.stdout or r.stderr).strip()[-300:]))
    doc["packages"].pop(name, None)
    _save_manifest(doc)
    import latexdraw
    latexdraw.forget_failures()


def status():
    with _LOCK:
        jobs = {k: {x: v.get(x) for x in ("name", "running", "done", "total", "say", "error")}
                for k, v in JOBS.items()}
    return {"jobs": jobs, "installed": manifest()["packages"]}
