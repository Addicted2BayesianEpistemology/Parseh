"""German: the \\vb a dictionary hit for a verb offers.

    \\vb{geben}{}{gab}{}{gegeben}{}{to give (er gibt)}
    \\vb{aufstehen}{}{stand auf}{}{aufgestanden}{}{to get up (aux. sein)}
    \\vb{sich freuen}{}{freute}{}{gefreut}{}{to be glad (über + acc.)}
    \\vb{können}{}{konnte}{}{gekonnt}{}{to be able (ich kann)}

docs/lang/de.md says what goes in, and nothing here adds to it: the three
principal parts -- the infinitive, the preterite (third person singular, as a
main clause has it, so `stand auf`), the past participle -- and after the
meaning, in one parenthesis and each only where it is not the ordinary case,
the third person present, the auxiliary, and the case or the preposition the
verb governs.  A reflexive meaning puts `sich` in front of the infinitive.

WHERE EACH COMES FROM.  Rows the source wrote, every one; nothing is built
from the infinitive:

    preterite    the head line's row tagged exactly `past` -- else the
                 table's `first-person indicative preterite singular`
    participle   the head line's `participle past` -- else the table's third
                 person perfect, `hat besucht`, with its auxiliary taken off
    er fährt     the head line's `present singular third-person`, printed
                 when it is neither the stem + t nor the stem + et
    aux. sein    the chosen sense's `aux:` tag where the page gives that
                 meaning its own auxiliary -- else the head line's
                 `auxiliary` rows
    + dat.       the chosen sense's `obj:` tag (Wiktionary's {{+obj}}) --
                 else its `with-dative` / `with-genitive`
    sich         the chosen sense, tagged `reflexive`
    the meaning  the chosen sense, trimmed by the core, then to ONE
                 equivalent (docs/lang/de.md), without a bracketed
                 qualifier the parenthesis already prints or a
                 parenthesis that only says the verb has an object

The CHOSEN SENSE is the core's -- the first ranked -- unless it is not a
meaning at all (sein's "forms the present perfect ..."), or the chunk says
the other kind: a reflexive pronoun chooses the reflexive senses and none the
plain ones, and a preposition in the clause passes over a sense governing a
different one (see _choose).

The sound slots are the lemma's sound and nothing else, which for German is
empty: no lib/lang/de.ipa.json turns the entry's IPA into the editions'
respelling, and the preterite and participle rows carry none.  docs/lang/de.md
fills them only where a pronunciation line is given at all, so an empty one
is not missing -- the annotator adds the stress of a prefixed verb by hand.

THE ENTRY'S OWN ROWS, AND EXACTLY THOSE TAGS.  A row whose note has a comma
is a pointer page's, linked to the first entry with that spelling and part of
speech, so a homograph collects its twin's forms: `übergesetzt`, the
participle of separable übersetzen (to ferry across), is filed as a pointer
under inseparable übersetzen (to translate).  And a tag set is matched whole:
`past` is not `past subjunctive` (führe), `participle past` is not
`nonstandard participle past rare` (canceln's gecancelled), and `auxiliary`
is not `Northwest-German auxiliary colloquial` -- anfangen's `sein`, which
read as a subset made anfangen a sein verb.  Several rows of one kind are
read in the order the source wrote them and the first wins: lib/getdict.py
follows every row with its case-folded copy (aß, then ass), and Wiktionary
lists the standard doublet first (werden: geworden, worden; können: gekonnt,
then the substitute infinitive können).

WHAT GETS NO \\vb (None, and the editor offers the \\dw it always did):

  - a hit that is not pos `verb`;
  - a verb the word reaches only through its `auxiliary` row, or only as a
    noun made from it (see _reaches);
  - a capitalised word inside a sentence (see _a_noun), and a word the
    verb has only as its imperative where no imperative stands (see
    _stray_imperative);
  - haben, sein or werden where the clause ends in the participle (or, for
    werden, the infinitive) they make a tense with (see _helps);
  - a page with neither a preterite nor a participle row: nothing a \\vb
    prints could be filled.

A SEPARATED VERB IS PUT BACK TOGETHER (see _joined): `stand ... auf` is
aufstehen, and the \\vb offered on `stand` is aufstehen's.  The text read
for it is the sentence where the core hands one on, else the chunk (_where).

MEASURED on dict/de.db (built 2026-09-10), every one of its 10 237 verb pages
as its own headword: 10 170 get a \\vb and 10 134 of those are complete.
The 67 without are idioms and pages with no conjugation at all (`es gibt`,
`wahrhaben`, the participle adjective gekocht, `c.`); the 36 incomplete
name a preterite the page does not give (abendessen, bergsteigen), a third
person given only as literary or colloquial (fechten: ficht, fechtet), or
the case after a two-way preposition (zweifeln `an + …`).  None is refused
by texwrite, and each plain line is texparse's reading of its \\vb.

Standard library only: the server imports it.
"""
import re

import lookup                                                  # noqa: E402
from verbs import Parts, one_equivalent, trim_meaning          # noqa: E402

