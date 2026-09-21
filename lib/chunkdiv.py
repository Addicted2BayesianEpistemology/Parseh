#!/usr/bin/env python3
"""Where one chunk ends and the next begins, moved by hand.

    from chunkdiv import cuts, merge, split
    cuts("هیچ جایِ دُنیا", lang)          -> the places it may be divided
    split(chunk, at, lang, "tex")        -> the two chunks it becomes
    merge(first, second, lang, "plain")  -> the one chunk they become

A chunk is a sense group, and where the sense groups fall is a judgement
somebody makes while reading.  Every tool here could already change what a
chunk SAYS; none of them could change where it STOPS, so a division that came
out wrong -- an LLM's, or one's own on a first pass -- could only be mended by
opening the .tex or the .json.  That is exactly the work this toolbox exists
to take off the desk of somebody who knows the language and is writing the
book themselves.

WHAT MAY BE DONE, AND WHY IT IS SAFE.

The one thing a chunk may never do is stop reproducing its source.  Both
doors check the same thing in the same way -- the chunks of a paragraph
joined with the language's word separator must equal the paragraph in
source/paras/ (lib/check_batch.py), and the chunks of a caption joined the
same way must equal the caption in transcript.txt (youtube/lib/
check_annotations.py) -- with the comparison run over text whose whitespace
has been collapsed and, for Persian and Arabic, whose marks have been taken
off.

Under that comparison:

  * MERGING is safe by construction.  `a` and `b` become `a + sep + b`, so
    the joined text of the paragraph is the string it was, character for
    character, before any normalising at all.

  * SPLITTING is safe exactly at a separator.  For a language whose words
    are separated by spaces, `a b` may become `a` and `b` -- joined back with
    the space they are the text again -- and may NOT become `a` and ` b` cut
    through the middle of a word, because `wo rd` is not `word` however the
    whitespace is collapsed.  For a language with no separator (Japanese,
    whose chunks are joined with nothing and whose comparison drops every
    space) any two characters may be parted.

    `cuts()` is that rule, and it is the only rule: it does not ask whether
    the division is a good one, which is the reader's business and not this
    file's.

WHAT IS PROPOSED, AND WHY IT IS ONLY A PROPOSAL.

Dividing the text is arithmetic.  Dividing the gloss is not: nothing in the
data says which half of a meaning belongs to which half of a phrase, and a
transliteration is not aligned to the words it romanises in any way a program
may rely on.  So everything here proposes, and the caller shows the proposal
in boxes somebody types over before anything is written.  The proposals are:

  fa    the cut itself -- the only field that is not a guess
  tr    cut at the same word, when the romanisation has exactly as many
        words as the text; otherwise all of it to the first chunk
  voc   entry by entry, each following its headword to the side whose text
        holds it -- and an entry whose headword is in neither side (the
        second line of a verb, a note) stays with the entry before it
  en    all to the first chunk, so that the second is visibly unwritten and
        gets written -- unless the meaning has exactly one comma, which is
        the one place a two-way division is already marked in the text
  kana  all to the first chunk, unless the reading opens with the first
        chunk's own characters, which is the case when a Japanese chunk is
        parted at a particle
  col   the colour was on the phrase, so both halves keep it
  words the word line (lib/wordline.py) divided where the text is: exactly
        at a word boundary, and through a word with its reading left whole
        on the first half, as the kana is
  note  to the first chunk, and unknown keys with it

and for a merge every field is joined with the separator its field uses --
the word separator for the text and the reading, a space for the
transliteration and the meaning, the vocabulary's own for the vocabulary --
with a note for anything that could not simply be put end to end.

Nothing here writes a file.  lib/texwrite.py and youtube/lib/annwrite.py do
that, and both prove the result against the checker before it lands, so a
proposal this file gets wrong is refused there rather than saved.

Standard library only: the server imports it.
"""
import re

import wordline

# The two ways a vocabulary line is written.  A book's is TeX -- four gloss
# macros and nothing else (docs/lang/<code>.md) -- and its entries are parted
# by a semicolon.  A video's is plain text and its entries are parted by a
# middle dot, which is also what separates the parts INSIDE one verb entry,
# so the two are told apart by the brackets around the second (see _entries).
TEX, PLAIN = "tex", "plain"
STYLES = (TEX, PLAIN)
VOC_SEP = {TEX: "; ", PLAIN: " · "}

