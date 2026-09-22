# SPDX-License-Identifier: GPL-3.0-or-later
"""Chinese: a \\vb only for the two kinds of verb that come apart in a sentence.

    \\vb{睡觉}{shuìjiào}{睡了觉}{shuìle jiào}{}{}{to sleep}      separable (vo)
    \\vb{看见}{kànjiàn}{}{}{看不见}{kànbujiàn}{to see}           with a complement
    None                                                  every other verb, and
                                                          every single character

A CHINESE VERB HAS NO FORMS, so the three-form model has nothing to fill for
nearly all of them and docs/lang/zh.md glosses them with \\dw: 吃 is 吃 in
every person and time there is.  What a reader needs beside two kinds of
verb, and cannot see in the characters, is where they come apart -- 睡了一觉,
帮我的忙 and 见过面 cannot be traced back to a word without being told that
睡觉, 帮忙 and 见面 part to let something in -- and so a \\vb is offered for
those two and nothing else (docs/lang/zh.md, "A verb is given as one form"):

  slot 1  the verb in simplified characters and its pinyin as one word
  slot 2  split: a separable verb-object verb (离合词) with 了 between its
          halves, the 了 said with the half before it -- 睡了觉 shuìle jiào.
          Always the plain A了B, never the idiomatic 睡了一觉.  Blank for a
          verb with a complement.
  slot 3  can't: a verb with a resultative or directional complement, with 不
          between verb and complement, one word in pinyin with the 不
          toneless -- 看不见 kànbujiàn -- or three where the source writes
          the complement as a word of its own (zhàn bu qǐlai).  Blank for a
          separable verb.
  extras  none: nothing goes in brackets after a Chinese meaning.

WHERE EACH PIECE IS IN dict/zh.db (lib/getdict.py, built 2026-09-10):

  which kind   entry.head's `type`, zh-verb's own word for the structure:
               vo (3172 entries), vo1..vo5 (63: the digit counts the verb
               half's letters, 打⫽電話 is vo1, 露出⫽馬腳 vo2), vc (118); and
               mv (13) and sp (12), which carry a split mark too but do not
               part in teaching (急⫽救, 頭⫽痛: *头了痛), and get no \\vb.
  where        the entry's own `canonical` row, 睡⫽覺.  Every one of the
               3378 typed entries has one, its letters the headword's but
               in five English words (high⫽tea for `high tea`), and thirteen
               with Latin letters have a lower-case twin (P⫽K, p⫽k).
  characters   the entry's own row tagged exactly `Simplified-Chinese`, and
               the headword where there is none: Wiktionary keys Chinese
               under the traditional characters (睡覺) and writes the
               simplified spelling only where it differs.  Of the 3353 vo
               and vc entries 2071 have that row, and of the 1282 without
               it one Chinese word has a character the dictionary simplifies
               elsewhere (the other is Hokkien half in Latin letters, and
               gets no \\vb): 置裝, whose 置装 is only an `another spelling`
               row -- and those are mostly variant TRADITIONAL spellings
               (起牀, 喫醋, 駭怕), so they are not read, and 置裝 comes out
               traditional.  Both rows are always in the block getdict
               wrote with the entry, never a pointer's; the exact tag set
               keeps out `Second-Round-Simplified-Chinese` (跳午 for 跳舞,
               邦忙 for 幫忙) and `alternative Simplified-Chinese Hokkien`
               (放计).
  pinyin       ctx.head_sound: entry.translit, which getdict takes from the
               first zh_pron row tagged only Mandarin/Pinyin/Standard --
               shuìjiào, and not the Xi'an fēijiāo filed beside it.  A
               polyphonic word is one entry per reading, so the archaic
               睡覺 shuìjué "to wake up" is its own hit and gets no split.

THE SPLIT IS DERIVED, NOT GUESSED: the source says where the verb parts
(⫽) and that it is verb-object or verb-complement, and what goes into the
gap is the grammar zh.md states, the same for every verb of the kind.  Its
pinyin is the entry's own, cut at the same place (_syllables: 2283 of the
2287 typed verbs with pinyin cut into a syllable per character, and the
four that do not are 立flag, 卡bug and two more with Latin letters, which
get no \\vb anyway); where the cut fails the form is still given and its
sound is named in `missing`.

WHAT IS NOT ANSWERED, measured:
  - a verb said only outside Mandarin (_mandarin): 1043 of the 3353 have
    every sense tagged with another lect, 走路's second entry is Cantonese/
    Min "to flee", and Cantonese says 揸咗車, not 揸了車 -- the 了 of the
    split is Mandarin grammar.
  - a verb with no standard pinyin, which is how the source says a word is
    not standard Mandarin when the tags do not (see the recipe).
  - an old reading whose word's plain reading does not split (_old_twin):
    知道 "to know the Way" is typed vo, 知道 "to know" is not.
  - a split whose verb half is a negation: 不要⫽臉 is vo2, and *不要了脸.
  - a "complement" verb that already is a potential: 輸⫽不起 is vc, and
    输不不起 is nothing.
  - a word with Latin letters in it (開P, 卸載QQ): no syllable to cut.
Everything else Wiktionary types gets its \\vb; what it does not type and a
reader meets on the first page -- 散步, 听懂, 回来 -- and the one common
verb it types wrongly, 想⫽到 as verb-object (想了到 is not Chinese; 想不到
is), are in lib/lang/zh.verbs.json, which is read before the head line.

Standard library only: the server imports it.
"""
import functools
import re
import unicodedata

