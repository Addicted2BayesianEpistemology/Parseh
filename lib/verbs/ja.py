"""Japanese: the \\vb of a verb -- dictionary form, -masu stem, -te form -- and its class.

    \\vb{書く}{kaku}{書き}{kaki}{書いて}{kaite}{to write (godan; tr.)}
    \\vb{勉強する}{benkyō suru}{勉強し}{benkyō shi}{勉強して}{benkyō shite}{to study (suru; tr./intr.)}
    \\vb{いらっしゃる}{irassharu}{いらっしゃい}{irasshai}{いらっしゃって}{irasshatte}{to go (godan; intr.; hon.)}

WHAT docs/lang/ja.md ASKS FOR, and where each piece is in dict/ja.db:

  slot 1  the dictionary form and its rōmaji: the entry's headword and the
          lemma's own sound (ctx.head_sound), never the reached form's --
          書いて reaches 書く with the hit's translit `kaite`.
  slot 2  the -masu stem: the head line's own row whose note is exactly
          `stem`, with the rōmaji Wiktionary wrote beside it (`kaki`).
  slot 3  the -te form: the head line's own `past` row (書いた kaita) with
          its last kana and syllable turned, た -> て, だ -> で.
  extras  the class, always; `tr.`/`intr.`/`tr./intr.` where the source
          says; `hon.`/`hum.` where the sense printed is tagged so.

WHY THE -te FORM IS MADE FROM THE PAST AND NOT READ.  The past is on the
head line of every conjugated verb (12,074 of the 12,750 verb entries,
each with its rōmaji); a `conjunctive` row -- the -te form itself -- is
on 89, only 21 of them the entry's own, and three are other words'
pointers filed under a homograph (いる -> いって, 持つ -> 以て, 統べる ->
すべて).  The past and the -te form differ in the last kana and nothing
else for every Japanese verb, 行った / 行って and 問うた / 問うて tōte
included -- the turned past equals the `conjunctive` row on the other 76
-- so the turn is not a guess: it is the one spelling rule the -te form
has.

WHY ONLY THE HEAD LINE'S OWN ROWS.  Most of a verb's rows are the
Classical Japanese table (ja-conj-bungo) printed under it, and its tags
share names with the modern forms: 書く has `書きき past` and `書けば
causative`, 食べる has `食ぶ stem terminative`.  The head line's rows come
first and say exactly `stem` and `past`; the classical table's pasts end in
き or けり and never in た.  And the entry's rows are not all its own:
another page's "past of X" is filed under the FIRST entry spelt X, so 来る
kuru carries kitaru's 来った `past` and 来り `continuative, stem` -- and a
pointer with ONE tag has no comma to give it away (書く's 645371 書いた
`past`, from the 書いた page; 3,531 verbs have such rows).  Filed after
the entry's own, they lose to them by rowid; where the entry has no past
of its own they would not, and だ, です and いきます would each borrow a
pointer's (だった, でした, いきました).  So a row counts as the entry's own
only inside the block getdict wrote with the entry (`_own`), and among
those the first by rowid wins.

THE CLASS IS THE HEAD TEMPLATE'S, and it is checked against the rows.
getdict keeps ja-verb's `type` as entry.head's `class` (godan, ichidan,
suru, irregular).  12,038 of the 12,039 classed verbs with a stem and a
past fit their class exactly (`_fits`: 書く/書き/書いた is godan, 食べる/
食べ/食べた ichidan); the one that does not is the suffix る, whose
"stem" is 糉, and it gets no \\vb.  Where the head says nothing (35 verbs:
盛り上がる, 撓める, 焙じる...) the class is the one the rows fit, which is
the same test run the other way (27 godan, 8 ichidan, none left without
one).  The classical types kept as `type`
(shimo ni, yo, kami ni, rahen, yodan: 147 verbs) have no modern stem or
past, so no \\vb either.

Standard library only: the server imports it.
"""
import re

import verbs
import lookup