# What opens a vocabulary entry in a book: the four gloss macros, and no
# others.  A semicolon not followed by one of these is inside an entry --
# "\dw{a}{b} one thing; another" -- and is not a place to divide.
_ENTRY_MACRO = re.compile(r"\\(dw|pw|bw|vb)(?![a-zA-Z])")

# The fields joined with the language's word separator rather than a space:
# they are the target language's own text, and Japanese has no space in it.
_TEXTLIKE = ("fa", "kana")

# What a headword may be wrapped in when it is looked for in the text.  A
# chunk's own words carry the sentence's punctuation and the headword does
# not, so both sides are trimmed of it before they are compared.
_EDGE = " \t\n\r‌.,;:!?？。、«»\"'()[]{}—–-…«»‹›„“”‘’٫٬،؛؟"


def _blank(v):
    return not (v or "").strip()


def _join(a, b, sep):
    """`a` and `b` end to end, with `sep` between them -- and with nothing
    between them when one of the two is empty, because a separator with
    nothing on one side of it is a separator somebody has to delete."""
    a, b = (a or "").rstrip(), (b or "").lstrip()
    if not a.strip():
        return b
    if not b.strip():
        return a
    return a + sep + b


# --- where a chunk may be divided ---------------------------------------
def cuts(fa, lang):
    """Every place this text may be divided, in the order they appear.

    A list of {"at": offset, "a": before, "b": after}: `at` is an offset into
    `fa` the caller hands back to `split`, and `a` and `b` are what the two
    chunks' text would be.  Empty when the chunk cannot be divided at all --
    a single word in a language written with spaces, which is not an error
    and is worth saying to whoever clicked.

    The rule is the reproduction check's, run backwards; the module docstring
    says why these places and no others.
    """
    fa = fa or ""
    out = []
    if lang.spaced:
        for m in re.finditer(r"\s+", fa):
            # only a run of the separator itself.  The halves are joined back
            # with one word_sep, so cutting at a tab or a non-breaking space
            # would put an ordinary space where that character was -- which
            # every checker forgives, because they collapse whitespace before
            # they compare, and which loses it from the file all the same.
            if set(m.group(0)) != {lang.word_sep}:
                continue
            a, b = fa[:m.start()], fa[m.end():]
            if a.strip() and b.strip():
                out.append({"at": m.start(), "end": m.end(), "a": a, "b": b})
    else:
        for i in range(1, len(fa)):
            a, b = fa[:i], fa[i:]
            if a.strip() and b.strip():
                out.append({"at": i, "end": i, "a": a, "b": b})
    return out


def pieces(fa, lang):
    """The text as the pieces a page draws, with a place to divide between
    each pair: [{"text": ..., "sep": ...}], the texts and separators run
    together being `fa` again and the number of gaps being the number of
    `cuts`.

    A page is given these rather than the offsets `cuts` carries, because the
    offsets are Python's -- code points -- and a page counts UTF-16 units, so
    a single character outside the basic plane would slide every mark in the
    picker one place to the left.  The offsets stay in the answer for the
    caller that writes; the pieces are for the caller that draws.
    """
    fa = fa or ""
    places = cuts(fa, lang)
    if not places:
        return [{"text": fa, "sep": ""}] if fa else []
    out, pos = [], 0
    for c in places:
        out.append({"text": fa[pos:c["at"]], "sep": fa[c["at"]:c["end"]]})
        pos = c["end"]
    out.append({"text": fa[pos:], "sep": ""})
    return out


def _cut_at(fa, at, lang):
    """The cut `at` names, or a ValueError naming the places there are."""
    for c in cuts(fa, lang):
        if c["at"] == at:
            return c
    places = cuts(fa, lang)
    if not places:
        raise ValueError(
            "this chunk cannot be divided: %s"
            % ("it is one word, and a chunk of a language written with spaces "
               "is divided at a space" if lang.spaced
               else "it is a single character"))
    raise ValueError("%r is not a place this chunk divides -- they are %s"
                     % (at, ", ".join(str(c["at"]) for c in places)))


