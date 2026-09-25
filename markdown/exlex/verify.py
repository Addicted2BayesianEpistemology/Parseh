# SPDX-License-Identifier: GPL-3.0-or-later
"""verify — prove that every target-language string in the .tex made it
into the PDF, in the right order and with correct letter shaping.

Which language the .tex is about is written into it by texgen as a
marker comment, `% exlex-target: <code> <dir>`; a .tex without one is
from before languages were declared and is Persian.

Right-to-left languages (see README, "Design notes" -> "Verification
method"):
  1. extract every glyph with its x coordinate (PyMuPDF rawdict);
  2. group glyphs into baselines, sort by x (a glyph's middle)  ->  true
     VISUAL order;
  3. REVERSE the visual glyph sequence, THEN decompose Arabic
     presentation forms to base letters  ->  reconstructed LOGICAL text.
     (Reverse-then-decompose, never the other way round: the lam-alef
     ligature is one glyph whose decomposition is already in logical
     order — decompose-then-reverse breaks every word containing لا.)
  4. every \\pe/\\pel/\\peb argument in the .tex must appear as a
     substring of the reconstruction (diacritics/ZWNJ/punct stripped).

A string found only in UNreversed order is flagged "LTR word order",
the classic bug this toolchain exists to prevent.

Left-to-right languages keep steps 1, 2 and 4 and skip the reversal:
the visual order IS the logical order, and the check is a forward
substring search on the extracted text -- for Devanagari after the two
signs it draws out of their written order are put back (_written_order).
For Japanese, PyMuPDF extracts horizontal CJK text in order; the lines
of a page are joined with nothing in between, so a breakable run that
wrapped is still found
(the script-only filter has already dropped whatever Latin sat between)
-- unless something stands beside it on its lines, as the marks stand
beside a true/false statement, one column of a matching exercise beside
the other, and a flashcard's back beside its front; such a run is looked
for once more down the page's columns (column_runs; on a right-to-left
page, column_wrapped_runs).  Vertical blocks are never checked: like the
`{fa}` blocks they are not \\pe arguments.
"""
import os
import re
import sys
import unicodedata

import pymupdf

_LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib")
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)
import languages  # noqa: E402


def _debase(ch):
    d = unicodedata.decomposition(ch)
    if d[:1] == "<" and d.split(">")[0][1:] in (
            "isolated", "initial", "medial", "final"):
        return "".join(chr(int(x, 16)) for x in d.split()[1:])
    return ch


# Letters that Persian writes one way and the shaper may emit another.
# `روزنامهٔ` is heh + hamza-above in the source, but XeTeX's HarfBuzz run
# hands back the precomposed U+06C0; strip the combining mark from each
# and the two sides end in different base letters, so a perfectly correct
# PDF is reported "missing".  The Arabic/Persian yeh and kaf pairs are the
# same story.  Folding them costs nothing: this file proves word ORDER,
# and these are variant spellings of one letter, not different letters.
# The table applies to the Arabic script only (Persian and Arabic alike).
_FOLD = {
    0x06C0: "ه",   # ۀ heh with yeh above  -> ه
    0x06D5: "ه",   # ە ae                  -> ه
    0x064A: "ی",   # ي arabic yeh          -> ی
    0x0649: "ی",   # ى alef maksura        -> ی
    0x0643: "ک",   # ك arabic kaf          -> ک
}

_MARKER_RE = re.compile(r"^%\s*exlex-target:\s*([a-z]+)\s+(rtl|ltr)\s*$", re.M)


def target_of(tex_path):
    """The language the .tex was generated for (a Lang), from its marker;
    Persian when the file predates the marker."""
    head = open(tex_path, encoding="utf-8").read(4000)
    m = _MARKER_RE.search(head)
    return languages.get_or_default(m.group(1) if m else None)


def _script_only(s, L):
    """The comparison key of a string: NFD, combining marks dropped, only
    the characters of the target script kept (Arabic script folded to
    one spelling per letter).  For a Latin-script target the letters and
    digits survive, so `perché` and `perche` compare equal on both sides
    whichever way the PDF's font encoded the accent."""
    s = unicodedata.normalize("NFD", s)
    out = []
    for c in s:
        if unicodedata.category(c) == "Mn":
            continue
        if L.script == "arabic":
            c = _FOLD.get(ord(c), c)
            if 0x0600 <= ord(c) <= 0x06FF:
                out.append(c)
        elif L.re_chars is not None:
            if L.re_chars.match(c):
                out.append(c)
        elif c.isalnum():
            out.append(c.lower())
    return "".join(out)


