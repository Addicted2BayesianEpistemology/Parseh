"""French: the \\vb a verb hit offers, read off the rows Wiktionary wrote.

    \\vb{aller}{alé}{vais}{vè}{allé}{alé}{to go (aux. être; fut. \\pw{irai} \\textit{iré})}
    \\vb{prendre}{prãdr}{prends}{prã}{pris}{pri}{to take (nous \\pw{prenons} \\textit{prenõ})}
    \\vb{se lever}{se levé}{me lève}{me lèv}{levé}{levé}{to rise (aux. être)}
    \\vb{falloir}{falwar}{il faut}{il fo}{fallu}{falü}{to need (fut. \\pw{il faudra} \\textit{il fodra})}
    \\vb{regarder}{regardé}{regarde}{regard}{regardé}{regardé}{to look at}

    python3 lib/verbs/__init__.py fr "il se lève et regarde l'arbre"

WHAT docs/lang/fr.md ASKS FOR, and all this file makes: the infinitive, the
first person present and the past participle, each with its sound; the
meaning; then, in one parenthesis and each only where it is not the ordinary
case, `aux. être` (or `aux. être/avoir`), the nous form where the plural is
not built on the infinitive, and the first person future where that is not
built on it either.  Nothing else: no -er/-ir/-re class, which the infinitive
prints by itself and which was wrong for aller anyway.

WHERE EACH FORM COMES FROM.  A French verb page carries a generated
conjugation table, and lib/getdict.py keeps it cell by cell, each cell a form
row whose note is its tags joined with spaces -- `vais` is `first-person
indicative present singular` -- and whose `ipa` is the cell's own
pronunciation (/vɛ/), which is the only record there is of how `prends` or
`aimons` is said.  Every slot is a cell asked for by its EXACT tag set: a
dialect row carries one tag more (aller's pointer `vas`, `North-America,
first-person, ...`) and a subset test would take it.  Only the entry's own
rows are read -- the block getdict wrote with the entry; the pointer pages
come later and are other pages' say -- and within them, first by rowid, which
is the source's order.

ONE PAGE, SEVERAL TABLES.  Over the 7 221 verb entries that have one, 7 072
have a single table, 137 two and 10 three: the plain verb's, then, where
Wiktionary gives it, the pronominal one (laver's `se laver`, asseoir's
`s'asseoir`) and an `s'en` one (servir's `s'en servir`).  They share their
tags -- être's second table has `me suis` exactly where the first has `suis`
-- so the rows are cut into tables at each `infinitive` row, and a slot is
read from the table the reading wants.  getdict folds a row identical to one
already written, which takes a second table's infinitive with it when it is
the first one's (demeurer: one table with avoir, one with être); such a table
starts at its auxiliary row instead.  78 verbs have only a pronominal table
(souvenir is `se souvenir`, `me souviens`), and are always given as that.

THE SOUNDS ARE THE SOURCE'S PRONUNCIATION, WRITTEN IN THE BOOK'S SCHEME.  The
scheme (docs/lang/fr.md, "Transliteration") is a respelling -- `ã` for /ɑ̃/,
`è` for /ɛ/, `ou` for /u/, a liaison carried on a hyphen, no letter doubled
-- and IPA goes into it by a table and four rules, the one mechanical walk
there is: `respell`, which is lib/translit.py respell_fr, since the reading
panel's French sounds are the same walk.  Checked against every sound the
fixture book writes by hand for a verb (tests/fixtures/books/french/
mini-fr/ch1.tex): 26 of 27 identical, and the 27th is Wiktionary giving
aurai /ɔ.ʁe/ where the book says oré.  A pronunciation holding a sound the
scheme has no letter for (/x/ in khalass, /ŋ/) is not forced into one: that
sound is left empty and named in `missing`.

THE PRONOMINAL VERB is read off the chunk, which is the only place it is
said: Wiktionary files se lever under lever and s'approcher under approcher,
usually with no table of its own (641 verbs with a sense tagged reflexive or
pronominal have none), and it is the chunk that says `il se lève`.  So a
verb is pronominal here when a reflexive pronoun is written onto it or
stands before it -- `se`, `s'`, or `me`/`te`/`nous`/`vous` agreeing with the
subject (`je me lève`, never `il me regarde`; `je vais me lever`, never `il
veut me voir`) -- or before the être it is the participle of (`il s'est
levé`).  Then it is given as the pronominal verb: from its own table where
the page has one, and otherwise with `se `/`s'` and `me `/`m'` written on,
their sounds with them; with aux. être, which every pronominal verb takes;
and with the first sense the source tags reflexive or pronominal.  `s'en va`
reaches the dictionary's own s'en aller where it has one.

NOTHING IS GUESSED.  What the rows do not say is named in `missing`: of the
516 single-word verb entries with no table, 38 are read from the page that
conjugates them (a homograph's: causer, poster, bosser; agir's for s'agir),
and 86 real verbs get their infinitive and nothing they would have to
invent.  An entry that is only an inflected page Wiktionary failed to parse
as one ("third-person plural present of constituer"), or an English word
filed as French, is not a verb this can describe, and is left to be the \\dw
it always was.  The one decision taken by hand is in lib/lang/fr.verbs.json:
five verbs whose second auxiliary is an obsolete or familiar sense (partir,
tomber) are given aux. être, and the file says why.
"""
import collections
import re

import lookup
import verbs
from translit import respell_fr as respell
from verbs import Parts, tl

