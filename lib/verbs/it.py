#!/usr/bin/env python3
"""Italian: what a \\vb says about a verb, from the dictionary's own rows.

    \\vb{venire}{}{vengo}{}{venuto}{}{to come (aux. \\pw{essere}; p.r. \\pw{venni})}
    \\vb{prendere}{prèndere}{prendo}{}{preso}{}{to take (p.r. \\pw{presi})}
    \\vb{alzarsi}{}{mi alzo}{}{alzato}{}{to stand up (aux. \\pw{essere})}

docs/lang/it.md says what an Italian \\vb is, and this is that page done by
the machine: the infinitive, the first person present and the past
participle, each with a sound only where the stress is not on the
next-to-last syllable; then, in the one parenthesis after the meaning, the
auxiliary when it is not plain avere, and the first person of the passato
remoto when it is not the regular one.  Everything comes from the head line
Wiktionary's editors wrote for the verb (it-verb), which kaikki keeps as the
entry's own form rows, the cell's name in the note:

    parlàre   canonical                            -> slot 1's sound, if needed
    pàrlo     first-person present singular        -> slot 2
    parlài    first-person historic past singular  -> p.r., if irregular
    parlàto   participle past                      -> slot 3
    avére     auxiliary                            -> aux., unless avere alone

and after it the generated conjugation table (gerund first), which is read
only where the head line is silent.

THE ROWS ARE PRONUNCIATIONS, NOT SPELLINGS, and that is the first thing
everything here has to deal with.  The head line writes every form with its
stressed vowel marked -- pàrlo, hò, sò, fùi, avére -- which is exactly what
a sound slot wants and exactly what a form slot must never print.  Italian
spells an accent only on a final stressed vowel of a word of more than one
syllable (parlò, può, già), so a form is written by taking every other
accent off (_written).  Measured against the unaccented pages the same
dictionary links to the same verbs (`parlo` "first-person, indicative,
present, singular"), that gives the page's own spelling for 7773 of 7785
first persons, 7422 of 7452 participles and 7444 of 7490 first persons of
the passato remoto; each of the rest is a second variant (abbuòno against
the page abbono, cernìto against cernuto), not a misspelling.

WHAT IS NOT A VERB'S OWN TABLE IS FOLLOWED TO ONE, never guessed at.  Of the
47 138 entries tagged verb, 33 290 are an enclitic compound with no table of
its own -- alzandosi, dimmelo, farlo: "compound of alzando, the gerund of
alzare, with si" -- and a few dozen are a page for one form ("first-person
plural present indicative/present subjunctive of potere").  The sense names
the verb, and the \\vb is that verb's (_target).  The one thing read from
the chunk is whether a reflexive pronoun stands before the word
(_pronominal): `si alzò` reaches alzare, "to lift", and the verb on the page
is alzarsi, "to get up", with essere.

None for a hit that is not a verb, and for a verb the dictionary cannot
describe (a compound of a verb it has no page for, a fixed form like `vedasi`
with no infinitive to name); the editor then offers the \\dw it always did.
"""
import re
import unicodedata

import lookup
import verbs

# ------------------------------------------------------------- the spelling
_MARKED = "àèéìíòóùúÀÈÉÌÍÒÓÙÚ"
_VOWELS = frozenset("aeiouAEIOU" + _MARKED)


def _fold(s):
    """`s` without its accents: èssere -> essere.  Accents are the only marks
    the rows carry: every non-ASCII letter in the slots' rows of the
    2026-09-10 dictionary is one of à è é ì í ò ó ù."""
    return "".join(ch for ch in unicodedata.normalize("NFD", s or "")
                   if unicodedata.category(ch) != "Mn")


def _written_word(w, keep):
    """One word of a head-line form as Italian spells it.

    Every accent goes but a final one on a word with a vowel before it:
    parlò, può, andrò keep theirs; pàrlo, hò, sò, dò, stò lose theirs.  A
    word the HEADWORD spells with an accent keeps it however short it is:
    `essere lì per` has the first person `sóno lì per`, and lì is a word
    whose accent is its spelling (li is a pronoun), which the rule alone
    would take off.
    """
    f = _fold(w)
    if f in keep:
        return keep[f]
    if w and w[-1] in _MARKED and any(ch in _VOWELS for ch in w[:-1]):
        return _fold(w[:-1]) + w[-1]
    return f


def _written(form, headword=""):
    """A head-line form as it is spelled (see _written_word)."""
    keep = {_fold(x): x for x in (headword or "").split()}
    return " ".join(_written_word(w, keep) for w in (form or "").split())


