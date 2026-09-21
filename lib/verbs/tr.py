"""Turkish: the \\vb a dictionary hit for a verb offers.

    \\vb{gitmek}{}{gidiyor}{}{gider}{}{to go}
    \\vb{bakmak}{}{bakıyor}{}{bakar}{}{to look at (-e)}
    \\vb{etmek}{}{ediyor}{}{eder}{}{}      in `teşekkür ederim`, with the \\bw
                                         for teşekkür named in `missing`

docs/lang/tr.md says what goes in, and nothing here adds to it: the -mek/-mak
infinitive, the present in -iyor and the aorist -- both the bare third person
singular -- with all three sound slots EMPTY, because the spelling already
says how each form is said; then the meaning, and after it, in one
parenthesis, the case the verb's complement takes -- (-e), (-i), (-den),
(-de), (ile) -- where the dictionary says so.

WHERE EACH FORM COMES FROM, all of it rows the source wrote:

    aorist      the head line's row, which wiktextract names `present
                singular third-person` (the tr-verb head's one argument);
                else the conjugation table's cell; else the page that is
                only "aorist of X" (_forms)
    -iyor       the conjugation table's cell; else the page that is only
                "present of X"; else the table of a homograph whose aorist
                is this one (_twins_present)
    compound    the light verb's own entry (_compound_forms)
    government  the tags of the sense the gloss uses (lookup.rank_senses's
                first), `with-dative` and the like, which lib/getdict.py
                reads out of the qualifier Wiktionary writes as prose

Measured on the whole extract (2 560 verb lemmas, 1 817 of them one word):
every one but the copula gets a \\vb; 1 627 single-word verbs have both
forms, and 732 of the 743 compounds; 78 carry a government.

A ROW IS PICKED BY WHAT IT IS, NEVER BY ITS PERSON TAGS, because those are
wrong in every Turkish table in the extract (2 101 of 2 101, measured on the
research pass): getdict drops the marker rows that open each block of a
tr-conj table, and every cell after them is labelled one place late --
`gelirim`, the first person, is `aorist singular third-person`, and `geliyor`,
the third, is `continuative plural second-person`.  Asking for the tags a
third person should have finds the first person.  What a third person
singular IS, though, can be read off the row itself: it is the one cell of
its tense that has no personal ending, the stem and the tense and nothing
else -- gel + ir, gel + iyor.  So a cell is taken when it is exactly that
(_aorist_of, _present_of), which is a test the row passes or fails, never a
form this file makes: what is printed is always the source's own spelling.
That test is also what keeps out the cells tagged the same way -- the
potential gelebilir and gelebiliyor, the impotential gelemez and gelemiyor
(neither tagged `negative`), bilmek's second table of `-ebilir` cells.

AND IT IS STRICT ABOUT THE AORIST'S VOWEL, because the table gets it wrong
and the head line is not always there: ölçmek's table has `ölçir`, gömmek's
`gömir`, bükmek's `bükir` -- not Turkish, since -Ir harmonises -- beside heads
that say ölçer, gömer, büker.  The head line is read first (it is what the
page's editors wrote; the table is a template's output) and a cell the
harmony refuses is not taken at all.  A form nothing passes is left blank and
named in `missing`, for the annotator; it is never built from the infinitive.

Standard library only: the server imports it.
"""
import re

import lookup
from verbs import Parts, one_equivalent, trim_meaning

# ------------------------------------------------------------- the rows
# The notes that say which row is which.  The head line's aorist is the one
# own row with exactly these tags -- the tr-conj table never says `present`.
# A page that is only "third-person singular aorist of X" (a pointer,
# comma-joined, its tags right because they are the page's own) has at least
# the other two, and sometimes more: diyor's page says `continuative,
# definite, indicative, present, singular, third-person`.
HEAD_AORIST = "present singular third-person"
PTR_AORIST = "aorist singular third-person"
PTR_PRESENT = "continuative present singular third-person"

# What a pointer page says a DIFFERENT verb is to this one.  `yapılmak` has
# no entry -- its page's only sense is "passive of yapmak", so getdict keeps
# it as a row of yapmak with the note `passive` -- and the word in the text
# is then yapılmak, whose aorist is yapılır and not yapar.
DERIVED = frozenset(("passive", "causative", "reflexive", "reciprocal"))