# The labels a class is printed with (docs/lang/ja.md): what builds every
# form the entry does not print.
CLASSES = ("godan", "ichidan", "suru", "irregular")

# The modern -masu stem of a godan verb: its dictionary ending moved to the
# i row.  Katakana too: 失ウ is written in it, 失イ / 失ッタ.
I_ROW = {"く": "き", "ぐ": "ぎ", "す": "し", "つ": "ち", "ぬ": "に",
         "ぶ": "び", "む": "み", "る": "り", "う": "い",
         "ク": "キ", "グ": "ギ", "ス": "シ", "ツ": "チ", "ヌ": "ニ",
         "ブ": "ビ", "ム": "ミ", "ル": "リ", "ウ": "イ"}

# The past's last kana, and the -te form's.
TE = {"た": "て", "だ": "で", "タ": "テ", "ダ": "デ"}

# SAID AS THE WORD WITHOUT A CLASS OF ITS OWN.  Wiktionary files する under
# ja-verb type `suru` like every noun + する, and docs/lang/ja.md keeps
# `suru` for those (勉強する, 愛する) and calls する itself `irregular`, as it
# calls 来る.  為る is the same word in kanji.
IRREGULAR_HEADS = frozenset(("する", "為る"))

# What a sense says about the verb's register, in docs/lang/ja.md's words.
# The sense printed is tagged honorific for 21 of the verbs given a \vb
# (いらっしゃる, おっしゃる, 召し上がる) and humble for 26 (申す, 参る, 伺う,
# 存じる).  `polite` and `formal` are not asked for, and ござる's `polite`
# is not what `hon.` means.
REGISTER = (("honorific", "hon."), ("humble", "hum."))

# ...and about its transitivity, where the head template does not say:
# for 95 verbs the head is silent and the sense printed is tagged (手伝う
# transitive, 泣く intransitive), beside 5,925 whose head says.
SENSE_TR = {"transitive": "tr.", "intransitive": "intr.",
            "ambitransitive": "tr./intr."}

# A MEANING THAT IS A SPELLING LIST.  A kana page that files several words
# under one reading, and a kanji page with more than one spelling, open the
# sense with the spellings it is about: あう is "会う: to meet", 聞く "聞く,
# 聴く: to hear, to listen (to)", 覚える "覚える, 憶える: to recall".  517 of
# the classed verbs' first senses start that way.  The list is Japanese in
# the gloss's slot and repeats the headword; the meaning is after the colon.
_SPELLINGS = re.compile(r"^\s*([^:：]{1,60}?)\s*[:：]\s+(\S.*)$")

# A SENSE THAT ONLY POINTS AT THE PAGE IT WAS ON.  A suru verb's own entry
# often says "Same as above." (贖罪, 看破, 四苦八苦) meaning the noun's
# senses above it on the Wiktionary page, which the reader does not have;
# an idiom's first sense can be "Used other than figuratively or
# idiomatically: see 蓋, を, 開ける."  Neither is a meaning, and 29 verbs'
# first ranked sense is one.  The next ranked sense is taken if there is
# one (蓋を開ける: "to start (an event)"), and otherwise the meaning is left
# for the annotator and named in `missing` (26 verbs).
_POINTER = re.compile(
    r"(?i)^\s*(?:(?:same as|see|to do)\b[^;]*\b(?:above|below)\b\.?"
    r"|used other than figuratively or idiomatically\b.*)\s*$")

# THE TRANSITIVITY WRITTEN INTO THE GLOSS, which the parenthesis after it
# says again in the house's words: うたう (歌う) is "(transitive,
# intransitive) to sing", and its \vb read `(transitive, intransitive) to
# sing (godan; tr./intr.)`.  Five verbs' first senses; taken out of the
# meaning, never out of the extras.
_TR_NOTE = re.compile(r"(?i)\(\s*(?:in)?transitive(?:\s*(?:,|/|or|and)\s*"
                      r"(?:in)?transitive)?\s*\)\s*")


