"""Hindi: the \\vb a dictionary hit for a verb offers.

    \\vb{करना}{karnā}{कर}{kar}{किया}{kiyā}{to do (+\\pw{ने})}
    \\vb{जाना}{jānā}{जा}{jā}{गया}{gayā}{to go}
    \\vb{समझना}{samajhnā}{समझ}{samajh}{समझा}{samjhā}{to understand (±\\pw{ने})}
    \\vb{करना}{karnā}{कर}{kar}{किया}{kiyā}{(+\\pw{ने})}   in `काम कर रहा था`,
                                        with the \\bw for काम named in `missing`

docs/lang/hi.md says what goes in, and nothing here adds to it: the
infinitive, the stem, the perfective masculine singular, each with its
transliteration; the meaning; and after it, in one parenthesis, whether the
subject takes ने in the perfective -- (+ने), (±ने), or nothing.

WHERE EACH FORM COMES FROM, all of it rows the source wrote:

    infinitive   the headword, said as the LEMMA is said (ctx.head_sound),
                 never as the word the chunk has
    stem         the table's `stem` row (1 582 of the 1 633 verb pages have
                 a table); else the infinitive less -ना, which is what
                 docs/lang/hi.md says a stem is -- and what the table's own
                 row is, in 1 575 of 1 582 (the 7 others are echo pairs,
                 घूमना-फिरना is घूम-फिर, which only the row gets right)
    perfective   the table's `direct masculine perfective singular` row;
                 else, for जाना alone in practice, the pointer page `masculine,
                 participle, perfective, singular` (गया has a page; जाना has
                 no table).  NEVER made from the stem: the rule reproduces
                 1 047 of the 1 056 single-word tables and misses exactly
                 the irregulars a reader needs (किया दिया लिया हुआ -- and
                 गया, whose verb has no table to test) and the five echo
                 pairs, and its sound would be wrong where the table's is
                 right -- समझा is samjhā, not samajh + ā.  A verb with
                 neither is named in `missing`.
    ने           lib/lang/hi.verbs.json first, a hand-kept list; then the
                 dictionary's transitivity, the hi-verb head code (entry.head
                 {"tr": ...}) or, where the head has none, the senses' own
                 labels.  See _ne for the measurement that ordered them.

THE SOUNDS ARE RESPELT, NOT GUESSED.  Wiktionary romanises Hindi with a
tilde for a nasal vowel (hãsnā, mẽ, ha͠i), an acute r for ऋ and ṣ for ष;
this series writes haṁsnā, meṁ, haiṁ, ri and ś (docs/lang/hi.md,
Transliteration).  The schwa -- the thing a table's sound is FOR -- is
Wiktionary's already (samajhnā, samjhā, niklā), and every other letter maps
one to one; _sound is that map and nothing else.

A VERB THAT IS NOT DOING A VERB'S JOB GETS NO \\vb.  The chunk is read for
four words a lookup meets one at a time: the vector of a compound (लिया in
रख लिया), the progressive (रहा in कर रहा था), the tense auxiliary (था in रहा
था) -- all three offered as the \\dw they always were, because
docs/lang/hi.md glosses what they add and never their dictionary meaning --
and the light verb of a conjunct (करना in काम करना), which gets its \\vb with
the meaning left to the \\bw.  The chunk is read only for a verb on one of
those lists, so every other verb is built once per entry and not once per
chunk (verbs.Ctx.text).

Standard library only: the server imports it.
"""
import json
import re
import unicodedata

import lookup                                                  # noqa: E402
import translit                                                # noqa: E402
from verbs import (Parts, one_equivalent, split_tags,          # noqa: E402
                   tl, trim_meaning)

INFINITIVE = "ना"                                    # -ना
# the cells of a hi-conj table this recipe prints, by their exact notes
STEM = "stem"
PERFECTIVE = "direct masculine perfective singular"
# a pointer page's perfective: `masculine, participle, perfective, singular`
# on गया.  Required tags, and the ones that make a row something else -- the
# `oblique` one is not decoration: जाना's pointers include a bogus `जाये`
# tagged `masculine, oblique, participle, perfective, singular`.
PTR_PERFECTIVE = frozenset(("masculine", "perfective", "singular"))
PTR_NOT = frozenset(("oblique", "feminine", "plural", "adjectival"))