def _arabic_only(s):
    return _script_only(s, languages.get("fa"))


# DEVANAGARI ON PAPER IS IN THE ORDER IT IS DRAWN, and two signs are drawn
# where they are not written.  The vowel sign i (ि) is written after the
# consonants it follows and drawn before them, "किताब" reading back as
# "िकताब"; and a र् before a consonant is drawn as a hook over the end of
# the cluster it begins (reph), "कुर्सी" reading back as "कुसर्ी", "दर्शक" as
# "दशर्क".  Both are put back where they are written before the comparison,
# and only these two, only from the order the shaper draws them in: a PDF
# set without the script's shaping draws ि after its consonant and र् before
# it, in the order written, and the rules then move them past the next
# consonant and before the one in front (a र् with none in front, as in
# "अर्थ", is read as nothing) -- such a PDF is reported missing, as it
# should be.  What stands between ि and its consonant is a mark drawn
# over them (the anusvara of "हिंदी") or a glyph with no character in the
# PDF; a cluster is consonants joined by the virama, each with its nukta.
#
# Where the two meet, the order alone cannot tell which cluster the reph
# is on.  "धार्मिक" (reph on मि) and "मर्यादित" (reph on य, then दि) both read
# back with र्ि between their clusters: "धार्िमक", "मयार्िदत".  The glyphs
# tell them apart.  Noto Serif Devanagari draws a reph over a syllable with
# ि as one glyph, which reads back as the three characters र्ि -- and the
# second and third letters of a glyph come back with no width (_middle);
# a reph over the syllable before is a glyph of its own and ि another, with
# its width.  The ि of that one glyph is read as _DEVA_I_OF_REPH
# (_span_chars), a noncharacter no text holds, and its reph is left where
# it stands, before its cluster as written.
#
# The vowel signs o and au (ो ौ) under a reph are drawn in two, ा and the
# stroke of े or ै with the reph between them: "धर्मों" reads back
# "धमार्ें".  Once the reph is back, the two are one sign again: two vowel
# signs never follow each other in writing.  The table applies to the
# Devanagari script only.
_DEVA_CONSONANTS = set(range(0x0915, 0x093A)) | set(range(0x0958, 0x0960)) | set(range(0x0978, 0x0980))
_DEVA_I, _DEVA_VIRAMA, _DEVA_NUKTA, _DEVA_RA = "\u093F", "\u094D", "\u093C", "\u0930"
_DEVA_I_OF_REPH = "\uFDD0"
_DEVA_SPLIT = {("\u093E", "\u0947"): "\u094B", ("\u093E", "\u0948"): "\u094C"}     # ा+े ो, ा+ै ौ


def _deva_consonant(c):
    return ord(c) in _DEVA_CONSONANTS


def _deva_cluster_end(s, i):
    """The end of the consonant cluster that starts at s[i] (i itself when
    none does): consonants, each with its nukta, joined by viramas."""
    j = i
    while j < len(s) and _deva_consonant(s[j]):
        j += 1
        if j < len(s) and s[j] == _DEVA_NUKTA:
            j += 1
        if j + 1 < len(s) and s[j] == _DEVA_VIRAMA and _deva_consonant(s[j + 1]):
            j += 1
            continue
        break
    return j


def _deva_cluster_start(s, j):
    """The start of the consonant cluster that ends just before s[j]."""
    i = j
    while i > 0:
        k = i - 1
        if s[k] == _DEVA_NUKTA and k > 0:
            k -= 1
        if not _deva_consonant(s[k]):
            break
        i = k
        if i > 1 and s[i - 1] == _DEVA_VIRAMA and _deva_consonant(s[i - 2]) or \
                i > 2 and s[i - 1] == _DEVA_VIRAMA and s[i - 2] == _DEVA_NUKTA:
            i -= 1
            continue
        break
    return i


def _deva_is_mark(c):
    """A sign drawn over or under a letter, or a glyph that has no
    character in the PDF (read back as some unrelated one)."""
    return unicodedata.category(c) == "Mn" or not ("\u0900" <= c <= "\u097F" or c.isspace())


