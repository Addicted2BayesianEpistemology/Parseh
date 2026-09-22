#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""The word line: where a chunk's text divides into words, and how each sounds.

    山(やま) へ 柴刈り(しばかり) に 、

One plain string, the same bytes in a book's \\chw / \\chrw argument and in a
video chunk's "words" key.  The grammar, whole:

    line   := token ( WS+ token )*
    token  := surface | surface "(" reading ")"

  * whitespace OUTSIDE parentheses separates words -- any whitespace, the
    ideographic space a Japanese input method types included;
  * whitespace INSIDE parentheses belongs to the reading (pinyin `běi jīng`);
  * a reading closes its word: `山(やま)へ` and `食(た)べる` are refused, with
    the fix in the message, because read leniently they silently become one
    word or a reading over the wrong characters;
  * `((` and `))` are a literal parenthesis; the fullwidth （ ） are ordinary
    text, and a word that uses them as a reading is refused by name;
  * a word with no reading is written without parentheses, and `山()` is
    refused -- one state, one spelling.

THE TEXT IS NOT IN THE LINE, ONLY ITS DIVISION.  The surfaces joined with the
language's word separator must reproduce the chunk's `fa` under the fidelity
comparison, which drops whitespace for an unspaced language.  So a space in
`fa` needs no spelling here: a page or a PDF draws the characters from `fa`
and takes from the line only where the words end and what each is read
(align()).

THE CHUNK'S READING IS NOT DERIVED FROM THE LINE, NOR THE LINE FROM IT.  In
kanbun the reading reorders the words; in Chinese `tr` writes the changed
tones of 一 and 不.  check() compares the two only to WARN, and a document read
out of its written order says "reorders": true and is not warned at all.

Every refusal and warning carries a `code` beside its sentence.  lib/
wordline.lua (the PDF) and lib/wordline.js (the pages) are the other two
parsers of this grammar, and tests/fixtures/wordline.json holds all three to
the same codes.  Standard library only, and nothing imported from the rest of
the toolbox: every checker and both writers import this.
"""
import re
import unicodedata

# What LaTeX reads as an instruction, and what is not text at all.  A book's
# word line sits in a macro argument, so it may hold neither; a video's may
# hold the first, since its text may.
TEX_SPECIALS = "\\{}$%&#_^~"
NOT_TEXT = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\ud800-\udfff]")

# A character that is read: a kanji or hanzi, and the two iteration marks
# only ever written after one.  A word holding one needs a reading.
HAN = re.compile("[々〆㐀-䶿一-鿿豈-﫿\U00020000-\U0003ffff]")
# The characters of a word proper, kana included -- what punctuation must not
# be glued to.  `50%` is a word; `へ、` is two.
_SCRIPT = re.compile("[ぁ-ゖゝゞァ-ヺー々〆㐀-䶿一-鿿豈-﫿\U00020000-\U0003ffff]")
_HIRA_TAIL = re.compile("[ぁ-ゖゝゞ]+$")
_HIRA_RUN = re.compile("^[ぁ-ゖゝゞ]+$")

BOOK, VIDEO = "book", "video"


class WordsError(ValueError):
    """A word line that cannot be read: `code` for a program, the sentence
    for a person."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


class Note(str):
    """A sentence from check(), carrying its `code`."""

    def __new__(cls, code, message):
        o = str.__new__(cls, message)
        o.code = code
        return o


def _punct(ch):
    return unicodedata.category(ch)[0] == "P"


