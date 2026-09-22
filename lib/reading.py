#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""What somebody has decided about a book's own text: reading.json.

Two decisions live here, both the reader's rather than the annotator's, and
both about PARAGRAPHS:

    {"free": ["1:13"],
     "collapsed": [["1:5", "1:9"]]}

  * `free` -- paragraphs that need not reproduce source/paras/.  The check
    that they do is worth keeping: it is what stops a model, or a careless
    edit of a file, quietly rewriting a book.  But a person editing a chunk in
    the reader may mean it, and then the paragraph is theirs.

    PER PARAGRAPH AND NOT PER CHUNK, because the check is: verify_book.py and
    texwrite both join every chunk under one \\parnum before comparing against
    source/paras/ch<N>_p<NN>.txt, so one chunk departing takes its paragraph
    with it.  A checkbox on a chunk is how it is offered, and what it means is
    said there in those words.

  * `collapsed` -- runs of consecutive paragraphs folded away: the reader does
    not show their text, and the narration skips from the subparagraph before
    the run to the first one after it.

A paragraph is named "<chapter>:<paragraph>": the chapter number a chapter
file carries in its NAME (ch1.tex and ch1b.tex are both chapter 1, which is
how verify_book and texwrite already read them) and the 1-based number of its
\\parnum.  Deliberately not a subkey -- a subkey names a subparagraph and
moves when its text is edited, and these two decisions have to outlive exactly
that.

The file travels with the book (lib/bundle.py carries it beside book.json), so
a collapsed reading and a paragraph somebody has taken charge of arrive with
the edition rather than staying on one machine.
"""
import io
import json
import os

NAME = "reading.json"


def path_for(book_dir):
    return os.path.join(book_dir, NAME)


def key(chapter, para):
    """The name of one paragraph, as this file writes it."""
    return "%d:%d" % (int(chapter), int(para))


def split(k):
    """"1:13" -> (1, 13), or None for anything else."""
    try:
        ch, para = str(k).split(":", 1)
        return int(ch), int(para)
    except (ValueError, AttributeError):
        return None


def load(book_dir):
    """The decisions for this book -> {"free": [...], "collapsed": [[a, b], ...]}.

    A book that has never had any -- which is every book until somebody makes
    one -- reads as empty rather than missing, so every caller can treat the
    two the same.
    """
    out = {"free": [], "collapsed": []}
    try:
        with io.open(path_for(book_dir), encoding="utf-8") as f:
            doc = json.load(f)
    except (OSError, ValueError):
        return out
    if not isinstance(doc, dict):
        return out
    free = doc.get("free")
    if isinstance(free, list):
        out["free"] = [k for k in (str(x) for x in free) if split(k)]
    runs = doc.get("collapsed")
    if isinstance(runs, list):
        for run in runs:
            if (isinstance(run, list) and len(run) == 2
                    and split(str(run[0])) and split(str(run[1]))):
                a, b = str(run[0]), str(run[1])
                out["collapsed"].append([a, b] if split(a) <= split(b) else [b, a])
    out["collapsed"].sort(key=lambda r: split(r[0]))
    return out


def save(book_dir, doc):
    """Write it, or take it away when there is nothing left to say.

    Written beside and renamed, the way every other file this toolbox keeps
    for a book is, so a crash never leaves half a decision.  A book with no
    decisions has no file at all: that is what it looked like before anybody
    made one, and it is what a bundle of it should carry.
    """
    free = sorted({k for k in doc.get("free", []) if split(k)}, key=split)
    runs = sorted([list(r) for r in doc.get("collapsed", [])],
                  key=lambda r: split(r[0]))
    p = path_for(book_dir)
    if not free and not runs:
        try:
            os.unlink(p)
        except OSError:
            pass
        return {"free": [], "collapsed": []}
    out = {"free": free, "collapsed": runs}
    tmp = p + ".tmp"
    with io.open(tmp, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, p)
    return out


# ---------------------------------------------------------------- the free ones
def is_free(book_dir, chapter, para):
    """Has this paragraph been taken charge of?"""
    if chapter is None or para is None:
        return False
    return key(chapter, para) in set(load(book_dir)["free"])


def set_free(book_dir, chapter, para, on):
    """Mark the paragraph as departing from its source, or stop."""
    doc = load(book_dir)
    k = key(chapter, para)
    have = set(doc["free"])
    if on:
        have.add(k)
    else:
        have.discard(k)
    doc["free"] = sorted(have, key=split)
    return save(book_dir, doc)


# --------------------------------------------------------------- the folded ones
def in_collapsed(doc, chapter, para):
    """Is this paragraph inside a folded run?  -> the run, or None."""
    here = (int(chapter), int(para))
    for run in doc.get("collapsed", []):
        a, b = split(run[0]), split(run[1])
        if a and b and a <= here <= b:
            return run
    return None


def collapse(book_dir, first, last, on=True):
    """Fold a run of paragraphs away, or unfold the run at `first`.

    Folding a run that touches or overlaps one already folded joins the two:
    two runs that meet are one run, and leaving them apart would mean two bars
    in the page with nothing between them -- or, where one run contains
    another, a run the page can never draw a bar for while the sheet goes on
    offering to unfold it.

    OVERLAPPING and TOUCHING are not the same question.  Overlapping is about
    the text and not about chapters at all: a run may begin in one chapter and
    end in the next, since the sheet offers every paragraph in the book.
    Touching is about chapters, and is the one thing this file cannot answer
    on its own -- it does not know how many paragraphs a chapter has, so the
    last of chapter 1 and the first of chapter 2 are adjacent only if
    something says so, and nothing here does.  So ends that share a chapter
    are asked whether they are one apart; ends that do not are not.
    """
    doc = load(book_dir)
    a, b = split(first), split(last)
    if not a or not b:
        raise ValueError("a paragraph is named <chapter>:<paragraph>")
    if b < a:
        a, b = b, a
    if not on:
        doc["collapsed"] = [r for r in doc["collapsed"]
                            if not (split(r[0]) <= a <= split(r[1]))]
        return save(book_dir, doc)
    # WHAT COUNTS AS ONE RUN.  Two questions, and only one is about chapters.
    # OVERLAP never is: ["1:5","2:3"] and ["1:7","1:8"] are one stretch of text
    # however the chapter boundary falls, and the sheet offers every paragraph
    # in the book, so a run crossing one is ordinary rather than exotic.
    # Keeping them apart drew a second bar over text already folded and, worse,
    # hid the nested run from foldedRun while the sheet still offered to unfold
    # it -- so pressing unfold left the text folded.  TOUCHING is the chapter
    # question: this file cannot know how many paragraphs a chapter has, so the
    # last of chapter 1 and the first of chapter 2 are adjacent only if
    # something says so, and nothing here does.  The +/-1 test is therefore
    # asked only of ends that share a chapter.  Repeated until nothing more
    # joins, because swallowing one run can bring the next within reach.
    lo, hi = a, b
    keep = [list(r) for r in doc["collapsed"]]
    moved = True
    while moved:
        moved, rest = False, []
        for run in keep:
            ra, rb = split(run[0]), split(run[1])
            touches = ((ra[0] == hi[0] and ra == (hi[0], hi[1] + 1))
                       or (rb[0] == lo[0] and rb == (lo[0], lo[1] - 1)))
            if (ra <= hi and lo <= rb) or touches:
                lo, hi, moved = min(lo, ra), max(hi, rb), True
            else:
                rest.append(run)
        keep = rest
    keep.append([key(*lo), key(*hi)])
    doc["collapsed"] = keep
    return save(book_dir, doc)
