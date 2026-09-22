# SPDX-License-Identifier: GPL-3.0-or-later
"""Spanish: the \\vb a verb hit offers, read off the rows Wiktionary wrote.

    \\vb{tener}{}{tengo}{}{tuvo}{}{to have (fut. \\pw{tendré})}
    \\vb{hacer}{}{hago}{}{hizo}{}{to do (p.p. \\pw{hecho}; fut. \\pw{haré})}
    \\vb{llover}{}{llueve}{}{llovió}{}{to rain}
    \\vb{irse}{}{me voy}{}{se fue}{}{to go away, to leave, to depart, to go}
    \\vb{haber}{}{hay}{}{hubo}{}{there to be (fut. \\pw{habrá})}

    python3 lib/verbs/__init__.py es "se fue antes de que saliera el sol"

WHAT docs/lang/es.md ASKS FOR, and all this file makes: the infinitive, the
first person present and the third person preterite -- the registry's
`pres.` and `pret.` -- then the meaning, then, in one parenthesis and only
where they are irregular, the past participle and the first person future.
No sound in any slot: the spelling says it, form.roman is empty in every
one of es.db's 674 540 rows, and the one pronunciation there is, entry.ipa,
is the infinitive's with its stress marked, which es.md forbids.

WHERE EACH FORM COMES FROM.  A Spanish verb page gives the three forms its
head line names -- `first-person present singular`, `first-person preterite
singular`, `participle past`, joined with spaces and WITHOUT `indicative` --
and then the generated table, whose cells do say `indicative`.  getdict.py
drops a table cell whose spelling the head line already gave, so tener's
table `tengo` is gone and only the head's is left; a question for the whole
tag set {first-person, indicative, present, singular} finds nothing for
tener and `me duermo` for dormir (a cell of dormir's reflexive table that no
head row shadowed).  So every cell is asked for by its EXACT tag set, the
head's and the table's separately, and a form that opens with a reflexive
clitic is taken only by the reading that wants one.  A row whose note has
commas is a pointer -- another page saying "tuvo is the third person
preterite of tener" -- and is asked last; the exact set is also what keeps
its `obsolete` and `with-voseo` cousins out (tener's pointers include tiée).

WHICH VERB THE CHUNK HAS is decided here and nowhere else, because only the
chunk says it and a lookup is one word at a time: `se fue` reaches ir, and
the \\vb es.md wants is irse's; `Había una vez` reaches haber, and the \\vb
it wants is hay's, not the auxiliary's.  See _chunk_pronominal and
_haber_impersonal for exactly what is taken as evidence.  Where the only
evidence is a bare `se` -- as often passive or impersonal (`se dice`) as
the verb's own (`se levanta`) -- the -se verb is drafted and `missing` says
it is a question, since the plain verb would be the other wrong draft and
would look finished.  Nothing reaches a fixed phrase (darse cuenta): the
lookup never offers one, and if a hit ever is one it is built from its own
rows like any other entry.

NOTHING IS GUESSED, and that includes the three things a Spanish \\vb is
tempted to guess.  An impersonal verb gives the third person present in the
second slot because its head line does (llover: llueve -- the table's
lluevo is not used); `me levanto` is `me ` and a row, the one composition
Spanish spelling never breaks; a phrase borrows its base verb's cell
(echar de menos: echó de menos) only when the base's first person, written
the way the phrase writes it, IS the phrase's own head row.  What cannot be
read is named in `missing`, in the registry's own words for the slot.
"""
import re
import unicodedata

import lookup
import verbs
from verbs import Parts, tl

# ------------------------------------------------------------- the cells
# Each cell by its exact tag set: _H as the head line spells it, _T as the
# table does (and the pointer pages, comma-joined).
PRES1_H = frozenset(("first-person", "present", "singular"))
PRES1_T = frozenset(("first-person", "indicative", "present", "singular"))
PRES3_H = frozenset(("present", "singular", "third-person"))
PRES3_T = frozenset(("indicative", "present", "singular", "third-person"))
PRET1_H = frozenset(("first-person", "preterite", "singular"))
PRET1_T = frozenset(("first-person", "indicative", "preterite", "singular"))
PRET3_H = frozenset(("preterite", "singular", "third-person"))
PRET3_T = frozenset(("indicative", "preterite", "singular", "third-person"))
PP = frozenset(("participle", "past"))
FUT1 = frozenset(("first-person", "future", "indicative", "singular"))
FUT3 = frozenset(("future", "indicative", "singular", "third-person"))
PERSONS = frozenset(("first-person", "second-person", "third-person"))