# --- the vocabulary line, entry by entry --------------------------------
def _entries(voc, style):
    """A vocabulary line cut into its entries, in order.

    A book's line is cut at a semicolon that is outside every brace group AND
    followed by one of the four gloss macros: a semicolon inside \\dw{...} is
    text, and one before a word rather than a macro is the middle of an entry
    that happens to have punctuation in it.

    A video's is cut at the middle dot, outside brackets -- because the same
    dot separates the parts of a single verb entry, which the conventions
    write inside brackets: `هستم hastam I am (بودن budan · pres. باش bāš)`.
    A line that writes a verb without them comes out as several entries; they
    are put back with the same dot, and `_stick` keeps them on one side, so
    the line is the line it was either way.
    """
    voc = voc or ""
    if not voc.strip():
        return []
    out, start = [], 0
    if style == TEX:
        depth = 0
        i = 0
        while i < len(voc):
            c = voc[i]
            if c == "\\":                       # a backslash steps over one
                i += 2                          # character, read_group's rule
                continue
            if c == "{":
                depth += 1
            elif c == "}":
                depth = max(0, depth - 1)
            elif c == ";" and depth == 0:
                rest = voc[i + 1:]
                if _ENTRY_MACRO.match(rest.lstrip()):
                    out.append(voc[start:i])
                    start = i + 1
            i += 1
    else:
        depth = 0
        i = 0
        while i < len(voc):
            c = voc[i]
            if c in "([":
                depth += 1
            elif c in ")]":
                depth = max(0, depth - 1)
            elif depth == 0 and voc.startswith(VOC_SEP[PLAIN], i):
                out.append(voc[start:i])
                start = i + len(VOC_SEP[PLAIN])
                i += len(VOC_SEP[PLAIN])
                continue
            i += 1
    out.append(voc[start:])
    return [e.strip() for e in out if e.strip()]


def _headword(entry, style):
    """The word an entry is about, as it would be found in the text.

    A book's entry opens with a gloss macro whose first argument is the
    headword; a video's opens with the headword itself.  An entry that opens
    with neither -- a continuation, a bare note -- has none, and `_stick`
    keeps it where the entry before it went.
    """
    entry = (entry or "").strip()
    if not entry:
        return ""
    if style == TEX:
        m = _ENTRY_MACRO.match(entry)
        if not m:
            return ""
        rest = entry[m.end():].lstrip()
        if not rest.startswith("{"):
            return ""
        depth, i = 0, 0
        while i < len(rest):
            c = rest[i]
            if c == "\\":
                i += 2
                continue
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return rest[1:i]
            i += 1
        return ""
    return entry.split()[0] if entry.split() else ""


def _holds(text, word, lang):
    """Whether this text is about that word, marks and punctuation aside.

    A headword is a dictionary form and the text carries an inflected one --
    جا for جایِ, كِتَاب for الْكِتَابِ -- so this is containment and not equality,
    which is right for a proposal and would be wrong for a check.
    """
    if not word.strip():
        return False
    a = lang.strip(text or "").strip(_EDGE)
    b = lang.strip(word).strip(_EDGE)
    return bool(b) and b in a


def _stick(entries, a_fa, b_fa, lang, style):
    """Each entry to the side whose text holds its headword; an entry with no
    headword of its own follows the entry before it, and the first entry with
    nowhere to go stays with the first chunk."""
    sides, last = [], "a"
    for e in entries:
        w = _headword(e, style)
        if _holds(a_fa, w, lang):
            last = "a"
        elif _holds(b_fa, w, lang):
            last = "b"
        sides.append(last)
    return sides


# --- dividing the other fields ------------------------------------------
def _split_tr(tr, a_fa, b_fa, lang):
    """The romanisation cut at the same word as the text, when it plainly has
    the same words to cut; otherwise all of it to the first chunk.

    "Plainly" is exact: as many space-separated pieces in the romanisation as
    in the whole text.  A language written without spaces has no word count
    to match, so nothing is guessed there.
    """
    tr = tr or ""
    if not tr.strip() or not lang.spaced:
        return tr, ""
    toks = tr.split()
    na, nb = len(a_fa.split()), len(b_fa.split())
    if len(toks) != na + nb or na == 0 or nb == 0:
        return tr, ""
    return " ".join(toks[:na]), " ".join(toks[na:])


