---
title: Licences and credits
linkTitle: Licences
weight: 8
description: What Parseh is under, and whose work it carries and downloads — the fonts, MathJax, the hyphenation patterns, the dictionaries, sentences and translation models — under which licence.
---

Parseh is free software, under the **GNU General Public License, version 3
or (at your option) any later version** — `GPL-3.0-or-later`. The
licence's text is the file `LICENSE`, at the top of the Parseh folder, and
every source file says so in its first lines:

```
SPDX-License-Identifier: GPL-3.0-or-later
```

It comes with no warranty. The source is the Parseh folder itself: the
server runs from it as it is.

In Parseh, the foot of the hub leads to **Licences** (`/licences/`), in
the browser interface and in the mobile one. That page says all of this,
with a link to each licence's text.

## What Parseh carries

These are in the Parseh folder and are not Parseh's own work. Each keeps
its licence, which travels with it.

| What | Where | Whose | Licence |
|---|---|---|---|
| Vazirmatn 33.003 | `lib/fonts/` | © 2015 The Vazirmatn Project Authors | SIL Open Font License 1.1 |
| Noto Naskh Arabic 2.004 | `lib/fonts/` | © 2019–2020 Google LLC | SIL Open Font License 1.1 |
| Noto Nastaliq Urdu | `lib/fonts/` | © 2014 Google Inc. | SIL Open Font License 1.1 |
| Noto Serif Devanagari 2.001 | `lib/fonts/` | © 2019 Google Inc. | SIL Open Font License 1.1 |
| TeX Gyre Pagella and Heros | copied from TeX by the studio, and into this guide's pages | © B. Jackowski, J. M. Nowacki and the TeX users groups | GUST Font License |
| MathJax 3.2.2 | `lib/mathjax/` | © The MathJax Consortium | Apache License 2.0 |
| The Italian hyphenation patterns, `hyph-it.tex` | `markdown/exlex/assets/hyph/` | © 2008–2011 Claudio Beccari | LaTeX Project Public License 1.3 or later, or MIT |
| Conjugation rows, and sentences with their machine translations, in the tests' data | `tests/fixtures/verbs/`, `tests/fixtures/align/` | Wiktionary's contributors; Tatoeba's contributors | CC BY-SA 4.0 (Wiktionary); CC BY 2.0 FR (Tatoeba) |

The texts sit beside the files:

- `lib/fonts/OFL.txt` is the Open Font License, with the copyright notice
  of each font under it. `lib/fonts/GUST-FONT-LICENSE.txt` is the TeX Gyre
  fonts' licence. `lib/fonts/README.md` says which file is which font.
  The compiled guide carries copies of all three beside its fonts, in
  `html-guide/site/_parseh/fonts/`.
- Each font file also carries its notice and the name of its licence in
  its own metadata. So a font packed into an Anki deck goes with its
  licence.
- `lib/mathjax/LICENSE` is MathJax's licence.
- `hyph-it.tex` says in its own header which licences it is under, and
  carries the MIT text.
- `tests/fixtures/README.md` says where every text the tests read comes
  from.

The Japanese and Chinese pages are set in the device's own faces, so none
travels with Parseh.

## What it downloads when you ask

The dictionaries, the sentences people have translated, the translation
models and their engine, the English synonyms and the character
components are not in the Parseh folder. Each is downloaded from its
source when you ask for it on [the reading-help
page](../lookup-and-languages/reading-help.md), and keeps its own licence.
Parseh writes that licence into the file it builds, and shows it wherever
it shows what the file says.
[Whose work it is](../lookup-and-languages/reading-help.md#whose-work-it-is)
lists every source and its licence.

The installer fetches micromamba, Python and the packages
`environment.yml` lists. Each of them is under the licence it comes with.

## What you read with it

The books, videos, documents and decks are yours, or their authors'.
Parseh ships none of them, and its licence says nothing about them.

## A new font

A face added for a new language travels with its licence ([Adding a
language](../lookup-and-languages/adding-a-language.md#giving-it-a-font)).
Record it in three places:

- a row in `lib/fonts/README.md`;
- its copyright line in `lib/fonts/OFL.txt`, or a licence file of its own
  beside the font, if it is not under the OFL;
- an entry in `FONTS`, in `lib/notices.py`, which draws the Licences page.

`tests/test_licences.py` fails until all three name the new font.