# The reflexive clitics, and who each one is.  A proclitic that is the same
# person as its verb is the verb's own object: `me voy`, `te quedas`.
REFL = {"me": ("first-person", "singular"), "te": ("second-person", "singular"),
        "se": ("third-person", None), "nos": ("first-person", "plural"),
        "os": ("second-person", "plural")}
CLITICS = frozenset(("me", "te", "se", "nos", "os",
                     "lo", "la", "los", "las", "le", "les"))

# AN INFINITIVE, perhaps with clitics written onto it, perhaps the first word
# of a phrase, perhaps after a `no`: hablar, reír, irse, arreglárselas, darse
# cuenta, echar de menos, no tener ni idea.  Over es.db's 11 856 verb
# entries, the 1 139 single words that are none of these are inflected forms
# entered as lemmas (había, "makes pluperfect to verbs"; autoanalicemos) or
# combined forms (ñangótale): not one has a head row to read.  Two phrases
# are ni ... ni ... and two have a comma in the headword, where the head
# template's arguments come apart -- llamar al pan, pan, y al vino, vino
# has `pan` and `vino` as "past participles".  Those four get no \vb.
_INF = re.compile(r"^(?P<inf>.*?[aeiáéí]r)(?P<cl>(?:se|me|te|nos|os|l[aeo]s?)*)$")
_CL = re.compile(r"se|me|te|nos|os|l[aeo]s?")

# What a participle looks like: -ado, -ido, -ído, and the strong ones in -to,
# -cho, -so (visto, hecho, impreso).  A row of a phrase's head line that is
# none of these is the phrase's words misread as a form (above).
_PARTICIPLE = re.compile(r"(?:ado|ido|ído|to|cho|so)$")

# Words of a chunk: letters only.  No Spanish verb hides behind an
# apostrophe or a hyphen.
_WORD = re.compile(r"[^\W\d_]+")

# SENSES THAT ARE NOT MEANINGS.  venir's first sense is a heading, "Senses
# relating to literal movement.", and a later one "Figurative senses.";
# 1 261 verb entries' first is "only used in se ... X" and 156 "synonym of
# X".  A heading is skipped for the sense under it; a pointer is what the
# whole entry is, and is said in `missing` rather than printed as a gloss.
_HEADING = re.compile(r"(?i)^(?:\w+\s+)?senses\b")
_POINTER = re.compile(r"(?i)^(?:only used in|synonym of|(?:[\w-]+\s+)*"
                      r"(?:form|spelling) of|compound of)\b")
# gustar's first sense says what English does with it and then explains:
# 'translated as "to like", analyzable in structure as "to please" ...'.
# The equivalent is the quoted one.
_TRANSLATED = re.compile(r'(?i)^translated\s+(?:\w+\s+)?as\s+"([^"]+)"')
# An entry that is only the clitic-less half of a pronominal verb:
# arrepentir is "only used in se ... arrepentir, syntactic variant of
# arrepentirse" (190 such infinitives).  The \vb is arrepentirse's.
_VARIANT = re.compile(r"(?i)^only used in se\b(?:.*?syntactic variant of\s+([^\s,.;]+))?")

# A sense tag that makes a reflexive tag optional: venir's "to come" is
# `reflexive,sometimes`, abrir's "to open" `intransitive,reflexive,
# transitive`.  Those are senses of the plain verb too.
_ALSO_PLAIN = frozenset(("transitive", "intransitive", "ambitransitive",
                         "ditransitive", "sometimes", "also", "often",
                         "usually", "optionally"))