def _split_en(en):
    """The meaning is not divisible by machine, so it stays with the first
    chunk and the second is visibly empty -- except where the writer has
    already marked a two-way division with a single comma, which is common
    enough in a gloss ("the fox went out, one day") to be worth offering."""
    en = en or ""
    if en.count(",") == 1:
        a, b = en.split(",")
        if a.strip() and b.strip():
            return a.strip() + ",", b.strip()
    return en, ""


def _split_kana(kana, a_fa):
    """The reading of the first chunk when the first chunk is already kana --
    a Japanese phrase parted at a particle -- and otherwise the whole reading
    to the first chunk, for somebody who can read it to divide."""
    kana = kana or ""
    if kana and a_fa and kana.startswith(a_fa):
        rest = kana[len(a_fa):]
        if rest.strip():
            return a_fa, rest
    return kana, ""


# --- the two operations -------------------------------------------------
def split(chunk, at, lang, style=TEX):
    """One chunk as the two it would become, and what was guessed.

    Returns (first, second, notes).  Both are whole chunks -- every key the
    original carried is on one of them -- and `notes` is a list of sentences
    for whoever is about to look at the boxes, naming each field that was not
    divided but merely handed over.

    Raises ValueError when `at` is not one of `cuts()`.
    """
    if style not in STYLES:
        raise ValueError("style must be %s" % " or ".join(STYLES))
    fa = chunk.get("fa") or ""
    c = _cut_at(fa, at, lang)
    a_fa, b_fa = c["a"], c["b"]

    # The divided fields, worked out first so the notes read in field order.
    ka, kb = _split_kana(chunk.get("kana"), a_fa)
    ta, tb = _split_tr(chunk.get("tr"), a_fa, b_fa, lang)
    ea, eb = _split_en(chunk.get("en"))
    entries = _entries(chunk.get("voc"), style)
    sides = _stick(entries, a_fa, b_fa, lang, style)
    sep = VOC_SEP[style]
    va = sep.join(e for e, s in zip(entries, sides) if s == "a")
    vb = sep.join(e for e, s in zip(entries, sides) if s == "b")

    divided = {"fa": (a_fa, b_fa), "kana": (ka, kb), "tr": (ta, tb),
               "voc": (va, vb), "en": (ea, eb)}
    word_notes = []
    if not _blank(chunk.get("words")):
        wa, wb, word_notes = wordline.divide(chunk["words"], a_fa)
        divided["words"] = (wa, wb)
    # Both chunks keep the colour: it marked the phrase, and the phrase is
    # still there, in two pieces.  `plain` likewise says what KIND of chunk
    # this is, which dividing does not change.  Everything else -- the note,
    # and any key a later format has added that this file has never heard of
    # -- stays with the first chunk rather than being copied into two places
    # or dropped from both.
    # "free" the same: it says the caption's text is the annotator's and not
    # the transcript's, and cutting a phrase in two changes nothing about that
    both = ("col", "plain", "free")
    a, b = {}, {}
    for k, v in chunk.items():                  # the chunk's own key order
        if k in divided:
            a[k], b[k] = divided[k]
        elif k in both:
            a[k] = b[k] = v
        else:
            a[k] = v
    for k, (va_, vb_) in divided.items():       # a field the chunk did not
        if k not in a and (va_ or vb_):         # carry but the division made
            a[k], b[k] = va_, vb_

    notes = []
    if not _blank(chunk.get("kana")) and _blank(kb):
        notes.append("the reading was left whole on the first chunk: the "
                     "second one needs its own")
    if not _blank(chunk.get("tr")) and _blank(tb):
        notes.append("the romanisation has not one word per word of the text, "
                     "so it was left whole on the first chunk")
    if entries:
        moved = sum(1 for s in sides if s == "b")
        notes.append("%d of the %d vocabulary entries followed its headword to "
                     "the second chunk" % (moved, len(entries)))
    if not _blank(chunk.get("en")):
        notes.append("the meaning was cut at its comma" if not _blank(eb) else
                     "the meaning cannot be divided by machine: it was left on "
                     "the first chunk, and the second one needs its own")
    if not _blank(chunk.get("note")):
        notes.append("the note stayed with the first chunk")
    notes.extend(word_notes)
    return _tidy(a), _tidy(b), notes


