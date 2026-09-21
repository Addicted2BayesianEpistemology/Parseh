---
title: Writing French
linkTitle: French
weight: 5
description: target fr — a Latin-script target, every run marked; section titles without |; the respelling that shows silent letters, nasals and liaisons.
target: fr
---

`target: fr` — French, *français*, written left to right in the Latin
alphabet: the studio cannot tell it from the prose, so every run of it is
marked.

## Every run is marked

Any mark sets a word or a group as French: `[…]{tl}`, French's code
`[…]{fr}`, a colour, a pronunciation, or any other word in the braces but
`la`, `ltr` and `math`.

```parseh-example
---
target: fr
---
[bonjour]{translit:bõʒour} = *hello*, [les amis]{teal translit:lé-zami} = *the friends*,
and [la pomme]{fr} = *the apple*.

[Il pleut sur la ville.]{tl bg=quote}
```

A whole paragraph marked `[…]{tl}` is a block, and takes `bg=`; inside a
line the options are not read. There are no automatic paragraphs and no
display lines. A wrong form is a marked run after `✗`: `✗[les amies]{tl}`.

French quotation marks are guillemets, which the editor's **«»** button
types; they are ordinary punctuation to the studio.

## Face

French is set in the prose's own face, **TeX Gyre Pagella**, at the
prose's size; it has no second face and is not set vertically.

## Vocabulary entries

Any `##` heading with two parts or more is a vocabulary entry, so **a
section title in a French document cannot hold a `|`**.

```parseh-example
---
target: fr
---
## fromage | fròmaʒ | Latin *formaticus*, shaped in a mould | = *cheese*
```

## Pronunciation

In French the pronunciation is worth giving for almost every word: the
spelling keeps letters the language stopped saying long ago. It is a
**respelling**, not IPA, written in lower case, without punctuation, and
for the whole word or group:

- **vowels**: `a`; `é` closed and `è` open; `e` only for the mute e of
  *le*; `i`; `o` closed and `ò` open; `ou`; `ü` the u of *tu*; `eu`;
- **nasals**: `ã` (*an, en*), `ẽ` (*in, ain, un*), `õ` (*on*) — nothing
  sounded after them: *bon* `bõ`, but *bonne* `bòn`;
- **glides**: `y` (*billet* `biyè`, *bien* `byẽ`), `w` (*moi* `mwa`), `ü`
  before a vowel (*lui* `lüi`);
- **consonants** as English and Italian read them, `g` always hard, `s`
  always hissed, plus `ʃ` (*chat* `ʃa`), `ʒ` (*je* `ʒe`) and `ɲ`
  (*montagne* `mõtaɲ`); never `c h j q x`;
- a **silent letter** is not written (*petit* `peti`);
- a **liaison** takes a hyphen, the sounded consonant at the head of the
  next word (*les amis* `lé-zami`), and the hyphen means nothing else;
- an **elision** makes one word (*l'homme* `lòm`);
- the **mute e** written where it is said and left out where it is not
  (*samedi* `samdi`); no stress marked; no letter doubled.

```parseh-example
---
target: fr
---
[merci beaucoup]{translit:mèrsi bokou}, [un grand homme]{translit:ẽ grã-tòm},
[la montagne]{teal translit:la mõtaɲ}.
```

French has **no reading**: `kana:` means nothing here.
