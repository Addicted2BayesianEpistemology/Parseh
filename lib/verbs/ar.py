#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Arabic's \\vb: the perfect and its form, the imperfect, the masdar.

    \\vb{وَصَلَ}{waṣala (I)}{يَصِلُ}{yaṣilu}{صِلَة}{ṣila}{to arrive at (+ \\pw{إِلَى})}

docs/lang/ar.md sets the slots.  The PERFECT, third person masculine
singular, fully vowelled, its sound carrying the verb's FORM in brackets:
kataba (I), arāda (IV), tarjama (Iq).  The IMPERFECT, third person
masculine singular indicative: yaktubu, yaqūlu, yarā.  The MASDAR, one,
never the perfect a second time, and nothing at all -- the pair blank, which
the edition does not print -- for a verb that has none.  After the meaning,
one extra: the preposition the verb governs, `+ إِلَى`, where the source
names one for the sense the meaning shows.

WHERE EACH COMES FROM.  A Wiktionary verb page has a head line its editors
wrote -- `وَصَلَ • (waṣala) I (non-past يَصِلُ (yaṣilu), verbal noun صِلَة
(ṣila) or وُصُول (wuṣūl))` -- and lib/getdict.py keeps it as form rows of one
tag set each, ahead of the conjugation table:

    وَصَلَ    canonical form-i     the perfect, vowelled, and its form
    waṣala    romanization         how the perfect is said
    يَصِلُ    non-past             the imperfect, with its roman
    صِلَة     noun-from-verb       each masdar, with its roman, in the
    وُصُول    noun-from-verb       order the page gives them