def _nuclei(s):
    """How many syllables `s` has, counted by its vowels: a, e and o are one
    each; an i or u beside another vowel is a glide in the same syllable
    (stù-dio, lìn-gua, fàc-cia-no), and alone is a syllable (à-bi-to)."""
    low, n = s.lower(), 0
    for i, ch in enumerate(low):
        if ch not in _VOWELS:
            continue
        if _fold(ch) in "iu":
            prev = low[i - 1] if i else ""
            nxt = low[i + 1] if i + 1 < len(low) else ""
            if (prev and prev in _VOWELS) or (nxt and nxt in _VOWELS):
                continue
        n += 1
    return n


def _off_penult(word):
    """Is this head-line word stressed where a reader would not stress it?

    Italian stresses the next-to-last syllable unless told otherwise, and
    its spelling tells only of a last one (parlò).  So a word needs its sound
    exactly when the marked vowel has two syllables or more after it --
    prèndere, àbito, desìdero, telèfono, èssere, andàrsene -- and never for
    pàrlo, avére or vedére, whose marks tell only what the reader would do
    anyway and whether an e or an o is open, which is the business of the
    chunk's own pronunciation line (docs/lang/it.md).  Over the 12 493
    one-word verbs given a \\vb, that puts a sound on 1081 infinitives, 1744
    first persons and 3 participles; counting the open and closed vowels too
    would have put one on half of the first persons.
    """
    marks = [i for i, ch in enumerate(word) if ch in _MARKED]
    if len(marks) != 1:
        return False                    # unmarked, or a page's typo (perplèttére)
    i = marks[0]
    after = _nuclei(word[i + 1:])
    if after >= 2:
        return True
    # stress on the last syllable, which the spelling shows only when the
    # marked vowel IS the last letter; a word of one syllable needs nothing
    return after == 0 and i != len(word) - 1 and _nuclei(word[:i]) > 0


def _sound(form):
    """A slot's sound: the head line's own marked spelling of the whole form,
    where any word of it is stressed off the next-to-last syllable, and
    nothing otherwise."""
    words = (form or "").split()
    return " ".join(words) if any(_off_penult(w) for w in words) else ""


# ------------------------------------------------------------- the clitics
# The unstressed pronouns a verb carries, before it (mi alzo, me ne vado, ce
# la faccio) or fused onto it (alzarsi, andarsene, farcela, esserci).
_CLITIC_WORDS = frozenset("mi ti si ci vi me te se ce ve ne lo la li le gli glie".split())
# a pronominal infinitive's tail: si, sene, sela, cela, ci, ne, la ...
_TAIL = re.compile(r"^(.*r)((?:[mtscv]i|[mtscv]e(?:ne|l[aeio])|gli(?:el[aeio]|ene)?"
                   r"|ne|l[aeio]))$")


def _untailed(form, tail):
    """A pronominal verb's form without the pronoun fused onto its verb word:
    alzàtosi -> alzàto, andàtosene -> andàto, fàttocela -> fàtto, and in an
    idiom the verb's word alone (`mèssosi all'òpera` -> `mèsso all'òpera`)."""
    if not tail:
        return form
    words = (form or "").split()
    for k, w in enumerate(words):
        if _fold(w).lower().endswith(tail) and len(w) > len(tail):
            words[k] = w[:len(w) - len(tail)]
            break
    return " ".join(words)


def _verb_word(form):
    """The verb of a form of several words, which is its first word that is
    not a pronoun: `me ne vàdo` -> vàdo, `gètto perle ai porci` -> gètto."""
    for w in (form or "").split():
        if _fold(w).lower() not in _CLITIC_WORDS:
            return w
    return ""


def _split_tail(headword):
    """(the infinitive with its r, the clitic tail) of a pronominal
    headword's verb word -- alzarsi (alzar, si), andarsene (andar, sene),
    farcela (far, cela), porsi (por, si) -- else (the word, "")."""
    w = ((headword or "").split() or [""])[0]
    m = _TAIL.match(w)
    return (m.group(1), m.group(2)) if m else (w, "")


def _conjugation(headword):
    """('are' | 'ere' | 'ire' | 'rre' | '', stem) of a headword's verb word.
    A tail leaves the infinitive without its last e (alzar-si, accorger-si)
    and a -rre verb without its -re (por-si, from porre), so a stem in `r`
    that is not -ar, -er or -ir is -rre."""
    stem_r, tail = _split_tail(headword)
    w = _fold(stem_r).lower()
    if tail:
        w = w + "e" if w[-2:] in ("ar", "er", "ir") else w + "re"
    for end in ("rre", "are", "ere", "ire"):
        if w.endswith(end):
            return end, w[:-3]
    return "", w


