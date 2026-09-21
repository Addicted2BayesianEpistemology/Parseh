---
title: Writing Arabic
linkTitle: Arabic
weight: 2
description: target ar — found by its script, right to left, Noto Naskh Arabic; full vowel marks welcome; the scholarly transliteration.
target: ar
---

`target: ar` — Arabic, العربية, in the Arabic script, written **right to
left**. Everything that holds for Persian holds for Arabic, with its own
face and its own transliteration.

## How its text is found

Arabic needs no mark. Every stretch of the Arabic script in the prose is
an Arabic run — its vowel marks (fatha, kasra, damma, sukun, shadda,
tanwin, the dagger alif) included, since they are part of the script.
Words parted by single spaces stay one run; the Arabic digits `٠–٩` and
the marks `،` `؛` `؟` belong to it; a Latin letter, a western digit or
Latin punctuation ends it.

```parseh-example
---
target: ar
---
The word كِتَابٌ *kitābun* means a book, and مَدْرَسَة *madrasa* a school.

العِلْمُ نُورٌ

ذهبتُ إلى المدرسة صباحًا، ثم عدتُ إلى البيت.

[أرسلتُ ملف PDF إلى المعلّم.]{tl}
```

- A paragraph of nothing but Arabic letters, marks, spaces and Arabic
  punctuation is a **display line**, set larger.
- A paragraph with no Latin letter is an **Arabic paragraph**, right to
  left.
- An Arabic sentence that holds a Latin word or western digits is marked
  `[…]{tl}`, or `[…]{ar}`: the same mark.

## Faces and direction

Arabic is set in **Noto Naskh Arabic**, which comes with the toolbox,
with Vazirmatn behind it on the screen; on paper in Noto Naskh Arabic,
with Amiri and Vazirmatn as fallbacks. It has no second face (`font=` is
ignored) and cannot be set vertically. Its text is set **1.52 times** the
size of the prose. Noto Naskh Arabic has no Latin letters, so on paper a
Latin word inside a marked stretch is set in the face of the text round
it.

As with Persian, right to left is the browser's work on the screen and
TeX's on paper, where every build reads the Arabic back off the page to
check its order.

```parseh-example
---
target: ar
---
[
قِفا نَبْكِ مِنْ ذِكْرى حَبيبٍ ومَنْزِلِ ⏎
بِسِقْطِ اللِّوى بَيْنَ الدَّخولِ فَحَوْمَلِ
]{tl bg=sand}
```

## Punctuation

The Arabic comma, semicolon and question mark belong **inside an Arabic
sentence of its own**. Between Arabic words that stand in the prose, use
the prose's punctuation: an Arabic comma next to an Arabic word is taken
into its run.

## Vocabulary entries

Three parts after the headword: transliteration, origin, meaning.

```parseh-example
---
target: ar
---
## كِتَاب | kitāb | root k-t-b, *writing* | = *book*
```

## Transliteration

A consistent scholarly transliteration of what is said — Modern Standard
Arabic as written, a dialect form as heard — the same in every document
whatever the prose is written in:

- long vowels **ā ī ū**, short **a i u**, the diphthongs **aw** and **ay**;
- hamza **ʾ** (never at the start of a word: *amal*), ʿayn **ʿ**;
- the emphatics with a dot under them, **ṣ ḍ ṭ ẓ**; **ḥ** = ح, **ḏ** = ذ,
  **ṯ** = ث, **ġ** = غ, **q** = ق, **š** = ش, **j** = ج; **ḫ** = خ,
  always one letter, never *kh*;
- tā marbūṭa **-a** in pause (*madīna*), **-at** where it is read
  (*madīnat al-malik*);
- the article **al-**, assimilated as heard before a sun letter:
  *aš-šams*, *ar-rajul*, but *al-qamar*;
- clitics hyphenated: *wa-*, *fa-*, *bi-*, *li-*, *ka-*, *sa-*, and the
  pronoun suffixes *-hu -hā -ka -ki -ī -nā -kum -hum*;
- doubled consonants written double: *muʿallim*.

```parseh-example
---
target: ar
---
[الشَّمْس]{translit:aš-šams} *the sun*, [مُعَلِّم]{teal translit:muʿallim} *teacher*.
```

Arabic has **no reading**: `kana:` means nothing in an Arabic document.