# ------------------------------------------------------------- the lemma
class Lemma:
    """What the headword says about the verb, before any row is read.

    `inf` the infinitive as written (arreglár), `base` without the accent a
    second clitic puts on it (arreglar), `clitics` the pronouns written onto
    it (['se', 'las']), `pre` a `no` before it, `rest` the words after it
    (cuenta, de menos), `pron` whether it is pronominal (a `se` among the
    clitics).
    """
    __slots__ = ("head", "inf", "base", "clitics", "pre", "rest", "pron")

    def __init__(self, head, inf, clitics, pre="", rest=""):
        self.head, self.inf, self.clitics = head, inf, list(clitics)
        self.pre, self.rest = pre, rest
        self.base = inf[:-2] + {"á": "a", "é": "e"}.get(inf[-2], inf[-2]) + "r"
        self.pron = "se" in self.clitics

    @classmethod
    def of(cls, headword):
        if "," in (headword or ""):
            return None
        words = (headword or "").split()
        pre = ""
        if len(words) > 1 and words[0].lower() == "no":
            pre, words = "no", words[1:]
        if not words:
            return None
        m = _INF.match(words[0].lower())
        if not m:
            return None
        return cls(headword, m.group("inf"), _CL.findall(m.group("cl")),
                   pre, " ".join(words[1:]))

    @property
    def simple(self):
        """One word, nothing written onto it: the only lemmas a chunk can
        turn into something else (ir -> irse, haber -> hay)."""
        return not (self.clitics or self.pre or self.rest)

    def pronominal(self):
        """The -se verb of a simple lemma: ir -> irse, reír -> reírse."""
        return Lemma(self.inf + "se", self.inf, ["se"])

    def shaped(self, form):
        """Is `form` already written the way this lemma writes its forms?"""
        w = (form or "").split()
        if not w:
            return False
        if self.pre and w[0].lower() == self.pre:
            return True
        if self.clitics and w[0].lower() in CLITICS:
            return True
        return bool(self.rest) and (form or "").endswith(" " + self.rest)

    def dressed(self, form, who):
        """A form of the BASE verb as this lemma writes it: the `no`, its
        clitics in front (the `se` as `me` for the first person), the phrase
        after -- tengo -> no tengo ni idea, doy -> me doy cuenta.  `who` is
        'me' for the first person, 'se' for the third.  A form already in
        the lemma's shape is left as it is."""
        if not form or self.simple or self.shaped(form):
            return form or ""
        front = ([self.pre] if self.pre else []) + \
                [who if c == "se" else c for c in self.clitics]
        return " ".join(front + [form] + ([self.rest] if self.rest else []))

    def core(self, form):
        """The verb word of a row this lemma wrote: `me las arreglo` ->
        arreglo, `echado de menos` -> echado, `no tenido ni idea` ->
        tenido."""
        w = (form or "").split()
        r = self.rest.split()
        if r and w[-len(r):] == r:
            w = w[:-len(r)]
        if self.pre and w and w[0].lower() == self.pre:
            w = w[1:]
        while len(w) > 1 and w[0].lower() in CLITICS:
            w = w[1:]
        return w[0] if w else ""


def _unaccent(s):
    """Acute accents off, the diaeresis and ñ left: váyase -> vayase."""
    d = unicodedata.normalize("NFD", s or "")
    return unicodedata.normalize("NFC", d.replace("́", ""))


def regular_pp(lem):
    """The participles a regular verb has: -ado, -ido, and -ído after a
    vowel (leído, oído, caído, reído) -- both spellings of that last one, so
    a source that drops the accent is not taken for an irregular verb."""
    inf = _unaccent(lem.base)
    stem = inf[:-2]
    if inf.endswith("ar"):
        return {stem + "ado"}
    return {stem + "ido", stem + "ído"}


def regular_future(lem, form):
    """Is this future the infinitive plus an ending -- es.md's own test?

    A test of the stem and not of `-é`, because a phrase's future need not
    be the first person singular: caérsele los anillos writes `se me caerán
    los anillos`, and caerán is caer + án, regular.  tendré is not tener +
    anything, nor haré hacer, nor prediré predecir.  reír loses the accent
    that kept its vowels apart (reiré), as oír does (oiré)."""
    core = _unaccent(lem.core(form).lower())
    return core.startswith(_unaccent(lem.base)) and len(core) > len(lem.base)


# ------------------------------------------------------------- the rows
def _rows_of(conn, eid):
    """Another entry's rows, as ctx.rows gives the hit's own."""
    roman = "roman" if lookup._has_col(conn, "roman", "form") else "''"
    return [verbs.Form(r["form"] or "", r["note"] or "", verbs.split_tags(r["note"]),
                       r["roman"] or "", r["rowid"])
            for r in conn.execute(
                "SELECT rowid, form, note, %s AS roman FROM form "
                "WHERE entry_id = ? ORDER BY rowid" % roman, (eid,))]


def _lead(form):
    """The reflexive clitic a row opens with ('me voy' -> 'me'), or ''."""
    w = (form or "").split(" ", 1)
    return w[0].lower() if len(w) > 1 and w[0].lower() in REFL else ""


