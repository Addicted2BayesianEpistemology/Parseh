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

**Version a0.1.0** - 
Currently released in alpha version, support for mobile version is still limited.
Bugs are to be expected.

**The guide — installing, using and extending Parseh, and the full reference
of its Markdown dialect — is at
<https://addicted2bayesianepistemology.github.io/Parseh/>.** The same pages
are in [`html-guide/`](html-guide/), and the printable manual is
[`HOW TO USE THIS TOOLBOX.pdf`](HOW%20TO%20USE%20THIS%20TOOLBOX.pdf).

## Quick start

| Linux | macOS | Windows |
|---|---|---|
| `./install.sh`, then `./serve.sh` | double-click **`Parseh.command`** | double-click **`install.bat`**, then **`serve.bat`** |

Then open <https://localhost:8765/> and accept the browser's warning about
the self-signed certificate, once. The guide's
[Installing Parseh](https://addicted2bayesianepistemology.github.io/Parseh/html-guide/site/getting-started/installing.html)
page has the details.

## License

The code is under the GNU General Public License v3.0 ([`LICENSE`](LICENSE)).
The bundled fonts in `lib/fonts/` are under the SIL Open Font License, and
MathJax (`lib/mathjax/`) under the Apache License 2.0. The repository ships
the software and none of the content: what you read with it is yours.
