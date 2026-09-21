# Chinese — the annotation conventions

How a Chinese sentence becomes a glossed line: what goes into each field and
how it is written. These rules bind both the reading editions and the video
captions; they are embedded whole into every prompt that asks for Chinese
annotation, so they are written as instructions to the annotator.

Two of the field names are languages, and neither is a claim about one: `fa`
is the text in the target language — Chinese here — and `en` is the gloss
beside it. They are the names Persian and English left behind from the days
when they were the only two languages the toolbox had, and they are the same
two keys in every book and every video. Which language the gloss is written
in is the book's or the video's own choice, `"gloss"` in `book.json` /
`video.json`, and English when the key is absent. This file is about Chinese
as the language being **taught**: the examples below gloss into English
because they must gloss into something, and every rule that turns on the
gloss language says so.

## The text field

`fa` reproduces the source **verbatim**: the same characters, the same
punctuation, the source's own oddities included — an uncommon character, a
caption's ASR slip. Chinese has no word separator, so a sentence is split
into chunks at the character boundaries you choose, and the chunks joined
back with **nothing between them** must reproduce the sentence exactly,
character for character — a machine checks that. (A source that does put a
space in — around a Latin word, a figure, a date — keeps it, inside the chunk
it falls in.) **Never correct the text in `fa`** — the correction goes in
`note` (videos) or in the vocabulary line (books).

Nothing comes off a Chinese character: there is no layer of marks here as
there is in Persian and Arabic. What a reading edition writes over it is
**pinyin, one word at a time**, in its first pass, from the chunk's `words`
(below) — and then the same sentence with nothing over it, the way a Chinese
book prints it, and once more set vertically, all from these same
characters. **No pinyin ever goes into `fa`**: the
sound is a field of its own, and a Chinese book that printed pinyin between
the characters would be teaching a page nobody in China prints.

**The punctuation is full-width, and stays full-width**: 。 ， 、 ； ： ？ ！
「 」 『 』 （ ） 《 》 【 】 and the ellipsis ……. Do not replace a mark with
its ASCII twin, do not put a space after one (a full-width mark carries its
own), and do not decide between 、 and ， — the enumeration comma between items
of a list and the ordinary comma between clauses are two marks, and the
source has already chosen. Quotation marks are the source's own: a mainland
book uses “ ” and a typeset one often 「 」, and both stay as printed.

**Figures are the source's**: 一九四九年 and 2024年 are both correct Chinese
and neither is normalised into the other. The registry gives Chinese the
Latin digits because that is what a modern book numbers its chapters with;
that is about the toolbox's labels, not about the text.

**Simplified characters.** Everything `zh` teaches is written in them, the
fonts are the SC cuts, and the dictionary and the translation model are
fetched for Simplified (`zh-Hans`). A **traditional** source is converted
**once, whole, before annotation**, and the conversion is recorded in the
book's or video's `note` — never chunk by chunk while glossing, and never
half of it. The conversion is not mechanical in one direction: several
traditional characters share one simplified form, and a machine going the
other way guesses. Read the converted text once with those in mind: 干 stands
for both 乾 (dry) and 幹 (to do), 发 for 發 (to send) and 髮 (hair), 里 for 裡
(inside) and 里 (a village, a mile), 后 for 後 (after) and 后 (a queen), 面 for
麵 (noodles) and 面 (a face). Where the source's own word is the one lost in
the conversion, the vocabulary line is where you say so. A source that mixes
the two scripts is a source that has not been converted yet.

## Reading

This language has no reading field: the `kana` key is ignored where it
appears, and nothing asks for one.

That is the one place Chinese and Japanese part company, and it is worth a
sentence, because the two look alike on the page. Japanese has a reading
field because kana is a reading **in the language's own script** — a Japanese
child reads it, a Japanese book prints it over the kanji — and the rōmaji
beside it is a second, foreign layer. Chinese has no phonetic script of its
own. Pinyin is the only romanisation there is, it is what a Chinese child
learns to type with and nothing more, and it goes where every other
language's transliteration goes, in `tr`. **One romanisation, not two
layers.**

So a character with more than one reading — 行 *xíng* to walk, *háng* a row;
长 *cháng* long, *zhǎng* to grow; 了 *le* the particle, *liǎo* to finish;
乐 *lè* happy, *yuè* music — is settled in `tr` and in the word's own pinyin
in `words`, and that alone is reason enough for the transliteration to be on
every glossed chunk. The pinyin a word wears over the text is not a reading
field either: it is that word's entry in `words`, and `tr` stays the chunk's.

## Transliteration

