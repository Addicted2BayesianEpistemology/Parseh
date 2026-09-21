---
title: Writing Spanish
linkTitle: Spanish
weight: 10
description: target es — a Latin-script target, every run marked; section titles without |; a pronunciation only where the spelling does not say it, stress never.
target: es
---

`target: es` — Spanish, *español*, written left to right in the Latin
alphabet: the studio cannot tell it from the prose, so every run of it is
marked.

## Every run is marked

Any mark sets a word or a group as Spanish: `[…]{tl}`, Spanish's code
`[…]{es}`, a colour, a pronunciation, or any other word in the braces but
`la`, `ltr` and `math`.

```parseh-example
---
target: es
---
[hola]{translit:ola} = *hello*, [la gente]{teal translit:la xente} = *the people*,
and [la calle]{es} = *the street*.

[¿Dónde está la estación?]{tl bg=rose}
```

A whole paragraph marked `[…]{tl}` is a block, and takes `bg=`; inside a
line the options are not read. There are no automatic paragraphs and no
display lines. A wrong form is a marked run after `✗`: `✗[sabo]{tl}`.

## Face

Spanish is set in the prose's own face, **TeX Gyre Pagella**, at the
prose's size; it has no second face and is not set vertically.

## Vocabulary entries

Any `##` heading with two parts or more is a vocabulary entry, so **a
section title in a Spanish document cannot hold a `|`**.

```parseh-example
---
target: es
---
## hijo | ixo | Latin *filius* | = *son*

## [calle]{teal translit:kaʝe} | | = *street*
```

## Pronunciation

Spanish spelling is nearly a map of its sound, and a pronunciation is
**given only where it does not say it** — for the whole word or group:

- **`g` before e or i, and `j`**, written `x`: *gente* `xente`, *hijo*
  `ixo`;
- **a silent `h`**, left out: *hola* `ola`;
- **`ll` and `y`**, written `ʝ`: *calle* `kaʝe`, *yo* `ʝo`;
- **`c` before e or i, and `z`**: `s` or `θ`, as the recording says it,
  one answer through a document;
- **`qu`, `gu`** before e or i are `k`, `g` (*queso* `keso`); `ü` puts the
  u back (*pingüino* `pingwino`);
- **a word-initial `r`** is the trill, `rr` (*rojo* `rroxo`);
- **`ñ`** is `ɲ`.

**Stress is never marked**: Spanish writes an accent wherever the
stress is not where the rule puts it, and a pronunciation keeps the
word's own accent (*corazón* `korasón`). Vowel quality is not marked
either.

```parseh-example
---
target: es
---
[el queso]{translit:el keso}, [el año]{translit:el aɲo}, [rojo]{teal translit:rroxo}.
```

Spanish has **no reading**: `kana:` means nothing here.
