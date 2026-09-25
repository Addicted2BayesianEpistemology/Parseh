---
title: "The command line: content, lookup, Anki"
linkTitle: "Commands: content, lookup, Anki"
weight: 3
description: The tools behind the reading-help downloads, the book and video pipelines, the bundles, the Anki sync and the studio's PDF, with their flags.
---

> **For the command line — and only if you want it.** The reading-help
> page (Settings → Reading help) gets and removes every dictionary, corpus, model and
> component pack with a button; the readers and the player edit, download
> and take back books and videos; the **Anki** page syncs your cards; the
> studio builds its PDFs. These are the scripts under those buttons, for
> scripting, for a machine with no browser, or for mending something by
> hand.

Run them from the top of the repository unless a heading says otherwise,
with the Python of Parseh's environment (`python3 lib/runtime.py python`
prints its path). [The command line: install, serve, build](commands.md)
has the installers, the server and the builds.

## Reading help: dictionaries, sentences, models

Each of these downloads somebody else's work once, builds a file from it
on your machine, and never sends anything about what you read. They are
exactly what the buttons of the reading-help page run, with a progress bar over them;
**remove** there deletes the file.

### A dictionary: getdict.py

```bash
# what is installed, and what is not
python3 lib/getdict.py
# fetch Persian from Wiktionary and build dict/fa.db
python3 lib/getdict.py fa
# ... and keep the download
python3 lib/getdict.py hi --keep
# build from a kaikki.org JSONL already here
python3 lib/getdict.py es --from FILE
# ... into PATH, leaving dict/ alone
python3 lib/getdict.py es --from FILE --out PATH
# every language the toolbox teaches
python3 lib/getdict.py --all
# stop after N entries, for a trial
python3 lib/getdict.py fa --limit 1000
```

The source is Wiktionary's own extract, from kaikki.org: tens or hundreds
of megabytes a language (Persian about 20 MB built, German over 300). Run
it again for a language to rebuild it — the **rebuild** button — and pick
up a year of Wiktionary's edits and whatever a newer Parseh keeps from it.

### Sentences somebody translated: getcorpus.py

```bash
# what is installed
python3 lib/getcorpus.py
# Persian, glossed in English: corpus/fa-en.db
python3 lib/getcorpus.py fa
# Persian, glossed in Italian
python3 lib/getcorpus.py fa it
# every language, glossed in English
python3 lib/getcorpus.py --all
# keep the Tatoeba exports it downloads
python3 lib/getcorpus.py fa --keep
```

A corpus is a **pair** of languages — what you read, and what its glosses
are written in — so it takes two codes where a dictionary takes one. The
sentences are Tatoeba's, under CC BY 2.0 FR.

### A translation model: getmt.py

```bash
# what is installed
python3 lib/getmt.py
# Persian to English, into mt/fa-en/
python3 lib/getmt.py fa en
# just the engine, without a model
python3 lib/getmt.py --engine
# every pair on offer
python3 lib/getmt.py --pairs
```

The engine is bergamot-translator, the one Firefox's translations use,
and it runs as WebAssembly inside the page; a model is about 20 MB a pair.
Mozilla trains its pairs against English, so every pair has English on
one side: Persian glossed in English has a model, Persian glossed in
Italian has none.

### Synonyms: getsyn.py

```bash
# get it, or say it is already there
python3 lib/getsyn.py
# fetch WordNet again and build it afresh
python3 lib/getsyn.py --rebuild
# take it off disk
python3 lib/getsyn.py --remove
```

About a megabyte, `mt/synonyms.en.json`, from Princeton WordNet: it lets
the mark over a machine's reading find `begin` where the dictionary said
`start`.

### Kanji and Hanzi components: getdecomposition.py

```bash
# KanjiVG, for Japanese
python3 lib/getdecomposition.py kanjivg
# Make Me a Hanzi, for Chinese
python3 lib/getdecomposition.py makemeahanzi
# CJKVI-IDS, the fallback for both
python3 lib/getdecomposition.py cjkvi
# from a file already here, offline
python3 lib/getdecomposition.py kanjivg --input path/to/source.zip
```

Each pack is a pinned version, checked before it is installed, and kept
in `components/`. The **Decompose Kanji** and **Decompose Hanzi** buttons
of the readers use them, offline.