# ------------------------------------------------------------- the cells
# Every slot by its exact tag set, `reflexive` aside: souvenir's only table
# tags its cells `reflexive` and être's second table, the same cells, does
# not.
INF = frozenset(("infinitive",))
AUX = frozenset(("infinitive", "multiword-construction"))
SG1 = frozenset(("first-person", "indicative", "present", "singular"))
SG3 = frozenset(("indicative", "present", "singular", "third-person"))
PL1 = frozenset(("first-person", "indicative", "plural", "present"))
PP = frozenset(("participle", "past"))
FUT1 = frozenset(("first-person", "future", "indicative", "singular"))
FUT3 = frozenset(("future", "indicative", "singular", "third-person"))

# A PRONUNCIATION FILED AS A FORM.  The source's table has, beside a cell,
# the same cell's IPA as a second "form": aimer `ɛm` next to `aime`, pouvoir
# `pø` next to `peux`, manger `mɑ̃ʒ`, choir `/ʃwa.ʁe/` -- 1 550 of them in
# the conjugated verbs' own rows.  These letters are IPA and never French
# spelling; `œ` and `æ` are not among them, because manœuvrer and œuvrer are
# spelt with them.
_IPA_ONLY = re.compile("[ɛɑɔʁʃʒøəɥɲŋˈ/‿ː]")

# The reflexive pronoun written onto a form of a pronominal table, with the
# en or y a pronominal table can carry after it: `se souvenir`, `s'asseoir`,
# `me souviens`, `m'en vais`, `nous en allons`.
_CLITIC = re.compile(r"^(?:(?:me|te|se|nous|vous) |[mts]['’])(?:(?:en|y) )?")
# ...and on a headword, where `y avoir` has only the y
_HEAD_CLITIC = re.compile(r"^(?:(?:se |s['’])(?:(?:en|y) )?|y )")
_REFLEXIVE = frozenset(("reflexive", "pronominal"))

# THE LETTERS BEFORE WHICH se IS s'.  An h is not among them, because it
# goes both ways (s'habiller, se hâter) and Wiktionary's pronunciation does
# not say which: /a.bi.je/ and /a.te/ both begin with the vowel.  Where the
# chunk writes the pronoun onto the verb it has answered; where it does not,
# the h is named in `missing`.
_VOWELS = frozenset("aàâäeéèêëiîïoôöuùûüœæ")

# The forms of être, the auxiliary a pronominal verb's participle follows:
# in `il s'est levé` the pronoun is before `est` and belongs to `levé`.
_ETRE = frozenset("""suis es est sommes êtes sont étais était étions étiez
    étaient fus fut fûmes fûtes furent serai seras sera serons serez seront
    serais serait serions seriez seraient sois soit soyons soyez soient
    fusse fusses fût fussions fussiez fussent""".split())
# ...and the words a negation puts between the two (il ne s'est pas levé).
_NEG = frozenset(("pas", "plus", "jamais", "point", "guère", "rien"))
# Who each non-third-person pronoun is reflexive for.  `il me regarde` is an
# object; `je me lève` is the verb's own.
_SUBJECT = {"me": ("je",), "te": ("tu",), "nous": ("nous",), "vous": ("vous",)}

# THE TWO AUXILIARIES ARE NEVER PRONOMINAL THEMSELVES.  A pronoun before
# `sont` in `ils se sont assis` is assis's, and être's own pronominal table
# (`me suis`) is Wiktionary's, not the language's.
_AUXILIARIES = frozenset(("être", "avoir"))

# A TABLELESS ENTRY IS A VERB ONLY IF ITS HEADWORD IS AN INFINITIVE, and
# not if its gloss says what it is an inflection of.  Of the 516 single-word
# verb entries with no table, 392 are not infinitives -- English words filed
# as French (back, follow) and pages Wiktionary failed to parse as the forms
# they are (constituent, "third-person plural present of constituer") -- and
# an inflection can end like one (vire is virer's).  A spelling pointer is an
# infinitive and a verb (assoir, the 1990 spelling of asseoir): its meaning
# is read where it points (_meaning).
_FORM_OF = re.compile(r"(?i)\b(?:form|participle|tense|person|plural|"
                      r"singular|subjunctive|indicative|imperative)"
                      r"\b[^.;]*\bof\s+\S+\s*\.?$")
_INFINITIVE = re.compile(r"(?:er|ir|ïr|re|oir)$")

_APOS = str.maketrans({"’": "'", "ʼ": "'"})

M_INF_SOUND = "sound of the infinitive"
M_SG1 = "first person present"
M_SG1_SOUND = "sound of the first person present"
M_PP = "past participle"
M_PP_SOUND = "sound of the past participle"
M_AUX = "auxiliary"
M_NOUS_SOUND = "sound of the nous form"
M_FUT_SOUND = "sound of the future"
M_ELIDE = "se or s' before the h"
M_MEANING = "meaning"
# the order the editor's button names them in: the slots' own
_ORDER = (M_INF_SOUND, M_ELIDE, M_SG1, M_SG1_SOUND, M_PP, M_PP_SOUND, M_AUX,
          M_NOUS_SOUND, M_FUT_SOUND, M_MEANING)


def _named(missing):
    return sorted(set(missing), key=_ORDER.index)


# ------------------------------------------------------------- the sounds
# IPA to the respelling of docs/lang/fr.md is lib/translit.py respell_fr,
# imported above as `respell`: it was written here and moved there, unchanged,
# when the reading panel wanted the same sounds for every French hit (a
# French hit had none: no character table can write French).


# -------------------------------------------------------------- the rows
Row = collections.namedtuple("Row", "form tags ipa rowid")


