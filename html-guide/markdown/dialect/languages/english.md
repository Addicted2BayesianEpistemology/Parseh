---
title: Writing English
linkTitle: English
weight: 8
description: target en — a Latin-script target, every run marked, even in English prose; section titles without |; IPA in General American, with its stress marks.
target: en
---

`target: en` — English as the language being learned: a document for a
learner of English, whose prose may be Persian, Italian or English itself.
Whatever the prose, the studio cannot tell an English word to be learned
from the words around it, so every run of it is marked.

## Every run is marked

Any mark sets a word or a group as the English being taught: `[…]{tl}`,
the code `[…]{en}`, a colour, a pronunciation, or any other word in the
braces but `la`, `ltr` and `math`.

```parseh-example
---
target: en
---
[thought]{translit:θɔt} = *an idea*, [though]{teal translit:ðoʊ}, [through]{translit:θru}
and [tough]{translit:tʌf}: the same letters *-ough*, and four different sounds.

[The weather is lovely today.]{tl bg=quote}
```

A whole paragraph marked `[…]{tl}` is a block, and takes `bg=`; inside a
line the options are not read. There are no automatic paragraphs and no
display lines. A wrong form is a marked run after `✗`: `✗[goed]{tl}`.

When the prose is written right to left — `lang: fa` for a Persian
writing English lessons for Persians — the editor writes its source right
to left too ([Front matter](../front-matter.md#lang)).

## Face

English is set in the prose's own face, **TeX Gyre Pagella**, at the
prose's size; it has no second face and is not set vertically.

## Vocabulary entries

Any `##` heading with two parts or more is a vocabulary entry, so **a
section title in an English document cannot hold a `|`**.

```parseh-example
---
target: en
---
## thought | θɔt | Old English *þōht* | = *an idea that comes to the mind*

## [light]{amber translit:laɪt} | | Old English *lēoht* | = *what lets us see*
```

## Pronunciation

English spelling says little of the sound, so a pronunciation is written
for **every** word or group taught, in **IPA**, in a General American
accent with every written `r` sounded, lower case and without punctuation:

- **consonants** as the IPA writes them, with `θ ð ʃ ʒ tʃ dʒ ŋ`, `j` for
  the y of *yes*, and the plain letters `g` and `r`;
- **vowels** `ɪ i ɛ æ ɑ ɔ ʊ u ʌ ə`; **diphthongs** `eɪ aɪ ɔɪ oʊ aʊ`; a vowel
  and an r written as the vowel then `r` (`kɑr`, `fɔr`, `bərd`);
- **stress**: `ˈ` before the stressed syllable of every word of more than
  one, `ˌ` for a secondary stress (`ˌʌndərˈstænd`);
- silent letters not written (`ni` *knee*); function words weak (`ðə`,
  `tə`, `əv`); a contraction one word (`doʊnt`); endings as said
  (`hɛlpt`, `bɛdz`); the flapped t written `t`.

```parseh-example
---
target: en
---
[record]{translit:ˈrɛkərd} *the thing* and [record]{translit:rəˈkɔrd} *the act*;
[island]{teal translit:ˈaɪlənd}.
```

English has **no reading**: `kana:` means nothing here.
