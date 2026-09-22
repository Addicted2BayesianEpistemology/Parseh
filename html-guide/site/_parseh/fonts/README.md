# The fonts that travel with Parseh

The faces of the target scripts that a device cannot be counted on to have.
Every page loads them from here (`/lib/fonts/`, the `.woff2` files), the
book and studio PDFs are set in them (the `.ttf` files), the Anki exporter
packs a language's face into its decks, and the guide's compiled site
carries copies (`html-guide/site/_parseh/fonts/`). Which language uses which
face is the registry's business (`lib/languages.json`, `fonts`).

They are not Parseh's work, and not under Parseh's licence (GPL-3.0-or-later,
`LICENSE`): each is under the **SIL Open Font License 1.1**, whose text and
the fonts' copyright notices are in [`OFL.txt`](OFL.txt). The `.woff2` file
of each family is the same font, compressed for the web.

| Files | Family | Version | Copyright | Licence |
|---|---|---|---|---|
| `NotoNaskhArabic-Regular.ttf`, `NotoNaskhArabic-Bold.ttf`, `NotoNaskhArabic.woff2` | Noto Naskh Arabic | 2.004 | © 2019–2020 Google LLC | OFL 1.1 |
| `NotoNastaliqUrdu-Regular.ttf`, `NotoNastaliqUrdu.woff2` | Noto Nastaliq Urdu | 20.0d1e3 | © 2014 Google Inc. | OFL 1.1 |
| `NotoSerifDevanagari-Regular.ttf`, `NotoSerifDevanagari-Bold.ttf`, `NotoSerifDevanagari.woff2` | Noto Serif Devanagari | 2.001 | © 2019 Google Inc. | OFL 1.1 |
| `Vazirmatn-Regular.ttf`, `Vazirmatn-Bold.ttf`, `Vazirmatn.woff2` | Vazirmatn | 33.003 | © 2015 The Vazirmatn Project Authors | OFL 1.1 |

The Noto families come from the Noto project (https://notofonts.github.io),
Vazirmatn from https://github.com/rastikerdar/vazirmatn.

## TeX Gyre, copied from TeX

The studio's pages and the guide's are set in **TeX Gyre Pagella** and
**TeX Gyre Heros**. They are not in this folder: the studio copies them from
the machine's TeX installation when it starts (`markdown/app/static/fonts/`),
and the guide's build copies them into its site
(`html-guide/site/_parseh/fonts/`, `texgyrepagella-*.otf`,
`texgyreheros-*.otf`). They are © B. Jackowski, J. M. Nowacki and the TeX
users groups, under the **GUST Font License**, whose text is here in
[`GUST-FONT-LICENSE.txt`](GUST-FONT-LICENSE.txt) — the LaTeX Project Public
License 1.3c or later, with a request to rename a modified font.

## Adding a face

A new language's face goes here as its `.woff2` (for the pages) and `.ttf`
(for the PDFs) — `lib/newlang.py --web-font` and the guide's *Adding a
language* say how. Record it in three places: a new row in the table above,
its copyright line in `OFL.txt` (or its own licence file beside it, if it is
not under the OFL), and an entry in `FONTS` in `lib/notices.py`, which draws
the app's Licences page (`/licences/`). A font travels with its licence, and
the guide's build copies the licence files of this folder into its site
along with the fonts. `tests/test_licences.py` checks that every font here
is named in all three, and that each file's own metadata says the same.
