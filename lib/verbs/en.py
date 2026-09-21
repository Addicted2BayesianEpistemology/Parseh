#!/usr/bin/env python3
"""English: what a \\vb says about a verb, from the dictionary's own rows.

    helped   \\vb{help}{hɛlp}{helped}{hɛlpt}{helped}{hɛlpt}{to provide ...}
    said     \\vb{say}{seɪ}{said}{sɛd}{said}{sɛd}{to pronounce (pres. \\pw{says} \\textit{sɛz})}
    wound    \\vb{wind}{waɪnd}{wound}{waʊnd}{wound}{waʊnd}{to turn coils around something}
    given up \\vb{give up}{gɪv ʌp}{gave up}{geɪv ʌp}{given up}{ˈgɪvən ʌp}{to surrender ...}
    went     \\vb{go}{}{went}{wɛnt}{gone}{}{to move, ...}    missing: the sound of go
             (the dictionary's /ɡəʊ/ is not General American), the sound of gone

docs/lang/en.md says what an English \\vb is, and this is that page done by
the machine: the plain form, the past and the past participle, each with how
it is said in General American, written in the edition's IPA; a phrasal verb
whole, however far the chunk has carried its particle; the present of the
four verbs nobody could build it for (be, have, do, say) in the one
parenthesis after the meaning; and no \\vb at all for a modal.  The forms
are the entry's own head-line rows -- kaikki keeps en-verb's line as one row
per form with the form's name in the note:

    walked    past                   -> slot 2
    walked    participle past        -> slot 3
    went      past  (with /wɛnt/, from the page that is only "past of go")

THE SOUND IS THE HARD HALF, AND MOST OF THIS FILE.  English spells none of
it, so the three sounds are the reason the line exists, and Wiktionary gives
each word a list of them in a dozen accents, which the dictionary keeps ONE
of.  Whatever that one is, it is read, never trusted: `_house` writes it the
way docs/lang/en.md writes a pronunciation (g and r for ɡ and ɹ, ər for ɚ,
no length, no stress mark on one syllable) and refuses it -- the slot left
blank and named in `missing` -- where the string itself shows it is not
General American (go /ɡəʊ/, pass /pɑːs/, learn /lɜːn/) or is a weak form
(do /də/, was /wəz/).  A regular past is not looked up at all: its -ed is
t, d or ɪd by the last sound of the verb, which is docs/lang/en.md's rule 5
and has no exception in a verb's past.

A PHRASAL VERB IS READ FROM THE CHUNK, since the lookup splits it at its
space: the hit is `given`, the chunk `he had given up`, and the dictionary
has give up -- so the \\vb is give up's, whose sound is give's and up's
where it has none of its own.  Only where the particle ends the chunk
(_closes, which says why).

Returns None for a hit that is not a verb; for a modal; for the particle of
a phrasal verb the chunk has (`down` in `put it down` is not the verb to
down a drink); for a verb entry with neither a past nor a past participle;
and for an entry the word reached only by being somebody else's -- the
other lie's `lied`, the obsolete ween's `went`, thee's Early Modern `the`
(_claimed_elsewhere, _reached_as_spelling).  The editor then offers the \\dw
it always did.
"""
import re
import unicodedata

import languages
import lookup
import verbs

# ------------------------------------------------------------------ the rows
# THE SLOTS COMPARE WHOLE TAG SETS.  kaikki writes a past that is only
# somebody's dialect as `Northern-England Scotland archaic past` (get's
# `gat`), a proscribed one as `past proscribed` (wind's `wound`, which is the
# OTHER wind's past), and get's p.p. `gotten` under ten tags; the exact set
# -- {past}, {participle, past} -- is the one plain form among them, and
# "has the tag past" would have let every one of the others in.
_PAST = frozenset(("past",))
_PP = frozenset(("participle", "past"))
# be has no row that is only `past`: its head line is a conjugation table, and
# its past is the persons of it -- was (first and third singular), were
# (second, and the plural).  Only these tags may stand beside `past` there.
_PERSONS = frozenset(("past", "first-person", "second-person", "third-person",
                      "singular", "plural", "indicative"))
# What makes a row a form of the verb at all, and not a way of spelling it.
_INFLECTION = frozenset((
    "past", "participle", "present", "gerund", "infinitive", "imperative",
    "singular", "plural", "first-person", "second-person", "third-person",
    "indicative", "subjunctive"))
# What makes a form not the one a reader of today's English meets.  Not a
# region, nor a qualifier kaikki could not parse: get's own `gotten` row is
# `Australia Canada Ireland New-Zealand UK US error-unknown-tag participle
# past recently`, and it is how General American says it.
_DEAD = frozenset(("archaic", "obsolete", "proscribed", "nonstandard", "rare",
                   "dialectal", "misspelling", "pronunciation-spelling",
                   "eye-dialect"))
# ...and, of two variants of one slot, what makes the page of one say it is
# gone.  Not `dialectal` or `rare`: the page for learned is `Canada, English,
# New-Zealand, US, dialectal, participle, past` -- dialectal in England, that
# is -- and it is the American past.
_GONE = frozenset(("archaic", "obsolete", "nonstandard", "proscribed",
                   "misspelling", "pronunciation-spelling", "eye-dialect"))
# A spelling nobody writes now: `the` is an Early Modern spelling of thee, `b`
# an Internet one of be, `hv` of have, `'ll` a contraction of will.
_NOT_WRITTEN = frozenset((
    "obsolete", "archaic", "abbreviation", "contraction", "clitic", "Internet",
    "pronunciation-spelling", "eye-dialect", "misspelling", "nonstandard",
    "informal", "dialectal", "rare", "informal-spelling"))
_NOT_A_SPELLING = re.compile(r"[\[\]()]|^-|-$|, ")


