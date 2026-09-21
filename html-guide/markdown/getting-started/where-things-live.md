---
title: Where everything lives
weight: 8
description: The folders on the disk — the software, your books, videos, documents and decks, and what the toolbox makes — and what is in the repository and what never is.
---

Everything Parseh has is in its own folder: the software, everything you
put into it, and everything it makes. Outside it there are only:

- the models of the Chinese word analyzer, in `~/.pkuseg`;
- the environment, when you made it with your own conda;
- on a TeX Live that has no Italian hyphenation, the Italian patterns the
  server adds to your own TeX folders as it starts (`TEXMFHOME` and
  `TEXMFCONFIG`, with the XeLaTeX format rebuilt to take them), so that
  the PDF of a studio document written in Italian breaks its words where
  Italian breaks them;
- with `./install.sh --pdf`, the TeX packages it adds to TeX Live itself;
- in each browser, a few of your preferences.

Deleting the Parseh folder leaves these behind: [Removing
it](installing.md#removing-it) says where each of them is.

## The folder

```text
Parseh/
  books/                 the books
  youtube/videos/        the videos
  youtube/anki/          the Anki card store
  markdown/library/      the studio's documents
  exercises/             the exercise decks
  clips/                 the clip tray
  dict/  corpus/  mt/  components/
                         what the dictionaries' page fetches
  lib/  markdown/app/  markdown/exlex/  youtube/lib/
                         the software
  html-guide/            this guide
  guide/                 the PDF manual's source
  docs/                  notes on the design
  tests/                 the tests, and what they test with
  .runtime/              the environment the installer made
  .tls/                  the certificate
```

**What one of each is made of**:

- `books/<language>/<slug>/` — **a book**: `book.json`, `main.tex` and its
  chapters, `source/` (the text it was made from), `markdown/` (the notes
  written beside it), `audio/` (its narration), `reader/` (its reader,
  built) and `main.pdf`.
- `youtube/videos/<language>/<id>/` — **a video**: `video.json`,
  `annotations.json` (the glossed transcript), its transcript and parts,
  `media.*` (the film, for a video of your own), `markdown/` (its notes).
- `youtube/anki/<language>/<deck>/` — **a deck of the Anki card store**.
- `markdown/library/<language>/<id>/` — **a studio document**:
  `source.md`, `meta.json`, its pictures and recordings, `build/` (its
  PDF).
- `exercises/<language>/<slug>/` — **an exercise deck**: `deck.json`,
  `items/`, `schedule/` (your answers), `images/`, `audio/`.
- `clips/` — **the clip tray**: the recordings and frames cut for cards.
- `dict/`, `corpus/`, `mt/`, `components/` — **what the dictionaries' page
  fetches**: dictionaries, translated sentences, translation models,
  character packs.

**The files at the top**:

| File | What it is |
|---|---|
| `install.sh`, `install.bat` | the installers, for Linux and macOS, and for Windows |
| `Parseh.command` | the Mac's double-click: install once, then start |
| `serve.sh`, `serve.bat` | starting and stopping, on Linux and macOS, and on Windows |
| `serve.py` | the server itself |
| `build.sh` | building the books: their PDFs, their readers, the library page |
| `environment.yml` | what the environment holds |
| `HOW TO USE THIS TOOLBOX.pdf` | the PDF manual |
| `serve.log`, `.serve.pid` | the server's log and its process number, on Linux and macOS |
| `.setup-done` | the Windows wizard has run through |

**Every kind of content is filed under its language**, in a folder named
after the language in English, in lower case: `persian`, `arabic`,
`italian`, `japanese`, `french`, `german`, `turkish`, `english`, `hindi`,
`spanish`, `chinese`. A book, a video or a note lying directly under
`books/`, `youtube/videos/` or `markdown/library/` — the way they were kept
before Parseh had languages — is still read, as Persian, with a note to
move it.

You never need to touch these folders: every door adds, changes, backs up
and removes what is behind it from its own pages. They are described here
so that you know what to keep safe, and what a folder you see is for.

## What is in the repository

The repository holds **the software, and not your content**. A fresh copy
of Parseh has:

- all the code, the fonts of Persian, Arabic and Hindi, the language
  registry, and the installers;
- the studio's starting pages — what a new document opens with, one for
  each language — with their pictures and their recording;
- this guide's pages, and the PDF manual;
- the tests, with a small book and a short video in each language to test
  with.

## What never is

What you read and write is yours, not the software's, and the repository
leaves it out.

**Your books, videos and studio documents** — in `books/`,
`youtube/videos/` and `markdown/library/` — are *untracked*: git shows them
as new files, and what you do with them is up to you.

**The rest, git ignores altogether**:

- the narrations, hundreds of megabytes each:
  `books/<language>/<slug>/audio/`;
- the films of your own videos: `media.*` beside each video;
- your Anki cards and decks: `youtube/anki/`;
- your exercise decks, with every answer you gave in them: `exercises/`;
- the clip tray: `clips/`;
- the dictionaries, sentences, translation models and character packs —
  somebody else's work, under somebody else's licence: `dict/`, `corpus/`,
  `mt/`, `components/`;
- what is built — the readers, the library page, the PDFs: `reader/`,
  `books/index.html`, `main.pdf` (this guide's compiled pages,
  `html-guide/site/`, are the one exception: they are committed, so that
  GitHub Pages can publish them);
- the environment, the certificate, the log: `.runtime/`, `.tls/`,
  `serve.log`.

So a copy of the folder is how your content moves — or, better, the
backups: [Backups at a glance](backups.md) has the four shelves, and a
single book, video, document or deck travels as its own zip from its own
page.

## Kept in the browser

A few things are not in the folder at all, because they are yours in one
browser rather than the toolbox's: the theme, the language picked on the
chips, the **Browser | Mobile** choice, where you are in each book and the
narration's speed, the switches of the reader and the player, the settings
of the **Aa** panels, the kanji you marked as known. Each browser keeps its
own, per address, and a backup does not carry them.

## Pages that open from the disk

Three kinds of page are plain files that a browser opens without the
server: a book's reader (`books/<language>/<slug>/reader/index.html`), the
books' library page (`books/index.html`), and this guide
(`html-guide/index.html`). They read as they always do; whatever needs the
server — saving, uploading, building, a backup — needs the page opened from
Parseh's own address, and the library page's buttons say so when it is
not.
