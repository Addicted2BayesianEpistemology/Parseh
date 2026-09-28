# SPDX-License-Identifier: GPL-3.0-or-later
"""engine.drawings -- the LaTeX drawings of the guide, drawn beforehand.

A latex block (`::::latex`) and a latex mark (`[...]{latex}`) are drawn by
LaTeX, and a compile of the guide runs where there may be no TeX -- a CI
machine, the copy `build.py --export` makes -- and must stay standard library
only.  So the guide never draws while it compiles.  Every drawing it shows was
made beforehand, by `build.py --draw` on a computer that has TeX, and lives in
html-guide/markdown/drawings/ as `<key>.svg` and `<key>.json` (the picture,
and its width, height and depth in points).  Everything under markdown/ that
is not a page is copied into the site, so the pictures need no copying of
their own.

THE KEY is a hash of what makes the picture: its LaTeX, the theme's name and
preamble, and whether it is a mark in a line -- and nothing of the machine.
lib/latexdraw.py's own key holds the TeX installation's state, which differs
from one computer to the next; a key like that would make every drawing
"missing" on every computer but the one that made it.  The guide's drawings
are made under the three starter themes (lib/latexthemes.py STARTERS), never
the ones in this computer's Settings, so the guide is the same everywhere:
a starter's preamble is in the key, and a starter that changes makes its
drawings missing, and said.

A drawing that is not there is not an error of the page: the studio's own
frame stands in its place (its LaTeX, and one line saying it is drawn where
Parseh can compile it), and the compile says so, once for each, so that
`--strict` fails on a forgotten `--draw`.

THE STUDIO'S DRAWER is a module-global (htmlgen.LATEX).  It is set for the
length of a compile and put back after, whatever happens: the guide's tests
compile in the same process as the studio's, and a drawer left behind would
draw every later document from these pictures.
"""
import concurrent.futures
import contextlib
import hashlib
import json
import posixpath
import shutil
import sys
import tempfile
from pathlib import Path

from .studio import htmlgen
import latexthemes  # noqa: E402  (on sys.path once engine.studio has been imported)

KEY_LENGTH = 24
FOLDER = "drawings"
THE_STARTERS = ("default", "chemistry", "drawing")
MISSING_SAID = ("It is drawn by LaTeX where Parseh can compile it, and shown here as it "
                "is written.")


def starter(name):
    """The starter theme called `name` (no name: the default one), or None."""
    want = latexthemes.name_key(name or latexthemes.DEFAULT)
    for t in latexthemes.STARTERS:
        if latexthemes.name_key(t["name"]) == want:
            return t
    return None


def key_of(tex, theme, inline=False):
    """The name of the drawing of `tex` under the starter theme `theme` (its
    dict), as a mark in a line or as a block."""
    blob = json.dumps({"guide-drawing": 1, "tex": tex, "theme": theme["name"],
                       "preamble": latexthemes.preamble(theme), "inline": bool(inline)},
                      sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:KEY_LENGTH]


def _rel_url(frm, to):
    base = posixpath.dirname(frm)
    return posixpath.relpath(to, base or ".")


class Drawings:
    """The drawings folder of one guide, and the drawer a compile hands the
    studio.  `wanted` fills as a compile asks: key -> {tex, theme, inline},
    which is how `build.py --draw` knows what to draw."""

    def __init__(self, folder):
        self.folder = Path(folder)
        self.wanted = {}

    def meta(self, key):
        """The measures of a drawing that is here (both files, the JSON
        readable and its numbers numbers), or None."""
        try:
            meta = json.loads((self.folder / (key + ".json")).read_text(encoding="utf-8"))
            if not (self.folder / (key + ".svg")).is_file():
                return None
            if not all(isinstance(meta.get(k), (int, float)) for k in ("w", "h")):
                return None
            return meta
        except (OSError, ValueError, AttributeError):
            return None

    def drawer(self, ctx_of):
        """The function htmlgen.set_latex() takes; `ctx_of()` is the page
        being compiled (its warnings, and where it lies in the site)."""
        def draw(tex, theme=None, inline=False, preview=False):
            ctx = ctx_of()
            found = starter(theme)
            if found is None:
                said = ("The guide draws with the three starter themes only (%s), and "
                        "“%s” is none of them." % (", ".join(THE_STARTERS), theme))
                ctx.warn("latex drawing: " + said)
                return {"ok": False, "kind": "theme", "said": said}
            key = key_of(tex, found, inline)
            self.wanted[key] = {"tex": tex, "theme": found["name"], "inline": bool(inline)}
            meta = self.meta(key)
            if meta is None:
                ctx.warn("latex drawing: no pre-drawn picture (theme “%s”, %s); "
                         "run html-guide/build.py --draw" % (found["name"], _shorten(tex)))
                return {"ok": False, "kind": "here", "said": MISSING_SAID}
            return {"ok": True, "key": key, "w": meta["w"], "h": meta["h"], "d": meta.get("d"),
                    "url": _rel_url(ctx.page.out, "%s/%s.svg" % (FOLDER, key))}
        return draw

    @contextlib.contextmanager
    def installed(self, ctx_of):
        """For the length of the block the studio draws from this folder; what
        was set before is put back.  A picture's url is already the page's own,
        so the prefix a running studio is served under (htmlgen.URL_BASE) must
        not be put in front of it."""
        saved, base = dict(htmlgen.LATEX), htmlgen.URL_BASE
        htmlgen.set_latex(self.drawer(ctx_of), None, None)
        htmlgen.URL_BASE = ""
        try:
            yield self
        finally:
            htmlgen.LATEX.clear()
            htmlgen.LATEX.update(saved)
            htmlgen.URL_BASE = base


