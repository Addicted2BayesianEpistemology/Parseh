#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""The chunks a person flagged to REVIEW LATER (a0.5.0).

Reading a book or watching a video, a person flags a chunk and goes on: the
pace is not broken, and the flashcard -- or the review -- comes later.  The
flags are listed in a sidebar beside the book or the video (lib/later.js), and
on a page of their own across every book and video (/later/,
lib/laterpage.py).

THE PERSON'S, NOT A BOOK'S (the owner, 2026-10-06).  A flag follows the person
from the phone to the computer, so it is kept by the toolbox like the reading
place is (lib/prefs.py), under a third top-level key of the same file:

    config/prefs.json
    {"settings": {...}, "places": {...},
     "later": {"items": {
        "later:book:/books/english/three-clocks/reader/:1.1-1ac09deff425:2:1x9k3": {
            "id": "later:book:/books/english/three-clocks/reader/:1.1-1ac09deff425:2:1x9k3",
            "kind": "book", "ref": "/books/english/three-clocks/reader/",
            "lang": "en", "glossLang": "fa", "title": "Three clocks",
            "at": 1758531600.0, "by": "Android phone · Chrome",
            "where": {"sub": "1.1-1ac09deff425", "k": 2, "para": "1:1",
                      "label": "1.1", "chapter": "Chapter 1", "t": 12.5},
            "text": "wound the clock", "kana": "", "tr": "", "en": "...",
            "voc": "", "sentence": "..."},
        "later:video:street-market-a1b2c3:2:1:9fz": {
            "kind": "video", "ref": "street-market-a1b2c3", "at": ...,
            "where": {"start": 2.0, "j": 1, "text": "The market opens early."}, ...},
        "later:book:...": {"gone": 1758540000.0, "kind": "book", "ref": "..."}   # a tombstone
     }}}

NEVER IN A BOOK, NEVER IN A BUNDLE.  The file is this machine's and no book's:
it is not in lib/bundle.py's allowlist, so a book handed on carries the
edition and not somebody's flags.

NO FORMAT NUMBER (lib/version.py FORMATS, tests/test_version.py).  `later` is a
key the older Parseh does not know, and prefs._read keeps every key it does
not know and prefs._write writes the whole document back: an older Parseh
reading this file ignores the flags and, writing, keeps them -- "a field
added that an older reader simply ignores is not such a change" -- so
prefs.STORE_FORMAT stays 1.  (The older Parseh does answer the flags to every
page at load, as part of /__prefs, which is only heavy and never wrong; this
one answers them at their own door, /__later.)

ONE RECORD IS ONE CHUNK.  The id is deterministic -- the kind, the book's
reader path or the video's id, where the chunk is, and a short hash of its
text, built by lib/later.js -- so a chunk flagged on two devices is ONE
record, and what each device sends is an operation on an id.

THE LAST CHANGE WINS, per id, by the moment it was made (`at`), as for the
settings in lib/prefs.py:
  * an `add` replaces a record of the same id that is not newer, revives a
    tombstone it is newer than, and is ignored by one that is as old or
    newer -- so a device that was away and still holds a chunk somebody
    removed in the meantime cannot bring it back;
  * a `remove` leaves a TOMBSTONE {gone: at, kind, ref}, kept for 90 days
    and dropped by the first write after that;
  * the flags are capped at 5000, the oldest dropped, and every text is
    clamped, so that a file made for a person's own use cannot grow without
    end.

