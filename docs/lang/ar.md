# Arabic — the annotation conventions

How an Arabic sentence becomes a glossed line: what goes into each field
and how it is written. These rules bind both the reading editions and the
video captions; they are embedded into every prompt that asks for Arabic
annotation, so they are written as instructions to the annotator.

Two of the field names are languages, and neither is a claim about one:
`fa` is the text in the target language — Arabic here — and `en` is the
gloss beside it. They are the names Persian and English left behind from
the days when they were the only two languages the toolbox had, and they
are the same two keys in every book and every video. Which language the
gloss is written in is the book's or the video's own choice, `"gloss"` in
`book.json` / `video.json`, and English when the key is absent. This file
is about Arabic as the language being **taught**: the examples below gloss
into English because they must gloss into something, and every rule that
turns on the gloss language says so.

## The text field

`fa` reproduces the source **verbatim**: same spelling, same punctuation,
same hamza seats and alif forms (`أ إ آ ا ى ة` exactly as the source has
them), the source's own oddities included — a dialect word in a caption, a
misspelling the ASR made. Chunks split only at spaces; joined back with
single spaces they must reproduce the sentence exactly, and a machine
checks that. **Never correct the text in `fa`** — the correction goes in
`note` (videos) or in the vocabulary line (books).

In a reading edition `fa` carries **full tashkil on every word**: fatha,
kasra, damma on every short vowel, **sukun** on every vowelless consonant,
**shadda** on every doubled one (with its own vowel on top), **tanwin** on
every indefinite case ending (`كِتَابٌ`, `كِتَابًا`, `كِتَابٍ`), the dagger alif
where the orthography has it (`هَٰذَا`, `لَٰكِنْ`). A word is either fully
vowelled or it is wrong; a half-vowelled word tells the reader nothing about
which half was left out. The bare pass is made by stripping these marks, so
nothing but the marks may differ between the vowelled text and the plain
one. The marks agree with the transliteration beside them: the
transliteration is what the marks are checked against.

Case endings are written as the text is read: full iʿrāb in classical and
literary prose (`الْكِتَابُ جَدِيدٌ`), pausal form at a pause (`جَدِيدْ`), and
what is actually said in a caption of spoken Arabic. There is no ezafe in
Arabic; the annexation (idafa) is shown by the case marks alone.

In a video caption `fa` carries no marks at all: the caption is copied as
YouTube has it.

## Reading

This language has no reading field.

## Transliteration

`tr` is a consistent scholarly transliteration of what is actually said or
printed — Modern Standard Arabic as written, the dialect form as heard when
the video speaks dialect.

- Long vowels **ā ī ū**; short a i u; the diphthongs **aw** and **ay**.
- Hamza is **ʾ** (never at the start of a word: `amal`, not `ʾamal`);
  ʿayn is **ʿ**.
- Emphatics with a dot under: **ṣ ḍ ṭ ẓ**; **ḥ** = ح; **ḏ** = ذ, **ṯ** = ث;
  **ġ** = غ; **q** = ق; **š** = ش; **j** = ج.
- خ is **ḫ** — one letter, always; never `kh`.
- Tā marbūṭa is **-a** in pause and at the end of a phrase (`madīna`),
  **-at** when the word is the first term of an idafa or carries a case
  ending that is read (`madīnat al-malik`, `madīnatun`).
- The article is written **al-** with a hyphen and **assimilated as heard**
  before a sun letter: `aš-šams`, `an-nūr`, `ar-rajul`; `al-qamar`. After a
  vowel the alif of the article is elided and written with an apostrophe
  after the hyphen only when the form is read that way (`fī l-bayt`,
  `wa-l-kitāb`).
- Hyphenate clitics: the conjunctions `wa-` `fa-`, the prepositions `bi-`
  `li-` `ka-`, the pronoun suffixes `-hu -hā -ka -ki -ī -nā -kum -hum`, the
  future `sa-`.
- Doubled consonants written double (`muʿallim`, `šidda`).
- Case endings only where `fa` has them and they are read.

