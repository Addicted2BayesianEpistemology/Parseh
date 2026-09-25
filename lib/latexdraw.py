# SPDX-License-Identifier: GPL-3.0-or-later
"""Drawing a latex block: compiled on its own, kept, and explained when it
fails (TO-DO §8.39, a0.4.0).

ON ITS OWN (the owner, 2026-09-24, settled).  A block is compiled in a
`standalone` document of its own, under its theme's preamble
(lib/latexthemes.py) and its theme's compiler, and what comes out is a PDF
cropped to the drawing.  The screen shows an SVG made from that very PDF
(PyMuPDF, the glyphs as outlines, as the studio's PDF figures have always
been shown: store.ensure_pdf_twin), and paper includes the PDF itself -- so
the two show the same drawing by construction, and a package added for
chemistry can never move a `:::math` formula, which never comes here.

COMPILED ONCE, KEPT IN markdown/latex/ -- derived, in no release, rebuilt at
will (.gitignore, lib/release.py NEVER).  A drawing is found again by its
KEY, the hash of everything that decides what it looks like:

  * the block's own LaTeX;
  * the resolved theme -- its preamble as it now is and its compiler, never
    its name: renaming a theme redraws nothing, editing it redraws exactly
    the blocks that name it;
  * the TeX installation: the compiler's own version, and the packages
    installed or removed through Parseh (the owner, 2026-09-25), so that a
    TeX upgraded or a package added draws afresh;
  * RENDERER, this module's own number, raised when the way a block is drawn
    changes -- never the version of Parseh, which would redraw everything on
    every release and call every kept page "updated".

A stale picture nobody can explain is the worst thing this feature can do,
worse than a slow compile: if in doubt, it is in the key.

SAFELY.  A theme and a document may come from somebody else, so a compile
runs with no shell escape, may read and write only its own temporary folder
and TeX's own files (openin_any / openout_any = p), is stopped after the
time Settings allows (30 seconds unless changed), runs in a folder wiped
after every compile (Formulae's way), and is killed when the server stops.

A FAILURE IS SAID IN WORDS, beside the block, with the line of the block it
happened on where TeX says one -- and the log's own line under it for
whoever wants it.  A failure is remembered as long as its key stands, so a
package installed since, or a theme changed, draws it again.
"""
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor

LIB = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(LIB)
if LIB not in sys.path:
    sys.path.insert(0, LIB)
import latexthemes                                           # noqa: E402

DRAWN = os.path.join(ROOT, "markdown", "latex")
FONTS = os.path.join(ROOT, "lib", "fonts")
RENDERER = 1
URL = "/latex/"
KEY_RE = re.compile(r"^[0-9a-f]{64}$")
DESIGN_PT = 10.0            # standalone's size: a drawing's natural width is w/10 em
PRUNE_DAYS = 30
WIN = os.name == "nt"

