# SPDX-License-Identifier: GPL-3.0-or-later
"""Persian: the \\vb a dictionary hit for a verb offers.

    \\vb{دیدن}{didan}{بین}{bin}{دید}{did}{to see}
    \\vb{برگشتن}{bar-gaštan}{برگرد}{bar-gard}{برگشت}{bar-gašt}{to return}
    \\vb{داشتن}{dāštan}{دار}{dār}{داشت}{dāšt}{to have (pres. without mi-)}
    \\vb{کردن}{kardan}{کن}{kon}{کرد}{kard}{}     in `فکر می‌کنم`, with the \\bw
                                               for فکر named in `missing`

docs/lang/fa.md says what goes in and nothing here adds to it: the
infinitive, the present stem -- the one nobody can guess -- and the past stem,
each with its sound; the meaning; and after it, in one parenthesis, the one
thing the three forms cannot say, which for Persian is a closed list of one:
داشتن's present takes no mi-.  A video's plain line adds the colloquial first
person present (`coll. می‌گم mi-gam`), because a video is spoken Tehrani and
a book is not.  A compound is the light verb's \\vb with an empty meaning,
then a \\bw for the word it carries, which a \\vb cannot hold: it is named in
`missing`, so the editor's button says what to add.

WHERE EACH FORM COMES FROM, all of it rows the source wrote:

    the table   entry.head, which lib/getdict.py _head fills from the ONE
                conjugation table whose header says `literary Iranian
                Persian` and whose infinitive is this headword: the present
                and past stems and all three sounds, from one source.  256 of
                the 471 simple verbs have it, and the commonest all do
    else        the head line's own `present stem` row, the sound after its
                `/` (`bīn /bin`: Classical, then Iranian); the infinitive's
                sound from the pronunciation (lookup's `said`, the Iran
                reading) or the source's Iranian romanisation of the
                headword; the past stem is the infinitive without its ن
    coll.       a `first-person indicative present singular` row with an
                Iranian romanisation (`mí-gam`) that is not the literary one:
                18 verbs, the ones fa.md names among them

ONE SOURCE FOR THE THREE SOUNDS, WHERE THERE IS ONE.  The pronunciation says
رسیدن is rasidan and the table says residan, res, resid; taken one from each,
the entry would print rasidan beside res.  The table is Iranian by its own
header, and it is what the fixture book writes (residan, res).

THE SOURCE'S ROWS ARE READ BY WHAT THEY ARE, NEVER BY WHERE THEY STAND.
A Persian verb page carries up to five tables -- literary Iranian,
colloquial Tehrani, dialectal Isfahan, literary Dari, colloquial Kabuli --
with the same tags in all of them, and getdict keeps one row per spelling
and tag set, so the Dari table's دانستن `dānistán` is the `infinitive` row
and the Iranian one, spelt the same, is gone.  What tells them apart is the
romanisation: Dari writes mḗ- and ī ū ē ō, Iranian writes mí- and â.

A POINTER ROW IS READ ONLY WHERE IT CANNOT BE SOMEBODY ELSE'S.  A page that
is only "present stem of X" is linked to the first verb spelt X, so the
`present, stem` row روب (of roftan, to sweep) sits under raftan, to go.  For
a headword only one verb has, the pointer is certainly this verb's, and it is
the one place بودن's present stem باش has a sound (`bāš`): the head line
lists it with none.

NOTHING HERE GUESSES.  A slot no row fills is left for the annotator and
named in `missing`.  The past stem is the one form made here, and it is not a
guess: a Persian infinitive IS its past stem and -an, without exception (the
literary table agrees on every verb whose table is not itself broken, and
the one verb it would not hold for, هستن, gets no \\vb at all).

Standard library only: the server imports it.
"""
import json
import re
import unicodedata

import lookup                                                  # noqa: E402
import translit                                                # noqa: E402
from verbs import (Form, Parts, one_equivalent, split_tags, tl,  # noqa: E402
                   trim_meaning)

# ------------------------------------------------------------- the rows
# The tag sets the recipe reads, exactly: a subset would take the dialectal
# Isfahan pointer `کون` (Isfahan, dialectal, present, stem) as کردن's stem.
PRESENT_STEM = frozenset(("present", "stem"))
FIRST_PRESENT = frozenset(("first-person", "indicative", "present", "singular"))
ROMANIZATION = frozenset(("romanization",))

# A PRONOUN IS NOT A FORM OF آراستن.  Seven old-style tables (آراستن, both
# جستن, افراشتن, پیراستن, ویراستن, نشسن) came out of wiktextract with their
# person column as cells -- من تو او وی آن ما شما ایشان آنان آنها, tagged
# exactly `error-unrecognized-form singular` or `... plural` -- so every او of
# every text was also آراستن: 792 of the 4 291 words with a verb hit, over
# 2 000 Tatoeba sentences.  (بودن's own `error-unrecognized-form` rows, هستم
# and باشم, are real forms and carry no number.)
PERSON_COLUMN = (frozenset(("error-unrecognized-form", "singular")),
                 frozenset(("error-unrecognized-form", "plural")))