class _Entry:
    """One verb entry and its form rows, the hit's own or one the recipe
    went looking for (the phrasal verb the chunk has, the base verb of a
    phrasal verb) -- which is why this is not verbs.Ctx, whose rows are the
    hit's only.  `row` is the entry as verbs.entry_row reads it, every
    column there ('' where the dictionary predates it); `rows` its form
    rows as verbs.Form, in the order the source wrote them."""

    def __init__(self, conn, row):
        self.id = row["id"]
        self.headword = row["headword"] or ""
        self.row = row
        self.rows = [verbs.Form(r["form"] or "", r["note"] or "",
                                verbs.split_tags(r["note"]), "", r["rowid"])
                     for r in conn.execute(
                         "SELECT rowid, form, note FROM form WHERE entry_id = ? "
                         "ORDER BY rowid", (self.id,))]

    def own(self, exact):
        """The spellings of the entry's own rows whose tags are exactly
        `exact`, first written first, each once -- and only those that are
        a spelling.  kaikki's parse of a head line leaves a few that are
        not, 395 of the 107 583 past and p.p. rows: `parallelled[UK
        nonstandard]`, `participle (US) partialed`, trick-or-treat's
        `trick-` and `-treated`; and a comma is what the slot itself joins
        two forms with (be: was, were)."""
        out = []
        for f in self.rows:
            if f.own and f.tags == exact and f.form not in out \
                    and not _NOT_A_SPELLING.search(f.form):
                out.append(f.form)
        return out


def _entry(conn, eid):
    return _Entry(conn, verbs.entry_row(conn, eid))


def _twins(conn, headword, eid=None):
    """Every other verb entry spelled `headword`, first written first.
    Wiktionary makes one entry per etymology, and English has many that are
    two verbs: wind (winded) and wind (wound), lie (lay, lain) and lie
    (lied)."""
    return [r["id"] for r in conn.execute(
        "SELECT id FROM entry WHERE headword = ? AND pos = 'verb' ORDER BY id",
        (headword,)) if r["id"] != eid]


def _slot(e, exact, fallback, surface):
    """The forms of one slot: the plain rows (tags exactly `exact`), else the
    ones also tagged `fallback`; then the one the chunk uses, if it is one
    of them, else the first written.

    FIRST WRITTEN IS THE AMERICAN ONE.  en-verb lists a verb's variants in
    Wiktionary's own order -- dreamed before dreamt, learned before learnt,
    hung before hanged -- which is the General American order this edition
    wants; the chunk's own spelling outranks it because the reader has to
    recognise the form on the page, and a \\vb that names dreamed beside a
    dreamt is a correction nobody asked for.  Not the plain form itself,
    though: `tread` is listed among tread's pasts (trod, tread, treaded),
    and a chunk that says tread is not saying its past.

    THE US FALLBACK is what makes a phrasal verb's p.p. American: get up has
    `got up` as `UK participle past` and `gotten up` as `US participle
    past`, and no plain row at all.
    """
    got = e.own(exact)
    if not got and fallback:
        got = e.own(exact | fallback)
    if not got:
        return None
    # A VARIANT ITS OWN PAGE CALLS DEAD GOES BEHIND ONE IT DOES NOT.  fix's
    # head line lists `fixt` first and plainly, and the page for fixt says
    # `obsolete, participle, past`; the \vb said fix, fixt, fixt.
    live = [g for g in got if not _dead_variant(e, g)]
    got = live or got
    if surface and surface != e.headword.casefold():
        for g in got:
            if g.casefold() == surface:
                return g
    return got[0]


def _dead_variant(e, form):
    """Does every page that says `form` is a past of this verb call it
    archaic, obsolete, nonstandard...?  None saying so is not dead."""
    tags = [f.tags for f in e.rows if not f.own and f.form == form]
    return bool(tags) and all(t & _GONE for t in tags)


def _persons_past(e):
    """be's past, from its table: every spelling tagged past and some person
    or number and nothing else, in order -- `was, were`."""
    out = []
    for f in e.rows:
        if f.own and "past" in f.tags and len(f.tags) > 1 \
                and f.tags <= _PERSONS and f.form not in out \
                and not _NOT_A_SPELLING.search(f.form):
            out.append(f.form)
    return ", ".join(out) if len(out) > 1 else None


def _by_pointer(conn, e, want):
    """A slot the entry's own rows do not give, from the pages that say they
    are that form of it.

    ONLY WHERE THE ENTRY HAS NO TWIN.  A page that is only "past participle
    of speak" is linked to the first verb entry with that headword, so it is
    certain to be this verb's only where there is one: the modal `can` has
    `canned` among its pointer rows, which is the other can's.  speak is the
    case this is for -- its head line in the extract has no `spoken` (the
    page's own template has it; kaikki's parse lost it) and its `spoken`
    page does -- and strike, whose head-line participles are all tagged
    obsolete.
    """
    if _twins(conn, e.headword, e.id):
        return None
    for f in e.rows:
        if not f.own and f.tags == want and not _NOT_A_SPELLING.search(f.form):
            return f.form
    return None


# ------------------------------------------------------------ the sound
# THE EDITION'S IPA (docs/lang/en.md, "Transliteration").  Every string the
# dictionary holds is either written into these symbols or refused.
_OK = set("pbtdkgfvθðszʃʒhmnŋlrwj" "ɪiɛæɑɔʊuʌə" "eao" "ˈˌ ")
_DIPHTHONGS = ("eɪ", "aɪ", "ɔɪ", "oʊ", "aʊ")
_MONO = "ɪiɛæɑɔʊuʌə"

# What a /…/ may carry that says HOW a sound is made and not which it is:
# the tie of t͡ʃ, the non-syllabic mark of eɪ̯.  Any other combining mark is
# a narrow transcription's (ä, ɑ̃, the lowering and raising signs), and the
# string is refused rather than read without it.
_TIES = {"͡", "͜", "̯", "̑"}
_SYLLABIC = {"̩", "̍"}