The whole of a request is checked before any of it is applied: a body that
is wrong is refused in words and changes nothing.  Every read-change-write
holds prefs.LOCK, the one lock of the file.
"""
import math
import re
import time

import prefs

KINDS = ("book", "video")
MAX_LIVE = 5000                    # the flags, oldest dropped past this
MAX_TOMBS = 20000                  # and the tombstones, for a client that removes without end
TOMB_SECONDS = 90 * 86400          # how long a removal is remembered
MAX_OPS = 1000                     # changes in one request: far more than a person makes
FUTURE = 60.0                      # a clock set wrong, or a value from the future: taken as at most this ahead

# every limit is in characters, after the whitespace has been squeezed
LIMIT = {"id": 300, "text": 600, "other": 600, "voc": 1200, "sentence": 800,
         "by": 60, "label": 80, "chapter": 300, "sub": 200, "para": 40}

# THE SHAPES, written once and read by lib/later.js's own checks: a reader's
# path as the toolbox serves it, and a video's id as the player's page is
# addressed (ytpages: an 11-character YouTube id, or a local film's name)
_SEG = r"[A-Za-z0-9][A-Za-z0-9._-]{0,80}"
BOOK_REF = re.compile(r"^/books/(?:%s/){1,2}reader/$" % _SEG)
VIDEO_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,120}$")
LANG = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,15}$")
KEYPART = re.compile(r"^[A-Za-z0-9._:@%+=~-]*$")        # a subparagraph's key, a paragraph's number
# an id: later:<kind>:<ref>:<where>:<k or j>:<hash>; the ref is told apart
# from the rest by its own shape, which has no colon in it, and is the shape
# of the kind it follows
ID = re.compile(r"^later:(?:(book):(/books/(?:%s/){1,2}reader/)|(video):([A-Za-z0-9][A-Za-z0-9._-]{0,120})):"
                r"[A-Za-z0-9_.:/@%%+=~-]*$" % _SEG)
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


# ----------------------------------------------------------------- checking
def _text(v, limit, lines=False):
    """A string squeezed and cut to `limit`: one line, or -- for a vocabulary
    line and a sentence -- the lines it had.  What is not text is nothing."""
    if isinstance(v, bool) or not isinstance(v, (str, int, float)):
        return ""
    s = str(v).replace("\r\n", "\n").replace("\r", "\n")
    s = _CONTROL.sub("", s)
    if lines:
        s = "\n".join(x for x in (" ".join(l.split()) for l in s.split("\n")) if x)
    else:
        s = " ".join(s.split())
    return s[:limit]


def _number(v, lo, hi, default):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return default
    if isinstance(v, bool) or not math.isfinite(x):
        return default
    return min(max(x, lo), hi)


def _whole(v, hi):
    return int(_number(v, 0, hi, 0))


def _key(v, limit):
    s = v if isinstance(v, str) else ""
    s = s.strip()[:limit]
    return s if KEYPART.match(s) else ""


def check_ref(ref, kind=None):
    """The reader's path or the video's id, or ValueError in words."""
    ref = ref if isinstance(ref, str) else ""
    if (kind in (None, "book")) and BOOK_REF.match(ref):
        return ref
    if (kind in (None, "video")) and VIDEO_REF.match(ref):
        return ref
    raise ValueError("a place is a book's reader path (/books/<folder>/<slug>/reader/) "
                     "or a video's id" + ("" if kind is None else ", and this one is neither"))


def _parts(rid):
    m = ID.match(rid) if isinstance(rid, str) and len(rid) <= LIMIT["id"] else None
    if not m:
        raise ValueError("that is not a flag's id (later:<book or video>:<its place>:...)")
    return (m.group(1) or m.group(3)), (m.group(2) or m.group(4))


def _where(kind, w):
    w = w if isinstance(w, dict) else {}
    if kind == "book":
        t = w.get("t")
        return {"sub": _key(w.get("sub"), LIMIT["sub"]), "k": _whole(w.get("k"), 100000),
                "para": _key(w.get("para"), LIMIT["para"]),
                "label": _text(w.get("label"), LIMIT["label"]),
                "chapter": _text(w.get("chapter"), LIMIT["chapter"]),
                "t": None if t is None else _number(t, 0.0, 1e7, None)}
    return {"start": _number(w.get("start"), 0.0, 1e7, 0.0), "j": _whole(w.get("j"), 100000),
            "text": _text(w.get("text"), LIMIT["text"])}


def clean_record(rec, now=None):
    """One flag as it is kept -> a new dict; ValueError, in words, for what
    cannot be one.  Everything that is only too long is cut."""
    now = time.time() if now is None else now
    if not isinstance(rec, dict):
        raise ValueError("a flag is an object")
    kind = rec.get("kind")
    if kind not in KINDS:
        raise ValueError("a flag's kind is 'book' or 'video'")
    ref = check_ref(rec.get("ref"), kind)
    rid = rec.get("id")
    id_kind, id_ref = _parts(rid)
    if (id_kind, id_ref) != (kind, ref):
        raise ValueError("the flag's id belongs to another place than the flag does")
    text = _text(rec.get("text"), LIMIT["text"])
    if not text:
        raise ValueError("a flag has the chunk's text")
    at = _number(rec.get("at"), 0.0, now + FUTURE, now)
    lang, gloss = rec.get("lang"), rec.get("glossLang")
    return {"id": rid, "kind": kind, "ref": ref,
            "lang": lang if isinstance(lang, str) and LANG.match(lang) else "",
            "glossLang": gloss if isinstance(gloss, str) and LANG.match(gloss) else "",
            "title": _text(rec.get("title"), LIMIT["other"]),
            "at": at, "by": _text(rec.get("by"), LIMIT["by"]),
            "where": _where(kind, rec.get("where")),
            "text": text, "kana": _text(rec.get("kana"), LIMIT["other"]),
            "tr": _text(rec.get("tr"), LIMIT["other"]), "en": _text(rec.get("en"), LIMIT["other"]),
            "voc": _text(rec.get("voc"), LIMIT["voc"], lines=True),
            "sentence": _text(rec.get("sentence"), LIMIT["sentence"], lines=True)}


def _clean_op(op, now, by):
    if not isinstance(op, dict):
        raise ValueError("a change is an object: {op: 'add', record} or {op: 'remove', id, at}")
    kind = op.get("op")
    if kind == "add":
        rec = clean_record(op.get("record"), now)
        if not rec["by"]:
            rec["by"] = by
        return ("add", rec)
    if kind == "remove":
        rid = op.get("id")
        _parts(rid)
        return ("remove", {"id": rid, "at": _number(op.get("at"), 0.0, now + FUTURE, now)})
    raise ValueError("a change is 'add' or 'remove'")


# ------------------------------------------------------------------ storing
def _items(doc):
    later = doc.get("later")
    items = later.get("items") if isinstance(later, dict) else None
    return items if isinstance(items, dict) else {}


def _is_tomb(e):
    return isinstance(e, dict) and "gone" in e


def _stamp(e):
    return e["gone"] if _is_tomb(e) else e["at"]


def _sound(rid, e):
    """An entry this Parseh can use.  What a hand-edited file, or a newer
    Parseh, may have left that it cannot is never shown and never counted --
    and never dropped (_tidy)."""
    if not isinstance(e, dict) or not isinstance(rid, str):
        return False
    stamp = e.get("gone") if "gone" in e else e.get("at")
    if isinstance(stamp, bool) or not isinstance(stamp, (int, float)) or not math.isfinite(stamp):
        return False
    if "gone" in e:
        return True
    return e.get("kind") in KINDS and isinstance(e.get("ref"), str) and isinstance(e.get("text"), str)


def _apply(items, op, rec):
    """One change onto `items` -> ('added' | 'removed' | 'ignored', whether
    `items` changed).  The same rule as lib/later.js's applyOp, which replays
    a device's own changes onto what the computer says."""
    if op == "add":
        was = items.get(rec["id"])
        if _sound(rec["id"], was):
            if _is_tomb(was):
                if not rec["at"] > was["gone"]:
                    return "ignored", False
            elif rec["at"] < was["at"] or rec == was:
                return "ignored", False
        items[rec["id"]] = rec
        return "added", True
    rid, at = rec["id"], rec["at"]
    was = items.get(rid)
    if _sound(rid, was):
        if _is_tomb(was):
            if at > was["gone"]:
                was["gone"] = at
                return "ignored", True
            return "ignored", False
        if at < was["at"]:
            return "ignored", False
        items[rid] = {"gone": at, "kind": was["kind"], "ref": was["ref"]}
        return "removed", True
    # a chunk this computer never heard of, removed: the tombstone is what
    # keeps a flag still on its way from another device out
    kind, ref = _parts(rid)
    items[rid] = {"gone": at, "kind": kind, "ref": ref}
    return "ignored", True


