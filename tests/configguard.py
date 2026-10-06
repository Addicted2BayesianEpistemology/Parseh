# SPDX-License-Identifier: GPL-3.0-or-later
"""NOTHING A TEST DOES MAY CHANGE config/.

config/ beside the checkout is the owner's own: his preferences
(`lib/prefs.py`, prefs.json), who may reach Parseh (`lib/network.py`,
network.json), the two memories the phone-keeping door learns
(`lib/offline.py`, digests.json and wheres.json) and the prompts he wrote for
the chatbots (`lib/prompts.py`, prompts.json -- his own words, which no test
may ever leave a line in).  A test may exercise every
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

Used by `tests/test_config_untouched.py`, which watches the unit suite, by
`tests/smoke.py`, which watches itself, and from the command line by release
step 1 (docs/releasing.md), around the loop of browser suites, which have no
suite of their own to watch them:

    python3 tests/configguard.py save ../parseh-suites/config.before
    ... every tests/*.mjs ...
    python3 tests/configguard.py check ../parseh-suites/config.before

`check` says what moved and WHEN each file was written, which is the way to
the suite that ran at that time (the logs of the loop are dated).  Standard
library only.
"""
import base64
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"

# what the report says after the list, for whoever reads a red run
ADVICE = ("config/ is the owner's own settings folder, and a test must leave "
          "it as it found it: point the store at the test's temporary tree "
          "first, as tests/decks_harness.py does for every store "
          "(tests/test_harness_stores.py lists them, and asks it of every "
          "harness).  (A Parseh started from this checkout and used while "
          "the tests ran writes there too, and would be reported in the "
          "same words.)")

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


def save(path, folder=CONFIG):
    """Remember what `folder` holds, in a file of its own, for `check` to be
    asked about after a run of suites that are not unit tests."""
    mem = {name: None if data is None else base64.b64encode(data).decode("ascii")
           for name, data in snapshot(folder).items()}
    Path(path).write_text(json.dumps(mem), encoding="utf-8")


def load(path):
    """What `save` remembered -> a snapshot."""
    mem = json.loads(Path(path).read_text(encoding="utf-8"))
    return {name: None if data is None else base64.b64decode(data) for name, data in mem.items()}


def check(path, folder=CONFIG):
    """What a run did to `folder` since `save` -> (the report, or "" when it
    is as it was, and the time each file it names was last written)."""
    before, now = load(path), snapshot(folder)
    when = []
    for line in changes(before, now):
        # a line of `changes` begins with the path it is about
        file = Path(folder) / line.split(" ", 1)[0]
        if file.is_file():
            when.append("%s written at %s" % (file.name, time.strftime("%H:%M:%S", time.localtime(file.stat().st_mtime))))
    return report(before, now, folder), when


def main(argv):
    folder = CONFIG
    if "--folder" in argv:
        i = argv.index("--folder")
        folder = Path(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    if len(argv) != 2 or argv[0] not in ("save", "check"):
        print("usage: python3 tests/configguard.py save|check FILE [--folder DIR]")
        return 2
    if argv[0] == "save":
        save(argv[1], folder)
        print("%s remembered in %s" % (folder, argv[1]))
        return 0
    said, when = check(argv[1], folder)
    if not said:
        print("%s is as it was" % folder)
        return 0
    print(said)
    for line in when:
        print("  " + line)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