# ------------------------------------------------------------- the rows
# The head line's rows, by their whole tag set, and the table's cell that
# stands in where the head line is silent.
PAST = frozenset(("past",))
PAST_TABLE = frozenset(("first-person", "indicative", "preterite", "singular"))
PART = frozenset(("participle", "past"))
PERFECT = frozenset(("indicative", "multiword-construction", "perfect",
                     "singular", "third-person"))
PRES3 = frozenset(("present", "singular", "third-person"))
PRES3_TABLE = frozenset(("indicative", "present", "singular", "third-person"))
AUXILIARY = frozenset(("auxiliary",))
FIRST_SG = frozenset(("first-person", "present", "singular"))

# What a pointer row says of a NOUN made from the verb: das Können, der
# Radfahrer.  No form of a verb carries a gender.
NOUNISH = frozenset(("gerund", "agent", "masculine", "feminine", "neuter"))

# The two auxiliaries as a form row writes them.  The head line also has a
# row `haben or sein` (or `sein or haben`) tagged `auxiliary` -- the
# conjugation table's header, not a word -- and fahren, stehen and anfangen
# all carry it; anfangen's real `sein` row is the colloquial one, so reading
# the pseudo-row would give anfangen both auxiliaries.
HABEN, SEIN = "haben", "sein"
AUX_VERBS = frozenset((HABEN, SEIN, "werden"))

# Where a clause stops, besides punctuation, for finding the separable
# prefix at its end: `Er stand auf und ging` has its `auf` before the `und`,
# `Sie hörte auf zu weinen` before the `zu`, `Er kam früher an als ich`
# before the `als`.
CLAUSE_WORDS = frozenset(("und", "oder", "aber", "sondern", "denn",
                          "als", "wie", "zu"))

# A reflexive pronoun, and the subject it is reflexive with.  `sich` is
# reflexive wherever it stands; `mir` only with `ich`.  `Ich freue mich` is
# reflexive and `Er zeigt mir das Buch` is not -- and zeigen HAS a reflexive
# sense (sich zeigen, to appear), so counting every `mir` would have printed
# `sich zeigen` for the second.
REFLEXIVE = {"sich": None, "mich": "ich", "mir": "ich", "dich": "du",
             "dir": "du", "uns": "wir", "euch": "ihr"}
SUBJECTS = frozenset(("ich", "du", "er", "sie", "es", "wir", "ihr", "man"))

# Where a clause or a sentence ends: any mark at a word's edge but an
# apostrophe or a hyphen (geht's, Ein- und Ausgang).
_CUT = re.compile(r"[^\w'’\-]")
_STOP = re.compile(r"[.!?:…]")


def _own(ctx, *exacts):
    """The first of the entry's own rows with exactly one of these tag sets,
    tried in the order given."""
    for ex in exacts:
        f = ctx.pick(exact=ex, own=True, where=lambda r: bool(r.form.strip()))
        if f is not None:
            return f
    return None


def _a_form(ctx, form):
    """Could `form` be a form of this headword at all?  A space in it is a
    verb written in two words (Rad fahren: `fuhr Rad`, `Rad gefahren`) or a
    separable one's clause order (`stand auf`) -- and in a participle of a
    one-word headword it is the head line misread: the participle adjective
    ausgeschlafen, filed as a verb, has `of ausschlafen` as its `participle
    past`."""
    return " " not in form or " " in ctx.entry["headword"].strip()


def _participle(ctx):
    """The past participle, or "".

    THE PERFECT IS THE FALLBACK, AND NEVER A POINTER.  A dictionary built
    before lib/getdict.py kept one row per spelling AND meaning lost the head
    line's `participle past` wherever it is also the third person present --
    besucht, erzählt, studiert, verkauft: 2 778 of 9 024 verbs in the file
    built on 2026-09-08 -- and the one other place the participle stands
    among the entry's own rows is the table's perfect, `hat besucht`.  (The
    rebuilt file has the head line's row on every verb, and the fallback is
    taken 0 times in 10 237; it is here for the dictionary somebody has not
    rebuilt.)  The pointer row `participle, past` would have been nearer to
    hand and is never used: it lands on the first homograph."""
    f = _own(ctx, PART)
    if f is not None and _a_form(ctx, f.form.strip()):
        return f.form.strip()
    f = _own(ctx, PERFECT)
    if f is not None:
        bits = f.form.split()
        if len(bits) > 1 and bits[0] in ("hat", "ist"):
            return " ".join(bits[1:])
    return ""


# -------------------------------------------------------------- the text
def _tokens(text, L):
    """[(word, clause number, opens a sentence, where it starts)], the words
    bare as lookup reads them.  A clause ends wherever a mark stands at a
    word's edge; a sentence where that mark is a stop."""
    out, clause, start = [], 0, True
    for m in re.finditer(r"\S+", text or ""):
        tok = m.group(0)
        w = lookup._bare(tok, L)
        if not w:
            clause += 1
            start = start or bool(_STOP.search(tok))
            continue
        k = tok.find(w)
        before, after = tok[:k], tok[k + len(w):]
        if out and _CUT.search(before):
            clause += 1
        out.append((w, clause, start, m.start() + k))
        start = False
        if _CUT.search(after):
            clause += 1
            start = bool(_STOP.search(after))
    return out