import lookup
import verbs

# ------------------------------------------------------------- the two kinds
# zh-verb's `type` for a verb-object verb, with or without the digit that
# counts the verb half's letters (vo1 打⫽電話, vo2 露出⫽馬腳).
_VO = re.compile(r"vo\d*")

# THE VERB HALF THAT IS A NEGATION.  不要⫽臉 is typed vo2 -- structurally a
# verb and its object, and 不要脸 does take its object apart in abuse (真不要
# 你的脸) -- but the split with 了 is *不要了脸: the aspect never goes inside a
# negated verb.  It is the one Mandarin entry of the 63 vo1..vo5 so shaped;
# the others (颠覆⫽国家政权, 露出⫽马脚) split as any verb does.
_NEGATIONS = frozenset("不没沒别別未無无莫勿")

# ... and the complement verb that is ITSELF a potential: 輸⫽不起 (to be a
# sore loser) is typed vc, and the 不 is already there.
_INFIXES = frozenset("不得")

# ----------------------------------------------------------- Mandarin or not
# THE SPLIT IS MANDARIN GRAMMAR, and nearly a third of the typed entries
# are not Mandarin words.  Wiktionary files every lect's words under the one
# Chinese heading and says which lect in the sense's tags: of the 3353 vo
# and vc entries, 1043 have every sense tagged with a lect that is not
# Mandarin -- Cantonese 揸車 "to drive a car", whose perfective is 揸咗車,
# not 揸了車 -- and a \\vb printing a 了 split and a Mandarin pinyin for them
# would teach a sentence nobody says.  A tag is a lect's when it names the
# family (Cantonese, Hokkien, Wu ...) or, for the Hokkien the source tags by
# town alone ('Quanzhou,Xiamen' on 70 senses, 刮 "to shave"), the town.
# Classical Chinese is here for the same reason: 主⫽義 "to uphold
# righteousness" is Classical, which has no 了 at all.
# A sense that ALSO says Mandarin is Mandarin (開開 is 'Mandarin, Min,
# Southern, colloquial'), and so is every Mandarin town and region the
# source names (Beijing, Xi'an, Sichuanese, Southwestern-Mandarin ...), and
# a region that is not a lect at all (Hong-Kong, Taiwan, Singapore).
_LECTS = frozenset((
    "Cantonese", "Hokkien", "Min", "Hakka", "Wu", "Teochew", "Xiang", "Gan",
    "Jin", "Pinghua", "Huizhou", "Taishanese", "Hainanese", "Waxiang",
    "Xiamen", "Quanzhou", "Zhangzhou", "Jinjiang", "Tong'an",
    "Classical", "Classical-Chinese"))


def _lect_tag(t):
    return t in _LECTS or t.endswith(("-Hokkien", "-Min"))


def _mandarin(tags):
    """Is a sense with these tags said in Mandarin?"""
    if "Mandarin" in tags or any(t.endswith("-Mandarin") for t in tags):
        return True
    return not any(_lect_tag(t) for t in tags)


def _tags(line):
    return set(t.strip() for t in (line or "").split(",") if t.strip())


# THE SPLIT OF AN OLD READING, WHERE THE WORD'S OWN READING HAS NONE.  A
# split belongs to one entry and not to the word: 知道 is two entries, the
# plain "to know (something)" with no type, and a literary "to know the Way,
# or, the Tao" typed vo -- so the literary hit, answered like any other,
# printed "split 知了道 zhīle dào" under every 知道 in every text, and 知了道
# is not Chinese in any register (Classical, where the Way is known, has no
# 了).  Of the 62 split entries whose every Mandarin sense is literary or
# older, two have a plain twin with no split, 知道 and 避諱 (historical
# "to observe the naming taboo", beside the plain bìhui "to avoid an
# inauspicious word"); those two get no \vb, the other 60 -- 設宴, 罷官,
# 請安, whose split is written today -- keep theirs.
_OLD = frozenset(("literary", "archaic", "obsolete", "historical", "dated",
                  "Classical", "Classical-Chinese"))