# SPELLINGS WHOSE l IS NOT SAID, so an l missing from the sound says nothing
# about the accent there: walk, talk, calm, palm, halve, could.
_SILENT_L = re.compile(r"alk|alm|alf|alv|olk|ould")
# THE a THAT RP SAYS ɑː AND GENERAL AMERICAN æ: before s, f, th, n + a
# consonant, m + a consonant, lf, lv and ugh -- pass, after, bath, plant,
# dance, sample, half, halve, laugh.  Wider than the lexical set, since a
# spelling cannot tell bath from father, and a sound refused where it was
# right only asks the annotator to write it.
_BATH = re.compile(r"a(s|f|th|n[a-z]|m[a-z]|lf|lv|ugh)")

# Written with its r in the edition (docs/lang/en.md: ɑr ɔr ɛr ɪr ʊr ər),
# whatever vowel a transcription gives before the r.
_R_VOWELS = (("ɪəɹ", "ɪr"), ("ɛəɹ", "ɛr"), ("eəɹ", "ɛr"), ("ʊəɹ", "ʊr"),
             ("ɪɚ", "ɪr"), ("ɛɚ", "ɛr"), ("eɚ", "ɛr"), ("ʊɚ", "ʊr"),
             ("ɔɚ", "ɔr"), ("oɚ", "ɔr"), ("ɑɚ", "ɑr"), ("oɹ", "ɔr"),
             ("eɹ", "ɛr"), ("ɜɹ", "ər"), ("ɝ", "ər"), ("ɚ", "ər"), ("ɹ", "r"))

# A STRING THAT SAYS IT IS NOT GENERAL AMERICAN.  Each of these is found
# only in a transcription of another accent: RP's GOAT əʊ and LOT ɒ, its
# centring diphthongs, the Scottish, Australian and London vowels, the
# Canadian raising Wiktionary tags as plain `US` (fight /fəɪt/, write
# /ɹəɪt/), the l-vocalised `kill` /ˈkɪʊ̯/, and the symbols of narrow
# transcriptions this edition writes as the phoneme (the glottal stop, the
# flap: docs/lang/en.md rule 6 writes better with a t).
_NOT_GA = ("əʊ", "ɒ", "ɪə", "eə", "ʊə", "ɛə", "ɐ", "ʉ", "ɵ", "ɘ", "ɤ", "ʏ", "ø",
           "œ", "y", "x", "ʁ", "ɾ", "ʔ", "ɬ", "ʍ", "ç", "β", "ɸ", "ɦ", "ʋ", "ɻ",
           "əɪ", "ʌɪ", "ɑɪ", "æɪ", "ɔʊ", "ɪʊ", "ɛɪ", "ɨ", "ᵻ", "ᵿ", "ʰ", "ʷ",
           "-", "ǁ", "˞", "ɜ", "ɛː", "eː", "oː", "aː", "æː", "ɜː")


def _nuclei(word):
    """How many syllables a written sound has: one per vowel, a diphthong
    counting once, ər (ə and its r) once."""
    n, i = 0, 0
    while i < len(word):
        if word[i:i + 2] in _DIPHTHONGS:
            n, i = n + 1, i + 2
        elif word[i] in _MONO:
            n, i = n + 1, i + 1
        else:
            i += 1
    return n