# A PERSIAN INFINITIVE ENDS IN -tan OR -dan, and nothing else on a verb page
# does.  Measured over the 1 415 pos=verb entries: 1 392 end so.  The other
# 23 are a copula form (هست), modals (باید, بایست, بایستی, شاید), forms that
# kept a gloss (بیا, نبود, گیرم, گفتا, شکسته), optatives (زنده باد, شاد
# باد), a compound that ends in its preposition (نزدیک شدن به), five
# dialect infinitives in -san (دونسن, خندسن, ...) and five words of other
# kinds filed as verbs (یعنی, سیل, کشاکش): none has two stems to print, and
# each is the \dw it is.
_INFINITIVE = ("تن", "دن")

# The Iranian romanisation, as the edition writes it.  tidy_roman already
# takes the acute off and makes â ā; these are the letters the literary
# table still writes and docs/lang/fa.md does not: `ġ` for غ (the scheme
# writes both ق and غ as q -- ġosse xordan, doruġ goftan: 24 tables), and on
# ten literary verbs a long vowel written the classical way -- sôxtan for
# سوختن, whose pronunciation is [suːx.t̪ʰǽn], sepōz, niyôšîdan, šakēb.  The
# edition's vowels are a e o ā i u and nothing else (lib/lang/fa.ipa.json
# makes eː i and oː u for the same reason), so ô ō ū are u and î ī ē are i.
# ONLY IN THE TABLE, whose header says it is Iranian: in any other row those
# letters are the Classical or Dari romanisation, and the row is refused.
_TABLE_LETTERS = {"ġ": "q", "ô": "u", "ō": "u", "ū": "u",
                  "î": "i", "ī": "i", "ē": "i"}
# What an edition sound may hold once tidied: the scheme's letters, the
# apostrophe of ع and ء, a hyphen, a space between the parts of a compound.
_SOUND = re.compile(r"[abdefghijklmnopqrstuvwxyzāčšž' -]+")
# w only in the diphthong ow (rowšan, towsif); anywhere else it is the
# Classical xw- or aw- (xwar, āwar) of a row that is not Iranian.
_CLASSICAL_W = re.compile(r"(?<!o)w")
# The letters only the CLASSICAL romanisation writes: it marks every long
# vowel with a macron (dīdan, xwāstan, būdan, and the majhul ē ō), where the
# Iranian one writes â for ā and leaves i and u bare (didan, xâstan, budan).
_CLASSICAL = re.compile("[āīūōēḗĀĪŪŌĒ]")

# The words that may stand between a verb and what goes with it, written
# apart: the mi- and nemi- a Tatoeba sentence and an old printing often
# write as a word of their own (`فکر می کنم`, `باز نمی شد`, the fixture's
# ch1.tex:63), and the future's auxiliary (`روده بر خواهد کرد`, :440).
_BETWEEN = frozenset(("می", "نمی", "خواهم", "خواهی", "خواهد", "خواهیم",
                      "خواهید", "خواهند", "نخواهم", "نخواهی", "نخواهد",
                      "نخواهیم", "نخواهید", "نخواهند"))

# A SENSE THAT ONLY POINTS AT ANOTHER WORD is no meaning: برگشادن is
# "synonym of گشودن", اڤزودن "Early New Persian form of افزودن" (6 verbs).
_POINTS = re.compile(r"\bof\s+[؀-ۿ]")


def _fold(s, L):
    """The spelling to compare: no harakat, no joiner, no space."""
    return lookup._fold(s or "", L).replace(" ", "")


def _en(ctx):
    return (ctx.gloss or "").strip().lower() == "en"


def _dialect_only(tags):
    """Is every sense of the entry tagged dialectal?"""
    return bool(tags) and all("dialectal" in t for t in tags)


def _tag_sets(row):
    """An entry's sense tags, one set per sense line, as ctx.sense_tags."""
    senses = (row["sense"] or "").split("\n")
    tags = (row["sense_tags"] or "").split("\n")
    return [set(t.strip() for t in (tags[i] if i < len(tags) else "").split(",")
                if t.strip()) for i in range(len(senses))]