def _where(ctx):
    """(the clause the word stands in, as a list of words; its place there;
    whether it opens a sentence) -- or (None, -1, True) where the text does
    not hold it.

    THE SENTENCE WHERE THERE IS ONE.  The prefix a separated verb leaves at
    the end of its clause is very often in the next chunk: the fixture book
    chunks `Der Schuster lächelte | und stand langsam | von seinem Stuhl
    auf.`, and from its chunk `stand` is stehen while from its sentence it is
    aufstehen.  The readers send the sentence with the chunk; where the core
    hands it on (`ctx.sentence`) it is read, and the word is looked for
    inside the chunk's own stretch of it, so that a word the sentence holds
    twice is the chunk's.  Otherwise the chunk is all there is.

    READING THE TEXT MAKES THE ANSWER DEPEND ON IT (verbs.Ctx.text), and
    German reads it for nearly every verb -- any finite form may have its
    prefix at the end of the clause -- so a German \\vb is built once per
    chunk and not once per verb.  It costs 2-3 ms a chunk.  The word is
    found as written first and folded second -- a sentence's first word is
    capitalised and lookup found it folded."""
    if not ctx.word:
        return None, -1, True
    chunk = ctx.text or ""
    sentence = getattr(ctx, "sentence", "") or ""
    for text in ((sentence, chunk) if sentence.strip() else (chunk,)):
        toks = _tokens(text, ctx.L)
        lo = -1
        if chunk.strip() and text is not chunk:
            lo = text.find(chunk.strip())
        hi = lo + len(chunk.strip()) if lo >= 0 else -1
        fold = lookup._fold(ctx.word, ctx.L)
        at = None
        for same in (lambda t: t[0] == ctx.word,
                     lambda t: lookup._fold(t[0], ctx.L) == fold):
            hits = [k for k, t in enumerate(toks) if same(t)]
            inside = [k for k in hits if lo <= toks[k][3] < hi]
            if inside or hits:
                at = (inside or hits)[0]
                break
        if at is None:
            continue
        n = toks[at][1]
        clause = [t[0] for t in toks if t[1] == n]
        first = next(k for k, t in enumerate(toks) if t[1] == n)
        return clause, at - first, toks[at][2]
    return None, -1, True


# ------------------------------------------------------ is this a verb here
def _reaches(ctx):
    """Does the word reach this entry as a form of the verb?

    NOT THROUGH ITS AUXILIARY.  A verb's head line lists the auxiliary it
    takes as a form row -- `haben` is that row on 9 241 verbs and `sein` on
    1 429 -- so the lookup of `haben` answers haben and then raven and
    listen, reached through those rows, and each would have offered its own
    \\vb for the word `haben`.

    NOR AS A NOUN MADE FROM IT.  A pointer page files das Können under
    können as a `gerund, neuter` and der Radfahrer under Rad fahren as an
    `agent, masculine`: the word is the noun, and a \\vb is not what it is
    glossed with.  A word that is also the verb's own form (können, the
    infinitive, under the capital of a sentence's first word) is the verb.
    """
    fold = lookup._fold(ctx.word, ctx.L)
    got = [r for r in ctx.rows if lookup._fold(r.form, ctx.L) == fold]
    if not got:
        return True             # reached some way not seen here: let it be
    return any(r.tags != AUXILIARY and not (r.tags & NOUNISH) for r in got)


def _a_noun(ctx):
    """Is the word, as the text writes it, a noun?

    CAPITALS ARE SPELLING (docs/lang/de.md): German writes every noun with
    one and no verb, so a capitalised word inside a sentence is a noun
    whatever else the dictionary says it can be -- `beim Schwimmen`, `das
    Essen`.  The first word of a sentence is capitalised whatever it is,
    `Können Sie mir helfen?`, and is let through; so is a word the text does
    not hold."""
    if not ctx.word[:1].isupper() or ctx.word.isupper():
        return False                        # small, or a line set in capitals
    clause, _i, opens = _where(ctx)
    return clause is not None and not opens


# What may stand before an imperative in its clause: `Und komm bald`,
# `Bitte setz dich`.
BEFORE_IMPERATIVE = frozenset(("und", "aber", "oder", "doch", "bitte", "nun",
                               "jetzt", "dann", "also", "so"))
IMPERATIVE_SUBJECTS = frozenset(("ich", "er", "es", "wir", "man"))