def _house(ipa, spelling):
    """A pronunciation from the dictionary as docs/lang/en.md writes one,
    and "" with the reason it cannot be, as (sound, why).

    `spelling` is the word it is of: its r and its l are what the sound is
    checked against, because a transcription that drops them is an accent
    that drops them (star /stɑː/, learn /lɜːn/, kill /ˈkɪʊ̯/).
    """
    raw = (ipa or "").strip()
    m = re.search(r"/([^/]+)/", raw)
    if m:
        s = m.group(1)
    else:
        # A NARROW ONE IS READ WHEN IT IS ALL THERE IS -- prefer has only
        # [pɹɪˈfɝ] -- with the aspiration and the unreleased stop that are
        # all it adds to an English /…/, and refused on anything else it
        # adds (a flap, a glottal stop, a devoiced l), like any other string.
        m = re.search(r"\[([^\[\]]+)\]", raw)
        s = m.group(1) if m else raw.strip("/ ")
        s = s.replace("ʰ", "").replace("̚", "")
    # OPTIONAL SOUNDS ARE KEPT: Wiktionary writes one transcription for both
    # accents as /stɑː(ɹ)/, /ˈbɑː.(ɹ)tə(ɹ)/, and the r in brackets is exactly
    # the one General American says; /ˈk(w)ɔɹ.tɚ/ and /ˈɪŋ.(ɡ)lɪʃ/ likewise.
    # All but the yod after t, d, n, s, l -- `knew` is /ˈn(j)u/, tagged US,
    # and that bracket is the one General American leaves out: nu.
    s = re.sub(r"(?<=[tdnszθl])\(j\)", "", s)
    s = s.replace("(", "").replace(")", "")
    s = unicodedata.normalize("NFD", s)
    out = []
    for ch in s:
        if ch in _SYLLABIC and out:
            out.insert(len(out) - 1, "ə")          # n̩ -> ən: taken ˈteɪkən
        elif ch in _TIES:
            continue
        elif unicodedata.combining(ch):
            return "", "a narrow transcription"
        else:
            out.append(ch)
    s = unicodedata.normalize("NFC", "".join(out))
    # a link between two words is a space between them: take‿in, shore‿up
    s = s.replace("‿", " ").replace(".", "").replace("ɡ", "g").replace("ɫ", "l")
    s = s.replace("ʧ", "tʃ").replace("ʤ", "dʒ").replace("r", "ɹ")
    s = re.sub(r"\s+", " ", s).strip()
    # A WEAK FORM IS NOT THE WORD.  do is listed /də/ first, was /wəz/, in
    # /ən/, were /wə(ɹ)/: a word whose one vowel is ə is how it is said
    # unstressed in a sentence, and a vocabulary line gives the word.  Not
    # ɚ: first /fɚst/ and curve /kɚv/ are stressed, written that way.
    if " " not in s and re.sub(r"[^ɪiɛæɑɔʊuʌəeaoɚɝɜɒɐ]", "", s) == "ə":
        return "", "a weak form"
    # THE VOWEL BEFORE AN r IS WRITTEN WITH ITS r, and first, so that what is
    # left of RP's centring diphthongs (ɪə, eə, ʊə) and its NURSE (ɜ) after
    # this is exactly the r-less kind: /ˈhɪə(ɹ)/ is hɪr, /hɪə/ is refused.
    s = s.replace("ɑːɹ", "ɑɹ").replace("ɜːɹ", "ɜɹ").replace("ɔːɹ", "ɔɹ")
    # LENGTH IS NOT WRITTEN, and where it marks a vowel General American
    # does not have, the string is refused instead: ɑː is RP's broad a in
    # the words spelt a before s, f, th, n, m or l -- pass /pɑːs/, ask
    # /ɑːsk/, plant /plɑːnt/, laugh, half, all æ in General American --
    # and ɜː its r-less NURSE (learn /lɜːn/).  Where the spelling has no
    # such a, ɑː is the ɑ of father and ah (/ɑː/), and is written so.
    if "ɑː" in s and _BATH.search(spelling.casefold()):
        return "", "RP's broad a"
    for a, b in _R_VOWELS:
        s = s.replace(a, b)
    for bad in _NOT_GA:
        if bad in s:
            return "", "not General American (%s)" % bad
    s = s.replace("ː", "")
    # THE YOD OF RP: after t, d, s, z and th General American drops it or
    # runs it into the consonant (produce /pɹəˈdjuːs/ is prəˈdus, maturate
    # /ˈmætjʊɹeɪt/ is ˈmætʃəreɪt); after n only where the syllable starts
    # (knew /ˈnjuː/ is nu, menu /ˈmɛnju/ keeps it); after l never (value).
    if re.search(r"[tdszθ]j[uʊ]|(^|[ˈˌ ]|[^ɪiɛæɑɔʊuʌəeao])nj[uʊ]", s):
        return "", "not General American (the yod of RP)"
    # a vowel letter only inside the diphthongs the edition writes
    if re.search(r"e(?!ɪ)|a(?![ɪʊ])|o(?!ʊ)", s):
        return "", "not General American (a vowel the edition does not use)"
    bad = sorted(set(ch for ch in s if ch not in _OK))
    if bad:
        return "", "a symbol the edition does not use (%s)" % "".join(bad)
    low = spelling.casefold()
    if "r" in low and "r" not in s:
        return "", "an accent that drops the r"
    if "l" in _SILENT_L.sub("", low) and "l" not in s:
        return "", "an accent that drops the l"
    # no stress mark on a word of one syllable: the fixture writes wound
    # waʊnd, and Wiktionary writes /ˈkeɪ̯m/
    words = [w.replace("ˈ", "").replace("ˌ", "") if _nuclei(w) <= 1 else w
             for w in s.split(" ")]
    return " ".join(w for w in words if w), ""


def _ed(sound):
    """The regular past of a verb said `sound` (docs/lang/en.md rule 5):
    t after a voiceless sound, ɪd after t or d, d after anything else --
    helped hɛlpt, played pleɪd, wanted ˈwɑntɪd.  ɪd makes a word of one
    syllable two, and the stress mark it then needs goes in front: wait
    weɪt, waited ˈweɪtɪd."""
    if sound.endswith(("t", "d")):
        if _nuclei(sound) == 1:
            return "ˈ" + sound.replace("ˈ", "").replace("ˌ", "") + "ɪd"
        return sound + "ɪd"
    if sound.endswith(("p", "k", "f", "θ", "s", "ʃ")):
        return sound + "t"
    return sound + "d"


def _regular(lemma, form):
    """Is `form` the plain form's regular -ed, by its spelling?  walk
    walked, smile smiled, try tried, stop stopped, panic panicked."""
    l, f = lemma.casefold(), form.casefold()
    if f == l + "ed" or (l.endswith("e") and f == l + "d"):
        return True
    if len(l) > 1 and l.endswith("y") and l[-2] not in "aeiou" and f == l[:-1] + "ied":
        return True
    if l[-1:] in set("bdfgklmnprstvz") and f == l + l[-1] + "ed":
        return True
    return l.endswith("c") and f == l + "ked"


def _heard(conn, headword, form):
    """How a page that is only a form of `headword` says `form`: the
    pronunciation getdict took from that page (went /wɛnt/, read /ɹɛd/),
    first written first.  Any verb entry spelled `headword` will do, since
    such a page is linked to the first of them whichever it is of -- and
    only such a page: `wound` the noun is /wuːnd/, and it is not the past of
    wind.

    WHATEVER THE PAGE'S SENSE IS TAGGED.  The tags are the sense's, not the
    sound's: get's `gotten` page is `Canada, Ireland, Northern-England,
    Scotland, US, dialectal, participle, past`, and it is still how gotten
    is said."""
    if not lookup._has_col(conn, "ipa", "form"):
        return ""
    for r in conn.execute(
            "SELECT f.note, f.ipa FROM form f JOIN entry e ON e.id = f.entry_id "
            "WHERE f.form = ? AND e.headword = ? AND e.pos = 'verb' "
            "AND f.ipa != '' ORDER BY f.rowid", (form, headword)):
        if "past" in verbs.split_tags(r["note"]):
            return r["ipa"]
    return ""