def _own_rows(conn, eid):
    """The rows getdict wrote WITH this entry, in its order, with their
    pronunciation.

    The entry's own rows are one run of rowids, starting at the headword
    (getdict inserts them together); the pointer pages were linked after
    every entry was in, so they start after a gap -- and a pointer whose note
    has one tag has no comma to give it away (`allez`, `a form of`).  Read
    here and not from ctx.rows because the recipe needs each row's `ipa`,
    which Form does not carry.
    """
    ipa = "ipa" if lookup._has_col(conn, "ipa", "form") else "''"
    out, last = [], None
    for r in conn.execute("SELECT rowid, form, note, %s AS ipa FROM form "
                          "WHERE entry_id = ? ORDER BY rowid" % ipa, (eid,)):
        if last is not None and r["rowid"] != last + 1:
            break
        last = r["rowid"]
        if "," in (r["note"] or ""):
            continue
        out.append(Row(r["form"] or "", verbs.split_tags(r["note"]),
                       r["ipa"] or "", r["rowid"]))
    return out


def _cell(row):
    return row.tags - {"reflexive"}


def _tables(rows, headword):
    """[(infinitive, rows)] -- the entry's tables, in the source's order.

    A table opens with its infinitive row.  Where getdict left that row out
    -- identical to the first table's (demeurer's second table, the one with
    être), or spelt already by the head line (récrier's head line gives `se
    récrier` as the canonical form, and its only table is that one's) -- the
    table opens with its auxiliary row instead, under the name the page gave.
    """
    out, opened, name = [], False, headword
    for r in rows:
        c = _cell(r)
        if not out and r.tags == {"canonical"}:
            name = r.form               # the head line spelt the infinitive
        if c == INF:
            out.append((r.form, [r]))
            opened = True
        elif c == AUX:
            if not opened:
                out.append((out[0][0] if out else name, []))
            out[-1][1].append(r)
            opened = True
        else:
            opened = False
            if out:
                out[-1][1].append(r)
    return out


def _head_rows(rows):
    """The head line's rows, between the headword's and the first table's.
    Three verbs have their participle only there -- getdict leaves out a
    table cell the head line already spelt, and choir's head line spells
    `chu` -- and a few say the verb is pronominal by nature: récrier's head
    line gives `se récrier` as the canonical form."""
    out = []
    for r in rows[1:]:
        if _cell(r) in (INF, AUX):
            break
        out.append(r)
    return out


def _junk(form):
    return not form or form == "-" or bool(_IPA_ONLY.search(form))


def _pick(rows, cell):
    """The first row of this exact cell whose form is a spelling."""
    for r in rows:
        if _cell(r) == cell and not _junk(r.form):
            return r
    return None


def _heard(row, rows):
    """A row's pronunciation, or that of another row with the same spelling
    (getdict lends them within a page, and a page's other table may have
    what this one lacks)."""
    if row.ipa:
        return row.ipa
    for r in rows:
        if r.form == row.form and r.ipa:
            return r.ipa
    return ""


def _is_refl(inf, headword):
    return inf in ("se " + headword, "s'" + headword, "s’" + headword)


def _bare_hw(hw):
    """A headword without the pronoun it is entered with: se casser ->
    casser, s'en aller -> aller, y avoir -> avoir."""
    return _HEAD_CLITIC.sub("", hw, count=1)


def _unclitic(form, ipa=""):
    """A pronominal table's form without its pronoun, and its sound without
    the pronoun's: `nous souvenons` /nu suv.nɔ̃/ -> souvenons /suv.nɔ̃/;
    `nous évanouissons` /nu.z‿e.va.nwi.sɔ̃/ -> évanouissons, whose liaison z
    was the pronoun's; `m'en vais` /mɑ̃ vɛ/ -> vais /vɛ/; `m'évanouis`
    /me.va.nwi/ -> évanouis /e.va.nwi/.

    The pronoun's words are counted off the sound's words, which a space or
    a liaison's ‿ part; an elided pronoun that stands alone before its ‿ (the
    s of /s‿ɑ̃/) is one word with what follows."""
    m = _CLITIC.match(form)
    if not m:
        return form, ipa
    bare = form[m.end():]
    s = (ipa or "").strip().strip("/[]")
    if not s:
        return bare, ""
    n = len(m.group().split())
    if m.group()[-1:] in "'’":
        return bare, s[1:] if s[:1] == form[:1] else ""
    segs = []
    for w in re.split(r"[ ‿]", s):
        if segs and re.fullmatch(r"[^aeiouyɑɛəɔøœ̃.]", segs[-1]):
            segs[-1] += w                   # s‿ɑ̃: the elided pronoun and its word
        else:
            segs.append(w)
    return bare, (" ".join(segs[n:]) if len(segs) > n else "")


# ------------------------------------------------------------ regularity
def _stem(inf):
    """(the infinitive's stem, its ending): prend + re, pouv + oir."""
    for end in ("oir", "er", "ir", "ïr", "re"):
        if inf.endswith(end) and len(inf) > len(end):
            return inf[:-len(end)], end
    return inf, ""


def _nous_regular(inf, pl1):
    """Is the nous form built on the infinitive?  prendre's prenons is not,
    nor boire's buvons, nor faire's faisons, nor être's sommes; parlons,
    finissons, venons, devons and avons are, and so is every -er verb's
    (commençons and mangeons with their spelling).  docs/lang/fr.md prints
    the form only where it is not, which is the one rule a reader can use:
    with no nous form printed, the plural is the infinitive's stem + -ons."""
    st, end = _stem(inf)
    ok = {st + "ons"}
    if end == "er":
        if st.endswith("c"):
            ok.add(st[:-1] + "çons")
        if st.endswith("g"):
            ok.add(st + "eons")
    if end == "ir":
        ok.add(st + "issons")           # the finir kind, which fr.md calls regular
    return pl1 in ok