def _own(rows):
    """The entry's own rows: the block getdict wrote with the entry.

    getdict inserts an entry's rows together, headword first, and only
    after every entry is in does it file the pointer pages' rows -- so the
    entry's own are the unbroken run of rowids from its first row, and
    everything after a gap is somebody else's page pointing here.  A comma
    also ends the run: a pointer's tags are comma-joined, and the very last
    entry in the file has no gap before the pointers.
    """
    out = []
    for i, f in enumerate(rows):
        if f.rowid != rows[0].rowid + i or "," in f.note:
            break
        out.append(f)
    return out


def _stem(own):
    """The head line's -masu stem, or None.

    TWO STEMS, ONE OF THEM THE -masu STEM.  The honorific -aru verbs list
    both of theirs, いらっしゃり and いらっしゃい (おっしゃる, 下さる, なさる,
    ござる likewise); ます is added to the second (いらっしゃいます), so that
    is the one printed.  Every other second stem is getdict's case-folded
    copy (TSし, tsし) or the second word of a kana page that holds two
    (たく: 焚く's たき, then 託する's たくし), and the first is taken.

    A RŌMAJI FILED AS A TAG.  wiktextract read two stems' romanisation as a
    tag: 感じる's stem is `感じ` noted `kanji stem`, 舐める's `舐め` noted
    `name stem`, both with no rōmaji.  Such a row is taken, with that word
    as its sound, only where the verb's own past proves it (kanjita,
    nameta): a tag is otherwise a tag.
    """
    stems = [f for f in own if f.tags == {"stem"} and f.form]
    forms = [f.form for f in stems]
    for f in stems:
        if f.form[-1:] == "い" and f.form[:-1] + "り" in forms:
            return f.form, f.roman
    if stems:
        return stems[0].form, stems[0].roman
    past = _past(own)
    for f in own:
        rest = f.tags - {"stem"}
        if "stem" in f.tags and len(rest) == 1 and f.form and not f.roman:
            w = next(iter(rest))
            if re.fullmatch(r"[a-zāēīōū']+", w) and past and past[1].startswith(w):
                return f.form, w
    return None


def _past(own):
    """The head line's past (書いた kaita), or None: the first own row
    noted exactly `past` that ends in た or だ -- the classical table's
    pasts (書きき, 書きけり) end otherwise."""
    for f in own:
        if f.tags == {"past"} and f.form[-1:] in TE:
            return f.form, f.roman
    return None


def _fits(cls, head, stem, past):
    """Do the stem and past the source gives belong to a verb of this class
    spelt `head`?  The morphology each class has, and nothing looser: a
    godan verb's stem is its ending moved to the i row (書く 書き, and the
    -aru verbs' い: いらっしゃる いらっしゃい); an ichidan verb's is the
    headword without る; a suru verb's is the noun + し (勉強 勉強し) or the
    headword with する -> し, ずる -> じ (愛する 愛し, 信ずる 信じ); する and
    来る make し and 来.  Every class but godan adds た to the stem."""
    if past[-1:] not in TE:
        return False
    plus_ta = past == stem + past[-1]
    if cls == "godan":
        end = head[-1:]
        return (end in I_ROW and past[:len(stem) - 1] == stem[:-1]
                and (stem == head[:-1] + I_ROW[end]
                     or (end in "るル" and stem == head[:-1] + "い")))
    if cls == "ichidan":
        return head[-1:] in "るル" and stem == head[:-1] and plus_ta
    if cls == "suru":
        return plus_ta and (stem == head + "し"
                            or (head.endswith("する") and stem == head[:-2] + "し")
                            or (head.endswith("ずる") and stem == head[:-2] + "じ"))
    if cls == "irregular":
        if head in IRREGULAR_HEADS:
            return plus_ta and stem == "し"
        return plus_ta and (
            (head.endswith("来る") and stem == head[:-2] + "来")
            or (head.endswith("くる") and stem == head[:-2] + "き"))
    return False