def _sound_of(conn, e, form, lemma_sound, data, missing):
    """The sound of one of `e`'s forms, or "" with its reason in `missing`.

    In this order: a regular -ed from the plain form's sound (a rule, and a
    better one than the -ed page, which is RP as often as not: started
    /ˈstɑːtɪd/); the page that says it is this form; the plain form's own
    sound where the spelling is the plain form's (put, cut, set, spread) --
    but not for read and its compounds, the one verb whose past is spelt as
    the plain form and said otherwise, which its page says (/ɹɛd/) and
    nothing else can.  They are told by their sound and not their spelling:
    read, reread, proofread end in rid, and spread, tread, dread and thread,
    whose past is said as they are, in rɛd.
    """
    if not form:
        return ""
    lemma = e.headword
    if lemma_sound and _regular(lemma, form):
        return _ed(lemma_sound)
    ipa = _heard(conn, lemma, form)
    if ipa:
        got, why = _house(ipa, form)
        if got:
            return got
        missing.append("the sound of %s (the dictionary's %s is %s)" % (form, ipa, why))
        return ""
    if form == lemma:
        if lemma_sound and not (lemma.casefold().endswith("read")
                                and lemma_sound.endswith("rid")):
            return lemma_sound
        if not lemma_sound:
            return ""                 # the plain form's sound is missing, and said so
    missing.append("the sound of %s" % form)
    return ""


# ------------------------------------------------------------ a phrasal verb
def _particles(data):
    return data.get("particles") or {}


def _phrasals(conn, lemma, parts):
    """The phrasal verbs of this verb the dictionary has, as (entry id, the
    particles): give up, give in, give it up... -- only those whose words
    after the verb are all particles, which is what docs/lang/en.md calls a
    phrasal verb (take place and make sense are idioms, and the recipe does
    not reach for them)."""
    out = []
    for r in conn.execute(
            "SELECT id, headword, sense FROM entry WHERE headword > ? AND "
            "headword < ? AND pos = 'verb' ORDER BY id", (lemma + " ", lemma + "!")):
        tail = r["headword"][len(lemma) + 1:].split(" ")
        if not tail or not all(t in parts for t in tail):
            continue
        # NOT A PAGE THAT SAYS IT IS NO PHRASAL VERB.  Wiktionary keeps some
        # sums of parts as entries, to say so: `use to` is "Used other than
        # figuratively or idiomatically: see use, to", and `get used to`
        # came out as the \vb of it.
        if all(_not_a_meaning(s) for s in (r["sense"] or "").split("\n") if s.strip()):
            continue
        # ...and that have a past to give: one without is no \vb, and the
        # chunk's verb is better offered alone than as nothing
        if conn.execute("SELECT 1 FROM form WHERE entry_id = ? AND note IN "
                        "('past', 'participle past') LIMIT 1", (r["id"],)).fetchone():
            out.append((r["id"], tuple(tail)))
    return out


# What may not stand between a verb and its particle: a word that starts a
# new clause, or the infinitive's `to` (in `I want you to come in` the `in`
# is come's, not want's).
_BREAK = frozenset(("to", "and", "or", "but", "that", "which", "who", "whom",
                    "if", "when", "while", "because", "than", "as", "so",
                    "then", "where", "what", "not"))


def _tokens(text):
    """The chunk's words as (bare, casefolded, the raw token)."""
    L = languages.get_or_default("en")
    out = []
    for t in (text or "").split():
        b = lookup._bare(t, L)
        if b:
            out.append((b, b.casefold(), t))
    return out


_DETERMINERS = frozenset(("the", "a", "an", "this", "that", "these", "those",
                          "my", "your", "his", "her", "its", "our", "their",
                          "some", "any", "no", "every", "each"))


def _closes(toks, i, tail, conn=None):
    """Does the chunk end with `tail`, the particles of a phrasal verb whose
    verb is toks[i], with at most two words between them?

    AT THE END OF THE CHUNK AND ONLY THERE.  A particle that closes the
    chunk has nothing left to be the preposition of, so the chunk has the
    phrasal verb -- `came in`, `he had given up`, `and put it down.`, `what
    he was waiting for.`, every phrasal verb of the English fixture.  One
    with more words after it may just as well be a verb and a preposition:
    `went to the shop` is not the phrasal verb go to, nor `walked in the
    park` walk in.  Those are offered as the plain verb, which the annotator
    may lengthen, rather than as a phrasal verb that has to be taken apart.
    """
    k = len(tail)
    rest = toks[i + 1:]
    if len(rest) < k or tuple(t[1] for t in rest[-k:]) != tail:
        return False
    gap = rest[:-k]
    if len(gap) > 2:
        return False
    # nothing may end a phrase before the last word: `slept, and the wind`
    for t in [toks[i]] + gap + rest[-k:-1]:
        if not t[2].endswith(t[0]):
            return False
    if any(t[1] in _BREAK for t in gap):
        return False
    # THE NEARER VERB HAS THE PARTICLE.  In `he had given up` the up is
    # given's -- give up -- and not had's, though the dictionary has a have
    # up (to arrest).  A word between them that is a verb with a phrasal
    # verb of its own on this tail takes it; a noun does not, and a word
    # after a determiner is one: `turned the light off`.
    if conn is not None:
        for n, t in enumerate(gap):
            if n and gap[n - 1][1] in _DETERMINERS:
                continue
            if t[1] in _DETERMINERS:
                continue
            if _verb_with(conn, t, tail):
                return False
    return True


def _verb_with(conn, tok, tail):
    """Is `tok` a form of a verb that has the phrasal verb `<verb> <tail>`?"""
    for r in conn.execute(
            "SELECT DISTINCT e.headword FROM form f JOIN entry e ON "
            "e.id = f.entry_id WHERE f.form IN (?, ?) AND e.pos = 'verb'",
            (tok[0], tok[1])):
        if conn.execute("SELECT 1 FROM entry WHERE headword = ? AND pos = 'verb'",
                        (r["headword"] + " " + " ".join(tail),)).fetchone():
            return True
    return False


def _phrasal_here(ctx, lemma, data):
    """The phrasal verb this hit is the verb of, in this chunk, as an entry
    id -- or None.  Reads the chunk only when the dictionary HAS a phrasal
    verb of this verb, so the answer depends on the chunk only then
    (verbs.Ctx.text: the cache keys on the chunk for a recipe that read it).
    """
    found = _phrasals(ctx.conn, lemma, _particles(data))
    if not found:
        return None
    toks = _tokens(ctx.text)
    w = (ctx.word or "").casefold()
    for i, t in enumerate(toks):
        if t[1] != w:
            continue
        # the longest phrasal verb first: put up with before put up
        for eid, tail in sorted(found, key=lambda x: -len(x[1])):
            if _closes(toks, i, tail, ctx.conn):
                return eid
    return None


