---
title: Notes between the captions
linkTitle: Notes between captions
weight: 9
description: A studio document written into the seam between two captions — writing one, reading one, where it says it sits, and where it lives.
---

A transcript is a caption and its gloss. It has nowhere to say the other
thing — that this idiom is the one from the first lesson, that the speaker
has just changed register, that the next four lines are a song and not
speech. A **note** is that somewhere.

## Writing one

Between any two captions — and before the first, and after the last — is a
**seam**, with a faint **+** in it that brightens when the pointer is near.
Press it (*write a note here*) and a new note is made, anchored to that
place, and opens straight in the editor, in a sheet over the page. It
starts with a title, **A note** (or **A note 2**, and so on, so that each
of a video's notes has a name of its own), and a line of text to write
over.

It is a **studio document** — not like one: the same editor writes it, the
same renderer draws it, and every mark of the dialect means what it means in
the studio, pictures, recordings and exercises included (the section
*Studio* explains the editor and the section *The Markdown dialect* what
it takes). A note's title is its **name** among this video's notes: two
notes of the same video link to each other by it —
`[as I said](doc:On the greeting)` — the name must be unique there, and
renaming a note follows every link to it, exactly as in the studio's own
library, but within this video's notes alone.

## Reading one

A seam with a note in it carries a small mark: **✎** and the note's title.
Click it and the note opens **over** the page — never inside the
transcript, because the transcript is the point, and a page with an essay
between two captions is not a transcript any more. The video pauses.

The sheet's bar has the title, **edit** (the note in the editor), **read**
(back to the note as it renders) and **✕**. Esc, the ✕, or a click on the
darkened page around it closes it; the marks are then drawn again, in case
the title changed.

**Rest the pointer on a mark first, and it says what the note is.** After a
third of a second — so that sweeping across a seam on the way to a phrase
does not light up every note it passes — a small card opens by the mark:
the note's title, the start of what it says (about 280 characters, the
markup taken out), and *click to open*. The keyboard gets the same card:
Tab to a mark and wait. It goes when the pointer leaves the mark, on Esc,
on a click and on any scroll, and clicks pass straight through it. On a
touch screen there is no card: a tap opens the note.

**The card is letters and nothing else.** A note is a file that travels —
inside a video's download, written in somebody else's toolbox — and a card
that opens because a pointer happened to cross a seam must never do more
than show text. Nothing in a note is run or drawn there; clicking the mark,
which opens the note itself, is a choice.

## Where a note says it sits

In its own front matter, one line:

```yaml
---
title: On the greeting
target: fa
anchor: before cap 12
---
```

`before` or `after`, then `cap` (a caption), then the caption's **start**
in seconds — what `transcript.txt` is keyed by, which is why a note stays
put when the phrases of a caption are edited, cut or joined. The seam
between the captions at 6 and 12 seconds is both `after cap 6` and
`before cap 12`; a note made with its **+** says the second, and one made
after the last caption says `after cap` and that caption's start.

**Moving a note is editing that line**, in the note's editor or in the file:
nothing else has to be told, because the file is the truth here as
everywhere in Parseh.

A note whose anchor names a caption that is not there — a start that was
moved, a line mistyped — is not dropped and is not an error. It is shown at
the **end** of the transcript, its mark dashed, and its card says *this
note names a caption that is no longer in the video — open it and change
its anchor line*. That is where somebody will look for it.

> **After moving a caption's start.** [The timings](the-timings.md) move
> a caption's start in the video's files, but a note anchored to that
> caption keeps its old number and comes adrift at the end. Open it and put
> the caption's new start in its anchor line, in seconds — the time you gave
> it in the timings, where `0:12.50` is `12.5` here.

## Where notes live

In the video's own folder, never in the studio's library, because a note
is about **this** video:

```text
youtube/videos/persian/<id>/markdown/persian/<note-id>/source.md
```

— the studio's own layout (a folder per language, a folder per document,
with its `meta.json`, its `images/` and `audio/`), rooted in the video's
`markdown/` folder.

Two things a note does not do:

- **It is never built.** A note is read on its page and nowhere else: there
  is no PDF of it and no `.tex`, and the server refuses both — *a note
  beside a book or a video is read on its page and nowhere else: it is
  never built to a PDF and never taken away as LaTeX. Copy it into the
  studio if you want either.*
- **It is in no prompt.** Nothing Parseh hands a model mentions notes, and
  nothing should: a note is your own reading, which is exactly what a model
  has nothing to put in.

Notes **travel** with the video: the ⤓ download carries every note of it,
pictures and recordings included (an `.svg` figure excepted: it stays on
the machine it was drawn on), and bringing the zip back puts them
back ([Taking videos away](downloads-and-backups.md)).