def _tidy(items, now):
    """What a write leaves behind: no tombstone older than 90 days, no more
    than MAX_TOMBS of them, no more than MAX_LIVE flags.  An entry this
    Parseh cannot read is left where it is -- it may be a newer Parseh's --
    and is never counted.  -> whether anything was dropped."""
    sound = {k: e for k, e in items.items() if _sound(k, e)}
    drop = [k for k, e in sound.items() if _is_tomb(e) and e["gone"] < now - TOMB_SECONDS]
    gone = set(drop)
    tombs = sorted((e["gone"], k) for k, e in sound.items() if _is_tomb(e) and k not in gone)
    drop += [k for _gone, k in tombs[:max(0, len(tombs) - MAX_TOMBS)]]
    live = sorted((e["at"], k) for k, e in sound.items() if not _is_tomb(e))
    drop += [k for _at, k in live[:max(0, len(live) - MAX_LIVE)]]
    for k in drop:
        del items[k]
    return bool(drop)


def apply_ops(ops, by=""):
    """What a device sends: [{op: 'add', record}, {op: 'remove', id, at}] ->
    {"added": n, "removed": n, "ignored": n, "live": n}.  ValueError, in
    words and naming the change, when any of them cannot be applied; then
    nothing is."""
    if not isinstance(ops, list):
        raise ValueError("ops is a list of changes: {op: 'add', record} and {op: 'remove', id, at}")
    if len(ops) > MAX_OPS:
        raise ValueError("%d changes at once; this door takes %d" % (len(ops), MAX_OPS))
    now = time.time()
    by = _text(by, LIMIT["by"])
    clean = []
    for i, op in enumerate(ops, 1):
        try:
            clean.append(_clean_op(op, now, by))
        except ValueError as e:
            raise ValueError("change %d: %s" % (i, e))
    said = {"added": 0, "removed": 0, "ignored": 0}
    with prefs.LOCK:
        doc = prefs._read()
        items = _items(doc)
        changed = False
        for op, rec in clean:
            result, moved = _apply(items, op, rec)
            said[result] += 1
            changed = changed or moved
        if _tidy(items, now):
            changed = True
        if changed:
            later = doc.get("later") if isinstance(doc.get("later"), dict) else {}
            later["items"] = items
            doc["later"] = later
            prefs._write(doc)
        said["live"] = sum(1 for k, e in items.items() if _sound(k, e) and not _is_tomb(e))
    return said