def _class(ctx, head, stem, past):
    """The class to print, or "" when the rows fit none; None when the rows
    contradict the class the head template gave (the junk the rows of
    the suffix る are)."""
    if head in IRREGULAR_HEADS:
        return "irregular" if _fits("irregular", head, stem, past) else None
    cls = ctx.head.get("class") or ""
    if cls in CLASSES:
        return cls if _fits(cls, head, stem, past) else None
    # no class on the head line: the one the rows fit.  Irregular before
    # ichidan, because 来る / 来 / 来た fits ichidan too.
    for c in ("irregular", "suru", "ichidan", "godan"):
        if _fits(c, head, stem, past):
            return c
    return ""


def _ranked(ctx):
    """The senses as lookup ranks them for the hit, each with its tags as a
    set (an `obj:` tag, which carries the template's own words, left out).
    Paired before the blank lines go, so a tag stays with its sense."""
    tags = (ctx.entry["sense_tags"] or "").split("\n")
    pairs = [(s, tags[i] if i < len(tags) else "")
             for i, s in enumerate(ctx.senses) if s.strip()]
    return [(s, set(x.strip() for x in t.split(",") if x.strip() and ":" not in x))
            for s, t, _tier in lookup.rank_senses([p[0] for p in pairs],
                                                  [p[1] for p in pairs])]


def _spelt(s):
    """A sense as (the spellings it opens with, the rest): ("飲む, 呑む: to
    drink") -> (["飲む", "呑む"], "to drink"); ([], s) for a plain one."""
    m = _SPELLINGS.match(s)
    if m:
        words = [w for w in re.split(r"[,、]\s*", m.group(1)) if w]
        if words and all(_japanese(w) for w in words):
            return words, m.group(2)
    return [], s


def _meaning(ranked, spelling=""):
    """(the meaning to print, the tags of the sense it is, whether there
    was nothing but pointers to print).

    The first ranked sense that is not a pointer -- or, where the chunk
    writes the verb in one of the entry's other spellings, the first that
    says it is about that spelling: とる is "取る: to take" first and
    "撮る: to take (a photograph)" further down, and a chunk with 撮った
    wants the second.  Trimmed as the core trims its own
    (verbs.trim_meaning), from the ranking lookup gives the hit, so where
    nothing is skipped this is ctx.meaning, and the register printed is
    that sense's."""
    plain = [(s, tags) for s, tags in ranked if not _POINTER.match(s)]
    if not plain:
        return "", (ranked[0][1] if ranked else set()), bool(ranked)
    pick = plain[0]
    if spelling:
        pick = next((p for p in plain if spelling in _spelt(p[0])[0]), pick)
    return verbs.trim_meaning(_TR_NOTE.sub("", _spelt(pick[0])[1])), pick[1], False


def _suffix(a, b):
    """The longest common ending of two strings."""
    n = 0
    while n < min(len(a), len(b)) and a[-1 - n] == b[-1 - n]:
        n += 1
    return a[len(a) - n:] if n else ""


def _shared(a, b):
    """How many characters two strings begin with in common."""
    n = 0
    while n < min(len(a), len(b)) and a[n] == b[n]:
        n += 1
    return n