def _old_twin(ctx):
    """Is this an old reading, with a plain entry of the same word that does
    not split?"""
    lines = [t for s, t in zip(ctx.senses, ctx.entry["sense_tags"].split("\n")
                               if ctx.entry["sense_tags"] else [])
             if s.strip()]
    mand = [_tags(t) for t in lines if _mandarin(_tags(t))]
    if not mand or not all(t & _OLD for t in mand):
        return False
    head = "head" if lookup._has_col(ctx.conn, "head") else "''"
    for r in ctx.conn.execute(
            "SELECT %s AS head, sense_tags FROM entry WHERE headword = ? "
            "AND id != ? AND pos = 'verb'" % head,
            (ctx.entry["headword"], ctx.entry["id"])):
        if '"type"' in (r["head"] or ""):
            continue
        if any(_mandarin(_tags(t)) and not (_tags(t) & _OLD)
               for t in (r["sense_tags"] or "").split("\n")):
            return True
    return False


# ---------------------------------------------------------------- the meaning
# A SENSE THAT ONLY POINTS SOMEWHERE ELSE.  Of the typed entries' first
# ranked senses, 23 are "Used other than figuratively or idiomatically: see
# 炒 (chǎo), 魷魚" -- the literal reading of an idiom like 炒魷魚, sent to
# the pages of its characters -- 19 are "erhua form of 聊天 (liáotiān)" and
# a few "synonym of 仆街".  None is a meaning as it stands, and two of them
# carry one inside, in the source's own words:
#   - the literal reading after the list of pages, where Wiktionary gives
#     it: 學好 is "Used other than figuratively or idiomatically: see 學 /学,
#     好: to learn well; to master", 餵老虎 "...see 餵 /喂 (wèi), 老虎
#     (lǎohǔ); to feed a tiger" -- and for a verb with a complement the
#     literal reading is the one its can't form belongs to (学不好);
#   - the other word's gloss in quotation marks: 串門兒 is "erhua form of
#     串門／串门 (chuànmén, “to pay a visit to someone's home; to drop by”)".
# Otherwise the next Mandarin sense is taken, and where there is none the
# meaning is named in `missing` (聊天兒 "erhua form of 聊天 (liáotiān)",
# 瞧熱鬧 "synonym of 看熱鬧": the pointer does not repeat the gloss).
_POINTER = re.compile(
    r"(?i)^\s*(?:used other than figuratively or idiomatically"
    r"|erhua form of|synonym of|alternative (?:form|spelling) of"
    r"|abbreviation of|short for)\b")
_LITERAL = re.compile(
    r"(?i)^\s*used other than figuratively or idiomatically\s*:\s*see\b"
    r"[^:;]*[:;]\s*(to\s.+)$")
_QUOTED = re.compile(r"“([^“”]+)”")


def _inside(s):
    """The meaning a pointer sense carries inside it, or ""."""
    m = _LITERAL.match(s)
    if m:
        return m.group(1)
    if s.lower().lstrip().startswith("used other"):
        return ""                     # its quotes gloss the characters, not it
    q = _QUOTED.search(s)
    return q.group(1) if q else ""


def _meaning(ctx):
    """(meaning, missing): None for "the core's", which is the first ranked
    sense trimmed, when that one will do; else the first ranked sense that
    is Mandarin and says something; "" with a name in `missing` when no
    sense is both.  () for an entry with no Mandarin sense at all."""
    senses = ctx.senses
    tags = (ctx.entry["sense_tags"] or "").split("\n")
    lines = [(s, tags[i] if i < len(tags) else "")
             for i, s in enumerate(senses) if s.strip()]
    ranked = lookup.rank_senses([s for s, _t in lines], [t for _s, t in lines])
    mand = [s for s, t, _tier in ranked if _mandarin(_tags(t))]
    if not mand:
        return ()
    if not verbs.gloss_is_en(ctx.gloss):
        return None, []
    for s in mand:
        if not _POINTER.match(s):
            return (None if s == ranked[0][0] else verbs.trim_meaning(s)), []
        inside = _inside(s)
        if inside:
            return verbs.trim_meaning(inside), []
    return "", ["meaning"]


