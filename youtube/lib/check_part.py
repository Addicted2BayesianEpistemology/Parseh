#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check ONE annotation batch, before the whole video is finished.

    python3 lib/check_part.py videos/<folder>/<id> parts/03.json

merge_parts.py can only run once every batch exists, and
check_annotations.py only after that -- but a batch is written by one
pass over one slice of the transcript, and that pass wants to know
whether it got the words right while it still remembers them.  So this
checks a single part against transcript.txt, on its own:

  * it is a JSON array of {start, chunks}
  * it sits in the transcript as one contiguous RUN of captions, with
    none skipped, doubled or invented
  * PLAIN captions are not in it (merge_parts fills those in)
  * FIDELITY: each segment's chunks, joined with the language's word
    separator (a space; nothing for Japanese), give the caption back word
    for word (the language's marks -- harakat -- stripped from both sides)
  * every chunk carries the fields its language requires (the meaning,
    the transliteration where the language wants one, the kana where it
    has a reading -- check_annotations.check_chunk, from the registry)
  * a chunk's word line, where it carries one, gives its text back
    (check_chunk again, told video.json's "reorders")

Exit code 0 only when there are no errors.  Standard library only.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_annotations import check_chunk, lang_of, norm, parse_transcript


def align(starts, want):
    """Where a batch sits in the transcript, or None.

    Matched as a contiguous run, never by looking a start up in a dict:
    two captions can share a timestamp (a laugh and the gasp after it,
    both in the same displayed second), and a dict keyed by start would
    silently drop one of them and check the batch against the wrong text.
    """
    n = len(starts)
    for p in range(len(want) - n + 1):
        if all(want[p + k]["start"] == starts[k] for k in range(n)):
            return p
    return None


def diagnose(starts, want, plain_starts, err):
    """Say, as precisely as possible, why a batch does not line up."""
    if starts[0] in plain_starts:
        err("the caption at %s is plain (not the target language) -- leave "
            "it out, merge_parts fills it in" % starts[0])
        return
    cands = [p for p in range(len(want)) if want[p]["start"] == starts[0]]
    if not cands:
        err("no caption starts at %s in transcript.txt -- this batch does "
            "not begin on a caption" % starts[0])
        return
    best, best_k = cands[0], -1
    for p in cands:
        k = 0
        while (k < len(starts) and p + k < len(want)
               and want[p + k]["start"] == starts[k]):
            k += 1
        if k > best_k:
            best, best_k = p, k
    if best + best_k >= len(want):
        err("the batch runs past the end of the transcript after %d captions"
            % best_k)
        return
    expected = want[best + best_k]["start"]
    got = starts[best_k]
    err("entry %d has start %s, but the caption after %s is at %s -- %s"
        % (best_k, got, starts[best_k - 1] if best_k else "the start",
           expected,
           "a caption has been skipped" if got > expected
           else "a caption is repeated or out of order"))
    if expected in plain_starts:
        err("(the caption at %s is plain -- it must NOT be in the batch)"
            % expected)


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    vdir, ppath = sys.argv[1].rstrip("/"), sys.argv[2]
    if not os.path.isabs(ppath) and not os.path.exists(ppath):
        # accept "parts/03.json", "03.json" or a path from anywhere
        for cand in (os.path.join(vdir, ppath),
                     os.path.join(vdir, "parts", os.path.basename(ppath))):
            if os.path.exists(cand):
                ppath = cand
                break
    meta = {}
    try:
        with open(os.path.join(vdir, "video.json"), encoding="utf-8") as f:
            meta = json.load(f)
    except (OSError, ValueError):
        pass
    lang = lang_of(meta.get("language"))
    reorders = bool(meta.get("reorders"))
    captions = parse_transcript(os.path.join(vdir, "transcript.txt"), lang)
    want = [c for c in captions if not c["plain"]]
    plain_starts = {c["start"] for c in captions if c["plain"]}

    errors, warnings = [], []
    err, warn = errors.append, warnings.append
    name = os.path.basename(ppath)
    try:
        with open(ppath, encoding="utf-8") as f:
            batch = json.load(f)
    except OSError as e:
        sys.exit("cannot read %s (%s)" % (ppath, e))
    except ValueError as e:
        sys.exit("ERROR: %s is not valid JSON: %s" % (ppath, e))
    if not isinstance(batch, list) or not batch:
        sys.exit("ERROR: %s must be a non-empty JSON array" % ppath)

    shape_ok = True
    for i, sg in enumerate(batch):
        if not isinstance(sg, dict):
            err("%s [%d]: not an object" % (name, i))
            shape_ok = False
            continue
        for field in sg:
            if field not in ("start", "chunks"):
                warn("%s [%d]: unexpected field %r (text, plain and chapter "
                     "are filled in by merge_parts)" % (name, i, field))
        if not isinstance(sg.get("start"), (int, float)):
            err("%s [%d]: missing or non-numeric start" % (name, i))
            shape_ok = False

    base = None
    if shape_ok:
        starts = [sg["start"] for sg in batch]
        base = align(starts, want)
        if base is None:
            diagnose(starts, want, plain_starts, err)

    nch = nw = 0
    if base is not None:
        for i, sg in enumerate(batch):
            cap = want[base + i]
            where = "%s [%d] (start %s)" % (name, i, sg.get("start"))
            chunks = sg.get("chunks")
            if not isinstance(chunks, list) or not chunks:
                err("%s: no chunks" % where)
                continue
            for j, ch in enumerate(chunks):
                if not isinstance(ch, dict):
                    err("%s chunk %d: not an object" % (where, j))
                    continue
                nw += check_chunk(ch, "%s chunk %d" % (where, j), err, warn, lang,
                                  reorders=reorders)
            nch += len(chunks)
            joined = norm(lang.word_sep.join(
                (ch.get("fa") or "") if isinstance(ch, dict) else ""
                for ch in chunks), lang)
            cap_norm = norm(cap["text"], lang)
            if joined != cap_norm:
                k = next((n for n, (a, b) in enumerate(zip(joined, cap_norm))
                          if a != b), min(len(joined), len(cap_norm)))
                err("%s: chunks do not reproduce the caption\n"
                    "    caption: ...%s...\n"
                    "    chunks:  ...%s..."
                    % (where, cap_norm[max(0, k-25):k+25],
                       joined[max(0, k-25):k+25]))

    for w in warnings:
        print("warning: %s" % w)
    for e in errors:
        print("ERROR: %s" % e)
    where = ("captions %d..%d" % (base, base + len(batch) - 1)
             if base is not None else "unplaced")
    print("%s: %d captions (%s), %d chunks, %d words -- %d error(s), "
          "%d warning(s)" % (name, len(batch), where, nch, nw,
                             len(errors), len(warnings)))
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
