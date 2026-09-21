#!/usr/bin/env python3
"""Recover clean, paragraph-structured text from a PDF's text layer.

    python3 lib/extract_pdf.py <pdf> [--lang fa] [--from N] [--to N] [--out clean.txt]
                               [--paras DIR --tag ch1]

The same recovery the Hedayat text needed, with nothing about that book baked
in: thresholds are measured from the page rather than assumed, and the
font-specific private-use harakat are applied only where they occur.

Text comes from pdftotext's layout mode (correct logical order); paragraph
structure comes from PyMuPDF line geometry -- an indented line starts a
paragraph, a short line ends one.

--lang names the book's language (a registry code, default fa).  It decides
two things.  The repairs of a broken Arabic-script text layer -- the ZWNJ a
font dropped, presentation forms, private-use harakat, kashida, the visual
mirroring of brackets, Arabic punctuation spacing, the Arabic kaf and ya --
run only for an Arabic-script language.  And the filter that tells a real
paragraph from the debris of a decorative rule or a drop-cap counts letters
of the language's own script (the registry's `chars`, letters only -- a line
of numerals or of marks is debris too): several words of them for a language
with words, several characters for Japanese, which has no word separator; a
Latin-script language, whose text cannot be told from any other Latin,
counts words of letters.
"""
import argparse
import collections
import os
import re
import subprocess
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import languages                                                # noqa: E402

RIGHT_JOIN_ONLY = set("اآأإٱدذرزژوؤةى")
BIDI = "‪‫‬‭‮‎‏⁦⁧⁨⁩"
MIRROR = {"(": ")", ")": "(", "[": "]", "]": "[", "«": "»", "»": "«"}
# fonts in these scans put the harakat in the private-use area as free glyphs.
# The keys are written as escapes on purpose: the glyphs are invisible in
# every editor, and an edit once dropped them, leaving an empty key that
# matched everywhere and put a shadda after every letter.
PUA = {"\ue820": "\u064e", "\ue821": "\u064f", "\ue822": "\u0650",
       "\ue823": "\u064b", "\ue825": "\u0651", "\ue828": "\u0651"}
COMBINING = {"ﹰ": "ً", "ﹲ": "ٌ", "ﹴ": "ٍ",
             "ﹶ": "َ", "ﹸ": "ُ", "ﹺ": "ِ",
             "ﹼ": "ّ", "ﹾ": "ْ"}

LANG = languages.get(languages.DEFAULT)         # set from --lang in main()


def form_of(ch):
    n = unicodedata.name(ch, "")
    for f in ("INITIAL", "MEDIAL", "FINAL", "ISOLATED"):
        if n.endswith(f + " FORM"):
            return f
    return None


def restore_zwnj(s):
    """A dual-joining letter in FINAL or ISOLATED form immediately before
    another letter can only mean the joining run was broken there."""
    out = []
    for i, ch in enumerate(s):
        out.append(ch)
        if form_of(ch) in ("FINAL", "ISOLATED") and \
           unicodedata.normalize("NFKC", ch)[-1] not in RIGHT_JOIN_ONLY:
            nxt = s[i + 1] if i + 1 < len(s) else ""
            if nxt and not ("ً" <= nxt <= "ْ") and \
               form_of(nxt) in ("INITIAL", "ISOLATED"):
                out.append("‌")
    return "".join(out)


# Glyphs a broken embedded encoding leaves behind.  Verified in context before
# being listed: "فرنگی مĤب" is فرنگی مآب, so Ĥ stands for آ.  An Arabic-script
# repair: in an Italian text Ĥ is a letter of its own.
GLYPH_FIX = {"Ĥ": "آ"}
CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def clean_arabic_line(line):
    """The repairs an Arabic-script text layer needs (Persian, Arabic)."""
    for a, b in GLYPH_FIX.items():
        line = line.replace(a, b)
    line = re.sub(r"[ \t]*ـ+[ \t]*", "", line)          # kashida + its gaps
    line = re.sub("[" + BIDI + "]", "", line)
    for pua, mark in PUA.items():
        line = re.sub(r"[ \t]+" + pua + r"[ \t]*", mark + " ", line)
        line = re.sub(r"[ \t]*" + pua + r"[ \t]*", mark, line)
    # a sukun always closes a word and keeps the gap; other marks sit inside one
    line = re.sub(r"[ \t]*ﹾ[ \t]*", "ْ ", line)
    for pf, mark in COMBINING.items():
        if pf == "ﹾ":
            continue
        line = re.sub(r"[ \t]+" + pf + r"[ \t]*", mark + " ", line)
        line = re.sub(r"[ \t]*" + pf + r"[ \t]*", mark, line)
    line = unicodedata.normalize("NFKC", restore_zwnj(line))
    line = re.sub(r"[ \t]*ـ+[ \t]*", "", line)
    line = line.replace("­", "–")             # soft hyphen -> en dash
    if LANG.code == "fa":
        # the Arabic kaf and ya for the Persian ones: a Persian text layer
        # set with an Arabic font.  An Arabic text keeps its own letters.
        line = line.replace("ك", "ک").replace("ي", "ی")
    line = "".join(MIRROR.get(c, c) for c in line)      # brackets are visual
    line = re.sub(r"\s+([،؛,.!؟?:])", r"\1", line)
    line = re.sub(r"([،؛])(?=\S)", r"\1 ", line)
    line = re.sub(r"(?<=[^\W\d_])([.!؟?])(?=[^\s.!؟?)\]»‌])", r"\1 ", line)
    return line