def _particle_of_phrasal(ctx, data):
    """Is this hit's word the particle of a phrasal verb the chunk has?
    `down` in `and put it down.` is a verb in the dictionary (to down a
    drink) and a particle on the page, and a \\vb of the verb down would be
    a wrong answer offered with confidence; so is `out` (to out someone) in
    `Tom likes trying out new things`.  A particle is the phrasal verb's
    wherever it stands right after a verb that has one with it -- the
    chunk-end rule (_closes) is for choosing the phrasal verb, and asking
    less here only takes away a \\vb that was never the word's."""
    parts = _particles(data)
    w = (ctx.word or "").casefold()
    if w not in parts:
        return False
    toks = _tokens(ctx.text)
    for j, t in enumerate(toks):
        if t[1] != w:
            continue
        if j and toks[j - 1][2].endswith(toks[j - 1][0]) \
                and _verb_with(ctx.conn, toks[j - 1], (w,)):
            return True
        if j + 1 != len(toks):
            continue
        for i in range(max(0, j - 4), j):
            for k in range(1, j - i + 1):
                tail = tuple(x[1] for x in toks[j - k + 1:j + 1])
                if all(x in parts for x in tail) \
                        and _verb_with(ctx.conn, toks[i], tail) \
                        and _closes(toks, i, tail, ctx.conn):
                    return True
    return False


# ------------------------------------------------------------ the meaning
# SENSES THAT ARE ABOUT GRAMMAR, NOT MEANING.  be's first ranked sense is "As
# an auxiliary verb:", then "Used with past participles of verbs to form the
# passive voice."; do's first five are "A syntactic marker ...".  A
# vocabulary line wants the verb's meaning: to exist, to perform.
_GRAMMAR = re.compile(r"(?i)^(used\b|a syntactic marker|as an? [a-z -]*verb\b)")
# A DEFINITION OF A VERB SAYS "to": at its start (after a qualifier in
# brackets), or after the subject it is said of -- "Of a liquid: to fall in
# drops", "(of a boat), to sail".
_TO = re.compile(r"(?i)(^(\([^()]*\)\s*)*|[:;,)]\s*)to\b")


def _not_a_meaning(sense, tags=""):
    """A sense that says how the verb is used and not what it means, or
    heads a group of senses without being one: be's "As a copulative
    verb:", do's "A syntactic marker.", tell's "Mental senses related to
    determining, reckoning, or perceiving" (its first ranked sense; the
    meaning is the next one, "To determine the number...").  A heading that
    IS a definition says to, and stays: go's "To move, either physically or
    in an abstract sense:"."""
    s = (sense or "").strip()
    if _GRAMMAR.match(s) or "auxiliary" in (tags or "").split(","):
        return True
    return not _TO.search(s)


def _meaning(e, gloss):
    """The first ranked sense of `e` that is a meaning, trimmed as the core
    trims one, with Wiktionary's capital To lowered -- English Wiktionary
    defines an English verb in a sentence ("To move ...") and a vocabulary
    line is not one (docs/lang/en.md: `to move from here to there`)."""
    if not verbs.gloss_is_en(gloss):
        return ""
    senses = [s for s in (e.row["sense"] or "").split("\n") if s.strip()]
    ranked = lookup.rank_senses(senses, (e.row["sense_tags"] or "").split("\n"))
    for sense, tags, _tier in ranked:
        if not _not_a_meaning(sense, tags):
            return _lower_to(verbs.trim_meaning(sense))
    return _lower_to(verbs.trim_meaning(ranked[0][0])) if ranked else ""


def _lower_to(m):
    """The capital a definition sentence starts with, lowered where it is the
    `To` of the infinitive or the `Of` of "Of a liquid: to fall in drops" --
    and nowhere else, since an English gloss may start with a name."""
    return re.sub(r"^((?:\([^()]*\)\s*)*)(To|Of)\b",
                  lambda x: x.group(1) + x.group(2).lower(), m or "")


# ------------------------------------------------------------ the parts
def _parts(conn, e, surface, data, missing):
    """The three (form, sound) pairs of a one-word verb entry."""
    lemma = e.headword
    sound, why = _house(e.row["ipa"], lemma) if e.row["ipa"] else ("", "")
    if not sound:
        missing.append("the sound of %s" % lemma
                       + (" (the dictionary's %s is %s)" % (e.row["ipa"], why)
                          if e.row["ipa"] else ""))
    past = (_slot(e, _PAST, frozenset(("US",)), surface)
            or _persons_past(e) or _by_pointer(conn, e, _PAST))
    pp = _slot(e, _PP, frozenset(("US",)), surface) or _by_pointer(conn, e, _PP)
    # the edition's p.p. over the dictionary's first one (en.verbs.json `pp`:
    # get, gotten) -- unless the chunk has the other one AS a p.p. only.  It
    # cannot be told from the word whether `got` is the past or the p.p.,
    # and when the word is the past slot's too it is read as the past.
    want = (data.get("pp") or {}).get(lemma)
    if want and pp and any(f.own and f.form == want and _PP <= f.tags
                           for f in e.rows) and \
            (not surface or pp.casefold() != surface
             or surface in (past or "").casefold().split(", ")):
        pp = want
    if not past:
        missing.append("the past")
    if not pp:
        missing.append("the past participle")
    out = [(lemma, sound)]
    for form in (past, pp):
        if form and ", " in form:            # be: was, were
            each = [_sound_of(conn, e, x, sound, data, missing)
                    for x in form.split(", ")]
            out.append((form, ", ".join(each) if all(each) else ""))
        else:
            out.append((form or "", _sound_of(conn, e, form, sound, data, missing)))
    return out


