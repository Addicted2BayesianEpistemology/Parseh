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
    (`bk_stopbnd`), whether the recording goes on into the next line
    (`bk_cont`, "keep going") -- the theme (`parseh_theme`) -- and the NAMES
    a person gave the levels of a book (`bk_lvl:<language>:<pass key>`, one
    key for each: `bk_lvl:fa:vocal`).

WHAT IS NOT HERE.  What is SHOWN stays with the device that shows it: which
levels are open, the size of the text, the margins.  A phone is not a
computer, and somebody reading in bed does not want the screen they set up at
a desk (the owner's choice, 2026-09-22).  What a level is CALLED is the
person's, though -- a name is a word they chose, not a way the screen is set
up -- and so it follows them (the owner's, 2026-10-06).

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
import re
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "config", "prefs.json")
# the shape of STORE, as a number (lib/version.py FORMATS): RAISE IT when the
# shape changes so that the Parseh before this one would read the file wrong
# -- an updater going back to that one then says so before it moves
#
# a0.5.0 ADDED KEYS TO `settings` (bk_cont, and the bk_lvl: family below) AND
# DID NOT RAISE IT.  The shape is the same -- {"settings": {key: {"v", "at",
# "by"}}, "places": {...}} -- and the Parseh before this one reads such a file
# as it always did: its set_settings ignores a key it does not know and keeps
# the ones it holds (it reads the whole document and writes the whole document
# back), and its pages ask the server for everything and wear only the keys of
# their own list.  A field added that an older reader simply ignores is not a
# change of shape (lib/version.py, "THE DATA'S OWN NUMBERS ARE NOT THE VERSION").
STORE_FORMAT = 1

# the settings that follow a person from one device to another.  A key not
# named here is nobody's business but the browser's that wrote it -- which is
# how "what is shown" (bk_no1 ... bk_no5, the levels hidden; bk_nogloss; the
# typography) stays per device.
KEYS = ("bk_rate", "bk_gap", "bk_skip", "bk_stopbnd", "bk_cont", "parseh_theme")
# THE ONE FAMILY OF KEYS KNOWN BY ITS BEGINNING: what a person calls a level of
# a book (a0.5.0).  One key per language and per level -- bk_lvl:fa:vocal --
# because the registry names its passes per language (lib/languages.py) and the
# last change wins for each of them on its own.  The WHOLE key must match the
# pattern, not only its beginning: it is a key in a file here and in
# localStorage on the page, and "never a risky key" means no page can put
# anything under this prefix but a language's code and a pass's key.
LEVEL_PREFIX = "bk_lvl:"
# matched with fullmatch, never match: a `$` would let "bk_lvl:fa:vocal\n" through
LEVEL_KEY = re.compile(r"bk_lvl:[a-z]{2,3}:[a-z][a-z0-9_]{0,15}")
# a level's name: 12 characters at most once trimmed (what a button holds --
# languages.LEVEL_NAME_MAX, which a test holds this to), and EMPTY IS A VALUE:
# it means "the registry's own name again", and it is kept so that the device
# which cleared it is not undone by one that still has the old name
MAX_LEVEL_NAME = 12
MAX_LEVEL_KEYS = 300     # eleven languages of five levels is 55: a ceiling, not a count
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


def follows(key):
    """Is this a setting that follows a person?  The exact keys of KEYS, and
    the level names (LEVEL_KEY); any other is the browser's own business."""
    return isinstance(key, str) and (key in KEYS or LEVEL_KEY.fullmatch(key) is not None)


def _value(key, raw):
    """The value as it is kept, or None when this key cannot hold it -- which
    is refused as a key nobody follows is: nothing is stored."""
    v = _clean(raw)
    if key.startswith(LEVEL_PREFIX):
        return v if len(v) <= MAX_LEVEL_NAME else None
    if key == "bk_cont":
        return v if v in ("0", "1") else None
    return v


def set_settings(changes, by=""):
    """`changes` is {key: {"v": value, "at": seconds}}; a key nobody follows is
    ignored, a value its key cannot hold is ignored (a level's name over 12
    characters, a "keep going" that is neither 0 nor 1), and an older change
    never overwrites a newer one."""
    doc = _read()
    now = time.time()
    said = {}
    for key, val in (changes or {}).items():
        if not follows(key) or not isinstance(val, dict):
            continue
        v = _value(key, val.get("v"))
        if v is None:
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
        if was is None and key.startswith(LEVEL_PREFIX) and \
                sum(1 for k in doc["settings"] if k.startswith(LEVEL_PREFIX)) >= MAX_LEVEL_KEYS:
            continue        # a name already kept may change; a new one past the ceiling may not
        doc["settings"][key] = {"v": v, "at": at, "by": _clean(by, 60)}
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