def _written_order(s, L):
    """A line of the PDF, as it reads back, with the signs a script draws
    out of their written place put back in it (Devanagari only)."""
    if L.script != "devanagari":
        return s
    s = list(s)
    # the reph: र् after the cluster it begins, put before it -- but for
    # one drawn in one glyph with the ि of its cluster, which stands before
    # that cluster already
    i = 0
    while i + 1 < len(s):
        if s[i] == _DEVA_RA and s[i + 1] == _DEVA_VIRAMA and not (
                i + 2 < len(s) and s[i + 2] == _DEVA_I_OF_REPH):
            j = i
            while j > 0 and not _deva_consonant(s[j - 1]) and (
                    unicodedata.category(s[j - 1]) in ("Mn", "Mc") or _deva_is_mark(s[j - 1])):
                j -= 1
            start = _deva_cluster_start(s, j)
            if start < j:
                s[start:i + 2] = [_DEVA_RA, _DEVA_VIRAMA] + s[start:i]
            elif i + 2 < len(s) and _deva_consonant(s[i + 2]):
                # before a consonant, with no cluster in front to be over:
                # where it is written, which the shaper never draws it --
                # "अर्थ" set without the shaping.  It is read as nothing.
                del s[i:i + 2]
                continue
        i += 1
    s = [_DEVA_I if c == _DEVA_I_OF_REPH else c for c in s]
    # the vowel signs o and au the reph had cut in two
    i = 0
    while i + 1 < len(s):
        if (s[i], s[i + 1]) in _DEVA_SPLIT:
            s[i:i + 2] = [_DEVA_SPLIT[s[i], s[i + 1]]]
        i += 1
    # the vowel sign i: before the cluster it follows in writing
    out, i = [], 0
    while i < len(s):
        if s[i] == _DEVA_I:
            j = i + 1
            while j < len(s) and _deva_is_mark(s[j]) and s[j] != _DEVA_I:
                j += 1
            end = _deva_cluster_end(s, j)
            if end > j:
                out += s[i + 1:end] + [_DEVA_I]
                i = end
                continue
        out.append(s[i])
        i += 1
    return "".join(out)


def _middle(bbox):
    """Where a glyph stands on its line, for putting a line's glyphs in
    visual order: its middle, not its left edge.  The second letter of a
    ligature (the "f" of "ff") comes back as a glyph of no width at the
    ligature's right edge, which is the next glyph's left edge -- and a
    float's last digit put it after that glyph: "Kaffee" read "Kafefe".
    Its middle is half a glyph clear of either neighbour's."""
    return (bbox[0] + bbox[2]) / 2


def _span_chars(sp):
    """A span's characters as (PyMuPDF's char, the character it is read
    as): its own, but for the ि of a reph drawn in one glyph with it (see
    _DEVA_I_OF_REPH).  That ि is the third letter of its glyph, with no
    width, where the र of the glyph has one; a ि of its own has its width,
    and a reph of its own none."""
    chars = sp["chars"]
    out = []
    for n, ch in enumerate(chars):
        c = ch["c"]
        if (c == _DEVA_I and n > 1 and chars[n - 1]["c"] == _DEVA_VIRAMA
                and chars[n - 2]["c"] == _DEVA_RA
                and ch["bbox"][2] <= ch["bbox"][0]
                and chars[n - 2]["bbox"][2] > chars[n - 2]["bbox"][0]):
            c = _DEVA_I_OF_REPH
        out.append((ch, c))
    return out


def visual_lines(pdf_path, ytol=2.5):
    """Yield one list of characters per visual line, in visual order
    (left to right), page after page."""
    doc = pymupdf.open(pdf_path)
    for page in doc:
        chars = []
        for b in page.get_text("rawdict")["blocks"]:
            if b.get("type") != 0:
                continue
            for l in b["lines"]:
                for sp in l["spans"]:
                    for ch, c in _span_chars(sp):
                        chars.append((round(ch["origin"][1], 1),
                                      _middle(ch["bbox"]), c))
        buckets = {}
        for y, x, c in chars:
            k = next((k for k in buckets if abs(k - y) <= ytol), y)
            buckets.setdefault(k, []).append((x, c))
        for _, v in sorted(buckets.items()):
            yield [c for _, c in sorted(v, key=lambda t: t[0])]


def logical_reconstruction(pdf_path, ytol=2.5):
    """Yield one logically-reconstructed string per visual line (the
    right-to-left reading)."""
    for visual in visual_lines(pdf_path, ytol):
        yield "".join(_debase(c) for c in reversed(visual))


def source_strings(tex_path):
    src = open(tex_path, encoding="utf-8").read()
    body = src[src.index(r"\begin{document}"):]
    args = re.findall(r"\\pe[lb]?\{([^{}]*)\}", body)
    for a in re.findall(r"\\voce\{([^{}]*)\}", body):
        args.append(a)
    return args


