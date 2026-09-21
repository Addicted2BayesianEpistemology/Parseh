# Japanese — the annotation conventions

How a Japanese sentence becomes a glossed line: what goes into each field
and how it is written. These rules bind both the reading editions and the
video captions; they are embedded into every prompt that asks for Japanese
annotation, so they are written as instructions to the annotator.

Two of the field names are languages, and neither is a claim about one:
`fa` is the text in the target language — Japanese here — and `en` is the
gloss beside it. They are the names Persian and English left behind from
the days when they were the only two languages the toolbox had, and they
are the same two keys in every book and every video. Which language the
gloss is written in is the book's or the video's own choice, `"gloss"` in
`book.json` / `video.json`, and English when the key is absent. This file
is about Japanese as the language being **taught**: the examples below
gloss into English because they must gloss into something, and every rule
that turns on the gloss language says so.

## The text field

`fa` reproduces the source **verbatim**, as written: kanji where the source
has kanji, kana where it has kana, the source's own okurigana, its
full-width punctuation (`、` `。` `「」`), its spaces or lack of them, its
oddities included — an unusual kanji choice, a caption's ASR slip. **No
furigana goes into `fa`**: the reading is a field of its own. Japanese has
no word separator, so a sentence is split into chunks at the boundaries
you choose, and the chunks joined back with **nothing between them** must
reproduce the sentence exactly, character for character — a machine checks
that. (A source that does put spaces in the text keeps them, inside the
chunk they fall in.) **Never correct the text in `fa`** — the correction
goes in `note` (videos) or in the vocabulary line (books).

There are no marks to strip: the plain pass shows the same text without
the reading over it.

## Reading

`kana` is the **reading of the whole chunk** in hiragana, written the way
the chunk is said and aligned to nothing smaller than the chunk — it is
one string, not a per-kanji list (the reading of each word is in `words`,
below). Katakana stays katakana where the text
has it (`テレビを見る` → `テレビをみる`); everything else is hiragana, kanji
and all. The rules that make readings comparable:

- **Particles as written**, not as pronounced: は → `は` (never `わ`), へ →
  `へ`, を → `を`.
- **Long vowels as written**: `おう` for おう (`とうきょう`, not `とーきょー`),
  `ええ`/`えい` as the text spells them, `ー` only where the text has it in
  katakana.
- The small kana as in the text: `っ`, `ゃ ゅ ょ`.
- Rendaku and sound changes as actually read: `ひとびと`, `がっこう`.
- Numbers read out: `三人` → `さんにん`, `一つ` → `ひとつ`.
- Kana in the text is copied unchanged into the reading; a chunk of pure
  kana has a `kana` identical to its `fa`, and that is right.
- **Punctuation as in the text**, where the text has it: `山へ柴刈りに、` →
  `やまへしばかりに、`, `「おい！」と` → `「おい！」と`. The machine compares
  readings with the punctuation set aside, so a mark is never an error; it
  is there because the reading is read as a line of its own.

Every chunk that is glossed has a `kana`; a machine refuses a glossed chunk
without one.

## Words

`words` is the chunk's text divided into **words**, each with its own
reading — the unit a reader looks up, marks as known, and sees furigana
over:

    山(やま) へ 柴刈り(しばかり) に 、

- One line, words parted by **spaces**. A word's reading follows it in
  **ASCII parentheses** `( )`, with no space between: `山(やま)`. A word
  with nothing to read — kana, punctuation, a Latin word, a figure — is
  written bare: `へ`, `、`, `テレビ`, `2024`.
- **The words joined with nothing between them must be `fa` exactly**,
  punctuation included; a machine checks it. The spaces in the line only
  part the words.
- A reading covers the **whole word, okurigana and all**, in hiragana, by
  the rules of `kana` above: `食べる(たべる)`, never `食(た)べる`;
  `住んでいました(すんでいました)`. A katakana word takes none.
- **What a word is.** A noun with its prefix and suffix (`お母さん`,
  `学生たち`); a verb or an adjective with its inflection and auxiliaries
  (`住んでいました`, `食べたくなかった`, `作ってくれた`); each particle on its
  own (`は`, `が`, `を`, `に`); the copula on its own after a noun (`学生 です`);
  each punctuation mark on its own. A compound noun is one word (`柴刈り`,
  `図書館`).
- `words` does not replace `kana`: the chunk's reading stays the reading of
  the whole chunk, as said. The two normally agree — the readings of the
  words, run together, are the chunk's `kana` — and a machine warns when
  they do not. They may rightly disagree only in **kanbun**, where the
  reading puts the words in another order: a book or video read that way
  says `"reorders": true` in its `book.json` / `video.json`, and then the
  words keep the **written** order while `kana` keeps the spoken one. The
  flag is a checkbox on the reader's **book info** sheet and the player's
  **video info** sheet, so nobody has to open the file for it.