def _respelling(ctx, own, head, forms):
    """(the spelling, the three forms in it) when the chunk writes this verb
    in one of the entry's own other spellings, else None.

    飲む HAS NO ENTRY OF ITS OWN: Wiktionary files it under the kana のむ,
    with 飲む, 呑む and 喫む as its `alternative kanji` rows -- and so does
    分かる under わかる, 取る and 撮る under とる, 休む under やすむ, 歌う under
    うたう, and 見つける under 見付ける (7 of 96 common verbs).  A chunk with
    飲んだ was offered \\vb{のむ}{nomu}{のみ}{nomi}{のんで}{nonde}, in a
    spelling the text does not use.  The other spelling is a row the source
    wrote for this entry, and it differs from the headword in a front part
    only (飲 for の, the ending む shared), which the stem and the past
    share too: so the three forms are the source's own with that part
    replaced -- 飲む, 飲み, 飲んで.

    WHICH SPELLING IS THE CHUNK'S is decided by the forms, not the first
    kanji: the spelling whose three forms begin the most like the chunk's
    word, and only if they do so better than the headword's own.  Asking
    only whether the word begins with the replaced part took 仰有る for 仰る
    (おっしゃる lists both, and both begin with 仰), 蹴落した for 蹴落とす and
    註釋 for 註釈: asked with each of the verbs' 6,641 alternative kanji,
    184 came out in a spelling other than the one asked for, and 16 do now
    -- each a spelling with okurigana left out (刈入 for 刈り入れ), given
    the nearest one the entry lists (刈入れする).
    """
    w = ctx.word or ""                     # the core hands it over bare
    if not w:
        return None
    best, score = None, max(_shared(w, x) for x in forms)
    for f in own:
        if not {"alternative", "kanji"} <= f.tags or not f.form or f.form == head:
            continue
        tail = _suffix(f.form, head)
        ps, ph = f.form[:len(f.form) - len(tail)], head[:len(head) - len(tail)]
        if not (tail and ps and ph) or not all(x.startswith(ph) for x in forms):
            continue
        alt = [ps + x[len(ph):] for x in forms]
        got = max(_shared(w, x) for x in alt)
        # the word has the whole replaced part, and where it parts from all
        # three forms right after it, it does so in kana -- an ending none
        # of them has (飲まない) and not another kanji (註釋 is not 註釈)
        if got > score and (got > len(ps)
                            or (got == len(ps) and _kana(w[got:got + 1]))):
            best, score = (f.form, alt), got
    return best


def _kana(s):
    """Is `s` (a character or more) kana?"""
    return bool(s) and all("぀" <= ch <= "ヿ" for ch in s)


def _japanese(w):
    """Is `w` a word in the Japanese script (kana, kanji, 々)?  Written
    here and not asked of ctx.in_script, which lets any letter of the
    registry's range through -- including the full-width Latin a spelling
    list never holds."""
    return bool(w) and all(
        "぀" <= ch <= "ヿ" or "㐀" <= ch <= "鿿"
        or "豈" <= ch <= "﫿" or ch in "々〆ヶ" for ch in w.strip())


def _te(past):
    """The -te form from the past: 書いた kaita -> 書いて kaite."""
    form, roman = past
    te = form[:-1] + TE[form[-1]]
    m = re.search(r"(t|d)a$", roman or "")
    return te, (roman[:-1] + "e") if m else ""


