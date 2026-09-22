#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Assemble videos/<folder>/<id>/annotations.json from its parts/ batches.

    python3 lib/merge_parts.py videos/<folder>/<id>

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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_annotations import lang_code, parse_transcript


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
    with open(apath, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("wrote %s: %d captions (%d glossed, %d plain)"
          % (apath, len(segs), len(want), len(captions) - len(want)))
    print("now run:  python3 lib/check_annotations.py %s" % vdir)


if __name__ == "__main__":
    main()