# ...and what it says a spelling of the WHOLE word is (the note getdict
# writes for an `alt_of` page ends in "spelling").
SPELLING = frozenset(("alternative", "spelling", "abbreviation", "ellipsis"))

_VOWELS = frozenset("aeıioöuüâêîôû")
_PLAIN = str.maketrans("âêîôû", "aeiou")
_BACK = frozenset("aıou")
_HIGH = {"a": "ı", "ı": "ı", "o": "u", "u": "u",
         "e": "i", "i": "i", "ö": "ü", "ü": "ü"}


def _last_vowel(s):
    """The last vowel of `s`, circumflex taken off (â is an a), or ''."""
    for ch in reversed(s.translate(_PLAIN)):
        if ch in _HIGH:
            return ch
    return ""


def _stems(stem):
    """The stem as it stands before a vowel: itself, and for a stem in -t
    the voiced one too.  A closed class voices -- gitmek gider, etmek eder,
    tatmak tadar, and every -etmek compound, 267 lemmas in the extract -- and
    which class a verb is in is the one thing the stem does not say, so both
    are allowed and the row says which it is."""
    out = [(stem, False)]
    if stem.endswith("t"):
        out.append((stem[:-1] + "d", True))
    return out


def _aorist_of(stem, form):
    """Is `form` the bare third person singular aorist of `stem`?  None if
    not; else whether it voiced the stem.  A vowel stem takes -r (okur,
    arar, der); a consonant stem -Ar or -Ir, harmonised to its last vowel --
    which of the two is the verb's own and is what the row is for."""
    for s, voiced in _stems(stem):
        if s[-1:] in _VOWELS:
            if form == s + "r":
                return voiced
            continue
        v = _last_vowel(s)
        if v and form in (s + ("a" if v in _BACK else "e") + "r", s + _HIGH[v] + "r"):
            return voiced
    return None


def _present_of(stem, form):
    """Is `form` the bare third person singular present in -iyor of `stem`?
    None if not; else whether it voiced the stem.

    A stem in -a/-e narrows it (ara- arıyor, bekle- bekliyor, oyna- oynuyor,
    and de-, ye- diyor, yiyor); any other vowel stem takes -yor (okuyor); a
    consonant stem a high vowel and -yor (geliyor, gidiyor).  The high vowel
    is any of the four here, not the harmonic one: this test tells the
    table's third person from its other cells, which differ by whole
    syllables, and a loan's harmony (the research pass met `harfliyor`) is
    no reason to refuse the source's own spelling."""
    if stem[-1:] in "aeâê":
        return False if re.fullmatch(re.escape(stem[:-1]) + "[ıiuü]yor", form) else None
    if stem[-1:] in _VOWELS:
        return False if form == stem + "yor" else None
    for s, voiced in _stems(stem):
        if re.fullmatch(re.escape(s) + "[ıiuü]yor", form):
            return voiced
    return None


def _found(ctx, test, stem, prefix, require=(), forbid=(), exact=None, own=True):
    """The first row, in the source's order, whose form (after a compound's
    noun) passes `test`: (form, voiced), or None."""
    for f in ctx.picks(require=require, forbid=forbid, exact=exact, own=own):
        form = f.form
        if prefix:
            if not form.startswith(prefix + " "):
                continue
            form = form[len(prefix) + 1:]
        v = test(stem, form)
        if v is not None:
            return form, v
    return None


def _unique(ctx, headword):
    """Is this the only verb entry spelt so?  A pointer row is filed under
    the FIRST entry with the headword it names, so a homograph collects its
    twin's: `yenir` -- the aorist of yenmek, to be eaten -- is a row of
    yenmek, to defeat, whose aorist is yener."""
    n = ctx.conn.execute("SELECT count(*) FROM entry WHERE headword = ? AND pos = 'verb'",
                         (headword,)).fetchone()[0]
    return n <= 1