class Table:
    """One entry's rows, asked for the cells a Spanish \\vb prints.

    Every question is an exact tag set (see the module docstring), the
    entry's own rows before the pointers, and a `lead`: the reflexive
    clitic the form must open with, '' for none -- which is what keeps
    dormir's reflexive table (me duermo, se durmió) out of dormir's \\vb --
    or None for whatever it opens with, which is how a phrase's own rows
    are asked (caérsele los anillos: `se me caen los anillos`).  Each
    answer is the Form, so the caller knows whether it was the entry's own
    row or a pointer's.
    """

    def __init__(self, rows):
        self.rows = rows

    def cells(self, tags, own, lead=""):
        return [f for f in self.rows
                if f.tags == tags and f.own == own and f.form
                and (lead is None or _lead(f.form) == lead)]

    def first(self, lead, *asks):
        for tags, own in asks:
            got = self.cells(tags, own, lead)
            if got:
                return got[0]
        return None

    def every(self, lead, tags):
        got = self.cells(tags, True, lead) or self.cells(tags, False, lead)
        out = []
        for f in got:
            if f.form not in [g.form for g in out]:
                out.append(f)
        return out

    def pres1(self, lead=""):
        return self.first(lead, (PRES1_H, True), (PRES1_T, True), (PRES1_T, False))

    def pres3(self, lead=""):
        """The third person present a head line gives INSTEAD of the first:
        the mark of an impersonal verb (llover, ocurrir, atardecer)."""
        return self.first(lead, (PRES3_H, True))

    def pret1(self, lead=""):
        return self.first(lead, (PRET1_H, True), (PRET1_T, True))

    def pret3(self, lead=""):
        return self.first(lead, (PRET3_T, True), (PRET3_H, True), (PRET3_T, False))

    def pp(self):
        return [f.form for f in self.every(None, PP)]

    def future(self, third=False, lead=""):
        return self.every(lead, FUT3 if third else FUT1)

    def impersonal_present(self):
        """haber's `hay`: the one present its page tags impersonal.  Measured:
        the only row of any Spanish verb that is."""
        for f in self.rows:
            if "impersonal" in f.tags and "present" in f.tags and f.form:
                return f.form
        return ""


def ask(lem, get, who, derived=False):
    """One cell as `lem` writes it; `get(lead)` asks the table for a Form.

    Three kinds of lemma, three ways to ask.  A plain verb takes its rows
    with no reflexive clitic in front.  A -se verb built out of a plain
    one's rows (irse out of ir's, for `se fue`: `derived`) takes the
    reflexive table's row where the page has one (me voy, se fue) and puts
    the clitic in front of the plain row where it does not (levantar:
    me levanto).  A -se verb or a phrase with a page of its own takes its
    own head and table rows AS WRITTEN -- me quejo, se quejó, echo de
    menos, se me caen los anillos: they were written for this lemma, and
    dressing them again made `basto y sobro` into `basto y sobro y sobrar`
    -- and dresses only a pointer at it (arrepiento -> me arrepiento).
    """
    if derived:
        f = get(who)
        if f is not None:
            return f.form
        f = get("")
        return "%s %s" % (who, f.form) if f is not None else ""
    if lem.simple:
        f = get("")
        return f.form if f is not None else ""
    f = get(None)
    if f is None:
        return ""
    return f.form if f.own else lem.dressed(f.form, who)


def ask_all(lem, get, who, derived=False):
    """Every spelling of a cell (the futures), as `ask` gives one."""
    if derived:
        got = get(who)
        return [f.form for f in got] or ["%s %s" % (who, f.form) for f in get("")]
    if lem.simple:
        return [f.form for f in get("")]
    return [f.form if f.own else lem.dressed(f.form, who) for f in get(None)]


# ------------------------------------------------------------- the meaning
def _pure_reflexive(tagline):
    """Is this sense the -se verb's alone?  levantar's "to get up" is
    (`reflexive`); abrir's "to open" is not (`intransitive,reflexive,
    transitive`), nor venir's "to come" (`reflexive,sometimes`)."""
    tags = set(t.strip() for t in (tagline or "").split(","))
    return bool(tags & {"reflexive", "pronominal"}) and not tags & _ALSO_PLAIN


def _reflexive(tagline):
    tags = set(t.strip() for t in (tagline or "").split(","))
    return bool(tags & {"reflexive", "pronominal"})


