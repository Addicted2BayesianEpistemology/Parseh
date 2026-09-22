#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Write the chapter source list that assemble.py checks a batch against.

    python3 lib/chapter_src.py [--book <dir-or-slug>] <chapter> [<chapter> ...]
    python3 lib/chapter_src.py --book books/my-book --all

assemble.py takes, as its second argument, ONE JSON file holding a whole
chapter as a list of paragraph strings, and indexes into it by the batch's
"idx".  For the first edition those lists lived in "work dir/src/src_chN.json"
and were made by hand from source/paras/; this writes the same thing, from the
same place, into the book's own directory,
books/<folder>/<slug>/source/src_chN.json, so the list travels with the book
and can never be a step behind the paragraph files it is derived from (NOTES
section 6: regenerate whenever the source changes).
"""
import argparse
import glob
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from books import find_book                                     # noqa: E402


def chapter_list(book_dir, ch):
    paras = sorted(glob.glob(os.path.join(book_dir, "source", "paras",
                                          "ch%d_p*.txt" % ch)),
                   key=lambda p: int(re.search(r"_p(\d+)\.txt$", p).group(1)))
    if not paras:
        raise SystemExit("no source/paras/ch%d_p*.txt in %s" % (ch, book_dir))
    idxs = [int(re.search(r"_p(\d+)\.txt$", p).group(1)) for p in paras]
    if idxs != list(range(len(idxs))):
        raise SystemExit("chapter %d's paragraph files are not 0..%d without "
                         "gaps: %s" % (ch, len(idxs) - 1, idxs))
    return [io.open(p, encoding="utf-8").read().strip() for p in paras]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("chapters", nargs="*", type=int)
    ap.add_argument("--book", default=None, help="book directory or slug")
    ap.add_argument("--all", action="store_true",
                    help="every chapter that has paragraph files")
    a = ap.parse_args()
    book = find_book(a.book or os.environ.get("FRANK_BOOK") or None)
    chs = a.chapters
    if a.all:
        found = set()
        for p in glob.glob(os.path.join(book.dir, "source", "paras", "ch*_p*.txt")):
            found.add(int(re.search(r"ch(\d+)_p", os.path.basename(p)).group(1)))
        chs = sorted(found)
    if not chs:
        ap.error("say which chapter(s), or --all")
    for ch in chs:
        lst = chapter_list(book.dir, ch)
        out = os.path.join(book.dir, "source", "src_ch%d.json" % ch)
        with io.open(out, "w", encoding="utf-8") as f:
            json.dump(lst, f, ensure_ascii=False, indent=0)
            f.write("\n")
        # the size an annotator cuts batches by: words where the language
        # has a word separator, characters where it has none (Japanese)
        if book.lang.spaced:
            size = "%d words" % sum(len(p.split()) for p in lst)
        else:
            size = "%d characters" % sum(len(re.sub(r"\s+", "", p)) for p in lst)
        print("%s: %d paragraphs, %s" % (os.path.relpath(out), len(lst), size))


if __name__ == "__main__":
    main()