# ------------------------------------------------------------------ reading
def all_of(ref=None, tombstones=False):
    """The live flags, newest first -- of one book or video when `ref` is
    given -- and, with `tombstones`, the removals too, as {id, gone, kind,
    ref}: a device needs them to know what it must not bring back."""
    out = []
    for rid, e in _items(prefs._read()).items():
        if not _sound(rid, e):
            continue
        if _is_tomb(e):
            if tombstones and (ref is None or e.get("ref") == ref):
                out.append({"id": rid, "gone": e["gone"], "kind": e.get("kind", ""),
                            "ref": e.get("ref", "")})
        elif ref is None or e["ref"] == ref:
            out.append(dict(e, id=rid))
    out.sort(key=lambda e: (-_stamp(e), e["id"]))
    return out


def counts():
    """What there is, per book and video -> {"counts": [{ref, kind, title,
    lang, n, at}, ...], "total": n}, the one flagged last first."""
    per = {}
    for e in all_of():
        c = per.get(e["ref"])
        if c is None:
            # the first met is the newest: it names the book
            c = per[e["ref"]] = {"ref": e["ref"], "kind": e["kind"], "title": e["title"],
                                 "lang": e["lang"], "n": 0, "at": e["at"]}
        c["n"] += 1
    rows = sorted(per.values(), key=lambda c: (-c["at"], c["ref"]))
    return {"counts": rows, "total": sum(c["n"] for c in rows)}


def by_language():
    """The hub's door: how many flags, and how many in each language ->
    ({lang: n}, total)."""
    per, total = {}, 0
    for e in all_of():
        total += 1
        if e["lang"]:
            per[e["lang"]] = per.get(e["lang"], 0) + 1
    return per, total
