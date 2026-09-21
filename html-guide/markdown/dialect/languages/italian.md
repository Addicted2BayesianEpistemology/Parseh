---
title: Writing Italian
linkTitle: Italian
weight: 3
description: target it — a Latin-script target, every run marked; section titles without |; the pronunciation marks for open and closed vowels, stress and s and z.
target: it
---

`target: it` — Italian, *italiano*, written left to right in the Latin
alphabet. That is what makes it different from Persian or Japanese: its
letters are the prose's letters, so the studio cannot find it on its own.

## Every run is marked

Nothing in an Italian document is found by its script — **every word or
group you want set as Italian is marked**, and any mark does:

- `[bello]{tl}`, or Italian's code, `[bello]{it}`;
- a colour, `[bello]{teal}`, or a pronunciation, `[ancora]{translit:àncora}`;
- any other word in the braces (only `la`, `ltr` and `math` mean something
  else).

```parseh-example
---
target: it
---
In Italian [bello]{tl} = *beautiful*, [la casa]{it} = *the house*, and
[ancora]{teal translit:àncora} = *anchor*; unmarked, bello is just a word.

[Una frase intera, messa in rilievo.]{tl bg=sand}
```

A marked word is a run of the target language: counted, colourable and
given a pronunciation from the reading view's cloud, gathered into the
glossary when it is glossed. A whole paragraph marked `[…]{tl}` is a
block, and takes a tint, `bg=`; inside a line the options are not read.
There are **no automatic paragraphs and no display lines**: an unmarked
Italian paragraph is prose.

A wrong form is a marked run after `✗`: `✗[andato]{tl}`.

## Face

Italian is set in the prose's own face, **TeX Gyre Pagella**, at the
prose's size (1.00): what sets it apart is the mark, not the letters. It
has no second face and is not set vertically.

## Vocabulary entries

Any `##` heading with two parts or more is a vocabulary entry — the
studio cannot tell an Italian headword from an English title — so **a
section title in an Italian document cannot hold a `|`**.

```parseh-example
---
target: it
---
## pesca | pèsca | Latin *persica*, the Persian apple | = *peach*

## [ancora]{teal translit:àncora} | | Greek *ánkyra* | = *anchor*
```

## Pronunciation

An Italian word's `translit:` is a pronunciation aid, **given only where
the spelling does not say it**, for the whole word or group:

- **open and closed e and o**: `è` for the open e, `é` for the closed;
  `ò` and `ó` the same (*pésca* peach, *pèsca* fishing);
- **the stress**, when it is not on the last syllable but one, or could be
  misread, marked as the dictionary marks it — a grave on `à ì ù` and on
  an open `è ò`, an acute on a closed `é ó` (*àncora* anchor, *ancóra*
  still; *telèfono*);
- **s and z**: `s` voiceless, `ṡ` voiced; `z` for /ts/, `ż` for /dz/
  (*càṡa*, *żèro*, *pizza*);
- the sounds a reader from elsewhere misreads: `gli` as **ʎ** (*fàmiʎa*),
  `gn` as **ɲ** (*ɲòkki*), `sc` before e and i as **ʃ** (*péʃe*), and
  doubled consonants written double.

No pronunciation for a word that is read as it is written.

```parseh-example
---
target: it
---
[la pesca]{translit:la pèsca} *fishing* and [la pesca]{translit:la pésca} *the peach*;
[gli gnocchi]{teal translit:ʎi ɲòkki}.
```

Italian has **no reading**: `kana:` means nothing here.