# The words a row's tags use for a participle or a finite past: what the
# word before a form of होना has to be for that form to be the auxiliary.
# `imperfect` is a tag of its own (था), not `perfect` with a prefix.
PARTICIPLE = frozenset(("participle", "perfective", "habitual", "perfect",
                        "progressive"))

# ------------------------------------------------------------- the sounds
# Wiktionary's Hindi romanisation -> docs/lang/hi.md's.  Worked on NFD, where
# a long nasal vowel is the vowel + macron + tilde and ṣ is s + dot below, so
# one rule covers a vowel with or without its length mark.  Counted over
# every romanised row of the rebuilt dict/hi.db: 36 586 long nasal i, 33 586
# nasal o, 27 318 long nasal u, 19 943 nasal ai (a double tilde over the
# pair), 19 593 nasal e, 2 526 long nasal a; the acute r and ṣ on the
# Sanskrit layer (घृणा, विश्लेषण).  Nothing else in them differs from the
# scheme: ṛ is ड़ in both, ṅ ñ ṇ are written out before a stop in both, and
# q x ġ z f are the nukta letters in both.
_NASAL = "m\u0307"                           # ṁ, decomposed
_DIPHTHONG = re.compile("([aeiou])\u0360([aeiou])")     # a͠i a͠u
_TILDE = re.compile("([aeiouAEIOU]\u0304?)\u0303")     # ã ā̃ ẽ õ ī̃ ū̃
_RESPELL = (("r\u0301", "ri"), ("R\u0301", "Ri"),       # ŕ is ऋ
            ("s\u0323", "s\u0301"), ("S\u0323", "S\u0301"))  # ṣ is ष, and ś


def _sound(s):
    """A romanisation from the dictionary, as this series writes it: the
    edition's own tidying first (translit.tidy_roman; lib/lang/hi.ipa.json,
    where it exists), then the respellings above.  Running it on a sound
    already respelt changes nothing, so it cannot fight a hi.ipa.json that
    learns the same map."""
    s = translit.tidy_roman("hi", (s or "").strip())
    if not s:
        return ""
    d = unicodedata.normalize("NFD", s)
    d = _DIPHTHONG.sub(lambda m: m.group(1) + m.group(2) + _NASAL, d)
    d = _TILDE.sub(lambda m: m.group(1) + _NASAL, d)
    for a, b in _RESPELL:
        d = d.replace(a, b)
    return unicodedata.normalize("NFC", d)


_CONSONANT = re.compile(r"[b-df-hj-np-tv-z]$", re.I)


def _cut_stem(sound):
    """The stem's sound where the table has no stem row: the infinitive's,
    less -nā, less the final schwa that is left -- "a word-final schwa always
    is [dropped]" (docs/lang/hi.md).  jānā is jā; janmanā is janm, not
    janma.  "" when the infinitive's sound does not end in -nā."""
    if not sound.endswith("nā"):
        return ""
    s = sound[:-2]
    if len(s) > 1 and s.endswith("a") and _CONSONANT.search(s[:-1]):
        s = s[:-1]
    return s


# ------------------------------------------------------------- the rows
def _rows_of(ctx, eid):
    """Another entry's rows, as ctx.rows gives this one's: a conjunct's page
    is reached, and the \\vb is its light verb's, from the light verb's own
    table."""
    return ctx.rows_of(eid)


def _first(rows, test):
    for f in rows:
        if test(f):
            return f
    return None


def _forms(ctx, eid, headword, sound, rows):
    """((stem, sound), (perfective, sound), missing) for one verb entry."""
    names = list(ctx.L.vb_forms or ("infinitive", "stem", "perfective (m. sg.)"))
    missing = []
    # THE ENTRY'S OWN ROW, by its exact note.  Pointer rows are linked to the
    # first verb entry with the headword they name, so a homograph collects
    # its twin's: 22 headwords have two or three verb pages (कसना, खिलाना,
    # घटना, बिलाना...), and only an entry's own rows are surely its own.
    stem = _first(rows, lambda f: f.own and f.note == STEM)
    if stem is not None and stem.form.strip():
        st = (stem.form.strip(), _sound(stem.roman))
    else:
        st = (headword[:-len(INFINITIVE)], _cut_stem(sound))
    if not st[1]:
        missing.append("the sound of the %s" % names[1])

    perf = _first(rows, lambda f: f.own and f.note == PERFECTIVE)
    if perf is None and _only_verb(ctx, headword, eid):
        # NO TABLE -- जाना, whose page has none (its own rows are the
        # headword and its `romanization`) -- and the only verb of that
        # spelling, so the pointers are surely its own: गया's page says
        # `masculine, participle, perfective, singular`, and `gayā`.
        perf = _first(rows, lambda f: not f.own and PTR_PERFECTIVE <= f.tags
                      and not (PTR_NOT & f.tags) and " " not in f.form.strip())
    if perf is None or not perf.form.strip():
        missing.append("the %s (the dictionary has no table for this verb)"
                       % names[2])
        pf = ("", "")
    else:
        pf = (perf.form.strip(), _sound(perf.roman))
        if not pf[1]:
            missing.append("the sound of the %s" % names[2])
    return st, pf, missing


