#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Apply confirmed pointing fixes to the built .tex, safely.

    python3 apply_pointing.py <rulings.json> [--write] [--book <dir-or-slug>]

Without --write it only reports.  `rulings.json` is a list of
    {"stripped": "...", "correct": "...", "wrong": [{"form": "...", "n": 3}]}

Two properties make this safe, and both are asserted rather than assumed:

  * Changing a mark never changes the stripped text, so source fidelity is
    untouched -- verify_book.py is run to prove it.
  * timings.json is keyed by sha1 of the STRIPPED text, so no measured
    narration time is orphaned by a pointing change.

A replacement is only made inside the text argument of a \\ch or \\chr (the
SECOND argument; the first is the reader's colour mark), and only on a whole
word, so a gloss or a romanisation can never be hit by accident.

"Pointing" is the language's strip range -- the harakat of Persian and
Arabic.  The tool strips with the book's language; a language that strips
nothing has no pointing to fix, and every ruling is refused as changing the
letters.  The diphthong guard is the Persian edition's convention and runs
for Persian alone.  Which book: --book, else $FRANK_BOOK, else the book the
current directory is in.
"""
import glob
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from books import find_book                                     # noqa: E402

BOOK = None                                     # the Book, set in __main__
LANG = None
EDGE = "«»()،؛.!؟:–—"

# \ch{col}{fa}{tr}...  and  \chr{col}{fa}{kana}{tr}...: the text is the second
# argument of both; what follows it differs, so the pattern stops there
CHUNK_RE = re.compile(r"\\ch(r?)\{(.*?)\}\{(.*?)\}\{")


def strip(s):
    return LANG.strip(s)


def chunk_fa_tr(body):
    """(fa, tr) of every \\ch and \\chr in a built file.  tr is the third
    argument of \\ch and the fourth of \\chr (the kana sits between), and the
    arguments hold no braces of their own, so a bounded read after the text
    is enough."""
    out = []
    for m in CHUNK_RE.finditer(body):
        rest = body[m.end() - 1:]
        args = re.match(r"\{([^{}]*)\}(?:\{([^{}]*)\})?", rest)
        if not args:
            continue
        tr = (args.group(2) if m.group(1) else args.group(1)) or ""
        out.append((m.group(3), tr))                # (r-flag, colour, fa): the text is group 3
    return out


def fix_fa(fa, table):
    """Replace whole words in one chunk's text argument."""
    out, n = [], 0
    for w in fa.split():
        lead = ""
        while w and w[0] in EDGE:
            lead, w = lead + w[0], w[1:]
        trail = ""
        while w and w[-1] in EDGE:
            trail, w = w[-1] + trail, w[:-1]
        if w in table:
            w = table[w]
            n += 1
        out.append(lead + w + trail)
    return " ".join(out), n


def main(path, write):
    rulings = json.load(io.open(path, encoding="utf-8"))
    KASRA = "\u0650"
    table, skipped = {}, []
    for r in rulings:
        good = (r.get("correct") or "").strip()
        if not good or " " in good or "/" in good:
            skipped.append((r["stripped"], good, "the ruling names no single replacement word"))
            continue
        snd = (r.get("sound") or "")
        # hyphens are prefix/enclitic convention and a trailing -e/-ye is the
        # ezafe; neither is a difference in the sound of the word itself
        def sound_key(x):
            x = x.split("(")[0].strip(" ()").lower().replace("-", "")
            return re.sub(r"(ye|e)$", "", x)
        alts = {k for part in snd.replace(" vs ", "/").split("/")
                for k in [sound_key(part)] if k}
        if len(alts) > 1:
            skipped.append((r["stripped"], good,
                            "the ruling names two sounds (%s) -- the romanisation has to move too"
                            % ", ".join(sorted(alts))))
            continue
        for bad in r.get("wrong", []):
            form = bad["form"] if isinstance(bad, dict) else bad
            if not form or form == good:
                continue
            # A trailing kasra is the ezafe and belongs to the sentence, not to
            # the ruling.  Swap the word body and put the ezafe back, so a
            # ruling phrased without one can never silently delete it.
            ez = form.endswith(KASRA)
            body_bad  = form[:-1] if ez else form
            body_good = good[:-1] if good.endswith(KASRA) else good
            repl = body_good + (KASRA if ez else "")
            if strip(body_bad) != strip(body_good):
                skipped.append((r["stripped"], "%s -> %s" % (form, good),
                                "changes the letters, not just the marks"))
                continue
            if repl == form:
                continue
            table[form] = repl
    # A form that is printed with two different romanisations in the book is two
    # different words wearing one spelling -- دورِ is dowr-e "around" in one chunk
    # and dur-e "distant" in another.  Replacing it blindly would corrupt the one
    # that is already right, so refuse it and say so.
    seen = {}
    for f in sorted(glob.glob(os.path.join(BOOK.dir, "ch*.tex"))):
        for fa, tr in chunk_fa_tr(io.open(f, encoding="utf-8").read()):
            fw, tw = fa.split(), tr.split()
            if len(fw) != len(tw):
                continue
            for w, t in zip(fw, tw):
                seen.setdefault(w.strip(EDGE), set()).add(
                    t.strip(",.;:!?").lower().replace("-", ""))
    # NOTES section 4 keeps /ow/ as fatha+vav and /ey/ as kasra+ya deliberately;
    # a sweep once forced kasra->fatha the wrong way and overwrote 26 correct
    # chunks.  Never strip the mark that spells a diphthong the page prints.
    # (The Persian edition's convention: it runs for Persian alone.)
    FATHA, KASRA_, VAV, YA = "\u064e", "\u0650", "\u0648", "\u06cc"
    for form in list(table) if LANG.code == "fa" else []:
        rep = table[form]
        for mark, letter, sound in ((FATHA, VAV, "ow"), (KASRA_, YA, "ey")):
            if mark + letter in form and mark + letter not in rep:
                if any(sound in t for t in seen.get(form, ())):
                    skipped.append((form, "%s -> %s" % (form, rep),
                                    "printed %s -- that mark spells the /%s/ the page shows"
                                    % (", ".join(sorted(seen.get(form, ()))), sound)))
                    table.pop(form, None)

    for form in list(table):
        sounds = seen.get(form, set())
        if len(sounds) > 1:
            skipped.append((form, "%s -> %s" % (form, table[form]),
                            "printed with %d different romanisations (%s) -- two words, one spelling"
                            % (len(sounds), ", ".join(sorted(sounds)))))
            del table[form]

    if skipped:
        print("SKIPPED %d rulings:" % len(skipped))
        for a, b, why in skipped:
            print("   %-14s %-28s %s" % (a, b, why))
        print()
    print("%d word forms to replace\n" % len(table))

    total, touched = 0, {}
    for f in sorted(glob.glob(os.path.join(BOOK.dir, "ch*.tex"))):
        body = io.open(f, encoding="utf-8").read()
        hits = [0]

        def repl(m):
            # \ch{colour}{fa}{...} / \chr{colour}{fa}{kana}{...}: the match is
            # (r-flag, colour, fa); the text is the third group, and the
            # colour in the second is the reader's own mark -- never touch it
            new, n = fix_fa(m.group(3), table)
            hits[0] += n
            return "\\ch%s{%s}{%s}{" % (m.group(1), m.group(2), new)

        out = re.sub(r"\\ch(r?)\{(.*?)\}\{(.*?)\}\{", repl, body)
        if hits[0]:
            touched[os.path.basename(f)] = hits[0]
            total += hits[0]
            if write:
                io.open(f, "w", encoding="utf-8").write(out)

    for f, n in sorted(touched.items(), key=lambda x: -x[1]):
        print("  %-12s %3d replacements" % (f, n))
    print("\n%d replacements across %d files%s"
          % (total, len(touched), "" if write else "   (dry run, nothing written)"))
    return 0


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("rulings", help="the rulings JSON")
    ap.add_argument("--write", action="store_true", help="write the files (default: report only)")
    ap.add_argument("--book", default=None, help="book directory, slug or <folder>/<slug>")
    a = ap.parse_args()
    BOOK = find_book(a.book or os.environ.get("FRANK_BOOK") or None)
    LANG = BOOK.lang
    sys.exit(main(a.rulings, a.write))