# --- reading the line ----------------------------------------------------
def parse(line):
    """[(surface, reading)] in written order; reading is "" for a word that
    has none.  Raises WordsError for anything the grammar does not allow."""
    if not isinstance(line, str):
        raise WordsError("type", "a word line is text, not %s" % type(line).__name__)
    pairs, surf, read = [], [], []
    state, start, i, n = 0, 0, 0, len(line)     # 0 surface, 1 reading, 2 closed

    def shown(end):
        return line[start:end].strip()

    def finish(end):
        nonlocal surf, read, state
        if state == 1:
            raise WordsError("unclosed", "%r opens a reading and never closes it"
                             % shown(end))
        s, r = "".join(surf), " ".join("".join(read).split())
        if s:
            if state == 2 and not r:
                raise WordsError("empty_reading", "%r has empty parentheses -- a "
                                 "word with no reading is written without them"
                                 % shown(end))
            if "（" in s and s.endswith("）") and not s.startswith("（"):
                raise WordsError("fullwidth", "%r puts its reading in the fullwidth "
                                 "parentheses （ ） (U+FF08, U+FF09): a reading is "
                                 "written in the ASCII ( ), and the fullwidth pair "
                                 "is part of the text" % shown(end))
            if s.endswith("(") or r.startswith("("):
                raise WordsError("unwritable", "%r ends in a literal '(', which "
                                 "cannot be written back: a word may not end in "
                                 "one nor a reading begin with one" % shown(end))
            pairs.append((s, r))
        surf, read, state = [], [], 0

    while i < n:
        c = line[i]
        if state == 2:
            if c.isspace():
                finish(i)
                i += 1
                start = i
                continue
            j = i
            while j < n and not line[j].isspace():
                j += 1
            tail, word = line[i:j], shown(i)
            s, r = "".join(surf), "".join(read)
            if _HIRA_RUN.match(tail):
                raise WordsError("joined", "%r is followed by %r with no space: if "
                                 "%s belongs to the word the reading covers it too, "
                                 "%s(%s), and if it is a word of its own put a space "
                                 "before it" % (word, tail, tail, s + tail, r + tail))
            raise WordsError("joined", "a reading ends its word: put a space "
                             "between %r and %r" % (word, tail))
        if c in "()" and i + 1 < n and line[i + 1] == c:
            (read if state == 1 else surf).append(c)
            i += 2
            continue
        if state == 0 and c.isspace():
            finish(i)
            i += 1
            start = i
            continue
        if c == "(":
            if state == 1:
                raise WordsError("second_open", "a second '(' inside %r -- a "
                                 "literal parenthesis is written twice, ((" % shown(n))
            if not surf:
                raise WordsError("no_word", "a reading with no word in front of "
                                 "it, in %r" % shown(n))
            state = 1
        elif c == ")":
            if state == 0:
                raise WordsError("stray_close", "%r closes a parenthesis it never "
                                 "opened -- a literal one is written twice, ))"
                                 % shown(n))
            state = 2
        else:
            (read if state == 1 else surf).append(c)
        i += 1
    finish(n)
    return pairs


def _esc(s):
    return s.replace("(", "((").replace(")", "))")


def token(surface, reading=""):
    """One word as it is written in the line."""
    reading = " ".join((reading or "").split())
    if not surface:
        raise WordsError("no_text", "a word with no text")
    if any(ch.isspace() for ch in surface):
        raise WordsError("space_in_word", "%r has a space in it: words are parted "
                         "by spaces, so no word can hold one" % surface)
    if surface.endswith("(") or reading.startswith("("):
        raise WordsError("unwritable", "%r(%s) cannot be written: a word may not "
                         "end in '(' nor a reading begin with one" % (surface, reading))
    return _esc(surface) + ("(" + _esc(reading) + ")" if reading else "")


def render(pairs):
    """The line for these words -- parse()'s inverse."""
    return " ".join(token(s, r) for s, r in pairs)


def join_lines(a, b):
    """Two chunks' lines as the merged chunk's: end to end with ONE space,
    never the language's word separator, which for ja and zh is nothing and
    would fuse the last word of one with the first of the other."""
    return " ".join(x for x in ((a or "").strip(), (b or "").strip()) if x)