### Looking, without writing

Three tools read what is installed and write nothing — the quickest way to
see what a reader would be shown:

```bash
# every language, and its dictionary if any
python3 lib/lookup.py
# what the dictionary says about a phrase
python3 lib/lookup.py fa "دوباره می‌سازمت"
# the sentences it would offer
python3 lib/corpus.py fa en "سیگار می‌کشد"
# each verb hit, and the \vb it would offer
python3 lib/verbs/__init__.py de "stand auf"
```

`lib/verbs/__init__.py` also takes `--gloss=<code>` (the language the
glosses are in) and `--sentence="…"` (the sentence around the phrase).

## Books by hand

What the reader's pencil, its **download** and the library's **Bring a
book back** panel do, from a terminal.

### Bundles: bundle.py

```bash
# a book or a video, as one zip
python3 lib/bundle.py pack <slug-or-id> [-o out.zip]
# a book's three shapes
python3 lib/bundle.py pack <slug> --audio text|linked|full
# what is in it; writes nothing
python3 lib/bundle.py inspect bundle.zip
# back into the toolbox
python3 lib/bundle.py install bundle.zip [--replace]
```

`pack` takes a book's slug, a video's id or a directory. `--audio` (or
`--media`) says how much of the recording comes with it: `text` (the
reading edition alone, nothing left pointing at a narration), `linked`
(everything but the recording — a book's default) or `full` (all of it; a
video that is a file on this machine defaults to this). `install` checks
the bundle exactly as the upload panel does, and overwrites a book or a
video of the same name only with `--replace`.

### Starting from nothing: draft.py

```bash
python3 lib/draft.py book --text chapter.txt --lang fa \
  --title "…" --into books/
python3 lib/draft.py video --transcript t.txt --lang ja \
  --url "https://…" --into youtube/videos/
```

The text divided into chunks with every gloss blank, as **Write it here,
by hand** on the add-a-book page and **Nobody — I gloss it in the player** on
the add-a-video page do. Without
`--into` nothing is written: it prints what it would make (`--show`
prints every file). A book also takes `--gloss`, `--slug`, `--author`,
`--title-latin`, `--title-en`, `--author-latin`, `--year`, `--blurb` and
`--chapter`; a video `--gloss`, `--id`, `--title`, `--title-native`,
`--channel`, `--level` and `--blurb`.

### Checking and building an edition

```bash
# one annotated paragraph, before assembling
python3 lib/check_batch.py annot/ch3_p12.json --book <slug>
# source/src_chN.json, what assemble.py checks against
python3 lib/chapter_src.py --book <slug> --all
# annotated paragraphs into a chapter's LaTeX, refused unless faithful
python3 lib/assemble.py <batch.json> <src_chN.json> <label> <out.tex> \
  [--partial] [--book <slug>]
# every built paragraph against its source
python3 lib/verify_book.py --book <slug>
# the chunks, numbered as the reader numbers them
python3 lib/texwrite.py books/<language>/<slug>/ch1.tex [N]
# a book's text, recovered from a PDF
python3 lib/extract_pdf.py book.pdf --lang fa --out clean.txt
```

`--book` takes a slug, `<language>/<slug>` or a directory; without it
the tools use `$FRANK_BOOK`, then the book the current folder is in.
`check_batch.py` exits with the number of errors; `assemble.py` ends its
report with *ALL PARAGRAPHS CLEAN* or the number of problems. A chunk nobody
has glossed is not an error to either checker — `check_batch.py` counts such
chunks in one note per paragraph, and `check_annotations.py` in one per
video (*N of M chunks have no gloss yet*) — while a chunk half glossed is.

### Narrations and word lines

```bash
# align the narration, write the times
python3 lib/timestamp.py --book <slug>
# one recording only
python3 lib/timestamp.py --book <slug> --narration <id>
# no transcript: share the recording out over its text
python3 lib/timestamp.py --book <slug> --spread
# word lines for a Japanese or Chinese book's chunks
python3 lib/fill_words.py --book <slug> [--dry-run]
# ... or a video's
python3 lib/fill_words.py --video <id> [--dry-run]
```

