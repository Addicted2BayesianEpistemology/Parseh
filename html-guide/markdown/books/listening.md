---
title: Playing and listening
weight: 5
description: The narration, a subparagraph at a time or straight through — continuous, loop, the gap, the speed, stop at a change, listen, follow.
---

A book with a recording plays in step with its text. The controls are in
the first row of the header, and appear only once the book has a recording
([Adding a narration](doc:Adding a narration)).

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
| **continuous** | on to begin with: at the end of a subparagraph, the next one plays | — |
| **loop** (**R**) | plays the same subparagraph again and again; while it is on, **gap** appears beside it, the pause between repetitions: 0 s, 0.5, 1, 1.5, 2, 3 or 5 s | the gap |
| **stop at a change** | off to begin with. On, playing holds where a new chapter or a new section begins, shows the new place, and waits for **▶** — which then plays *into* the new chapter rather than repeating the last subparagraph | yes, for every book |
| the speed | 0.5 to 1.5 times | yes |

Opening a sheet over the page — the chunk sheet, the card sheet, book info,
the narration panel, the fold sheet — pauses the recording; closing it
plays on where that makes sense.

## Listening rather than reading

**listen** puts the recording on and leaves the text alone: nothing is
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

Two more buttons wake up while listening, and start unpressed every time
**listen** is turned on:

- **follow** puts the mark back on the text the way a video's captions
  follow the video: it moves to the subparagraph the recording has reached,
  and carries straight on — it never stops at a subparagraph's end. It never
  touches your reading place: turn it off, or turn **listen** off, and the
  mark goes back where you were reading.
- **scroll to it** means something only together with **follow**: it keeps
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