def _regular_pr(headword, pr, third=False):
    """Is `pr` (the verb word, written) the regular passato remoto of this
    headword -- first person, or third for a verb that has only the third?

    Regular is what the infinitive predicts: -are parlai, -ere credei or
    credetti (both are regular, and dovere's first row is dovetti), -ire
    finii; a -rre verb has none.  Only an irregular one is printed
    (docs/lang/it.md): for 1236 of the 12 493 one-word verbs given a \\vb --
    fare feci, dire dissi, vedere vidi, venire venni, prendere presi, stare
    stetti, dare diedi -- and for none of andai, dovetti, uscii, aprii.
    """
    end, stem = _conjugation(headword)
    p = _fold(pr).lower()
    if end == "are":
        return p == stem + ("o" if third else "ai")
    if end == "ere":
        return p in ((stem + "e", stem + "ette") if third else (stem + "ei", stem + "etti"))
    if end == "ire":
        return p == stem + ("i" if third else "ii")
    return False


# ------------------------------------------------------------- the rows
_FIRST_PRES = frozenset(("first-person", "present", "singular"))
_THIRD_PRES = frozenset(("present", "singular", "third-person"))
_PART_PAST = frozenset(("participle", "past"))
_FIRST_PR = frozenset(("first-person", "historic", "past", "singular"))
_THIRD_PR = frozenset(("historic", "past", "singular", "third-person"))

# the qualifiers a less usual variant may carry and still be offered where
# the head line gives no plain one
_OK_EXTRA = frozenset(("indicative", "common", "traditional", "uncommon",
                       "formal", "rare", "error-unknown-tag"))


def _head_end(t):
    """The rowid where the head line ends: its table's first row, the
    gerund.  (Not the unaccented `parlando` `gerund` at the very end, which
    is the page parlando pointing here, one tag and so no comma.)"""
    for f in t.rows:
        if f.note == "gerund" and f.form != _fold(f.form):
            return f.rowid
    return float("inf")


def _slot(t, core):
    """The first own row for one cell, best source first.

    THE HEAD LINE, THEN THE TABLE, THEN A QUALIFIED VARIANT.  The head line's
    note is exactly the cell (`first-person present singular`) and its first
    row is the editors' first form: dovere dèvo before débbo, porre pósto
    before ponuto, perdere pèrsi before perdétti.  A head line without the
    cell (succedere's is broken by a stray row) leaves the table's
    `first-person indicative present singular`.  Last, a form the source
    marks as the less usual one -- soddisfare has no plain first person, only
    soddisfàccio `uncommon` and soddìsfo `common ... proscribed`; convergere's
    only participle is the table's `convèrso` `participle past rare` -- but
    never a subjunctive, an archaic, a poetic or a proscribed one.  The rows
    are in the page's order, so the head line is always asked before its
    table and the table before the variants the table lists after itself.
    """
    r = t.pick(exact=core, own=True)
    if r is None:
        r = t.pick(exact=core | {"indicative"}, own=True)
    if r is None:
        r = t.pick(require=core, own=True, where=lambda f: f.tags - core <= _OK_EXTRA)
    return r


# THE AUXILIARY.  Kept: a row tagged `auxiliary` whose word is avere or
# essere, qualifiers and all -- a dual verb's rows say which meaning takes
# which (`auxiliary intransitive` and `auxiliary transitive`: passare,
# salire, crescere), and an exact match on the note `auxiliary` finds 12 873
# of the 14 022 such rows and gives correre (`auxiliary error-unknown-tag
# goal`) and cominciare none at all.  Dropped: what the source itself says
# is not the ordinary auxiliary -- an archaic one, one that is only `rare`,
# `uncommon` or `traditional` (vivere's `èssere` `auxiliary traditional
# uncommon`, volgere's `auxiliary rare`), and a bare `also auxiliary`, which
# is prendere's èssere "also in the meaning 'to happen unexpectedly'" with
# the meaning lost: kept, the line would say prendere takes essere.
_AUX_GONE = frozenset(("archaic", "obsolete", "dated", "dialectal", "regional"))
_AUX_WEAK = frozenset(("rare", "uncommon", "traditional"))
_AUX_NOISE = frozenset(("auxiliary", "also", "error-unknown-tag"))
# A sense nobody uses today, for _transitive: what lookup ranks last (obsolete,
# archaic, rare, nonstandard ...), and what is written only in books or only
# somewhere (literary, poetic, dialectal, a region: `Tuscany`).  Not the
# figurative, colloquial or slang ones -- agghiacciare's transitive "to
# frighten" is `figuratively` and is how the verb is used.
_NOT_NOW = frozenset(lookup._STALE) | {"literary", "poetic", "dialectal", "regional"}


def _transitive(t):
    """Is the verb used transitively today, as far as its senses say?

    True for a current transitive sense; False where the senses do describe a
    transitive use and every one of them is out of use; None where no sense
    is tagged transitive at all -- which says nothing, because the senses
    under-describe: accrescere's only sense is "to increase", intransitive,
    and `ha accresciuto il patrimonio` is the commonest thing it does.
    """
    said = False
    for tags in t.sense_tags:
        if not tags & {"transitive", "ambitransitive"}:
            continue
        said = True
        if not (tags & _NOT_NOW) and not any(x[:1].isupper() for x in tags):
            return True
    return False if said else None