`timestamp.py` also takes `--force` (re-time what already has a time),
`--no-snap` (no snapping to silences, which needs `ffmpeg`),
`--from-sidecar` (write the times back into the chapters from
`timings.json`), `--apply-review` and `--dry-run`. The reader's
**narration** panel runs it for you: **align**, **estimate times**. A
word line already there is never replaced by `fill_words.py`, which
writes through the same checker the reader's editor uses.

### Off the shelf, and back

The ✕ on a card moves the book to `books/.trash/` (a video to
`youtube/videos/.trash/`), named after it and the minute. To bring one
back, move its folder into `books/<language>/` again and write the
library page afresh: `python3 lib/make_index.py`.

## Videos, from the youtube/ folder

The pipeline an LLM session in Claude Code follows for a long video
(`youtube/PROMPT.md`), batch by batch. Run these from `youtube/`:

```bash
# how the captions divide into batches
python3 lib/slice_part.py videos/<language>/<id>
# the captions of one batch, as JSON
python3 lib/slice_part.py videos/<language>/<id> 0 25
# one batch, checked on its own
python3 lib/check_part.py videos/<language>/<id> parts/03.json
# parts/ + transcript.txt -> annotations.json
python3 lib/merge_parts.py videos/<language>/<id>
# the whole video: must say 0 error(s)
python3 lib/check_annotations.py videos/<language>/<id>
# a video in the older format
python3 lib/import_old_video.py "<old folder>" [--dry-run] [--replace]
```

`merge_parts.py` assembles `annotations.json` from the batches **while a
video is being added**, and the batches are dropped once it is on the shelf
([parts/ is retired](../videos/the-files.md#parts)) — so there is nothing
left for a later run to overwrite. Run by hand on a video old enough to
still carry `parts/`, it now **refuses** rather than rebuilding over work
done in the player: it says which captions differ, at which times and in
which fields.

## Languages

```bash
# what a language needs, and the languages there are
python3 lib/newlang.py
# every entry validated, every file it needs present
python3 lib/newlang.py --check
python3 lib/newlang.py ko --name Korean --native 한국어 \
  [--script … --chars … --font … --web-font …]
```

A language is a row of the registry and the files it implies — the row in
`config/languages.json`, this machine's languages, which an update keeps
(`--shipped` writes Parseh's own `lib/languages.json` instead);
`newlang.py` writes them all at once, and says what it did not write — the
verb recipe, `lib/verbs/<code>.py`.

## Anki, from the youtube/ folder

The **Anki** page on the hub (`/anki/sync/`) is these three with a
wizard over them. Run them from `youtube/`:

```bash
# what a sync would change; writes nothing
python3 lib/sync_apkg.py <export.apkg> --dry-run
# pull the edits made in Anki into the store
python3 lib/sync_apkg.py <export.apkg>
# ... and retire cards deleted inside Anki
python3 lib/sync_apkg.py <export.apkg> --delete-missing
# build the .apkg to import into Anki
python3 lib/anki_export.py anki/<language>/<deck> [out.apkg]
# bring a deck into the store for the first time
python3 lib/import_apkg.py <file.apkg> [--merge]
```

`--delete-missing` moves the retired cards' files to
`anki/<language>/<deck>/deleted/`, so it can be undone. `anki_export.py`
writes `anki/build/<language>-<deck>.apkg` unless told otherwise.
`import_apkg.py` creates the decks it does not hold; with `--merge`, a
deck already held is given the cards it lacks.

## The studio's PDF, from the markdown/exlex/ folder

```bash
# a document's Markdown into a verified PDF, as Build PDF makes it
python3 exlex.py build answer.md [-o OUTDIR] [--scale S] \
  [--size 11|14|17|20] [--mono] [--no-verify]
# check a built PDF's text again
python3 exlex.py verify OUT/main.pdf OUT/main.tex
# what page 3 holds, in visual order
python3 exlex.py inspect OUT/main.pdf 3
# prepare the fonts and the hyphenation only
python3 exlex.py setup
```

The same `.tex` **Build PDF** writes: `--scale` is the size of the target
script against the Latin, `--size` the print size (**PDF options ▾**),
`--mono` black and white. The exit status is 0 when the PDF verified, 1
when its check failed, 2 for a wrong argument or a failed compile.