`tr` is **Hanyu Pinyin with tone marks**, of what is actually said in the
chunk. It is on every glossed chunk without exception; a chunk with a `voc`
and no `tr` is not finished.

- **Tone marks, never tone numbers.** `nǐ hǎo`, not `ni3 hao3` and not
  `ni hao`. The four are ā á ǎ à, and the mark sits on a or e when there is
  one (`hǎo`, `xiè`), on the o of ou (`gǒu`), and otherwise on the last
  vowel written (`liù`, `guī`, `duì`). A syllable in the **neutral tone
  carries no mark at all**: `māma`, `xièxie`, `de`, `le`, `ma`, `zhuōzi`.
- **ü keeps its two dots** where the sound is that vowel: `nǚ`, `lǜ`,
  `qùnián`. After **j q x y** it is written `u`, because nothing else can
  stand there: `jū`, `qù`, `xǔ`, `yǔ`.
- **Write words, not syllables.** This is the rule that is broken most
  often. 中国 is `Zhōngguó`, one word; 我们 is `wǒmen`; 图书馆 is
  `túshūguǎn`; 今天 is `jīntiān`. A verb keeps its aspect particle attached
  (`chīle`, `kànzhe`, `qùguo`) and its suffixed complement too (`kànjiàn`,
  `chīwán`). Standing free are the sentence-final particles (`ma`, `ne`,
  `ba`, `a`), the three *de* (`de`), the negations (`bù`, `méi`), and the
  measure word (`yí ge rén`, `sān běn shū`).
- **The apostrophe divides syllables that would otherwise run together**,
  and only those: before a syllable beginning with **a, o or e** —
  `Xī'ān` (two syllables, not `xian`), `píng'ān`, `nǚ'ér`, `Tiān'ānmén`.
  Nowhere else.
- **Er-hua is written into the word**: `nǎr`, `wánr`, `yìdiǎnr`, `xiǎoháir`.
- **Capitals for proper names only** — `Běijīng`, `Lǐ Míng`, `Zhōngguó`,
  `Chángchéng` — and not for the first word of a sentence. A chunk is a
  slice of a sentence, and a rule that capitalised its first word would
  spell the same chunk two ways depending on where it fell.
- **Write the tones the words have, not the tones the sentence says.**
  Third tone before third tone is said as a second, and 你好 is nonetheless
  `nǐ hǎo` and never `ní hǎo`: the reader is learning the word, and the
  sandhi is automatic for anyone who says it aloud. The **two exceptions
  are 不 and 一**, whose changed tone is part of how pinyin is written
  everywhere: `bù hǎo` but `bú shì`, `bú duì`; `yì bēi`, `yì zhāng` but
  `yí ge`, `yí kuài` — and plain `yī` when it is counting or a figure.
- **Punctuation in `tr` is ASCII**, matching the source's own marks:
  。 → `.` , ， and 、 → `,` , ？ → `?` , ！ → `!` , ： → `:` , …… → `...`,
  the quotation marks → `" "` or `' '`. The transliteration is a Latin line
  and reads as one.

