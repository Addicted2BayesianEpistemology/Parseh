---
title: Writing Persian
linkTitle: Persian
weight: 1
description: target fa — found by its script, right to left, Vazirmatn and Nastaliq; the zero-width non-joiner; the transliteration scheme.
target: fa
---

`target: fa` — Persian, فارسی, in the Arabic script, written **right to
left**. It is the studio's first language and its default: a document that
names no `target:` is a Persian one.

## How its text is found

Persian needs no mark. Every stretch of the Arabic script in the prose is
a Persian run: words parted by single spaces stay one run, and the
zero-width non-joiner, the Persian digits `۰–۹` and the marks `،` `؛` `؟`
belong to it. A Latin letter, a western digit or Latin punctuation ends
it.

```parseh-example
---
target: fa
---
Persian inside English needs no mark: سلام *salām*, hello, and می‌روم *mi-ravam*, I go.

قطره قطره جمع گردد، وانگهی دریا شود

امروز هوا خیلی خوب است. با دوستم به پارک می‌روم!

[امروز یک فایل PDF برای معلمم فرستادم.]{tl}
```

- A paragraph of nothing but Persian letters, spaces and Persian
  punctuation is a **display line**, set larger.
- A paragraph with no Latin letter — a Latin full stop, `!` or a western
  digit is allowed — is a **Persian paragraph**, right to left.
- A Persian sentence that holds a Latin word is marked, `[…]{tl}`: `{fa}`
  and the old `{rtl}` are the same mark.

## Faces and direction

On the screen Persian is set in **Vazirmatn**, which comes with the
toolbox, with Noto Naskh Arabic behind it; on paper in Vazirmatn too. The
second face, `font=nastaliq`, is **Noto Nastaliq Urdu** — the flowing hand
of Persian poetry, which comes with the toolbox too — set with taller
lines, since its letters hang far below the line.

```parseh-example
---
target: fa
---
[
بنی آدم اعضای یک پیکرند ⏎
که در آفرینش ز یک گوهرند
]{tl font=nastaliq bg=quote}
```

Persian text is set **1.52 times** the size of the prose. Right to left is
the browser's work on the screen; on paper it is set with TeX's own
right-to-left commands, and every PDF build then reads the Persian back
off the page, glyph by glyph, and counts the strings it found in the right
order (the `[…]{tl}` blocks, laid out whole, excepted). A Latin word
inside a Persian block keeps its own direction, and a bracket in it is
turned the way the sentence reads.

Persian cannot be set vertically: `vertical` is ignored.

## The zero-width non-joiner

Persian keeps the parts of some words apart without a space: the prefix
می, the plural ها, the suffixes. The character that does it — the
zero-width non-joiner, *nim-fāsele* — is typed by the editor's **ZWNJ**
button, and is part of the word it sits in.

```parseh-example
---
target: fa
---
می‌روم *mi-ravam* I go, کتاب‌ها *ketāb-hā* books, خانه‌ای *xāne-i* a house.
```

## Punctuation

Persian punctuation — `،` `؛` `؟` — goes **inside a Persian sentence or
clause of its own**, typically a `[…]{tl}` block or a Persian paragraph.
Between Persian words that stand in English prose, use the prose's comma:
a Persian comma there is taken into the Persian run beside it, and set as
part of it.

## Vocabulary entries

Three parts after the headword's own: transliteration, origin, meaning.

```parseh-example
---
target: fa
---
## کتاب | ketāb | from Arabic *kitāb* | = *book*

## [خانه]{teal translit:xāne} | | Middle Persian *xānag* | = *house*
```

## Transliteration

A Persian word's `translit:` is the transliteration of **what is said** —
colloquial forms as heard, `mi-kone` when that is what is spoken — in one
scheme for every document, whatever the prose is written in:

- long **ā**, short **a e o**; long **i u** written plainly;
- **š** = ش, **č** = چ, **ž** = ژ, **x** = خ;
- **q** for both ق and غ, and an apostrophe, `'`, for both ع and ء;
- the emphatics flattened: س ص ث are **s**, ز ذ ض ظ **z**, ت ط **t**,
  ه ح **h**;
- the parts of a word **hyphenated** where the grammar is transparent:
  `mi-`, `nemi-`, `be-`, `na-`, the ezafe `-e`/`-ye`, the plural
  `-hā` (spoken `-ā`), the indefinite `-i`, the clitic pronouns `-am -et
  -eš -emun -etun -ešun`, the object `-o`; a zero-width non-joiner inside
  a word becomes a hyphen.

```parseh-example
---
target: fa
---
[می‌کنه]{translit:mi-kone} *he does*, [خانهٔ من]{translit:xāne-ye man} *my house*,
[کتاب‌ها]{teal translit:ketāb-hā} *books*.
```

Persian has **no reading**: `kana:` means nothing in a Persian document.
