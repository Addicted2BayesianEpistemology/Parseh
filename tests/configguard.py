# SPDX-License-Identifier: GPL-3.0-or-later
"""NOTHING A TEST DOES MAY CHANGE config/.

config/ beside the checkout is the owner's own: his preferences
(`lib/prefs.py`, prefs.json), who may reach Parseh (`lib/network.py`,
network.json), and the two memories the phone-keeping door learns
(`lib/offline.py`, digests.json and wheres.json).  A test may exercise every
one of those stores and must never write the real one: it points the store
at a temporary tree first, as `tests/decks_harness.py` and the harnesses
beside it do, or patches it for as long as it runs, as
`tests/test_wave_estimate.py` does.

WHY A GUARD AND NOT ONLY THE FIXES (TO-DO §2.25).  The same fault has now
been found twice.  A suite once left the owner's theme dark by writing his
real prefs.json, and the harnesses were pointed at their temporary trees --
for the two stores anybody had thought of.  Two unit modules went on writing
digests.json and wheres.json, and nobody saw it until another session
happened to hash the file.  A redirect mends one store; this makes the next
one visible the first time the suite runs, whatever the store is called.

Used by `tests/test_config_untouched.py`, which watches the unit suite, and
by `tests/smoke.py`, which watches itself.  Standard library only.
"""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"

# what the report says after the list, for whoever reads a red run
ADVICE = ("config/ is the owner's own settings folder, and a test must leave "
          "it as it found it: point the store at the test's temporary tree "
          "first, as tests/decks_harness.py does for prefs.STORE, "
          "network.STORE, offline.DIGESTS and offline.WHERES.  (A Parseh "
          "started from this checkout and used while the tests ran writes "
          "there too, and would be reported in the same words.)")

_GONE = object()


def snapshot(folder=CONFIG):
    """Every file under `folder` with its bytes, and every folder under it,
    by the path relative to `folder` -> {path: bytes, or None for a folder}.

    THE BYTES AND NOT A HASH, because config/ is small -- a few hundred
    kilobytes, nearly all of it digests.json -- and a report that can say
    WHICH entries appeared is one that points at the test that wrote them:
    the entries of these stores are named by paths, and a test's paths are
    those of its own temporary tree.

    A file that vanishes between being listed and being read is left out
    rather than failing the look: it is the scratch neighbour a store is
    written to and moved from, and the file it was moved over is what counts.
    """
    out = {}
    folder = Path(folder)
    for here, dirs, files in os.walk(folder):
        dirs.sort()
        at = Path(here)
        for name in dirs:
            out[(at / name).relative_to(folder).as_posix() + "/"] = None
        for name in sorted(files):
            try:
                out[(at / name).relative_to(folder).as_posix()] = (at / name).read_bytes()
            except OSError:
                pass
    return out


def changes(before, after):
    """What differs between two snapshots, one line to a path, in words ->
    [] when nothing does."""
    said = []
    for path in sorted(set(before) | set(after)):
        was, now = before.get(path, _GONE), after.get(path, _GONE)
        if was == now:
            continue
        if was is _GONE:
            said.append("%s appeared%s" % (path, "" if now is None else
                                           " (%d bytes)" % len(now)))
        elif now is _GONE:
            said.append("%s was removed" % path)
        else:
            said.append("%s changed (%d -> %d bytes)%s"
                        % (path, len(was), len(now), _entries(was, now)))
    return said


def _entries(was, now):
    """For a store -- a JSON object -- which of its entries moved, with the
    names of a few.  Nothing to add for anything else."""
    try:
        a, b = json.loads(was), json.loads(now)
    except ValueError:
        return ""
    if not (isinstance(a, dict) and isinstance(b, dict)):
        return ""
    parts = []
    added = [k for k in b if k not in a]
    removed = [k for k in a if k not in b]
    moved = [k for k in a if k in b and a[k] != b[k]]
    if added:
        parts.append("%d added, e.g. %s" % (len(added), ", ".join(added[:3])))
    if removed:
        parts.append("%d removed, e.g. %s" % (len(removed), ", ".join(removed[:3])))
    if moved:
        # a preference is one short value, and the old one is what somebody
        # would need to put it back by hand; a digest's record is not worth
        # printing
        parts.append("%d changed, e.g. %s" % (len(moved), ", ".join(
            "%s (%s -> %s)" % (k, json.dumps(a[k]), json.dumps(b[k]))
            if len(json.dumps(a[k])) + len(json.dumps(b[k])) < 80 else k
            for k in moved[:3])))
    return ": " + "; ".join(parts) if parts else ""


def report(before, after, folder=CONFIG):
    """The whole of what a red run says, or "" when the folder is as it was."""
    said = changes(before, after)
    if not said:
        return ""
    return ("%s changed while the tests ran:\n  %s\n%s"
            % (folder, "\n  ".join(said), ADVICE))
