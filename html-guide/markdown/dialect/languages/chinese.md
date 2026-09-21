---
title: Writing Chinese
linkTitle: Chinese
weight: 11
description: target zh — found by its script, no spaces, pinyin with tone marks as its transliteration, vertical columns, and no reading.
target: zh
---

`target: zh` — Chinese, 中文, in simplified or traditional characters,
written **left to right** or **in vertical columns**. Its pronunciation is
pinyin, in the transliteration: Chinese has no reading of its own script,
as Japanese has kana.

## How its text is found

Chinese needs no mark: its characters, the Chinese punctuation `，。、？！：`
and the full-width signs are found on their own. There are no spaces
between words, so a run is **the characters that touch**; a space, a
Latin letter or a western digit ends it.

```parseh-example
---
target: zh
---
Chinese needs no mark: 我学习中文 = *I study Chinese*, and **中文** is bold.

学而时习之，不亦说乎？

我每天学习30分钟中文，周末学习一个小时。

[周末我们去唱卡拉OK吧！]{tl}
```

- A paragraph of nothing but characters and Chinese punctuation — not
  even a figure — is a **display line**, set larger.
- A paragraph with no Latin letter is a **Chinese paragraph**, figures
  included.
- A stretch with Latin letters in it is marked `[…]{tl}` or `[…]{zh}`:
  the OK of 卡拉OK would cut it in two otherwise.

**Keep each sentence on one line of the source**: the lines of a
paragraph are joined with a space, which Chinese does not want.

## Faces and vertical columns

Chinese is set in **Noto Serif CJK SC**, from your device on the screen,
and on paper; no Chinese face travels with the toolbox, and there is no
second face (`font=` is ignored). Its text is set **1.20 times** the size
of the prose.

`vertical` (or `tategaki`, or `mode=vertical`) sets a block in columns,
top to bottom, right to left; `height=` is a column's height in em, 8 to
60, 22 when left out.

```parseh-example
---
target: zh
---
[
床前明月光，⏎
疑是地上霜。⏎
举头望明月，⏎
低头思故乡。
]{tl vertical height=8 bg=sand}

[
A：你好吗？⏎
B：我很好，谢谢。你呢？
]{tl bg=sage}
```

```parseh-example
---
target: zh
---
[学而时习之，⏎不亦说乎？]{tl mode=vertical height=8}
```

A vertical block's tint shows on the screen and is dropped on paper,
where the columns are set rotated.

## Vocabulary entries

Three parts after the headword, as in Persian: pinyin, origin, meaning.
There is no reading part.

```parseh-example
---
target: zh
---
## 学习 | xuéxí | = *to study, to learn*

## [咖啡]{teal translit:kāfēi} | | from English *coffee* | = *coffee*
```

## Pinyin

The transliteration is **Hanyu Pinyin with tone marks**, of what is said,
the same in every document whatever the prose is written in:

- **tone marks, never tone numbers**: *nǐ hǎo*, not *ni3 hao3*; the mark
  on a or e, on the o of ou, otherwise on the last vowel (*liù*, *guī*);
  the **neutral tone unmarked** (*māma*, *xièxie*, *de*, *le*);
- **ü** keeps its dots (*nǚ*, *lǜ*), and is written u after j q x y
  (*qù*, *xǔ*);
- **words, not syllables**: *Zhōngguó*, *wǒmen*, *túshūguǎn*; a verb with
  its aspect particle (*chīle*) and its complement (*kànjiàn*); particles,
  negations and measure words standing free;
- the apostrophe only before a syllable starting with a, o or e
  (*Xī'ān*, *nǚ'ér*);
- er-hua in the word (*nǎr*, *wánr*);
- capitals for names only (*Běijīng*);
- the tones the words have, not the sandhi (*nǐ hǎo*) — except 不 and 一,
  written as said (*bú shì*, *yí ge*).

```parseh-example
---
target: zh
---
[苹果]{translit:píngguǒ} = *apple*, [谢谢]{teal translit:xièxie} = *thank you*,
[图书馆]{translit:túshūguǎn} = *library*.
```

`kana:` means nothing in a Chinese document.