def _only_verb(ctx, headword, eid):
    got = ctx.conn.execute(
        "SELECT id FROM entry WHERE headword = ? AND pos = 'verb' LIMIT 2",
        (headword,)).fetchall()
    return [r[0] for r in got] == [eid]


# ---------------------------------------------------------------- the ने
# THE HAND-KEPT LIST FIRST, AND THE DICTIONARY ONLY AFTER IT, because ने is
# not transitivity and the dictionary's codes are missing where they matter
# most.  Measured on the rebuilt dict/hi.db against common verbs scored by
# hand (the numbers are in lib/lang/hi.verbs.json, `ne`): the head code is
# absent on करना जाना आना लेना खाना पीना, and wrong on लाना (tr., and never
# ने), लिखना and सुनना (intr., and always ने).  Where the head says nothing
# the senses' own labels are read -- 29 single-word verbs have them and no
# code -- and a verb whose senses disagree (फेंकना, हारना) goes either way.
_TR = {"tr.": "+", "intr.": "", "tr./intr.": "±"}
_TRANSITIVE = frozenset(("transitive", "ditransitive"))


def _listed(D, headword):
    """'+', '±' or '' from the hand-kept list, or None where it is silent."""
    ne = D.get("ne") or {}
    for key, mark in (("never", ""), ("either", "±"), ("takes", "+")):
        if headword in (ne.get(key) or ()):
            return mark
    return None


def _from_dict(head, sense_tags):
    tr = _TR.get((head or {}).get("tr") or "")
    if tr is not None:
        return tr
    seen = set()
    for tags in sense_tags:
        seen |= set(tags) & (_TRANSITIVE | {"intransitive", "ambitransitive"})
    if not seen:
        return None
    t = bool(seen & _TRANSITIVE)
    i = "intransitive" in seen
    if "ambitransitive" in seen or (t and i):
        return "±"
    return "+" if t else ""


def _ne(ctx, D, headword, phrase="", head=None, sense_tags=None):
    """The mark, or None where nothing says.  A conjunct is asked for by its
    whole headword first (दिखाई देना: dative subject, no ने, where देना takes
    it) and then as its light verb.  NOT by the conjunct's own dictionary
    code: फ़ोन करना is coded intransitive and पता चलना transitive, and
    उसने फ़ोन किया, मुझे पता चला say the opposite of both."""
    if phrase:
        got = _listed(D, phrase)
        if got is not None:
            return got
    got = _listed(D, headword)
    if got is not None:
        return got
    return _from_dict(ctx.head if head is None else head,
                      ctx.sense_tags if sense_tags is None else sense_tags)


def _mark(ne):
    return ["%s%s" % (ne, tl("ने"))] if ne else []       # ने


# ------------------------------------------------------------- the meaning
# A SENSE THAT ONLY POINTS AT ANOTHER WORD is not a meaning: खरीदना is
# "nuqtaless form of ख़रीदना (xarīdnā)" and nothing else, and it is how the
# verb to buy is written in most printed Hindi.  13 single-word verbs open
# their first sense so (synonym of, nuqtaless form of).  The meaning is what
# the sense says after the pointer where it says more -- गड़ाना is "synonym
# of गाड़ना (gāṛnā); to pierce, bury" -- else the one the pointer gives in
# quotes -- चोरना is "synonym of चुराना (curānā, “to steal”)" -- else the
# first ranked sense of the verb it points at.
_DEVA = "\u0900-\u097f\u200c\u200d"          # Devanagari and its joiners
_POINTER = re.compile(r"^\s*(?:synonym|(?:[a-z]+\s+)?(?:form|spelling))\s+of\s+"
                      r"([%s ]+?)\s*(?:\((.*)\))?\s*[.:]?\s*$" % _DEVA)
