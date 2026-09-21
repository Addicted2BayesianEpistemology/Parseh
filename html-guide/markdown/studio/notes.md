---
title: Notes beside books and videos
weight: 11
description: A note written between two lines of a book or a video is a studio document too — the same studio, in a library of its own.
---

A reading edition is a text and its gloss, and a video is a transcript and
its gloss; neither has room to say the other thing — that this idiom is the
one from chapter two, that the speaker has just changed register, that the
next four lines are a quotation. A **note** is that room. You write it in
the seam between two lines of a book or a video, and it is a studio
document: not one *like* it, the same — written in the same editor, drawn
by the same renderer, with the same dialect, the same hover tools, the same
glosses and exercises. What differs is only **where it lives**.

## Writing one

Between any two lines of a book's reader, or of a video's transcript, there
is a small **+**. Press it and a new note is made there, and opens straight
in the editor, over the page. Afterwards the seam carries a mark with the
note's title: point at it to see the note's first lines, click it to open
the note over the page. The reader's and the player's own pages say more
about the seams and the marks: see the [books](../books/_index.md) and
[videos](../videos/_index.md) sections.

The window a note opens in has **edit**, which turns it to the editor, or
**read**, which turns it back to the note's page, and **✕**; Escape closes
it wherever the pointer is, even inside the note. Closing it draws the marks again, since the note's title
may have changed.

A new note starts short:

```markdown
---
title: A note
lang: en
target: fa
anchor: after sub 1.2-6f8f21d7175b
---

Written by hand, about the line above. Everything the studio can do goes
here; nothing here is ever built to a PDF.
```

- **`target:`** is the book's or the video's language, so the note opens in
  the face and direction of the text beside it.
- **`anchor:`** says where the note sits: `after` or `before` a line, `sub`
  for a book's subparagraph or `cap` for a video's caption, and which one.
  The book's line keeps its name through a rebuild; a caption is named by
  the second it starts at. Moving a note is editing this one line. A note
  whose anchor names a line that is no longer there is not lost: the reader
  shows it at the end, marked *adrift*, so you can open it and set its
  anchor again.
- **`title:`** is *A note* — or *A note 2*, *A note 3*…, since two notes of
  one book cannot share a name. Give it a name of its own; that is the name
  links to it spell.

## A library of their own

The notes of one book, or of one video, are a **library** of their own,
kept in that book's or video's folder (its `markdown/` subfolder) rather
than in the studio's library. So:

- **They travel with the book or the video** — in its download, in its
  bundle, in the shelf's backup — and never mix with the studio's own
  documents.
- **Names are unique among the notes of that book** and not across the
  toolbox: two books can each have a note called *Vocabulary*. The
  name-conflict dialog works there as it does in the studio.
- **Links reach the notes of the same book.** A link from one note to
  another — `[the first note](doc:A note)`, or through **Doc link…**, which
  lists that book's notes — works, is followed by renames, and appears in
  the other note's **↩ Linked from**. A link from a note to a studio
  document, or to another book's note, finds nothing.
- **Every page and button is there** — scoped to the notes. A note's page
  has its tags, its typography, its contents, its glosses, its exercises
  with **Check exercises** and **⤢ Enlarge**; its **← Library** opens the
  library of that book's notes, with the same search, tags, **Upload .md /
  .zip**, **Backup**, **Load from backup** and **Download N shown** as the
  studio's. (A document made there with **+ New** has no anchor, and the
  reader shows it at the end of the book, adrift.)
- **Exercise decks** — a note has **+ Deck** and **+ Add all exercises**,
  and its editor **Load from a deck…**, whenever Parseh knows which book or
  video the note belongs to; a deck's copy of an exercise links back to
  the note.

## What a note does not do

**A note is never printed.** It is read on its page and nowhere else:
**Build PDF** answers *a note beside a book or a video is read on its page
and nowhere else: it is never built to a PDF and never taken away as
LaTeX. Copy it into the studio if you want either.* — and **Download ▾ →
LaTeX (.tex)** and **→ PDF** stay greyed out. To print one, copy its text
into a new document of the studio.

**No prompt asks for one.** A note is your own reading of your own book,
and nothing in the toolbox asks a model to write one: the LLM prompt knows
nothing of notes beside a book or a video, nor of `anchor:`. The buttons
are still there, as every button is — the notes library has **LLM
prompt** and **Paste LLM answer**, a note's editor has **Exercises ▾ →
Generate with LLM…** — and they work as they do in the studio; a document
pasted there is a note with no `anchor:`, shown at the end, adrift, like
one made with **+ New**.

**The preview on the mark is plain text.** Pointing at a note's mark in the
reader shows its title and its first lines — at most 280 characters, the
front matter, the footnotes and the pictures left out, and each exercise
shown only as `<Exercise>` — as text and nothing more: a note can come in a
bundle from somebody else's toolbox, and merely passing the pointer over it
must not do more than show its words. A touch screen has no pointer to rest,
and a tap opens the note.

Notes written before links named documents by name are brought up to names
the first time the notes of that book or video are opened after Parseh
starts, as the studio's library is (see
[Names and links](names-and-links.md#links-written-before-names)): notes
that were all called *A note*, as every new note once was, become *A note*,
*A note 2*, *A note 3*…, the oldest keeping the name.