def _future_regular(inf, presents, fut, suffix):
    """Is the future built on the infinitive?  The infinitive + -ai (finirai,
    and prendrai for a -re verb), or, for an -er verb, one of its own
    presents + -rai: lèverai, jetterai, appellerai follow the present the
    second slot already prints, and payer's paierai follows paie as payerai
    follows paye.  irai, serai, aurai, ferai, viendrai, pourrai, verrai,
    enverrai, cueillerai do not.  `suffix` is -ai, or -a for an impersonal
    verb's third person (il pleuvra; il neigera is regular)."""
    _st, end = _stem(inf)
    ok = {inf + suffix}
    if end == "re":
        ok.add(inf[:-1] + suffix)
    if end == "er":
        ok.update(p + "r" + suffix for p in presents if p)
    return fut in ok


# ---------------------------------------------------------- the pronoun
def _word(s, L):
    return lookup._bare(s or "", L).lower().translate(_APOS)


def _signal(words, i, infinitive=False):
    """How the chunk makes words[i] pronominal, or None.

    (pronoun, how it is written before this verb, en or y): the pronoun is
    se/me/te/nous/vous, and `written` is "'" where it is elided onto the
    verb itself (s'approcha), " " where it stands before it unelided (se
    lève), and "" where the chunk says nothing about the verb's first sound
    (it is on the auxiliary: s'est levé).
    """
    w = words[i]
    k = i - 1                           # where the subject is looked for
    written = ""
    en = ""
    m = re.match(r"^([mts])'(?=\w)", w)
    if m:
        pron, written = m.group(1) + "e", "'"
    else:
        p = words[i - 1] if i >= 1 else ""
        if p in ("se", "me", "te", "nous", "vous"):
            # an unelided se/me/te says the verb does not begin with a
            # vowel sound; nous and vous are never elided and say nothing
            pron, k = p, i - 2
            written = " " if p in ("se", "me", "te") else ""
        else:
            m = re.match(r"^([mts])'(en|y)$", p)
            if m:
                pron, en, k = m.group(1) + "e", m.group(2), i - 2
            elif p in ("en", "y") and i >= 2 and words[i - 2] in ("nous", "vous"):
                pron, en, k = words[i - 2], p, i - 3
            else:
                # the participle after its être: s'est levé, se sont assis,
                # ne s'est pas levé
                j = i - 1
                if j >= 0 and words[j] in _NEG:
                    j -= 1
                a = words[j] if j >= 0 else ""
                m = re.match(r"^([mts])'(\w+)$", a)
                if m and m.group(2) in _ETRE:
                    pron, k = m.group(1) + "e", j - 1
                elif a in _ETRE and j >= 1 and words[j - 1] in _SUBJECT.keys() | {"se"}:
                    pron, k = words[j - 1], j - 2
                else:
                    return None
    if pron != "se":
        while k >= 0 and words[k] in ("ne", "n"):
            k -= 1
        if k < 0 or words[k] not in _SUBJECT[pron]:
            # an infinitive after the verb that governs it: `je vais me
            # lever`, `nous allons nous coucher` -- the subject is one word
            # further back, and must still agree (`il veut me voir` is not)
            if not infinitive or k < 1 or words[k - 1] not in _SUBJECT[pron]:
                return None
    return pron, written, en


def _pronominal(ctx):
    """The chunk's say on this verb: None, or _signal's answer for the first
    place it is pronominal."""
    words = [_word(w, ctx.L) for w in (ctx.text or "").split()]
    me = _word(ctx.word, ctx.L)
    # A FORM OF ÊTRE IS THE AUXILIARY, whatever else it spells: in `je me
    # suis trompé` the me is trompé's, and `suis` reaching suivre is no
    # `se suivre`.
    if me in _ETRE:
        return None
    inf = me == (ctx.entry["headword"] or "").lower()
    for i, w in enumerate(words):
        if w and w == me:
            got = _signal(words, i, inf)
            if got:
                return got
    return None


def _elides(word, written):
    """True, False, or None where nothing says (an h the chunk did not write
    the pronoun onto)."""
    c = (word or "")[:1].lower()
    if c in _VOWELS:
        return True
    if c == "h":
        return {"'": True, " ": False}.get(written)
    return False


# ------------------------------------------------------------ the meaning
# A SENSE THAT IS ONLY A POINTER.  Over the 7 221 verbs with a table, the
# first ranked sense of 72 is "post-1990 spelling of dîner" or "Pre-1990
# spelling of asséner", and of 22 "synonym of démarrer": printed, the \vb
# for diner said its meaning was a spelling.  The source names the verb
# whose meaning it is, and the meaning is read from there -- one step, and
# nothing if that verb is not in the dictionary.
_POINTER = re.compile(
    r"(?i)^(?:[\w-]+\s+)?(spelling|synonym)\s+of\s+([^\s,;/.()]+)")
_USAGE = re.compile(r"(?i)^used\b")


def _ranked(entry):
    senses = (entry["sense"] or "").split("\n")
    tags = (entry["sense_tags"] or "").split("\n")
    keep = [(s, tags[i] if i < len(tags) else "") for i, s in enumerate(senses)
            if s.strip()]
    return lookup.rank_senses([s for s, _t in keep], [t for _s, t in keep])


def _pointer(conn, entry):
    """(kind, the verb entry it points at) when the first ranked sense is a
    pointer -- `spelling` or `synonym` -- else None."""
    ranked = _ranked(entry)
    m = _POINTER.match(ranked[0][0]) if ranked else None
    if not m:
        return None
    return m.group(1).lower(), _entry(conn, "headword = ? AND pos = 'verb' "
                                            "ORDER BY id", (m.group(2),))


