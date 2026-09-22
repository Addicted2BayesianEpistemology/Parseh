# The Parseh guide, as web pages

The guide to Parseh is a set of static web pages: they need no server to be
read (a browser opens `index.html` straight from the disk), and they use a
little JavaScript for what makes them pleasant — the list of pages, the
search, the themes, the Copy buttons, the exercises. The hub's **guide**
button opens them at `/guide/`, and the same pages can be published on
GitHub Pages. They are the whole manual: there is no PDF of it (the address
the PDF manual had, `/guide.pdf`, opens them).

The pages themselves are Markdown files under `markdown/`, compiled into
`site/` by `build.py`. **The guide explains its own writing**: its section
*Writing this guide* (`markdown/writing-this-guide/`) shows every construct
working, and is the reference; this file is the summary.

## What is where

```text
html-guide/
  README.md       this file
  index.html      the front page: written by hand, tracked, what opens first
  build.py        the compiler's command
  engine/         the compiler: standard-library Python
  assets/         guide.css, guide.js, favicon.svg: loaded by every page, tracked
  markdown/       the pages (tracked); a folder is a section; pictures beside them
  site/           what a compile makes (tracked: GitHub Pages publishes it): the pages, nav.js,
                  search-index.js, build.json, _parseh/ (the studio's runtime)
```

The search box looks through every word of every page: `site/search-index.js`
holds each page's title, headings, description and its whole text, and is
loaded the first time the box is used.

`index.html` works before anything is compiled: it uses only `assets/`, and
reads the list of pages from `site/nav.js` with a plain `<script src>` — the
one way a page opened from the disk can read another file. Without a
compiled site it says so; served by Parseh it offers a **Compile the guide**
button. Every address in every page is relative and names its file, so the
same pages work from the disk, under `/guide/` and on GitHub Pages.

One thing does not work from the disk: YouTube's player, which refuses a page
that sends no Referer ("Video player configuration error", Error 153), and a
`file://` page sends none. There `assets/guide.js` puts a card in each
YouTube player's place — the video's still, **Watch on YouTube** from the
clip's start, opening it in a new tab — and one line under the figure saying
that the player works when the guide is served. The card's words are never
cut: `guide.css` sizes them by the card's own width (a container query), and
a narrow card, as on a phone, says only **YouTube, 0:30 ↗**, keeping the
start. Served, by Parseh or any web host, the players are left alone.
Vimeo's player plays from the disk and is kept.

A page knows it was served by Parseh only when the server says so
(`GET /guide/__status`, which only Parseh answers, with `parseh: true`), not
from its address: a website may publish the guide under `/guide/` too. Only
then does the bar show the way back to the hub, the page load Parseh's
**Working…** list (`/lib/activity.js`, the pill every page of Parseh has),
and the front page offer the compile.

## Writing a page

A page is a `.md` file under `markdown/`; `markdown/a/b.md` becomes
`site/a/b.html`. A folder is a section; its `_index.md` is the section's own
page and gives the section its title and place. The root `markdown/_index.md`
only names the guide (`title:`). Any other file under `markdown/` is copied
to the same place under `site/`.

**Front matter**, YAML (`---`), TOML (`+++`) or JSON (`{…}`):

| Key | |
|---|---|
| `title`, `linkTitle` | the page's title; a shorter one for the list of pages |
| `description` | a line in its section's list and in the search |
| `weight` | its place: lower first; no weight after every weight; then by title |
| `draft: true` | leave it out |
| `toc: false` | no **On this page** |
| `aliases` | old addresses that go on to it |
| `target` | the target language (a registry code); **default `fa`**, as in the studio |
| `lang` | the prose's language; default `en` |
| `subtitle`, `note` | the studio's title block |
| anything else | readable with `{{< param "key" >}}` |

**The Markdown** is Hugo's (Goldmark with its default extensions) and the
Parseh studio's dialect, together:

- Hugo: ATX and setext headings (to level 6, closing `#`s, `{#id .class}`),
  paragraphs, hard breaks (two spaces, `\`), emphasis with `*` and `_`,
  `***both***`, `~~strike~~`, code spans (any number of backticks, opaque),
  fenced code (`` ``` `` or `~~~`, with Hugo's `{linenos=true,hl_lines=[2,"4-5"],linenostart=10}`),
  lists nested to any depth, loose or tight, with start numbers and task
  items, tables with alignment and `\|`, links with titles, reference links
  and definitions, autolinks and bare URLs, inline images with titles,
  footnotes, definition lists, the typographer (“ ” ‘ ’ – — … « »), backslash
  escapes, entities, rules, block attributes (`{.class}` on the line after a
  block), and the front matters above.
- Parseh: everything in `markdown/README.md` — target-language runs and
  `[…]{tl …}` marks and blocks (vertical ones too), colours,
  `{translit:…}`/`{kana:…}`, lemma headings, `>` boxes, `{la}` blocks,
  `✗ ✅ → ⏎`, `^[inline notes]`, `[…]{math}` and `:::math`, `:::exercise`
  (all thirteen, interactive), picture and recording lines with the studio's
  `{width= align= offset= start= end=}`, `@[…](youtube)` videos, and
  `[label](doc:Title)` — a link to the page with that **title**.
- Hugo's built-in shortcodes: `figure`, `details`, `highlight`, `ref`,
  `relref`, `param`, `youtube`, `vimeo`, `qr` (a real QR code, drawn by
  `engine/qr.py`), `comment`, and `x`, `instagram`, `gist` as plain links (the
  guide is built without the network). An unknown shortcode is a warning and
  a red box. `{{</* x */>}}` shows a shortcode instead of running it.

**Code** is never interpreted — no marks, no shortcodes, no typographer —
shown in a coloured block with its language and a **Copy** button that copies
it exactly, a tab as a tab (Clipboard API, with the old `execCommand` where
that is refused). Tabs are read as four columns only for a page's structure
(indentation, list items); in a code block they stay tabs.
Markdown (with the dialect's marks), bash, Python, JSON, YAML, TOML,
HTML/XML, CSS, JavaScript and LaTeX are highlighted (`engine/highlight.py`).
A longer fence holds a shorter one. **`parseh-example`** as a fence's
language shows the Markdown *and*, below it, what the studio draws from it —
rendered as a document of its own, which may start with its own front
matter (`target: ja`).

**Pictures**: name them by their path from the page; a missing one is said
at compile time with its file and line; they load lazily, never overflow the
column, and open large on a click.

### Where Parseh wins

When the same text means one thing to Hugo and another to the studio, the
studio's reading wins:

| You write | Hugo | The guide |
|---|---|---|
| `> text` | a blockquote | the studio's box; no lazy continuation |
| `## a \| b \| c` | a heading | a lemma (headword, transliteration, etymology), when the studio reads one |
| `## Title` | a heading | a numbered section, with Hugo's id |
| `## 3. Title`, `## Title = *x*` | as written | the typed number and the gloss taken off |
| `[text]{…}` | text and braces | a mark: `{tl}`, colour, `{translit:}`, `{math}`, `{la}` |
| `![c](p.png){width=50}` | a picture and `{…}` | the studio's figure, laid out |
| `![c](a.mp3)` | a broken picture | a player |
| `@[c](youtube…)` | text | a video |
| `*x*`, `**x**` | emphasis | the studio's (never inside a word, never across a target run) |
| every item `- **Label** text` | a list | the studio's description list |
| a line under a list item, at the margin | more of the item's text (a "lazy" line) | a paragraph after the list, as in the studio; indent it (two spaces) to carry the item on |
| `[^1]` used twice | one note | two notes, as the studio numbers them |
| `^[note]` | text | an inline footnote |
| tables | GFM | GFM's syntax, the studio's look; `—`/`--`/`-` alone is an empty cell; rows end at a line without `\|` |
| `->` | `->` | → |
| `✗` `✅` `⏎`, `x = *gloss*` | text | the dialect's marks |
| `:::exercise`, `:::math` | text | an exercise, a formula |
| `[l](doc:Title)` | a link | a link to the page titled so |
| raw HTML | left out | shown as text, as in the studio; `<!-- comments -->` left out |
| four-space indentation | a code block | text: code is always fenced |

Where the studio has no reading of its own, Hugo's holds: code spans are
opaque, lists nest, `===` and `---` make headings, and the rest above.

One case is decided the other way, on purpose: **a blank line between two
list items** keeps Hugo's reading — one *loose* list, numbered on (`1.`,
blank, `1.` gives 1 and 2). The studio ends the list at the blank line and
starts the next at 1 again, because it has no item of more than one line of
text; the guide needs Hugo's loose lists, start numbers, and items holding
more paragraphs, code or a box, so here Hugo wins. A studio document pasted
into a page may therefore number such a list on where the studio restarts
it; write it with no blank lines between the items to have it as the studio
draws it.

## Compiling

```sh
python3 html-guide/build.py             # markdown/ -> site/ (a clean rebuild, swapped in whole)
python3 html-guide/build.py --check     # compile into a scratch folder, keep nothing, say what is wrong
python3 html-guide/build.py --strict    # warnings fail too
python3 html-guide/build.py --out DIR   # somewhere else
python3 html-guide/build.py --clean     # remove site/
```

A compile replaces its folder whole, so `--out`, `--pages` and `--export`
go only into a folder that is new, empty, or one they made before (an
earlier compile's `build.json`, the `.parseh-guide-pages` that `--pages`
leaves, an export's `engine/vendor/`). Any other folder is refused — exit
status 2, and not a file in it touched — so a mistyped `--out ~/Documents`
costs nothing.

Any Python 3.8+ — the engine uses only the standard library. The installers
run it every time: `install.sh` and `install.bat` (`lib/runtime.py`'s `guide`
step), and the Windows wizard, `serve.bat`'s first run, in its step for the
books (`lib/launcher.py`, which leaves a guide already compiled from the same
pages as it is). `./install.sh --guide` runs only that, and the front page's **Compile the guide** button runs it through
the server (`POST /guide/__compile`, `GET /guide/__status`,
`lib/guidebuild.py`), offered when the site is missing or older than its
sources — `site/build.json` holds a hash of every source
(`engine/fingerprint.py`). A compile started there is on Parseh's activity
list (`/__activity`) while it runs, as *Compiling the guide*: on the page's
pill and on the hub.

The compile prints each problem as `warning:` or `error:` with its file and
line — a missing picture, a dead link or `doc:` link, an unknown shortcode, an
exercise that needs attention (warnings); a `ref` to no page, front matter
that does not read (errors) — writes every page it can, and exits 1 when
there was an error. The same sources always give the same bytes.

## How it is built

- **The studio draws the dialect.** `engine/studio.py` imports the studio's
  own `mdparser`, `htmlgen` and `languages` (from `../markdown/exlex`,
  `../markdown/app`, `../lib`). The engine's block parser (`engine/blocks.py`)
  finds Hugo's blocks itself and hands every Parseh block — paragraphs,
  tables, lemmas, figures, exercises, formulas — to `htmlgen`, so a page looks
  exactly like a studio document.
- **One seam for Hugo's inline Markdown.** For the length of a compile,
  `htmlgen.inline` is replaced by a function that first puts every Hugo-only
  construct behind a placeholder of Unicode private-use characters (which no
  rule of the studio's, and no language's script, matches) and then calls the
  original (`engine/inline.py`); the placeholders become HTML at the end —
  or, inside an attribute the studio wrote, the Markdown they stood for. That
  is why the Parseh server never imports the engine and runs `build.py` as a
  child process.
- **The studio's script and stylesheet, reused.** `markdown/app/static/app.js`
  runs on a static page (it calls no server on load); it is copied into
  `site/_parseh/` with its case fold spliced in as the studio's server does,
  and `bindExercises` is called on the article. `app.css` is rewritten at
  compile time so that every rule applies inside the article only
  (`engine/cssscope.py`), with the studio's themes following the toolbox's.
  MathJax, the language font tokens and the fonts go beside them.
- **The palette is lib/parseh.css's**, copied into `assets/guide.css`
  (`tests/test_html_guide.py` holds them together), and the ◐ button shares
  the whole toolbox's `parseh_theme` setting.

## Publishing on GitHub Pages

The compiled pages are committed (`site/` is tracked), and the repository's
root holds the two files GitHub Pages needs to serve them as they are: an
`index.html` that sends a visitor on to `html-guide/index.html`, and an
empty `.nojekyll`, without which GitHub would run the files through Jekyll
and leave out every folder whose name starts with `_` — `site/_parseh/`,
the studio's runtime, among them.

Once, on GitHub:

1. **Settings → Pages → Build and deployment → Source: Deploy from a
   branch.**
2. **Branch: `main`, folder: `/ (root)`, Save.**

The guide is then at `https://<user>.github.io/Parseh/` (the front page
itself at `…/Parseh/html-guide/`), a minute or two after the first save,
and again after every push to `main`: GitHub publishes what is committed.
So a changed page reaches the web when it is compiled and committed —
`python3 html-guide/build.py` (or `./install.sh --guide`), then commit
`html-guide/markdown/` and `html-guide/site/` together.

**Letting GitHub compile it instead.** `.github/workflows/guide-pages.yml`
compiles the guide on every push to `main` that touches it (or the studio's
renderer, the registry, the fonts, MathJax), as a check that it still
builds. Run by hand (**Actions → guide on GitHub Pages → Run workflow**),
it also publishes what it compiled — for that, set **Source** to **GitHub
Actions** first. It runs `python3 html-guide/build.py --pages _site`, which
lays out `index.html`, `assets/` and `site/` in one folder (plus
`.nojekyll`, and the `.parseh-guide-pages` that lets the next `--pages`
empty it), the same shape as `html-guide/`, so every relative address holds
— on GitHub Pages, any static host, or opened from the disk. Every file in
it is readable by all, as Pages demands (the workflow also runs the
`chmod -R +rX` that `upload-pages-artifact` recommends).

## A project of its own

```sh
python3 html-guide/build.py --export ../parseh-website
```

copies the guide — engine, assets, pages, front page — with a snapshot of
exactly what it takes from Parseh (`engine/manifest.py`: the studio's
parser and renderer, the registry, `app.js`, `app.css`, MathJax, the fonts
the sheet names and their licences) into `engine/vendor/`, a `.gitignore` and a
Pages workflow of its own. There `engine/vendor/` is committed; the copy
builds with plain Python into the same bytes the in-repo build makes. Export
again to refresh the snapshot. (In Parseh, `engine/vendor/` is ignored and
never used while the live sources are there.)

## Limits

- One target language per page (and per `parseh-example`), as in the studio.
- Hugo's templates, taxonomies, menus, i18n, `.Site` variables and custom
  shortcodes are not there: this is Hugo's *Markdown*, not Hugo.
- `==mark==`, `^sup^`, `~sub~` and emoji codes, off by default in Hugo, are
  off here.
- A footnote is one paragraph, and a reference used twice is two notes (the
  studio's rule).