def _aorist(ctx, stem, prefix):
    """The entry's own aorist: the head line's, else the table's."""
    return (_found(ctx, _aorist_of, stem, prefix, exact=HEAD_AORIST)
            or _found(ctx, _aorist_of, stem, prefix, require="aorist", forbid="negative"))


def _present(ctx, stem, prefix):
    """The entry's own present in -iyor: the table's."""
    return _found(ctx, _present_of, stem, prefix, require="continuative",
                  forbid="negative")


def _twins_present(ctx, stem, prefix, headword, aor):
    """The present a homograph's table gives, where its aorist is this one.

    Wiktionary splits a verb by etymology, and often only one of the two
    pages carries the table: yakmak "to light" has a head line and nothing
    else, yakmak "to apply, smear on" the whole conjugation; so do dokunmak
    (to touch / to be woven), yüzmek (to skin / to swim), sarmak, yormak and
    yorulmak -- 9 of the 209 verbs with no present of their own.  The present
    in -iyor is the one form that cannot differ between two verbs spelt
    alike: it is the stem, narrowed where it ends in a vowel and voiced where
    the verb voices, and whether it voices is what the aorist shows.  So the
    twin's present is taken only when the twin's aorist IS this one's --
    yenmek's two (yener to defeat, yenir to be eaten) would lend nothing,
    and the aorist, which is lexical, is never lent at all.
    """
    for (tid,) in ctx.conn.execute(
            "SELECT id FROM entry WHERE headword = ? AND pos = 'verb' AND id != ? "
            "ORDER BY id", (headword, ctx.entry["id"])).fetchall():
        twin = ctx.other(tid)
        if twin is not None and _aorist(twin, stem, prefix) == aor:
            got = _present(twin, stem, prefix)
            if got is not None and got[1] == aor[1]:
                return got
    return None


def _forms(ctx, stem, prefix, headword):
    """(present, aorist, what is missing) from this entry's rows."""
    aor = _aorist(ctx, stem, prefix)
    pres = _present(ctx, stem, prefix)
    # THE POINTER PAGES, LAST, AND ONLY WHERE NO TWIN CAN HAVE FILED ONE HERE.
    # Their tags are right (they are the page's own), and they are the only
    # record of a form for a verb whose page has no table.
    if (aor is None or pres is None) and _unique(ctx, headword):
        aor = aor or _found(ctx, _aorist_of, stem, prefix, require=PTR_AORIST,
                            forbid="negative", own=False)
        pres = pres or _found(ctx, _present_of, stem, prefix, require=PTR_PRESENT,
                              forbid="negative", own=False)
    if pres is None and aor is not None:
        pres = _twins_present(ctx, stem, prefix, headword, aor)
    names = ctx.L.vb_forms
    missing = []
    # THE TWO MUST VOICE ALIKE: a t that is a d before -er is a d before
    # -iyor too.  When they disagree one of them is wrong, and the head line
    # is the page's editors' while the table is a template's -- hafifletmek's
    # head says hafifletir and its table hafifleder, hafiflediyor -- so the
    # table's present goes, and the annotator is told why.
    if aor and pres and aor[1] != pres[1]:
        missing.append("%s: the table's %s does not voice like the aorist %s"
                       % (names[1], pres[0], aor[0]))
        pres = None
    elif pres is None:
        missing.append(names[1])
    if aor is None:
        missing.append(names[2])
    return (pres[0] if pres else ""), (aor[0] if aor else ""), missing


# ----------------------------------------------------------- the meaning
# The case endings a sense's tags name, in the order docs/lang/tr.md lists
# them, as the suffix in its front-vowel shape.  Both spellings are read:
# getdict writes `with-dative` from the qualifier, and wiktextract wrote a
# bare `dative` of its own on a few -- yardım etmek has only that.  The
# genitive is not in the docs' list and is here for the one verb that has
# it, farkında olmak (bir şeyin farkında olmak, to be aware of something).
_CASES = (("dative", "-e"), ("accusative", "-i"), ("ablative", "-den"),
          ("locative", "-de"), ("instrumental", "ile"), ("genitive", "-in"))