_QUOTED = re.compile("“([^”]+)”")
_DEVA_RUN = re.compile(r"[%s]+(?:\s+[%s]+)*" % (_DEVA, _DEVA))


def _ranked(sense, sense_tags):
    senses = [s for s in (sense or "").split("\n") if s.strip()]
    ranked = lookup.rank_senses(senses, (sense_tags or "").split("\n"))
    return [r[0] for r in ranked]


def _first_sense(ctx):
    got = [s for s in (ctx.hit.get("senses") or []) if (s or "").strip()]
    return got[0] if got else next(iter(_ranked(ctx.entry["sense"],
                                                ctx.entry["sense_tags"])), "")


def _split(sense):
    """(the sense up to its first semicolon outside the brackets, the rest)."""
    depth = 0
    for i, ch in enumerate(sense):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif ch == ";" and depth == 0:
            return sense[:i], sense[i + 1:]
    return sense, ""


def _pointed(ctx, sense):
    """(meaning, missing) for a sense that is a pointer, or None."""
    head, rest = _split(sense or "")
    got = _POINTER.match(head)
    if not got:
        return None
    if rest.strip() and not _POINTER.match(_split(rest)[0]):
        return trim_meaning(rest), []
    quoted = _QUOTED.search(got.group(2) or "")
    if quoted:
        return trim_meaning(quoted.group(1)), []
    row = _verb_page(ctx, got.group(1).strip())
    ranked = _ranked(row["sense"], row["sense_tags"]) if row else []
    if ranked and not _POINTER.match(_split(ranked[0])[0]):
        return trim_meaning(ranked[0]), []
    return "", ["the meaning (the dictionary only points at %s)"
                % got.group(1).strip()]


def _meaning(ctx):
    """(meaning, what is missing about it).  One equivalent, as
    docs/lang/hi.md asks -- "to do", not "to do, to perform, to execute" --
    and a word of Hindi inside it marked as one (\\pw in a book)."""
    if (ctx.gloss or "").strip().lower() != "en":
        return "", []
    got = _pointed(ctx, _first_sense(ctx))
    m, why = got if got is not None else (ctx.meaning, [])
    m = one_equivalent(m)
    return _DEVA_RUN.sub(lambda x: tl(x.group(0)), m), why


# ------------------------------------------------------------- the chunk
_ASKED = {}


def _cached(ctx, kind, word, ask):
    """One question about one word of the chunk, asked once per dictionary
    file: the reader looks ahead ten chunks, and कर is in most of them."""
    key = (id(ctx.conn), lookup._stamp(lookup.path_for(ctx.code)), kind, word)
    if key not in _ASKED:
        if len(_ASKED) > 20000:
            _ASKED.clear()
        _ASKED[key] = ask()
    return _ASKED[key]


def _is_stem(ctx, w):
    """Is `w` some verb's bare stem?  Its `stem` row says so; so does -ना
    making a verb of it, which is the only way to know जा: जाना has no table."""
    def ask():
        return ctx.conn.execute(
            "SELECT 1 FROM form f JOIN entry e ON e.id = f.entry_id "
            "WHERE f.form = ? AND f.note = ? AND e.pos = 'verb' LIMIT 1",
            (w, STEM)).fetchone() is not None or ctx.conn.execute(
            "SELECT 1 FROM entry WHERE headword = ? AND pos = 'verb' LIMIT 1",
            (w + INFINITIVE,)).fetchone() is not None
    return bool(w) and _cached(ctx, "stem", w, ask)


def _tags_as_verb(ctx, w):
    """Every tag set `w` has as a form of some verb."""
    def ask():
        return [split_tags(r[0]) for r in ctx.conn.execute(
            "SELECT f.note FROM form f JOIN entry e ON e.id = f.entry_id "
            "WHERE f.form = ? AND e.pos = 'verb'", (w,))]
    return _cached(ctx, "tags", w, ask) if w else []


def _is_participle(ctx, w):
    return any(t & PARTICIPLE for t in _tags_as_verb(ctx, w))


def _is_oblique_infinitive(ctx, w):
    return w.endswith("ने") and any(               # -ने
        {"infinitive", "oblique"} <= t for t in _tags_as_verb(ctx, w))