def _meaning(conn, entry, gloss, reflexive, follow=True):
    """The first ranked sense the reading wants: tagged reflexive or
    pronominal for a pronominal verb (lever's is "to rise, stand up", its
    first plain one "to raise, lift"), untagged for the plain verb; the
    first ranked sense where there is none of that kind.  One equivalent, as
    docs/lang/fr.md asks: attendre's "to wait for, to await" is the fixture
    book's "to wait for".  None for "the core's", "" for a meaning that
    could not be read (a pointer at a verb the dictionary does not have)."""
    if (gloss or "").strip().lower() != "en":
        return None
    ranked = _ranked(entry)
    if not ranked:
        return None
    if follow:
        p = _pointer(conn, entry)
        if p:
            return _meaning(conn, p[1], gloss, reflexive, False) if p[1] else ""
    want = [r for r in ranked if reflexive is None or
            bool(_REFLEXIVE & set(t.strip() for t in r[1].split(","))) == reflexive]
    # A USAGE NOTE IS NOT A MEANING: s'en être's only sense is "Used only in
    # the simple past tense for s'en aller".  The next sense if there is one.
    for r in want + [r for r in ranked if r not in want]:
        best = r[0].strip()
        if _USAGE.match(best):
            continue
        # the source's quotation marks around a whole gloss ("to renounce
        # (property)", 24 verbs) are its typography, not the meaning
        if len(best) > 1 and best[0] in "\"“" and best[-1] in "\"”":
            best = best[1:-1].strip()
        # and a sense that is only its qualifier -- intriquer's first is
        # "(rare, sciences or literary)" -- trims to nothing: the next one
        got = verbs.one_equivalent(verbs.trim_meaning(best))
        if got:
            return got
    return ""


# --------------------------------------------------------------- the entry
# ------------------------------------------------------------ locutions
# A VERBAL LOCUTION IS A VERB WELDED TO A BARE NOUN -- avoir peur, faire
# attention, prendre garde, rendre visite -- and docs/lang/fr.md glosses it
# the way Persian and Turkish gloss a compound verb: a \vb for the verb with
# an EMPTY seventh argument, then a \bw for the noun, "which carries the
# meaning of the whole.  The verb is not given a meaning of its own: it has
# none there."  A \vb cannot hold a \bw, so the \vb is built as the doc
# writes it and the \bw is named in `missing`, its meaning read off the
# locution's own entry -- and handed over whole (Parts.compound) for the
# button that puts the pair in as the one entry it is.
#
# The lookup reads a chunk one word at a time, so `j'ai peur` arrives as ai
# (avoir) and peur (a noun), never as the locution.  It is found from the
# chunk: the word after the verb, and the two after it, joined to the verb's
# infinitive and looked for as a verb headword -- the Turkish scan
# (lib/verbs/tr.py) with the noun on the other side, French putting it after
# the verb.  Reading the chunk makes the answer depend on it (Ctx.text), so
# it is read only for a verb that begins some locution at all.
_STARTS = {}

# WHAT MAY STAND BETWEEN THE VERB AND ITS NOUN: the second half of a
# negation, which always sits there -- `je n'ai pas peur`, `il ne fait plus
# attention`.  Nothing else is skipped: an adverb between them would as
# easily be a chunk where the noun is an object of its own.
_BETWEEN = frozenset(("pas", "plus", "jamais", "point", "guere", "guère"))


def _starts_a_locution(ctx, headword):
    """Does some locution begin with this verb?  One scan of the verb
    entries per dictionary file, kept until the file changes -- keyed on the
    file and not the connection, which is one per thread (lib/verbs/tr.py's
    _ends_a_compound, the same scan read the other way round)."""
    p = lookup.path_for(ctx.code)
    key = (p, lookup._stamp(p))
    got = _STARTS.get(key)
    if got is None:
        got = frozenset(r[0].split()[0] for r in ctx.conn.execute(
            "SELECT headword FROM entry WHERE pos = 'verb' AND headword LIKE '% %'"))
        _STARTS.clear()
        _STARTS[key] = got
    return headword in got


def _locution_in_text(ctx, headword):
    """The locution entry the chunk makes of this verb and the word(s) after
    it, or None.  Longest first: `avoir besoin de` before `avoir besoin`."""
    if " " in headword or not _starts_a_locution(ctx, headword):
        return None
    words = [_word(w, ctx.L) for w in (ctx.text or "").split()]
    me = _word(ctx.word, ctx.L)
    for i, w in enumerate(words):
        if w != me:
            continue
        j = i + 1
        while j < len(words) and words[j] in _BETWEEN:
            j += 1
        for n in (2, 1):
            if j + n > len(words):
                continue
            noun = " ".join(words[j:j + n])
            row = _entry(ctx.conn, "headword = ? AND pos = 'verb' ORDER BY id",
                         ("%s %s" % (headword, noun),))
            if row is not None:
                return row
    return None


def _locution_parts(ctx, row, said, verb_sound):
    """The locution as the entry it is, for the button that puts it in whole:
    avoir peur avwar peur, the noun the verb carries, and what the pair means.

    THE NOUN'S SOUND IS THE NOUN'S OWN, respelt as every other sound in a
    French \vb is (lib/translit.py respell_fr), and the whole one is the two
    said in a row -- the verb's, which the \vb itself prints, and the
    noun's.  Where either is missing nothing is made up: the slot stays
    empty and the entry goes in without it."""
    noun = row["headword"].split(" ", 1)[1]
    got = _entry(ctx.conn, "headword = ? AND pos = 'noun' ORDER BY id", (noun,))
    sound = respell(got["ipa"] or "") if got is not None else ""
    return {"name": "verbal locution", "whole": row["headword"],
            "whole_sound": ("%s %s" % (verb_sound, sound)) if verb_sound and sound else "",
            "mean": said, "word": noun, "word_sound": sound}


