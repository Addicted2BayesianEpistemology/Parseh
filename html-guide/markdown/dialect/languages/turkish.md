---
title: Writing Turkish
linkTitle: Turkish
weight: 7
description: target tr — a Latin-script target, every run marked; section titles without |; a pronunciation only for ğ, hidden long vowels and early stress.
target: tr
---

`target: tr` — Turkish, *Türkçe*, written left to right in the Latin
alphabet with letters of its own — ç ğ ı İ ö ş ü. The studio still cannot
tell it from the prose, so every run of it is marked.

## Every run is marked

Any mark sets a word or a group as Turkish: `[…]{tl}`, Turkish's code
`[…]{tr}`, a colour, a pronunciation, or any other word in the braces but
`la`, `ltr` and `math`.

```parseh-example
---
target: tr
---
[kitap]{tl} = *book*, [dağ]{teal translit:dā} = *mountain*, and
[Ankara]{translit:ˈAnkara}, stressed on its first syllable.

[Bugün hava çok güzel.]{tl bg=sand}
```

A whole paragraph marked `[…]{tl}` is a block, and takes `bg=`; inside a
line the options are not read. There are no automatic paragraphs and no
display lines.

**A wrong form is always marked**, `✗[gelmiş]{tl}`: a `✗` before an
unmarked word reddens only the letters of the Western European
languages, and stops at a `ş`, a `ğ` or an `ı`.

## Face

Turkish is set in the prose's own face, **TeX Gyre Pagella**, at the
prose's size; it has no second face and is not set vertically.

## Vocabulary entries

Any `##` heading with two parts or more is a vocabulary entry, so **a
section title in a Turkish document cannot hold a `|`**.

```parseh-example
---
target: tr
---
## dağ | dā | Old Turkic *taġ* | = *mountain*

## [kâr]{teal translit:kār} | | from Persian *kār* | = *profit*
```

## Pronunciation

Turkish spelling is one letter, one sound, and a pronunciation is **given
only where it helps** — in three cases, and only three, for the whole word
or group:

1. **ğ**, which is never a consonant: after `a ı o u` it lengthens the
   vowel (*dağ* `dā`, *yağmur* `yāmur`), after `e i` it is a `y` (*değil*
   `deyil`), after `ö ü` it lengthens again (*düğün* `dǖn`).
2. **A long vowel the spelling does not show**, in a word from Arabic or
   Persian: *kâr* `kār` profit against *kar* snow, *hâlâ* `hālā`.
3. **A stress not on the last syllable**, with `ˈ` (U+02C8, not an
   apostrophe) before the stressed syllable: the negative *ˈgelme*, place
   names (*ˈAnkara*, *İsˈtanbul*), and a short list of adverbs (*ˈşimdi*,
   *ˈsonra*).

The only symbols: `ā ē ī ō ū ȫ ǖ` for long vowels, `ä` for the open e
inside a line already given, and `ˈ`. Capitals stay as the text has them;
the apostrophe of *İstanbul'da* is dropped (`İsˈtanbulda`).

```parseh-example
---
target: tr
---
[yağmur]{translit:yāmur} *rain*, [hâlâ]{translit:hālā} *still*,
[şimdi]{teal translit:ˈşimdi} *now*.
```

Turkish has **no reading**: `kana:` means nothing here.
