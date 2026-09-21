---
title: Writing Hindi
linkTitle: Hindi
weight: 9
description: target hi — Devanagari, found by its script, left to right, Noto Serif Devanagari; the danda; the transliteration of what is said.
target: hi
---

`target: hi` — Hindi, हिन्दी, in the Devanagari script, written **left to
right**.

## How its text is found

Hindi needs no mark: Devanagari is found in the prose on its own. Words
parted by single spaces stay one run; the danda `।` and double danda `॥`,
the Devanagari digits, and the zero-width non-joiner and joiner that shape
a conjunct belong to it. A Latin letter, a western digit or Latin
punctuation — a `?`, a `!`, a comma — ends it.

```parseh-example
---
target: hi
---
Devanagari needs no mark: नमस्ते *namaste*, and धन्यवाद = *thank you*.

जैसी करनी वैसी भरनी।

आज सोमवार है और मौसम बहुत अच्छा है। क्या आप मेरे साथ चाय पिएँगे?

[आप कैसे हैं?]{tl} means *how are you?*, and [शुभ रात्रि]{hi} *good night*.
```

- A paragraph of nothing but Devanagari, spaces and dandas is a **display
  line**, set larger.
- A paragraph with no Latin letter is a **Hindi paragraph**.
- Mark a phrase `[…]{tl}` — or `[…]{hi}` — to keep a `?`, a comma or a
  western digit inside it: without the mark they cut it in pieces.

## Faces

Hindi is set in **Noto Serif Devanagari**, which comes with the toolbox,
on the screen and on paper; Noto Sans Devanagari stands behind it. It has
no second face (`font=` is ignored) and cannot be set vertically. Its text
is set **1.20 times** the size of the prose. The Devanagari faces have no
Latin letters, so on paper a Latin word inside a marked stretch is set in
the face of the text round it.

```parseh-example
---
target: hi
---
[
बुरा जो देखन मैं चला, बुरा न मिलिया कोय।⏎
जो दिल खोजा आपना, मुझसा बुरा न कोय॥
]{tl bg=sand}
```

## Vocabulary entries

Three parts after the headword: transliteration, origin, meaning.

```parseh-example
---
target: hi
---
## किताब | kitāb | from Arabic through Persian | = *book*
```

## Transliteration

The transliteration of what is **said**, not of the letters one by one:

- vowels **a ā i ī u ū e ai o au**;
- consonants by row: **k kh g gh ṅ** · **c ch j jh ñ** · **ṭ ṭh ḍ ḍh ṇ** ·
  **t th d dh n** · **p ph b bh m** · **y r l v** · **ś s h**; the nukta
  letters **q x ġ z f** and **ṛ ṛh**;
- **ष is ś**, like श; **ऋ is ri**;
- the **nukta** written where the page has it and not where it has not:
  ज़रूर *zarūr*, जरूर *jarūr*;
- **nasals**: before a stop the nasal of that row is written out (हिंदी
  *hindī*), elsewhere, and for every candrabindu, **ṁ** on the vowel
  (हूँ *hūṁ*, नहीं *nahīṁ*);
- **the schwa** that is written and not said is left out: कमल *kamal*,
  समझना *samajhnā*; long vowels always marked, doubled consonants
  written double;
- few hyphens: the postpositions are separate words; hyphenate only
  *-jī*, echo pairs (*cāy-vāy*) and a solid Sanskrit compound
  (राष्ट्रपति *rāśṭra-pati*).

```parseh-example
---
target: hi
---
[समझना]{translit:samajhnā} = *to understand*, [हूँ]{translit:hūṁ} = *am*,
[हिंदी]{teal translit:hindī}.
```

Hindi has **no reading**: `kana:` means nothing in a Hindi document.
