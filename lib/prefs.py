#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""What this person has settled, kept by the toolbox rather than by a browser
(TO-DO §4.9).

Two things live here, both asked for so that a phone can go on where the
computer stopped:

  * **The reading place**, per book: which subparagraph was last read, said in
    words as well as by its number, with the time and the device that read it.
  * **The settings that follow a person**, for every book at once: how fast a
    narration plays (`bk_rate`), the pause between repetitions (`bk_gap`), how
    far ↺ and ↻ carry (`bk_skip`), whether a chapter's start waits for play
    (`bk_stopbnd`) -- and the theme (`parseh_theme`).

WHAT IS NOT HERE.  What is SHOWN stays with the device that shows it: which
passes are open, the size of the text, the margins.  A phone is not a
computer, and somebody reading in bed does not want the screen they set up at
a desk (the owner's choice, 2026-09-22).

    config/prefs.json
    {"settings": {"bk_rate": {"v": "1.5", "at": 1758531600.0,
                              "by": "Linux computer · Firefox"}, ...},
     "places": {"/books/english/three-clocks/reader/":
                {"i": 12, "label": "2 · 1.1", "pct": 40,
                 "at": 1758531600.0, "by": "Android phone · Chrome"}}}

EVERY VALUE CARRIES THE MOMENT IT WAS SET, because two devices may both have
been away: for the settings the last change wins, plainly; for the reading
place nothing is overruled at all -- a device opens at its own place and is
ASKED whether to go to the other's, which is the one thing here a person
might disagree with.

The file is this machine's, and no book's: it is not in `lib/bundle.py`'s
allowlist, so a book downloaded and handed on carries the edition, not
somebody's progress through it.
"""
import functools
import itertools
import json
import os
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "config", "prefs.json")
# the shape of STORE, as a number (lib/version.py FORMATS): RAISE IT when the
# shape changes so that the Parseh before this one would read the file wrong
# -- an updater going back to that one then says so before it moves
STORE_FORMAT = 1

# the settings that follow a person from one device to another.  A key not
# named here is nobody's business but the browser's that wrote it -- which is
# how "what is shown" (bk_p1, bk_nogloss, the typography) stays per device.
KEYS = ("bk_rate", "bk_gap", "bk_skip", "bk_stopbnd", "parseh_theme")
MAX_VALUE = 200          # a setting is a number or a word, never a document
MAX_PLACES = 2000        # one per book ever opened; far more than a shelf holds


# THE ONE LOCK FOR THIS FILE, which every writer in this process takes around
# its whole read-change-write (lib/later.py shares it).  The server answers
# each request on a thread of its own, and a person's pages write together --
# a reader's place, a speed, a mark -- so two of them used to read the same
# file, change different things and write it back, the later one erasing the
# earlier's change; and, worse, both wrote through ONE temporary name, so the
# second `open` truncated what the first was about to move into place, and
# the first `os.replace` then failed with FileNotFoundError, answered as a 400
# (tests/making.mjs measured 379 of 3000 writes lost that way).  An RLock, so
# that a function holding it may call another that takes it.
LOCK = threading.RLock()
# and a temporary name no other write can share, between threads and between
# two servers over one config/ alike
_SEQ = itertools.count(1)


def _locked(fn):
    """A function that reads this file, changes what it read and writes it
    back, as one step nobody else's can fall into."""
    @functools.wraps(fn)
    def inside(*args, **kwargs):
        with LOCK:
            return fn(*args, **kwargs)
    return inside


def _read():
    # under the lock so that a read never has the file open while a write
    # moves a new one over it (a platform that will not replace an open file
    # would refuse the write)
    with LOCK:
        try:
            with open(STORE, "r", encoding="utf-8") as fh:
                doc = json.load(fh)
        except (OSError, ValueError):
            return {"settings": {}, "places": {}}
    if not isinstance(doc, dict):
        return {"settings": {}, "places": {}}
    for k in ("settings", "places"):
        if not isinstance(doc.get(k), dict):
            doc[k] = {}
    return doc


def _write(doc):
    """Written whole, through a temporary file beside it: a reader asking for
    the place while it is being written gets the old file or the new one, and
    never half of either.  The temporary name is this write's own (process,
    then a number), and the whole is held under LOCK."""
    with LOCK:
        folder = os.path.dirname(STORE)
        os.makedirs(folder, exist_ok=True)
        tmp = "%s.%d.%d.tmp" % (STORE, os.getpid(), next(_SEQ))
        try:
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(doc, fh, ensure_ascii=False, indent=1, sort_keys=True)
                fh.write("\n")
            os.replace(tmp, STORE)
        finally:
            # a write that failed half way leaves nothing behind
            try:
                os.unlink(tmp)
            except OSError:
                pass
    return doc


def all_of():
    """Everything a page asks for at load: the settings and the places.  NOT
    `later` (lib/later.py), the chunks flagged to review: they have a door of
    their own (/__later) so that they do not ride on every page load.  They
    stay in the file all the same, which every writer here writes back whole."""
    doc = _read()
    return {"settings": doc["settings"], "places": doc["places"]}


def settings():
    return _read()["settings"]


def places():
    return _read()["places"]


def _clean(s, limit=MAX_VALUE):
    s = "" if s is None else str(s)
    s = s.replace("\n", " ").replace("\r", " ").strip()
    return s[:limit]


@_locked
def set_settings(changes, by=""):
    """`changes` is {key: {"v": value, "at": seconds}}; a key nobody follows is
    ignored, and an older change never overwrites a newer one."""
    doc = _read()
    now = time.time()
    said = {}
    for key, val in (changes or {}).items():
        if key not in KEYS or not isinstance(val, dict):
            continue
        at = val.get("at")
        try:
            at = float(at)
        except (TypeError, ValueError):
            at = now
        # a clock set wrong, or a value from the future: taken as now
        at = min(max(at, 0.0), now + 60.0)
        was = doc["settings"].get(key)
        if isinstance(was, dict) and float(was.get("at") or 0) > at:
            continue
        doc["settings"][key] = {"v": _clean(val.get("v")), "at": at, "by": _clean(by, 60)}
        said[key] = doc["settings"][key]
    if said:
        _write(doc)
    return doc["settings"]


def place(path):
    return _read()["places"].get(path)


@_locked
def set_place(path, i, label="", pct=None, by="", at=None):
    """Where a book was last read. `path` is the reader's own address, which is
    what a reader already keys its own copy by (`MINE('pos')`)."""
    path = _clean(path, 300)
    if not path:
        raise ValueError("which book?")
    try:
        i = int(i)
    except (TypeError, ValueError):
        raise ValueError("the place is a subparagraph's number")
    if i < 0:
        raise ValueError("the place is a subparagraph's number")
    doc = _read()
    now = time.time()
    try:
        at = min(float(at), now + 60.0) if at is not None else now
    except (TypeError, ValueError):
        at = now
    was = doc["places"].get(path)
    if isinstance(was, dict) and float(was.get("at") or 0) > at:
        return was
    rec = {"i": i, "label": _clean(label, 80), "at": at, "by": _clean(by, 60)}
    if pct is not None:
        try:
            rec["pct"] = max(0, min(100, int(pct)))
        except (TypeError, ValueError):
            pass
    doc["places"][path] = rec
    # a shelf of books cannot grow past this, but a tree read and rebuilt
    # under many addresses could: the oldest go
    if len(doc["places"]) > MAX_PLACES:
        old = sorted(doc["places"].items(), key=lambda kv: float(kv[1].get("at") or 0))
        for k, _ in old[:len(doc["places"]) - MAX_PLACES]:
            doc["places"].pop(k, None)
    _write(doc)
    return rec


@_locked
def forget_place(path):
    doc = _read()
    if doc["places"].pop(_clean(path, 300), None) is None:
        return False
    _write(doc)
    return True