def _auxiliaries(t):
    """['avere'] / ['essere'] / ['avere', 'essere'] from the head line (the
    table's only where the head line has none), [] when neither says.

    THE HEAD LINE'S AUXILIARY, NOT THE TABLE'S.  The table repeats it, and
    the repeat is dropped as the head line's own spelling (lib/getdict.py);
    what is left of the table's is an auxiliary the head line does NOT give,
    listed after the table among its variants.  piacere's head line says
    essere and nothing else, and its table's `avére` sits beside `piàcio`
    and `piàceno`; volere's head line says avere, and the table's `èssere`
    beside `volsùto`; insegnare's beside `inségneno`.  Read as rows, those
    made piacere and volere take "avere/essere", which docs/lang/it.md says
    piacere does not.  Only where the head line has none (eccellere,
    convergere, permanere: their head lines give no participle either) is
    the table's taken.
    """
    rows = t.picks(require={"auxiliary"}, own=True)
    end = _head_end(t)
    head = [f for f in rows if f.rowid < end]
    got = []
    for f in head or rows:
        word = _fold(f.form).strip().lower()
        if word not in ("avere", "essere") or f.tags & _AUX_GONE:
            continue
        q = f.tags - _AUX_NOISE
        if (q and q <= _AUX_WEAK) or (not q and "also" in f.tags):
            continue
        # AN AVERE FOR A TRANSITIVE USE NOBODY MAKES TODAY is not a second
        # auxiliary.  arrivare, tornare and morire are essere verbs whose
        # head lines add `avére` `auxiliary transitive` -- for "to reach (a
        # person)", literary; "to give back", literary; "to kill", obsolete
        # and Tuscan -- and "aux. avere/essere" would tell a reader `ho
        # arrivato`.  Only this case is checked against the senses, and only
        # where they describe the transitive use (_transitive): they
        # under-describe, the intransitive side most (cambiare's two senses
        # are both transitive, and `è cambiato` is the commonest thing it
        # does), so an essere for an intransitive use is always believed.
        if word == "avere" and "transitive" in q and "intransitive" not in q \
                and _transitive(t) is False:
            continue
        if word not in got:
            got.append(word)
    # ONE ORDER FOR "BOTH", whichever the page gives first.  correre's head
    # line has èssere before avére and cominciare's avére before èssere, and
    # the reader is told "aux. avere/essere" means both (docs/lang/it.md): a
    # line that said "essere/avere" for some verbs would look like it meant
    # something else.
    return sorted(got)


# ------------------------------------------------------------ the entries
# The cells that make an entry a verb's table.  Not the marked spelling alone:
# `fiero` has a `canonical` row and nothing else, and its sense is "Old
# Italian form of saranno, third-person plural future of essere".
_SLOT_NOTES = ("first-person present singular", "participle past",
               "present singular third-person",
               "first-person indicative present singular")


def _has_table(conn, eid):
    """Does this entry carry a table of its own (a cell a \\vb prints)?"""
    return conn.execute(
        "SELECT 1 FROM form WHERE entry_id = ? AND note IN (%s) LIMIT 1"
        % ",".join("?" * len(_SLOT_NOTES)), (eid,) + _SLOT_NOTES).fetchone() is not None


def _verb_entry(conn, headword):
    """The first verb entry by that headword that has a table, or None.
    FIRST BY ID: trovare has two verb entries, "to find" and "to compose
    poetry", and the first is the one the page lists first."""
    for (eid,) in conn.execute(
            "SELECT id FROM entry WHERE headword = ? AND pos = 'verb' ORDER BY id",
            (headword,)):
        if _has_table(conn, eid):
            return eid
    return None


def _spelt_as(conn, word):
    """The verb a word is another spelling of: `pronunziare` has no page of
    its own, only a row `alternative spelling` on pronunciare's -- and 307
    compounds are of a verb like that."""
    for (eid,) in conn.execute(
            "SELECT f.entry_id FROM form f JOIN entry e ON e.id = f.entry_id "
            "WHERE f.form = ? AND e.pos = 'verb' AND f.note LIKE '%alternative%' "
            "ORDER BY f.rowid", (word,)):
        if _has_table(conn, eid):
            return eid
    return None


def _sub(ctx, eid):
    """A Ctx for another entry -- the verb a compound or a form names --
    reading the same dictionary, or None.  The chunk is read through `ctx`
    alone; a read through this one would tell the cache all the same
    (verbs.Ctx.other)."""
    return ctx.other(eid)