def recipe(ctx):
    if (ctx.entry["pos"] or "") != "verb":
        return None                   # i-adjectives are `adj`; nouns `noun`
    if ctx.head.get("type") and not ctx.head.get("class"):
        return None                   # a classical-only verb: no modern forms
    own = _own(ctx.rows)
    stem, past = _stem(own), _past(own)
    if stem is None or past is None:
        # THE PAGES THAT ARE NOT A CONJUGATED VERB: 529 of the verb entries.
        # 381 are only a form of another verb -- 行った "past tense of 行く",
        # 居 "stem forms of いる", している "-te iru form of する" -- whose
        # lemma is an entry of its own; the rest are だ and です (on the
        # never-gloss list, filed as verbs), 候, and one-kana pages (す, や).
        return None
    head = ctx.entry["headword"] or ""
    cls = _class(ctx, head, stem[0], past[0])
    if cls is None:
        return None
    missing = []

    # SLOT 1.  A noun + する verb is filed under the noun -- entry 勉強, pos
    # verb, translit `benkyō suru`, stem 勉強し -- and a \vb of it is whole in
    # every slot (docs/lang/ja.md), so the form is the noun + する.  Its
    # sound is the entry's when that says `suru`; 遅延's says `tien` (the
    # Kunrei spelling, beside the noun entry's `chien`), and its own stem
    # row says `chien shi`, from which the verb is `chien suru`.
    f1, s1 = head, ctx.head_sound
    if cls == "suru" and stem[0] == head + "し":
        f1 = head + "する"
        if not re.search(r"suru$", s1 or ""):
            s1 = re.sub(r"shi$", "suru", stem[1]) if stem[1].endswith("shi") else ""
    if not s1:
        missing.append("rōmaji of the dictionary form")

    # SLOT 2 and 3, each with the rōmaji Wiktionary wrote.  Where a stem has
    # none but the past has (or the other way), and the past IS the stem +
    # た -- every class but godan -- the one is the other with `ta` off or
    # on.  Every head past in dict/ja.db carries its rōmaji, and every head
    # stem but three (感じる and 舐める, whose rōmaji _stem finds in a tag,
    # and the suffix る's); the rule is for a dictionary that does not, and
    # it is never used on a godan verb, whose 書き / 書いた share no ending
    # to take off.
    f2, s2 = stem
    f3, s3 = _te(past)
    plus_ta = past[0] == f2 + past[0][-1]
    if not s2 and plus_ta and re.search(r"[td]a$", past[1] or ""):
        s2 = past[1][:-2]
    if not s3 and plus_ta and s2:
        s3 = s2 + ("de" if past[0][-1] in "だダ" else "te")
    if not s2:
        missing.append("rōmaji of the -masu stem")
    if not s3:
        missing.append("rōmaji of the -te form")

    # the chunk's own spelling, where it is one of the entry's (_respelling)
    alt = _respelling(ctx, own, head, (f1, f2, f3))
    if alt:
        f1, f2, f3 = alt[1]

    # THE KANA OF A KANJI HEADWORD, which a video's line prints after it and
    # a book's \vb never does -- the chunk's kana line says it there
    # (docs/lang/ja.md: `書く かく kaku · stem 書き kaki · …`).  The entry's
    # reading (書く かく), with the する slot 1 added to a noun + する verb
    # (勉強 べんきょう -> 勉強する べんきょうする); or, for a verb filed under
    # its kana and printed in the chunk's kanji, that kana (のむ for 飲む,
    # whose entry has no reading).  One string, as the kana line is written:
    # the head template spaces a phrase's words (持って来る もって くる).
    kana = re.sub(r"\s+", "", ctx.entry["reading"] or "")
    if not _kana(kana):
        kana = head if _kana(head) else ""
    if kana and f1.endswith("する") and not head.endswith("する") \
            and not kana.endswith("する"):
        kana += "する"
    reading = kana if kana and kana != f1 and not _kana(f1) else ""

    extras = []
    if cls:
        extras.append(cls)
    else:
        missing.append("the class (godan, ichidan, suru or irregular)")

    meaning, tags, junk = _meaning(_ranked(ctx), alt[0] if alt else "")
    if junk and (ctx.gloss or "").strip().lower() == "en":
        missing.append("the meaning (the dictionary only points at another sense)")

    # TRANSITIVITY: the head template's, which is about the verb and so
    # true whichever meaning the annotator keeps (開く hiraku is tr./intr.
    # though its first sense is tagged intransitive); where it is silent,
    # the tag of the sense printed.
    tr = ctx.head.get("tr") or ""
    if tr not in ("tr.", "intr.", "tr./intr."):
        got = [SENSE_TR[t] for t in ("ambitransitive", "transitive", "intransitive")
               if t in tags]
        tr = ("tr./intr." if "tr./intr." in got or len(got) > 1
              else got[0] if got else "")
    if tr:
        extras.append(tr)
    # REGISTER: of the sense printed only.  食べる's third sense is `archaic,
    # humble` and 食べる is not a humble verb; いらっしゃる's every sense is
    # honorific.
    extras += [lab for tag, lab in REGISTER if tag in tags]

    return verbs.Parts(parts=[(f1, s1), (f2, s2), (f3, s3)],
                       meaning=meaning, extras=extras, missing=missing,
                       reading=reading)