def breakable_strings(tex_path):
    """The \\pel arguments: the runs that may wrap (a \\pe or \\peb is one
    box and never does)."""
    with open(tex_path, encoding="utf-8") as f:
        src = f.read()
    return set(re.findall(r"\\pel\{([^{}]*)\}", src[src.index(r"\begin{document}"):]))


def _islands(visual):
    """A visual line's right-to-left islands, left to right: the stretches
    between its left-to-right letters and digits (bidi L and EN), each as
    it reads -- reversed, presentation forms decomposed."""
    out, cur = [], []
    for c in visual:
        if unicodedata.bidirectional(c) in ("L", "EN"):
            if cur:
                out.append(cur)
            cur = []
        else:
            cur.append(c)
    if cur:
        out.append(cur)
    return ["".join(_debase(c) for c in reversed(i)) for i in out]


def wrapped_runs(visual_lines_seq, L):
    """What a run that wrapped reads as.  In a left-to-right paragraph it
    ends a line at the right, fills any line under it whole, and goes on at
    the left of the one after; in a right-to-left paragraph it ends at the
    left and goes on at the right.  Each way, the islands are chained in
    reading order through lines that are one island each, and a chain is
    cut where a line holds more than one (or none): a run cannot pass
    through other text."""
    out, ltr, rtl = [], "", ""
    for visual in visual_lines_seq:
        isl = [i for i in (_script_only(x, L) for x in _islands(visual)) if i]
        if len(isl) == 1:
            ltr, rtl = ltr + isl[0], rtl + isl[0]
            continue
        if isl:
            out += [ltr + isl[0], rtl + isl[-1]]
            ltr, rtl = isl[-1], isl[0]
        else:
            out += [ltr, rtl]
            ltr = rtl = ""
    out += [ltr, rtl]
    return "\x00".join(out)


def _line_pieces(page, ytol=2.5, gap=0.75):
    """A page's visual lines, top to bottom, each cut where a gap wider than
    `gap` em opens in it -- between a true/false statement and its marks,
    between the two columns of a matching exercise, between the two halves
    of a flashcard; a word space is a third of an em: [(y, [(left edge,
    right edge, its characters in visual order), ...]), ...]."""
    buckets = {}
    for b in page.get_text("rawdict")["blocks"]:
        if b.get("type") != 0:
            continue
        for l in b["lines"]:
            for sp in l["spans"]:
                for ch, c in _span_chars(sp):
                    if c.isspace():
                        continue     # a space the reader made up spans the gap
                    y = round(ch["origin"][1], 1)
                    k = next((k for k in buckets if abs(k - y) <= ytol), y)
                    x0, _top, x1, _bottom = ch["bbox"]
                    buckets.setdefault(k, []).append(
                        (_middle(ch["bbox"]), x0, x1, sp["size"], c))
    lines = []
    for y, line in sorted(buckets.items()):
        line.sort()
        pieces, piece, left, right, size = [], [], 0, 0, 0
        for _mid, x0, x1, sz, c in line:
            if piece and x0 - right > gap * max(size, sz):
                pieces.append((left, right, piece))
                piece = []
            if not piece:
                left, right = x0, x1
            piece.append(c)
            right, size = max(right, x1), sz
        pieces.append((left, right, piece))
        lines.append((y, pieces))
    return lines


def side_by_side(lines):
    """The columns of a page (_line_pieces) read down by where they stand,
    not by where they start: each piece goes on the column whose last piece
    it stands under -- the two overlap across the page -- and never on one
    that already has a piece of its own line.  The two halves of a
    flashcard are such columns, each centred in its half, so that no two of
    a half's lines start at one x: a run that wrapped in one half is read
    down that half, with nothing from the other between its lines.  Each
    column is a list of its pieces, top to bottom (characters in visual
    order)."""
    columns = []                 # [left, right, y of its last piece, pieces]
    for y, pieces in lines:
        for left, right, chars in pieces:
            col = next((c for c in reversed(columns)
                        if c[2] != y and c[0] < right and left < c[1]), None)
            if col is None:
                col = [left, right, y, []]
                columns.append(col)
            col[0], col[1], col[2] = left, right, y
            col[3].append(chars)
    return [c[3] for c in columns]