# --- the line against the text -------------------------------------------
def norm(s, lang):
    """The comparison's form: the language's marks off, and whitespace
    collapsed -- or dropped, for a language with no separator.  Code point by
    code point, never normalised: lib/wordline.lua sets the PDF from these
    same characters, so a line that matched its text only after NFC would
    pass here and stop the build there, and divide() would count a
    decomposed character twice."""
    s = lang.strip(s or "")
    return " ".join(s.split()) if lang.spaced else "".join(s.split())


def _diff(got, want):
    k = next((i for i, (x, y) in enumerate(zip(got, want)) if x != y),
             min(len(got), len(want)))

    def at(s):
        return "U+%04X %s" % (ord(s[k]), s[k]) if k < len(s) else "nothing"
    return ("the words give %r and the text is %r: at character %d the words "
            "have %s and the text has %s" % (got, want, k, at(got), at(want)))


def align(fa, pairs):
    """`fa` cut at the word boundaries: [(text, reading, k)] whose texts run
    together are `fa`, whitespace and all.  k is the word's index, or None for
    whitespace standing between two words; whitespace inside a word stays in
    it.  Raises WordsError when the words do not rejoin the text, compared
    code point by code point as norm() says."""
    fa = fa or ""
    words = "".join(s for s, _ in pairs)
    out, i, n = [], 0, len(fa)
    for k, (s, r) in enumerate(pairs):
        j = i
        while j < n and fa[j].isspace():
            j += 1
        if j > i:
            out.append((fa[i:j], "", None))
        i = start = j
        for ch in s:
            while i < n and fa[i].isspace():
                i += 1
            if i >= n or fa[i] != ch:
                raise WordsError("reproduce", _diff(words, "".join(fa.split())))
            i += 1
        out.append((fa[start:i], r, k))
    if fa[i:].strip():
        raise WordsError("reproduce", _diff(words, "".join(fa.split())))
    if i < n:
        out.append((fa[i:], "", None))
    return out


def sounds(pairs):
    """Each word's part in the chunk read aloud, in written order: its
    reading, or its own characters where it needs none (kana, punctuation, a
    latin word).  A word of kanji left without a reading contributes nothing."""
    return [r if r else s for s, r in pairs if r or not HAN.search(s)]


# --- the chunk read aloud --------------------------------------------------
# The punctuation a chunk's text may end with and its reading leave out: ASCII
# punctuation and symbols, Latin-1's, the general punctuation block, and the
# CJK and fullwidth forms.  wordline.lua and wordline.js hold the same ranges,
# so the PDF's aloud pass and the reader's end a chunk on the same marks.
TRAIL = ((0x21, 0x2F), (0x3A, 0x40), (0x5B, 0x60), (0x7B, 0x7E), (0xA1, 0xBF),
         (0x2010, 0x2027), (0x2030, 0x205E), (0x3001, 0x3003), (0x3008, 0x3011),
         (0x3014, 0x301F), (0x30FB, 0x30FB), (0xFF01, 0xFF0F), (0xFF1A, 0xFF20),
         (0xFF3B, 0xFF40), (0xFF5B, 0xFF65))


def _trails(ch):
    c = ord(ch)
    return any(a <= c <= b for a, b in TRAIL)


def trailing(fa):
    """The punctuation that closes `fa`: its longest suffix of TRAIL
    characters, whitespace inside it skipped rather than kept --
    `「おい！ 」 ` gives `！」`."""
    fa, out = fa or "", []
    for ch in reversed(fa):
        if ch.isspace():
            continue
        if not _trails(ch):
            break
        out.append(ch)
    return "".join(reversed(out))


def aloud(reading, fa):
    """One chunk as the aloud pass reads it: its reading, then whatever of
    the text's closing punctuation the reading does not already end with, so
    that `やまへしばかりに` over `山へ柴刈りに、` is `やまへしばかりに、`.  A chunk
    with no reading -- a \\chp, a chunk nobody gave one -- is its text.

    The reading is the chunk's own (kana, or tr where the language has no
    reading), never the words': a kanbun reading reorders them."""
    r = (reading or "").strip()
    if not r:
        return fa or ""
    p = trailing(fa)
    k = len(p)
    while k and not r.endswith(p[:k]):
        k -= 1
    return r + p[k:]