def meaning_of(senses, taglines, want=None):
    """(meaning, found) from an entry's senses, ranked as lookup ranks them.

    `want` "refl": the first sense tagged reflexive or pronominal -- the
    meaning of irse, not ir's; "plain": the first that is not the -se
    verb's alone, since a plain verb's \\vb should not carry levantarse's
    "to get up"; None: the first.  A heading is skipped, `translated as
    "X"` gives X, and a sense that only points at another lemma is not a
    meaning at all.
    """
    ranked = lookup.rank_senses(list(senses), list(taglines))
    pool = [(s.strip(), t) for s, t, _tier in ranked
            if (s or "").strip() and not _HEADING.match(s.strip())]
    if want == "refl":
        # a sense of the -se verb itself before a note on the plain verb's
        # passive se (see _verb_gloss)
        pool = [(s, t) for s, t in pool if _verb_gloss(s, t)] or \
               [(s, t) for s, t in pool if _reflexive(t)]
    elif want == "plain":
        pool = [(s, t) for s, t in pool if not _pure_reflexive(t)] or pool
    for s, _t in pool:
        m = _TRANSLATED.match(s)
        if m:
            return verbs.trim_meaning(m.group(1)), True
        if _POINTER.match(s):
            continue
        got = verbs.trim_meaning(s)
        if got:
            return got, True
    return "", False


# ------------------------------------------------------------- the chunk
def _tokens(text):
    return [w.lower() for w in _WORD.findall(text or "")]


def _matching(rows, word):
    w = (word or "").lower()
    return [f for f in rows if f.form.lower() == w]


def _persons(rows):
    """(person, number) pairs these rows say a form can be; an object's
    person (combined forms) is not the verb's."""
    out = set()
    for f in rows:
        if any(t.startswith("object-") for t in f.tags):
            continue
        for p in PERSONS & f.tags:
            for n in [n for n in ("singular", "plural") if n in f.tags] or [None]:
                out.add((p, n))
    return out


def _verb_notes(conn, tok):
    return [verbs.split_tags(r["note"]) if r["note"] else frozenset(("infinitive",))
            for r in conn.execute(
                "SELECT f.note FROM form f JOIN entry e ON e.id = f.entry_id "
                "WHERE f.form = ? AND e.pos = 'verb' LIMIT 64", (tok,))]


def _nonfinite(conn, tok):
    """Is `tok` an infinitive, a gerund or a past participle of some verb?
    (A headword's own row has an empty note, and is its infinitive.)"""
    return any("infinitive" in t or "gerund" in t or PP <= t
               for t in _verb_notes(conn, tok))


def _participle(conn, tok):
    """Is `tok` the past participle that follows haber (masculine, singular:
    the one that does not agree)?"""
    return any(PP <= t and not t & {"feminine", "plural"}
               for t in _verb_notes(conn, tok))


def _next_verb(tokens, i):
    """The word after tokens[i], past one `que`, `a` or `de` (tener que, ir
    a, acabar de): where a clitic that climbed would have come from."""
    j = i + 1
    if j < len(tokens) and tokens[j] in ("que", "a", "de"):
        j += 1
    return tokens[j] if j < len(tokens) else ""


def _enclitic(word, rows):
    """Does the word itself carry the verb's own reflexive clitic?

    Two ways the rows say so.  A pointer page tags it (levantarse is
    `infinitive, reflexive`).  Or the word is a row of the verb with `se`
    or `te` after it: an infinitive or gerund with `se` (irse, yéndose,
    enamorarse), a formal imperative with `se` (váyase, siéntese), a tú
    imperative with `te` (siéntate, vete, ponte).  Not the -se of the
    imperfect subjunctive: hablase is habla + se only by its letters, and
    habla is the tú imperative, which takes te.

    NOT `irme`, `quedarte`, though the reflexive table lists them: the same
    spelling is an object as often -- `volver a llamarme` is "to call me
    again", and read as llamarse it drafted "to be called".  Only a verb
    that cannot take an object could tell the two apart, and the sense
    tags cannot say which verbs those are (llamar and decir have no sense
    tagged transitive at all).
    """
    w = (word or "").lower()
    for f in _matching(rows, w):
        if "reflexive" in f.tags:
            return True
    for suffix, person in (("se", "third-person"), ("te", "second-person")):
        if not w.endswith(suffix) or len(w) < len(suffix) + 2:
            continue
        stem = _unaccent(w[:-len(suffix)])
        for f in rows:
            if _unaccent(f.form.lower()) != stem or \
                    any(t.startswith("object-") for t in f.tags):
                continue
            if suffix == "se" and (f.tags & {"infinitive", "gerund"} or not f.note):
                return True                        # irse, yéndose
            if "imperative" in f.tags and person in f.tags and "plural" not in f.tags:
                return True                        # váyase, siéntate
    return False