def _stray_imperative(ctx):
    """Is the word this verb's imperative and nothing else, where no
    imperative can stand?

    A WORD THE DICTIONARY KNOWS ONLY AS AN IMPERATIVE IS USUALLY ANOTHER
    WORD.  `hat` is haten's (to hate) imperative, `weiß` weißen's, `still`
    stillen's, `schnell` schnellen's, `weil` weilen's, `tun` tunen's: the
    lookup answers each after the word the text means, and each offered its
    \\vb -- `\\vb{haten}{}{hatete}{}{gehatet}{}{to hate}` on every `hat` in a
    book.  An imperative opens its clause (after an `und` or a `bitte` at
    most) and has no subject of its own; `Er hat Hunger`, `Die Straße lag
    still`, `weil er früh aufsteht` have theirs elsewhere or a subject, and
    those hits get no \\vb.  `Beeil dich!` and `Mach die Tür zu!` keep
    theirs."""
    fold = lookup._fold(ctx.word, ctx.L)
    got = [r for r in ctx.rows if lookup._fold(r.form, ctx.L) == fold]
    if not got or not all("imperative" in r.tags for r in got):
        return False
    clause, i, _opens = _where(ctx)
    if clause is None:
        return False
    if any(w.lower() not in BEFORE_IMPERATIVE for w in clause[:i]):
        return True
    # `sie` written small is she or they; `Sie` may be the polite imperative's
    return any(w.lower() in IMPERATIVE_SUBJECTS or w == "sie" for w in clause)


def _is_participle(conn, w):
    return conn.execute(
        "SELECT 1 FROM form f JOIN entry e ON e.id = f.entry_id "
        "WHERE f.form = ? AND f.note = 'participle past' AND e.pos = 'verb' "
        "LIMIT 1", (w,)).fetchone() is not None


def _is_infinitive(conn, w):
    return conn.execute(
        "SELECT 1 FROM entry WHERE headword = ? AND pos = 'verb' LIMIT 1",
        (w,)).fetchone() is not None


def _helps(ctx):
    """Is this haben, sein or werden an auxiliary here?

    docs/lang/de.md gives the full entry of a perfect to the participle, where
    the meaning is -- `gesehen`: \\vb{sehen}... -- and the auxiliary a
    pointer, `hat · haben, makes the perfect with gesehen below`; a
    \\vb{haben} on that `hat` would say `to have` of a sentence about
    seeing.  So where the clause ENDS in the participle (any verb's own
    `participle past`: gegessen, angekommen, gewesen) -- or, for werden, in
    an infinitive, the future's `wird kommen` -- there is no \\vb, and the
    editor offers the \\dw the pointer is written from.  `Er hat ein Haus`,
    `Er ist müde`, `Er wird Arzt` end in neither and get their \\vb.

    AT THE END, because that is where German puts it, and anywhere else a
    participle is an adjective or an adverb: `Das ist bestimmt richtig` has
    bestimmen's participle in it, and its `ist` is the copula.  The end is
    read past the verbs a perfect can close on -- `weil er angekommen ist`,
    `gegessen haben`, `gelesen worden`, `hat kommen können` -- and nothing
    else.  A participle in the next chunk is not seen, and the \\vb offered
    is the draft docs/lang/de.md tells the annotator to correct."""
    if ctx.entry["headword"] not in AUX_VERBS:
        return False
    fold = lookup._fold(ctx.word, ctx.L)
    if any(lookup._fold(r.form, ctx.L) == fold
           for r in ctx.picks(exact=PART, own=True)):
        return False                        # the word IS its participle
    clause, i, _opens = _where(ctx)
    if clause is None:
        return False
    future = ctx.entry["headword"] == "werden"
    for k in range(len(clause) - 1, -1, -1):
        if k == i:
            continue
        w = clause[k]
        if _is_participle(ctx.conn, w):
            return True
        if not _is_infinitive(ctx.conn, w):
            return False                    # the clause ends in something else
        if future:
            return True
    return False


# ------------------------------------------------- the separated verb
def _joined(ctx):
    """The separable verb this finite form belongs to, where the clause
    holds its prefix -- as a Ctx on that verb's entry -- or None.

    GERMAN LEAVES THE PREFIX AT THE END OF THE CLAUSE.  `Er stand langsam
    auf`: the finite verb alone is another verb (stand is stehen, to stand)
    and the sentence says aufstehen, to get up.  The dictionary knows the
    pair: aufstehen's own table has `stand auf` as its `past`, anrufen's
    `rief an`, abfahren's `fährt ab`, and a verb written in two words has
    them the same way (Rad fahren: `fährt Rad`).  So each word after this
    one that ends the clause -- the last, or the last before an `und`, a
    `zu`, an `als` -- is tried with this one, `stand auf`, among the verbs'
    own rows; the first a verb has is the verb.

    NOT THE COMPOUND TENSES.  The table has `ist aufgestanden` and `wird
    aufstehen` too, as rows of aufstehen, and joining on them made the `ist`
    of `ist aufgestanden` offer aufstehen's \\vb: only the simple forms
    count, which are the only ones a prefix leaves.

    A PREFIX THAT IS NOT AT THE END IS A PREPOSITION.  `Er stand auf dem
    Tisch` has its `auf` before its noun, and `stand auf` is never tried."""
    clause, i, _opens = _where(ctx)
    if clause is None:
        return None
    L = ctx.L
    for j in range(i + 1, len(clause)):
        # the last word, or the last before an `und`; a clause word is a
        # candidate too where it ends the clause -- `zu` is zumachen's
        # prefix in `Er macht die Tür zu`
        if j + 1 < len(clause) and clause[j + 1].lower() not in CLAUSE_WORDS:
            continue
        pair = "%s %s" % (ctx.word, clause[j])
        for form in dict.fromkeys((pair, lookup._fold(pair, L))):
            for r in ctx.conn.execute(
                    "SELECT f.entry_id, f.note FROM form f JOIN entry e "
                    "ON e.id = f.entry_id WHERE f.form = ? AND e.pos = 'verb' "
                    "ORDER BY f.rowid", (form,)):
                note = r["note"] or ""
                if ("," in note or "multiword-construction" in note
                        or r["entry_id"] == ctx.entry["id"]):
                    continue
                # that verb's Ctx: its hit carries the lemma's own sound, the
                # way lookup works it out for a hit -- never the finite
                # verb's, whose entry this is not -- and it has this word,
                # chunk and sentence (_where): `Stell dir vor!` is read for
                # its `dir` on vorstellen too
                sub = ctx.other(r["entry_id"])
                if sub is not None:
                    return sub
    return None


