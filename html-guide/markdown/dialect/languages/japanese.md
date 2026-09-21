---
title: Writing Japanese
linkTitle: Japanese
weight: 4
description: target ja — found by its script, no spaces, a reading in kana, rōmaji in Hepburn, a Gothic face and vertical columns.
target: ja
---

`target: ja` — Japanese, 日本語: kanji, hiragana and katakana, written
**left to right**, or **in vertical columns** read from right to left. It
is the one target language with a **reading**, the kana over the kanji.

## How its text is found

Japanese needs no mark. Kanji, hiragana, katakana, the Japanese
punctuation `。、「」` and the full-width signs are found in the prose on
their own. Japanese puts no spaces between its words, so a run is **the
characters that touch**: a space, a Latin letter or a western digit ends
it.

```parseh-example
---
target: ja
---
Japanese needs no mark: 日本語 *nihongo*, and 水 = *water*.

猿も木から落ちる。

毎朝7時に起きて、8時に家を出ます。

[週末はDVDで映画を見ます。]{tl}
```

- A paragraph of nothing but Japanese characters and Japanese punctuation
  is a **display line**, set larger.
- A paragraph with no Latin letter — western digits allowed — is a
  **Japanese paragraph**.
- A word or a sentence with Latin letters or digits inside it is marked
  `[…]{tl}` or `[…]{ja}` to stay one: `[Tシャツ]{tl}`, `[3時]{tl}`.

**Keep each sentence on one line of the source.** The studio joins the
lines of a paragraph with a space, which Japanese does not want.

## Faces

On the screen Japanese is set in the **Noto Serif CJK JP** of your device,
or its mincho face (Hiragino Mincho, Yu Mincho, IPAex Mincho, MS
Mincho) — no Japanese face travels with the toolbox; on paper in Noto
Serif CJK JP. The second face, `font=gothic`, is **Noto Sans CJK JP**, the
plain sans-serif of signs and screens. Japanese text is set **1.20
times** the size of the prose.

```parseh-example
---
target: ja
---
[本日休業]{tl font=gothic bg=rose}
```

## Vertical columns

`vertical` — or `tategaki`, or `mode=vertical` — sets a block in columns,
top to bottom, the columns following each other from right to left, as
books and poems are set. `height=` is a column's height in em, from 8 to
60, 22 when left out; on the screen a block wider than the page scrolls
sideways. A vertical block is always a whole paragraph.

```parseh-example
---
target: ja
---
[
古池や⏎
蛙飛び込む⏎
水の音
]{tl vertical height=8}

[The old pond / a frog jumps in / the sound of the water.]{la align=center bg=sand}
```

```parseh-example
---
target: ja
---
[菜の花や⏎月は東に⏎日は西に]{tl tategaki height=10}
```

On paper the columns are set rotated — true vertical setting — and the
block's tint is left out; in large print a column is never longer than
the page.

## The reading

A word may carry its reading in kana beside its rōmaji: `kana:` (or
`reading:`) and `translit:`, in either order, a colour before them.

```parseh-example
---
target: ja
---
[漢字]{kana:かんじ} has its reading, [東京]{translit:Tōkyō} its rōmaji,
[日本語]{kana:にほんご translit:nihongo} both, and
[学校]{indigo kana:がっこう translit:gakkō} a colour as well, and
[先生]{reading:せんせい translit:sensei} uses the other name of `kana:`.
```

Pointing at the word shows the kana above the rōmaji; the glossary has a
reading column; on paper the word is printed alone. In a Japanese
document the editor shows a **kana** button, which wraps the selection in
`[…]{kana:}`, and the reading view's cloud has a field for the kana beside
the one for the rōmaji.

## Vocabulary entries

Four parts after the headword, **the reading first**: kana, rōmaji,
origin, meaning. The second part is always the reading; leave it empty
(`## 猫 | | neko`) to give only the rōmaji.

```parseh-example
---
target: ja
---
## 食べる | たべる | taberu | = *to eat*

## [猫]{teal translit:neko} | ねこ | = *cat*
```

## Rōmaji

Hepburn, written from the reading, the same in every document whatever the
prose is written in:

- long vowels with macrons, **ō ū** (*Tōkyō*, *kūki*); `ei` and `ii` as
  written (*sensei*);
- the particles は, へ, を as they sound: **wa, e, o**;
- っ doubles the next consonant (*gakkō*, *kitte*; *matcha*);
- ん is **n**, and **n'** before a vowel or y (*kin'en*); never *m*
  (*shinbun*);
- *shi chi tsu fu ji*, *sha shu sho*, *cha chu cho*, *ja ju jo*;
- words parted where a dictionary parts them, a particle as a word of its
  own, a verb with its auxiliaries (*tabeteimasu*); capitals only for
  names.

In the kana of a reading, particles are written as written (は, not わ),
long vowels as spelled (とうきょう), and katakana stays katakana.
