# SPDX-License-Identifier: GPL-3.0-or-later
"""A few rough, friendly numbers for Settings -> About: how long Parseh has
kept somebody company, how many cards they have answered, how many videos
and books are on their shelves.

NOTHING IS RECORDED FOR THIS.  Every number is read off what is already kept:
the answers in each deck's schedule/<id>.json (decks.py), a video's video.json
(its length and the day it was added), a book's book.json.  So there is no
stored format, nothing to migrate and nothing to forget to update, and the
numbers are honestly approximate: a deck that was deleted took its answers
with it, and the hours are the videos' LENGTHS, not the time somebody spent
watching them (Parseh does not time that, and this does not pretend to).

Standard library only, and no other Parseh module: it is handed the folder of
the install (`root`), so a test can point it at a temporary tree.  A shelf
with thousands of cards is read for at most `budget` seconds; what was not
reached is said ("at least") rather than waited for.
"""
import json
import os
import time
from datetime import date

MONTHS = ("January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December")
# the length of a feature film, for "about N films' worth" (no more precise than that)
FILM_HOURS = 1.6
PACK = 52          # a pack of playing cards


def _json(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _dirs(path):
    """The sub-folders of `path` that are not dot folders (.trash is never content)."""
    try:
        names = sorted(os.listdir(path))
    except OSError:
        return []
    return [n for n in names if not n.startswith(".") and os.path.isdir(os.path.join(path, n))]


def _day(text):
    """The calendar day an ISO stamp or date begins with, or None."""
    try:
        return date.fromisoformat(str(text)[:10])
    except ValueError:
        return None


def seconds(text):
    """`35`, `0:35`, `75:20` or `1:15:20` as seconds; 0 for anything else."""
    try:
        parts = [int(p) for p in str(text).strip().split(":")]
    except ValueError:
        return 0
    if not 1 <= len(parts) <= 3 or any(p < 0 for p in parts):
        return 0
    total = 0
    for p in parts:
        total = total * 60 + p
    return total


def collect(root, budget=1.5, clock=time.monotonic):
    """{"answers", "decks", "exercises", "videos", "video_seconds", "books",
    "folders": language folders holding anything, "since": the earliest day
    anything here says, or None, "complete": False when the time ran out}."""
    deadline = clock() + budget
    out = {"answers": 0, "decks": 0, "exercises": 0, "videos": 0, "video_seconds": 0,
           "books": 0, "folders": [], "since": None, "complete": True}
    seen = set()
    first = []

    def note(day, folder=None):
        if day is not None:
            first.append(day)
        if folder:
            seen.add(folder)

    def late():
        if clock() > deadline:
            out["complete"] = False
            return True
        return False

    # books: books/<folder>/<slug>/book.json, and the layout before languages, books/<slug>/book.json
    books = os.path.join(root, "books")
    for name in _dirs(books):
        d = os.path.join(books, name)
        if os.path.isfile(os.path.join(d, "book.json")):
            out["books"] += 1
            continue
        for sub in _dirs(d):
            if os.path.isfile(os.path.join(d, sub, "book.json")):
                out["books"] += 1
                seen.add(name)

    # videos: youtube/videos/<folder>/<id>/video.json
    videos = os.path.join(root, "youtube", "videos")
    for folder in _dirs(videos):
        for vid in _dirs(os.path.join(videos, folder)):
            if late():
                break
            meta = _json(os.path.join(videos, folder, vid, "video.json"))
            if not isinstance(meta, dict):
                continue
            out["videos"] += 1
            out["video_seconds"] += seconds(meta.get("duration"))
            note(_day(meta.get("added")), folder)

    # decks: exercises/<folder>/<slug>/deck.json, items/<id>.json, schedule/<id>.json
    decks = os.path.join(root, "exercises")
    for folder in _dirs(decks):
        for slug in _dirs(os.path.join(decks, folder)):
            d = os.path.join(decks, folder, slug)
            meta = _json(os.path.join(d, "deck.json"))
            if not isinstance(meta, dict):
                continue
            out["decks"] += 1
            note(_day(meta.get("created")), folder)
            try:
                out["exercises"] += sum(1 for n in os.listdir(os.path.join(d, "items")) if n.endswith(".json"))
                schedules = [n for n in os.listdir(os.path.join(d, "schedule")) if n.endswith(".json")]
            except OSError:
                continue
            for n in schedules:
                if late():
                    break
                sched = _json(os.path.join(d, "schedule", n))
                history = sched.get("history") if isinstance(sched, dict) else None
                if not isinstance(history, list) or not history:
                    continue
                out["answers"] += len(history)
                if isinstance(history[0], dict):
                    note(_day(history[0].get("at")))
    out["folders"] = sorted(seen)
    out["since"] = min(first).isoformat() if first else None
    return out


# ------------------------------------------------------------------ words

def number(n):
    return "{:,}".format(int(n))


def long_date(iso):
    d = _day(iso)
    return "%d %s %d" % (d.day, MONTHS[d.month - 1], d.year) if d else ""


def span(hours):
    """About how long, in the words a person would use."""
    if hours < 1:
        minutes = int(round(hours * 60))
        return "about %d minute%s" % (minutes, "" if minutes == 1 else "s") if minutes else "less than a minute"
    if hours < 10:
        h = round(hours * 2) / 2
        return "about %s hour%s" % (("%g" % h), "" if h == 1 else "s")
    return "about %d hours" % int(round(hours))


def answers_remark(n):
    if n <= 0:
        return "None yet: the first is waiting in a deck."
    if n < PACK:
        return "A good start."
    return "As many as %s pack%s of playing cards." % (number(n // PACK), "" if n // PACK == 1 else "s")


def videos_remark(count, secs):
    if not count:
        return "Add one from Videos."
    hours = secs / 3600.0
    if not secs:
        return "Their lengths are not known."
    line = span(hours)
    films = hours / FILM_HOURS
    if films >= 2:
        line += ", roughly %d films' worth" % int(round(films))
    return line[0].upper() + line[1:] + " of video."


def tiles(s, names=None):
    """The four numbers the page shows: [(big number, what it counts, a small remark)]."""
    more = "" if s["complete"] else "at least "
    names = names or {}
    langs = [names.get(f, f) for f in s["folders"]]
    return [
        (more + number(s["answers"]), "card%s answered" % ("" if s["answers"] == 1 else "s"), answers_remark(s["answers"])),
        (more + number(s["videos"]), "video%s on the shelf" % ("" if s["videos"] == 1 else "s"),
         videos_remark(s["videos"], s["video_seconds"])),
        (number(s["books"]), "book%s on the shelf" % ("" if s["books"] == 1 else "s"),
         ("In %d language%s." % (len(langs), "" if len(langs) == 1 else "s")) if s["books"] and langs else
         "Make one from Books."),
        (number(s["decks"]), "deck%s of exercises" % ("" if s["decks"] == 1 else "s"),
         ("Holding %s exercise%s." % (number(s["exercises"]), "" if s["exercises"] == 1 else "s")) if s["decks"] else
         "Make one in the studio."),
    ]


def since_line(s, today=None):
    """`Parseh has been with you since 3 September 2026 (32 days).`, or ''."""
    d = _day(s["since"]) if s["since"] else None
    if not d:
        return ""
    days = ((today or date.today()) - d).days
    if days < 0:
        return ""
    how = "today" if days == 0 else ("1 day" if days == 1 else "%s days" % number(days))
    return ("Parseh has been with you since %s%s." % (long_date(s["since"]), "" if days == 0 else " (" + how + ")")
            if days else "Your first day with Parseh is today.")