# -------------------------------------------------------------- the sense
# WHAT A SENSE LINE CAN BE THAT IS NOT A MEANING.  The first ranked sense of
# sein is "forms the present perfect and past perfect tenses of certain
# verbs", of haben "forms the perfect aspect (have)", of werden "will, to be
# going to, forms the future tense" and then two more of the kind; anziehen's
# first is the sense-group heading "senses related to dressing", sein's
# second "As a copulative verb:".  63 verbs open on "synonym of ...", 13 on
# "censored spelling of ...", 11 idioms on "Used other than figuratively or
# idiomatically: see ...".  Each is passed over for the first sense that is
# a meaning; a verb with none keeps its first.
_JUNK = re.compile(
    r"(?i)^(?:senses? related to|as an? [\w-]+ verb|used\b|forms\b|"
    r"translated\b|expresses\b|synonym of|censored spelling|former spelling|"
    r"dated spelling|clipping of|alternate transliteration|"
    r"alternative (?:form|spelling)|for non-idiomatic)"
    r"|\bforms the\b|:$")

# The qualifiers a raw gloss keeps in square brackets are the facts the
# parenthesis prints from the tags -- `[with dative] to resemble` (ähneln),
# `[auxiliary haben] to brush` (streifen) -- and printed twice they read
# `to resemble (+ dat.)` beside a `[with dative]`.  One cut short by the
# source runs to the end (fehlen: `for there to be a lack [with dative
# ‘to someone/something’`).
_BRACKET = re.compile(r"\s*\[(?:with|auxiliary)\b[^\]]*(?:\]|$)")


# A PARENTHESIS THAT ONLY SAYS THE VERB HAS AN OBJECT.  können is "to be
# able (to do or be something)", müssen "to have to (do something)", mögen
# "to like (something or someone)", helfen "to help (someone)": the core
# keeps a qualifier that short as information, and here it is none -- the
# object is what the parenthesis after the meaning names, `+ dat.` -- and
# it printed `to help (someone) (er hilft; + dat.)` where docs/lang/de.md's
# model entry is `to help (er hilft; + dat.)`.  Only a parenthesis made of
# nothing but these words goes: "(for)" (warten) and "(a vehicle)" stay.
_PLACEHOLDER = frozenset((
    "to", "do", "be", "or", "and", "something", "someone", "somebody",
    "sth", "sb", "smth", "smb", "one", "oneself", "someone's", "one's"))


def _no_placeholder(m):
    words = [w for w in re.split(r"[\s/]+", m.group(1).lower()) if w]
    if words and all(w in _PLACEHOLDER for w in words):
        return ""
    return m.group(0)


def _meaning(sense):
    """A sense line as the meaning slot: the core's trimming, without the
    bracketed qualifiers or an object placeholder, and ONE equivalent --
    docs/lang/de.md: "One equivalent in the gloss language rather than a
    string of synonyms" (freuen's "to gladden, to make glad, to make
    pleased" is "to gladden")."""
    s = trim_meaning(_BRACKET.sub("", sense or ""))
    s = re.sub(r"\s*\(([^()]*)\)", _no_placeholder, s)
    s = re.sub(r"\s+([,;])", r"\1", s).strip()
    return one_equivalent(s)


def _senses(ctx):
    """[(meaning, tags, the raw line)] per sense, the tags a tuple in the
    line's own order (the first {{+obj}} of a sense is its object), in
    lookup's order -- the order the hit's senses are in, so that the first
    is the core's own meaning."""
    tags = (ctx.entry["sense_tags"] or "").split("\n")
    keep = [(s, tags[i] if i < len(tags) else "")
            for i, s in enumerate(ctx.senses) if s.strip()]
    ranked = lookup.rank_senses([s for s, _t in keep], [t for _s, t in keep])
    return [(_meaning(s), tuple(x.strip() for x in t.split(",") if x.strip()),
             s) for s, t, _tier in ranked]


# A sense tagged `reflexive` and nothing else of the kind is a reflexive
# verb; one tagged `reflexive` beside `transitive` is a verb that CAN be
# reflexive.  waschen has one sense, `ditransitive, intransitive, reflexive,
# transitive`: read as reflexive it printed `sich waschen` for `Ich wasche
# das Auto`.
_VALENCY = frozenset(("transitive", "intransitive", "ditransitive",
                      "ambitransitive"))


