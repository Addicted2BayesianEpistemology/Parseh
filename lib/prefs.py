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
import json
import os
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "config", "prefs.json")

# the settings that follow a person from one device to another.  A key not
# named here is nobody's business but the browser's that wrote it -- which is
# how "what is shown" (bk_p1, bk_nogloss, the typography) stays per device.
KEYS = ("bk_rate", "bk_gap", "bk_skip", "bk_stopbnd", "parseh_theme")
MAX_VALUE = 200          # a setting is a number or a word, never a document
MAX_PLACES = 2000        # one per book ever opened; far more than a shelf holds


def _read():
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
    never half of either."""
    folder = os.path.dirname(STORE)
    os.makedirs(folder, exist_ok=True)
    tmp = STORE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, STORE)
    return doc


def all_of():
    """Everything, as a page asks for it at load."""
    return _read()


def settings():
    return _read()["settings"]


def places():
    return _read()["places"]


def _clean(s, limit=MAX_VALUE):
    s = "" if s is None else str(s)
    s = s.replace("\n", " ").replace("\r", " ").strip()
    return s[:limit]


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


def forget_place(path):
    doc = _read()
    if doc["places"].pop(_clean(path, 300), None) is None:
        return False
    _write(doc)
    return True