def _verb_gloss(sense, tagline):
    """Is this reflexive sense a VERB of its own -- levantarse "to get up"
    -- rather than a note on the passive or impersonal se the plain verb
    takes?  decir's two reflexive senses are "to be said (passive voice
    structure)" and "it is said"; esperar's is "to be expected", tagged
    impersonal.  A verb's meaning is glossed as an English infinitive."""
    t = set(x.strip() for x in (tagline or "").split(","))
    s = (sense or "").strip()
    return (bool(t & {"reflexive", "pronominal"}) and "impersonal" not in t
            and s.lower().startswith("to ") and "passive" not in s.lower())


def _chunk_pronominal(ctx, rows, senses, taglines):
    """Does the chunk use this verb with its own reflexive clitic?  None
    for no, "sure" for a clitic that can be nothing else, "se" for the one
    that can.

    SURE: the word carries it (see _enclitic), or the word before it is
    `me`, `te`, `nos` or `os` and the same person as the verb -- `me voy`,
    `te quedas`, `nos casamos` -- where an object that is the subject IS
    the reflexive.  `te quiero`, `me dio` are an object and are not taken;
    nor is `se lo di`, whose se is le before lo.  The person is read from
    the entry's own rows: a nonstandard Catalan pointer at ir files `ves`
    as its imperative, and read with it `te ves` was irse.

    SE, the hard one.  `se levanta`, `se fue`, `se enamoró` are the -se
    verb; `se dice`, `se vendieron como rosquillas`, `se usan` are the
    impersonal and passive se of the plain one; nothing in a row tells them
    apart.  Measured on 3 000 sentences of corpus/es-en.db with se before a
    verb: the entry's own reflexive table has that very form (ir: `se fue`)
    in 1 241 cases, and a reflexive sense glossed as a verb of its own
    (levantar: "to get up") adds 932; read by hand, about three in four of
    the second kind are the -se verb, and the table is wrong too (usar has
    `se usan`).  So either is taken, and the caller says in `missing` that
    the se is a question -- the plain verb would have been the other wrong
    draft, and one that looked finished.

    NEVER where the next verb is not finite: in `se ha ido`, `me tengo que
    ir`, `se puso a llorar`, `no se puede quitar` the clitic may have
    climbed from the verb after it, and the plain verb is the honest draft.
    """
    w = (ctx.word or "").lower()
    if not w:
        return None
    if _enclitic(w, rows):
        return "sure"
    toks = _tokens(ctx.text)
    persons = _persons([f for f in _matching(rows, w) if f.own])
    own = {f.form.lower() for f in rows if f.own}
    verbal = any(_verb_gloss(s, t) for s, t in zip(senses, list(taglines) + [""] * len(senses)))
    got = None
    for i, t in enumerate(toks):
        if t != w or i == 0 or toks[i - 1] not in REFL:
            continue
        cl = toks[i - 1]
        p, n = REFL[cl]
        if not any(pp == p and (n is None or nn == n) for pp, nn in persons):
            continue
        if cl == "se" and not (("se " + w) in own or verbal):
            continue
        nxt = _next_verb(toks, i)
        if nxt and _nonfinite(ctx.conn, nxt):
            continue
        if cl != "se":
            return "sure"
        got = "se"
    return got


def _haber_impersonal(ctx, rows, hay):
    """Is this haber the one with no subject -- hay, había una vez -- and
    not the auxiliary of había llegado?

    `hay` says so itself: its page tags it impersonal.  Any other form is
    impersonal when it is a third person singular, or not finite, and the
    chunk puts no past participle after it: `Había una vez` against
    `había llegado`, `ha habido problemas` (whose habido is the impersonal
    one) against `ha sido`.  `ha` never is -- the impersonal present is
    hay -- nor `he`, `has`, `han`.  Without the chunk only hay is.
    """
    w = (ctx.word or "").lower()
    if w == hay.lower():
        return True
    mine = _matching(rows, w)
    if not mine or w in {f.form.lower() for f in rows if f.tags in (PRES3_H, PRES3_T)}:
        return False
    if not any(("third-person" in f.tags and "singular" in f.tags) or
               f.tags & {"infinitive", "gerund"} or PP <= f.tags or not f.note
               for f in mine):
        return False
    toks = _tokens(ctx.text)
    seen = False
    for i, t in enumerate(toks):
        if t != w:
            continue
        seen = True
        if i + 1 < len(toks) and _participle(ctx.conn, toks[i + 1]):
            return False
    return seen