def _shorten(tex):
    one = " ".join(tex.split())
    return "“%s”" % (one if len(one) <= 48 else one[:45] + "...")


# ------------------------------------------------------------ build.py --draw
def _latexdraw():
    """lib/latexdraw.py, or an explanation of why this computer cannot draw."""
    try:
        import latexdraw
    except ImportError:
        raise SystemExit(
            "--draw needs lib/latexdraw.py, which a guide copied out of Parseh "
            "(build.py --export) does not carry: draw from the Parseh checkout, "
            "where the environment has PyMuPDF and TeX, and copy html-guide/"
            "markdown/drawings/ over")
    if latexdraw.compiler("xelatex") is None:
        raise SystemExit("--draw needs xelatex on the PATH (TeX Live or MiKTeX): the "
                         "starter themes are compiled with it")
    return latexdraw


def _write(folder, key, item, result):
    meta = {"tex": item["tex"], "theme": item["theme"], "inline": item["inline"],
            "w": result["w"], "h": result["h"]}
    if item["inline"]:
        meta["d"] = result.get("d") or 0
    (folder / (key + ".svg")).write_bytes(Path(result["svg"]).read_bytes())
    (folder / (key + ".json")).write_text(
        json.dumps(meta, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def main(guide, check=False, quiet=False):
    """`build.py --draw` -> an exit code.  Compiles the guide into a scratch
    folder to learn which drawings its pages ask for, draws the ones that are
    not in markdown/drawings/ yet, and removes the ones no page asks for any
    more.  `check` only says what it would do."""
    from .site import Site
    say = (lambda *_a: None) if quiet else print
    site = Site(guide)
    scratch = Path(tempfile.mkdtemp(prefix="parseh-guide-draw-"))
    try:
        report = site.build(scratch / "site")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    for p in report.errors:
        print(p, file=sys.stderr)
    if report.errors:
        return 1
    folder = site.drawings.folder
    wanted = site.drawings.wanted
    missing = sorted(k for k in wanted if site.drawings.meta(k) is None)
    unused = sorted({p.stem for p in folder.glob("*") if p.suffix in (".svg", ".json")}
                    - set(wanted)) if folder.is_dir() else []
    say("the guide asks for %d drawing%s: %d there, %d to draw, %d nobody asks for"
        % (len(wanted), "" if len(wanted) == 1 else "s", len(wanted) - len(missing),
           len(missing), len(unused)))
    if check:
        for k in missing:
            say("  would draw %s  %s (%s)" % (k, _shorten(wanted[k]["tex"]), wanted[k]["theme"]))
        for k in unused:
            say("  would remove %s" % k)
        return 0
    failed = 0
    if missing:
        latexdraw = _latexdraw()
        folder.mkdir(parents=True, exist_ok=True)
        # drawn in a folder of their own: the checkout's markdown/latex cache
        # (the drawings of a document a person is writing) is neither read nor
        # added to by a build of the guide
        kept = latexdraw.DRAWN
        latexdraw.DRAWN = tempfile.mkdtemp(prefix="parseh-guide-drawn-")
        try:
            def one(key):
                item = wanted[key]
                return key, latexdraw.draw(item["tex"], None, theme=starter(item["theme"]),
                                           limit=120, inline=item["inline"])
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
                for key, result in pool.map(one, missing):
                    item = wanted[key]
                    if result.get("ok"):
                        _write(folder, key, item, result)
                        say("  drew %s  %s (%s)" % (key, _shorten(item["tex"]), item["theme"]))
                    else:
                        failed += 1
                        print("  COULD NOT DRAW %s (%s): %s%s" % (
                            _shorten(item["tex"]), item["theme"], result.get("said"),
                            "\n%s" % result["detail"] if result.get("detail") else ""), file=sys.stderr)
        finally:
            shutil.rmtree(latexdraw.DRAWN, ignore_errors=True)
            latexdraw.DRAWN = kept
    for k in unused:
        for ext in (".svg", ".json"):
            (folder / (k + ext)).unlink(missing_ok=True)
        say("  removed %s" % k)
    return 1 if failed else 0