def _base_for(conn, lemma, past, pp):
    """The verb entry a phrasal verb is built on: the one spelled `lemma`
    whose own past (or p.p.) is the phrasal verb's -- `wound up` is wind
    (wound), not wind (winded), and wind up is waɪnd ʌp."""
    ids = _twins(conn, lemma)
    for eid in ids:
        e = _entry(conn, eid)
        if (past and past in e.own(_PAST)) or (pp and pp in e.own(_PP)):
            return e
    return _entry(conn, ids[0]) if len(ids) == 1 else None


def _phrasal_parts(conn, p, surface, data, missing):
    """The three pairs of a phrasal verb entry `p` (give up): its forms from
    its own rows, its sounds from its own pronunciation where it has one
    (come in /ˌkʌm ˈɪn/, wind up /waɪnd ˈʌp/) and otherwise its verb's and
    its particles' -- give up is give and up, gave up is gave and up."""
    words = p.headword.split(" ")
    verb, tail = words[0], words[1:]
    parts = _particles(data)
    past = _slot(p, _PAST, frozenset(("US",)), surface)
    pp = _slot(p, _PP, frozenset(("US",)), surface)
    if not past:
        missing.append("the past")
    if not pp:
        missing.append("the past participle")

    def split(form):
        """`gave up` -> `gave`, when what follows it is the headword's own
        particles; else None."""
        w = (form or "").split(" ")
        return w[0] if len(w) == len(words) and w[1:] == tail else None

    own, _why = _house(p.row["ipa"], p.headword) if p.row["ipa"] else ("", "")
    if own and len(own.split(" ")) != len(words):
        own = ""                          # a sound that cannot be told word from word
    tail_sounds = own.split(" ")[1:] if own else [parts.get(t, "") for t in tail]
    base = _base_for(conn, verb, split(past), split(pp))
    base_sound = ""
    if base is not None and base.row["ipa"]:
        base_sound = _house(base.row["ipa"], verb)[0]
    verb_sound = own.split(" ")[0] if own else base_sound

    def sound(form, is_lemma=False):
        if is_lemma and own:
            return own
        v = split(form)
        if not v or not all(tail_sounds):
            return ""
        if v == verb:
            s = verb_sound
        elif verb_sound and _regular(verb, v):
            s = _ed(verb_sound)
        elif base is not None:
            s = _sound_of(conn, base, v, verb_sound, data, [])
        else:
            s = ""
        return (s + " " + " ".join(tail_sounds)) if s else ""

    out = []
    for form, is_lemma in ((p.headword, True), (past, False), (pp, False)):
        s = sound(form, is_lemma) if form else ""
        if form and not s:
            missing.append("the sound of %s" % form)
        out.append((form or "", s))
    return out


def _extras(data, lemma, past):
    """The present of be, have, do and say, in the words docs/lang/en.md
    gives it -- and only for the verb the list means: the entry's past must
    be the one the list names (say, to assay, has sayed)."""
    got = (data.get("present") or {}).get(lemma)
    if not got or got.get("past") not in (past or "").split(", "):
        return []
    items = [verbs.tl(f, s) for f, s in got.get("forms") or []]
    return ["pres. " + ", ".join(items)] if items else []


# ------------------------------------------------------------ the recipe
def _is_modal(e, data):
    """One of docs/lang/en.md's ten modals -- and, of the entries with that
    spelling, the one with no past participle, which is why a modal gets no
    \\vb: can (could, and `couth`, obsolete) is the modal, can (canned) is
    to put in cans."""
    if e.headword.casefold() not in set(data.get("modals") or ()):
        return False
    return not e.own(_PP)


def _plain(f, w):
    """Is row `f` the entry's own, current inflection spelled `w`?"""
    return (f.own and f.form.casefold() == w and bool(f.tags & _INFLECTION)
            and not f.tags & _DEAD)


# The region tags that do not mark a verb as another accent's: this edition
# is General American.
_HOME = frozenset(("US", "American", "General-American", "North-America",
                   "Canada"))


def _marked(tags):
    """Is a sense, by its tags, somebody's dialect, slang or history rather
    than the language a reader meets -- dialectal, obsolete, slang
    (lookup's own ranking), or a place: gan, to go, is `North, Northumbria,
    Yorkshire`, and Wiktionary writes a place with a capital."""
    if lookup._sense_rank(tags) >= 1:
        return True
    return any(t[:1].isupper() and t not in _HOME
               for t in (x.strip() for x in (tags or "").split(",")) if t)


def _marked_entry(tag_lines):
    lines = (tag_lines or "").split("\n")
    return bool(lines) and all(_marked(t) for t in lines)


def _claimed_elsewhere(conn, e, word):
    """Was this entry reached by a word that belongs to another verb?

    A word that is not this entry's headword nor one of its own current
    inflections, and IS another verb's -- that verb's headword, or its own
    plain form -- is that verb on the page, and that verb is a hit of its
    own.  So is a word that a dialect's verb has as a plain form and the
    language's verb has too.  What this keeps out, measured on the sentences
    of the tests:

      lied  -> lie, to recline: the page "past of lie" is linked to the
               first verb spelled lie; lie, to tell a lie, has lied as its
               own past.  A \\vb of lie, lay, lain was being offered.
      wound -> wind (winded), whose `wound` is `past proscribed`: the other
               wind has it plainly.
      went  -> wend and ween, which had it as an archaic past; go has it --
               and gan, Northumbrian for go, whose past it is too.
      would -> will, to bequeath (`would` `past rare`); the modal has it.
      take  -> tak, a Durham verb that lists take among its `alternative`
               forms; give -> gyve; put -> set store by; have -> can haz.
      must  -> mote, archaic `may or might`, whose past it is.
      met   -> met, an obsolete "to dream", whose headword it is; and sang
               -> sang, Appalachian slang for gathering ginseng.  A dialect's
               or history's verb steps aside even for its own headword when
               the language's verb has the word plainly.
    """
    w = (word or "").casefold()
    if not w:
        return False
    marked = _marked_entry(e.row["sense_tags"])
    mine = w == e.headword.casefold() or any(_plain(f, w) for f in e.rows)
    if mine and not marked:
        return False
    for r in conn.execute(
            "SELECT e.headword, e.sense_tags, f.note FROM form f JOIN entry e "
            "ON e.id = f.entry_id WHERE f.form IN (?, ?) AND e.pos = 'verb' "
            "AND f.entry_id != ?", (word, w, e.id)):
        note = r["note"] or ""
        tags = verbs.split_tags(note)
        theirs = ((r["headword"] or "").casefold() == w
                  or ("," not in note and tags & _INFLECTION and not tags & _DEAD))
        if theirs and (not mine or not _marked_entry(r["sense_tags"])):
            return True
    return False


