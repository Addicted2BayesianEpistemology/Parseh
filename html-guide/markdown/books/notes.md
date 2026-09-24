---
title: Notes in the seam
weight: 10
description: A note between two subparagraphs — writing one, reading it, where it lives and how it says where it sits.
---

A reading edition is a text and its gloss, and there is nowhere in it to say
the other thing — that this idiom is the one from chapter two, that the
next four lines are a quotation, that the narrator has just changed
register. A **note** is that somewhere: a short document in the seam between
two subparagraphs.

## Writing one

Between any two subparagraphs — and after the last one — there is a faint
**+** (*write a note here*), which shows when the pointer is in the seam.
Press it, and a new note is made there and opens straight in the editor,
over the page.

A note is a **studio document**. Not *like* one: the same store keeps it, the
same editor edits it, the same renderer draws it, and every mark of the
studio's Markdown means what it means there — target-language text, colours,
boxes, exercises, pictures, recordings; the guide's sections on the studio
and its Markdown dialect cover all of that. The note is written in the book's language, so
it opens in the same face and direction as the text beside it.

## Reading one

A seam with a note in it carries a small mark with the note's title. Click
it and the note opens **over** the page — not inside it, because the reading
is the point, and a page with an essay between two subparagraphs would not
be a reading edition any more. The window's head has **edit**, which turns
it into the editor, **read**, which turns it back, and **✕**; **Esc** or a
click outside close it. When it closes, the marks are redrawn, so a new
title shows at once.

**It opens at once, even from another room.** What the window shows is the
note on the studio's own sheet — the same face, the same colours, the same
marks — and nothing else: no editor, no scripts, none of the studio's
machinery. The reader also **fetches the notes within a screen of where you
are** before you ask for one, so opening a mark is instant over a slow
tunnel. Where the full page is wanted, **open in the studio** is in the
window's head. A note that **holds an exercise** opens the full studio page
straight away instead, so an exercise is never shown as something that
cannot be answered.

**A folded run keeps its notes.** Folding a run of paragraphs hides the
seams, and with them their marks; so the fold bar carries **a row of the
marks of every note inside the run** — the first three, then *+N more*,
which shows the rest. Open the run and the row goes: the notes are back in
their own seams.

**They come with the book onto a phone.** *Keep on this phone* lists them as
one line of its own — *its notes · 34 · about 280 kB* — ticked to begin with,
and you can untick it like any other. Kept, the marks are in their seams and
the notes open with the computer asleep, off or a train away, in the studio's
own face and colours; a note that holds an **exercise** can be answered there
exactly as it can at the desk. Their **pictures** come with them; their
**recordings** are a line of their own further down the list, beside the
book's narrations, so nothing heavy is ever kept by surprise. Write a new note
at the desk and its mark appears on the phone the next time the two can reach
each other, without keeping anything again — and the book says it is out of
date, so the note itself is one tap away. A note you **delete** is given back
the next time you press *Save* on that list, which says how many before it
does it. All of it: [Browser and Mobile](../getting-started/mobile-mode.md).

**Rest the pointer on a mark first**, and after a moment — a third of a
second, so that sweeping across a seam on the way to a word does not light
up every note it passes — a small card opens beside it: the note's title and
the start of what it says, a few lines of plain text. The keyboard gets the
same card: **Tab** to a mark and wait. The card goes when the pointer
leaves, on **Esc**, on a click and on any scroll; it stays while the pointer
is on the card itself, so a long excerpt can be read to the end, and once one
card is up the next mark along shows its own at once. On a touch screen
there is no hover and so no card: a tap opens the note.

The card is **letters and nothing else**. A note is a file that travels — in
a book's download, written in somebody else's toolbox — so a card that opens
because a pointer crossed a seam never does more than show text: nothing in
the note's Markdown is run or drawn there. Clicking the mark, which opens the
note's page, is the choice it always was.

## Where notes live

In the book's own folder, never in the studio's library, because a note is
about *this* book:

```text
books/persian/<slug>/markdown/<language>/<id>/source.md
```

They travel in the book's download in every shape, even **the text alone**:
they are part of the content ([Taking a book away](doc:Taking a book away)).

Two things a note does not have. It is never built into a PDF and never
downloaded as `.tex` — it is read on its page and nowhere else, and the
server refuses those doors for a note rather than merely hiding them. And it
is in no prompt: nothing Parseh hands a model mentions notes. A note is your
reading of your own book.

## Where a note says it sits

In its own front matter, one line:

```yaml
---
title: On the second qasida
target: fa
anchor: after sub 1.2-6f8f21d7175b
---
```

`before` or `after`, then `sub` (a subparagraph), then the subparagraph's
**key**: its label and a fingerprint of its text. The key stays the same
through a rebuild, an edited chunk, and chunks cut or joined — so a note
stays put through all of those.

The front matter, and not a database, because the file is the truth here as
everywhere in Parseh: **moving a note is editing that one line**, in the
editor like any other line of the note.

A note whose anchor names a place that is no longer there — the text was
rewritten under it, or the line was mistyped — is not dropped and is not an
error. It is shown at the end of the book, marked **adrift** (*this note
names a place that is no longer in the book — open it to see what it says,
and change its anchor line*), which is where somebody will look for it.
