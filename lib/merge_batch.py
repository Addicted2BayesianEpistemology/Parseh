#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Fold the per-paragraph annotations into one batch, applying confirmed fixes.

    python3 merge_batch.py <out.json> <fixes.json|-> <p11.json> <p12.json> ... [--book <dir-or-slug>]

`fixes.json` is the confirmed findings, a list of
    {"idx": 11, "chunk_fa": "...", "field": "voc", "proposed": "..."}
Only findings that a sceptic confirmed belong in it -- NOTES section 6.

Every fix must match exactly one chunk; a fix that matches none or several is a
hard error, because silently skipping one would leave the batch half-corrected.

A fix names its chunk by the chunk's text with the language's marks taken
off (the harakat, for Persian and Arabic), so a proof-reader who quotes the
chunk with a different pointing still lands.  Which language: the book's --
--book, else $FRANK_BOOK, else the book the current directory is in.
"""
import argparse
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from books import find_book                                     # noqa: E402
import languages                                                # noqa: E402

LANG = languages.get(languages.DEFAULT)     # set from the book in __main__


def strip(s):
    return LANG.strip(s)


def main(out, fixes_path, paths):
    fixes = [] if fixes_path == "-" else json.load(io.open(fixes_path, encoding="utf-8"))
    paras, applied, missed = [], 0, []

    for p in paths:
        blob = json.load(io.open(p, encoding="utf-8"))
        if "paragraphs" in blob:                       # tolerate the wrapped shape
            blob = blob["paragraphs"][0]
        idx = blob["idx"]
        chunks = [c for s in blob["ann"]["sentences"] for c in s["chunks"]]

        for fx in [f for f in fixes if f["idx"] == idx]:
            want = strip(fx["chunk_fa"]).strip()
            hits = [c for c in chunks if strip(c["fa"]).strip() == want]
            if len(hits) != 1:
                missed.append("p%d: %r matched %d chunks" % (idx, fx["chunk_fa"], len(hits)))
                continue
            field = fx["field"]
            if hits[0].get(field) == fx["proposed"]:
                continue                               # already right, nothing to do
            hits[0][field] = fx["proposed"]
            applied += 1

        paras.append({"idx": idx, "ann": blob["ann"]})
        print("  p%-3d %3d chunks in %2d sentences"
              % (idx, len(chunks), len(blob["ann"]["sentences"])))

    paras.sort(key=lambda x: x["idx"])
    idxs = [p["idx"] for p in paras]
    if idxs != list(range(idxs[0], idxs[0] + len(idxs))):
        sys.exit("paragraphs are not contiguous: %s -- assemble.py will refuse them" % idxs)

    json.dump({"paragraphs": paras}, io.open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    n = sum(len(c["chunks"]) for p in paras for c in p["ann"]["sentences"])
    print("\n%s: paragraphs %d..%d, %d chunks, %d fixes applied"
          % (out, idxs[0], idxs[-1], n, applied))
    if missed:
        print("\nFIXES THAT DID NOT LAND (%d):" % len(missed))
        for m in missed:
            print("   " + m)
        sys.exit(1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out", help="the batch JSON to write")
    ap.add_argument("fixes", help="confirmed findings, or - for none")
    ap.add_argument("paras", nargs="+", help="the per-paragraph JSON files")
    ap.add_argument("--book", default=None, help="book directory, slug or <folder>/<slug>")
    a = ap.parse_args()
    LANG = find_book(a.book or os.environ.get("FRANK_BOOK") or None).lang
    main(a.out, a.fixes, a.paras)
