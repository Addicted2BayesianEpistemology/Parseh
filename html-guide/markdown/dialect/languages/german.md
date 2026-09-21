---
title: Writing German
linkTitle: German
weight: 6
description: target de — a Latin-script target, every run marked; section titles without |; the pronunciation line with its length and stress marks.
target: de
---

`target: de` — German, *Deutsch*, written left to right in the Latin
alphabet: the studio cannot tell it from the prose, so every run of it is
marked.

## Every run is marked

Any mark sets a word or a group as German: `[…]{tl}`, German's code
`[…]{de}`, a colour, a pronunciation, or any other word in the braces but
`la`, `ltr` and `math`. A noun is best marked with its article, which
belongs to it.

```parseh-example
---
target: de
---
[das Buch]{teal translit:das bu:x} = *the book*, [die Straße]{tl} = *the street*,
and [ich]{translit:iç} = *I*.

[Das Wetter ist heute schön.]{tl bg=sage}
```

A whole paragraph marked `[…]{tl}` is a block, and takes `bg=`; inside a
line the options are not read. There are no automatic paragraphs and no
display lines. A wrong form is a marked run after `✗`: `✗[gegeht]{tl}`.

## Face

German is set in the prose's own face, **TeX Gyre Pagella**, at the
prose's size; it has no second face and is not set vertically. On paper,
`lang: de` in the front matter breaks German prose by the modern
patterns.

## Vocabulary entries

Any `##` heading with two parts or more is a vocabulary entry, so **a
section title in a German document cannot hold a `|`**. The headword may
be the noun with its article.

```parseh-example
---
target: de
---
## das Buch | das bu:x | Old High German *buoh* | = *book*

## [die Zeit]{teal} | di: tsait | = *time*
```

## Pronunciation

A pronunciation line, **given only where the spelling misleads**, in
small letters, for the whole word or group:

- `:` after a vowel makes it **long** (`schta:t` *Staat*, `schtat`
  *Stadt*); `'` before a syllable puts the **stress** there (`be'zu:xen`);
- `ch` is `x` after a, o, u, au (`bax`) and `ç` everywhere else (`iç`,
  `'mä:tçen`); final `-ig` is `iç`;
- a doubled consonant is written single (`'ofen` *offen*);
- `v` is `f` (`'fa:ta`), `w` is `v`, `z` and `tz` are `ts`;
- `s` before a vowel is `z` (`'zone`); `st` and `sp` at the start of a
  stem are `scht` and `schp`; `ß` is `s`;
- a final `b d g` is `p t k` (`ta:k` *Tag*); a final `-er` is `a`
  (`'fa:ta` *Vater*);
- `ei` is `ai`, `ie` is `i:`, `eu` and `äu` are `oy`; an `h` after a vowel
  only lengthens it.

Give one for a length the sense turns on, for every `ch`, for a stress
not on the first syllable, and for a verb with a prefix; leave it out
where the spelling already says it.

```parseh-example
---
target: de
---
[die Bäckerei]{translit:di: bäke'rai}, [nicht]{teal translit:niçt},
[umfahren]{translit:'umfa:ren} *to run over*.
```

German has **no reading**: `kana:` means nothing here.