def _bw_note(noun, said):
    """The \bw the locution needs after the verb's \vb, as one item of
    `missing`: the noun, and the locution's meaning where the gloss gave one.
    No backslash -- the core takes every one out of `missing` -- and no
    comma, which is what the editor joins the items with.  The words
    lib/verbs/fa.py and tr.py use, for the one thing all three do."""
    return ("bw for %s after it%s" % (noun, (": " + said) if said else "")
            ).replace(",", ";")


def _entry(conn, sql, args):
    cols = ("id, headword, ipa, sense, %s AS sense_tags"
            % ("sense_tags" if lookup._has_col(conn, "sense_tags") else "''"))
    return conn.execute("SELECT %s FROM entry WHERE %s" % (cols, sql), args).fetchone()


def _has_table(rows):
    return any(_cell(r) in (SG1, PP) for r in rows)


def _sibling(conn, entry):
    """The rows of the page that conjugates a tableless entry, or None.

    A HOMOGRAPH WITH A TABLE: causer (to chat) reads causer (to cause),
    which Wiktionary conjugated once for both -- 37 such entries.  An -er
    homograph is conjugated as its twin is; the pairs that are not (sortir,
    to go out, and the law's sortir, conjugated like finir) each have a
    table of their own and never come here.

    THE PLAIN VERB'S PAGE, for a pronominal verb entered on its own: s'agir
    has no table, and agir's page has one whose infinitive is `s'agir`.
    """
    hw = entry["headword"] or ""
    for r in conn.execute("SELECT id FROM entry WHERE headword = ? AND pos = 'verb' "
                          "AND id != ? ORDER BY id", (hw, entry["id"])):
        rows = _own_rows(conn, r["id"])
        if _has_table(rows):
            return rows
    bare = _bare_hw(hw)
    if bare != hw:
        for r in conn.execute("SELECT id FROM entry WHERE headword = ? AND "
                              "pos = 'verb' ORDER BY id", (bare,)):
            rows = _own_rows(conn, r["id"])
            if any(t[0] == hw for t in _tables(rows, bare)):
                return rows
    return None


def _canonical_refl(head, hw):
    """Does the head line give the pronominal verb as the canonical form?
    récrier's does (`se récrier`), and so do positionner's and intriquer's."""
    return any(r.tags == {"canonical"} and _is_refl(r.form, hw) for r in head)


def recipe(ctx):
    e = ctx.entry
    if (e["pos"] or "") != "verb":
        return None
    hw = e["headword"] or ""
    # the verb without the pronoun it is entered with: casser for se
    # casser, agir for s'agir -- hw itself for all but a few dozen
    bare = _bare_hw(hw)
    rows = _own_rows(ctx.conn, e["id"])
    # A WORD THAT IS ONLY THIS VERB'S AUXILIARY is not this verb.  The
    # table's `avoir` row (monter, passer: the bare avoir beside `être +
    # past participle`) and every `ayant` are form rows, so the word avoir
    # comes back with passer and partir among its hits: they are hits
    # lookup made, and no \vb of passer is what `avoir` means.
    w = (ctx.word or "").casefold()
    if w and w != hw.casefold():
        mine = [r for r in rows if r.form.casefold() == w]
        if mine and all("multiword-construction" in r.tags for r in mine):
            return None
    if not _has_table(rows):
        rows = _sibling(ctx.conn, e)
    if rows is None:
        return _bare_verb(ctx)
    tables = _tables(rows, hw)
    head = _head_rows(rows)
    plain = [t for t in tables if t[0] == hw]
    refl = [t for t in tables if _is_refl(t[0], hw)]
    missing = []
    extras = []

    # ---- which reading: the plain verb, or the pronominal one
    sig = None
    if bare != hw:
        pass                            # entered pronominal: its table is the verb
    elif (not plain and refl) or _canonical_refl(head, hw):
        sig = ("se", "", "")            # souvenir: a pronominal verb and nothing else
    elif hw not in _AUXILIARIES:
        sig = _pronominal(ctx)
    if sig and sig[2]:
        # s'en va is s'en aller where the dictionary has that as its own verb
        got = _entry(ctx.conn, "headword = ? AND pos = 'verb' ORDER BY id",
                     ("s'%s %s" % (sig[2], hw),))
        if got is not None:
            r2 = _own_rows(ctx.conn, got["id"])
            t2 = [t for t in _tables(r2, got["headword"]) if t[0] == got["headword"]]
            if t2 and _pick(t2[0][1], SG1):
                return _whole(ctx, got, t2[0][1], r2, plain, rows, hw)
    pron = bool(sig)
    base = (plain or refl or tables or [(hw, [])])[0][1]

    # ---- the rows each slot is read from
    use = refl[0][1] if (pron and refl) else base
    sg = _pick(use, SG1)
    # the participle from the table read, else any of the page's (s'agir's
    # table lost `agi` to agir's, identical), else the head line (choir)
    pp = (_pick(use, PP) or _pick(base, PP)
          or next((p for _i, t in tables for p in [_pick(t, PP)] if p), None)
          or _pick(head, PP))
    f3 = s3 = ""
    if pp is not None:
        f3, s3 = pp.form, respell(_heard(pp, rows))
        if not s3:
            missing.append(M_PP_SOUND)
    else:
        missing.append(M_PP)

    # ---- slot 1: the infinitive, with the lemma's own sound
    snd1 = _lemma_sound(ctx, e)
    # a pronunciation that begins with the pronoun is the pronominal verb's
    # (intriquer is entered with s'intriquer's, /s‿ɛ̃.tʁi.ke/)
    pre = bool(re.match(r"^[/\[]?s(?:‿|ə |\(ə\) )", e["ipa"] or ""))
    if not snd1:
        snd1 = _as_participle(bare, f3, s3)
        if snd1 and bare != hw:
            snd1 = _with_pronoun(hw, snd1)  # the participle is the bare verb's
    if not snd1:
        missing.append(M_INF_SOUND)
    written = sig[1] if sig else ""
    f1, s1 = hw, snd1
    if pron and refl:
        f1 = refl[0][0]
        s1 = _with_pronoun(f1, snd1, pre)

    # ---- slot 2: the first person present
    f2 = s2 = ""
    impersonal = None
    if sg is not None:
        f2, s2 = sg.form, respell(_heard(sg, rows))
    elif not _pick(use, PL1):
        # falloir, pleuvoir, neiger: no first person at all, and the third
        # is the present a learner meets -- `il faut`, `il s'agit`
        impersonal = _pick(use, SG3)
        if impersonal is not None:
            snd = respell(_heard(impersonal, rows))
            f2, s2 = "il " + impersonal.form, ("il " + snd) if snd else ""
    if pron and not refl:
        # written on by rule: se/s' before the infinitive, me/m' before the
        # first person, as the chunk writes the pronoun where it says
        f1, s1 = _pronounce(hw, snd1, _elides(hw, written), "se", missing, pre)
        if f2 and impersonal is None:
            f2, s2 = _pronounce(f2, s2, _elides(f2, written), "me", missing)
    if not f2:
        missing.append(M_SG1)
    elif not s2:
        missing.append(M_SG1_SOUND)

    # ---- the auxiliary
    if pron:
        extras.append("aux. être")
    else:
        aux = _aux(plain or tables[:1])
        over = (ctx.data().get("aux") or {}).get(hw)
        if over in ("être", "avoir", "être/avoir"):
            aux = set(over.split("/"))
        if not aux:
            missing.append(M_AUX)
        elif aux == {"être"}:
            extras.append("aux. être")
        elif aux == {"être", "avoir"}:
            extras.append("aux. être/avoir")

    # ---- the nous form and the future, where not built on the infinitive
    extras += _nous_fut(bare, base, rows, impersonal is not None, missing)
    # ---- a verbal locution the chunk makes of this verb: `j'ai peur`
    # THE MEANING IS LEFT EMPTY ON PURPOSE and so is never missing: it is the
    # \bw's, and docs/lang/fr.md says the verb "has none there".
    loc = None if pron else _locution_in_text(ctx, hw)
    if loc is not None:
        said = _meaning(ctx.conn, loc, ctx.gloss, None) or ""
        return Parts([(f1, s1), (f2, s2), (f3, s3)], meaning="", extras=extras,
                     missing=_named(missing) +
                             [_bw_note(loc["headword"].split(" ", 1)[1], said)],
                     compound=_locution_parts(ctx, loc, said, s1))

    meaning = _said(ctx, e, True if pron else (None if bare != hw else False),
                    missing)
    return Parts([(f1, s1), (f2, s2), (f3, s3)], meaning=meaning,
                 extras=extras, missing=_named(missing))