Pinyin belongs to Chinese and does not move with the gloss language. `q`,
`x`, `zh` and `c` are pinyin's letters in a book glossed in Italian, in
French or in Turkish exactly as in one glossed in English; never respell them
into somebody's orthography (`ci` for `q`, `ç` for `c`, `ch'` for `q` as
Wade–Giles had it), and never drop the tone marks because the gloss language
has no use for diacritics. A reader who has learnt the scheme once must be
able to read every edition of this series.

## Words

`words` is the chunk's text divided into **words**, each with its own pinyin —
the unit a reader looks up, marks as known, and sees pinyin over:

    我(wǒ) 想(xiǎng) 要(yào) 一(yì) 杯(bēi) 茶(chá)

- One line, words parted by **spaces**; a word's pinyin follows it in **ASCII
  parentheses** `( )`, with no space between: `中国(Zhōngguó)`. Punctuation,
  a Latin word or a figure is written bare: `，`, `iPhone`, `2024`.
- **The words joined with nothing between them must be `fa` exactly**,
  punctuation included, and the punctuation is `fa`'s own full-width marks;
  a machine checks it.
- **A word is a word, not a character** — the first rule of this file, with
  double force here: `中国(Zhōngguó)`, `图书馆(túshūguǎn)`, never
  `中(zhōng) 国(guó)`. A measure word, a sentence-final particle, a negation
  and 的 stand on their own, as they stand free in `tr` (`一(yí) 个(ge)
  人(rén)`); a verb keeps its aspect particle and its complement (`吃了(chīle)`,
  `看见(kànjiàn)`).
- The pinyin is written **as in `tr`**: tone marks, the word's syllables
  together, the apostrophe before a, o or e, the neutral tone unmarked, the
  changed tones of 不 and 一 (`一(yì) 杯(bēi)`, `不(bú) 是(shì)`), and a capital
  for a proper name only.
- `words` does not replace `tr`: `tr` stays the chunk's transliteration. The
  two normally say the same syllables — a machine compares them with the tones
  and the spacing set aside, and warns when they differ.

In a book the line is the last argument of `\chw`,
`\chw{}{我想要一杯茶}{wǒ xiǎng yào yì bēi chá}{…}{…}{我(wǒ) 想(xiǎng) 要(yào) 一(yì) 杯(bēi) 茶(chá)}`;
in a video it is the chunk's `"words"`. **Every chunk of Chinese text carries
its words, and they start from the machine's**: the toolbox proposes the
division and the pinyin when a text is added, and they are a draft to
correct. A draft made from pasted text also starts each chunk's `tr` as its
words' pinyin, parted by spaces, with the text's punctuation in ASCII as above
(`wǒ xiǎng yào yì bēi chá.`). An annotator starts the same way — `python3
lib/fill_words.py --lang zh --json <file>` on the chunks it has cut, a book's
paragraph or a video's part — and then corrects every line; a video's prompt
lists the machine's division under each caption for the same reason. Never
write the words from nothing. Where the chunk already has its `tr`, each
word's pinyin is cut from it, tones, capitals and all; where it has none yet,
a word of one character takes its commonest reading, so `很长` comes back
`zhǎng` where it is `cháng`.

## Vocabulary

`voc` is written in the voice of the books' gloss blocks: headword + pinyin +
meaning. One equivalent in the gloss language rather than a string of
synonyms, and **an empty `voc` is the right answer** for a chunk that needs
nothing. The meaning is what the gloss language is for; the labels around it
— *measure word*, *classifier for*, and the ones the edition prints from the
registry — are not, and stay as this file writes them whatever the glosses
are in.

In a **video** the line is plain text; Chinese characters inside it are fine,
the player shows them in the target font. In a **book** it uses four macros
and nothing else: `\dw{fa}{rom} gloss` ·
`\vb{verb}{rom}{A了B}{rom}{A不B}{rom}{meaning}` · `\bw{base}{rom}{meaning}` ·
`\pw{fa}` — plus `\textit`, `\emph`, `\nobreak`. Of the four, **`\vb` is for
two kinds of verb only**, for the reason two paragraphs down.

**A character is not a word.** 中国 is one word written with two characters,
and it is glossed once, as a word: `\dw{中国}{Zhōngguó} China`. Never gloss
the characters of a word one at a time, and never explain what a character
means "on its own" inside a word that has a meaning of its own: 东西 is a
thing, not east-west; 马上 is at once, not on-horse; 意思 is a meaning, not
idea-thought. Where a character **is** a word, it is glossed as one
(`\dw{山}{shān} mountain`), and character etymology belongs in no line of
this series.

**A verb is given as one form, and nearly always with `\dw`.** A Chinese
verb has no forms: nothing is added to it for person, number, time or mood,
and 吃 is 吃 everywhere. So a verb takes `\dw` like any other headword —
`\dw{吃}{chī} to eat`, `\dw{知道}{zhīdào} to know` — and **every single
character** does, whatever it means. The three-slot `\vb`, which exists for
languages whose verbs change shape, is used for exactly two kinds of verb,
the two that come apart in a sentence and so cannot be found in it without
help:

- **A separable verb** (verb + object, 离合词: 睡觉, 结婚, 帮忙, 见面) gives
  its **split** — the verb with 了 between its halves, the pinyin of 了
  joined to the syllables before it as everywhere in this file — and leaves
  the third pair empty:
  `\vb{睡觉}{shuìjiào}{睡了觉}{shuìle jiào}{}{}{to sleep}`, printed
  *睡觉 shuìjiào · split 睡了觉 shuìle jiào · to sleep*. Always the plain
  A了B, never the idiomatic 睡了一觉 or 睡了个好觉 — those are what the text
  shows, and the entry is what they are traced back to.
- **A verb with a resultative or directional complement** (看见, 听懂, 吃完,
  起来, 打开) gives its **can't** form — the potential with 不 inside, one word
  in pinyin with the 不 toneless (`kànbujiàn`), the one place a negation is
  not written free; where the verb and a two-syllable complement are two
  words (`zhàn qǐlai`), the toneless 不 stands between them as a third
  (`zhàn bu qǐlai`) — and leaves the second pair empty:
  `\vb{看见}{kànjiàn}{}{}{看不见}{kànbujiàn}{to see}`, printed *看见 kànjiàn ·
  can't 看不见 kànbujiàn · to see*. The *can* form, with 得 in the same place,
  is not given: it follows from the other.

A verb is one or the other, never both; the edition prints a pair only when
its form is written, so the empty one leaves no label behind. Nothing goes
in brackets after a Chinese meaning — Chinese has no extras — and a verb
that is neither kind stays `\dw`, however long it is. *split* and *can't*
are the registry's labels for the two slots (`lib/lang/zh.tex` sets the same
pair, and the check compares them). What a tense would have said is said by
the words standing beside the verb, and it is the **meaning line** that must
carry it:

- **了 the action completed** — 他吃了饭 `he ate` / `he has eaten`, and
  明天吃了饭就走 `tomorrow, once he has eaten, he will go`. 了 is not a past
  tense and must never be glossed as one; what fixes the time in English is
  the sentence's own 昨天, 明天, 已经, and where the sentence fixes nothing,
  neither should the gloss.
- **了 at the end of a sentence is a change of state**, which is a different
  word doing a different job: 下雨了 `it has started to rain`, 他十八岁了
  `he is eighteen now`, 我不去了 `I am not going after all`. The *now* and
  the *after all* are the gloss's business; there is no entry for 了.
- **着 the state goes on** — 门开着 `the door is standing open`,
  他笑着说 `he said, smiling`. Not the English progressive, which is 在:
  他在吃饭 `he is eating`.
- **过 has done it at some time** — 我去过中国 `I have been to China`
  (at some point, not necessarily lately). This is the one of the three a
  gloss most often loses; keep the *ever* in it.

了 is in the never-gloss list below and 着 and 过 are not: give each of those
two one entry the first time it appears (`\dw{着}{zhe} the state goes on`,
`\dw{过}{guo} has done it at some time`), and after that let the meaning
line carry them.

**The measure word is named, always, and never glossed as a number.** In
一个人 the 个 is not "one" and it is not nothing: it is the word Chinese puts
between a number or a demonstrative and its noun. `一个人` is
`\dw{一}{yī} one; \dw{个}{ge} measure word, the general one` — and where the
noun takes something other than 个, the entry says which noun it counts:
`\dw{本}{běn} measure word for books`, `\dw{条}{tiáo} measure word for long
thin things (roads, rivers, fish)`, `\dw{只}{zhī} measure word for animals`,
`\dw{张}{zhāng} measure word for flat things (tables, paper, tickets)`,
`\dw{位}{wèi} measure word for people, politely`. A reader who meets 这本书
without being told what 本 is will read it as a word he has missed.

Three more things a Chinese line must name, because the characters do not:

- **The separable verb.** 结婚, 帮忙, 睡觉, 见面 are one word in the
  dictionary and two in the sentence — 结了婚, 帮我的忙, 睡了一觉. Gloss the
  whole verb from its dictionary form with its `\vb` (above), wherever in the
  chunk its halves stand: `\vb{结婚}{jiéhūn}{结了婚}{jiéle hūn}{}{}{to
  marry}`. What stands between them in the text, when it is not 了, is named
  after the entry: `帮我的忙` is `\vb{帮忙}{bāngmáng}{帮了忙}{bāngle
  máng}{}{}{to help}, with the person helped between its halves`.
- **The complement.** 看见 (`to see`, look-and-succeed), 听懂 (`to
  understand`, listen-and-grasp), 吃完 (`to finish eating`), 走出去 (`to
  walk out`) are a verb plus a result or a direction, and the second half
  is where the meaning is finished. Gloss the pair, not the halves, with its
  `\vb` (above). The **potential** form puts 得 or 不 inside it — 看得见 `can
  see`, 看不见 `cannot see` — and that infix is the whole difference between
  the two: the `\vb` gives the 不 form, and where the text has the 得 one,
  say so after the entry: `\vb{看见}{kànjiàn}{}{}{看不见}{kànbujiàn}{to see};
  here \pw{看得见} \textit{kàndejiàn}, can see — 得 inside makes it possible`.
- **The coverb.** 在, 从, 对, 跟, 给, 把, 被 stand where a preposition stands
  and are verbs by origin, and two of them restructure the sentence:
  `\dw{把}{bǎ} puts the object before the verb, of doing something to it`
  and `\dw{被}{bèi} by, marks the doer of something suffered`. Give each of
  these an entry the first time it appears in a book.

The gloss editor's sources sidebar, in the reader and in the player, now
proposes a `\vb` from the dictionary for a verb the dictionary marks as
separable or as a verb with a complement, and a `\dw` for everything else
(`lib/verbs/zh.py`). The characters are the dictionary's own simplified
spelling, the pinyin its standard Mandarin reading, the split always the
plain A了B. It is a **draft for you to correct**, and it knows what it cannot
do:

- The dictionary **marks fewer verbs than there are**. The commonest it
  misses — 散步, 跑步, 唱歌, 请客, 听懂, 看懂, 回来, 进来, 学会, 记住 and
  some fifty more — are kept by hand in `lib/lang/zh.verbs.json`, which is
  also where its one common mistake is put right: it marks 想到 as
  verb-object, and 想了到 is not Chinese (想不到 is). A verb in neither —
  吃完 and 找到 are not in the dictionary as words at all, and come back as
  吃 and 完 — is offered as `\dw`s, and the `\vb` is yours to write.
- A **word the dictionary has only in another lect** — Cantonese 揸车, whose
  perfective is 揸咗车 — gets no `\vb`, because the 了 of the split is
  Mandarin grammar; nor does a word with no standard pinyin, which is how
  the dictionary says a word is not standard Mandarin. Nor does a split that
  belongs only to an old reading of a word whose plain reading does not
  split: 知道 "to know the Way" is marked separable, 知道 "to know" is not.
- A verb that has **come apart in the sentence** (结了婚, 见过面, 睡了一觉)
  is not found as one word, and a **potential** the dictionary lists as a
  word of its own (看不见, 听不懂) comes back as that word, with a `\dw`: in
  both cases the `\vb` is the dictionary form's, and yours to write.
- Where the dictionary's only sense for a verb is a pointer (聊天儿 is
  "erhua form of 聊天") the meaning is left empty and the button says so.

Which words the reader already owns turns on the gloss language, and here
Chinese has one relationship no other language in the toolbox has. A book
glossed in **Japanese** is read by somebody who owns most of the characters
already and will read them with Japanese meanings — and the ones that have
drifted are exactly the ones he will not stop at: 手纸 is toilet paper and
not a letter, 汽车 is a car and not a steam train, 爱人 is a spouse and not a
lover, 勉强 is reluctantly and not study, 大丈夫 is a real man and not "it's
all right". Those deserve a full entry precisely because that reader thinks
he has them. Everything else that reader needs is the sound, not the meaning,
so the entries around them can be short. To a reader of Persian, Turkish,
Hindi or Italian no character says anything at all, and every word takes the
ordinary entry.

The repetition rule is Frank's own: a full entry the **first time** a word
appears, briefer or none on later appearances.

## Never gloss

These function words are already in dictionary form and never get a
vocabulary entry. What the three *de* and the aspect 了 are doing shows in
the meaning line instead, and never in an entry of their own:

```
的 地 得 了
是 不 没 别
我 你 您 他 她 它 们 自己
这 那 哪 什么 谁 怎么
很 也 都 就 还 又 再
和 或 但是 因为 所以
吗 呢 吧 啊 呀 啦
```

## Chunking

A chunk is a sense group of roughly **2–8 characters** — a verb with its
object, a noun with what qualifies it, a coverb with the noun it governs:
something a reader hovers and that *means* something on its own. Chinese
punctuates at every clause, and a Chinese comma is the most reliable chunk
boundary there is; take it wherever the sentence offers one, and put the mark
with the chunk before it. A very short sentence (`好。`, `你呢？`) is one
chunk; that is normal and not a fault.

Runs of Chinese are found by their script, so nothing is marked by hand.

Never split:

- a **word into its characters** (中国, 朋友, 图书馆, 因为) — this is the
  first rule, and the one a language written without spaces makes easy to
  break;
- a **number or demonstrative from its measure word**, or either from the
  noun (一个人, 三本书, 这条河);
- a **verb from its aspect particle** (吃了, 看着, 去过) or from the
  complement that finishes it (看见, 听懂, 走出去, 看不见);
- a **verb from its negation** (不去, 没有, 别走);
- **的 from what it modifies** — the modifier and its head are one chunk
  (我的书, 红色的花, 昨天买的那本书) — for the same reason a Japanese chunk
  is never cut at の;
- a **coverb from its object** (在家, 跟他, 从北京, 把书), nor the 把 phrase
  from the verb that disposes of it;
- a **fixed expression**, whether it is four characters of literary Chinese
  (马马虎虎, 一举两得) or an ordinary idiom: the meaning is not in the parts,
  and showing the parts teaches the reader something untrue.