# ------------------------------------------------------------- the recipe
def recipe(ctx):
    e = ctx.entry
    if (e["pos"] or "") != "verb":
        return None
    if (ctx.word or "").lower() in _never_gloss(ctx):
        # para is parar's and parir's too, sobre sobrar's, entre entrar's;
        # es.md's never-gloss list gives the word no entry at all, and a
        # \vb button under a preposition is a trap for the hand that edits
        return None
    lem = Lemma.of(e["headword"])
    if lem is None:
        return None
    senses = ctx.senses
    taglines = (e["sense_tags"] or "").split("\n")

    # arrepentir is only the clitic-less half of arrepentirse: that one's
    # rows, senses and lemma, when the dictionary has it
    m = _VARIANT.match(_first_sense(senses, taglines))
    if m and lem.simple:
        got = ctx.conn.execute(
            "SELECT id, headword, sense, sense_tags FROM entry "
            "WHERE headword = ? AND pos = 'verb' ORDER BY id LIMIT 1",
            (m.group(1) or lem.head + "se",)).fetchone()
        lem2 = Lemma.of(got["headword"]) if got is not None else None
        if lem2 is not None and lem2.pron:
            return build(ctx, lem2, _rows_of(ctx.conn, got["id"]), got["id"],
                         (got["sense"] or "").split("\n"),
                         (got["sense_tags"] or "").split("\n"), chunk=False)
    return build(ctx, lem, ctx.rows, e["id"], senses, taglines, chunk=True)


def _first_sense(senses, taglines):
    for s, _t, _tier in lookup.rank_senses(list(senses), list(taglines)):
        if (s or "").strip():
            return s.strip()
    return ""


def build(ctx, lem, rows, eid, senses, taglines, chunk=True):
    """The Parts for one entry.  `chunk`: may the chunk change which verb
    it is (ir -> irse, haber -> hay)?  Not for an entry reached by
    redirection, which is already the verb the page pointed at."""
    T = Table(rows)
    names = list(getattr(ctx.L, "vb_forms", None) or ())
    names += ["infinitive", "1st sg. present", "3rd sg. preterite"][len(names):]

    # ---- which verb: as it stands, impersonal, pronominal, haber's hay
    # IMPERSONAL IS THE HEAD LINE'S WORD, not the table's: llover's head
    # gives llueve and no first person, and its generated table gives a
    # lluevo all the same, which an ask that fell through to the table
    # printed as `pres. lluevo`.
    lead = "" if lem.simple else None
    impersonal = (T.first(lead, (PRES1_H, True)) is None
                  and T.first(lead, (PRES3_H, True)) is not None)
    hay = T.impersonal_present()
    use_hay = pron = doubt_se = False
    if chunk and lem.simple:
        if hay:
            use_hay = _haber_impersonal(ctx, rows, hay)
        elif not impersonal and any(_reflexive(t) for t in taglines):
            reading = _chunk_pronominal(ctx, rows, senses, taglines)
            pron = reading is not None
            doubt_se = reading == "se"
    if pron:
        lem = lem.pronominal()
    third = impersonal or use_hay
    who1 = "se" if third else "me"

    # ---- the three forms
    if use_hay:
        f2 = hay
    else:
        f2 = ask(lem, T.pres3 if impersonal else T.pres1, who1, pron)
    f3 = ask(lem, T.pret3, "se", pron)
    pps = [p for p in T.pp() if _PARTICIPLE.search(lem.core(p))]
    futs = ask_all(lem, lambda ld: T.future(third, ld), who1, pron)

    # ---- what this entry lacks, from one that proves it is the same verb
    if f2 and not use_hay and not (f3 and pps and futs):
        got = _borrow(ctx, lem, eid, T, f2, third, pron)
        if got is not None:
            f3 = f3 or got[0]
            pps = pps or got[1]
            futs = futs or got[2]

    meaning, found = _meaning(ctx, lem, senses, taglines, pron, use_hay)
    if not (f2 or f3 or found):
        # tar ("apheretic form of estar"), infarte ("only used in me
        # infarte"): no form to give and no meaning -- nothing a \vb could
        # offer that the \dw does not
        return None

    missing = []
    if not f2:
        missing.append(names[1])
    if not f3:
        missing.append(names[2])

    # ---- the extras, only what is irregular, and every spelling where one is
    extras = []
    if pps:
        cores = [lem.core(p) for p in pps]
        if any(c not in regular_pp(lem) for c in cores):
            extras.append(_alts("p.p. ", cores))
    else:
        missing.append("whether the past participle is irregular")
    if futs:
        if not all(regular_future(lem, f) for f in futs):
            # the clitic stays on a pronominal verb's future, as it does on
            # its two forms (me pondré beside me pongo, se puso); a phrase's
            # other words do not (hacer caso: fut. haré)
            cores = [lem.core(f) for f in futs]
            extras.append(_alts("fut. ", ["%s %s" % (who1, c) for c in cores]
                                if lem.pron else cores))
    else:
        missing.append("whether the future is irregular")
    if not found and verbs.gloss_is_en(ctx.gloss):
        missing.append("meaning")
    if doubt_se:
        missing.append("whether it is %s here (se may be passive or impersonal)"
                       % lem.head)
    return Parts(parts=[lem.head, f2, f3],
                 meaning=meaning if verbs.gloss_is_en(ctx.gloss) else None,
                 extras=extras, missing=missing)