def _lemma_sound(ctx, e):
    """How the infinitive is said: the entry's pronunciation, respelt -- or,
    for an entry that is only another spelling of a verb (naitre, the 1990
    spelling of naître, has no IPA of its own), that verb's, since a spelling
    of a word is said as the word is.  ctx.head_sound last: it is lookup's
    own reading of the same IPA, which today has no French table and is
    empty."""
    snd = respell(e["ipa"] or "")
    if not snd:
        p = _pointer(ctx.conn, e)
        if p and p[0] == "spelling" and p[1] is not None:
            snd = respell(p[1]["ipa"] or "")
    return snd or ctx.head_sound


def _as_participle(hw, pp, pp_sound):
    """THE INFINITIVE SAID AS ITS PARTICIPLE, where the two are one sound.

    560 verbs with a table have no pronunciation of their own -- the table's
    infinitive cell never carries one -- and 523 of them are -er verbs whose
    participle is the same stem + é and does: sabrer is sabré's /sa.bʁe/.
    -er and -é are one sound, [e], in every -er verb there is; and an -ir
    infinitive is its -i participle and a sounded r (racornir, racorni).
    Nothing else is read this way: a -re verb's participle says nothing of
    its infinitive.
    """
    if not pp_sound:
        return ""
    stem, end = _stem(hw)
    if end == "er" and pp == stem + "é":
        return pp_sound
    if end == "ir" and pp == stem + "i":
        return pp_sound + "r"
    return ""


def _said(ctx, e, reflexive, missing):
    """_meaning, with a meaning that could not be read named in missing."""
    m = _meaning(ctx.conn, e, ctx.gloss, reflexive)
    if m == "":
        missing.append(M_MEANING)
    return m


def _with_pronoun(form, snd, pre=False):
    """The sound of a pronominal infinitive whose pronunciation the source
    gives only for the bare verb: `se souvenir` is `se ` + souvenir,
    `s'asseoir` is `s` + aswar, joined, since an elision makes one word.
    An `s'en` or an `s'y` is not written on: their sound is the entry's own
    (s'en aller /s‿ɑ̃.n‿a.le/) or nothing.  `pre`: the pronunciation is the
    pronominal verb's already."""
    m = _HEAD_CLITIC.match(form)
    if not snd or not m:
        return snd if not m else ""
    if pre:
        return snd                  # intriquer's is s'intriquer's: /s‿ɛ̃.tʁi.ke/
    if m.group() == "se ":
        return "se " + snd
    if m.group() in ("s'", "s’"):
        return "s" + snd
    return ""