def clean_other_line(line):
    """What every other script needs: the bidi controls a layout tool may
    leave, and the compatibility forms (fi/fl ligatures, full-width Latin)
    folded back.  A CJK script is NOT NFKC-folded: that would turn its full-width
    punctuation and its half-width katakana into other characters, and the
    text must reproduce the page.  A soft hyphen is a hyphenation point the
    line join must not print."""
    line = re.sub("[" + BIDI + "]", "", line)
    line = line.replace("­", "")
    # ASKED OF `tex.script`, NOT OF THE SCRIPT NAME.  This used to be
    # `script == "japanese"`, which is the name of ONE row: Chinese calls its
    # script `cjk`, so every extracted Chinese page had 他说：「你好，中国。」
    # folded to 他说:「你好,中国。」 -- the colon and the comma quietly turned
    # into ASCII, in a toolbox whose first rule is that the chunks reproduce
    # the text.
    if (getattr(LANG, "tex", None) or {}).get("script") == "CJK":
        return unicodedata.normalize("NFC", line)
    return unicodedata.normalize("NFKC", line)


def clean_line(line):
    line = CONTROL.sub("", line)
    if LANG.script == "arabic":
        line = clean_arabic_line(line)
    else:
        line = clean_other_line(line)
    return re.sub(r"[ \t]+", " ", line).strip()


def geometry(pdf, first, last):
    """Per page: (x0, x1, text) of every text line, in reading order.  The
    text is the line's own, as PyMuPDF reads it, so that for a left-to-right
    script the text and its geometry come from one object and can never
    disagree.  For a right-to-left script that text is not used (see
    extract): PyMuPDF orders the glyphs of a bidi line unreliably, which is
    why the text of those languages comes from pdftotext."""
    # PyMuPDF >= 1.24 renamed the module; the `fitz` alias still works but
    # prints a deprecation warning ON STDOUT, which lands in the text we emit.
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz
    doc = fitz.open(pdf)
    pages = []
    for pno in range(first, min(last + 1, doc.page_count)):
        rows = collections.defaultdict(lambda: [9e9, -9e9, []])
        for b in doc[pno].get_text("dict")["blocks"]:
            if b["type"]:
                continue
            for l in b["lines"]:
                t = "".join(s["text"] for s in l["spans"])
                if not t.strip():
                    continue
                y = round(l["bbox"][1] / 3)
                rows[y][0] = min(rows[y][0], l["bbox"][0])
                rows[y][1] = max(rows[y][1], l["bbox"][2])
                rows[y][2].append((l["bbox"][0], t))
        page = []
        for y in sorted(rows):
            x0, x1, parts = rows[y]
            parts.sort(reverse=LANG.rtl)
            page.append((x0, x1, (LANG.word_sep or "").join(t for _x, t in parts)))
        pages.append(page)
    return pages


def join_lines(lines):
    """One paragraph out of its lines.  Words separated by spaces get a
    space at the line break; Japanese gets nothing, since a line ends
    mid-word as readily as anywhere.  A Latin line that ends in a hyphen
    before a lower-case continuation was hyphenated by the typesetter, and
    the hyphen goes."""
    if not LANG.spaced:
        return "".join(lines)
    out = []
    for text in lines:
        if out and LANG.script == "latin" and out[-1].endswith("-") \
           and text[:1].islower():
            out[-1] = out[-1][:-1] + text
        else:
            out.append(text)
    return " ".join(out)


def is_letter(c):
    """A letter of the language's script.  The registry's `chars` is the
    whole block -- for Persian it holds the digits, the harakat and the
    Arabic punctuation as well -- so a line of numerals or stray marks would
    count as words of the script; isalpha keeps only the letters, which is
    what the Persian-only filter counted.  A Latin-script language has no
    block and counts every letter."""
    return c.isalpha() and (LANG.re_chars is None or LANG.re_chars.match(c) is not None)


def is_paragraph(p):
    """Decorative rules and drop-caps survive as a few stray glyphs -- and so
    do a date line, a page range or a run of harakat; a real paragraph has
    several words with letters of the language's script in them: three words
    of two letters or more, or six letters for Japanese, which has no word
    separator."""
    if not LANG.spaced:
        return sum(1 for c in p if is_letter(c)) >= 6
    return sum(1 for w in p.split() if sum(1 for c in w if is_letter(c)) >= 2) >= 3