# ------------------------------------------------------------ the sounds
def _sound(s, table=False):
    """One romanisation the source gives, as the edition writes it, or ''.

    The head line writes the two registers at once, `bīn /bin` (Classical,
    then Iranian): the part after the last `/` is taken.  A comma or an `or`
    offers alternatives, `šenow, šonow`, `nah or neh`: the first is taken.
    The glottal stop that opens a word is not written (lib/lang/fa.ipa.json
    `strip_leading`: عکس is aks).  A sound left with a letter the scheme does
    not have is not the Iranian reading at all, and '' says so."""
    s = (s or "").strip()
    s = re.split(r"\s*,\s*|\s+or\s+", s)[0]
    if "/" in s:
        s = s.split("/")[-1]
    s = translit.tidy_roman("fa", s.strip())
    if table:
        for a, b in _TABLE_LETTERS.items():
            s = s.replace(a, b)
    else:
        s = s.replace("ġ", "q")
    s = unicodedata.normalize("NFC", re.sub(r"\s+", " ", s)).strip().lower()
    s = " ".join(w[1:] if w.startswith("'") and len(w) > 1 else w for w in s.split(" "))
    if not s or not _SOUND.fullmatch(s) or _CLASSICAL_W.search(s):
        return ""
    return s


def _plain(s):
    return (s or "").replace("-", "").replace(" ", "")


# ---------------------------------------------------------------- an entry
class _Entry:
    """One verb entry's row, form rows and head facts -- the hit's own, or
    another the chunk turned out to be about (a compound's light verb, a
    preverb verb written apart) -- read through the same few questions."""

    def __init__(self, ctx, row, rows=None):
        self.ctx, self.row = ctx, row
        self._rows = rows

    @property
    def headword(self):
        return self.ctx.bare(self.row["headword"] or "")

    @property
    def rows(self):
        if self._rows is None:
            c = self.ctx.conn
            roman = "roman" if lookup._has_col(c, "roman", "form") else "''"
            self._rows = [
                Form(r["form"] or "", r["note"] or "", split_tags(r["note"]),
                     r["roman"] or "", r["rowid"])
                for r in c.execute(
                    "SELECT rowid, form, note, %s AS roman FROM form "
                    "WHERE entry_id = ? ORDER BY rowid" % roman, (self.row["id"],))]
        return self._rows

    @property
    def head(self):
        try:
            d = json.loads(self.row["head"] or "{}")
        except (ValueError, TypeError):
            d = {}
        return d if isinstance(d, dict) else {}

    @property
    def said(self):
        """How the infinitive is said, from the pronunciation (the Iran
        reading lib/lang/fa.ipa.json asks getdict for): lookup's `said`, the
        lemma's own and never the reached form's."""
        return translit.from_ipa("fa", self.row["ipa"] or "")

    @property
    def alone(self):
        """Is this the only verb spelt so?  Then a pointer row filed under
        the spelling is certainly this verb's."""
        n = self.ctx.conn.execute(
            "SELECT count(*) FROM entry WHERE headword = ? AND pos = 'verb'",
            (self.row["headword"],)).fetchone()[0]
        return n <= 1


def _verbs_spelt(ctx, headword):
    """The verb entries with exactly this headword, first first -- every
    column _Entry reads present, '' where the dictionary predates it."""
    c = ctx.conn
    cols = ", ".join((
        "id", "headword", "translit", "sense",
        "ipa" if lookup._has_col(c, "ipa") else "'' AS ipa",
        "head" if lookup._has_col(c, "head") else "'' AS head",
        "sense_tags" if lookup._has_col(c, "sense_tags") else "'' AS sense_tags"))
    return c.execute("SELECT %s FROM entry WHERE headword = ? AND pos = 'verb' "
                     "ORDER BY id" % cols, (headword,)).fetchall()


def _verbs_by_id(ctx, eid):
    """One entry by id, with the columns _verbs_spelt gives."""
    c = ctx.conn
    cols = ", ".join((
        "id", "headword", "translit", "sense",
        "ipa" if lookup._has_col(c, "ipa") else "'' AS ipa",
        "head" if lookup._has_col(c, "head") else "'' AS head",
        "sense_tags" if lookup._has_col(c, "sense_tags") else "'' AS sense_tags"))
    return c.execute("SELECT %s FROM entry WHERE id = ?" % cols, (eid,)).fetchone()


# ------------------------------------------------------------- the stems
def _table(ent, past):
    """The literary Iranian table's present stem and sounds, or {}.

    TAKEN ONLY WHEN IT AGREES WITH ITSELF.  Its past stem must be this
    headword without its ن -- a table of another verb is not this one's --
    and its sounds must say the same thing twice: the infinitive's sound is
    the past stem's and -an.  One table does not, بلعیدن's (bal'īdanán,
    bal'īdan: every sound a syllable long), and its sounds are not used.
    The stem is written in one piece (the table writes برگشتن's `بر گرد`,
    apart, to show where mi- goes; the book writes برگرد); the raw sounds
    are kept for _preverb, which reads that same space."""
    ctx = ent.ctx
    h = ent.head
    prs = ctx.bare(re.sub(r"\s+", "", str(h.get("prs") or "")))
    ps = ctx.bare(re.sub(r"\s+", "", str(h.get("ps") or "")))
    if not prs or not ctx.in_script(prs):
        return {}
    if ps and _fold(ps, ctx.L) != _fold(past, ctx.L):
        return {}
    got = {"prs": prs, "raw": [str(h.get("prs_tr") or ""), str(h.get("inf_tr") or "")]}
    inf_s = _sound(h.get("inf_tr"), table=True)
    prs_s = _sound(h.get("prs_tr"), table=True)
    ps_s = _sound(h.get("ps_tr"), table=True)
    if inf_s and (not inf_s.endswith("an")
                  or (ps_s and _plain(inf_s) != _plain(ps_s) + "an")):
        return got
    got.update(inf_s=inf_s, prs_s=prs_s, ps_s=ps_s)
    return got