_LOCK = threading.Lock()
_RUNNING = set()            # the TeX processes running now, killed when the server stops
_BUSY = {}                  # key -> Event: one compile of a key at a time
_FAILED = {}                # key -> the failure, while its key stands
_TOOLS = {}                 # compiler -> {"path", "version", "miktex"} or None
_POOL = ThreadPoolExecutor(max_workers=max(1, min(4, (os.cpu_count() or 2) // 2)))


# ------------------------------------------------------------ the compilers
def compiler(name, fresh=False):
    """{"path", "version", "miktex"} of a compiler this computer has, or None."""
    with _LOCK:
        if name in _TOOLS and not fresh:
            return _TOOLS[name]
    path = shutil.which(name)
    info = None
    if path:
        try:
            r = subprocess.run([path, "--version"], capture_output=True, text=True,
                               timeout=20, stdin=subprocess.DEVNULL)
            first = (r.stdout or r.stderr or "").strip().splitlines()
            version = first[0].strip() if first else name
            info = {"path": path, "version": version,
                    "miktex": "miktex" in (r.stdout or "").lower()}
        except (OSError, subprocess.SubprocessError):
            info = None
    with _LOCK:
        _TOOLS[name] = info
    return info


def compilers(fresh=False):
    """Every compiler Parseh offers, and whether this computer has it."""
    return {c: compiler(c, fresh) for c in latexthemes.COMPILERS}


def tex_state(name):
    """What the TeX installation contributes to a key: the compiler's version
    and the packages Parseh installed or removed (lib/texpackages.py)."""
    info = compiler(name)
    try:
        import texpackages
        packages = texpackages.state()
    except Exception:                                        # noqa: BLE001
        packages = ""
    return "%s|%s" % ((info or {}).get("version", ""), packages)


def key_of(tex, resolved, state):
    blob = json.dumps({"renderer": RENDERER, "compiler": resolved["compiler"],
                       "preamble": resolved["preamble"], "tex": tex, "tex-state": state},
                      sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


# ------------------------------------------------------------------ the cache
def _dir(key):
    return os.path.join(DRAWN, key[:2])


def paths(key):
    d = _dir(key)
    return {"svg": os.path.join(d, key + ".svg"), "pdf": os.path.join(d, key + ".pdf"),
            "meta": os.path.join(d, key + ".json"), "fail": os.path.join(d, key + ".fail.json")}


def cached(key):
    """The kept drawing's facts ({"w", "h"} in points), or None."""
    p = paths(key)
    try:
        with open(p["meta"], encoding="utf-8") as fh:
            meta = json.load(fh)
    except (OSError, ValueError):
        return None
    if not (os.path.exists(p["svg"]) and os.path.exists(p["pdf"])):
        return None
    # used: a drawing asked for is not pruned (its meta's time says when)
    try:
        if time.time() - os.path.getmtime(p["meta"]) > 86400:
            os.utime(p["meta"], None)
    except OSError:
        pass
    return meta


def _write_atomic(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = "%s.%d.%d.tmp" % (path, os.getpid(), threading.get_ident())
    with open(tmp, "wb") as fh:
        fh.write(data)
    os.replace(tmp, path)


def url_of(key):
    return URL + key + ".svg"


def file_of(name):
    """/latex/<key>.svg or .pdf -> the file on this disk, or None."""
    m = re.match(r"^([0-9a-f]{64})\.(svg|pdf)$", name or "")
    if not m:
        return None
    p = paths(m.group(1))[m.group(2)]
    return p if os.path.isfile(p) else None


# ------------------------------------------------------------------ drawing
def plan(tex, theme_name, theme=None):
    """What drawing a block would be -> {"key", "resolved", "compiler"} or a
    failure ({"ok": False, ...}) that no compile can mend: no such theme, or
    no such compiler on this computer."""
    if theme is not None:
        resolved = {"name": theme.get("name") or "", "compiler": theme["compiler"],
                    "preamble": latexthemes.preamble(theme), "theme": theme,
                    "languages": theme.get("languages")}
    else:
        resolved = latexthemes.resolve(theme_name)
    if resolved is None:
        name = theme_name or latexthemes.default_name()
        return {"ok": False, "kind": "theme", "theme": name,
                "said": 'This drawing asks for the theme "%s", which this Parseh does not have.'
                        % name,
                "fix": {"kind": "theme-missing", "theme": name}}
    info = compiler(resolved["compiler"])
    if info is None:
        return {"ok": False, "kind": "compiler", "theme": resolved["name"],
                "said": "This drawing is made with %s, which this computer does not have."
                        % resolved["compiler"],
                "fix": {"kind": "theme", "theme": resolved["name"]}}
    state = tex_state(resolved["compiler"])
    return {"ok": True, "key": key_of(tex, resolved, state), "resolved": resolved,
            "compiler": info}


def peek(tex, theme_name):
    """A block's drawing if it is kept, without compiling anything -> the
    result draw() would give, or {"ok": None, "key"} when it is not drawn yet."""
    p = plan(tex, theme_name)
    if not p["ok"]:
        return p
    meta = cached(p["key"])
    if meta:
        return _ok(p["key"], meta)
    with _LOCK:
        if p["key"] in _FAILED:
            return _FAILED[p["key"]]
    fail = _read_fail(p["key"])
    if fail:
        return fail
    return {"ok": None, "key": p["key"]}


def _ok(key, meta):
    return {"ok": True, "key": key, "url": url_of(key), "w": meta.get("w"), "h": meta.get("h"),
            "pdf": paths(key)["pdf"], "svg": paths(key)["svg"]}


def _read_fail(key):
    try:
        with open(paths(key)["fail"], encoding="utf-8") as fh:
            f = json.load(fh)
        return f if isinstance(f, dict) and f.get("ok") is False else None
    except (OSError, ValueError):
        return None


def draw(tex, theme_name, theme=None, limit=None):
    """A block drawn -- from the cache when it is there, compiled when not ->
    {"ok": True, "key", "url", "w", "h", "pdf", "svg"} or {"ok": False, "kind",
    "said", "line"?, "detail"?, "fix"?}."""
    p = plan(tex, theme_name, theme)
    if not p["ok"]:
        return p
    key = p["key"]
    meta = cached(key)
    if meta:
        return _ok(key, meta)
    limit = limit or latexthemes.timeout()
    while True:
        with _LOCK:
            if key in _FAILED and _FAILED[key].get("limit", limit) >= limit:
                return _FAILED[key]
            ev = _BUSY.get(key)
            if ev is None:
                ev = _BUSY[key] = threading.Event()
                mine = True
            else:
                mine = False
        if not mine:
            ev.wait(limit + 30)
            meta = cached(key)
            if meta:
                return _ok(key, meta)
            continue
        try:
            fail = _read_fail(key)
            if fail:
                with _LOCK:
                    _FAILED[key] = fail
                return fail
            out = _compile(tex, p["resolved"], p["compiler"], key, limit)
            if out.get("ok"):
                return out
            with _LOCK:
                _FAILED[key] = dict(out, limit=limit)
            if out.get("kind") != "timeout":
                try:
                    _write_atomic(paths(key)["fail"], json.dumps(out).encode("utf-8"))
                except OSError:
                    pass
            return out
        finally:
            with _LOCK:
                _BUSY.pop(key, None)
            ev.set()


def draw_all(pairs):
    """Many blocks at once, several compiles side by side ->
    [result, ...] in the order of `pairs` ((tex, theme name), ...)."""
    futures = [_POOL.submit(draw, tex, name) for tex, name in pairs]
    return [f.result() for f in futures]


def _preexec():
    # on Linux the drawing dies with the server even when the server is
    # killed outright (PR_SET_PDEATHSIG); elsewhere the server's own stop
    # ends it (stop_all), and the time limit ends it in any case
    try:
        import ctypes
        ctypes.CDLL("libc.so.6", use_errno=True).prctl(1, signal.SIGKILL)
    except Exception:                                        # noqa: BLE001
        pass


def _compile(tex, resolved, info, key, limit):
    work = tempfile.mkdtemp(prefix="parseh-latex-")
    try:
        pre = resolved["preamble"]
        doc = pre + "\\begin{document}\n" + tex + "\n\\end{document}\n"
        first_body = pre.count("\n") + 2           # the line the block's first line is on
        with open(os.path.join(work, "d.tex"), "w", encoding="utf-8") as fh:
            fh.write(doc)
        if resolved.get("languages"):
            os.makedirs(os.path.join(work, "fonts"), exist_ok=True)
            for name in os.listdir(FONTS) if os.path.isdir(FONTS) else ():
                if name.lower().endswith((".ttf", ".otf")):
                    src, dst = os.path.join(FONTS, name), os.path.join(work, "fonts", name)
                    try:
                        os.link(src, dst)
                    except OSError:
                        shutil.copy(src, dst)
        cmd = [info["path"], "-interaction=nonstopmode", "-halt-on-error", "-file-line-error"]
        cmd += (["-disable-write18", "-disable-installer"] if info.get("miktex")
                else ["-no-shell-escape"])
        cmd.append("d.tex")
        env = dict(os.environ, openin_any="p", openout_any="p")
        try:
            import texpackages
            tree = texpackages.tree()
        except Exception:                                    # noqa: BLE001
            tree = None
        if tree and os.path.isdir(tree):
            env["TEXMFAUXTREES"] = tree.replace("\\", "/") + ","
        kw = {"cwd": work, "env": env, "stdin": subprocess.DEVNULL,
              "stdout": subprocess.PIPE, "stderr": subprocess.STDOUT}
        if WIN:
            kw["creationflags"] = (getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                                   | getattr(subprocess, "CREATE_NO_WINDOW", 0))
        else:
            kw["start_new_session"] = True
            if sys.platform.startswith("linux"):
                kw["preexec_fn"] = _preexec
        started = time.time()
        try:
            proc = subprocess.Popen(cmd, **kw)
        except OSError as e:
            return {"ok": False, "kind": "compiler", "said": "%s could not be started: %s"
                    % (resolved["compiler"], e), "fix": {"kind": "theme", "theme": resolved["name"]}}
        with _LOCK:
            _RUNNING.add(proc)
        try:
            out, _ = proc.communicate(timeout=limit)
        except subprocess.TimeoutExpired:
            _kill(proc)
            proc.communicate()
            return {"ok": False, "kind": "timeout",
                    "said": "The drawing did not finish in %d seconds, and was stopped. "
                            "Settings \u2192 LaTeX drawings says how long a drawing may take."
                            % limit}
        finally:
            with _LOCK:
                _RUNNING.discard(proc)
        pdf = os.path.join(work, "d.pdf")
        if proc.returncode != 0 or not os.path.exists(pdf):
            try:
                with open(os.path.join(work, "d.log"), encoding="utf-8", errors="replace") as fh:
                    log = fh.read()
            except OSError:
                log = (out or b"").decode("utf-8", "replace")
            return explain(log, first_body, tex, resolved)
        try:
            import pymupdf
        except ImportError:
            try:
                import fitz as pymupdf                       # an older PyMuPDF
            except ImportError:
                return {"ok": False, "kind": "tool",
                        "said": "Drawings are shown on the screen by PyMuPDF, which the "
                                "environment Parseh installs has; this Parseh is running "
                                "without it."}
        with open(pdf, "rb") as fh:
            pdf_bytes = fh.read()
        with pymupdf.open(stream=pdf_bytes, filetype="pdf") as d:
            if not d.page_count:
                return {"ok": False, "kind": "empty", "said": "The drawing came out empty."}
            page = d[0]
            svg = page.get_svg_image(text_as_path=True)
            w, h = round(page.rect.width, 2), round(page.rect.height, 2)
        meta = {"w": w, "h": h, "compiler": resolved["compiler"],
                "theme": resolved["name"], "drawn": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "took": round(time.time() - started, 2), "renderer": RENDERER}
        p = paths(key)
        _write_atomic(p["pdf"], pdf_bytes)
        _write_atomic(p["svg"], svg.encode("utf-8"))
        _write_atomic(p["meta"], json.dumps(meta).encode("utf-8"))
        return _ok(key, meta)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _kill(proc):
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


def stop_all():
    """Every drawing being made, stopped: the server is stopping."""
    with _LOCK:
        running = list(_RUNNING)
    for proc in running:
        _kill(proc)


# ------------------------------------------------------------- in words
# the commands a theme's checkbox gives, so that a command TeX does not know
# can be said with the box that would make it known
_COMMANDS = {
    "ce": "mhchem", "cee": "mhchem", "cf": "mhchem", "chemfig": "chemfig",
    "SI": "siunitx", "si": "siunitx", "qty": "siunitx", "unit": "siunitx", "num": "siunitx",
    "ang": "siunitx", "mathscr": "mathrsfs", "mathds": "dsfont", "vv": "esvect",
    "llbracket": "stmaryrd", "rrbracket": "stmaryrd", "male": "wasysym", "female": "wasysym",
    "smiley": "wasysym", "Yen": "marvosym", "Mundus": "marvosym", "cancel": "cancel",
    "bcancel": "cancel", "cancelto": "cancel", "slashed": "slashed", "mathlarger": "relsize",
    "mathsmaller": "relsize", "newtheorem": "amsthm", "bm": "bm", "textcolor": "xcolor",
    "color": "xcolor", "colorbox": "xcolor", "coloneqq": "mathtools", "mathbb": "amssymb",
    "mathfrak": "amsfonts", "dv": "physics", "pdv": "physics", "abs": "physics",
    "norm": "physics", "bra": "physics", "ket": "physics", "braket": "physics",
    "draw": "tikz", "node": "tikz", "fill": "tikz", "path": "tikz", "usetikzlibrary": "tikz",
    "addplot": "pgfplots", "lstinline": "listings", "text": "amsmath", "tfrac": "amsmath",
    "dfrac": "amsmath", "binom": "amsmath", "operatorname": "amsmath", "iint": "amsmath",
}
_ENVIRONMENTS = {
    "tikzpicture": "tikz", "axis": "pgfplots", "tikzcd": "tikz-cd", "circuitikz": "circuitikz",
    "lstlisting": "listings", "algorithm": "algorithm2e", "proof": "amsthm",
    "pmatrix": "amsmath", "bmatrix": "amsmath", "vmatrix": "amsmath", "matrix": "amsmath",
    "align": "amsmath", "align*": "amsmath", "aligned": "amsmath", "cases": "amsmath",
    "gather": "amsmath", "multline": "amsmath", "split": "amsmath",
}


def _where(line_no, first_body, tex):
    """TeX's line -> (the line of the block, or None when it is in the theme)."""
    if line_no is None:
        return None
    n = line_no - first_body + 1
    return n if 1 <= n <= tex.count("\n") + 1 else None


def explain(log, first_body, tex, resolved):
    """LaTeX's log -> the failure in ordinary words: what went wrong, on which
    line of the block when TeX says one, and what would mend it."""
    theme = resolved.get("name") or ""
    lines = log.splitlines()
    msg, line_no, ctx = None, None, ""
    for i, l in enumerate(lines):
        m = re.match(r"^(?:\./)?d\.tex:(\d+): (.*)$", l)
        if m:
            line_no, msg = int(m.group(1)), m.group(2)
            ctx = "\n".join(lines[i:i + 4])
            break
        if l.startswith("! "):
            msg = l[2:]
            ctx = "\n".join(lines[i:i + 4])
            for later in lines[i:i + 12]:
                mm = re.match(r"^l\.(\d+) ", later)
                if mm:
                    line_no = int(mm.group(1))
                    break
            break
    at = _where(line_no, first_body, tex)
    where = (" on line %d of the block" % at) if at else (
        " in the theme's preamble" if line_no else "")
    out = {"ok": False, "kind": "latex", "line": at, "detail": ctx.strip()[:1200],
           "theme": theme}
    if msg is None:
        # no error line at all: say what TeX did say, at its end
        tail = [l for l in lines if l.strip()][-6:]
        out.update(said="LaTeX stopped without saying why.", detail="\n".join(tail)[:1200])
        return out
    m = re.search(r"File [`'](.+?)' not found", msg)
    if m:
        pkg = re.sub(r"\.(sty|cls|tex)$", "", m.group(1))
        out.update(kind="package", said="The package %s is not installed on this computer%s."
                   % (pkg, where), fix={"kind": "install", "file": m.group(1), "package": pkg})
        return out
    m = re.search(r'The font "(.+?)" cannot be found', msg)
    if m:
        out.update(said='The font "%s" is not on this computer: choose another for the theme '
                        '"%s" in Settings \u2192 LaTeX drawings.' % (m.group(1), theme),
                   fix={"kind": "theme", "theme": theme})
        return out
    if "Undefined control sequence" in msg:
        cs = None
        for l in ctx.splitlines():
            mm = re.match(r"^l\.\d+ (.*)$", l)
            if mm:
                found = re.findall(r"\\([A-Za-z@]+)", mm.group(1))
                cs = found[-1] if found else None
                break
        pkg = _COMMANDS.get(cs or "")
        if cs and pkg:
            out.update(said="\\%s is not a command the theme \"%s\" knows%s. It comes with "
                            "%s: tick %s in the theme, in Settings \u2192 LaTeX drawings."
                            % (cs, theme, where, pkg, pkg),
                       fix={"kind": "theme", "theme": theme, "package": pkg})
        elif cs:
            out.update(said="\\%s is not a command LaTeX knows here%s: a typing slip, or a "
                            "package the theme \"%s\" does not load." % (cs, where, theme))
        else:
            out.update(said="A command LaTeX does not know%s." % where)
        return out
    m = re.search(r"Environment (\S+) undefined", msg)
    if m:
        env = m.group(1)
        pkg = _ENVIRONMENTS.get(env)
        said = "\\begin{%s} names something the theme \"%s\" does not know%s." % (env, theme, where)
        if pkg:
            said += " It comes with %s: tick %s in the theme, in Settings \u2192 LaTeX drawings." % (pkg, pkg)
            out["fix"] = {"kind": "theme", "theme": theme, "package": pkg}
        out.update(said=said)
        return out
    if "Missing $ inserted" in msg:
        out.update(said="Mathematics outside a formula%s: put it between \\( and \\), or "
                        "between $ and $." % where)
        return out
    if re.search(r"Missing \} inserted|Extra \}|Runaway argument|File ended while scanning|"
                 r"Missing \{ inserted|Extra alignment tab", msg):
        out.update(said="A brace is missing, or there is one too many%s." % where)
        return out
    m = re.search(r"I do not know the key '([^']+)'", msg)
    if m:
        out.update(said="TikZ does not know the option \"%s\"%s." % (m.group(1).split("/")[-1], where))
        return out
    m = re.search(r"Undefined color `?'?([^'`]+)'", msg)
    if m:
        out.update(said="The colour \"%s\" is not one LaTeX knows%s." % (m.group(1), where))
        return out
    if "Emergency stop" in msg or "Fatal" in msg:
        out.update(said="LaTeX gave up%s." % where)
        return out
    out.update(said="LaTeX stopped%s: %s" % (where, msg.strip().rstrip(".") + "."))
    return out


# ------------------------------------------------------------ what is kept
def size():
    n, total = 0, 0
    for here, _dirs, files in os.walk(DRAWN):
        for f in files:
            if f.endswith(".svg"):
                n += 1
            try:
                total += os.path.getsize(os.path.join(here, f))
            except OSError:
                pass
    return {"drawings": n, "bytes": total}


def prune(days=PRUNE_DAYS):
    """What no block has asked for in `days` days, removed (when Parseh starts)."""
    cut = time.time() - days * 86400
    gone = 0
    for here, _dirs, files in os.walk(DRAWN):
        for f in files:
            if not f.endswith(".json") or f.endswith(".fail.json"):
                continue
            meta = os.path.join(here, f)
            try:
                if os.path.getmtime(meta) >= cut:
                    continue
            except OSError:
                continue
            key = f[:-5]
            for p in paths(key).values():
                try:
                    os.unlink(p)
                except OSError:
                    pass
            gone += 1
    return gone


def forget_unused(used):
    """Every drawing whose key is not in `used`, removed -> how many, and
    how many bytes that freed.  Settings' "Forget drawings nothing uses"."""
    gone, freed = 0, 0
    for here, _dirs, files in os.walk(DRAWN):
        for f in files:
            key = f.split(".")[0]
            if KEY_RE.match(key) and key not in used:
                p = os.path.join(here, f)
                try:
                    freed += os.path.getsize(p)
                    os.unlink(p)
                    if f.endswith(".svg"):
                        gone += 1
                except OSError:
                    pass
    with _LOCK:
        _FAILED.clear()
    return {"drawings": gone, "bytes": freed}


def forget_failures():
    """Every failure remembered, forgotten: a package installed, a compiler
    found, a limit changed -- anything that may mend one."""
    with _LOCK:
        _FAILED.clear()
        for name in list(_TOOLS):
            _TOOLS.pop(name, None)
    for here, _dirs, files in os.walk(DRAWN):
        for f in files:
            if f.endswith(".fail.json"):
                try:
                    os.unlink(os.path.join(here, f))
                except OSError:
                    pass
