#!/usr/bin/env python3
"""Check one video's annotations, the way check_batch.py checks a book batch.

    python3 lib/check_annotations.py videos/<folder>/<id>

It proves, mechanically, what a machine can prove:

  * video.json and annotations.json parse and carry the required fields
  * caption starts are strictly increasing
  * FIDELITY: for every caption, its chunks joined with the language's word
    separator (a space; nothing for Japanese) reproduce the caption text
    word for word (the language's marks --
    harakat for Persian and Arabic -- are stripped from both sides first,
    so vocalising a chunk cannot break the test -- which also means a
    POINTING error is invisible to it, exactly as in the book pipeline:
    that still needs a reader)
  * the captions equal transcript.txt's, in order, down to their chapter
    headings and their plain marks
  * every chunk carries what its language requires: the meaning, the
    transliteration where the language wants one, the kana reading where
    the language has one (lib/languages.json decides)
  * a chunk's word line ("words", for a language divided into words:
    lib/wordline.py) gives its text back word for word; that its readings
    say what the chunk's own reading says is only a warning, and is not
    asked of a video whose video.json says "reorders": true
  * a chunk that carries a colour carries one of the four the books mark
    a chunk with -- red, blue, orange, green, and nothing else

A VIDEO STILL BEING ANNOTATED says so: video.json carries "draft": true,
which lib/draft.py writes when it makes an annotation out of nothing but the
transcript (one chunk per sentence of each caption, every gloss blank).  Such
a file would fail this checker on the day it was made, so a chunk with
NOTHING written in it -- no tr, no voc, no en, no kana -- is then counted and
passed over.  One field written makes it a chunk somebody is working on, and
everything its language requires is required again: a meaning with no
transliteration beside it, where the language wants one, is exactly the
half-done work this file exists to catch, and it stays an error draft or no
draft.  The flag is in video.json and not in annotations.json because
merge_parts.py rewrites the annotations from the parts and would drop it.

The language is video.json's "language" (a registry code; content written
before languages were declared is Persian).  Nothing here names a script,
a digit or a word of any language: the registry is asked.

A video declares a SECOND language: video.json's "gloss", the one its
meanings are WRITTEN in -- an Italian learning English wants them in
Italian.  Absent means English, which is what every video written before
the field existed means, so nothing here changes for any of them.  It is
checked and nothing else: no rule in this file reads what a gloss SAYS,
only that it is there (see check_chunk), so the gloss language cannot
make a check right or wrong -- but a code this toolbox cannot set would
reach the player, the prompt and the Anki card as a silent English, and
that is the error below.

Exit code 0 only when there are no errors.  Standard library only.
"""
import json
import os
import re
import sys
import unicodedata

LIB = os.path.dirname(os.path.realpath(__file__))
TOOLBOX_LIB = os.path.join(os.path.dirname(os.path.dirname(LIB)), "lib")
if TOOLBOX_LIB not in sys.path:
    sys.path.insert(0, TOOLBOX_LIB)
import languages  # noqa: E402  the registry: scripts, digits, duration words
import wordline   # noqa: E402  the word line's grammar, the books' as well

# A caption's clock line: "8:07", "1:02:03" -- and, since the add page's
# editor can move a caption by a tenth of a second, an optional fraction
# after it ("0:08.4", or "0:08,4" as a comma-writing keyboard types it).  A
# panel pasted from YouTube never carries one, and a transcript written
# before this read the same then as it does now.
TIMESTAMP = re.compile(r"^(\d+):(\d\d)(?::(\d\d))?(?:[.,](\d{1,3}))?$")
# The human line YouTube's transcript view puts under a timestamp, in
# whatever language the panel was copied under: Italian ("1 minuto e 6
# secondi"), English, Persian ("6 ثانیه", "1 دقیقه و 3 ثانیه"), Japanese
# ("1 分 6 秒").  Every language's units MUST be listed: a unit written in
# the target script would otherwise pass the plain-text test as speech and
# glue the duration onto the caption.  The units of the languages the
# toolbox teaches come from the registry (duration_units); the English and
# Italian ones are here because a panel is often copied under the browser's
# own locale, whatever the video speaks.  Digits may be Latin or any
# language's own (languages.digit_class), or full-width ("１分６秒", as a
# Japanese panel may be set).  A chapter line, which is what the uploader
# typed, may also number itself with kanji ("第一章", "第十二章"); the
# duration line may not, so that a caption that IS a kanji number and a
# unit ("十分", enough) is never swallowed as one.  Full-width digits and
# kanji numerals are Unicode's other spellings of a number, not a
# language's digit table: the registry's, which writes labels, stays
# Latin for Japanese, and these classes only READ.
_FULLWIDTH = "０-９"
_KANJI_NUM = "〇一二三四五六七八九十百"
_DUR_NUM = r"[%s%s]+" % (languages.digit_class(), _FULLWIDTH)
_CHAP_NUM = r"[%s%s%s]+" % (languages.digit_class(), _FULLWIDTH, _KANJI_NUM)
_UNITS = ["secondi", "secondo", "seconds", "second", "minuti", "minuto",
          "minutes", "minute", "ore", "ora", "hours", "hour"]
