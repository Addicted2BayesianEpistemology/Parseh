#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Fold a video's parts/ batches into annotations.json, ONCE, as it is added.

    python3 lib/merge_parts.py videos/<folder>/<id>

parts/ IS RETIRED (2026-09-23).  It was a second source of truth for the
same glosses, and the player writes annotations.json only: a video glossed,
coloured or corrected in the player and then merged again came back as the
batches had left it, and the loss was silent.  So the batches now live only
while a video is being added -- the add page (ytpages.api_add), the old-format
importer and the by-hand pipeline in PROMPT.md all write them, run this
once, and drop them; nothing on the shelf carries a parts/ any more, and
annotations.json is the video's only annotation from the moment it arrives.

Because a video added before that date still has its batches on disk, this
refuses to rebuild over an annotations.json that is NEWER than they are,
and says what that would have thrown away (`_lost`).  That refusal is the
whole of the guard: a merge whose result is the file that is already there
loses nothing and is allowed, so re-deriving a video to check it still
works.

The directory may sit in any language folder (videos/persian/<id>,
videos/japanese/<id>); the language is video.json's "language", default
Persian, and it decides which captions are plain (see parse_transcript).

Each  parts/*.json  is a JSON ARRAY of segments in caption order:

    [ {"start": 27, "chunks": [ {"fa": "...", "tr": "...",
                                 "voc": "...", "en": "..."}, ... ]}, ... ]

The caption TEXT is never typed into a part.  It is taken from
transcript.txt -- the pasted transcript is the single source of truth,
so a part cannot drift from it -- and each part's declared starts are
matched against the transcript's timestamps, which catches a batch that
skipped or doubled a caption before anything is written.

PLAIN captions (the video's own English framing, for a script language:
see parse_transcript) are not annotated at all.  They are filled in here straight from the
transcript, so the parts hold only what actually wants glossing, and a
part is never asked to echo an English sentence it cannot improve on.
Chapter headings come from the transcript the same way.

Then run check_annotations.py; this script only assembles.
"""
import glob
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_annotations import lang_code, parse_transcript

# THE SHAPE OF parts/*.json, the one this docstring draws, as a number
# (lib/version.py FORMATS).  The add page (ytpages.py) and import_old_video.py
# write batches in it, captimes.py moves a start in the ones an older video
# still carries, and this is what reads them, so the number is kept here; the
# files carry none.  RAISE IT when the shape changes so that the Parseh
# before this one would read a batch wrong.
PARTS_FORMAT = 1

# A second of slack before one file is called newer than another.  Some
# filesystems keep a whole second only, and the pipeline writes the batches
# and the annotations in one breath; without the slack a video added in that
# same second could not be re-derived at all.
SLACK = 1.0


def _when(path):
    """A file's own clock, as somebody reading the refusal would write it."""
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(path)))


def _differing_keys(old, new):
    """The names of what one segment says and the other does not.

    Names and not a count, because "the file would change" is nothing
    anybody can act on.  What the player writes into annotations.json and
    the batches never had has a name -- `col` a colour, `note` an aside,
    `words` a word line, `en` a gloss somebody corrected -- so the refusal
    can say which, and the person can go and look at it.
    """
    old = old if isinstance(old, dict) else {}
    new = new if isinstance(new, dict) else {}
    out = set(k for k in set(old) | set(new)
              if k != "chunks" and old.get(k) != new.get(k))
    oc, nc = old.get("chunks") or [], new.get("chunks") or []
    if len(oc) != len(nc):
        out.add("chunks")
    for a, b in zip(oc, nc):
        a = a if isinstance(a, dict) else {}
        b = b if isinstance(b, dict) else {}
        out |= set(k for k in set(a) | set(b) if a.get(k) != b.get(k))
    return out


def _lost(apath, out):
    """What rebuilding would take out of the annotations.json already there:
    (the starts of the captions that differ, the names of the fields).  An
    empty list of captions means the rebuild is the file itself."""
    try:
        with open(apath, encoding="utf-8") as f:
            old = json.load(f)
    except (OSError, ValueError):
        # unreadable is not the same as identical: a file nobody here can
        # parse is exactly the kind that should not be written over blind
        return None, []
    osegs = old.get("segments") if isinstance(old, dict) else None
    if not isinstance(osegs, list):
        return None, []
    nsegs = out["segments"]
    at, keys = [], set()
    for i in range(max(len(osegs), len(nsegs))):
        o = osegs[i] if i < len(osegs) else None
        n = nsegs[i] if i < len(nsegs) else None
        if o == n:
            continue
        at.append(o.get("start") if isinstance(o, dict) else
                  (n.get("start") if isinstance(n, dict) else "?"))
        keys |= _differing_keys(o, n)
    return at, sorted(keys)


def _stamp(sec):
    """A caption's start as the player's own timeline shows it."""
    try:
        return "%d:%02d" % (int(float(sec)) // 60, int(float(sec)) % 60)
    except (TypeError, ValueError):
        return str(sec)


def guard(vdir, parts, out):
    """(the sentence to refuse with, the one to print first) -- both "" when
    this merge may go ahead with nothing to say about it.

    The one thing parts/ can still do harm with: a video added before the
    folder was retired, whose annotations have since been edited in the
    player, merged again by a hand following an older page of the guide.
    """
    apath = os.path.join(vdir, "annotations.json")
    if not os.path.exists(apath):
        return "", ""
    at, keys = _lost(apath, out)
    if at == []:
        return "", ""                 # nothing to lose: the same file again
    if at is None:
        what = "  it cannot be read here, so what it holds is unknown"
    else:
        what = ("  %d caption(s) differ, at %s%s%s"
                % (len(at), ", ".join(_stamp(s) for s in at[:8]),
                   " …" if len(at) > 8 else "",
                   (", in: " + ", ".join(keys)) if keys else ""))
    newest = max(os.path.getmtime(p) for p in parts)
    if os.path.getmtime(apath) <= newest + SLACK:
        # The batches are the later word, so this is the by-hand pipeline
        # doing what it has always done -- but it is still writing over
        # somebody's file, and the one thing that was ever wrong with that
        # was doing it without a word.
        return "", ("note: annotations.json was there and is being replaced\n"
                    "%s" % what)
    return ("annotations.json is newer than the batches in parts/, and it is "
            "not what they would build.\n"
            "  annotations.json  %s\n"
            "  newest batch      %s\n"
            "%s\n"
            "Rebuilding would throw that away.  parts/ is retired: the "
            "batches are folded in once, while a video is being added, and "
            "after that annotations.json is the video's only annotation -- "
            "the player writes it, and nothing rebuilds it.  Move "
            "annotations.json aside if you really do mean to go back to the "
            "batches."
            % (_when(apath), _when(max(parts, key=os.path.getmtime)),
               what)), ""


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    vdir = sys.argv[1].rstrip("/")
    tpath = os.path.join(vdir, "transcript.txt")
    if not os.path.exists(tpath):
        sys.exit("no transcript.txt in %s" % vdir)
    meta = {}
    try:
        with open(os.path.join(vdir, "video.json"), encoding="utf-8") as f:
            meta = json.load(f)
    except (OSError, ValueError):
        pass
    # the registry code, as written (a malformed value spelled out as a
    # string); parse_transcript takes an unknown or missing one as the
    # default (Persian), and the checker warns about it
    lang = lang_code(meta.get("language")) or "fa"
    captions = parse_transcript(tpath, lang)
    if not captions:
        sys.exit("transcript.txt parsed to zero captions")
    want = [c for c in captions if not c["plain"]]

    parts = sorted(glob.glob(os.path.join(vdir, "parts", "*.json")))
    if not parts:
        sys.exit("no parts/*.json in %s" % vdir)
    annotated = []
    for p in parts:
        with open(p, encoding="utf-8") as f:
            batch = json.load(f)
        if not isinstance(batch, list):
            sys.exit("%s: not a JSON array" % p)
        annotated.extend(batch)
        print("%s: %d segments" % (os.path.basename(p), len(batch)))

    if len(annotated) != len(want):
        sys.exit("parts carry %d segments but %d captions want glossing\n"
                 "(%d of the %d captions are plain and are filled in from "
                 "the transcript)"
                 % (len(annotated), len(want),
                    len(captions) - len(want), len(captions)))
    for i, (sg, cap) in enumerate(zip(annotated, want)):
        if sg.get("start") != cap["start"]:
            sys.exit("annotated segment %d: part says start %s, transcript "
                     "says %s\n(a batch has skipped or doubled a caption)"
                     % (i, sg.get("start"), cap["start"]))

    segs, it = [], iter(annotated)
    for cap in captions:
        if cap["plain"]:
            sg = {"start": cap["start"], "plain": True}
        else:
            sg = dict(next(it))
        sg["text"] = cap["text"]
        if cap["chapter"]:
            sg["chapter"] = cap["chapter"]
        # a stable key order, so a rebuilt file diffs cleanly
        segs.append({k: sg[k] for k in
                     ("start", "chapter", "plain", "text", "chunks")
                     if k in sg})

    out = {"video": meta.get("id", os.path.basename(vdir)),
           "language": lang,
           "segments": segs}
    apath = os.path.join(vdir, "annotations.json")
    # The batches are dropped by whoever is ADDING the video, once this and
    # check_annotations have both passed -- not here.  A merge that the check
    # then turns away has to be mendable, and it is only mendable while the
    # batches it was built from are still on disk.
    no, note = guard(vdir, parts, out)
    if no:
        sys.exit(no)
    if note:
        print(note)
    with open(apath, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("wrote %s: %d captions (%d glossed, %d plain)"
          % (apath, len(segs), len(want), len(captions) - len(want)))
    # Not a word here about dropping the batches afterwards, though PROMPT.md
    # asks for it: this output is quoted back on the add page ("what the
    # pipeline said"), where the page has already done it, and no page of
    # this toolbox hands somebody a command to type.
    print("now run:  python3 lib/check_annotations.py %s" % vdir)


if __name__ == "__main__":
    main()