def page_lines(pdf, first, last):
    """Per page: (text, (x0, x1)) of every line, cleaned, and how many pages
    had text and geometry disagree.  A right-to-left script takes its text
    from pdftotext (correct logical order) and its geometry from PyMuPDF,
    matched line for line -- a page where the counts differ keeps its text
    and loses its paragraph structure.  A left-to-right script takes both
    from PyMuPDF: pdftotext de-hyphenates, merging the two halves of a
    hyphenated line into one, and an Italian page then never matched its
    geometry."""
    geo = geometry(pdf, first, last)
    pages, mismatched = [], 0
    if LANG.rtl:
        txt = subprocess.run(["pdftotext", "-f", str(first + 1), "-l", str(last + 1),
                              pdf, "-"], capture_output=True, text=True).stdout
        for pno, raw in enumerate(txt.split("\f")):
            lines = [c for c in (clean_line(l) for l in raw.split("\n")) if c]
            rows = [r[:2] for r in geo[pno]] if pno < len(geo) else []
            if len(lines) != len(rows):
                mismatched += 1
                rows = [[0.0, 1e4]] * len(lines)
            pages.append(list(zip(lines, rows)))
    else:
        for rows in geo:
            page = []
            for x0, x1, t in rows:
                c = clean_line(t)
                if c:
                    page.append((c, (x0, x1)))
            pages.append(page)
    return pages, mismatched


def extract(pdf, first, last, drop=()):
    pages, mismatched = page_lines(pdf, first, last)
    paras, cur = [], []
    droppat = [re.compile(d) for d in drop]
    pagenum = re.compile(r"[%s]+" % languages.digit_class())
    for lines in pages:
        rows = [r for _t, r in lines]
        # measure the margins from the page itself
        right = max((r[1] for r in rows), default=1e4)
        left = min((r[0] for r in rows), default=0.0)
        for text, (x0, x1) in lines:
            if pagenum.fullmatch(text):                  # running page number
                continue
            if any(p.search(text) for p in droppat):     # running header
                continue
            # The indent is on the line's START and the short line's gap at
            # its END: the right edge for a right-to-left script, the left
            # edge for the others.
            if LANG.rtl:
                indented, short = x1 < right - 8, x0 > left + 12
            else:
                indented, short = x0 > left + 8, x1 < right - 12
            if indented and cur:                         # indented: new paragraph
                paras.append(join_lines(cur))
                cur = []
            cur.append(text)
            if short:                                    # short line: paragraph ends
                paras.append(join_lines(cur))
                cur = []
    if cur:
        paras.append(join_lines(cur))
    paras = [re.sub(r"\s+", " ", p).strip() for p in paras if p.strip()]
    paras = [p for p in paras if is_paragraph(p)]
    return paras, mismatched


def main():
    global LANG
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--lang", default=languages.DEFAULT, choices=languages.CODES,
                    help="the book's language, a registry code (default %s)" % languages.DEFAULT)
    ap.add_argument("--from", dest="first", type=int, default=0,
                    help="first PDF page, 0-based")
    ap.add_argument("--to", dest="last", type=int, default=10 ** 6)
    ap.add_argument("--drop", action="append", default=[],
                    help="regex of a running header line to discard")
    ap.add_argument("--out", default=None)
    ap.add_argument("--paras", default=None, help="directory for one file per paragraph")
    ap.add_argument("--tag", default="ch1")
    args = ap.parse_args()
    LANG = languages.get(args.lang)

    paras, bad = extract(args.pdf, args.first, args.last, args.drop)
    if LANG.spaced:
        size = "%d words" % sum(len(p.split()) for p in paras)
    else:
        size = "%d characters" % sum(len(p) for p in paras)
    print("%d paragraphs, %s%s"
          % (len(paras), size,
             "" if not bad else "  (%d pages where text and geometry disagreed)" % bad))
    if LANG.script == "arabic":
        left = len(re.findall(r"[ﭐ-﷿ﹰ-﻿]", "".join(paras)))
        print("stray presentation forms: %d | ZWNJ restored: %d"
              % (left, "".join(paras).count("‌")))
    if args.out:
        open(args.out, "w", encoding="utf-8").write("\n\n".join(paras))
        print("wrote", args.out)
    if args.paras:
        os.makedirs(args.paras, exist_ok=True)
        for i, p in enumerate(paras):
            open(os.path.join(args.paras, "%s_p%02d.txt" % (args.tag, i)),
                 "w", encoding="utf-8").write(p)
        print("wrote %d paragraph files to %s" % (len(paras), args.paras))
    for p in paras[:2]:
        print("   ", p[:78])


if __name__ == "__main__":
    main()