def _refl_can(tags):
    return "reflexive" in tags


def _refl_only(tags):
    return "reflexive" in tags and not (_VALENCY & set(tags))


def _wants_refl(ctx):
    """Does the clause hold a reflexive pronoun for this verb?

    AN IMPERATIVE HAS NO SUBJECT TO AGREE WITH -- `Beeil dich!` -- so a
    `dich` with a verb that can be one counts, but only in a clause with no
    subject pronoun: `denke` and `verstehe` are imperatives too, and `Ich
    denke oft an dich` and `Ich verstehe dich nicht` were read as sich
    denken, to imagine, and sich verstehen, to understand oneself."""
    clause, _i, _opens = _where(ctx)
    if clause is None:
        return False
    low = [w.lower() for w in clause]
    fold = lookup._fold(ctx.word, ctx.L)

    def mine(r):
        # the word's own row -- or, for a separable verb put back together,
        # the row it heads: `Stell dir vor!` is vorstellen's `stell vor`
        f = lookup._fold(r.form, ctx.L)
        return f == fold or f.startswith(fold + " ")
    for w in low:
        if w not in REFLEXIVE:
            continue
        subj = REFLEXIVE[w]
        if subj is None or subj in low:
            return True
        if subj in ("du", "ihr") and not (set(low) & SUBJECTS) and any(
                "imperative" in r.tags for r in ctx.rows if mine(r)):
            return True
    return False


def _choose(ctx, senses):
    """The sense the \\vb describes, and whether it is the reflexive verb:
    (meaning, tags, sich) -- ("", (), False) where there is no sense.

    THE FIRST RANKED SENSE, as the core would take it, unless it is not a
    meaning (_JUNK) or the text says the other kind.  A verb with reflexive
    and plain senses is two verbs a learner must tell apart -- freuen, to
    gladden, and sich freuen, to be glad -- and which one the chunk holds is
    written in it: a `sich` (or `mich` with `ich`) is the reflexive, none is
    the plain.  A verb whose every sense is reflexive and nothing else
    (beeilen: sich beeilen, to hurry) is reflexive with or without a pronoun
    in view; one that only CAN be (waschen) is reflexive only with one.
    """
    if not senses:
        return "", (), False
    wants = any(_refl_can(s[1]) for s in senses) and _wants_refl(ctx)
    if wants:
        pool = [s for s in senses if _refl_can(s[1])] or senses
    else:
        pool = [s for s in senses if not _refl_only(s[1])] or senses
    good = [s for s in pool + senses if s[0]
            and not _JUNK.search(s[2].strip()) and not _JUNK.search(s[0])]
    pick = good[0] if good else pool[0]
    # THE PREPOSITION IN THE TEXT OVERRULES THE ONE IN THE ORDER.  sich
    # freuen is `über + acc.` first (to be glad about) and `auf + acc.`
    # second (to look forward to), and `Er freut sich auf den Urlaub` was
    # offered the first -- a line whose parenthesis says über beside a
    # sentence that says auf.  Only that: a sense is passed over when the
    # preposition it governs is not in the clause and a later one's is; a
    # sense governing none is never passed over for one that does.
    said = _prep_of(ctx, pick[1])
    if said:
        clause, i, _opens = _where(ctx)
        words = set(w.lower() for k, w in enumerate(clause or []) if k != i)
        if said not in words:
            for s in good:
                if (s is not pick and s in pool
                        and _prep_of(ctx, s[1]) in words):
                    pick = s
                    break
    sich = _refl_can(pick[1]) if wants else _refl_only(pick[1])
    return pick[0], pick[1], sich


def _prep_of(ctx, tags):
    """The preposition this sense's parenthesis would print, or ""."""
    item = _governs(ctx, tags)[0]
    return "" if not item or item.startswith("+") else item.split()[0]


# ---------------------------------------------------------- the extras
def _stem(inf):
    """The present stem, for the one test the third person is put to:
    fahren -> fahr, lächeln -> lächel, tun -> tu, sein -> sei."""
    if inf.endswith("en"):
        return inf[:-2]
    if inf.endswith("n"):
        return inf[:-1]
    return inf