Every slot is one of those rows and nothing else; the preposition is a tag
on the sense (`obj::إِلَى/acc<somewhere>`, Wiktionary's +obj template, kept
by getdict._sense_facts).  Over the whole extract -- 7233 verb entries in
the dictionary getdict builds from it -- 7152 get a \\vb, every one with its
imperfect, 7116 with a masdar, 543 with a preposition.  The 81 without are
the verbs docs/lang/ar.md wants as a \\dw -- لَيْسَ (perfect only, "not to
be"), لا يزال, the Judeo-Arabic spellings, the interjections filed as verbs
(هَاتِ, تَعَالَ): nothing on the page names a perfect's form -- and two
pages whose head lines wiktextract left in pieces (see _heads).

WHAT IS LEFT OUT, AND WHY.  The root: the doc gives it for a noun and not
for a verb.  The imperative, the passive, the participles: a lookup note
names them when the text has one.  The second imperfect some verbs allow
(عَنَدَ: يَعْنُدُ and يَعْنِدُ, 216 heads): a free variant of the same verb,
and the doc wants one, so the first.  Transitivity: the doc says not.
"""
import re
import unicodedata

import lookup
import translit
import verbs

# THE PERFECT IS THE ROW THAT NAMES ITS FORM, and only that row.  Tagged
# `canonical` alone there are 133 rows and nearly all are not perfects:
# parser junk with the head line's words in it (`first-person non-past
# لَبِبْتُ`), and the head of a verb that has no forms to give -- لَيْسَ,
# whose page is a `head` template with a perfect-only table and no
# non-past, and which docs/lang/ar.md glosses as \dw{لَيْسَ}{laysa} "is not".
# With its form tag the row is the vowelled perfect on 7143 of 7233 verb
# entries: form-i to form-xiii and the quadriliterals form-iq to form-ivq.
_FORM = re.compile(r"form-([ivx]+)(q?)")

# ...AND THE ROW THAT SAYS ITS FORM IN ITS TEXT.  On 15 pages wiktextract
# left the head line's numeral inside the form and no form tag on it:
# أَبْقَى "to keep" is the row `أَبْقَى IV .`, تَعَايَشَ `تَعَايَشَ VI .`,
# اِرْتَقَى `اِرْتَقَى VIII .`.  On four more it ran several heads into one
# row, parted by the numeral: `كَمَنَ I كَمِنَ`, `يَتِمَ I يَتُمَ I يَتَمَ`.
# The perfect and its form are both there in the source's own words; they
# are read, not guessed.  (getdict's case-folded copy of each, `أَبْقَى iv
# .`, is no row of the page and is passed over.)
_NUMERAL = re.compile(r"(?:X{0,1}(?:IX|IV|V?I{0,3})|XI{1,3}|XIV|XV)q?")
_LOWER = re.compile(r"[ivx]+q?")

# THE HEAD LINE'S ROWS, which is where a head's imperfect and masdar are.
# A head ends at the next perfect, or at the first row that is none of
# these, which is where the conjugation table begins -- and the table must
# not be read as the head's: its cells carry `non-past` too, among six other
# tags, and it is the SAME table for every head of the entry.  Measured on
# the head lines of the extract: romanization, non-past, noun-from-verb, an
# `alternative` perfect (ذَرَى beside ذَرَا, 98), the first person of a
# doubled verb (أَبِبْتُ, 60), and nothing else more than twice.
_HEAD_LINE = frozenset(("romanization", "non-past", "noun-from-verb",
                        "alternative", "archaic", "rare", "obsolete", "hard",
                        "first-person", "past", "singular"))

_TATWEEL = "ـ"


def _nfc(s):
    """One spelling for one vowelling: a shadda and its fatha reach the page
    in either order, and NFC puts them in one."""
    return unicodedata.normalize("NFC", s or "")


def _form_number(f):
    """The verb's form as the edition writes it -- I, IV, XIII, Iq, IVq --
    from the perfect's own form tag, or ''."""
    if not f.own or len(f.tags) != 2 or "canonical" not in f.tags:
        return ""
    for t in f.tags:
        m = _FORM.fullmatch(t)
        if m:
            return m.group(1).upper() + m.group(2)
    return ""


def _perfects(f):
    """([the perfects this row gives], their form), or ([], '') for a row
    that is not a perfect: one perfect for a clean row, several where the
    parser ran the heads of a page into one (see _NUMERAL)."""
    if not f.own or "canonical" not in f.tags:
        return [], ""
    tag = _form_number(f)
    if len(f.tags) > 1 and not tag:
        return [], ""                   # `canonical masculine`: a noun's head
    toks = f.form.split()
    if any(_LOWER.fullmatch(t) for t in toks):
        return [], ""                   # getdict's case-folded copy
    nums = [t for t in toks if t and _NUMERAL.fullmatch(t)]
    if not nums:
        return ([f.form], tag) if tag else ([], "")
    if len(set(nums)) != 1 or (tag and nums[0] != tag):
        return [], ""
    out, cur = [], []
    for t in toks + [nums[0]]:
        if t == nums[0]:
            if cur:
                out.append(" ".join(cur))
            cur = []
        elif t != ".":
            cur.append(t)
    return out, nums[0]


def _heads(ctx):
    """The verbs of this entry, in the source's order: [(the perfect's row,
    its form, [the rows of its head line])].

    MOSTLY ONE, AND SOMETIMES THREE.  71 entries hold two heads and 10 hold
    three, because Wiktionary writes one head per vowelling of the same verb
    under one list of senses: رشد is رَشَدَ yaršudu rušd AND رَشِدَ yaršadu
    rašad.  Read as one head, the second perfect's imperfect and masdar
    would follow the first perfect.  getdict dropped the head numbers, so
    the heads are found again where each one starts -- at its perfect.
    """
    region = []
    for f in ctx.rows:
        if f.own and f.tags and (f.tags <= _HEAD_LINE or "canonical" in f.tags):
            region.append(f)
        elif any(_perfects(x)[0] for x in region):
            break                       # the conjugation table begins
    cans = [i for i, f in enumerate(region) if _perfects(f)[0]]
    if not cans:
        return []

    def np(f):
        return f.tags == {"non-past"}

    def junk(f):
        return "canonical" in f.tags and not _perfects(f)[0]
    # THE IMPERFECT IS NOT ALWAYS AFTER ITS PERFECT.  Where the head line
    # has more in it than the three forms -- `passive-only`, the first
    # person of a doubled verb -- wiktextract writes the non-past FIRST:
    # صُدِرَ's page is يُصْدَرُ, صُدِرَ, ṣudira, صَدْر, and لَبَّ's has two
    # `canonical` rows of head-line words in the middle.  Read after the
    # perfect only, 96 heads came out with no imperfect.  So the rows before
    # a perfect are its own, and on an entry of several heads the non-past
    # run that closes one head's rows AFTER its masdar opens the next head.
    leads = [region[:cans[0]]] + [[] for _ in cans[1:]]
    segs = []
    for k, i in enumerate(cans):
        seg = region[i + 1:cans[k + 1]] if k + 1 < len(cans) else region[i + 1:]
        if k + 1 < len(cans):
            j = len(seg)
            while j and (np(seg[j - 1]) or junk(seg[j - 1])):
                j -= 1
            vn = any(f.tags == {"noun-from-verb"} for f in seg[:j])
            if vn and any(np(f) for f in seg[j:]):
                leads[k + 1], seg = seg[j:], seg[:j]
        segs.append(seg)
    out = []
    for k, i in enumerate(cans):
        perfs, num = _perfects(region[i])
        rows = [f for f in leads[k] + segs[k] if not junk(f)]
        if len(perfs) == 1:
            out.append((region[i]._replace(form=perfs[0]), num, rows))
            continue
        # SEVERAL PERFECTS IN ONE ROW, and after it their head lines one
        # after the other, each opening on its romanisation: كَمَنَ I كَمِنَ
        # is kamana, يَكْمُنُ, كُمُون, then kamina, يَكْمَنُ.  Paired only when
        # there is one romanisation per perfect, and where there is not, the
        # page's head lines are in pieces and NOTHING on it is paired: خرف
        # "to be senile" has `خَرِفَ I خَرَفَ` with no rows after it, then
        # a clean-looking خَرُفَ followed by ḵarifa -- the first perfect's
        # sound -- and read head by head it printed خَرُفَ ḫarifa.  A \dw is
        # offered instead, as for any verb the recipe cannot describe.
        at = [n for n, f in enumerate(rows) if f.tags == {"romanization"}]
        if len(at) != len(perfs) or (at and at[0] != 0):
            return []
        for n, p in enumerate(perfs):
            out.append((region[i]._replace(form=p), num,
                        rows[at[n]:at[n + 1] if n + 1 < len(at) else len(rows)]))
    return out


def _which(ctx, heads):
    """Which of the entry's heads the chunk has.

    A VOWELLED WORD SAYS, AND A BARE ONE CANNOT.  يَبْعَدُ is بَعِدَ's
    imperfect and no row of بَعُدَ's, and in a book, whose text is fully
    vowelled, that settles it.  So does a cell of the conjugation table,
    once it is known whose table the cell is in: the tables follow the head
    lines in the heads' order, each opening on its active participle --
    بعد has بَعِيد at the head of the first and بَاعِد of the second -- and
    where there is one such row per head the tables are told apart by them.
    Where the word does not say -- a video, pass 3, a participle both
    tables share -- the first head is taken, and it is not a guess about
    the verb: the heads of one entry are the vowellings of ONE verb under
    one list of senses, and they always share their form (measured: not one
    of the 81 entries with several heads mixes two forms).
    """
    if len(heads) == 1:
        return heads[0]
    w = _nfc(ctx.word)
    if not w or w == _nfc(verbs.strip_marks(w, ctx.L)):
        return heads[0]
    mine = [h for h in heads
            if w == _nfc(h[0].form) or any(w == _nfc(f.form) for f in h[2])]
    if len(mine) == 1:
        return mine[0]
    last = max(f.rowid for f in heads[-1][2] + [heads[-1][0]])
    starts = [f.rowid for f in ctx.rows
              if f.rowid > last and f.own and f.tags == {"active", "participle"}]
    if len(starts) == len(heads):
        at = [f.rowid for f in ctx.rows if f.rowid >= starts[0] and _nfc(f.form) == w]
        got = {sum(1 for s in starts[1:] if s <= r) for r in at}
        if len(got) == 1:
            return heads[got.pop()]
    return heads[0]


def _roman(ctx, s):
    """The source's romanisation as docs/lang/ar.md writes it.

    translit.tidy_roman first, which is where the language's own rule would
    live (lib/lang/ar.ipa.json: there is none yet, and it changes nothing),
    then ar.verbs.json's table: ʔ ʕ ḵ ḡ are ʾ ʿ ḫ ġ, and no hamza starts a
    word.  A fixed respelling of what the source wrote, the same letter for
    the same letter every time -- not a reading of the Arabic, which is the
    one thing this file must not invent.  Applied twice it changes nothing,
    so a tidy_roman that learns the same rule later costs nothing here.
    """
    d = ctx.data()
    s = translit.tidy_roman(ctx.code, s or "")
    for a, b in (d.get("roman") or {}).items():
        s = s.replace(a, b)
    lead = d.get("drop_initial") or ""
    if lead:
        s = re.sub(r"(^|\s)%s" % re.escape(lead), r"\1", s)
    return re.sub(r"\s+", " ", s).strip()


# ------------------------------------------------------------- the preposition
_RUNS = {}


def _arabic_runs(ctx):
    """Words of the language's script, as a pattern: its letters and the
    marks on them, and not the Arabic comma, question mark or digits, which
    sit in the same block."""
    rx = _RUNS.get(ctx.L.code)
    if rx is None:
        one = r"(?:(?![،؛؟٠-٩۔])%s)" % ctx.L.re_chars.pattern.replace("\\u200C", "")
        rx = _RUNS[ctx.L.code] = re.compile(one + "+")
    return rx


# A romanisation in brackets after an Arabic word: Latin letters with their
# marks, Wiktionary's ʔ ʕ, a hyphen -- (ʕan), (li-), (dahana).  Not `("only")`,
# which is the word's meaning in quotation marks and stays text.
_SOUND = r"\s*\(([A-Za-zÀ-ɏḀ-ỿʔʕʾʿ'\-]+)\)"


def _prep(ctx, w):
    """Is this word one of the prepositions (ar.verbs.json), as written in
    the source -- إِلَى, بِـ -- or bare?"""
    bare = verbs.strip_marks(w or "", ctx.L).replace(_TATWEEL, "").strip()
    return bool(bare) and bare in (ctx.data().get("prepositions") or ())


def _add(got, w, ctx):
    """w into got unless a spelling of it is there (عَن and عَنْ are one)."""
    key = verbs.strip_marks(w, ctx.L).replace(_TATWEEL, "")
    if all(verbs.strip_marks(g, ctx.L).replace(_TATWEEL, "") != key for g in got):
        got.append(w)


def _from_tag(ctx, tags):
    """The prepositions the sense's +obj tag names, one list per object.

    The template's argument, as getdict kept it: objects parted by `+`,
    alternatives by `/`, a preposition after a colon, a case by its name,
    and the object's gloss in angle brackets --
        :إِلَى/acc<somewhere>                  arrive: إِلَى, or a direct object
        acc<something> + :بِ<with something>  unite: an object, and بِ
        acc                                   كَانَ's predicate: nothing
    Measured over the first ranked senses: 497 carry one.  A handful write
    the preposition without its colon (`obj:بِ`, 4) and are read the same.
    What is not a preposition -- the accusative, أَنْ with the subjunctive,
    نَفْسَهُ -- is not what the extra is for.
    """
    out = []
    for t in tags.split(","):
        t = t.strip()
        if not t.startswith("obj:"):
            continue
        v = re.sub(r"<[^<>]*>", "", t[4:])
        v = re.sub(r"\([^()]*\)", "", v)
        for obj in re.split(r"[+;&]", v):
            got = []
            for alt in obj.split("/"):
                alt = alt.strip().lstrip(":").strip()
                if _prep(ctx, alt):
                    _add(got, alt, ctx)
            if got:
                out.append(got)
    return out


def _groups(s):
    """The outermost (...) and [...] of a gloss: (start, end, inside)."""
    out, depth, start = [], 0, 0
    for i, ch in enumerate(s):
        if ch in "([":
            if depth == 0:
                start = i
            depth += 1
        elif ch in ")]" and depth:
            depth -= 1
            if depth == 0:
                out.append((start, i + 1, s[start + 1:i]))
    return out


def _from_gloss(ctx, sense):
    """(the sense without its preposition brackets, [prepositions per
    bracket]) -- for a sense that says it in its words and not in a tag.

    WIKTIONARY WRITES IT BOTH WAYS.  The +obj template's expansion lands in
    the gloss itself where the editor put the template mid-sentence --
    خَرَجَ is "to move [with مِنْ (min) ‘from inside’] (somewhere) to
    outside" -- and older entries write it by hand: "to differ (عَنْ (ʕan)
    from)", "to attack (عَلَى (ʕalā))", "to look after (بِ (bi))".  Of the
    7233 first ranked senses, 144 keep Arabic in the trimmed meaning, and
    those are nearly all this.  A bracket that names a preposition, or a
    `[with ...]` that is the template's own, comes out of the meaning -- the
    extra says it now, in the edition's own shape -- and a bracket that
    merely holds an Arabic word ("together with نَفْسَهُ") stays.
    """
    runs = _arabic_runs(ctx)
    cut, found = [], []
    for a, b, inner in _groups(sense):
        got = []
        for w in runs.findall(inner):
            if _prep(ctx, w):
                _add(got, w, ctx)
        if got:
            found.append(got)
        if got or (sense[a] == "[" and inner.strip().lower().startswith("with")):
            cut.append((a, b))
    for a, b in reversed(cut):
        sense = sense[:a] + " " + sense[b:]
    return re.sub(r"\s+", " ", sense).strip(), found


def _extra(objs):
    """[[p, ...], ...] -> `+ إِلَى`, `+ بِ/إِلَى`, `+ لِ + بِ`: alternatives
    for one object parted by a slash, as de writes `aux. haben/sein`, and a
    second object after a second +."""
    if not objs:
        return ""
    return "+ " + " + ".join("/".join(verbs.tl(p) for p in got) for got in objs)


def _in_meaning(ctx, text):
    """Arabic left in the meaning, as the language's words (\\pw in a book),
    with the romanisation the source put after one in brackets as its sound:
    "the word فقط ("only")" keeps its quotation, "synonym of دَهَنَ (dahana)"
    becomes \\pw{دَهَنَ} \\textit{dahana}."""
    runs = _arabic_runs(ctx).pattern
    rx = re.compile(r"(%s(?:\s+%s)*)(?:%s)?" % (runs, runs, _SOUND))
    out, pos = [], 0
    for m in rx.finditer(text):
        out.append(text[pos:m.start()])
        out.append(verbs.tl(m.group(1), _roman(ctx, m.group(2) or "")))
        pos = m.end()
    out.append(text[pos:])
    return "".join(out)


def _first_sense(ctx):
    """(the sense the meaning slot shows, its tags): the hit's first sense,
    which lookup ranked, found again among the entry's lines for its tags."""
    tags = (ctx.entry["sense_tags"] or "").split("\n")
    lines = [(s, tags[i] if i < len(tags) else "")
             for i, s in enumerate(ctx.senses) if s.strip()]
    if not lines:
        return "", ""
    first = next((s for s in ctx.hit.get("senses") or [] if (s or "").strip()), "")
    for s, t in lines:
        if s == first:
            return s, t
    ranked = lookup.rank_senses([s for s, _t in lines], [t for _s, t in lines])
    return ranked[0][0], ranked[0][1]


# ------------------------------------------------------------------ the recipe
def recipe(ctx):
    e = ctx.entry
    if (e["pos"] or "") != "verb":
        return None
    # a perfect in the language's script and nothing else: a row with a
    # Latin word left in it is a piece of the head line, not a verb
    heads = [h for h in _heads(ctx) if ctx.in_script(h[0].form)]
    if not heads:
        return None                     # لَيْسَ and the rest: a \dw
    perf, num, line = _which(ctx, heads)
    missing = []

    # the perfect's sound: the head's own romanisation row, and for the
    # entry's first head the entry's, which is the same row read by getdict
    rom = next((f.form for f in line if f.tags == {"romanization"}), "")
    if not rom and perf is heads[0][0]:
        rom = e["translit"] or ""
    s1 = _roman(ctx, rom)
    if not s1:
        missing.append("transliteration of the perfect")
    s1 = ("%s (%s)" % (s1, num)).strip()

    # the imperfect: the head line's non-past, exactly -- a table cell with
    # `non-past` among six other tags is some other person or mood
    impf = next((f for f in line if f.tags == {"non-past"} and ctx.in_script(f.form)),
                None)
    f2 = impf.form if impf else ""
    s2 = _roman(ctx, impf.roman) if impf else ""
    if not f2:
        missing.append("imperfect")
    elif not s2:
        missing.append("transliteration of the imperfect")

    # THE MASDAR IS THE FIRST THE SOURCE GIVES, and that is a draft.  1122
    # entries give more than one, and which of them goes with the sense in
    # the text -- what docs/lang/ar.md asks for -- is exactly what no row
    # says: the first is often the one in use (كَتَبَ كِتَابَة, قَالَ قَوْل,
    # ذَهَبَ ذَهَاب) and often not (هَلَكَ lists هُلْك before هَلَاك, دَامَ
    # دَوْم before دَوَام, وَصَلَ "to arrive" صِلَة before وُصُول).  It is the
    # meaning's own problem -- the first ranked sense need not be the text's
    # either -- and it is not `missing`, which says a slot went in blank.
    # Preferring the masdar a homograph does not also list was tried: it gave
    # وَصَلَ its وُصُول and took مَوْت from مَاتَ, إِذْن from أَذِنَ and
    # تَذْكِير from ذَكَّرَ -- 109 entries changed, half for the worse.
    # NO MASDAR ROW IS NOT AN ANSWER.  A head line with no verbal noun says
    # one of two things, and the dictionary keeps neither: `vn:-`, the verb
    # has none in use (28 heads: زَالَ, the idioms like كَشَفَ النِّقَابَ),
    # or `verbal noun ?`, nobody has written it yet (15: بَنَّ, سَالَ,
    # مَهَرَ).  A blank pair prints nothing, label and all, and reads as the
    # first -- so it is named, and the button asks, unless entry.head says
    # the source's answer was "none" (`vn_none`, the perfects whose template
    # has vn:-; a dictionary built before getdict keeps it has no such key).
    # Also here: a later head whose masdar had an earlier head's spelling,
    # which getdict keeps once.
    seen, vns = set(), []
    for f in line:
        if f.tags == {"noun-from-verb"} and ctx.in_script(f.form) \
                and _nfc(f.form) != _nfc(perf.form) and _nfc(f.form) not in seen:
            seen.add(_nfc(f.form))
            vns.append(f)
    f3 = vns[0].form if vns else ""
    s3 = _roman(ctx, vns[0].roman) if vns else ""
    if vns and not s3:
        missing.append("transliteration of the masdar")
    none = ctx.head.get("vn_none")
    if not vns and not (isinstance(none, list)
                        and _nfc(perf.form) in {_nfc(str(x)) for x in none}):
        missing.append("masdar")
    # THE OTHERS ARE A NOTE, beside the line and never in the \vb: the one
    # that goes with the text's sense is the editor's to choose, and it is
    # not `missing`, which says a slot went in blank.  قَالَ gives قَوْل and
    # the note `masdar also: مَقَال maqāl, مَقَالَة maqāla`.
    notes = []
    if len(vns) > 1:
        notes.append("%s also: " % ctx.L.vb_labels[1] + ", ".join(
            verbs.tl(f.form, _roman(ctx, f.roman)) for f in vns[1:]))

    # THE PREPOSITION, of the sense the meaning shows and of no other: وَصَلَ
    # "to unite" takes بِ and "to arrive" إِلَى, and they are two entries;
    # inside one entry the senses differ just as much.
    sense, tags = _first_sense(ctx)
    objs = _from_tag(ctx, tags)
    cleaned, inline = _from_gloss(ctx, sense)
    if not objs:
        objs = inline
    # one object named twice is one object: اِسْتَخْبَرَ is "to inquire of
    # (someone عَنْ ...), to ask (someone عَنْ ...)", two equivalents with the
    # same bracket each, and `+ عَنْ + عَنْ` says a second object it has not
    once, named = set(), []
    for got in objs:
        key = tuple(verbs.strip_marks(p, ctx.L).replace(_TATWEEL, "") for p in got)
        if key not in once:
            once.add(key)
            named.append(got)
    extras = [x for x in (_extra(named),) if x]
    meaning = None
    if cleaned != sense or _arabic_runs(ctx).search(sense):
        meaning = _in_meaning(ctx, verbs.trim_meaning(cleaned))

    return verbs.Parts(parts=[(perf.form, s1), (f2, s2), (f3, s3)],
                       meaning=meaning, extras=extras, missing=missing,
                       notes=notes)