def _reached_as_spelling(conn, e, word):
    """Did `word` reach this entry only as another way of spelling it, which
    on the page it is not?  `the` is an Early Modern spelling of thee, which
    is also a verb (to address someone as thee) -- and the headword of the
    article; `b` is an Internet spelling of be.  So: reached through no row
    that makes it a form of the verb (get's `gotten` is `... error-unknown-
    tag participle past recently`, and it is get), and either a word of its
    own in the dictionary, or a spelling nobody writes now, or a spelling of
    a verb that is itself dead.  A spelling in current use that is nothing
    else stays: a book spelt the British way still wants the \\vb of the
    verb its word spells."""
    w = (word or "").casefold()
    if not w or w == e.headword.casefold():
        return False
    rows = [f for f in e.rows if f.form.casefold() == w]
    if not rows:
        return False
    if any(f.tags & _INFLECTION for f in rows):
        return False
    if all(f.tags & _NOT_WRITTEN for f in rows):
        return True
    # an obsolete verb's current-looking spelling is as dead as the verb:
    # `had` is an `alternative` of hode, to ordain, whose every sense is
    # tagged obsolete
    if all(lookup._sense_rank(t) == 2
           for t in (e.row["sense_tags"] or "").split("\n")):
        return True
    return conn.execute("SELECT 1 FROM entry WHERE headword IN (?, ?) AND id != ? "
                        "LIMIT 1", (word, w, e.id)).fetchone() is not None


def _only_a_form(conn, e):
    """Is this entry a form of another verb that Wiktionary also defines --
    `had` ("used to form the past perfect tense"), `got` ("expressing
    obligation") -- rather than a verb of its own?  It has no past and no
    past participle of its own, and another verb has its headword as its
    plain past: the \\vb is that verb's (have, get), and that verb is a hit
    of its own for the same word."""
    if e.own(_PAST) or e.own(_PP):
        return False
    for r in conn.execute(
            "SELECT f.note FROM form f JOIN entry e ON e.id = f.entry_id "
            "WHERE f.form = ? AND e.pos = 'verb' AND e.headword != ? "
            "AND f.entry_id != ?", (e.headword, e.headword, e.id)):
        tags = verbs.split_tags(r["note"])
        if "," not in (r["note"] or "") and "past" in tags and not tags & _DEAD:
            return True
    return False


def recipe(ctx):
    if (ctx.entry["pos"] or "") != "verb":
        return None
    data = ctx.data()
    conn = ctx.conn
    e = _entry(conn, ctx.entry["id"])
    word = (ctx.word or "").casefold()
    if " " in e.headword.strip():
        # A PHRASAL VERB FOUND WHOLE -- by a lookup that asks for the words
        # together, which today's does not (it splits at spaces).  Reached
        # from ONE word it is the source's junk: get up off lists a bare
        # `got` as its past, set store by a bare `put` as an alternative.
        if " " not in word.strip():
            return None
        missing = []
        pairs = _phrasal_parts(conn, e, word, data, missing)
        if not pairs[1][0] and not pairs[2][0]:
            return None                   # no past and no p.p.: see below
        return verbs.Parts(pairs, meaning=_meaning(e, ctx.gloss),
                           missing=_dedup(missing))
    if _is_modal(e, data) or _only_a_form(conn, e):
        return None
    if _reached_as_spelling(conn, e, word) or _claimed_elsewhere(conn, e, word):
        return None
    if word in _particles(data) and _particle_of_phrasal(ctx, data):
        return None
    pid = _phrasal_here(ctx, e.headword, data)
    if pid is not None:
        p = _entry(conn, pid)
        missing = []
        pairs = _phrasal_parts(conn, p, word, data, missing)
        return verbs.Parts(pairs, meaning=_meaning(p, ctx.gloss),
                           missing=_dedup(missing))
    missing = []
    pairs = _parts(conn, e, word, data, missing)
    if not pairs[1][0] and not pairs[2][0]:
        # NEITHER A PAST NOR A PAST PARTICIPLE, which is what the \vb is
        # for.  Measured: 330 of 36 613 one-word verb entries, and they are
        # contractions (dunna, av), inflections with a page of their own
        # (sorroweth, glimpseth), abbreviations (KMS, rmb, cf.), spellings
        # (ware, "eye dialect spelling of were"), and a few verbs of
        # Singlish (chiong, gostan) with no table at all.  A \vb with both
        # slots empty prints what a \dw prints, and says it is a verb with
        # two parts nobody could find.
        return None
    # the core's meaning is the hit's first ranked sense; it is replaced only
    # where that sense is not a meaning at all (be, do, tell -- above), which
    # is asked of the sense as written and not of its trim
    first = next((s for s in ctx.hit.get("senses") or [] if (s or "").strip()), "")
    m = ctx.meaning
    if m and _not_a_meaning(first, (ctx.hit.get("marks") or [""])[0]):
        m = _meaning(e, ctx.gloss)
    return verbs.Parts(pairs, meaning=_lower_to(m) if m else m,
                       extras=_extras(data, e.headword, pairs[1][0]),
                       missing=_dedup(missing))


def _dedup(xs):
    out = []
    for x in xs:
        if x not in out:
            out.append(x)
    return out
