"""engine.fingerprint -- what a compile of the guide depends on, as one hash.

The compiled site/ is up to date when it was built from exactly the sources
there are now: the pages under markdown/ (and every picture beside them), the
engine itself, and the files it takes from Parseh (engine/manifest.py) --
the studio's renderer and its runtime.  The build writes the hash into
site/build.json; the Parseh server (lib/guidebuild.py) computes it again to
say whether the guide the button opens is the guide the sources make.

Standard library only, and nothing of the studio imported: the server asks
this without loading the renderer into its own process.  The assets/ and
index.html are not in it -- a page links them live, so changing them never
needs a compile.
"""
import hashlib
import os
from pathlib import Path

from .manifest import MODULE_FILES, RUNTIME_FILES

ENGINE = Path(__file__).resolve().parent
GUIDE = ENGINE.parent


def _studio_root():
    live = GUIDE.parent
    if all((live / f).is_file() for f in MODULE_FILES):
        return live
    return ENGINE / "vendor"


def _walk(base):
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = sorted(d for d in dirnames
                             if not d.startswith(".") and d not in ("__pycache__", "vendor"))
        for name in sorted(filenames):
            if not name.startswith(".") and not name.endswith((".pyc", ".pyo")):
                yield Path(dirpath) / name


def sources(guide=GUIDE):
    """[(label, path)] of everything a compile reads, in a fixed order."""
    guide = Path(guide)
    out = [("markdown/" + p.relative_to(guide / "markdown").as_posix(), p)
           for p in _walk(guide / "markdown")]
    out += [("engine/" + p.relative_to(guide / "engine").as_posix(), p)
            for p in _walk(guide / "engine") if p.suffix == ".py"]
    root = _studio_root()
    out += [("parseh/" + rel, root / rel) for rel in MODULE_FILES + RUNTIME_FILES]
    return out


def fingerprint(guide=GUIDE):
    """The hash of every source's name and bytes."""
    h = hashlib.sha256()
    for label, path in sources(guide):
        h.update(label.encode("utf-8") + b"\0")
        try:
            h.update(hashlib.sha256(path.read_bytes()).digest())
        except OSError:
            h.update(b"missing")
    return h.hexdigest()