# "compound of the infinitive fare with lo", "compound of alzando, the gerund
# of alzare, with si", "compound of farmi, the first-person singular
# infinitive of farsi, with la": 33 277 of the 33 290 compounds, and the verb
# they name has a table for 32 970 of them.  Five more say it another way --
# smettila, piantala, finiscila: "Compound of imperative (tu form) of
# smettere and la."
_COMPOUND = re.compile(
    r"^compound of (?:the infinitive (\S+)|(\S+?),? the (.+?) of (\S+?),?) "
    r"with (.+?)\.?$", re.I)
_COMPOUND_IMP = re.compile(
    r"^compound of (imperative) \(\w+ form\) of (\S+) and (.+?)\.?$", re.I)
# A PAGE FOR ONE FORM, said as a sentence rather than as a pointer: possiamo
# "first-person plural present indicative/present subjunctive of potere",
# morto "past participle of morire", capivo "first-person singular impfect
# indicative of capire", simo "alternative form of siamo: inflection of
# essere", fenno "old form of fecero, past historic of fare".  Lookup reaches
# nothing else for them -- `possiamo` comes back as this page and not as
# potere -- so the verb it names is the \vb: the last word after an "of"
# that is a verb with a table (fecero is not, fare is).
_FORM_WORDS = re.compile(
    r"(?i)\b(?:first|second|third)[- ]person\b|\bparticiple\b|\bgerund\b|"
    r"\binflection of\b|\bpast historic\b|\bimperfect\b|\bimpfect\b|\bform of\b")
_OF = re.compile(r"(?i)\bof ([^\s,;:.()“”]+)")
_INFINITIVE = re.compile(r"(?:are|ere|ire|rre)$")


def _compound(sense):
    """(verb, the form it is in, [clitics]) of a compound's sense, or None."""
    m = _COMPOUND.match(sense or "")
    if m:
        base = m.group(1) or m.group(4)
        what = "infinitive" if m.group(1) else (m.group(3) or "")
        tail = m.group(5)
    else:
        m = _COMPOUND_IMP.match(sense or "")
        if not m:
            return None
        what, base, tail = m.group(1), m.group(2), m.group(3)
    clit = [w for w in re.findall(r"\b([a-z]+)\b", re.sub(r"\([^)]*\)", "", tail))
            if w in _CLITIC_WORDS]
    return base, what, clit


def _pronominal_head(conn, base, tail):
    """The pronominal verb made of this infinitive and this clitic tail --
    alzare + si -> alzarsi, andare + sene -> andarsene, fare + cela ->
    farcela -- as (entry id, headword) if the dictionary has it with a
    table, else None."""
    if " " in base or _split_tail(base)[1]:
        return None
    w = _fold(base).lower()
    if w.endswith("rre"):
        head = base[:-2] + tail
    elif w.endswith(("are", "ere", "ire")):
        head = base[:-1] + tail
    else:
        return None
    eid = _verb_entry(conn, head)
    return (eid, head) if eid else None


def _compound_target(ctx, base, what, clit, depth=0):
    """The verb a compound is a form of: the pronominal one where its pronoun
    makes it reflexive, else the one the sense names.

    A SI MAKES IT THE PRONOMINAL VERB.  alzandosi is alzando + si, and the
    verb it is a form of is alzarsi, "to get up", essere -- not alzare, "to
    lift", avere.  Only si (or se, its form before ne and lo) says so alone:
    mi, ti, ci and vi are as often the object (vederti is "to see you"),
    unless the verb is in their own person, which only an imperative shows
    (alzatevi, alziamoci).

    A compound can name another compound -- essendosene is "compound of
    essendosi, the gerund of essersi, with ne", and essersi is "compound of
    the infinitive essere with si" -- and that one is followed once more.
    """
    first = clit[0] if clit else ""
    rest = "".join(clit[1:2])
    refl = first in ("si", "se") or (
        first in ("ti", "te") and "second-person singular imperative" in what) or (
        first in ("vi", "ve") and "second-person plural imperative" in what) or (
        first in ("ci", "ce") and "first-person plural imperative" in what)
    if refl:
        for tail in (["se" + rest] if rest else []) + ["si"]:
            got = _pronominal_head(ctx.conn, base, tail)
            if got:
                return _sub(ctx, got[0])
    got = _verb_entry(ctx.conn, base) or _spelt_as(ctx.conn, base)
    if got:
        return _sub(ctx, got)
    if depth == 0:
        for (sense,) in ctx.conn.execute(
                "SELECT sense FROM entry WHERE headword = ? AND pos = 'verb' "
                "ORDER BY id", (base,)):
            comp = _compound((sense or "").split("\n")[0].strip())
            if comp:
                return _compound_target(ctx, *comp, depth=1)
    return None


def _named(ctx, sense):
    """The verb with a table that a sense names last after an "of", or None."""
    for name in reversed(_OF.findall(sense)):
        got = _verb_entry(ctx.conn, name)
        if got:
            return _sub(ctx, got)
    return None