def _spelt_out(ent):
    """The infinitive's sound where there is neither a table nor a
    pronunciation: the source's own romanisation of the headword, but only
    the Iranian one.  73 simple verbs have neither, all rare (لنگیدن,
    هراسیدن, دواندن), and this gives 53 of them a sound.

    The head line writes both, `būdan /budan`, and getdict keeps them as
    `romanization` rows, Classical first, and the first as the entry's
    translit.  The last row that is not Classical is taken -- one with an â
    (harâsidan, davândan) or with no long vowel marked at all (langidan,
    whose ی the Classical would write ī) -- and a Classical one (čalīdan,
    Āmuzāndan) never is: it is a register this edition is not written in."""
    ctx = ent.ctx
    cands = [f.form for f in ent.rows if f.own and f.tags == ROMANIZATION]
    if not cands:
        cands = [ent.row["translit"] or ""]
    for raw in reversed(cands):
        raw = (raw or "").strip()
        if not raw or _CLASSICAL.search(raw) or ctx.in_script(raw):
            continue
        s = _sound(raw.lower())
        if s.endswith("an"):
            return s
    return ""


def _stem_rows(ent):
    """The rows that say they are this verb's present stem: its own first,
    then -- for a verb nobody else is spelt as -- the pointers at it."""
    ctx = ent.ctx
    own = [f for f in ent.rows if f.own and f.tags == PRESENT_STEM
           and ctx.in_script(f.form)]
    ptr = [f for f in ent.rows if not f.own and f.tags == PRESENT_STEM
           and ctx.in_script(f.form)] if ent.alone else []
    return own + ptr


def _first_person(ent, stem, stem_s):
    """The Iranian `first-person indicative present singular` rows, split
    into the literary one, built on this stem, and the others, in the order
    written: ((row, sound) or None, [(row, sound), ...]).

    THE LITERARY PRESENT IS می + stem + م, said mi- + stem + -am, and after a
    stem that ends in a vowel می + stem + یم, mi- + stem + -yam: می‌آیم, not
    میآم, is آمدن's -- میآم is the colloquial table's mí-âm, which the
    spelling alone would have taken for the literary one.  A row is the
    literary one if its spelling or its sound says so: the spelling where the
    table writes the stem's vowel its own way (سوختن's stem is `sôz` in the
    table and سوز in the script), the sound where the spelling was not kept
    (دانستن's میدانم is the Dari table's, mḗ-dānam)."""
    ctx = ent.ctx
    mine, others = None, []
    if stem_s:
        tail = ("یم",) if stem_s[-1] in "aeoāiu" else ("م",)
    else:
        tail = ("م", "یم")
    forms = {_fold("می" + stem + t, ctx.L) for t in tail}
    want = ({"mi" + _plain(stem_s) + "am", "mi" + _plain(stem_s) + "yam"}
            if stem_s else set())
    for f in ent.rows:
        if f.tags != FIRST_PRESENT or not f.own or not ctx.in_script(f.form):
            continue
        s = translit.tidy_roman("fa", f.roman or "").strip().lower()
        # the Iranian tables write mí-; Dari and Kabuli write mḗ- or run
        # the prefix into the stem (myāyum), and are another register
        if not s.startswith("mi-") or " " in s or not _SOUND.fullmatch(s):
            continue
        if _fold(f.form, ctx.L) in forms or _plain(s) in want:
            if mine is None:
                mine = (f, s)
            continue
        others.append((f, s))
    return mine, others