for _L in languages.LANGS.values():
    _UNITS += _L.duration_units
# longest first, so "minuti" is never cut to "minut" + a stray letter
_DUR_UNIT = "|".join(re.escape(u) for u in
                     sorted(set(_UNITS), key=lambda u: (-len(u), u)))
# The conjunction between the two parts, in the panel's own language, and
# optional: Japanese and Turkish juxtapose ("1 分 6 秒", "1 dakika 6
# saniye"), the rest join ("1 minuto e 6 secondi", "1 minute et 6
# secondes", "1 Minute und 6 Sekunden", "۱ دقیقه و ۳ ثانیه").  These are
# words of the INTERFACE, not of a language the toolbox teaches -- the
# registry has no field for them, and would not be asked anyway, since the
# panel is usually copied under the browser's locale whatever the video
# speaks.  Longest first, so "und" is never cut to "un".
_DUR_JOIN = ("und", "and", "et", "e", "y", "و")
DURATION = re.compile(
    r"^%s\s*(?:%s)(?:\s*(?:%s)?\s*%s\s*(?:%s))?\s*$"
    % (_DUR_NUM, _DUR_UNIT, "|".join(_DUR_JOIN), _DUR_NUM, _DUR_UNIT), re.I)
# YouTube's chapter marker, as the uploader typed it, in whatever language
# the panel was copied under.  It belongs to the caption that FOLLOWS it,
# never to the one before.  The chapter words of the taught languages come
# from the registry (chapter_words); a word may also follow the number, as
# Japanese does ("第3章: …"), and the number may be in the language's
# digits, full-width or kanji (_CHAP_NUM).
#
# Two orders, because Turkish counts the other way round: "Bölüm 3 — …" as
# every other language does, and "3. Bölüm: …", which is the commoner
# Turkish spelling.  The number-first form demands the ORDINAL point after
# the number, and that point is the whole of what tells a marker from
# speech: "۴ فصل: بهار، تابستان، پاییز و زمستان" is Persian for "four seasons:
# spring, summer, autumn, winter", and Arabic and Italian count the same
# way ("2 capitoli: il primo e il secondo").  Mistaking one for a marker
# is silent and expensive -- the line is deleted from the transcript and
# its tail retitles the caption after it -- so a bare cardinal in front of
# the word stays speech, and only "3." is a chapter.
_CHAP_WORDS = ["capitolo", "chapter", "capítulo", "capitulo", "kapitel",
               "chapitre", "глава"]
for _L in languages.LANGS.values():
    _CHAP_WORDS += _L.chapter_words
_CHAP_WORD = "|".join(re.escape(w) for w in
                      sorted(set(_CHAP_WORDS), key=lambda w: (-len(w), w)))
# the separator carries the em dash as well as the en dash: "Chapitre 4 —
# Le prince" is how a French or German title is typed, and it was the one
# dash the class did not have
CHAPTER = re.compile(
    r"^(?:(?:%s)\s*%s\s*(?:%s)?|%s\.\s*(?:%s))\s*[:：.．—–-]\s*(.+)$"
    % (_CHAP_WORD, _CHAP_NUM, _CHAP_WORD, _CHAP_NUM, _CHAP_WORD), re.I)