# A QUALIFIER THAT SAYS NOTHING BUT THE CASE is the government the extra
# prints, and printed twice it reads "(with -le) to get married (to someone)
# (ile)".  Wiktionary put it in the gloss text of 21 first senses -- evlenmek,
# dövüşmek, öldürmek's "(with accusative case)", sığmak's "[with dative]" --
# and in a bracket the meaning's trimming cannot see into: kıyaslamak's
# "[with -le; or with ile] to compare" was cut at the semicolon inside it and
# came out "[with -le".  So such a group goes before the sense is trimmed,
# and only when the extra says it instead.
_CASE_WORDS = frozenset(
    "dative ablative accusative instrumental locative genitive "
    "-e -a -ye -ya -den -dan -ten -tan -i -ı -u -ü -yi -yı -yu -yü "
    "-de -da -te -ta -le -la -yle -yla ile -in -ın -un -ün -nin -nın -nun -nün".split())
_GLUE = frozenset(("with", "or", "and", "case", "cases", "used", "+", "the"))
_GROUP = re.compile(r"\s*(\(([^()\[\]]*)\)|\[([^()\[\]]*)\])")


def _no_case_groups(sense):
    def gone(m):
        inner = (m.group(2) if m.group(2) is not None else m.group(3)).lower()
        toks = re.findall(r"[^\s,;]+", inner)
        if not toks or toks[0] not in ("with", "used", "+"):
            return m.group(0)
        rest = [t for t in toks if t not in _GLUE]
        return "" if rest and all(t in _CASE_WORDS for t in rest) else m.group(0)
    return _GROUP.sub(gone, sense)


# THE SUM-OF-PARTS LINE IS NOT A MEANING.  Wiktionary opens an idiom's page
# with "Used other than figuratively or idiomatically: see sahip, olmak." --
# sahip olmak, bok yemek, fındık kırmak and four more -- and it is the first
# sense, so it was what the meaning slot said.
_NOT_A_MEANING = re.compile(r"(?i)^used other than figuratively or idiomatically\b")


def _sense(sense, sense_tags):
    """(text, tags) of the sense the gloss uses: lookup's first ranked,
    ranked exactly as lookup ranks it, so the government read here is the
    government of the meaning the reader is shown.

    A HEADING IS NOT ITS OWN SENSE.  "causative of eğlenmek:" is the first
    line of eğlendirmek and "to entertain" the second: getdict writes a
    sense's heading and its sub-sense as two lines, and the colon is what
    says the meaning follows.  8 first senses are headings like that.
    """
    lines = [x for x in (sense or "").split("\n") if x.strip()]
    tags = (sense_tags or "").split("\n")
    ranked = lookup.rank_senses(lines, tags)
    for s, t, _tier in ranked:
        if _NOT_A_MEANING.match(s):
            continue
        if s.rstrip().endswith(":"):
            i = lines.index(s)
            if i + 1 < len(lines):
                return lines[i + 1], (tags[i + 1] if i + 1 < len(tags) else t)
        return s, t
    return "", ""


def _cases(tagline):
    tags = set(t.strip() for t in (tagline or "").split(","))
    return [(case, suf) for case, suf in _CASES if {case, "with-" + case} & tags]


# The words an English verb ends in when it takes its object through a
# preposition -- "to wait for", "to get rid of", "to look (at)".
_PREPS = frozenset("about after against at for from in into of on onto over "
                   "through to upon with".split())


# A SENSE THAT NAMES ANOTHER VERB AND THEN SAYS WHAT IT MEANS -- "reciprocal
# of anlamak; to understand each other", "synonym of benzemek (“to resemble,
# look alike”)", "reciprocal of çarpmak: to bump into" -- has its meaning
# after the name, and trimmed as it stands it kept the name and lost the
# meaning ("reciprocal of anlamak").  The name alone, with nothing after it
# ("causative of kurumak"), is all the sense says, and stays.
_OF_VERB = re.compile(r"(?i)(?:synonym|causative|passive|reflexive|reciprocal) of "
                      r"[^\s:;,.(“]+(?: [^\s:;,.(“]+)*\s*(?:[:;,.]\s*|\(“)")


