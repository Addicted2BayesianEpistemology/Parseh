---
title: Compiling and publishing
weight: 7
description: The compile and what it says, reading the guide, GitHub Pages, and a project of its own.
---

## Compiling

The pages in `html-guide/markdown/` become web pages in
`html-guide/site/` when they are compiled. Three things compile them:

- **The installer**, every time it runs, on every system: its step
  “the guide”. On Linux and macOS, `./install.sh --guide` does that step
  and nothing else.
- **The guide's front page, when Parseh serves it.** The hub's **guide**
  button opens it; when the compiled pages are missing, or older than the
  Markdown they come from, it says so and offers **Compile the guide**,
  and opens the new pages when the compile is done. If the compile fails,
  it still opens every page it could write, and what it said is shown on
  the front page.
- **`html-guide/build.py`**, run by hand, with any Python 3 — it needs
  nothing but the standard library.

`site/` is not kept in git: it is made from `markdown/`, whole, by every
compile.

## What the compile says

```text
warning: markdown/writing-this-guide/pages.md:48: no such file: shots/editor.png (looked for markdown/writing-this-guide/shots/editor.png)
error: markdown/showcase.md:12: ref: no page 'studio/decks.md'
the guide: 11 pages and 3 other files -> html-guide/site; 1 warning, 1 error
```

Each line names the page and the line. A **warning** leaves the page as
good as it can be — a picture missing, a link to a page that is not there,
an unknown shortcode (drawn as a red box), an exercise that needs attention
(drawn as the studio draws it) — and the compile goes on. An **error** —
a `ref` to no page, a front matter that cannot be read — still writes every
page it can, and makes the compile end with a failure, so that the
installer and the page's button say so.

```bash
python3 html-guide/build.py             # compile into html-guide/site/
python3 html-guide/build.py --check     # compile into a scratch folder and only say what is wrong
python3 html-guide/build.py --strict    # warnings fail it too
python3 html-guide/build.py --clean     # remove html-guide/site/
```

A compile takes a second or two for the whole guide, and gives the same
files for the same pages every time: nothing in them depends on the day.

## Reading it

The same compiled pages work three ways, which is why every address in
them is relative:

1. **In Parseh**, from the hub's **guide** button, at
   `https://localhost:8765/guide/`.
2. **From the disk**: open `html-guide/index.html` in a browser. Nothing
   needs a server — not the list of pages, the search, the exercises or
   the formulas.
3. **On GitHub Pages**, below.

The PDF manual stays where it was, at the **PDF manual** link at the top of
every page (**PDF**, on a phone), and at `/guide.pdf` in Parseh.

## Publishing on GitHub Pages

The compiled pages, `html-guide/site/`, are committed with the Markdown
they come from, and the repository's root holds the two small files GitHub
Pages needs to serve them as they are: `index.html`, which sends a visitor
on to the guide's front page, and an empty `.nojekyll`, without which
GitHub would leave out the folders whose names start with `_` (the studio's
runtime among them). Switching it on is one setting, once:

1. On GitHub, open the repository's **Settings → Pages**.
2. Under **Build and deployment**, set **Source** to **Deploy from a
   branch**, pick the branch **main** and the folder **/ (root)**, and
   press **Save**.

The guide is then at `https://<your user name>.github.io/Parseh/`, a minute
or two later, and each push to `main` publishes it again. A changed page
reaches the web once it is compiled and committed: compile (the front
page's button, `./install.sh --guide` or `python3 html-guide/build.py`),
then commit `html-guide/markdown/` and `html-guide/site/` together.

The repository also carries a workflow, `.github/workflows/guide-pages.yml`,
that compiles the guide on every push to `main` that changes it, the
studio's renderer or the language registry — a check that it still builds.
To have GitHub publish a guide it compiled itself instead of the committed
one, set **Source** to **GitHub Actions** and press **Actions → guide on
GitHub Pages → Run workflow**. It runs `python3 html-guide/build.py --pages
_site`, which puts the front page, `assets/` and the compiled `site/`
together in one folder — the same layout as `html-guide/`, so the same
relative addresses hold. The same folder can be put on any other static
host.

## A project of its own

The guide is meant to be part of Parseh's website one day, in a repository
that holds nothing else.

```bash
python3 html-guide/build.py --export ../parseh-site
```

copies the guide there — the engine, the assets, the pages, the front page
— with a snapshot of exactly what it takes from Parseh (the studio's parser
and renderer, the language registry, the exercises' script and stylesheet,
MathJax, the fonts, the PDF manual) in `engine/vendor/`, and a workflow of
its own for GitHub Pages. The copy compiles on its own, with any Python 3,
into the same pages. Run the export again to bring the snapshot up to date.

The folder must be new or empty, or an earlier export: the export replaces
the engine, the pages and the front page in it. Any other folder is refused
and left exactly as it was — and so is one given to `--out` or `--pages`
that holds anything but what they made there before.