# A chunk's highlight: the reader's own mark on a phrase, the same four
# colours a book passes as the first argument of \ch and the reading page
# paints as hl-red ... hl-green (HL in lib/tex2html.py).  Absent or empty
# means unmarked.  A fifth name is an ERROR and not a warning: the player
# would paint it as nothing at all, so a typo would lose the mark without
# saying a word, and the reader would blame the click.
#
# The colour does NOT go into the Anki card a chunk makes, and that is a
# decision, not an omission.  The book door already drops it: collectCard
# in lib/tex2html.py gathers fa, kana, tr, en, context, notes, tags and
# the source, never hl_class, so a red chunk in a reading edition makes
# the same card a black one does.  anki_export.note_fields has no field
# to put a colour in either, and cannot grow one -- a note type that
# changes shape stops updating the notes already studied with it
# (youtube/anki/README.md), so a Colour field would fork every deck in
# the toolbox for a mark that means nothing to Anki.  And the mark is a
# pass-1 thing in the books: what the reader noticed BEFORE any help
# arrived.  A card is the help.  Both doors leave the colour on the page.
COLOURS = ("red", "blue", "orange", "green")

# "col" is last because it is the one field nothing in the pipeline ever
# writes: an annotator does not colour a chunk and merge_parts copies no
# such key -- a reader adds it later, from the player.  "words" stands next
# to "fa" because it is nothing but fa divided (lib/wordline.py).
CHUNK_FIELDS = ("fa", "words", "kana", "tr", "voc", "en", "note", "plain", "col",
                "free")


def lang_code(value):
    """video.json's "language" as the string the registry is asked for: the
    code itself, "" when the field is missing, and a malformed value (a
    number, a list) spelled out -- so that it is reported as an unknown
    language, like every other bad field, instead of crashing the tool
    (languages.get strips the code, and a number has nothing to strip)."""
    if value is None:
        return ""
    return value if isinstance(value, str) else str(value)


def lang_of(code):
    """The Lang record for a code, or the default (Persian) -- accepts a
    Lang already looked up, so a caller may pass either."""
    if isinstance(code, languages.Lang):
        return code
    return languages.get_or_default(lang_code(code))


def unwritten(ch, lang=None):
    """True when not one part of this chunk's gloss has been written.

    The vocabulary counts even though no language requires it: a field
    somebody has typed into is a chunk somebody is working on, and from
    then on everything the language asks for is asked for.  A value that
    is not text at all counts as written -- wrongly written -- so the
    checks below still report it.  This is the only kind of chunk a draft
    is forgiven.

    Given the video's language, the reading a draft gave the chunk from its
    words (wordline.seed) is not counted while it still says exactly that:
    nobody wrote it.
    """
    field, seeded = wordline.seed(ch, lang_of(lang)) if lang is not None else (None, "")
    for f in ("tr", "voc", "en", "kana"):
        v = ch.get(f)
        if v is None:
            continue
        if not isinstance(v, str):
            return False
        if v.strip() and not (f == field and seeded and v.strip() == seeded):
            return False
    return True


def norm(s, lang=None):
    """The comparable form: NFC, the language's stripped marks gone (harakat
    for Persian and Arabic; nothing for the others), whitespace collapsed.
    For a language without a word separator (Japanese) whitespace is
    dropped altogether: YouTube's Japanese captions carry spaces at
    phrase boundaries or not at random, chunks are joined with nothing,
    and a space is never a letter there."""
    L = lang_of(lang)
    s = unicodedata.normalize("NFC", s)
    s = L.strip(s)
    if not L.spaced:
        return re.sub(r"\s+", "", s)
    return re.sub(r"\s+", " ", s).strip()


def to_seconds(m):
    """A TIMESTAMP match as seconds: an int where the line carried no
    fraction, so every transcript written before fractions existed still
    parses to exactly the numbers it always did."""
    if m.group(3) is not None:
        whole = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
    else:
        whole = int(m.group(1)) * 60 + int(m.group(2))
    if m.lastindex is None or m.group(m.re.groups) is None:
        return whole
    frac = m.group(m.re.groups)
    return round(whole + int(frac) / 10.0 ** len(frac), 3)


