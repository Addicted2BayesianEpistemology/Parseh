---
title: Playing and listening
weight: 5
description: The narration, a subparagraph at a time or straight through — keep going, loop, between repeats, the speed, wait at each new chapter, listen, highlight.
---

A book with a recording plays in step with its text. The controls are in
the first row of the header, and appear only once the book has a recording
([Adding a narration](doc:Adding a narration)); the ones you reach for less
live in the **Listening** group of the **⚙ page** panel, the same switches
under their longer names ([The ⚙ settings of a page](../getting-started/page-settings.md)).

## A subparagraph at a time

Everything in the reader plays a **subparagraph**: the stretch of the
recording that reads it, and then it stops. A click anywhere in a
subparagraph plays it and makes it the reading place; **▶** (or **Space**)
plays the reading place and **‖** pauses; **→** and **←** play the next and
the previous one. With no reading place yet, **▶** starts at the first
subparagraph that has a time.

A subparagraph with no time in the recording is not played, and the arrows
walk past it — but clicking it still moves the reading place there, which is
all the mark means in a book with no narration at all.

| Control | What it does | Remembered |
|---|---|---|
| **keep going** | on to begin with: at the end of a subparagraph, the next one plays. Off, you practise one subparagraph at a time. The panel calls it **Keep playing into the next line** | yes, and it follows you |
| **loop** (**R**) | plays the same subparagraph again and again; while it is on, **between repeats** appears beside it, the pause between repetitions: 0 s, 0.5, 1, 1.5, 2, 3 or 5 s. The panel calls them **Repeat this line** and **Pause between repeats** | the pause between repeats |
| **Wait at each new chapter** | only in the panel, under **Listening**. Off to begin with. On, playing holds where a new chapter or a new section begins, shows the new place, and waits for **▶** — which then plays *into* the new chapter rather than repeating the last subparagraph | yes, for every book |
| the speed | 0.25 to 2 times (**Playback speed** in the panel; the **[** and **]** keys step it) | yes |
| **↺** and **↻** | back and on by **Skip distance** seconds — 1, 2, 5, 10, 15, 30 or 60, set in the panel; **Shift+←** and **Shift+→** do the same | yes |

Opening a sheet over the page — the chunk sheet, the card sheet, book info,
the narration panel, the fold sheet — pauses the recording; closing it
plays on where that makes sense.

## Waiting while you read a gloss

**Pause while a gloss is open** — in the panel, under **Glosses in a cloud**, which
is the page's **hover** — makes the recording wait
while a gloss cloud is open. It is off to begin with. On, pointing at a
chunk (or tapping it) pauses a playing recording, and closing the cloud lets
it go on a third of a second later — so moving from one chunk to its
neighbour is one pause, not a stutter. A recording you paused yourself stays
paused. In **loop**, where the recording is silent between two repeats, the
cloud takes the wait too, and the repeat starts a third of a second after
the cloud closes. In **keep going** the wait between two subparagraphs is a
tenth of a second, and is left alone.

It is remembered on this device only, and is not drawn in a book with no
recording. On a phone it is in the same panel, which opens as a sheet
([Browser and Mobile](../getting-started/mobile-mode.md#the-books)).

## Listening rather than reading

**listen** — **Listen on its own** in the panel — puts the recording on and leaves the text alone: nothing is
highlighted, nothing scrolls, and the reading place stays where you left it.
It is the one way to put a book on and let it run. A **seek bar** comes with
it, so you can start from any moment of the recording, not only from the
reading place.

**A fold is still a fold.** A run you folded away is text you have said you
do not want, and played straight through it would be read out all the same.
So listening stops at the first folded run ahead, and leaves the playhead at
the *end* of that run: the next **▶** carries on after the text that was
folded. The seek bar is there for anyone who meant otherwise — drag it into
a folded stretch and that stretch plays.

Two more buttons are drawn only while listening, and start unpressed every time
**listen** is turned on:

- **highlight** puts the mark back on the text the way a video's captions
  follow the video: it moves to the subparagraph the recording has reached,
  and carries straight on — it never stops at a subparagraph's end. It never
  touches your reading place: turn it off, or turn **listen** off, and the
  mark goes back where you were reading.
- **keep in view** means something only together with **highlight**: it keeps
  the marked subparagraph in view. Without it, the mark moves and the page
  does not.

**listen** is a habit of the moment and is not remembered: open the book
again and you are reading it. Turn it off and playing is by subparagraph
again, stopping at the end of the one under the playhead.

## A book in several recordings

A book may be recorded a part at a time ([Adding a narration](doc:Adding a narration)).
Nothing about playing changes: the reader moves from one recording to the
next as you read across the seam, and the time in the header says which
recording it is counting in (`1:12 / 8:40 · n2`).

## When the recording will not play

If the recording cannot be loaded, or cannot be sought (the page served by
something other than Parseh, which answers the browser's requests for a
piece of the file), the header shows a warning in red, and **pick the file**
in it lets you choose the recording from the disk to play from instead. A narration named in `book.json` but missing from the book's
folder is reported in the narration panel.