The scheme does not follow the gloss language: `š`, `ḫ` and `ʿ` are what
they are in a book glossed in Italian or in Turkish as much as in one
glossed in English, and never `sh`, `kh` or a dropped mark. It is a
transliteration of the Arabic, not a respelling in somebody's orthography,
and a reader who has learnt it once must be able to read the next edition
with it.

## Vocabulary

`voc` is written in the voice of the books' gloss blocks: headword +
transliteration + meaning.

- A **noun** gives the singular with its plural (`كِتَاب kitāb, pl. كُتُب
  kutub · book`) and the **root in parentheses** (`(ك ت ب)`).
- A **verb** is given as the perfect with its form, the imperfect and the
  masdar: `كَتَبَ kataba (I) · impf. يَكْتُبُ yaktubu · masdar كِتَابَة kitāba ·
  to write`; a derived form names its number the same way (`عَلَّمَ ʿallama
  (II) · impf. يُعَلِّمُ yuʿallimu · masdar تَعْلِيم taʿlīm · to teach`). Every
  verb in the text gets this entry the first time it appears. What each slot
  holds is set out under the book's macros below, and it is the same in a
  video.
- A **participle**, a **verbal noun** or a broken plural is tied to its
  verb or singular, not glossed as a word of its own.
- Name what was stripped from the form in the text: the pronoun suffix, the
  case ending, the dual, the sound plural, the feminine ending.
- In a video the line is plain text; Arabic script inside it is fine — the
  player isolates it. A verb is `أراد arāda (IV) · impf. يريد yurīdu · masdar
  إرادة irāda · to want`, and a form of it in the chunk comes first with that
  entry in brackets after it (`يريد yurīdu wants (أراد arāda (IV) · impf. …)`).
  In a book the line uses the four macros `\dw` `\vb` `\bw` `\pw` (plus
  `\textit`, `\emph`, `\nobreak`), as the Persian editions do: `\vb` for
  every verb, `\dw` for every other headword. The seven slots of `\vb` are,
  in this order, **perfect, imperfect, masdar**, each with its
  transliteration, then the meaning —
  `\vb{كَتَبَ}{kataba (I)}{يَكْتُبُ}{yaktubu}{كِتَابَة}{kitāba}{to write}` — and
  the edition prints its own label before the second and third forms, so
  never put another form into those slots:
  - the **perfect** is the third person masculine singular, fully vowelled,
    and its transliteration carries the verb's **form** in brackets, Roman
    numerals I–X (Iq–IVq for a four-letter root): `kataba (I)`, `arāda (IV)`,
    `ištarā (VIII)`, `tarjama (Iq)`. The number is what makes the other two
    slots a pattern for every form but the first; write it every time.
  - the **imperfect** is the third person masculine singular indicative,
    with its final *-u*: `yaktubu`, `yaqūlu`, `yaṣilu`, `yarā`. For form I its
    vowel is the one thing nobody can guess.
  - the **masdar** is the verbal noun **that goes with the sense in the
    text**, one only: `وُصُول wuṣūl` for وَصَلَ *to arrive*, not the صِلَة of
    its other sense; `رُؤْيَة ruʾya` for رَأَى *to see*. It is **never the
    perfect written again** — a masdar slot that repeats the perfect prints
    `masdar رَأَى raʾā` and teaches something false. A verb with no masdar in
    use leaves the pair empty, `{}{}`, and the edition prints nothing there,
    label and all.
- What the three forms cannot say goes in **one parenthesis after the
  meaning**, items parted by `; `. Arabic has one such item: the
  **preposition the verb governs**, where the verb does not simply take a
  direct object — `+ \pw{إِلَى}` in a book, `+ إلى` in a video:
  `\vb{وَصَلَ}{waṣala (I)}{يَصِلُ}{yaṣilu}{وُصُول}{wuṣūl}{to arrive (+
  \pw{إِلَى})}`; so `رَغِبَ … (+ \pw{فِي})`, `بَحَثَ … (+ \pw{عَنْ})`. Two
  prepositions that are alternatives take one `+` and a slash (`بَعُدَ … (+
  \pw{مِنْ}/\pw{عَنْ})`), a second object a second `+` (`سَمَحَ … (+ \pw{لِ}
  + \pw{بِ})`). Nothing else goes in the parenthesis: not the root, not a
  transitivity label.