def _target(ctx):
    """The Ctx of the entry whose table describes this verb -- ctx itself
    when it has one, or when it is an infinitive nothing else describes --
    or None for a hit that names no verb this can describe."""
    if _has_table(ctx.conn, ctx.entry["id"]):
        return ctx
    first = next((s.strip() for s in ctx.senses if s.strip()), "")
    comp = _compound(first)
    if comp:
        return _compound_target(ctx, *comp)
    head = ctx.entry["headword"] or ""
    verb = _fold(head.split()[0] if head.split() else "").lower()
    if not (_INFINITIVE.search(verb) or _split_tail(verb)[1]):
        # a form, not an infinitive: the verb its sense names, if any
        return _named(ctx, first) if _FORM_WORDS.search(first) else None
    # AN INFINITIVE THAT IS ANOTHER'S FORM is that verb: sarpare is "Old
    # Italian form of salpare", savere "alternative form of sapere", and
    # neither page has a table of its own
    if re.search(r"(?i)\b(?:form|spelling) of\b", first):
        got = _named(ctx, first)
        if got is not None:
            return got
    # AN INFINITIVE WITH NO TABLE is a verb all the same -- gamificare "to
    # gamify", nullafare, autoaffermarsi, and 230 idioms whose page has no
    # head line (dare nell'occhio, mangiarsi le mani) -- and gets its \vb
    # with what the source did not give named as missing
    return ctx


# ------------------------------------------------- a pronoun before the word
# The pronominal tails a pronoun before the verb can stand for: `mi alzo`,
# `si alza`, `ci alziamo` are all alzarsi, `me ne vado` is andarsene, `ce la
# faccio` is farcela, and `ci sono` is esserci as well as a reflexive's first
# person plural.  Only candidates: the source's own row decides.
_TAILS_ONE = {"mi": ["si"], "ti": ["si"], "si": ["si"], "ci": ["si", "ci"], "vi": ["si"]}
_TAILS_TWO = {"ne": "sene", "la": "sela", "le": "sele", "lo": "selo", "li": "seli"}
_PERSON = {"mi": ("first-person", "singular"), "ti": ("second-person", "singular"),
           "si": ("third-person", ""), "ci": ("first-person", "plural"),
           "vi": ("second-person", "plural")}


def _tails(cluster):
    """The pronominal tails a pronoun cluster before a verb can stand for."""
    c = [_fold(w).lower() for w in cluster]
    if len(c) == 1:
        return _TAILS_ONE.get(c[0], [])
    if len(c) == 2 and c[0] in ("me", "te", "se", "ce", "ve") and c[1] in _TAILS_TWO:
        return [_TAILS_TWO[c[1]]] + (["cela"] if c == ["ce", "la"] else [])
    return []


def _pronominal(ctx, t):
    """(the pronominal verb's Ctx, what is not settled) when the chunk puts
    a reflexive pronoun before this word, else None.

    `si alzò` reaches alzare, "to lift", avere -- the page `alzò` is a form
    of alzare, and lookup reads one word at a time -- while the verb the
    reader is looking at is alzarsi, "to get up", essere.  The dictionary
    says so word for word: alzarsi's own table has the row `si alzò`.  So
    the chunk is read (only for a verb that HAS a pronominal twin: reading it
    makes the cache keep one entry per chunk), the pronouns before the word
    are joined to it, and the twin is taken only when that string is one of
    the twin's rows -- which also makes the persons agree: `mi alzo` is a row
    of alzarsi, `mi dice` (he tells me) is no row of dirsi.  In a compound
    past (`si è alzato`, `mi sono alzato`) the participle follows a form of
    essere, whose person the pronoun must be: `mi è piaciuto` is piacere,
    to me, and not piacersi.

    SI IS SAID TO BE UNSETTLED, because it is: `si alzò` is alzarsi, but
    `si dice` -- "one says" -- is dire, and dirsi has the row `si dice` too.
    The pronominal verb is offered (a narrative's si is mostly reflexive) and
    `missing` names the question, so the editor's button says it is open.
    """
    head = t.entry["headword"] or ""
    if " " in head or _split_tail(head)[1]:
        return None
    twins = {}
    for tail in ("si", "sene", "ci", "cela", "sela", "sele", "selo", "seli"):
        got = _pronominal_head(ctx.conn, head, tail)
        if got:
            twins[tail] = got
    if not twins:
        return None
    L = ctx.L
    words = [lookup._bare(w, L) for w in L.split_words(ctx.text or "")]
    low = [_fold(w).lower() for w in words]
    me = _fold(lookup._bare(ctx.word or "", L)).lower()
    note = ctx.hit.get("note") or ""
    for i, w in enumerate(low):
        if w != me:
            continue
        # AN AUXILIARY IS NOT ITS OWN VERB.  `ci siamo alzati` is alzarsi in
        # the perfect, and its `ci siamo` -- a row of esserci, "to be there"
        # -- is only the auxiliary: a word followed by a past participle is
        # left as the verb it is.
        aux = i + 1 < len(words) and _participle(ctx.conn, words[i + 1].lower())
        for k in (2, 1):                       # a simple tense: pronouns, word
            if aux or i < k or not all(c in _CLITIC_WORDS for c in low[i - k:i]):
                continue
            said = " ".join(low[i - k:i + 1])
            for tail in _tails(low[i - k:i]):
                tw = _sub(ctx, twins[tail][0]) if tail in twins else None
                if tw is not None and said in {_fold(f.form).lower()
                                               for f in tw.picks(own=True) if f.note}:
                    return tw, _doubt(low[i - k:i], head, twins[tail][1])
        # a compound past: pronoun, a form of essere, this participle
        if i >= 2 and "si" in twins and "participle" in note and "past" in note \
                and low[i - 2] in _PERSON \
                and _essere_agrees(ctx.conn, words[i - 1].lower(), low[i - 2]):
            tw = _sub(ctx, twins["si"][0])
            if tw is not None:
                return tw, _doubt(low[i - 2:i - 1], head, twins["si"][1])
    return None