def _meaning(text, cases):
    """The meaning slot, from one sense.

    The core's trimming (verbs.trim_meaning), then ONE equivalent, which is
    docs/lang/tr.md's rule ("one equivalent in the gloss language rather than
    a string of synonyms"): gelmek is "to come, move closer" in the
    dictionary and `to come` in the book.  A sense Wiktionary starts with a
    capital (185 first senses: "To wait for, to await.") is written the way
    the other 2 375 are.
    """
    s = _no_case_groups(text) if cases else text
    m = _OF_VERB.match(s)
    if m and re.match(r"(?i)to\s", s[m.end():]):
        s = re.sub(r"”\)?\s*$", "", s[m.end():])
    s = one_equivalent(trim_meaning(s))
    return re.sub(r"^To (?=[a-z])", "to ", s)


def _opened(meaning, gov):
    """`to look (at)` as `to look at` where the government follows it.  The
    dictionary brackets the preposition to say the verb is used with or
    without it (bakmak "to look (at), gaze"); once the case is printed the
    complement is there, and two brackets side by side -- "to look (at)
    (-e)" -- read as two qualifiers.  docs/lang/tr.md's own entry is `to
    look at (-e)`.  Only a lone preposition at the very end is opened."""
    if not gov:
        return meaning
    return re.sub(r" \((%s)\)$" % "|".join(sorted(_PREPS)), r" \1", meaning)


def _government(cases, meaning, gloss):
    """The extras: the cases the complement takes, as docs/lang/tr.md prints
    them.  -e, -den, -de and ile always; -i only where the gloss-language
    verb takes its object through a preposition, because otherwise it is the
    plain object the gloss already leads the reader to expect -- `to wait
    for (-i)` teaches something, `to kill (-i)` (öldürmek's first sense is
    tagged with-accusative) does not.  Which the gloss-language verb does is
    only known for the gloss the meaning is written in, English; a book
    glossed in anything else is not given -i at all."""
    out = []
    for case, suf in cases:
        if case == "accusative":
            words = re.findall(r"[a-z]+", (meaning or "").lower())
            if not ((gloss or "").strip().lower() == "en" and len(words) >= 3
                    and words[0] == "to" and words[-1] in _PREPS):
                continue
        out.append(suf)
    return out


# ------------------------------------------------------------ compounds
# A COMPOUND VERB IS WRITTEN AS TWO WORDS -- teşekkür etmek, yardım etmek,
# karar vermek; 743 of the 2 560 verb lemmas -- and docs/lang/tr.md glosses it
# the Persian way: a \vb for the light verb with an EMPTY meaning, then a \bw
# for the word it carries, and the compound's government goes on the \bw.  A
# \vb cannot hold a \bw, so the \vb is built as the docs write it and the \bw
# is named in `missing`, meaning and government filled in from the
# compound's own entry: the editor's button then says exactly what to add.
#
# The lookup reads a chunk one word at a time, so `teşekkür ederim` arrives
# as teşekkür (a noun) and ederim (etmek) and never as the compound.  The
# compound is found from the chunk: the word before the verb, and the two
# before it, joined to the verb's infinitive, looked for as a verb headword.
# Reading the chunk makes the answer depend on it (Ctx.text), so it is read
# only for a verb that ends some compound at all.
_ENDS = {}


def _ends_a_compound(ctx, headword):
    """Does some compound end in this verb?  One scan of the verb entries
    per dictionary file (743 compounds end in 187 verbs), kept until the
    file changes -- keyed on the file and not the connection, which is one
    per thread."""
    p = lookup.path_for(ctx.code)
    key = (p, lookup._stamp(p))
    got = _ENDS.get(key)
    if got is None:
        got = frozenset(r[0].split()[-1] for r in ctx.conn.execute(
            "SELECT headword FROM entry WHERE pos = 'verb' AND headword LIKE '% %'"))
        _ENDS.clear()
        _ENDS[key] = got
    return headword in got


def _tr_lower(s):
    """Turkish lower case: I is ı and İ is i (docs/lang/tr.md: never
    case-fold Turkish the English way)."""
    return (s or "").replace("I", "ı").replace("İ", "i").lower()