def _verb_page(ctx, headword):
    """The first verb page with this headword: id headword translit sense
    sense_tags head, the last two '' in a dictionary built before them."""
    cols = ["id", "headword", "translit", "sense"] + [
        c if lookup._has_col(ctx.conn, c) else "'' AS %s" % c
        for c in ("sense_tags", "head")]
    return ctx.conn.execute(
        "SELECT %s FROM entry WHERE headword = ? AND pos = 'verb' "
        "ORDER BY id LIMIT 1" % ", ".join(cols), (headword,)).fetchone()


def _lists(D):
    vec = D.get("vectors") or {}
    return (set((D.get("light") or {}).get("verbs") or ()),
            set(vec.get("verbs") or ()),
            set(vec.get("after_oblique_infinitive") or ()),
            set((D.get("auxiliary") or {}).get("forms") or ()),
            set((D.get("particles") or {}).get("words") or ()))


def _nfc(s):
    return unicodedata.normalize("NFC", s or "")


def _roles(ctx, D, headword, stem_form):
    """What the chunk makes of this verb, wherever the word stands in it:
    'helper' (a vector, the progressive, the auxiliary: no \\vb),
    ('conjunct', noun, its page) or 'verb'.

    Where the word stands twice and the two disagree it is a verb: the
    full entry says the most, and a helper's \\dw is one click away."""
    lights, vectors, after_inf, aux_forms, skip = _lists(D)
    # COMPOSED, as the dictionary is.  A nukta letter has a precomposed code
    # point (U+0958-U+095F) that NFC takes apart -- they are composition
    # exclusions -- and dict/hi.db holds not one of them in 525 159 form
    # rows; a chunk typed with them must meet its neighbours the same way.
    word = _nfc(ctx.word)
    if not word:
        return "verb"                 # built for no word of any chunk
    light = headword in lights
    vector = headword in vectors
    after = headword in after_inf
    aux = headword == "होना" and word in aux_forms      # होना
    if not (light or vector or after or aux):
        return "verb"                 # the chunk is not read: see the docstring
    words = [_nfc(lookup._bare(w, ctx.L)) for w in ctx.L.split_words(ctx.text)]
    roles = []
    for i, w in enumerate(words):
        if w != word:
            continue
        j = i - 1
        while j >= 0 and words[j] in skip:
            j -= 1
        prev = words[j] if j >= 0 else ""
        role = "verb"
        if vector and _is_stem(ctx, prev) and (
                word != _nfc(stem_form)
                # THE WORD IS ITSELF A BARE STEM.  In बस आ गई it is the main
                # verb (आ, came) whatever बस could be; in छोड़ दे it is the
                # vector in its intimate imperative, and the dictionary says
                # which by having छोड़ देना as a page.
                or _verb_page(ctx, "%s %s" % (prev, headword)) is not None):
            role = "helper"
        elif after and _is_oblique_infinitive(ctx, prev):
            role = "helper"
        elif aux and _is_participle(ctx, prev):
            role = "helper"
        elif light and prev:
            # the longest page first: पेट साफ़ करना before साफ़ करना
            for n in (3, 2, 1):
                if j - n + 1 < 0:
                    continue
                noun = words[j - n + 1:j + 1]
                row = _verb_page(ctx, " ".join(noun + [headword]))
                if row is not None:
                    role = ("conjunct", " ".join(noun), row)
                    break
        roles.append(role)
    if roles and all(r == roles[0] for r in roles):
        return roles[0]
    return "verb"


def _compound_parts(ctx, noun, row):
    """The conjunct as the entry it is, for the button that puts it in whole:
    काम करना kām karnā, the word the light verb carries, and what the pair
    means.

    A CONJUNCT, NOT A COMPOUND.  docs/lang/hi.md keeps the two apart, and so
    does this: कर लिया, a stem and a vector, is the compound verb, and it
    gets no \\vb at all (`_roles` calls it a helper).  The name here is what
    the door calls the button, so it has to be the language's own word.

    The noun's own sound is the head of the conjunct's romanisation, the way
    Persian takes it from the compound's (lib/verbs/fa.py): kām karnā gives
    kām for काम.  docs/lang/hi.md's own \\bw glosses the noun with its gender
    (`m. work`), which no row read here says; what goes in is the conjunct's
    meaning, the one this row has always named, and the gender is the
    annotator's to add -- as every draft this sidebar proposes is theirs to
    correct."""
    said = _sound(row["translit"])
    words = said.split(" ")
    n = len(noun.split())
    mean = ""
    if (ctx.gloss or "").strip().lower() == "en":
        ranked = _ranked(row["sense"], row["sense_tags"])
        if ranked:
            mean = one_equivalent(trim_meaning(ranked[0]))
    return {"name": "conjunct verb", "whole": row["headword"],
            "whole_sound": said, "mean": mean, "word": noun,
            "word_sound": " ".join(words[:n]) if len(words) > n else ""}