# ------------------------------------------------------------------ pinyin
# The syllables of Hanyu Pinyin, generously: every initial with every final,
# which admits a few the language never says (bü) and loses nothing it
# does.  A syllable with no initial is one of the thirteen that open with a,
# o or e -- the rest are written with y or w (yi, wu, yu).  The interjections
# m, n, ng, hm, hng are left out: no verb has one, and a syllable of one
# consonant would cut xīnán as xīn + án.
_INITIALS = ("zh", "ch", "sh", "b", "p", "m", "f", "d", "t", "n", "l", "g",
             "k", "h", "j", "q", "x", "r", "z", "c", "s", "y", "w")
_FINALS = ("a", "o", "e", "ai", "ei", "ao", "ou", "an", "en", "ang", "eng",
           "ong", "i", "ia", "ie", "iao", "iu", "ian", "in", "iang", "ing",
           "iong", "u", "ua", "uo", "uai", "ui", "uan", "un", "uang", "ueng",
           "ü", "üe", "üan", "ün", "ue")
_OPEN = ("a", "o", "e", "ai", "ei", "ao", "ou", "an", "en", "ang", "eng",
         "er", "ê")
_SYLLABLES = frozenset([i + f for i in _INITIALS for f in _FINALS]
                       + list(_OPEN))

# What stands between two syllables where the letters would not say where
# one ends: the space between words, pinyin's apostrophe (Xī'ān), a hyphen.
_SEP = " '’-"


def _toneless(s):
    """`s` with its tone marks off and lower-cased, ONE LETTER FOR ONE, so
    an index into the one is an index into the other.  ü keeps its dots:
    lǜ and lù are different syllables.  None where a letter will not come
    down to one."""
    out = []
    for ch in s:
        d = "".join(c for c in unicodedata.normalize("NFD", ch)
                    if not unicodedata.combining(c) or c == "\u0308")
        d = unicodedata.normalize("NFC", d).lower()
        if len(d) != 1:
            return None
        out.append(d)
    return "".join(out)


def _syllables(p, n):
    """Where the n syllables of pinyin `p` are, as (start, end) indices into
    it -- or None when it will not cut into exactly n.

    AS MANY SYLLABLES AS CHARACTERS: that is the whole of what makes the
    cut decidable.  Longest first, backtracking, with pinyin's own rule that
    a syllable opening with a, o or e after another one is marked (Xī'ān,
    píng'ān): so jiāngé is jiān + gé and never jiāng + é, and fāngàn is fān
    + gàn.  An erhua r (玩兒 wánr) is a syllable of its own when it is
    written onto the one before, because 兒 is a character of its own.
    """
    s = unicodedata.normalize("NFC", (p or "").strip())
    b = _toneless(s)
    if not s or b is None:
        return None
    size = len(s)

    @functools.lru_cache(maxsize=None)
    def go(i, k):
        j0, apart = i, i == 0
        while j0 < size and s[j0] in _SEP:
            j0 += 1
            apart = True
        if j0 == size:
            return () if k == 0 else None
        if k == 0:
            return None
        for j in range(min(size, j0 + 6), j0, -1):
            seg = b[j0:j]
            if seg in _SYLLABLES:
                if not apart and seg[0] in "aoeê":
                    continue
            elif not (seg == "r" and not apart):
                continue
            rest = go(j, k - 1)
            if rest is not None:
                return ((j0, j),) + rest
        return None

    return go(0, n)


def _cut(p, n, at):
    """Pinyin `p` of a word of `n` characters as (the sound before character
    `at`, the sound from it on, whether the source wrote them as two words),
    or None.  The halves keep whatever the source wrote inside them (kāi |
    wánxiào, zhàn | qǐlai)."""
    spans = _syllables(p, n)
    if spans is None or not 0 < at < n:
        return None
    p = unicodedata.normalize("NFC", p.strip())
    a, b = spans[at - 1][1], spans[at][0]
    return p[:a], p[b:], " " in p[a:b]


# ------------------------------------------------------------ the hand table
_TABLE = {}


def _table(ctx):
    """lib/lang/zh.verbs.json as {simplified word: (kind, where it splits)}.
    The file writes each word as the source does, with ⫽ where it parts:
    "散⫽步" under "vo", "听⫽懂" under "vc"."""
    d = ctx.data()
    got = _TABLE.get(id(d))
    if got is not None and got[0] is d:
        return got[1]
    out = {}
    for kind in ("vo", "vc"):
        for w in d.get(kind) or ():
            w = str(w).strip()
            if w.count("⫽") == 1 and w[0] != "⫽" and w[-1] != "⫽":
                out[w.replace("⫽", "")] = (kind, w.index("⫽"))
    _TABLE.clear()
    _TABLE[id(d)] = (d, out)
    return out


