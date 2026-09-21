---
title: What differs, language by language
linkTitle: Language by language
weight: 10
description: Passes, readings, words, vertical text, verb entries, transliteration schemes and the reading help — everything that is not the same in all eleven languages.
---

The doors, the buttons and the file formats are the same for every
language. This page is everything that is not: what each language needs to
be read, and what each part of Parseh does about it.

## The passes of a reading edition

A reading edition gives each passage several times — **passes** — and how
many, and what each one is, depends on the language. The reader shows one
button per pass in its header, numbered as below and captioned *which
passes you see*; each button's tooltip is the pass's title, and turning one
off hides that pass.

| Language | Its passes |
|---|---|
| Persian | **1** the vowelled attempt · **2** chunks and glosses · **3** bare naskh · **4** nastaliq |
| Arabic | **1** the vowelled attempt · **2** chunks and glosses · **3** unvowelled, as Arabic is written |
| Japanese | **1** with furigana over each word · **2** the reading alone, in kana · **3** chunks and glosses · **4** plain, as Japanese is written · **5** vertical (tategaki) |
| Chinese | **1** with pinyin over each word · **2** the reading alone, in pinyin · **3** chunks and glosses · **4** plain, as Chinese is written · **5** vertical |
| Italian, French, German, Turkish, English, Spanish, Hindi | **1** the sentence · **2** chunks and glosses |

Why these and not others:

- **A bare pass exists only where it shows something pass 1 does not.**
  Persian and Arabic are written in the reading editions with their vowel
  marks (harakat) — pass 1 is *the vowelled attempt* — and the bare pass
  takes them off, as the languages are normally printed. Japanese and
  Chinese take away the readings over the words. The Latin-script languages
  and Hindi have nothing to take off (Devanagari writes its vowels), so
  their pass 1 already shows all a bare pass could.
- **A fourth face** is Persian's alone: the passage again in **nastaliq**,
  the calligraphic hand of Persian poetry and titles.
- **Japanese and Chinese have a reading pass and a vertical pass.** In
  pass 1 each word of a chunk wears its reading over it, where the chunk
  carries its word line (a Japanese chunk without one wears its kana over
  the whole of it); pass 2 is the reading alone — the passage in kana, or
  in pinyin, as it is said, with the punctuation that ends each chunk —
  and pass 5 sets the passage in columns read top to bottom and right to
  left.

## Readings, words and columns

| | Japanese | Chinese | the rest |
|---|---|---|---|
| **Transliteration line** | rōmaji (Hepburn) | pinyin, with tone marks | see below |
| **A reading beside it** | **kana**: every glossed chunk carries it, and the checkers require it | none — pinyin *is* the transliteration | none |
| **Words** | every chunk may carry a **word line**, `山(やま) へ 柴刈り(しばかり) に`: its words and each word's reading | the same, with pinyin: `我(wǒ) 想(xiǎng) 喝(hē) 茶(chá)` | no need: spaces already divide the words |
| **Vertical text** | the fifth pass; a studio block with `vertical` | the same | — |
| **No word separator** | a chunk counts as one word everywhere; the dictionary cuts it (or follows its word line) | the same | — |

The word line is what the furigana of pass 1 stand over, what the
[dictionary](dictionaries.md) looks up word by word, and what the cloud's
*山: I know this* buttons work by: a word you know stops wearing its reading
wherever it appears in that book or video. The video player of a Japanese
or Chinese video has one more button, named after the reading — **kana** or
**pinyin** — which shows every phrase as it is said, in place of its text.

## The transliteration, language by language

Each language's rules for writing its lines live in its **conventions
file**, `docs/lang/<code>.md` — the rules every prompt that asks a model to
annotate that language includes, and the page to read when you wonder why
a gloss is written the way it is.