def _participle(conn, word):
    """Is `word` a past participle, as the dictionary lists it -- itself
    (alzato, `participle, past`) or as the plural or feminine of one (alzati
    is only `masculine, plural` of alzato)?"""
    pp = "note LIKE '%participle%' AND note LIKE '%past%'"
    if conn.execute("SELECT 1 FROM form WHERE form = ? AND %s LIMIT 1" % pp,
                    (word,)).fetchone():
        return True
    return conn.execute(
        "SELECT 1 FROM form f JOIN entry e ON e.id = f.entry_id WHERE f.form = ? "
        "AND e.headword IN (SELECT form FROM form WHERE form = e.headword AND %s) "
        "LIMIT 1" % pp, (word,)).fetchone() is not None


def _essere_agrees(conn, word, clitic):
    """Is `word` a form of essere in this pronoun's person (and number)?"""
    eid = _verb_entry(conn, "essere")
    if eid is None:
        return False
    person, number = _PERSON[clitic]
    for (note,) in conn.execute("SELECT note FROM form WHERE form = ? AND entry_id = ?",
                                (word, eid)):
        tags = verbs.split_tags(note)
        if person in tags and (not number or number in tags):
            return True
    return False


def _doubt(cluster, plain, pronominal):
    """What is not settled by taking the pronominal verb: nothing for mi,
    ti, ci and vi; for si, whether it is reflexive or impersonal."""
    if cluster and cluster[0] in ("si", "se"):
        return ["whether %s here makes it %s or is impersonal (%s)"
                % (" ".join(cluster), pronominal, plain)]
    return []


# ----------------------------------------------------------- the meaning
_JUNK = re.compile(r"(?i)^(?:used\b|synonym of\b|compound of\b|denotes\b|"
                   r"reflexive of\b|alternative (?:form|spelling) of\b)")


def _ranked(t):
    return lookup.rank_senses([s for s in t.senses if s.strip()],
                              (t.entry["sense_tags"] or "").split("\n"))


def _meaning(ctx, t):
    """The meaning slot, or None for the core's own.

    The core's -- the hit's first ranked sense, trimmed -- where the verb IS
    the hit and that sense is a meaning.  Where it is not one -- essere's
    first sense is "Used as a copula. to be", 57 verbs' is "Used other than
    figuratively or idiomatically: compound of ...", 232 are "synonym of X"
    -- the equivalent after the usage note ("to be"), else the next ranked
    sense that is a meaning (dirsi's first is "reflexive of dire", its
    second "to say to oneself"), else X's.  A compound's or a form page's own
    sense ("compound of alzando, the gerund of alzare, with si") is never a
    meaning: the verb's senses are read instead.
    """
    if not verbs.gloss_is_en(ctx.gloss):
        return ""
    if t is ctx and ctx.meaning and not _JUNK.match(ctx.meaning):
        return None
    ranked = _ranked(t)
    for sense, _tags, _tier in ranked:
        m = verbs.trim_meaning(sense)
        if m and not _JUNK.match(m):
            return m
        k = m.find(". ")
        if m.lower().startswith("used") and k > 0 and m[k + 2:].startswith("to "):
            return m[k + 2:]
    for sense, _tags, _tier in ranked:
        s = re.match(r"(?i)synonym of (\S+?)[,;:.]?(?:\s|$)", verbs.trim_meaning(sense))
        eid = _verb_entry(t.conn, s.group(1)) if s else None
        if eid:
            for x, _a, _b in _ranked(_sub(ctx, eid)):
                m = verbs.trim_meaning(x)
                if m and not _JUNK.match(m):
                    return m
    return verbs.trim_meaning(ranked[0][0]) if ranked else ""