def _pronounce(form, snd, elides, pron, missing, pre=False):
    """(form, sound) with the reflexive pronoun written on -- not onto a
    form that has one, and not into a sound that has it (`pre`)."""
    if _CLITIC.match(form):
        return form, snd
    if elides is None:
        if M_ELIDE not in missing:
            missing.append(M_ELIDE)
        return form, snd
    if elides:
        return pron[0] + "'" + form, (pron[0] + snd) if snd and not pre else snd
    return pron + " " + form, (pron + " " + snd) if snd and not pre else snd


def _aux(tables):
    """{'avoir'}, {'être'}, both, or set() -- from each table's auxiliary
    row.  avoir for 7 063 verbs; être for 55 like aller and naître (and the
    78 that are only pronominal, `s'être + past participle`); both for 23:
    monter's table writes a bare `avoir` row beside the être one, and
    demeurer and paralyser have a second table, with être."""
    got = set()
    for _inf, rows in tables:
        for r in rows:
            if _cell(r) != AUX:
                continue
            w = r.form.replace("’", "'")
            w = re.sub(r"^(?:s'en |s'y |se l'|s'|y )", "", w)
            if w.startswith("avoir") or w.startswith("ayant"):
                got.add("avoir")
            elif w.startswith("être") or w.startswith("étant"):
                got.add("être")
    return got


def _variants(rows, cell):
    return [r for r in rows if _cell(r) == cell and not _junk(r.form)]


def _nous_fut(inf, base, rows, impersonal, missing):
    """The nous form and the future, each only where it is not built on the
    infinitive (`inf`, without any pronoun the headword is entered with).
    Printed without the reflexive pronoun, which the slots already show;
    an impersonal verb's future is its third person, whole: il faudra, il
    s'en faudra.

    WHERE THE SOURCE GIVES TWO, the first that is not built on the
    infinitive is the one printed, if either is not: cueillir's table lists
    cueillirai before cueillerai, and it is cueillerai that a reader meets
    and cannot build.  Eight verbs are decided by it (cueillir, accueillir,
    recueillir, tressaillir, choir, déchoir, ouïr, gésir); every other pair
    of variants is two regular spellings (payerai and paierai, after paye
    and paie).
    """
    out = []
    if not impersonal:
        for pl in _variants(base, PL1):
            f, ipa = _unclitic(pl.form, _heard(pl, rows))
            if not _nous_regular(inf, f):
                snd = respell(ipa)
                if not snd:
                    missing.append(M_NOUS_SOUND)
                out.append("nous " + tl(f, snd))
                break
    presents = [_unclitic(r.form)[0]
                for r in _variants(base, SG3 if impersonal else SG1)]
    for fut in _variants(base, FUT3 if impersonal else FUT1):
        heard = _heard(fut, rows)
        f, ipa = _unclitic(fut.form, heard)
        if _future_regular(inf, presents, f, "a" if impersonal else "ai"):
            continue
        if impersonal:
            f, ipa = "il " + fut.form, heard
        snd = respell(ipa)
        if impersonal and snd:
            snd = "il " + snd
        if not snd:
            missing.append(M_FUT_SOUND)
        out.append("fut. " + tl(f, snd))
        break
    return out


def _whole(ctx, got, table, rows, plain, hw_rows, hw):
    """A pronominal verb the dictionary has as its own headword -- s'en
    aller, s'en sortir, s'y prendre -- read whole from that entry: its
    infinitive's sound is its own (/s‿ɑ̃.n‿a.le/, `sã-nalé`), and its nous
    form and future are the plain verb's."""
    missing = []
    f1 = got["headword"]
    s1 = _lemma_sound(ctx, got)
    if not s1:
        missing.append(M_INF_SOUND)
    sg = _pick(table, SG1)
    f2, s2 = sg.form, respell(_heard(sg, rows))
    if not s2:
        missing.append(M_SG1_SOUND)
    pp = _pick(table, PP)
    if pp is None and plain:
        pp = _pick(plain[0][1], PP)     # allé: the plain verb's, the same word
    f3 = s3 = ""
    if pp is not None:
        f3, s3 = pp.form, respell(_heard(pp, rows + hw_rows))
        if not s3:
            missing.append(M_PP_SOUND)
    else:
        missing.append(M_PP)
    extras = ["aux. être"]
    if plain:
        extras += _nous_fut(hw, plain[0][1], hw_rows, False, missing)
    meaning = _said(ctx, got, None, missing)
    return Parts([(f1, s1), (f2, s2), (f3, s3)], meaning=meaning,
                 extras=extras, missing=_named(missing))


def _bare_verb(ctx):
    """A verb entry with no table at all, and no homograph to read one from.

    Given as its infinitive and nothing it would have to invent, the rest
    named in `missing`: scléroser, messeoir, pailleter are verbs, and the
    editor's button says what to fill.  What is not an infinitive is not a
    verb this can describe -- an inflected page filed as a lemma (`chérisses`,
    "second-person singular present subjunctive of chérir"), an English word
    filed as French -- and is left to be a \\dw.
    """
    e = ctx.entry
    hw = e["headword"] or ""
    first = next((s for s in (e["sense"] or "").split("\n") if s.strip()), "")
    # a locution (avoir peur) is not described here; a pronominal verb
    # entered whole (se planter) is, as its infinitive
    if (" " in _bare_hw(hw) or not _INFINITIVE.search(hw)
            or _FORM_OF.search(first)):
        return None
    missing = []
    snd = _lemma_sound(ctx, e)
    if not snd:
        missing.append(M_INF_SOUND)
    missing += [M_SG1, M_PP, M_AUX]
    meaning = _said(ctx, e, False, missing)
    return Parts([(hw, snd), None, None], meaning=meaning,
                 missing=_named(missing))
