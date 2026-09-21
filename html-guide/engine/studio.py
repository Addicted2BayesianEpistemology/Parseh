"""engine.studio -- where the studio's renderer comes from, and the one seam
the guide opens in it.

THE GUIDE SHOWS EXACTLY WHAT THE STUDIO SHOWS.  A lemma heading, a box, a
target-language run, an exercise, a formula: every one of them is drawn by
the studio's own parser and renderer (markdown/exlex/mdparser.py,
markdown/app/htmlgen.py, with lib/languages.py behind them), imported here
and never copied by hand.  A change to the dialect reaches the guide the next
time it is compiled, and a page of the guide can never drift from what a
document in the studio looks like.

WHERE THEY ARE.  Inside Parseh, html-guide/ sits beside markdown/ and lib/,
and the live sources are used.  Copied into a project of its own
(`build.py --export`), the guide carries a snapshot of exactly the files it
needs under engine/vendor/, laid out as they are in Parseh -- vendor/lib/,
vendor/markdown/exlex/, vendor/markdown/app/ -- so the modules find one
another by the same relative paths and not a line of them is patched.
PARSEH_GUIDE_STUDIO=vendor forces the snapshot (the export test uses it);
=live forces the checkout.

THE SEAM.  htmlgen.inline() is where the studio turns a line of its dialect
into HTML, and every block renderer calls it by its module-level name.  The
guide adds Hugo's inline Markdown (code spans, links with titles, reference
links, autolinks, `_emphasis_`, `~~strikethrough~~`, typographic quotes...)
by replacing that name, for the duration of one compile, with a function
that first protects the Hugo constructs behind placeholders and then calls
the original.  Every block the studio draws -- a table cell, a list item, an
exercise prompt, a footnote -- gets the same inline language that way,
without a line of htmlgen changing.  The replacement is process-wide, which
is why the Parseh server never imports this package: it runs build.py as a
child process (lib/guidebuild.py), and only a compile ever has the seam open.
"""
import contextlib
import importlib
import os
import sys
from pathlib import Path

from .manifest import MODULE_FILES, RUNTIME_FILES, FONT_DIRS, MANUAL  # noqa: F401

ENGINE = Path(__file__).resolve().parent
GUIDE = ENGINE.parent
VENDOR = ENGINE / "vendor"


def _complete(root):
    return all((root / f).is_file() for f in MODULE_FILES)


def locate():
    """(root, kind): the directory the studio's sources are under -- the
    Parseh checkout html-guide/ lives in ("live"), or the snapshot under
    engine/vendor/ ("vendor")."""
    want = os.environ.get("PARSEH_GUIDE_STUDIO", "").strip().lower()
    live = GUIDE.parent
    if want != "vendor" and _complete(live):
        return live, "live"
    if want != "live" and _complete(VENDOR):
        return VENDOR, "vendor"
    raise SystemExit(
        "the guide's engine needs the Parseh studio's renderer: either run it "
        "from html-guide/ inside a Parseh checkout, or from a copy made with "
        "`build.py --export`, which carries it in engine/vendor/ (looked in %s "
        "and %s)" % (live, VENDOR))


ROOT, KIND = locate()

for _sub in ("lib", "markdown/exlex", "markdown/app"):
    _p = str(ROOT / _sub)
    if _p not in sys.path:
        sys.path.insert(0, _p)

languages = importlib.import_module("languages")
texgen = importlib.import_module("texgen")
mdparser = importlib.import_module("mdparser")
htmlgen = importlib.import_module("htmlgen")

# the studio's own inline(), whatever the seam below has done to the name
ORIGINAL_INLINE = htmlgen.inline


def source(rel):
    """A file of the studio's, by its path in Parseh (`lib/mathjax.js`)."""
    return ROOT / rel


def find_font(name):
    """Where a font the studio's sheet names is on this machine, or None.

    The target scripts' faces travel with the toolbox (lib/fonts).  The
    sheet's Latin faces, TeX Gyre Pagella and Heros, are TeX's: the studio
    copies them out of the TeX installation at start (server.py
    ensure_web_fonts), and so does this, looking where TeX Live, a Linux
    distribution's fonts-texgyre and the usual font folders keep them.  A
    face not found is simply not copied: the sheet's stack falls back to
    Palatino, Georgia and the like, and the page still reads."""
    for d in FONT_DIRS:
        p = ROOT / d / name
        if p.is_file():
            return p
    if name.startswith("texgyre"):
        import shutil
        import subprocess
        if shutil.which("kpsewhich"):
            try:
                r = subprocess.run(["kpsewhich", name], capture_output=True,
                                   text=True, timeout=20)
                p = Path(r.stdout.strip()) if r.stdout.strip() else None
                if p and p.is_file():
                    return p
            except (OSError, subprocess.SubprocessError):
                pass
        home = Path.home()
        for d in ("/usr/share/texmf/fonts/opentype/public/tex-gyre",
                  "/usr/share/texlive/texmf-dist/fonts/opentype/public/tex-gyre",
                  "/usr/local/texlive/texmf-dist/fonts/opentype/public/tex-gyre",
                  "/usr/share/fonts/opentype/texgyre", "/usr/share/fonts/texgyre",
                  "/usr/share/fonts/OTF", "/Library/Fonts", str(home / "Library/Fonts"),
                  str(home / ".local/share/fonts"), str(home / ".fonts"),
                  os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")):
            p = Path(d) / name
            if p.is_file():
                return p
    return None


@contextlib.contextmanager
def inline_seam(prepare):
    """For the duration of the block: every call the studio's renderer makes
    to its own inline() goes through `prepare` first (the Hugo layer,
    engine/inline.py), then to the original.  The original is put back
    whatever happens inside."""
    def inline(text, force_breakable=False):
        return ORIGINAL_INLINE(prepare(text), force_breakable)
    htmlgen.inline = inline
    try:
        yield
    finally:
        htmlgen.inline = ORIGINAL_INLINE


@contextlib.contextmanager
def isolated_render(target):
    """A fresh render state (footnote numbering, occurrence counters, the
    target language) for a piece rendered on its own -- a `parseh-example`
    block -- with the page's put back afterwards.  The two stores are
    texgen.ThreadDict, which keeps this thread's dict as `_d`: copied whole,
    so a key the studio adds later is saved too."""
    fn = dict(htmlgen._FN._d)
    occ = dict(htmlgen._OCC._d)
    was = texgen.cur_lang().code
    texgen.set_target(target)
    htmlgen.reset_state({})
    try:
        yield
    finally:
        htmlgen._FN.clear()
        htmlgen._FN.update(fn)
        htmlgen._OCC.clear()
        htmlgen._OCC.update(occ)
        texgen.set_target(was)