| Language | The transliteration line |
|---|---|
| **Persian** | required. A scheme of its own: long *ā*, *š č ž x q*, the emphatics flattened, transparent morphology hyphenated (*mi-kone*, *ketāb-hā*); what is *said*, colloquial forms included. |
| **Arabic** | required. A scholarly scheme: *ā ī ū*, *ʾ* and *ʿ*, the emphatics with a dot under them. |
| **Hindi** | required, because the script hides what it does not say: the inherent *a* printed in every consonant and often silent — कमल is *kamal*. Every noun is glossed with *m.* or *f.* |
| **Japanese** | required: Hepburn rōmaji written from the kana (*Tōkyō*, particles *wa e o* as said). |
| **Chinese** | required: pinyin with tone marks, never numbers; the neutral tone unmarked. |
| **Italian**, **Spanish** | optional, and given only where the spelling misleads — Italian's open and closed *e* and *o* and its stress, Spanish's silent *h*. Most chunks need none. |
| **German** | optional, where the spelling misleads (vowel length, the two *ch*, stress). Capitals are spelling — a noun always has one — and a separable verb is glossed as the whole verb, however far apart its halves are. |
| **Turkish** | optional and rarely needed: the spelling is phonemic. The vocabulary line carries the morphology instead — a word's stem and each suffix in order. |
| **French** | optional in principle, given on almost every chunk in practice: the spelling hides the sound (silent endings, nasal vowels, liaisons). A respelling, not IPA. |
| **English** | written for every chunk with a word in it, in IPA, General American: English spelling is the least reliable guide to sound of any here. |

## Verb entries

A vocabulary line gives a verb as a **`\vb`**: three forms, each with its
sound, then the meaning — the same shape in every language. What the three
forms *are*, and the two labels printed before the second and third, are
each language's:

| Language | The three forms | Printed labels |
|---|---|---|
| Persian | infinitive · present stem · past stem | *pres.* / *past* |
| Arabic | perfect (3rd m. sg.; its form number in the sound) · imperfect (3rd m. sg.) · masdar | *impf.* / *masdar* |
| Italian | infinitive · 1st sg. present · past participle | *pres.* / *p.p.* |
| Japanese | dictionary form · -masu stem · -te form | *stem* / *-te* |
| French | infinitive · 1st sg. present · past participle | *pres.* / *p.p.* |
| German | infinitive · preterite (3rd sg.) · past participle | *pret.* / *p.p.* |
| Turkish | infinitive · present in -iyor (3rd sg.) · aorist (3rd sg.) | *pres.* / *aor.* |
| English | plain form · past · past participle | *past* / *p.p.* |
| Hindi | infinitive · stem · perfective (m. sg.) | *stem* / *perf.* |
| Spanish | infinitive · 1st sg. present · 3rd sg. preterite | *pres.* / *pret.* |
| Chinese | verb · A了B (a separable verb only) · A不B (a verb with a complement only) | *split* / *can't* |

A pair left blank is not printed at all — a Chinese verb has its *split*
form or its *can't* form, never both. Whatever else a language's verbs need
goes in one parenthesis after the meaning: *to drive (er fährt; aux.
sein)*. The chunk sheet's `\vb{}{}{}{}{}{}{}` button names the three
forms of the book's language in its tooltip, and the dictionary's verb entries, where a
language's recipe recognises a verb, arrive in exactly this shape
([Dictionaries](dictionaries.md)). Every one of the eleven languages has
such a recipe.

## In each door

| Door | What changes with the language |
|---|---|
| **Book reader** | the passes above; the direction and side of the chunk column; the digits of the labels; ruby over the words of Japanese and Chinese; the **Aa** panel's first slider named after the language, and a *columns height* slider for Japanese and Chinese |
| **Video player** | the direction and face of the transcript; the kana line of a Japanese phrase above its rōmaji; the **kana** / **pinyin** reading button for Japanese and Chinese |
| **Studio** | which text is found by its script and which must be marked; the fonts offered by `font=` (`nastaliq` for Persian, `gothic` for Japanese); `vertical` for Japanese and Chinese; a lemma heading's reading field and a **kana** insert button for Japanese; the target-text editor's button, **✎ Persian**, **✎ Japanese**… |
| **Reading help** | a dictionary for every language, with extra rules for Persian, Arabic, French, Italian, Japanese and Chinese; a corpus of Japanese or Chinese only after its dictionary; **Decompose Kanji** / **Decompose Hanzi** for Japanese and Chinese only; translation models only to or from English |
| **Anki** | a pair of note types per language — *Frank Italian* and *Frank Italian Opposites*, and so on (Persian's first is *Frank YouTube Persian*) — whose first field is named after the language (*Headword* for English), with a *Reading* field for Japanese; tags `<language>-book` and `<language>-youtube` (`farsi-…` for Persian) |
| **Videos, adding one** | which captions count as *plain* (in a script language, a caption with none of its letters); the words for seconds, minutes and chapters in the transcript |

The chapters on each door have the details: this page only says what the
language decides.