def _alts(label, forms):
    """`p.p. \\pw{freído}/\\pw{frito}`: every spelling the source gives, in
    its order, once one of them is irregular.  Taking the first alone would
    print nothing for freír, imprimir and bendecir, whose first participle is
    the regular one and whose second (frito, impreso, bendito) is the one a
    reader meets."""
    out = label
    for k, f in enumerate(forms):
        out += ("/" if k else "") + tl(f)
    return out


def _meaning(ctx, lem, senses, taglines, pron, use_hay):
    """(the meaning slot, whether there is one).  Asked whatever the gloss
    is, because an entry with no form and no meaning gets no \\vb at all;
    the core drops it from a book not glossed in English."""
    table = ctx.data()
    if use_hay:
        fixed = (table.get("impersonal_meanings") or {}).get(lem.head)
        if fixed:
            return fixed, True
        for s, t in zip(senses, list(taglines) + [""] * len(senses)):
            if "impersonal" in t.split(","):
                return verbs.trim_meaning(s), True
    if not pron:
        fixed = (table.get("meanings") or {}).get(lem.head)
        if fixed:
            return fixed, True
    return meaning_of(senses, taglines,
                      "refl" if pron else (None if lem.pron else "plain"))


def _borrow(ctx, lem, eid, T, f2, third, derived):
    """(3sg preterite, participles, futures) from an entry that is this
    verb too, written the way this lemma writes them; or None.

    A phrase has head rows and no table: echar de menos gives `echo de
    menos` and nothing for él.  Its base verb, echar, has the table.  A
    single word may have a twin: explotar is two entries, "to exploit" with
    its head line only and "to explode" with the table.  THE OTHER ENTRY
    HAS TO PROVE IT IS THE SAME VERB, because some twins are not: apostar
    is to bet (apuesto) and to post (aposto), colar to strain (cuelo) and
    to confer (colo) -- 10 of the 72 twin headwords give two different
    presents.  So it is used only when its present, written as this lemma
    writes it, IS this entry's -- and, where both give one, its first
    person preterite too.  A phrase whose words change with the person
    (dar con sus huesos: doy con mis huesos) has no row to prove it with,
    and borrows nothing.
    """
    name = lem.head if lem.simple else lem.base
    who1 = "se" if third else "me"
    mine1 = ask(lem, T.pret1, "me", derived)
    for r in ctx.conn.execute(
            "SELECT id FROM entry WHERE headword = ? AND pos = 'verb' "
            "AND id != ? ORDER BY id", (name, eid)):
        U = Table(_rows_of(ctx.conn, r["id"]))
        p = U.pres3() if third else U.pres1()
        if p is None or lem.dressed(p.form, who1) != f2:
            continue
        theirs1 = U.pret1()
        if mine1 and theirs1 is not None and lem.dressed(theirs1.form, "me") != mine1:
            continue
        p3 = U.pret3()
        return (lem.dressed(p3.form, "se") if p3 is not None else "",
                [x for x in U.pp() if _PARTICIPLE.search(x)],
                [lem.dressed(f.form, who1) for f in U.future(third)])
    return None


def _never_gloss(ctx):
    return frozenset(w.lower() for w in (ctx.data().get("never_gloss") or [])
                     if isinstance(w, str))