def _preverb(ent, t, same):
    """The preverb's sound, where the source parts it from the verb, or ''.

    docs/lang/fa.md hyphenates a verb with a preverb after it, in all three
    sounds, because that is where mi-, be- and na- go: bar-mi-gardam,
    bar-gard.  WHERE THE PREVERB ENDS IS THE SOURCE'S TO SAY, and it says so
    three ways: the literary table writes the stems apart (برگشتن's `بر گرد`,
    `bar gard`); a present-stem row spelt apart (برداشتن's `بر دار`, `bar
    dār`, beside its `بَردار`); a present written with the mi- after the
    preverb (بازداشتن's `باز میدارم`, bāz mḗ-dāram -- the Dari table's, and
    the preverb is said the same in both).  Eleven verbs, برگشتن, درآوردن
    and فراگرفتن among them.  Nothing else is taken for one: برخاستن is بر +
    خاستن, and no row of it says where mi- goes, so its sounds come in one
    piece for the annotator; and برانداختن's own table says mí-barandâzam, a
    verb the source does not part."""
    ctx = ent.ctx
    for s in t.get("raw") or ():
        s = re.split(r"\s*,\s*|\s+or\s+", s.strip())[0]     # šenow, šonow
        if " " in s:
            return _sound(s.split()[0], table=True)
    hw = _fold(ent.headword, ctx.L)
    for f in same:
        if len(ctx.bare(f.form).split()) == 2:
            r = (f.roman or "").split("/")[-1].split()
            if len(r) == 2:
                return _sound(r[0])
    for f in ent.rows:
        words = ctx.bare(f.form).split()
        if not (f.own and len(words) == 2 and words[1].startswith("می")):
            continue
        # the preverb, and after it a verb: not داشتن's `داشت میداشت`
        rest = hw[len(_fold(words[0], ctx.L)):]
        if (hw.startswith(_fold(words[0], ctx.L)) and len(rest) > 2
                and rest.endswith(_INFINITIVE)):
            r = translit.tidy_roman("fa", f.roman or "").split()
            if len(r) == 2 and not _CLASSICAL.search(r[0]):
                return _sound(r[0])
    return ""


def _parted(s, pre):
    """One sound with the preverb hyphened off: at the source's own space
    where it wrote one (`bar gard`, `dar bar gir`), else after the preverb's
    sound (bardāštan, from the pronunciation, is bar-dāštan)."""
    if " " in s:
        return re.sub(r"\s+", "-", s.strip())
    if pre and s.startswith(pre) and len(s) > len(pre):
        return pre + "-" + s[len(pre):]
    return s


def _stems(ent):
    """(the three pairs, what is missing, the colloquial present or None)."""
    ctx = ent.ctx
    hw = ent.headword
    past = hw[:-1]
    t = _table(ent, past)
    prs = t.get("prs", "")
    prs_s, inf_s, ps_s = t.get("prs_s", ""), t.get("inf_s", ""), t.get("ps_s", "")

    rows = _stem_rows(ent)
    if not prs and rows:
        # THE HEAD LINE'S STEM, which is the first row: the tables' rows come
        # after it, and the colloquial table's `stems` (گه ge, ره re, شه še)
        # are its third person, not a stem.
        prs = ctx.bare(re.sub(r"\s+", "", rows[0].form))
    same = [f for f in rows if _fold(f.form, ctx.L) == _fold(prs, ctx.L)] if prs else []
    if prs and not prs_s:
        prs_s = next((s for s in (_sound(f.roman) for f in same) if s), "")
    if prs and not prs_s:
        # NO ROW SAYS THE STEM, but the present built on it does: می‌بینم is
        # mí-binam, so the stem is bin.  Only a row spelt exactly
        # می + stem + (ی)م is read, and only its Iranian romanisation.
        mine, _others = _first_person(ent, prs, "")
        if mine is not None:
            core = mine[1][3:]
            for end in ("yam", "am"):
                if core.endswith(end) and len(core) > len(end):
                    prs_s = _sound(core[:-len(end)])
                    break

    if not inf_s:
        inf_s = _sound(ent.said)
        if not inf_s.endswith("an"):
            inf_s = ""
    if not inf_s:
        inf_s = _spelt_out(ent)
    if inf_s and not ps_s:
        ps_s = inf_s[:-2]

    pre = _preverb(ent, t, same)
    inf_s, prs_s, ps_s = (_parted(x, pre) for x in (inf_s, prs_s, ps_s))

    names = ctx.L.vb_forms
    missing = []
    if not inf_s:
        missing.append("%s sound" % names[0])
    if not prs:
        missing.append(names[1])
    elif not prs_s:
        missing.append("%s sound" % names[1])

    coll = None
    if prs and prs_s and not pre:
        _mine, others = _first_person(ent, prs, prs_s)
        if others:
            f, s = others[0]
            form = ctx.bare(f.form)
            # the table writes میگم, the edition می‌گم: the joiner the
            # romanisation's own hyphen stands for (docs/lang/fa.md)
            if form.startswith("می") and not form.startswith("می‌"):
                form = "می‌" + form[2:]
            coll = (form, s)
    return [(hw, inf_s), (prs, prs_s), (past, ps_s)], missing, coll


