<!--
  The banner is docs/banner-light.svg and docs/banner-dark.svg, built from
  docs/banner.tex by `cd docs && ./banner.sh` (never edit the SVGs).  Keep
  the pair: GitHub picks the dark one on a dark theme.
-->
<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/banner-dark.svg">
    <img src="docs/banner-light.svg" width="820"
         alt="Parseh — one toolbox for reading a language the Ilya Frank way">
  </picture>
</p>

A toolkit for learning languages through annotated content and active
recall. Read books and watch videos glossed the Ilya Frank way, chunk by
chunk, with the narration in step; write notes and interactive exercises in
a Markdown dialect of its own and study them with spaced repetition; turn
anything you read into Anki cards. Eleven languages: Persian, Arabic,
Italian, Japanese, French, German, Turkish, English, Hindi, Spanish and
Chinese.

**Version a0.2.0** - 
Currently released in alpha version, support for mobile version is still limited.
Bugs are to be expected.

**The guide — installing, using and extending Parseh, and the full reference
of its Markdown dialect — is at
<https://addicted2bayesianepistemology.github.io/Parseh/>.** The same pages
are in [`html-guide/`](html-guide/), and Parseh serves them at `/guide/`.

## Quick start

| Linux | macOS | Windows |
|---|---|---|
| `./install.sh`, then `./serve.sh` | double-click **`Parseh.command`** | double-click **`install.bat`**, then **`serve.bat`** |

Then open <https://localhost:8765/> and accept the browser's warning about
the self-signed certificate, once. The guide's
[Installing Parseh](https://addicted2bayesianepistemology.github.io/Parseh/html-guide/site/getting-started/installing.html)
page has the details.

## License

Parseh is free software under the GNU General Public License, version 3
or (at your option) any later version — `GPL-3.0-or-later`
([`LICENSE`](LICENSE)); every source file says so in its
`SPDX-License-Identifier` line.

What it carries of other people's work keeps their licences:

- the fonts in `lib/fonts/` (Vazirmatn, Noto Naskh Arabic, Noto Nastaliq
  Urdu, Noto Serif Devanagari): SIL Open Font License 1.1 — the licence and
  their copyright notices in [`lib/fonts/OFL.txt`](lib/fonts/OFL.txt), every
  file named in [`lib/fonts/README.md`](lib/fonts/README.md);
- TeX Gyre Pagella and Heros, copied from TeX into the compiled guide
  (`html-guide/site/_parseh/fonts/`): GUST Font License
  ([`lib/fonts/GUST-FONT-LICENSE.txt`](lib/fonts/GUST-FONT-LICENSE.txt));
- MathJax 3.2.2 (`lib/mathjax/`): Apache License 2.0 (its `LICENSE` beside it);
- the Italian hyphenation patterns (`markdown/exlex/assets/hyph/hyph-it.tex`,
  © Claudio Beccari, hyph-utf8): LaTeX Project Public License 1.3 or later,
  or MIT — the file's header says so and carries the MIT text;
- excerpts in the tests' data (`tests/fixtures/`): conjugation rows from
  Wiktionary (CC BY-SA 4.0) and sentences from Tatoeba (CC BY 2.0 FR).
  [`tests/fixtures/README.md`](tests/fixtures/README.md) says where every
  test text comes from.

The dictionaries, sentences, translation models and character data the
reading help downloads on request are not in the repository; each keeps its
own licence, which travels inside the file it becomes. The app's
**Licences** page (the hub's foot, `/licences/`) lists all of it. The
repository ships the software and none of the content: what you read with
it is yours.