def _compound_in_text(ctx, headword):
    """The compound entry the chunk makes of this verb and the word(s) before
    it, or None.  Longest first: `el ele vermek` before `ele vermek`.  A
    capital is tried both ways, the Turkish way (`Teşekkür ederim.`)."""
    words = [lookup._bare(w, ctx.L) for w in ctx.L.split_words(ctx.text)]
    for i, w in enumerate(words):
        if w != ctx.word or i == 0:
            continue
        for n in (2, 1):
            if i - n < 0:
                continue
            noun = " ".join(words[i - n:i])
            for spelt in dict.fromkeys((noun, _tr_lower(noun))):
                row = ctx.conn.execute(
                    "SELECT id, headword, sense, sense_tags FROM entry "
                    "WHERE headword = ? AND pos = 'verb' ORDER BY id LIMIT 1",
                    ("%s %s" % (spelt, headword),)).fetchone()
                if row is not None:
                    return row
    return None


def _compound_said(ctx, sense, tags):
    """(meaning, government) of the compound itself -- teşekkür etmek is `to
    thank` and takes -e -- where the gloss is English."""
    text, tagline = _sense(sense, tags)
    cases = _cases(tagline)
    en = (ctx.gloss or "").strip().lower() == "en"
    mean = _meaning(text, cases) if en else ""
    gov = _government(cases, mean, ctx.gloss)
    return _opened(mean, gov), gov


def _bw_note(ctx, noun, sense, tags):
    """What the \\bw after the light verb should say, as one item of
    `missing`: the compound's meaning (where the gloss is English) and its
    government.  No backslash -- the core takes every one out of `missing`
    -- and no comma, which is what the editor joins the items with."""
    mean, gov = _compound_said(ctx, sense, tags)
    said = (": " + mean if mean else "") + (" (%s)" % "; ".join(gov) if gov else "")
    return ("bw for %s after it%s" % (noun, said)).replace(",", ";")


def _compound_parts(ctx, noun, whole, sense, tags):
    """...and the same compound as the entry it is, for the button that puts
    it in whole: teşekkür etmek, the noun it carries, and what the pair means.

    NOTHING IS ROMANISED HERE.  Turkish is written as it is said, and
    docs/lang/tr.md leaves the sound slot of both macros empty
    (`\\bw{teşekkür}{}{thanks (-e)}`); the segmentation that slot can hold is
    the annotator's, never a dictionary's.

    THE MEANING IS THE COMPOUND'S, which is the one the dictionary's entry
    is for and the one the row has always named.  An edition that would
    rather gloss the noun itself (`thanks`) trims it there, as it trims every
    other draft this sidebar proposes."""
    mean, gov = _compound_said(ctx, sense, tags)
    tail = (" (%s)" % "; ".join(gov)) if gov else ""
    return {"name": "compound verb", "whole": whole, "whole_sound": "",
            "mean": (mean + tail) if mean else tail.strip(),
            "word": noun, "word_sound": ""}