# ------------------------------------------------------------------ recipe
def recipe(ctx):
    head = ctx.entry["headword"] or ""
    simp = ctx.pick(exact="Simplified-Chinese", own=True)
    word = simp.form if simp is not None else head
    # WHICH KIND: the hand table first -- it is where the source's type is
    # corrected (想到) -- and then the head line's.  A word the table names
    # must be a verb entry: 过去 is also "the past".
    kind, at = _table(ctx).get(word, (None, None))
    if kind is None:
        typ = str(ctx.head.get("type") or "")
        kind = "vc" if typ == "vc" else ("vo" if _VO.fullmatch(typ) else None)
        if kind is None:
            return None
        canon = ctx.pick(exact="canonical", own=True,
                         where=lambda f: f.form.count("⫽") == 1
                         and f.form.replace("⫽", "") == head)
        if canon is None:
            return None
        at = canon.form.index("⫽")
    elif (ctx.entry["pos"] or "") != "verb":
        return None
    # THE CUT IS TRANSFERRED, not re-found: the traditional canonical row and
    # the simplified word are the same length (2071 of the 2071 vo and vc
    # entries that have both), and simplification changes a character,
    # never the count.  The script test is what refuses 開P and 卸載QQ.
    if len(word) != len(head) or not 0 < at < len(word) \
            or not ctx.in_script(word):
        return None
    a, b = word[:at], word[at:]
    if kind == "vo" and a[0] in _NEGATIONS:
        return None
    # an infix standing between a verb and a complement (輸 | 不起), not a
    # verb that is itself 得 (得⫽到 "to obtain" is 得不到, as it should be)
    if kind == "vc" and ((len(b) > 1 and b[0] in _INFIXES)
                         or (len(a) > 1 and a[-1] in _INFIXES)):
        return None
    # NO STANDARD PINYIN, NO MANDARIN WORD.  Wiktionary gives the standard
    # Mandarin reading of every word said in standard Mandarin, and getdict
    # keeps only that one (shuìjiào, never a Sichuanese or Xi'an reading).
    # The 105 typed verbs that have none and pass the sense tags are dialect
    # words whose lect the tags do not name -- each has a dialect's
    # pronunciation and no standard one: Cantonese 食飯 /sɪk̚² faːn²²/, Wu
    # 起陣頭, Sichuanese 耍朋友, Min 拆婚 -- save two with no pronunciation
    # at all (嬎蛋, 下小屌).  拆婚 shows what answering them costs: its
    # `Simplified-Chinese` row is 离婚, a different word, and its \vb came
    # out as 离婚's with the pinyin to fill.  A \vb left to fill would be a
    # Mandarin entry for a word Mandarin does not say; the \dw is right.
    sound = ctx.head_sound or ""
    if not sound:
        return None
    got = _meaning(ctx)
    if got == ():
        return None                                 # no Mandarin sense at all
    if _old_twin(ctx):
        return None                                 # 知道 "to know the Way"
    meaning, missing = got

    halves = _cut(sound, len(word), at)
    if halves is None:
        missing = ["pinyin of the %s form"
                   % ("split" if kind == "vo" else "can't")] + missing
    if kind == "vo":
        # 了 IS SAID WITH THE HALF BEFORE IT, as zh.md writes every aspect
        # particle (chīle, kànzhe), and the object stands free: shuìle jiào.
        two = (a + "了" + b, (halves[0] + "le " + halves[1]) if halves else "")
        three = ("", "")
    else:
        # ONE WORD, 不 TONELESS, as Wiktionary spells its own 看不見
        # kànbujiàn -- and the apostrophe pinyin puts before a syllable that
        # opens with a, o or e, which after bu is now inside the word.
        # BUT THE SOURCE'S WORDS STAY ITS WORDS: where it writes the verb and
        # a two-syllable complement apart, as pinyin's rules ask (站起來 zhàn
        # qǐlai, 說清楚 shuō qīngchu, 弄清楚: 3 of the 123), 不 goes into that
        # space as a word of its own, zhàn bu qǐlai, and not zhànbuqǐlai.
        if halves:
            pa, pb, apart = halves
            if apart:
                s3 = pa + " bu " + pb
            else:
                opens = _toneless(pb[:1]) or ""
                glue = "'" if opens in ("a", "o", "e") else ""
                s3 = pa + "bu" + glue + pb
        else:
            s3 = ""
        two = ("", "")
        three = (a + "不" + b, s3)
    return verbs.Parts(parts=[(word, sound), two, three], meaning=meaning,
                       missing=missing)
