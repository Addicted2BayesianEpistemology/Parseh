#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""One-time, idempotent injection of \\parstart into the already-built .tex.

Every batch built from now on gets its \\parstart from assemble.py, which has
the annotation JSON in front of it.  For the batches built before that the
JSON is gone and the .tex IS the only copy, so the anchors have to be cut out
of it -- the accepted pattern in this project (cf. lib/verify_book.py, which
re-checks those same batches against source/paras/ for the same reason).

    python3 lib/inject_parstart.py                  # every book under books/
    python3 lib/inject_parstart.py --check          # report, change nothing
    python3 lib/inject_parstart.py [--check] <book-dir-or-slug> ...   # just these

Books live under books/<language folder>/<slug>/ (and, before languages were
declared, directly under books/); both layouts are walked through
lib/books.py, and each book brings its language: the digits its labels are
written in, and whether its chunks are \\ch, \\chr (with a kana argument),
\\chw / \\chrw (the same two with a word line last) or \\chp.

\\parstart{chapter.paragraph}{incipit} goes immediately before the FIRST
subparagraph of each paragraph, i.e. before \\parnum{N.1} in the book's
digits.  The label is in the language's digits, the way the book prints it;
the incipit is the opening of the paragraph's text -- the fa of that
subparagraph's chunks: six words, or twelve characters for a language
without a word separator (Japanese), the same rule as assemble.py.  Running
this twice must not double up, so a paragraph that already carries a
\\parstart is left alone.
"""
import glob
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from books import find_book, all_books                          # noqa: E402
import languages                                                # noqa: E402

D = languages.digit_class()
PARNUM   = re.compile(r"^\\parnum\{([%s]+)\.([%s]+)\}\s*$" % (D, D))
PARSTART = re.compile(r"^\\parstart\{")
CHAPOPEN = re.compile(r"^\\chapopen\{([%s]+)\}" % D)
# \ch \chr \chp, and \chw \chrw with their word line last; longest names first
CHUNK    = re.compile(r"^\\ch(?:rw|w|r|p)?\{")


def arg_at(line, k):
    """The k-th (0-based) braced argument of a macro line, brace-counted.
    The text of a \\ch / \\chr / \\chp / \\chw / \\chrw is the second (k=1);
    the first is the colour, the reader's own mark."""
    i = line.index("{")
    depth, out, n = 0, [], 0
    for ch in line[i:]:
        if ch == "{":
            depth += 1
            if depth == 1:
                continue
        elif ch == "}":
            depth -= 1
            if depth == 0:
                if n == k:
                    return "".join(out)
                n += 1
                out = []
                continue
        if depth >= 1:
            out.append(ch)
    raise ValueError("unbalanced braces: %s" % line[:60])


def chapter_of(path, lines):
    """The chapter number.  \\chapopen{\u06f3} is the authority where a file has
    one; only the first file of a chapter does, so the rest fall back to the
    name.  Where both speak they must agree."""
    from_name = re.match(r"ch(\d+)", os.path.basename(path))
    named = int(from_name.group(1)) if from_name else None
    for line in lines:
        m = CHAPOPEN.match(line)
        if m:
            opened = int(languages.any_to_latin_digits(m.group(1)))
            if named is not None and opened != named:
                raise SystemExit("%s: \\chapopen says chapter %d, the name says %d"
                                 % (path, opened, named))
            return opened
    if named is None:
        raise SystemExit("%s: no \\chapopen and no chapter in the name" % path)
    return named


def incipit(L, lines, i, words=6, chars=12):
    """The opening of the subparagraph opened at line i -- the text pass 1
    sets: six words, or twelve characters where words are not separated."""
    fa = []
    for line in lines[i + 1:]:
        if line.startswith("\\end{frank}"):
            break
        if CHUNK.match(line):
            fa.append(arg_at(line, 1))
    if L.spaced:
        return " ".join(" ".join(fa).split()[:words])
    return re.sub(r"\s+", "", "".join(fa))[:chars]


def process(path, L, check):
    lines = io.open(path, encoding="utf-8").read().split("\n")
    ch = chapter_of(path, lines)
    out, added, kept = [], 0, 0
    for i, line in enumerate(lines):
        m = PARNUM.match(line)
        if m and languages.any_to_latin_digits(m.group(2)) == "1":
            # idempotence: a paragraph that already has its anchor keeps it
            prev = next((x for x in reversed(out) if x.strip()), "")
            if PARSTART.match(prev):
                kept += 1
            else:
                para = L.to_native_digits(languages.any_to_latin_digits(m.group(1)))
                label = "%s.%s" % (L.to_native_digits(ch), para)
                out.append("\\parstart{%s}{%s}" % (label, incipit(L, lines, i)))
                added += 1
        out.append(line)
    if added and not check:
        io.open(path, "w", encoding="utf-8").write("\n".join(out))
    return added, kept


def main():
    check = "--check" in sys.argv
    wanted = [a for a in sys.argv[1:] if not a.startswith("--")]
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    books = [find_book(w) for w in wanted] if wanted else all_books()
    total = kept_total = 0
    for book in books:
        for path in sorted(glob.glob(os.path.join(book.dir, "ch*.tex"))):
            added, kept = process(path, book.lang, check)
            total += added
            kept_total += kept
            print("  %-44s %3d added, %3d already there"
                  % (os.path.relpath(path, root), added, kept))
    print("\n%d \\parstart %s, %d left alone"
          % (total, "would be added" if check else "added", kept_total))


if __name__ == "__main__":
    main()
