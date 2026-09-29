---
title: A book made by an agent
weight: 3
description: Watching a book grow in the library while an agent you choose writes it — the making panel, the asks you steer it with, and Finish.
---

An edition made the way the first ones were — an agent recovering the text,
deciding the chapters and annotating ten paragraphs at a time, with a checker
after every batch — takes days. So the book does not wait for the end to
appear: it is on the library from the first minute, marked **being made**,
and everything that used to be done in a terminal is a button. This page is
about what happens after **make the book's folder** on the add page ([Adding a
book](doc:Adding a book)): opening the folder in an agent, watching the book
grow, steering it, and finishing it.

**Parseh never starts an agent.** You use whichever you like — a coding
assistant in its own app, in a terminal or in an editor: anything that works
inside a folder — and Parseh does not name one as *the* way. It writes the
folder and the instructions, shows you where they are, and reads what the
agent writes.

## What is in the folder

The agent works on the real book, in `books/<language>/<slug>/`, not on a
copy, with Parseh's own tools run by Parseh's own Python (the instructions
give its full path, so nothing is installed or activated) and writing nowhere
but in that folder. Beside the book's own files the folder holds:

- **`original/`** The text the book is made from, as you chose it.
- **`AGENTS.md`** The instructions: where the tools are, the rules, what to
  keep. A plain file any agent can be told to read, and several read by
  themselves; `CLAUDE.md` is one line pointing at it.
- **`NOTES.md`** The book's journal: the source's oddities, the decisions
  taken, what is open. The agent keeps it, and its last lines are shown in the
  making panel.
- **`ASKS.md`** What you ask of the agent, one dated entry at a time
  (below). Empty until you write in it.
- **`making.json`** The record of the making: where it stands, for the panel
  and the library card.
- **`annot/`** The annotation the chapters are assembled from. It is the
  book's truth while it is made: the `.tex` files are output.

The agent never runs the full build (`build.sh`) while it works — the page
does that, one job at a time. It may typeset the chapters so far into
`frankdraft.pdf` beside the book, which is never `main.pdf`, so the two
cannot collide.

## Watching it

**On the library page** the book's card says **being made** with where the
making stands and when the agent last wrote — *being made · batch 2 of 6 ·
3 minutes ago* — and moves by itself while the page is open. The stage is one
of: *not started yet*, *source recovered*, *chapter table*, *batch N of M*,
*all batches in* and, once you finish it, nothing at all.

**In the reader** the header has a button, **being made · batch 2 of 6**, which
opens the **making panel**. It is a panel any device let in can read, on a
phone too, and it is drawn again by itself every few seconds while it is open:

- **Where it is.** The stage, when the agent last wrote, and the one line it
  says it is on. Under it, in a box of its own, anything you should know:
  *Parseh was updated during the making* (with the version it began under and
  this one — the tools the agent calls may have changed under it); a
  `making.json` the agent is writing at that moment and cannot be read just
  now (the book is still being made, and stays locked); or *the agent has
  written more since this page was built*.
- **look at it now.** Rebuilds this page from what has been written so far
  — the same job as **rebuild the reader** — and reloads it with the panel
  open again. The reader of a book being made shows the batches it has, and
  says under the last of them which chapters are still to come.
- **the PDF of these chapters.** The chapters written so far, typeset into a
  PDF (`frankdraft.pdf`), with a link to open it, and whether it is older than
  the newest batch. It is the reading edition's own draft build, a shell
  script, so where the computer has none — Windows — the panel says so
  plainly: *the PDF of these chapters is not available on this computer,
  which has no shell to make it. The reader is available: look at it now.*
- **The chapters.** The table the agent decided on, the chapters written so
  far and those still to come.
- **What the tools said.** The last words of `check_batch`, `assemble` and
  `verify_book`, as the agent kept them in `making.json`.
- **The agent's notes.** The end of `NOTES.md`.
- **What to change from now on**, **the folder** and **finish** — below.

## While it is made, the reader does not edit

The pipeline's truth is `annot/*.json`, and the `.tex` files are assembled
from it. An edit made in the reader writes the `.tex`, and the agent's next
assembly of that batch would erase it. So while a book is being made:

- the **pencil** over a chunk says why (*editing is off while an agent makes
  this book*) and opens the chunk sheet, which shows the chunk, shuts
  everything that writes it — the boxes cannot be typed in, and save, delete
  gloss, cut, join, the source mark and the LLM row are not there — and
  offers **ask about this chunk** (below);
- **book info** and **gloss with an LLM** are greyed, each with its reason;
- the passes, the glosses' clouds, the dictionary, the narration and the
  builds work exactly as in any book;
- and the server refuses the doors that write a chapter — an edit, a cut or a
  join, a chapter's name or a section, an LLM's answer, the free mark, more
  text — whatever the page does, answering *This book is being made by an
  agent … editing is off until the making is finished*.