# ------------------------------------------------------------ the chunk
def _tokens(ctx):
    """The chunk's words, folded, and where the hit's word is among them.

    THE WORD CAN BE TWO TOKENS.  lookup joins a progressive prefix written
    apart to its verb (fa.lookup.json `join_next`: `می کنم` is looked up as
    one word), and the hit's word is then both tokens.  Compared token by
    token it was never found, so every compound, element and preverb reading
    failed on it: `گریه می کند` came back as کردن with its own meaning
    instead of the compound's empty one (60 of 469 compounds on the fixture
    book and 1,500 corpus sentences).  So the word is matched as a run of as
    many tokens as it has, and placed at its LAST token -- the verb --
    where _before already steps back over the mi-."""
    toks = [_fold(lookup._bare(w, ctx.L), ctx.L) for w in ctx.L.split_words(ctx.text)]
    toks = [t for t in toks if t]
    me = _fold(ctx.word, ctx.L)
    n = max(1, len(ctx.L.split_words(ctx.word)))
    return toks, [i + n - 1 for i in range(len(toks) - n + 1)
                  if "".join(toks[i:i + n]) == me]


def _before(toks, i):
    """Where the words before toks[i] end, a mi- written apart and the
    future's auxiliary passed over."""
    j = i - 1
    while j >= 0 and toks[j] in _BETWEEN:
        j -= 1
    return j


def _compound_here(ctx, infinitive):
    """The compound the chunk makes of this verb and the word or words before
    it, as (its entry row, the element as the headword writes it), or None.
    Only one the dictionary has as a verb: فکر می‌کنم is فکر کردن, and هوا
    سرد شد is شدن, to become, because سرد شدن is not an entry.  Longest
    first: روده بر کردن, then بر کردن.  Compared without harakat or joiner,
    so a book's `عَوَض کُنَم` and Tatoeba's `پیشبینی` find عوض کردن and
    پیش‌بینی کردن."""
    known = _index(ctx)["compounds"]
    toks, at = _tokens(ctx)
    for i in at:
        j = _before(toks, i)
        for n in (3, 2, 1):
            if j - n + 1 < 0:
                continue
            eid = known.get(("".join(toks[j - n + 1:j + 1]), infinitive))
            if eid is not None:
                row = _verbs_by_id(ctx, eid)
                return row, " ".join(ctx.bare(row["headword"]).split()[:-1])
    return None


def _element_here(ctx, element):
    """Is this compound's element in the chunk, just before the hit's word?

    A compound's entry is reached through its light verb alone -- getdict
    keeps the colloquial table's rows, which drop the element, so گرفتم is a
    row of اندازه گرفتن -- and هستند came back as بلد بودن, امیدوار بودن,
    پشیمان بودن and شاهد بودن.  None of them is what هستند says."""
    el = [_fold(w, ctx.L) for w in element.split()]
    me = _fold(ctx.word, ctx.L)
    if me.startswith("".join(el)) and len(me) > len("".join(el)):
        return True                     # the word carries it: متشکرم
    toks, at = _tokens(ctx)
    for i in at:
        j = _before(toks, i)
        if j - len(el) + 1 >= 0 and toks[j - len(el) + 1:j + 1] == el:
            return True
    return False


def _preverb_here(ctx, infinitive):
    """The preverb verb the chunk writes apart -- `بر می‌گردم`, `دَر آوَردِه
    بود` (the fixture's ch1.tex:452) -- as its entry row, or None.

    بر AND در ARE ALSO PREPOSITIONS, and the preposition was the commoner
    reading by far: over the corpus, `در آن` (in that) came back as درآمدن 28
    times -- آن is also آمدن's colloquial `they come` -- `در بدن` (in the
    body) and `در ده` as دردادن.  So three things must hold: a preverb of the
    closed list (lib/lang/fa.verbs.json) stands directly before the verb (a
    mi- written apart aside); the preverb verb's own table has the two words
    as one of its forms (برگشتن lists `بر میگردم`, درآوردن `در آورده`, and
    `در بدن` is nobody's); and the word is not a pronoun, a determiner, a
    number or another word of the closed classes, which is what a
    preposition is followed by -- the table of درآمدن does list `در آن`."""
    pre = ctx.data().get("preverbs") or ()
    toks, at = _tokens(ctx)
    for i in at:
        j = _before(toks, i)
        if j < 0 or toks[j] not in pre:
            continue
        got = _verbs_spelt(ctx, toks[j] + infinitive)
        if not got:
            continue
        if ctx.conn.execute(
                "SELECT 1 FROM entry WHERE headword = ? AND pos IN (%s) LIMIT 1"
                % ",".join("?" * len(lookup._CLOSED)),
                (ctx.bare(ctx.word),) + tuple(lookup._CLOSED)).fetchone():
            continue
        want = "".join(toks[j:i + 1])
        for f in _Entry(ctx, got[0]).rows:
            if _fold(f.form, ctx.L) == want:
                return got[0]
    return None


_INDEX = {}


