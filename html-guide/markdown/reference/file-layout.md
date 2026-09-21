---
title: The file layout
linkTitle: File layout
weight: 4
description: The folders of the repository, and what a book, a video, a studio document, a note, an exercise deck and an Anki deck look like on the disk.
---

Every folder and file of Parseh, one by one: the detailed companion of
[Where everything lives](../getting-started/where-things-live.md) in
*Getting started*. You never need to open these folders — every page of
Parseh reads and writes them for you, and a **download** or a **Backup**
takes nearly anything away in one file (a backup of the whole book shelf
leaves the recordings out: [Keeping everything
safe](daily-loops.md#keeping-everything-safe)). This page is for when you want to look
anyway: to find a recording, to back a folder up by hand, to understand
what a zip holds.

Everything is under the folder you cloned or unpacked, the one that
holds `serve.sh`. Nothing is installed anywhere else, except the word
analyzers' models (in `~/.pkuseg/`), the environment if you made it with
your own conda, and what your browser keeps.

## The repository

```text
Parseh/
  serve.sh  serve.py  serve.bat
  install.sh  install.bat  Parseh.command
  build.sh  environment.yml
  lib/  books/  youtube/  markdown/  exercises/  clips/
  dict/  corpus/  mt/  components/
  docs/  guide/  html-guide/  tests/  .github/
  .runtime/  .tls/
```

| Path | What it is |
|---|---|
| `serve.py` | The one server: https, the hub, every door, the guide. `serve.sh` runs it in the background. |
| `serve.bat` | The same on Windows: double-click it. The first run is a setup wizard (its work is done by `lib/launcher.py`). |
| `install.sh` | The installer on Linux and macOS. `install.bat` is Windows's, and `Parseh.command` a Mac's double-click that installs the first time and then starts. |
| `build.sh` | Builds the books: each one's PDF and reader, and the library page. |
| `environment.yml` | The packages of the `ilya-frank` environment. |
| `lib/` | What every door shares — see the next table. |
| `books/` | The books, one folder a book, under its language's folder (below). |
| `youtube/` | The video player: `lib/` (its pages, its script, the annotation pipeline, the Anki tools), `videos/` (one folder a video, below), `anki/` (the card store, below). |
| `markdown/` | The studio: `app/` (its server, pages and script, and the exercise decks' pages, store and scheduler), `exlex/` (Markdown to LaTeX to a verified PDF, and `starters/`, the page a new document starts from), `library/` (one folder a document, below). |
| `exercises/` | The exercise decks, one folder a deck, under its language's folder (below). |
| `clips/` | The clip tray: recordings and frames cut for cards, waiting to be used. |
| `dict/` | The reading help's downloads, with `corpus/`, `mt/` and `components/` (below). |
| `docs/` | The design notes: `languages.md`, `lang/<code>.md` (each language's conventions), `mobile.md`, `installer.md`, `studio-exercises.md`, the notes on character components, and the prompts. |
| `guide/` | The PDF manual's source; its build is `HOW TO USE THIS TOOLBOX.pdf`, at the top. |
| `html-guide/` | These pages: `markdown/` (their source), `build.py` and `engine/` (the compiler), `assets/` and `index.html` (the front page); `site/` is what a compile makes. |
| `.github/` | Its `guide-pages.yml` workflow: the guide, compiled and published on GitHub Pages. |
| `tests/` | The unit tests, `smoke.py`, the browser tests, and `fixtures/`: a small book, video and Anki deck in every language. |
| `.runtime/` | The environment, when the installer made it: `bin/micromamba`, `env/`, and micromamba's package cache, `mamba/`. |
| `.tls/` | The certificate `serve.py` makes on its first start. |

### Inside lib/

| Path | What it is |
|---|---|
| `languages.json` | The language registry: everything a language is, read by every tool through `languages.py`. |
| `lang/<code>.tex` | What each language decides in a book's LaTeX preamble. |
| `verbs/<code>.py` | How each language's verb entry (`\vb`) is read out of its dictionary. |
| `parseh.js` | With `parseh.css`: the palette and the themes, the language chips, the clipboard, the Browser/Mobile mode. |
| `mobile.css` | The mobile interface's sheet. |
| `activity.js` | With `activity.py`: what the server is working on — the **Working…** pill and the hub's panel. |
| `tex2html.py` | A book's reader, written from its chapters. |
| `bundle.py` | A book or a video as one zip. |
| `draft.py` | A book or a video started empty. |
| `runtime.py` | Finding the environment and making it; `env.sh` finds it for the shell scripts, and `launcher.py` starts Parseh on Windows. |
| `getdict.py` | With `getcorpus.py`, `getmt.py`, `getsyn.py` and the components' getter: the reading help's downloads. |
| `guidebuild.py` | Serving the guide at `/guide/`, and its **Compile the guide** button. |
| `fonts/` | Vazirmatn, Noto Nastaliq Urdu, Noto Naskh Arabic, Noto Serif Devanagari. The Japanese and Chinese faces are the system's own. |

### One folder per language

Every door files its content under the language it teaches, in a folder
named after the language in English, in lower case: `persian`, `arabic`,
`italian`, `japanese`, `french`, `german`, `turkish`, `english`, `hindi`,
`spanish`, `chinese`. The list comes from the language registry,
`lib/languages.json`, and nowhere else. A book, a video or a document
lying directly under `books/`, `youtube/videos/` or `markdown/library/`
— the layout from before there were languages — is still read, as
Persian, with a note to move it.

## A book

`books/<language>/<slug>/`, the slug being the book's short name in Latin
letters. The tests' small books, one in each language under
`tests/fixtures/books/` (`tests/fixtures/books/japanese/mini-ja/`, say),
are short ones to look at.

| Path | What it is |
|---|---|
| `book.json` | The title and author (and their transliterations), the language and the gloss language, the draft flag, the narration's recordings and what each covers. |
| `main.tex` | The edition's own title page, and the chapters it inputs. |
| `ch1.tex`, `ch2.tex` … | The chapters, written by hand: every chunk one `\ch` call (or `\chr`, `\chw`, `\chp`…). |
| `NOTES.md` | Notes on the edition, when it has them. |
| `annot/` | The annotated paragraphs an LLM wrote, batch by batch, when the book was made that way (`check_batch.py` and `assemble.py` read them). |
| `source/paras/` | The text the edition was made from, one file a paragraph (`ch1_p01.txt` …): what the chapters must still reproduce. |
| `src_chN.json` | In `source/`: the same paragraphs, one list per chapter, for `assemble.py`. |
| `reading.json` | The reader's own decisions: paragraphs that may depart from their source, runs of paragraphs folded away. |
| `audio/` | The narration: one or more recordings, and their transcripts. |
| `timings.json` | Where each subparagraph is in the recordings. A `% @par` comment above each subparagraph in the chapters says the same. |
| `review.json` | With its corrections and `review.html`: an alignment's review. |
| `markdown/` | The notes written into the book's seams (below). |
| `main.pdf` | *Built:* the PDF. |
| `reader/` | *Built:* `index.html`, and `ch-2.html` … for a book of several chapters. |
| `.build-key` | And `.reader-key`. *Built:* what the last build read, so that an unchanged book is skipped. |

What is *built* is made by **build**, **build PDF** and **rebuild the
reader**, and is never in a download: a stale copy carried back in would
show text the chapters no longer say. A book's **download** holds
`book.json`, every `.tex` (`main.tex` and the chapters), `NOTES.md`,
`source/`, `markdown/` and `reading.json` — and, as the shape you pick
asks, the timings, the alignment's review and `audio/` (never
`review.html`, which is a page). `annot/` is not in it in any shape: it
stays on this machine. Taking a book off the shelf with ✕ moves the
whole folder to `books/.trash/`.

## A video

`youtube/videos/<language>/<id>/`, where the id is the YouTube video's
own, or for a film on this machine the one the add page gave it.

| Path | What it is |
|---|---|
| `video.json` | The title and its native form, the channel, the language and the gloss language, the level, the blurb, the draft flag. |
| `transcript.txt` | The transcript as it was pasted: the text every caption is checked against. |
| `annotations.json` | Every caption's chunks and glosses: what the player shows. |
| `parts/NN.json` | The batches an LLM annotated, when it was made that way; `merge_parts.py` assembles the file above from them. |
| `waveform.json` | The picture of the sound, once one has been recorded. |
| `media.<ext>` | The film itself, for a video that is a file on this machine. |
| `markdown/` | The notes written into the video's seams (below). |

The player's **⤓** downloads all of it as one zip, a film on this machine
included (`lib/bundle.py pack --media text` leaves the film out). A video
is on the index as soon as its folder is there: there is nothing to
build. Taken off with ✕, it goes to `youtube/videos/.trash/`.

## A studio document

`markdown/library/<language>/<id>/`, filed under the document's target
language (its front matter's `target:`) and moved when that changes. The
id is made from the first title and a random suffix, and never changes,
whatever the document is renamed to.

| Path | What it is |
|---|---|
| `source.md` | The document: its front matter and its Markdown — the one truth. |
| `meta.json` | Its name, its tags, its uid, its dates, its last build and the options it was built with. |
| `images/` | Its pictures. An SVG gets a `.svg.pdf` twin for the PDF, a PDF a `.pdf.svg` twin for the page. |
| `audio/` | Its recordings. |
| `build/` | *Built:* `main.tex`, `main.pdf`, and what the build needed beside them. |

A document's **Download ▾** gives the Markdown alone, the Markdown with
its pictures and recordings as a zip (its tags travel beside it, in
`<name>.tags.json`), the `.tex` or the PDF. The library's **Backup**
takes every document whole, `meta.json` included, so that **Load from
backup** brings each back as itself.

### A note in a seam

A note written between two lines of a book or a video is a studio
document in every respect but where it lives: in that book's or video's
own `markdown/` folder, laid out as the studio's library is —
`books/<language>/<slug>/markdown/<language>/<id>/source.md`. Its front
matter says where it sits (`anchor: after sub …`, `anchor: before cap …`),
and it travels in the book's or the video's download.

## An exercise deck

`exercises/<language>/<slug>/`:

| Path | What it is |
|---|---|
| `deck.json` | Its name, its language, its id, and the options that differ from the defaults. |
| `items/<id>.json` | One exercise: its Markdown, its footnotes, where it came from. |
| `schedule/<id>.json` | Its state and every answer given (no file while it is new). |
| `images/` | The pictures its exercises use. |
| `audio/` | The recordings its flashcards play. |

A deck moves between machines by its **Export** (with or without the
scheduling) or by the Exercises page's **Backup**, never by git. A
deleted deck goes to `exercises/.trash/`.

## The Anki card store

`youtube/anki/`, shared by the book reader and the video player. A deck
is a folder, `<language>/<deck>/`, holding:

| Path | What it is |
|---|---|
| `deck.json` | The deck's name, its language, its Anki id. |
| `cards/<id>.json` | One card a file: the truth the `.apkg` is built from. |
| `media/` | The screenshots and recordings the cards show. |
| `deleted/` | Cards a sync retired because you deleted them inside Anki. Move one back into `cards/` to undo. |

And beside the decks, for the whole store:

| Path | What it is |
|---|---|
| `inbox/` | The exports you dropped on the sync page. |
| `build/` | The `.apkg` files built to import into Anki. |
| `notetypes.json` | With `seen.json`: what the store knows of your Anki collection. |

## The clip tray

`clips/` holds, in one flat folder, every recording cut from a narration
or a film and every frame captured from a video, under names no other
file of the toolbox has — so that a card's Markdown naming one can be
pasted anywhere. A document, a deck or an Anki card that uses one takes a
copy when it is saved; **The clip tray** on the hub plays them and deletes
what no card needs any more.

## The reading help's downloads

| Path | What it is |
|---|---|
| `dict/<code>.db` | A dictionary, from Wiktionary. |
| `corpus/` | Sentences somebody translated, from Tatoeba: `<code>-<gloss>.db`, one a pair of languages. |
| `mt/` | The translation engine, and one folder of model per pair, `mt/<from>-<to>/`. |
| `mt/synonyms.en.json` | The WordNet synonyms the machine's reading uses. |
| `components/` | The Kanji and Hanzi component packs, `<source>.db`. |

All of them are got and removed on `/lookup/` (or by the commands in [The
command line: content, lookup, Anki](commands-content.md)).

## What is not in the repository

The repository ships the doors and none of the content: the language
folders under `books/`, `youtube/videos/` and `markdown/library/` hold a
`.gitkeep` and nothing else. What you add there — books, videos,
documents and their notes — shows in git as untracked files: nothing
ignores them, and nothing commits them unless you do.

Git ignores outright, so that a stray `git add` cannot take them:

- your study state and your cards: the exercise decks, the Anki store,
  the clip tray;
- the recordings and films: `audio/` under a book, `media.*` under a
  video;
- everything a build makes: the PDFs, the readers, the library page
  (`books/index.html`), a studio document's `build/` — but not the guide's
  compiled `html-guide/site/`, which is committed so that GitHub Pages can
  publish it;
- a book or a video taken off the shelf (`.trash/`), the downloads of the
  reading help, the environment (`.runtime/`), the certificate (`.tls/`),
  `serve.log` and `.serve.pid`.

The one built file that is tracked is the PDF manual, `HOW TO USE THIS
TOOLBOX.pdf`, so that a fresh checkout has it.