Finishing ends all of it.

## Steering it

The agent re-reads `ASKS.md` before **every** batch, does what an entry asks
from the next batch on, writes in `NOTES.md` what it changed because of it,
and asks you in its own chat when an ask goes against the method. Two ways to
write an entry, both open to any device let in:

- **What to change from now on**, a box on the making panel: *keep the
  vocabulary lines shorter*, *write the meanings more literally*. **ask** adds
  a dated entry, and the panel counts the asks written so far.
- **Ask about this chunk**, in the chunk sheet of the reader: the chunk's
  address (*chapter 1, paragraph 2, subparagraph 2.1, chunk 4*), its text and
  your line, so a remark is anchored where you saw it.

An entry looks like this:

```markdown
## 2026-09-29 14:12 — about a chunk

chapter 1, paragraph 1, subparagraph 1.1, chunk 0:
> The old man

This meaning is too free: make it literal.
```

Whether a batch already built is redone because of an ask is the agent's to
propose and yours to accept, in its chat: nothing already checked is changed
behind your back.

## Finish

When the agent says every batch is in — the stage reads **all batches in** —
**finish…**, in the panel, ends the making. It is the computer's: from another
device the panel says so where the button would be. It asks *Has the agent
stopped?* first, because the agent must not write in the folder any more, and
then, as jobs whose progress you can watch:

1. **checks every paragraph against its source** (`verify_book`), and says in
   words what it found: *every paragraph reproduces its source (24
   paragraphs)*, or *2 paragraphs do not reproduce their source*, and for each
   one which chapter and paragraph and at which character; a book with no
   chapter yet is not finished;
2. **builds the whole book** — the PDF and the reader, the build the **build
   PDF** button runs — and says what TeX first complained of if it fails. A
   computer with no TeX cannot make the PDF, so there the reader alone is
   built and the answer says the PDF was left: such a computer could never
   have finished otherwise.

Both clean, the making ends: `making.json` says **finished**, the agent finds a
last entry in `ASKS.md` telling it to stop, the library card stops saying
*being made*, and the reader — reloaded as an ordinary book — edits again: its
pencil writes the `.tex`, which is the truth from then on. **`annot/` stays**
as the record of how the book was made; nothing of Parseh's assembles it
again. If either is not clean, the panel says which and what to do, the book
is still being made, and you can finish again once it is mended.

## Who may do what

| Any device let in | The computer Parseh runs on |
|---|---|
| read the making panel; **look at it now**; **the PDF of these chapters**; write an ask, and ask about a chunk | **make the book's folder** and see the instructions before it is made; **open the folder**; **finish** |

The second column changes what Parseh will run — an agent runs Parseh's own
tools in that folder, and Finish runs a build here — so a phone or another
computer that has been let in is refused in the words *That is changed on the
computer Parseh runs on and nowhere else, because it changes what Parseh will
run*, and the panel shows the reason instead of a button
([From a phone or another computer](doc:From a phone or another computer)).

## What `making.json` says

It is one small object Parseh and the agent keep between them, and the
first thing to read if you hand the folder to another agent:

| Key | Whose | What it says |
|---|---|---|
| `state` | Parseh's | `making`, or `finished`: written when the folder is made and by Finish, never by the agent |
| `parseh`, `started` | Parseh's | the version of Parseh the folder was made under, and when |
| `stage` | the agent's | `source`, `chapters`, `batch` or `done` |
| `on` | the agent's | one line: what it is on now |
| `chapters` | the agent's | the chapter table: `[{"chapter": 1, "paragraphs": 24}, …]` |
| `batches` | the agent's | `{"done": 3, "of": 12}` |
| `checks` | the agent's | what the tools last said |
| `updated` | the agent's | when it last wrote the file |

A file the agent wrote wrongly, or half, never stops the panel: what cannot
be read is said, and the book stays locked.

## What a finished book carries

Its **download** and **Backup every book** carry the original and `annot/`
beside what they always carried — the chapters, `book.json`, `NOTES.md`,
`source/`, the notes — so a copy on another computer keeps how it was made
and what it was made from ([Taking a book away](doc:Taking a book away)). The
agent's own files — `AGENTS.md`, `CLAUDE.md`, `.claude/`, `ASKS.md` and
`making.json` — never travel: they are about one making on one computer. The
bundle's format number went up with this; an older Parseh refuses such a
bundle in words, and going back to an older Parseh asks you to tick *I
understand* first ([Updating Parseh](doc:Updating Parseh)).

## When something goes wrong

The panel and the add page say what is wrong in words; the rows for this
page are in [When something looks wrong](../reference/troubleshooting.md#a-book-made-by-an-agent).