def _index(ctx):
    """What the whole dictionary says about verbs made of other verbs, asked
    once per file: `ends`, the verbs some compound ends in or some preverb
    verb goes on as (کردن, گشتن), and `compounds`, each compound's element
    (folded) and light verb -> its entry's id, the first that is not a
    dialect's.  A verb in neither never reads the chunk, and is built once
    and not once per chunk (reading ctx.text puts the chunk in the cache's
    key)."""
    pre = tuple(ctx.data().get("preverbs") or ())
    key = (id(ctx.conn), lookup._stamp(lookup.path_for(ctx.code)), pre)
    got = _INDEX.get(key)
    if got is None:
        ends, compounds = set(), {}
        for r in ctx.conn.execute(
                "SELECT id, headword, sense, %s AS sense_tags FROM entry "
                "WHERE pos = 'verb' ORDER BY id"
                % ("sense_tags" if lookup._has_col(ctx.conn, "sense_tags") else "''")):
            ws = ctx.bare(r["headword"] or "").split()
            if len(ws) > 1:
                ends.add(ws[-1])
                k = (_fold("".join(ws[:-1]), ctx.L), ws[-1])
                if k not in compounds and not _dialect_only(_tag_sets(r)):
                    compounds[k] = r["id"]
            elif ws:
                ends.update(ws[0][len(p):] for p in pre
                            if ws[0].startswith(p) and len(ws[0]) > len(p) + 2)
        got = {"ends": ends, "compounds": compounds}
        _INDEX.clear()
        _INDEX[key] = got
    return got


# ------------------------------------------------------------ the pieces
def _ranked(row):
    """An entry's senses, plainest first, the way lookup ranks a hit's."""
    senses = [s for s in (row["sense"] or "").split("\n") if s.strip()]
    return [r[0] for r in lookup.rank_senses(senses, (row["sense_tags"] or "").split("\n"))]


def _meaning(ctx, headword, first, senses):
    """(the meaning, what is missing), from the first ranked sense trimmed
    (`first`: the core's ctx.meaning for the hit's own entry) and the ranked
    senses behind it.

    ONE EQUIVALENT (docs/lang/fa.md: "one equivalent in the gloss language
    rather than a string of synonyms", and check_batch warns on two): دیدن's
    first sense is "to see, to look".  The hand-kept table says where the
    source's first sense is not the one a reader meets (بودن: see
    lib/lang/fa.verbs.json).  A sense that only points at another word is
    passed over for the next that does not, and where none does the meaning
    is left to the annotator and named."""
    if not _en(ctx):
        return "", []
    over = (ctx.data().get("meaning") or {}).get(headword)
    if isinstance(over, str):
        return over, []
    if not _POINTS.search(first or ""):
        return one_equivalent(first or ""), []
    # the pointer's own gloss of the word it points at, where it gives one:
    # وایستادن is "synonym of وایسادن (vâysâdan, “to stand, to stop”)."
    quoted = re.search("“([^”]+)”", (senses or [""])[0] or "")
    if quoted and trim_meaning(quoted.group(1)):
        return one_equivalent(trim_meaning(quoted.group(1))), []
    for s in (senses or [])[1:]:
        m = trim_meaning(s)
        if m and not _POINTS.search(m):
            return one_equivalent(m), []
    m = re.search(r"of\s+(\S+)", first)
    return "", ["meaning: the dictionary only points at %s"
                % (m.group(1) if m else "another word")]


def _extras(ctx, headword):
    """What the three forms cannot say: a closed list, docs/lang/fa.md."""
    if headword in (ctx.data().get("no_mi") or {}):
        return ["pres. without mi-"]
    return []


def _video(ctx, coll):
    """The colloquial present, for a video's line only -- and not where the
    chunk's word IS that present, which the line already starts with."""
    if not coll or _fold(coll[0], ctx.L) == _fold(ctx.word, ctx.L):
        return []
    return ["coll. " + tl(coll[0], coll[1])]


def _compound_parts(ctx, element, compound):
    """The compound in pieces: the whole verb (فکر کردن, its sound and its
    meaning) and the element the light verb carries, whose sound is the head
    of the compound's own -- `labxand zadan` minus the light verb's word.

    Persian puts the compound's meaning in the \\bw as well (docs/lang/fa.md:
    `\\bw{لبخند}{labxand}{to smile}`), so `word_mean` is left to the core,
    which takes the compound's where a language does not say otherwise."""
    ent = _Entry(ctx, compound)
    said = _sound(ent.head.get("inf_tr"), table=True)
    words = said.split(" ")
    n = len(element.split())
    sound = " ".join(words[:n]) if len(words) > n else ""
    mean = one_equivalent(trim_meaning(_ranked(compound)[0])) \
        if _en(ctx) and _ranked(compound) else ""
    return {"name": "compound verb",
            "whole": ent.headword, "whole_sound": said, "mean": mean,
            "word": element, "word_sound": sound}