def _bw_note(ctx, noun, row):
    """The \\bw a conjunct needs after the light verb's \\vb, as one item of
    `missing`: the word, and the conjunct's meaning where the gloss is
    English.  No backslash -- the core takes every one out of `missing` --
    and no comma, which is what the editor joins the items with."""
    said = _compound_parts(ctx, noun, row)["mean"]
    return ("bw for %s after it%s" % (
        noun, (": %s is %s" % (row["headword"], said)) if said else "")
    ).replace(",", ";")


# ------------------------------------------------------------ the recipe
def recipe(ctx):
    e = ctx.entry
    if (e["pos"] or "") != "verb":
        return None                                  # खाना the meal, आना the anna
    headword = (e["headword"] or "").strip()
    # THE INFINITIVE IS THE TEST OF A VERB, not the part of speech alone: 8
    # pos=verb pages are not infinitives -- खेलकर is "conjunctive of खेलना",
    # चर is "variable", होए "might be" -- and have nothing a \vb could print.
    if not headword.endswith(INFINITIVE) or headword == INFINITIVE:
        return None
    D = ctx.data()
    words = headword.split()
    if len(words) > 1:
        return _phrase(ctx, D, headword, words)

    names = list(ctx.L.vb_forms or ("infinitive",))
    sound = _sound(ctx.head_sound)
    stem, perf, missing = _forms(ctx, e["id"], headword, sound, ctx.rows)
    if not sound:
        missing.insert(0, "the sound of the %s" % names[0])
    role = _roles(ctx, D, headword, stem[0])
    if role == "helper":
        return None
    if role != "verb":
        _kind, noun, row = role
        # A CONJUNCT: the light verb's own \vb, the meaning left to the \bw
        # (docs/lang/hi.md), the ने the conjunct's -- which is its light
        # verb's, except where the list says otherwise for the whole.
        return Parts(parts=[(headword, sound), stem, perf], meaning="",
                     extras=_mark(_ne(ctx, D, headword, phrase=row["headword"])),
                     missing=missing + [_bw_note(ctx, noun, row)],
                     compound=_compound_parts(ctx, noun, row))
    meaning, why = _meaning(ctx)
    ne = _ne(ctx, D, headword)
    if ne is None:
        missing.append("whether the subject takes ने in the "
                       "perfective (+ने; ±ने; or nothing)")
    return Parts(parts=[(headword, sound), stem, perf], meaning=meaning,
                 extras=_mark(ne), missing=missing + why)


def _phrase(ctx, D, headword, words):
    """A multiword page -- इंतज़ार करना, याद आना -- reached as itself.

    The lookup reads a chunk a word at a time and never reaches one; a
    caller that hands one in gets what the chunk would have got: the LIGHT
    verb's \\vb from the light verb's own table (the page's table has
    इंतज़ार कर and इंतज़ार किया, which is not what a \\vb prints, and a rule
    applied to पसंद होना would make पसंद होया), no meaning, and the \\bw
    named.  A compound page -- भूल जाना, छोड़ देना: a stem and a vector --
    or an idiom ending in anything else is not a conjunct, and gets none."""
    lights, vectors, _after, _aux, _skip = _lists(D)
    light = words[-1]
    if light not in lights or (light in vectors and _is_stem(ctx, words[-2])):
        return None
    row = _verb_page(ctx, light)
    if row is None:
        return None
    sound = _sound(row["translit"])
    stem, perf, missing = _forms(ctx, row["id"], light, sound,
                                 _rows_of(ctx, row["id"]))
    try:
        head = json.loads(row["head"] or "{}")
    except (ValueError, TypeError):
        head = {}
    tags = [set(t.strip() for t in line.split(",") if t.strip())
            for line in (row["sense_tags"] or "").split("\n")]
    ne = _ne(ctx, D, light, phrase=headword,
             head=head if isinstance(head, dict) else {}, sense_tags=tags)
    noun = " ".join(words[:-1])
    missing.append(_bw_note(ctx, noun, ctx.entry))
    return Parts(parts=[(light, sound), stem, perf], meaning="",
                 extras=_mark(ne), missing=missing,
                 compound=_compound_parts(ctx, noun, ctx.entry))