- A verb that is perfect only — `لَيْسَ` — is a `\dw` and not a `\vb`, with
  what it does in the meaning: `\dw{لَيْسَ}{laysa} is not, perfect in form and
  present in meaning`.
- The gloss editor's sources sidebar, in the reader and in the player, now
  proposes this entry from the dictionary for a verb it recognises: the
  vowelled perfect with its form, the imperfect, a masdar, and a governed
  preposition where the dictionary has one, each transliteration respelt in
  the scheme above (the dictionary writes `ʔ ʕ ḵ ḡ` and an initial hamza).
  It is a **draft for you to correct**: where the dictionary lists several
  masdars — it does for about one verb in six — the draft has the first,
  which is often the one for another sense (`صِلَة` where *to arrive* wants
  `وُصُول`); the meaning and the preposition are those of the sense the
  dictionary gives first, and its meaning runs to a line of synonyms; and a
  hit reached through an unvowelled word may be the wrong verb altogether.
  Fix it before it is saved; where it could not fill a slot — a masdar the
  dictionary does not know, which it does not tell apart from a verb that
  has none — the pair goes in blank and the button says which. In a video
  the draft keeps the dictionary's tashkil, and a video's vocabulary line is
  written without it (`أراد arāda (IV) · impf. يريد yurīdu …`, above): take
  the marks off as you correct it.

One equivalent in the gloss language rather than a string of synonyms; no
etymologies; **an empty `voc` is the right answer** for a chunk needing
nothing. The repetition rule is Frank's own: a full entry the **first
time** a word appears, briefer or none on later appearances.

The meaning is what the gloss language is for; the labels around it are
not. *impf.* and *masdar* are printed by the edition itself — the same two
words in every Arabic book, out of the registry — so leave them, and the
form number, the `+` before a preposition, the `pl.` and the root, as they
are written here whatever the glosses are in. Where the gloss language is
Arabic, the meaning is a **definition** and not a translation: commoner
words than the headword, and never a word of the headword's own root, which
in Arabic is the easiest circle to write by accident. `docs/lang/en.md`
sets that case out in full; it belongs to no one language.

Which words the reader already owns turns on the gloss language as well. A
book glossed in Persian or in Turkish is read by somebody who has met a
great part of this vocabulary already, and sometimes in another sense —
كثيف is *dense* in Arabic where Persian took it for *dirty*, زحمة
is a *crowd* and not the Persian's trouble — so the entry those words want
names the difference rather than the meaning. To a reader of English or
Italian they are simply new words and take the ordinary entry.

## Never gloss

The article, the prepositions, the pronouns and the common conjunctions
never get a vocabulary entry:

```
ال في من إلى على عن بـ لـ كـ مع عند حتى منذ بين أمام خلف فوق تحت بعد قبل
أنا أنت أنتِ هو هي نحن أنتم هم هذا هذه ذلك تلك هؤلاء أولئك الذي التي الذين
و ف ثم أو أم لكن بل إن أن لأن إذا لو ما لا لم لن لماذا كيف أين متى كم هل
نعم لا كل بعض غير
```

## Chunking

A chunk is a sense group of roughly **2–6 words** — a verb with its
subject or object, a noun with its adjective, a preposition with its noun:
something a reader hovers and that *means* something on its own. Never
split an **idafa** (`بَيْتُ الرَّجُلِ`), a **preposition from its noun**
(`فِي الْبَيْتِ`), or **the article from its noun** — the article is written
joined and cannot be split anyway, but a phrase like `هَٰذَا الْكِتَاب` is one
chunk. A negation stays with its verb (`لَمْ يَكْتُبْ`, `لَا أَعْرِف`), a
conjunction clitic with the word it is written on. A very short sentence
(`نَعَمْ`, `اُكْتُبْ`) is one chunk; that is normal and not a fault.