- A `(` or `)` inside a word is written twice, `((` `))`; the fullwidth
  `（` `）` are ordinary text.

In a book the line is the last argument of `\chrw`,
`\chrw{}{山へ柴刈りに、}{やまへしばかりに、}{yama e shibakari ni,}{…}{…}{山(やま) へ 柴刈り(しばかり) に 、}`;
in a video it is the chunk's `"words"`. **Every chunk of Japanese text
carries its words, and they start from the machine's**: the toolbox proposes
the division and the readings when a text is added, and they are a draft to
correct. A draft made from pasted text also starts each chunk's `kana` as its
words' readings run together, the punctuation where the text has it. An
annotator starts the same way — `python3
lib/fill_words.py --lang ja --json <file>` on the chunks it has cut, a book's
paragraph or a video's part — and then corrects every line; a video's prompt
lists the machine's division under each caption for the same reason. Never
write the words from nothing. Where the chunk already has its `kana`, each
word's reading is cut from it, so the furigana say what `kana` says; where it
has none yet, the readings are a dictionary's, which is not the sentence's
(`私` comes back `わたくし` where the speaker says `わたし`).

## Transliteration

`tr` is **Hepburn rōmaji**, written from the reading:

- Long vowels with macrons: **ō ū** (`Tōkyō`, `kūki`), `ei` written `ei`
  (`sensei`), `ii` written `ii`.
- The particles は, へ, を as they sound: **wa, e, o**.
- **っ** doubles the following consonant (`gakkō`, `kitte`; `tch` before
  ch: `matcha`).
- **ん** is `n`; **n'** before a vowel or y (`kin'en`, `shin'yō`); `m` is
  never used before b/m/p (`shinbun`, not `shimbun`).
- `shi chi tsu fu ji` (`ぢ` and `づ` as `ji` and `zu`), `sha shu sho`, `cha
  chu cho`, `ja ju jo`.
- Words separated by spaces at the boundaries a dictionary would draw
  (`kanji o kaku`); a particle is its own word; a verb and its auxiliaries
  stay together (`tabeteimasu`); no capitals except proper names.

`tr` is on every glossed chunk, like `kana`.

Hepburn is built on English spelling — `sh`, `ch`, `j` are read as an
English reader reads them — and it stays Hepburn whatever the glosses are
written in. Never respell the reading in the gloss language's orthography:
`sci` for し in an Italian book, `ş` for し in a Turkish one, `ou` for う in
a French one would each make one edition unreadable to everybody else,
and the reading is in `kana` beside it for whoever wants the sound without
the convention.

## Vocabulary

`voc` is written in the voice of the books' gloss blocks: headword +
reading + meaning.

- A **verb** is given as its **dictionary form, -masu stem and -te form**,
  then the meaning, with its **class** in brackets after it: `書く かく kaku ·
  stem 書き kaki · -te 書いて kaite · to write (godan; tr.)`; `食べる たべる
  taberu · stem 食べ tabe · -te 食べて tabete · to eat (ichidan; tr.)`; `する`
  and `来る くる` are `irregular`; a **-suru** compound is whole in every slot,
  `勉強する · stem 勉強し · -te 勉強して · to study (suru)`. The form in the
  text is tied to it: `書いて · 書く, te-form`; `食べました · 食べる, past
  polite`.
- An **adjective** names its class: `高い たかい (i-adj.) · high, expensive`;
  `静か しずか (na-adj.) · quiet`.
- A **noun** is `漢字 かんじ · Chinese character`; a counter is named as such
  (`人 にん · counter for people`).
- A **particle** doing something a learner may not expect is **named**:
  `に · particle, direction`, `と · particle, quotation`; the ordinary
  particles are never glossed (below).
- Name what was stripped: the honorific `お`/`ご`, the plural `たち`, the
  nominaliser `の`/`こと`, the copula, the sentence-final particles (`ね`,
  `よ`).