# ------------------------------------------------------------ the recipe
def recipe(ctx):
    e = ctx.entry
    if (e["pos"] or "") != "verb":
        return None                                  # yemek the meal, gelir income
    headword = (e["headword"] or "").strip()
    words = headword.split()
    # THE INFINITIVE IS THE TEST OF A VERB, not the part of speech alone:
    # 38 pos=verb pages are stray forms that kept a gloss (değilim, imiş,
    # desene, sevse), and have nothing a \vb could print.
    if not words or not re.search(r"m[ae]k$", words[-1]):
        return None
    if headword in (ctx.data().get("no_vb") or {}):
        return None
    light = words[-1]
    prefix = " ".join(words[:-1])
    stem = light[:-3]

    # which of this entry's rows the chunk's word is
    spelt = {ctx.word, _tr_lower(ctx.word), ctx.word.casefold()}
    here = [f for f in ctx.rows if f.form in spelt]

    # THE WORD IS ANOTHER VERB, which this dictionary knows only as a note on
    # this one (DERIVED).  Its forms are not this entry's, and it has none of
    # its own here: the infinitive, which the pointer page wrote, and nothing
    # else -- and not at all where the derived verb has an entry of its own
    # (getirmek is "causative of gelmek" and a verb with a table), whose hit
    # carries the \vb.
    if here and all(f.tags & DERIVED for f in here):
        derived = here[0].form
        if not re.search(r"m[ae]k$", derived) or ctx.conn.execute(
                "SELECT 1 FROM entry WHERE headword = ? AND pos = 'verb' LIMIT 1",
                (derived,)).fetchone():
            return None
        kind = sorted(here[0].tags & DERIVED)[0]
        return Parts(parts=[(derived, ""), ("", ""), ("", "")], meaning="",
                     missing=[ctx.L.vb_forms[1], ctx.L.vb_forms[2],
                              "meaning: the dictionary has %s only as the %s of %s"
                              % (derived, kind, headword)])

    if prefix:
        # A SPELLING OF THE WHOLE COMPOUND, reaching its entry, is not the
        # light verb: terketmek is "alternative of terk etmek", written solid,
        # and yırtmak alone is "ellipsis of kefeni yırtmak".  Neither can be
        # cut into a \vb and a \bw, and yırtmak has a \vb of its own.
        if here and all(f.tags & SPELLING for f in here):
            return None
        pres, aor, missing = _compound_forms(ctx, light, prefix, headword)
        missing.append(_bw_note(ctx, prefix, e["sense"], e["sense_tags"]))
        return Parts(parts=[(light, ""), (pres, ""), (aor, "")], meaning="",
                     missing=missing,
                     compound=_compound_parts(ctx, prefix, headword,
                                              e["sense"], e["sense_tags"]))

    pres, aor, missing = _forms(ctx, stem, "", headword)
    if _ends_a_compound(ctx, headword):
        row = _compound_in_text(ctx, headword)
        if row is not None:
            # the noun as the dictionary spells it -- the \bw's headword --
            # and not as the head of a sentence capitalises it
            noun = row["headword"].rsplit(" ", 1)[0]
            missing.append(_bw_note(ctx, noun, row["sense"], row["sense_tags"]))
            return Parts(parts=[(headword, ""), (pres, ""), (aor, "")], meaning="",
                         missing=missing,
                         compound=_compound_parts(ctx, noun, row["headword"],
                                                  row["sense"], row["sense_tags"]))

    text, tagline = _sense(e["sense"], e["sense_tags"])
    cases = _cases(tagline)
    meaning = _meaning(text, cases)
    gov = _government(cases, meaning, ctx.gloss)
    return Parts(parts=[(headword, ""), (pres, ""), (aor, "")],
                 meaning=_opened(meaning, gov), extras=gov, missing=missing)


def _compound_forms(ctx, light, prefix, headword):
    """A compound's light-verb forms: from the light verb's own entry, then
    from the compound's own rows for whatever that did not give.

    THE LIGHT VERB'S PAGE FIRST.  The \\vb is the light verb's, and its own
    page is the one its forms are written on; a compound's page repeats them
    and gets them wrong where it disagrees -- nefes salmak's head says
    `nefes salır` where salmak's says salar, seferberlik ilan etmek's `...
    etir` where etmek's says eder, the only two disagreements over 576
    compounds -- and has none at all for 248 of them (satın almak has no head
    line and no table to speak of).  Only where exactly one verb is spelt so:
    a homograph's twin (see _unique) is not this compound's verb, and there
    the compound's own rows, which know which one they conjugate, are all
    there is.
    """
    stem = light[:-3]
    got = [_forms(ctx, stem, prefix, headword)]
    rows = ctx.conn.execute("SELECT id FROM entry WHERE headword = ? AND pos = 'verb'",
                            (light,)).fetchall()
    if len(rows) == 1:
        # its rows through a Ctx of its own: _forms reads nothing else
        sub = ctx.other(rows[0][0])
        if sub is not None:
            got.insert(0, _forms(sub, stem, "", light))
    pres = next((g[0] for g in got if g[0]), "")
    aor = next((g[1] for g in got if g[1]), "")
    names = ctx.L.vb_forms
    missing = []
    if not pres:
        # the first source's own words for it: the plain name, or why its
        # table's present was not taken
        missing.append(next(m for m in got[0][2] if m.startswith(names[1])))
    if not aor:
        missing.append(names[2])
    return pres, aor, missing