def _kana_key(s):
    s = unicodedata.normalize("NFC", s)
    return "".join(ch for ch in s if not ch.isspace() and not _punct(ch))


def _roman_key(s):
    s = unicodedata.normalize("NFD", s).lower()
    return "".join(ch for ch in s if ch.isascii() and ch.isalnum())


def agrees(pairs, reading, lang):
    """Do the words, read in their written order, say what the chunk's
    reading says -- punctuation and spacing aside, and for a romanised reading
    tones and case too?  None when there is nothing to compare."""
    if not (reading or "").strip() or not pairs:
        return None
    key = _kana_key if lang.reading else _roman_key
    return key("".join(sounds(pairs))) == key(reading)


# Chinese marks as docs/lang/zh.md writes them in tr, which is a Latin line
# and so punctuates in ASCII.  An opening mark is written against the word
# after it, every other mark against the word before.
_LATIN_MARK = {"。": ".", "．": ".", "，": ",", "、": ",", "？": "?", "！": "!",
               "：": ":", "；": ";", "…": "...", "“": '"', "”": '"', "「": '"',
               "」": '"', "‘": "'", "’": "'", "『": "'", "』": "'", "（": "(",
               "）": ")", "《": '"', "》": '"'}
_OPENING = "“‘「『（《〈【〔"


def _latin_marks(s):
    return "".join(_LATIN_MARK.get(ch, ch) for ch in s.replace("……", "…"))


def reading_from(line, lang):
    """The chunk's reading as its words spell it, in written order: the kana
    run together for a language with a reading, the words' pinyin parted by
    spaces for one without.  The punctuation stays where the text has it:
    as written in kana (`やまへしばかりに、`), and in pinyin as the ASCII marks
    tr is written with, each against its word (`tā shuō: "nǐ hǎo!"`).

    What a draft starts a chunk's own reading from (lib/draft.py), and what
    lib/fill_words.py gives a chunk whose reading is still blank -- a proposal
    like the words it comes from.  "" when the line does not parse, or when a
    word written in characters has no reading: a reading with a kanji in it
    would be no reading at all."""
    try:
        pairs = line if isinstance(line, list) else parse(line)
    except WordsError:
        return ""
    kana, out, glued = getattr(lang, "reading", False), "", True
    for s, r in pairs:
        if not r and HAN.search(s):
            return ""
        said = r or "".join(s.split())
        if kana:
            out += said
            continue
        if not r and all(_punct(ch) or _trails(ch) for ch in said):
            opening = all(ch in _OPENING for ch in said)
            out += (" " if opening and not glued else "") + _latin_marks(said)
            glued = opening
            continue
        out += ("" if glued else " ") + (said if r else _latin_marks(said))
        glued = False
    return out


def seed(chunk, lang):
    """(field, reading): the field a draft fills from a chunk's word line --
    "kana" for a language with a reading, "tr" for one without -- and what it
    fills it with.  (None, "") when the chunk has no line to read.

    The checkers ask it so that a reading which still says exactly this is
    not counted as somebody's writing: a draft's chunk is unwritten until a
    person changes something in it."""
    if not getattr(lang, "words", False) or not isinstance(chunk, dict):
        return None, ""
    line = chunk.get("words")
    if not isinstance(line, str) or not line.strip():
        return None, ""
    return ("kana" if lang.reading else "tr"), reading_from(line, lang)