def _third(ctx, head, senses):
    """`er fährt`, `er fährt ab`, `ich kann` -- or "" where the third person
    is the ordinary one -- and whether the row was there to test at all.

    ORDINARY IS STEM + T OR STEM + ET, tested on the finite verb alone: the
    row of a separable verb is `fährt ab` and of a verb in two words `fährt
    Rad`, and the rest is taken off the headword to find the verb it goes
    with (abfahren -> fahren, Rad fahren -> fahren).  arbeitet, öffnet,
    heißt, lächelt, tut are ordinary; gibt, hält, lädt, ist, wird are not.
    What is printed is the row whole: `er fährt ab`.

    THE FIRST PERSON WHERE IT IS THE SAME WORD.  docs/lang/de.md: "A modal
    changes it through the whole singular, so the first person goes there
    instead: ich kann".  Which verbs those are is the source's to say, one of
    two ways.  A row that is this very spelling as the first person: the
    pointer page `kann` is `first-person, present, singular, third-person`,
    `weiß` is `first-person, present, singular` -- a pointer trusted here
    only to say that our own `kann` is also `ich kann`, never to bring a form
    in.  Or a sense tagged `preterite-present` AND a third person with no
    -t, which is what a preterite-present's is (kann, muss, darf, mag, will,
    vermag): the tag alone is not enough, because Wiktionary puts it on
    herabwerfen, and `ich wirft herab` is not German.  werden's `wird` is
    neither -- its first person is `werde` -- and stays `er wird`.

    `es` FOR A VERB THAT HAS NO OTHER SUBJECT: one whose every sense is
    tagged `impersonal`."""
    f = _own(ctx, PRES3, PRES3_TABLE)
    if f is None:
        return "", False
    form = f.form.strip()
    bits = form.split()
    fin, rest = bits[0], [b for b in bits[1:] if b.lower() != "sich"]
    base = " ".join(b for b in head.split() if b.lower() != "sich")
    if rest:
        tail = " ".join(rest)
        if base.lower().startswith(tail.lower()):
            base = base[len(tail):].strip()
        else:
            base = base.split()[-1]
    else:
        base = base.split()[-1] if base.split() else base
    stem = _stem(base)
    if fin in (stem + "t", stem + "et"):
        return "", True
    first = any(
        FIRST_SG <= r.tags and not (r.tags & {"subjunctive", "subjunctive-i",
                                               "subjunctive-ii", "imperative"})
        and r.form.strip() == form for r in ctx.rows) or (
        not fin.endswith("t")
        and any("preterite-present" in s[1] for s in senses))
    if first:
        who = "ich"
    elif senses and all("impersonal" in s[1] for s in senses):
        who = "es"
    else:
        who = "er"
    return "%s %s" % (who, form), True


def _auxiliary(ctx, tags):
    """`aux. sein`, `aux. haben/sein`, or "" for haben -- and whether
    anything said which.

    THE MEANING'S OWN AUXILIARY FIRST.  Wiktionary gives it per sense where
    the verb takes both -- aufstehen `to get up [auxiliary sein]` but `to be
    open [auxiliary haben or sein]`, passieren `to happen` sein but `to pass`
    haben -- and lib/getdict.py keeps it as `aux:sein`.  Where the sense says
    nothing the head line's rows answer for the whole verb, and a verb with
    both prints both: fahren, liegen, sitzen and stehen are `aux.
    haben/sein` (sitzen's senses say so themselves -- the south says `ist
    gesessen`), which the annotator trims to the text's.  Nothing is
    inferred from `intransitive`: liegen, sitzen and stehen are intransitive
    and the north makes their perfect with haben.

    NO ROW, THEN THE PERFECT: `hat gefahren` / `ist gefahren`, first words
    only."""
    said = [t[4:] for t in tags if t.startswith("aux:")]
    aux = set()
    for s in said[:1]:
        aux = set(p for p in s.split("/") if p in (HABEN, SEIN))
    if not aux:
        aux = set(r.form.strip() for r in ctx.picks(exact=AUXILIARY, own=True)
                  if r.form.strip() in (HABEN, SEIN))
    if not aux:
        for r in ctx.picks(exact=PERFECT, own=True):
            w = r.form.split()[0] if r.form.split() else ""
            aux.add({"hat": HABEN, "ist": SEIN}.get(w, ""))
        aux.discard("")
    if not aux:
        return "", False
    if aux == {HABEN}:
        return "", True
    if aux == {SEIN}:
        return "aux. sein", True
    return "aux. haben/sein", True


def _split_top(s, sep):
    """`s` split on `sep` where it stands outside <...> and (...)."""
    out, cur, depth = [], [], 0
    for ch in s:
        if ch in "<(":
            depth += 1
        elif ch in ">)" and depth:
            depth -= 1
        if ch == sep and depth == 0:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    out.append("".join(cur))
    return [x.strip() for x in out if x.strip()]


_CASES = {"acc": "acc", "accusative": "acc", "dat": "dat", "dative": "dat",
          "gen": "gen", "genitive": "gen"}
_PREP = re.compile(r":(\w+)(?:\((acc|dat|gen)\)|&(acc|dat|gen))?")