- In a video the line is plain text; Japanese script inside it is fine —
  the player shows it in the target font. A verb is `書く かく kaku · stem 書き
  kaki · -te 書いて kaite · to write (godan; tr.)` — the kana of a kanji
  headword after it, as for every word — and a form of it in the chunk
  comes first with the entry in brackets after it. In a book the line uses
  the four macros `\dw` `\vb` `\bw` `\pw` (plus `\textit`, `\emph`,
  `\nobreak`), as the Persian editions do: `\vb` for every verb, `\dw` for
  every other headword. The seven slots of `\vb` are, in this order,
  **dictionary form, -masu stem, -te form**, each with its rōmaji and never
  with kana (the chunk's kana line carries the reading), then the meaning —
  `\vb{書く}{kaku}{書き}{kaki}{書いて}{kaite}{to write (godan; tr.)}` — and
  the edition prints *stem* and *-te* before the second and third forms,
  so never put another form (the past, the potential) into those slots.
- What the three forms do not name goes in **one parenthesis after the
  meaning**, items parted by `; `, in this order and these words:
  - the **class**, always: `godan`, `ichidan`, `suru` (a noun or phrase +
    する — 勉強する, 気にする — and 愛する-type verbs) or `irregular` (する
    itself, and 来る with its compounds — 持って来る). It is what builds
    every form the entry does not print — 買う makes 買わない, 食べる makes
    食べない — so it is never left out. The old ending note (`-ku`) is not
    written: the dictionary form shows it.
  - `tr.`, `intr.` or `tr./intr.`, **never guessed**: give it where you are
    sure of it, and always for the pairs that share one English gloss and
    not one particle — 開ける `tr.` (ドアを開ける), 開く `intr.` (ドアが開く).
  - `hon.` or `hum.` for a verb that is honorific or humble (いらっしゃる,
    おっしゃる, 参る, 申す), which a gloss like *to come* would hide.

  `\vb{来る}{kuru}{来}{ki}{来て}{kite}{to come (irregular; intr.)}`,
  `\vb{いらっしゃる}{irassharu}{いらっしゃい}{irasshai}{いらっしゃって}{irasshatte}{to
  come, to go, to be (godan; intr.; hon.)}`.
- The gloss editor's sources sidebar, in the reader and in the player, now
  proposes this entry from the dictionary for a verb it recognises: the
  three forms with the rōmaji the dictionary gives them (the -te form is its
  past with た made て, 書いた kaita → 書いて kaite), the class it records,
  checked against those forms — so 帰る, which looks ichidan, comes out
  godan, as its stem 帰り says — `tr.`/`intr.` only where it records one
  (about half the verbs; the rest are left without, not guessed), and
  `hon.`/`hum.` where the sense it prints is tagged so. A verb the chunk
  writes in another of the dictionary's spellings is proposed in the
  chunk's: 飲んだ gives 飲む, though the dictionary files it under のむ. It
  is a **draft for you to correct**: the meaning is the dictionary's first
  sense, which is often a definition rather than the one equivalent wanted
  here, or not the sense of the passage; an auxiliary after the -te form
  (いる in 書いている, しまう, みる) is proposed as a verb of its own, and is
  glossed instead as the construction, `\textit{-te iru}`; and in a video,
  check that the kana of a kanji headword follows it. Where it could not
  fill a slot, the button says which.

One equivalent in the gloss language rather than a string of synonyms; no
etymologies of kanji; **an empty `voc` is the right answer** for a chunk
needing nothing. The repetition rule is Frank's own: a full entry the
**first time** a word appears, briefer or none on later appearances.

The meaning is what the gloss language is for; the labels around it are
not. *stem* and *-te* are printed by the edition itself — the same two
words in every Japanese book, out of the registry — so leave them, and
`godan`, `ichidan`, `suru`, `irregular`, `tr.`, `intr.`, `hon.`, `hum.`,
`i-adj.`, `na-adj.` and the names of the forms, as they are written above
whatever the glosses are in: they name categories
a gloss language may well have no word of its own for, and the te-form is
called the te-form in a grammar of Japanese written in any language.

Where the gloss language is Japanese, the meaning is a **definition** and
not a translation: commoner words than the headword, and never the
headword's own compounds. `docs/lang/en.md` sets that case out in full; it
belongs to no one language.

## Never gloss

The particles and the copula forms never get a vocabulary entry:

```
は が を に で と も の へ から まで
だ です である でした だった じゃない ではない
```

## Chunking

A chunk is a sense group of roughly **2–8 characters** of kanji and kana —
a noun with its particle, a verb with its auxiliaries, a modifier with the
noun it modifies: something a reader hovers and that *means* something on
its own. **A chunk ends after a particle or after a verb form**; that is
where Japanese breathes. Never split a **word from its particle**
(`漢字を`, `学校に`), a **compound verb** or a verb from its auxiliaries
(`書いている`, `食べてしまった`, `勉強する`), a **modifier from its noun**
(`赤い花`, `大きな家`), or the copula from what it follows (`学生です`).
Punctuation stays with the chunk before it. A very short sentence (`はい`,
`行こう`) is one chunk; that is normal and not a fault.