def check(fa, line, lang, reading="", reorders=False, door=BOOK):
    """(errors, warnings) for one chunk's word line: lists of Note, each a
    sentence without a location -- the caller says which chunk -- and a code.

    `reading` is the chunk's own: kana where the language has a reading, tr
    where it has not.  `reorders` is the document's flag for a text read out
    of its written order.  `door` is BOOK or VIDEO: only a book's line lives
    inside a LaTeX argument."""
    errors, warnings = [], []
    if not isinstance(line, str):
        return [Note("type", "words must be text, not %s" % type(line).__name__)], []
    if not getattr(lang, "words", False):
        return [Note("no_layer", "%s has no word layer, so a chunk carries no "
                     "words" % lang.name)], []
    m = NOT_TEXT.search(line)
    if m:
        errors.append(Note("control", "words carries U+%04X at character %d, "
                           "which is not text" % (ord(m.group()), m.start())))
    if door == BOOK:
        bad = sorted({c for c in line if c in TEX_SPECIALS})
        if bad:
            errors.append(Note("tex_special", "words may not contain %s -- LaTeX "
                               "reads it as an instruction"
                               % " ".join(repr(c) for c in bad)))
        if re.search(r"\n[ \t]*\n", line):
            errors.append(Note("blank_line", "a blank line inside words ends the "
                               "paragraph"))
    if errors:
        return errors, warnings
    try:
        pairs = parse(line)
    except WordsError as e:
        return [Note(e.code, str(e))], warnings
    if not pairs:
        return [Note("empty", "words is empty -- a chunk without words is "
                     "written without the field")], warnings
    got = norm((lang.word_sep or "").join(s for s, _ in pairs), lang)
    want = norm(fa, lang)
    if got != want:
        return [Note("reproduce", "the words do not reproduce the text: "
                     + _diff(got, want))], warnings

    for s, r in pairs:
        if not r and HAN.search(s) and not reorders:
            warnings.append(Note("no_reading", "%s has no reading" % s))
        if r and lang.reading and not lang.is_reading(r):
            warnings.append(Note("reading_script", "the reading of %s, %r, is not "
                                 "written in %s" % (s, r, lang.reading_label or
                                                    "the reading's script")))
        if r and not lang.reading and lang.has_script(r):
            warnings.append(Note("reading_script", "the reading of %s, %r, has %s "
                                 "characters in it" % (s, r, lang.name)))
        tail = _HIRA_TAIL.search(s)
        if lang.reading and r and tail and HAN.search(s) and not r.endswith(tail.group()):
            warnings.append(Note("okurigana", "%s(%s): the reading should cover the "
                                 "whole word, ending with its okurigana %s"
                                 % (s, r, tail.group())))
        if _SCRIPT.search(s) and any(_punct(ch) for ch in s):
            warnings.append(Note("punctuation", "%s runs punctuation into a word: "
                                 "the punctuation is a word of its own" % s))
    if not reorders and agrees(pairs, reading, lang) is False:
        said = ("" if lang.reading else " ").join(sounds(pairs))
        warnings.append(Note("disagrees", "the words read %r and the chunk's "
                             "reading is %r: a text read out of its written order "
                             "(kanbun) is marked \"reorders\": true, and anything "
                             "else is a reading to correct" % (said, reading)))
    return errors, warnings


# --- dividing a chunk ------------------------------------------------------
def divide(line, a_fa):
    """A chunk's line cut after the text `a_fa`: (first, second, notes).

    A cut between two words divides the line exactly.  A cut inside a word
    divides its characters, keeps the whole reading on the first half, and
    says so -- the rule lib/chunkdiv.py already follows for a chunk's kana."""
    pairs = parse(line)
    target = len("".join((a_fa or "").split()))
    first, second, notes, count = [], [], [], 0
    for s, r in pairs:
        if count >= target:
            second.append((s, r))
        elif count + len(s) <= target:
            first.append((s, r))
        else:
            m = target - count
            first.append((s[:m], r))
            second.append((s[m:], ""))
            if r and HAN.search(s[m:]):
                notes.append("the chunk was cut through %s: its reading stayed "
                             "with %s, and %s needs one of its own"
                             % (s, s[:m], s[m:]))
        count += len(s)
    return render(first), render(second), notes


if __name__ == "__main__":
    import sys
    for arg in sys.argv[1:]:
        try:
            print(parse(arg))
        except WordsError as e:
            print("%s: %s" % (e.code, e))