def parse_transcript(path, language="fa"):
    """[{start, text, chapter, plain}] from a pasted YouTube transcript.

    A block is a timestamp line, then optionally the spoken-duration line
    ("1 minuto e 6 secondi"), then the caption's text line(s).

    For a SCRIPT language (Persian, Arabic, Japanese) a caption with not
    one letter of the target script -- the framing these teaching videos
    open with, English in most of them -- is marked PLAIN: it is shown as
    it stands and never glossed, so nobody has to invent a transliteration
    for "welcome to a new session".  Mixed captions are not plain; their
    foreign runs are glossed chunk by chunk, or left bare (see
    check_chunk).

    For a LATIN-script target nothing is plain automatically -- French or
    Turkish cannot be told from English by its letters, and English is
    itself a target here -- so every caption wants glossing, and an aside
    in another language is a chunk the annotator marks "plain": true.

    The test is the TARGET script and only that, so the video's gloss
    language does not enter it: a caption is plain because it is not the
    language being taught, never because of what it is instead.
    """
    with open(path, encoding="utf-8") as f:
        return parse_transcript_text(f.read(), language)


def parse_transcript_text(text, language="fa"):
    """parse_transcript, of text already in hand.

    The add page edits a transcript before anything is built from it, and
    a transcript being edited is a string and not yet a file; every rule
    about what a block is lives here, so that door and the pipeline read
    one pasted panel the same way.  transcript_text writes them back.
    """
    L = lang_of(language)
    out = []
    cur = None            # {"start":…, "lines":[…], "chapter":…}
    pending = None        # a chapter title waiting for its caption

    def flush():
        if cur and cur["lines"]:
            said = " ".join(cur["lines"])
            out.append({"start": cur["start"], "text": said,
                        "chapter": cur["chapter"],
                        "plain": bool(L.chars is not None and not L.has_script(said))})

    for raw in (text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw.strip()
        if not line:
            continue
        m = CHAPTER.match(line)
        if m:
            pending = m.group(1).strip()
            continue
        m = TIMESTAMP.match(line)
        if m:
            flush()
            cur = {"start": to_seconds(m), "lines": [],
                   "chapter": pending}
            pending = None
            continue
        if cur is None:
            continue                          # preamble before the first stamp
        if not cur["lines"] and DURATION.match(line):
            continue                          # the "N secondi" line
        cur["lines"].append(line)
    flush()
    return out


def stamp_of(seconds):
    """A caption's start as a transcript line writes it: `8:07`, `1:02:03`
    once there is an hour, and `8:07.4` where the start is not a whole
    second.

    The fraction is written ONLY when there is one, to a thousandth and
    with no trailing zeros, so a panel of whole seconds -- which is every
    panel YouTube ever pasted -- is written back exactly as it came.  It is
    a pasted panel that has no fractions, not this format: TIMESTAMP reads
    one, and the add page's editor makes them (a tenth of a second at a
    time)."""
    t = max(0.0, round(float(seconds or 0), 3))
    n = int(t)
    frac = round(t - n, 3)
    if frac >= 0.9995:                       # 8.9999 is nine seconds
        n, frac = n + 1, 0.0
    if n >= 3600:
        out = "%d:%02d:%02d" % (n // 3600, (n // 60) % 60, n % 60)
    else:
        out = "%d:%02d" % (n // 60, n % 60)
    if frac:
        out += ("%.3f" % frac)[1:].rstrip("0")
    return out


def transcript_text(captions):
    """[{start, text, chapter}] back as a pasted panel.

    The other half of parse_transcript_text, and its inverse: what this
    writes, that reads, and gives these captions back.  A chapter is
    written as the line the panel puts before the caption it opens, in the
    plainest of the forms CHAPTER reads.  Nothing else is written -- the
    spoken-duration line is the panel's own noise and no transcript here
    needs it, and `plain` is not written at all because it is worked out
    from the text (a caption is plain because it is not the language being
    taught, never because a file said so).
    """
    out, n = [], 0
    for c in captions or []:
        if not isinstance(c, dict):
            continue
        chapter = " ".join((c.get("chapter") or "").split())
        said = " ".join((c.get("text") or "").split())
        if not said:
            continue                          # a caption with no words is none
        if chapter:
            # CHAPTER wants a number, and the number is the WRITER'S: what
            # a chapter line means here is its title, which is all the
            # parse keeps, so counting them in order gives back exactly
            # what was read even where the panel numbered them otherwise
            n += 1
            out.append("Chapter %d: %s" % (n, chapter))
        out.append(stamp_of(c.get("start")))
        out.append(said)
    return "\n".join(out) + ("\n" if out else "")


def check_chunk(ch, where, err, warn, lang=None, draft=False, reorders=False):
    """One chunk's own fields.

    A chunk of the target language must carry its meaning (en), its
    transliteration (tr) where the language wants one (require_tr), and
    its reading (kana) where the language has one (reading).  For a script
    language a chunk with no target script at all is a run of the video's
    own framing -- glossing "welcome to" would be noise, so only the text
    itself is required there.  For a Latin-script target every chunk is
    target text unless it says otherwise.

    `en` is required, never read: what a meaning must SAY is the business
    of whoever proofreads it, and it is said in the video's gloss
    language, which may be any prose language (video.json's "gloss").  So
    the only rules here that look at a script are about the TARGET's --
    which caption is plain, and the warning below about it turning up in
    a transliteration -- and none of them changes with the gloss.

    A chunk marked "plain": true is target text deliberately left
    unglossed: for a script language it comes only from an import of the
    older format (an annotator never writes it; a chunk that merely forgets
    its gloss is still an error); for a Latin-script target it is how an
    aside in another language is told from the target language around it,
    and the annotator IS allowed to write it.  Either way it is shown as
    text, never a target, and asked for nothing.

    "col" is checked before any of that, because the mark is on the
    phrase and not on the gloss: a plain chunk is as markable as a
    glossed one, and the plain branch below returns before the
    unknown-field sweep at the end ever runs.

    With `draft` a chunk nobody has written any part of the gloss of
    (`unwritten`) is asked for nothing -- not the fields its language
    requires, and not the chunk length either, since a draft's chunk is a
    whole sentence and "%d words in one chunk" would then be certain in
    advance of every chunk in the file.  A warning that cannot fail
    teaches its reader to skip warnings.  The colour, the text and the
    unknown-field sweep are checked in a draft exactly as anywhere else.

    A chunk somebody has half written -- the meaning typed, the
    transliteration not yet -- is SAID in a draft and not refused.  That is
    what the middle of the work looks like, it is what the player's own
    editor writes, and refusing it left a draft that could not come back
    through the bundle door it had gone out of.  Without the flag it is an
    error, as it always was.

    "words", the word line, is on the phrase too and is checked with the
    colour, in a draft as well: present, it is text that gives `fa` back
    (lib/wordline.py; a blank one is an error, since a chunk without words
    has no key), and a chunk marked plain has none.  The line is compared
    with the chunk's own reading -- kana where the language has one, tr
    where it has not -- only to warn, and not at all for `reorders`,
    video.json's flag for a text read out of its written order.  A draft's
    blank reading has nothing to compare, so nothing is said.
    """
    L = lang_of(lang)
    fa = ch.get("fa")
    if not isinstance(fa, str) or not fa.strip():
        err("%s: missing 'fa'" % where)
        return 0
    words = len(L.split_words(fa))
    col = ch.get("col")
    if col not in (None, "") and col not in COLOURS:
        err("%s: colour %r is not one of %s"
            % (where, col, ", ".join(COLOURS)))
    # "free": this chunk does not reproduce transcript.txt.  The pasted
    # transcript is what YouTube heard, and it is sometimes wrong: a chunk
    # marked here may be corrected, and its caption is no longer held against
    # the transcript (check_segments, departs).  True, or not written at all
    if "free" in ch and ch["free"] is not True:
        err("%s: 'free' is true or is not written at all" % where)
    if "words" in ch:
        if ch.get("plain"):
            err("%s: a chunk marked plain carries no words" % where)
        else:
            reading = ch.get("kana" if L.reading else "tr")
            bad, doubt = wordline.check(
                fa, ch["words"], L, reading if isinstance(reading, str) else "",
                reorders, wordline.VIDEO)
            for n in bad:
                err("%s: %s" % (where, n))
            for n in doubt:
                warn("%s: %s" % (where, n))
    if ch.get("plain"):
        return words
    is_target = L.has_script(fa) if L.chars else True
    if is_target and not (draft and unwritten(ch, L)):
        need = ["en"]
        if L.require_tr:
            need.insert(0, "tr")
        if L.reading:
            need.insert(0, "kana")
        for field in need:
            v = ch.get(field)
            if not isinstance(v, str) or not v.strip():
                # A DRAFT IS UNFINISHED BY DEFINITION, and half-finished is
                # what the middle of the work looks like: the meanings of a
                # caption typed in one pass and the transliterations in the
                # next.  The player's own editor writes exactly that -- it
                # checks an edit WITHOUT this flag on purpose (annwrite says
                # why), so typing a meaning into a blank chunk stands -- and
                # a video it refused here could never come back through the
                # bundle door it had just gone out of (lib/bundle.py raises
                # on an error and only notes a warning).  So in a draft this
                # is said and not refused; the moment "draft" comes off
                # video.json it is an error again, which is what the flag is
                # for.  Nothing else here softens: the text, the colour, the
                # word line and the chunks reproducing their caption are
                # checked in a draft exactly as anywhere else.
                if draft:
                    warn("%s: missing %r -- still a draft" % (where, field))
                else:
                    err("%s: missing %r" % (where, field))
        if L.chars and isinstance(ch.get("tr"), str) and L.has_script(ch["tr"]):
            warn("%s: %s script inside tr" % (where, L.name))
        if words > 7:
            warn("%s: %d words in one chunk" % (where, words))
    for field in ch:
        if field not in CHUNK_FIELDS:
            warn("%s: unknown field %r" % (where, field))
    return words


def departs(seg):
    """Does this caption hold a chunk marked as departing from the
    transcript?  Then the transcript is no longer what its text is held
    against: the words are the annotator's (check_segments, annwrite).  It
    is asked of the CAPTION because the check is of the caption: every
    chunk is joined before the text is compared, so one chunk departing
    takes its caption with it -- the reading editions' own rule, where a
    chunk taken charge of takes its paragraph (lib/reading.py)."""
    return any(isinstance(ch, dict) and ch.get("free") is True
               for ch in (seg.get("chunks") or []))


def check_segments(segs, captions, err, warn, lang=None, draft=False,
                   reorders=False):
    """The annotations against the transcript.  Returns (chunks, words).

    `draft` is video.json's flag, passed on to check_chunk, and so is
    `reorders`, which only ever quiets a warning.  The return is
    deliberately still the pair it always was: lib/bundle.py and
    youtube/lib/annwrite.py both call this, and the second one calls it
    twice round an edit and refuses whatever the edit INTRODUCED -- which
    is why annwrite must go on calling it WITHOUT the flag.  Under the
    strict rule a blank chunk's missing 'tr' is already there before the
    edit, so typing the English into it introduces nothing and the edit
    stands; tell annwrite about the draft and that same edit would be
    refused, because the chunk would pass from forgiven to half-written.
    """
    L = lang_of(lang)
    nch = nw = 0
    prev = -1.0
    for i, sg in enumerate(segs):
        where = "segment %d (start %s)" % (i, sg.get("start"))
        start = sg.get("start")
        if not isinstance(start, (int, float)) or start < 0:
            err("%s: bad start" % where)
        elif start < prev:
            # equal is legal and happens: YouTube shows a laugh and the
            # gasp after it as two captions in the same displayed second
            err("%s: start goes backwards (previous %s)" % (where, prev))
        if isinstance(start, (int, float)):
            prev = start
        text = sg.get("text")
        if not isinstance(text, str) or not text.strip():
            err("%s: no text" % where)
            continue
        if sg.get("plain"):
            # not the target language: shown as it stands, never glossed
            if sg.get("chunks"):
                err("%s: a plain caption must carry no chunks" % where)
            continue
        chunks = sg.get("chunks")
        if not isinstance(chunks, list) or not chunks:
            err("%s: no chunks" % where)
            continue
        for j, ch in enumerate(chunks):
            if not isinstance(ch, dict):
                err("%s chunk %d: not an object" % (where, j))
                continue
            nw += check_chunk(ch, "%s chunk %d" % (where, j), err, warn, L, draft,
                              reorders)
        nch += len(chunks)
        joined = norm(L.word_sep.join(
            (ch.get("fa") or "") if isinstance(ch, dict) else ""
            for ch in chunks), L)
        want = norm(text, L)
        if joined != want:
            k = next((n for n, (a, b) in enumerate(zip(joined, want))
                      if a != b), min(len(joined), len(want)))
            err("%s: chunks do not reproduce the text\n"
                "    text:   ...%s...\n"
                "    chunks: ...%s..." % (where, want[max(0, k-20):k+20],
                                          joined[max(0, k-20):k+20]))

    if captions is not None:
        free = 0
        if len(captions) != len(segs):
            err("transcript.txt has %d captions, annotations %d"
                % (len(captions), len(segs)))
        for i, (cap, sg) in enumerate(zip(captions, segs)):
            if isinstance(sg.get("start"), (int, float)) and \
               abs(sg["start"] - cap["start"]) > 0.51:
                err("segment %d: start %s but transcript says %s"
                    % (i, sg["start"], cap["start"]))
            if departs(sg):
                free += 1
            elif norm(sg.get("text") or "", L) != norm(cap["text"], L):
                err("segment %d: text differs from transcript.txt\n"
                    "    transcript: %s\n"
                    "    annotation: %s" % (i, cap["text"], sg.get("text")))
            if bool(sg.get("plain")) != cap["plain"]:
                err("segment %d: plain is %r, transcript says %r"
                    % (i, bool(sg.get("plain")), cap["plain"]))
            if (sg.get("chapter") or None) != cap["chapter"]:
                err("segment %d: chapter %r, transcript says %r"
                    % (i, sg.get("chapter"), cap["chapter"]))
        if free:
            warn("%d caption%s not checked against transcript.txt: a chunk of "
                 "each is marked as departing from it" % (free, "" if free == 1 else "s"))
    return nch, nw


def video_language(vdir, meta=None, ann=None, warn=None):
    """The video's language: video.json's "language", else annotations.json's,
    else the default.  The folder the video sits in is expected to agree
    (videos/japanese/ holds "ja" videos); a disagreement is reported once,
    and the JSON wins, as docs/languages.md says."""
    declared = lang_code((meta or {}).get("language"))
    code = declared or lang_code((ann or {}).get("language")) or languages.DEFAULT
    L = languages.get_or_default(code)
    if declared and code.strip().lower() not in languages.LANGS and warn:
        warn("video.json: unknown language %r -- taken as %s"
             % ((meta or {}).get("language"), L.name))
    by_dir = languages.detect_from_path(vdir)
    if warn and by_dir and by_dir.code != L.code:
        warn("filed under videos/%s/ but video.json says language %s (videos/%s/)"
             % (by_dir.folder, L.code, L.folder))
    return L


def video_gloss(meta=None, err=None):
    """The language this video's glosses are WRITTEN in: video.json's
    "gloss", English when it says nothing.

    Refused rather than fallen back on, which is where it parts company
    with video_language above.  A wrong "language" is loud: the video is
    filed under the wrong folder, set in the wrong font, and its captions
    all come out plain -- somebody sees it the hour it is written, so a
    warning is enough and the folder check catches the rest.  A wrong
    "gloss" is silent: the page looks exactly right, and the meanings are
    merely hyphenated, spoken and laid out as a language they are not, for
    the rest of the video's life.  So `err` is told, in the registry's own
    sentence (which lists what a gloss may be written in), and the return
    is English so that everything else in the file is still checked.

    Only video.json is asked, never annotations.json: merge_parts.py
    rewrites the annotations from the parts and would drop the field, which
    is the reason "draft" lives in the metadata too.
    """
    raw = (meta or {}).get("gloss")
    try:
        return languages.gloss(lang_code(raw) or None)
    except KeyError as e:
        if err:
            err("video.json: %s" % (e.args[0] if e.args else e))
        return languages.gloss(None)


def _read_json(vdir, name):
    try:
        with open(os.path.join(vdir, name), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def draft_state(vdir):
    """(draft, blank, glossable) for a video directory: whether video.json
    says "draft": true, how many chunks have no gloss written at all, and how
    many were asked for one in the first place.

    Its own small read of the two files, because check() returns the triple
    lib/bundle.py unpacks and that shape is not worth changing for a line the
    command line prints.  A page that wants to badge a draft asks this too.

    Only the chunks check_chunk would ask a gloss of are counted: a plain
    caption's, a chunk marked plain, and -- for a script language -- a chunk
    with none of the script in it are all legitimately blank in a finished
    file, and counting them would make the note below say that a video which
    reports no errors at all has unwritten chunks in it.
    """
    meta = _read_json(vdir, "video.json") or {}
    ann = _read_json(vdir, "annotations.json") or {}
    L = video_language(vdir, meta, ann)
    blank = total = 0
    for sg in ann.get("segments") or []:
        if not isinstance(sg, dict) or sg.get("plain"):
            continue
        for ch in sg.get("chunks") or []:
            if not isinstance(ch, dict) or ch.get("plain"):
                continue
            fa = ch.get("fa")
            if not isinstance(fa, str) or not fa.strip():
                continue
            if L.chars and not L.has_script(fa):
                continue            # a run of the video's own framing
            total += 1
            if unwritten(ch, L):
                blank += 1
    return bool(meta.get("draft")), blank, total


def check(vdir):
    errors, warnings = [], []
    err, warn = errors.append, warnings.append

    meta = None
    mpath = os.path.join(vdir, "video.json")
    try:
        with open(mpath, encoding="utf-8") as f:
            meta = json.load(f)
    except OSError:
        err("%s: missing" % mpath)
    except ValueError as e:
        err("%s: not JSON (%s)" % (mpath, e))
    vid = os.path.basename(os.path.normpath(vdir))
    if meta:
        if not meta.get("id"):
            err("video.json: no \"id\"")
        elif meta["id"] != vid:
            warn("video.json id %r differs from directory name %r"
                 % (meta["id"], vid))
        if meta.get("id") and meta.get("url") and meta["id"] not in meta["url"]:
            warn("video.json: url does not contain the id")

    apath = os.path.join(vdir, "annotations.json")
    ann = None
    try:
        with open(apath, encoding="utf-8") as f:
            ann = json.load(f)
    except OSError:
        err("%s: missing" % apath)
    except ValueError as e:
        err("%s: not JSON (%s)" % (apath, e))
    if ann is None:
        return errors, warnings, (0, 0, 0)

    segs = ann.get("segments")
    if not isinstance(segs, list) or not segs:
        err("annotations.json: \"segments\" missing or empty")
        return errors, warnings, (0, 0, 0)
    if meta and ann.get("video") not in (None, meta.get("id")):
        warn("annotations.json \"video\" %r != video.json id" % ann.get("video"))

    # video.json's "draft": the annotation is being written, so a chunk
    # nobody has touched yet is counted and passed over (see the header)
    draft = bool((meta or {}).get("draft"))
    # and "reorders": a text read out of its written order, whose words are
    # not held to the chunk's reading (lib/wordline.py)
    reorders = bool((meta or {}).get("reorders"))
    L = video_language(vdir, meta, ann, warn)
    # the gloss language is checked here and used nowhere below: no rule
    # reads a meaning, only that there is one, so this is the one place a
    # code nobody can set is caught before the player and the card believe it
    video_gloss(meta, err)
    tpath = os.path.join(vdir, "transcript.txt")
    captions = None
    if os.path.exists(tpath):
        captions = parse_transcript(tpath, L)
    else:
        warn("no transcript.txt to check against")

    nch, nw = check_segments(segs, captions, err, warn, L, draft, reorders)
    return errors, warnings, (len(segs), nch, nw)


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    vdir = sys.argv[1]
    if not os.path.isdir(vdir):
        sys.exit("not a directory: %s" % vdir)
    errors, warnings, (ns, nc, nw) = check(vdir)
    for w in warnings:
        print("warning: %s" % w)
    for e in errors:
        print("ERROR: %s" % e)
    # said only when it is not English, so the line every video in the
    # toolbox today prints is the line it has always printed
    G = video_gloss(_read_json(vdir, "video.json"))
    if G.code != languages.DEFAULT_GLOSS:
        print("note: the meanings are written in %s (video.json's \"gloss\")"
              % G.name)
    draft, blank, glossable = draft_state(vdir)
    if draft:
        print("note: video.json says \"draft\": true -- %s"
              % ("%d of %d chunks wanting a gloss have none written yet, and "
                 "a chunk half written is a warning above and not an error "
                 "either: take the flag off video.json and every one of them "
                 "is an error again"
                 % (blank, glossable) if blank else
                 "every chunk is glossed; the flag can go"))
    elif blank:
        print("note: %d of %d chunks wanting a gloss have none at all, and "
              "each is an error above.  An annotation being written says so "
              "with \"draft\": true in video.json."
              % (blank, glossable))
    print("%d captions, %d chunks, %d words -- %d error(s), %d warning(s)"
          % (ns, nc, nw, len(errors), len(warnings)))
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