def _bw_note(ctx, element, compound):
    """...and the same thing said, as one item of `missing`.  No backslash
    (the core takes every one out) and no comma (the editor joins the items
    with them) -- the words lib/verbs/tr.py uses, because docs/lang/tr.md
    glosses its compounds the Persian way.

    It is said even where `compound` carries the whole entry to be put in
    with one press: the reader is told what the entry is about to become
    before pressing, and the row is what the yellow line says."""
    got = _compound_parts(ctx, element, compound)
    note = "bw for %s%s after it%s" % (
        got["word"], (" " + got["word_sound"]) if got["word_sound"] else "",
        (": " + got["mean"]) if got["mean"] else "")
    return note.replace(",", ";")


def _light_verb(ctx, compound, infinitive):
    """The light verb's own entry, for a compound: کردن for فکر کردن.

    THE LIGHT VERB'S ENTRY AND NOT THE COMPOUND'S TABLE, so that کردن is
    printed the same way whether the chunk reached it through فکر کردن or on
    its own -- a book repeats a stem as it first gave it, and check_batch
    warns where it does not.  Where two verbs are spelt so (رفتن is raftan
    and roftan), the compound's own present stem says which: در رفتن's is
    `در رو`.  One compound spells its light verb with an Arabic kāf (كردن)."""
    spelt = infinitive.replace("ك", "ک").replace("ي", "ی")
    cands = _verbs_spelt(ctx, spelt)
    if len(cands) > 1:
        last = str(_Entry(ctx, compound).head.get("prs") or "").split()
        for c in cands:
            t = _table(_Entry(ctx, c), spelt[:-1])
            if last and t.get("prs") and _fold(t["prs"], ctx.L) == _fold(last[-1], ctx.L):
                return c
    return cands[0] if cands else None


# ------------------------------------------------------------ the recipe
def recipe(ctx):
    e = ctx.entry
    if (e["pos"] or "") != "verb":
        return None
    words = ctx.bare(e["headword"] or "").split()
    if not words or not words[-1].endswith(_INFINITIVE) or len(words[-1]) < 3:
        return None
    infinitive = words[-1]
    if (e["headword"] or "").strip() in (ctx.data().get("no_vb") or {}):
        return None
    # A VERB OF ANOTHER DIALECT, every sense of it tagged so -- Isfahani
    # رفدن, Khesht گربسن, Kazerun تراشتن: 27 entries, in no register an
    # edition is written in (docs/lang/fa.md: the page's own Persian, and a
    # video's spoken Tehrani).  A chunk that reaches one reached it through a
    # spelling it shares with a word of the standard language.
    if _dialect_only(ctx.sense_tags):
        return None
    me = _fold(ctx.word, ctx.L)
    reached = [f for f in ctx.rows if _fold(f.form, ctx.L) == me]
    if reached and all(f.tags in PERSON_COLUMN for f in reached):
        return None                                  # او, not آراستن

    if len(words) > 1:
        # A COMPOUND'S ENTRY: the light verb's \vb with an empty meaning, and
        # the \bw for the word it carries named in `missing` (docs/lang/fa.md:
        # never gloss the light verb's own meaning) -- but only where that
        # word is in the chunk, or the entry was reached by a bare form of
        # the light verb and is not what the chunk says.
        element = " ".join(words[:-1])
        if not _element_here(ctx, element):
            return None
        lv = _light_verb(ctx, e, infinitive)
        if lv is None:
            return None
        parts, missing, coll = _stems(_Entry(ctx, lv))
        return Parts(parts=parts, meaning="", extras_video=_video(ctx, coll),
                     missing=missing + [_bw_note(ctx, element, e)],
                     compound=_compound_parts(ctx, element, e))

    if infinitive in _index(ctx)["ends"]:
        # THE CHUNK MAY SAY THIS VERB IS PART OF ANOTHER: a preverb verb
        # written apart, whose \vb is the one to offer, or a compound the
        # dictionary knows, whose light verb is glossed with no meaning.
        got = _preverb_here(ctx, infinitive)
        if got is not None:
            ent = _Entry(ctx, got)
            parts, missing, coll = _stems(ent)
            ranked = _ranked(got)
            mean, more = _meaning(ctx, ent.headword,
                                  trim_meaning(ranked[0]) if ranked else "", ranked)
            return Parts(parts=parts, meaning=mean, extras=_extras(ctx, ent.headword),
                         extras_video=_video(ctx, coll), missing=missing + more)
        got = _compound_here(ctx, infinitive)
        if got is not None:
            row, element = got
            parts, missing, coll = _stems(_Entry(ctx, e, ctx.rows))
            return Parts(parts=parts, meaning="", extras_video=_video(ctx, coll),
                         missing=missing + [_bw_note(ctx, element, row)],
                         compound=_compound_parts(ctx, element, row))

    parts, missing, coll = _stems(_Entry(ctx, e, ctx.rows))
    mean, more = _meaning(ctx, infinitive, ctx.meaning,
                          ctx.hit.get("senses") or _ranked(e))
    return Parts(parts=parts, meaning=mean, extras=_extras(ctx, infinitive),
                 extras_video=_video(ctx, coll), missing=missing + more)