def _governs(ctx, tags):
    """(`+ dat.`, `auf + acc.`, `mit + dat.` or "", what is missing or "").

    FROM THE SENSE'S {{+obj}}, which Wiktionary writes as a small language
    of its own and lib/getdict.py keeps whole: `dat<someone>+:bei(dat)<with>`
    is helfen's -- a dative, then an optional bei with its dative; `:auf(acc)`
    is warten's; `acc<something> + dat<to someone>` a verb of giving.  Each
    `+` is one object, each `/` inside it an alternative, `<...>` a gloss or
    a qualifier.  The first alternative of each object is read (skipping one
    marked `<q:...>`, a register or a region: brauchen's archaic genitive,
    anrufen's Swiss dative), and the FIRST OBJECT WORTH PRINTING is
    printed, which is what docs/lang/de.md's model entries print: helfen
    `+ dat.`, warten `auf + acc.`, sich freuen `über + acc.`.

    NEVER A PLAIN ACCUSATIVE, and a dative only where it is the verb's one
    object: beside an accusative -- `jemandem etwas geben` -- it is the
    ordinary indirect object, and a sense tagged transitive has that
    accusative even where the template lists only the dative (erklären,
    `dat<to someone>`: jemandem etwas erklären).

    A PREPOSITION WITHOUT ITS CASE (`:mit`, `:für<for>`) takes the case the
    preposition always takes (lib/lang/de.verbs.json); one of the nine that
    take either (`:auf`) is printed `auf + …` and its case named as missing,
    because with a verb which one it is -- warten auf + acc., bestehen auf
    + dat. -- is the verb's, and the source did not say.

    NO {{+obj}}, THEN THE PROSE: `[with dative] to resemble` (ähneln) is
    kept as `with-dative`.
    """
    preps = (ctx.data() or {}).get("prepositions") or {}
    fixed = {p: c for c in ("acc", "dat", "gen") for p in preps.get(c) or []}
    both = set(preps.get("both") or [])
    transitive = bool(set(tags) & {"transitive", "ditransitive"})
    objs = [t[4:] for t in tags if t.startswith("obj:")]
    for v in objs[:1]:
        groups = []
        for g in _split_top(v, "+"):
            alts = [re.sub(r"<[^<>]*>", "", a).strip()
                    for a in _split_top(g, "/") if "<q:" not in a]
            if not alts:
                continue
            first = alts[0]
            # A CASE WRITTEN ONCE FOR SEVERAL PREPOSITIONS: kleben's
            # `:an/:auf(acc)` is Wiktionary's "with an or auf (+
            # accusative)", stoßen's `:an/:gegen(acc)` "with an or gegen (+
            # accusative)" -- the case after the last is the case of all.
            # Read as `:an` alone it printed `an + …` and called the case
            # missing on 7 verbs whose case the source had given.
            m = _PREP.fullmatch(first)
            if m and not (m.group(2) or m.group(3)):
                for a in alts[1:]:
                    n = _PREP.fullmatch(a)
                    if n and (n.group(2) or n.group(3)):
                        first = "%s(%s)" % (first, n.group(2) or n.group(3))
                        break
            groups.append(first)
        has_acc = any(_CASES.get(g) == "acc" for g in groups)
        for g in groups:
            case = _CASES.get(g)
            if case == "acc":
                continue
            if case == "dat":
                if has_acc or transitive:
                    continue
                return "+ dat.", ""
            if case == "gen":
                return "+ gen.", ""
            m = _PREP.fullmatch(g)
            if not m:
                continue
            p, c = m.group(1), m.group(2) or m.group(3)
            if p in fixed or p in both:
                if c:
                    return "%s + %s." % (p, c), ""
                if p in fixed:
                    return "%s + %s." % (p, fixed[p]), ""
                return "%s + …" % p, "the case after %s (acc. or dat.)" % p
        return "", ""
    if "with-dative" in tags and not transitive:
        return "+ dat.", ""
    if "with-genitive" in tags:
        return "+ gen.", ""
    return "", ""


# ---------------------------------------------------------------- recipe
def recipe(ctx):
    """The German \\vb this hit offers, as a verbs.Parts, or None (see the
    module docstring for which hits get none)."""
    if (ctx.entry["pos"] or "") != "verb":
        return None
    if ctx.word:
        if (not _reaches(ctx) or _a_noun(ctx) or _stray_imperative(ctx)
                or _helps(ctx)):
            return None
        ctx = _joined(ctx) or ctx
    return _describe(ctx)


def _describe(ctx):
    """The Parts for this entry: its three forms, the chosen sense, and the
    parenthesis in docs/lang/de.md's order -- third person, auxiliary,
    government -- with what the source left out named in `missing`."""
    head = (ctx.entry["headword"] or "").strip()
    past = _own(ctx, PAST, PAST_TABLE)
    part = _participle(ctx)
    if past is None and not part:
        return None
    missing = []
    if past is None:
        missing.append("the preterite")
    if not part:
        missing.append("the past participle")

    senses = _senses(ctx)
    meaning, tags, sich = _choose(ctx, senses)
    lemma = head
    if sich and [w.lower() for w in head.split()[:1]] != ["sich"]:
        lemma = "sich " + head

    extras = []
    third, had = _third(ctx, head, senses)
    if third:
        extras.append(third)
    elif not had:
        missing.append("the third person present (er …)")
    aux, had = _auxiliary(ctx, tags)
    if aux:
        extras.append(aux)
    elif not had:
        missing.append("the auxiliary (haben or sein)")
    gov, lack = _governs(ctx, tags)
    if gov:
        extras.append(gov)
    if lack:
        missing.append(lack)

    return Parts(parts=[(lemma, ctx.head_sound),
                        ((past.form.strip() if past else ""), ""),
                        (part, "")],
                 meaning=meaning, extras=extras, missing=missing)
