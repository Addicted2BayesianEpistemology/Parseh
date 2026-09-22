#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Print the captions one batch is responsible for.

    python3 lib/slice_part.py videos/<folder>/<id> <first> <count>

<first> counts from 0 over the captions that WANT GLOSSING -- plain ones
(the video's own English, for a script language; video.json's "language"
decides) are not in the numbering, because merge_parts
fills those in from the transcript and no batch should touch them.

The output is a JSON array of {i, start, text}: the authoritative text to
chunk, straight from transcript.txt, so a batch never works from text
that has been retyped or passed through a prompt.  With no <first>, it
prints how the whole video divides up instead.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_annotations import parse_transcript


def load(vdir):
    meta = {}
    try:
        with open(os.path.join(vdir, "video.json"), encoding="utf-8") as f:
            meta = json.load(f)
    except (OSError, ValueError):
        pass
    caps = parse_transcript(os.path.join(vdir, "transcript.txt"),
                           meta.get("language") or "fa")
    return [c for c in caps if not c["plain"]], caps


def main():
    if len(sys.argv) not in (2, 3, 4):
        sys.exit(__doc__)
    vdir = sys.argv[1].rstrip("/")
    want, caps = load(vdir)
    if len(sys.argv) == 2:
        print("%s: %d captions, %d want glossing, %d plain"
              % (os.path.basename(vdir), len(caps), len(want),
                 len(caps) - len(want)))
        return
    first = int(sys.argv[2])
    count = int(sys.argv[3]) if len(sys.argv) == 4 else len(want) - first
    part = want[first:first + count]
    if not part:
        sys.exit("no captions at %d..%d (only %d want glossing)"
                 % (first, first + count, len(want)))
    print(json.dumps([{"i": first + n, "start": c["start"], "text": c["text"]}
                      for n, c in enumerate(part)],
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