def entries_for(chunk, at, lang, style=TEX):
    """The vocabulary line as chips a page can move between the two halves.

    [{"text": entry, "side": "a" | "b"}], in the line's own order, with the
    side each entry was proposed for.  The page rebuilds the two lines by
    joining the entries of each side with `VOC_SEP[style]`, so the rule for
    where an entry begins and where it goes stays here and the page carries
    only the answer -- one implementation, drawn twice.
    """
    fa = chunk.get("fa") or ""
    c = _cut_at(fa, at, lang)
    es = _entries(chunk.get("voc"), style)
    return [{"text": e, "side": s}
            for e, s in zip(es, _stick(es, c["a"], c["b"], lang, style))]


def merge(first, second, lang, style=TEX):
    """Two chunks as the one they would become, and what was joined.

    Returns (chunk, notes).  Every field is put end to end with the separator
    that field uses; the colour, which cannot be, is the first chunk's and the
    note says when that lost the second one's.

    Raises ValueError when the two cannot be one chunk at all: an aside marked
    plain does not join a glossed phrase, because the two are not the same
    kind of thing and the checkers would be right to say so.
    """
    if style not in STYLES:
        raise ValueError("style must be %s" % " or ".join(STYLES))
    if bool(first.get("plain")) != bool(second.get("plain")):
        raise ValueError("one of these chunks is marked plain and the other is "
                         "glossed: an aside and a phrase of the language are "
                         "not one chunk")
    sep = lang.word_sep or ""
    out, notes = {}, []
    for k, v in first.items():
        out[k] = v
    for k, v in second.items():                 # a key only the second has
        if k not in out:                        # comes over rather than being
            out[k] = v                          # quietly dropped
            if k not in ("fa", "words", "kana", "tr", "voc", "en", "note",
                         "col", "plain", "free"):
                notes.append("%r was on the second chunk only and was kept" % k)

    for f in _TEXTLIKE:
        if not _blank(first.get(f)) or not _blank(second.get(f)):
            out[f] = _join(first.get(f), second.get(f), sep)
    for f in ("tr", "en"):
        if not _blank(first.get(f)) or not _blank(second.get(f)):
            out[f] = _join(first.get(f), second.get(f), " ")
    if not _blank(first.get("voc")) or not _blank(second.get("voc")):
        out["voc"] = _join(first.get("voc"), second.get("voc"), VOC_SEP[style])
    if not _blank(first.get("note")) or not _blank(second.get("note")):
        out["note"] = _join(first.get("note"), second.get("note"), "; ")
    # Word lines join with one space, never the word separator (which would
    # fuse two words); a line on only one side cannot reproduce the merged
    # text, so it is dropped and the chunk is divided into words again.
    wa, wb = first.get("words"), second.get("words")
    if not _blank(wa) and not _blank(wb):
        out["words"] = wordline.join_lines(wa, wb)
    elif not _blank(wa) or not _blank(wb):
        out.pop("words", None)
        notes.append("only one of the two chunks was divided into words, so the "
                     "merged chunk has none until it is divided again")

    ca, cb = (first.get("col") or "").strip(), (second.get("col") or "").strip()
    out["col"] = ca or cb
    if ca and cb and ca != cb:
        notes.append("the two were coloured differently: the first one's %s "
                     "stands and the second one's %s is gone" % (ca, cb))
    if not _blank(first.get("en")) and not _blank(second.get("en")):
        notes.append("the two meanings were put end to end -- read them once, "
                     "they were written to be read apart")
    return _tidy(out), notes


def _tidy(chunk):
    """A chunk with its empty fields dropped, the way both writers store one:
    absent and empty say the same thing to every reader of either format, and
    a key holding nothing is a line somebody has to look at twice."""
    return {k: v for k, v in chunk.items()
            if not (isinstance(v, str) and not v.strip())}