# ------------------------------------------------------------ the recipe
def recipe(ctx):
    """The Parts of an Italian verb hit, or None (see the module docstring)."""
    if (ctx.entry["pos"] or "") != "verb":
        return None
    t = _target(ctx)
    if t is None:
        return None
    doubt = []
    pro = _pronominal(ctx, t)
    if pro is not None:
        t, doubt = pro
    return _describe(ctx, t, doubt)


def _forms(L):
    return list(getattr(L, "vb_forms", None)
                or ["infinitive", "1st sg. present", "past participle"])


def _one(ctx, m):
    """The meaning as the slot prints it.

    ONE EQUIVALENT, as docs/lang/it.md asks ("one equivalent in the gloss
    language rather than a string of synonyms"): prendere's first sense is
    "to take, hold, pick up, get", cominciare's "to begin, to start, to
    commence, to set about".  And without the square brackets Italian senses
    keep the page's grammar in -- eccellere is "to excel [auxiliary essere
    or avere]", godere "to enjoy [with di ‘something’" (cut short by the
    core, which caps a sense), antivenire "to precede [with a]": the
    auxiliary has its own place in the line, and a construction is the
    chunk's meaning's business.
    """
    m = ctx.meaning if m is None else m
    m = re.sub(r"\s*\[[^\[\]]*\]", "", m or "")
    m = re.sub(r"\s*\[.*$", "", m).strip(" ,;:")
    return verbs.one_equivalent(m)


def _describe(ctx, t, doubt):
    forms = _forms(ctx.L)
    head = t.entry["headword"] or ""
    missing = list(doubt)

    # slot 1: the infinitive as written, and its sound from the marked row --
    # cut at a bracket, which some pages fill with junk ("rimanére
    # [auxiliary essere]", "disimparàre [transitive ‘something’"), and only
    # where that row IS this headword: an idiom's may be another (`metter
    # acqua nel vino` for mettere acqua nel vino)
    canon = t.pick(exact={"canonical"}, own=True)
    marked = re.split(r"\s*\[", canon.form)[0].strip() if canon else ""
    s1 = _sound(marked) if marked and _fold(marked) == _fold(head) else ""

    # slot 2: the first person present, its pronouns and all (mi alzo, me ne
    # vado, ce la faccio)
    third = False
    p2 = _slot(t, _FIRST_PRES)
    if p2 is None:
        # A VERB OF THE THIRD PERSON ONLY -- accadere, nevicare -- has no
        # first person to give, and its head line gives the third instead
        # (`accàde` present singular third-person), which is how the
        # dictionary says it is learnt: docs/lang/it.md takes it as the form
        p2 = t.pick(exact=_THIRD_PRES, own=True)
        third = p2 is not None
    f2 = _written(p2.form, head) if p2 else ""
    s2 = _sound(p2.form) if p2 else ""
    if p2 is None:
        missing.append(forms[1])

    # slot 3: the participle, bare.  A pronominal verb's is written with its
    # pronoun fused on (alzàtosi, andàtosene, fàttocela, stàtoci), which
    # never goes in the slot: the headword's own tail comes off.
    _stem, tail = _split_tail(head)
    no_pp = any("no-past-participle" in tags for tags in t.sense_tags)
    p3 = _slot(t, _PART_PAST)
    f3 = s3 = ""
    if p3 is not None:
        acc = _untailed(p3.form, tail)
        f3, s3 = _written(acc, head), _sound(acc)
    elif not no_pp:
        missing.append(forms[2])

    extras = []
    aux = _auxiliaries(t)
    if not aux and tail[:1] == "s":
        # every pronominal verb makes its perfect with essere -- alzarsi,
        # andarsene, cavarsela; the 13 of 2410 with a table whose page does
        # not say so (puntellarsi, strapazzarsi) are not exceptions, only
        # pages written short
        aux = ["essere"]
    if aux == ["essere"]:
        extras.append("aux. " + verbs.tl("essere"))
    elif aux == ["avere", "essere"]:
        extras.append("aux. " + verbs.tl("avere") + "/" + verbs.tl("essere"))
    elif not aux and not no_pp:
        missing.append("auxiliary (avere or essere)")

    pr = _slot(t, _THIRD_PR if third else _FIRST_PR)
    if pr is not None and not _regular_pr(head, _written(_verb_word(pr.form)), third):
        # written with the pronouns the present has (p.r. mi accorsi), and
        # judged on the verb alone
        extras.append("p.r. " + verbs.tl(_written(pr.form, head)))

    return verbs.Parts(parts=[(head, s1), (f2, s2), (f3, s3)],
                       meaning=_one(ctx, _meaning(ctx, t)), extras=extras,
                       missing=missing)