def column_runs(pdf_path, L, ytol=2.5, gap=0.75):
    """What a run that wrapped inside a column reads as, on a left-to-right
    page.  Each visual line is cut into pieces where a gap opens in it
    (_line_pieces), and the pieces that start at one x are read down the
    page, one after the other: a column's lines in order, with nothing from
    beside it between them -- and so are the pieces that stand under one
    another (side_by_side), for a column whose lines are centred, as a
    flashcard's are.  Only a \\pel is looked for here, as in wrapped_runs."""
    out = []
    with pymupdf.open(pdf_path) as doc:
        for page in doc:
            lines = _line_pieces(page, ytol, gap)
            columns = {}
            for left, y, text in sorted((left, y, "".join(chars))
                                        for y, pieces in lines for left, _right, chars in pieces):
                k = next((k for k in columns if abs(k - left) <= 1.5), left)
                columns.setdefault(k, []).append((y, text))
            out += ["".join(t for _, t in sorted(col)) for col in columns.values()]
            out += ["".join("".join(chars) for chars in col) for col in side_by_side(lines)]
    # a column read both ways is the same text: once is enough
    return "\x00".join(dict.fromkeys(_script_only(_written_order(x, L), L) for x in out))


def column_wrapped_runs(pdf_path, L, ytol=2.5, gap=0.75):
    """What a run that wrapped reads as on a right-to-left page (wrapped_runs),
    read down the page's lines whole and down each of its columns
    (side_by_side): a flashcard's front and back stand side by side, and a
    run that wrapped in one half has the other half's lines between its
    own when the page is read whole."""
    out = [wrapped_runs(visual_lines(pdf_path, ytol), L)]
    with pymupdf.open(pdf_path) as doc:
        for page in doc:
            out += [wrapped_runs(col, L) for col in side_by_side(_line_pieces(page, ytol, gap))]
    return "\x00".join(out)


def check(pdf_path, tex_path):
    L = target_of(tex_path)
    if L.rtl:
        haystack = "\x00".join(_script_only(l, L)
                               for l in logical_reconstruction(pdf_path))
        # A \pel run is breakable, and one that wrapped is split between two
        # lines, where it was reported "missing" -- the blind spot README.md
        # names.  Large print wraps many more of them (a display line at
        # 20 pt, a phrase in an Italian sentence at 17), so a breakable run
        # not found whole on one line is looked for once more, joined across
        # a line's end the two ways a run can wrap, in reading order: a run
        # whose words came out reversed on either line is still reported.
        # Never a \pe: it cannot wrap, and two short words are too easily
        # met by chance where two lines are joined.
        wrapped, breakable = None, breakable_strings(tex_path)
    else:
        haystack = "".join(_script_only(_written_order("".join(v), L), L)
                           for v in visual_lines(pdf_path))
        # The lines are joined already, so a run that wrapped is found --
        # unless something stood beside it: a true/false statement's first
        # line ends in its marks, and a matching entry's lines alternate
        # with those of the entry beside it (a correct Italian worksheet
        # was reported "missing").  A \pel not found is looked for once
        # more down the page's columns.
        wrapped, breakable = None, breakable_strings(tex_path)
    ok, failures = 0, []
    for a in source_strings(tex_path):
        t = _script_only(a, L)
        if len(t) < 2:
            continue
        if t not in haystack and a in breakable and wrapped is None:
            wrapped = (column_wrapped_runs(pdf_path, L) if L.rtl
                       else column_runs(pdf_path, L))
        if t in haystack or (a in breakable and t in wrapped):
            ok += 1
        else:
            kind = ("LTR word order (bidi bug!)"
                    if L.rtl and t[::-1] in haystack and len(t) > 3
                    else "missing")
            failures.append((a, kind))
    return ok, failures


def scan_log(log_path, threshold=10.0):
    """Return overfull hboxes wider than threshold pt."""
    bad = []
    try:
        log = open(log_path, encoding="utf-8", errors="replace").read()
    except OSError:
        return bad
    for m in re.finditer(r"Overfull \\hbox \(([\d.]+)pt", log):
        if float(m.group(1)) > threshold:
            bad.append(float(m.group(1)))
    return bad


def main(argv):
    if len(argv) != 3:
        print("usage: verify.py FILE.pdf FILE.tex"); return 2
    pdf, tex = argv[1], argv[2]
    L = target_of(tex)
    ok, failures = check(pdf, tex)
    over = scan_log(re.sub(r"\.pdf$", ".log", pdf))
    print(f"target strings checked  : {ok + len(failures)}  ({L.name})")
    print(f"  {'correct RTL order' if L.rtl else 'found in order   '}     : {ok}")
    print(f"  FAILED                : {len(failures)}")
    for a, kind in failures:
        print(f"    - {a!r:45s} {kind}")
    if over:
        print(f"overfull hboxes > 10pt  : {len(over)} (max {max(over):.1f}pt)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
